# Bid forecast benchmark prototypes

Independent research implementations of the Cui (2011) campaign bid-landscape model and the Wang (2016) censored market-price model. They are experimental tools and are not integrated into the production auction path.

## Layout

- `cui/`: Cui model, feature selection, GBDT, and tree helpers.
- `wang/`: Wang categorical survival tree and Kaplan?Meier estimator.
- `bench/`: synthetic, stand-log, fixed-scenario, and price evaluation runners.
- `tests/`: focused checks for model behavior and benchmark reporting.
- `demo.py`: small deterministic demonstration.
- Saved reports and run artifacts: [`docs/benchmark/bid_forecast/`](../../docs/benchmark/bid_forecast/README.md).

## Run from the repository root (PowerShell)

```powershell
.venv\Scripts\python.exe -m benchmarks.bid_forecast_benchmark.demo
.venv\Scripts\python.exe -m pytest benchmarks/bid_forecast_benchmark -q
.venv\Scripts\python.exe -m benchmarks.bid_forecast_benchmark.bench.benchmark --seeds 3,17,29 --rows 240
.venv\Scripts\python.exe -m benchmarks.bid_forecast_benchmark.bench.stand_benchmark --seeds 19,43,71 --max-requests 30000
```

The benchmark runners write saved outputs under `docs/benchmark/bid_forecast/results/` by default. Use their output options to select another location.

## Method notes

Cui models campaign-level bid distributions as a weighted mixture of log-normal segment distributions. The implementation converts each segment's arithmetic mean and standard deviation into log-space parameters. Its feature-selection pipeline uses disjoint history, template-selection, and model-training windows to avoid leaking later prices into earlier decisions.

Wang models market prices with a categorical survival tree and Kaplan?Meier estimates. Winning observations reveal the market price; losing observations are right-censored at the submitted bid. The implementation preserves the distinction between a submitted bid and the market price, and treats equality as a loss (`bid > price`).

Both implementations are prototypes based on the cited papers, with documented adaptations. The saved synthetic evaluation is illustrative and does not reproduce the papers' original datasets. See the [benchmark report](../../docs/benchmark/bid_forecast/bid_forecast_report.md) and [method comparison](../../docs/benchmark/bid_forecast/winning_price_distribution_methods.md) for details.
