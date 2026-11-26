from rtb_sdk.schemas import AuctionStats, AuctionTypeId, GranulatedCounter
from rtb_sdk.constants import AuctionType, DataAuctionType
from rtb_sdk.errors import AuctionError, ErrorCodes
from ..type_helpers import check_type
from .granulated_counter_helpers import (
    is_valid_granulated_counter,
    load_granulated_counter,
    create_granulated_counter,
)

_VALID_AUCTION_TYPES = frozenset(v for k, v in vars(AuctionType).items() if not k.startswith('_'))


def _is_valid_auction_stats_value(val) -> bool:
    if not isinstance(val, dict):
        return False
    for k, v in val.items():
        if k not in _VALID_AUCTION_TYPES:
            return False
        if not is_valid_granulated_counter(v):
            return False
    return True


def get_auction_stats_dict(stats: AuctionStats) -> dict:
    return stats.get('value', {})


def is_valid_auction_stats(val) -> bool:
    if not check_type(val, 'AuctionStats'):
        return False
    inner = get_auction_stats_dict(val)
    return _is_valid_auction_stats_value(inner)


def create_auction_stats(precise_counter: GranulatedCounter = create_granulated_counter(),
                         fuzzy_counter: GranulatedCounter = create_granulated_counter()) -> AuctionStats:
    if not is_valid_granulated_counter(precise_counter):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid precise_counter: {precise_counter!r}")
    if not is_valid_granulated_counter(fuzzy_counter):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid fuzzy_counter: {fuzzy_counter!r}")
    return {
        '__type': DataAuctionType.AUCTION_STATS,
        'value': {
            AuctionType.PRECISE: precise_counter,
            AuctionType.FUZZY: fuzzy_counter,
        },
    }  # type: ignore[return-value]


def load_auction_stats(data: dict) -> AuctionStats:
    if not check_type(data, 'AuctionStats'):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid __type for AuctionStats: {data!r}")
    inner = data.get('value', {})
    if not isinstance(inner, dict):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid AuctionStats value: {inner!r}")
    for k, v in inner.items():
        if k not in _VALID_AUCTION_TYPES:
            raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid auction type key: {k!r}")
        load_granulated_counter(v)
    return data  # type: ignore[return-value]


def get_auction_stats_by_type(stats: AuctionStats, auction_type: AuctionTypeId) -> GranulatedCounter:
    if auction_type not in _VALID_AUCTION_TYPES:
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, "Wrong auction type")
    return get_auction_stats_dict(stats).get(auction_type, create_granulated_counter())
