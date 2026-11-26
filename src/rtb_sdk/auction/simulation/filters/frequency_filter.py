"""
Filter of ads by global frequency limits (sliding window).

Checks the impression timestamps of each ad_id against the limit
in the sliding window [current_time - window, current_time].
"""
from datetime import datetime

from rtb_sdk.schemas import AdsDict, Ad, AdId, Granularity, TimestampList
from rtb_sdk.helpers import (
    get_ad_frequency_limit,
    get_frequency_limit_by_gran,
    get_ads_dict,
    create_ads_dict,
)
from rtb_sdk.constants import Gran
from rtb_sdk.auction.simulation.statistics.counter import is_over_limit, GRAN_SECONDS


_GRANS: list[Granularity] = [Gran.TEN_MINUTES, Gran.HOUR, Gran.DAY, Gran.WEEK, Gran.MONTH]


def _is_within_frequency_limit(
    timestamps: TimestampList,
    ad: Ad,
    current_time: datetime,
) -> bool:
    """
    Checks whether the ad's global frequency limit has been exceeded.

    A limit value of 0 or -1 is treated as "no limit".

    Args:
        timestamps: list of impression timestamps (sorted, oldest first)
        ad: the ad (ad_frequency_limit is taken from it)
        current_time: current request time

    Returns:
        bool: True if the limit is not exceeded for any granularity
    """
    limits = get_ad_frequency_limit(ad)
    for gran in _GRANS:
        limit = get_frequency_limit_by_gran(limits, gran)
        if limit <= 0:
            continue
        if is_over_limit(timestamps, int(limit), GRAN_SECONDS[gran], current_time):
            return False
    return True


def filter_by_ad_frequency(
    ads: AdsDict,
    ad_timestamps: dict[AdId, TimestampList],
    current_time: datetime,
) -> AdsDict:
    """
    Filters ads by global frequency limits (sliding window).

    For each ad:
      1. Takes the list of impression timestamps (all auction_type merged)
      2. For each granularity checks whether the limit is already reached
         in the sliding window (a value of -1 or 0 in the limit = no limit)
      3. If the limit is exceeded for at least one granularity — excludes

    Args:
        ads: AdsDict of candidate ads
        ad_timestamps: {ad_id → list[datetime]}
                       from get_ad_timestamps(driver)
        current_time: current request time

    Returns:
        AdsDict: ads that did not exceed the frequency limit
    """
    result = {}
    for ad_id, ad in get_ads_dict(ads).items():
        timestamps = ad_timestamps.get(ad_id, [])
        if _is_within_frequency_limit(timestamps, ad, current_time):
            result[ad_id] = ad
    return create_ads_dict(result)
