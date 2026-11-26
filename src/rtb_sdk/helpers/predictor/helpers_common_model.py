from typing import Any, cast

from rtb_sdk.schemas import CommonModel, ModelType
from rtb_sdk.schemas import Granularity
from rtb_sdk.errors.predictor import PredictorError, ErrorCodes
from rtb_sdk.constants import ModelTypeName
from rtb_sdk.constants.data_types import DataPredictorType
from rtb_sdk.helpers.type_helpers import check_predictor_type, _VALID_GRANULARITIES
from rtb_sdk.helpers.predictor.helpers_utils import is_in_class


# ─── CommonModel ───────────────────────────────────────────────────────────────

def get_common_model_type(model: CommonModel,
                          default: ModelType | None = None
                          ) -> ModelType | None:
    return model.get("type", default)


def get_common_model_resolution(model: CommonModel,
                                default: Granularity | None = None
                                ) -> Granularity | None:
    return model.get("resolution", default)


def get_common_model_description(model: CommonModel,
                                 default: str | None = None
                                 ) -> str | None:
    return model.get("description", default)


def _check_common_model_type(model: CommonModel) -> bool:
    return (check_predictor_type(model, DataPredictorType.COMMON_MODEL)
            or check_predictor_type(model, DataPredictorType.PROPHET_MODEL))


def _is_valid_common_model_type(model: CommonModel) -> bool:
    if not _check_common_model_type(model):
        return False
    model_type = get_common_model_type(model)
    if not isinstance(model_type, str):
        return False
    return is_in_class(ModelTypeName, model_type)


def _is_valid_common_model_resolution(model: CommonModel) -> bool:
    if not _check_common_model_type(model):
        return False
    resolution = get_common_model_resolution(model)
    if not isinstance(resolution, str):
        return False
    return resolution in _VALID_GRANULARITIES


def _is_valid_common_model_description(model: CommonModel) -> bool:
    if not _check_common_model_type(model):
        return False
    description = get_common_model_description(model)
    return description is None or isinstance(description, str)


CheckCommonModelList = [
    _is_valid_common_model_type,
    _is_valid_common_model_resolution,
    _is_valid_common_model_description,
]


def _check_fields_common_model(model: CommonModel) -> bool:
    for check in CheckCommonModelList:
        if not check(model):
            return False
    return True


def is_valid_common_model(model: Any) -> bool:
    if not _check_common_model_type(model):
        return False
    return _check_fields_common_model(model)


def create_common_model(type: ModelType,
                        resolution: Granularity,
                        description: str | None = None,
                        **kwargs) -> CommonModel:
    result = {
        "type": type,
        "resolution": resolution,
        "description": description,
        "__type": DataPredictorType.COMMON_MODEL,
    }
    if is_valid_common_model(result):
        return cast(CommonModel, result)
    raise PredictorError(
        ErrorCodes.PARAMETER_ERROR_CODE,
        "Invalid parameters for CommonModel"
    )


def create_common_model_from_dict(data: dict[str, Any]) -> CommonModel:
    try:
        return create_common_model(**data)
    except Exception:
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Invalid parameters for CommonModel"
        )
