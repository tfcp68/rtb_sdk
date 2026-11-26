# RTB SDK

A Python SDK for Real-Time Bidding: traffic forecasting, parameter optimization, ad selection, and traffic allocation across campaigns.

## Requirements

- Python 3.12 or newer
- Git

## Installation

### Install directly from GitHub (recommended)

```bash
pip install git+https://github.com/tfcp68/rtb_sdk.git
```

A specific branch or tag:

```bash
pip install git+https://github.com/tfcp68/rtb_sdk.git@main
pip install git+https://github.com/tfcp68/rtb_sdk.git@v1.0.0
```

> **Note:** the `prophet` dependency requires a C++ compiler and may take several minutes to install.

---

### Install from a local clone (for development)

#### 1. Clone the repository

```bash
git clone https://github.com/tfcp68/rtb_sdk.git
cd rtb_sdk
```

#### 2. (Optional) create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\activate         # Windows
```

#### 3. Install the library

For use without running the tests:

```bash
pip install .
```

For development and running the tests (includes `pytest`, `pytest-describe`, `pytest-rich`):

```bash
pip install -e ".[dev]"
```

## Verifying the installation

After installation, run the tests to make sure all modules work correctly:

```bash
pytest tests/
```

To check a specific module:

```bash
pytest tests/predictor/
pytest tests/optimizer/
pytest tests/auction/
pytest tests/adwords/
pytest tests/balancer/
```

The repository's [pytest.ini](pytest.ini) configures the source and test import paths and excludes temporary directories. Run these commands from the repository root. Tests for private log preparation are skipped when the local source adapter is unavailable; see [local sources](docs/local_sources.md).

## Module structure

| Module | Purpose | What it does |
|---|---|---|
| [Predictor](src/rtb_sdk/predictor/README.md) | Forecast traffic over time | Fits time-series models, predicts future traffic, evaluates forecast quality, and exports reports. |
| [Optimizer](src/rtb_sdk/optimizer/README.md) | Search for good parameter settings | Generates candidate parameter combinations, evaluates an objective, and iterates with grid search or a genetic algorithm. |
| [Auction](src/rtb_sdk/auction/README.md) | Select an ad for an incoming request | Ranks eligible campaigns by price, delivery pace, priority, or a combined score; supports deterministic and randomized selection. |
| [AdWords](src/rtb_sdk/auction/adwords/README.md) | Allocate impressions using online matching | Implements A2/A3 algorithms with persistent allocation state and budget-aware decisions. |
| [Simulation](src/rtb_sdk/auction/simulation/README.md) | Replay a request stream | Applies targeting and frequency filters, updates impression statistics, and produces delivery reports. |
| [Balancer](src/rtb_sdk/balancer/README.md) | Plan traffic allocation across campaigns | Optimizes campaign volumes or sellout, adds campaigns, estimates redistribution, and accounts for seasonal traffic and frequency limits. |

## Benchmarks and research

The [benchmark index](docs/benchmark/README.md) explains each experiment, its findings, limitations, and where to find the reports, tables, and plots. Benchmark runners remain in [benchmarks/](benchmarks/README.md); saved results live in `docs/benchmark/`.

## Usage examples

```bash
python examples/predictor/full_cycle_core.py
python examples/predictor/full_cycle_core_and_serialization.py
```
