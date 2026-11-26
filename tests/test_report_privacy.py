import copy
import json

from benchmarks import report_privacy as privacy


def test_report_pseudonyms_preserve_metrics_identity_and_missing_buckets():
    original = {
        "targets": {"Region": ["700001", "700002", "<other>"]},
        "slices": [{"field": "Device", "value": "VENDOR_TV", "n": 700001,
                    "share": 0.25}],
        "status_counts": {"200": 700001, "204": 12},
    }
    snapshot = copy.deepcopy(original)
    result = privacy.report(original)
    assert original == snapshot
    assert result["targets"]["Region"] == [privacy.tag_label("700001"),
                                            privacy.tag_label("700002"), "<other>"]
    assert result["targets"]["Region"][0] != result["targets"]["Region"][1]
    assert result["slices"][0]["value"] == privacy.tag_label("VENDOR_TV")
    assert result["slices"][0]["n"] == 700001
    assert result["status_counts"] == original["status_counts"]
    assert privacy.report(result) == result


def test_markdown_and_json_use_identical_labels_without_replacing_measurements():
    privacy.register(["VENDOR_TV", "700001"])
    raw = ('| location | requests |\n|---|---|\n| 700001 | 700001 |\n\n'
           'Device=VENDOR_TV; Region:700001; '
           '`{"Region": ["700001"]}`; requests=700001\n')
    result = privacy.markdown(raw)
    assert f'| {privacy.tag_label("700001")} | 700001 |' in result
    assert "Device=" + privacy.tag_label("VENDOR_TV") in result
    assert "Region:" + privacy.tag_label("700001") in result
    assert json.dumps(privacy.report({"Region": ["700001"]})) in result
    assert "requests=700001" in result
    assert privacy.markdown(result) == result


def test_legacy_prepared_vocabulary_keeps_raw_metadata_and_signature():
    from benchmarks.log_benchmark.stream import Prepared

    metadata = {"vocab_order": ["\u0420\u0435\u0433\u0438\u043e\u043d"],
                "vocabs": {"\u0420\u0435\u0433\u0438\u043e\u043d": ["<other>", "700001"]}}
    snapshot = copy.deepcopy(metadata)
    prep = Prepared("unused", metadata, None, None)
    assert prep.vocab_order == ["Region"]
    assert prep.vocabs == {"Region": ["<other>", "700001"]}
    assert prep.meta == snapshot


def test_exported_targets_and_device_pools_replay_with_identical_distribution():
    import numpy as np
    from benchmarks.log_benchmark.stream import Prepared
    from benchmarks.log_benchmark.ads import compute_match_rates, _resolve_report_targets
    from benchmarks.closed_stand.stand import pool_mask_of

    prep = Prepared("unused", {"vocab_order": ["Region", "Device"],
                              "vocabs": {"Region": ["<none>", "700001", "700002"],
                                         "Device": ["<none>", "VENDOR_TV", "VENDOR_WEB"]}},
                    np.array([[1, 1], [1, 2], [2, 1]]), np.array([50, 30, 20]))
    original = [{"id": "campaign", "targets": {"Region": ["700001"]}}]
    exported = privacy.report(original)
    assert compute_match_rates(prep, original) == compute_match_rates(prep, exported) == [0.8]
    assert _resolve_report_targets(prep, exported)[0]["targets"] == original[0]["targets"]
    assert np.array_equal(pool_mask_of(prep, ["VENDOR_TV"]),
                          pool_mask_of(prep, [privacy.tag_label("VENDOR_TV")]))


def test_timezone_and_boolean_metadata_are_not_tag_values():
    privacy.register(["Moscow", "true", "false", "1.0", "0.0", "1e6"])
    original = {"timezone": "Europe/Moscow", "period": "Moscow time",
                "fallback": False, "notes": '{"enabled": true}'}
    assert privacy.report(original) == original
    assert privacy.text("rate=1.0, loss=0.0, count=1e6") == "rate=1.0, loss=0.0, count=1e6"
    assert privacy.report({"client_version": "1.0"}) == {"client_version": privacy.tag_label("1.0")}
    assert privacy.report({"City": ["Moscow"]})["City"] == [privacy.tag_label("Moscow")]


def test_readable_aliases_retain_hardware_types_and_logical_values():
    original = {"Device": ["WEB_BROWSER_A", "ANDROID_TV_A", "ANDROID_SET_TOP_BOX_A", "SET_TOP_BOX_A", "IOS_PHONE_A", "IOS_TABLET_A",
                           "SMART_TV_PLATFORM_A", "SMART_TV_PLATFORM_B"],
                "Child": ["true", "false", True, False], "Age": ["18-24", "55+", "18"],
                "position": ["1", "2", "3"]}
    result = privacy.report(original)
    assert result["Device"] == ["WEB_BROWSER_A", "ANDROID_TV_A", "ANDROID_SET_TOP_BOX_A", "SET_TOP_BOX_A",
                                 "IOS_PHONE_A", "IOS_TABLET_A", "SMART_TV_PLATFORM_A", "SMART_TV_PLATFORM_B"]
    for field in ("Child", "Age", "position"):
        assert result[field] == original[field]
    assert privacy.report(result) == result


def test_numeric_ids_are_different_numeric_labels_without_merging_or_leaking_suffixes():
    originals = ["0", "01", "1", "100001", "700001", "100001001", "2147483647"]
    labels = [privacy.tag_label(v, "Region") for v in originals]
    assert all(v.isdigit() for v in labels)
    assert len(set(labels)) == len(originals)
    assert set(labels).isdisjoint(originals)
    assert all(not alias.endswith(raw) for raw, alias in zip(originals[3:], labels[3:]))
    assert [privacy.tag_label(v, "Region") for v in labels] == labels


def test_new_and_legacy_exported_target_ids_both_replay():
    import numpy as np
    from benchmarks.log_benchmark.stream import Prepared
    from benchmarks.log_benchmark.ads import compute_match_rates

    prep = Prepared("unused", {"vocab_order": ["Region"], "vocabs": {"Region": ["<none>", "700001"]}},
                    np.array([[1]]), np.array([50]))
    for value in (privacy.tag_label("700001"), privacy.legacy_label("700001")):
        assert compute_match_rates(prep, [{"id": "campaign", "targets": {"Region": [value]}}]) == [1.0]


def test_campaign_export_sanitizes_calibration_history_and_preserves_references():
    original = {
        "meta": {"selected_changes": [{"campaign": "seller_alpha", "vocab": "Device",
                                         "tag": "VENDOR_TV", "match_gain": 0.25}],
                 "campaigns": [{"id": "seller_alpha", "coverage": 0.5}]},
        "ads": [{"id": "seller_alpha", "targets": {"Device": ["VENDOR_TV"]},
                 "cpm": 100, "user_frequency_limit": {"d": 4}}],
    }
    snapshot = copy.deepcopy(original)
    exported = privacy.campaign_config(original)
    change = exported["meta"]["selected_changes"][0]
    assert change["tag"] == exported["ads"][0]["targets"]["Device"][0]
    assert change["campaign"] == exported["ads"][0]["id"]
    assert exported["meta"]["campaigns"][0]["id"] == change["campaign"]
    assert change["match_gain"] == 0.25
    assert exported["ads"][0]["user_frequency_limit"] == {"d": 4}
    assert original == snapshot
    assert privacy.campaign_config(exported) == exported


def test_prose_preserves_field_mappings_and_parentheses_around_flags():
    assert privacy.text("(Region=location, Device=device_type)") == "(Region=location, Device=device_type)"
    assert privacy.text("child content (is_child=true)") == "child content (is_child=true)"


def test_checked_in_campaign_configs_are_sanitized():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "benchmarks"
    paths = [*root.glob("closed_stand/manager*.json"), *root.glob("log_benchmark/ads*.json")]
    assert paths
    for path in paths:
        config = json.loads(path.read_text(encoding="utf-8"))
        assert privacy.campaign_config(config) == config, str(path)
