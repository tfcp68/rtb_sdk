import json

import numpy as np
import pytest

from benchmarks.closed_stand.reconstruction import (
    CooldownReconstructor, Rule, RuleReconstructor, compare_targeting, response_metrics,
)


def test_dnf_recovers_disjoint_conjunctions_without_winner_labels():
    profiles = np.array([(a, b, c) for a in range(1, 4) for b in range(1, 4) for c in range(1, 4)])
    tags = np.repeat(profiles, 30, axis=0)
    y = ((tags[:, 0] == 1) & (tags[:, 1] == 2)) | ((tags[:, 0] == 3) & (tags[:, 2] == 1))
    single = RuleReconstructor(depth=1, min_support=20).fit(tags, y)
    model = RuleReconstructor(depth=2, min_support=20).fit(tags, y)
    assert len(model.rules) == 2
    assert {rule.terms for rule in model.rules} == {((0, 1), (1, 2)), ((0, 3), (2, 1))}
    assert response_metrics(y, model.predict(tags))["brier"] < response_metrics(y, single.predict(tags))["brier"]
    actual = [rule.mask(profiles) for rule in model.rules]
    comparison = compare_targeting(model.rules, profiles, np.ones(len(profiles)), actual, ["a", "b"])
    assert comparison["campaign_recall"] == 1
    assert comparison["union_iou"] == 1


def test_empty_signal_and_repeated_fit_do_not_invent_campaigns():
    tags = np.ones((100, 2), dtype=int)
    model = RuleReconstructor().fit(tags, np.ones(100))
    assert len(model.rules) == 1 and model.rules[0].terms == ()
    model.fit(tags, np.zeros(100))
    assert model.rules == []
    assert np.all(model.predict(tags) < 0.5)
    with pytest.raises(ValueError, match="Empty"):
        model.fit(tags[:0], np.zeros(0))


def test_multivalue_merge_recovers_channel_list_and_preserves_union():
    profiles = np.array([[1], [2], [3], [4], [5]])
    tags = np.repeat(profiles, 100, axis=0)
    y = tags[:, 0] < 4
    plain = RuleReconstructor(depth=1).fit(tags, y)
    merged = RuleReconstructor(depth=2, merge_probability=0.04).fit(tags, y)
    assert len(plain.rules) == 3
    assert len(merged.rules) == 1
    assert merged.rules[0].terms == ((0, (1, 2, 3)),)
    assert merged.rules[0].support == merged.rules[0].successes == 300
    assert merged.rules[0].mask(profiles).tolist() == [True, True, True, False, False]
    assert merged.rules[0].export(["channel"], {"channel": ["none", "a", "b", "c", "d", "e"]})["targets"] == {
        "channel": ["a", "b", "c"]}


def test_one_to_one_matching_does_not_reward_duplicate_hypotheses():
    profiles = np.array([[1], [2], [3]])
    rules = [Rule(((0, 1),), 0.9, 100, 90)] * 2
    actual = [np.array([True, False, False]), np.array([False, True, False])]
    result = compare_targeting(rules, profiles, np.array([90, 9, 1]), actual, ["one", "two"])
    assert result["campaign_precision"] == result["campaign_recall"] == 0.5
    assert result["union_iou"] == pytest.approx(90 / 99)


def test_fsm_prediction_is_causal_and_observes_only_past_answers():
    # Fixed learned rule isolates READY/BLOCKED semantics from search noise.
    model = CooldownReconstructor()
    model.rules = [Rule(((0, 1),), 0.9, 100, 90, cooldown=120)]
    model.background = 0.1
    tags = np.ones((4, 1), dtype=int)
    ts, user = np.array([0, 30, 120, 150]), np.array([7, 7, 7, 8])
    y = np.array([1, 0, 1, 1])
    first = model.predict(tags, ts, user, y)
    second = model.predict(tags, ts, user, np.array([1, 1, 0, 0]))
    assert first.tolist() == pytest.approx([0.9, 0.02, 0.9, 0.9])
    assert np.array_equal(first[:3], second[:3])
    # User 8 has independent state.
    assert first[-1] == 0.9


def test_cooldown_selection_uses_train_and_improves_repeated_user_predictions():
    ts = np.arange(0, 6000, 30)
    tags = np.ones((len(ts), 1), dtype=int)
    user = np.ones(len(ts), dtype=int)
    y = np.arange(len(ts)) % 4 == 0
    # Low penalty lets the noisy aggregate support survive the rule search.
    model = CooldownReconstructor(negative_penalty=0.1).fit(tags, y, ts, user)
    assert model.selected_cooldown == 120
    assert response_metrics(y, model.predict(tags, ts, user, y))["brier"] < 0.19


def test_benchmark_artifacts_replay_and_hidden_truth_separation(tmp_path):
    from benchmarks.closed_stand import benchmark_reconstruction as bench

    prepared = tmp_path / "prepared"
    prepared.mkdir()
    meta = dict(vocab_order=["Device", "Region"], t0=0,
                vocabs={"Device": ["none", "ANDROID_TV_A"], "Region": ["none", "A", "B"]},
                days=[{"name": str(day)} for day in range(3)])
    (prepared / "meta.json").write_text(json.dumps(meta))
    np.save(prepared / "combos.npy", np.array([[1, 1], [1, 2]], dtype=np.uint16))
    np.save(prepared / "combo_counts.npy", np.array([150, 150]))
    for day in range(3):
        np.save(prepared / f"{day}_ts.npy", np.arange(100) * 60 + day * 86400)
        np.save(prepared / f"{day}_user.npy", np.arange(100, dtype=np.uint32))
        np.save(prepared / f"{day}_combo.npy", np.arange(100) % 2)
    ads = tmp_path / "manager.json"
    ads.write_text(json.dumps([dict(id="secret", name="Secret", cpm=100, priority=1, limits="none",
                                   targets={"Region": ["A"]}, min_interval=120)]))
    args = bench.parser().parse_args([
        "--name", "case", "--prepared", str(prepared), "--manager-ads", str(ads),
        "--output-root", str(tmp_path / "out"), "--days", "0:3", "--split-day", "2",
        "--sample", "1", "--q", "1", "--min-support", "5",
    ])
    report = bench.run(args)
    assert report["train_n"] == 200 and report["test_n"] == 100
    assert report["truth"][0]["train_impressions"] == 100
    assert report["truth"][0]["test_impressions"] == 50
    for result in report["algorithms"].values():
        assert result["targeting"]["union_iou"] == 1
    observed = bench.pl.read_parquet(tmp_path / "out/case/observations.parquet")
    assert "winner" not in observed.columns and "winner_index" not in observed.columns
    prediction = bench.pl.read_parquet(tmp_path / "out/case/test_predictions.parquet")
    assert prediction.height == 100
    assert set(report["algorithms"]) == {"single_feature", "dnf_beam", "dnf_cooldown_fsm", "dnf_validated", "motif_noisy_or"}
    with pytest.raises(FileExistsError):
        bench.run(args)
