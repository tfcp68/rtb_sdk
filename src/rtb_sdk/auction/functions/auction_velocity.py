import random
from typing import Optional
from rtb_sdk.schemas import Ad, AuctionParams, AdsDict
from rtb_sdk.helpers import (
    get_ad_stats_from_params,
    get_counter_value,
    get_ads_dict,
    get_ad_from_ads,
    is_ads_empty,
    is_valid_auction_ads_dict,
    get_ad_stats_by_id,
    get_auction_stats_by_type,
    merge_granulated_counters,
)
from rtb_sdk.auction.functions.utils import (
    get_real_month_volume,
    velocity_factor,
)
from rtb_sdk.constants import AuctionType
from rtb_sdk.errors import AuctionError, ErrorCodes


def auction_random_velocity(ads: AdsDict,
                            parameters: AuctionParams,
                            ) -> Optional[Ad]:
    """Returns a random ad with probability proportional to velocity_factor.

    velocity_factor reflects how "under-delivered" an ad is
    relative to its monthly limit: the less of the limit has been
    used, the higher the factor and the probability of winning. Delivery
    statistics are taken from parameters; the PRECISE and FUZZY counters
    are merged before the calculation.

    Args:
        ads (AdsDict): Dictionary of candidate ads.
        parameters (AuctionParams): Auction parameters with ad delivery
            statistics.

    Returns:
        Optional[Ad]: The randomly chosen ad, or None
            if ads is empty.

    Raises:
        AuctionError: If ads failed validation.

    Example:
        >>> ad = auction_random_velocity(ads_dict, params)
        >>> ad is None or isinstance(ad, Ad)
        True
    """
    if not is_valid_auction_ads_dict(ads):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid ads_dict: {ads!r}")
    if is_ads_empty(ads):
        return None

    ads_value = get_ads_dict(ads)
    ads_stats = get_ad_stats_from_params(parameters)

    max_ad_month_volume_name = max(ads_value, key=lambda x: get_real_month_volume(ads_value[x]))
    max_ad_month_volume = get_real_month_volume(ads_value[max_ad_month_volume_name])

    ads_velocity = {}
    for ad_id in ads_value:
        ad = ads_value[ad_id]

        ad_stats = get_ad_stats_by_id(ads_stats, ad_id)
        precise_stat = get_auction_stats_by_type(ad_stats, AuctionType.PRECISE)
        fuzzy_stat = get_auction_stats_by_type(ad_stats, AuctionType.FUZZY)
        combined_stat = merge_granulated_counters(precise_stat, fuzzy_stat)

        current_month_volume = get_counter_value(combined_stat, 'm')
        ad_month_volume = get_real_month_volume(ad)
        ads_velocity[ad_id] = velocity_factor(current_month_volume, ad_month_volume, max_ad_month_volume)

    elements = list(ads_velocity.keys())
    weights = [w + 1e-9 for w in ads_velocity.values()]
    return get_ad_from_ads(ads, random.choices(elements, weights=weights, k=1)[0])


def auction_best_velocity(ads: AdsDict,
                          parameters: AuctionParams,
                          ) -> Optional[Ad]:
    """Returns the ad with the maximum velocity_factor.

    velocity_factor reflects how "under-delivered" an ad is
    relative to its monthly limit: the ad with the largest
    remaining part of the limit wins. Deterministic auction. Delivery
    statistics are taken from parameters; the PRECISE and FUZZY counters
    are merged before the calculation.

    Args:
        ads (AdsDict): Dictionary of candidate ads.
        parameters (AuctionParams): Auction parameters with ad delivery
            statistics.

    Returns:
        Optional[Ad]: The ad with the maximum velocity_factor, or None
            if ads is empty.

    Raises:
        AuctionError: If ads failed validation.

    Example:
        >>> ad = auction_best_velocity(ads_dict, params)
        >>> ad is None or isinstance(ad, Ad)
        True
    """
    if not is_valid_auction_ads_dict(ads):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid ads_dict: {ads!r}")
    if is_ads_empty(ads):
        return None

    ads_value = get_ads_dict(ads)
    ads_stats = get_ad_stats_from_params(parameters)

    max_ad_month_volume_name = max(ads_value, key=lambda x: get_real_month_volume(ads_value[x]))
    max_ad_month_volume = get_real_month_volume(ads_value[max_ad_month_volume_name])

    ads_velocity = {}
    for ad_id in ads_value:
        ad = ads_value[ad_id]

        ad_stats = get_ad_stats_by_id(ads_stats, ad_id)
        precise_stat = get_auction_stats_by_type(ad_stats, AuctionType.PRECISE)
        fuzzy_stat = get_auction_stats_by_type(ad_stats, AuctionType.FUZZY)
        combined_stat = merge_granulated_counters(precise_stat, fuzzy_stat)

        current_month_volume = get_counter_value(combined_stat, 'm')
        ad_month_volume = get_real_month_volume(ad)
        ads_velocity[ad_id] = velocity_factor(current_month_volume, ad_month_volume, max_ad_month_volume)

    return get_ad_from_ads(ads, max(ads_velocity.items(), key=lambda x: x[1])[0])
