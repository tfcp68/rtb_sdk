"""
MockStatistics — impression statistics store for the simulation.

Structure (sliding windows, list of datetimes):
  ad_timestamps[ad_id]                           → list[datetime]
  user_ad_timestamps[ad_id][user_id]             → list[datetime]
  ad_total_counts[ad_id][auction_type]           → int  (total for all time)

Each impression is recorded as a datetime timestamp (oldest first).
Frequency limits are checked with the sliding window method: the n-th
most recent impression (where n = limit) is taken and checked for whether it falls
into the current window [current_time - window, current_time].

This removes the boundary effect of the old approach (reset by calendar window),
under which 5 impressions at 12:58 + 5 impressions at 13:02 bypassed the 5/hour limit.
"""
from typing import TypedDict
from datetime import datetime, timedelta

from rtb_sdk.schemas import AdStats, AdId, AdShowTimes, AuctionTypeId, TimestampList, UserId
from rtb_sdk.constants import AuctionType
from rtb_sdk.helpers import (
    create_ad_stats,
    create_auction_stats,
    create_granulated_counter,
)

from rtb_sdk.auction.simulation.statistics.counter import (
    append_timestamp,
    timestamps_to_granulated_counter,
    MAX_WINDOW_SECONDS,
)


# ── type aliases ───────────────────────────────────────────────────────────────

type AdTimestamps = dict[AdId, TimestampList]
type UserAdTimestamps = dict[AdId, dict[UserId, TimestampList]]
type AdTotalCounts = dict[AdId, dict[AuctionTypeId, int]]


# ── TypedDict ──────────────────────────────────────────────────────────────────

class MockStatistics(TypedDict):
    # [ad_id] → list[datetime] of impressions (oldest first, sliding window)
    ad_timestamps: AdTimestamps

    # [ad_id][user_id] → list[datetime] of impressions to the user
    user_ad_timestamps: UserAdTimestamps

    # [ad_id][auction_type] → int (total for the whole simulation time)
    ad_total_counts: AdTotalCounts


# ── create ─────────────────────────────────────────────────────────────────────

def create_mock_statistics() -> MockStatistics:
    """Creates an empty MockStatistics."""
    return {
        'ad_timestamps': {},
        'user_ad_timestamps': {},
        'ad_total_counts': {},
    }


# ── ad timestamps ──────────────────────────────────────────────────────────────

def get_ad_timestamps(
    stats: MockStatistics,
    ad_ids: list[AdId] | None = None,
) -> AdTimestamps:
    """
    Returns the lists of ad impression timestamps.

    Args:
        stats: MockStatistics
        ad_ids: list of ad ids; None → all from stats

    Returns:
        AdTimestamps: {ad_id → list[datetime]}
    """
    if ad_ids is None:
        return stats['ad_timestamps']
    timestamps = stats['ad_timestamps']
    return {ad_id: timestamps.get(ad_id, []) for ad_id in ad_ids}


def get_ad_show_times(
    stats: MockStatistics,
    ad_ids: list[AdId] | None = None,
) -> AdShowTimes:
    """
    Returns the last impression time for each ad.

    Computed as the last element of the timestamps list.
    Missing or empty lists are skipped (the filter will apply DATE_ZERO).

    Args:
        stats: MockStatistics
        ad_ids: list of ad ids; None → all from stats

    Returns:
        AdShowTimes
    """
    source = get_ad_timestamps(stats, ad_ids)
    return {
        ad_id: ts_list[-1]
        for ad_id, ts_list in source.items()
        if ts_list
    }


def get_ad_stats(
    stats: MockStatistics,
    ad_ids: list[AdId] | None = None,
    current_time: datetime | None = None,
) -> AdStats:
    """
    Computes AdStats (GranulatedCounter) from lists of timestamps.

    Used to pass into the auction strategies (best_velocity, etc.).
    For each granularity counts impressions in the sliding window.
    All impressions (precise + fuzzy) are merged into a single counter.

    Args:
        stats: MockStatistics
        ad_ids: list of ad ids; None → all from stats
        current_time: point in time for calculating the sliding windows;
                      if None — datetime.now() is used

    Returns:
        AdStats
    """
    if current_time is None:
        current_time = datetime.now()
    ad_ts = get_ad_timestamps(stats, ad_ids)
    result: dict = {}
    for ad_id, timestamps in ad_ts.items():
        combined_counter = timestamps_to_granulated_counter(timestamps, current_time)
        result[ad_id] = create_auction_stats(combined_counter, create_granulated_counter())
    return create_ad_stats(result)


def update_ad_stats(
    stats: MockStatistics,
    ad_id: AdId,
    auction_type: AuctionTypeId,
    current_time: datetime,
) -> None:
    """
    Adds an ad impression timestamp and increments the counter.

    Initializes the nested dicts on first access.
    Automatically trims timestamps older than MAX_WINDOW_SECONDS.
    Mutates stats in place.

    Args:
        stats: MockStatistics
        ad_id: ad id
        auction_type: 'precise' | 'fuzzy'
        current_time: impression time
    """
    if ad_id not in stats['ad_timestamps']:
        stats['ad_timestamps'][ad_id] = []
    stats['ad_timestamps'][ad_id] = append_timestamp(
        stats['ad_timestamps'][ad_id],
        current_time,
    )
    # total counter for all time
    if ad_id not in stats['ad_total_counts']:
        stats['ad_total_counts'][ad_id] = {}
    counts = stats['ad_total_counts'][ad_id]
    counts[auction_type] = counts.get(auction_type, 0) + 1


def reset_ad_stats_if_needed(
    stats: MockStatistics,
    current_time: datetime,
) -> None:
    """
    Trims stale impression timestamps for all ads.

    Removes timestamps older than MAX_WINDOW_SECONDS. Called at the start of
    processing each request to keep memory usage under control.

    Args:
        stats: MockStatistics
        current_time: current request time
    """
    cutoff = current_time - timedelta(seconds=MAX_WINDOW_SECONDS)
    for ad_id in list(stats['ad_timestamps'].keys()):
        stats['ad_timestamps'][ad_id] = [
            t for t in stats['ad_timestamps'][ad_id] if t > cutoff
        ]


# ── user-ad timestamps ─────────────────────────────────────────────────────────

def get_user_ad_timestamps(
    stats: MockStatistics,
    user_id: UserId,
) -> dict[AdId, TimestampList]:
    """
    Returns the impression timestamp lists for a specific user.

    Args:
        stats: MockStatistics
        user_id: user id

    Returns:
        dict[AdId, TimestampList]: {} if user_id has not been seen
    """
    result: dict[AdId, TimestampList] = {}
    for ad_id, users in stats['user_ad_timestamps'].items():
        ts = users.get(user_id)
        if ts is not None:
            result[ad_id] = ts
    return result


def get_user_ad_show_times(
    stats: MockStatistics,
    user_id: UserId,
) -> AdShowTimes:
    """
    Returns the last impression time for each of the user's ads.

    Args:
        stats: MockStatistics
        user_id: user id

    Returns:
        AdShowTimes: {} if user_id has not been seen
    """
    user_ts = get_user_ad_timestamps(stats, user_id)
    return {ad_id: ts_list[-1] for ad_id, ts_list in user_ts.items() if ts_list}


def get_user_ad_stats(
    stats: MockStatistics,
    user_id: UserId,
    current_time: datetime | None = None,
) -> AdStats:
    """
    Computes AdStats for a user from timestamps.

    Args:
        stats: MockStatistics
        user_id: user id
        current_time: moment for window calculation; None → datetime.now()

    Returns:
        AdStats: empty AdStats if user_id is not found
    """
    if current_time is None:
        current_time = datetime.now()
    user_ts = get_user_ad_timestamps(stats, user_id)
    if not user_ts:
        return create_ad_stats({})
    result: dict = {}
    for ad_id, timestamps in user_ts.items():
        combined_counter = timestamps_to_granulated_counter(timestamps, current_time)
        result[ad_id] = create_auction_stats(combined_counter, create_granulated_counter())
    return create_ad_stats(result)


def update_user_ad_stats(
    stats: MockStatistics,
    user_id: UserId,
    ad_id: AdId,
    auction_type: AuctionTypeId,
    current_time: datetime,
) -> None:
    """
    Adds an ad impression timestamp for a user.

    Initializes the nested dicts on first access.
    Automatically trims stale timestamps.
    Mutates stats in place.

    Args:
        stats: MockStatistics
        user_id: user id
        ad_id: ad id
        auction_type: 'precise' | 'fuzzy'
        current_time: impression time
    """
    if ad_id not in stats['user_ad_timestamps']:
        stats['user_ad_timestamps'][ad_id] = {}
    if user_id not in stats['user_ad_timestamps'][ad_id]:
        stats['user_ad_timestamps'][ad_id][user_id] = []
    stats['user_ad_timestamps'][ad_id][user_id] = append_timestamp(
        stats['user_ad_timestamps'][ad_id][user_id],
        current_time,
    )


def reset_user_ad_stats_if_needed(
    stats: MockStatistics,
    user_id: UserId,
    current_time: datetime,
) -> None:
    """
    Trims stale impression timestamps for a specific user.

    Args:
        stats: MockStatistics
        user_id: user id
        current_time: current request time
    """
    cutoff = current_time - timedelta(seconds=MAX_WINDOW_SECONDS)
    for ad_id in list(stats['user_ad_timestamps'].keys()):
        users = stats['user_ad_timestamps'][ad_id]
        if user_id in users:
            users[user_id] = [t for t in users[user_id] if t > cutoff]
