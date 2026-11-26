from typing import Optional
from rtb_sdk.schemas import Ad, AuctionParams, AdsDict
from rtb_sdk.helpers import get_ad_from_ads, get_ads_ids, is_ads_empty, is_valid_auction_ads_dict
from rtb_sdk.errors import AuctionError, ErrorCodes
import random


def auction_first_one(ads: AdsDict,
                     parameters: AuctionParams,
                     ) -> Optional[Ad]:
    """Returns the first ad from the ads dictionary in iteration order.

    Price and priority are ignored — the winner is determined by position
    in the data structure. Deterministic auction: for identical
    input data the same ad is always chosen.

    Args:
        ads (AdsDict): Dictionary of candidate ads.
        parameters (AuctionParams): Auction parameters (unused,
            present for interface compatibility).

    Returns:
        Optional[Ad]: The first ad in iteration order, or None
            if ads is empty.

    Raises:
        AuctionError: If ads failed validation.

    Example:
        >>> ad = auction_first_one(ads_dict, params)
        >>> ad is None or isinstance(ad, Ad)
        True
    """
    if not is_valid_auction_ads_dict(ads):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid ads_dict: {ads!r}")
    if is_ads_empty(ads):
        return None
    target_ad = next(iter(get_ads_ids(ads)))
    return get_ad_from_ads(ads, target_ad)


def auction_random_one(ads: AdsDict,
                       parameters: AuctionParams,
                       ) -> Optional[Ad]:
    """Returns a random ad from the ads dictionary with a uniform distribution.

    Price and priority are ignored — all ads have the same
    probability of winning. Non-deterministic auction: for identical
    input data the result may differ.

    Args:
        ads (AdsDict): Dictionary of candidate ads.
        parameters (AuctionParams): Auction parameters (unused,
            present for interface compatibility).

    Returns:
        Optional[Ad]: A random ad, or None if ads is empty.

    Raises:
        AuctionError: If ads failed validation.

    Example:
        >>> ad = auction_random_one(ads_dict, params)
        >>> ad is None or isinstance(ad, Ad)
        True
    """
    if not is_valid_auction_ads_dict(ads):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid ads_dict: {ads!r}")
    if is_ads_empty(ads):
        return None
    rand_id = random.choice(get_ads_ids(ads))
    return get_ad_from_ads(ads, rand_id)
