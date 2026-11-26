"""Measuring the GAIN from the fix of hypothesis 1 (cumulative user constraints).

The notebook test_cumfreq.ipynb proved that the PROBLEM is real: the current 'd' model
spreads the daily volume ∝ w_h (`prop`), while reality is front-loaded (`true`),
the gap TV(prop,true) ≈ 7% at C=5 (up to ~12% at C=1). But the FIX ITSELF was not measured there
(see cumfreq_report.md, pp. 21-24).

This script applies two cheap approximations from section 1 of
`frequency_accounting_improvements.md` — WITHOUT touching the balancer code, purely on
logs — and measures what share of the gap each one closes:

  fixed_headroom (Solution B, recommended): aggregated remaining headroom.
      We go through hours 0->23 with a SHARED remaining budget b, starting at C.
      In each hour we deliver Σ_userdays min(req_uh, b) over the REAL hourly
      request histogram, then deplete b -= delivered_h / N_userdays.
      Front-loading arises adaptively; the residual error vs true = the
      user heterogeneity that the aggregate by definition does not see
      (for true each user has their own personal `before`, here — a common population one).

  fixed_elastic (Solution A): prop[h] * (1 - h/24)^beta, sweep over beta.
      A pure time-of-day heuristic (multiplies the 'd' volume by a decaying curve).
      For a fair SHAPE comparison we re-normalize to the same total T; the raw total
      is also printed (the heuristic itself loses volume).

Gain metric: gap_closed% = (TV(prop,true) - TV(fixed,true)) / TV(prop,true).

Run:
    .venv/Scripts/python.exe docs/benchmark/reach_frequency/cumulative_freq/measure_fix_gain.py
"""

from __future__ import annotations

import os

import numpy as np
import duckdb

# --------------------------------------------------------------------------- #
# Configuration (matches the notebook; the clean week from the report = janus-20260615)
# --------------------------------------------------------------------------- #
TIMEZONE = "Europe/Moscow"
PROFILE_FILE = os.environ.get("PROFILE_FILE", "E:/Logs/janus-20260615.parquet")

CAPS = [1, 2, 3, 5, 10]
CAP_MAIN = 5
BETAS = [0.5, 0.8, 1.0, 1.5]          # sweep of the elastic buffer shape

DUCKDB_THREADS = 4
DUCKDB_MEMORY_LIMIT = "8GB"
DUCKDB_TEMP_DIR = "E:/duckdb_tmp"

# None = the whole week. For a quick logic check set it to 2 (or env SAMPLE_DAYS).
_sd = os.environ.get("SAMPLE_DAYS")
SAMPLE_DAYS: int | None = int(_sd) if _sd else None


# --------------------------------------------------------------------------- #
# Loading (as in the notebook): (user, day, hour) -> req + cumulative before
# --------------------------------------------------------------------------- #
def build_cum(con: duckdb.DuckDBPyConnection) -> tuple[np.ndarray, int, int]:
    """Materializes events, cum, hourreq. Returns (w_arr, n_days, N_ud)."""
    local = f"(datetime AT TIME ZONE '{TIMEZONE}')"
    user_expr = (
        "COALESCE(NULLIF(regexp_extract('?' || split_part(path, '?', 2), "
        "'[?&]client_id=([^&]*)', 1), ''), 'EmptyUser')"
    )

    file_start = con.execute(
        f"SELECT MIN(datetime)::VARCHAR FROM read_parquet('{PROFILE_FILE}')"
    ).fetchone()[0]
    where = ""
    if SAMPLE_DAYS is not None:
        where = (
            f"WHERE datetime < TIMESTAMP '{file_start}' "
            f"+ INTERVAL '{SAMPLE_DAYS} days'"
        )

    print(f"Reading {PROFILE_FILE}{' [SAMPLE]' if where else ' [FULL]'} ...", flush=True)
    con.execute(
        f"""
        CREATE TEMP TABLE events AS
        SELECT EXTRACT(hour FROM {local})::INT AS h,
               {user_expr} AS uid,
               date_trunc('day', {local}) AS day
        FROM read_parquet('{PROFILE_FILE}')
        {where}
        """
    )

    agg = con.execute("SELECT h, COUNT(*) c FROM events GROUP BY h ORDER BY h").fetchdf()
    w = {int(h): float(c) for h, c in zip(agg["h"], agg["c"])}
    w_arr = np.array([w.get(h, 0.0) for h in range(24)])
    w_arr = w_arr / w_arr.sum()

    n_days = int(con.execute("SELECT COUNT(DISTINCT day) FROM events").fetchone()[0])
    print(f"Days in the sample: {n_days}", flush=True)

    print("Build cum (window user-day, heavy-pass)...", flush=True)
    con.execute(
        """
        CREATE TEMP TABLE cum AS
        WITH ud AS (
            SELECT uid, day, h, COUNT(*) AS req
            FROM events GROUP BY uid, day, h
        )
        SELECT uid, day, h, req,
            COALESCE(SUM(req) OVER (PARTITION BY uid, day ORDER BY h
                     ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING), 0) AS before
        FROM ud
        """
    )

    # Hourly request histogram for the aggregated headroom fix.
    # We exclude EmptyUser (a synthetic aggregate uid of anonymous users) — as in the notebook.
    con.execute(
        """
        CREATE TEMP TABLE hourreq AS
        SELECT h, req, COUNT(*) AS cnt
        FROM cum WHERE uid <> 'EmptyUser'
        GROUP BY h, req
        """
    )
    n_ud = int(
        con.execute(
            "SELECT COUNT(*) FROM (SELECT DISTINCT uid, day FROM cum WHERE uid <> 'EmptyUser')"
        ).fetchone()[0]
    )
    print(f"cum + hourreq materialized. Users-days (without EmptyUser): {n_ud:,}",
          flush=True)
    return w_arr, n_days, n_ud


# --------------------------------------------------------------------------- #
# Metric
# --------------------------------------------------------------------------- #
def tv_shape(a: np.ndarray, b: np.ndarray) -> float:
    """TV between shapes (each normalized to sum 1)."""
    sa, sb = a.sum(), b.sum()
    if sa == 0 or sb == 0:
        return float("nan")
    return 0.5 * float(np.sum(np.abs(a / sa - b / sb)))


# --------------------------------------------------------------------------- #
# Simulation of all curves for one C
# --------------------------------------------------------------------------- #
def simulate(
    con: duckdb.DuckDBPyConnection,
    C: int,
    w_arr: np.ndarray,
    n_days: int,
    n_ud: int,
    hourreq: dict[int, list[tuple[int, int]]],
) -> dict:
    # true (per-user cumulative) — as in the notebook, EmptyUser is excluded for
    # consistency with fixed_headroom (which is also without EmptyUser).
    d = con.execute(
        f"""
        SELECT h, SUM(GREATEST(0, LEAST(req, {C} - before))) AS true_d
        FROM cum WHERE uid <> 'EmptyUser'
        GROUP BY h ORDER BY h
        """
    ).fetchdf()
    true = np.zeros(24)
    for h, t in zip(d["h"].astype(int), d["true_d"]):
        true[h] = t / n_days
    T = true.sum()

    prop = T * w_arr  # the current 'd' model

    # --- fixed_headroom (Solution B): a shared decreasing budget remainder -------- #
    b = float(C)
    fixed_hr = np.zeros(24)
    for h in range(24):
        rows = hourreq.get(h, [])
        # Σ_userdays min(req, b) over the real hourly histogram
        delivered = sum(cnt * min(req, b) for req, cnt in rows)
        fixed_hr[h] = delivered / n_days
        b = max(0.0, b - delivered / n_ud)  # deplete the shared headroom

    # --- fixed_elastic (Solution A): prop * (1-h/24)^beta ------------------- #
    hh = np.arange(24)
    elastic = {}
    for beta in BETAS:
        m = (1.0 - hh / 24.0) ** beta
        raw = prop * m
        renorm = raw * (T / raw.sum()) if raw.sum() > 0 else raw
        elastic[beta] = {"raw": raw, "renorm": renorm}

    return {"true": true, "prop": prop, "fixed_hr": fixed_hr,
            "elastic": elastic, "T": T}


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> None:
    con = duckdb.connect()
    con.execute(f"PRAGMA threads={DUCKDB_THREADS}")
    con.execute(f"PRAGMA memory_limit='{DUCKDB_MEMORY_LIMIT}'")
    con.execute(f"PRAGMA temp_directory='{DUCKDB_TEMP_DIR}'")

    w_arr, n_days, n_ud = build_cum(con)

    # Load hourreq into memory once (for a cheap sweep over C in Python).
    hr_df = con.execute("SELECT h, req, cnt FROM hourreq").fetchdf()
    hourreq: dict[int, list[tuple[int, int]]] = {}
    for h, req, cnt in zip(hr_df["h"].astype(int), hr_df["req"].astype(int),
                           hr_df["cnt"].astype(int)):
        hourreq.setdefault(h, []).append((req, cnt))

    sims = {C: simulate(con, C, w_arr, n_days, n_ud, hourreq) for C in CAPS}

    # ---- Gain table over the C sweep ------------------------------------- #
    print("\n" + "=" * 78)
    print("GROWN FIX: TV reality (true) and fraction of the closed gap")
    print("=" * 78)
    print(f"{'C':>3} | {'TV(prop)':>9} {'TV(hr)':>8} {'gap_closed':>11} | "
          f"{'vol_hr/T':>9} | best-β elastic")
    print("-" * 78)
    for C in CAPS:
        s = sims[C]
        tv_prop = tv_shape(s["prop"], s["true"])
        tv_hr = tv_shape(s["fixed_hr"], s["true"])
        gap = (tv_prop - tv_hr) / tv_prop if tv_prop > 0 else float("nan")
        vol_hr = s["fixed_hr"].sum() / s["T"] if s["T"] else float("nan")

        # best beta by TV(renorm, true)
        best_b, best_tv = None, float("inf")
        for beta, cur in s["elastic"].items():
            tvb = tv_shape(cur["renorm"], s["true"])
            if tvb < best_tv:
                best_b, best_tv = beta, tvb
        gap_el = (tv_prop - best_tv) / tv_prop if tv_prop > 0 else float("nan")

        print(f"{C:>3} | {tv_prop:>9.4f} {tv_hr:>8.4f} {gap:>10.0%} | "
              f"{vol_hr:>8.2f}x | β={best_b} TV={best_tv:.4f} ({gap_el:.0%})")

    # ---- Details for CAP_MAIN --------------------------------------- #
    s = sims[CAP_MAIN]
    tv_prop = tv_shape(s["prop"], s["true"])
    tv_hr = tv_shape(s["fixed_hr"], s["true"])
    print("\n" + "=" * 78)
    print(f"Details in C={CAP_MAIN}")
    print("=" * 78)
    print(f"  TV(prop, true)        = {tv_prop:.4f}   (current-break)")
    print(f"  TV(fixed_hr, true)    = {tv_hr:.4f}   "
          f"(-> closed {(tv_prop - tv_hr) / tv_prop:.0%} rupture)")
    print(f"  volume fixed_hr / true = {s['fixed_hr'].sum() / s['T']:.3f}x "
          f"(1.0 = faithful total)")
    print("  elastic β-swipe (renorm toward T):")
    for beta, cur in s["elastic"].items():
        tvb = tv_shape(cur["renorm"], s["true"])
        gapb = (tv_prop - tvb) / tv_prop
        vraw = cur["raw"].sum() / s["T"]
        print(f"    β={beta}: TV={tvb:.4f} (closed {gapb:>4.0%})  "
              f"raw={vraw:.2f}x")

    # hourly curves for C=CAP_MAIN
    print(f"\n  hourly (impressions/hourly), C={CAP_MAIN}:")
    print(f"  {'h':>3} {'true':>10} {'prop':>10} {'fixed_hr':>10}")
    for h in range(24):
        print(f"  {h:>3} {s['true'][h]:>10.0f} {s['prop'][h]:>10.0f} "
              f"{s['fixed_hr'][h]:>10.0f}")


if __name__ == "__main__":
    main()
