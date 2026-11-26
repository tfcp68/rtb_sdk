from typing import Optional
from rtb_sdk.schemas import Ad, AuctionParams, AdsDict
from rtb_sdk.helpers import get_ad_price, get_ads_dict, get_ad_from_ads, is_ads_empty, is_valid_auction_ads_dict
from rtb_sdk.errors import AuctionError, ErrorCodes
import random


def auction_best_price(ads: AdsDict,
                       parameters: AuctionParams,
                       ) -> Optional[Ad]:
    """Returns the ad with the maximum price among all candidates.

    Deterministic auction: whoever paid more always wins.
    On equal prices the winner is determined by the dictionary
    iteration order.

    Args:
        ads (AdsDict): Dictionary of candidate ads.
        parameters (AuctionParams): Auction parameters (unused,
            present for interface compatibility).

    Returns:
        Optional[Ad]: The ad with the maximum price, or None
            if ads is empty.

    Raises:
        AuctionError: If ads failed validation.

    Example:
        >>> ad = auction_best_price(ads_dict, params)
        >>> ad is None or isinstance(ad, Ad)
        True
    """
    if not is_valid_auction_ads_dict(ads):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid ads_dict: {ads!r}")
    if is_ads_empty(ads):
        return None

    ads_value = get_ads_dict(ads)
    max_ad = max(ads_value, key=lambda ad_id: get_ad_price(ads_value[ad_id]))
    return get_ad_from_ads(ads, max_ad)


def auction_random_price(ads: AdsDict,
                         parameters: AuctionParams,
                         ) -> Optional[Ad]:
    """Returns a random ad with probability proportional to price.

    Weights are normalized by the maximum price using the formula
    weight = price / max_price. The ad with the maximum price
    gets weight=1.0, the others get less. A small constant 1e-9
    is added to each weight to rule out zero probability.

    Args:
        ads (AdsDict): Dictionary of candidate ads.
        parameters (AuctionParams): Auction parameters (unused,
            present for interface compatibility).

    Returns:
        Optional[Ad]: The randomly chosen ad, or None
            if ads is empty.

    Raises:
        AuctionError: If ads failed validation.

    Example:
        >>> ad = auction_random_price(ads_dict, params)
        >>> ad is None or isinstance(ad, Ad)
        True
    """
    if not is_valid_auction_ads_dict(ads):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid ads_dict: {ads!r}")
    if is_ads_empty(ads):
        return None

    _EPS = 1e-9
    ads_value = get_ads_dict(ads)
    ads_prices = {ad_id: get_ad_price(ads_value[ad_id]) + _EPS for ad_id in ads_value}
    max_price = max(ads_prices.values())
    ads_probability = {ad_id: ads_prices[ad_id] / max_price for ad_id in ads_value}

    ad_ids = list(ads_probability.keys())
    ad_weights = list(ads_probability.values())
    best_ad_id = random.choices(ad_ids, ad_weights, k=1)
    return get_ad_from_ads(ads, best_ad_id[0])
