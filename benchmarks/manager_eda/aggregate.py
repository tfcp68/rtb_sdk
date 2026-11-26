#!/usr/bin/env python3
"""
Step 1: per-day aggregates (cached in benchmarks/manager_eda/cache/). These are what the EDA needs;
raw rows are no longer read. All aggregates are computed over all valid requests
(device_type is known, ep ∈ {avod, alive}); segments (markups) are applied at the analysis step.

Cache:
    cube_dXX.parquet     hour × device × ep × place × position × is_child × age × broadcast × has_cid → n
    hc_<tag>_dXX.parquet tag × device × ep × place → n          (tag ∈ HIGH_CARD)
    combo_dXX.parquet    device × ep × place × location × category × channel → n
    users_dXX.parquet    per user with client_id: n, n_dev, dev, ep_mask, n_sess, first_ts, last_ts
    gaps_dXX.npz         histograms of intervals/ranks/sessions by dev × ep

Run:  python benchmarks/manager_eda/aggregate.py [--force]
"""
from __future__ import annotations

import argparse
import glob
import os
import sys
import time

import numpy as np
import polars as pl

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import ALL_DEVICES, CACHE, DEV_IDX, EP_IDX, HIGH_CARD, PREPARED, SESSION_GAP  # noqa: E402

LOG2_BINS = 22        # gap: floor(log2(gap+1)) ∈ [0, 21]
LIN_BINS = 360        # gap < 3600 s, step 10 s
RANK_CAP = 60
SESS_CAP = 60


def _valid(lf: pl.LazyFrame) -> pl.LazyFrame:
    return lf.filter(pl.col("device").is_in(ALL_DEVICES) & pl.col("ep").is_in(list(EP_IDX)))


def _gaps_and_users(fp: str) -> tuple[pl.DataFrame, dict]:
    """numpy pass: sorting (user, ts), intervals between requests of one user within a day."""
    d = (
        _valid(pl.scan_parquet(fp)).filter(pl.col("has_cid"))
        .select(
            "user", "ts",
            pl.col("device").replace_strict(DEV_IDX, return_dtype=pl.UInt8).alias("dev"),
            pl.col("ep").replace_strict(EP_IDX, return_dtype=pl.UInt8).alias("epi"),
        ).collect()
    )
    user = d["user"].to_numpy().astype(np.uint64)
    ts = d["ts"].to_numpy().astype(np.uint64)
    dev = d["dev"].to_numpy().astype(np.uint64)
    epi = d["epi"].to_numpy().astype(np.uint64)
    del d
    key = (user << np.uint64(26)) | (ts << np.uint64(6)) | (dev << np.uint64(1)) | epi
    del user, ts, dev, epi
    key.sort()
    u = (key >> np.uint64(26)).astype(np.uint32)
    t = ((key >> np.uint64(6)) & np.uint64((1 << 20) - 1)).astype(np.int64)
    dv = ((key >> np.uint64(1)) & np.uint64(31)).astype(np.int16)
    ep = (key & np.uint64(1)).astype(np.int16)
    del key
    n = len(u)
    same = np.zeros(n, dtype=bool)
    same[1:] = u[1:] == u[:-1]
    gap = np.zeros(n, dtype=np.int64)
    gap[1:] = t[1:] - t[:-1]
    starts = np.flatnonzero(~same)
    counts = np.diff(np.append(starts, n))
    rank = np.arange(n) - np.repeat(starts, counts)          # 0-based request number of the user within the day
    sess_new = (~same) | (gap > SESSION_GAP)
    sess_id = np.cumsum(sess_new) - 1
    sess_len = np.bincount(sess_id)
    sess_first = np.flatnonzero(sess_new)

    nd, ne = 32, 2
    flat = dv.astype(np.int64) * ne + ep
    out = {}
    # log2 intervals (only within a user)
    m = same
    b = np.minimum(np.floor(np.log2(gap[m] + 1)).astype(np.int64), LOG2_BINS - 1)
    out["gap_log2"] = np.bincount(flat[m] * LOG2_BINS + b, minlength=nd * ne * LOG2_BINS).reshape(nd, ne, LOG2_BINS)
    # linear 10-second intervals < 1 hour
    m2 = same & (gap < 3600)
    out["gap_lin"] = np.bincount(flat[m2] * LIN_BINS + gap[m2] // 10, minlength=nd * ne * LIN_BINS).reshape(nd, ne, LIN_BINS)
    # request rank within the day
    r = np.minimum(rank, RANK_CAP - 1)
    out["rank"] = np.bincount(flat * RANK_CAP + r, minlength=nd * ne * RANK_CAP).reshape(nd, ne, RANK_CAP)
    # requests in a session (by the device/ep of the session's first request)
    sl = np.minimum(sess_len, SESS_CAP) - 1
    out["sess_len"] = np.bincount(flat[sess_first] * SESS_CAP + sl, minlength=nd * ne * SESS_CAP).reshape(nd, ne, SESS_CAP)
    # per user
    n_sess = np.add.reduceat(sess_new.astype(np.int64), starts)
    ep_mask = np.bitwise_or.reduceat((1 << ep).astype(np.int16), starts)
    dev_first = dv[starts]
    # n_dev: how many distinct devices a user has within a day (by rows — via sorting by (user, dev))
    key2 = (u.astype(np.uint64) << np.uint64(5)) | dv.astype(np.uint64)
    key2.sort()
    u2 = (key2 >> np.uint64(5)).astype(np.uint32)
    new2 = np.ones(len(key2), dtype=bool)
    new2[1:] = key2[1:] != key2[:-1]
    ustarts2 = np.flatnonzero(np.r_[True, u2[1:] != u2[:-1]])
    n_dev = np.add.reduceat(new2.astype(np.int64), ustarts2)
    users = pl.DataFrame({
        "user": u[starts], "n": counts.astype(np.int32), "n_sess": n_sess.astype(np.int16),
        "dev": dev_first.astype(np.int8), "ep_mask": ep_mask.astype(np.int8),
        "n_dev": n_dev.astype(np.int8), "first_ts": t[starts].astype(np.int32), "last_ts": t[starts + counts - 1].astype(np.int32),
    })
    return users, out


def aggregate_day(i: int, fp: str, force: bool) -> None:
    sfx = f"d{i:02d}"
    done = os.path.join(CACHE, f"gaps_{sfx}.npz")
    if os.path.exists(done) and not force:
        print(f"  day {i}: cache, pass-through", flush=True)
        return
    t0 = time.time()
    lf = _valid(pl.scan_parquet(fp))
    # 1) low-cardinality cube
    cube = (
        lf.with_columns((pl.col("ts") // 3600).cast(pl.Int32).alias("hour"))
        .group_by("hour", "device", "ep", "place", "position", "is_child", "age", "broadcast", "has_cid")
        .agg(pl.len().alias("n")).collect(engine="streaming")
    )
    cube.write_parquet(os.path.join(CACHE, f"cube_{sfx}.parquet"))
    # 2) high-cardinality tags
    for tag in HIGH_CARD:
        (lf.group_by(tag, "device", "ep", "place").agg(pl.len().alias("n")).collect(engine="streaming")
         .write_parquet(os.path.join(CACHE, f"hc_{tag}_{sfx}.parquet")))
    # 3) full combinations
    (lf.group_by("device", "ep", "place", "location", "category", "channel").agg(pl.len().alias("n"))
     .collect(engine="streaming").write_parquet(os.path.join(CACHE, f"combo_{sfx}.parquet")))
    print(f"  day {i}: assemblies {time.time() - t0:.0f}c", flush=True)
    # 4) users/intervals
    users, g = _gaps_and_users(fp)
    users.write_parquet(os.path.join(CACHE, f"users_{sfx}.parquet"))
    np.savez_compressed(done, **g)
    print(f"  day {i}: ready-for {time.time() - t0:.0f}c ({cube['n'].sum():,} requests, {len(users):,} user)", flush=True)


HX_TAGS = ["location", "channel", "category", "contractor", "client_version"]


def aggregate_hx(i: int, fp: str, force: bool) -> None:
    """tag × device × ep × hour — for the "tag ↔ time of day / day of week" relations."""
    sfx = f"d{i:02d}"
    if not force and all(os.path.exists(os.path.join(CACHE, f"hx_{t}_{sfx}.parquet")) for t in HX_TAGS):
        return
    lf = _valid(pl.scan_parquet(fp)).with_columns((pl.col("ts") // 3600).cast(pl.Int32).alias("hour"))
    for tag in HX_TAGS:
        (lf.group_by("hour", "device", "ep", tag).agg(pl.len().alias("n")).collect(engine="streaming")
         .write_parquet(os.path.join(CACHE, f"hx_{tag}_{sfx}.parquet")))
    print(f"  day {i}: hx ready", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    os.makedirs(CACHE, exist_ok=True)
    files = sorted(glob.glob(os.path.join(PREPARED, "day_*.parquet")))
    if not files:
        raise SystemExit("No prepared dens: launch prepare.py")
    for i, fp in enumerate(files):
        aggregate_day(i, fp, a.force)
        aggregate_hx(i, fp, a.force)
    print("Cash is ready →", CACHE)


if __name__ == "__main__":
    main()
