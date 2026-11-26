"""
Filter of ads by user frequency limits (sliding window).

Checks the impression timestamps for a (user_id, ad_id) pair against the limit
in the sliding window [current_time - window, current_time].
"""
from datetime import datetime

from rtb_sdk.schemas import AdsDict, Ad, AdId, Granularity, TimestampList
from rtb_sdk.helpers import (
    get_frequency_limit_by_gran,
    get_ads_dict,
    create_ads_dict,
)
from rtb_sdk.constants import Gran
from rtb_sdk.auction.simulation.statistics.counter import is_over_limit, GRAN_SECONDS


_GRANS: list[Granularity] = [Gran.TEN_MINUTES, Gran.HOUR, Gran.DAY, Gran.WEEK, Gran.MONTH]


def _is_within_user_frequency_limit(
    timestamps: list[datetime],
    ad: Ad,
    current_time: datetime,
) -> bool:
    """
    Checks whether the user limit for the given ad has been exceeded.

    A limit value of 0 or -1 is treated as "no limit".

    Args:
        timestamps: list of impression timestamps (sorted, oldest first)
        ad: the ad (user_frequency_limit is taken from it)
        current_time: current request time

    Returns:
        bool: True if the limit is not exceeded
    """
    limits = ad.get('user_frequency_limit')
    if limits is None:
        return True
    for gran in _GRANS:
        limit = get_frequency_limit_by_gran(limits, gran)
        if limit <= 0:
            continue
        if is_over_limit(timestamps, int(limit), GRAN_SECONDS[gran], current_time):
            return False
    return True


def filter_by_user_frequency(
    ads: AdsDict,
    user_ad_timestamps: dict[AdId, TimestampList],
    current_time: datetime,
) -> AdsDict:
    """
    Filters ads by user frequency limits (sliding window).

    For each ad:
      1. Takes the list of the user's impression timestamps for the given ad
      2. Checks against the sliding window: whether user_frequency_limit is exceeded
      3. If the user has no history for the ad — it passes the filter

    Args:
        ads: AdsDict of candidate ads
        user_ad_timestamps: {ad_id → list[datetime]}
                            from get_user_ad_timestamps(driver, user_id)
        current_time: current request time

    Returns:
        AdsDict: ads that did not exceed the user limit
    """
    result = {}
    for ad_id, ad in get_ads_dict(ads).items():
        timestamps = user_ad_timestamps.get(ad_id, [])
        if _is_within_user_frequency_limit(timestamps, ad, current_time):
            result[ad_id] = ad
    return create_ads_dict(result)
