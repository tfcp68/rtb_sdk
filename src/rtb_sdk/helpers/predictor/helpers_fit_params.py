from typing import Any, cast
from datetime import datetime, timedelta
import polars as pl

from rtb_sdk.schemas import FitParams
from rtb_sdk.schemas import Granularity
from rtb_sdk.errors.predictor import PredictorError, ErrorCodes
from rtb_sdk.constants.data_types import DataPredictorType
from rtb_sdk.constants.frequencies_consts import TIMEDELTA_TO_GRAN
from rtb_sdk.helpers.type_helpers import check_predictor_type, _VALID_GRANULARITIES
from rtb_sdk.helpers.predictor.helpers_utils import (
    _is_valid_datetime_list,
    _is_valid_numeric_list,
    _is_valid_datetime_sequence,
    _parse_polars_datetime_column,
)


# ─── FitParams ─────────────────────────────────────────────────────────────────

def get_fit_params_dates(data: FitParams,
                         default: list[datetime] | None = None
                         ) -> list[datetime] | None:
    return data.get("dates", default)


def get_fit_params_values(data: FitParams,
                          default: list[float] | None = None
                          ) -> list[float] | None:
    return data.get("values", default)


def get_fit_params_resolution(data: FitParams,
                              default: Granularity | None = None
                              ) -> Granularity | None:
    return data.get("resolution", default)


def _is_valid_fit_params_dates(data: FitParams) -> bool:
    if not check_predictor_type(data, DataPredictorType.FIT_PARAMS):
        return False
    dates = get_fit_params_dates(data)
    values = get_fit_params_values(data)
    if not _is_valid_datetime_list(dates):
        return False
    return isinstance(dates, list) and isinstance(values, list) and len(dates) == len(values)


def _is_valid_fit_params_values(data: FitParams) -> bool:
    if not check_predictor_type(data, DataPredictorType.FIT_PARAMS):
        return False
    dates = get_fit_params_dates(data)
    values = get_fit_params_values(data)
    if not _is_valid_numeric_list(values):
        return False
    return isinstance(dates, list) and isinstance(values, list) and len(dates) == len(values)


def _is_valid_fit_params_resolution(data: FitParams) -> bool:
    if not check_predictor_type(data, DataPredictorType.FIT_PARAMS):
        return False
    resolution = get_fit_params_resolution(data)
    if not isinstance(resolution, str) or resolution not in _VALID_GRANULARITIES:
        return False
    dates = get_fit_params_dates(data)
    if not _is_valid_datetime_list(dates):
        return False
    return isinstance(dates, list) and _is_valid_datetime_sequence(dates, resolution)


CheckFitParamsList = [
    _is_valid_fit_params_dates,
    _is_valid_fit_params_values,
    _is_valid_fit_params_resolution,
]


def _check_fields_fit_params(data: FitParams) -> bool:
    for check in CheckFitParamsList:
        if not check(data):
            return False
    return True


def is_valid_fit_params(data: Any) -> bool:
    if not check_predictor_type(data, DataPredictorType.FIT_PARAMS):
        return False
    return _check_fields_fit_params(data)


def create_fit_params(dates: list[datetime],
                      values: list[float],
                      resolution: Granularity,
                      **kwargs) -> FitParams:
    result = {
        "dates": dates,
        "values": values,
        "resolution": resolution,
        "__type": DataPredictorType.FIT_PARAMS,
    }
    if is_valid_fit_params(result):
        return cast(FitParams, result)
    raise PredictorError(
        ErrorCodes.PARAMETER_ERROR_CODE,
        "Invalid parameters for FitParams"
    )


def create_fit_params_from_dict(data: dict[str, Any]) -> FitParams:
    try:
        return create_fit_params(**data)
    except Exception:
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Invalid parameters for FitParams"
        )


# ─── FitParams: Polars / Granularity helpers ──────────────────────────────────

def create_from_timedelta(delta_time: timedelta) -> Granularity:
    if delta_time < timedelta(days=28):
        try:
            return cast(Granularity, TIMEDELTA_TO_GRAN[delta_time])
        except Exception:
            raise PredictorError(
                ErrorCodes.PARAMETER_ERROR_CODE,
                "Unsupported recording frequency format"
            )
    elif delta_time < timedelta(days=32):
        return 'm'
    raise PredictorError(
        ErrorCodes.PARAMETER_ERROR_CODE,
        "Unsupported recording frequency format"
    )


def create_fit_params_from_polars_df(df: pl.DataFrame,
                                     date_column: str,
                                     value_column: str) -> FitParams:
    if not isinstance(df, pl.DataFrame):
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Invalid parameters for FitParams"
        )
    if date_column not in df.columns or value_column not in df.columns:
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Invalid parameters for FitParams"
        )
    try:
        prepared = (
            df.select([date_column, value_column])
            .with_columns(_parse_polars_datetime_column(df, date_column).alias(date_column))
            .with_columns(pl.col(value_column).cast(pl.Float64, strict=False))
            .sort(date_column)
        )
        dates = prepared[date_column].to_list()
        values = prepared[value_column].to_list()
        if len(dates) < 2:
            raise PredictorError(
                ErrorCodes.PARAMETER_ERROR_CODE,
                "Invalid parameters for FitParams: At least two valid lines are required"
            )
        if not _is_valid_datetime_list(dates) or not _is_valid_numeric_list(values):
            raise PredictorError(
                ErrorCodes.PARAMETER_ERROR_CODE,
                "Invalid parameters for FitParams: wrong-date, significance, null, NaN or infinity"
            )
        dt = dates[0] - dates[1] if dates[0] > dates[1] else dates[1] - dates[0]
        resolution = create_from_timedelta(dt)
        return create_fit_params(dates, values, resolution)
    except Exception:
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Invalid parameters for FitParams"
        )


def fit_params_to_polars(data: FitParams,
                         date_column: str,
                         value_column: str) -> pl.DataFrame:
    d = create_fit_params_from_dict(cast(dict[str, Any], data))
    return pl.DataFrame({
        date_column: get_fit_params_dates(d),
        value_column: get_fit_params_values(d),
    })
