from articles_prorotypes.bench.benchmark import (distribution_metrics, make_wang_dataset,
                                           run, split_wang, make_cui_windows,
                                           market_price_anlp, _partition_fingerprint)
from articles_prorotypes.bench.stand_benchmark import response_metrics
import pytest


def test_distribution_metrics_include_cdf_and_win_probability_quality():
    result = distribution_metrics([1, 2, 3], [1.0, 2.0, 4.0], {1.0: 1.0}, 0.0)
    assert result["cdf_mae"] > 0
    assert result["cdf_rmse"] > 0
    assert result["win_probability_mae"] >= 0


def test_wang_splitter_returns_aligned_truth_indices_and_disjoint_sets():
    rows, truth = make_wang_dataset(seed=13, n=240)
    train, validation, test_indices, validation_indices = split_wang(rows, seed=13)
    assert len(train) == 144 and len(validation) == 48 and len(test_indices) == 48
    assert len(validation_indices) == len(validation)
    assert not ({id(x) for x in train} & {id(x) for x in validation})
    assert not ({id(x) for x in train} & {id(rows[i]) for i in test_indices})
    assert all(truth[i] == rows[i].market_price for i in test_indices if rows[i].won)
    assert all(truth[i] >= rows[i].bid for i in test_indices if not rows[i].won)
    assert all(rows[i].market_price is None for i in test_indices if not rows[i].won)


def test_training_rows_never_expose_heldout_market_truth():
    rows, _ = make_wang_dataset(seed=11, n=60)
    train, validation, test_indices, _ = split_wang(rows, seed=11)
    test = [rows[i] for i in test_indices]
    assert train and test
    assert all(not hasattr(row, "latent_price") for row in train)
    assert all(row.market_price is None for row in train if not row.won)
    assert not ({id(row) for row in train} & {id(row) for row in test})
    assert all(row.market_price is None or row.market_price <= row.bid for row in test)


def test_benchmark_includes_both_article_model_inventories_and_real_fit_times():
    result = run(seeds=[3], n=60)
    inventory = {row["model"] for row in result["results"]}
    assert inventory == {"CUI_MIXTURE", "CUI_HISTORY", "CUI_SAMPLE_MEAN",
                         "WANG_NM", "WANG_SM", "WANG_NTM", "WANG_STM",
                         "WANG_NTM_PRUNED", "WANG_STM_PRUNED"}
    for row in result["results"]:
        assert row["fit_seconds"] > 0
        assert row["test_rows"] > 0


def test_cui_temporal_windows_keep_heldout_campaign_truth_out_of_fit():
    windows = make_cui_windows(seed=7, n=60)
    assert set(windows) == {"history", "template", "training", "test"}
    model_keys = {tuple(row["target"].items()) for name in ("history", "template", "training")
                  for row in windows[name]}
    test_keys = [tuple(target.items()) for target, _, _ in windows["test"]]
    assert all(tuple(target.items()) in model_keys for target, _, _ in windows["test"])
    assert all({tuple(row["target"].items()) for row in windows[key]} ==
               {(("segment", f"segment-{group}"),) for group in range(3)}
               for key in ("history", "template", "training"))
    assert len(set(test_keys)) > 1
    assert not ({id(row) for key in ("history", "template", "training") for row in windows[key]}
                & {id(row) for row in windows["test"]})


def test_cui_shared_category_data_uses_informative_tree_lookup():
    result = run(seeds=[3], n=240)
    cui_results = [row for row in result["results"] if row["article"] == "Cui2011"]
    assert all(row["parameters"]["test_informative_history_matches"] > 0 for row in cui_results)


def test_wang_market_anlp_uses_exact_mass_and_epsilon_for_zero_support():
    from articles_prorotypes.wang.wang2016 import PriceDistribution
    result = market_price_anlp([PriceDistribution({2: .5}, .5), PriceDistribution({1: 1}, 0)], [2, 3])
    assert result["market_price_anlp"] == pytest.approx(
        (__import__("math").log(2) - __import__("math").log(1e-12)) / 2)
    assert result["market_price_zero_support_count"] == 1


def test_paired_wang_pruning_variants_share_train_seed_and_settings():
    result = run(seeds=[17], n=60)
    records = {row["model"]: row for row in result["results"] if row["article"] == "Wang2016"}
    for pair in (("WANG_NTM", "WANG_NTM_PRUNED"), ("WANG_STM", "WANG_STM_PRUNED")):
        plain, pruned = (records[name] for name in pair)
        assert plain["training_data_sha256"] == pruned["training_data_sha256"]
        assert plain["validation_data_sha256"] == pruned["validation_data_sha256"]
        assert plain["test_data_sha256"] == pruned["test_data_sha256"]
        assert plain["parameters"]["random_seed"] == pruned["parameters"]["random_seed"]
        assert plain["validation_role"] == "held_out_not_used"
        assert pruned["validation_role"] == "pruning_only"
        assert plain["parameters"]["estimator"] == pruned["parameters"]["estimator"]


def test_partition_fingerprint_is_order_independent_for_identical_rows():
    rows, _ = make_wang_dataset(seed=15, n=20)
    assert _partition_fingerprint(rows) == _partition_fingerprint(list(rows))


def test_benchmark_records_all_seeds_rows_and_cui_metrics():
    result = run(seeds=[3, 17, 29], n=240)
    assert result["seeds"] == [3, 17, 29]
    assert all(row["test_rows"] >= 12 for row in result["results"])
    cui = [row for row in result["results"] if row["article"] == "Cui2011"]
    mixture, history, mean = (next(row for row in cui if row["model"] == name)
                              for name in ("CUI_MIXTURE", "CUI_HISTORY", "CUI_SAMPLE_MEAN"))
    assert all("segment_moment_mean_mae" in row and "segment_moment_std_mae" in row
               for row in (mixture, mean))
    assert "segment_moment_mean_mae" not in history
    assert "segment_moment_std_mae" not in history
    assert mixture["template_seconds"] > 0
    assert history["predict_seconds"] < mixture["predict_seconds"]
    assert mean["predict_seconds"] > 0
    assert history["fit_seconds"] == history["history_seconds"]
    assert mean["fit_seconds"] == pytest.approx(
        mean["history_seconds"] + mean["template_seconds"] + mean["gbdt_seconds"])


@pytest.mark.parametrize("n", [0, 59])
def test_run_rejects_too_few_rows(n):
    with pytest.raises(ValueError, match="at least 60"):
        run(seeds=[3], n=n)


@pytest.mark.parametrize("seeds", [[], [3, "x"], [3, 0], [True]])
def test_run_rejects_invalid_seeds(seeds):
    with pytest.raises(ValueError, match="non-empty integer seeds"):
        run(seeds=seeds, n=60)


def test_stand_response_calibration_handles_empty_bins_and_binary_metrics():
    result = response_metrics([0, 1, 1, 0], [.1, .7, .8, .2])
    assert result["brier"] == pytest.approx(.045)
    assert result["log_loss"] > 0
    assert sum(row["count"] for row in result["calibration_bins"]) == 4
    assert any(row["count"] == 0 and row["observed_rate"] is None for row in result["calibration_bins"])
