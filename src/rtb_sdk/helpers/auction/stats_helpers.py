from rtb_sdk.schemas import (
    AuctionParams,
    AdStats,
    AuctionSelectionFunc,
    Granularity,
    ParametersAdsStats,
)
from rtb_sdk.errors import AuctionError, ErrorCodes
from rtb_sdk.constants import GranResolution, SelectionFunc, DataAuctionType
from typing import Optional, TypeAliasType, TypeGuard, get_args
from .ad_stats_helpers import is_valid_ad_stats, create_ad_stats, load_ad_stats
from ..type_helpers import check_type

_VALID_SELECTION_FUNCS = frozenset(v for k, v in vars(SelectionFunc).items() if not k.startswith('_'))


def is_valid_auction_selection_func(val) -> bool:
    return val in _VALID_SELECTION_FUNCS


def is_valid_auction_params(val) -> bool:
    if not check_type(val, 'ParametersAdsStats'):
        return False
    if not is_valid_auction_selection_func(get_auction_func(val)):
        return False
    if not is_valid_ad_stats(get_ad_stats_from_params(val)):
        return False
    return True


def create_parameters_ads_stats(
        auction_type: AuctionSelectionFunc = 'best_one',
        ads_stats: AdStats = create_ad_stats(),
        price_probability: Optional[float] = None,
        velocity_threshold: Optional[float] = None,
) -> ParametersAdsStats:
    validators: dict[str, tuple] = {
        'auction_type': (auction_type, is_valid_auction_selection_func, f"Invalid auction_type: {auction_type!r}"),
        'ads_stats':    (ads_stats,    is_valid_ad_stats,               f"Invalid ads_stats: {ads_stats!r}"),
    }
    for _field, (value, validator, error_msg) in validators.items():
        if not validator(value):
            raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, error_msg)
    if price_probability is not None and not is_valid_price_probability(price_probability):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid price_probability: {price_probability!r}")
    if velocity_threshold is not None and not is_valid_velocity_threshold(velocity_threshold):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid velocity_threshold: {velocity_threshold!r}")
    params: ParametersAdsStats = {
        '__type': DataAuctionType.PARAMETERS_ADS_STATS,
        'auction_type': auction_type,
        'ads_stats': ads_stats,
    }
    if price_probability is not None:
        params['price_probability'] = price_probability
    if velocity_threshold is not None:
        params['velocity_threshold'] = velocity_threshold
    return params


def load_parameters_ads_stats(data: dict) -> ParametersAdsStats:
    if not check_type(data, 'ParametersAdsStats'):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid __type for ParametersAdsStats: {data!r}")
    auction_type = data.get('auction_type')
    if not is_valid_auction_selection_func(auction_type):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid auction_type: {auction_type!r}")
    load_ad_stats(data.get('ads_stats', {}))
    return data  # type: ignore[return-value]


def get_actual_args(alias):
    if isinstance(alias, TypeAliasType):
        return get_args(alias.__value__)
    return get_args(alias)

def is_granularity(val: str) -> bool:
    return val in get_actual_args(Granularity.__value__)

def get_auction_func(params: AuctionParams) -> AuctionSelectionFunc:
    return params.get("auction_type", None)

def get_ad_stats_from_params(params: AuctionParams) -> AdStats:
    return params.get("ads_stats", {'__type': DataAuctionType.AD_STATS, 'value': {}})

def is_valid_price_probability(val) -> TypeGuard[float]:
    return isinstance(val, (int, float)) and not isinstance(val, bool) and 0 < val < 1

def is_valid_velocity_threshold(val) -> TypeGuard[float]:
    return isinstance(val, (int, float)) and not isinstance(val, bool)

def get_price_probability(params: AuctionParams) -> float:
    value = params.get("price_probability", None)
    if not is_valid_price_probability(value):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid price_probability: {value!r}")
    return value

def get_velocity_threshold(params: AuctionParams) -> float:
    value = params.get("velocity_threshold", None)
    if not is_valid_velocity_threshold(value):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid velocity_threshold: {value!r}")
    return value

def get_gran_resolution(from_gran: Granularity, to_gran: Granularity) -> float:
    if not (is_granularity(from_gran) or is_granularity(to_gran)):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, "Wrong data format")
    return GranResolution[from_gran][to_gran]
