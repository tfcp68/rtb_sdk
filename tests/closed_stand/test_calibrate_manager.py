import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "benchmarks" / "closed_stand"))
import stand  # adds log_benchmark to the import path
from ads import build_pack
from calibrate_manager import loss, next_weights, scale_frequency_limits
from calibrate_targeting import proposals


def test_volume_weights_change_allocation_without_changing_total():
    prep = SimpleNamespace(vocab_order=["Device"], vocabs={"Device": ["<none>", "A"]},
                           combo_counts=np.array([100]), combos=np.array([[1]]))
    ads = [dict(id="a", cpm=100, priority=1, targets={}), dict(id="b", cpm=100, priority=1, targets={})]
    before = build_pack(prep, ads, 100, 1)
    ads[0]["volume_weight"] = 3
    after = build_pack(prep, ads, 100, 1)
    assert before.volume == [65, 65]
    assert after.volume == [98, 32]
    ads[0]["volume_weight"] = -1
    with pytest.raises(ValueError):
        build_pack(prep, ads, 100, 1)


def test_calibration_reduces_weight_for_underdelivery_and_is_bounded():
    ads = [{"id": "a"}, {"id": "b"}]
    result = {"hidden_manager": [{"id": "a", "volume": 100, "impressions": 10},
                                 {"id": "b", "volume": 100, "impressions": 60}]}
    updated = next_weights(ads, result, 0.6, 1, 0.25, 4)
    assert updated[0]["volume_weight"] == 0.25
    assert updated[1]["volume_weight"] == 1
    assert "volume_weight" not in ads[0]
    assert loss(result, 0.6) == 0.25


def test_frequency_scaling_preserves_unlimited_windows_and_interval():
    ads = [{"id": "a", "limits": "tight", "ad_frequency_limit": {"h": 7, "d": 0},
            "user_frequency_limit": {"d": 5, "w": 18, "h": 1}, "min_interval": 45},
           {"id": "b", "limits": "none"}]
    changed = scale_frequency_limits(ads, 1.25, 1.5)
    assert changed[0]["ad_limits_rel"]["h"] == 1.5 * 1.25
    assert changed[0]["ad_frequency_limit"] == {"h": 8, "d": 0}
    assert changed[0]["user_frequency_limit"] == {"d": 7, "w": 27, "h": 1}
    assert changed[0]["min_interval"] == 45
    assert "ad_limits_rel" not in changed[1]
    assert "ad_limits_rel" not in ads[0]


def test_targeting_proposals_respect_pool_and_rank_added_coverage():
    prep = SimpleNamespace(vocab_order=["Device"],
                           vocabs={"Device": ["<none>", "<other>", "STB", "TV", "WEB"]},
                           combos=np.array([[2], [3], [4]]), combo_counts=np.array([10, 20, 100]))
    ads = [{"id": "a", "targets": {"Device": ["STB"]}}]
    choices = proposals(prep, ads, {"STB", "TV"}, 4, 5)
    assert len(choices) == 1
    assert choices[0][1:] == (0, "Device", "TV")
    assert choices[0][0] == pytest.approx(20 / 130)
    assert ads[0]["targets"]["Device"] == ["STB"]
    from benchmarks import report_privacy as privacy

    assert proposals(prep, privacy.campaign_config(ads),
                     {privacy.tag_label(v, "Device") for v in ("STB", "TV")}, 4, 5) == choices
