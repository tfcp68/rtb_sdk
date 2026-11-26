from typing import Any, cast

from rtb_sdk.schemas import (
    OptimizationStrategyId,
    GridSearchOptions,
    DecisionVariables,
    OptimizationMethodId,
    MethodOptions
)
from rtb_sdk.constants import (
    OptimizationStrategies,
    OptimizationMethod,
    DataOptimizerType,
)
from rtb_sdk.helpers.type_helpers import check_type
from rtb_sdk.helpers.optimizer.utils import is_valid_optimization_strategy
from rtb_sdk.helpers.optimizer.decision_variables_helpers import get_decision_variables
import rtb_sdk.errors.optimizer as com_err


def _cartesian_product_size(decision_variables: DecisionVariables) -> int:
    vocab = get_decision_variables(decision_variables)
    if not vocab:
        return 0
    result = 1
    for seq in vocab:
        seq = vocab[seq]
        result *= len(seq)
    return result


# --- Getters ---

def get_grid_options_n_combinations(options: GridSearchOptions, default: int = 0) -> int:
    return options.get("n_combinations", default)

def get_grid_options_n_step_combinations(options: GridSearchOptions, default: int = 0) -> int:
    return options.get("n_step_combinations", default)

def get_grid_options_objective_type(options: GridSearchOptions,
                                     default: OptimizationStrategyId | None = None
                                     ) -> OptimizationStrategyId | None:
    return options.get("strategy_type", default)

def get_grid_option_method_type(options: GridSearchOptions,
                                 default: OptimizationMethodId | None = None
                                 ) -> OptimizationMethodId | None:
    return options.get("method_type", default)

def is_grid_search_options(options: MethodOptions) -> bool:
    return options.get("method_type") == OptimizationMethod.GRID_SEARCH

# --- _is_valid: checking the type of a field value ---

def _is_valid_grid_options_n_step_combinations(options: GridSearchOptions) -> bool:
    if not check_type(options, DataOptimizerType.GRID_SEARCH_OPTIONS):
        return False
    n_step_combinations = get_grid_options_n_step_combinations(options)
    if not isinstance(n_step_combinations, int):
        return False
    return n_step_combinations >= 1

def _is_valid_grid_options_n_combinations(options: GridSearchOptions) -> bool:
    if not check_type(options, DataOptimizerType.GRID_SEARCH_OPTIONS):
        return False
    n_combinations = get_grid_options_n_combinations(options)
    if not isinstance(n_combinations, int):
        return False
    return n_combinations >= 1

def _is_valid_grid_options_strategy_type(options: GridSearchOptions) -> bool:
    if not check_type(options, DataOptimizerType.GRID_SEARCH_OPTIONS):
        return False
    strategy_type = get_grid_options_objective_type(options)
    if not isinstance(strategy_type, str):
        return False
    return is_valid_optimization_strategy(strategy_type)

def _is_valid_grid_options_method_type(options: GridSearchOptions) -> bool:
    if not check_type(options, DataOptimizerType.GRID_SEARCH_OPTIONS):
        return False
    method_type = get_grid_option_method_type(options)
    if not isinstance(method_type, str):
        return False
    return method_type == OptimizationMethod.GRID_SEARCH

CheckGridOptionsList = [
    _is_valid_grid_options_n_step_combinations,
    _is_valid_grid_options_n_combinations,
    _is_valid_grid_options_strategy_type,
    _is_valid_grid_options_method_type
]

# --- _check: checking a field value for validity ---

def _check_fields_grid_options(options: GridSearchOptions) -> bool:
    for check in CheckGridOptionsList:
        if not check(options):
            return False
    return True

# --- Main validation and checking functions ---

def is_valid_grid_options(options: Any) -> bool:
    if not check_type(options, DataOptimizerType.GRID_SEARCH_OPTIONS):
        return False
    return _check_fields_grid_options(options)


# --- Builder ---

def create_grid_search_options(decision_variables: DecisionVariables,
                               n_step_combinations: int = 10,
                               n_combinations: int | None = None,
                               strategy_type: OptimizationStrategyId = OptimizationStrategies.MINIMIZE,
                               **kwargs
                               ) -> GridSearchOptions:
    if n_combinations is None:
        n_combinations = _cartesian_product_size(decision_variables)

    res = {
        "n_step_combinations": n_step_combinations,
        "n_combinations": n_combinations,
        "strategy_type": strategy_type,
        "method_type": OptimizationMethod.GRID_SEARCH,
        "__type": DataOptimizerType.GRID_SEARCH_OPTIONS,
    }
    if is_valid_grid_options(res):
        return cast(GridSearchOptions, res)
    else:
        raise com_err.OptimizerError(
            com_err.ErrorCodes.PARAMETER_ERROR_CODE,
            "Not valid parameters for GridSearchOptions"
        )

def create_grid_search_options_from_dict(decision_variables: DecisionVariables,
                                         data: dict) -> GridSearchOptions:
    try:
        return create_grid_search_options(decision_variables, **data)
    except Exception as e:
        raise com_err.OptimizerError(
            com_err.ErrorCodes.PARAMETER_ERROR_CODE,
            "Not valid parameters for GridSearchOptions"
        )
