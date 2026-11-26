import itertools
from types import SimpleNamespace

import numpy as np
import pytest

from benchmarks.closed_stand.generate_reconstruction_campaigns import generate_campaigns, from_prepared
from benchmarks.closed_stand.reconstruction import MotifReconstructor, ValidatedRuleReconstructor, Rule, RuleReconstructor, response_metrics


def domain():
    profiles = np.array(list(itertools.product(range(1, 6), repeat=3)))
    order = ["device", "region", "channel"]
    vocabs = {field: ["none"] + [str(v) for v in range(1, 6)] for field in order}
    return profiles, order, vocabs


def test_generator_is_reproducible_bounded_and_diverse():
    profiles, order, vocabs = domain()
    kwargs = dict(profiles=profiles, weights=np.arange(1, len(profiles) + 1), order=order, vocabs=vocabs)
    result = generate_campaigns(**kwargs)
    assert result == generate_campaigns(**kwargs)
    assert result != generate_campaigns(**kwargs, seed=43)
    assert len(result["ads"]) == 8
    assert result["meta"]["union_coverage"] <= 0.85
    assert all(d["exclusive_coverage"] >= 0.10 * d["coverage"] for d in result["meta"]["campaigns"])
    assert {len(ad["targets"]) for ad in result["ads"]} == {1, 2, 3}
    masks = []
    weights = kwargs["weights"] / kwargs["weights"].sum()
    for ad in result["ads"]:
        assert ad["limits"] == "none" and ad["min_interval"] == 0
        terms = tuple((order.index(f), tuple(int(v) for v in values)) for f, values in ad["targets"].items())
        mask = Rule(terms, 0, 0, 0).mask(profiles)
        assert 0.025 <= weights[mask].sum() <= 0.20
        for old in masks:
            assert weights[old & mask].sum() / weights[old | mask].sum() <= 0.60
        masks.append(mask)
    dynamic = generate_campaigns(**kwargs, scenario="dynamic")
    assert [a["targets"] for a in dynamic["ads"]] == [a["targets"] for a in result["ads"]]
    assert any(ad["min_interval"] > 0 for ad in dynamic["ads"])


def test_generator_fails_instead_of_falling_back_to_universal_campaign():
    with pytest.raises(ValueError, match="Could generate only"):
        generate_campaigns(np.ones((1, 2), dtype=int), [100], ["a", "b"],
                           {"a": ["none", "x"], "b": ["none", "x"]}, count=2)


def test_generator_counts_only_requested_training_traffic(monkeypatch):
    from benchmarks.closed_stand import stand
    profiles, order, vocabs = domain()
    prep = SimpleNamespace(combos=profiles, vocab_order=order, vocabs=vocabs)
    requested = []

    def chunks(prepared, days, sample):
        requested.append((days, sample))
        yield 0, None, None, np.tile(np.arange(len(profiles)), 3)

    monkeypatch.setattr(stand, "iter_chunks", chunks)
    monkeypatch.setattr(stand, "pool_mask_of", lambda *_: np.ones(len(profiles), dtype=bool))
    monkeypatch.setattr(stand, "prepared_signature", lambda _: "test")
    result, counts = from_prepared(prep, (1, 3), 0.2, ["test"])
    assert requested == [((1, 3), 0.2)]
    assert counts.tolist() == [3] * len(profiles)
    assert result["meta"]["training_days"] == [1, 3]


def test_motifs_recover_noisy_overlapping_multivalue_targets_on_heldout_responses():
    profiles = np.array(list(itertools.product(range(1, 5), repeat=3)))
    tags = np.repeat(profiles, 400, axis=0)
    a = (tags[:, 0] == 1) & np.isin(tags[:, 1], [1, 2])
    b = (tags[:, 1] == 2) & (tags[:, 2] == 3)
    probability = 1 - (1 - 0.015) * (1 - 0.45 * a) * (1 - 0.60 * b)
    rng = np.random.default_rng(7)
    train = rng.random(len(tags)) < probability
    test = rng.random(len(tags)) < probability
    model = MotifReconstructor(depth=3, min_support=50).fit(tags, train)
    baseline = RuleReconstructor(depth=3, min_support=50).fit(tags, train)
    assert {r.terms for r in model.rules} == {((0, 1), (1, (1, 2))), ((1, 2), (2, 3))}
    assert response_metrics(test, model.predict(tags))["brier"] < response_metrics(test, baseline.predict(tags))["brier"] * 0.75
    # No test response is required or consulted by the static model.
    assert np.array_equal(model.predict(tags, observed=test), model.predict(tags, observed=~test))
    assert np.mean((model.predict(tags) - probability) ** 2) < 0.001
    model.fit(tags, np.zeros(len(tags)))
    assert not model.rules
    assert np.all(model.predict(tags) < 0.01)
    with pytest.raises(ValueError, match="Empty"):
        model.fit(tags[:0], train[:0])


def test_validation_recovers_low_rate_signal_and_keeps_test_out_of_tuning():
    rng = np.random.default_rng(43)
    tags = rng.integers(1, 3, size=(12000, 1))
    y = rng.random(len(tags)) < np.where(tags[:, 0] == 1, 0.35, 0.01)
    train = np.arange(8000)
    model = ValidatedRuleReconstructor(depth=1).fit(tags[train], y[train], train)
    baseline = RuleReconstructor(depth=1).fit(tags[train], y[train])
    assert model.selected_negative_penalty < 2
    assert model.rules and not baseline.rules
    assert response_metrics(y[8000:], model.predict(tags[8000:]))["brier"] < response_metrics(y[8000:], baseline.predict(tags[8000:]))["brier"]
    with pytest.raises(ValueError, match="chronological"):
        model.fit(tags[train], y[train], train[::-1])
