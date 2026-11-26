from datetime import datetime
from typing import Any, Optional, cast

from prophet import Prophet
from prophet.serialize import model_to_json, model_from_json

from rtb_sdk.schemas import (
    ProphetModel,
    ProphetModelPredictParams,
    ProphetModelTestParams,
)
from rtb_sdk.schemas import Granularity, ModelType
from rtb_sdk.constants import ModelTypeName
from rtb_sdk.constants.data_types import DataPredictorType
from rtb_sdk.helpers.type_helpers import check_predictor_type, _VALID_GRANULARITIES
from rtb_sdk.helpers.predictor.helpers_utils import (
    is_in_class,
    _is_valid_datetime_list,
    _is_valid_numeric_list,
    _is_valid_datetime_sequence,
    _dates_match_resolution,
)
from rtb_sdk.helpers.predictor.serialization import (
    _dumps,
    _loads,
    _parse_date_list,
)
from rtb_sdk.errors.predictor import PredictorError, ErrorCodes


# ─── Internal trained Prophet state (the `Prophet` object) ─────────────────

def _is_valid_fitted_state(state: Any) -> bool:
    """Checks that the object is a trained `Prophet` model.

    After `Prophet.fit(...)` the `history` attribute is set to the training
    DataFrame; before fit it is `None`.
    """
    return isinstance(state, Prophet) and getattr(state, "history", None) is not None


def _format_fitted_state(state: Any) -> str:
    """Serializes a trained Prophet model into a JSON string via its built-in mechanism."""
    if not _is_valid_fitted_state(state):
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Invalid parameters for ProphetModel.model"
        )
    try:
        return model_to_json(state)
    except Exception as e:
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            f"Failed to serialize the model Prophet: {e}"
        )


def _restore_fitted_state(payload: Any) -> Prophet:
    """Restores a Prophet model from a JSON string or a dict.

    `model_from_json` expects a string; if a dict arrives as input (e.g.
    after a full `json.loads` of ProphetModel), we pack it back into a string.
    """
    if isinstance(payload, Prophet):
        return payload
    if isinstance(payload, dict):
        payload = _dumps(payload)
    if not isinstance(payload, str):
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Invalid parameters for ProphetModel.model"
        )
    try:
        restored = model_from_json(payload)
    except Exception as e:
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            f"It was not possible to deserialize the model Prophet"
        )
    if not _is_valid_fitted_state(restored):
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Invalid parameters for ProphetModel.model"
        )
    return restored


# ─── ProphetModel ──────────────────────────────────────────────────────────────

def get_prophet_model_type(model: ProphetModel,
                           default: ModelType | None = None
                           ) -> ModelType | None:
    return model.get("type", default)


def get_prophet_model_resolution(model: ProphetModel,
                                 default: Granularity | None = None
                                 ) -> Granularity | None:
    return model.get("resolution", default)


def get_prophet_model_description(model: ProphetModel,
                                  default: str | None = None
                                  ) -> str | None:
    return model.get("description", default)


def get_prophet_model_model(model: ProphetModel,
                            default: Prophet | None = None
                            ) -> Prophet | None:
    return model.get("model", default)


def _is_valid_prophet_model_type(model: ProphetModel) -> bool:
    if not check_predictor_type(model, DataPredictorType.PROPHET_MODEL):
        return False
    model_type = get_prophet_model_type(model)
    if not isinstance(model_type, str):
        return False
    return is_in_class(ModelTypeName, model_type) and model_type == ModelTypeName.PROPHET


def _is_valid_prophet_model_resolution(model: ProphetModel) -> bool:
    if not check_predictor_type(model, DataPredictorType.PROPHET_MODEL):
        return False
    resolution = get_prophet_model_resolution(model)
    return isinstance(resolution, str) and resolution in _VALID_GRANULARITIES


def _is_valid_prophet_model_description(model: ProphetModel) -> bool:
    if not check_predictor_type(model, DataPredictorType.PROPHET_MODEL):
        return False
    description = get_prophet_model_description(model)
    return description is None or isinstance(description, str)


def _is_valid_prophet_model_model(model: ProphetModel) -> bool:
    if not check_predictor_type(model, DataPredictorType.PROPHET_MODEL):
        return False
    return _is_valid_fitted_state(get_prophet_model_model(model))


CheckProphetModelList = [
    _is_valid_prophet_model_type,
    _is_valid_prophet_model_resolution,
    _is_valid_prophet_model_description,
    _is_valid_prophet_model_model,
]


def _check_fields_prophet_model(model: ProphetModel) -> bool:
    for check in CheckProphetModelList:
        if not check(model):
            return False
    return True


def is_valid_prophet_model(model: Any) -> bool:
    if not check_predictor_type(model, DataPredictorType.PROPHET_MODEL):
        return False
    return _check_fields_prophet_model(model)


def create_prophet_model(model: Prophet,
                         resolution: Granularity,
                         description: Optional[str] = None,
                         **kwargs) -> ProphetModel:
    result = {
        "type": "prophet",
        "resolution": resolution,
        "description": description,
        "model": model,
        "__type": DataPredictorType.PROPHET_MODEL,
    }
    if is_valid_prophet_model(result):
        return cast(ProphetModel, result)
    raise PredictorError(
        ErrorCodes.PARAMETER_ERROR_CODE,
        "Invalid parameters for ProphetModel"
    )


def create_prophet_model_from_dict(data: dict[str, Any]) -> ProphetModel:
    try:
        return create_prophet_model(**data)
    except Exception:
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Invalid parameters for ProphetModel"
        )


def serialize_prophet_model(model: ProphetModel) -> str:
    if not is_valid_prophet_model(model):
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Invalid parameters for ProphetModel"
        )
    out = dict(model)
    out["model"] = _format_fitted_state(get_prophet_model_model(model))
    return _dumps(out)


def deserialize_prophet_model(data: str) -> ProphetModel:
    raw = _loads(data)
    if not isinstance(raw, dict):
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Invalid parameters for ProphetModel"
        )
    if "model" in raw:
        raw["model"] = _restore_fitted_state(raw["model"])
    return create_prophet_model_from_dict(raw)


# ─── ProphetModelPredictParams ─────────────────────────────────────────────────

def get_prophet_model_predict_params_resolution(predict_params: ProphetModelPredictParams,
                                                default: Granularity | None = None
                                                ) -> Granularity | None:
    return predict_params.get("resolution", default)


def get_prophet_model_predict_params_forecast_periods(predict_params: ProphetModelPredictParams,
                                                      default: int | None = None
                                                      ) -> int | None:
    return predict_params.get("forecast_periods", default)


def _is_valid_prophet_model_predict_params_resolution(data: ProphetModelPredictParams) -> bool:
    if not check_predictor_type(data, DataPredictorType.PROPHET_MODEL_PREDICT_PARAMS):
        return False
    resolution = get_prophet_model_predict_params_resolution(data)
    return isinstance(resolution, str) and resolution in _VALID_GRANULARITIES


def _is_valid_prophet_model_predict_params_forecast_periods(data: ProphetModelPredictParams) -> bool:
    if not check_predictor_type(data, DataPredictorType.PROPHET_MODEL_PREDICT_PARAMS):
        return False
    forecast_periods = get_prophet_model_predict_params_forecast_periods(data)
    return isinstance(forecast_periods, int) and forecast_periods > 0


CheckProphetModelPredictParamsList = [
    _is_valid_prophet_model_predict_params_resolution,
    _is_valid_prophet_model_predict_params_forecast_periods,
]


def _check_fields_prophet_model_predict_params(data: ProphetModelPredictParams) -> bool:
    for check in CheckProphetModelPredictParamsList:
        if not check(data):
            return False
    return True


def is_valid_prophet_model_predict_params(data: Any) -> bool:
    if not check_predictor_type(data, DataPredictorType.PROPHET_MODEL_PREDICT_PARAMS):
        return False
    return _check_fields_prophet_model_predict_params(data)


def create_prophet_model_predict_params(resolution: Granularity,
                                        forecast_periods: int,
                                        **kwargs) -> ProphetModelPredictParams:
    result = {
        "resolution": resolution,
        "forecast_periods": forecast_periods,
        "__type": DataPredictorType.PROPHET_MODEL_PREDICT_PARAMS,
    }
    if is_valid_prophet_model_predict_params(result):
        return cast(ProphetModelPredictParams, result)
    raise PredictorError(
        ErrorCodes.PARAMETER_ERROR_CODE,
        "Invalid parameters for ProphetModelPredictParams"
    )


def create_prophet_model_predict_params_from_dict(data: dict[str, Any]) -> ProphetModelPredictParams:
    try:
        return create_prophet_model_predict_params(**data)
    except Exception:
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Invalid parameters for ProphetModelPredictParams"
        )


def serialize_prophet_model_predict_params(data: ProphetModelPredictParams) -> str:
    if not is_valid_prophet_model_predict_params(data):
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Invalid parameters for ProphetModelPredictParams"
        )
    return _dumps(data)


def deserialize_prophet_model_predict_params(data: str) -> ProphetModelPredictParams:
    raw = _loads(data)
    if not isinstance(raw, dict):
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Invalid parameters for ProphetModelPredictParams"
        )
    return create_prophet_model_predict_params_from_dict(raw)


# ─── ProphetModelTestParams ────────────────────────────────────────────────────

def get_prophet_model_test_params_training_dates(data: ProphetModelTestParams,
                                                 default: list[datetime] | None = None
                                                 ) -> list[datetime] | None:
    return data.get("training_dates", default)


def get_prophet_model_test_params_training_values(data: ProphetModelTestParams,
                                                  default: list[float] | None = None
                                                  ) -> list[float] | None:
    return data.get("training_values", default)


def get_prophet_model_test_params_expected_dates(data: ProphetModelTestParams,
                                                 default: list[datetime] | None = None
                                                 ) -> list[datetime] | None:
    return data.get("expected_dates", default)


def get_prophet_model_test_params_expected_values(data: ProphetModelTestParams,
                                                  default: list[float] | None = None
                                                  ) -> list[float] | None:
    return data.get("expected_values", default)


def get_prophet_model_test_params_resolution(data: ProphetModelTestParams,
                                             default: Granularity | None = None
                                             ) -> Granularity | None:
    return data.get("resolution", default)


def _is_valid_prophet_model_test_params_training_dates(data: ProphetModelTestParams) -> bool:
    if not check_predictor_type(data, DataPredictorType.PROPHET_MODEL_TEST_PARAMS):
        return False
    training_dates = get_prophet_model_test_params_training_dates(data)
    training_values = get_prophet_model_test_params_training_values(data)
    if not _is_valid_datetime_list(training_dates) or not training_dates:
        return False
    if not (isinstance(training_values, list) and len(training_dates) == len(training_values)):
        return False
    resolution = get_prophet_model_test_params_resolution(data)
    if isinstance(resolution, str) and resolution in _VALID_GRANULARITIES:
        if not _is_valid_datetime_sequence(training_dates, resolution):
            return False
    return True


def _is_valid_prophet_model_test_params_training_values(data: ProphetModelTestParams) -> bool:
    if not check_predictor_type(data, DataPredictorType.PROPHET_MODEL_TEST_PARAMS):
        return False
    training_dates = get_prophet_model_test_params_training_dates(data)
    training_values = get_prophet_model_test_params_training_values(data)
    if not _is_valid_numeric_list(training_values):
        return False
    return isinstance(training_dates, list) and isinstance(training_values, list) and len(training_dates) == len(training_values)


def _is_valid_prophet_model_test_params_expected_dates(data: ProphetModelTestParams) -> bool:
    if not check_predictor_type(data, DataPredictorType.PROPHET_MODEL_TEST_PARAMS):
        return False
    expected_dates = get_prophet_model_test_params_expected_dates(data)
    expected_values = get_prophet_model_test_params_expected_values(data)
    training_dates = get_prophet_model_test_params_training_dates(data)
    resolution = get_prophet_model_test_params_resolution(data)
    if not _is_valid_datetime_list(expected_dates) or not expected_dates:
        return False
    if not (isinstance(expected_values, list) and len(expected_dates) == len(expected_values)):
        return False
    if isinstance(resolution, str) and resolution in _VALID_GRANULARITIES:
        if not _is_valid_datetime_sequence(expected_dates, resolution):
            return False
        if (_is_valid_datetime_list(training_dates) and training_dates
                and not _dates_match_resolution(training_dates[-1], expected_dates[0], resolution)):
            return False
    return True


def _is_valid_prophet_model_test_params_expected_values(data: ProphetModelTestParams) -> bool:
    if not check_predictor_type(data, DataPredictorType.PROPHET_MODEL_TEST_PARAMS):
        return False
    expected_dates = get_prophet_model_test_params_expected_dates(data)
    expected_values = get_prophet_model_test_params_expected_values(data)
    if not _is_valid_numeric_list(expected_values):
        return False
    return isinstance(expected_dates, list) and isinstance(expected_values, list) and len(expected_dates) == len(expected_values)


def _is_valid_prophet_model_test_params_resolution(data: ProphetModelTestParams) -> bool:
    if not check_predictor_type(data, DataPredictorType.PROPHET_MODEL_TEST_PARAMS):
        return False
    resolution = get_prophet_model_test_params_resolution(data)
    if not isinstance(resolution, str) or resolution not in _VALID_GRANULARITIES:
        return False
    training_dates = get_prophet_model_test_params_training_dates(data)
    expected_dates = get_prophet_model_test_params_expected_dates(data)
    if (_is_valid_datetime_list(training_dates) and training_dates
            and not _is_valid_datetime_sequence(training_dates, resolution)):
        return False
    if (_is_valid_datetime_list(expected_dates) and expected_dates
            and not _is_valid_datetime_sequence(expected_dates, resolution)):
        return False
    if (_is_valid_datetime_list(training_dates) and training_dates
            and _is_valid_datetime_list(expected_dates) and expected_dates
            and not _dates_match_resolution(training_dates[-1], expected_dates[0], resolution)):
        return False
    return True


CheckProphetModelTestParamsList = [
    _is_valid_prophet_model_test_params_training_dates,
    _is_valid_prophet_model_test_params_training_values,
    _is_valid_prophet_model_test_params_expected_dates,
    _is_valid_prophet_model_test_params_expected_values,
    _is_valid_prophet_model_test_params_resolution,
]


def _check_fields_prophet_model_test_params(data: ProphetModelTestParams) -> bool:
    for check in CheckProphetModelTestParamsList:
        if not check(data):
            return False
    return True


def is_valid_prophet_model_test_params(data: Any) -> bool:
    if not check_predictor_type(data, DataPredictorType.PROPHET_MODEL_TEST_PARAMS):
        return False
    return _check_fields_prophet_model_test_params(data)


def create_prophet_model_test_params(training_dates: list[datetime],
                                     training_values: list[float],
                                     expected_dates: list[datetime],
                                     expected_values: list[float],
                                     resolution: Granularity,
                                     **kwargs) -> ProphetModelTestParams:
    result = {
        "training_dates": training_dates,
        "training_values": training_values,
        "expected_dates": expected_dates,
        "expected_values": expected_values,
        "resolution": resolution,
        "__type": DataPredictorType.PROPHET_MODEL_TEST_PARAMS,
    }
    if is_valid_prophet_model_test_params(result):
        return cast(ProphetModelTestParams, result)
    raise PredictorError(
        ErrorCodes.PARAMETER_ERROR_CODE,
        "Invalid parameters for ProphetModelTestParams"
    )


def create_prophet_model_test_params_from_dict(data: dict[str, Any]) -> ProphetModelTestParams:
    try:
        return create_prophet_model_test_params(**data)
    except Exception:
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Invalid parameters for ProphetModelTestParams"
        )


def serialize_prophet_model_test_params(data: ProphetModelTestParams) -> str:
    if not is_valid_prophet_model_test_params(data):
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Invalid parameters for ProphetModelTestParams"
        )
    return _dumps(data)


def deserialize_prophet_model_test_params(data: str) -> ProphetModelTestParams:
    raw = _loads(data)
    if not isinstance(raw, dict):
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Invalid parameters for ProphetModelTestParams"
        )
    for key in ("training_dates", "expected_dates"):
        if key in raw:
            raw[key] = _parse_date_list(raw[key])
    return create_prophet_model_test_params_from_dict(raw)