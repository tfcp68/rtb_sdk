from typing import Any, cast

from rtb_sdk.schemas import ModelOptions, ModelType
from rtb_sdk.errors.predictor import PredictorError, ErrorCodes
from rtb_sdk.constants import ModelTypeName
from rtb_sdk.constants.data_types import DataPredictorType
from rtb_sdk.helpers.type_helpers import check_predictor_type
from rtb_sdk.helpers.predictor.helpers_utils import is_in_class


# ─── ModelOptions ──────────────────────────────────────────────────────────────

def get_model_options_model_type(options: ModelOptions,
                                 default: ModelType | None = None
                                 ) -> ModelType | None:
    return options.get("model_type", default)


def _check_model_options_type(options: ModelOptions) -> bool:
    return (check_predictor_type(options, DataPredictorType.MODEL_OPTIONS)
            or check_predictor_type(options, DataPredictorType.PROPHET_OPTIONS))


def _is_valid_model_options_model_type(options: ModelOptions) -> bool:
    if not _check_model_options_type(options):
        return False
    model_type = get_model_options_model_type(options)
    if not isinstance(model_type, str):
        return False
    return is_in_class(ModelTypeName, model_type)


CheckModelOptionsList = [
    _is_valid_model_options_model_type,
]


def _check_fields_model_options(options: ModelOptions) -> bool:
    for check in CheckModelOptionsList:
        if not check(options):
            return False
    return True


def is_valid_model_options(options: Any) -> bool:
    if not _check_model_options_type(options):
        return False
    return _check_fields_model_options(options)


def create_model_options(model_type: ModelType,
                         **kwargs) -> ModelOptions:
    result = {
        "model_type": model_type,
        "__type": DataPredictorType.MODEL_OPTIONS,
    }
    if is_valid_model_options(result):
        return cast(ModelOptions, result)
    raise PredictorError(
        ErrorCodes.PARAMETER_ERROR_CODE,
        "Invalid parameters for ModelOptions"
    )


def create_model_options_from_dict(data: dict[str, Any]) -> ModelOptions:
    try:
        return create_model_options(**data)
    except Exception:
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Invalid parameters for ModelOptions"
        )
