from rtb_sdk.schemas import (
    Ad,
    AdId,
    FrequencyLimits,
    TargetVector,
    VocabName,
    FullTag,
)
from datetime import datetime
from typing import Optional
from rtb_sdk.constants import DATE_ZERO, DATE_INFINITY, INFINITY_FREQUENCIES, MIN_INTERVAL, DataAuctionType
from rtb_sdk.errors import AuctionError, ErrorCodes
from .target_vector_helpers import is_valid_target_vector, create_target_vector, load_target_vector
from .frequency_limits_helpers import is_valid_frequency_limits, create_frequency_limits, load_frequency_limits
from ..type_helpers import check_type


def is_valid_ad_id(val) -> bool:
    return isinstance(val, str) and len(val) > 0

def is_valid_active(val) -> bool:
    return isinstance(val, bool)

def is_valid_start_date(val) -> bool:
    return isinstance(val, datetime)

def is_valid_end_date(val) -> bool:
    return isinstance(val, datetime)

def is_valid_cpm(val) -> bool:
    return isinstance(val, (int, float)) and not isinstance(val, bool)

def is_valid_priority(val) -> bool:
    return isinstance(val, (int, float)) and not isinstance(val, bool)

def is_valid_volume(val) -> bool:
    return isinstance(val, int) and not isinstance(val, bool)

def is_valid_vocabulary_weights(val) -> bool:
    if not isinstance(val, dict):
        return False
    for k, v in val.items():
        if not isinstance(k, str):
            return False
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            return False
    return True

def is_valid_tag_weights(val) -> bool:
    if not isinstance(val, dict):
        return False
    for k, v in val.items():
        if not isinstance(k, str):
            return False
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            return False
    return True

def is_valid_budget(val) -> bool:
    return isinstance(val, (int, float)) and not isinstance(val, bool)


def create_ad(
        id: AdId = 'EmptyAd',
        targets: TargetVector = create_target_vector(),
        active: bool = True,
        start_date: datetime = DATE_ZERO,
        end_date: datetime = DATE_INFINITY,
        cpm: float = 0,
        priority: float = 0,
        volume: int = 0,
        budget: float = 0.0,
        ad_frequency_limit: FrequencyLimits = create_frequency_limits(),
        user_frequency_limit: FrequencyLimits = create_frequency_limits(),
        parasitic_freq_limit: FrequencyLimits = create_frequency_limits(),
        vocabulary_weights: dict[VocabName, float] = {},
        tag_weights: dict[FullTag, float] = {},
) -> Ad:
    validators: dict[str, tuple] = {
        'id':                   (id,                   is_valid_ad_id,              f"Invalid ad id: {id!r}"),
        'targets':              (targets,              is_valid_target_vector,      f"Invalid target vector: {targets!r}"),
        'active':               (active,               is_valid_active,             f"Invalid active: {active!r}"),
        'start_date':           (start_date,           is_valid_start_date,         f"Invalid start_date: {start_date!r}"),
        'end_date':             (end_date,             is_valid_end_date,           f"Invalid end_date: {end_date!r}"),
        'cpm':                  (cpm,                  is_valid_cpm,                f"Invalid cpm: {cpm!r}"),
        'priority':             (priority,             is_valid_priority,           f"Invalid priority: {priority!r}"),
        'volume':               (volume,               is_valid_volume,             f"Invalid volume: {volume!r}"),
        'budget':               (budget,               is_valid_budget,             f"Invalid budget: {budget!r}"),
        'ad_frequency_limit':   (ad_frequency_limit,   is_valid_frequency_limits,   f"Invalid ad_frequency_limit: {ad_frequency_limit!r}"),
        'user_frequency_limit': (user_frequency_limit, is_valid_frequency_limits,   f"Invalid user_frequency_limit: {user_frequency_limit!r}"),
        'parasitic_freq_limit': (parasitic_freq_limit, is_valid_frequency_limits,   f"Invalid parasitic_freq_limit: {parasitic_freq_limit!r}"),
        'vocabulary_weights':   (vocabulary_weights,   is_valid_vocabulary_weights, f"Invalid vocabulary_weights: {vocabulary_weights!r}"),
        'tag_weights':          (tag_weights,          is_valid_tag_weights,        f"Invalid tag_weights: {tag_weights!r}"),
    }
    for _field, (value, validator, error_msg) in validators.items():
        if not validator(value):
            raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, error_msg)
    ad: Ad = {
        '__type': DataAuctionType.AD,
        'id': id,
        'targets': targets,
        'active': active,
        'start_date': start_date,
        'end_date': end_date,
        'cpm': cpm,
        'priority': priority,
        'volume': volume,
        'budget': budget,
        'ad_frequency_limit': ad_frequency_limit,
        'user_frequency_limit': user_frequency_limit,
        'parasitic_freq_limit': parasitic_freq_limit,
        'vocabulary_weights': vocabulary_weights,
        'tag_weights': tag_weights,
    }
    return ad


_GRAN_PARAM_MAP: dict[str, str] = {
    't': 'ten_minutes',
    'h': 'hour',
    'd': 'day',
    'w': 'week',
    'm': 'month',
}


def _raw_to_frequency_limits(data: dict) -> FrequencyLimits:
    """
    Builds FrequencyLimits from a raw dictionary with short keys (t/h/d/w/m).

    Supports both formats:
      - typed: {'__type': 'FrequencyLimits', 'value': {'h': 10, ...}}
      - raw: {'h': 10, 'd': 100, ...}

    Args:
        data: raw dict or typed FrequencyLimits dict

    Returns:
        FrequencyLimits
    """
    if data.get('__type') == 'FrequencyLimits':
        return load_frequency_limits(data)
    kwargs: dict = {}
    for k, v in data.items():
        if k in _GRAN_PARAM_MAP:
            kwargs[_GRAN_PARAM_MAP[k]] = v
        elif k == 'min_interval':
            kwargs['min_interval'] = v
    return create_frequency_limits(**kwargs)


def _parse_target_vector(data) -> TargetVector:
    """
    Builds a TargetVector from a raw dictionary or a typed dict.

    Supports both formats:
      - typed: {'__type': 'TargetVector', 'value': {...}}
      - raw: {vocab_name: [raw_tag, ...], ...}

    Args:
        data: raw dict or typed TargetVector dict

    Returns:
        TargetVector
    """
    if isinstance(data, dict) and data.get('__type') == 'TargetVector':
        return load_target_vector(data)
    return create_target_vector(data if isinstance(data, dict) else {})


def load_ad_raw(data: dict) -> Ad:
    """
    Creates an Ad from a raw dictionary without the __type wrapper.

    Used by the simulation loader and tests to build
    ads from JSON files or test cases.

    Supports both field formats:
      - targets: raw {vocab → [raw_tag]} or typed {'__type': 'TargetVector', ...}
      - frequency_limits: raw {t/h/d/w/m → int} or typed {'__type': 'FrequencyLimits', ...}
      - dates: ISO 8601 strings or datetime

    Args:
        data: raw dictionary with the ad's fields

    Returns:
        Ad: typed ad
    """
    data = dict(data)

    start_date = data.get('start_date', DATE_ZERO)
    if isinstance(start_date, str):
        start_date = datetime.fromisoformat(start_date)

    end_date = data.get('end_date', DATE_INFINITY)
    if isinstance(end_date, str):
        end_date = datetime.fromisoformat(end_date)

    return create_ad(
        id=str(data.get('id', 'EmptyAd')),
        targets=_parse_target_vector(data.get('targets', {})),
        active=data.get('active', True),
        start_date=start_date,
        end_date=end_date,
        cpm=float(data.get('cpm', 0)),
        priority=float(data.get('priority', 0)),
        volume=int(data.get('volume', 0)),
        budget=float(data.get('budget', 0.0)),
        ad_frequency_limit=_raw_to_frequency_limits(data.get('ad_frequency_limit', {})),
        user_frequency_limit=_raw_to_frequency_limits(data.get('user_frequency_limit', {})),
        parasitic_freq_limit=_raw_to_frequency_limits(data.get('parasitic_freq_limit', {})),
        vocabulary_weights=data.get('vocabulary_weights', {}),
        tag_weights=data.get('tag_weights', {}),
    )


def load_ad(data: dict) -> Ad:
    if not check_type(data, 'Ad'):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid __type for Ad: {data!r}")
    validators: dict[str, tuple] = {
        'id':                   (data.get('id'),                   is_valid_ad_id,              "Invalid ad id"),
        'active':               (data.get('active'),               is_valid_active,             "Invalid active"),
        'start_date':           (data.get('start_date'),           is_valid_start_date,         "Invalid start_date"),
        'end_date':             (data.get('end_date'),             is_valid_end_date,           "Invalid end_date"),
        'cpm':                  (data.get('cpm'),                  is_valid_cpm,                "Invalid cpm"),
        'priority':             (data.get('priority'),             is_valid_priority,           "Invalid priority"),
        'volume':               (data.get('volume'),               is_valid_volume,             "Invalid volume"),
        'vocabulary_weights':   (data.get('vocabulary_weights'),   is_valid_vocabulary_weights, "Invalid vocabulary_weights"),
        'tag_weights':          (data.get('tag_weights'),          is_valid_tag_weights,        "Invalid tag_weights"),
    }
    for _field, (value, validator, error_msg) in validators.items():
        if not validator(value):
            raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, error_msg)
    load_target_vector(data.get('targets', {}))
    load_frequency_limits(data.get('ad_frequency_limit', {}))
    load_frequency_limits(data.get('user_frequency_limit', {}))
    load_frequency_limits(data.get('parasitic_freq_limit', {}))
    return data  # type: ignore[return-value]


def get_ad_id(ad: Ad, default: AdId = 'EmptyAd') -> AdId:
    return ad.get('id', default)

def get_ad_targetvector(ad: Ad, default: TargetVector = create_target_vector()) -> TargetVector:
    return ad.get("targets", default)

def get_ad_active(ad: Ad, default: bool = True) -> bool:
    return ad.get("active", default)

def get_ad_start_date(ad: Ad, default: datetime = DATE_ZERO) -> datetime:
    return ad.get('start_date', default)

def get_ad_end_date(ad: Ad, default: datetime = DATE_INFINITY) -> datetime:
    return ad.get('end_date', default)

def get_ad_price(ad: Ad, default: float = 1e-9) -> float:
    return ad.get('cpm', default)

def get_ad_priority(ad: Ad, default: float = 0) -> float:
    return ad.get('priority', default)

def get_ad_volume(ad: Ad, default: int = 0) -> int:
    return ad.get("volume", default)

def get_ad_frequency_limit(ad: Ad) -> FrequencyLimits:
    freq = ad.get("ad_frequency_limit", INFINITY_FREQUENCIES)
    return freq

def get_ad_min_interval(ad: Ad, default: float = 0) -> float:
    freq = ad.get("ad_frequency_limit", INFINITY_FREQUENCIES)
    if freq is INFINITY_FREQUENCIES:
        return default
    return freq['value'].get(MIN_INTERVAL, default)


# Returns the recalculated (monthly) ad volume if the campaign duration exceeds a month
def get_date_month_volume(ad: Ad
                          ) -> Optional[float]:
    start_date = get_ad_start_date(ad)
    end_date = get_ad_end_date(ad)
    if start_date == DATE_ZERO or end_date == DATE_INFINITY:
        return get_ad_volume(ad)
    days = (end_date - start_date).days + 1

    if days < 31:
        return get_ad_volume(ad)
    else:
        return get_ad_volume(ad) * 31 / days
