"""JSON helpers and (de)serialization of the predictor schemas.

The low-level `_dumps`/`_loads`/`_parse_date_list` are also used
from the submodules of specific models (e.g. Prophet).
"""
import json
from typing import Any
from datetime import datetime

from rtb_sdk.schemas import (
    ModelOptions,
    CommonModel,
    FitParams,
    PredictResult,
    TestResult,
    TestMetrics,
)
from rtb_sdk.errors.predictor import PredictorError, ErrorCodes
from rtb_sdk.helpers.predictor.helpers_model_options import (
    is_valid_model_options,
    create_model_options_from_dict,
)
from rtb_sdk.helpers.predictor.helpers_common_model import (
    is_valid_common_model,
    create_common_model_from_dict,
)
from rtb_sdk.helpers.predictor.helpers_fit_params import (
    is_valid_fit_params,
    create_fit_params_from_dict,
)
from rtb_sdk.helpers.predictor.helpers_predict_result import (
    is_valid_predict_result,
    create_predict_result_from_dict,
)
from rtb_sdk.helpers.predictor.helpers_test_result import (
    is_valid_test_result,
    create_test_result_from_dict,
)
from rtb_sdk.helpers.predictor.helpers_test_metrics import (
    is_valid_test_metrics,
    create_test_metrics_from_dict,
)


# ─── Generic JSON helpers ──────────────────────────────────────────────────────

def _json_default(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _dumps(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, default=_json_default)
    except (TypeError, ValueError) as e:
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            f"Failed to serialize the scheme: {e}"
        )


def _loads(s: str) -> Any:
    try:
        return json.loads(s)
    except (TypeError, ValueError) as e:
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            f"Failed to deserialize the scheme: {e}"
        )


def _parse_date_list(v: Any) -> list[datetime]:
    if not isinstance(v, list):
        return v
    try:
        return [datetime.fromisoformat(d) if isinstance(d, str) else d for d in v]
    except (TypeError, ValueError) as e:
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            f"Date invalidity-timeline: {e}"
        )


# ─── ModelOptions ──────────────────────────────────────────────────────────────

def serialize_model_options(options: ModelOptions) -> str:
    if not is_valid_model_options(options):
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Invalid parameters for ModelOptions"
        )
    return _dumps(options)


def deserialize_model_options(data: str) -> ModelOptions:
    raw = _loads(data)
    if not isinstance(raw, dict):
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Invalid parameters for ModelOptions"
        )
    return create_model_options_from_dict(raw)


# ─── CommonModel ───────────────────────────────────────────────────────────────

def serialize_common_model(model: CommonModel) -> str:
    if not is_valid_common_model(model):
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Invalid parameters for CommonModel"
        )
    return _dumps(model)


def deserialize_common_model(data: str) -> CommonModel:
    raw = _loads(data)
    if not isinstance(raw, dict):
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Invalid parameters for CommonModel"
        )
    return create_common_model_from_dict(raw)


# ─── FitParams ─────────────────────────────────────────────────────────────────

def serialize_fit_params(data: FitParams) -> str:
    if not is_valid_fit_params(data):
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Invalid parameters for FitParams"
        )
    return _dumps(data)


def deserialize_fit_params(data: str) -> FitParams:
    raw = _loads(data)
    if not isinstance(raw, dict):
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Invalid parameters for FitParams"
        )
    if "dates" in raw:
        raw["dates"] = _parse_date_list(raw["dates"])
    return create_fit_params_from_dict(raw)


# ─── PredictResult ─────────────────────────────────────────────────────────────

def serialize_predict_result(result: PredictResult) -> str:
    if not is_valid_predict_result(result):
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Invalid parameters for PredictResult"
        )
    return _dumps(result)


def deserialize_predict_result(data: str) -> PredictResult:
    raw = _loads(data)
    if not isinstance(raw, dict):
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Invalid parameters for PredictResult"
        )
    for key in ("training_dates", "predict_dates"):
        if key in raw:
            raw[key] = _parse_date_list(raw[key])
    return create_predict_result_from_dict(raw)


# ─── TestResult ────────────────────────────────────────────────────────────────

def serialize_test_result(result: TestResult) -> str:
    if not is_valid_test_result(result):
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Invalid parameters for TestResult"
        )
    return _dumps(result)


def deserialize_test_result(data: str) -> TestResult:
    raw = _loads(data)
    if not isinstance(raw, dict):
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Invalid parameters for TestResult"
        )
    for key in ("training_dates", "predict_dates"):
        if key in raw:
            raw[key] = _parse_date_list(raw[key])
    return create_test_result_from_dict(raw)


# ─── TestMetrics ───────────────────────────────────────────────────────────────

def serialize_test_metrics(metrics: TestMetrics) -> str:
    if not is_valid_test_metrics(metrics):
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Invalid parameters for TestMetrics"
        )
    return _dumps(metrics)


def deserialize_test_metrics(data: str) -> TestMetrics:
    raw = _loads(data)
    if not isinstance(raw, dict):
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Invalid parameters for TestMetrics"
        )
    return create_test_metrics_from_dict(raw)