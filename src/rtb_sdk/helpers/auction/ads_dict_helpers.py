from typing import Optional
from rtb_sdk.schemas import AdsDict, Ad, AdId
from rtb_sdk.constants import DataAuctionType
from rtb_sdk.errors import AuctionError, ErrorCodes
from ..type_helpers import check_type
from .ad_helpers import (
    is_valid_ad_id,
    is_valid_cpm,
    is_valid_priority,
    is_valid_volume,
    is_valid_start_date,
    is_valid_end_date,
    get_ad_id,
    get_ad_price,
    get_ad_priority,
    get_ad_volume,
    get_ad_frequency_limit,
    get_ad_start_date,
    get_ad_end_date,
    load_ad,
)
from .frequency_limits_helpers import is_valid_frequency_limits


def create_ads_dict(value: dict[AdId, Ad] = {}) -> AdsDict:
    if not isinstance(value, dict):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid value: {value!r}")
    for k, v in value.items():
        if not isinstance(k, str):
            raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid ad id key: {k!r}")
        if not check_type(v, 'Ad'):
            raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid Ad entry: {v!r}")
    return {'__type': DataAuctionType.ADS_DICT, 'value': value}


def load_ads_dict(data: dict) -> AdsDict:
    if not check_type(data, 'AdsDict'):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid __type for AdsDict: {data!r}")
    inner = data.get('value', {})
    if not isinstance(inner, dict):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid AdsDict value: {inner!r}")
    for k, v in inner.items():
        if not isinstance(k, str):
            raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid ad id key: {k!r}")
        load_ad(v)
    return data  # type: ignore[return-value]


def get_ads_dict(ads: AdsDict) -> dict[AdId, Ad]:
    return ads.get('value', {})

def get_ads_ids(ads: AdsDict) -> list[AdId]:
    return list(get_ads_dict(ads).keys())

def get_ad_from_ads(ads: AdsDict, ad_id: AdId) -> Optional[Ad]:
    return get_ads_dict(ads).get(ad_id)

def get_ads_list(ads: AdsDict) -> list[Ad]:
    return list(get_ads_dict(ads).values())

def is_ads_empty(ads: AdsDict) -> bool:
    return not get_ads_dict(ads)

def is_valid_ads_dict(val) -> bool:
    if not check_type(val, 'AdsDict'):
        return False
    inner = get_ads_dict(val)
    if not isinstance(inner, dict):
        return False
    return True


def _is_valid_auction_ad(ad) -> bool:
    if not check_type(ad, 'Ad'):
        return False
    if not is_valid_ad_id(get_ad_id(ad)):
        return False
    cpm = get_ad_price(ad)
    if not is_valid_cpm(cpm) or cpm < 0:
        return False
    priority = get_ad_priority(ad)
    if not is_valid_priority(priority) or priority < 0:
        return False
    volume = get_ad_volume(ad)
    if not is_valid_volume(volume) or volume < 0:
        return False
    if not is_valid_frequency_limits(get_ad_frequency_limit(ad)):
        return False
    if not is_valid_start_date(get_ad_start_date(ad)):
        return False
    if not is_valid_end_date(get_ad_end_date(ad)):
        return False
    return True


def is_valid_auction_ads_dict(val) -> bool:
    if not is_valid_ads_dict(val):
        return False
    for ad in get_ads_list(val):
        if not _is_valid_auction_ad(ad):
            return False
    return True
