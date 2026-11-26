"""
Filter of off-target (fuzzy-targeting) traffic.

Applied before fuzzy matching. Limits the share of off-target impressions
by checking the total number of FUZZY impressions (ad_total_counts) against
the ad's parasitic_freq_limit.

Two modes:
  - absolute: compares the FUZZY counter with parasitic_freq_limit directly
  - percentage: fuzzy_targeting_limit = floor(ad_freq_limit * percent)
"""
import math

from rtb_sdk.schemas import AdsDict, Ad, AdId, AuctionTypeId
from rtb_sdk.helpers import (
    get_ad_frequency_limit,
    get_frequency_limit_by_gran,
    get_ads_dict,
    create_ads_dict,
)
from rtb_sdk.constants import AuctionType, Gran


def _get_fuzzy_count(
    ad_id: AdId,
    ad_total_counts: dict[AdId, dict[AuctionTypeId, int]],
) -> int:
    """
    Returns the total number of FUZZY impressions of the ad.

    Args:
        ad_id: ad id
        ad_total_counts: {ad_id → {auction_type → int}}

    Returns:
        int: number of FUZZY impressions; 0 if absent
    """
    return ad_total_counts.get(ad_id, {}).get(AuctionType.FUZZY, 0)


def _is_within_fuzzy_targeting_limit(
    fuzzy_count: int,
    ad: Ad,
) -> bool:
    """
    Checks whether the absolute parasitic_freq_limit has been exceeded.

    Uses the monthly limit (m) as a total threshold for all time.
    A limit value of 0 or -1 is treated as "no limit".

    Args:
        fuzzy_count: total number of FUZZY impressions of the ad
        ad: the ad (parasitic_freq_limit is taken from it)

    Returns:
        bool: True if the limit is not exceeded
    """
    limits = ad.get('parasitic_freq_limit')
    if limits is None:
        return True
    limit = get_frequency_limit_by_gran(limits, Gran.MONTH)
    if limit <= 0:
        return True
    return fuzzy_count < limit


def _is_within_fuzzy_targeting_percent_limit(
    fuzzy_count: int,
    total_count: int,
    ad: Ad,
    percent: float = 0.1,
) -> bool:
    """
    Checks the percentage fuzzy-targeting limit.

    Computes: fuzzy_targeting_limit = floor(ad_frequency_limit[m] * percent)
    Compares fuzzy_count with this limit.

    Args:
        fuzzy_count: total number of FUZZY impressions
        total_count: total number of all impressions
        ad: the ad (ad_frequency_limit is taken to compute the percentage limit)
        percent: percentage of the total limit (default 10%)

    Returns:
        bool: True if the percentage limit is not exceeded
    """
    ad_limits = get_ad_frequency_limit(ad)
    ad_limit = get_frequency_limit_by_gran(ad_limits, Gran.MONTH)
    if ad_limit <= 0:
        return True
    fuzzy_targeting_limit = math.floor(ad_limit * percent)
    return fuzzy_count < fuzzy_targeting_limit


def filter_by_fuzzy_targeting_frequency(
    ads: AdsDict,
    ad_total_counts: dict[AdId, dict[AuctionTypeId, int]],
) -> AdsDict:
    """
    Filters ads by the absolute parasitic_freq_limit.

    Checks the total FUZZY impressions (ad_total_counts) against
    the monthly limit from parasitic_freq_limit.

    Args:
        ads: AdsDict of candidate ads
        ad_total_counts: {ad_id → {auction_type → int}}
                         from get_ad_total_counts(driver)

    Returns:
        AdsDict: ads that did not exceed the fuzzy-targeting limit
    """
    result = {}
    for ad_id, ad in get_ads_dict(ads).items():
        fuzzy_count = _get_fuzzy_count(ad_id, ad_total_counts)
        if _is_within_fuzzy_targeting_limit(fuzzy_count, ad):
            result[ad_id] = ad
    return create_ads_dict(result)


def filter_by_fuzzy_targeting_percent_frequency(
    ads: AdsDict,
    ad_total_counts: dict[AdId, dict[AuctionTypeId, int]],
    percent: float = 0.1,
) -> AdsDict:
    """
    Filters ads by the percentage fuzzy-targeting limit.

    Used as an alternative to filter_by_fuzzy_targeting_frequency when
    the ad has no explicit parasitic_freq_limit.

    Args:
        ads: AdsDict of candidate ads
        ad_total_counts: {ad_id → {auction_type → int}}
        percent: share of ad_frequency_limit (default 10%)

    Returns:
        AdsDict: ads that did not exceed the percentage fuzzy-targeting limit
    """
    result = {}
    for ad_id, ad in get_ads_dict(ads).items():
        fuzzy_count = _get_fuzzy_count(ad_id, ad_total_counts)
        total_count = sum(ad_total_counts.get(ad_id, {}).values())
        if _is_within_fuzzy_targeting_percent_limit(fuzzy_count, total_count, ad, percent):
            result[ad_id] = ad
    return create_ads_dict(result)
