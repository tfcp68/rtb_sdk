"""Downsample a janus parquet into a CSV log for the A/B harness of hypothesis 1.

`build_seasonal_context` reads a CSV from disk (`open(config['path'])` → `csv.DictReader`),
so running the real balancer requires a log on disk. The full parquet (8 GB,
~154M events) is unsuitable as CSV — we take a subsample.

**We sample by whole USERS** (`hash(uid) % K = 0`), not by events: the whole
fix relies on the per-user frequency structure (group C — heavy multi-hour users
exceeding the limit), and an event sample would destroy it, understating the frequencies.

We write the UTC timestamp as naive ISO: `process_log_chunk` treats a naive ts as UTC and
converts it to the config timezone (`Europe/Moscow`) — the same way my sim does
`AT TIME ZONE`. So the hourly buckets match.

PITFALLS (already stepped on): the `datetime` column is TIMESTAMP WITH TIME ZONE, and the session TZ of
DuckDB is picked up from the OS and here equals `Europe/Moscow`. So a bare
`strftime(datetime, ...)` renders LOCAL time WITHOUT a zone mark, the balancer reads it
as UTC and adds another +3h — all events shift by 3 hours. An explicit
`AT TIME ZONE 'UTC'` before strftime is mandatory.

We take WHOLE days by local time, skipping partial days at the file boundaries
(in the report this is the `n_days=8` artifact).

Run:
    DAYS=1 OUT=.../ab_log_1day.csv  python make_ab_log.py
    DAYS=7 OUT=.../ab_log_7day.csv  python make_ab_log.py
"""

from __future__ import annotations

import os

import duckdb

PARQUET = os.environ.get("PROFILE_FILE", "E:/Logs/janus-20260615.parquet")
DAYS = int(os.environ.get("DAYS", "1"))
# The divisor of the hash sampling by users. 187 was chosen on a single-day window
# (5.6M uniques/day -> ~30k). Fixed intentionally: the same K on different windows
# gives THE SAME subsample of people, so the 1-day and multi-day runs
# are comparable to each other.
K = int(os.environ.get("K", "187"))
OUT = os.environ.get(
    "OUT", "docs/benchmark/reach_frequency/cumulative_freq/ab_log_1day.csv"
)
TIMEZONE = "Europe/Moscow"

DUCKDB_THREADS = int(os.environ.get("DUCKDB_THREADS", "4"))
# IMPORTANT: the machine has 17 GB, but sometimes only ~3-4 GB are free. An 8 GB limit drove DuckDB into
# swap and crashed the build. DuckDB spills to temp_directory, so a smaller limit
# just means more disk spill, not a crash. Keep a margin from the free RAM.
DUCKDB_MEMORY_LIMIT = os.environ.get("DUCKDB_MEMORY_LIMIT", "2GB")
DUCKDB_TEMP_DIR = os.environ.get("DUCKDB_TEMP_DIR", "E:/duckdb_tmp")

USER_EXPR = (
    "COALESCE(NULLIF(regexp_extract('?' || split_part(path, '?', 2), "
    "'[?&]client_id=([^&]*)', 1), ''), 'EmptyUser')"
)


def main() -> None:
    con = duckdb.connect()
    con.execute(f"PRAGMA threads={DUCKDB_THREADS}")
    con.execute(f"PRAGMA memory_limit='{DUCKDB_MEMORY_LIMIT}'")
    con.execute(f"PRAGMA temp_directory='{DUCKDB_TEMP_DIR}'")

    local = f"(datetime AT TIME ZONE '{TIMEZONE}')"

    # Boundaries by LOCAL time; the first whole day starts on the next
    # local date after the minimum (the first day in the file is almost always partial).
    lo, hi = con.execute(
        f"SELECT MIN({local})::DATE, MAX({local})::DATE FROM read_parquet('{PARQUET}')"
    ).fetchone()
    print(f"Local dates in the file: {lo} .. {hi}; take {DAYS} day-long {lo}+1 daylight",
          flush=True)

    # K is fixed rather than derived from an exact COUNT(DISTINCT): counting uniques over ~130M
    # rows is a separate heavy pass, while hash sampling is deterministic, so the same
    # K gives a CONSISTENT subsample of users on any window (which is what we need so that
    # the 1-day and multi-day runs are compared on the same people).
    # Neither ORDER BY (build_seasonal_context just accumulates counters, order does not matter)
    # nor a temp table — a single streaming pass straight into the CSV.
    out = OUT.replace("\\", "/")
    con.execute(
        f"""
        COPY (
            SELECT strftime(datetime AT TIME ZONE 'UTC', '%Y-%m-%dT%H:%M:%S') AS datetime,
                   uid AS client_id
            FROM (
                SELECT datetime, {USER_EXPR} AS uid
                FROM read_parquet('{PARQUET}')
                WHERE {local} >= DATE '{lo}' + INTERVAL 1 day
                  AND {local} <  DATE '{lo}' + INTERVAL {DAYS + 1} day
            )
            WHERE uid <> 'EmptyUser' AND hash(uid) % {K} = 0
        ) TO '{out}' (HEADER, DELIMITER ',')
        """
    )
    size_mb = os.path.getsize(OUT) / 1e6
    print(f"Ready: {out}  ({size_mb:.0f} MB, K={K})")


if __name__ == "__main__":
    main()
