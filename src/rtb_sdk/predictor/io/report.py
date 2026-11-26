import json
from datetime import datetime
from typing import Any, cast

from rtb_sdk.schemas import (
    TestResult,
    TestMetrics,
    ReportType,
)
from rtb_sdk.helpers.predictor import (
    get_test_result_training_dates,
    get_test_result_training_values,
    get_test_result_predict_dates,
    get_test_result_predict_values,
    get_test_result_expected_values,
    get_test_metrics_accuracy,
    get_test_metrics_precision,
    get_test_metrics_mse,
    get_test_metrics_autocorrelation,
    get_test_metrics_mae,
    get_test_metrics_lb_stat,
    get_test_metrics_lb_sq_stat,
    is_valid_test_result,
    calc_metrics,
)


class WrongDataFormatError(Exception):
    """Raised when data format is invalid for predictor functions."""
    pass


def save_report(
    result: TestResult,
    report_type: ReportType,
    output_report_path: str,
) -> TestMetrics:
    """
    Computes metrics via calc_metrics and saves the test report
    in the chosen format: md, json or png.
    """
    if not is_valid_test_result(result):
        raise WrongDataFormatError("Invalid TestResult")

    metrics = calc_metrics(result)

    predicted_dates = get_test_result_predict_dates(result)
    actual_values = get_test_result_expected_values(result)
    predicted_values = get_test_result_predict_values(result)
    training_dates = get_test_result_training_dates(result)
    training_values = get_test_result_training_values(result)

    start_date = predicted_dates[0] if predicted_dates else None
    end_date = predicted_dates[-1] if predicted_dates else None

    if report_type == 'md':
        _save_md(output_report_path, start_date, end_date, metrics)
    elif report_type == 'json':
        _save_json(output_report_path, start_date, end_date, metrics)
    elif report_type == 'png':
        if (training_dates is None or training_values is None or
                predicted_dates is None or actual_values is None or predicted_values is None):
            raise WrongDataFormatError("Missing data for PNG report")
        _save_png(output_report_path,
                  training_dates, training_values,
                  predicted_dates, actual_values, predicted_values)
    else:
        raise ValueError(f"Unknown report_type '{report_type}'. Expected 'md', 'json', or 'png'.")

    return metrics


def _save_md(path: str,
             start_date: datetime | None,
             end_date: datetime | None,
             metrics: TestMetrics) -> None:
    accuracy = get_test_metrics_accuracy(metrics, 0.0)
    precision = get_test_metrics_precision(metrics, 0.0)
    mse = get_test_metrics_mse(metrics, 0.0)
    autocorrelation = get_test_metrics_autocorrelation(metrics, 0.0)
    mae = get_test_metrics_mae(metrics, 0.0)
    lb_stat = get_test_metrics_lb_stat(metrics, 0.0)
    lb_sq_stat = get_test_metrics_lb_sq_stat(metrics, 0.0)

    lines = [
        "# Test report",
        "",
        "## Parameters",
        "| Parameter | Value |",
        "| :--- | :--- |",
        f"| Start date of forecast | {start_date} |",
        f"| End of forecast date | {end_date} |",
        "",
        "## Metrics",
        "| Metric | Value |",
        "| :--- | :--- |",
        f"| accuracy | {accuracy} |",
        f"| precision | {precision} |",
        f"| mse | {mse} |",
        f"| autocorrelation | {autocorrelation} |",
        f"| mae | {mae} |",
        f"| lb_stat | {lb_stat} |",
        f"| lb_sq_stat | {lb_sq_stat} |",
    ]
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def _save_json(path: str,
               start_date: datetime | None,
               end_date: datetime | None,
               metrics: TestMetrics) -> None:
    data = {
        "start_date": str(start_date),
        "end_date": str(end_date),
        "accuracy": get_test_metrics_accuracy(metrics, 0.0),
        "precision": get_test_metrics_precision(metrics, 0.0),
        "mse": get_test_metrics_mse(metrics, 0.0),
        "autocorrelation": get_test_metrics_autocorrelation(metrics, 0.0),
        "mae": get_test_metrics_mae(metrics, 0.0),
        "lb_stat": get_test_metrics_lb_stat(metrics, 0.0),
        "lb_sq_stat": get_test_metrics_lb_sq_stat(metrics, 0.0),
    }
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _save_png(path: str,
              training_dates: list[Any],
              training_values: list[Any],
              predicted_dates: list[Any],
              actual_values: list[Any],
              predicted_values: list[Any]) -> None:
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
    except ImportError:
        raise ImportError(
            "matplotlib is required for PNG reports. Install it with: pip install matplotlib"
        )

    fig, ax = plt.subplots(figsize=(14, 6))

    # Historical (training) — solid blue.
    ax.plot(training_dates, training_values,
            label='Historical', color='steelblue', linewidth=1.5)

    # Expected (actual values of the test period) — solid green,
    # joined to the history through the last training point so that the line looks
    # continuous.
    if training_dates and predicted_dates:
        expected_dates_plot = [training_dates[-1]] + list(predicted_dates)
        expected_values_plot = [training_values[-1]] + list(actual_values)
    else:
        expected_dates_plot = list(predicted_dates)
        expected_values_plot = list(actual_values)
    ax.plot(expected_dates_plot, expected_values_plot,
            label='Expected', color='seagreen', linewidth=1.5)

    # Forecast values — dashed red on top of the expected ones.
    ax.plot(predicted_dates, predicted_values,
            label='Predicted', color='tomato',
            linewidth=1.8, linestyle='--')

    if training_dates:
        ax.axvline(x=cast(float, training_dates[-1]), color='gray', linestyle=':', linewidth=1,
                   label='Forecast start')

    ax.set_title('Historical / Expected / Predicted')
    ax.set_xlabel('Date')
    ax.set_ylabel('Value')
    ax.legend()
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    fig.autofmt_xdate()
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)