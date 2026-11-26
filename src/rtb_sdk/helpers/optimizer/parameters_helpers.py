from typing import Any, cast

from rtb_sdk.schemas import Parameters
from rtb_sdk.constants import DataOptimizerType
from rtb_sdk.helpers.type_helpers import check_type
import rtb_sdk.errors.optimizer as com_err


# --- Getters ---

def get_parameters_parameters(params: Parameters,
                              default: dict[str, Any] | None = None) -> dict[str, Any] | None:
    return params.get("parameters", default)

def get_parameters_parameters_keys(params: Parameters) -> list[str]:
    parameters = get_parameters_parameters(params)
    if parameters is None:
        return []
    return list(parameters.keys())

# --- _is_valid: checking the type of a field value ---

def _is_valid_parameters_dict(params: Parameters) -> bool:
    if not check_type(params, DataOptimizerType.PARAMETERS):
        return False
    parameters = get_parameters_parameters(params)
    if not isinstance(parameters, dict):
        return False
    return all(isinstance(k, str) for k in get_parameters_parameters_keys(params))

CheckParametersList = [_is_valid_parameters_dict]

# --- _check: checking a field value for validity ---

def _check_fields_parameters(params: Parameters) -> bool:
    for check in CheckParametersList:
        if not check(params):
            return False
    return True

# --- Main validation and checking functions ---

def is_valid_parameters(params: Any) -> bool:
    if not check_type(params, DataOptimizerType.PARAMETERS):
        return False
    return _check_fields_parameters(params)

# --- Builder ---

def build_parameters(parameters: dict[str, Any] | None = None, **kwargs) -> Parameters:
    if parameters is None:
        parameters = {}
    res = {
        "parameters": parameters,
        "__type": DataOptimizerType.PARAMETERS
    }
    if is_valid_parameters(res):
        return cast(Parameters, res)
    else:
        raise com_err.OptimizerError(
            com_err.ErrorCodes.PARAMETER_ERROR_CODE,
            "Not valid parameters for Parameters"
        )

def build_parameters_from_dict(data: dict) -> Parameters:
    try:
        return build_parameters(**data)
    except Exception as e:
        raise com_err.OptimizerError(
            com_err.ErrorCodes.PARAMETER_ERROR_CODE,
            "Not valid parameters for Parameters"
        )
