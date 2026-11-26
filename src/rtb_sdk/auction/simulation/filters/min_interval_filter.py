"""
Filter of ads by the minimum interval between impressions to a user.

Checks whether enough time has passed since the last impression
of a specific ad to a specific user.
"""
from datetime import datetime, timedelta

from rtb_sdk.schemas import AdsDict, AdId, AdShowTimes
from rtb_sdk.helpers import get_ad_min_interval, get_ads_dict, create_ads_dict
from rtb_sdk.constants import DATE_ZERO


def _is_interval_passed(
    last_show_time: datetime,
    min_interval_seconds: float,
    current_time: datetime,
) -> bool:
    """
    Checks whether the minimum interval since the last impression has passed.

    Args:
        last_show_time: datetime of the last impression
        min_interval_seconds: minimum interval in seconds
        current_time: current request time

    Returns:
        bool: True if the interval has passed (or min_interval == 0)
    """
    if min_interval_seconds == 0:
        return True
    return (current_time - last_show_time).total_seconds() >= min_interval_seconds


def filter_by_min_interval(
    ads: AdsDict,
    user_ad_show_times: AdShowTimes,
    current_time: datetime,
) -> AdsDict:
    """
    Filters ads by the minimum interval between impressions.

    For each ad:
      1. Takes the last impression time from user_ad_show_times[ad_id]
      2. Checks: current_time >= last_show_time + min_interval
      3. If the interval has not passed — excludes the ad

    If the user has no statistics for the ad — it passes the filter.
    If min_interval == 0 — the ad always passes the filter.

    Args:
        ads: AdsDict of candidate ads
        user_ad_show_times: AdShowTimes — last impression times from MockStatistics
        current_time: current request time

    Returns:
        AdsDict: ads for which the interval has passed
    """
    result = {}
    for ad_id, ad in get_ads_dict(ads).items():
        min_interval = get_ad_min_interval(ad)
        last_show = user_ad_show_times.get(ad_id, DATE_ZERO)
        if _is_interval_passed(last_show, min_interval, current_time):
            result[ad_id] = ad
    return create_ads_dict(result)
