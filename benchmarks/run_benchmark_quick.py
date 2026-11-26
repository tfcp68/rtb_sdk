#!/usr/bin/env python3
"""
Quick benchmark: only 10k and 100k requests, a separate results file.

Run:
    python benchmarks/run_benchmark_quick.py
    python benchmarks/run_benchmark_quick.py --companies 3 10 --traffic balanced
    python benchmarks/run_benchmark_quick.py --runs 100 --output docs/benchmark/auction/synthetic/quick.md
"""
import argparse
import sys
import os
import time
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from auction_benchmark.seeds import (
    build_company_set,
    build_scenario_ads,
    actual_request_count,
    SCENARIO_MATRIX,
    CLASSIC_STRATEGIES,
    ADWORDS_ALGORITHMS,
    DEFAULT_ADWORDS_RUNS,
)
from auction_benchmark.engine import run_scenario
from auction_benchmark.reporter import (
    format_scenario_section,
    write_report_header,
    write_toc,
    write_summary_table,
    build_summary_row,
    hybrid_summary_cells,
    balancer_summary_cells,
    REPORT_SIMPLIFICATIONS,
)

# Only small volumes
QUICK_REQUEST_COUNTS = [10_000, 100_000]


def parse_args():
    p = argparse.ArgumentParser(description="Fast benchmark (10k / 100k requests)")
    p.add_argument("--companies", nargs="+", type=int, default=None)
    p.add_argument("--traffic", nargs="+", choices=["balanced", "shortage", "excess"], default=None)
    p.add_argument("--runs", type=int, default=None,
                   help="Fixed number of runs A2/A3 (default: 1000 for 10k, 300 for 100k)")
    p.add_argument("--output", default=None)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--no-adwords", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def build_scenario_list(args):
    matrix = [(c, n, t) for c, n, t in SCENARIO_MATRIX if n in QUICK_REQUEST_COUNTS]
    if args.companies:
        matrix = [(c, n, t) for c, n, t in matrix if c in args.companies]
    if args.traffic:
        matrix = [(c, n, t) for c, n, t in matrix if t in args.traffic]
    return matrix


def fmt_n(n):
    return {10_000: "10k", 100_000: "100k"}.get(n, str(n))


def make_progress_bar_factory():
    algo_labels = {"a2_single_valued": "A2", "a3_small": "A3"}
    def factory(algo: str):
        prefix = algo_labels.get(algo, algo)
        start = [time.time()]
        def cb(done, total):
            pct = done / total * 100
            elapsed = time.time() - start[0]
            eta = (elapsed / done * (total - done)) if done else 0
            bar_len = 28
            filled = int(bar_len * done / total)
            bar = "█" * filled + "░" * (bar_len - filled)
            print(f"\r  {prefix} [{bar}] {pct:5.1f}%  ETA {eta:4.0f}s", end="", flush=True)
            if done == total:
                print(f"\r  {prefix} [{bar}] 100%  {elapsed:.1f}s               ")
        return cb
    return factory


def _build_io_md(writer, *args):
    import io
    buf = io.StringIO()
    writer(buf, *args)
    return buf.getvalue()


def main():
    args = parse_args()
    scenarios = build_scenario_list(args)

    if not scenarios:
        print("No scripts, filter-appropriate.")
        return

    if args.dry_run:
        print(f"Scripts for the run: {len(scenarios)}\n")
        for i, (nc, nr, tt) in enumerate(scenarios, 1):
            runs = args.runs or DEFAULT_ADWORDS_RUNS.get(nr, 10)
            print(f"  {i:3d}. {nc:3d} campaigns  {fmt_n(nr):>5s} requests  {tt:<10s}  adwords runs={runs}")
        return

    if args.output:
        output_path = args.output
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        output_path = os.path.join(
            os.path.dirname(__file__), "..", "docs", "benchmark", "auction", "synthetic", f"benchmark_quick_{ts}.md"
        )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    adwords_algos = [] if args.no_adwords else ADWORDS_ALGORITHMS
    runs_map = {n: (args.runs or DEFAULT_ADWORDS_RUNS.get(n, 10)) for _, n, _ in scenarios}

    summary_rows = []
    toc_entries = []

    with open(output_path, "w", encoding="utf-8-sig") as f:
        write_report_header(
            f,
            total_scenarios=len(scenarios),
            adwords_runs_map={n: runs_map[n] for n in set(runs_map)},
            simplifications=REPORT_SIMPLIFICATIONS,
        )

        print(f"Fast benchmark: {len(scenarios)} scenario → {output_path}\n")

        for sc_idx, (n_companies, n_requests, traffic_type) in enumerate(scenarios, 1):
            n_runs = runs_map[n_requests]
            n_requests_actual = actual_request_count(n_requests, traffic_type)
            print(f"[{sc_idx}/{len(scenarios)}] "
                  f"{n_companies} campaigns / {fmt_n(n_requests)} (fact {n_requests_actual}) requests / {traffic_type} "
                  f"(adwords × {n_runs})")

            companies = build_company_set(n_companies)
            ad_data = build_scenario_ads(companies, n_requests)

            t0 = time.time()
            results = run_scenario(
                ad_data=ad_data,
                n_requests=n_requests_actual,
                classic_strategies=CLASSIC_STRATEGIES,
                adwords_algorithms=adwords_algos,
                adwords_runs=n_runs,
                request_seed=args.seed,
                classic_seed=args.seed,
                progress_cb=make_progress_bar_factory() if adwords_algos else None,
            )
            elapsed = time.time() - t0
            print(f"  Ready for it {elapsed:.1f}s")

            from auction_benchmark.reporter import _fmt_pct, _fmt_int
            bp = results["classic"].get("best_price")
            a2 = results["adwords"].get("a2_single_valued")
            a3 = results["adwords"].get("a3_small")

            total_volume = sum(d["volume"] for d in ad_data.values())
            if traffic_type == "balanced" and bp and total_volume > 0:
                sellout = _fmt_pct(bp.total_impressions / total_volume)
            else:
                sellout = "—"

            summary_rows.append(build_summary_row(
                scenario_index=sc_idx,
                n_companies=n_companies,
                n_requests_label=_fmt_int(n_requests_actual),
                traffic_type=traffic_type,
                total_volume=total_volume,
                bp_impressions=bp.total_impressions if bp else None,
                a2_impressions=a2.impressions_mean if a2 else None,
                a3_impressions=a3.impressions_mean if a3 else None,
                bp_revenue=bp.total_revenue if bp else None,
                a2_revenue=a2.revenue_mean if a2 else None,
                a3_revenue=a3.revenue_mean if a3 else None,
                sellout=sellout,
                hybrid_cells=hybrid_summary_cells(results["classic"])
                             + balancer_summary_cells(results["classic"]),
            ))
            toc_entries.append((sc_idx, n_companies, n_requests_actual, traffic_type))

            section = format_scenario_section(
                n_companies=n_companies,
                n_requests=n_requests_actual,
                traffic_type=traffic_type,
                ad_data=ad_data,
                classic_results=results["classic"],
                adwords_results=results["adwords"],
                scenario_index=sc_idx,
            )
            f.write(section)
            f.flush()

    # Insert the summary table after the header
    with open(output_path, "r", encoding="utf-8-sig") as f:
        content = f.read()
    marker = "---\n\n"
    pos = content.find(marker)
    if pos != -1:
        insert_at = pos + len(marker)
        toc_md = _build_io_md(write_toc, toc_entries)
        summary_md = _build_io_md(write_summary_table, summary_rows)
        content = content[:insert_at] + toc_md + summary_md + content[insert_at:]
        with open(output_path, "w", encoding="utf-8-sig") as f:
            f.write(content)

    print(f"\nReport saved: {output_path}")


if __name__ == "__main__":
    main()
