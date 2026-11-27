"""Sparse bid star-tree history index (Cui et al., section 3.1.1)."""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from .cui_features import STAR


class StarTree:
    """Index weighted raw events at every wildcard specialization path."""

    def __init__(self, feature_names: Sequence[str], leaves: dict[tuple[Any, ...], tuple[float, float, int]]):
        self.feature_names = tuple(feature_names)
        self._leaves = leaves

    @classmethod
    def fit(cls, targets: Sequence[Mapping[str, Any]], bids: Sequence[float],
            impressions: Sequence[float] | None = None, min_impressions: float = 1) -> "StarTree":
        if len(targets) != len(bids) or not targets or min_impressions < 0:
            raise ValueError("targets/bids must be aligned and non-empty; min_impressions non-negative")
        names = tuple(targets[0])
        if not names or any(tuple(row) != names for row in targets):
            raise ValueError("all targets must have identical ordered features")
        weights = list(impressions) if impressions is not None else [1.0] * len(bids)
        if len(weights) != len(bids):
            raise ValueError("impressions must align with bids")
        # Keep both log-space history moments and arithmetic moments for Eq. 4.
        stats: dict[tuple[Any, ...], list[float]] = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0, 0.0])
        for row, bid, weight in zip(targets, bids, weights):
            if not math.isfinite(float(bid)) or bid <= 0 or not math.isfinite(float(weight)) or weight <= 0:
                raise ValueError("bids and impression weights must be finite and positive")
            vals = tuple(row[name] for name in names)
            log_bid = math.log(float(bid))
            for mask in range(1 << len(names)):
                path = tuple(STAR if mask & (1 << i) else vals[i] for i in range(len(names)))
                entry = stats[path]
                entry[0] += weight * log_bid
                entry[1] += weight * log_bid**2
                entry[2] += weight
                entry[3] += weight * float(bid)
                entry[4] += weight * float(bid)**2
        leaves = {}
        for path, (sum_log, sum_sq, count, sum_bid, sum_bid_sq) in stats.items():
            if count < min_impressions:
                continue
            log_mean = sum_log / count
            log_std = math.sqrt(max(0.0, sum_sq / count - log_mean**2))
            # Log moments are retained/calculated per paper; Eq. 4 maps them back to moments.
            mean = sum_bid / count
            std = math.sqrt(max(0.0, sum_bid_sq / count - mean**2))
            leaves[path] = (mean, std, int(count) if count.is_integer() else count)
        return cls(names, leaves)

    def get(self, path: Sequence[Any]) -> tuple[float, float, int] | None:
        return self._leaves.get(tuple(path))

    def __contains__(self, path: Sequence[Any]) -> bool:
        return tuple(path) in self._leaves
