from typing import Any, cast
from datetime import datetime

from rtb_sdk.schemas import TestParams
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


# ─── TestParams ────────────────────────────────────────────────────────────────

def get_test_params_training_dates(data: TestParams,
                                   default: list[datetime] | None = None
                                   ) -> list[datetime] | None:
    return data.get("training_dates", default)


def get_test_params_training_values(data: TestParams,
                                    default: list[float] | None = None
                                    ) -> list[float] | None:
    return data.get("training_values", default)


def get_test_params_expected_dates(data: TestParams,
                                   default: list[datetime] | None = None
                                   ) -> list[datetime] | None:
    return data.get("expected_dates", default)


def get_test_params_expected_values(data: TestParams,
                                    default: list[float] | None = None
                                    ) -> list[float] | None:
    return data.get("expected_values", default)


def get_test_params_resolution(data: TestParams,
                               default: Granularity | None = None
                               ) -> Granularity | None:
    return data.get("resolution", default)


def _check_test_params_type(data: TestParams) -> bool:
    return (check_predictor_type(data, DataPredictorType.TEST_PARAMS)
            or check_predictor_type(data, DataPredictorType.PROPHET_MODEL_TEST_PARAMS))


def _is_valid_test_params_training_dates(data: TestParams) -> bool:
    if not _check_test_params_type(data):
        return False
    training_dates = get_test_params_training_dates(data)
    training_values = get_test_params_training_values(data)
    if not _is_valid_datetime_list(training_dates) or not training_dates:
        return False
    if not (isinstance(training_values, list) and len(training_dates) == len(training_values)):
        return False
    resolution = get_test_params_resolution(data)
    if isinstance(resolution, str) and resolution in _VALID_GRANULARITIES:
        if not _is_valid_datetime_sequence(training_dates, resolution):
            return False
    return True


def _is_valid_test_params_training_values(data: TestParams) -> bool:
    if not _check_test_params_type(data):
        return False
    training_dates = get_test_params_training_dates(data)
    training_values = get_test_params_training_values(data)
    if not _is_valid_numeric_list(training_values):
        return False
    return isinstance(training_dates, list) and isinstance(training_values, list) and len(training_dates) == len(training_values)


def _is_valid_test_params_expected_dates(data: TestParams) -> bool:
    if not _check_test_params_type(data):
        return False
    expected_dates = get_test_params_expected_dates(data)
    expected_values = get_test_params_expected_values(data)
    training_dates = get_test_params_training_dates(data)
    resolution = get_test_params_resolution(data)
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


def _is_valid_test_params_expected_values(data: TestParams) -> bool:
    if not _check_test_params_type(data):
        return False
    expected_dates = get_test_params_expected_dates(data)
    expected_values = get_test_params_expected_values(data)
    if not _is_valid_numeric_list(expected_values):
        return False
    return isinstance(expected_dates, list) and isinstance(expected_values, list) and len(expected_dates) == len(expected_values)


def _is_valid_test_params_resolution(data: TestParams) -> bool:
    if not _check_test_params_type(data):
        return False
    resolution = get_test_params_resolution(data)
    if not isinstance(resolution, str) or resolution not in _VALID_GRANULARITIES:
        return False
    training_dates = get_test_params_training_dates(data)
    expected_dates = get_test_params_expected_dates(data)
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


CheckTestParamsList = [
    _is_valid_test_params_training_dates,
    _is_valid_test_params_training_values,
    _is_valid_test_params_expected_dates,
    _is_valid_test_params_expected_values,
    _is_valid_test_params_resolution,
]


def _check_fields_test_params(data: TestParams) -> bool:
    for check in CheckTestParamsList:
        if not check(data):
            return False
    return True


def is_valid_test_params(data: Any) -> bool:
    if not _check_test_params_type(data):
        return False
    return _check_fields_test_params(data)


def create_test_params(training_dates: list[datetime],
                       training_values: list[float],
                       expected_dates: list[datetime],
                       expected_values: list[float],
                       resolution: Granularity,
                       **kwargs) -> TestParams:
    result = {
        "training_dates": training_dates,
        "training_values": training_values,
        "expected_dates": expected_dates,
        "expected_values": expected_values,
        "resolution": resolution,
        "__type": DataPredictorType.TEST_PARAMS,
    }
    if is_valid_test_params(result):
        return cast(TestParams, result)
    raise PredictorError(
        ErrorCodes.PARAMETER_ERROR_CODE,
        "Invalid parameters for TestParams"
    )


def create_test_params_from_dict(data: dict[str, Any]) -> TestParams:
    try:
        return create_test_params(**data)
    except PredictorError:
        raise
    except Exception:
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Invalid parameters for TestParams"
        )
