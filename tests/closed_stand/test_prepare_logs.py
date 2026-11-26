import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from benchmarks.source_adapters import adapter_directory

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq


def test_combined_parquet_preparation_keeps_status_and_moscow_days(tmp_path):
    if not (adapter_directory() / "prepare_benchmark.py").is_file():
        pytest.skip("Optional local source adapter is not installed")
    source = tmp_path / "source.parquet"
    out = tmp_path / "out"
    dt = pa.array([datetime(2026, 10, 12, 21, 0, tzinfo=timezone.utc),
                   datetime(2026, 10, 11, 21, 1, tzinfo=timezone.utc),
                   datetime(2026, 10, 11, 21, 0, tzinfo=timezone.utc)], type=pa.timestamp("ms", tz="UTC"))
    pq.write_table(pa.table({"datetime": dt, "path": ["/?client_id=a&device_type=SET_TOP_BOX_A",
                   "/?client_id=b&device_type=SET_TOP_BOX_A", "/?device_type=WEB_BROWSER_A"],
                   "status": pa.array([204, 200, 204], type=pa.uint16())}), source)
    script = Path(__file__).resolve().parents[2] / "benchmarks/log_benchmark/prepare_logs.py"
    subprocess.run([sys.executable, str(script), "--source", str(source), "--out", str(out), "--workers", "1"], check=True)
    meta = json.loads((out / "meta.json").read_text())
    assert len(meta["days"]) == 2
    assert meta["days"][0]["missing_users"] == 1
    assert np.load(out / "day_00_ts.npy").tolist() == [0, 60]
    assert np.load(out / "day_00_status.npy").tolist() == [204, 200]
    assert np.load(out / "day_01_ts.npy").tolist() == [86400]
    assert np.load(out / "day_01_status.npy").tolist() == [204]
