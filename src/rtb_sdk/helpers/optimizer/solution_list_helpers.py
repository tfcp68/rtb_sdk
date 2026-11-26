from typing import Any, cast

from rtb_sdk.schemas import Solution, SolutionList
from rtb_sdk.constants import DataOptimizerType
from rtb_sdk.helpers.type_helpers import check_type
import rtb_sdk.errors.optimizer as com_err
from .solution_helpers import is_valid_solution, build_solution_from_dict


# --- Getters ---

def get_solution_list(solution_list: SolutionList,
                      default: list[Solution] | None = None) -> list[Solution] | None:
    return solution_list.get("solution_list", default)

# --- _is_valid: checking the type of a field value ---

def _is_valid_solution_list_items(sl: SolutionList) -> bool:
    if not check_type(sl, DataOptimizerType.SOLUTION_LIST):
        return False
    solution_list = get_solution_list(sl)
    if not isinstance(solution_list, list):
        return False
    return all(is_valid_solution(s) for s in solution_list)

CheckSolutionListList = [_is_valid_solution_list_items]

# --- _check: checking a field value for validity ---

def _check_fields_solution_list(sl: SolutionList) -> bool:
    for check in CheckSolutionListList:
        if not check(sl):
            return False
    return True

# --- Main validation and checking functions ---

def is_valid_solution_list(sl: Any) -> bool:
    if not check_type(sl, DataOptimizerType.SOLUTION_LIST):
        return False
    return _check_fields_solution_list(sl)

# --- Builder ---

def build_solution_list(solution_list: list[Solution],
                        **kwargs) -> SolutionList:
    solution_list_tmp = []
    for solution in solution_list:
        solution_list_tmp.append(build_solution_from_dict(solution))
    res = {
        "solution_list": solution_list_tmp,
        "__type": DataOptimizerType.SOLUTION_LIST
    }
    if is_valid_solution_list(res):
        return cast(SolutionList, res)
    else:
        raise com_err.OptimizerError(
            com_err.ErrorCodes.PARAMETER_ERROR_CODE,
            "Not valid parameters for SolutionList"
        )

def build_solution_list_from_dict(data: dict) -> SolutionList:
    try:
        return build_solution_list(**data)
    except Exception as e:
        raise com_err.OptimizerError(
            com_err.ErrorCodes.PARAMETER_ERROR_CODE,
            "Not valid parameters for SolutionList"
        )
