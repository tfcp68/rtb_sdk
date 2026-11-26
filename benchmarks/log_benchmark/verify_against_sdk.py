#!/usr/bin/env python3
"""
Verification of the fast engine (engine_full) against the SDK `auction/simulation` chain.

Takes a short piece of the log stream, runs it in two ways —
through MockDriver + filters + `auction()` from the SDK and through engine_full — and
compares the sequences of winners. Deterministic strategies
(best_one, best_price, best_velocity, best_heuristics, best_hybrid_*) must
match 100%.

A hard volume cap was added to the SDK chain (as in the benchmark): an ad that
has exhausted volume leaves the pool.

    python benchmarks/log_benchmark/verify_against_sdk.py --requests 30000 --n-ads 12
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "..", "src"))

from stream import load_prepared, iter_days  # noqa: E402
from ads import load_ads_file, build_pack  # noqa: E402
from engine_full import run_algorithm, build_match_lists  # noqa: E402

T0 = datetime(2026, 9, 30, 21, 0)


def sdk_run(strategy, pack, prep, ts, user, combo, price_probability=None, velocity_threshold=None):
    from rtb_sdk.auction.simulation.driver.builder import create_mock_driver
    from rtb_sdk.auction.simulation.driver.driver import (
        get_ad_timestamps, get_user_ad_timestamps, get_user_ad_show_times,
        get_ad_stats, reset_statistics_if_needed, update_statistics, get_ads)
    from rtb_sdk.auction.simulation.filters.frequency_filter import filter_by_ad_frequency
    from rtb_sdk.auction.simulation.filters.user_frequency_filter import filter_by_user_frequency
    from rtb_sdk.auction.simulation.filters.min_interval_filter import filter_by_min_interval
    from rtb_sdk.auction.simulation.filters.match_filter import filter_by_precise_match
    from rtb_sdk.auction.auction import auction
    from rtb_sdk.constants import AuctionType, DATE_ZERO, DATE_INFINITY
    from rtb_sdk.helpers import get_ads_dict, create_parameters_ads_stats, get_ad_id
    from rtb_sdk.helpers.auction import (
        create_ad, create_ads_dict, create_target_vector, create_frequency_limits,
        create_request, create_request_tags)

    gran_key = {"t": "ten_minutes", "h": "hour", "d": "day", "w": "week", "m": "month"}
    inv = {600: "t", 3600: "h", 86400: "d", 604800: "w", 2592000: "m"}
    period_s = None
    ads = {}
    for a in range(pack.n):
        al = {gran_key[inv[w]]: l for l, w in pack.ad_lims[a]}
        ul = {gran_key[inv[w]]: l for l, w in pack.user_lims[a]}
        ads[pack.ids[a]] = create_ad(
            id=pack.ids[a], targets=create_target_vector(pack.targets[a]),
            cpm=pack.cpm[a], priority=pack.priority[a], volume=pack.volume[a], budget=pack.budget[a],
            start_date=DATE_ZERO,
            end_date=DATE_INFINITY,
            ad_frequency_limit=create_frequency_limits(**al, min_interval=pack.min_interval[a]),
            user_frequency_limit=create_frequency_limits(**ul),
        )
    driver = create_mock_driver(ads=create_ads_dict(ads), vocabs=create_target_vector({}))
    cnt = {i: 0 for i in pack.ids}
    order = prep.vocab_order
    out = []
    for i in range(len(ts)):
        row = prep.combos[combo[i]]
        tags = {v: f"{v}:{prep.vocabs[v][row[k]]}" for k, v in enumerate(order) if row[k] != 0}
        req = create_request(id=str(i), user_id=str(int(user[i])),
                             date=T0 + timedelta(seconds=int(ts[i])),
                             tags=create_request_tags(tags))
        now = req["date"]
        reset_statistics_if_needed(driver, req)
        # we do not use filter_by_active from the SDK: DATE_ZERO is naive, while DATE_INFINITY is tz-aware
        # (comparison with any request.date fails). The semantics are the same: start <= now < end.
        sec = int(ts[i])
        f = create_ads_dict({k: v for k, v in get_ads_dict(get_ads(driver)).items()
                             if pack.start_s[pack.ids.index(k)] <= sec < pack.end_s[pack.ids.index(k)]})
        f = filter_by_ad_frequency(f, get_ad_timestamps(driver), now)
        f = filter_by_user_frequency(f, get_user_ad_timestamps(driver, req["user_id"]), now)
        f = filter_by_min_interval(f, get_user_ad_show_times(driver, req["user_id"]), now)
        f = filter_by_precise_match(req, f)
        pool = {k: v for k, v in get_ads_dict(f).items() if cnt[k] < v["volume"]}
        if not pool:
            continue
        ids = list(pool)
        params = create_parameters_ads_stats(
            auction_type=strategy, ads_stats=get_ad_stats(driver, ids, now),
            price_probability=price_probability, velocity_threshold=velocity_threshold)
        w = auction(create_ads_dict(pool), params)
        if w is None:
            continue
        wid = get_ad_id(w)
        cnt[wid] += 1
        update_statistics(driver, req, AuctionType.PRECISE, wid)
        out.append((int(ts[i]), int(user[i]), pack.ids.index(wid)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ads", default=os.path.join(HERE, "ads_manual.json"))
    ap.add_argument("--prepared", default=os.path.join(HERE, "..", "logs", "prepared_20261012"))
    ap.add_argument("--n-ads", type=int, default=12)
    ap.add_argument("--requests", type=int, default=30000)
    ap.add_argument("--volume-factor", type=float, default=0.5)
    ap.add_argument("--span-hours", type=float, default=1.0, help="Length of lair window, hours (sample pick up)")
    a = ap.parse_args()

    prep = load_prepared(a.prepared)
    ts, user, combo = prep.day_arrays(0)
    ts, user, combo = np.asarray(ts), np.asarray(user), np.asarray(combo)
    lo = 12 * 3600  # middle of the day
    m = (ts >= lo) & (ts < lo + int(a.span_hours * 3600))
    ts, user, combo = ts[m], user[m], combo[m]
    # sampling by users to get the given number of requests and preserve repeats
    frac = min(1.0, a.requests / len(ts))
    keep = user < np.uint32(int(frac * 2**32 - 1))
    ts, user, combo = ts[keep], user[keep], combo[keep]
    ts = ts - lo
    print(f"Requests: {len(ts):,}; user: {len(np.unique(user)):,}")

    ads = load_ads_file(a.ads)[: a.n_ads]
    # volume is chosen so that some ads hit the volume cap while the limits work
    # ad limits are computed from the uniform rate over the period → period = window length
    pack = build_pack(prep, ads, len(ts), a.span_hours / 24, a.volume_factor, True)
    match = build_match_lists(prep, pack.targets)

    strategies = [("best_one", "best_one", {}), ("best_price", "best_price", {}),
                  ("best_velocity", "best_velocity", {}), ("best_heuristics", "best_heuristics", {}),
                  ("best_hybrid_0.2", "best_hybrid", {"velocity_threshold": 0.2})]
    ok_all = True
    for name, sdk_name, kw in strategies:
        tr = []
        stream = iter([(0, ts.astype(np.int32), user, combo)])
        run_algorithm(name, pack, match, stream, prep, seed=1, trace=tr)
        ref = sdk_run(sdk_name, pack, prep, ts, user, combo, **kw)
        same = tr == ref
        ok_all &= same
        print(f"{name:18s} SDK impressions={len(ref):6d}  engine={len(tr):6d}  "
              f"{'SOVPALO' if same else 'Differences'}")
        if not same:
            for i, (x, y) in enumerate(zip(tr, ref)):
                if x != y:
                    print(f"   first divergence #{i}: engine={x} sdk={y}")
                    break
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
