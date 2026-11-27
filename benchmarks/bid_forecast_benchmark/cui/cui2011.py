"""Cui et al. (2011): weighted log-normal campaign bid landscape."""

from dataclasses import dataclass
import math
from collections.abc import Sequence
from collections.abc import Mapping
from typing import Any

from scipy.special import ndtr

from .cui_features import STAR, fcbf_select, select_templates, symmetric_uncertainty
from .cui_gbdt import GradientBoostingRegressor
from .cui_star_tree import StarTree


@dataclass(frozen=True)
class SegmentForecast:
    """Linear-space segment mean, standard deviation, and impression weight."""

    mean: float
    std: float
    weight: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.mean) or self.mean <= 0:
            raise ValueError("mean must be finite and positive")
        if not math.isfinite(self.std) or self.std < 0:
            raise ValueError("std must be finite and non-negative")
        if not math.isfinite(self.weight) or self.weight < 0:
            raise ValueError("weight must be finite and non-negative")


def lognormal_parameters(mean: float, std: float) -> tuple[float, float]:
    """Convert arithmetic-space moments to log-space (Cui Eq. 4)."""
    if not math.isfinite(mean) or mean <= 0 or not math.isfinite(std) or std < 0:
        raise ValueError("mean must be positive and std non-negative, both finite")
    if std == 0:
        return math.log(mean), 0.0
    log_ratio = math.log(std) - math.log(mean)
    variance_log = log_ratio * 2 + math.log1p(math.exp(-2 * log_ratio)) if log_ratio > 0 else math.log1p(math.exp(2 * log_ratio))
    return math.log(mean) - variance_log / 2, math.sqrt(variance_log)


def campaign_cdf(segments: Sequence[SegmentForecast], bids: Sequence[float]) -> list[float]:
    """Evaluate impression-weighted mixture of segment log-normal CDFs."""
    max_weight = max((item.weight for item in segments), default=0.0)
    if not segments or max_weight <= 0:
        raise ValueError("segments must have positive total weight")
    if any(not math.isfinite(bid) or bid < 0 for bid in bids):
        raise ValueError("bids must be finite and non-negative")
    normalized_weights = [item.weight / max_weight for item in segments]
    total = sum(normalized_weights)
    output = []
    for bid in bids:
        cdf = 0.0
        for item, weight in zip(segments, normalized_weights):
            if bid == 0:
                component = 0.0
            else:
                mu, sigma = lognormal_parameters(item.mean, item.std)
                component = (1.0 if math.log(bid) >= mu else 0.0) if sigma == 0 else float(
                    ndtr((math.log(bid) - mu) / sigma))
            cdf += weight * component / total
        output.append(min(1.0, max(0.0, cdf)))
    return output


@dataclass(frozen=True)
class CuiForecast:
    """Benchmark-friendly forecast and intermediate sample moments."""
    samples: tuple[SegmentForecast, ...]
    cdf: list[float]


class CuiForecaster:
    """End-to-end Cui-style model; records are {target, features, bid, impressions?}."""

    def __init__(self, n_estimators: int = 30, learning_rate: float = 0.1,
                 max_depth: int = 2, min_samples_leaf: int = 2,
                 min_impressions: float = 1, n_templates: int = 30):
        self.n_estimators, self.learning_rate = n_estimators, learning_rate
        self.max_depth, self.min_samples_leaf = max_depth, min_samples_leaf
        self.min_impressions, self.n_templates = min_impressions, n_templates

    @staticmethod
    def _validate_rows(rows: Sequence[Mapping[str, Any]]) -> tuple[list[dict], list[dict], list[float], list[float]]:
        if not rows:
            raise ValueError("training rows must not be empty")
        targets = [dict(row["target"]) for row in rows]
        features = [dict(row.get("features", {})) for row in rows]
        bids = [float(row["bid"]) for row in rows]
        weights = [float(row.get("impressions", 1)) for row in rows]
        if any(not math.isfinite(b) or b <= 0 for b in bids):
            raise ValueError("bids must be finite and positive")
        return targets, features, bids, weights

    def fit(self, rows: Sequence[Mapping[str, Any]]) -> "CuiForecaster":
        targets, features, bids, weights = self._validate_rows(rows)
        self.feature_names = tuple(targets[0])
        if any(tuple(target) != self.feature_names for target in targets):
            raise ValueError("target attributes must have identical ordered keys")
        self.tree = StarTree.fit(targets, bids, weights, self.min_impressions)
        labels = [round(math.log(b), 3) for b in bids]
        self._select_features_and_templates(targets, labels, weights)
        self._fit_regressors(targets, features, bids, weights)
        return self

    def _select_features_and_templates(self, targets, labels, weights):
        columns = {name: [target[name] for target in targets] for name in self.feature_names}
        selected = fcbf_select(columns, labels)
        self.selected_features = tuple(selected) if selected else self.feature_names
        self.feature_weights = ({name: symmetric_uncertainty(columns[name], labels)
                                 for name in self.feature_names}
                                if selected else {name: 1.0 for name in self.feature_names})
        self.templates = select_templates(targets, weights, self.feature_weights, self.tree,
                                          min(self.n_templates, 1 << len(self.feature_names)))

    def fit_windows(self, history_rows: Sequence[Mapping[str, Any]],
                    template_rows: Sequence[Mapping[str, Any]],
                    model_rows: Sequence[Mapping[str, Any]]) -> "CuiForecaster":
        """Fit star history on t1, template coverage on held-out t2, regressors on t3."""
        history_targets, _, history_bids, history_weights = self._validate_rows(history_rows)
        template_targets, _, _, template_weights = self._validate_rows(template_rows)
        targets, features, bids, weights = self._validate_rows(model_rows)
        names = tuple(history_targets[0])
        if any(tuple(row) != names for group in (history_targets, template_targets, targets) for row in group):
            raise ValueError("target attributes must have identical ordered keys across windows")
        self.feature_names = names
        self.tree = StarTree.fit(history_targets, history_bids, history_weights, self.min_impressions)
        history_labels = [round(math.log(bid), 3) for bid in history_bids]
        self._select_features_and_templates(history_targets, history_labels, history_weights)
        # Template t2 contributes coverage only; its outcomes do not set feature weights.
        self.templates = select_templates(template_targets, template_weights, self.feature_weights,
                                          self.tree, min(self.n_templates, 1 << len(names)))
        self._fit_regressors(targets, features, bids, weights)
        return self

    def _fit_regressors(self, targets, features, bids, weights):
        grouped: dict[tuple[Any, ...], list[tuple[float, float]]] = {}
        for target, bid, weight in zip(targets, bids, weights):
            grouped.setdefault(tuple(target[name] for name in self.feature_names), []).append((bid, weight))
        training, means, stds, train_weights = [], [], [], []
        representatives = {tuple(t[name] for name in self.feature_names): (t, f)
                           for t, f in zip(targets, features)}
        for key, observations in grouped.items():
            total = sum(w for _, w in observations)
            mean = sum(b * w for b, w in observations) / total
            variance = sum(w * (b - mean) ** 2 for b, w in observations) / total
            target, feat = representatives[key]
            hmean, hstd, _ = self._history(target)
            training.append({**target, **feat, "history_mean": hmean, "history_std": hstd})
            means.append(mean); stds.append(math.sqrt(variance)); train_weights.append(total)
        self.feature_keys = tuple(features[0])
        selected_training = self._selected_rows(training)
        self.mean_model = GradientBoostingRegressor(self.n_estimators, self.learning_rate,
            self.max_depth, self.min_samples_leaf).fit(selected_training, means, train_weights)
        self.std_model = GradientBoostingRegressor(self.n_estimators, self.learning_rate,
            self.max_depth, self.min_samples_leaf).fit(selected_training, stds, train_weights)
        self.training_targets = list(grouped)

    def _selected_rows(self, rows):
        keys = set(self.selected_features) | set(self.feature_keys if hasattr(self, "feature_keys") else ())
        keys.update(("history_mean", "history_std"))
        return [{key: value for key, value in row.items() if key in keys} for row in rows]

    def _history(self, target: Mapping[str, Any]) -> tuple[float, float, int]:
        matches = []
        for template in self.templates:
            path = tuple(target[name] if mode == "v" else STAR for name, mode in zip(self.feature_names, template))
            value = self.tree.get(path)
            if value is not None:
                quality = sum(self.feature_weights[n] for n, mode in zip(self.feature_names, template) if mode == "v")
                matches.append((quality, value))
        if matches:
            return max(matches, key=lambda pair: pair[0])[1]
        fallback = self.tree.get((STAR,) * len(self.feature_names))
        if fallback is None:
            raise ValueError("star tree has no usable history; lower min_impressions")
        return fallback

    def predict_sample(self, target: Mapping[str, Any], features: Mapping[str, Any] | None = None) -> SegmentForecast:
        return self.predict_samples([target], [features or {}])[0]

    def predict_samples(self, targets: Sequence[Mapping[str, Any]],
                        features: Sequence[Mapping[str, Any]] | None = None) -> list[SegmentForecast]:
        """Batched predict_sample: one booster call for all rows."""
        keep = set(self.selected_features) | set(self.feature_keys) | {"history_mean", "history_std"}
        histories = [self._history(t) for t in targets]
        rows = [{k: v for k, v in {**t, **f, "history_mean": h[0], "history_std": h[1]}.items() if k in keep}
                for t, f, h in zip(targets, features or [{}] * len(targets), histories)]
        means, stds = self.mean_model.predict(rows), self.std_model.predict(rows)
        return [SegmentForecast(max(1e-12, m), max(0.0, s), float(h[2])) for m, s, h in zip(means, stds, histories)]

    def _campaign_samples(self, campaign: Mapping[str, Sequence[Any]], features: Sequence[Mapping[str, Any]] | None = None):
        names = tuple(campaign)
        if names != self.feature_names or any(not campaign[name] for name in names):
            raise ValueError("campaign must provide non-empty values for all fitted targeting attributes")
        from itertools import product
        size = math.prod(len(campaign[name]) for name in names)
        if size > 2048:
            raise ValueError("campaign expansion limit is 2048 combinations")
        targets = [dict(zip(names, values)) for values in product(*(campaign[name] for name in names))]
        supplied = list(features) if features is not None else [{} for _ in targets]
        if len(supplied) != len(targets):
            raise ValueError("features must have one mapping per expanded sample")
        predictions = self.predict_samples(targets, supplied)
        # No expected available impressions are supplied per combination; history support is not future traffic share.
        # TODO: compare equal mixture weights with expected-impression shares and likelihood-learned weights (Cui, section 3.3).
        return [SegmentForecast(item.mean, item.std, 1.0) for item in predictions]

    def predict(self, campaign: Mapping[str, Sequence[Any]], bids: Sequence[float],
                features: Sequence[Mapping[str, Any]] | None = None) -> CuiForecast:
        samples = self._campaign_samples(campaign, features)
        return CuiForecast(tuple(samples), campaign_cdf(samples, bids))

    def baseline_mean_cdf(self, campaign: Mapping[str, Sequence[Any]], bids: Sequence[float],
                          features: Sequence[Mapping[str, Any]] | None = None) -> list[float]:
        """Cui campaign baseline 2: point mass at each sample's forecast mean."""
        if any(not math.isfinite(float(bid)) or float(bid) < 0 for bid in bids):
            raise ValueError("bids must be finite and non-negative")
        samples = self._campaign_samples(campaign, features)
        total = sum(item.weight for item in samples)
        if total <= 0:
            raise ValueError("campaign sample weights must be positive")
        return [sum(item.weight for item in samples if item.mean <= bid) / total for bid in bids]

    @staticmethod
    def baseline_copy_history_cdf(history_bids: Sequence[float] | None, bids: Sequence[float]) -> list[float] | None:
        """Cui campaign baseline 1: empirical recent campaign history, if available."""
        if history_bids is None:
            return None
        if not history_bids or any(not math.isfinite(float(value)) or value <= 0 for value in history_bids):
            raise ValueError("history_bids must be non-empty positive finite bids")
        if any(not math.isfinite(float(value)) or value < 0 for value in bids):
            raise ValueError("bids must be finite and non-negative")
        ordered = sorted(history_bids)
        return [sum(value <= bid for value in ordered) / len(ordered) for bid in bids]
