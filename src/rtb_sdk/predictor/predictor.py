from typing import cast, Any

from rtb_sdk.constants import ModelTypeName
from rtb_sdk.schemas import (
    ModelOptions,
    CommonModel,
    TestResult,
    FitParams,
    PredictParams,
    TestParams,
    PredictResult,
)
from .prophet_model import (
    prophet_model_fit,
    prophet_model_predict,
    prophet_model_test,
)
from rtb_sdk.helpers.predictor import (
    create_fit_params_from_dict,
    create_model_options_from_dict,
    create_prophet_model_from_dict,
    create_prophet_model_predict_params_from_dict,
    create_prophet_model_test_params_from_dict,
    create_prophet_options_from_dict,
    get_model_options_model_type,
    is_valid_fit_params,
    is_valid_model_options,
    is_valid_predict_params,
    is_valid_test_params,
)
from rtb_sdk.errors.predictor import PredictorError, ErrorCodes


model_method_hash = {
    ModelTypeName.PROPHET: {
        'fit': prophet_model_fit,
        'predict': prophet_model_predict,
        'test': prophet_model_test,
        'options_builder': create_prophet_options_from_dict,
        'model_builder': create_prophet_model_from_dict,
        'predict_params_builder': create_prophet_model_predict_params_from_dict,
        'test_params_builder': create_prophet_model_test_params_from_dict,
    },
}


def _resolve_model_type(options: ModelOptions) -> str:
    common_options = create_model_options_from_dict(cast(dict[str, Any], options))
    model_type = get_model_options_model_type(common_options)
    if model_type not in model_method_hash:
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Unsupported model type"
        )
    return model_type


def fit(data: FitParams,
        options: ModelOptions,
        ) -> CommonModel:
    if not (is_valid_fit_params(data) and
            is_valid_model_options(options)):
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Invalid parameters for fit"
        )
    common_fit_params = create_fit_params_from_dict(cast(dict[str, Any], data))
    model_type = _resolve_model_type(options)
    model_type_options = model_method_hash[model_type]['options_builder'](options)
    return model_method_hash[model_type]['fit'](
        common_fit_params,
        model_type_options,
    )


def predict(model: CommonModel,
            options: ModelOptions,
            data: PredictParams) -> PredictResult:
    if not (is_valid_model_options(options) and
            is_valid_predict_params(data)):
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Invalid parameters for predict"
        )
    model_type = _resolve_model_type(options)
    model_type_options = model_method_hash[model_type]['options_builder'](options)
    model_type_model = model_method_hash[model_type]['model_builder'](model)
    model_type_predict_params = model_method_hash[model_type]['predict_params_builder'](data)
    return model_method_hash[model_type]['predict'](
        model_type_model,
        model_type_options,
        model_type_predict_params,
    )


def test(model: CommonModel,
         options: ModelOptions,
         data: TestParams) -> TestResult:
    """
    Checks the model on test data.
    Returns a TestResult with the training data, the expected values and the forecast.
    """
    if not (is_valid_model_options(options) and
            is_valid_test_params(data)):
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Invalid parameters for test"
        )
    model_type = _resolve_model_type(options)
    model_type_options = model_method_hash[model_type]['options_builder'](options)
    model_type_model = model_method_hash[model_type]['model_builder'](model)
    model_type_test_params = model_method_hash[model_type]['test_params_builder'](data)
    return model_method_hash[model_type]['test'](
        model_type_model,
        model_type_options,
        model_type_test_params,
    )
