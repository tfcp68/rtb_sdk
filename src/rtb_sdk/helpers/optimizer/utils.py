from typing import Callable, Any, get_args

from rtb_sdk.schemas import OptimizationMethodId, OptimizationStrategyId, Estimation, SolutionList
from rtb_sdk.constants import OptimizationStrategies
from .parameters_helpers import get_parameters_parameters
from .solution_helpers import get_solution_parameters, build_solution
from .solution_list_helpers import get_solution_list, build_solution_list


_VALID_OPTIMIZATION_METHODS: frozenset = frozenset(get_args(OptimizationMethodId.__value__))
_VALID_OPTIMIZATION_STRATEGIES: frozenset = frozenset(get_args(OptimizationStrategyId.__value__))


def is_valid_optimization_method(method: OptimizationMethodId) -> bool:
    return method in _VALID_OPTIMIZATION_METHODS


def is_valid_optimization_strategy(strategy: OptimizationStrategyId) -> bool:
    return strategy in _VALID_OPTIMIZATION_STRATEGIES


# ===========================
# Utility functions
# ===========================

def estimate_func(candidates: SolutionList, est_func: Callable[[dict[str, Any]], Estimation]) -> SolutionList:
    result = []
    solution_list = get_solution_list(candidates) or []
    for candidate in solution_list:
        solution_parameters = get_solution_parameters(candidate)
        if solution_parameters is None:
            continue
        params = get_parameters_parameters(solution_parameters) or {}
        result.append(
            build_solution(
                parameters=solution_parameters,
                estimation=est_func(params)
            )
        )
    return build_solution_list(result)

def check_maximize(type_: OptimizationStrategyId) -> bool:
    return type_ == OptimizationStrategies.MAXIMIZE

def check_minimize(type_: OptimizationStrategyId) -> bool:
    return type_ == OptimizationStrategies.MINIMIZE

def validate_optimization_method(method: OptimizationMethodId) -> bool:
    return isinstance(method, str)

def check_optimization_method(method: OptimizationMethodId) -> bool:
    if not validate_optimization_method(method):
        return False
    return is_valid_optimization_method(method)
