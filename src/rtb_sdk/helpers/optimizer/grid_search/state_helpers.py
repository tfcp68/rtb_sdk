from typing import Any, cast

from rtb_sdk.schemas import (
    OptimizationStrategyId,
    GridSearchState,
    Parameters,
    DecisionVariables,
    OptimizationMethodId,
    MethodState
)
from rtb_sdk.constants import (
    OptimizationStrategies,
    OptimizationMethod,
    DataOptimizerType,
)
from rtb_sdk.helpers.type_helpers import check_type
from rtb_sdk.helpers.optimizer.utils import is_valid_optimization_strategy
from .options_helpers import _cartesian_product_size
import rtb_sdk.errors.optimizer as com_err


# --- Getters ---

def get_grid_state_best_vectors(state: GridSearchState,
                                default: list[Parameters] | None = None) -> list[Parameters] | None:
    return state.get("best_vectors", default)

def get_grid_state_n_combinations(state: GridSearchState, default: int = 0) -> int:
    return state.get("n_combinations", default)

def get_grid_state_n_step_combination(state: GridSearchState, default: int = 0) -> int:
    return state.get("n_step_combinations", default)

def get_grid_state_index(state: GridSearchState, default: int = 0) -> int:
    return state.get("index", default)

def get_grid_state_n_cartesian_product(state: GridSearchState, default: int = 0) -> int:
    return state.get("n_cartesian_product", default)

def get_grid_state_strategy_type(state: GridSearchState,
                                 default: OptimizationStrategyId = OptimizationStrategies.MINIMIZE
                                 ) -> OptimizationStrategyId:
    return state.get("strategy_type", default)

def get_grid_state_method_type(state: GridSearchState,
                               default: OptimizationMethodId = OptimizationMethod.GRID_SEARCH
                               ) -> OptimizationMethodId:
    return state.get("method_type", default)

def is_grid_search_state(state: MethodState) -> bool:
    return state.get("method_type") == OptimizationMethod.GRID_SEARCH

def is_grid_search_optimization_done(state: GridSearchState) -> bool:
    if not check_type(state, DataOptimizerType.GRID_SEARCH_STATE):
        raise com_err.OptimizerError(
            com_err.ErrorCodes.PARAMETER_ERROR_CODE,
            "Parameter state must be GridSearchState"
        )
    if not (_is_valid_grid_state_index(state) and
            _is_valid_grid_state_n_combinations(state) and
            _is_valid_grid_state_n_cartesian_product(state)):
        raise com_err.OptimizerError(
            com_err.ErrorCodes.PARAMETER_ERROR_CODE,
            "Parameter state Has non-valid fields to determine the completeness of the optimization"
        )
    index = get_grid_state_index(state)
    n_combinations = get_grid_state_n_combinations(state)
    n_cartesian_product = get_grid_state_n_cartesian_product(state)
    return index >= min(n_combinations, n_cartesian_product)

# --- _is_valid: checking the type of a field value ---

def _is_valid_grid_state_best_vectors(state: GridSearchState) -> bool:
    if not check_type(state, DataOptimizerType.GRID_SEARCH_STATE):
        return False
    best_vectors = get_grid_state_best_vectors(state)
    if not isinstance(best_vectors, list):
        return False
    return all(isinstance(vec, dict) for vec in best_vectors)

def _is_valid_grid_state_n_combinations(state: GridSearchState) -> bool:
    if not check_type(state, DataOptimizerType.GRID_SEARCH_STATE):
        return False
    n_combinations = get_grid_state_n_combinations(state)
    if not isinstance(n_combinations, int):
        return False
    return n_combinations >= 1

def _is_valid_grid_state_n_step_combinations(state: GridSearchState) -> bool:
    if not check_type(state, DataOptimizerType.GRID_SEARCH_STATE):
        return False
    n_step_combinations = get_grid_state_n_step_combination(state)
    if not isinstance(n_step_combinations, int):
        return False
    return n_step_combinations >= 1

def _is_valid_grid_state_index(state: GridSearchState) -> bool:
    if not check_type(state, DataOptimizerType.GRID_SEARCH_STATE):
        return False
    index = get_grid_state_index(state)
    if not isinstance(index, int):
        return False
    return index >= 0

def _is_valid_grid_state_n_cartesian_product(state: GridSearchState) -> bool:
    if not check_type(state, DataOptimizerType.GRID_SEARCH_STATE):
        return False
    n_cartesian_product = get_grid_state_n_cartesian_product(state)
    if not isinstance(n_cartesian_product, int):
        return False
    return n_cartesian_product >= 1

def _is_valid_grid_state_strategy_type(state: GridSearchState) -> bool:
    if not check_type(state, DataOptimizerType.GRID_SEARCH_STATE):
        return False
    strategy_type = get_grid_state_strategy_type(state)
    if not isinstance(strategy_type, str):
        return False
    return is_valid_optimization_strategy(strategy_type)

def _is_valid_grid_state_method_type(state: GridSearchState) -> bool:
    if not check_type(state, DataOptimizerType.GRID_SEARCH_STATE):
        return False
    method_type = get_grid_state_method_type(state)
    if not isinstance(method_type, str):
        return False
    return method_type == OptimizationMethod.GRID_SEARCH

CheckGridStateList = [
    _is_valid_grid_state_best_vectors,
    _is_valid_grid_state_n_combinations,
    _is_valid_grid_state_n_step_combinations,
    _is_valid_grid_state_index,
    _is_valid_grid_state_n_cartesian_product,
    _is_valid_grid_state_strategy_type,
    _is_valid_grid_state_method_type
]

# --- _check: checking a field value for validity ---

def _check_fields_grid_state(state: GridSearchState) -> bool:
    for check in CheckGridStateList:
        if not check(state):
            return False
    return True

# --- Main validation and checking functions ---

def is_valid_grid_state(state: Any) -> bool:
    if not check_type(state, DataOptimizerType.GRID_SEARCH_STATE):
        return False
    return _check_fields_grid_state(state)


# --- Builder ---

def build_grid_search_state(decision_variables: DecisionVariables,
                            best_vectors: list[Parameters] | None = None,
                            n_combinations: int = 100,
                            n_step_combinations: int = 1,
                            index: int = 0,
                            strategy_type: OptimizationStrategyId = OptimizationStrategies.MINIMIZE,
                            **kwargs
                            ) -> GridSearchState:
    if best_vectors is None:
        best_vectors = []

    n_cartesian_product = _cartesian_product_size(decision_variables)

    res = {
        "best_vectors": best_vectors,
        "n_combinations": n_combinations,
        "n_step_combinations": n_step_combinations,
        "index": index,
        "n_cartesian_product": n_cartesian_product,
        "strategy_type": strategy_type,
        "method_type": OptimizationMethod.GRID_SEARCH,
        "__type": DataOptimizerType.GRID_SEARCH_STATE,
    }
    if is_valid_grid_state(res):
        return cast(GridSearchState, res)
    else:
        raise com_err.OptimizerError(
            com_err.ErrorCodes.PARAMETER_ERROR_CODE,
            "Not valid parameters for GridSearchState"
        )

def build_grid_search_state_from_dict(decision_variables: DecisionVariables,
                                      data: dict) -> GridSearchState:
    try:
        return build_grid_search_state(decision_variables, **data)
    except Exception as e:
        raise com_err.OptimizerError(
            com_err.ErrorCodes.PARAMETER_ERROR_CODE,
            "Not valid parameters for GridSearchState"
        )
