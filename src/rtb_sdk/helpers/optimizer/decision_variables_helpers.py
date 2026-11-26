from typing import Any, cast

from rtb_sdk.schemas import DecisionVariables
from rtb_sdk.constants import DataOptimizerType
from rtb_sdk.helpers.type_helpers import check_type
import rtb_sdk.errors.optimizer as com_err


# --- Getters ---

def get_decision_variables(vocab: DecisionVariables,
                           default: dict[str, list[Any]] | None = None) -> dict[str, list[Any]] | None:
    return vocab.get("decision_variables", default)

def get_decision_variables_items(vocab: dict[str, list[Any]]) -> list[Any]:
    return list(vocab.items())

# --- _is_valid: checking the type of a field value ---

def _is_valid_decision_variables_dict(dv: DecisionVariables) -> bool:
    if not check_type(dv, DataOptimizerType.DECISION_VARIABLES):
        return False
    decision_variables = get_decision_variables(dv)
    if not isinstance(decision_variables, dict):
        return False
    return all(isinstance(k, str) and isinstance(v, list) and len(v) != 0
               for k, v in get_decision_variables_items(decision_variables))

CheckDecisionVariablesList = [_is_valid_decision_variables_dict]

# --- _check: checking a field value for validity ---

def _check_fields_decision_variables(dv: DecisionVariables) -> bool:
    for check in CheckDecisionVariablesList:
        if not check(dv):
            return False
    return True

# --- Main validation and checking functions ---

def is_valid_decision_variables(dv: Any) -> bool:
    if not check_type(dv, DataOptimizerType.DECISION_VARIABLES):
        return False
    return _check_fields_decision_variables(dv)

# --- Builder ---

def build_decision_variables(decision_variables: dict[str, list[Any]],
                             **kwargs) -> DecisionVariables:
    res = {
        "decision_variables": decision_variables,
        "__type": DataOptimizerType.DECISION_VARIABLES
    }
    if is_valid_decision_variables(res):
        return cast(DecisionVariables, res)
    else:
        raise com_err.OptimizerError(
            com_err.ErrorCodes.PARAMETER_ERROR_CODE,
            "Not valid parameters for DecisionVariables"
        )

def build_decision_variables_from_dict(data: dict) -> DecisionVariables:
    try:
        return build_decision_variables(**data)
    except Exception as e:
        raise com_err.OptimizerError(
            com_err.ErrorCodes.PARAMETER_ERROR_CODE,
            "Not valid parameters for DecisionVariables"
        )
