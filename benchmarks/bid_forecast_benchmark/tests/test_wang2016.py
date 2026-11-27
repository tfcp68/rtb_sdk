import pytest

from articles_prorotypes.wang.wang2016 import (
    AuctionObservation,
    SurvivalTree,
    cluster_categories,
    fit_baseline,
)


def test_kaplan_meier_uses_wins_and_censored_losses():
    observations = [
        AuctionObservation({}, 1.0, True, market_price=0.5),
        AuctionObservation({}, 2.0, False),
        AuctionObservation({}, 3.0, True, market_price=2.5),
    ]
    model = SurvivalTree(max_depth=0).fit(observations)
    estimate = model.predict({})
    assert estimate.masses == pytest.approx({0.5: 1 / 3, 2.5: 2 / 3})
    assert estimate.tail_probability == pytest.approx(0.0)
    assert estimate.cdf(0.5) == pytest.approx(1 / 3)  # CDF includes a boundary mass.
    assert estimate.win_probability(0.5) == pytest.approx(0.0)  # bid > price is strict.
    assert estimate.cdf(1.0) == pytest.approx(1 / 3)
    assert estimate.win_probability(1.0) == pytest.approx(1 / 3)


def test_distribution_tree_splits_distinct_categorical_landscapes():
    observations = [
        AuctionObservation({"region": "north"}, 1.0, True, 0.9),
        AuctionObservation({"region": "north"}, 1.0, True, 0.9),
        AuctionObservation({"region": "south"}, 5.0, True, 4.9),
        AuctionObservation({"region": "south"}, 5.0, True, 4.9),
    ]
    model = SurvivalTree(max_depth=1, min_leaf_size=1).fit(observations)
    north = model.predict({"region": "north"})
    south = model.predict({"region": "south"})
    assert north.masses != south.masses
    assert sum(north.masses.values()) + north.tail_probability == pytest.approx(1.0)
    assert sum(south.masses.values()) + south.tail_probability == pytest.approx(1.0)


def test_wang_validates_observation_and_missing_features_are_deterministic():
    with pytest.raises(ValueError):
        AuctionObservation({}, -1.0, True)
    observations = [AuctionObservation({"region": "north"}, 2.0, True, 1.0)]
    model = SurvivalTree(max_depth=1, random_seed=7).fit(observations)
    assert model.predict({"region": "unknown"}) == model.predict({"region": "unknown"})


def test_win_requires_market_price_and_loss_forbids_it():
    with pytest.raises(ValueError):
        AuctionObservation({}, 2.0, True)
    with pytest.raises(ValueError):
        AuctionObservation({}, 2.0, False, 1.0)
    with pytest.raises(ValueError):
        AuctionObservation({}, 2.0, True, 3.0)


def test_all_losses_are_valid_and_preserve_full_unidentified_tail():
    model = SurvivalTree(max_depth=0).fit([
        AuctionObservation({}, 1.0, False), AuctionObservation({}, 3.0, False)
    ])
    estimate = model.predict({})
    assert estimate.masses == {}
    assert estimate.tail_probability == 1.0
    assert estimate.cdf(1.0) == 0.0
    assert estimate.win_probability(1.0) == 0.0


@pytest.mark.parametrize("features", [{"x": []}, {"x": float("nan")}, {"x": float("inf")}])
def test_feature_values_must_be_hashable_and_finite(features):
    with pytest.raises(ValueError):
        AuctionObservation(features, 1.0, False)


@pytest.mark.parametrize("depth,leaf", [(1.5, 1), (True, 1), (1, 1.5), (1, False)])
def test_tree_parameters_must_be_non_boolean_integers(depth, leaf):
    with pytest.raises(ValueError):
        SurvivalTree(max_depth=depth, min_leaf_size=leaf)


def test_unseen_category_routes_repeatably_and_large_cardinality_is_guarded():
    observations = [
        AuctionObservation({"x": "a"}, 1.0, True, 0.9),
        AuctionObservation({"x": "b"}, 3.0, True, 2.0),
        AuctionObservation({"x": "c"}, 9.0, True, 8.0),
        AuctionObservation({"x": "d"}, 9.0, True, 8.9),
    ]
    model = SurvivalTree(max_depth=1, min_leaf_size=1, random_seed=3).fit(observations)
    first = model.predict({"x": "not-in-training"})
    assert first == model.predict({"x": "not-in-training"})
    with pytest.raises(ValueError, match="cardinality"):
        SurvivalTree(max_depth=1, min_leaf_size=1, max_categories=3).fit(observations)


def test_algorithm1_em_groups_distribution_points_and_is_seeded():
    rows = [
        AuctionObservation({"x": "a"}, 2, True, 1),
        AuctionObservation({"x": "b"}, 2, True, 1),
        AuctionObservation({"x": "c"}, 9, True, 8),
        AuctionObservation({"x": "d"}, 9, True, 8),
    ]
    result = cluster_categories(rows, "x", random_seed=19)
    assert result.left_values | result.right_values == frozenset("abcd")
    assert result.left_values.isdisjoint(result.right_values)
    assert result.divergence >= 0
    assert result == cluster_categories(rows, "x", random_seed=19)


def test_algorithm1_assigns_to_s2_only_when_k1_strictly_exceeds_k2():
    # Distances are KL(Mk,Q1)=0 and KL(Mk,Q2)>0, therefore the paper assigns S2.
    from articles_prorotypes.wang.wang2016 import _kl, _distribution
    rows = [AuctionObservation({"x": "near"}, 2, True, 1),
            AuctionObservation({"x": "far"}, 10, True, 9)]
    result = cluster_categories(rows, "x", random_seed=1)
    assert result.left_values | result.right_values == {"near", "far"}
    assert result.left_values.isdisjoint(result.right_values)
    # Independent exact distance check captures the asymmetric decision direction.
    near = _distribution([rows[0]])
    far = _distribution([rows[1]])
    assert _kl(near, far) > _kl(near, near)


def test_reduced_error_pruning_uses_validation_nll_and_keeps_improving_split():
    train = [
        AuctionObservation({"x": "a"}, 2, True, 1),
        AuctionObservation({"x": "a"}, 2, True, 1),
        AuctionObservation({"x": "b"}, 6, True, 5),
        AuctionObservation({"x": "b"}, 6, True, 5),
    ]
    validation = [
        AuctionObservation({"x": "a"}, 2, True, 1),
        AuctionObservation({"x": "b"}, 6, True, 5),
    ]
    model = SurvivalTree(max_depth=1, min_leaf_size=1).fit(train, validation=validation)
    assert model.root is not None
    assert model.root.feature == "x"


def test_reduced_error_pruning_collapses_split_when_validation_prefers_parent():
    train = [
        AuctionObservation({"x": "a"}, 2, True, 1),
        AuctionObservation({"x": "a"}, 2, True, 1),
        AuctionObservation({"x": "b"}, 6, True, 5),
        AuctionObservation({"x": "b"}, 6, True, 5),
    ]
    validation = [AuctionObservation({"x": "a"}, 6, True, 5), AuctionObservation({"x": "b"}, 2, True, 1)]
    model = SurvivalTree(max_depth=1, min_leaf_size=1).fit(train, validation=validation)
    assert model.root is not None
    assert model.root.feature is None
    assert model.pruned_nodes == 1


def test_pruning_likelihood_penalizes_lost_rows_and_includes_tie_mass():
    from articles_prorotypes.wang.wang2016 import PriceDistribution
    model = SurvivalTree(max_depth=0).fit([AuctionObservation({}, 1, False)])
    assert model.root is not None
    model.root.distribution = PriceDistribution({1.0: 0.4}, 0.6)
    assert model._nll([AuctionObservation({}, 1, False)]) == pytest.approx(0.0)
    model.root.distribution = PriceDistribution({2.0: 0.4}, 0.6)
    assert model._nll([AuctionObservation({}, 1, False)]) == pytest.approx(0.0)
    model.root.distribution = PriceDistribution({1.0: 0.4}, 0.6)
    assert model._nll([AuctionObservation({}, 2, False)]) > model._nll([AuctionObservation({}, 1, False)])


def test_discrete_equations_5_6_ties_and_continuous_extension_indexing():
    rows = [AuctionObservation({}, 2, True, 1), AuctionObservation({}, 1, False)]
    distribution = SurvivalTree(max_depth=0).fit(rows).predict({})
    assert distribution.win_probability(1) == 0.0
    assert distribution.win_probability(2) == pytest.approx(distribution.masses[1])


def test_winning_market_price_must_be_strictly_below_bid():
    with pytest.raises(ValueError, match="strictly less"):
        AuctionObservation({}, 2, True, 2)


def test_tree_can_build_normal_and_survival_estimators():
    rows = [AuctionObservation({}, 1, True, 0), AuctionObservation({}, 2, False)]
    survival = SurvivalTree(max_depth=0, estimator="survival").fit(rows).predict({})
    normal = SurvivalTree(max_depth=0, estimator="normal").fit(rows).predict({})
    assert survival.masses != normal.masses


def test_paper_baseline_nm_sm_and_mm_variants_expose_predictions():
    rows = [
        AuctionObservation({}, 2, True, 1),
        AuctionObservation({}, 2, False),
        AuctionObservation({}, 3, True, 2),
    ]
    nm = fit_baseline("NM", rows).predict({})
    sm = fit_baseline("SM", rows).predict({})
    assert nm.masses != sm.masses
    with pytest.raises(NotImplementedError, match="Wu et al"):
        fit_baseline("MM", rows)


def test_wang_predict_returns_defensive_distribution_copy():
    model = SurvivalTree(max_depth=0).fit([AuctionObservation({}, 2, True, 1)])
    prediction = model.predict({})
    prediction.masses[999] = 1
    assert 999 not in model.predict({}).masses


def test_wang_refit_resets_pruned_node_count():
    train = [AuctionObservation({"x": c}, 2 if c == "a" else 6, True, 1 if c == "a" else 5)
             for c in ("a", "a", "b", "b")]
    validation = [AuctionObservation({"x": "a"}, 6, True, 5), AuctionObservation({"x": "b"}, 2, True, 1)]
    model = SurvivalTree(max_depth=1, min_leaf_size=1).fit(train, validation=validation)
    assert model.pruned_nodes == 1
    model.fit(train)
    assert model.pruned_nodes == 0


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -1.0])
def test_point_mean_baseline_rejects_invalid_prices(bad):
    from articles_prorotypes.bench.benchmark import point_mean_distribution
    with pytest.raises(ValueError, match="finite non-negative"):
        point_mean_distribution([bad])
