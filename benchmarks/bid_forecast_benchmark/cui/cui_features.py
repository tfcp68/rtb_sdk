"""Feature scoring and held-out template selection for Cui et al. (2011)."""

from __future__ import annotations

import math
from collections import Counter
from itertools import product
from typing import Any, Mapping, Sequence

from scipy.stats import entropy

STAR = "*"


def _entropy(values: Sequence[Any]) -> float:
    return float(entropy(list(Counter(values).values()), base=2))


def symmetric_uncertainty(features: Sequence[Any], target: Sequence[Any]) -> float:
    """Return normalized information gain SU(feature,target) from equation (1)."""
    if len(features) != len(target) or not features:
        raise ValueError("features and target must have the same non-zero length")
    hx, hy = _entropy(features), _entropy(target)
    denom = hx + hy
    if denom == 0:
        return 0.0
    joint = list(zip(features, target))
    return max(0.0, min(1.0, 2.0 * (hx + hy - _entropy(joint)) / denom))


def fcbf_select(features: Mapping[str, Sequence[Any]], target: Sequence[Any],
                threshold: float = 0.0) -> list[str]:
    """Fast correlation-based filter: retain relevant features, prune SU-redundancy."""
    if not features or threshold < 0 or not math.isfinite(threshold):
        raise ValueError("features and a finite non-negative threshold are required")
    if any(len(values) != len(target) or not target for values in features.values()):
        raise ValueError("all feature columns and target must have equal non-zero length")
    relevance = {name: symmetric_uncertainty(values, target) for name, values in features.items()}
    ordered = sorted((name for name in features if relevance[name] > threshold),
                     key=lambda name: (-relevance[name], list(features).index(name)))
    selected = []
    for name in ordered:
        if any(symmetric_uncertainty(features[name], features[kept]) >= relevance[name]
               for kept in selected):
            continue
        selected.append(name)
    return selected


def select_templates(
    samples: Sequence[Mapping[str, Any]], impressions: Sequence[float],
    feature_weights: Mapping[str, float], tree: Any, k: int = 30,
) -> list[tuple[str, ...]]:
    """Select templates by Cui Algorithm 1 (quality then held-out traffic coverage)."""
    names = tuple(feature_weights)
    if len(samples) != len(impressions) or not samples or k < 1 or not names:
        raise ValueError("need aligned non-empty samples/impressions, features and k >= 1")
    dimensions = len(tree.feature_names)
    if any(name not in feature_weights for name in tree.feature_names):
        raise ValueError("feature_weights must cover every star-tree dimension")
    if dimensions > 20:
        raise ValueError("template enumeration is limited to 20 dimensions")
    if any(not math.isfinite(float(w)) or float(w) < 0 for w in impressions):
        raise ValueError("impressions must be finite and non-negative")
    weights = [float(feature_weights[name]) for name in tree.feature_names]
    names = tuple(tree.feature_names)
    templates = list(product((STAR, "v"), repeat=dimensions))
    quality = {t: sum(weights[i] for i, mode in enumerate(t) if mode == "v") for t in templates}
    ordered = sorted(templates, key=lambda t: (-quality[t], t))
    coverage: dict[tuple[str, ...], float] = {}
    for sample, imp in zip(samples, impressions):
        for template in ordered:
            path = tuple(sample.get(name, STAR) if mode == "v" else STAR for name, mode in zip(names, template))
            if tree.get(path) is not None:
                coverage[template] = coverage.get(template, 0.0) + float(imp)
                break
    chosen = sorted(templates, key=lambda t: (-coverage.get(t, 0.0), -quality[t], t))[:k]
    all_star = (STAR,) * dimensions
    if all_star not in chosen:
        chosen[-1] = all_star
    return [tuple(str(part) for part in template) for template in chosen]
