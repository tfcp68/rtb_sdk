from rtb_sdk.schemas import FullTagVector, VocabName, FullTag
from rtb_sdk.constants import DataAuctionType
from rtb_sdk.errors import AuctionError, ErrorCodes
from ..type_helpers import check_type


def _is_valid_full_tag_vector_value(val) -> bool:
    if not isinstance(val, dict):
        return False
    for k, v in val.items():
        if not isinstance(k, str):
            return False
        if not isinstance(v, list):
            return False
        if not all(isinstance(tag, str) for tag in v):
            return False
    return True


def get_full_tag_vector_dict(ftv: FullTagVector) -> dict:
    return ftv.get('value', {})


def is_valid_full_tag_vector(val) -> bool:
    if not check_type(val, 'FullTagVector'):
        return False
    inner = get_full_tag_vector_dict(val)
    return _is_valid_full_tag_vector_value(inner)


def create_full_tag_vector(value: dict[VocabName, list[FullTag]] = {}) -> FullTagVector:
    if not _is_valid_full_tag_vector_value(value):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid value: {value!r}")
    return {'__type': DataAuctionType.FULL_TAG_VECTOR, 'value': value}  # type: ignore[return-value]


def load_full_tag_vector(data: dict) -> FullTagVector:
    if not check_type(data, 'FullTagVector'):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid __type for FullTagVector: {data!r}")
    inner = data.get('value', {})
    if not _is_valid_full_tag_vector_value(inner):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid FullTagVector value: {inner!r}")
    return data  # type: ignore[return-value]
