from typing import Any, cast

from rtb_sdk.schemas import OptimizationMethodId, OptimizationStrategyId, MethodOptions
from rtb_sdk.constants import DataOptimizerType
from rtb_sdk.helpers.type_helpers import check_type
import rtb_sdk.errors.optimizer as com_err
from .utils import is_valid_optimization_method, is_valid_optimization_strategy


# --- Getters ---

def get_option_strategy_type(options: MethodOptions,
                             default: OptimizationStrategyId | None = None
                             ) -> OptimizationStrategyId | None:
    return options.get("strategy_type", default)

def get_option_method_type(options: MethodOptions,
                           default: OptimizationMethodId | None = None
                           ) -> OptimizationMethodId | None:
    return options.get("method_type", default)

# --- _is_valid: checking the type of a field value ---

def _is_valid_option_strategy_type(options: MethodOptions) -> bool:
    if not (check_type(options, DataOptimizerType.METHOD_OPTIONS) or check_type(options, DataOptimizerType.GENETIC_SEARCH_OPTIONS)
            or check_type(options, DataOptimizerType.GRID_SEARCH_OPTIONS)
            or check_type(options, DataOptimizerType.GRID_SEARCH_OPTIONS)):
        return False
    strategy_type = get_option_strategy_type(options)
    if not isinstance(strategy_type, str):
        return False
    return is_valid_optimization_strategy(strategy_type)

def _is_valid_option_method_type(options: MethodOptions) -> bool:
    if not (check_type(options, DataOptimizerType.METHOD_OPTIONS) or check_type(options, DataOptimizerType.GENETIC_SEARCH_OPTIONS)
            or check_type(options, DataOptimizerType.GRID_SEARCH_OPTIONS)
            or check_type(options, DataOptimizerType.GRID_SEARCH_OPTIONS)):
        return False
    method_type = get_option_method_type(options)
    if not isinstance(method_type, str):
        return False
    return is_valid_optimization_method(method_type)

CheckMethodOptionsList = [_is_valid_option_strategy_type,
                          _is_valid_option_method_type]

# --- _check: checking a field value for validity ---

def _check_fields_method_options(options: MethodOptions) -> bool:
    for check in CheckMethodOptionsList:
        if not check(options):
            return False
    return True

# --- Main validation and checking functions ---

def is_valid_method_options(options: Any) -> bool:
    if not (check_type(options, DataOptimizerType.METHOD_OPTIONS) or check_type(options, DataOptimizerType.GENETIC_SEARCH_OPTIONS)
            or check_type(options, DataOptimizerType.GRID_SEARCH_OPTIONS)
            or check_type(options, DataOptimizerType.GRID_SEARCH_OPTIONS)):
        return False
    return _check_fields_method_options(options)

# --- Builder ---

def build_method_options(strategy_type: OptimizationStrategyId,
                         method_type: OptimizationMethodId,
                         **kwargs) -> MethodOptions:
    res = {
        "strategy_type": strategy_type,
        "method_type": method_type,
        "__type": DataOptimizerType.METHOD_OPTIONS,
    }
    if is_valid_method_options(res):
        return cast(MethodOptions, res)
    else:
        raise com_err.OptimizerError(
            com_err.ErrorCodes.PARAMETER_ERROR_CODE,
            "Not valid parameters for MethodOptions"
        )

def build_method_options_from_dict(data: dict) -> MethodOptions:
    try:
        return build_method_options(**data)
    except Exception as e:
        raise com_err.OptimizerError(
            com_err.ErrorCodes.PARAMETER_ERROR_CODE,
            "Not valid parameters for MethodOptions"
        )
