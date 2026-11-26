from rtb_sdk.schemas import FrequencyLimits, Granularity
from rtb_sdk.constants import Gran, MIN_INTERVAL, INT_INFINITY, DataAuctionType
from rtb_sdk.errors import AuctionError, ErrorCodes
from ..type_helpers import check_type

_VALID_FREQ_KEYS = frozenset({*(v for k, v in vars(Gran).items() if not k.startswith('_')), MIN_INTERVAL})


def _is_valid_frequency_limits_value(val) -> bool:
    if not isinstance(val, dict):
        return False
    for k, v in val.items():
        if k not in _VALID_FREQ_KEYS:
            return False
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            return False
        if v < 0:
            return False
    return True


def get_frequency_limits_dict(limits: FrequencyLimits) -> dict:
    return limits.get('value', {})


def is_valid_frequency_limits(val) -> bool:
    if not check_type(val, 'FrequencyLimits'):
        return False
    inner = get_frequency_limits_dict(val)
    return _is_valid_frequency_limits_value(inner)


def create_frequency_limits(ten_minutes: float = 0,
                            hour: float = 0,
                            day: float = 0,
                            week: float = 0,
                            month: float = 0,
                            min_interval: float = 0) -> FrequencyLimits:
    value = {
        Gran.TEN_MINUTES: ten_minutes,
        Gran.HOUR: hour,
        Gran.DAY: day,
        Gran.WEEK: week,
        Gran.MONTH: month,
        MIN_INTERVAL: min_interval,
    }
    if not _is_valid_frequency_limits_value(value):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid frequency limits value: {value!r}")
    return {'__type': DataAuctionType.FREQUENCY_LIMITS, 'value': value}  # type: ignore[return-value]


def load_frequency_limits(data: dict) -> FrequencyLimits:
    if not check_type(data, 'FrequencyLimits'):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid __type for FrequencyLimits: {data!r}")
    inner = data.get('value', {})
    if not _is_valid_frequency_limits_value(inner):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid FrequencyLimits value: {inner!r}")
    return data  # type: ignore[return-value]


def get_frequency_limit_by_gran(limit: FrequencyLimits, resolution: Granularity) -> float:
    from .stats_helpers import is_granularity
    if not is_granularity(resolution):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, "Wrong data format")
    try:
        return limit['value'][resolution]
    except Exception:
        return INT_INFINITY


def get_real_month_ad_frequency(ad_frequencies: FrequencyLimits,
                                delta_date_factor: float = 1.0
                                ) -> float:
    from .stats_helpers import get_gran_resolution
    non_month_grans: list[Granularity] = [Gran.TEN_MINUTES, Gran.HOUR, Gran.DAY, Gran.WEEK]
    results = []
    for gran in non_month_grans:
        val = get_frequency_limit_by_gran(ad_frequencies, gran)
        results.append(val * get_gran_resolution(gran, Gran.MONTH) if val > 0 else INT_INFINITY)

    month = get_frequency_limit_by_gran(ad_frequencies, Gran.MONTH)
    if month <= 0:
        month = INT_INFINITY

    return min(month, *results)
