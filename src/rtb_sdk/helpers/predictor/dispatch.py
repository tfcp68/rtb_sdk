from typing import Any, Callable, cast

from rtb_sdk.schemas import (
    ModelOptions,
    CommonModel,
    PredictParams,
    TestParams,
    ModelType,
)
from rtb_sdk.constants import ModelTypeName
from rtb_sdk.errors.predictor import PredictorError, ErrorCodes
from rtb_sdk.helpers.predictor.helpers_model_options import (
    create_model_options_from_dict,
    get_model_options_model_type,
)
from rtb_sdk.helpers.predictor.helpers_common_model import (
    create_common_model_from_dict,
    get_common_model_type,
)
from rtb_sdk.helpers.predictor.serialization import _loads
from rtb_sdk.helpers.predictor.models.prophet_model import (
    create_prophet_options_from_dict,
    serialize_prophet_options,
    deserialize_prophet_options,
    create_prophet_model_from_dict,
    serialize_prophet_model,
    deserialize_prophet_model,
    create_prophet_model_predict_params_from_dict,
    serialize_prophet_model_predict_params,
    deserialize_prophet_model_predict_params,
    create_prophet_model_test_params_from_dict,
    serialize_prophet_model_test_params,
    deserialize_prophet_model_test_params,
)


# ─── Dispatch tables ───────────────────────────────────────────────────────────

PREDICTOR_OPTIONS_METHODS: dict[ModelType, dict[str, Callable[..., Any]]] = {
    ModelTypeName.PROPHET: {
        "builder": create_prophet_options_from_dict,
        "serialize": serialize_prophet_options,
        "deserialize": deserialize_prophet_options,
    },
}

PREDICTOR_MODEL_SERIALIZATION_METHODS: dict[ModelType, dict[str, Callable[..., Any]]] = {
    ModelTypeName.PROPHET: {
        "builder": create_prophet_model_from_dict,
        "serialize": serialize_prophet_model,
        "deserialize": deserialize_prophet_model,
    },
}

PREDICTOR_PREDICT_PARAMS_METHODS: dict[ModelType, dict[str, Callable[..., Any]]] = {
    ModelTypeName.PROPHET: {
        "builder": create_prophet_model_predict_params_from_dict,
        "serialize": serialize_prophet_model_predict_params,
        "deserialize": deserialize_prophet_model_predict_params,
    },
}

PREDICTOR_TEST_PARAMS_METHODS: dict[ModelType, dict[str, Callable[..., Any]]] = {
    ModelTypeName.PROPHET: {
        "builder": create_prophet_model_test_params_from_dict,
        "serialize": serialize_prophet_model_test_params,
        "deserialize": deserialize_prophet_model_test_params,
    },
}


def _dispatch_model_methods(methods: dict[ModelType, dict[str, Callable[..., Any]]],
                            model_type: Any,
                            dispatch_name: str) -> dict[str, Any]:
    if model_type not in methods:
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            f"No dispatcher {dispatch_name} model: {model_type}"
        )
    return methods[model_type]


def _dispatch_options_methods(model_type: ModelType) -> dict[str, Callable[..., Any]]:
    return _dispatch_model_methods(PREDICTOR_OPTIONS_METHODS, model_type, "options")


def _dispatch_model_serialization_methods(model_type: ModelType) -> dict[str, Callable[..., Any]]:
    return _dispatch_model_methods(PREDICTOR_MODEL_SERIALIZATION_METHODS, model_type, "model")


def _dispatch_predict_params_methods(model_type: ModelType) -> dict[str, Callable[..., Any]]:
    return _dispatch_model_methods(PREDICTOR_PREDICT_PARAMS_METHODS, model_type, "predict_params")


def _dispatch_test_params_methods(model_type: ModelType) -> dict[str, Callable[..., Any]]:
    return _dispatch_model_methods(PREDICTOR_TEST_PARAMS_METHODS, model_type, "test_params")


def _resolve_model_type_from_options(options: ModelOptions) -> ModelType | None:
    common_options = create_model_options_from_dict(cast(dict[str, Any], options))
    return get_model_options_model_type(common_options)


# ─── Common serializers by `model_type` ───────────────────────────────────────

def serialize_options(options: ModelOptions) -> str:
    model_type = _resolve_model_type_from_options(options)
    if model_type is None:
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "No model type in the options, It is not possible to choose a serial manager"
        )
    dispatch = _dispatch_options_methods(model_type)
    specific_options = dispatch["builder"](options)
    return dispatch["serialize"](specific_options)


def deserialize_options(data: str) -> ModelOptions:
    raw = _loads(data)
    if not isinstance(raw, dict):
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Disabled parameters for the scheme"
        )
    model_type = _resolve_model_type_from_options(cast(ModelOptions, raw))
    if model_type is None:
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "No model type in the options, It is not possible to choose a serial manager"
        )
    dispatch = _dispatch_options_methods(model_type)
    return dispatch["builder"](raw)


def serialize_model(model: CommonModel) -> str:
    common_model = create_common_model_from_dict(cast(dict[str, Any], model))
    model_type = get_common_model_type(common_model)
    if model_type is None:
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "No model type in the options, It is not possible to choose a serial manager"
        )
    dispatch = _dispatch_model_serialization_methods(model_type)
    specific_model = dispatch["builder"](model)
    return dispatch["serialize"](specific_model)


def deserialize_model(data: str) -> CommonModel:
    raw = _loads(data)
    if not isinstance(raw, dict):
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Disabled parameters for the scheme"
        )
    common_model = create_common_model_from_dict(raw)
    model_type = get_common_model_type(common_model)
    if model_type is None:
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "No model type in the options, It is not possible to choose a serial manager"
        )
    dispatch = _dispatch_model_serialization_methods(model_type)
    return dispatch["deserialize"](data)


def serialize_predict_params(data: PredictParams,
                             options: ModelOptions) -> str:
    if not isinstance(data, dict):
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Disabled parameters for the scheme"
        )
    raw = data
    model_type = _resolve_model_type_from_options(options)
    if model_type is None:
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "No model type in the options, It is not possible to choose a serial manager"
        )
    dispatch = _dispatch_predict_params_methods(model_type)
    specific_params = dispatch["builder"](raw)
    return dispatch["serialize"](specific_params)


def deserialize_predict_params(data: str,
                               options: ModelOptions) -> PredictParams:
    raw = _loads(data)
    if not isinstance(raw, dict):
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Disabled parameters for the scheme"
        )
    model_type = _resolve_model_type_from_options(options)
    if model_type is None:
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "No model type in the options, It is not possible to choose a serial manager"
        )
    dispatch = _dispatch_predict_params_methods(model_type)
    return dispatch["deserialize"](data)


def serialize_test_params(data: TestParams,
                          options: ModelOptions) -> str:
    if not isinstance(data, dict):
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Disabled parameters for the scheme"
        )
    raw = data
    model_type = _resolve_model_type_from_options(options)
    if model_type is None:
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "No model type in the options, It is not possible to choose a serial manager"
        )
    dispatch = _dispatch_test_params_methods(model_type)
    specific_params = dispatch["builder"](raw)
    return dispatch["serialize"](specific_params)


def deserialize_test_params(data: str,
                            options: ModelOptions) -> TestParams:
    raw = _loads(data)
    if not isinstance(raw, dict):
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Disabled parameters for the scheme"
        )
    model_type = _resolve_model_type_from_options(options)
    if model_type is None:
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "No model type in the options, It is not possible to choose a serial manager"
        )
    dispatch = _dispatch_test_params_methods(model_type)
    return dispatch["deserialize"](data)