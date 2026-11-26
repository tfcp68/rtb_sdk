from rtb_sdk.schemas import TargetVector, VocabName, RawTag
from rtb_sdk.constants import DataAuctionType
from rtb_sdk.errors import AuctionError, ErrorCodes
from ..type_helpers import check_type


def _is_valid_target_vector_value(val) -> bool:
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


def get_target_vector_dict(tv: TargetVector) -> dict:
    return tv.get('value', {})


def is_valid_target_vector(val) -> bool:
    if not check_type(val, 'TargetVector'):
        return False
    inner = get_target_vector_dict(val)
    return _is_valid_target_vector_value(inner)


def create_target_vector(value: dict[VocabName, list[RawTag]] = {}) -> TargetVector:
    if not _is_valid_target_vector_value(value):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid value: {value!r}")
    return {'__type': DataAuctionType.TARGET_VECTOR, 'value': value}  # type: ignore[return-value]


def load_target_vector(data: dict) -> TargetVector:
    if not check_type(data, 'TargetVector'):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid __type for TargetVector: {data!r}")
    inner = data.get('value', {})
    if not _is_valid_target_vector_value(inner):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid TargetVector value: {inner!r}")
    return data  # type: ignore[return-value]
