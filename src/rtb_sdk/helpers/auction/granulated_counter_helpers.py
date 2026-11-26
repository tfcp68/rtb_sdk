from rtb_sdk.schemas import GranulatedCounter, Granularity
from rtb_sdk.constants import Gran, INT_ZERO, DataAuctionType
from rtb_sdk.errors import AuctionError, ErrorCodes
from ..type_helpers import check_type

_VALID_GRAN_KEYS = frozenset(v for k, v in vars(Gran).items() if not k.startswith('_'))


def _is_valid_counter_value(val) -> bool:
    if not isinstance(val, dict):
        return False
    for k, v in val.items():
        if k not in _VALID_GRAN_KEYS:
            return False
        if not isinstance(v, int) or isinstance(v, bool):
            return False
        if v < 0:
            return False
    return True


def get_granulated_counter_dict(counter: GranulatedCounter) -> dict:
    return counter.get('value', {})


def is_valid_granulated_counter(val) -> bool:
    if not check_type(val, 'GranulatedCounter'):
        return False
    inner = get_granulated_counter_dict(val)
    return _is_valid_counter_value(inner)


def create_granulated_counter(ten_minutes: int = 0,
                              hour: int = 0,
                              day: int = 0,
                              week: int = 0,
                              month: int = 0) -> GranulatedCounter:
    value = {
        Gran.TEN_MINUTES: ten_minutes,
        Gran.HOUR: hour,
        Gran.DAY: day,
        Gran.WEEK: week,
        Gran.MONTH: month,
    }
    if not _is_valid_counter_value(value):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid counter value: {value!r}")
    return {'__type': DataAuctionType.GRANULATED_COUNTER, 'value': value}  # type: ignore[return-value]


def load_granulated_counter(data: dict) -> GranulatedCounter:
    if not check_type(data, 'GranulatedCounter'):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid __type for GranulatedCounter: {data!r}")
    inner = data.get('value', {})
    if not _is_valid_counter_value(inner):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid GranulatedCounter value: {inner!r}")
    return data  # type: ignore[return-value]


def get_counter_value(counter: GranulatedCounter, resolution: Granularity) -> int:
    try:
        return counter['value'][resolution]
    except Exception:
        return INT_ZERO


def merge_granulated_counters(a: GranulatedCounter, b: GranulatedCounter) -> GranulatedCounter:
    a_val = get_granulated_counter_dict(a)
    b_val = get_granulated_counter_dict(b)
    merged = {k: a_val.get(k, 0) + b_val.get(k, 0) for k in set(a_val) | set(b_val)}
    return {'__type': DataAuctionType.GRANULATED_COUNTER, 'value': merged}  # type: ignore[return-value]
