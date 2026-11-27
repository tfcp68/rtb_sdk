# Bid forecast benchmark

Research prototypes for estimating campaign bid landscapes and market-price distributions. The implementations of Cui (2011) and Wang (2016) are exploratory and are not part of the production auction path.

## Findings and artifacts

- [Evaluation report](bid_forecast_report.md): problem setup and conclusions.
- [Method comparison](winning_price_distribution_methods.md): assumptions and model details.
- [`results/synthetic.md`](results/synthetic.md): deterministic synthetic comparison of both papers' methods.
- [`results/price/results.md`](results/price/results.md): price and win-probability evaluation across three seeds.
- [`results/stand_logs/results.md`](results/stand_logs/results.md): evaluation on closed-stand response logs. These logs do not contain valid market-price labels.
- `results/` also contains the JSON inputs and provenance for saved runs.

The synthetic data is illustrative; it is not a reproduction of the papers' original experiments. Stand responses (200/204) describe simulated seller feedback, not clearing prices. See each report for its scope and limitations.

## Reproducing runs

Run the prototype commands from the repository root; see [`benchmarks/bid_forecast_benchmark/README.md`](../../../benchmarks/bid_forecast_benchmark/README.md). Runners save results here by default. Keep each run in a separate output directory when a runner refuses to overwrite existing files.
