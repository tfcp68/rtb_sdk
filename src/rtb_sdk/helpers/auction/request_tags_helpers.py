from rtb_sdk.schemas import RequestTags, VocabName, FullTag
from rtb_sdk.constants import DataAuctionType
from rtb_sdk.errors import AuctionError, ErrorCodes
from ..type_helpers import check_type


def _is_valid_request_tags_value(val) -> bool:
    if not isinstance(val, dict):
        return False
    for k, v in val.items():
        if not isinstance(k, str):
            return False
        if not isinstance(v, str):
            return False
    return True


def is_valid_request_tags(val) -> bool:
    if not check_type(val, 'RequestTags'):
        return False
    inner = get_request_tags_dict(val)
    return _is_valid_request_tags_value(inner)


def create_request_tags(value: dict[VocabName, FullTag] = {}) -> RequestTags:
    if not _is_valid_request_tags_value(value):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid value: {value!r}")
    return {'__type': DataAuctionType.REQUEST_TAGS, 'value': value}  # type: ignore[return-value]


def load_request_tags(data: dict) -> RequestTags:
    if not check_type(data, 'RequestTags'):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid __type for RequestTags: {data!r}")
    inner = data.get('value', {})
    if not _is_valid_request_tags_value(inner):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid RequestTags value: {inner!r}")
    return data  # type: ignore[return-value]


def get_request_tags_dict(tags: RequestTags) -> dict:
    return tags.get('value', {})
