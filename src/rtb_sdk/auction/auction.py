from rtb_sdk.constants import SelectionFunc
from rtb_sdk.helpers import get_auction_func, is_valid_auction_ads_dict, is_valid_auction_params
from rtb_sdk.schemas import Ad, AdsDict, AuctionParams
from rtb_sdk.errors import AuctionError, ErrorCodes
from rtb_sdk.auction.functions.auction_one import auction_first_one, auction_random_one
from rtb_sdk.auction.functions.auction_velocity import auction_best_velocity, auction_random_velocity
from rtb_sdk.auction.functions.auction_price import auction_best_price, auction_random_price
from rtb_sdk.auction.functions.auction_heuristics import auction_best_heuristics, auction_random_heuristics
from rtb_sdk.auction.functions.auction_hybrid import auction_best_hybrid, auction_random_hybrid
from typing import Optional

AUCTIONS = {
    SelectionFunc.BEST_ONE: auction_first_one,
    SelectionFunc.RANDOM_ONE: auction_random_one,

    SelectionFunc.BEST_PRICE: auction_best_price,
    SelectionFunc.RANDOM_PRICE: auction_random_price,

    SelectionFunc.BEST_VELOCITY: auction_best_velocity,
    SelectionFunc.RANDOM_VELOCITY: auction_random_velocity,

    SelectionFunc.BEST_HEURISTICS: auction_best_heuristics,
    SelectionFunc.RANDOM_HEURISTICS: auction_random_heuristics,

    SelectionFunc.BEST_HYBRID: auction_best_hybrid,
    SelectionFunc.RANDOM_HYBRID: auction_random_hybrid,
}

def auction(ads: AdsDict,
            parameters: AuctionParams,
            ) -> Optional[Ad]:
    """Runs an auction and returns the winning ad.

    Determines the auction type from the parameters, picks the matching
    strategy from the AUCTIONS registry and delegates winner selection to it.

    Args:
        ads (AdsDict): Dictionary of candidate ads.
        parameters (AuctionParams): Auction parameters, including the selection
            strategy type and delivery statistics.

    Returns:
        Optional[Ad]: The winning ad, or None if the auction type
            is not registered in AUCTIONS.

    Raises:
        AuctionError: If ads or parameters failed validation.

    Example:
        >>> result = auction(ads_dict, params)
        >>> result is None or isinstance(result, Ad)
        True
    """
    if not is_valid_auction_ads_dict(ads):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid ads_dict: {ads!r}")
    if not is_valid_auction_params(parameters):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid parameters: {parameters!r}")
    try:
        auction = get_auction_func(parameters)
        return AUCTIONS[auction](ads, parameters)
    except KeyError:
        return None