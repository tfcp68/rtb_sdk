import numpy as np

from articles_prorotypes.bench.price_benchmark import GRID, cdf_of_distribution, empirical_matrix, evaluate, oracle_profit, report
from articles_prorotypes.wang.wang2016 import PriceDistribution


def test_cdf_is_strict_win_probability():
    F = cdf_of_distribution(PriceDistribution({100.0: 0.5, 200.0: 0.5}, 0.0))
    assert F[100] == 0 and F[101] == 0.5 and F[200] == 0.5 and F[201] == 1


def test_true_distribution_gives_oracle_like_first_price_bid():
    # one combo, z always 100, value 300: optimal first-price bid is 101, profit 199 per request
    combo, z, v = np.zeros(10, int), np.full(10, 100.0), np.full(1, 300.0)
    uniq, inv = np.unique(combo, return_inverse=True)
    out = evaluate(empirical_matrix(combo, z, uniq), inv, z, v, np.full(10, 150), 50, 360)
    assert out["profit"] == oracle_profit(np.full(10, 300.0), z) == 1990
    assert out["brier"] == 0 and out["win@0.95"] == 1 and out["bid@0.95"] == 101


def test_competed_metrics_condition_on_z_above_reserve():
    # one combo: half the requests free (z = 50), half competed at z = 150; value 300
    combo, z = np.zeros(10, int), np.array([50.0] * 5 + [150.0] * 5)
    uniq, inv = np.unique(combo, return_inverse=True)
    F = empirical_matrix(combo, z, uniq)
    out = evaluate(F, inv, z, np.full(1, 300.0), np.arange(10) * 30 + 55, 50, 360)
    # conditioned on z > 50 the true distribution is a point mass at 150 -> perfect probability metrics
    assert out["brier_comp"] == 0 and out["bid@0.95_comp"] == 151
    # unconditional F sees half the mass at 50, so it scores worse on the same competed rows' probability
    assert out["brier"] > 0
    # the bid is the model's own b* on all rows (151 here); competed profit is the part earned on z = 150 rows
    assert out["profit_comp"] == 5 * (300 - 151) and out["profit"] == 10 * (300 - 151)


def test_target_metrics_are_reachable_only_and_coverage_is_row_weighted():
    # Combo zero appears three times but is unreachable; combo one appears once and is reachable.
    combo = np.array([0, 0, 0, 1])
    z = np.array([390.0, 390.0, 390.0, 100.0])
    uniq, inv = np.unique(combo, return_inverse=True)
    F = np.zeros((2, len(GRID)))
    F[1, 101:] = 1.0
    out = evaluate(F, inv, z, np.full(2, 300.0), np.full(4, 150), 50, 360)
    for target in (0.5, 0.8, 0.95):
        assert out[f"reachable@{target}"] == 0.25
        assert out[f"win@{target}"] == 1.0
        assert out[f"bid@{target}"] == 101.0
        assert out[f"fallback_win@{target}"] == 1.0
        assert out[f"fallback_bid@{target}"] == 400.0
        assert out[f"reachable@{target}_comp"] == 0.25


def test_unreachable_target_has_none_outcome_and_keeps_max_grid_fallback():
    out = evaluate(np.zeros((1, len(GRID))), np.zeros(3, int), np.full(3, 390.0),
                   np.full(1, 300.0), np.full(3, 150), 50, 360)
    for target in (0.5, 0.8, 0.95):
        assert out[f"reachable@{target}"] == 0.0
        assert out[f"win@{target}"] is None and out[f"bid@{target}"] is None
        assert out[f"fallback_win@{target}"] == 1.0
        assert out[f"fallback_bid@{target}"] == 400.0


def test_all_reachable_and_reports_cover_fallback_for_all_and_comp_sections():
    combo, z = np.zeros(3, int), np.full(3, 100.0)
    uniq, inv = np.unique(combo, return_inverse=True)
    out = evaluate(empirical_matrix(combo, z, uniq), inv, z, np.full(1, 300.0), np.full(3, 150), 50, 360)
    for target in (0.5, 0.8, 0.95):
        assert out[f"reachable@{target}"] == 1.0
        assert out[f"win@{target}"] == 1.0 and out[f"bid@{target}"] == 101.0
        assert out[f"fallback_win@{target}"] is None
        assert out[f"fallback_bid@{target}"] is None
        assert out[f"reachable@{target}_comp"] == 1.0

    row = {"regime": "full", "model": "m", "brier": 0.0, "log_loss": 0.0, "ece": 0.0, "crps": 0.0,
           "brier_comp": 0.0, "log_loss_comp": 0.0, "ece_comp": 0.0, "crps_comp": 0.0}
    for target in (0.5, 0.8, 0.95):
        row.update({f"reachable@{target}": 0.0, f"win@{target}": None, f"bid@{target}": None,
                    f"fallback_win@{target}": 0.0, f"fallback_bid@{target}": 400.0,
                    f"reachable@{target}_comp": 0.0, f"win@{target}_comp": None, f"bid@{target}_comp": None,
                    f"fallback_win@{target}_comp": 0.0, f"fallback_bid@{target}_comp": 400.0})
    payload = {"args": {"seeds": [1], "sample": 1, "train_days": [0, 1], "val_days": [1, 2], "test_days": [2, 3],
                         "reserve": 50, "train_cap": 10}, "data": [], "results": [row]}
    rendered = report(payload)
    assert "coverage" in rendered and "fallback" in rendered
    assert "If no rows qualify" in rendered
    assert "## 1c." in rendered and "## 2c." in rendered
