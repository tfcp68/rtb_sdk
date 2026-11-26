# Predictor

## Table of contents

- [Description](#description)
  - [Quick start](#quick-start)
    - [Fit](#fit)
    - [Predict](#predict)
    - [Test](#test)
  - [Input data validation](#input-data-validation)
- [Data types](#data-types)
  - [ModelType](#modeltype)
  - [Granularity](#granularity)
  - [ReportType](#reporttype)
  - [ModelOptions](#modeloptions)
  - [FitParams](#fitparams)
  - [CommonModel](#commonmodel)
  - [PredictParams](#predictparams)
  - [PredictResult](#predictresult)
  - [TestParams](#testparams)
  - [TestResult](#testresult)
  - [TestMetrics](#testmetrics)
  - [Prophet types](#prophet-types)
    - [ProphetOptions](#prophetoptions)
      - [GrowthNameType](#growthnametype)
      - [SeasonalityModeType](#seasonalitymodetype)
      - [SeasonalityNameType](#seasonalitynametype)
      - [Seasonality](#seasonality)
    - [ProphetModel](#prophetmodel)
    - [ProphetModelPredictParams](#prophetmodelpredictparams)
    - [ProphetModelTestParams](#prophetmodeltestparams)
- [Functions](#functions)
  - [Core](#core)
    - [fit](#fit-1)
    - [predict](#predict-1)
    - [test](#test-1)
  - [Common (de)serialize](#common-deserialize)
  - [Metrics](#metrics)
    - [calc_metrics](#calc_metrics)
  - [Working with reports](#working-with-reports)
    - [save_report](#save_report)

---

## Description

The module is intended for forecasting time series based on historical data.

The work consists of three stages:
1. **fit** — training the model on historical data;
2. **predict** — building a forecast for a given period;
3. **test** — evaluating forecast accuracy by comparing it with real data.

### Quick start

In the examples below, input schemas are stored in JSON files. The file contents are first
loaded as a string and then passed to `deserialize_*`; the result of
`serialize_*` is saved back to a file via `write_text`.

#### Fit

```python
from pathlib import Path

from rtb_sdk.predictor import (
    fit,
    deserialize_fit_params,
    deserialize_options,
    serialize_model,
)

# Read the input JSON schemas from files as strings.
fit_params_str = Path("fit_params.json").read_text(encoding="utf-8")
options_str = Path("options.json").read_text(encoding="utf-8")

# 1. Deserialize via the common dispatchers.
fit_params = deserialize_fit_params(fit_params_str)
options    = deserialize_options(options_str)   # determines the type itself from model_type

# 2. Training.
model = fit(data=fit_params, options=options)

# 3. Serialize the model back to a string and save it to a file.
model_str: str = serialize_model(model)
Path("model.json").write_text(model_str, encoding="utf-8")
```

#### Predict

```python
from pathlib import Path

from rtb_sdk.predictor import (
    predict,
    deserialize_model,
    deserialize_options,
    deserialize_predict_params,
    serialize_predict_result,
)

# Take the trained model schema from the file saved at the Fit step.
model_str = Path("model.json").read_text(encoding="utf-8")
options_str = Path("options.json").read_text(encoding="utf-8")
predict_params_str = Path("predict_params.json").read_text(encoding="utf-8")

# 1. Deserialization via the common dispatchers.
model          = deserialize_model(model_str)           # first CommonModel → then the concrete one
options        = deserialize_options(options_str)
predict_params = deserialize_predict_params(predict_params_str, options)

# 2. Forecast.
result = predict(model=model, options=options, data=predict_params)

# 3. Serialize the forecast result and save it to a file.
result_str: str = serialize_predict_result(result)
Path("predict_result.json").write_text(result_str, encoding="utf-8")
```

#### Test

```python
from pathlib import Path

from rtb_sdk.predictor import (
    test,
    deserialize_model,
    deserialize_options,
    deserialize_test_params,
    serialize_test_result,
    save_report,
)
from rtb_sdk.helpers.predictor import is_valid_test_result

# Take the trained model schema from the file saved at the Fit step.
model_str = Path("model.json").read_text(encoding="utf-8")
options_str = Path("options.json").read_text(encoding="utf-8")
test_params_str = Path("test_params.json").read_text(encoding="utf-8")

model       = deserialize_model(model_str)
options     = deserialize_options(options_str)
test_params = deserialize_test_params(test_params_str, options)

result = test(model=model, options=options, data=test_params)
if not is_valid_test_result(result):
    raise ValueError("Invalid TestResult")

# save_report calls calc_metrics itself and returns TestMetrics;
# there is no need to call calc_metrics separately.
metrics = save_report(result=result, report_type='md',   output_report_path='report.md')
save_report(result=result, report_type='json', output_report_path='report.json')
try:
    save_report(result=result, report_type='png',  output_report_path='report.png')
except ImportError:
    pass

# If desired, TestResult can also be serialized and saved to a file.
result_str: str = serialize_test_result(result)
Path("test_result.json").write_text(result_str, encoding="utf-8")
```

### Input data validation

Predictor validates the time series before training, forecasting, and testing. When the contract is violated, a `PredictorError` with `PARAMETER_ERROR_CODE` is raised; invalid rows are not silently dropped.

| Scenario | Behavior |
| --- | --- |
| `None`, `NaN`, `inf`, a string like `"na"`, or a non-numeric value in `values` | Error at the stage of building/validating `FitParams`, `TestParams`, `PredictResult`, or `TestResult` |
| Invalid date, empty date, a date string that cannot be parsed | Error; for Polars/CSV the value is first cast to `Datetime`, then checked for `null` |
| Different lengths of `dates` and `values` | Error, because a date and a value must form one-to-one pairs |
| Gap, duplicate, or reversed order of dates in Python lists | Error: adjacent dates must go strictly forward with a step of `resolution` |
| Date gap in CSV/Polars | The data is sorted by date, after which the whole series is checked for continuity; if there is a gap or duplicate after sorting, an error is returned |
| The actual date granularity differs from `resolution` | Error before training or testing |
| `predict` is called with a `resolution` different from the trained model's `resolution` | Error, so that the forecast is not built with a different step than the model's history |
| In `test` there is a gap between the training period and the expected dates | Error; the first `expected_date` must come immediately after the last training date |
| `expected_dates` do not match the dates the model forecasts | Test result validation error |

Additional scenarios worth checking in integration data: duplicate timestamps after aggregation, mixing of time zones before loading into Predictor, monthly series with irregular calendar dates, and series where all `actual` values are zero. For the `accuracy` metric, points with `actual = 0` are excluded from MAPE; if there are no such points at all, MAPE is taken to be `0`.

---

## Data types

### ModelType

The type of the forecasting model:
- `'prophet'` — a statistical time-series forecasting model

Prototype:
```python
type ModelType = Literal["prophet",]
```

```python
class ModelTypeName:
    PROPHET: ModelType = 'prophet'
```

Example:
```python
from rtb_sdk.schemas import ModelType
from rtb_sdk.constants import ModelTypeName

model_type: ModelType = ModelTypeName.PROPHET
```

### Granularity

The time-series data step:

| Value | Description |
| --- | --- |
| `'t'` | 10 minutes |
| `'h'` | Hour |
| `'d'` | Day |
| `'w'` | Week |
| `'m'` | Month |

Prototype:
```python
type Granularity = Literal['t', 'h', 'd', 'w', 'm']
```

```python
class Gran:
    TEN_MINUTES: Granularity = 't'
    HOUR: Granularity = 'h'
    DAY: Granularity = 'd'
    WEEK: Granularity = 'w'
    MONTH: Granularity = 'm'
```

Example:
```python
from rtb_sdk.schemas import Granularity
from rtb_sdk.constants import Gran

resolution: Granularity = Gran.DAY
```

### ReportType

Report format:

| Value | Description |
| --- | --- |
| `'md'` | Markdown |
| `'json'` | JSON |
| `'png'` | PNG chart |

Prototype:
```python
type ReportType = Literal['md', 'json', 'png']
```

### ModelOptions

Common options of the forecasting model

```python
class ModelOptions(DiscriminatedTypedDict):
    model_type: ModelType
```

| Parameter | Description | Possible values | Default |
| --- | --- | --- | --- |
| `model_type` | Model type; determines the algorithm used and the set of additional parameters | [`ModelType`](#modeltype) | — |

> The specific set of parameters depends on the selected model. With `model_type = 'prophet'`, [`ProphetOptions`](#prophetoptions) is used, which extends `ModelOptions` with Prophet-specific fields.

Methods:

| Method | Argument types | Return type | Description |
| --- | --- | --- | --- |
| `get_model_options_model_type` | `options: ModelOptions`, `default: ModelType \| None = None` | [`ModelType`](#modeltype) \| None | Returns the model type |
| `is_valid_model_options` | `options: Any` | `bool` | Checks the validity of the options |
| `create_model_options` | `model_type: ModelType` | [`ModelOptions`](#modeloptions) | Creates a ModelOptions object |
| `create_model_options_from_dict` | `data: dict` | [`ModelOptions`](#modeloptions) | Creates ModelOptions from a dictionary |
| `serialize_model_options` | `options: ModelOptions` | `str` | Serializes ModelOptions to a JSON string |
| `deserialize_model_options` | `data: str` | [`ModelOptions`](#modeloptions) | Restores ModelOptions from a JSON string |

```python
from rtb_sdk.helpers.predictor import (
    get_model_options_model_type,
    is_valid_model_options,
    create_model_options,
    create_model_options_from_dict,
    serialize_model_options,
    deserialize_model_options,
)
```

### FitParams

Input parameters for training the model

```python
class FitParams(DiscriminatedTypedDict):
    dates: list[datetime]
    values: list[float]
    resolution: Granularity
```

| Parameter | Description | Possible values | Default |
| --- | --- | --- | --- |
| `dates` | Observation timestamps (period start dates) in chronological order | `list[datetime]` | — |
| `values` | Numeric values of the series; each element corresponds to a date from `dates` | `list[float]` | — |
| `resolution` | Step between adjacent observations; fixed in the trained model | [`Granularity`](#granularity) | — |

Used in: the `data` parameter of the `fit` function.

Example:
```python
from datetime import datetime
from rtb_sdk.schemas import FitParams

params: FitParams = {
    'dates': [datetime(2023, 1, 1), datetime(2023, 1, 2)],
    'values': [1716677, 1924853],
    'resolution': 'd'
}
```

Methods:

| Method | Argument types | Return type | Description |
| --- | --- | --- | --- |
| `get_fit_params_dates` | `data: FitParams`, `default: list[datetime] \| None = None` | `list[datetime] \| None` | Returns the list of dates |
| `get_fit_params_values` | `data: FitParams`, `default: list[float] \| None = None` | `list[float] \| None` | Returns the list of values |
| `get_fit_params_resolution` | `data: FitParams`, `default: Granularity \| None = None` | [`Granularity`](#granularity) \| None | Returns the data step |
| `is_valid_fit_params` | `data: Any` | `bool` | Checks the validity of the object |
| `create_fit_params` | `dates: list[datetime]`, `values: list[float]`, `resolution: Granularity` | [`FitParams`](#fitparams) | Creates a FitParams object |
| `create_fit_params_from_dict` | `data: dict` | [`FitParams`](#fitparams) | Creates FitParams from a dictionary |
| `create_fit_params_from_polars_df` | `df: pl.DataFrame`, `date_column: str`, `value_column: str` | [`FitParams`](#fitparams) | Creates from a Polars DataFrame; the step is determined automatically from the date difference |
| `create_from_timedelta` | `delta_time: timedelta` | [`Granularity`](#granularity) | Determines Granularity from a timedelta |
| `fit_params_to_polars` | `data: FitParams`, `date_column: str`, `value_column: str` | `pl.DataFrame` | Converts to a Polars DataFrame |
| `serialize_fit_params` | `data: FitParams` | `str` | Serializes FitParams to a JSON string (dates → `__datetime__`) |
| `deserialize_fit_params` | `data: str` | [`FitParams`](#fitparams) | Restores FitParams from a JSON string |

```python
from rtb_sdk.helpers.predictor import (
    get_fit_params_dates,
    get_fit_params_values,
    get_fit_params_resolution,
    is_valid_fit_params,
    create_fit_params,
    create_fit_params_from_dict,
    create_fit_params_from_polars_df,
    create_from_timedelta,
    fit_params_to_polars,
    serialize_fit_params,
    deserialize_fit_params,
)
```

### CommonModel

The base type of a trained model. All concrete models inherit from `CommonModel`.

```python
class CommonModel(DiscriminatedTypedDict):
    type: ModelType
    resolution: Granularity
    description: Optional[str]
```

| Parameter | Description | Possible values | Default |
| --- | --- | --- | --- |
| `type` | Discriminator model type; uniquely identifies the concrete subclass | [`ModelType`](#modeltype) | — |
| `resolution` | Step of the data the model was trained on; taken from `FitParams.resolution` | [`Granularity`](#granularity) | — |
| `description` | Optional text description of the model | `str \| None` | `None` |

Used in: returned from `fit`, passed to `predict`, `test`.

Methods:

| Method | Argument types | Return type | Description |
| --- | --- | --- | --- |
| `get_common_model_type` | `model: CommonModel`, `default: ModelType \| None = None` | [`ModelType`](#modeltype) \| None | Returns the model type |
| `get_common_model_resolution` | `model: CommonModel`, `default: Granularity \| None = None` | [`Granularity`](#granularity) \| None | Returns the data step |
| `get_common_model_description` | `model: CommonModel`, `default: str \| None = None` | `str \| None` | Returns the description |
| `serialize_common_model` | `model: CommonModel` | `str` | Serializes CommonModel to a JSON string |
| `deserialize_common_model` | `data: str` | [`CommonModel`](#commonmodel) | Restores CommonModel from a JSON string |

```python
from rtb_sdk.schemas import CommonModel
from rtb_sdk.helpers.predictor import (
    get_common_model_type,
    get_common_model_resolution,
    get_common_model_description,
    serialize_common_model,
    deserialize_common_model,
)
```

### PredictParams

A marker base type of forecast parameters. Concrete implementations add algorithm-specific fields.

```python
class PredictParams(DiscriminatedTypedDict):
    pass
```

Concrete implementations add algorithm-specific fields (in particular, `resolution` and forecast horizon parameters).

Used in: the base type of the `data` parameter of the `predict` function. For Prophet, [`ProphetModelPredictParams`](#prophetmodelpredictparams) is used.

Methods:

| Method | Argument types | Return type | Description |
| --- | --- | --- | --- |
| `is_valid_predict_params` | `data: Any` | `bool` | Checks the validity of the object |
| `serialize_predict_params` | `data: PredictParams`, `options: ModelOptions` | `str` | Serializes PredictParams to a JSON string; the concrete model is determined by `options.model_type` |
| `deserialize_predict_params` | `data: str`, `options: ModelOptions` | [`PredictParams`](#predictparams) | Restores PredictParams from a JSON string; the concrete model is determined by `options.model_type` |

```python
from rtb_sdk.helpers.predictor import (
    is_valid_predict_params,
    serialize_predict_params,
    deserialize_predict_params,
)
```

### PredictResult

The forecasting result

```python
class PredictResult(DiscriminatedTypedDict):
    training_dates: list[datetime]
    training_values: list[float]
    predict_dates: list[datetime]
    predict_values: list[float]
```

| Parameter | Description | Possible values | Default |
| --- | --- | --- | --- |
| `training_dates` | Dates of the training observations used in training | `list[datetime]` | — |
| `training_values` | Values of the training series corresponding to `training_dates` | `list[float]` | — |
| `predict_dates` | Dates of the forecast period (following the last training point) | `list[datetime]` | — |
| `predict_values` | Forecast values corresponding to `predict_dates` | `list[float]` | — |

Used in: returned from `predict`.

Methods:

| Method | Argument types | Return type | Description |
| --- | --- | --- | --- |
| `get_predict_result_training_dates` | `result: PredictResult`, `default: list[datetime] \| None = None` | `list[datetime] \| None` | Returns the training sample dates |
| `get_predict_result_training_values` | `result: PredictResult`, `default: list[float] \| None = None` | `list[float] \| None` | Returns the training sample values |
| `get_predict_result_predict_dates` | `result: PredictResult`, `default: list[datetime] \| None = None` | `list[datetime] \| None` | Returns the forecast dates |
| `get_predict_result_predict_values` | `result: PredictResult`, `default: list[float] \| None = None` | `list[float] \| None` | Returns the forecast values |
| `is_valid_predict_result` | `result: Any` | `bool` | Checks the validity of the object |
| `create_predict_result` | `training_dates: list[datetime]`, `training_values: list[float]`, `predict_dates: list[datetime]`, `predict_values: list[float]` | [`PredictResult`](#predictresult) | Creates a PredictResult object |
| `create_predict_result_from_dict` | `data: dict` | [`PredictResult`](#predictresult) | Creates PredictResult from a dictionary |
| `serialize_predict_result` | `result: PredictResult` | `str` | Serializes PredictResult to a JSON string |
| `deserialize_predict_result` | `data: str` | [`PredictResult`](#predictresult) | Restores PredictResult from a JSON string |

```python
from rtb_sdk.helpers.predictor import (
    get_predict_result_training_dates,
    get_predict_result_training_values,
    get_predict_result_predict_dates,
    get_predict_result_predict_values,
    is_valid_predict_result,
    create_predict_result,
    create_predict_result_from_dict,
    serialize_predict_result,
    deserialize_predict_result,
)
```

### TestParams

Input parameters for testing the model

```python
class TestParams(DiscriminatedTypedDict):
    training_dates: list[datetime]
    training_values: list[float]
    expected_dates: list[datetime]
    expected_values: list[float]
    resolution: Granularity
```

| Parameter | Description | Possible values | Default |
| --- | --- | --- | --- |
| `training_dates` | Dates of the training sample | `list[datetime]` | — |
| `training_values` | Values of the training sample corresponding to `training_dates` | `list[float]` | — |
| `expected_dates` | Dates of the test period; real observations to compare with the forecast | `list[datetime]` | — |
| `expected_values` | Actual values of the test period corresponding to `expected_dates` | `list[float]` | — |
| `resolution` | Data step; must match the `resolution` of the training sample | [`Granularity`](#granularity) | — |

Used in: the `data` parameter of the `test` function.

Methods:

| Method | Argument types | Return type | Description |
| --- | --- | --- | --- |
| `get_test_params_training_dates` | `data: TestParams`, `default: list[datetime] \| None = None` | `list[datetime] \| None` | Returns the training sample dates |
| `get_test_params_training_values` | `data: TestParams`, `default: list[float] \| None = None` | `list[float] \| None` | Returns the training sample values |
| `get_test_params_expected_dates` | `data: TestParams`, `default: list[datetime] \| None = None` | `list[datetime] \| None` | Returns the test period dates |
| `get_test_params_expected_values` | `data: TestParams`, `default: list[float] \| None = None` | `list[float] \| None` | Returns the actual values of the test period |
| `get_test_params_resolution` | `data: TestParams`, `default: Granularity \| None = None` | [`Granularity`](#granularity) \| None | Returns the data step |
| `is_valid_test_params` | `data: Any` | `bool` | Checks the validity of the object |
| `create_test_params` | `training_dates: list[datetime]`, `training_values: list[float]`, `expected_dates: list[datetime]`, `expected_values: list[float]`, `resolution: Granularity` | [`TestParams`](#testparams) | Creates a TestParams object |
| `create_test_params_from_dict` | `data: dict` | [`TestParams`](#testparams) | Creates TestParams from a dictionary |
| `serialize_test_params` | `data: TestParams`, `options: ModelOptions` | `str` | Serializes TestParams to a JSON string; the concrete model is determined by `options.model_type` |
| `deserialize_test_params` | `data: str`, `options: ModelOptions` | [`TestParams`](#testparams) | Restores TestParams from a JSON string; the concrete model is determined by `options.model_type` |

```python
from rtb_sdk.helpers.predictor import (
    get_test_params_training_dates,
    get_test_params_training_values,
    get_test_params_expected_dates,
    get_test_params_expected_values,
    get_test_params_resolution,
    is_valid_test_params,
    create_test_params,
    create_test_params_from_dict,
    serialize_test_params,
    deserialize_test_params,
)
```

### TestResult

The model testing result

```python
class TestResult(DiscriminatedTypedDict):
    training_dates: list[datetime]
    training_values: list[float]
    predict_dates: list[datetime]
    predict_values: list[float]
    expected_values: list[float]
    resolution: Granularity
```

| Parameter | Description | Possible values | Default |
| --- | --- | --- | --- |
| `training_dates` | Dates of the training sample | `list[datetime]` | — |
| `training_values` | Values of the training sample corresponding to `training_dates` | `list[float]` | — |
| `predict_dates` | Dates of the test period for which the forecast was built | `list[datetime]` | — |
| `predict_values` | Model forecast values corresponding to `predict_dates` | `list[float]` | — |
| `expected_values` | Actual values of the test period (the reference to compare with `predict_values`) | `list[float]` | — |
| `resolution` | Data step; inherited from `TestParams.resolution` | [`Granularity`](#granularity) | — |

Used in: returned from `test`; passed to `calc_metrics`, `save_report`.

Methods:

| Method | Argument types | Return type | Description |
| --- | --- | --- | --- |
| `get_test_result_training_dates` | `result: TestResult`, `default: list[datetime] \| None = None` | `list[datetime] \| None` | Returns the training sample dates |
| `get_test_result_training_values` | `result: TestResult`, `default: list[float] \| None = None` | `list[float] \| None` | Returns the training sample values |
| `get_test_result_predict_dates` | `result: TestResult`, `default: list[datetime] \| None = None` | `list[datetime] \| None` | Returns the forecast dates |
| `get_test_result_predict_values` | `result: TestResult`, `default: list[float] \| None = None` | `list[float] \| None` | Returns the forecast values |
| `get_test_result_expected_values` | `result: TestResult`, `default: list[float] \| None = None` | `list[float] \| None` | Returns the actual values of the test period |
| `get_test_result_resolution` | `result: TestResult`, `default: Granularity \| None = None` | [`Granularity`](#granularity) \| None | Returns the data step |
| `is_valid_test_result` | `result: Any` | `bool` | Checks the validity of the object |
| `create_test_result` | `training_dates: list[datetime]`, `training_values: list[float]`, `predict_dates: list[datetime]`, `predict_values: list[float]`, `expected_values: list[float]`, `resolution: Granularity` | [`TestResult`](#testresult) | Creates a TestResult object |
| `create_test_result_from_dict` | `data: dict` | [`TestResult`](#testresult) | Creates TestResult from a dictionary |
| `serialize_test_result` | `result: TestResult` | `str` | Serializes TestResult to a JSON string |
| `deserialize_test_result` | `data: str` | [`TestResult`](#testresult) | Restores TestResult from a JSON string |

```python
from rtb_sdk.helpers.predictor import (
    get_test_result_training_dates,
    get_test_result_training_values,
    get_test_result_predict_dates,
    get_test_result_predict_values,
    get_test_result_expected_values,
    get_test_result_resolution,
    is_valid_test_result,
    create_test_result,
    create_test_result_from_dict,
    serialize_test_result,
    deserialize_test_result,
)
```

### TestMetrics

Forecast quality metrics computed from the test results

```python
class TestMetrics(DiscriminatedTypedDict):
    accuracy: float
    precision: float
    mse: float
    autocorrelation: float
    mae: float
    lb_stat: float
    lb_sq_stat: float
```

| Parameter | Description | Possible values | Default |
| --- | --- | --- | --- |
| `accuracy` | Forecast accuracy: `max(0, 1 − MAPE)`; points with `actual = 0` are not included in MAPE | `float`, \[0, 1\] | — |
| `precision` | Share of steps where `actual` and `predicted` change in the same direction; a zero change does not count as a match | `float`, \[0, 1\] | — |
| `mse` | Mean Squared Error | `float`, ≥ 0 | — |
| `autocorrelation` | Lag-1 autocorrelation of the residuals `(predicted − actual)`; values close to 0 — no pronounced autocorrelation | `float`, \[−1, 1\] | — |
| `mae` | Mean Absolute Error in the units of the series | `float`, ≥ 0 | — |
| `lb_stat` | Q-statistic of the Ljung–Box test on the residuals (lag=1); large values — presence of autocorrelation in the residuals | `float`, ≥ 0 | — |
| `lb_sq_stat` | Q-statistic of the Ljung–Box test on the squared residuals (lag=1); large values — presence of ARCH effects (volatility clustering) | `float`, ≥ 0 | — |

Used in: returned from `calc_metrics`; used in `save_report`.

Methods:

| Method | Argument types | Return type | Description |
| --- | --- | --- | --- |
| `get_test_metrics_accuracy` | `metrics: TestMetrics`, `default: float \| None = None` | `float \| None` | Returns the accuracy metric |
| `get_test_metrics_precision` | `metrics: TestMetrics`, `default: float \| None = None` | `float \| None` | Returns the precision metric |
| `get_test_metrics_mse` | `metrics: TestMetrics`, `default: float \| None = None` | `float \| None` | Returns the mse metric |
| `get_test_metrics_autocorrelation` | `metrics: TestMetrics`, `default: float \| None = None` | `float \| None` | Returns the autocorrelation metric |
| `get_test_metrics_mae` | `metrics: TestMetrics`, `default: float \| None = None` | `float \| None` | Returns the mae metric |
| `get_test_metrics_lb_stat` | `metrics: TestMetrics`, `default: float \| None = None` | `float \| None` | Returns the Q-statistic of the Ljung–Box test on the residuals |
| `get_test_metrics_lb_sq_stat` | `metrics: TestMetrics`, `default: float \| None = None` | `float \| None` | Returns the Q-statistic of the Ljung–Box test on the squared residuals |
| `is_valid_test_metrics` | `metrics: Any` | `bool` | Checks the validity of the object |
| `create_test_metrics` | `accuracy: float`, `precision: float`, `mse: float`, `autocorrelation: float`, `mae: float`, `lb_stat: float`, `lb_sq_stat: float` | [`TestMetrics`](#testmetrics) | Creates a TestMetrics object |
| `create_test_metrics_from_dict` | `data: dict` | [`TestMetrics`](#testmetrics) | Creates TestMetrics from a dictionary |
| `serialize_test_metrics` | `metrics: TestMetrics` | `str` | Serializes TestMetrics to a JSON string |
| `deserialize_test_metrics` | `data: str` | [`TestMetrics`](#testmetrics) | Restores TestMetrics from a JSON string |

```python
from rtb_sdk.helpers.predictor import (
    get_test_metrics_accuracy,
    get_test_metrics_precision,
    get_test_metrics_mse,
    get_test_metrics_autocorrelation,
    get_test_metrics_mae,
    get_test_metrics_lb_stat,
    get_test_metrics_lb_sq_stat,
    is_valid_test_metrics,
    create_test_metrics,
    create_test_metrics_from_dict,
    serialize_test_metrics,
    deserialize_test_metrics,
)
```

### Prophet types

In the current version, `prophet` is an internal Prophet-like implementation: training estimates a linear trend and seasonal offsets, and the external `prophet` package is not called. Of `ProphetOptions`, the calculation currently uses the `weekly_seasonality` flag and the periods from `seasonalities`; the remaining fields are validated and serialized for API compatibility.

#### ProphetOptions

Prophet model options. Extends [`ModelOptions`](#modeloptions).

```python
class ProphetOptions(ModelOptions):
    growth: GrowthNameType
    changepoint_prior_scale: float
    seasonality_mode: SeasonalityModeType
    seasonality_prior_scale: float
    yearly_seasonality: bool
    weekly_seasonality: bool
    n_changepoints: int
    changepoint_range: float
    seasonalities: dict[SeasonalityNameType, Seasonality]
```

| Parameter | Description | Possible values | Default |
| --- | --- | --- | --- |
| `growth` | Trend type | [`GrowthNameType`](#growthnametype) | `'linear'` |
| `changepoint_prior_scale` | Trend flexibility; larger values — the trend changes direction more actively | `float`, > 0 | `0.05` |
| `seasonality_mode` | How seasonality is accounted for | [`SeasonalityModeType`](#seasonalitymodetype) | `'additive'` |
| `seasonality_prior_scale` | Regularization of the seasonal components; small values reduce their influence | `float`, > 0 | `10.0` |
| `yearly_seasonality` | Whether to account for yearly seasonality | `bool` | `true` |
| `weekly_seasonality` | Whether to account for weekly seasonality | `bool` | `true` |
| `n_changepoints` | Number of potential trend changepoints | `int`, > 0 | `25` |
| `changepoint_range` | Share of history, from the start of the series, within which changepoints are searched | `float`, > 0 | `0.8` |
| `seasonalities` | Dictionary of custom seasonality components | `dict[SeasonalityNameType, Seasonality]`, see [`SeasonalityNameType`](#seasonalitynametype) and [`Seasonality`](#seasonality) | `{}` |
| `model_type` | Discriminator model type; always `'prophet'` | [`ModelType`](#modeltype) | `'prophet'` |

JSON example (`serialize_prophet_options` returns a string of this form):
```json
{
  "model_type": "prophet",
  "growth": "linear",
  "changepoint_prior_scale": 0.001,
  "seasonality_mode": "additive",
  "seasonality_prior_scale": 0.05,
  "yearly_seasonality": true,
  "weekly_seasonality": true,
  "n_changepoints": 30,
  "changepoint_range": 0.5,
  "seasonalities": {
    "monthly": {
      "name": "monthly",
      "period": 30.5,
      "fourier_order": 5,
      "__type": "Seasonality"
    }
  },
  "__type": "ProphetOptions"
}
```

Methods:

| Method | Argument types | Return type | Description |
| --- | --- | --- | --- |
| `get_prophet_options_growth` | `options: ProphetOptions`, `default: GrowthNameType \| None = None` | [`GrowthNameType`](#growthnametype) \| None | Returns the trend type |
| `get_prophet_options_changepoint_prior_scale` | `options: ProphetOptions`, `default: float \| None = None` | `float \| None` | Returns the trend flexibility |
| `get_prophet_options_seasonality_mode` | `options: ProphetOptions`, `default: SeasonalityModeType \| None = None` | [`SeasonalityModeType`](#seasonalitymodetype) \| None | Returns the seasonality mode |
| `get_prophet_options_seasonality_prior_scale` | `options: ProphetOptions`, `default: float \| None = None` | `float \| None` | Returns the regularization of the seasonal components |
| `get_prophet_options_yearly_seasonality` | `options: ProphetOptions`, `default: bool \| None = None` | `bool \| None` | Returns the yearly seasonality flag |
| `get_prophet_options_weekly_seasonality` | `options: ProphetOptions`, `default: bool \| None = None` | `bool \| None` | Returns the weekly seasonality flag |
| `get_prophet_options_n_changepoints` | `options: ProphetOptions`, `default: int \| None = None` | `int \| None` | Returns the number of changepoints |
| `get_prophet_options_changepoint_range` | `options: ProphetOptions`, `default: float \| None = None` | `float \| None` | Returns the share of history for changepoint search |
| `get_prophet_options_seasonalities` | `options: ProphetOptions`, `default: dict[SeasonalityNameType, Seasonality] \| None = None` | dict[[`SeasonalityNameType`](#seasonalitynametype), [`Seasonality`](#seasonality)] \| None | Returns the dictionary of custom seasonalities |
| `get_prophet_options_model_type` | `options: ProphetOptions`, `default: ModelType \| None = None` | [`ModelType`](#modeltype) \| None | Returns the model type |
| `is_valid_prophet_options` | `options: Any` | `bool` | Checks the validity of the options |
| `create_prophet_options` | `growth: GrowthNameType`, `changepoint_prior_scale: float`, `seasonality_mode: SeasonalityModeType`, `seasonality_prior_scale: float`, `yearly_seasonality: bool`, `weekly_seasonality: bool`, `n_changepoints: int`, `changepoint_range: float`, `seasonalities: dict[SeasonalityNameType, Seasonality] \| None`, `model_type: ModelType` | [`ProphetOptions`](#prophetoptions) | Creates a ProphetOptions object |
| `create_prophet_options_from_dict` | `data: dict` | [`ProphetOptions`](#prophetoptions) | Creates ProphetOptions from a dictionary |
| `serialize_prophet_options` | `options: ProphetOptions` | `str` | Serializes ProphetOptions to a JSON string |
| `deserialize_prophet_options` | `data: str` | [`ProphetOptions`](#prophetoptions) | Restores ProphetOptions from a JSON string |

```python
from rtb_sdk.helpers.predictor import (
    get_prophet_options_growth,
    get_prophet_options_changepoint_prior_scale,
    get_prophet_options_seasonality_mode,
    get_prophet_options_seasonality_prior_scale,
    get_prophet_options_yearly_seasonality,
    get_prophet_options_weekly_seasonality,
    get_prophet_options_n_changepoints,
    get_prophet_options_changepoint_range,
    get_prophet_options_seasonalities,
    get_prophet_options_model_type,
    is_valid_prophet_options,
    create_prophet_options,
    create_prophet_options_from_dict,
    serialize_prophet_options,
    deserialize_prophet_options,
)
```

##### GrowthNameType

The model trend type:

| Value | Description |
| --- | --- |
| `'linear'` | Linear trend |
| `'logistic'` | Logistic trend (growth with saturation) |

Prototype:
```python
type GrowthNameType = Literal['linear', 'logistic']
```

```python
class GrowthName:
    linear: GrowthNameType = 'linear'
    logistic: GrowthNameType = 'logistic'
```

Example:
```python
from rtb_sdk.schemas import GrowthNameType
from rtb_sdk.constants import GrowthName

growth: GrowthNameType = GrowthName.linear
```

##### SeasonalityModeType

Seasonality accounting mode:

| Value | Description |
| --- | --- |
| `'additive'` | Seasonality is added to the trend |
| `'multiplicative'` | Seasonality is multiplied by the trend |

Prototype:
```python
type SeasonalityModeType = Literal['multiplicative', 'additive']
```

```python
class SeasonalityMode:
    multiplicative: SeasonalityModeType = 'multiplicative'
    additive: SeasonalityModeType = 'additive'
```

Example:
```python
from rtb_sdk.schemas import SeasonalityModeType
from rtb_sdk.constants import SeasonalityMode

seasonality_mode: SeasonalityModeType = SeasonalityMode.additive
```

##### SeasonalityNameType

Identifier of a seasonal component:

| Value | Description |
| --- | --- |
| `'monthly'` | Monthly |
| `'weekly'` | Weekly |
| `'daily'` | Daily |

Prototype:
```python
type SeasonalityNameType = Literal['monthly', 'weekly', 'daily']
```

```python
class SeasonalityName:
    monthly: SeasonalityNameType = 'monthly'
    weekly: SeasonalityNameType = 'weekly'
    daily: SeasonalityNameType = 'daily'
```

Example:
```python
from rtb_sdk.schemas import SeasonalityNameType
from rtb_sdk.constants import SeasonalityName

seasonality_name: SeasonalityNameType = SeasonalityName.monthly
```

##### Seasonality

Parameters of a seasonal component

```python
class Seasonality(DiscriminatedTypedDict):
    name: SeasonalityNameType
    period: float
    fourier_order: int
```

| Parameter | Description | Possible values | Default |
| --- | --- | --- | --- |
| `name` | Component identifier; used as the key in the `seasonalities` dictionary | [`SeasonalityNameType`](#seasonalitynametype) | — |
| `period` | Period in days | `float`, > 0 (7.0 — weekly, 30.5 — monthly, 365.25 — yearly) | — |
| `fourier_order` | Fourier series order; larger values — a more complex pattern, smaller — a smoother curve | `int`, > 0 | — |

Example:
```python
from rtb_sdk.schemas import Seasonality

seasonality: Seasonality = {
    "name": "monthly",
    "period": 30.5,
    "fourier_order": 5
}
```

Methods:

| Method | Argument types | Return type | Description |
| --- | --- | --- | --- |
| `get_seasonality_name` | `seasonality: Seasonality`, `default: SeasonalityNameType \| None = None` | [`SeasonalityNameType`](#seasonalitynametype) \| None | Returns the component identifier |
| `get_seasonality_period` | `seasonality: Seasonality`, `default: float \| None = None` | `float \| None` | Returns the period in days |
| `get_seasonality_fourier_order` | `seasonality: Seasonality`, `default: int \| None = None` | `int \| None` | Returns the Fourier series order |
| `is_valid_seasonality` | `seasonality: Any` | `bool` | Checks the validity of the object |
| `create_seasonality` | `name: SeasonalityNameType`, `period: float`, `fourier_order: int` | [`Seasonality`](#seasonality) | Creates a Seasonality object |
| `create_seasonality_from_dict` | `data: dict` | [`Seasonality`](#seasonality) | Creates Seasonality from a dictionary |
| `serialize_seasonality` | `seasonality: Seasonality` | `str` | Serializes Seasonality to a JSON string |
| `deserialize_seasonality` | `data: str` | [`Seasonality`](#seasonality) | Restores Seasonality from a JSON string |

```python
from rtb_sdk.helpers.predictor import (
    get_seasonality_name,
    get_seasonality_period,
    get_seasonality_fourier_order,
    is_valid_seasonality,
    create_seasonality,
    create_seasonality_from_dict,
    serialize_seasonality,
    deserialize_seasonality,
)
```

#### ProphetModel

A trained Prophet model. Inherits from [`CommonModel`](#commonmodel).

```python
class ProphetModel(CommonModel):
    model: Any
```

| Parameter | Description | Possible values | Default |
| --- | --- | --- | --- |
| `type` | Always `'prophet'` (inherited) | [`ModelType`](#modeltype) | `'prophet'` |
| `resolution` | Step of the training series data; taken from `FitParams.resolution` (inherited) | [`Granularity`](#granularity) | — |
| `description` | Optional description (inherited) | `str \| None` | `None` |
| `model` | Trained model state | `Any` | — |

On serialization, the `model` field is packed into a nested JSON string.
`deserialize_prophet_model` transparently restores the trained model state.

Methods:

| Method | Argument types | Return type | Description |
| --- | --- | --- | --- |
| `get_prophet_model_type` | `model: ProphetModel`, `default: ModelType \| None = None` | [`ModelType`](#modeltype) \| None | Returns the model type |
| `get_prophet_model_resolution` | `model: ProphetModel`, `default: Granularity \| None = None` | [`Granularity`](#granularity) \| None | Returns the data step |
| `get_prophet_model_description` | `model: ProphetModel`, `default: str \| None = None` | `str \| None` | Returns the model description |
| `get_prophet_model_model` | `model: ProphetModel`, `default: Any \| None = None` | `Any \| None` | Returns the trained model state |
| `is_valid_prophet_model` | `model: Any` | `bool` | Checks the validity of the object |
| `create_prophet_model` | `model: Any`, `resolution: Granularity`, `description: Optional[str] = None` | [`ProphetModel`](#prophetmodel) | Creates a ProphetModel object |
| `create_prophet_model_from_dict` | `data: dict` | [`ProphetModel`](#prophetmodel) | Creates ProphetModel from a dictionary |
| `serialize_prophet_model` | `model: ProphetModel` | `str` | Serializes ProphetModel to a JSON string |
| `deserialize_prophet_model` | `data: str` | [`ProphetModel`](#prophetmodel) | Restores ProphetModel from a JSON string |

```python
from rtb_sdk.helpers.predictor import (
    get_prophet_model_type,
    get_prophet_model_resolution,
    get_prophet_model_description,
    get_prophet_model_model,
    is_valid_prophet_model,
    create_prophet_model,
    create_prophet_model_from_dict,
    serialize_prophet_model,
    deserialize_prophet_model,
)
```

#### ProphetModelPredictParams

Forecast parameters for the Prophet model. Extends [`PredictParams`](#predictparams).

```python
class ProphetModelPredictParams(PredictParams):
    forecast_periods: int
    resolution: Granularity
```

| Parameter | Description | Possible values | Default |
| --- | --- | --- | --- |
| `forecast_periods` | Number of forecast points ahead of the last training date | `int`, ≥ 1 | — |
| `resolution` | Step of the forecast series; must match the step of the training data | [`Granularity`](#granularity) | — |

Used in: the `data` parameter of the `predict` function when working with ProphetModel.

Methods:

| Method | Argument types | Return type | Description |
| --- | --- | --- | --- |
| `get_prophet_model_predict_params_forecast_periods` | `data: ProphetModelPredictParams`, `default: int \| None = None` | `int \| None` | Returns the number of forecast points |
| `get_prophet_model_predict_params_resolution` | `data: ProphetModelPredictParams`, `default: Granularity \| None = None` | [`Granularity`](#granularity) \| None | Returns the data step |
| `is_valid_prophet_model_predict_params` | `data: Any` | `bool` | Checks the validity of the object |
| `create_prophet_model_predict_params` | `resolution: Granularity`, `forecast_periods: int` | [`ProphetModelPredictParams`](#prophetmodelpredictparams) | Creates a ProphetModelPredictParams object |
| `create_prophet_model_predict_params_from_dict` | `data: dict` | [`ProphetModelPredictParams`](#prophetmodelpredictparams) | Creates ProphetModelPredictParams from a dictionary |
| `serialize_prophet_model_predict_params` | `data: ProphetModelPredictParams` | `str` | Serializes ProphetModelPredictParams to a JSON string |
| `deserialize_prophet_model_predict_params` | `data: str` | [`ProphetModelPredictParams`](#prophetmodelpredictparams) | Restores ProphetModelPredictParams from a JSON string |

```python
from rtb_sdk.helpers.predictor import (
    get_prophet_model_predict_params_forecast_periods,
    get_prophet_model_predict_params_resolution,
    is_valid_prophet_model_predict_params,
    create_prophet_model_predict_params,
    create_prophet_model_predict_params_from_dict,
    serialize_prophet_model_predict_params,
    deserialize_prophet_model_predict_params,
)
```

#### ProphetModelTestParams

Test parameters for the Prophet model. Extends [`TestParams`](#testparams).

```python
class ProphetModelTestParams(TestParams):
    pass
```

All fields are inherited from [`TestParams`](#testparams). The `resolution` step must match `model.resolution`.

Methods:

| Method | Argument types | Return type | Description |
| --- | --- | --- | --- |
| `get_prophet_model_test_params_training_dates` | `data: ProphetModelTestParams`, `default: list[datetime] \| None = None` | `list[datetime] \| None` | Returns the training sample dates |
| `get_prophet_model_test_params_training_values` | `data: ProphetModelTestParams`, `default: list[float] \| None = None` | `list[float] \| None` | Returns the training sample values |
| `get_prophet_model_test_params_expected_dates` | `data: ProphetModelTestParams`, `default: list[datetime] \| None = None` | `list[datetime] \| None` | Returns the test period dates |
| `get_prophet_model_test_params_expected_values` | `data: ProphetModelTestParams`, `default: list[float] \| None = None` | `list[float] \| None` | Returns the actual values of the test period |
| `get_prophet_model_test_params_resolution` | `data: ProphetModelTestParams`, `default: Granularity \| None = None` | [`Granularity`](#granularity) \| None | Returns the data step |
| `is_valid_prophet_model_test_params` | `data: Any` | `bool` | Checks the validity of the object |
| `create_prophet_model_test_params` | `training_dates: list[datetime]`, `training_values: list[float]`, `expected_dates: list[datetime]`, `expected_values: list[float]`, `resolution: Granularity` | [`ProphetModelTestParams`](#prophetmodeltestparams) | Creates a ProphetModelTestParams object |
| `create_prophet_model_test_params_from_dict` | `data: dict` | [`ProphetModelTestParams`](#prophetmodeltestparams) | Creates ProphetModelTestParams from a dictionary |
| `serialize_prophet_model_test_params` | `data: ProphetModelTestParams` | `str` | Serializes ProphetModelTestParams to a JSON string |
| `deserialize_prophet_model_test_params` | `data: str` | [`ProphetModelTestParams`](#prophetmodeltestparams) | Restores ProphetModelTestParams from a JSON string |

```python
from rtb_sdk.helpers.predictor import (
    get_prophet_model_test_params_training_dates,
    get_prophet_model_test_params_training_values,
    get_prophet_model_test_params_expected_dates,
    get_prophet_model_test_params_expected_values,
    get_prophet_model_test_params_resolution,
    is_valid_prophet_model_test_params,
    create_prophet_model_test_params,
    create_prophet_model_test_params_from_dict,
    serialize_prophet_model_test_params,
    deserialize_prophet_model_test_params,
)
```

---

## Functions

### Core

Located in `predictor/predictor.py`.

#### fit

Training the model on historical data

```python
from rtb_sdk.predictor import fit
from rtb_sdk.schemas import FitParams, ModelOptions, CommonModel

def fit(data: FitParams,
        options: ModelOptions) -> CommonModel
```

| Parameter | Type | Description |
| --- | --- | --- |
| `data` | [`FitParams`](#fitparams) | Time-series parameters; the `resolution` field is fixed in the returned model |
| `options` | [`ModelOptions`](#modeloptions) / [`ProphetOptions`](#prophetoptions) | Model settings |

Returns: [`CommonModel`](#commonmodel) — the trained model with `type` and `resolution` filled in

#### predict

Building a forecast for a given period

```python
from rtb_sdk.predictor import predict
from rtb_sdk.schemas import CommonModel, ModelOptions, PredictParams, PredictResult

def predict(model: CommonModel,
            options: ModelOptions,
            data: PredictParams) -> PredictResult
```

| Parameter | Type | Description |
| --- | --- | --- |
| `model` | [`CommonModel`](#commonmodel) | The trained model |
| `options` | [`ModelOptions`](#modeloptions) / [`ProphetOptions`](#prophetoptions) | Model settings |
| `data` | [`PredictParams`](#predictparams) / [`ProphetModelPredictParams`](#prophetmodelpredictparams) | Forecast parameters |

Returns: [`PredictResult`](#predictresult)

#### test

Evaluating model accuracy by comparing the forecast with real data

```python
from rtb_sdk.predictor import test
from rtb_sdk.schemas import CommonModel, ModelOptions, TestParams, TestResult

def test(model: CommonModel,
         options: ModelOptions,
         data: TestParams) -> TestResult
```

| Parameter | Type | Description |
| --- | --- | --- |
| `model` | [`CommonModel`](#commonmodel) | The trained model |
| `options` | [`ModelOptions`](#modeloptions) / [`ProphetOptions`](#prophetoptions) | Model settings |
| `data` | [`TestParams`](#testparams) / [`ProphetModelTestParams`](#prophetmodeltestparams) | Training data + reference values for comparison |

Returns: [`TestResult`](#testresult)

### Common (de)serialize

Implemented in `helpers/predictor/helpers.py` and re-exported from `predictor`. Intended for the schemas participating in
`fit / predict / test`: they work at the level of the abstract type and
choose the concrete implementation themselves by the discriminator.

```python
from rtb_sdk.predictor import (
    serialize_options, deserialize_options,
    serialize_model, deserialize_model,
    serialize_predict_params, deserialize_predict_params,
    serialize_test_params, deserialize_test_params,
    serialize_fit_params, deserialize_fit_params,
    serialize_predict_result, deserialize_predict_result,
    serialize_test_result, deserialize_test_result,
)
```

| Method | Argument types | Return type | Description |
| --- | --- | --- | --- |
| `serialize_options` | `options: ModelOptions` | `str` | Serializes the model options; for Prophet it dispatches to `serialize_prophet_options` by `model_type` |
| `deserialize_options` | `data: str` | [`ModelOptions`](#modeloptions) | Restores the model options; for Prophet it dispatches to `deserialize_prophet_options` by `model_type` |
| `serialize_model` | `model: CommonModel` | `str` | Serializes the trained model; for Prophet it dispatches to `serialize_prophet_model` by `type` |
| `deserialize_model` | `data: str` | [`CommonModel`](#commonmodel) | Restores the trained model; for Prophet it dispatches to `deserialize_prophet_model` by `type` |
| `serialize_predict_params` | `data: PredictParams`, `options: ModelOptions` | `str` | Serializes the forecast parameters; for Prophet it dispatches to `serialize_prophet_model_predict_params` by `options.model_type` |
| `deserialize_predict_params` | `data: str`, `options: ModelOptions` | [`PredictParams`](#predictparams) | Restores the forecast parameters; for Prophet it dispatches to `deserialize_prophet_model_predict_params` by `options.model_type` |
| `serialize_test_params` | `data: TestParams`, `options: ModelOptions` | `str` | Serializes the test parameters; for Prophet it dispatches to `serialize_prophet_model_test_params` by `options.model_type` |
| `deserialize_test_params` | `data: str`, `options: ModelOptions` | [`TestParams`](#testparams) | Restores the test parameters; for Prophet it dispatches to `deserialize_prophet_model_test_params` by `options.model_type` |
| `serialize_fit_params` | `data: FitParams` | `str` | Serializes the training parameters |
| `deserialize_fit_params` | `data: str` | [`FitParams`](#fitparams) | Restores the training parameters |
| `serialize_predict_result` | `result: PredictResult` | `str` | Serializes the forecast result |
| `deserialize_predict_result` | `data: str` | [`PredictResult`](#predictresult) | Restores the forecast result |
| `serialize_test_result` | `result: TestResult` | `str` | Serializes the test result |
| `deserialize_test_result` | `data: str` | [`TestResult`](#testresult) | Restores the test result |

The `deserialize_model` algorithm:
1. parse the JSON into a dictionary;
2. get `type` (common parsing via `deserialize_common_model`);
3. call `deserialize_<model>_model` according to the dispatcher table.

`deserialize_options` determines the model by `model_type` inside the JSON. For `deserialize_predict_params`
and `deserialize_test_params`, the model is passed explicitly via `options`, because the forecast/test
parameters themselves are not required to store the model type.

### Metrics

#### calc_metrics

Computes forecast quality metrics from the test results

```python
from rtb_sdk.helpers.predictor import calc_metrics
from rtb_sdk.schemas import TestResult, TestMetrics

def calc_metrics(result: TestResult) -> TestMetrics
```

| Parameter | Type | Description |
| --- | --- | --- |
| `result` | [`TestResult`](#testresult) | Test result; `predict_values` and `expected_values` are used |

Returns: [`TestMetrics`](#testmetrics)

Computed metrics:

| Field             | Formula                                                                                    |
|-------------------|--------------------------------------------------------------------------------------------|
| `accuracy`        | `max(0, 1 − mean(\|actual − predicted\| / \|actual\|))` over points where `actual ≠ 0`; if there are no such points, MAPE = 0 |
| `precision`       | Share of steps `i` where `(actual[i] − actual[i−1]) * (predicted[i] − predicted[i−1]) > 0`  |
| `mse`             | `mean((actual − predicted)²)`                                                              |
| `autocorrelation` | Lag-1 autocorrelation of the residuals `e[i] = predicted[i] − actual[i]`                   |
| `mae`             | `mean(\|actual − predicted\|)`                                                             |
| `lb_stat`         | Q = n(n+2) · Σ(rₖ / (n−k)), k=1, where rₖ is the residual autocorrelation at lag k         |
| `lb_sq_stat`      | Q = n(n+2) · Σ(rₖ² / (n−k)), k=1, where rₖ is the squared-residual autocorrelation at lag k |

### Working with reports

Located in `predictor/io/report.py`. The module is responsible only for generating
reports. To validate the result, use `is_valid_test_result` from the `TestResult` method group.
Saving/loading of the other schemas is done
via `serialize_*` / `deserialize_*`.

#### save_report

Computes the metrics (calls [`calc_metrics`](#calc_metrics) internally) and saves
the report in one of the formats: Markdown, JSON, or PNG. The report shows all
[`TestMetrics`](#testmetrics) metrics; the PNG additionally includes a chart of actual and
forecast values. Returns the same metrics so that the caller does not have to
call `calc_metrics` separately.

```python
from rtb_sdk.predictor import save_report
from rtb_sdk.schemas import TestResult, ReportType, TestMetrics

def save_report(
        result: TestResult,
        report_type: ReportType,
        output_report_path: str,
) -> TestMetrics
```

| Parameter | Type | Description |
| --- | --- | --- |
| `result` | [`TestResult`](#testresult) | Test result |
| `report_type` | [`ReportType`](#reporttype) | Report format: `'md'`, `'json'`, or `'png'` |
| `output_report_path` | `str` | Path to the output report file (including name and extension) |

Returns: [`TestMetrics`](#testmetrics) — the computed metrics (they also go into the report).
