# Analyzing and improving the predictor

## Table of contents

1. [Ongoing implementation](#1-current-implementation)
2. [Challenges of Current Implementation](#2-problem-current-implementation)
3. [Alternative options](#3-alternative-variants)
   - [NeuralProphet](#31-neuralprophet--evolutionary-upgrade-prophet)
   - [StatsForecast](#32-statsforecast--statistical-model-scale)
   - [NeuralForecast](#33-neuralforecast--deep-teaching-for-forecasting)
   - [LightGBM/XGBoost](#34-lightgbmxgboost-for-forecasting)
   - [Temporal Fusion Transformer](#35-temporal-fusion-transformer-tft)
   - [Darts](#36-darts-unit8--netflix-inspired)
   - [pmdarima](#37-pmdarima)
   - [PyCaret](#38-pycaret-time-series)
4. [Comparative Table](#4-comparative-table-extended)
   - [Overview table](#41-general-comparative-table)
   - [RTB-context](#42-table-for-rtb-context)
   - [Repositories](#43-repositories-and-version)
5. [Recommendations](#5-recommendations)
   - [Migration strategy](#51-strategy-migration)
   - [Priorities](#52-priorities)
   - [What to avoid](#53-what?-avoid)
   - [What to add to the scheme](#54-what-add-in-scheme)
   - [Risks and cons Darts](#55-risk-and-minuses-darts)
6. [Conclusion](#6-conclusion)

---

## 1 : Current implementation

### Architecture

The predictor is a wrapper over **Facebook Prophet** with the following structure:

```
┌─────────────────────────────────────────────────────────────┐
│                     PUBLIC API                              │
│  fit() → predict() → test() → save_report()                 │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              predictor.py (Dispatcher)                      │
│  model_method_hash = {                                      │
│    'prophet': { fit, predict, test, options_builder, ... }  │
│  }                                                          │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│         prophet_model/prophet_model.py                      │
│  prophet_model_fit()  → Prophet().fit()                     │
│  prophet_model_predict() → model.predict()                  │
│  prophet_model_test()  → forecast + validation              │
└─────────────────────────────────────────────────────────────┘
```

### Input data

**CSV format:**
```
date_from,date_to,value
2024-01-01 00:00:00,2024-01-02 00:00:00,100.0
2024-01-02 00:00:00,2024-01-03 00:00:00,108.07
...
```

**FitParams:**
```python
{
    'dates': list[datetime],       # Beginning of the period
    'values': list[float],         # Time series values
    'resolution': Granularity      # 't'|'h'|'d'|'w'|'m'
}
```

### ProphetOptions (current configuration)

```python
{
    'growth': 'linear',                      # 'linear' | 'logistic'
    'changepoint_prior_scale': 0.05,         # Trend flexibility
    'seasonality_mode': 'additive',          # 'additive' | 'multiplicative'
    'seasonality_prior_scale': 10.0,         # Regularization of seasonality
    'yearly_seasonality': False,
    'weekly_seasonality': True,
    'n_changepoints': 10,                    # Number of Trend Breakpoints
    'changepoint_range': 0.8,                # Share of history to find points
    'seasonalities': {
        'monthly': {'period': 30.5, 'fourier_order': 5}
    }
}
```

### Quality metrics

The current implementation calculates:
- **accuracy** = max(0, 1 − MAPE)
- **Precision** – Share of agreed directions of change
- **mse** is the average square error
- **mae** — average absolute error
- **Autocorrelation ** - lag-1 autocorrelation of residues
- **lb_stat / lb_sq_stat** - Q-statistics Ljung-Box

---

## 2 : Current Implementation Issues

### 1 Limited Model Set

**Problem:** Model type — `Literal["prophet"]`. You can’t switch to alternative models without writing new code.

```python
# Ongoing implementation — only Prophet
type ModelType = Literal["prophet",]
```

**Impact:** You cannot choose a model for a specific task. For volatile data Prophet may lose ARIMA, large-scale — decision-tree.

---

### 2 No support for Exogenous Regressors

**Problem:** `ProphetOptions` No field for external factors (campaigning, rivalry, weather, festival).

Prophet supports `add_regressor()` in its library, but this is not reflected in the current scheme.

```python
# What is not in the current implementation:
# m.add_regressor('price')
# m.add_regressor('promotion')
# m.add_country_holidays('Russia')
```

**Impact:** External factors cannot be taken into account, which may affect the time series (discount, marketing activities, Macroeconomic developments).

---

### 3: No Uncertainty Intervals

**Problem:** `PredictResult` Returns only point predictions:

```python
class PredictResult(DiscriminatedTypedDict):
    training_dates: list[datetime]
    training_values: list[float]
    predict_dates: list[datetime]
    predict_values: list[float]  # Only a point, spacingly
```

Prophet has a built-in uncertainty score (`uncertainty_samples=1000`), but the result is not returned.

**Impact:** There is no understanding of the reliability of the forecast. To take business-Confidence intervals are required.

---

### 4 No built-in cross-validation

**Problem:** No mechanism time-series cross-validation. Prophet has `model.cross_validation()`, but SDK does not grant him access.

**Influence: ** It's hard to measure the quality of a model from historical data. You can't automatically pick up a forecast horizon.

---

### 5 Problems with Monthly Data Processing

**Problem:** Monthly approval validation uses heuristics:

```python
# prophet_model.py, line 196-198
if resolution == 'm':
    delta_days = (next_date - prev_date).days
    return 28 <= delta_days <= 31  # Heuristics!
```

**Impact:** Months have different lengths (28-31 day). Heuristics can miss errors or give false positives.

---

### 6 : No support for Russian holidays

**Problem:** Prophet promotes the holidays through `add_country_holidays()`, but in the scheme `ProphetOptions` There’s no field to activate them.

**Impact:** This is critical for the Russian market — festival (New Year, May, 8 March) It strongly influences consumer behavior.

---

### 7 : Manual adjustment of Hyperparameters

**Problem: ** All parameters (`changepoint_prior_scale`, `seasonality_prior_scale`, `n_changepoints`) are manually set. There is no automatic matching.

**Impact: ** Non-optimal hyperparameters = lower quality of forecasts.

---

### 8: The gap in the Prophet API between Schema and Reality

**Problem: ** The `prophet_model.py` code doesn't use all of Prophet's features:

```python
# prophet_model.py, line 72-73
yearly_seasonality=cast(str, get_prophet_options_yearly_seasonality(options)),
weekly_seasonality=cast(str, get_prophet_options_weekly_seasonality(options)),
```

**But!** `add_country_holidays()` callless, `add_regressor()` unsupported.

---

### 9. No autoregression (Lag effects)

**Problem:** Prophet It does not take into account autocorrelation in a number of — Each prediction is made independently of previous predictions.

**Impact:** The model can’t "remember" recent. For data with strong autocorrelation - It’s a problem.

---

### 10 : The inconsistency of Defaults

**Problem:** In `create_prophet_options()`, the default values are different from the examples and from the original Prophet:

```python
# In code (prophet_options.py, line 326-335):
changepoint_prior_scale: float = 0.001,            # Prophet default = 0.05
seasonality_mode = SeasonalityMode.multiplicative  # An example of this additive

# In an example (prophet_options.json):
changepoint_prior_scale: 0.05,                # Doesn’t match the code!
seasonality_mode: 'additive'                  # Doesn’t match the code!
```

---

## 3 : Alternative options

### 3.1 NeuralProphet - The Prophet Evolutionary Upgrade

#### Description

**NeuralProphet** — it’s a fork Prophet, translated PyTorch. Maintains compatibility with API Prophet, It adds neural network components.

**Repository:** [github.com/ourownstory/neuralprophet](https://github.com/ourownstory/neuralprophet)

#### How to solve problems

| Problem | Decision |
|---|---|
| No autoregression | ✅ Built-in AR-Net (autoregression) |
| Weak accuracy | ✅ 55-92% improvement vs Prophet (centimetre. clause) |
| There are no Russian holidays | ✅ `add_country_holidays('Russia')` |
| No exogenous regressors | ✅ `add_lagged_regressor()` nonlinear |
| Slow work | ✅ Hurry up CPU, support GPU |

> ⚠️ **Reservation to the number 55-92%:** This is the result of the original article NeuralProphet (arXiv:2111.15397) It is especially true for short-term/middle rows and small datasets. As history grows, (independent benchmarks — from ~1270 point) Prophet leapfrog NeuralProphet precisely; On very large datasets, simple methods like ETS Show comparable or better quality orders of magnitude faster. The number should not be taken as an absolute superiority — We need a benchmark for real ones RTB-pre-decision.

#### Key features

```
┌────────────────────────────────────────────────────────────┐
│                 NeuralProphet vs Prophet                   │
├────────────────────────────────────────────────────────────┤
│  Prophet           │  NeuralProphet                        │
├────────────────────────────────────────────────────────────┤
│  Linear trend    │  Neural network trend (NR-Nets)         │
│  No AR            │  AR-Net autoregression                 │
│  Fourier seasonality│  Fourier + Neural seasonality          │
│  Additive regressor│  Neural regressors (nonlinear!)      │
│  CPU               │  GPU support                          │
└────────────────────────────────────────────────────────────┘
```

#### Example of the Code

```python
from neuralprophet import NeuralProphet
from neuralprophet.df_utils import NeuralProphetDataLoader

# Minimum replacement of the current prophet_model_fit
m = NeuralProphet(
    growth='linear',
    changepoint_prior_scale=0.05,
    seasonality_mode='additive',
    n_changepoints=10,
    epochs=100,                    # New: period
    learning_rate=0.01,             # New: speed
)

# Russian holidays — piece, lacking!
m.add_country_holidays('Russia')

# Weekly and annual seasonality
m.set_seasonality(name='weekly', period=7, fourier_order=5)
m.set_seasonality(name='yearly', period=365.25, fourier_order=10)

# External factors (nonlinear!)
m.add_lagged_regressor(['price', 'promotion'])

# Training
df = df.rename(columns={'date_from': 'ds', 'value': 'y'})
metrics = m.fit(df, freq='D')

# Forecast
future = m.make_future_dataframe(df, periods=30)
forecast = m.predict(future)
```

#### When to use

- NeuralProphet almost drop-in replacement
- ✅ I need it AR (lag-dependent) — Prophet That doesn’t work
- Russian holidays are critical
- Data with nonlinear dependencies on external factors

---

### 3.2 StatsForecast - Statistical Scale Models

#### Description

**StatsForecast** (from Nixtla) is a high-performance library of statistical forecasting models, including AutoARIMA, AutoETS, AutoCES, MSTL and others.

**Repository:** [github.com/Nixtla/statsforecast](https://github.com/Nixtla/statsforecast)

#### How to solve problems

| Problem | Decision |
|---|---|
| Scalability | ✅ 500x faster Prophet for ARIMA |
| Only one model | ✅ 10+ statistical models in one API |
| Manual selection of parameters | ✅ AutoARIMA, AutoETS — pick-up |
| No uncertainty | ✅ Built-in confidence intervals |

#### Benchmarky Productivity

| Operation | Prophet | StatsForecast (AutoARIMA) |
|---|---|---|
| Training 1 series | ~30 sec | ~0.06 sec |
| Training 10000 series | ~83 hourly | ~10 minute |

#### Models in the kit

```
StatsForecast Models:
├── AutoARIMA      — Automatic ARIMA s seasonal component
├── AutoETS        — Automatic exponential smoothing
├── AutoCES        — Complex Exponential Smoothing
├── AutoTheta      — Theta method (M3 champion)
├── AutoTBATS      — TBATS multi-seasonal
├── MSTL           — Multiple Seasonal-Trend decomposition
└── SeasonalExponentialSmoothing
```

#### Example of the Code

```python
from statsforecast import StatsForecast
from statsforecast.models import AutoARIMA, AutoETS, AutoTheta, MSTL

# Data preparation (format Nixtla)
df = df.rename(columns={'date_from': 'ds', 'value': 'y'})
df['unique_id'] = 'series_1'  # Nixtla demand ID

# Creation forecaster
sf = StatsForecast(
    models=[
        AutoARIMA(season_length=7),      # Weekly seasonality
        AutoETS(season_length=7),
        AutoTheta(season_length=7),
        MSTL(season_length=[7, 365]),   # Weekly + yearly
    ],
    freq='D',                            # Daily data
    n_jobs=-1,                           # Parallel implementation
)

# Training
sf.fit(df)

# Forecast 30 days
forecasts = sf.predict(h=30, level=[95])  # 95% confidence interval

# The result:
#    unique_id  ds  AutoARIMA  AutoARIMA-lo-95  AutoARIMA-hi-95  ...
```

#### When to use

- Scalability is required (100 K+ series)
- ✅ You want to automatically select the model (manually ARIMA/ETS)
- We need confidence intervals out of the box.
- Speed of learning is important

---

### 3.3 NeuralForecast – Deep Learning for Forecasting

#### Description

**NeuralForecast** (from Nixtla) is a deep learning library with 30+ architectures. NBEATS, NHITS, PatchTST, Temporal Fusion Transformer, LSTM and others.

**Repository:** [github.com/Nixtla/neuralforecast](https://github.com/Nixtla/neuralforecast)

#### How to solve problems

| Problem | Decision |
|---|---|
| Low accuracy on complex patterns | ✅ SOTA model (NBEATS, NHITS, PatchTST) |
| No multiple seasonality | ✅ MSTL, NBEATSx decomposition |
| No GPU acceleration | ✅ PyTorch + CUDA |

#### Architecture

```
NeuralForecast Models (30+):
├── N-BEATS Family
│   ├── NBEATS      — Neural Basis Expansion Analysis
│   ├── NBEATSx     — NBEATS s exogenous variable
│   └── NHITS       — Neural Hierarchical Interpolating Time Series
├── Transformers
│   ├── PatchTST     — Pretrained Transformer for Time Series ★
│   ├── TFT         — Temporal Fusion Transformer
│   ├── Informer    — Long-sequence forecasting
│   └── AutoFormer   — AutoML for Transformer
├── Recurrent
│   ├── LSTM        — Long Short-Term Memory
│   ├── GRU         — Gated Recurrent Unit
│   └── DeepAR      — Probabilistic forecasting
└── MLP-Based
    ├── DLinear      — Disentangled Linear
    ├── NLinear      — Linear normalized
    └── TiDE        — Tiny attention for large datasets
```

#### Example of the Code

```python
from neuralforecast import NeuralForecast
from neuralforecast.models import NBEATS, NHITS, PatchTST

# Data preparation
df = df.rename(columns={'date_from': 'ds', 'value': 'y'})
df['unique_id'] = 'series_1'

# Creation forecaster
nf = NeuralForecast(
    models=[
        # NBEATS — Good for decomposition trend/seasonality
        NBEATS(
            input_size=24,         # Use 24 entry-point
            h=30,                  # Forecast horizon
            max_steps=100,         # Maximum of epochs
        ),
        # NHITS — hierarchical
        NHITS(
            input_size=24,
            h=30,
            max_steps=100,
        ),
        # PatchTST — transformer (SOTA on many benchmarks)
        PatchTST(
            input_size=24,
            h=30,
            max_steps=100,
        ),
    ],
    freq='D',
)

# Training
nf.fit(df)

# Forecast
forecasts = nf.predict()

# Ensemble — Averaging the predictions of several models
nf.predict(h=30, model=['NBEATS', 'NHITS'])
```

#### Important Limitation

> ⚠️ **NeuralForecast Does not support gaps in data!**
>
> If there is a NaN in the row, they must be pre-filled (impute).

```python
# Before use NeuralForecast:
df['y'] = df['y'].interpolate(method='linear')  # Fill in the gaps
```

#### When to use

- Maximum accuracy is more important than speed
- There are GPUs for learning
- ✅ Data is clean (passless)
- Need a state-of-the-art result

---

### 3.4 LightGBM/XGBoost for Prediction

#### Description

Gradient boosting is a classic approach to tabular data. Time series requires feature engineering: lags, sliding statistics, calendar features.

**Key libraries:**
- `mlforecast` (Nixtla) - Automatic feature engineering
- `skforecast` – Sklearn-like API
- `lightgbm`/`xgboost` directly

#### How to solve problems

| Problem | Decision |
|---|---|
| No pass support | ✅ Trees are being processed NaN |
| Manually feature engineering | ✅ MLForecast maker auto |
| No external regressors | ✅ Any signs |
| Scalability | ✅ Millions of rows |

#### Feature Engineering for Time Series

Trees don't understand "time" - you need to create signs:

```python
def build_features(df, target='y'):
    result = df.copy()
    s = result[target]
    
    # lagi (delay)
    for lag in [1, 2, 3, 7, 14, 30]:
        result[f'lag_{lag}'] = s.shift(lag)
    
    # Moving statistics
    for w in [7, 14, 30]:
        rolled = s.shift(1).rolling(w)
        result[f'rolling_mean_{w}'] = rolled.mean()
        result[f'rolling_std_{w}'] = rolled.std()
    
    # Calendar signs
    result['dayofweek'] = result.index.dayofweek
    result['month'] = result.index.month
    result['is_weekend'] = (result.index.dayofweek >= 5).astype(int)
    
    # Cyclical coding
    result['doy_sin'] = np.sin(2 * np.pi * result.index.dayofyear / 365.25)
    result['doy_cos'] = np.cos(2 * np.pi * result.index.dayofyear / 365.25)
    
    return result.dropna()
```

#### Example from MLForecast (Nixtla)

```python
from mlforecast import Forecast
import lightgbm as lgb
import pandas as pd

# Data preparation
df = df.rename(columns={'date_from': 'ds', 'value': 'y'})
df['unique_id'] = 'series_1'

# Creation forecaster motor-car-fitch
fcst = Forecast(
    models=[lgb.LGBMRegressor(
        n_estimators=100,
        learning_rate=0.1,
        num_leaves=31,
    )],
    freq='D',
    
    # Automatic lags
    lags=[7, 14, 30],
    
    # Automatic moving statistics
    lag_transforms={
        1: ['expanding_mean'],           # Expanding mean past
        7: [('rolling_mean', 7)],         # 7-day-moving average
    },
    
    # Automatic calendar signs
    date_features=['dayofweek', 'month', 'quarter', 'year'],
    
    # Difference (stationary)
    differences=[1],  # First difference: y(t) - y(t-1)
)

# Training
fcst.fit(df)

# Forecast
forecasts = fcst.predict(14)  # 14 daylight
```

#### When to use

- There are many external factors (prices, advertising, weather)
- There are gaps in the data
- You want to be interpretable (feature importance)
- We need scalability.

---

### 3.5 Temporal Fusion Transformer (TFT)

#### Description

**TFT** is a state-of-the-art architecture for multi-horizon forecasting with interpretability. Built-in attention mechanisms show which time steps the model is paying attention to.

**Implementation:** `pytorch-forecasting` or `neuralforecast`

#### How to solve problems

| Problem | Decision |
|---|---|
| No interpretability | ✅ Attention weights |
| Complex patterns | ✅ Multi-horizon attention |
| Different types of entrances | ✅ Static, known future, observed past |

#### TFT architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  Temporal Fusion Transformer                    │
├─────────────────────────────────────────────────────────────────┤
│  Inputs:                                                        │
│  ├── Static categorical (group_id, category) ──► Static Encoder │
│  ├── Known future (holiday, price)           ──► Future Encoder │
│  └── Observed past (target lags)              ──► Past Encoder  │
├─────────────────────────────────────────────────────────────────┤
│  Processing:                                                    │
│  ├── Variable Selection Network (VSN) — What features are important        │
│  ├── Gated Residual Network (GRN) — adaptive nonlinearity     │
│  ├── LSTM — temporal processing                                 │
│  └── Multi-Head Attention — long-range dependencies             │
├─────────────────────────────────────────────────────────────────┤
│  Output:                                                        │
│  ├── Point forecast (quantiles: 10%, 50%, 90%)                  │
│  └── Attention weights (interpretability)                       │
└─────────────────────────────────────────────────────────────────┘
```

#### Example of the Code

```python
from pytorch_forecasting import TemporalFusionTransformer, TimeSeriesDataSet
from pytorch_forecasting.data import GroupNormalizer
import pandas as pd

# Data preparation
df['time_idx'] = df.groupby('unique_id').cumcount()

# Creation dataset
training = TimeSeriesDataSet(
    df,
    time_idx='time_idx',
    target='y',
    group_ids=['unique_id'],
    
    # Encoder/decoder length
    max_encoder_length=30,   # How many past points to use
    max_prediction_length=7,  # Forecast horizon
    
    # Static categories
    static_categoricals=['category'],
    
    # Known future values
    time_varying_known_categoricals=['is_holiday'],
    time_varying_known_reals=['price', 'promotion'],
    
    # Observed past
    time_varying_unknown_reals=['y'],
    
    # Normalization
    target_normalizer=GroupNormalizer(groups=['unique_id']),
)

# Model
tft = TemporalFusionTransformer.from_dataset(
    training,
    hidden_size=32,
    attention_head_size=4,
    dropout=0.1,
    hidden_continuous_size=16,
    learning_rate=0.01,
    loss_quantiles=[0.1, 0.5, 0.9],  # Quantile regression
)

# Training
trainer.fit(tft, train_dataloader=train_dataloader)

# Forecast with interpretability
raw_predictions = tft.predict(new_data, mode='raw', return_x=True)
# attention = raw_predictions.attentions  # Attention of the model
```

#### When to use

- Maximum interpretability is critical
- Multidimensional data with different types of inputs
- ✅ Long-horizon forecasting
- Need attention analysis

---

### 3.6 Darts (Unit8 / Netflix-inspired)

| Parameter | Characterization |
|----------|----------------|
| **Version** | 0.45.0 (June 2026) |
| **GitHub** | 9.5k ★, unit8co/darts |
| **PyPI** | `darts` |
| **License** | Apache-2.0 |
| **Python** | ≥ 3.10 |
| **Support** | ✅ **Active!** 61 release, frequent. Unit8 — company, supporter. |

#### Strong Parties

- **The widest model arsenal: ** ARIMA, Prophet, Exponential Smoothing, Theta, RandomForest, LightGBM, LinearRegression, **N-BEATS, TFT, TCN, RNN, LSTM, GRU, Transformer**
- **A single sklearn-like API** - `fit()`, `predict()` - easy to switch models
- **Probabilistic forecasting** from the box
- **Backtesting** built-in
- **Past and Future covariates** — exogenous (festival, budget)
- **Multivariate and univariate**
- **Anomalies** — anomaly detection built in
- Monzo (Bank) is used in production

#### Weak Sides

- **Heavy dependency tree** – PyTorch as an optional, but actually necessary, dependency for DL models greatly increases image size and build time compared to the current installation (`prophet` + `pystan` /`cmdstanpy` only).
- **Heterogeneous API between models** – not all models support `probabilistic`, `past_covariates` or `future_covariates` equally; model switching is not always painless despite the overall `fit()/predict()`
- **Holidays are not “out of the box”** – unlike NeuralProphet (`add_country_holidays()`), Darts holidays need to be manually collected in `TimeSeries`-covariate and transmitted as `future_covariates`
- **Young Release Cycle** – 0.45.0 shows ongoing breaking changes between minor releases; production requires strict pin versions and update regression tests
- Full risk analysis — section [5.5 Risks and cons Darts](#55-risk-and-minuses-darts)

#### Code.

```python
from darts import TimeSeries
from darts.models import (
    ExponentialSmoothing,
    ARIMA,
    Prophet,
    LightGBMModel,
    NBEATS,
)

# Data preparation
series = TimeSeries.from_dataframe(
    df, time_col='date_from', value_cols='value'
)

# Model
model = ExponentialSmoothing(seasonal_periods=7)
model.fit(series)

# Forecast 30 days
forecast = model.predict(n=30)

# Ensemble — prediction-averaging
ensemble = [ExponentialSmoothing(), ARIMA(), Prophet(), NBEATS()]
predictions = [m.predict(n=30) for m in ensemble]
final = sum(predictions) / len(predictions)
```

#### Verdict

⭐ **Best candidate to replace Prophet amongst**, but not: A rich model arsenal and active support are accompanied by an increase in the weight of dependencies and operational complexity. Before taking a decision, see. [5.5 Risks and cons Darts](#55-risk-and-minuses-darts) — Migration should start with a pilot in statistical models (`ExponentialSmoothing`, `Theta`), demand-free PyTorch, before investing DL-armoury.

---

### 3.7 pmdarima

| Parameter | Characterization |
|----------|----------------|
| **Version** | 2.1.1 (November 2025) |
| **GitHub** | alkaline-ml/pmdarima |
| **PyPI** | `pmdarima` |
| **License** | MIT |
| **Python** | ≥ 3.10, C extensions |
| **Support** | ✅ **Maintained.** |

#### Strong Parties

- `auto_arima` - R-equivalent to automatic selection of ARIMA
- sklearn-compatible API
- Fast Cython implementation
- Exogenous regressors (ARIMAX)
- CV utilities, pipelines

#### Code.

```python
from pmdarima import auto_arima
from pmdarima.pipeline import Pipeline
from pmdarima.preprocessing import ARIMAXFeaturizer

# Auto-ARIMA
model = auto_arima(
    y,  # target range
    X=X_exog,  # exogenous (festival!)
    seasonal=True,
    m=7,  # weekly
    trace=True,  # search log
    error_action='ignore',
    suppress_warnings=True,
    stepwise=True
)

forecast = model.predict(n_periods=30, X=X_future_exog)
```

#### Verdict

If the data has a clear ARIMA pattern, it's the best solution, but Prophet often does better on business data.

---

### 3.8 PyCaret (Time Series)

| Parameter | Characterization |
|----------|----------------|
| **Version** | 3.3 (relevant) |
| **GitHub** | 8.6k+ ★, pycaret/pycaret |
| **PyPI** | `pycaret` |
| **License** | MIT |
| **Python** | ≥ 3.9 |
| **Support** | ✅ **Active.** |

#### Strong Parties

- Low-code AutoML – `compare_models()` for 3 lines
- Time series module setup → compare_models → tune_model → blend_models
- **Ensemble** models built-in
- Visualization's built in.
- MLflow integration

#### Code.

```python
from pycaret.time_series import *

# Setup
setup(data, target='value', fh=30, session_id=42)

# Compare all models
best = compare_models()

# Tuning
tuned = tune_model(best)

# Ensemble
ensemble = blend_models(estimator_list=top5)

# Finalize predict
finalize_model(ensemble)
predictions = predict_model(ensemble, data=test_df)
```

#### Verdict

️ Good for prototyping and baseline. For production, use libraries directly.

---

## 4 . Comparative Table (Extended)

### 4.1 General Comparative Table

| Criteria | Prophet | NeuralProphet | StatsForecast | NeuralForecast | LightGBM | TFT | **Darts** | **pmdarima** | **PyCaret** |
|---|---|---|---|---|---|---|---|---|---|
| **precision** | Basic | Tall | Good | **SOTA** | Tall | Tall | Tall | Good | Good |
| **Speed** | ~30 sec | ~10 sec | **0.06 sec** | Slow | Fast | Slow | Fast | Fast | Fast |
| **Scalability** | Low | Medium | **Very high** | Tall | Tall | Medium | Tall | Low | Medium |
| **Model arsenal** | 1 | 1+ | 10+ | 30+ | 1 | 1 | **30+** | 1 | 10+ |
| **Ease of migration** | — | **Easy** | Middle-Average | Hardly | Middle-Average | Hardly | **Easy** | Easy | Easy |
| **sklearn API** | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ |
| **Russian holidays** | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **External factors** | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Data omissions** | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ✅ | ❌ | ✅ |
| **Uncertainty** | ✅ | ✅ | ✅ | ✅ | ⚠️ | ✅ | ✅ | ⚠️ | ✅ |
| **GPU support** | ❌ | ✅ | ❌ | ✅ | ❌ | ✅ | ⚠️ | ❌ | ⚠️ |
| **Auto-selection** | ❌ | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ |
| **Active support** | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Production-ready** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

### 4.2 Table for RTB context

| Function | Prophet | Darts | StatsForecast | NeuralForecast | pmdarima | PyCaret |
|---------|:---:|:---:|:---:|:---:|:---:|:---:|
| **Multiple seasonality** | ✅ Fourier | ✅ model-dependably | ✅ (MSTL) | ✅ | ⚠️ SARIMA | ✅ |
| **Exogenous (future known)** | ✅ add_regressor | ✅ futr_exog_list | ✅ | ✅ | ✅ | ✅ |
| **Exogenous (past observed)** | ❌ | ✅ hist_exog_list | ❌ | ✅ | ❌ | ✅ |
| **Data gaps** | ✅ cartridge | ✅ | ❌ | ❌ | ❌ | ✅ |
| **Backtesting** | ⚠️ | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ |
| **Interpretability** | ✅ decomposition | ✅ model-dependably | ⚠️ | ⚠️ | ⚠️ | ⚠️ |

### 4.3 Repositories and Versions

| Library | GitHub ★ | Version | The latest release | License |
|------------|----------|--------|----------------|---------|
| **Darts** | 9.5k | 0.45.0 | June 2026 | Apache-2.0 |
| **NeuralForecast** | 3.5k | 1.5.x | Active | MIT |
| **StatsForecast** | 4.8k | 2.0.3 | Oct 2025 | Apache-2.0 |
| **NeuralProphet** | 5.5k | 0.7.x | Active | MIT |
| **Prophet** | 18.5k | 1.3.0 | jan 2026 | MIT |
| **pmdarima** | 2k+ | 2.1.1 | Noah 2025 | MIT |
| **PyCaret** | 8.6k | 3.3 | Active | MIT |

---

## 5 Recommendations

### 5.1 Migration Strategy

#### 0 Phase: Preserving Compatibility
- Leave Prophet for backward compatibility
- Add a new `ModelType` without removing an existing one

#### 1 Phase: Darts as the Main Alternative
**Why Darts:**
- 30 + models in one API (from ARIMA to NBEATS/TFT)
- sklearn-like `fit()/predict()` - migration is minimal
- Probabilistic forecasting from the box
- Past/future Covariates – Holidays and Budget
- Backtesting is built-in
- Active support (Unit8 - company, not community)
- Monzo is using production technology.

**Minimum changes:**
```python
# Add in model_method_hash
model_method_hash = {
    'prophet': {...},
    'darts': {
        'fit': darts_model_fit,
        'predict': darts_model_predict,
        'test': darts_model_test,
        ...
    }
}
```

#### 2 Phase: Expansion to Ensemble
```python
# Ensemble of Darts model
ensemble_models = [
    darts.models.ExponentialSmoothing(seasonal_periods=7),
    darts.models.ARIMA(),
    darts.models.Prophet(),
    darts.models.NBEATS(input_size=48, h=24),
]

# Backtesting selecting the best model
backtests = [model.backtest(series) for model in ensemble_models]
scores = [mape(bt, actual) for bt in backtests]
```

#### 3: Production Scale (StatsForecast + MLForecast)
```python
# For 100K+ rows — Nixtla ecosystem
from statsforecast import StatsForecast
from statsforecast.models import AutoARIMA, AutoETS

sf = StatsForecast(models=[AutoARIMA(season_length=7)], freq='D', n_jobs=-1)
sf.fit(df)

# MLForecast externally
from mlforecast import Forecast
fcst = Forecast(models=[lgb.LGBMRegressor()], lags=[7, 14, 30])
fcst.fit(df)
```

---

### 5.2 Priorities

| Priority | Library | When to use |
|-----------|------------|-------------------|
| ⭐ **1** | **Darts** | Universal replacement Prophet, 30+ model |
| **2** | StatsForecast | For statistical purposes baseline scale |
| **3** | NeuralForecast | For maximum accuracy (GPU) |
| **4** | NeuralProphet | If you need Russian holidays (box) |
| **5** | pmdarima | If you want clean ARIMA |
| **6** | PyCaret | For prototyping and fast baseline |

---

### 5.3 What to Avoid

| Library | Reason |
|------------|---------|
| ❌ **Kats** | A dead project (Meta, 2022) |
| ⚠️ **Greykite** | LinkedIn not actively developing |
| ⚠️ **Orbit** | Moderate support, specific Bayesian approach |
| ⚠️ **Prophet** (current) | Slowly, passiveness |

---

### 5.4 What to Add to the Scheme

To support Darts, you need to expand `ModelOptions`:

```python
class ModelOptions(DiscriminatedTypedDict):
    model_type: ModelType  # Literal["prophet", "darts", "pmdarima"]
    # Common fields
    exogenous_vars: list[str] | None  # External factors
    uncertainty_samples: int | None     # For probabilistic
    # Darts-specific
    darts_model: str | None  # "ExponentialSmoothing", "ARIMA", "NBEATS"
```

---

### 5.5 Risks and Cons of Darts

The 4-5 sections call Darts the best candidate – but, symmetrically parsing the problems of the current Prophet solution (2 section), migration has its own specific risks tied to the architecture of this SDK.

**1 .Serialization incompatible with current pattern**

**Problem:** `serialize_prophet_model()` (`prophet_model.py`) serializes the trained model through the built-in `prophet.serialize.model_to_json()` - the result is put into a regular JSON document through `_dumps()` /`json.dumps` (`helpers/predictor/serialization.py`). Darts has a single JSON serialization for all models: statistical models (`ExponentialSmoothing`, `ARIMA`) are serialized through `pickle`, PyTorch models - through its own `save()` /`load()` checkpoint in torch.

**Impact:** Option A from the 5.4 section (store model object as it is in `model: Any`, as now Prophet) will not be able to pass through the existing JSON-based `_dumps` /`_loads` in the same way. It will require either a branching of the model-type serialization format or a transition to a binary storage format for Darts models - this changes the `CommonModel` contract for all model types, not just Darts.

**2 .Duplicating the volume of the boilerplate code per model**

**Problem:** Current Prophet-path is patterned `getter → per-field validator → CheckList → is_valid_* → builder → serializer` (centimetre. `prophet_options.py`, `prophet_model.py` in `helpers/predictor/models/prophet_model/`) — it ≈400 lines on one model without taking into account the `prophet_model.py` in `predictor/`.

**Impact:** Each new model (Darts, much less if sktime/StatsForecast is added later) will require the same amount of code to validate and (de)series options.The 5.1 section promises Darts to be added "in 1-2 weeks" - this estimate does not take into account the volume of the already existing boilerplate for the Prophet model alone.

**3: Heterogeneous capability support between Darts models**

**Problem:** `probabilistic forecasting`, `past_covariates`/`future_covariates` and `backtest()` in Darts not supported by all 30+ model (for example, simpler models `NaiveSeasonal` don’t support covariate).

**Impact:** One `darts_model_fit/predict/test` sectional 5.1 can’t be-presently universal — wrapper needs validation "This option is incompatible with this model" for each combination, Otherwise, mistakes will fall deep inside Darts, not at the level of validation SDK (as currently implemented for ProphetOptions).

**4 Holidays and heavy addictions**

The lack of a built-in `add_country_holidays()` analogue (as opposed to NeuralProphet) and the optional, but actually necessary, dependence on PyTorch for DL models increase the weight and complexity of the build compared to the current installation (`prophet` + `pystan` /`cmdstanpy`).

**5 .Young release cycle**

**Problem:** 61 release and version 0.45.0 (section 4.3) They talk about frequent changes API minor versions.

**Impact:** It’ll take a clear pin versioning-test for each update, Otherwise, migration risks becoming a constant race for the future breaking changes — unlike Prophet, whose API It hasn’t changed in years-for lack of active development.

> Compatibility according to version Python **not a risk**: The project already requires `>=3.12` (`pyproject.toml`), meets the minimum requirements Darts (`>=3.10`).

None of these points negates Darts’ status as a priority candidate (5.2 section) – but migration should start with one or two Darts statistical models (without PyTorch) to estimate the real cost of serialization and boilerplate before investing in the DL part of the arsenal.

---

## 6: Conclusion

The current implementation of Prophet is a good starting point, but it is:

1. ❌ **Limited to one model** — `Literal["prophet"]`
2. ❌ **No external factors** — not in the scheme `add_regressor`
3. ❌ **No uncertainty intervals** — `PredictResult` fails
4. ❌ **No cross-validation** — no `backtest()`
5. ❌ **Slow installation** — demand C++ compiler Stan
6 .  ️ **Passive support** - Meta has stopped active development

### Recommended Path Forward

> Estimates below — off-time, (a) Relative workload by phase. Point of reference: current Prophet-implementation — it ≈400 line-file/model (`prophet_options.py`, `prophet_model.py` in `helpers/predictor/models/prophet_model/`) patterned `getter → validator → CheckList → builder → serializer`, plus a separate `prophet_model.py` in `predictor/`. Each new type of model repeats this volume. The real term should be evaluated separately after solving the issue of serialization (centimetre. [5.5, paragraph 1](#55-risk-and-minuses-darts)).

```
Phase 1 — pilot on a statistical model Darts (without PyTorch):
├── Dealing with serialization: JSON (Prophet-style) unsuitable Darts,
│   We need to decide between pickle-branch and extension of the format CommonModel
├── Add ModelOptions/CommonModel-diagram (ExponentialSmoothing/Theta),
│   volume-comparable prophet_options.py (~400 validation)
├── Implement darts_model_fit/predict/test, freshen model_method_hash in predictor.py
└── Test on the real thing RTB-rows, match up/speed Prophet directly
    (Not on the Vendor benchmarks in the section 3)

Phase 2 — extension of the set of models and backtesting:
├── Add 2-4 model Darts, each clearly check the support
│   probabilistic/covariates (Not all models support the same — centimetre. 5.5, paragraph 3)
├── Implement backtesting superimposed darts.backtest()
└── Estimate the increase in accuracy versus the cost of supporting a new serialization format

Phase 3 — production scale (Only if the previous steps have been justified):
├── StatsForecast for baseline/scale (demand PyTorch)
├── MLForecast row-c exogenous-variable
└── Monitoring of model quality in production
```

### Final verdict

| Library | Status | Reason |
|------------|--------|---------|
| ⭐ **Darts** | **Best choice with reservations** | 30+ model, supportive, sklearn API — But it requires a new serialization format and code size at the current level Prophet-implementation, centimetre. [5.5](#55-risk-and-minuses-darts) |
| StatsForecast | Good | Fast ARIMA, scale |
| NeuralForecast | Good | SOTA deep learning |
| NeuralProphet | Mean | Better Prophet, but Darts better |
| pmdarima | Mean | Clean ARIMA, if not ensemble |
| PyCaret | Mean | Prototyping, not production |
| **Kats** | ❌ | Dead |
| **Greykite** | ⚠️ | Passive support |
| **Orbit** | ⚠️ | Moderate support |
| **Prophet** | ⚠️ | Keep it for compatibility |
