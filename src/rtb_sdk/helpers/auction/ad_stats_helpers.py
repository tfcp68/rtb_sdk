from rtb_sdk.schemas import AdStats, AuctionStats, AdId
from rtb_sdk.constants import DataAuctionType
from rtb_sdk.errors import AuctionError, ErrorCodes
from ..type_helpers import check_type
from .auction_stats_helpers import is_valid_auction_stats, load_auction_stats, create_auction_stats


def _is_valid_ad_stats_value(val) -> bool:
    if not isinstance(val, dict):
        return False
    for k, v in val.items():
        if not isinstance(k, str):
            return False
        if not is_valid_auction_stats(v):
            return False
    return True


def get_ad_stats_dict(stats: AdStats) -> dict:
    return stats.get('value', {})


def is_valid_ad_stats(val) -> bool:
    if not check_type(val, 'AdStats'):
        return False
    inner = get_ad_stats_dict(val)
    return _is_valid_ad_stats_value(inner)


def create_ad_stats(value: dict[AdId, AuctionStats] = {}) -> AdStats:
    if not _is_valid_ad_stats_value(value):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid value: {value!r}")
    return {'__type': DataAuctionType.AD_STATS, 'value': value}  # type: ignore[return-value]


def load_ad_stats(data: dict) -> AdStats:
    if not check_type(data, 'AdStats'):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid __type for AdStats: {data!r}")
    inner = data.get('value', {})
    if not isinstance(inner, dict):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid AdStats value: {inner!r}")
    for k, v in inner.items():
        if not isinstance(k, str):
            raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid AdStats key: {k!r}")
        load_auction_stats(v)
    return data  # type: ignore[return-value]


def get_ad_stats_by_id(stats: AdStats, ad_id: AdId) -> AuctionStats:
    return get_ad_stats_dict(stats).get(ad_id, create_auction_stats())
