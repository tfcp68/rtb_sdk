"""
Shortened full-cycle example: the input is only JSON strings, as if they
came from a queue / DB / file. We use the common dispatchers to restore the
schemas, go through fit / predict / test, save the report (save_report computes
the metrics itself).
"""
import io
import sys
import os
import json
from typing import cast

import polars as pl

from rtb_sdk.predictor import (
    fit, predict, test,
    save_report,
)
from rtb_sdk.helpers.predictor import (
    create_prophet_options_from_dict,
    create_fit_params_from_polars_df,
    create_prophet_model_predict_params,
    create_prophet_model_test_params,
    is_valid_test_result, serialize_options, deserialize_options,
    serialize_model,
    serialize_fit_params, deserialize_fit_params,
    serialize_predict_params, deserialize_predict_params,
    serialize_test_params, deserialize_test_params,
    serialize_predict_result,
    serialize_test_result,
)

cast(io.TextIOWrapper, sys.stdout).reconfigure(encoding='utf-8')


# === 0. Paths and preparing the output ===
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, 'test_data')
TRAIN_CSV_PATH = os.path.join(DATA_DIR, 'train_data.csv')
SAMPLE_CSV_PATH = os.path.join(DATA_DIR, 'sample_data.csv')
OPTIONS_JSON_PATH = os.path.join(DATA_DIR, 'prophet_options.json')
OUTPUT_DIR = os.path.join(DATA_DIR, 'output')
os.makedirs(OUTPUT_DIR, exist_ok=True)


# === 1. Prepare the inputs as JSON strings ===
train_df = pl.read_csv(TRAIN_CSV_PATH, try_parse_dates=True)
sample_df = pl.read_csv(SAMPLE_CSV_PATH, try_parse_dates=True)

fit_params = create_fit_params_from_polars_df(
    df=train_df, date_column='date_from', value_column='value',
)
sample_params = create_fit_params_from_polars_df(
    df=sample_df, date_column='date_from', value_column='value',
)

with open(OPTIONS_JSON_PATH, encoding='utf-8') as f:
    options = create_prophet_options_from_dict(json.load(f))

predict_params = create_prophet_model_predict_params(
    resolution=fit_params['resolution'],
    forecast_periods=len(sample_params['dates']),
)
test_params = create_prophet_model_test_params(
    training_dates=fit_params['dates'],
    training_values=fit_params['values'],
    expected_dates=sample_params['dates'],
    expected_values=sample_params['values'],
    resolution=fit_params['resolution'],
)

fit_params_str = serialize_fit_params(fit_params)
options_str = serialize_options(options)
predict_params_str = serialize_predict_params(predict_params, options)
test_params_str = serialize_test_params(test_params, options)


# === 2. Deserialization ===
print("=== DESERIALIZE ===")
fit_params = deserialize_fit_params(fit_params_str)
options = deserialize_options(options_str)
predict_params = deserialize_predict_params(predict_params_str, options)
test_params = deserialize_test_params(test_params_str, options)
print(f"  options.model_type = {options['model_type']}")


# === 3. Fit / Predict / Test ===
print("\n=== FIT / PREDICT / TEST ===")
model = fit(data=fit_params, options=options)
prediction = predict(model=model, options=options, data=predict_params)
test_result = test(model=model, options=options, data=test_params)
if not is_valid_test_result(test_result):
    raise ValueError("Invalid TestResult")
print(f"  forecasting-point: {len(prediction['predict_values'])}")


# === 4. Serialization of the outputs ===
print("\n=== SERIALIZE OUT ===")
model_str = serialize_model(model)
pred_str = serialize_predict_result(prediction)
test_result_str = serialize_test_result(test_result)
print(f"  model_str size:          {len(model_str)}")
print(f"  predict_result_str size: {len(pred_str)}")
print(f"  test_result_str size:    {len(test_result_str)}")


# === 5. Report (calc_metrics inside save_report) ===
print("\n=== REPORT ===")
metrics = save_report(test_result, 'md', os.path.join(OUTPUT_DIR, 'report.md'))
save_report(test_result, 'json', os.path.join(OUTPUT_DIR, 'report.json'))
try:
    save_report(test_result, 'png', os.path.join(OUTPUT_DIR, 'report.png'))
except ImportError:
    print("  PNG skipped (matplotlib fixed)")
print(f"  accuracy: {metrics['accuracy']:.4f}, mae: {metrics['mae']:.4f}")
print("\nDone.")