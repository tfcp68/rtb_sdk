import pytest

from articles_prorotypes.bench.strategy_validation import (
    paired_summary,
    validate_windows,
    window_bootstrap,
)


def test_paired_summary_pairs_random_runs_and_reports_full_distribution():
    result = paired_summary([12, 8, 15], [10, 10, 10])
    assert result["delta_mean"] == pytest.approx(5 / 3)
    assert result["random_mean"] == pytest.approx(10)
    assert result["random_sd"] == pytest.approx(0)
    assert result["random_p95"] == pytest.approx(10)
    assert result["fraction_random_runs_beaten"] == pytest.approx(2 / 3)


def test_paired_summary_uses_per_run_relative_deltas_and_rejects_bad_pairs():
    result = paired_summary([20, 5], [10, 10])
    assert result["relative_delta_mean"] == pytest.approx(0.25)
    with pytest.raises(ValueError):
        paired_summary([1], [1, 2])


def test_windows_must_be_ordered_disjoint_and_within_data_days():
    validate_windows((0, 3), (3, 5), (5, 7), 7)
    with pytest.raises(ValueError):
        validate_windows((0, 4), (3, 5), (5, 7), 7)
    with pytest.raises(ValueError):
        validate_windows((0, 3), (3, 5), (5, 8), 7)


def test_window_bootstrap_counts_windows_and_refuses_fake_ci_from_one_window():
    assert window_bootstrap([5], 7)["ci95"] is None
    out = window_bootstrap([1, 3, 5], 7, n_boot=500)
    assert out["n_windows"] == 3
    assert out["ci95"][0] <= out["mean"] <= out["ci95"][1]
