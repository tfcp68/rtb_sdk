from typing import Optional
from rtb_sdk.schemas import Ad, AuctionParams, AdsDict
from rtb_sdk.constants import AuctionType
from rtb_sdk.helpers import (
    get_ad_stats_from_params,
    get_ad_price,
    get_ad_priority,
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
    price_factor,
    priority_factor,
    heuristic_function_simplest,
)
from rtb_sdk.errors import AuctionError, ErrorCodes
import random


def auction_best_heuristics(ads: AdsDict,
                            parameters: AuctionParams,
                            ) -> Optional[Ad]:
    """Returns the ad with the maximum heuristic function value.

    The heuristic combines three normalized factors: priority, price and
    velocity (limit under-delivery). The final score is computed as
    priority_factor * price_factor * velocity_factor. Deterministic
    auction: the ad with the largest product of factors wins.

    Args:
        ads (AdsDict): Dictionary of candidate ads.
        parameters (AuctionParams): Auction parameters with ad delivery
            statistics.

    Returns:
        Optional[Ad]: The ad with the maximum heuristic score, or
            None if ads is empty.

    Raises:
        AuctionError: If ads failed validation or on division by
            zero in the factor functions.

    Example:
        >>> ad = auction_best_heuristics(ads_dict, params)
        >>> ad is None or isinstance(ad, Ad)
        True
    """
    if not is_valid_auction_ads_dict(ads):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid ads_dict: {ads!r}")
    if is_ads_empty(ads):
        return None

    ads_value = get_ads_dict(ads)
    ads_stats = get_ad_stats_from_params(parameters)

    # get the maximum values

    # price
    max_ad_price_name = max(ads_value, key=lambda x: get_ad_price(ads_value[x]))
    max_ad_price = get_ad_price(ads_value[max_ad_price_name])

    # priority
    max_ad_priority_name = max(ads_value, key=lambda x: get_ad_priority(ads_value[x]))
    max_ad_priority = get_ad_priority(ads_value[max_ad_priority_name])

    # delivery speed
    max_ad_month_volume_name = max(ads_value, key=lambda x: get_real_month_volume(ads_value[x]))
    max_ad_month_volume = get_real_month_volume(ads_value[max_ad_month_volume_name])

    ad_heurs = {}
    for ad_id in ads_value:
        ad = ads_value[ad_id]

        # price factor
        price_f = price_factor(get_ad_price(ad), max_ad_price)

        # priority factor
        priority_f = priority_factor(get_ad_priority(ad), max_ad_priority)

        # delivery speed factor
        ad_stats = get_ad_stats_by_id(ads_stats, ad_id)
        precise_stat = get_auction_stats_by_type(ad_stats, AuctionType.PRECISE)
        fuzzy_stat = get_auction_stats_by_type(ad_stats, AuctionType.FUZZY)
        combined_stat = merge_granulated_counters(precise_stat, fuzzy_stat)

        current_month_volume = get_counter_value(combined_stat, 'm')
        month_limit = get_real_month_volume(ad)
        velocity_f = velocity_factor(current_month_volume, month_limit, max_ad_month_volume)

        ad_heurs[ad_id] = heuristic_function_simplest(priority_f, price_f, velocity_f)

    return get_ad_from_ads(ads, max(ad_heurs.items(), key=lambda x: x[1])[0])


def auction_random_heuristics(ads: AdsDict,
                              parameters: AuctionParams,
                              ) -> Optional[Ad]:
    """Returns a random ad with probability proportional to the heuristic function.

    The heuristic combines three normalized factors: priority, price and
    velocity (limit under-delivery). The final weight is computed as
    priority_factor * price_factor * velocity_factor. Ads with a
    high score win more often, but not guaranteed. A small constant 1e-9
    is added to each weight to rule out zero probability.

    Args:
        ads (AdsDict): Dictionary of candidate ads.
        parameters (AuctionParams): Auction parameters with ad delivery
            statistics.

    Returns:
        Optional[Ad]: The randomly chosen ad, or None
            if ads is empty.

    Raises:
        AuctionError: If ads failed validation or on division by
            zero in the factor functions.

    Example:
        >>> ad = auction_random_heuristics(ads_dict, params)
        >>> ad is None or isinstance(ad, Ad)
        True
    """
    if not is_valid_auction_ads_dict(ads):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid ads_dict: {ads!r}")
    if is_ads_empty(ads):
        return None

    ads_value = get_ads_dict(ads)
    ads_stats = get_ad_stats_from_params(parameters)

    # get the maximum values

    # price
    max_ad_price_name = max(ads_value, key=lambda x: get_ad_price(ads_value[x]))
    max_ad_price = get_ad_price(ads_value[max_ad_price_name])

    # priority
    max_ad_priority_name = max(ads_value, key=lambda x: get_ad_priority(ads_value[x]))
    max_ad_priority = get_ad_priority(ads_value[max_ad_priority_name])

    # delivery speed
    max_ad_month_volume_name = max(ads_value, key=lambda x: get_real_month_volume(ads_value[x]))
    max_ad_month_volume = get_real_month_volume(ads_value[max_ad_month_volume_name])

    ad_heurs = {}
    for ad_id in ads_value:
        ad = ads_value[ad_id]

        # price factor
        price_f = price_factor(get_ad_price(ad), max_ad_price)

        # priority factor
        priority_f = priority_factor(get_ad_priority(ad), max_ad_priority)

        # delivery speed factor
        ad_stats = get_ad_stats_by_id(ads_stats, ad_id)
        precise_stat = get_auction_stats_by_type(ad_stats, AuctionType.PRECISE)
        fuzzy_stat = get_auction_stats_by_type(ad_stats, AuctionType.FUZZY)
        combined_stat = merge_granulated_counters(precise_stat, fuzzy_stat)

        current_month_volume = get_counter_value(combined_stat, 'm')
        month_limit = get_real_month_volume(ad)
        velocity_f = velocity_factor(current_month_volume, month_limit, max_ad_month_volume)

        ad_heurs[ad_id] = heuristic_function_simplest(priority_f, price_f, velocity_f)

    elements = list(ad_heurs.keys())
    weights = [w + 1e-9 for w in ad_heurs.values()]
    return get_ad_from_ads(ads, random.choices(elements, weights=weights, k=1)[0])
