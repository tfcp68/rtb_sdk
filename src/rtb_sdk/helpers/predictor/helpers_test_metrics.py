from typing import Any, cast

from rtb_sdk.schemas import TestMetrics
from rtb_sdk.errors.predictor import PredictorError, ErrorCodes
from rtb_sdk.constants.data_types import DataPredictorType
from rtb_sdk.helpers.type_helpers import check_predictor_type
from rtb_sdk.helpers.predictor.helpers_utils import _is_valid_numeric_value


# ─── TestMetrics ───────────────────────────────────────────────────────────────

def get_test_metrics_accuracy(metrics: TestMetrics,
                              default: float | None = None
                              ) -> float | None:
    return metrics.get("accuracy", default)


def get_test_metrics_precision(metrics: TestMetrics,
                               default: float | None = None
                               ) -> float | None:
    return metrics.get("precision", default)


def get_test_metrics_mse(metrics: TestMetrics,
                         default: float | None = None
                         ) -> float | None:
    return metrics.get("mse", default)


def get_test_metrics_autocorrelation(metrics: TestMetrics,
                                     default: float | None = None
                                     ) -> float | None:
    return metrics.get("autocorrelation", default)


def get_test_metrics_mae(metrics: TestMetrics,
                         default: float | None = None
                         ) -> float | None:
    return metrics.get("mae", default)


def get_test_metrics_lb_stat(metrics: TestMetrics,
                             default: float | None = None
                             ) -> float | None:
    return metrics.get("lb_stat", default)


def get_test_metrics_lb_sq_stat(metrics: TestMetrics,
                                default: float | None = None
                                ) -> float | None:
    return metrics.get("lb_sq_stat", default)


def _is_valid_test_metrics_accuracy(metrics: TestMetrics) -> bool:
    if not check_predictor_type(metrics, DataPredictorType.TEST_METRICS):
        return False
    return _is_valid_numeric_value(get_test_metrics_accuracy(metrics))


def _is_valid_test_metrics_precision(metrics: TestMetrics) -> bool:
    if not check_predictor_type(metrics, DataPredictorType.TEST_METRICS):
        return False
    return _is_valid_numeric_value(get_test_metrics_precision(metrics))


def _is_valid_test_metrics_mse(metrics: TestMetrics) -> bool:
    if not check_predictor_type(metrics, DataPredictorType.TEST_METRICS):
        return False
    return _is_valid_numeric_value(get_test_metrics_mse(metrics))


def _is_valid_test_metrics_autocorrelation(metrics: TestMetrics) -> bool:
    if not check_predictor_type(metrics, DataPredictorType.TEST_METRICS):
        return False
    return _is_valid_numeric_value(get_test_metrics_autocorrelation(metrics))


def _is_valid_test_metrics_mae(metrics: TestMetrics) -> bool:
    if not check_predictor_type(metrics, DataPredictorType.TEST_METRICS):
        return False
    return _is_valid_numeric_value(get_test_metrics_mae(metrics))


def _is_valid_test_metrics_lb_stat(metrics: TestMetrics) -> bool:
    if not check_predictor_type(metrics, DataPredictorType.TEST_METRICS):
        return False
    return _is_valid_numeric_value(get_test_metrics_lb_stat(metrics))


def _is_valid_test_metrics_lb_sq_stat(metrics: TestMetrics) -> bool:
    if not check_predictor_type(metrics, DataPredictorType.TEST_METRICS):
        return False
    return _is_valid_numeric_value(get_test_metrics_lb_sq_stat(metrics))


CheckTestMetricsList = [
    _is_valid_test_metrics_accuracy,
    _is_valid_test_metrics_precision,
    _is_valid_test_metrics_mse,
    _is_valid_test_metrics_autocorrelation,
    _is_valid_test_metrics_mae,
    _is_valid_test_metrics_lb_stat,
    _is_valid_test_metrics_lb_sq_stat,
]


def _check_fields_test_metrics(metrics: TestMetrics) -> bool:
    for check in CheckTestMetricsList:
        if not check(metrics):
            return False
    return True


def is_valid_test_metrics(metrics: Any) -> bool:
    if not check_predictor_type(metrics, DataPredictorType.TEST_METRICS):
        return False
    return _check_fields_test_metrics(metrics)


def create_test_metrics(accuracy: float,
                        precision: float,
                        mse: float,
                        autocorrelation: float,
                        mae: float,
                        lb_stat: float,
                        lb_sq_stat: float,
                        **kwargs) -> TestMetrics:
    result = {
        "accuracy": accuracy,
        "precision": precision,
        "mse": mse,
        "autocorrelation": autocorrelation,
        "mae": mae,
        "lb_stat": lb_stat,
        "lb_sq_stat": lb_sq_stat,
        "__type": DataPredictorType.TEST_METRICS,
    }
    if is_valid_test_metrics(result):
        return cast(TestMetrics, result)
    raise PredictorError(
        ErrorCodes.PARAMETER_ERROR_CODE,
        "Invalid parameters for TestMetrics"
    )


def create_test_metrics_from_dict(data: dict[str, Any]) -> TestMetrics:
    try:
        return create_test_metrics(**data)
    except Exception:
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Invalid parameters for TestMetrics"
        )
