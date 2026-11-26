import json

import pytest

from benchmarks.source_adapters import device_aliases, run_adapter
from examples.sample_data import generate_samples


def test_optional_aliases_and_adapter_have_no_required_private_dependency(tmp_path, monkeypatch):
    monkeypatch.setenv("AUCTION_SOURCE_ADAPTERS", str(tmp_path))
    assert device_aliases() == {}
    with pytest.raises(SystemExit, match="Local source adapter is unavailable"):
        run_adapter("prepare_benchmark")
    (tmp_path / "device_aliases.json").write_text(json.dumps({"vendor_browser": "WEB_BROWSER_A"}))
    assert device_aliases() == {"vendor_browser": "WEB_BROWSER_A"}
    (tmp_path / "device_aliases.json").write_text('["invalid"]')
    with pytest.raises(ValueError, match="Expected a mapping"):
        device_aliases()


def test_synthetic_inputs_work_with_sdk_loaders_and_temporal_context(tmp_path):
    from rtb_sdk.auction.helpers import load_ads_from_json, load_requests_from_json, load_vocabs_from_json
    from rtb_sdk.helpers import get_ads_dict, get_request_user_id, get_target_vector_dict
    from rtb_sdk.balancer.seasonal import HistoricalLogsConfig, build_seasonal_context
    from examples.temporal_balancer.fixtures import ADS, PERIOD, TAG_COL_MAP

    generate_samples(tmp_path, count=120)
    requests = load_requests_from_json(str(tmp_path / "filtered_requests.json"))
    ads = load_ads_from_json(str(tmp_path / "filtered_ads.json"))
    vocabs = load_vocabs_from_json(str(tmp_path / "vocab.json"))
    assert len(requests) == 120
    assert len({get_request_user_id(r) for r in requests}) == 120
    assert len(get_ads_dict(ads)) == 3
    assert "WEB_BROWSER_A" in get_target_vector_dict(vocabs)["device_type"]
    context = build_seasonal_context(HistoricalLogsConfig(
        path=str(tmp_path / "logs.csv"), timestamp_col="ts", user_id_col="user_id",
        aggregation_mode="hour_of_day", timezone="UTC"), ADS, PERIOD, tag_col_map=TAG_COL_MAP)
    assert set(context["context"]) == set(range(24))


def test_public_labels_work_without_local_aliases(tmp_path):
    import os
    import subprocess
    import sys

    subprocess.run([sys.executable, "-c", "\n".join([
        "from benchmarks.report_labels import label",
        "from benchmarks.closed_stand.stand import POOL_DEVICES",
        "from benchmarks.manager_eda.config import ALL_DEVICES",
        "assert label('WEB_BROWSER_A', 'Device') == 'WEB_BROWSER_A'",
        "assert 'ANDROID_TV_A' in POOL_DEVICES",
        "assert 'WEB_BROWSER_A' in ALL_DEVICES",
    ])], env={**os.environ, "AUCTION_SOURCE_ADAPTERS": str(tmp_path)}, check=True)
