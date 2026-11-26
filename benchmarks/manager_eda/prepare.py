"""Optional local source preparation; see docs/local_sources.md."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from benchmarks.source_adapters import run_adapter

if __name__ == "__main__":
    run_adapter('prepare_eda')
