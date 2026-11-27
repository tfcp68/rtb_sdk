import importlib.util
from pathlib import Path

import numpy as np
import pytest

PATH = Path(__file__).parents[1] / "bench" / "probability_diagnostics.py"


def helper():
    spec = importlib.util.spec_from_file_location("probability_diagnostics", PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_probabilities_at_bids_strict_ece_and_counts():
    d = helper()
    grid = np.array([0., 2., 5.])
    F = np.array([[0., .5, 1.]])
    got = d.probability_metrics(F, np.array([0, 0]), grid, np.array([2., 5.]),
                               np.array([2., 5.]), np.array([True, True]))
    assert got["n"] == got["positive_bid_n"] == 2
    assert got["mean_predicted_win"] == pytest.approx(.75)
    assert got["mean_observed_win"] == 0
    assert got["brier"] == pytest.approx(.625)
    assert got["ece_bins"][5]["count"] == 1
    assert got["ece_bins"][9]["count"] == 1
    assert sum(x["count"] for x in got["ece_bins"]) == got["n"]
    assert got["confidently_wrong_count"] == 1


def test_empty_eligible_rows_and_strict_local_oracle_nonuniform_grid():
    d = helper()
    grid = np.array([0., 1., 4., 7.])
    empty = d.probability_metrics(np.zeros((1, 4)), np.array([0]), grid,
                                  np.array([0.]), np.array([0.]), np.array([False]))
    assert empty["n"] == 0 and empty["brier"] is None
    oracle = d.local_oracle_metrics(np.array([8., 3., 8.]), np.array([4., 5., 4.]),
                                    np.array([4., 4., 5.]), grid)
    assert oracle["oracle_bids"] == [7., 7., 7.]
    assert oracle["regret_sum"] == pytest.approx(-1.)


def test_grid_requires_finite_aligned_probability_matrix_and_exact_bid_values():
    d = helper()
    with pytest.raises(ValueError, match="shape"):
        d.probability_metrics(np.zeros((1, 2)), np.array([0]), np.array([0., 1., 2.]),
                              np.array([1.]), np.array([1.]), np.array([True]))
    with pytest.raises(ValueError, match="grid"):
        d.probability_metrics(np.zeros((1, 2)), np.array([0]), np.array([0., 1.]),
                              np.array([.5]), np.array([1.]), np.array([True]))


def test_probability_matrix_clips_only_floating_point_boundary_noise():
    d = helper()
    grid = np.array([0., 2.])
    F = np.array([[0., 1. + 5e-13]])
    got = d.probability_metrics(F, np.array([0]), grid, np.array([2.]),
                               np.array([1.]), np.array([True]))
    assert got["mean_predicted_win"] == 1.
    assert F[0, 1] > 1.  # scoring normalization must not mutate frozen policy probabilities
    with pytest.raises(ValueError, match="out of range"):
        d.probability_metrics(np.array([[0., 1. + 1e-6]]), np.array([0]), grid,
                              np.array([2.]), np.array([1.]), np.array([True]))


def test_zero_bid_is_valid_only_when_zero_is_on_grid():
    d = helper()
    got = d.probability_metrics(np.array([[0., .5]]), np.array([0]), np.array([0., 2.]),
                               np.array([0.]), np.array([0.]), np.array([True]))
    assert got["n"] == 1 and got["positive_bid_n"] == 0
    with pytest.raises(ValueError, match="grid"):
        d.probability_metrics(np.array([[.5]]), np.array([0]), np.array([2.]),
                              np.array([0.]), np.array([0.]), np.array([True]))
