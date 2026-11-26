# predictor / examples

Full-cycle Predictor examples: generating test CSV data, loading it via Polars, training a Prophet model, forecasting, testing, schema serialization, and saving reports.

Run from the repository root as modules so that the project's root packages are imported without manually changing `sys.path`.

---

## Commands

```powershell
python -m examples.predictor.generate_test_data
python -m examples.predictor.full_cycle_core
python -m examples.predictor.full_cycle_core_and_serialization

python -m pytest tests/predictor
```

## generate_test_data

Generates input files in `examples/predictor/test_data/`.

Output:

| File | Description |
|---|---|
| `train_data.csv` | 150 daily points of the training series |
| `sample_data.csv` | 30 daily points of the test period |
| `prophet_options.json` | Prophet model settings |

## full_cycle_core

Shows the full cycle using the common types and strings:

1. Loads `train_data.csv` and `sample_data.csv` via `polars.read_csv(..., try_parse_dates=True)`, then builds `FitParams` and `TestParams`.
2. Loads `prophet_options.json`, builds `ModelOptions`, and serializes the input schemas to JSON strings.
3. Deserializes them via the common `deserialize_*` dispatchers.
4. Runs `fit`, `predict`, `test`.
5. Serializes the model and results back to strings.
6. Saves reports via `save_report`.

## full_cycle_core_and_serialization

A shorter full-cycle example for checking the common serialization contract:

1. Loads CSV via `polars.read_csv(..., try_parse_dates=True)` and prepares the input schemas as JSON strings.
2. Restores the schemas via `deserialize_fit_params`, `deserialize_options`, `deserialize_predict_params`, `deserialize_test_params`.
3. Runs `fit / predict / test`.
4. Serializes the `model`, `PredictResult`, and `TestResult`.
5. Saves reports to `test_data/output/`.

## Input data

```
examples/predictor/test_data/
  train_data.csv
  sample_data.csv
  prophet_options.json
```

The CSV files use the following columns:

| Column | Description |
|---|---|
| `date_from` | Period start |
| `date_to` | Period end |
| `value` | Time-series value |

Both full-cycle examples read the source data via `polars.read_csv(..., try_parse_dates=True)`. The `date_from` column is additionally normalized in `create_fit_params_from_polars_df`, including string dates and native Polars `Date`/`Datetime` types.

## Output data

```
examples/predictor/test_data/output/
  report.md
  report.json
  report.png
```

`save_report` itself triggers the metrics calculation and returns `TestMetrics`. The PNG report is created only if `matplotlib` is installed; without it, the scripts skip the PNG and continue.

## Related tests

Predictor tests are located in `tests/predictor/`.

| Path | Responsibility |
|---|---|
| `test_predictor.py` | JSON cases for `fit`, `predict`, `test`, `save_report`, `is_valid_test_result` |
| `test_serialization.py` | Serialization/deserialization round-trip of schemas (Seasonality, FitParams, ProphetOptions, PredictResult, TestResult, TestMetrics, ProphetModelPredictParams, ProphetModelTestParams, common dispatchers for options/predict params/test params, end-to-end ProphetModel) |
| `test_input_validation.py` | Validator contract: NaN/inf in values, unparseable date, dates ↔ resolution mismatch, different CSV date formats via polars, series gaps, resolution conflict in predict, gap between training and expected in test |
| `test_polars_date_formats.py` | Polars date parser over 8 formats (`%Y-%m-%d %H:%M:%S`, ISO, date without time, slash, dot, fractional seconds, Z, +03:00) and native Polars `Date`/`Datetime` types |
| `test_file_io.py` | `is_valid_test_result` and `save_report` (md/json/png + rejection of an invalid result) |
| `cases/` | JSON cases for parameterized tests |
| `reports/` | Reference and generated test reports |
