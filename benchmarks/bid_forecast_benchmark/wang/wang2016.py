"""Wang et al. (2016) functional bid landscape forecasting prototype."""

from collections import defaultdict
from dataclasses import dataclass
import math
import random
from numbers import Integral
from typing import Any

import numpy as np
from scipy.special import rel_entr


@dataclass(frozen=True)
class AuctionObservation:
    features: dict[str, Any]
    bid: float
    won: bool
    market_price: float | None = None

    def __post_init__(self) -> None:
        if not math.isfinite(self.bid) or self.bid < 0:
            raise ValueError("bid must be finite and non-negative")
        if not isinstance(self.won, bool):
            raise ValueError("won must be bool")
        if self.won:
            if self.market_price is None or not math.isfinite(self.market_price) or self.market_price < 0:
                raise ValueError("wins require a finite non-negative market_price")
            if self.market_price >= self.bid:
                raise ValueError("winning market_price must be strictly less than bid")
        elif self.market_price is not None:
            raise ValueError("losses must not include market_price")
        if not isinstance(self.features, dict):
            raise ValueError("features must be a dict")
        for name, value in self.features.items():
            try:
                hash(value)
            except TypeError as exc:
                raise ValueError(f"feature {name!r} must be hashable") from exc
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError(f"feature {name!r} must be finite")


@dataclass(frozen=True)
class PriceDistribution:
    masses: dict[float, float]
    tail_probability: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.tail_probability) or not 0 <= self.tail_probability <= 1:
            raise ValueError("tail_probability must be finite and in [0, 1]")
        if any(not math.isfinite(x) or x < 0 or not math.isfinite(p) or p < 0 for x, p in self.masses.items()):
            raise ValueError("masses must have finite non-negative prices and probabilities")
        if not math.isclose(math.fsum(self.masses.values()) + self.tail_probability, 1, abs_tol=1e-9):
            raise ValueError("event masses and tail_probability must sum to one")

    def cdf(self, threshold: float) -> float:
        if not math.isfinite(threshold):
            raise ValueError("threshold must be finite")
        return math.fsum(p for price, p in self.masses.items() if price <= threshold)

    def win_probability(self, bid: float) -> float:
        if not math.isfinite(bid) or bid < 0:
            raise ValueError("bid must be finite and non-negative")
        return math.fsum(p for price, p in self.masses.items() if price < bid)


def _distribution(rows: list[AuctionObservation], estimator: str = "survival") -> PriceDistribution:
    if estimator == "normal":
        counts: dict[float, int] = defaultdict(int)
        for row in rows:
            if row.won:
                if row.market_price is not None:
                    counts[row.market_price] += 1
        n = sum(counts.values())
        if not n:
            return PriceDistribution({}, 1.0)
        return PriceDistribution({price: count / n for price, count in counts.items()}, 0.0)
    times: dict[float, list[int]] = defaultdict(lambda: [0, 0])
    for row in rows:
        time = row.market_price if row.won else row.bid
        times[time if time is not None else row.bid][0 if row.won else 1] += 1
    at_risk, survival = len(rows), 1.0
    masses: dict[float, float] = {}
    for time in sorted(times):
        events, censored = times[time]
        if events:
            hazard = events / at_risk
            masses[time] = survival * hazard
            survival *= 1 - hazard
        at_risk -= events + censored
    return PriceDistribution(masses, survival)


def _kl(p: PriceDistribution, q: PriceDistribution) -> float:
    support = p.masses.keys() | q.masses.keys()
    pvals = [p.masses.get(x, 0) for x in support] + [p.tail_probability]
    qvals = [q.masses.get(x, 0) for x in support] + [q.tail_probability]
    return float(rel_entr(pvals, np.maximum(qvals, 1e-12)).sum())


@dataclass(frozen=True)
class CategoryClustering:
    divergence: float
    left_values: frozenset[Any]
    right_values: frozenset[Any]
    iterations: int


def cluster_categories(rows: list[AuctionObservation], feature: str, random_seed: int = 0,
                       estimator: str = "survival", max_iterations: int = 100) -> CategoryClustering:
    """Algorithm 1: deterministic-seeded EM/K-means over category distributions."""
    groups: dict[Any, list[AuctionObservation]] = defaultdict(list)
    for row in rows:
        if feature not in row.features:
            raise ValueError(f"feature {feature!r} missing from training observations")
        groups[row.features[feature]].append(row)
    values = sorted(groups, key=repr)
    if len(values) < 2:
        return CategoryClustering(0.0, frozenset(values), frozenset(), 0)
    rng = random.Random(random_seed)
    rng.shuffle(values)
    left, right = set(values[:len(values) // 2]), set(values[len(values) // 2:])
    points = {v: _distribution(groups[v], estimator) for v in groups}
    divergence = -1.0
    iteration = 0
    for iteration in range(1, max_iterations + 1):
        q1 = _distribution([r for v in left for r in groups[v]], estimator)
        q2 = _distribution([r for v in right for r in groups[v]], estimator)
        updated_left, updated_right = set(), set()
        for value in sorted(groups, key=repr):
            # The paper states K1 > K2 assigns to S2; preserve its written comparison.
            (updated_right if _kl(points[value], q1) > _kl(points[value], q2) else updated_left).add(value)
        if not updated_left or not updated_right:
            updated_left, updated_right = left, right
        new_q1 = _distribution([r for v in updated_left for r in groups[v]], estimator)
        new_q2 = _distribution([r for v in updated_right for r in groups[v]], estimator)
        new_divergence = _kl(new_q1, new_q2)
        converged = updated_left == left and updated_right == right and new_divergence == divergence
        left, right, divergence = updated_left, updated_right, new_divergence
        if converged:
            break
    return CategoryClustering(divergence, frozenset(left), frozenset(right), iteration)


@dataclass
class _Node:
    rows: list[AuctionObservation]
    depth: int
    feature: str | None = None
    left_values: frozenset[Any] = frozenset()
    known_values: frozenset[Any] = frozenset()
    left: "_Node | None" = None
    right: "_Node | None" = None
    distribution: PriceDistribution | None = None


class SurvivalTree:
    """Wang binary categorical tree; estimator='normal' gives NTM, survival gives STM."""

    def __init__(self, max_depth: int = 2, min_leaf_size: int = 2, random_seed: int = 0,
                 max_categories: int | None = None, estimator: str = "survival"):
        if (isinstance(max_depth, bool) or not isinstance(max_depth, Integral) or max_depth < 0
                or isinstance(min_leaf_size, bool) or not isinstance(min_leaf_size, Integral) or min_leaf_size < 1):
            raise ValueError("max_depth and min_leaf_size must be valid non-boolean integers")
        if estimator not in {"normal", "survival"}:
            raise ValueError("estimator must be 'normal' or 'survival'")
        self.max_depth, self.min_leaf_size = int(max_depth), int(min_leaf_size)
        self.random_seed, self.max_categories, self.estimator = random_seed, max_categories, estimator
        self.root: _Node | None = None
        self.pruned_nodes = 0

    def fit(self, observations: list[AuctionObservation], validation: list[AuctionObservation] | None = None) -> "SurvivalTree":
        if not observations:
            raise ValueError("observations must not be empty")
        self.pruned_nodes = 0
        self.root = self._grow(list(observations), 0)
        if validation is not None:
            self.pruned_nodes = self._prune(self.root, validation)
        return self

    def _grow(self, rows: list[AuctionObservation], depth: int) -> _Node:
        node = _Node(rows, depth, distribution=_distribution(rows, self.estimator))
        if depth >= self.max_depth or len(rows) < 2 * self.min_leaf_size:
            return node
        best = None
        features = set.intersection(*(set(r.features) for r in rows))
        for feature in sorted(features):
            values = {r.features[feature] for r in rows}
            if len(values) < 2:
                continue
            if self.max_categories is not None and len(values) > self.max_categories:
                raise ValueError(f"feature {feature!r} cardinality exceeds max_categories={self.max_categories}")
            result = cluster_categories(rows, feature, self.random_seed, self.estimator)
            left = [r for r in rows if r.features[feature] in result.left_values]
            right = [r for r in rows if r.features[feature] in result.right_values]
            if min(len(left), len(right)) < self.min_leaf_size or not left or not right:
                continue
            score = _kl(_distribution(left, self.estimator), _distribution(right, self.estimator))
            candidate = (score, feature, result.left_values, left, right)
            if best is None or candidate[0] > best[0] or (candidate[0] == best[0] and candidate[1] < best[1]):
                best = candidate
        if best is None or best[0] <= 1e-12:
            return node
        _, feature, left_values, left, right = best
        node.feature, node.left_values = feature, left_values
        node.known_values = frozenset(r.features[feature] for r in rows)
        node.left, node.right = self._grow(left, depth + 1), self._grow(right, depth + 1)
        return node

    def _route(self, features: dict[str, Any], node: _Node) -> _Node:
        while node.feature is not None and node.left and node.right:
            feature = node.feature
            value = features.get(feature)
            if feature not in features or value not in node.known_values:
                rng = random.Random(repr((self.random_seed, node.depth, feature, tuple(sorted(map(repr, node.known_values))))))
                node = node.left if rng.random() < .5 else node.right
            else:
                node = node.left if value in node.left_values else node.right
        return node

    def _route_to_child(self, features: dict[str, Any], node: _Node) -> _Node:
        if node.feature is None or node.left is None or node.right is None:
            return node
        value = features.get(node.feature)
        if node.feature not in features or value not in node.known_values:
            rng = random.Random(repr((self.random_seed, node.depth, node.feature, tuple(sorted(map(repr, node.known_values))))))
            return node.left if rng.random() < .5 else node.right
        return node.left if value in node.left_values else node.right

    def predict(self, features: dict[str, Any]) -> PriceDistribution:
        if self.root is None:
            raise ValueError("fit must be called before predict")
        distribution = self._route(features, self.root).distribution or PriceDistribution({}, 1)
        return PriceDistribution(dict(distribution.masses), distribution.tail_probability)

    def _nll(self, rows: list[AuctionObservation]) -> float:
        if not rows:
            return 0.0
        total = 0.0
        for row in rows:
            if self.root is None:
                raise ValueError("fit must be called before pruning")
            prediction = self._route(row.features, self.root).distribution or PriceDistribution({}, 1)
            if row.won:
                probability = prediction.masses.get(row.market_price, 0.0) if row.market_price is not None else 0.0
            else:
                # Strict win rule b > z: loss likelihood includes equality mass at z=b.
                probability = prediction.tail_probability + math.fsum(
                    mass for price, mass in prediction.masses.items() if price >= row.bid)
            total -= math.log(max(probability, 1e-12))
        return total

    def _prune(self, node: _Node, rows: list[AuctionObservation]) -> int:
        if node.left is None or node.right is None:
            return 0
        left, right = node.left, node.right
        original_root = self.root
        if self.root is not node:
            self.root = node
        left_rows = [r for r in rows if self._route_to_child(r.features, node) is left]
        right_rows = [r for r in rows if self._route_to_child(r.features, node) is right]
        pruned = self._prune(left, left_rows) + self._prune(right, right_rows)
        before = self._nll(rows)
        feature, values, known = node.feature, node.left_values, node.known_values
        node.left = node.right = None
        node.feature = None
        after = self._nll(rows)
        if after <= before:
            self.root = original_root
            return pruned + 1
        node.left, node.right, node.feature, node.left_values, node.known_values = left, right, feature, values, known
        self.root = original_root
        return pruned


class _FixedDistribution:
    def __init__(self, distribution: PriceDistribution):
        self.distribution = distribution

    def predict(self, features: dict[str, Any]) -> PriceDistribution:
        return self.distribution


def fit_baseline(name: str, observations: list[AuctionObservation]) -> _FixedDistribution:
    """Fit paper baselines: NM (wins only), SM (Kaplan-Meier), MM (proxy below)."""
    if name not in {"NM", "SM", "MM"}:
        raise ValueError("baseline must be NM, SM, or MM")
    if not observations:
        raise ValueError("observations must not be empty")
    if name == "NM":
        return _FixedDistribution(_distribution(observations, "normal"))
    if name == "SM":
        return _FixedDistribution(_distribution(observations, "survival"))
    raise NotImplementedError(
        "MM needs Wu et al. (2015)'s linear/censored regression model; Wang (2016) does not specify it"
    )
