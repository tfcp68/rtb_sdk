"""A/B of hypothesis 1 (aggregated user headroom) on the REAL balancer.

Runs the real `build_seasonal_context` + the slot loop of `seasonal_balance_traffic` on
a real downsampled log (make_ab_log.py), flag off vs on, and compares with an independent
simulation.

What we check (spec §6, docs/superpowers/specs/2026-07-17-...-design.md):

  Layer 2 — balancer == sim:
      OFF  must reproduce `prop[h]` (shape ∝ w_h)
      ON   must reproduce `fixed[h]` (headroom sweep), up to
           a renormalization scale — we compare the SHAPES via TV.
  Layer 3 — guardrails: no-op at a free limit, conservation of Σ, the shape is front-loaded.

Two modes (spec §6.2):

  PERIOD_DAYS=1 (ab_log_1day.csv) — a single-day log. user-day == user, the resolution
      matches the sim -> the balancer MUST reproduce the gain. Validation of the integration.

  PERIOD_DAYS=6 (ab_log_6day.csv) — multi-day. build_seasonal_context aggregates
      hours ACROSS ALL DAYS (seasonality.py:86 discards the date), so "7 requests in
      one day" and "1 request seven days in a row" are indistinguishable to it. The `true` reference
      honestly resets the budget every day. The delta to the single-day run is
      the price of day-blending, i.e. a realistic production figure (spec §7).

Run:
    PYTHONUTF8=1 python .../hyp1_ab_balancer.py
    AB_LOG=.../ab_log_6day.csv PERIOD_DAYS=6 PYTHONUTF8=1 python .../hyp1_ab_balancer.py
"""

from __future__ import annotations

import csv
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone as _tz
from zoneinfo import ZoneInfo

import numpy as np

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src"))

from rtb_sdk.balancer.seasonal.balance import (  # noqa: E402
    _hour_balance_traffic,
    _iter_slots,
    build_seasonal_context,
)

LOG = os.environ.get(
    "AB_LOG", "docs/benchmark/reach_frequency/cumulative_freq/ab_log_1day.csv"
)
PERIOD_DAYS = int(os.environ.get("PERIOD_DAYS", "1"))
CAPS = [1, 2, 3, 5, 10]
CAP_MAIN = 5
BETAS = [0.5, 0.8, 1.0, 1.5]      # sweep of the elastic buffer steepness (fix A)
TIMEZONE = "Europe/Moscow"

# The log starts from the first WHOLE local day of the janus-20260615 file (see make_ab_log.py).
_START = datetime(2026, 6, 16, 0, 0)
PERIOD = {"period_start": _START, "period_end": _START + timedelta(days=PERIOD_DAYS)}


# --------------------------------------------------------------------------- #
# Loading the log
# --------------------------------------------------------------------------- #
def load_log():
    """CSV -> (hist, totals, counts, per_ud).

    hist[h][uid], totals[uid] — exactly what build_seasonal_context will build:
        hours aggregated ACROSS ALL DAYS (the date discarded).
    per_ud[(uid, date)][h] — with per-day resolution; needed by the `true` reference, which
        resets the daily budget every day. Precisely the discrepancy between these two
        representations is the day-blending.
    """
    tz = ZoneInfo(TIMEZONE)
    hist: dict[int, dict[str, int]] = {h: {} for h in range(24)}
    totals: dict[str, int] = {}
    counts = np.zeros(24)
    per_ud: dict[tuple[str, object], dict[int, int]] = defaultdict(lambda: defaultdict(int))

    with open(LOG, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            ts = datetime.fromisoformat(row["datetime"])
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=_tz.utc)
            lt = ts.astimezone(tz)
            h, uid = lt.hour, row["client_id"]
            hist[h][uid] = hist[h].get(uid, 0) + 1
            totals[uid] = totals.get(uid, 0) + 1
            counts[h] += 1
            per_ud[(uid, lt.date())][h] += 1
    return hist, totals, counts, per_ud


# --------------------------------------------------------------------------- #
# Simulation (independent of the balancer)
# --------------------------------------------------------------------------- #
def sim_true(per_ud, cap: float) -> np.ndarray:
    """Cumulative reality: each user has their own budget, RESET every day."""
    true = np.zeros(24)
    for hours in per_ud.values():
        b = float(cap)
        for h in sorted(hours):
            d = min(hours[h], b)
            true[h] += d
            b -= d
    return true


def sim_fixed(hist, n_users: int, cap: float) -> np.ndarray:
    """Sweep of the aggregated headroom — the same formula as in _headroom_sweep.

    cap here is user_period_limit (for the whole period), as the balancer computes it.
    """
    b = float(cap)
    out = np.zeros(24)
    for h in range(24):
        if not hist[h]:
            continue
        delivered = sum(min(c, b) for c in hist[h].values())
        out[h] = delivered
        b = max(0.0, b - delivered / n_users)
    return out


def tv(a: np.ndarray, b: np.ndarray) -> float:
    sa, sb = a.sum(), b.sum()
    if sa == 0 or sb == 0:
        return float("nan")
    return 0.5 * float(np.sum(np.abs(a / sa - b / sb)))


# --------------------------------------------------------------------------- #
# The real balancer with an hourly breakdown
# --------------------------------------------------------------------------- #
def run_balancer(ads: dict, total: int, ctx) -> np.ndarray:
    """Repeats the seasonal_balance_traffic loop, but records the volume by hour.

    We recover the hour by object identity: _iter_slots puts into
    slot_params['seasonal_context'] THE SAME AdditionalContext object that lies in
    ctx['context'][h] -> a reverse map by id() gives the hour without touching the balancer code
    (enumerate does not work: _iter_slots skips empty slots).
    """
    id2h = {id(c): h for h, c in ctx["context"].items()}
    params = {
        "total_traffic_volume": int(total),
        "tag_probabilities": {"geo:t": 1.0},
        "vocabs": {"geo": ["geo:t"]},
        "objective": "maximize_money",
        "max_n_categories": 100,
        "min_category_probability": 1e-9,
        "n_threads": 1,
        "seasonal_context": ctx,
        "period": PERIOD,
    }
    by_hour = np.zeros(24)
    for slot_ads, slot_params, _, remaining in _iter_slots(dict(ads), params):
        h = id2h[id(slot_params["seasonal_context"])]
        for ad_id, vol in _hour_balance_traffic(slot_ads, slot_params).items():
            by_hour[h] += vol
            remaining[ad_id] = max(0, remaining.get(ad_id, 0) - vol)
    return by_hour


def make_ad(cap: int, volume: int) -> dict:
    """An ad throttled ONLY by user_frequency_limit (P=1).

    IMPORTANT about volume. user_activity_ratio is applied in prepare_hour_ads as
    ``vol = ad_max · ratio`` (there is no ad_frequency_limit -> hour_limit = inf). With
    volume=10**9 the product is still orders of magnitude larger than the slot's traffic, binds the
    traffic pool, and ratio does NOT reach the result — the fix looks like a no-op.
    Therefore volume = the full volume of the log: then slot_max_vol ≈ counts_h and
    vol = counts_h · coef[h] really binds.
    """
    return {
        "a": {
            "id": "a",
            "targets": {"value": {"geo": ["t"]}},
            "volume": int(volume),
            "cpm": 10.0,
            "user_frequency_limit": {"value": {"d": cap}},
        }
    }


def main() -> None:
    print(f"Log: {LOG}   period: {PERIOD_DAYS} days", flush=True)
    hist, totals, counts, per_ud = load_log()
    total_events = int(counts.sum())
    w = counts / counts.sum()
    n_users = len(totals)
    print(f"Yuserov: {n_users:,}  user-days: {len(per_ud):,}  events: {total_events:,}  "
          f"requests/user/days: {total_events / len(per_ud):.2f}\n", flush=True)

    cfg = {
        "path": LOG,
        "timestamp_col": "datetime",
        "user_id_col": "client_id",
        "timezone": TIMEZONE,
        "aggregation_mode": "hour_of_day",
    }

    print("=" * 94)
    print(f"A/B: balancer OFF vs ON (period {PERIOD_DAYS} days). TV — standard true")
    print("=" * 94)
    print(f"{'C':>3} | {'TV(bal_off)':>11} {'TV(bal_on)':>10} {'closed':>8} | "
          f"{'TV(off,prop)':>12} {'TV(on,fixed)':>12} | {'Σon/Σoff':>8}")
    print("-" * 94)

    rows = []
    for cap in CAPS:
        ads = make_ad(cap, total_events)
        true = sim_true(per_ud, cap)
        # The balancer measures the budget over the WHOLE period: user_period_limit = (d/24)·n_hours.
        cap_period = cap * PERIOD_DAYS
        fixed = sim_fixed(hist, n_users, cap_period)
        prop = true.sum() * w

        ctx_off = build_seasonal_context(cfg, ads, PERIOD, use_cumulative_user_headroom=False)
        ctx_on = build_seasonal_context(cfg, ads, PERIOD, use_cumulative_user_headroom=True)
        off = run_balancer(ads, total_events, ctx_off)
        on = run_balancer(ads, total_events, ctx_on)

        tv_off, tv_on = tv(off, true), tv(on, true)
        closed = (tv_off - tv_on) / tv_off if tv_off > 0 else float("nan")
        v_off, v_on = tv(off, prop), tv(on, fixed)
        ratio = on.sum() / off.sum() if off.sum() else float("nan")

        print(f"{cap:>3} | {tv_off:>11.4f} {tv_on:>10.4f} {closed:>7.0%} | "
              f"{v_off:>12.4f} {v_on:>12.4f} | {ratio:>7.3f}x")
        rows.append((cap, off, on, true, fixed))

    # ---- Fix A (elastic buffer), sweep over beta ---------------------------
    # Hypothesis: A is a pure function of the hour, it does not touch the per-user structure, so
    # day-blending (which killed B on long profiles) should NOT affect it.
    print("\n" + "=" * 94)
    print(f"FIX A (slippery buffer), swipe β — close-up, period {PERIOD_DAYS} days")
    print("=" * 94)
    hdr = "  ".join(f"β={b:<4}" for b in BETAS)
    print(f"{'C':>3} | {'TV(off)':>8} | {hdr} | {'ΣA/Σoff best β':>20}")
    print("-" * 94)
    for cap in CAPS:
        ads = make_ad(cap, total_events)
        true = sim_true(per_ud, cap)
        off = next(r[1] for r in rows if r[0] == cap)
        tv_off = tv(off, true)
        cells, best = [], (None, float("inf"), None)
        for b in BETAS:
            ctx_a = build_seasonal_context(
                cfg, ads, PERIOD, use_elastic_user_limit=True, elastic_beta=b)
            a = run_balancer(ads, total_events, ctx_a)
            tv_a = tv(a, true)
            cells.append(f"{(tv_off - tv_a) / tv_off:>+6.0%}")
            if tv_a < best[1]:
                best = (b, tv_a, a)
        vol = best[2].sum() / off.sum() if off.sum() else float("nan")
        print(f"{cap:>3} | {tv_off:>8.4f} | {'  '.join(cells)} | "
              f"β={best[0]}: {vol:>6.3f}x")

    cap, off, on, true, fixed = next(r for r in rows if r[0] == CAP_MAIN)
    print("\n" + "=" * 94)
    print(f"Hourly curves, C={CAP_MAIN}")
    print("=" * 94)
    print(f"{'h':>3} {'true':>10} {'bal_off':>10} {'bal_on':>10} {'sim_fixed':>10}")
    for h in range(24):
        print(f"{h:>3} {true[h]:>10.0f} {off[h]:>10.0f} {on[h]:>10.0f} {fixed[h]:>10.0f}")
    print(f"{'Σ':>3} {true.sum():>10.0f} {off.sum():>10.0f} {on.sum():>10.0f} {fixed.sum():>10.0f}")

    print("\n" + "=" * 94)
    print("GUARDRAIL: limit -> fixation must no-op")
    print("=" * 94)
    ads = make_ad(10_000, total_events)
    c_off = build_seasonal_context(cfg, ads, PERIOD, use_cumulative_user_headroom=False)
    c_on = build_seasonal_context(cfg, ads, PERIOD, use_cumulative_user_headroom=True)
    o = run_balancer(ads, total_events, c_off)
    n_ = run_balancer(ads, total_events, c_on)
    print(f"Σoff={o.sum():.0f}  Σon={n_.sum():.0f}  coincidentally={np.allclose(o, n_)}")


if __name__ == "__main__":
    main()
