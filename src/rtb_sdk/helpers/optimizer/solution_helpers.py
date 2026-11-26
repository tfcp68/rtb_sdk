from typing import Any, Mapping, cast

from rtb_sdk.schemas import Parameters, Estimation, Solution
from rtb_sdk.constants import DataOptimizerType
from rtb_sdk.helpers.type_helpers import check_type
import rtb_sdk.errors.optimizer as com_err
from .parameters_helpers import build_parameters


# --- Getters ---

def get_solution_parameters(candidate: Solution, default: Parameters | None = None) -> Parameters | None:
    return candidate.get("parameters", default)

def get_solution_estimation(candidate: Solution, default: Estimation = 0.0) -> Estimation:
    return candidate.get("estimation", default)

# --- _is_valid: checking the type of a field value ---

def _is_valid_solution_parameters(solution: Solution) -> bool:
    if not check_type(solution, DataOptimizerType.SOLUTION):
        return False
    parameters = get_solution_parameters(solution)
    if not isinstance(parameters, dict):
        return False
    return len(parameters) > 0

def _is_valid_solution_estimation(solution: Solution) -> bool:
    if not check_type(solution, DataOptimizerType.SOLUTION):
        return False
    estimation = get_solution_estimation(solution)
    return isinstance(estimation, (int, float))

CheckSolutionList = [_is_valid_solution_parameters,
                     _is_valid_solution_estimation]

# --- _check: checking a field value for validity ---

def _check_fields_solution(solution: Solution) -> bool:
    for check in CheckSolutionList:
        if not check(solution):
            return False
    return True

# --- Main validation and checking functions ---

def is_valid_solution(solution: Any) -> bool:
    if not check_type(solution, DataOptimizerType.SOLUTION):
        return False
    return _check_fields_solution(solution)

# --- Builder ---

def build_solution(parameters: Parameters | None = None,
                   estimation: Estimation = -1.0,
                   **kwargs) -> Solution:
    if parameters is None:
        parameters = build_parameters()
    res = {
        "parameters": parameters,
        "estimation": estimation,
        "__type": DataOptimizerType.SOLUTION
    }
    if is_valid_solution(res):
        return cast(Solution, res)
    else:
        raise com_err.OptimizerError(
            com_err.ErrorCodes.PARAMETER_ERROR_CODE,
            "Not valid parameters for Solution"
        )

def build_solution_from_dict(data: Mapping[str, Any]) -> Solution:
    try:
        return build_solution(**data)
    except Exception as e:
        raise com_err.OptimizerError(
            com_err.ErrorCodes.PARAMETER_ERROR_CODE,
            "Not valid parameters for Solution"
        )
