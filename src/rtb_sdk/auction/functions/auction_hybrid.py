from typing import Optional
from rtb_sdk.schemas import Ad, AuctionParams, AdsDict
from rtb_sdk.constants import AuctionType
from rtb_sdk.helpers import (
    get_ad_stats_from_params,
    get_price_probability,
    get_velocity_threshold,
    get_counter_value,
    get_ads_dict,
    is_ads_empty,
    is_valid_auction_ads_dict,
    get_ad_stats_by_id,
    get_auction_stats_by_type,
    merge_granulated_counters,
)
from rtb_sdk.auction.functions.auction_price import auction_best_price
from rtb_sdk.auction.functions.auction_velocity import auction_best_velocity
from rtb_sdk.auction.functions.utils import (
    get_real_month_volume,
    velocity_factor,
)
from rtb_sdk.errors import AuctionError, ErrorCodes
import random


def auction_random_hybrid(ads: AdsDict,
                          parameters: AuctionParams,
                          ) -> Optional[Ad]:
    """Randomly delegates the choice to best_price or best_velocity.

    With probability price_probability (a required field of parameters,
    range (0, 1)) the best_price strategy wins, otherwise
    best_velocity. The coin is flipped once per call —
    the randomness is at the level of strategy choice, not of an
    individual ad.

    Args:
        ads (AdsDict): Dictionary of candidate ads.
        parameters (AuctionParams): Auction parameters that must
            contain price_probability.

    Returns:
        Optional[Ad]: The winning ad, or None if ads is empty.

    Raises:
        AuctionError: If ads failed validation, or
            price_probability is missing or outside the range (0, 1).

    Example:
        >>> ad = auction_random_hybrid(ads_dict, params)
        >>> ad is None or isinstance(ad, Ad)
        True
    """
    if not is_valid_auction_ads_dict(ads):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid ads_dict: {ads!r}")
    if is_ads_empty(ads):
        return None

    price_probability = get_price_probability(parameters)
    if random.random() < price_probability:
        return auction_best_price(ads, parameters)
    return auction_best_velocity(ads, parameters)


def auction_best_hybrid(ads: AdsDict,
                        parameters: AuctionParams,
                        ) -> Optional[Ad]:
    """Deterministically delegates the choice to best_velocity or best_price.

    Ad plan fulfillment = 1 - velocity_factor (the share of the monthly
    limit already delivered). If at least one of the given ads
    has not reached the velocity_threshold (a required field of parameters)
    in plan fulfillment, the best_velocity strategy wins. If all ads
    reached the threshold, best_price is used.

    Args:
        ads (AdsDict): Dictionary of candidate ads.
        parameters (AuctionParams): Auction parameters that must
            contain velocity_threshold and delivery statistics.

    Returns:
        Optional[Ad]: The winning ad, or None if ads is empty.

    Raises:
        AuctionError: If ads failed validation, or
            velocity_threshold is missing or has an invalid type.

    Example:
        >>> ad = auction_best_hybrid(ads_dict, params)
        >>> ad is None or isinstance(ad, Ad)
        True
    """
    if not is_valid_auction_ads_dict(ads):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid ads_dict: {ads!r}")
    if is_ads_empty(ads):
        return None

    velocity_threshold = get_velocity_threshold(parameters)

    ads_value = get_ads_dict(ads)
    ads_stats = get_ad_stats_from_params(parameters)

    max_ad_month_volume_name = max(ads_value, key=lambda x: get_real_month_volume(ads_value[x]))
    max_ad_month_volume = get_real_month_volume(ads_value[max_ad_month_volume_name])

    for ad_id in ads_value:
        ad = ads_value[ad_id]

        ad_stats = get_ad_stats_by_id(ads_stats, ad_id)
        precise_stat = get_auction_stats_by_type(ad_stats, AuctionType.PRECISE)
        fuzzy_stat = get_auction_stats_by_type(ad_stats, AuctionType.FUZZY)
        combined_stat = merge_granulated_counters(precise_stat, fuzzy_stat)

        current_month_volume = get_counter_value(combined_stat, 'm')
        ad_month_volume = get_real_month_volume(ad)
        velocity = velocity_factor(current_month_volume, ad_month_volume, max_ad_month_volume)

        if 1 - velocity < velocity_threshold:
            return auction_best_velocity(ads, parameters)

    return auction_best_price(ads, parameters)
