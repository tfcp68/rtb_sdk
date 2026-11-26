from typing import Any, cast
from datetime import datetime

from rtb_sdk.schemas import TestResult
from rtb_sdk.schemas import Granularity
from rtb_sdk.errors.predictor import PredictorError, ErrorCodes
from rtb_sdk.constants.data_types import DataPredictorType
from rtb_sdk.helpers.type_helpers import check_predictor_type, _VALID_GRANULARITIES
from rtb_sdk.helpers.predictor.helpers_utils import (
    _is_valid_datetime_list,
    _is_valid_numeric_list,
    _dates_match_resolution,
    _is_valid_datetime_sequence,
)


# ─── TestResult ────────────────────────────────────────────────────────────────

def get_test_result_training_dates(result: TestResult,
                                   default: list[datetime] | None = None
                                   ) -> list[datetime] | None:
    return result.get("training_dates", default)


def get_test_result_training_values(result: TestResult,
                                    default: list[float] | None = None
                                    ) -> list[float] | None:
    return result.get("training_values", default)


def get_test_result_predict_dates(result: TestResult,
                                  default: list[datetime] | None = None
                                  ) -> list[datetime] | None:
    return result.get("predict_dates", default)


def get_test_result_predict_values(result: TestResult,
                                   default: list[float] | None = None
                                   ) -> list[float] | None:
    return result.get("predict_values", default)


def get_test_result_expected_values(result: TestResult,
                                    default: list[float] | None = None
                                    ) -> list[float] | None:
    return result.get("expected_values", default)


def get_test_result_resolution(result: TestResult,
                               default: Granularity | None = None
                               ) -> Granularity | None:
    return result.get("resolution", default)


def _is_valid_test_result_training_dates(result: TestResult) -> bool:
    if not check_predictor_type(result, DataPredictorType.TEST_RESULT):
        return False
    training_dates = get_test_result_training_dates(result)
    training_values = get_test_result_training_values(result)
    if not _is_valid_datetime_list(training_dates) or not training_dates:
        return False
    if not (isinstance(training_values, list) and len(training_dates) == len(training_values)):
        return False
    resolution = get_test_result_resolution(result)
    predict_dates = get_test_result_predict_dates(result)
    if isinstance(resolution, str) and resolution in _VALID_GRANULARITIES:
        if not _is_valid_datetime_sequence(training_dates, resolution):
            return False
        if (_is_valid_datetime_list(predict_dates) and predict_dates
                and not _dates_match_resolution(training_dates[-1], predict_dates[0], resolution)):
            return False
    return True


def _is_valid_test_result_training_values(result: TestResult) -> bool:
    if not check_predictor_type(result, DataPredictorType.TEST_RESULT):
        return False
    training_dates = get_test_result_training_dates(result)
    training_values = get_test_result_training_values(result)
    if not _is_valid_numeric_list(training_values):
        return False
    return isinstance(training_dates, list) and isinstance(training_values, list) and len(training_dates) == len(training_values)


def _is_valid_test_result_predict_dates(result: TestResult) -> bool:
    if not check_predictor_type(result, DataPredictorType.TEST_RESULT):
        return False
    predict_dates = get_test_result_predict_dates(result)
    predict_values = get_test_result_predict_values(result)
    expected_values = get_test_result_expected_values(result)
    if not _is_valid_datetime_list(predict_dates) or not predict_dates:
        return False
    if not (isinstance(predict_values, list) and len(predict_dates) == len(predict_values)):
        return False
    if not (isinstance(expected_values, list) and len(predict_dates) == len(expected_values)):
        return False
    resolution = get_test_result_resolution(result)
    training_dates = get_test_result_training_dates(result)
    if isinstance(resolution, str) and resolution in _VALID_GRANULARITIES:
        if not _is_valid_datetime_sequence(predict_dates, resolution):
            return False
        if (_is_valid_datetime_list(training_dates) and training_dates
                and not _dates_match_resolution(training_dates[-1], predict_dates[0], resolution)):
            return False
    return True


def _is_valid_test_result_predict_values(result: TestResult) -> bool:
    if not check_predictor_type(result, DataPredictorType.TEST_RESULT):
        return False
    predict_dates = get_test_result_predict_dates(result)
    predict_values = get_test_result_predict_values(result)
    if not _is_valid_numeric_list(predict_values):
        return False
    return isinstance(predict_dates, list) and isinstance(predict_values, list) and len(predict_dates) == len(predict_values)


def _is_valid_test_result_expected_values(result: TestResult) -> bool:
    if not check_predictor_type(result, DataPredictorType.TEST_RESULT):
        return False
    predict_dates = get_test_result_predict_dates(result)
    expected_values = get_test_result_expected_values(result)
    if not _is_valid_numeric_list(expected_values):
        return False
    return isinstance(predict_dates, list) and isinstance(expected_values, list) and len(predict_dates) == len(expected_values)


def _is_valid_test_result_resolution(result: TestResult) -> bool:
    if not check_predictor_type(result, DataPredictorType.TEST_RESULT):
        return False
    resolution = get_test_result_resolution(result)
    if not isinstance(resolution, str) or resolution not in _VALID_GRANULARITIES:
        return False
    training_dates = get_test_result_training_dates(result)
    predict_dates = get_test_result_predict_dates(result)
    if (_is_valid_datetime_list(training_dates) and training_dates
            and not _is_valid_datetime_sequence(training_dates, resolution)):
        return False
    if (_is_valid_datetime_list(predict_dates) and predict_dates
            and not _is_valid_datetime_sequence(predict_dates, resolution)):
        return False
    if (_is_valid_datetime_list(training_dates) and training_dates
            and _is_valid_datetime_list(predict_dates) and predict_dates
            and not _dates_match_resolution(training_dates[-1], predict_dates[0], resolution)):
        return False
    return True


CheckTestResultList = [
    _is_valid_test_result_training_dates,
    _is_valid_test_result_training_values,
    _is_valid_test_result_predict_dates,
    _is_valid_test_result_predict_values,
    _is_valid_test_result_expected_values,
    _is_valid_test_result_resolution,
]


def _check_fields_test_result(result: TestResult) -> bool:
    for check in CheckTestResultList:
        if not check(result):
            return False
    return True


def is_valid_test_result(result: Any) -> bool:
    if not check_predictor_type(result, DataPredictorType.TEST_RESULT):
        return False
    return _check_fields_test_result(result)


def create_test_result(training_dates: list[datetime],
                       training_values: list[float],
                       predict_dates: list[datetime],
                       predict_values: list[float],
                       expected_values: list[float],
                       resolution: Granularity,
                       **kwargs) -> TestResult:
    result = {
        "training_dates": training_dates,
        "training_values": training_values,
        "predict_dates": predict_dates,
        "predict_values": predict_values,
        "expected_values": expected_values,
        "resolution": resolution,
        "__type": DataPredictorType.TEST_RESULT,
    }
    if is_valid_test_result(result):
        return cast(TestResult, result)
    raise PredictorError(
        ErrorCodes.PARAMETER_ERROR_CODE,
        "Invalid parameters for TestResult"
    )


def create_test_result_from_dict(data: dict[str, Any]) -> TestResult:
    try:
        return create_test_result(**data)
    except Exception:
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Invalid parameters for TestResult"
        )
