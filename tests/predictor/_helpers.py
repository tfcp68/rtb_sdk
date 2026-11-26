"""
Helper factories of test data for the predictor.

They use the public create_* of the schemas — no internal builders.
"""
from datetime import datetime, timedelta
from typing import cast

from rtb_sdk.schemas import Granularity
from rtb_sdk.schemas.predictor_schemas import CommonModel, ModelOptions
from rtb_sdk.helpers import (
    create_prophet_options,
    create_fit_params,
    create_test_params,
    create_test_result,
    create_predict_result,
)


FREQ_DELTA: dict[str, timedelta] = {
    't': timedelta(minutes=10),
    'h': timedelta(hours=1),
    'd': timedelta(days=1),
    'w': timedelta(weeks=1),
    'm': timedelta(days=30),
}

DEFAULT_START = datetime(2024, 1, 1)


# ── Primitives ──────────────────────────────────────────────────────────────────

def make_dates(
    n: int,
    start: datetime = DEFAULT_START,
    granularity: Granularity = 'd',
) -> list[datetime]:
    delta = FREQ_DELTA.get(granularity, timedelta(days=1))
    return [start + delta * i for i in range(n)]


def make_values(n: int, base: float = 100.0) -> list[float]:
    return [base + float(i) for i in range(n)]


# ── Schema stubs ──────────────────────────────────────────────────────────────────

def make_model_options() -> ModelOptions:
    return cast(ModelOptions, create_prophet_options(seasonalities={}))


def make_common_model() -> CommonModel:
    """CommonModel stub — for negative cases; the model is not valid."""
    return cast(CommonModel, {
        '__type': 'CommonModel',
        'type': 'prophet',
        'resolution': 'd',
        'description': None,
    })


# ── Schema factories ───────────────────────────────────────────────────────────────

def make_predictor_data(n: int = 10, granularity: Granularity = 'd'):
    return create_fit_params(
        dates=make_dates(n, granularity=granularity),
        values=make_values(n),
        resolution=granularity,
    )


def make_fit_data(n: int = 10, granularity: Granularity = 'd'):
    return create_fit_params(
        dates=make_dates(n, granularity=granularity),
        values=make_values(n),
        resolution=granularity,
    )


def make_test_data(
    history_n: int = 10,
    sample_n: int = 5,
    granularity: Granularity = 'd',
):
    delta = FREQ_DELTA.get(granularity, timedelta(days=1))
    sample_start = DEFAULT_START + delta * history_n
    history = make_predictor_data(history_n, granularity)
    expected_dates = make_dates(sample_n, start=sample_start, granularity=granularity)
    expected_values = make_values(sample_n, base=200.0)
    return create_test_params(
        training_dates=history['dates'],
        training_values=history['values'],
        expected_dates=expected_dates,
        expected_values=expected_values,
        resolution=granularity,
    )


def make_result_test_data(
    history_n: int = 10,
    sample_n: int = 5,
    granularity: Granularity = 'd',
):
    delta = FREQ_DELTA.get(granularity, timedelta(days=1))
    sample_start = DEFAULT_START + delta * history_n
    history = make_predictor_data(history_n, granularity)
    expected_dates = make_dates(sample_n, start=sample_start, granularity=granularity)
    expected_values = make_values(sample_n, base=200.0)
    predict_values = make_values(sample_n, base=195.0)
    return create_test_result(
        training_dates=history['dates'],
        training_values=history['values'],
        predict_dates=expected_dates,
        predict_values=predict_values,
        expected_values=expected_values,
        resolution=granularity,
    )


def make_predict_result_data(
    history_n: int = 10,
    sample_n: int = 5,
    granularity: Granularity = 'd',
):
    delta = FREQ_DELTA.get(granularity, timedelta(days=1))
    sample_start = DEFAULT_START + delta * history_n
    history = make_predictor_data(history_n, granularity)
    predict_dates = make_dates(sample_n, start=sample_start, granularity=granularity)
    predict_values = make_values(sample_n, base=195.0)
    return create_predict_result(
        training_dates=history['dates'],
        training_values=history['values'],
        predict_dates=predict_dates,
        predict_values=predict_values,
    )