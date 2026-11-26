from typing import Any, get_args
from rtb_sdk.schemas import Granularity
from rtb_sdk.schemas.discriminated_type_schemas import (
    GenericDiscriminatedType,
    DiscriminatedAuctionType,
    DiscriminatedOptimizerType,
    DiscriminatedPredictorType
)

def _get_literal_values(type_alias) -> tuple:
    while hasattr(type_alias, '__value__'):
        type_alias = type_alias.__value__
    return get_args(type_alias)

_VALID_AUCTION_TYPES: frozenset = frozenset(_get_literal_values(DiscriminatedAuctionType))

_VALID_OPTIMIZER_TYPES: frozenset = frozenset(_get_literal_values(DiscriminatedOptimizerType))

_VALID_PREDICTOR_TYPES: frozenset = frozenset(_get_literal_values(DiscriminatedPredictorType))

_VALID_TYPES: frozenset = _VALID_AUCTION_TYPES | _VALID_OPTIMIZER_TYPES | _VALID_PREDICTOR_TYPES

_VALID_GRANULARITIES: frozenset = frozenset(_get_literal_values(Granularity))

def check_type(obj: Any, cls: GenericDiscriminatedType) -> bool:
    if not isinstance(obj, dict):
        return False
    return get_type(obj) == cls

def check_auction_type(obj: Any, cls: DiscriminatedAuctionType) -> bool:
    if not isinstance(obj, dict):
        return False
    value = obj.get('__type', None)
    if value not in _VALID_AUCTION_TYPES:
        return False
    return get_type(obj) == cls

def check_optimizer_type(obj: Any, cls: DiscriminatedOptimizerType) -> bool:
    if not isinstance(obj, dict):
        return False
    value = obj.get('__type', None)
    if value not in _VALID_OPTIMIZER_TYPES:
        return False
    return get_type(obj) == cls

def check_predictor_type(obj: Any, cls: DiscriminatedPredictorType) -> bool:
    if not isinstance(obj, dict):
        return False
    value = obj.get('__type', None)
    if value not in _VALID_PREDICTOR_TYPES:
        return False
    return get_type(obj) == cls

def get_type(obj: Any) -> GenericDiscriminatedType | None:
    value = obj.get('__type', None)
    if value not in _VALID_TYPES:
        return None
    return value

def get_auction_type(obj: Any) -> DiscriminatedAuctionType | None:
    value = obj.get('__type', None)
    if value not in _VALID_AUCTION_TYPES:
        return None
    return value

def get_optimizer_type(obj: Any) -> DiscriminatedOptimizerType | None:
    value = obj.get('__type', None)
    if value not in _VALID_OPTIMIZER_TYPES:
        return None
    return value

def get_predictor_type(obj: Any) -> DiscriminatedPredictorType | None:
    value = obj.get('__type', None)
    if value not in _VALID_PREDICTOR_TYPES:
        return None
    return value
