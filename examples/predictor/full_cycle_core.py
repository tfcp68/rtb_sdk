"""
Full predictor cycle on the common types:
  1) assemble the input strings (as if they came from outside);
  2) deserialize via the common dispatchers;
  3) call fit / predict / test;
  4) serialize the model and the results back into strings;
  5) save_report calls calc_metrics itself and returns TestMetrics.

The script reads the CSV/JSON itself (this is an example), while the predictor module itself creates
no files — the output directory is created right here.
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
    serialize_model, deserialize_model,
    serialize_fit_params, deserialize_fit_params,
    serialize_predict_params, deserialize_predict_params,
    serialize_test_params, deserialize_test_params,
    serialize_predict_result, deserialize_predict_result,
    serialize_test_result, deserialize_test_result,
)

cast(io.TextIOWrapper, sys.stdout).reconfigure(encoding='utf-8')


# === 0. Paths and preparing the output directory ===
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, 'test_data')
TRAIN_CSV_PATH = os.path.join(DATA_DIR, 'train_data.csv')
SAMPLE_CSV_PATH = os.path.join(DATA_DIR, 'sample_data.csv')
OPTIONS_JSON_PATH = os.path.join(DATA_DIR, 'prophet_options.json')
OUTPUT_DIR = os.path.join(DATA_DIR, 'output')
os.makedirs(OUTPUT_DIR, exist_ok=True)


# === 1. Read the CSV/JSON and build the schemas from a polars DataFrame and dict ===
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


# === 2. Serialize the inputs into strings (imitating an external format) ===
fit_params_str = serialize_fit_params(fit_params)
options_str = serialize_options(options)
predict_params_str = serialize_predict_params(predict_params, options)
test_params_str = serialize_test_params(test_params, options)


# === 3. Deserialize via the common dispatchers ===
print("=== DESERIALIZE INPUTS ===")
fit_params = deserialize_fit_params(fit_params_str)
options = deserialize_options(options_str)
predict_params = deserialize_predict_params(predict_params_str, options)
test_params = deserialize_test_params(test_params_str, options)
print(f"  FitParams: {len(fit_params['dates'])} point")
print(f"  ModelOptions: model_type={options['model_type']}")


# === 4. Fit ===
print("\n=== FIT ===")
model = fit(data=fit_params, options=options)
print(f"  trained, resolution={model['resolution']}")


# === 5. Model serialization and round-trip ===
print("\n=== SERIALIZE MODEL ===")
model_str = serialize_model(model)
model_back = deserialize_model(model_str)
print(f"  lineage: {len(model_str)}")
print(f"  restored: {model_back['type']}")


# === 6. Predict + serializing the result ===
print("\n=== PREDICT ===")
prediction = predict(model=model_back, options=options, data=predict_params)
pred_str = serialize_predict_result(prediction)
prediction_back = deserialize_predict_result(pred_str)
print(f"  forecasting-point: {len(prediction_back['predict_values'])}")


# === 7. Test + saving the reports ===
print("\n=== TEST + REPORT ===")
test_result = test(model=model_back, options=options, data=test_params)
if not is_valid_test_result(test_result):
    raise ValueError("Invalid TestResult")

metrics = save_report(test_result, 'md', os.path.join(OUTPUT_DIR, 'report.md'))
save_report(test_result, 'json', os.path.join(OUTPUT_DIR, 'report.json'))
try:
    save_report(test_result, 'png', os.path.join(OUTPUT_DIR, 'report.png'))
except ImportError:
    print("  PNG skipped (matplotlib fixed)")

print(f"  accuracy:  {metrics['accuracy']:.4f}")
print(f"  mae:       {metrics['mae']:.4f}")
print(f"  precision: {metrics['precision']:.4f}")


# === 8. Round-trip TestResult ===
test_result_str = serialize_test_result(test_result)
_ = deserialize_test_result(test_result_str)
print(f"\nTestResult serialized, size: {len(test_result_str)}")
print("\nDone.")