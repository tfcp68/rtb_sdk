#!/usr/bin/env python3
"""
Auction benchmark.

Modes:
  auction   — runs the auction functions N times
  validate  — compares three validation approaches: none / native / pydantic

Usage:
  python -m tools.benchmark                              # auction, all functions, 1000 iterations
  python -m tools.benchmark --func best_heuristics       # a single function
  python -m tools.benchmark -n 5000                      # custom number of iterations
  python -m tools.benchmark --save                       # save the report to auction/reports/
  python -m tools.benchmark --mode validate              # compare none / native / pydantic
  python -m tools.benchmark --mode validate -n 5000 --save
"""

import argparse
import statistics
import io
import sys
import time
from typing import cast
from datetime import datetime
from pathlib import Path

cast(io.TextIOWrapper, sys.stdout).reconfigure(encoding='utf-8')

from rtb_sdk.constants import SelectionFunc
from rtb_sdk.helpers import (
    create_parameters_ads_stats,
    is_valid_auction_ads_dict,
    is_valid_auction_params,
)
from rtb_sdk.auction.auction import auction
from examples.auction.fixtures import test_ads1, test_stats1
from rtb_sdk.schemas import AuctionSelectionFunc

FUNCS: dict[str, AuctionSelectionFunc] = {
    'best_one':          SelectionFunc.BEST_ONE,
    'random_one':        SelectionFunc.RANDOM_ONE,
    'best_price':        SelectionFunc.BEST_PRICE,
    'random_price':      SelectionFunc.RANDOM_PRICE,
    'best_velocity':     SelectionFunc.BEST_VELOCITY,
    'random_velocity':   SelectionFunc.RANDOM_VELOCITY,
    'best_heuristics':   SelectionFunc.BEST_HEURISTICS,
    'random_heuristics': SelectionFunc.RANDOM_HEURISTICS,
}

SEP  = '─' * 56
SEP2 = '  ' + '·' * 52


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _timings(fn, n: int) -> dict:
    times: list[float] = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn()
        times.append((time.perf_counter() - t0) * 1_000_000)  # µs
    s = sorted(times)
    return {
        'n':         n,
        'total_ms':  sum(times) / 1000,
        'mean_us':   statistics.mean(times),
        'median_us': statistics.median(times),
        'stdev_us':  statistics.stdev(times) if n > 1 else 0.0,
        'min_us':    s[0],
        'p95_us':    s[int(0.95 * n)],
        'p99_us':    s[int(0.99 * n)],
        'max_us':    s[-1],
    }


def _fmt_block(label: str, r: dict) -> str:
    w = 12
    return (
        f"  {'label':<{w}}: {label}\n"
        f"  {'runs':<{w}}: {r['n']}\n"
        f"  {'total':<{w}}: {r['total_ms']:.2f} ms\n"
        f"  {'mean':<{w}}: {r['mean_us']:.2f} µs\n"
        f"  {'median':<{w}}: {r['median_us']:.2f} µs\n"
        f"  {'stdev':<{w}}: {r['stdev_us']:.2f} µs\n"
        f"  {'min':<{w}}: {r['min_us']:.2f} µs\n"
        f"  {'p95':<{w}}: {r['p95_us']:.2f} µs\n"
        f"  {'p99':<{w}}: {r['p99_us']:.2f} µs\n"
        f"  {'max':<{w}}: {r['max_us']:.2f} µs"
    )


# ---------------------------------------------------------------------------
# Mode: auction
# ---------------------------------------------------------------------------

def _run_auction(func_name: str, n: int) -> dict:
    params = create_parameters_ads_stats(
        auction_type=FUNCS[func_name],
        ads_stats=test_stats1,
    )
    r = _timings(lambda: auction(ads=test_ads1, parameters=params), n)
    return {'func': func_name, **r}


def bench_auction(args: argparse.Namespace) -> tuple[str, list[dict]]:
    funcs = list(FUNCS) if args.func == 'all' else [args.func]
    results: list[dict] = []
    for func_name in funcs:
        print(f"\n  running {func_name} × {args.iterations} ...", end=' ', flush=True)
        r = _run_auction(func_name, args.iterations)
        results.append(r)
        print('done')
        print(_fmt_block(r['func'], r))
    return 'auction', results


# ---------------------------------------------------------------------------
# Mode: validate  (none / native / pydantic)
# ---------------------------------------------------------------------------

# Three variants for each subject
_VARIANTS = ('none', 'native', 'pydantic')


def _ratio_str(val: float, base: float) -> str:
    """Returns '×N.NN slower' (slower) / '×N.NN faster' (faster) / 'baseline'."""
    if base == 0:
        return '—'
    r = val / base
    if abs(r - 1.0) < 0.005:
        return '≈ baseline'
    if r > 1:
        return f'×{r:.2f} slower'
    return f'×{1/r:.2f} faster'


def _fmt_summary(subjects: list[dict]) -> list[str]:
    """
    subjects — list of {'name': str, 'results': {'none': dict, 'native': dict, 'pydantic': dict}}
    """
    col_v  = 10   # variant column width
    col_m  = 12   # mean column width
    col_r  = 22   # ratio column width

    header = (
        f"  {'':>{col_v}}  {'mean':>{col_m}}  "
        f"{'vs none':>{col_r}}  {'vs native':>{col_r}}"
    )

    lines: list[str] = [SEP2, '  Final comparison', SEP2]
    for subj in subjects:
        lines.append(f"\n  {subj['name']}")
        lines.append(header)
        r = subj['results']
        base_none   = r['none']['mean_us']
        base_native = r['native']['mean_us']
        for i, variant in enumerate(_VARIANTS):
            mean = r[variant]['mean_us']
            prefix = '└─' if i == len(_VARIANTS) - 1 else '├─'
            vs_none   = 'baseline' if variant == 'none'   else _ratio_str(mean, base_none)
            vs_native = 'baseline' if variant == 'native' else _ratio_str(mean, base_native)
            vs_none_col   = f'{vs_none:>{col_r}}'
            vs_native_col = f'{vs_native:>{col_r}}' if variant != 'none' else f"{'—':>{col_r}}"
            lines.append(
                f"  {prefix} {variant:<{col_v - 3}}  {mean:>{col_m}.2f} µs  "
                f"{vs_none_col}  {vs_native_col}"
            )
    lines.append('')
    return lines


def bench_validate(args: argparse.Namespace) -> tuple[str, list[str]]:
    from rtb_sdk.auction.reports.pydantic_models import AdsDictModel, ParametersAdsStatsModel  # type: ignore[import]

    params = create_parameters_ads_stats(
        auction_type=SelectionFunc.BEST_HEURISTICS,
        ads_stats=test_stats1,
    )

    subjects_spec: list[tuple[str, list[tuple[str, object]]]] = [
        ('AdsDict', [
            ('none',     lambda: None),
            ('native',   lambda: is_valid_auction_ads_dict(test_ads1)),
            ('pydantic', lambda: AdsDictModel.model_validate(test_ads1)),
        ]),
        ('Params', [
            ('none',     lambda: None),
            ('native',   lambda: is_valid_auction_params(params)),
            ('pydantic', lambda: ParametersAdsStatsModel.model_validate(params)),
        ]),
    ]

    all_blocks: list[str] = []   # for --save
    subjects_summary: list[dict] = []

    for subj_name, cases in subjects_spec:
        print(f"\n{SEP2}")
        print(f"  {subj_name}")
        print(SEP2)

        subj_results: dict[str, dict] = {}
        for variant, fn in cases:
            label = f'{subj_name} / {variant}'
            print(f"\n  running [{label}] × {args.iterations} ...", end=' ', flush=True)
            r = _timings(fn, args.iterations)  # type: ignore[arg-type]
            subj_results[variant] = r
            print('done')
            block = _fmt_block(label, r)
            print(block)
            all_blocks.append(block)

        subjects_summary.append({'name': subj_name, 'results': subj_results})

    summary_lines = _fmt_summary(subjects_summary)
    summary_text = '\n'.join(summary_lines)
    print(summary_text)

    return 'validate', all_blocks + [summary_text]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description='Auction benchmark')
    parser.add_argument(
        '--mode',
        choices=['auction', 'validate'],
        default='auction',
        help='Benchmark regime (default: auction)',
    )
    parser.add_argument(
        '--func',
        choices=[*FUNCS, 'all'],
        default='all',
        help='[auction] Benchmark function (default: all)',
    )
    parser.add_argument(
        '-n', '--iterations',
        type=int,
        default=1000,
        help='Number of iterations (default: 1000)',
    )
    parser.add_argument(
        '--save',
        action='store_true',
        help='Save the report in auction/reports/',
    )
    args = parser.parse_args()

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    header = f"{SEP}\n  Auction Benchmark [{args.mode}]  {timestamp}  n={args.iterations}\n{SEP}"
    print(header)

    if args.mode == 'auction':
        mode_label, results = bench_auction(args)
        report_blocks = [_fmt_block(r['func'], r) for r in results]
    else:
        mode_label, report_blocks = bench_validate(args)

    print(f"\n{SEP}")

    if args.save:
        reports_dir = Path(__file__).parent.parent / 'auction' / 'reports'
        reports_dir.mkdir(exist_ok=True)
        file_ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        out = reports_dir / f'benchmark_{mode_label}_{file_ts}.txt'
        lines = [header, '']
        lines.extend(report_blocks)
        lines.append(f'\n{SEP}')
        out.write_text('\n'.join(lines), encoding='utf-8')
        print(f'\n  saved → {out}')


if __name__ == '__main__':
    main()
