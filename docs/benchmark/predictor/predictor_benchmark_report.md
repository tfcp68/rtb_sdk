# Benchmark predictor: Prophet (feed-in) vs alternatives, forecast horizon

- Generated: `2026-07-20T19:31:52`
- Python 3.12.10, Windows-10 -10.0.19045 -SP0 platform
- Baseline, the real `rtb_sdk.predictor.fit/test` (Prophet) product path, is called with **net `create_prophet_options()` defaults, no manual tuning,** just like the rest of the 5 engines, which are called directly (not yet built into the SDK) with one generalized configuration for all scenarios. The comparison here is all engines out of the box on equal terms.
- **Rolling-origin backtesting**: one-off train/test-split-screen — until `5` origins (fixed-size sliding learning window `n_train`), horizons — `mean ± 95% CI` by origins (confidence interval t-distribution; upon `n=1` origin with this horizon — numberless ±, the interval of one point is not considered). This provides a statistical basis for the selection of the engine in the product, Not a point estimate on one random window.
- Metrics — same formulae, what `rtb_sdk.helpers.predictor.metrics.calc_metrics` (`accuracy=1-MAPE`).  `fit, s` — average-time origins (no matter the horizon). `accuracy@h` — predictability `h` Steps forward from the end of the learning sample of each origin.
- **Bug found and corrected during this benchmark**: `prophet_sdk` fell at monthly resolution with `PredictorError: Forecast did not pass validation` due to `GRAN_TO_PROPHET_FREQ['m'] = "M"` (`src/rtb_sdk/constants/frequencies_consts.py`, end of month instead of start) - corrected to `"MS"` + added regression test `round_trip_test_monthly`. Figures below - **after** fix.

## Summary: Rating of predictors

### Rating table by average accuracy

| rang | Predictor | Mean accuracy | Victory | Balls | Status |
| ---: | --- | --: | --: | --: | --- |
| — | **Prophet (feed-in)** | **0.8275** | 0 | 0 | Baseline, current-sale |
| 1 | AutoARIMA (pmdarima) | 0.9119 | 2 | 20 | ⭐ Best candidate |
| 2 | AutoARIMA (StatsForecas) | 0.9036 | 1 | 18 | ⭐ For periods |
| 3 | N-BEATS (NeuralForecast) | 0.9011 | 1 | 18 | ✓ Sentinels |
| 4 | Theta (DARTS) | 0.8925 | 1 | 18 | ⭐ Daytime |
| 5 | AutoETS (StatsForecas) | 0.8924 | 2 | 16 | ✓ Fast |
| 6 | LightGBM (ML Forecast) | 0.8843 | 0 | 0 | ⚠ Weaker |
| 7 | N-HiTS (NeuralForecast) | 0.8878 | 0 | 0 | ✓ Similar N-BEATS |
| 8 | Exp. Smoothing (DARTS) | 0.8769 | 3 | 14 | ✓ 3 victory |
| 9 | NeuralProphet | 0.8409 | 1 | 12 | ⚠ Unstable |

**Points**: 1 - place = 10 points, 2 -e = 9 , ..., 10 -e = 1 Recalculation: (1 + number of wins × 2 )

**Conclusions for implementation**:

- **Front**: AutoARIMA (pmdarima) – +4.4% to baseline 0.8275, leader with 2 wins and versatile
- **Insurance**: AutoETS (StatsForecas) - +5.5% but wins only on CO2 and JFK; faster (0.31 vs 39.2 c)
- **Hourly Trends**: N-BEATS (NeuralForecast) is the only one with +0.86 to baseline on real_traffic_hourly
- **Daytime backlogs**: Theta (DARTS) — win M4 daily (+1.0 accuracy)

---

### Detailed scenario table

Average accuracy over all forecast horizons for each scenario (fat is the best engine in the column).

| Predictor | [smooth_seasonal](#scripture-smooth_seasonal) | [short_volatile](#scripture-short_volatile) | [real_airpassengers](#scripture-real_airpassengers) | [real_co2_monthly](#scripture-real_co2_monthly) | [real_seatbelts](#scripture-real_seatbelts) | [real_jfk_passengers](#scripture-real_jfk_passengers) | [real_air_quality_temp](#scripture-real_air_quality_temp) | [real_m4_monthly](#scripture-real_m4_monthly) | [real_traffic_hourly](#scripture-real_traffic_hourly) | [real_m4_daily](#scripture-real_m4_daily) | Mean |
| --- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| Prophet (feed-in) — baseline | 0.7340 | 0.7396 | 0.9552 | 0.9989 | 0.8506 | 0.8718 | 0.6803 | 0.8121 | 0.6474 | 0.9854 | 0.8275 |
| AutoARIMA (pmdarima) | **0.9650** | 0.7583 | 0.9624 | 0.9990 | 0.8899 | 0.9672 | **0.8694** | 0.9057 | 0.8103 | 0.9916 | **0.9119** |
| AutoARIMA (StatsForecas) | 0.9477 | 0.7601 | 0.9575 | 0.9991 | 0.8804 | 0.9727 | 0.8173 | 0.9028 | 0.8068 | 0.9916 | **0.9036** |
| N-BEATS (NeuralForecast) | 0.9618 | 0.6752 | 0.9602 | 0.9944 | 0.8631 | 0.9552 | 0.8542 | 0.8939 | **0.8626** | 0.9908 | **0.9011** |
| Theta (DARTS) | 0.9141 | 0.7662 | 0.9325 | 0.9970 | 0.8845 | 0.9397 | 0.8442 | 0.8007 | 0.8527 | **0.9929** | **0.8925** |
| AutoETS (StatsForecas) | 0.8856 | 0.7635 | 0.9520 | **0.9992** | 0.8750 | **0.9745** | 0.7676 | 0.9241 | 0.7913 | 0.9916 | **0.8924** |
| LightGBM (ML Forecast) | 0.9543 | 0.7485 | 0.8848 | 0.9953 | 0.8420 | 0.9400 | 0.8542 | 0.8300 | 0.8055 | 0.9890 | 0.8843 |
| N-HiTS (NeuralForecast) | 0.9569 | 0.6768 | 0.9448 | 0.9950 | 0.8491 | 0.9194 | 0.8204 | 0.8746 | 0.8503 | 0.9906 | 0.8878 |
| Exp. Smoothing (DARTS) | 0.6984 | **0.7741** | **0.9700** | 0.9991 | 0.8730 | 0.9650 | 0.7962 | **0.9260** | 0.7754 | 0.9918 | 0.8769 |
| NeuralProphet | 0.8593 | 0.7530 | 0.9316 | 0.9986 | **0.8946** | 0.9393 | 0.8175 | 0.4475 | 0.7785 | 0.9893 | 0.8409 |

**The Best Engine on Long Horizons** (`h>=60`, forward-looking, daytime scenarios only):

- `smooth_seasonal`: **pmdarima_autoarima** (0.9679)
- `real_m4_daily`: **darts_theta** (0.9863)

## Screenplay: `smooth_seasonal`

[↑ To the detailed table](#detailed-table-by-script) · [↑ To the rating table](#table-rating-by-middle-class-precision)

**Synthetics** (generated by this script, No real data). 240 days, `train=150 / test=90`, `resolution='d'`. Formula: trend-cycle — sinusoid 30 days (amplitude 20) + weekly — sinusoid 7 days (amplitude 5) + gauss (σ=2). Specially smooth and predictable series — patterned `examples/predictor/generate_test_data.py`, if Prophet He was not in unfavorable conditions at the start. Test tail is enlarged to 90 days, to cover all horizons up to `h=90`.

**Accuracy on the forecast horizon** (rolling-origin backtesting, 5 origins, `mean±95% CI`; with `n=1` - just a number without ±; `h` - steps forward from origin, `resolution='d'`; in parentheses, the engine - the average time of `fit`, c):

| Engine | h=1 | h=3 | h=7 | h=14 | h=20 | h=30 | h=60 | h=90 |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| prophet_sdk (baseline, feed-in) (fit 0.719s) | 0.883±0.121 | 0.861±0.116 | 0.741±0.190 | 0.576±0.485 | 0.544±0.625 | 0.734±0.367 | 0.727±1.451 | 0.856 (n=1) |
| darts_ets (fit 1.346s) | 0.974±0.038 | 0.961±0.079 | 0.914±0.140 | 0.762±0.189 | 0.603±0.152 | 0.341±0.367 | 0.000±0.000 | 0.000 (n=1) |
| darts_theta (fit 0.012s) | 0.938±0.034 | 0.907±0.062 | 0.919±0.031 | 0.906±0.012 | 0.906±0.017 | 0.913±0.016 | 0.903±0.091 | 0.888 (n=1) |
| statsforecast_autoarima (fit 7.545s) | 0.968±0.030 | 0.967±0.026 | 0.947±0.061 | 0.933±0.117 | 0.934±0.090 | 0.938±0.122 | 0.944±0.073 | 0.919 (n=1) |
| statsforecast_autoets (fit 0.212s) | 0.968±0.024 | 0.956±0.045 | 0.902±0.083 | 0.827±0.051 | 0.813±0.086 | 0.845±0.086 | 0.837±0.428 | 0.870 (n=1) |
| pmdarima_autoarima (fit 39.225s) | 0.984±0.019 | 0.984±0.010 | 0.972±0.018 | 0.944±0.104 | 0.927±0.158 | 0.974±0.010 | 0.970±0.024 | 0.963 (n=1) |
| mlforecast_lightgbm (fit 0.936s) | 0.967±0.037 | 0.964±0.032 | 0.962±0.011 | 0.958±0.025 | 0.950±0.041 | 0.956±0.024 | 0.922±0.363 | 0.875 (n=1) |
| neuralforecast_nbeats (fit 28.071s) | 0.965±0.031 | 0.969±0.029 | 0.955±0.026 | 0.953±0.034 | 0.957±0.033 | 0.968±0.021 | 0.965±0.099 | 0.969 (n=1) |
| neuralforecast_nhits (fit 31.628s) | 0.975±0.026 | 0.951±0.056 | 0.951±0.034 | 0.951±0.029 | 0.950±0.025 | 0.957±0.020 | 0.958±0.029 | 0.957 (n=1) |
| neuralprophet (fit 42.509s) | 0.897±0.101 | 0.866±0.104 | 0.854±0.060 | 0.829±0.084 | 0.831±0.036 | 0.865±0.022 | 0.867±0.008 | 0.866 (n=1) |

## Screenplay: `short_volatile`

[↑ To the detailed table](#detailed-table-by-script) · [↑ To the rating table](#table-rating-by-middle-class-precision)

**Synthetics.** 74 of the day, `train=60 / test=14`, `resolution='d'`. Without trend, only weekly seasonality (sinusoid, amplitude of 15) + heavy noise (σ=6) + rare bursts (+40 with probability of 5% per day, imitation of advertising peaks). Short history, high volatility - closer to what a young RTB campaign without a long backtest really sees.

**Accuracy on the forecast horizon** (rolling-origin backtesting, 5 origins, `mean±95% CI`; with `n=1` - just a number without ±; `h` - steps forward from origin, `resolution='d'`; in parentheses, the engine - the average time of `fit`, c):

| Engine | h=1 | h=3 | h=7 | h=14 |
|---|--:|--:|--:|--:|
| prophet_sdk (baseline, feed-in) (fit 0.788s) | 0.691±0.232 | 0.768±0.165 | 0.770±0.143 | 0.778 (n=1) |
| darts_ets (fit 0.204s) | 0.718±0.186 | 0.801±0.192 | 0.815±0.173 | 0.824 (n=1) |
| darts_theta (fit 0.016s) | 0.695±0.233 | 0.806±0.208 | 0.813±0.189 | 0.825 (n=1) |
| statsforecast_autoarima (fit 2.215s) | 0.739±0.211 | 0.755±0.152 | 0.793±0.116 | 0.786 (n=1) |
| statsforecast_autoets (fit 0.125s) | 0.711±0.215 | 0.782±0.131 | 0.810±0.099 | 0.809 (n=1) |
| pmdarima_autoarima (fit 9.707s) | 0.717±0.189 | 0.770±0.162 | 0.799±0.124 | 0.795 (n=1) |
| mlforecast_lightgbm (fit 0.043s) | 0.725±0.244 | 0.751±0.145 | 0.776±0.098 | 0.770 (n=1) |
| neuralforecast_nbeats (fit 22.331s) | 0.689±0.176 | 0.647±0.075 | 0.669±0.164 | 0.736 (n=1) |
| neuralforecast_nhits (fit 24.300s) | 0.678±0.211 | 0.648±0.147 | 0.686±0.213 | 0.756 (n=1) |
| neuralprophet (fit 44.193s) | 0.705±0.262 | 0.794±0.281 | 0.771±0.317 | 0.778 (n=1) |

## Screenplay: `real_airpassengers`

[↑ To the detailed table](#detailed-table-by-script) · [↑ To the rating table](#table-rating-by-middle-class-precision)

**Real data.** Classical **AirPassengers** — Number of American Airlines Passengers, thousand. chelo./moss. Source: `pmdarima.datasets.load_airpassengers()` (offline, goes along `pmdarima`, don’t). 144 point, 1949-01–1960-12, `train=120 / test=24`, `resolution='m'`. A clear upward trend + **multiplier** seasonality (The amplitude of seasonal fluctuations increases with the level of) — training standard Holt-Winters/ARIMA s 1970-x.

**Accuracy on the forecast horizon** (rolling-origin backtesting, 5 origins, `mean±95% CI`; with `n=1` - just a number without ±; `h` - steps forward from origin, `resolution='m'`; in parentheses, the engine - the average time of `fit`, c):

| Engine | h=1 | h=2 | h=3 | h=6 | h=12 |
|---|--:|--:|--:|--:|--:|
| prophet_sdk (baseline, feed-in) (fit 0.667s) | 0.965±0.025 | 0.952±0.031 | 0.953±0.034 | 0.953±0.025 | 0.950±0.016 |
| darts_ets (fit 0.202s) | 0.978±0.015 | 0.975±0.024 | 0.966±0.012 | 0.966±0.014 | 0.959±0.031 |
| darts_theta (fit 0.017s) | 0.947±0.095 | 0.933±0.130 | 0.940±0.075 | 0.928±0.095 | 0.905±0.104 |
| statsforecast_autoarima (fit 1.821s) | 0.972±0.021 | 0.964±0.028 | 0.956±0.034 | 0.950±0.047 | 0.936±0.095 |
| statsforecast_autoets (fit 0.181s) | 0.967±0.028 | 0.954±0.044 | 0.948±0.030 | 0.948±0.012 | 0.935±0.078 |
| pmdarima_autoarima (fit 6.921s) | 0.975±0.018 | 0.968±0.020 | 0.959±0.021 | 0.956±0.031 | 0.947±0.053 |
| mlforecast_lightgbm (fit 0.046s) | 0.903±0.107 | 0.856±0.174 | 0.871±0.157 | 0.898±0.080 | 0.892±0.026 |
| neuralforecast_nbeats (fit 20.963s) | 0.974±0.039 | 0.958±0.054 | 0.953±0.048 | 0.957±0.025 | 0.953±0.034 |
| neuralforecast_nhits (fit 33.399s) | 0.956±0.054 | 0.944±0.023 | 0.945±0.017 | 0.941±0.013 | 0.932±0.020 |
| neuralprophet (fit 31.783s) | 0.934±0.056 | 0.918±0.079 | 0.925±0.064 | 0.942±0.027 | 0.942±0.014 |

## Screenplay: `real_co2_monthly`

[↑ To the detailed table](#detailed-table-by-script) · [↑ To the rating table](#table-rating-by-middle-class-precision)

**Real data.** Concentration CO₂ (ppm), observatory Mauna Loa. Source: `statsmodels.datasets.co2` (offline, goes along `statsmodels`) — initially **weekly** row 1958 year-end, here resampled on a monthly basis (month-average) and take the last 180 point, 1987-01–2001-12, `train=150 / test=30`, `resolution='m'`. **Same row, officially quickstart-tutorial Prophet.** Very smooth linear trend + steady-season — practically «silent» standard (engine-wise accuracy >0.99).

**Accuracy on the forecast horizon** (rolling-origin backtesting, 5 origins, `mean±95% CI`; with `n=1` - just a number without ±; `h` - steps forward from origin, `resolution='m'`; in parentheses, the engine - the average time of `fit`, c):

| Engine | h=1 | h=2 | h=3 | h=6 | h=12 |
|---|--:|--:|--:|--:|--:|
| prophet_sdk (baseline, feed-in) (fit 0.279s) | 0.999±0.001 | 0.999±0.001 | 0.999±0.001 | 0.999±0.001 | 0.999±0.001 |
| darts_ets (fit 0.190s) | 0.999±0.000 | 0.999±0.001 | 0.999±0.001 | 0.999±0.001 | 0.999±0.000 |
| darts_theta (fit 0.013s) | 0.998±0.001 | 0.997±0.004 | 0.997±0.006 | 0.995±0.007 | 0.997±0.007 |
| statsforecast_autoarima (fit 2.918s) | 0.999±0.001 | 0.999±0.001 | 0.999±0.000 | 0.999±0.000 | 0.999±0.001 |
| statsforecast_autoets (fit 0.306s) | 0.999±0.001 | 0.999±0.001 | 0.999±0.001 | 0.999±0.001 | 0.999±0.001 |
| pmdarima_autoarima (fit 44.889s) | 0.999±0.001 | 0.999±0.000 | 0.999±0.000 | 0.999±0.000 | 0.999±0.001 |
| mlforecast_lightgbm (fit 0.041s) | 0.996±0.004 | 0.995±0.004 | 0.995±0.002 | 0.995±0.002 | 0.995±0.001 |
| neuralforecast_nbeats (fit 19.205s) | 0.997±0.004 | 0.995±0.007 | 0.994±0.008 | 0.992±0.008 | 0.994±0.006 |
| neuralforecast_nhits (fit 32.372s) | 0.997±0.002 | 0.996±0.006 | 0.995±0.008 | 0.993±0.008 | 0.994±0.007 |
| neuralprophet (fit 35.240s) | 0.999±0.001 | 0.999±0.002 | 0.999±0.001 | 0.998±0.002 | 0.998±0.001 |

## Screenplay: `real_seatbelts`

[↑ To the detailed table](#detailed-table-by-script) · [↑ To the rating table](#table-rating-by-middle-class-precision)

**Real data.** **UK Driver Deaths** — Number of dead and seriously injured drivers/passengers in Britain. Source: [Turing Change Point Dataset](https://github.com/alan-turing-institute/TCPD) (license GPL-2, original — R `datasets::UKDriverDeaths`), localization `benchmarks/data/seatbelts.json`. 192 point, 1969-01–1984-12, `train=168 / test=24`, `resolution='m'`. **Not smooth seasonality** — in 1983 Mandatory seat belts became law, And the data shows a dramatic structural shift in the level. A classic test case for detection methods changepoint — specially, To test models not only on smooth trends.

**Accuracy on the forecast horizon** (rolling-origin backtesting, 5 origins, `mean±95% CI`; with `n=1` - just a number without ±; `h` - steps forward from origin, `resolution='m'`; in parentheses, the engine - the average time of `fit`, c):

| Engine | h=1 | h=2 | h=3 | h=6 | h=12 |
|---|--:|--:|--:|--:|--:|
| prophet_sdk (baseline, feed-in) (fit 0.784s) | 0.897±0.109 | 0.822±0.095 | 0.846±0.068 | 0.840±0.102 | 0.831±0.102 |
| darts_ets (fit 4.491s) | 0.925±0.061 | 0.869±0.155 | 0.867±0.160 | 0.855±0.158 | 0.825±0.260 |
| darts_theta (fit 0.015s) | 0.926±0.044 | 0.881±0.155 | 0.880±0.153 | 0.864±0.150 | 0.853±0.299 |
| statsforecast_autoarima (fit 11.159s) | 0.926±0.049 | 0.858±0.136 | 0.871±0.147 | 0.872±0.179 | 0.857±0.350 |
| statsforecast_autoets (fit 0.338s) | 0.921±0.058 | 0.866±0.156 | 0.871±0.161 | 0.858±0.153 | 0.837±0.275 |
| pmdarima_autoarima (fit 31.154s) | 0.940±0.070 | 0.894±0.192 | 0.884±0.184 | 0.876±0.183 | 0.827±0.280 |
| mlforecast_lightgbm (fit 0.048s) | 0.906±0.086 | 0.821±0.190 | 0.845±0.158 | 0.811±0.121 | 0.800±0.207 |
| neuralforecast_nbeats (fit 23.543s) | 0.901±0.073 | 0.858±0.189 | 0.858±0.192 | 0.856±0.230 | 0.824±0.410 |
| neuralforecast_nhits (fit 36.965s) | 0.898±0.143 | 0.838±0.342 | 0.847±0.319 | 0.845±0.334 | 0.792±0.534 |
| neuralprophet (fit 35.369s) | 0.933±0.106 | 0.883±0.197 | 0.895±0.156 | 0.880±0.151 | 0.866±0.245 |

## Screenplay: `real_jfk_passengers`

[↑ To the detailed table](#detailed-table-by-script) · [↑ To the rating table](#table-rating-by-middle-class-precision)

**Real data.** Airport passenger traffic **JFK** (arrival + departure), chelo./moss. Source: [Turing Change Point Dataset](https://github.com/alan-turing-institute/TCPD) (baseline — Kaggle/NY State Air Passenger Traffic, license CC0), localization `benchmarks/data/jfk_passengers.json`. 468 point, 1977-01–2015-12, `train=444 / test=24`, `resolution='m'` — Real Trendy Traffic, seasonality and structural shocks (energy crises, 11 September 2001, financial crisis 2008).

**Accuracy on the forecast horizon** (rolling-origin backtesting, 5 origins, `mean±95% CI`; with `n=1` - just a number without ±; `h` - steps forward from origin, `resolution='m'`; in parentheses, the engine - the average time of `fit`, c):

| Engine | h=1 | h=2 | h=3 | h=6 | h=12 |
|---|--:|--:|--:|--:|--:|
| prophet_sdk (baseline, feed-in) (fit 0.964s) | 0.875±0.041 | 0.884±0.036 | 0.879±0.028 | 0.859±0.031 | 0.859±0.041 |
| darts_ets (fit 1.312s) | 0.980±0.022 | 0.963±0.039 | 0.964±0.036 | 0.961±0.020 | 0.949±0.029 |
| darts_theta (fit 0.020s) | 0.943±0.036 | 0.931±0.038 | 0.935±0.041 | 0.946±0.018 | 0.943±0.023 |
| statsforecast_autoarima (fit 19.180s) | 0.983±0.024 | 0.970±0.034 | 0.970±0.027 | 0.972±0.017 | 0.965±0.012 |
| statsforecast_autoets (fit 0.690s) | 0.984±0.013 | 0.974±0.022 | 0.971±0.022 | 0.971±0.013 | 0.969±0.012 |
| pmdarima_autoarima (fit 195.344s) | 0.977±0.028 | 0.960±0.049 | 0.964±0.039 | 0.968±0.021 | 0.964±0.021 |
| mlforecast_lightgbm (fit 0.071s) | 0.955±0.044 | 0.927±0.061 | 0.926±0.045 | 0.944±0.010 | 0.945±0.007 |
| neuralforecast_nbeats (fit 23.671s) | 0.960±0.046 | 0.945±0.103 | 0.952±0.077 | 0.958±0.035 | 0.961±0.035 |
| neuralforecast_nhits (fit 22.199s) | 0.937±0.051 | 0.882±0.144 | 0.908±0.101 | 0.936±0.047 | 0.935±0.035 |
| neuralprophet (fit 52.608s) | 0.943±0.035 | 0.928±0.060 | 0.937±0.049 | 0.942±0.028 | 0.948±0.031 |

## Screenplay: `real_air_quality_temp`

[↑ To the detailed table](#detailed-table-by-script) · [↑ To the rating table](#table-rating-by-middle-class-precision)

**Real data.** Air temperature (°C), hourly. Source: [UCI Air Quality Dataset](https://archive.ics.uci.edu/dataset/360) (archive.ics.uci.edu), localization `benchmarks/data/air_quality_temp.json`, pass-through (~3.9%, centinel `-200`) Prointerpolated linearly when downloaded. Taken first 230 row (~9.6 daylight; row — 9357 hours, even 600 The clocks were unbearable in time: auto-ARIMA/pmdarima seasonally `m=24` not fitting in 13+ minute — season-time 24 much heavier, more `m=12` monthly), `train=180 / test=50`, `resolution='h'` — **First and Only Hourly Screenplay**, daily seasonality (`season_length=24`) weekly/yearly.

**Accuracy on the forecast horizon** (rolling-origin backtesting, 5 origins, `mean±95% CI`; with `n=1` - just a number without ±; `h` - steps forward from origin, `resolution='h'`; in parentheses, the engine - the average time of `fit`, c):

| Engine | h=1 | h=6 | h=12 | h=24 | h=48 |
|---|--:|--:|--:|--:|--:|
| prophet_sdk (baseline, feed-in) (fit 2.778s) | 0.871±0.119 | 0.800±0.150 | 0.670±0.260 | 0.444±0.958 | 0.000 (n=1) |
| darts_ets (fit 1.593s) | 0.952±0.032 | 0.813±0.112 | 0.701±0.133 | 0.704±0.183 | 0.609 (n=1) |
| darts_theta (fit 0.013s) | 0.936±0.056 | 0.859±0.103 | 0.774±0.208 | 0.767±0.298 | 0.839 (n=1) |
| statsforecast_autoarima (fit 25.274s) | 0.941±0.036 | 0.841±0.194 | 0.736±0.310 | 0.751±0.098 | 0.626 (n=1) |
| statsforecast_autoets (fit 0.344s) | 0.947±0.067 | 0.787±0.340 | 0.644±0.514 | 0.602±0.866 | 0.784 (n=1) |
| pmdarima_autoarima (fit 137.512s) | 0.976±0.023 | 0.877±0.077 | 0.783±0.159 | 0.798±0.257 | 0.863 (n=1) |
| mlforecast_lightgbm (fit 0.055s) | 0.957±0.056 | 0.864±0.149 | 0.816±0.246 | 0.757±0.243 | 0.751 (n=1) |
| neuralforecast_nbeats (fit 25.049s) | 0.939±0.054 | 0.878±0.123 | 0.794±0.243 | 0.802±0.183 | 0.728 (n=1) |
| neuralforecast_nhits (fit 21.747s) | 0.943±0.046 | 0.836±0.215 | 0.723±0.359 | 0.757±0.265 | 0.725 (n=1) |
| neuralprophet (fit 27.630s) | 0.847±0.194 | 0.842±0.072 | 0.780±0.209 | 0.803±0.107 | 0.767 (n=1) |

## Screenplay: `real_m4_monthly`

[↑ To the detailed table](#detailed-table-by-script) · [↑ To the rating table](#table-rating-by-middle-class-precision)

**Real data.** Series **M1** of [M4 Competition](https://github.com/Mcompetitions/M4-methods) — «gold-standard» Academic Benchmark Forecasting (100 000 rows, Here’s one monthly, category Macro). Local copy `benchmarks/data/m4_monthly_m1.json` (original train+test M4 continually). 487 point, 1976-06–2016-12, `train=463 / test=24`, `resolution='m'`. Rows in M4 anonymously — There is no description of the physical quantity, category.

**Accuracy on the forecast horizon** (rolling-origin backtesting, 5 origins, `mean±95% CI`; with `n=1` - just a number without ±; `h` - steps forward from origin, `resolution='m'`; in parentheses, the engine - the average time of `fit`, c):

| Engine | h=1 | h=2 | h=3 | h=6 | h=12 |
|---|--:|--:|--:|--:|--:|
| prophet_sdk (baseline, feed-in) (fit 0.699s) | 0.775±0.178 | 0.820±0.165 | 0.830±0.117 | 0.826±0.137 | 0.821±0.132 |
| darts_ets (fit 0.261s) | 0.960±0.043 | 0.960±0.069 | 0.922±0.071 | 0.893±0.038 | 0.873±0.109 |
| darts_theta (fit 0.022s) | 0.835±0.175 | 0.810±0.277 | 0.774±0.248 | 0.790±0.179 | 0.781±0.172 |
| statsforecast_autoarima (fit 54.055s) | 0.918±0.017 | 0.923±0.037 | 0.898±0.044 | 0.890±0.042 | 0.873±0.061 |
| statsforecast_autoets (fit 0.629s) | 0.953±0.060 | 0.956±0.064 | 0.920±0.063 | 0.896±0.039 | 0.876±0.098 |
| pmdarima_autoarima (fit 162.038s) | 0.914±0.039 | 0.927±0.044 | 0.902±0.041 | 0.896±0.045 | 0.882±0.011 |
| mlforecast_lightgbm (fit 0.072s) | 0.824±0.091 | 0.851±0.060 | 0.825±0.036 | 0.826±0.040 | 0.824±0.111 |
| neuralforecast_nbeats (fit 19.803s) | 0.899±0.085 | 0.908±0.034 | 0.891±0.052 | 0.891±0.038 | 0.874±0.019 |
| neuralforecast_nhits (fit 30.487s) | 0.865±0.104 | 0.887±0.088 | 0.874±0.079 | 0.878±0.063 | 0.871±0.054 |
| neuralprophet (fit 40.842s) | 0.465±0.366 | 0.527±0.474 | 0.484±0.367 | 0.388±0.172 | 0.342±0.156 |

## Screenplay: `real_traffic_hourly`

[↑ To the detailed table](#detailed-table-by-script) · [↑ To the rating table](#table-rating-by-middle-class-precision)

**Real data — project, non-external.** Number of ad-hourly, directly counted production-den (`E:/Logs/janus-*.parquet`, month-long 2026-06-01–2026-07-01, ~710M. Events, local time `Europe/Moscow`). Local copy — `benchmarks/data/real_traffic_hourly.json` (719 hours). In aggregation found and linearly interpolated 2 one-hour emissions (neighbourhood, >4x/<0.25x): `2026-06-10T12:00` — 117 430 960 instead ~608k (known artifact of broken data in `janus-20260608.parquet`, centimetre. `docs/benchmark/reach_frequency/README.md`), and `2026-06-05T03:00` — 37 660 instead of the typical hour 290-600k. `train=180 / test=130`, `resolution='h'`, daily seasonality (`season_length=24`). Horizons extended to `h=72/96/120` (3-5 daylight) Specifically to check the multi-day forecast on real traffic.

**Accuracy on the forecast horizon** (rolling-origin backtesting, 5 origins, `mean±95% CI`; with `n=1` - just a number without ±; `h` - steps forward from origin, `resolution='h'`; in parentheses, the engine - the average time of `fit`, c):

| Engine | h=1 | h=6 | h=12 | h=24 | h=48 | h=72 | h=96 | h=120 |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| prophet_sdk (baseline, feed-in) (fit 2.368s) | 0.727±0.228 | 0.683±0.272 | 0.621±0.448 | 0.602±0.592 | 0.626±0.493 | 0.649±0.440 | 0.629±0.342 | 0.622±0.294 |
| darts_ets (fit 1.145s) | 0.872±0.204 | 0.827±0.212 | 0.874±0.080 | 0.830±0.140 | 0.760±0.344 | 0.726±0.477 | 0.661±0.589 | 0.630±0.674 |
| darts_theta (fit 0.012s) | 0.888±0.219 | 0.842±0.285 | 0.871±0.172 | 0.873±0.166 | 0.852±0.110 | 0.848±0.104 | 0.825±0.087 | 0.814±0.071 |
| statsforecast_autoarima (fit 26.776s) | 0.886±0.189 | 0.841±0.264 | 0.865±0.165 | 0.821±0.190 | 0.785±0.268 | 0.769±0.283 | 0.745±0.274 | 0.723±0.312 |
| statsforecast_autoets (fit 0.307s) | 0.867±0.221 | 0.802±0.282 | 0.815±0.204 | 0.780±0.281 | 0.774±0.275 | 0.772±0.271 | 0.752±0.248 | 0.750±0.238 |
| pmdarima_autoarima (fit 54.370s) | 0.907±0.210 | 0.843±0.240 | 0.852±0.105 | 0.808±0.129 | 0.792±0.132 | 0.778±0.156 | 0.746±0.148 | 0.730±0.147 |
| mlforecast_lightgbm (fit 0.047s) | 0.869±0.226 | 0.824±0.273 | 0.856±0.133 | 0.839±0.182 | 0.796±0.182 | 0.781±0.181 | 0.743±0.197 | 0.720±0.222 |
| neuralforecast_nbeats (fit 21.941s) | 0.901±0.158 | 0.882±0.194 | 0.915±0.098 | 0.893±0.095 | 0.862±0.079 | 0.846±0.079 | 0.805±0.062 | 0.787±0.060 |
| neuralforecast_nhits (fit 30.246s) | 0.910±0.181 | 0.873±0.202 | 0.895±0.079 | 0.878±0.075 | 0.845±0.075 | 0.829±0.087 | 0.787±0.076 | 0.772±0.068 |
| neuralprophet (fit 27.348s) | 0.847±0.245 | 0.820±0.298 | 0.841±0.185 | 0.819±0.195 | 0.785±0.132 | 0.743±0.176 | 0.696±0.211 | 0.659±0.276 |

## Screenplay: `real_m4_daily`

[↑ To the detailed table](#detailed-table-by-script) · [↑ To the rating table](#table-rating-by-middle-class-precision)

**Real data.** Series **D1** of [M4 Competition](https://github.com/Mcompetitions/M4-methods) — category Macro, daytime (Unlike other real-world scenarios, periodical/sentry). Local copy `benchmarks/data/m4_daily_d1.json` (original train+test M4 continually, 1020 point). Rows in M4 Anonymized and do not carry a real calendar — synthetic dates from `StartingDate=1994-01-03` (of `M4-info.csv`), self-employed **significance** real-life. `train=600 / test=90`, `resolution='d'` — The test tail has been specially increased to 90 days, close the gap: prognosis (`h=60`, `h=90`) real-world, not just synthetics `smooth_seasonal`.

**Accuracy on the forecast horizon** (rolling-origin backtesting, 5 origins, `mean±95% CI`; with `n=1` - just a number without ±; `h` - steps forward from origin, `resolution='d'`; in parentheses, the engine - the average time of `fit`, c):

| Engine | h=1 | h=3 | h=7 | h=14 | h=20 | h=30 | h=60 | h=90 |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| prophet_sdk (baseline, feed-in) (fit 0.379s) | 0.988±0.011 | 0.992±0.008 | 0.990±0.010 | 0.987±0.014 | 0.984±0.018 | 0.981±0.022 | 0.980±0.016 | 0.980±0.014 |
| darts_ets (fit 0.343s) | 0.997±0.004 | 0.996±0.006 | 0.995±0.005 | 0.993±0.007 | 0.993±0.007 | 0.991±0.011 | 0.986±0.019 | 0.982±0.020 |
| darts_theta (fit 0.009s) | 0.997±0.004 | 0.996±0.005 | 0.996±0.004 | 0.994±0.005 | 0.994±0.006 | 0.992±0.008 | 0.989±0.012 | 0.984±0.012 |
| statsforecast_autoarima (fit 0.875s) | 0.997±0.004 | 0.996±0.006 | 0.995±0.006 | 0.993±0.007 | 0.992±0.007 | 0.990±0.011 | 0.986±0.019 | 0.982±0.020 |
| statsforecast_autoets (fit 0.823s) | 0.997±0.004 | 0.996±0.006 | 0.995±0.006 | 0.993±0.007 | 0.992±0.007 | 0.990±0.011 | 0.986±0.019 | 0.982±0.020 |
| pmdarima_autoarima (fit 6.037s) | 0.997±0.004 | 0.996±0.006 | 0.995±0.006 | 0.993±0.007 | 0.992±0.007 | 0.990±0.011 | 0.986±0.019 | 0.982±0.020 |
| mlforecast_lightgbm (fit 0.070s) | 0.993±0.007 | 0.994±0.006 | 0.992±0.007 | 0.993±0.007 | 0.992±0.006 | 0.990±0.008 | 0.983±0.012 | 0.974±0.022 |
| neuralforecast_nbeats (fit 21.054s) | 0.997±0.004 | 0.996±0.005 | 0.995±0.005 | 0.993±0.007 | 0.992±0.008 | 0.990±0.012 | 0.983±0.022 | 0.979±0.026 |
| neuralforecast_nhits (fit 20.543s) | 0.996±0.004 | 0.995±0.006 | 0.995±0.006 | 0.993±0.008 | 0.992±0.008 | 0.990±0.013 | 0.983±0.022 | 0.979±0.026 |
| neuralprophet (fit 40.312s) | 0.991±0.007 | 0.992±0.005 | 0.992±0.004 | 0.994±0.003 | 0.993±0.006 | 0.990±0.009 | 0.984±0.017 | 0.978±0.019 |
