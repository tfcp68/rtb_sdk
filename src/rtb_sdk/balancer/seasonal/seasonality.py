"""
Streaming aggregation of CSV logs to build a seasonality profile.

Builds HourlyWeights in O(24) or O(168) memory regardless of
the file size. The same single pass optionally collects
UserActivityHistogram and TagCountsByHour to pass into TemporalContext.

Low-level primitives (process_log_chunk, accumulate_tag_counts,
normalize_*) are used in balance.build_seasonal_context for a single
pass collecting all aggregates at once.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone as _tz_utc
from zoneinfo import ZoneInfo

from rtb_sdk.balancer.seasonal.types import (
    AggregationMode,
    HistoricalLogsConfig,
    HourlyWeights,
    LogStreamState,
    TagCountsByHour,
)


# ---------------------------------------------------------------------------
# Determining the hour type from a timestamp
# ---------------------------------------------------------------------------

def _get_h_type(ts: datetime, mode: AggregationMode) -> int:
    if mode == 'hour_of_week':
        return ts.weekday() * 24 + ts.hour
    return ts.hour


# ---------------------------------------------------------------------------
# Processing the stream of rows
# ---------------------------------------------------------------------------

def process_log_chunk(
    chunk: list[dict[str, str]],
    state: LogStreamState,
    config: HistoricalLogsConfig,
    tz: ZoneInfo,
    tag_col_map: dict[str, str] | None = None,
) -> None:
    """Processes one chunk of CSV rows and updates state in place.

    In a single pass over the chunk:
    - Parses the timestamp and adds events to state['counts'].
    - If config contains user_id_col — accumulates state['user_counts'].
    - If tag_col_map is set — accumulates state['tag_counts'].

    Args:
        chunk:       list of rows from csv.DictReader (list[dict]).
        state:       mutable state (LogStreamState).
        config:      source configuration (HistoricalLogsConfig).
        tz:          time zone for normalizing timestamps.
        tag_col_map: {VocabName: column_name_in_csv}; None → tags are not collected.
    """
    ts_col: str = config['timestamp_col']
    count_col: str | None = config.get('count_col')
    user_id_col: str | None = config.get('user_id_col')
    mode = state['mode']

    counts = state['counts']
    user_counts_by_hour = state['user_counts_by_hour']
    user_counts_total = state['user_counts_total']
    tag_counts = state['tag_counts']

    for row in chunk:
        ts_str = row.get(ts_col, '').strip()
        if not ts_str:
            continue
        try:
            ts = datetime.fromisoformat(ts_str)
        except ValueError:
            continue

        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=_tz_utc.utc)
        ts = ts.astimezone(tz)

        h = _get_h_type(ts, mode)

        value = 1.0
        if count_col:
            raw = row.get(count_col, '').strip()
            if raw:
                try:
                    value = float(raw)
                except ValueError:
                    pass

        counts[h] = counts.get(h, 0.0) + value

        if user_id_col:
            uid = row.get(user_id_col, '').strip()
            if uid:
                hour_uids = user_counts_by_hour.setdefault(h, {})
                hour_uids[uid] = hour_uids.get(uid, 0) + int(value)
                user_counts_total[uid] = user_counts_total.get(uid, 0) + int(value)

        if tag_col_map:
            accumulate_tag_counts(row, h, tag_counts, tag_col_map)


def normalize_counts(counts: dict[int, float]) -> dict[int, float]:
    """Normalizes the counts dictionary to a sum of 1.0.

    Raises:
        ValueError: if total == 0 (the file is empty or all rows were not recognized).
    """
    total = sum(counts.values())
    if total == 0:
        raise ValueError("Logs are empty — seasonality profile is not built")
    return {k: v / total for k, v in counts.items()}


def accumulate_tag_counts(
    row: dict[str, str],
    h_type: int,
    tag_counts: TagCountsByHour,
    tag_col_map: dict[str, str],
) -> None:
    """Adds the tags of one CSV row to the accumulator tag_counts[h_type].

    Accumulates in the format {VocabName: {RawTag: count}} — each dictionary
    is normalized independently via normalize_tag_counts.

    Args:
        row:         one CSV row (dict col→value).
        h_type:      hour type of the row (0-23 or 0-167).
        tag_counts:  mutable accumulator.
        tag_col_map: {VocabName: column_name_in_csv}.
    """
    h_slot: dict[str, dict[str, float]] = tag_counts.setdefault(h_type, {})
    for vocab, col in tag_col_map.items():
        val = row.get(col, '').strip()
        if val:
            vocab_counts = h_slot.setdefault(vocab, {})
            vocab_counts[val] = vocab_counts.get(val, 0.0) + 1.0


def normalize_tag_counts(
    tag_counts: TagCountsByHour,
) -> TagCountsByHour:
    """Normalizes tag counters to probabilities (per-vocab, sum=1).

    Each tag dictionary is normalized independently: sum(probs[vocab]) == 1.0
    for each vocab and each h_type.

    Returns:
        {h_type: {VocabName: {RawTag: probability}}}.
    """
    result: TagCountsByHour = {}
    for h_type, vocab_counts in tag_counts.items():
        result[h_type] = {}
        for vocab, inner in vocab_counts.items():
            total = sum(inner.values())
            if total > 0:
                result[h_type][vocab] = {tag: v / total for tag, v in inner.items()}
            else:
                result[h_type][vocab] = {}
    return result


# ---------------------------------------------------------------------------
# Building the seasonality profile — public entry point
# ---------------------------------------------------------------------------

def build_seasonality_profile(config: HistoricalLogsConfig) -> HourlyWeights:
    """Builds a normalized seasonality profile from a CSV file.

    Reads the file as a stream, chunk_size rows at a time; memory consumption is O(24) or
    O(168) regardless of the file size. Collects only counts
    (the user histogram and tags are not needed here). To collect
    all aggregates at once use balance.build_seasonal_context.

    Args:
        config: HistoricalLogsConfig with the required path and timestamp_col.

    Returns:
        HourlyWeights with normalized weights (sum == 1.0).

    Raises:
        ValueError:        if the file is empty or no row was recognized.
        FileNotFoundError: if the file at the path is not found.
        KeyError:          if path or timestamp_col is missing from config.
    """
    mode: AggregationMode = config.get(
        'aggregation_mode', 'hour_of_day'
    )
    tz = ZoneInfo(config.get('timezone', 'UTC'))
    chunk_size = int(config.get('chunk_size', 10_000))
    n = 24 if mode == 'hour_of_day' else 168

    state = LogStreamState(
        counts={h: 0.0 for h in range(n)},
        user_counts_by_hour={},
        user_counts_total={},
        tag_counts={},
        mode=mode,
    )

    with open(config['path'], newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        chunk: list[dict[str, str]] = []

        for row in reader:
            chunk.append(row)
            if len(chunk) >= chunk_size:
                process_log_chunk(chunk, state, config, tz)
                chunk.clear()

        if chunk:
            process_log_chunk(chunk, state, config, tz)

    weights = normalize_counts(state['counts'])
    return HourlyWeights(mode=mode, weights=weights)
