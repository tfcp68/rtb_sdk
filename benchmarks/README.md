# Benchmark runners

Saved results and their interpretation are in the
[benchmark index](../docs/benchmark/README.md). This directory contains the
runners, simulator engines and campaign configurations.

| Runner | Purpose | Default report location |
| --- | --- | --- |
| `run_benchmark.py` | Synthetic comparison of classic auctions, hybrids, balancer allocation and AdWords A2/A3. | `docs/benchmark/auction/synthetic/` |
| `run_benchmark_quick.py` | Reduced synthetic matrix with 10k/100k requests. | `docs/benchmark/auction/synthetic/` |
| [log_benchmark](log_benchmark/README.md) | Replay prepared traffic with the full filter chain. | `docs/benchmark/auction/log_replay/` |
| [closed_stand](closed_stand/README.md) | Compare routing policies against a simulated closed manager. | `docs/benchmark/manager_routing/runs/` |
| [Probability evaluation](closed_stand/PROBABILITY_GUIDE.md) | Evaluate response probability, calibration and quota ranking in simulator/historical modes. | `docs/benchmark/manager_routing/runs/probability/` |
| [Campaign reconstruction](closed_stand/RECONSTRUCTION.md) | Infer synthetic hidden campaign targeting from response feedback. | `docs/benchmark/manager_routing/runs/reconstruction/` |
| `manager_eda/eda_manager.py`, `eda_relations.py` | Analyze incoming traffic and categorical dependencies. | `docs/benchmark/manager_traffic/reports/` |
| `manager_eda/oracle_bounds.py` | Compute modeled routing ceilings. | `docs/benchmark/manager_traffic/analysis/` |

For a public synthetic check without source data:

```bash
python benchmarks/run_benchmark_quick.py --companies 3 --traffic balanced --runs 2 --dry-run
```

Omit `--dry-run` to execute it. Use the runners' output options for a separate
report destination. Private raw-log preparation is an optional local integration;
see [local sources](../docs/local_sources.md).
