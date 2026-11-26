# Local sources and public examples

The SDK, benchmark engines and example generators use neutral device names.
Source-specific vocabularies, raw-log parsers and original datasets are local
inputs and are excluded from Git.

Public examples generate deterministic synthetic data automatically. They need
no private source adapter:

```bash
PYTHONPATH=src:. python -m examples.temporal_balancer.01_context
PYTHONPATH=src:. python -m examples.temporal_balancer.02_balance
PYTHONPATH=src:. python -m examples.simulation.full_cycle_from_json
PYTHONPATH=src:. python -m examples.simulation.full_cycle_with_report
```

Generated sample data lives in `examples/generated_samples/`. Simulation reports
in `examples/simulation/report/` are also ignored. Original example requests and
CSV logs at their old paths remain local files; the public examples use the
synthetic inputs instead.

For private log preparation, install local adapter files in
`.local/source_adapters/`, or set `AUCTION_SOURCE_ADAPTERS` to a directory outside
the repository. The supported entry points are:

| Public command | Local implementation |
| --- | --- |
| `python benchmarks/log_benchmark/prepare_logs.py` | `prepare_benchmark.py` |
| `python benchmarks/manager_eda/prepare.py` | `prepare_eda.py` |
| `python examples/temporal_balancer/prepare_logs.py` | `prepare_temporal.py` |

The wrappers preserve command-line arguments. Adapter files implement their own
CLI and source schema. They are trusted local Python code. If an adapter is
missing, its wrapper reports how to configure it; other modules still import
and run. The raw-log integration test is skipped when its adapter is absent.

Optional `device_aliases.json` in the same directory maps source device names to
public names. For example:

```json
{"vendor_browser": "WEB_BROWSER_A", "vendor_tv": "SMART_TV_PLATFORM_A"}
```

Additional source labels (such as client versions) can be mapped in
`label_aliases.json` using the same format. Reports use these aliases; campaign targeting and device pools resolve aliases
against prepared vocabularies. Existing raw prepared data and EDA caches remain
usable with their local alias mapping. Raw logs, prepared arrays and caches
belong in the already ignored `benchmarks/logs/` and cache directories.

Removing files from the current Git index does not remove them from earlier
commits. This separation changes the current tree; rewriting published Git
history is a separate operation.
