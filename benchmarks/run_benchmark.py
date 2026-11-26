#!/usr/bin/env python3
"""
Running the comparative benchmark of auction algorithms.

Examples:
    # Run all scenarios (warning: slow for 1M/10M)
    python benchmarks/run_benchmark.py

    # Only scenarios with 3 and 10 companies, requests ≤ 100k
    python benchmarks/run_benchmark.py --companies 3 10 --requests 10000 100000

    # A specific traffic type
    python benchmarks/run_benchmark.py --traffic balanced

    # Reduce the number of A2/A3 runs
    python benchmarks/run_benchmark.py --runs 100

    # Specify the output file
    python benchmarks/run_benchmark.py --output docs/benchmark/auction/synthetic/my_run.md
"""
import argparse
import sys
import os
import time
from datetime import datetime

# Add src/ to PYTHONPATH
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


def parse_args():
    p = argparse.ArgumentParser(
        description="Comparative benchmark of auctions (A2/A3 vs classic)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--companies", nargs="+", type=int,
        default=None,
        help="Filter by number of companies (needlessly. 3 10 20 100). By default — everything.",
    )
    p.add_argument(
        "--requests", nargs="+", type=int,
        default=None,
        help="Filter by number of requests (needlessly. 10000 100000). By default — everything.",
    )
    p.add_argument(
        "--traffic", nargs="+",
        choices=["balanced", "shortage", "excess"],
        default=None,
        help="Filter by type of traffic. By default — three-type.",
    )
    p.add_argument(
        "--runs", type=int, default=None,
        help="Fixed number of runs A2/A3 for all scenarios. "
             "Default depends on the number of requests (1000/300/50/10).",
    )
    p.add_argument(
        "--output", default=None,
        help="The Way to the Weekend MD-file. By default docs/benchmark/auction/synthetic/benchmark_<ts>.md",
    )
    p.add_argument(
        "--seed", type=int, default=42,
        help="Basic seed request-generation (default: 42).",
    )
    p.add_argument(
        "--no-adwords", action="store_true",
        help="Use only classical strategies (without A2/A3).",
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="Show a list of scripts and exit without running.",
    )
    return p.parse_args()


def build_scenario_list(args):
    matrix = SCENARIO_MATRIX
    if args.companies:
        matrix = [(c, n, t) for c, n, t in matrix if c in args.companies]
    if args.requests:
        matrix = [(c, n, t) for c, n, t in matrix if n in args.requests]
    if args.traffic:
        matrix = [(c, n, t) for c, n, t in matrix if t in args.traffic]
    return matrix


def fmt_n(n):
    return {10_000:"10k", 100_000:"100k", 1_000_000:"1M", 10_000_000:"10M"}.get(n, str(n))


def make_progress_bar_factory(total: int):
    """Returns a factory of callbacks — one for each algorithm."""
    algo_labels = {
        "a2_single_valued": "A2",
        "a3_small":         "A3",
    }
    def factory(algo: str):
        prefix = algo_labels.get(algo, algo)
        start = [time.time()]
        def cb(done, _total):
            pct = done / _total * 100
            elapsed = time.time() - start[0]
            eta = (elapsed / done * (_total - done)) if done else 0
            bar_len = 28
            filled = int(bar_len * done / _total)
            bar = "█" * filled + "░" * (bar_len - filled)
            print(f"\r  {prefix} [{bar}] {pct:5.1f}%  ETA {eta:4.0f}s", end="", flush=True)
            if done == _total:
                print(f"\r  {prefix} [{bar}] 100%  {elapsed:.1f}s               ")
        return cb
    return factory


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
            print(f"  {i:3d}. {nc:3d} campaigns  {fmt_n(nr):>4s} requests  {tt:<10s}  "
                  f"adwords runs={runs}")
        return

    # Determine the output file
    if args.output:
        output_path = args.output
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        output_path = os.path.join(
            os.path.dirname(__file__), "..", "docs", "benchmark", "auction", "synthetic", f"benchmark_{ts}.md"
        )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    adwords_algos = [] if args.no_adwords else ADWORDS_ALGORITHMS
    runs_map = {
        n: (args.runs if args.runs else DEFAULT_ADWORDS_RUNS.get(n, 10))
        for _, n, _ in scenarios
    }

    summary_rows = []
    toc_entries = []

    with open(output_path, "w", encoding="utf-8-sig") as f:
        write_report_header(
            f,
            total_scenarios=len(scenarios),
            adwords_runs_map={n: runs_map[n] for n in set(runs_map)},
            simplifications=REPORT_SIMPLIFICATIONS,
        )

        print(f"benchmark: {len(scenarios)} scenario → {output_path}\n")

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
                progress_cb=make_progress_bar_factory(n_runs) if adwords_algos else None,
            )
            elapsed = time.time() - t0
            print(f"  Ready for it {elapsed:.1f}s")

            # Summary row
            bp = results["classic"].get("best_price")
            a2 = results["adwords"].get("a2_single_valued")
            a3 = results["adwords"].get("a3_small")

            from auction_benchmark.reporter import _fmt_pct, _fmt_int

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

            # Full scenario section
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

        # Insert the summary table at the beginning (overwrite)
    # Append summary: read, insert after the header
    with open(output_path, "r", encoding="utf-8-sig") as f:
        content = f.read()

    # Find the position after the header (after the first "---\n\n")
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


def _build_io_md(writer, *args) -> str:
    import io
    buf = io.StringIO()
    writer(buf, *args)
    return buf.getvalue()


if __name__ == "__main__":
    main()
