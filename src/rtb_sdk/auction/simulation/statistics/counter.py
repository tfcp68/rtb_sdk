"""
Sliding window for accurate counting of frequency limits.

Logic: for each ad a list of impression datetime timestamps is stored.
The limit check uses the "n-th most recent impression" method:

  If len(timestamps) >= limit AND timestamps[-limit] lies
  inside the window [current_time - window, current_time] —
  the window already holds >= limit impressions, the limit is exhausted.

This guarantees correct behavior at period boundaries:
  5 impressions at 12:58 + 5 impressions at 13:02 with a limit of 5/hour →
  check at 13:02: timestamps[-5] = 12:58 > 12:02 (window_start) → BLOCKED.
"""
from datetime import datetime, timedelta

from rtb_sdk.schemas import GranulatedCounter
from rtb_sdk.constants import Gran
from rtb_sdk.helpers import create_granulated_counter


# Sliding window lengths in seconds
GRAN_SECONDS: dict[str, int] = {
    Gran.TEN_MINUTES: 600,
    Gran.HOUR:        3_600,
    Gran.DAY:         86_400,
    Gran.WEEK:        604_800,
    Gran.MONTH:       30 * 86_400,
}

# Maximum timestamp retention depth; records older than this threshold are trimmed
MAX_WINDOW_SECONDS: int = 30 * 86_400


# ── rolling window check ───────────────────────────────────────────────────────

def is_over_limit(
    timestamps: list[datetime],
    limit: int,
    window_seconds: int,
    current_time: datetime,
) -> bool:
    """
    Checks whether the limit is exhausted in the sliding window.

    Algorithm: take the limit-th most recent impression (timestamps[-limit]).
    If it lies inside the window [current_time - window, current_time] —
    the window already holds >= limit impressions, the limit is exhausted.

    Args:
        timestamps: list of impression datetimes, sorted ascending (oldest first)
        limit: maximum allowed number of impressions in the window (<=0 = no limit)
        window_seconds: sliding window length in seconds
        current_time: current request time

    Returns:
        bool: True if the limit is exceeded
    """
    if limit <= 0:
        return False
    if len(timestamps) < limit:
        return False
    nth_recent = timestamps[-limit]
    window_start = current_time - timedelta(seconds=window_seconds)
    return nth_recent > window_start


def count_in_window(
    timestamps: list[datetime],
    window_seconds: int,
    current_time: datetime,
) -> int:
    """
    Counts the number of impressions inside the sliding window.

    Args:
        timestamps: list of impression datetimes
        window_seconds: window length in seconds
        current_time: current request time

    Returns:
        int: number of impressions in the window (current_time - window, current_time]
    """
    window_start = current_time - timedelta(seconds=window_seconds)
    return sum(1 for t in timestamps if t > window_start)


# ── counter computation ────────────────────────────────────────────────────────

def timestamps_to_granulated_counter(
    timestamps: list[datetime],
    current_time: datetime,
) -> GranulatedCounter:
    """
    Computes a GranulatedCounter from a list of timestamps over sliding windows.

    For each granularity counts the number of impressions
    in the corresponding sliding window.

    Args:
        timestamps: list of impression datetimes
        current_time: current request time

    Returns:
        GranulatedCounter: counters for all granularities
    """
    return create_granulated_counter(
        ten_minutes=count_in_window(timestamps, GRAN_SECONDS[Gran.TEN_MINUTES], current_time),
        hour=count_in_window(timestamps, GRAN_SECONDS[Gran.HOUR], current_time),
        day=count_in_window(timestamps, GRAN_SECONDS[Gran.DAY], current_time),
        week=count_in_window(timestamps, GRAN_SECONDS[Gran.WEEK], current_time),
        month=count_in_window(timestamps, GRAN_SECONDS[Gran.MONTH], current_time),
    )


# ── timestamp list management ──────────────────────────────────────────────────

def append_timestamp(
    timestamps: list[datetime],
    current_time: datetime,
) -> list[datetime]:
    """
    Adds a timestamp and trims stale records.

    Removes impressions older than MAX_WINDOW_SECONDS to save memory.

    Args:
        timestamps: current list of timestamps (oldest first)
        current_time: time of the new impression

    Returns:
        list[datetime]: updated list of timestamps
    """
    new_timestamps = timestamps + [current_time]
    cutoff = current_time - timedelta(seconds=MAX_WINDOW_SECONDS)
    return [t for t in new_timestamps if t > cutoff]
