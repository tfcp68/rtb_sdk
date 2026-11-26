"""
Header file: imports and re-exports all functions under test
of the predictor module. The root test file uses FUNCTIONS to build
the describe_ blocks.

FUNCTIONS: {func_name: (func, unpacker | None)}
  - func     — the function under test or a wrapper
  - unpacker — takes a raw case (dict) and returns a case with already
               assembled objects; None for functions without complex types.
"""
import json
import math
import os
import tempfile
from datetime import datetime, timedelta
from typing import Any, cast

import polars as pl
import pytest

from rtb_sdk.predictor.predictor import fit, predict, test
from rtb_sdk.predictor.io.report import save_report
from rtb_sdk.helpers import (
    is_valid_test_result,
    is_valid_model_options,
    is_valid_common_model,
    is_valid_fit_params,
    is_valid_predict_params,
    is_valid_predict_result,
    is_valid_test_params,
    is_valid_test_metrics,
    is_valid_seasonality,
    is_valid_prophet_options,
    is_valid_prophet_model_predict_params,
    # Builders
    create_fit_params,
    create_fit_params_from_polars_df,
    create_model_options,
    create_prophet_options,
    create_seasonality,
    create_predict_result,
    create_test_result,
    create_test_metrics,
    create_prophet_model_predict_params,
    create_prophet_model_test_params,
    # Serialization — FitParams
    serialize_fit_params,
    deserialize_fit_params,
    # Serialization — ModelOptions / ProphetOptions
    serialize_model_options,
    deserialize_model_options,
    serialize_prophet_options,
    deserialize_prophet_options,
    # Serialization — Seasonality
    serialize_seasonality,
    deserialize_seasonality,
    # Serialization — Results / Metrics
    serialize_predict_result,
    deserialize_predict_result,
    serialize_test_result,
    deserialize_test_result,
    serialize_test_metrics,
    deserialize_test_metrics,
    # Serialization — Prophet sub-params
    serialize_prophet_model_predict_params,
    deserialize_prophet_model_predict_params,
    serialize_prophet_model_test_params,
    deserialize_prophet_model_test_params,
    # Serialization — Common dispatchers
    serialize_options,
    deserialize_options,
    serialize_predict_params,
    deserialize_predict_params,
    serialize_test_params,
    deserialize_test_params,
    serialize_model,
    deserialize_model,
    # Public helpers
    calc_metrics,
    fit_params_to_polars,
    create_from_timedelta,
    is_in_class,
)
from rtb_sdk.schemas import FitParams, TestParams, TestResult, Granularity, ModelType, SeasonalityNameType
from rtb_sdk.constants import ModelTypeName, Gran
from tests.predictor._helpers import make_result_test_data


# ---------------------------------------------------------------------------
# Internal primitives
# ---------------------------------------------------------------------------

def _dt_list(
    n: int,
    resolution: str = 'd',
    start: datetime = datetime(2024, 1, 1),
) -> list[datetime]:
    deltas: dict[str, timedelta] = {
        't': timedelta(minutes=10),
        'h': timedelta(hours=1),
        'd': timedelta(days=1),
        'w': timedelta(weeks=1),
        'm': timedelta(days=30),
    }
    step = deltas.get(resolution, timedelta(days=1))
    return [start + step * i for i in range(n)]


def _vals(n: int, base: float = 0.0) -> list[float]:
    return [base + float(i) for i in range(n)]


# ---------------------------------------------------------------------------
# Case unpackers (for the main functions)
# ---------------------------------------------------------------------------

def _parse_dt_list(values: list) -> list[datetime]:
    return [datetime.fromisoformat(v) if isinstance(v, str) else v for v in values]


def _unpack_fit(case: dict) -> dict:
    """fit / is_valid_fit_params: data.dates → list[datetime]."""
    data = case['input'].get('data') or {}
    if 'dates' in data:
        data['dates'] = _parse_dt_list(data['dates'])
    return case


def _unpack_predict(case: dict) -> dict:
    """predict: without conversions (the model is a stub)."""
    return case


def _unpack_test(case: dict) -> dict:
    """test / is_valid_test_params: data.training_dates / expected_dates → datetime."""
    data = case['input'].get('data') or {}
    for key in ('training_dates', 'expected_dates'):
        if key in data:
            data[key] = _parse_dt_list(data[key])
    return case


def _unpack_test_result(case: dict) -> dict:
    """is_valid_test_result / is_valid_predict_result: result dates → datetime."""
    result = case['input'].get('result') or {}
    for key in ('training_dates', 'predict_dates'):
        if key in result:
            result[key] = _parse_dt_list(result[key])
    return case


def _unpack_save_test_result(case: dict) -> dict:
    """save_report: result dates → datetime."""
    result = case['input'].get('result') or {}
    for key in ('training_dates', 'predict_dates'):
        if key in result:
            result[key] = _parse_dt_list(result[key])
    return case


# ---------------------------------------------------------------------------
# Wrappers: serialization — primitive schemas
# ---------------------------------------------------------------------------

def _round_trip_seasonality(name: SeasonalityNameType, period: float, fourier_order: int) -> bool:
    s = create_seasonality(name=name, period=period, fourier_order=fourier_order)
    assert deserialize_seasonality(serialize_seasonality(s)) == s
    return True


def _round_trip_fit_params(n: int, resolution: Granularity) -> bool:
    dates = _dt_list(n, resolution)
    fp = create_fit_params(dates=dates, values=_vals(n), resolution=resolution)
    assert deserialize_fit_params(serialize_fit_params(fp)) == fp
    return True


def _round_trip_model_options(model_type: ModelType) -> bool:
    opts = create_model_options(model_type=model_type)
    assert deserialize_model_options(serialize_model_options(opts)) == opts
    return True


def _round_trip_prophet_options(with_seasonality: bool = False) -> bool:
    if with_seasonality:
        s = create_seasonality(name='monthly', period=30.5, fourier_order=5)
        op = create_prophet_options(seasonalities={'monthly': s})
    else:
        op = create_prophet_options(seasonalities={})
    assert deserialize_prophet_options(serialize_prophet_options(op)) == op
    return True


def _round_trip_predict_result(n_train: int = 2, n_predict: int = 2) -> bool:
    train_dates = _dt_list(n_train, 'd')
    predict_dates = _dt_list(n_predict, 'd', start=datetime(2024, 1, n_train + 1))
    pr = create_predict_result(
        training_dates=train_dates,
        training_values=_vals(n_train),
        predict_dates=predict_dates,
        predict_values=_vals(n_predict, base=10.0),
    )
    assert deserialize_predict_result(serialize_predict_result(pr)) == pr
    return True


def _round_trip_test_result(n_train: int = 2, n_predict: int = 2) -> bool:
    train_dates = _dt_list(n_train, 'd')
    predict_dates = _dt_list(n_predict, 'd', start=datetime(2024, 1, n_train + 1))
    tr = create_test_result(
        training_dates=train_dates,
        training_values=_vals(n_train),
        predict_dates=predict_dates,
        predict_values=_vals(n_predict, base=5.0),
        expected_values=_vals(n_predict, base=6.0),
        resolution='d',
    )
    assert deserialize_test_result(serialize_test_result(tr)) == tr
    return True


def _round_trip_test_metrics(
    accuracy: float,
    precision: float,
    mse: float,
    autocorrelation: float,
    mae: float,
    lb_stat: float,
    lb_sq_stat: float,
) -> bool:
    m = create_test_metrics(accuracy, precision, mse, autocorrelation, mae, lb_stat, lb_sq_stat)
    assert deserialize_test_metrics(serialize_test_metrics(m)) == m
    return True


def _round_trip_prophet_predict_params(resolution: Granularity, forecast_periods: int) -> bool:
    pp = create_prophet_model_predict_params(resolution=resolution, forecast_periods=forecast_periods)
    assert deserialize_prophet_model_predict_params(
        serialize_prophet_model_predict_params(pp)
    ) == pp
    return True


def _round_trip_prophet_test_params(
    n_train: int = 2,
    n_expected: int = 2,
    resolution: Granularity = 'd',
) -> bool:
    train_dates = _dt_list(n_train, resolution)
    expected_dates = _dt_list(n_expected, resolution, start=datetime(2024, 1, n_train + 1))
    tp = create_prophet_model_test_params(
        training_dates=train_dates,
        training_values=_vals(n_train),
        expected_dates=expected_dates,
        expected_values=_vals(n_expected, base=200.0),
        resolution=resolution,
    )
    assert deserialize_prophet_model_test_params(
        serialize_prophet_model_test_params(tp)
    ) == tp
    return True


# ---------------------------------------------------------------------------
# Wrappers: serialization — common dispatchers and the model
# ---------------------------------------------------------------------------

def _serialize_dispatch(kind: str, model_type: str = 'nope') -> bool:
    """Tests of the common serialize_*/deserialize_* dispatchers."""
    if kind == 'options':
        op = create_prophet_options(seasonalities={})
        s = serialize_options(op)
        restored = deserialize_options(s)
        assert restored == op
        assert restored['__type'] == 'ProphetOptions'
    elif kind == 'predict_params':
        op = create_prophet_options(seasonalities={})
        pp = create_prophet_model_predict_params(resolution='d', forecast_periods=3)
        s = serialize_predict_params(pp, op)
        assert deserialize_predict_params(s, op) == pp
    elif kind == 'test_params':
        op = create_prophet_options(seasonalities={})
        tp = create_prophet_model_test_params(
            training_dates=_dt_list(2, 'd'),
            training_values=_vals(2),
            expected_dates=_dt_list(2, 'd', start=datetime(2024, 1, 3)),
            expected_values=_vals(2, base=200.0),
            resolution='d',
        )
        s = serialize_test_params(tp, op)
        assert deserialize_test_params(s, op) == tp
    elif kind == 'unknown_options_type':
        bad = json.dumps({'model_type': model_type, '__type': 'ProphetOptions'})
        deserialize_options(bad)  # must raise PredictorError
        return False  # must not be reached
    return True


def _round_trip_model(n_train: int = 30) -> bool:
    """Full cycle: fit → serialize → deserialize → predict."""
    dates = _dt_list(n_train, 'd')
    fp = create_fit_params(
        dates=dates,
        values=[100.0 + i for i in range(n_train)],
        resolution='d',
    )
    options = create_prophet_options(seasonalities={})
    model = fit(data=fp, options=options)

    # Checking fields in the serialized JSON
    raw = json.loads(serialize_model(model))
    assert raw['type'] == 'prophet'
    assert '__type' in raw

    # Round-trip
    restored = deserialize_model(serialize_model(model))
    assert restored['type'] == 'prophet'
    assert restored['resolution'] == 'd'

    # Predict on the restored model
    pp = create_prophet_model_predict_params(resolution='d', forecast_periods=3)
    result = predict(model=restored, options=options, data=pp)
    assert len(result['predict_values']) == 3
    return True


# ---------------------------------------------------------------------------
# Wrappers: input data validation (create_fit_params)
# ---------------------------------------------------------------------------

def _validate_fit_failure(scenario: str) -> None:
    """All scenarios must raise PredictorError."""
    dates_3d = _dt_list(3, 'd')
    dates_3h = _dt_list(3, 'h')

    if scenario == 'nan_values':
        create_fit_params(dates=dates_3d, values=[100.0, math.nan, 102.0], resolution='d')
    elif scenario == 'inf_values':
        create_fit_params(dates=dates_3d, values=[100.0, math.inf, 102.0], resolution='d')
    elif scenario == 'length_mismatch':
        create_fit_params(dates=dates_3d, values=[100.0, 101.0], resolution='d')
    elif scenario == 'duplicate_dates':
        create_fit_params(
            dates=[datetime(2024, 1, 1), datetime(2024, 1, 1), datetime(2024, 1, 2)],
            values=[100.0, 101.0, 102.0],
            resolution='d',
        )
    elif scenario == 'reverse_dates':
        create_fit_params(
            dates=[datetime(2024, 1, 3), datetime(2024, 1, 2), datetime(2024, 1, 1)],
            values=[100.0, 101.0, 102.0],
            resolution='d',
        )
    elif scenario == 'invalid_date_string':
        payload = '{"__type":"FitParams","dates":["na"],"values":[100.0],"resolution":"d"}'
        deserialize_fit_params(payload)
    elif scenario == 'resolution_mismatch':
        options = create_prophet_options(seasonalities={})
        data = cast(FitParams, {
            '__type': 'FitParams',
            'dates': dates_3h,
            'values': [100.0, 101.0, 102.0],
            'resolution': 'd',
        })
        fit(data=data, options=options)


# ---------------------------------------------------------------------------
# Wrappers: validation — Polars DataFrame
# ---------------------------------------------------------------------------

def _validate_polars_failure(scenario: str) -> None:
    """All scenarios must raise PredictorError."""
    if scenario == 'invalid_date_string':
        df = pl.DataFrame({'date_from': ['2024-01-01', 'na'], 'value': [100.0, 101.0]})
        create_fit_params_from_polars_df(df, 'date_from', 'value')
    elif scenario == 'invalid_value_string':
        df = pl.DataFrame({'date_from': ['2024-01-01', '2024-01-02'], 'value': ['100.0', 'na']})
        create_fit_params_from_polars_df(df, 'date_from', 'value')
    elif scenario == 'null_date':
        df = pl.DataFrame({'date_from': ['2024-01-01', None], 'value': [100.0, 101.0]})
        create_fit_params_from_polars_df(df, 'date_from', 'value')
    elif scenario == 'null_value':
        df = pl.DataFrame({'date_from': ['2024-01-01', '2024-01-02'], 'value': [100.0, None]})
        create_fit_params_from_polars_df(df, 'date_from', 'value')
    elif scenario == 'gap_in_dates':
        df = pl.DataFrame({
            'date_from': ['2024-01-01', '2024-01-02', '2024-01-04'],
            'value': [100.0, 101.0, 102.0],
        })
        create_fit_params_from_polars_df(df, 'date_from', 'value')
    elif scenario == 'missing_column':
        df = pl.DataFrame({'date_from': ['2024-01-01', '2024-01-02'], 'value': [1.0, 2.0]})
        create_fit_params_from_polars_df(df, 'date_from', 'nonexistent_col')
    elif scenario == 'single_row':
        df = pl.DataFrame({'date_from': ['2024-01-01'], 'value': [100.0]})
        create_fit_params_from_polars_df(df, 'date_from', 'value')


# ---------------------------------------------------------------------------
# Wrappers: validation — predict / test
# ---------------------------------------------------------------------------

def _validate_predict_failure(scenario: str) -> None:
    """All scenarios must raise PredictorError."""
    options = create_prophet_options(seasonalities={})

    if scenario == 'resolution_mismatch':
        dates_14d = _dt_list(14, 'd')
        model = fit(
            data=create_fit_params(
                dates=dates_14d,
                values=[100.0 + i for i in range(14)],
                resolution='d',
            ),
            options=options,
        )
        pp = create_prophet_model_predict_params(resolution='h', forecast_periods=3)
        predict(model=model, options=options, data=pp)
    elif scenario == 'zero_forecast_periods':
        create_prophet_model_predict_params(resolution='d', forecast_periods=0)


def _validate_test_failure(scenario: str) -> None:
    """All scenarios must raise PredictorError."""
    options = create_prophet_options(seasonalities={})
    training_dates = _dt_list(14, 'd')
    training_values = [100.0 + i for i in range(14)]

    model = fit(
        data=create_fit_params(dates=training_dates, values=training_values, resolution='d'),
        options=options,
    )

    if scenario == 'expected_dates_with_gap':
        data = cast(TestParams, {
            '__type': 'ProphetModelTestParams',
            'training_dates': training_dates,
            'training_values': training_values,
            'expected_dates': [datetime(2024, 1, 15), datetime(2024, 1, 17)],
            'expected_values': [200.0, 201.0],
            'resolution': 'd',
        })
        test(model=model, options=options, data=data)
    elif scenario == 'expected_dates_not_continuous':
        data = cast(TestParams, {
            '__type': 'ProphetModelTestParams',
            'training_dates': training_dates,
            'training_values': training_values,
            'expected_dates': [datetime(2024, 2, 1), datetime(2024, 2, 2)],
            'expected_values': [200.0, 201.0],
            'resolution': 'd',
        })
        test(model=model, options=options, data=data)


# ---------------------------------------------------------------------------
# Wrappers: is_valid_test_result with dynamic data
# ---------------------------------------------------------------------------

def _is_valid_test_result_dynamic(scenario: str) -> bool:
    result = make_result_test_data()
    d: dict[str, Any] = dict(result)

    if scenario == 'accepts_continuous':
        return is_valid_test_result(result)
    elif scenario == 'rejects_length_mismatch':
        d['expected_values'] = d['expected_values'] + [999.0]
        return is_valid_test_result(cast(TestResult, d))
    elif scenario == 'rejects_non_continuous':
        d['predict_dates'] = [d['predict_dates'][0] + timedelta(days=1)] + d['predict_dates'][1:]
        return is_valid_test_result(cast(TestResult, d))
    elif scenario == 'rejects_missing_resolution':
        del d['resolution']
        return is_valid_test_result(cast(TestResult, d))
    elif scenario == 'rejects_wrong_type':
        d['__type'] = 'WrongType'
        return is_valid_test_result(cast(TestResult, d))
    return False


# ---------------------------------------------------------------------------
# Wrappers: save_report with content checks (via tempfile)
# ---------------------------------------------------------------------------

def _save_report_checks(scenario: str) -> bool:
    result = make_result_test_data(history_n=3, sample_n=2)
    with tempfile.TemporaryDirectory() as tmp:
        if scenario == 'md_content':
            output = os.path.join(tmp, 'report.md')
            metrics = save_report(result, 'md', output)
            content = open(output, encoding='utf-8').read()
            assert '# Test report' in content
            assert '| accuracy |' in content
            assert metrics['__type'] == 'TestMetrics'
            assert 'accuracy' in metrics
        elif scenario == 'json_content':
            output = os.path.join(tmp, 'report.json')
            metrics = save_report(result, 'json', output)
            payload = json.loads(open(output, encoding='utf-8').read())
            assert 'accuracy' in payload
            assert payload['start_date'].startswith('2024-01-04')
            assert payload['accuracy'] == metrics['accuracy']
        elif scenario == 'png_exists':
            output = os.path.join(tmp, 'report.png')
            metrics = save_report(result, 'png', output)
            assert os.path.exists(output)
            assert os.path.getsize(output) > 0
            assert metrics['__type'] == 'TestMetrics'
        elif scenario == 'rejects_invalid_result':
            result['expected_values'] = result['expected_values'] + [999.0]
            output = os.path.join(tmp, 'report.md')
            save_report(result, 'md', output)  # raises WrongDataFormatError
            return False  # must not be reached
        elif scenario == 'same_metrics_all_formats':
            result2 = make_result_test_data(history_n=5, sample_n=3)
            md_metrics = save_report(result2, 'md', os.path.join(tmp, 'r.md'))
            json_metrics = save_report(result2, 'json', os.path.join(tmp, 'r.json'))
            assert md_metrics['accuracy'] == json_metrics['accuracy']
            assert md_metrics['mse'] == json_metrics['mse']
    return True


# ---------------------------------------------------------------------------
# Wrappers: Polars date formats (via tempfile for CSV)
# ---------------------------------------------------------------------------

def _test_polars_csv_format(date_format: str) -> bool:
    rows = ['date_from,value']
    for i, dt in enumerate(_dt_list(14, 'd')):
        rows.append(f'{dt.strftime(date_format)},{100.0 + i}')

    with tempfile.TemporaryDirectory() as tmp:
        csv_path = os.path.join(tmp, 'test.csv')
        with open(csv_path, 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(rows))
        df = pl.read_csv(csv_path)
        fit_params = create_fit_params_from_polars_df(df, 'date_from', 'value')

    assert fit_params['resolution'] == 'd'
    assert all(isinstance(item, datetime) for item in fit_params['dates'])

    options = create_prophet_options(seasonalities={})
    model = fit(data=fit_params, options=options)
    result = predict(
        model=model,
        options=options,
        data=create_prophet_model_predict_params(resolution='d', forecast_periods=3),
    )
    assert len(result['predict_dates']) == 3
    assert len(result['predict_values']) == 3
    return True


def _test_polars_native_type(scenario: str) -> bool:
    from datetime import date as _date

    if scenario == 'sorts_automatically':
        dates = _dt_list(5, 'd')
        shuffled = [dates[2], dates[0], dates[4], dates[1], dates[3]]
        df = pl.DataFrame({
            'date_from': shuffled,
            'value': [float(i) for i in range(5)],
        })
        fit_params = create_fit_params_from_polars_df(df, 'date_from', 'value')
        assert fit_params['dates'] == dates
        return True

    if scenario == 'datetime':
        date_values = _dt_list(6, 'd')
    elif scenario == 'date':
        date_values = [_date(2024, 1, 1) + timedelta(days=i) for i in range(6)]
    else:
        return False

    df = pl.DataFrame({
        'date_from': date_values,
        'value': [float(i) for i in range(len(date_values))],
    })
    fit_params = create_fit_params_from_polars_df(df, 'date_from', 'value')
    assert fit_params['resolution'] == 'd'
    assert all(isinstance(item, datetime) for item in fit_params['dates'])
    return True


# ---------------------------------------------------------------------------
# Wrappers: calc_metrics
# ---------------------------------------------------------------------------

def _calc_metrics_checks(scenario: str) -> bool:
    def _make_tr(predicted: list[float], actual: list[float], resolution: Granularity = 'd'):
        n_train = 2
        step = timedelta(days=1) if resolution == 'd' else timedelta(hours=1)
        start = datetime(2024, 1, 1)
        training_dates = [start + step * i for i in range(n_train)]
        predict_dates = [start + step * (n_train + i) for i in range(len(predicted))]
        return create_test_result(
            training_dates=training_dates,
            training_values=[100.0] * n_train,
            predict_dates=predict_dates,
            predict_values=predicted,
            expected_values=actual,
            resolution=resolution,
        )

    if scenario == 'perfect_forecast':
        values = [100.0, 110.0, 120.0]
        metrics = calc_metrics(_make_tr(values, values))
        assert metrics['accuracy'] == pytest.approx(1.0, abs=1e-6)
        assert metrics['mse'] == pytest.approx(0.0, abs=1e-6)
        assert metrics['mae'] == pytest.approx(0.0, abs=1e-6)
    elif scenario == 'all_zeros_actual':
        metrics = calc_metrics(_make_tr([5.0, 6.0, 7.0], [0.0, 0.0, 0.0]))
        assert metrics['accuracy'] == pytest.approx(1.0, abs=1e-6)
    elif scenario == 'single_point_precision_zero':
        metrics = calc_metrics(_make_tr([110.0], [100.0]))
        assert metrics['precision'] == pytest.approx(0.0, abs=1e-6)
    elif scenario == 'accuracy_capped_at_zero':
        metrics = calc_metrics(_make_tr([1000.0, 2000.0], [1.0, 2.0]))
        assert metrics['accuracy'] >= 0.0
    elif scenario == 'precision_correct_directions':
        metrics = calc_metrics(_make_tr([100.0, 111.0, 122.0], [100.0, 110.0, 120.0]))
        assert metrics['precision'] == pytest.approx(1.0, abs=1e-6)
    elif scenario == 'precision_wrong_directions':
        metrics = calc_metrics(_make_tr([100.0, 90.0, 80.0], [100.0, 110.0, 120.0]))
        assert metrics['precision'] == pytest.approx(0.0, abs=1e-6)
    elif scenario == 'mse_non_negative':
        metrics = calc_metrics(_make_tr([105.0, 108.0], [100.0, 110.0]))
        assert metrics['mse'] >= 0.0
    elif scenario == 'mae_non_negative':
        metrics = calc_metrics(_make_tr([105.0, 108.0], [100.0, 110.0]))
        assert metrics['mae'] >= 0.0
    elif scenario == 'all_fields_present':
        metrics = calc_metrics(_make_tr([105.0, 108.0, 112.0], [100.0, 110.0, 115.0]))
        for field in ('accuracy', 'precision', 'mse', 'autocorrelation', 'mae', 'lb_stat', 'lb_sq_stat'):
            assert field in metrics
    elif scenario == 'mse_formula':
        # MSE = ((0)^2 + (2)^2) / 2 = 2.0
        metrics = calc_metrics(_make_tr([100.0, 102.0], [100.0, 100.0]))
        assert metrics['mse'] == pytest.approx(2.0, abs=1e-5)
    elif scenario == 'mae_formula':
        # MAE = (0 + 2) / 2 = 1.0
        metrics = calc_metrics(_make_tr([100.0, 102.0], [100.0, 100.0]))
        assert metrics['mae'] == pytest.approx(1.0, abs=1e-5)
    elif scenario == 'raises_on_empty':
        # Create a raw dict, bypassing the builder
        bad_result = cast(TestResult, {
            '__type': 'TestResult',
            'training_dates': [datetime(2024, 1, 1)],
            'training_values': [100.0],
            'predict_dates': [],
            'predict_values': [],
            'expected_values': [],
            'resolution': 'd',
        })
        calc_metrics(bad_result)  # raises PredictorError → propagates
        return False  # must not be reached
    return True


# ---------------------------------------------------------------------------
# Wrappers: fit_params_to_polars
# ---------------------------------------------------------------------------

def _fit_params_to_polars_check(scenario: str) -> bool:
    base_dates = [datetime(2024, 1, 1) + timedelta(days=i) for i in range(7)]

    if scenario == 'round_trip':
        fp = create_fit_params(dates=base_dates[:5], values=[float(i * 10) for i in range(5)], resolution='d')
        df = fit_params_to_polars(fp, date_column='ds', value_column='y')
        assert isinstance(df, pl.DataFrame)
        assert list(df.columns) == ['ds', 'y']
        assert len(df) == 5
    elif scenario == 'column_names':
        fp = create_fit_params(dates=base_dates[:3], values=[1.0, 2.0, 3.0], resolution='d')
        df = fit_params_to_polars(fp, date_column='date_from', value_column='value')
        assert 'date_from' in df.columns
        assert 'value' in df.columns
    elif scenario == 'values_preserved':
        vals = [10.5, 20.0, 30.7]
        fp = create_fit_params(dates=base_dates[:3], values=vals, resolution='d')
        df = fit_params_to_polars(fp, date_column='ds', value_column='y')
        assert df['y'].to_list() == pytest.approx(vals)
    elif scenario == 'row_count':
        n = 7
        fp = create_fit_params(dates=base_dates, values=[float(i) for i in range(n)], resolution='d')
        df = fit_params_to_polars(fp, date_column='ds', value_column='y')
        assert len(df) == n
    return True


# ---------------------------------------------------------------------------
# Wrappers: create_from_timedelta
# ---------------------------------------------------------------------------

def _create_gran_from_timedelta(
    days: int = 0,
    hours: int = 0,
    minutes: int = 0,
    seconds: int = 0,
    weeks: int = 0,
) -> str:
    return create_from_timedelta(
        timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds, weeks=weeks)
    )


# ---------------------------------------------------------------------------
# Wrappers: is_in_class
# ---------------------------------------------------------------------------

def _is_in_class_check(class_name: str, value: str) -> bool:
    if class_name == 'ModelTypeName':
        return is_in_class(ModelTypeName, value)
    elif class_name == 'Gran':
        return is_in_class(Gran, value)
    return False


# ---------------------------------------------------------------------------
# Mapping: function name → (function, unpacker | None)
# ---------------------------------------------------------------------------

FUNCTIONS: dict[str, tuple[Any, Any]] = {
    # ── Core ─────────────────────────────────────────────────────────────────
    'fit':                                    (fit,                                    _unpack_fit),
    'predict':                                (predict,                                _unpack_predict),
    'test':                                   (test,                                   _unpack_test),
    # ── Reports ───────────────────────────────────────────────────────────────
    'save_report':                            (save_report,                            _unpack_save_test_result),
    # ── Validators: ModelOptions / CommonModel ────────────────────────────────
    'is_valid_model_options':                 (is_valid_model_options,                 None),
    'is_valid_common_model':                  (is_valid_common_model,                  None),
    # ── Validators: FitParams ─────────────────────────────────────────────────
    'is_valid_fit_params':                    (is_valid_fit_params,                    _unpack_fit),
    # ── Validators: PredictParams / PredictResult ─────────────────────────────
    'is_valid_predict_params':                (is_valid_predict_params,                None),
    'is_valid_predict_result':                (is_valid_predict_result,                _unpack_test_result),
    # ── Validators: TestParams / TestResult ───────────────────────────────────
    'is_valid_test_params':                   (is_valid_test_params,                   _unpack_test),
    'is_valid_test_result':                   (is_valid_test_result,                   _unpack_test_result),
    # ── Validators: TestMetrics ───────────────────────────────────────────────
    'is_valid_test_metrics':                  (is_valid_test_metrics,                  None),
    # ── Validators: Prophet-specific ──────────────────────────────────────
    'is_valid_seasonality':                   (is_valid_seasonality,                   None),
    'is_valid_prophet_options':               (is_valid_prophet_options,               None),
    'is_valid_prophet_model_predict_params':  (is_valid_prophet_model_predict_params,  None),
    # ── Serialization: primitive schemas ───────────────────────────────────────
    'round_trip_seasonality':                 (_round_trip_seasonality,                None),
    'round_trip_fit_params':                  (_round_trip_fit_params,                 None),
    'round_trip_model_options':               (_round_trip_model_options,              None),
    'round_trip_prophet_options':             (_round_trip_prophet_options,            None),
    'round_trip_predict_result':              (_round_trip_predict_result,             None),
    'round_trip_test_result':                 (_round_trip_test_result,                None),
    'round_trip_test_metrics':                (_round_trip_test_metrics,               None),
    'round_trip_prophet_predict_params':      (_round_trip_prophet_predict_params,     None),
    'round_trip_prophet_test_params':         (_round_trip_prophet_test_params,        None),
    # ── Serialization: dispatchers and the model ─────────────────────────────────────
    'serialize_dispatch':                     (_serialize_dispatch,                    None),
    'round_trip_model':                       (_round_trip_model,                      None),
    # ── Input data validation ──────────────────────────────────────────────
    'validate_fit_failure':                   (_validate_fit_failure,                  None),
    'validate_polars_failure':                (_validate_polars_failure,               None),
    'validate_predict_failure':               (_validate_predict_failure,              None),
    'validate_test_failure':                  (_validate_test_failure,                 None),
    # ── is_valid_test_result with dynamic data ──────────────────────────
    'is_valid_test_result_dynamic':           (_is_valid_test_result_dynamic,          None),
    # ── save_report with content checks ──────────────────────────────────
    'save_report_checks':                     (_save_report_checks,                    None),
    # ── Polars date formats ────────────────────────────────────────────────────
    'polars_csv_format':                      (_test_polars_csv_format,                None),
    'polars_native_type':                     (_test_polars_native_type,               None),
    # ── Public helpers ─────────────────────────────────────────────────────
    'calc_metrics_checks':                    (_calc_metrics_checks,                   None),
    'fit_params_to_polars_check':             (_fit_params_to_polars_check,            None),
    'create_gran_from_timedelta':             (_create_gran_from_timedelta,            None),
    'is_in_class_check':                      (_is_in_class_check,                     None),
}
