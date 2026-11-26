"""Computing forecast quality metrics from a `TestResult`."""
from rtb_sdk.schemas import TestResult, TestMetrics
from rtb_sdk.errors.predictor import PredictorError, ErrorCodes
from rtb_sdk.helpers.predictor.helpers_test_result import (
    get_test_result_predict_values,
    get_test_result_expected_values,
)
from rtb_sdk.helpers.predictor.helpers_test_metrics import create_test_metrics


def _lag1_autocorr(series: list[float]) -> float:
    n = len(series)
    if n < 2:
        return 0.0
    mean = sum(series) / n
    centered = [x - mean for x in series]
    c0 = sum(x * x for x in centered)
    if c0 == 0:
        return 0.0
    c1 = sum(centered[i] * centered[i - 1] for i in range(1, n))
    return c1 / c0


def _ljung_box_stat(series: list[float], lag: int = 1) -> float:
    n = len(series)
    if n < lag + 2:
        return 0.0
    mean = sum(series) / n
    centered = [x - mean for x in series]
    c0 = sum(x * x for x in centered)
    if c0 == 0:
        return 0.0
    result = 0.0
    for k in range(1, lag + 1):
        ck = sum(centered[i] * centered[i - k] for i in range(k, n))
        rk = ck / c0
        result += rk * rk / (n - k)
    return n * (n + 2) * result


def calc_metrics(result: TestResult) -> TestMetrics:
    predicted = get_test_result_predict_values(result)
    actual = get_test_result_expected_values(result)

    if not predicted or not actual or len(predicted) != len(actual):
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Disabled data for calculating metrics"
        )

    n = len(actual)

    mape_terms = [abs(a - p) / abs(a) for a, p in zip(actual, predicted) if a != 0]
    mape = sum(mape_terms) / len(mape_terms) if mape_terms else 0.0
    accuracy = max(0.0, 1.0 - mape)

    if n > 1:
        correct = sum(
            1 for i in range(1, n)
            if (actual[i] - actual[i - 1]) * (predicted[i] - predicted[i - 1]) > 0
        )
        precision = correct / (n - 1)
    else:
        precision = 0.0

    mse = sum((a - p) ** 2 for a, p in zip(actual, predicted)) / n

    residuals = [p - a for p, a in zip(predicted, actual)]
    autocorrelation = _lag1_autocorr(residuals)

    mae = sum(abs(a - p) for a, p in zip(actual, predicted)) / n

    lb_stat = _ljung_box_stat(residuals)
    lb_sq_stat = _ljung_box_stat([r ** 2 for r in residuals])

    return create_test_metrics(
        accuracy=round(accuracy, 6),
        precision=round(precision, 6),
        mse=round(mse, 6),
        autocorrelation=round(autocorrelation, 6),
        mae=round(mae, 6),
        lb_stat=round(lb_stat, 6),
        lb_sq_stat=round(lb_sq_stat, 6),
    )