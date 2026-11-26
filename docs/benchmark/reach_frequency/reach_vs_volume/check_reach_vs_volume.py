"""
Checking the hypothesis from hypothesis.md: does the current hourly weight `w_h`
mix reach and frequency (freq) per user, and does the composition of
user segments ("user shares") change by hour.

Uses the same hour bucketing logic as the production code
(`rtb_sdk.balancer.seasonal.seasonality._get_h_type`, `normalize_counts`),
so that the result is directly comparable with the real `weights_dict`.

Run:

    python check_reach_vs_volume.py
    python check_reach_vs_volume.py --path ../../data/requests.json --mode hour_of_day

Input data format — a JSON list of records `{"user_id": ..., "date": ...}`
(like `data/requests.json`); only these two fields are minimally required.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np

from rtb_sdk.balancer.seasonal.seasonality import _get_h_type, normalize_counts

DEFAULT_PATH = Path(__file__).resolve().parents[3] / "data" / "requests.json"

# Quantile boundaries of the user activity segments over the whole period,
# analogous to the distribution from section 5 of the main doc
# (0-10 regular / 10-50 active / 50-200 super-active / 200+ bots) —
# here they are set as rank percentiles rather than absolute thresholds, so as to work
# on samples of any scale.
SEGMENT_BOUNDS = [
    ("casual", 0.0, 0.60),
    ("active", 0.60, 0.90),
    ("superactive", 0.90, 0.98),
    ("bot", 0.98, 1.00),
]


def load_records(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def bucket_by_hour(
    records: list[dict],
    mode: str,
    user_id_col: str = "user_id",
    timestamp_col: str = "date",
) -> tuple[dict[int, float], dict[int, set[str]], list[datetime]]:
    """Returns (counts[h], reach_users[h] -> set(uid), list of all timestamps)."""
    counts: dict[int, float] = defaultdict(float)
    reach_users: dict[int, set[str]] = defaultdict(set)
    timestamps: list[datetime] = []

    for row in records:
        uid = row.get(user_id_col)
        ts_str = row.get(timestamp_col)
        if uid is None or not ts_str:
            continue
        ts = datetime.fromisoformat(ts_str)
        timestamps.append(ts)
        h = _get_h_type(ts, mode)
        counts[h] += 1.0
        reach_users[h].add(uid)

    return dict(counts), dict(reach_users), timestamps


def check_coverage(timestamps: list[datetime], mode: str, n_hour_types: int) -> list[str]:
    """Returns a list of warnings about data incompleteness."""
    warnings: list[str] = []
    if not timestamps:
        warnings.append("Log is empty — check-out.")
        return warnings

    span = max(timestamps) - min(timestamps)
    required_days = 1 if mode == "hour_of_day" else 7
    if span.total_seconds() < required_days * 86400:
        warnings.append(
            f"The data only covers {span} — regimen '{mode}' needle "
            f"minimum {required_days} bottom. continuous-log, if reach[h]/freq[h] "
            f"No noise from a small sample. Conclusions below — indicative."
        )
    return warnings


def pearson(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 2 or np.std(a) == 0 or np.std(b) == 0:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def spearman(a: np.ndarray, b: np.ndarray) -> float:
    def rank(x: np.ndarray) -> np.ndarray:
        order = np.argsort(x)
        ranks = np.empty_like(order, dtype=float)
        ranks[order] = np.arange(len(x))
        return ranks

    return pearson(rank(a), rank(b))


def segment_users(reach_users: dict[int, set[str]]) -> dict[str, str]:
    """Assigns each uid an activity segment by its total number of
    appearances over the whole period (the sum over all hours in which it was seen)."""
    total_per_user: dict[str, int] = defaultdict(int)
    for uids in reach_users.values():
        for uid in uids:
            total_per_user[uid] += 1

    ranked = sorted(total_per_user.items(), key=lambda kv: kv[1])
    n = len(ranked)
    segment_of: dict[str, str] = {}
    for i, (uid, _count) in enumerate(ranked):
        pct = i / n if n else 0.0
        for name, lo, hi in SEGMENT_BOUNDS:
            if lo <= pct < hi or (hi == 1.0 and pct == 1.0):
                segment_of[uid] = name
                break
    return segment_of


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=DEFAULT_PATH)
    parser.add_argument("--mode", choices=["hour_of_day", "hour_of_week"], default="hour_of_day")
    parser.add_argument("--user-id-col", default="user_id")
    parser.add_argument("--timestamp-col", default="date")
    parser.add_argument("--cov-threshold", type=float, default=0.15)
    parser.add_argument("--diff-threshold", type=float, default=0.05)
    args = parser.parse_args()

    if not args.path.exists():
        print(f"File not found: {args.path}", file=sys.stderr)
        sys.exit(1)

    records = load_records(args.path)
    counts, reach_users, timestamps = bucket_by_hour(
        records, args.mode, args.user_id_col, args.timestamp_col
    )

    n_hour_types = 24 if args.mode == "hour_of_day" else 168
    for w in check_coverage(timestamps, args.mode, n_hour_types):
        print(f"[WARNING] {w}")

    hours = sorted(counts.keys())
    reach = {h: float(len(reach_users[h])) for h in hours}
    freq = {h: counts[h] / reach[h] for h in hours if reach[h] > 0}

    w_h = normalize_counts(counts)
    reach_share = normalize_counts(reach)

    total_counts = float(sum(counts.values()))

    print(
        f"\n{'h':>4} {'counts':>8} {'reach':>7} {'freq':>7} {'w_h':>8} {'reach_share':>12} "
        f"{'diff':>8} {'diff/100':>9} {'diff_abs':>9}"
    )
    for h in hours:
        diff = w_h[h] - reach_share.get(h, 0.0)
        diff_abs = diff * total_counts  # the same diff, but in impression counts at the log's actual volume
        print(
            f"{h:>4} {counts[h]:>8.0f} {reach[h]:>7.0f} {freq.get(h, 0.0):>7.2f} "
            f"{w_h[h]:>8.4f} {reach_share.get(h, 0.0):>12.4f} {diff:>8.4f} "
            f"{diff * 100:>9.2f} {diff_abs:>9.1f}"
        )

    freq_values = np.array(list(freq.values()))
    cov_freq = float(freq_values.std() / freq_values.mean()) if freq_values.mean() > 0 else float("nan")

    w_arr = np.array([w_h[h] for h in hours])
    reach_arr = np.array([reach_share.get(h, 0.0) for h in hours])
    max_diff = float(np.max(np.abs(w_arr - reach_arr)))
    max_diff_abs = max_diff * total_counts
    pearson_r = pearson(w_arr, reach_arr)
    spearman_r = spearman(w_arr, reach_arr)

    print("\n--- Summary ---")
    print(f"CoV(freq_h)                 = {cov_freq:.4f}  (threshold: {args.cov_threshold})")
    print(f"max|w_h - reach_share_h|    = {max_diff:.4f}  (threshold: {args.diff_threshold})")
    print(f"  ...show-off 100 = {max_diff * 100:.2f}")
    print(f"  ...factually. log-space ({total_counts:.0f} showdown) = {max_diff_abs:.1f}")
    print(f"Pearson(w_h, reach_share_h) = {pearson_r:.4f}")
    print(f"Spearman(w_h, reach_share_h)= {spearman_r:.4f}")

    h1_supported = cov_freq > args.cov_threshold or max_diff > args.diff_threshold
    print(f"\nVerdict: {'H1 (decomposition is needed)' if h1_supported else 'H0 (current w_h sufficient)'}")

    # Shares of user segments by hour
    segment_of = segment_users(reach_users)
    segment_names = [name for name, _lo, _hi in SEGMENT_BOUNDS]
    print(f"\n{'h':>4} " + " ".join(f"{name:>12}" for name in segment_names))
    segment_share_series: dict[str, list[float]] = {name: [] for name in segment_names}
    for h in hours:
        uids = reach_users[h]
        seg_counts = defaultdict(int)
        for uid in uids:
            seg_counts[segment_of.get(uid, "casual")] += 1
        total = len(uids) or 1
        shares = {name: seg_counts[name] / total for name in segment_names}
        for name in segment_names:
            segment_share_series[name].append(shares[name])
        print(f"{h:>4} " + " ".join(f"{shares[name]:>12.4f}" for name in segment_names))

    print("\n--- CoV segments by hour (high-end CoV => hourly coverage-dependency) ---")
    for name in segment_names:
        series = np.array(segment_share_series[name])
        cov = float(series.std() / series.mean()) if series.mean() > 0 else float("nan")
        print(f"{name:>12}: CoV = {cov:.4f}")


if __name__ == "__main__":
    main()
