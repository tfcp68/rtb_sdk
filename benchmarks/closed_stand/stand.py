#!/usr/bin/env python3
"""
Stand "closed manager": an unknown company inside the platform.

  open    run 1: the manager's companies are known (manager_ads.json), a policy decides which pool requests
          go to the manager (random share q / the whole pool). Output: a training log
          (request features + 200/204) — WITHOUT the manager's targeting, frequencies and winners.
  closed  run 2: the manager is a black box. The algorithm learns from the log (HierBeta §4.1 + user features §4.2 of
          strategy.md, pluggable) and routes the requests; the manager's answers are the only feedback.

Splitting the days (all ranges are base days of the prepared logs, `a:b`):
  open   --days 0:4                       train
  closed --val-days 4:5 --days 5:7        validation (tuning --tune-m) and test (the final numbers)

Examples:
  python benchmarks/closed_stand/stand.py open --name demo --policy random --q 0.5 --days 0:4
  python benchmarks/closed_stand/stand.py closed --name demo --days 4:7 --policies random hier_beta all
  python benchmarks/closed_stand/stand.py closed --name demo --val-days 4:5 --days 5:7 --tune-m 5 20 80
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED
from concurrent.futures.process import BrokenProcessPool
import dataclasses
import hashlib
import json
import multiprocessing as mp
import os
import sys
import time

# BLAS defaults can spawn many threads per worker. Respect explicit settings.
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(variable, "1")

import numpy as np
import polars as pl

HERE = os.path.dirname(os.path.abspath(__file__))
for p in (HERE, os.path.join(HERE, "..", "log_benchmark"), os.path.join(HERE, ".."), os.path.join(HERE, "..", "..", "src")):
    sys.path.insert(0, p)

from benchmarks import report_privacy as privacy
from stream import load_prepared, _user_mask, DAY  # noqa: E402
from ads import load_ads_file, build_pack  # noqa: E402
from engine_full import build_match_lists  # noqa: E402
from seller import Seller  # noqa: E402
from predictors import HierBeta, HierBetaUser, RuleTrie, ConstPredictor, CatBoostPredictor, UserCatBoost, XGBPredictor, UserXGB  # noqa: E402
from routers import SendAll, RandomShare, ThresholdQuota  # noqa: E402

PREPARED = os.path.join(HERE, "..", "logs", "prepared_20261012")
RUNS = os.path.join(HERE, "..", "..", "docs", "benchmark", "manager_routing", "runs")
POOL_DEVICES = ["ANDROID_TV_A", "ANDROID_SET_TOP_BOX_A", "SET_TOP_BOX_A", "SMART_TV_PLATFORM_A", "SMART_TV_PLATFORM_B", "SMART_TV_PLATFORM_C", "STREAMING_TV_BOX_A"]
CHUNK_S = 3600
def _n_cats(prep): return [len(prep.vocabs[n]) for n in prep.vocab_order]


# predictor policies: name -> factory(prep, m, seed); TUNABLE get m chosen by --tune-m on --val-days
MODELS = {
    "hier_beta": lambda prep, m, seed: HierBeta(prep.vocab_order, m=m),
    "hier_user": lambda prep, m, seed: HierBetaUser(prep.vocab_order, m=m),
    "rule_trie": lambda prep, m, seed: RuleTrie(prep.vocab_order, m=m),
    "catboost": lambda prep, m, seed: CatBoostPredictor(prep.vocab_order, seed=seed),
    "catboost_fb": lambda prep, m, seed: UserCatBoost(prep.vocab_order, stream=False, seed=seed),
    "catboost_user": lambda prep, m, seed: UserCatBoost(prep.vocab_order, stream=True, seed=seed),
    "xgboost": lambda prep, m, seed: XGBPredictor(prep.vocab_order, _n_cats(prep), seed=seed),
    "xgb_fb": lambda prep, m, seed: UserXGB(prep.vocab_order, _n_cats(prep), stream=False, seed=seed),
    "xgb_user": lambda prep, m, seed: UserXGB(prep.vocab_order, _n_cats(prep), stream=True, seed=seed),
}
TUNABLE = ("hier_beta", "hier_user", "rule_trie")


def parse_range(s: str) -> tuple[int, int]:
    a, b = s.split(":")
    return int(a), int(b)


def pool_mask_of(prep, devices) -> np.ndarray:
    labels = prep.vocabs["Device"]
    lut = np.zeros(len(labels), dtype=bool)
    reverse = {alias: label for label in labels
               for alias in (privacy.tag_label(label, "Device"), privacy.legacy_label(label))}
    for d in devices:
        d = reverse.get(d, d)
        if d in labels:
            lut[labels.index(d)] = True
    lut[0] = False
    return lut[prep.combos[:, prep.vocab_order.index("Device")]]


def iter_chunks(prep, rng_days, sample):
    """Yields (day_rel, ts_global int64, user, combo) per control chunk; ts counts from the start of the range."""
    a, b = rng_days
    for d in range(a, b):
        ts, user, combo = (np.asarray(x) for x in prep.day_arrays(d))
        m = _user_mask(user, sample)
        if m is not None:
            ts, user, combo = ts[m], user[m], combo[m]
        ts = ts.astype(np.int64) - a * DAY   # prepared ts is global (day d: d·DAY…)
        bounds = np.searchsorted(ts, np.arange((d - a) * DAY, (d - a + 1) * DAY + 1, CHUNK_S))
        for i in range(len(bounds) - 1):
            s, e = bounds[i], bounds[i + 1]
            yield d - a, ts[s:e], user[s:e].astype(np.int64), combo[s:e].astype(np.int64)


def count_requests(prep, rng_days, sample, pool_mask):
    tot = pool = 0
    for d in range(*rng_days):
        _, user, combo = (np.asarray(x) for x in prep.day_arrays(d))
        m = _user_mask(user, sample)
        if m is not None:
            combo = combo[m]
        tot += len(combo)
        pool += int(pool_mask[combo].sum())
    return tot, pool


def auto_sample(prep, rng_days, max_requests):
    full = sum(len(prep.day_arrays(d)[0]) for d in range(*rng_days))
    return min(1.0, max_requests / full)


# ───────────────────────────── simulation ─────────────────────────────

def simulate(prep, rng_days, sample, mgr_ads, our_ads, pool_mask, q_nominal, router_factory,
             manager_price, fallback_204=False, seed=0, collect_log=False, volume_factor=1.3, progress=None):
    """One pass of the stream. Returns a dict with the results (and the log of the sent requests)."""
    n_days = rng_days[1] - rng_days[0]
    if progress:
        progress("Traffic counting and campaign preparation")
    total, pool_n = count_requests(prep, rng_days, sample, pool_mask)
    # the manager's volumes are split by the match rates INSIDE the pool (it only ever sees the pool)
    pool_prep = dataclasses.replace(prep, combo_counts=prep.combo_counts * pool_mask)
    mgr_pack = build_pack(pool_prep, mgr_ads, max(1, round(q_nominal * pool_n)), n_days, volume_factor, True)
    our_pack = build_pack(prep, our_ads, total, n_days, volume_factor, True)
    mgr = Seller(mgr_pack, build_match_lists(prep, mgr_pack.targets))
    ours = Seller(our_pack, build_match_lists(prep, our_pack.targets))
    if progress:
        progress("modelling")
    router = router_factory()

    days = [dict(pool=0, sent=0, ok=0, mgr_rev=0.0, our_rev=0.0, requests=0) for _ in range(n_days)]
    per_hour = []
    log_parts = []
    t0 = time.time()
    processed = 0
    for chunk_no, (d, ts, user, combo) in enumerate(iter_chunks(prep, rng_days, sample), 1):
        sent = router.route(ts, user, combo)
        codes = []
        st = days[d]
        st["requests"] += len(ts)
        st["pool"] += int(pool_mask[combo].sum())
        for t, u, c, s in zip(ts.tolist(), user.tolist(), combo.tolist(), sent.tolist()):
            if s:
                if mgr.serve(t, u, c) >= 0:
                    codes.append(200)
                else:
                    codes.append(204)
                    if fallback_204:
                        ours.serve(t, u, c)
            else:
                ours.serve(t, u, c)
        codes = np.array(codes, dtype=np.uint16)
        router.observe(ts, user, combo, sent, codes)
        st["sent"] += len(codes)
        st["ok"] += int((codes == 200).sum())
        per_hour.append(dict(
            start_s=rng_days[0] * DAY + (chunk_no - 1) * CHUNK_S,
            end_s=rng_days[0] * DAY + chunk_no * CHUNK_S,
            requests=len(ts), pool=int(pool_mask[combo].sum()),
            sent=len(codes), ok=int((codes == 200).sum()),
        ))
        if collect_log and len(codes):
            si = np.flatnonzero(sent)
            log_parts.append((ts[si] + rng_days[0] * DAY, user[si], combo[si], codes))
        processed += len(ts)
        if progress and (chunk_no % 6 == 0 or chunk_no == n_days * 24):
            progress(f"request {_i(processed)}/{_i(total)} ({processed / total * 100:.1f}%)" if total
                     else f"intervaled {chunk_no}/{n_days * 24}")
    # per-day revenue of the ours/manager is derived from totals (daily split of ours is not tracked)
    sent_n = sum(x["sent"] for x in days)
    ok_n = sum(x["ok"] for x in days)
    res = dict(
        policy=getattr(router, "name", "?"), days=list(rng_days), sample=sample, requests=total, pool=pool_n,
        sent=sent_n, ok=ok_n, per_day=days, per_hour=per_hour,
        time_series_origin_unix=prep.meta.get("t0", 0),
        sent_pct_pool=sent_n / pool_n if pool_n else 0.0, sent_pct_all=sent_n / total if total else 0.0,
        sellthrough=ok_n / sent_n if sent_n else 0.0, ok_pct_pool=ok_n / pool_n if pool_n else 0.0,
        manager_price=manager_price, manager_revenue=ok_n * manager_price, our_revenue=ours.revenue,
        total_revenue=ok_n * manager_price + ours.revenue,
        our_impressions=ours.total_impressions, our_requests=ours.requests, our_miss_nomatch=ours.miss_nomatch,
        our_miss_filtered=ours.miss_filtered,
        ours=[dict(id=our_pack.ids[a], name=our_pack.names[a], cpm=our_pack.cpm[a], volume=our_pack.volume[a],
                   impressions=ours.impressions[a]) for a in range(our_pack.n)],
        hidden_manager=[dict(id=mgr_pack.ids[a], name=mgr_pack.names[a], volume=mgr_pack.volume[a],
                             impressions=mgr.impressions[a]) for a in range(mgr_pack.n)],
        seconds=time.time() - t0,
    )
    if collect_log:
        res["_log"] = tuple(np.concatenate([p[i] for p in log_parts]) for i in range(4)) if log_parts else None
        res["_pool"] = tuple(np.concatenate([p[i] for p in pool_parts]) for i in range(3))
    return res


def write_log(path, prep, log):
    ts, user, combo, codes = log
    tags = prep.combos[combo]
    cols = {"ts": ts.astype(np.int32), "user": user.astype(np.uint32), "combo": combo.astype(np.int32)}
    for i, v in enumerate(prep.vocab_order):
        labels = np.array(prep.vocabs[v], dtype=object)
        cols[v] = labels[tags[:, i]]
    cols["status"] = codes
    pl.DataFrame(cols).write_parquet(path, compression="zstd")


def write_pool_log(path, pool):
    ts, user, combo = pool
    pl.DataFrame({"ts": ts.astype(np.int32), "user": user.astype(np.uint32), "combo": combo.astype(np.int32)}).write_parquet(
        path, compression="zstd")


def read_pool_log(path):
    """(ts, user) of all pool requests of the open run, or None for runs made before the pool log existed."""
    if not os.path.exists(path):
        return None
    df = pl.read_parquet(path, columns=["ts", "user"])
    return df["ts"].to_numpy().astype(np.int64), df["user"].to_numpy().astype(np.int64)


def read_log(path, prep):
    df = pl.read_parquet(path)
    combo = df["combo"].to_numpy().astype(np.int64)
    return dict(ts=df["ts"].to_numpy().astype(np.int64), user=df["user"].to_numpy().astype(np.int64),
                tags=prep.combos[combo], y=(df["status"].to_numpy() == 200), status=df["status"].to_numpy())


def prepared_signature(prep):
    digest = hashlib.sha256(prep.combos.tobytes())
    digest.update(json.dumps({k: prep.meta[k] for k in ("vocabs", "vocab_order", "t0", "days")},
                             ensure_ascii=False, sort_keys=True).encode())
    return digest.hexdigest()


# ───────────────────────────── report ─────────────────────────────

def _p(x): return f"{x * 100:.2f}%"
def _i(x): return f"{int(x):,}".replace(",", " ")


def table(head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def plot_sellout(path, results):
    """Plot actual routed outcomes; undefined hourly rates remain gaps."""
    try:
        import matplotlib
    except ImportError:
        print("Plot skipped: install matplotlib (pip install -e '.[benchmark]').", flush=True)
        return False
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.ticker import PercentFormatter
    from datetime import datetime, timedelta, timezone

    tz = timezone(timedelta(hours=3))
    baseline = next((r for r in results if r["policy"] == "random"), None)
    base_rates = {h["start_s"]: h["ok"] / h["sent"] if h["sent"] else np.nan
                  for h in baseline["per_hour"]} if baseline else {}
    fig, axes = plt.subplots(2 if baseline else 1, 1, figsize=(15, 8 if baseline else 5),
                             sharex=True, squeeze=False)
    axes = axes[:, 0]
    for result in results:
        hours = result["per_hour"]
        dates = [datetime.fromtimestamp(result["time_series_origin_unix"] +
                                       (h["start_s"] + h["end_s"]) / 2, tz) for h in hours]
        rates = np.array([h["ok"] / h["sent"] if h["sent"] else np.nan for h in hours])
        style = dict(color="black", linestyle="--", linewidth=2) if result is baseline else {}
        line, = axes[0].plot(dates, rates, label=result["policy"], **style)
        if baseline:
            base = np.array([base_rates.get(h["start_s"], np.nan) for h in hours])
            lift = np.full(len(hours), np.nan)
            np.divide(rates, base, out=lift, where=base > 0)
            axes[1].plot(dates, lift - 1, color=line.get_color(),
                         linestyle=style.get("linestyle", "-"))
    axes[0].set(title="Hourly hidden-manager sellout: observed simulator responses",
                ylabel="200 / sent", ylim=(0, 1))
    axes[0].legend(loc="upper left", bbox_to_anchor=(1.01, 1), fontsize=8)
    if baseline:
        axes[1].set(ylabel="Relative increase to random")
        axes[1].axhline(0, color="gray", linestyle=":")
    axes[-1].set_xlabel("Test period, Moscow-time (UTC+3)")
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%d.%m\n%H:%M", tz=tz))
    for ax in axes:
        ax.yaxis.set_major_formatter(PercentFormatter(1))
        ax.grid(alpha=.25)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return True


def section(title, results):
    L = [f"### {title}", ""]
    head = ["Politics", "Days", "Sent / pool", "Sent / traffic", "Sell-through (200/gone)", "200 / pool", "200 piece",
            "Manager’s revenue", "Revenue from ours", "Total"]
    rows = [[r["policy"], f"{r['days'][0]}:{r['days'][1]}", _p(r["sent_pct_pool"]), _p(r["sent_pct_all"]),
             _p(r["sellthrough"]), _p(r["ok_pct_pool"]), _i(r["ok"]), _i(r["manager_revenue"]),
             _i(r["our_revenue"]), _i(r["total_revenue"])] for r in results]
    L += [table(head, rows), ""]
    base = next((r for r in results if r["policy"] == "random"), None)
    if base:
        L.append("Regarding `random` (same-size): " + "; ".join(
            f"`{r['policy']}`: sell-through {(r['sellthrough'] - base['sellthrough']) * 100:+.2f} p.p., "
            f"200 {r['ok'] - base['ok']:+,}".replace(",", " ") for r in results if r is not base) + "\n")
    for r in results:
        L += [f"#### `{r['policy']}` — day-to-day", "",
              table(["Day", "Requests", "Pool", "Sent", "Sent/pool", "200", "Sell-through"],
                    [[i, _i(d["requests"]), _i(d["pool"]), _i(d["sent"]),
                      _p(d["sent"] / d["pool"] if d["pool"] else 0), _i(d["ok"]),
                      _p(d["ok"] / d["sent"] if d["sent"] else 0)] for i, d in enumerate(r["per_day"])]), ""]
        L += [f"Our companies (`{r['policy']}`): sold out {_i(r['our_impressions'])} impressions, "
              f"targetless {_p(r['our_miss_nomatch'] / max(r['our_requests'], 1))}, "
              f"filtered {_p(r['our_miss_filtered'] / max(r['our_requests'], 1))} request, come down to ours.", "",
              table(["Campaign", "cpm", "volume", "impressions", "sell-out", "revenue"],
                    [[c["name"], c["cpm"], _i(c["volume"]), _i(c["impressions"]),
                      _p(c["impressions"] / c["volume"]), _i(c["impressions"] * c["cpm"])] for c in r["ours"]]), ""]
        L += [f"Manager’s Hidden Companies (`{r['policy']}`, diagnostics — algorithm can’t see):", "",
              table(["Campaign", "volume", "200", "sell-out"],
                    [[c["name"], _i(c["volume"]), _i(c["impressions"]), _p(c["impressions"] / c["volume"])]
                     for c in r["hidden_manager"]]), ""]
    return "\n".join(L)


# ───────────────────────────── modes ─────────────────────────────

def cmd_open(a):
    prep = load_prepared(a.prepared)
    rng_days = parse_range(a.days)
    out = os.path.join(RUNS, a.name)
    os.makedirs(out, exist_ok=True)
    pool_mask = pool_mask_of(prep, a.pool_devices)
    sample = a.sample or auto_sample(prep, rng_days, a.max_requests)
    q = 1.0 if a.policy == "all" else a.q
    mgr_ads, our_ads = load_ads_file(a.manager_ads), load_ads_file(a.our_ads)
    mk = (lambda: SendAll(pool_mask, prep.combos)) if a.policy == "all" else \
         (lambda: RandomShare(pool_mask, prep.combos, a.q, a.seed))
    print(f"open: days {rng_days}, sample={sample:.4f}, policy={a.policy}, q={q}")
    r = simulate(prep, rng_days, sample, mgr_ads, our_ads, pool_mask, q, mk, a.manager_price,
                 a.fallback_204, a.seed, collect_log=True)
    write_log(os.path.join(out, "train_log.parquet"), prep, r.pop("_log"))
    write_pool_log(os.path.join(out, "pool_log.parquet"), r.pop("_pool"))
    meta = dict(sample=sample, q=q, policy=a.policy, pool_devices=a.pool_devices, days=list(rng_days), seed=a.seed,
                prepared_signature=prepared_signature(prep), prepared_source=prep.meta.get("source", "legacy"),
                manager_ads=a.manager_ads, our_ads=a.our_ads, manager_price=a.manager_price,
                fallback_204=a.fallback_204)
    json.dump(privacy.report(meta), open(os.path.join(out, "meta.json"), "w"), ensure_ascii=False, indent=1)
    md = [f"# Open run `{a.name}`", "", f"Parameters: {json.dumps(meta, ensure_ascii=False)}", "",
          section("Open run (learning-log)", [r])]
    open(os.path.join(out, "open_report.md"), "w", encoding="utf-8").write(privacy.markdown("\n".join(md)))
    print(f"  gone {_i(r['sent'])} ({_p(r['sent_pct_pool'])} pool), sell-through {_p(r['sellthrough'])}, "
          f"{r['seconds']:.0f}s\n  log: {out}/train_log.parquet")


_CTX: dict = {}


def _run_policy(task):
    pol, rng_days, m = task
    c = _CTX
    prep = c["prep"]
    label = f"{pol}(m={m:g})" if pol in TUNABLE else pol

    def progress(message):
        print(f"  [{label}] {message}", flush=True)

    progress("launch")
    predictor = None
    if pol == "all":
        mk = lambda: SendAll(c["pool_mask"], prep.combos)
    elif pol == "random":
        mk = lambda: RandomShare(c["pool_mask"], prep.combos, c["q"], c["seed"])
    elif pol in MODELS:
        def mk():
            nonlocal predictor
            pred = MODELS[pol](prep, m, c["seed"])
            predictor = pred
            if hasattr(pred, "observe_pool") and c["pool"] is not None:
                pred.observe_pool(*c["pool"])
            lg = c["log"]
            pred.update(lg["tags"], lg["y"], lg["ts"], lg["user"])
            n = len(lg["y"])
            rng = np.random.default_rng(c["seed"])
            if pred.stateful:
                seed_ref = pred.seed_scores(50_000, rng)
            else:
                sub = rng.choice(n, min(n, 50_000), replace=False)
                seed_ref = (lg["ts"][sub], lg["user"][sub], lg["tags"][sub])
            r = ThresholdQuota(c["pool_mask"], prep.combos, pred, c["q"], c["eps"], c["seed"],
                               seed_ref=seed_ref, ts_shift=rng_days[0] * DAY)
            r.name = f"{pol}(m={m:g})" if pol in TUNABLE else pol
            return r
    else:
        raise SystemExit(f"politics-story {pol}")
    r = simulate(prep, rng_days, c["sample"], c["mgr_ads"], c["our_ads"], c["pool_mask"], c["q"], mk,
                 c["price"], c["fallback_204"], c["seed"], progress=progress)
    r["policy"] = r["policy"] if pol in MODELS else pol
    if pol == "rule_trie":
        r["inferred_rules"] = predictor.top_rules(prep.vocab_order, prep.vocabs)
    return r


def cmd_closed(a):
    print("closed: loading of prepared data and training log", flush=True)
    prep = load_prepared(a.prepared)
    out = os.path.join(RUNS, a.name)
    meta = json.load(open(os.path.join(out, "meta.json")))
    signature = meta.get("prepared_signature")
    if signature is None:
        if os.path.realpath(a.prepared) != os.path.realpath(os.path.join(HERE, "..", "logs", "prepared")):
            raise SystemExit("The old log without a signature is prepared on the previous data: point out --prepared benchmarks/logs/prepared Or create a new one open-run")
    elif signature != prepared_signature(prep):
        raise SystemExit("Learning Log Created for Another Data Set: Use the same --prepared Or create a new one open-run")
    q = a.q if a.q is not None else 0.8
    pool_mask = pool_mask_of(prep, meta["pool_devices"])
    log = read_log(os.path.join(out, "train_log.parquet"), prep)
    _CTX.update(prep=prep, pool_mask=pool_mask, q=q, seed=a.seed, eps=a.eps, sample=meta["sample"],
                mgr_ads=load_ads_file(meta["manager_ads"]), our_ads=load_ads_file(meta["our_ads"]),
                price=meta["manager_price"], fallback_204=meta["fallback_204"], log=log,
                pool=read_pool_log(os.path.join(out, "pool_log.parquet")))
    test_days = parse_range(a.days)
    val_days = parse_range(a.val_days) if a.val_days else None
    # _CTX reaches the workers only through fork; without it (Windows) the policies run one by one
    ctx = mp.get_context("fork") if "fork" in mp.get_all_start_methods() and a.workers > 1 else None
    sections = []

    def run(tasks):
        if ctx is None:
            return [_run_policy(t) for t in tasks]
        with ctx.Pool(min(a.workers, len(tasks))) as pool:
            return pool.map(_run_policy, tasks)

    ms = a.tune_m or [a.m]
    tuned = [p for p in a.policies if p in TUNABLE]
    pols = [p for p in a.policies if p not in TUNABLE]
    m_best = {p: ms[0] for p in tuned}
    if val_days:
        tasks = [(p, val_days, a.m) for p in pols] + [(p, val_days, m) for p in tuned for m in ms]
        print(f"closed: validation {val_days}, task {len(tasks)}")
        res = run(tasks)
        sections.append(section(f"Validation (days {val_days[0]}:{val_days[1]})", res))
        for p in tuned:
            rs = [r for r, t in zip(res, tasks) if t[0] == p]
            if len(rs) > 1:
                m_best[p] = max(zip(rs, ms), key=lambda x: x[0]["ok"])[1]
                sections.append(f"Selected by validation for `{p}`: m = {m_best[p]:g} (maximum 200)\n")
    elif len(ms) > 1:
        raise SystemExit("--tune-m demand --val-days (The test cannot be used for selection)")
    tasks = [(p, test_days, a.m) for p in pols] + [(p, test_days, m_best[p]) for p in tuned]
    print(f"closed: test {test_days}, q={q}, task {len(tasks)}")
    res = run(tasks)
    for r in res:
        print(f"  {r['policy']:<18s} gone/pool {_p(r['sent_pct_pool'])}  sell-through {_p(r['sellthrough'])}  "
              f"200: {_i(r['ok'])}  total revenue {_i(r['total_revenue'])}  {r['seconds']:.0f}s")
    sections.append(section(f"Test (days {test_days[0]}:{test_days[1]})", res))
    for result in res:
        if "inferred_rules" in result:
            sections += ["### Segments rule_trie post-test", "",
                         "Observed segments, non-campaign IDs; statistics online-renewal.", "",
                         table(["Tags", "Requests", "200", "Evaluation", "Deviation from the general"],
                               [[json.dumps(x["tags"], ensure_ascii=False), _i(x["count"]), _i(x["successes"]),
                                 _p(x["probability"]), f'{x["lift"] * 100:+.2f} p.p.']
                                for x in result["inferred_rules"]]), ""]
    md = [f"# Closed run `{a.name}`", "",
          f"Training on the open run log (days {meta['days'][0]}:{meta['days'][1]}, policy `{meta['policy']}`, "
          f"{_i(len(log['y']))} lineage). Target share q = {q}, ε = {a.eps}, price 200 = {meta['manager_price']}.", ""] + sections
    stamp = time.strftime("%Y%m%d_%H%M")
    path = os.path.join(out, f"closed_report_{stamp}.md")
    plot_name = f"sellout_over_time_{stamp}.png"
    if plot_sellout(os.path.join(out, plot_name), res):
        md += ["", "### selaut time (test)", "",
               f"![Manager’s hourly selaut]({plot_name})", "",
               "selaut = 200 / sent in an hour. Growth = polluter / selau random − 1; "
               "It’s a relative percentage, non-interest-point. Empty hours and zero comparisons "
               "selaut random ripped. Each policy changes budgets and frequencies separately "
               "manager; It’s a repeat routing simulation, Not selection on fixed answers."]
    open(path, "w", encoding="utf-8").write(privacy.markdown("\n".join(md)))
    json.dump(privacy.report(res), open(path.replace(".md", ".json"), "w"), ensure_ascii=False, indent=1)
    print(f"Report: {path}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="mode", required=True)
    for name in ("open", "closed"):
        s = sub.add_parser(name)
        s.add_argument("--name", required=True, help="experiment (folder docs/benchmark/manager_routing/runs/<name>)")
        s.add_argument("--prepared", default=PREPARED)
        s.add_argument("--seed", type=int, default=42)
        s.add_argument("--days", default="0:4" if name == "open" else "4:7", help="base-day a:b")
    o = sub.choices["open"]
    o.add_argument("--policy", choices=["random", "all"], default="random")
    o.add_argument("--q", type=float, default=0.8, help="share no-mobile pool, managerial (policy=random)")
    o.add_argument("--pool-devices", nargs="+", default=POOL_DEVICES)
    o.add_argument("--manager-ads", default=os.path.join(HERE, "manager_target50_20261012.json"))
    o.add_argument("--our-ads", default=os.path.join(HERE, "..", "log_benchmark", "ads_manual.json"))
    o.add_argument("--manager-price", type=float, default=150.0, help="flat-rate 200 manager")
    o.add_argument("--fallback-204", action="store_true", help="request 204 We are leaving our companies")
    o.add_argument("--sample", type=float, default=None)
    o.add_argument("--max-requests", type=int, default=5_000_000)
    c = sub.choices["closed"]
    c.add_argument("--val-days", default=None, help="validation a:b (necessarily)")
    c.add_argument("--policies", nargs="+", default=["random", "hier_beta", "hier_user", "rule_trie", "all"], choices=["random", "all", *MODELS])
    c.add_argument("--q", type=float, default=None, help="target-pool (default: 0.8)")
    c.add_argument("--eps", type=float, default=0.02, help="randomization")
    c.add_argument("--m", type=float, default=20.0, help="priorism HierBeta")
    c.add_argument("--tune-m", type=float, nargs="+", default=None, help="significance m validation")
    c.add_argument("--workers", type=int, default=1, help="number of parallel processes (default: 1)")
    a = p.parse_args()
    (cmd_open if a.mode == "open" else cmd_closed)(a)


if __name__ == "__main__":
    main()
