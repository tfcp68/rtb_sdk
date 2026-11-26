from typing import Any, cast

from rtb_sdk.schemas import OptimizationMethodId, OptimizationStrategyId, Parameters, MethodState
from rtb_sdk.constants import DataOptimizerType
from rtb_sdk.helpers.type_helpers import check_type
import rtb_sdk.errors.optimizer as com_err
from .utils import is_valid_optimization_method, is_valid_optimization_strategy


# --- Getters ---

def get_state_best_vectors(state: MethodState,
                           default: list[Parameters] | None = None) -> list[Parameters] | None:
    return state.get("best_vectors", default)

def get_state_method_type(state: MethodState,
                          default: OptimizationMethodId | None = None
                          ) -> OptimizationMethodId | None:
    return state.get("method_type", default)

def get_state_strategy_type(state: MethodState,
                            default: OptimizationStrategyId | None = None
                            ) -> OptimizationStrategyId | None:
    return state.get("strategy_type", default)

# --- _is_valid: checking the type of a field value ---

def _is_valid_state_best_vectors(state: MethodState) -> bool:
    if not (check_type(state, DataOptimizerType.METHOD_STATE)
            or check_type(state, DataOptimizerType.GENETIC_SEARCH_STATE)
            or check_type(state, DataOptimizerType.GRID_SEARCH_STATE)):
        return False
    best_vectors = get_state_best_vectors(state)
    if not isinstance(best_vectors, list):
        return False
    return all(isinstance(vec, dict) for vec in best_vectors)

def _is_valid_state_method_type(state: MethodState) -> bool:
    if not (check_type(state, DataOptimizerType.METHOD_STATE)
            or check_type(state, DataOptimizerType.GENETIC_SEARCH_STATE)
            or check_type(state, DataOptimizerType.GRID_SEARCH_STATE)):
        return False
    method_type = get_state_method_type(state)
    if not isinstance(method_type, str):
        return False
    return is_valid_optimization_method(method_type)

def _is_valid_state_strategy_type(state: MethodState) -> bool:
    if not (check_type(state, DataOptimizerType.METHOD_STATE)
            or check_type(state, DataOptimizerType.GENETIC_SEARCH_STATE)
            or check_type(state, DataOptimizerType.GRID_SEARCH_STATE)):
        return False
    strategy_type = get_state_strategy_type(state)
    if not isinstance(strategy_type, str):
        return False
    return is_valid_optimization_strategy(strategy_type)

CheckMethodStateList = [_is_valid_state_best_vectors,
                        _is_valid_state_method_type,
                        _is_valid_state_strategy_type]

# --- _check: checking a field value for validity ---

def _check_fields_method_state(state: MethodState) -> bool:
    for check in CheckMethodStateList:
        if not check(state):
            return False
    return True

# --- Main validation and checking functions ---

def is_valid_method_state(state: Any) -> bool:
    if not (check_type(state, DataOptimizerType.METHOD_STATE)
            or check_type(state, DataOptimizerType.GENETIC_SEARCH_STATE)
            or check_type(state, DataOptimizerType.GRID_SEARCH_STATE)):
        return False
    return _check_fields_method_state(state)

# --- Builder ---

def build_method_state(method_type: OptimizationMethodId,
                       strategy_type: OptimizationStrategyId,
                       best_vectors: list[Parameters] | None = None,
                       **kwargs) -> MethodState:
    if best_vectors is None:
        best_vectors = []
    res = {
        "best_vectors": best_vectors,
        "method_type": method_type,
        "strategy_type": strategy_type,
        "__type": DataOptimizerType.METHOD_STATE,
    }
    if is_valid_method_state(res):
        return cast(MethodState, res)
    else:
        raise com_err.OptimizerError(
            com_err.ErrorCodes.PARAMETER_ERROR_CODE,
            "Not valid parameters for MethodState"
        )

def build_method_state_from_dict(data: dict) -> MethodState:
    try:
        return build_method_state(**data)
    except Exception as e:
        raise com_err.OptimizerError(
            com_err.ErrorCodes.PARAMETER_ERROR_CODE,
            "Not valid parameters for MethodState"
        )
