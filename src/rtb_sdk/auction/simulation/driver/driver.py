"""
MockDriver — the main store of simulation state.

Holds the ads, tag dictionaries and impression statistics.
Provides a single interface for reading data and updating statistics
during the simulation loop.
"""
from typing import TypedDict
from datetime import datetime

from rtb_sdk.schemas import AdsDict, AdStats, AdId, AdShowTimes, AuctionTypeId, Request, TargetVector, TimestampList, UserId
from rtb_sdk.helpers import get_request_user_id, get_request_date

from rtb_sdk.auction.simulation.statistics.mock_statistics import (
    MockStatistics,
    AdTimestamps,
    AdTotalCounts,
)
import rtb_sdk.auction.simulation.statistics.mock_statistics as mock_statistics


class MockDriver(TypedDict):
    ads: AdsDict
    vocabs: TargetVector
    stats: MockStatistics


# ── data access ────────────────────────────────────────────────────────────────

def get_ads(driver: MockDriver) -> AdsDict:
    """
    Returns all ads from the driver.

    Returns:
        AdsDict
    """
    return driver['ads']


def get_vocabs(driver: MockDriver) -> TargetVector:
    """
    Returns the tag dictionaries from the driver.

    Returns:
        TargetVector
    """
    return driver['vocabs']


# ── stats access ───────────────────────────────────────────────────────────────

def get_ad_timestamps(
    driver: MockDriver,
    ad_ids: list[AdId] | None = None,
) -> AdTimestamps:
    """
    Returns the lists of ad impression timestamps.

    Used by the frequency limit filters
    (filter_by_ad_frequency, filter_by_fuzzy_targeting_frequency).

    Args:
        driver: MockDriver
        ad_ids: list of ad ids; None → all ads from stats

    Returns:
        AdTimestamps: {ad_id → list[datetime]}
    """
    return mock_statistics.get_ad_timestamps(driver['stats'], ad_ids)


def get_ad_total_counts(
    driver: MockDriver,
    ad_ids: list[AdId] | None = None,
) -> AdTotalCounts:
    """
    Returns the total impression counters for the whole simulation time.

    Used by the report and the fuzzy-targeting filter to count fuzzy impressions.

    Args:
        driver: MockDriver
        ad_ids: list of ad ids; None → all from stats

    Returns:
        AdTotalCounts: {ad_id → {auction_type → int}}
    """
    counts = driver['stats']['ad_total_counts']
    if ad_ids is None:
        return counts
    return {ad_id: counts.get(ad_id, {}) for ad_id in ad_ids}


def get_ad_stats(
    driver: MockDriver,
    ad_ids: list[AdId] | None = None,
    current_time: datetime | None = None,
) -> AdStats:
    """
    Computes AdStats from timestamp lists for the auction strategies.

    For each granularity counts impressions in the sliding window.
    Used to pass into the auction (best_velocity, best_price, etc.).

    Args:
        driver: MockDriver
        ad_ids: list of ad ids; None → all from stats
        current_time: moment for window calculation; None → datetime.now()

    Returns:
        AdStats
    """
    return mock_statistics.get_ad_stats(driver['stats'], ad_ids, current_time)


def get_ad_show_times(
    driver: MockDriver,
    ad_ids: list[AdId] | None = None,
) -> AdShowTimes:
    """
    Returns the last impression time for each ad.

    Delegates to mock_statistics.get_ad_show_times.

    Args:
        driver: MockDriver
        ad_ids: list of ad ids; None → all from stats

    Returns:
        AdShowTimes
    """
    return mock_statistics.get_ad_show_times(driver['stats'], ad_ids)


def get_user_ad_timestamps(
    driver: MockDriver,
    user_id: UserId,
) -> dict[AdId, TimestampList]:
    """
    Returns the impression timestamp lists for a specific user.

    Used by the user frequency limit filter
    (filter_by_user_frequency).

    Args:
        driver: MockDriver
        user_id: user id

    Returns:
        dict[AdId, TimestampList]: {} if not found
    """
    return mock_statistics.get_user_ad_timestamps(driver['stats'], user_id)


def get_user_ad_stats(
    driver: MockDriver,
    user_id: UserId,
    current_time: datetime | None = None,
) -> AdStats:
    """
    Computes the user's AdStats from timestamp lists.

    Args:
        driver: MockDriver
        user_id: user id
        current_time: moment for window calculation; None → datetime.now()

    Returns:
        AdStats: empty AdStats if not found
    """
    return mock_statistics.get_user_ad_stats(driver['stats'], user_id, current_time)


def get_user_ad_show_times(
    driver: MockDriver,
    user_id: UserId,
) -> AdShowTimes:
    """
    Returns the last impression times for a specific user.

    Used by filter_by_min_interval.

    Args:
        driver: MockDriver
        user_id: user id

    Returns:
        AdShowTimes: {} if not found
    """
    return mock_statistics.get_user_ad_show_times(driver['stats'], user_id)


# ── stats mutation ─────────────────────────────────────────────────────────────

def update_statistics(
    driver: MockDriver,
    request: Request,
    auction_type: AuctionTypeId,
    ad_id: AdId | None,
) -> None:
    """
    Updates statistics after an auction result.

    Called:
      - on HIT (ad_id is not None): adds a timestamp to ad_timestamps
        and user_ad_timestamps, increments ad_total_counts
      - on MISS (ad_id is None): updates nothing

    Uses get_request_user_id and get_request_date from the request.

    Args:
        driver: MockDriver
        request: current request
        auction_type: 'precise' | 'fuzzy'
        ad_id: id of the winning ad, or None on MISS
    """
    if ad_id is not None:
        user_id = get_request_user_id(request)
        current_time = get_request_date(request)
        mock_statistics.update_ad_stats(driver['stats'], ad_id, auction_type, current_time)
        mock_statistics.update_user_ad_stats(driver['stats'], user_id, ad_id, auction_type, current_time)


def reset_statistics_if_needed(
    driver: MockDriver,
    request: Request,
) -> None:
    """
    Trims stale timestamps at the start of request processing.

    Removes records older than MAX_WINDOW_SECONDS from ad_timestamps
    and from the current user's user_ad_timestamps.

    Args:
        driver: MockDriver
        request: current request (user_id and date are taken from it)
    """
    user_id = get_request_user_id(request)
    current_time = get_request_date(request)
    mock_statistics.reset_ad_stats_if_needed(driver['stats'], current_time)
    mock_statistics.reset_user_ad_stats_if_needed(driver['stats'], user_id, current_time)
