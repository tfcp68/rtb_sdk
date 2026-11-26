from typing import Callable, Iterable
from inspect import signature

from rtb_sdk.errors.balancer import BalancerError, ErrorCodes
from rtb_sdk.helpers.balancer.optimize_params_helpers import create_optimize_params, create_balancing_params
from rtb_sdk.constants.balancer_constants import (
    DEFAULT_ACCURACY_PERCENT,
    DEFAULT_FUNC_REPLACE_INFINITY,
    MAX_MONEY,
    MIN_CATEGORY_PROBABILITY,
    OBJECTIVES,
)
from rtb_sdk.schemas.auction_schemas import FullTag, VocabName, RawTag
from rtb_sdk.schemas.balancer_schemas import BalancingBySelloutParams, InnerVocabs, OuterVocabs


def is_valid_parameters_accuracy_percent(val) -> bool:
    return isinstance(val, float) and val > 0


def is_valid_parameters_func_replace_infinity(val) -> bool:
    if val is None:
        return True

    if not callable(val):
        return False

    try:
        sig = signature(val)
    except (ValueError, TypeError):
        return True

    try:
        sig.bind([])
    except TypeError:
        return False

    return True


def get_balance_by_sellout_parameters_accuracy_percent(
    params: BalancingBySelloutParams,
    default: float = DEFAULT_ACCURACY_PERCENT,
) -> float:
    return params.get('accuracy_percent', default)


def get_balance_by_sellout_parameters_func_replace_infinity(
    params: BalancingBySelloutParams,
    default: Callable[[Iterable[float]], int] | None = DEFAULT_FUNC_REPLACE_INFINITY,
) -> Callable[[Iterable[float]], int] | None:
    return params.get('func_replace_infinity', default)



def create_balance_by_sellout_params(
    total_traffic_volume: int,
    tag_probabilities: dict[FullTag, float],
    vocabs: InnerVocabs,
    objective: OBJECTIVES = MAX_MONEY,
    max_n_categories: int = 100,
    min_category_probability: float = MIN_CATEGORY_PROBABILITY,
    n_threads: int = 1,
    accuracy_percent: float = DEFAULT_ACCURACY_PERCENT,
    func_replace_infinity: Callable[[Iterable[float]], int] | None = DEFAULT_FUNC_REPLACE_INFINITY,
) -> BalancingBySelloutParams:
    optimize_params = create_optimize_params(
        total_traffic_volume=total_traffic_volume,
        tag_probabilities=tag_probabilities,
        vocabs=vocabs,
        objective=objective,
        max_n_categories=max_n_categories,
        min_category_probability=min_category_probability,
        n_threads=n_threads,
    )

    validators: dict[str, tuple] = {
        'accuracy_percent':      (accuracy_percent,      is_valid_parameters_accuracy_percent,      f"Invalid accuracy_percent: {accuracy_percent!r}"),
        'func_replace_infinity': (func_replace_infinity, is_valid_parameters_func_replace_infinity, f"Invalid func_replace_infinity: {func_replace_infinity!r}"),
    }
    for _field, (value, validator, error_msg) in validators.items():
        if not validator(value):
            raise BalancerError(ErrorCodes.INPUT_VALIDATION_ERROR, error_msg)
    
    return BalancingBySelloutParams(
        **optimize_params,
        accuracy_percent=accuracy_percent,
        func_replace_infinity=func_replace_infinity,
    )


def create_balance_by_sellout_params_outer(
    total_traffic_volume: int,
    tag_probabilities_outer: dict[VocabName, dict[RawTag, float]],
    vocabs_outer: OuterVocabs,
    objective: OBJECTIVES = MAX_MONEY,
    max_n_categories: int = 100,
    min_category_probability: float = MIN_CATEGORY_PROBABILITY,
    n_threads: int = 1,
    accuracy_percent: float = DEFAULT_ACCURACY_PERCENT,
    func_replace_infinity: Callable[[Iterable[float]], int] | None = DEFAULT_FUNC_REPLACE_INFINITY,
) -> BalancingBySelloutParams:
    """Accepts the outer (RawTag) format, converts it to the inner one."""
    base = create_balancing_params(
        total_traffic_volume=total_traffic_volume,
        tag_probabilities_outer=tag_probabilities_outer,
        vocabs_outer=vocabs_outer,
        objective=objective,
        max_n_categories=max_n_categories,
        min_category_probability=min_category_probability,
        n_threads=n_threads,
    )

    validators: dict[str, tuple] = {
        'accuracy_percent':      (accuracy_percent,      is_valid_parameters_accuracy_percent,      f"Invalid accuracy_percent: {accuracy_percent!r}"),
        'func_replace_infinity': (func_replace_infinity, is_valid_parameters_func_replace_infinity, f"Invalid func_replace_infinity: {func_replace_infinity!r}"),
    }
    for _field, (value, validator, error_msg) in validators.items():
        if not validator(value):
            raise BalancerError(ErrorCodes.INPUT_VALIDATION_ERROR, error_msg)

    return BalancingBySelloutParams(
        **base,
        accuracy_percent=accuracy_percent,
        func_replace_infinity=func_replace_infinity,
    )
