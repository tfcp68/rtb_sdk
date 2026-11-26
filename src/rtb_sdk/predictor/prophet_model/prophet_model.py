"""
Prophet time series model.

Uses the `prophet` library: on training a `Prophet` object is created,
and `fit` is called on it; on forecasting — `make_future_dataframe` + `predict`.
Model serialization is done via `prophet.serialize.{model_to_json,
model_from_json}` — it is encapsulated in `helpers/predictor/models/prophet_model`.
"""
from datetime import datetime
from typing import cast, Any

import polars as pl
from prophet import Prophet

from rtb_sdk.schemas import Granularity
from rtb_sdk.schemas import (
    ProphetOptions,
    FitParams,
    ProphetModel,
    ProphetModelPredictParams,
    PredictResult,
    TestParams,
    TestResult,
)
from rtb_sdk.helpers.predictor import (
    # ProphetOptions / Seasonality
    get_prophet_options_growth,
    get_prophet_options_changepoint_prior_scale,
    get_prophet_options_seasonality_mode,
    get_prophet_options_seasonality_prior_scale,
    get_prophet_options_yearly_seasonality,
    get_prophet_options_weekly_seasonality,
    get_prophet_options_n_changepoints,
    get_prophet_options_changepoint_range,
    get_prophet_options_seasonalities,
    get_seasonality_name,
    get_seasonality_period,
    get_seasonality_fourier_order,
    create_prophet_options_from_dict,
    # FitParams / TestParams / Predict-Test result
    fit_params_to_polars,
    create_fit_params_from_dict,
    create_predict_result,
    get_test_params_training_dates,
    get_test_params_training_values,
    get_test_params_expected_dates,
    get_test_params_expected_values,
    get_test_params_resolution,
    create_test_result,
    # ProphetModel / ProphetModelPredictParams
    create_prophet_model,
    create_prophet_model_from_dict,
    get_prophet_model_model,
    get_prophet_model_resolution,
    create_prophet_model_predict_params_from_dict,
    get_prophet_model_predict_params_forecast_periods,
    get_prophet_model_predict_params_resolution,
    create_prophet_model_predict_params,
)
from rtb_sdk.errors.predictor import PredictorError, ErrorCodes
from rtb_sdk.constants import CoreColumnConstants
from rtb_sdk.constants.frequencies_consts import GRAN_TO_TIMEDELTA, GRAN_TO_PROPHET_FREQ


def __build_prophet(options: ProphetOptions) -> Prophet:
    """Constructs a `Prophet` from options and registers custom seasonalities."""
    model = Prophet(
        growth=cast(str, get_prophet_options_growth(options)),
        changepoint_prior_scale=cast(float, get_prophet_options_changepoint_prior_scale(options)),
        seasonality_mode=cast(str, get_prophet_options_seasonality_mode(options)),
        seasonality_prior_scale=cast(float, get_prophet_options_seasonality_prior_scale(options)),
        yearly_seasonality=cast(str, get_prophet_options_yearly_seasonality(options)),
        weekly_seasonality=cast(str, get_prophet_options_weekly_seasonality(options)),
        n_changepoints=cast(int, get_prophet_options_n_changepoints(options)),
        changepoint_range=cast(float, get_prophet_options_changepoint_range(options)),
    )
    seasonalities = get_prophet_options_seasonalities(options) or {}
    for seasonality in seasonalities.values():
        model.add_seasonality(
            name=get_seasonality_name(seasonality),
            period=get_seasonality_period(seasonality),
            fourier_order=get_seasonality_fourier_order(seasonality),
        )
    return model


def __training_dataframe(df: pl.DataFrame):
    """Prepares the training DataFrame in Prophet format (`ds`, `y`)."""
    prepared = (
        df.select([CoreColumnConstants.DS_COLUMN, CoreColumnConstants.Y_COLUMN])
        .with_columns(pl.col(CoreColumnConstants.Y_COLUMN).cast(pl.Float64, strict=False))
        .sort(CoreColumnConstants.DS_COLUMN)
    )
    if prepared.height < 2:
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Fit data must contain at least two points"
        )
    return prepared.to_pandas()


def prophet_model_fit(data: FitParams,
                      options: ProphetOptions) -> ProphetModel:
    """Trains a `Prophet` and packs it into a `ProphetModel`."""
    data_params = create_fit_params_from_dict(cast(dict[str, Any], data))
    model_options = create_prophet_options_from_dict(cast(dict[str, Any], options))
    resolution = data_params.get("resolution")
    df = fit_params_to_polars(
        data_params,
        CoreColumnConstants.DS_COLUMN,
        CoreColumnConstants.Y_COLUMN,
    )
    pandas_df = __training_dataframe(df)
    model = __build_prophet(model_options)
    model.fit(pandas_df)
    return create_prophet_model(model=model, resolution=resolution)


def __forecast_with_prophet(model: Prophet,
                            forecast_periods: int,
                            resolution: Granularity) -> tuple[list[datetime], list[float]]:
    """Makes a forecast `forecast_periods` steps ahead via `Prophet.predict`."""
    freq = GRAN_TO_PROPHET_FREQ.get(resolution)
    if freq is None:
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            f"Unsupported resolution for Prophet: {resolution}"
        )
    future = model.make_future_dataframe(periods=forecast_periods, freq=freq, include_history=False)
    forecast = model.predict(future)
    forecast_dates = [ts.to_pydatetime() for ts in forecast["ds"].tolist()]
    forecast_values = [float(v) for v in forecast["yhat"].tolist()]
    return forecast_dates, forecast_values


def prophet_model_predict(model: ProphetModel,
                          options: ProphetOptions,
                          data: ProphetModelPredictParams) -> PredictResult:
    """Restores a trained Prophet model and builds a forecast."""
    model_data = create_prophet_model_from_dict(cast(dict[str, Any], model))
    create_prophet_options_from_dict(cast(dict[str, Any], options))
    predict_params = create_prophet_model_predict_params_from_dict(cast(dict[str, Any], data))

    fitted = get_prophet_model_model(model_data)
    forecast_periods = get_prophet_model_predict_params_forecast_periods(predict_params)
    resolution = get_prophet_model_predict_params_resolution(predict_params)
    if fitted is None or forecast_periods is None or resolution is None:
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Invalid model or predict params"
        )
    model_resolution = get_prophet_model_resolution(model_data)
    if resolution != model_resolution:
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Predict resolution must match fitted model resolution"
        )

    history = fitted.history
    if history is None:
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Model is not fitted"
        )
    training_dates = [ts.to_pydatetime() for ts in history["ds"].tolist()]
    training_values = [float(v) for v in history["y"].tolist()]

    predict_dates, predict_values = __forecast_with_prophet(fitted, forecast_periods, resolution)

    return create_predict_result(
        training_dates=training_dates,
        training_values=training_values,
        predict_dates=predict_dates,
        predict_values=predict_values,
    )


def __list_to_series(value: list, col: str) -> pl.Series:
    return pl.Series(col, value)


def __length_of_series_is_equal(dates: pl.Series, values: pl.Series) -> bool:
    return len(dates) == len(values)


def __have_empty_values(data: pl.Series) -> bool:
    return data.null_count() > 0


def __date_step_matches_resolution(prev_date: datetime,
                                   next_date: datetime,
                                   resolution: Granularity) -> bool:
    try:
        if next_date <= prev_date:
            return False
        if resolution == 'm':
            delta_days = (next_date - prev_date).days
            return 28 <= delta_days <= 31
        return next_date - prev_date == GRAN_TO_TIMEDELTA[resolution]
    except Exception:
        return False


def __series_matches_resolution(dates: pl.Series,
                                resolution: Granularity) -> bool:
    values = dates.to_list()
    if len(values) < 2:
        return True
    return all(
        __date_step_matches_resolution(values[i - 1], values[i], resolution)
        for i in range(1, len(values))
    )


def __is_series_continuous_smoothly(start_dates: pl.Series,
                                    end_dates: pl.Series,
                                    resolution: Granularity) -> bool:
    return __date_step_matches_resolution(start_dates[-1], end_dates[0], resolution)


def __is_valid_prophet_test(training_dates: list, training_values: list,
                            expected_dates: list, expected_values: list,
                            predict_dates: list, predict_values: list,
                            resolution: Granularity) -> bool:
    """Checks consistency of the training, expected and forecast series."""

    t_dates = __list_to_series(training_dates, 'training_dates')
    t_values = __list_to_series(training_values, 'training_values')

    e_dates = __list_to_series(expected_dates, 'expected_dates')
    e_values = __list_to_series(expected_values, 'expected_values')

    p_dates = __list_to_series(predict_dates, 'predict_dates')
    p_values = __list_to_series(predict_values, 'predict_values')

    if not (__length_of_series_is_equal(t_dates, t_values) and
            __length_of_series_is_equal(e_dates, e_values) and
            __length_of_series_is_equal(p_dates, p_values) and
            __length_of_series_is_equal(e_dates, p_dates)):
        return False

    if len(t_dates) == 0 or len(e_dates) == 0 or len(p_dates) == 0:
        return False

    if (__have_empty_values(t_dates) or __have_empty_values(t_values) or
            __have_empty_values(e_dates) or __have_empty_values(e_values) or
            __have_empty_values(p_dates) or __have_empty_values(p_values)):
        return False

    if not (t_dates.is_sorted() and e_dates.is_sorted() and p_dates.is_sorted()):
        return False

    if t_dates.to_list()[-1] >= e_dates.to_list()[0]:
        return False

    if not (__series_matches_resolution(t_dates, resolution) and
            __series_matches_resolution(e_dates, resolution) and
            __series_matches_resolution(p_dates, resolution)):
        return False

    if not __is_series_continuous_smoothly(t_dates, e_dates, resolution):
        return False

    if e_dates.to_list() != p_dates.to_list():
        return False

    return True


def prophet_model_test(model: ProphetModel,
                       options: ProphetOptions,
                       data: TestParams) -> TestResult:
    """Builds a forecast of the test period length and verifies it against the expected dates."""
    model_data = create_prophet_model_from_dict(cast(dict[str, Any], model))
    model_options = create_prophet_options_from_dict(cast(dict[str, Any], options))

    training_dates = get_test_params_training_dates(data)
    training_values = get_test_params_training_values(data)
    expected_dates = get_test_params_expected_dates(data)
    expected_values = get_test_params_expected_values(data)
    resolution = get_test_params_resolution(data)
    if (training_dates is None or training_values is None or
            expected_dates is None or expected_values is None or resolution is None):
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Invalid test params"
        )

    predict_settings = create_prophet_model_predict_params(
        resolution=resolution,
        forecast_periods=len(expected_dates),
    )

    predict_result = prophet_model_predict(
        model=model_data,
        options=model_options,
        data=predict_settings,
    )

    predict_dates = predict_result.get("predict_dates")
    predict_values = predict_result.get("predict_values")
    if predict_dates is None or predict_values is None:
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Invalid predict result"
        )

    if not __is_valid_prophet_test(training_dates, training_values,
                                   expected_dates, expected_values,
                                   predict_dates, predict_values,
                                   resolution):
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Forecast did not pass validation")

    return create_test_result(
        training_dates=training_dates,
        training_values=training_values,
        predict_dates=predict_dates,
        predict_values=predict_values,
        expected_values=expected_values,
        resolution=resolution,
    )