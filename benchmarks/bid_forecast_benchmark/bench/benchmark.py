"""Bounded, deterministic synthetic benchmarks for Cui (2011) and Wang (2016)."""
from __future__ import annotations

import argparse
import json
import hashlib
import math
import platform
import random
import statistics
import time
from numbers import Integral
from pathlib import Path
from typing import Any
from ..cui.cui_features import select_templates

from ..cui.cui2011 import CuiForecaster, SegmentForecast, campaign_cdf
from ..wang.wang2016 import AuctionObservation, SurvivalTree, fit_baseline


def _time(call):
    start = time.perf_counter()
    value = call()
    return value, max(time.perf_counter() - start, 1e-12)


def make_cui_windows(seed: int, n: int = 240):
    """Disjoint period rows sharing three categories; test truths are evaluator-only."""
    rng = random.Random(seed)
    result = {name: [] for name in ("history", "template", "training")}
    test = []
    for period, count, offset in zip(("history", "template", "training"),
                                     [n // 4, n // 4, n // 4], (0, 10_000, 20_000)):
        for i in range(count):
            group = i % 3
            segment = f"segment-{group}"
            exposure = float(1 + (i % 4))
            latent = max(0.1, 1.0 + group * 1.5 + rng.gauss(0, .35))
            row = {"target": {"segment": segment}, "features": {"hour": i % 24},
                   "bid": latent, "impressions": exposure}
            result[period].append(row)
    for i in range(max(1, n // 4)):
        group = i % 3
        segment = f"segment-{group}"
        latent = max(0.1, 1.0 + group * 1.5 + rng.gauss(0, .35))
        test.append(({"segment": segment}, {"hour": i % 24}, latent))
    result["test"] = test
    return result


def make_wang_dataset(seed: int, n: int = 240):
    """Model-facing censored observations; latent truth is returned separately."""
    rng = random.Random(seed)
    rows, truth = [], []
    for i in range(n):
        group = i % 3
        price = max(1, int(rng.gauss(4 + group * 5, 2 + group)))
        bid = rng.randint(2, 10)
        won = bid > price
        truth.append(price)
        rows.append(AuctionObservation({"segment": str(group), "hour": str(i % 4)}, bid, won,
                                       price if won else None))
    return rows, truth


def split_wang(rows, seed):
    indices = list(range(len(rows)))
    random.Random(seed).shuffle(indices)
    a, b = int(len(rows) * .6), int(len(rows) * .8)
    return ([rows[i] for i in indices[:a]], [rows[i] for i in indices[a:b]],
            indices[b:], indices[a:b])


def _partition_fingerprint(rows):
    payload = "\n".join(repr((row.features, row.bid, row.won, row.market_price)) for row in rows)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def distribution_metrics(true_prices, bids, masses, tail=0.0):
    thresholds = sorted(set(bids) | set(true_prices) | set(masses))
    cdf_errors, win_errors = [], []
    for x in thresholds:
        actual = sum(p <= x for p in true_prices) / len(true_prices)
        predicted = math.fsum(p for price, p in masses.items() if price <= x)
        actual_win = sum(p < x for p in true_prices) / len(true_prices)
        predicted_win = math.fsum(p for price, p in masses.items() if price < x)
        cdf_errors.append(predicted - actual)
        win_errors.append(predicted_win - actual_win)
    return {"cdf_mae": statistics.mean(map(abs, cdf_errors)),
            "cdf_rmse": math.sqrt(statistics.mean(e * e for e in cdf_errors)),
             "win_probability_mae": statistics.mean(map(abs, win_errors)),
             "predicted_tail_mass": tail, "threshold_count": len(thresholds)}


def _win_outcome_metrics(probabilities, outcomes):
    probabilities = [min(1 - 1e-12, max(1e-12, p)) for p in probabilities]
    return {"win_brier": statistics.mean((p - y) ** 2 for p, y in zip(probabilities, outcomes)),
            "win_log_loss": -statistics.mean(y * math.log(p) + (1 - y) * math.log1p(-p)
                                              for p, y in zip(probabilities, outcomes))}


def point_mean_distribution(prices):
    """Empirical point-mass baseline used by article benchmark utilities."""
    if not prices or any(not math.isfinite(float(price)) or float(price) < 0 for price in prices):
        raise ValueError("prices must be non-empty, finite non-negative values")
    counts = {}
    for price in prices:
        value = float(price)
        counts[value] = counts.get(value, 0) + 1
    from ..wang.wang2016 import PriceDistribution
    return PriceDistribution({price: count / len(prices) for price, count in counts.items()}, 0.0)


def market_price_anlp(distributions, true_prices, epsilon=1e-12):
    """Mean -log exact heldout price mass; unidentified KM tail is not a price bin."""
    if len(distributions) != len(true_prices) or not distributions:
        raise ValueError("distributions and heldout prices must be aligned and non-empty")
    log_losses, zero_support = [], 0
    for distribution, price in zip(distributions, true_prices):
        probability = distribution.masses.get(price, 0.0)
        if probability <= 0:
            zero_support += 1
        log_losses.append(-math.log(max(probability, epsilon)))
    return {"market_price_anlp": statistics.mean(log_losses),
            "market_price_zero_support_count": zero_support,
            "market_price_epsilon": epsilon}


def run(seeds=(3, 17, 29), n=240):
    seeds = list(seeds)
    if not isinstance(n, Integral) or isinstance(n, bool) or n < 60:
        raise ValueError("n must be an integer with at least 60 rows")
    if not seeds or any(not isinstance(seed, Integral) or isinstance(seed, bool) or seed <= 0
                        for seed in seeds):
        raise ValueError("seeds must be non-empty integer seeds")
    records = []
    for seed in seeds:
        windows = make_cui_windows(seed, n)
        model: Any = CuiForecaster(n_estimators=8, min_impressions=1, n_templates=8, min_samples_leaf=1)
        from ..cui.cui_star_tree import StarTree
        (model.tree, history_s) = _time(lambda: StarTree.fit(
            [r["target"] for r in windows["history"]], [r["bid"] for r in windows["history"]],
            [r["impressions"] for r in windows["history"]], 1))
        model.feature_names = ("segment",)
        (_, feature_selection_s) = _time(lambda: model._select_features_and_templates(
            [r["target"] for r in windows["history"]],
            [round(math.log(r["bid"]), 3) for r in windows["history"]],
            [r["impressions"] for r in windows["history"]]))
        (model.templates, actual_template_s) = _time(lambda: select_templates(
            [r["target"] for r in windows["template"]], [r["impressions"] for r in windows["template"]],
            model.feature_weights, model.tree, model.n_templates))
        template_s = feature_selection_s + actual_template_s
        (_, gbdt_s) = _time(lambda: model._fit_regressors(
            [r["target"] for r in windows["training"]], [r["features"] for r in windows["training"]],
            [r["bid"] for r in windows["training"]], [r["impressions"] for r in windows["training"]]))
        fit_total = history_s + template_s + gbdt_s
        test, bids = windows["test"], [x * .5 for x in range(0, 15)]
        truth = [price for _, _, price in test]
        predictions, mixture_predict_s = _time(lambda: [model.predict_sample(t, f) for t, f, _ in test])
        exposure = [1.0 for _ in test]
        mixture_cdf, mixture_cdf_s = _time(lambda: campaign_cdf(
            [SegmentForecast(p.mean, p.std, w) for p, w in zip(predictions, exposure)], bids))
        truths_by_segment: dict[str, list[float]] = {}
        forecasts_by_segment: dict[str, list[SegmentForecast]] = {}
        for (target, _, price), prediction in zip(test, predictions):
            segment = target["segment"]
            truths_by_segment.setdefault(segment, []).append(price)
            forecasts_by_segment.setdefault(segment, []).append(prediction)
        mean_errors, std_errors = [], []
        for segment, segment_truths in truths_by_segment.items():
            forecasts = forecasts_by_segment[segment]
            actual_mean = statistics.mean(segment_truths)
            actual_std = statistics.pstdev(segment_truths)
            mean_errors.append(abs(statistics.mean(p.mean for p in forecasts) - actual_mean))
            std_errors.append(abs(statistics.mean(p.std for p in forecasts) - actual_std))
        # Each baseline independently executes its own forecast construction and CDF.
        (history_cdf, history_predict_s) = _time(lambda: CuiForecaster.baseline_copy_history_cdf(
            [r["bid"] for r in windows["history"]], bids))
        def predict_sample_mean():
            baseline_predictions = [model.predict_sample(target, features) for target, features, _ in test]
            return [sum(p.mean <= bid for p in baseline_predictions) / len(baseline_predictions)
                    for bid in bids]
        mean_cdf, mean_predict_s = _time(predict_sample_mean)
        if history_cdf is None:
            raise ValueError("Cui history baseline needs non-empty history window")
        star_history = model.tree.get(("*",))
        if star_history is None:
            raise ValueError("Cui star-tree needs an all-star history summary")
        method_data = (("CUI_MIXTURE", mixture_cdf, fit_total, mixture_predict_s + mixture_cdf_s),
                       ("CUI_HISTORY", history_cdf, history_s, history_predict_s),
                       ("CUI_SAMPLE_MEAN", mean_cdf, fit_total, mean_predict_s))
        for name, cdf, fit_time, predict_time in method_data:
            actual_cdf = [sum(p <= b for p in truth) / len(truth) for b in bids]
            errors = [a - b for a, b in zip(cdf, actual_cdf)]
            records.append({"seed": seed, "article": "Cui2011", "model": name,
                "train_rows": sum(len(windows[k]) for k in ("history", "training")),
                "template_rows": len(windows["template"]), "test_rows": len(test),
                "fit_seconds": fit_time, "predict_seconds": predict_time,
                "history_seconds": history_s, "template_seconds": template_s, "gbdt_seconds": gbdt_s,
                "parameters": {"n_estimators": 8, "n_templates": 8, "exposure_weighting": True,
                                "test_informative_history_matches": sum(
                                    model._history(t)[0] != star_history[0]
                                    for t, _, _ in test)},
                "template_selected_coverage": len(model.templates),
                "cdf_mae": statistics.mean(map(abs, errors)),
                "cdf_rmse": math.sqrt(statistics.mean(e * e for e in errors)),
                "threshold_count": len(bids)})
            if name != "CUI_HISTORY":
                records[-1]["segment_moment_mean_mae"] = statistics.mean(mean_errors)
                records[-1]["segment_moment_std_mae"] = statistics.mean(std_errors)

        rows, truth = make_wang_dataset(seed, n)
        assert truth is not None
        train, validation, test_indices, validation_indices = split_wang(rows, seed)
        # Validation/test split indices are separate from training; prices are evaluator-side only.
        test = [rows[i] for i in test_indices]
        test_truth = [truth[i] for i in test_indices]
        for name, estimator in (("WANG_NM", "normal"), ("WANG_SM", "survival"),
                                ("WANG_NTM", "normal"), ("WANG_NTM_PRUNED", "normal"),
                                ("WANG_STM", "survival"), ("WANG_STM_PRUNED", "survival")):
            if name in {"WANG_NM", "WANG_SM"}:
                model = None
                baseline_name = "NM" if name == "WANG_NM" else "SM"
                fit_call = lambda baseline_name=baseline_name: fit_baseline(baseline_name, train)
            else:
                pruned = name.endswith("PRUNED")
                model = SurvivalTree(max_depth=2, min_leaf_size=3, random_seed=seed, estimator=estimator)
                fit_call = lambda model=model, pruned=pruned: model.fit(train, validation=validation if pruned else None)
            model, fit_s = _time(fit_call)
            probs, pred_s = _time(lambda: [model.predict(r.features) for r in test])
            agg = {}
            for dist in probs:
                for price, mass in dist.masses.items(): agg[price] = agg.get(price, 0) + mass / len(probs)
            metrics = distribution_metrics(test_truth, [r.bid for r in test], agg,
                                           statistics.mean(d.tail_probability for d in probs))
            outcomes = [float(r.won) for r in test]
            win_probs = [d.win_probability(r.bid) for d, r in zip(probs, test)]
            records.append({"seed": seed, "article": "Wang2016", "model": name,
                "train_rows": len(train), "validation_rows": len(validation), "test_rows": len(test),
                "training_partition": f"seed-{seed}-train-60pct",
                "training_data_sha256": _partition_fingerprint(train),
                "validation_data_sha256": _partition_fingerprint(validation),
                "test_data_sha256": _partition_fingerprint(test),
                "validation_role": "pruning_only" if name.endswith("PRUNED") else "held_out_not_used",
                "training_wall_seconds": fit_s,
                "fit_seconds": fit_s, "predict_seconds": pred_s,
                "parameters": {"max_depth": 2 if "NT" in name or "ST" in name else None,
                    "min_leaf_size": 3 if "NT" in name or "ST" in name else None,
                    "estimator": estimator, "random_seed": seed,
                    "validation_pruning": name.endswith("PRUNED")},
                **metrics, **_win_outcome_metrics(win_probs, outcomes),
                **market_price_anlp(probs, test_truth)})
    inventory = sorted({r["model"] for r in records})
    return {"title": "Synthetic benchmarks for Cui2011 and Wang2016; not article reproduction",
            "environment": {"python": platform.python_version(), "platform": platform.platform(),
                            "implementation": platform.python_implementation(),
                            "processor": platform.processor()},
            "seeds": list(seeds), "synthetic_rows_per_seed": n, "minimum_wang_rows_per_seed": n,
            "split": {"train": 0.6, "validation": 0.2, "test": 0.2},
            "metric_definitions": {
                "market_price_anlp": "mean exact heldout mass NLL; zero mass clipped at epsilon",
                "win_brier": "Brier score on observed win/loss outcome",
                "win_log_loss": "binary log loss on observed win/loss outcome",
                "cdf_mae_rmse": "heldout market price empirical CDF comparison",
                "epsilon": 1e-12}, "model_inventory": inventory,
            "results": records}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", default="3,17,29")
    parser.add_argument("--rows", type=int, default=240)
    parser.add_argument("--output", default="docs/benchmark/bid_forecast/results/synthetic.json")
    args = parser.parse_args(argv)
    try:
        seeds = [int(s.strip()) for s in args.seeds.split(",")]
    except ValueError as exc:
        parser.error(f"--seeds must be a comma-separated list of integers: {exc}")
    data = run(seeds, args.rows)
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    columns = ("seed", "article", "model", "train_rows", "validation_rows", "test_rows", "cdf_mae", "cdf_rmse", "market_price_anlp", "win_brier", "win_log_loss", "fit_seconds", "predict_seconds")
    rows = ["| " + " | ".join(columns) + " |", "|" + "|".join(["---"] * len(columns)) + "|"]
    rows += ["| " + " | ".join(str(r.get(k, "")) if isinstance(r.get(k, ""), int) or isinstance(r.get(k, ""), str) else f"{r.get(k, ''):.6f}" for k in columns) + " |" for r in data["results"]]
    output.with_suffix(".md").write_text("# Synthetic dual-paper benchmark\n\n" + data["title"] + "\n\n" + "\n".join(rows) + "\n", encoding="utf-8")
    print(f"saved {output} and {output.with_suffix('.md')} ({len(data['results'])} measurements; models: {', '.join(data['model_inventory'])})")


if __name__ == "__main__":
    main()
