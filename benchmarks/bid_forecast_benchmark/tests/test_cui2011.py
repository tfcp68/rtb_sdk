import math

import pytest

from articles_prorotypes.cui.cui2011 import SegmentForecast, campaign_cdf, lognormal_parameters
from articles_prorotypes.cui.cui2011 import CuiForecaster, StarTree, symmetric_uncertainty, select_templates


def test_lognormal_parameters_match_arithmetic_mean_and_std():
    mu, sigma = lognormal_parameters(2.0, 1.0)
    assert mu == pytest.approx(math.log(2.0) - 0.5 * math.log(1.25))
    assert sigma == pytest.approx(math.sqrt(math.log(1.25)))


def test_campaign_cdf_is_weighted_mixture_and_monotone():
    forecasts = [SegmentForecast(1.0, 0.0, 1), SegmentForecast(3.0, 0.0, 3)]
    values = campaign_cdf(forecasts, [0.5, 1.0, 3.0])
    assert values == pytest.approx([0.0, 0.25, 1.0])
    assert all(0.0 <= value <= 1.0 for value in values)


def test_cui_rejects_invalid_forecasts_and_bids():
    with pytest.raises(ValueError):
        SegmentForecast(0.0, 1.0, 1)
    with pytest.raises(ValueError):
        campaign_cdf([SegmentForecast(1.0, 1.0, 1)], [-1.0])


def test_lognormal_moments_and_weight_mixture_are_stable_at_extremes():
    mu, sigma = lognormal_parameters(1e308, 1e-308)
    assert math.isfinite(mu) and math.isfinite(sigma)
    result = campaign_cdf(
        [SegmentForecast(1.0, 0.0, 1e308), SegmentForecast(2.0, 0.0, 1e308)],
        [1.0, 2.0],
    )
    assert result == pytest.approx([0.5, 1.0])


def test_star_tree_expands_wildcards_and_prunes_rare_leaves():
    tree = StarTree.fit(
        [{"geo": "A", "device": "m"}, {"geo": "A", "device": "m"}, {"geo": "B", "device": "d"}],
        [1.0, 3.0, 10.0], min_impressions=2,
    )
    leaf = tree.get(("A", "m"))
    assert leaf is not None
    mean, std, count = leaf
    assert mean == pytest.approx(2.0)
    assert std == pytest.approx(1.0)
    assert count == 2
    assert tree.get(("B", "d")) is None
    assert tree.get(("A", "*")) is not None
    assert tree.get(("*", "*")) is not None
    assert tree.get(("A", "*")) is not None
    assert tree.get(("*", "*")) is not None
    assert tree.get(("A", "*")) == pytest.approx((2.0, 1.0, 2))
    all_star = tree.get(("*", "*"))
    assert all_star is not None
    assert all_star[2] == 3


def test_star_tree_converts_log_bid_moments_back_to_linear_space():
    tree = StarTree.fit([{"x": "a"}, {"x": "a"}], [1.0, math.e])
    result = tree.get(("a",))
    assert result is not None
    mean, std, _ = result
    assert mean == pytest.approx((1 + math.e) / 2)
    assert std == pytest.approx((math.e - 1) / 2)


def test_su_and_template_selection_retain_coverage_and_all_star():
    assert symmetric_uncertainty(["a", "a", "b", "b"], [0, 0, 1, 1]) == pytest.approx(1)
    tree = StarTree.fit([{"x": "a", "y": "u"}, {"x": "b", "y": "v"}], [1, 3])
    templates = select_templates(
        [{"x": "a", "y": "u"}, {"x": "a", "y": "v"}, {"x": "z", "y": "v"}],
        [2, 1, 1], {"x": 0.8, "y": 0.2}, tree, k=2,
    )
    assert len(templates) == 2
    assert ("*", "*") in templates


def test_gbdt_learns_numeric_and_categorical_non_linear_pattern():
    from articles_prorotypes.cui.cui_gbdt import GradientBoostingRegressor
    rows = [{"x": x, "group": group} for x, group in [(0, "a"), (1, "a"), (2, "b"), (3, "b")]]
    model = GradientBoostingRegressor(n_estimators=20, learning_rate=0.3, max_depth=1,
                                      min_samples_leaf=1).fit(rows, [0, 0, 10, 10])
    predictions = model.predict(rows)
    assert predictions[0] == pytest.approx(predictions[1])
    assert predictions[2] == pytest.approx(predictions[3])
    assert predictions[2] > predictions[0]


def test_gbdt_matches_textbook_least_squares_boosting():
    """Eq. (2): F0 = mean, then each round fits a depth-1 tree to residuals and adds eta * leaf mean."""
    import numpy as np
    from articles_prorotypes.cui.cui_gbdt import GradientBoostingRegressor
    x = np.array([0., 1., 2., 3., 4., 5., 6., 7.])
    y = np.array([1., 1., 2., 6., 6., 7., 9., 9.])
    eta, rounds = 0.3, 5
    pred = np.full_like(y, y.mean())
    for _ in range(rounds):                         # exact CART stump on 8 distinct x values
        r = y - pred
        best = min(((((r[x <= t] - r[x <= t].mean()) ** 2).sum() + ((r[x > t] - r[x > t].mean()) ** 2).sum(), t)
                    for t in (x[:-1] + x[1:]) / 2))
        t = best[1]
        pred = pred + eta * np.where(x <= t, r[x <= t].mean(), r[x > t].mean())
    rows = [{"x": float(v)} for v in x]
    model = GradientBoostingRegressor(n_estimators=rounds, learning_rate=eta, max_depth=1, min_samples_leaf=1).fit(rows, y)
    assert np.allclose(model.predict(rows), pred, atol=1e-4)


def test_gbdt_depth_zero_is_constant_weighted_mean():
    from articles_prorotypes.cui.cui_gbdt import GradientBoostingRegressor
    rows = [{"x": float(v)} for v in range(4)]
    model = GradientBoostingRegressor(n_estimators=5, max_depth=0).fit(rows, [0, 0, 10, 10], [1, 1, 1, 3])
    assert model.predict(rows) == pytest.approx([(0 + 0 + 10 + 30) / 6] * 4)


def test_gbdt_numpy_integers_stay_numeric():
    import numpy as np
    from articles_prorotypes.cui.cui_gbdt import GradientBoostingRegressor
    rows = [{"x": np.int64(v)} for v in range(6)]
    model = GradientBoostingRegressor(n_estimators=1, max_depth=1, min_samples_leaf=1).fit(rows, [0, 0, 0, 5, 5, 5])
    assert not model.categories                     # numeric, so a threshold split, not one-vs-rest categories
    assert model.predict([{"x": 4.5}])[0] > model.predict([{"x": 0.5}])[0]


def test_cui_forecaster_fits_predicts_and_exposes_baselines():
    rows = [
        {"target": {"geo": geo}, "features": {"quality": float(q)}, "bid": bid, "impressions": 1}
        for geo, q, bid in [("A", 0, 1.0), ("A", 1, 2.0), ("B", 0, 3.0), ("B", 1, 4.0)]
    ]
    model = CuiForecaster(n_estimators=3, min_impressions=1, n_templates=2).fit(rows)
    forecast = model.predict({"geo": ["A", "B"]}, bids=[1, 2, 4])
    assert len(forecast.samples) == 2
    assert len(forecast.cdf) == 3
    assert forecast.cdf == sorted(forecast.cdf)
    assert model.predict_sample(rows[0]["target"], rows[0]["features"]).mean > 0
    assert len(model.baseline_mean_cdf({"geo": ["A", "B"]}, [1, 2, 4])) == 3
    assert CuiForecaster.baseline_copy_history_cdf([1, 2, 3], [0, 2, 4]) == [0, pytest.approx(2 / 3), 1]
    assert CuiForecaster.baseline_copy_history_cdf(None, [1]) is None


def test_fcbf_removes_redundant_features_and_preserves_relevant_feature():
    from articles_prorotypes.cui.cui_features import fcbf_select

    x = [0, 0, 1, 1, 0, 0, 1, 1]
    duplicate = list(x)
    noise = [0, 1, 0, 1, 1, 0, 1, 0]
    target = [0, 0, 1, 1, 0, 0, 1, 1]
    assert fcbf_select({"x": x, "duplicate": duplicate, "noise": noise}, target) == ["x"]


def test_fit_windows_keeps_history_template_and_model_windows_disjoint():
    model = CuiForecaster(n_estimators=3, min_impressions=1, n_templates=2)
    history = [
        {"target": {"geo": "A"}, "features": {}, "bid": 2.0, "impressions": 2},
        {"target": {"geo": "B"}, "features": {}, "bid": 8.0, "impressions": 2},
    ]
    template = [
        {"target": {"geo": "A"}, "features": {}, "bid": 3.0, "impressions": 1},
        {"target": {"geo": "B"}, "features": {}, "bid": 9.0, "impressions": 1},
    ]
    training = [
        {"target": {"geo": "A"}, "features": {"x": 0}, "bid": 4.0, "impressions": 2},
        {"target": {"geo": "B"}, "features": {"x": 1}, "bid": 10.0, "impressions": 2},
    ]
    model.fit_windows(history, template, training)
    history_value = model.tree.get(("A",))
    assert history_value is not None and history_value[0] == pytest.approx(2.0)
    assert model.templates
    assert model.training_targets == [("A",), ("B",)]
    assert model.selected_features == ("geo",)


def test_fcbf_selected_features_are_actual_regressor_inputs():
    model = CuiForecaster(n_estimators=1, min_impressions=1, n_templates=2)
    rows = [{"target": {"signal": x, "duplicate": x}, "features": {"extra": x},
             "bid": 1 + x, "impressions": 1} for x in (0, 0, 1, 1)]
    model.fit(rows)
    assert model.selected_features == ("signal",)


def test_cui_redundant_fcbf_dimensions_keep_full_star_tree_paths_and_conditional_history():
    rows = []
    for geo, device, base in [("A", "mobile", 2), ("B", "tv", 9)]:
        for _ in range(6):
            rows.append({"target": {"geo": geo, "device": device},
                         "features": {"redundant": geo}, "bid": float(base), "impressions": 1})
    model = CuiForecaster(n_estimators=2, min_impressions=1, n_templates=2).fit(rows)
    assert model.selected_features == ("geo",)
    assert model._history({"geo": "A", "device": "mobile"})[0] == pytest.approx(2)
    assert model._history({"geo": "B", "device": "tv"})[0] == pytest.approx(9)
    assert model.tree.get(("A", "mobile")) is not None


def test_cui_fit_uses_observed_dimension_values_when_fcbf_falls_back_to_all_star():
    rows = [{"target": {"geo": geo, "device": device}, "features": {}, "bid": float(bid)}
            for geo, device, bid in [("a", "m", 5), ("a", "n", 5), ("b", "m", 5), ("b", "n", 5)]]
    # constant bid => SU(feature, label) = 0 for every feature => FCBF selects nothing, falls back to all features
    model = CuiForecaster(n_estimators=1, min_impressions=1, n_templates=1).fit(rows)
    assert model.selected_features == ("geo", "device")
    # the fallback branch sets unit weights; real selection would carry SU values (0.667 for distinct bids)
    assert model.feature_weights == {"geo": 1.0, "device": 1.0}
    assert model.templates == [("*", "*")]


def test_cui_single_window_training_uses_same_filtered_features_as_prediction():
    rows = [{"target": {"x": x}, "features": {"signal": x, "irrelevant": "constant"},
             "bid": float(1 + 8 * x), "impressions": 1} for x in (0, 0, 1, 1)]
    model = CuiForecaster(n_estimators=2, min_impressions=1, n_templates=2).fit(rows)
    assert model.mean_model.used_features() <=set(model.selected_features + ("signal", "history_mean", "history_std"))


@pytest.mark.parametrize("campaign", [{"x": list(range(2049))}])
def test_cui_campaign_expansion_is_bounded(campaign):
    model = CuiForecaster(n_estimators=1)
    model.feature_names = ("x",)
    with pytest.raises(ValueError, match="expansion limit"):
        model._campaign_samples(campaign)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -1.0])
def test_cui_point_mean_baseline_rejects_invalid_bids(bad):
    model = CuiForecaster(n_estimators=1, min_impressions=1, n_templates=2).fit([
        {"target": {"x": "a"}, "features": {}, "bid": 2.0},
        {"target": {"x": "b"}, "features": {}, "bid": 3.0},
    ])
    with pytest.raises(ValueError, match="finite and non-negative"):
        model.baseline_mean_cdf({"x": ["a", "b"]}, [bad])
