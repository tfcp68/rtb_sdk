from rtb_sdk.schemas import Frequency, Granularity
from rtb_sdk.constants import Gran, DataAuctionType
from rtb_sdk.errors import AuctionError, ErrorCodes
from ..type_helpers import check_type

_VALID_FREQ_GRAN_KEYS = frozenset(v for k, v in vars(Gran).items() if not k.startswith('_'))


def _is_valid_frequency_value(val) -> bool:
    if not isinstance(val, dict):
        return False
    for k, v in val.items():
        if k not in _VALID_FREQ_GRAN_KEYS:
            return False
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            return False
        if v < 0:
            return False
    return True


def get_frequency_dict(freq: Frequency) -> dict:
    return freq.get('value', {})


def is_valid_frequency(val) -> bool:
    if not check_type(val, 'Frequency'):
        return False
    inner = get_frequency_dict(val)
    return _is_valid_frequency_value(inner)


def create_frequency(ten_minutes: float = 0,
                     hour: float = 0,
                     day: float = 0,
                     week: float = 0,
                     month: float = 0) -> Frequency:
    value = {
        Gran.TEN_MINUTES: ten_minutes,
        Gran.HOUR: hour,
        Gran.DAY: day,
        Gran.WEEK: week,
        Gran.MONTH: month,
    }
    if not _is_valid_frequency_value(value):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid frequency value: {value!r}")
    return {'__type': DataAuctionType.FREQUENCY, 'value': value}  # type: ignore[return-value]


def load_frequency(data: dict) -> Frequency:
    if not check_type(data, 'Frequency'):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid __type for Frequency: {data!r}")
    inner = data.get('value', {})
    if not _is_valid_frequency_value(inner):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid Frequency value: {inner!r}")
    return data  # type: ignore[return-value]
