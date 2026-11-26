from typing import Any, cast
from datetime import datetime

from rtb_sdk.schemas import PredictResult
from rtb_sdk.errors.predictor import PredictorError, ErrorCodes
from rtb_sdk.constants.data_types import DataPredictorType
from rtb_sdk.helpers.type_helpers import check_predictor_type
from rtb_sdk.helpers.predictor.helpers_utils import (
    _is_valid_datetime_list,
    _is_valid_numeric_list,
)


# ─── PredictResult ─────────────────────────────────────────────────────────────

def get_predict_result_training_dates(result: PredictResult,
                                      default: list[datetime] | None = None
                                      ) -> list[datetime] | None:
    return result.get("training_dates", default)


def get_predict_result_training_values(result: PredictResult,
                                       default: list[float] | None = None
                                       ) -> list[float] | None:
    return result.get("training_values", default)


def get_predict_result_predict_dates(result: PredictResult,
                                     default: list[datetime] | None = None
                                     ) -> list[datetime] | None:
    return result.get("predict_dates", default)


def get_predict_result_predict_values(result: PredictResult,
                                      default: list[float] | None = None
                                      ) -> list[float] | None:
    return result.get("predict_values", default)


def _is_valid_predict_result_training_dates(result: PredictResult) -> bool:
    if not check_predictor_type(result, DataPredictorType.PREDICT_RESULT):
        return False
    dates = get_predict_result_training_dates(result)
    values = get_predict_result_training_values(result)
    if not _is_valid_datetime_list(dates):
        return False
    return isinstance(dates, list) and isinstance(values, list) and len(dates) == len(values)


def _is_valid_predict_result_training_values(result: PredictResult) -> bool:
    if not check_predictor_type(result, DataPredictorType.PREDICT_RESULT):
        return False
    dates = get_predict_result_training_dates(result)
    values = get_predict_result_training_values(result)
    if not _is_valid_numeric_list(values):
        return False
    return isinstance(dates, list) and isinstance(values, list) and len(dates) == len(values)


def _is_valid_predict_result_predict_dates(result: PredictResult) -> bool:
    if not check_predictor_type(result, DataPredictorType.PREDICT_RESULT):
        return False
    dates = get_predict_result_predict_dates(result)
    values = get_predict_result_predict_values(result)
    if not _is_valid_datetime_list(dates):
        return False
    return isinstance(dates, list) and isinstance(values, list) and len(dates) == len(values)


def _is_valid_predict_result_predict_values(result: PredictResult) -> bool:
    if not check_predictor_type(result, DataPredictorType.PREDICT_RESULT):
        return False
    dates = get_predict_result_predict_dates(result)
    values = get_predict_result_predict_values(result)
    if not _is_valid_numeric_list(values):
        return False
    return isinstance(dates, list) and isinstance(values, list) and len(dates) == len(values)


CheckPredictResultList = [
    _is_valid_predict_result_training_dates,
    _is_valid_predict_result_training_values,
    _is_valid_predict_result_predict_dates,
    _is_valid_predict_result_predict_values,
]


def _check_fields_predict_result(result: PredictResult) -> bool:
    for check in CheckPredictResultList:
        if not check(result):
            return False
    return True


def is_valid_predict_result(result: Any) -> bool:
    if not check_predictor_type(result, DataPredictorType.PREDICT_RESULT):
        return False
    return _check_fields_predict_result(result)


def create_predict_result(training_dates: list[datetime],
                          training_values: list[float],
                          predict_dates: list[datetime],
                          predict_values: list[float],
                          **kwargs) -> PredictResult:
    result = {
        "training_dates": training_dates,
        "training_values": training_values,
        "predict_dates": predict_dates,
        "predict_values": predict_values,
        "__type": DataPredictorType.PREDICT_RESULT,
    }
    if is_valid_predict_result(result):
        return cast(PredictResult, result)
    raise PredictorError(
        ErrorCodes.PARAMETER_ERROR_CODE,
        "Invalid parameters for PredictResult"
    )


def create_predict_result_from_dict(data: dict[str, Any]) -> PredictResult:
    try:
        return create_predict_result(**data)
    except Exception:
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Invalid parameters for PredictResult"
        )
