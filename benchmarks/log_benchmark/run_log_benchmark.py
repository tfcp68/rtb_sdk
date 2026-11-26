#!/usr/bin/env python3
"""
Benchmark of auction algorithms on real logs with the full auction logic.

Beforehand: python benchmarks/log_benchmark/prepare_logs.py

Examples:
    # a week, all three traffic types, generated companies, ~5M requests per run
    python benchmarks/log_benchmark/run_log_benchmark.py \\
        --ads benchmarks/log_benchmark/ads_generated.json --period week

    # a day, a manual set, all traffic, 4 processes
    python benchmarks/log_benchmark/run_log_benchmark.py \\
        --ads benchmarks/log_benchmark/ads_manual.json --period day --sample 1.0 --traffic balanced

    # a month (the week is repeated with noise), 20M requests per run
    python benchmarks/log_benchmark/run_log_benchmark.py --ads ... --period month --max-requests 20000000

    # quick check
    python benchmarks/log_benchmark/run_log_benchmark.py --ads ... --period day --max-requests 300000 \\
        --algos best_price best_velocity balancer a2_single_valued
"""
from __future__ import annotations

import argparse
import multiprocessing as mp
import os
import sys
import time
from dataclasses import asdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "..", "src"))

from stream import load_prepared, nominal_requests, iter_days, sampled_day_sizes  # noqa: E402
from ads import (load_ads_file, build_pack, TRAFFIC_FACTORS, BASE_VOLUME_FACTOR)  # noqa: E402
from engine_full import (run_algorithm, build_match_lists, ALL_ALGORITHMS, ADWORDS,
                         CLASSIC_STRATEGIES, BALANCER, BALANCER_TEMPORAL)  # noqa: E402
from report_logs import scenario_section, write_report, dump_json, _pct, _int  # noqa: E402

PERIODS = {"day": 1, "week": 7, "month": 30}
NOTES = [
    "Only PRECISE-matching (fuzzy and parasitic-limits do not apply).",
    "Filter chain as in `auction/simulation`: active (start/end) → ad_frequency_limit "
    "(slip-window t/h/d/w/m) → user_frequency_limit → min_interval → precise match → winner.",
    "`min_interval` readable `ad_frequency_limit` (does SDK `get_ad_min_interval`) and applies to a pair user×ad.",
    "velocity/heuristics/hybrid: month_limit = `get_real_month_volume(ad)` of SDK, currentness = show-off "
    "slippery 30 daylight.",
    "volume — show-line (synthetic benchmark); budget = volume × cpm (necessary A3).",
    "User = client_id (hash uint32). Tags: Region, Device, Child, Category (VOD), Channel (live); "
    "Category and Channel are mutually exclusive; sparsely `<other>`.",
    "Adwords (a2/a3) single-start (not N runs) candidate-pool, filtered.",
    "Balancer: `balance_traffic` on the empirical probabilities of tags from logs, weight = distribution × P(req) / P(ad) "
    "candidate-pool, filtered. If all pool weights are zero — get out best_price (fallback).",
    "balancer_temporal: `seasonal_balance_traffic` period-day: hourly profile, start/end and "
    "frequency limits of companies, saturation user_frequency_limit; volume smear over the remaining active days.",
]

_CTX: dict = {}


def _work(task):
    algo, pack_key = task
    c = _CTX
    pack = c["packs"][pack_key]
    stream = iter_days(c["prep"], c["days"], c["sample"], c["traffic_factor"], c["seed"],
                       c["jitter"], c["noise"])
    r = run_algorithm(algo, pack, c["match"][pack_key], stream, c["prep"], seed=c["seed"],
                      n_requests_hint=c["requests_est"], period_days=c["days"])
    return (algo, pack_key, r)


def parse_args():
    p = argparse.ArgumentParser(description="Benchmark Log Auctions (logic)",
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("--ads", required=True, help="JSON company (ads_manual.json / ads_generated.json)")
    p.add_argument("--n-ads", type=int, nargs="+", default=None, help="Take first N company (multiple values)")
    p.add_argument("--prepared", default=os.path.join(HERE, "..", "logs", "prepared_20261012"))
    p.add_argument("--period", nargs="+", choices=list(PERIODS), default=["week"])
    p.add_argument("--traffic", nargs="+", choices=list(TRAFFIC_FACTORS), default=["shortage", "balanced", "excess"])
    p.add_argument("--sample", type=float, default=None, help="Percentage of users (0..1). By default — by --max-requests")
    p.add_argument("--max-requests", type=int, default=5_000_000,
                   help="The upper limit of the nominal number of requests for running (motor-car-sample). default: 5M")
    p.add_argument("--workers", type=int, default=4, help="Parallel processes (default 4)")
    p.add_argument("--memory-gb", type=float, default=4.0, help="Memory budget, GB (default 4); limiting the number of processes")
    p.add_argument("--algos", nargs="+", default=None, help=f"Subset of algorithms (default: everything). Available: {', '.join(ALL_ALGORITHMS)}")
    p.add_argument("--no-adwords", action="store_true",
                   help="Don’t let go a2_single_valued and a3_small (longest algorithms)")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--jitter", type=int, default=120, help="Shifting the time of repeating days, ± seconds")
    p.add_argument("--noise", type=float, default=0.02, help="Percentage of missed/duplicate requests in repetitions")
    p.add_argument("--volume-factor", type=float, default=BASE_VOLUME_FACTOR)
    p.add_argument("--ref-no-limits", action="store_true",
                   help="Add reference runs best_price/best_velocity frequency-free")
    p.add_argument("--output", default=None)
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def main():
    a = parse_args()
    algos = a.algos or ALL_ALGORITHMS
    if a.no_adwords:
        algos = [x for x in algos if x not in ADWORDS]
        if not algos:
            raise SystemExit("After --no-adwords There are no algorithms left")
    bad = [x for x in algos if x not in ALL_ALGORITHMS]
    if bad:
        raise SystemExit(f"Unknown algorithms: {bad}")

    prep = load_prepared(a.prepared)
    ads_all = load_ads_file(a.ads)
    n_list = a.n_ads or [len(ads_all)]
    total_full = sum(sampled_day_sizes(prep, 1.0))
    per_day_avg = total_full / prep.n_days

    scenarios = [(p, t, n) for p in a.period for n in n_list for t in a.traffic]
    print(f"Logs: {prep.n_days} days., {total_full:,} requests; scenario: {len(scenarios)}; "
          f"algorithms: {len(algos)}; workers={a.workers}")
    if a.dry_run:
        for s in scenarios:
            print("  ", s)
        return

    out = a.output or os.path.join(HERE, "..", "..", "docs", "benchmark", "auction", "log_replay", f"log_benchmark_{time.strftime('%Y%m%d_%H%M')}.md")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)

    sections, summary, js = [], [], []
    summary.append(["#", "Period", "Traffic", "Campaigns", "Requests", "Sellout best_price",
                    "best_price: lost-limitless", "Best in revenue", "Revenue from the best / best_price"])
    for si, (period, traffic, n_ads) in enumerate(scenarios, 1):
        days = PERIODS[period]
        full_n = per_day_avg * days
        sample = a.sample if a.sample is not None else min(1.0, a.max_requests / full_n)
        factor = TRAFFIC_FACTORS[traffic]
        t_sc = time.time()
        nominal = nominal_requests(prep, days, sample)
        requests_est = int(nominal * factor)
        ads = ads_all[:n_ads]
        print(f"\n[{si}/{len(scenarios)}] {period} / {traffic} / {len(ads)} company: "
              f"sample={sample:.4f}, denomination={nominal:,}, requests≈{requests_est:,}", flush=True)

        packs = {"main": build_pack(prep, ads, nominal, days, a.volume_factor, True)}
        match = {"main": build_match_lists(prep, packs["main"].targets)}
        tasks = [(x, "main") for x in algos]
        if a.ref_no_limits:
            packs["nolim"] = build_pack(prep, ads, nominal, days, a.volume_factor, False)
            match["nolim"] = match["main"]
            tasks += [(x, "nolim") for x in ("best_price", "best_velocity") if x in algos]

        # memory estimate per process
        max_day = int(max(sampled_day_sizes(prep, sample)) * max(1.0, factor) * 1.1)
        per_worker_gb = (max_day * 56 + requests_est * 220) / 1e9 + 0.3
        workers = max(1, min(a.workers, int(a.memory_gb // per_worker_gb) or 1, len(tasks)))
        if workers < a.workers:
            print(f"  memory: ≈{per_worker_gb:.1f} GB/process → workers={workers} (budget {a.memory_gb} GB)")
        # heavy ones first
        weight = lambda t: 0 if t[0] in ADWORDS else (1 if t[0] in (BALANCER, BALANCER_TEMPORAL) else 2)
        tasks.sort(key=weight)

        _CTX.update(dict(prep=prep, packs=packs, match=match, days=days, sample=sample,
                         traffic_factor=factor, seed=a.seed, jitter=a.jitter, noise=a.noise,
                         requests_est=requests_est))
        results, ref = {}, {}
        t0 = time.time()
        ctx = mp.get_context("fork")
        with ctx.Pool(workers) as pool:
            for algo, key, r in pool.imap_unordered(_work, tasks):
                (results if key == "main" else ref)[algo] = r
                print(f"  ✓ {algo:<18s}{'(limitless)' if key == 'nolim' else '':<14s} "
                      f"impressions={r.total_impressions:>10,} fill={r.fill_rate:6.1%} "
                      f"{r.seconds:6.0f}s", flush=True)
        for algo, r in ref.items():
            r.algo = f"{algo}@no-limits"
            results[r.algo] = r

        sc = dict(period=period, days=days, traffic=traffic, traffic_factor=factor, n_ads=len(ads),
                  sample=sample, nominal=nominal, requests=next(iter(results.values())).requests,
                  volume_factor=a.volume_factor)
        pack = packs["main"]
        sections.append(scenario_section(si, sc, pack, results))
        main_res = {k: v for k, v in results.items() if "@" not in k}
        bp = results.get("best_price")
        best = max(main_res.values(), key=lambda r: r.revenue)
        total_vol = sum(pack.volume)
        summary.append([str(si), period, traffic, str(len(ads)), _int(sc["requests"]),
                        _pct(bp.total_impressions / total_vol) if bp else "—",
                        _pct(bp.miss_by_limits / bp.requests) if bp else "—",
                        best.algo,
                        f"{best.revenue / bp.revenue * 100:.1f}%" if bp else "—"])
        js.append(dict(scenario=sc, ads=dict(ids=pack.ids, volume=pack.volume, cpm=pack.cpm,
                                              match_rate=pack.match_rate),
                       results={k: asdict(v) for k, v in results.items()}))
        print(f"  script {time.time() - t_sc:.0f}s", flush=True)
        write_report(out, dict(ads_file=a.ads, logs=a.prepared, periods=a.period, traffic=a.traffic,
                               n_ads=n_list, max_requests=a.max_requests, sample=a.sample or "auto",
                               seed=a.seed, jitter=f"±{a.jitter}s", noise=a.noise, workers=a.workers,
                               volume_factor=a.volume_factor),
                     sections, summary, NOTES)
        dump_json(out.replace(".md", ".json"), js)
    print(f"\nReport: {out}")


if __name__ == "__main__":
    main()
