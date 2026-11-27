"""Least-squares gradient-boosted trees for Cui et al. (2011) Eq. (2), backed by XGBoost.

Rows are dicts of heterogeneous values: numeric columns (any real number type, numpy included) stay numeric,
everything else becomes a pandas category. Categorical splits are one-vs-rest (max_cat_to_onehot); the paper does
not specify how categories are split, this is our choice. Values unseen at fit time and None are routed as missing.
Numeric splits are histogram-binned (256 bins), so thresholds can differ slightly from exact CART.

min_samples_leaf: XGBoost limits leaf size only by the sum of sample weights (min_child_weight), not by a row count.
With unit weights the two coincide. With other weights we use min_samples_leaf × (mean weight): a leaf must carry
the weight of min_samples_leaf average rows. A single heavy row can therefore form its own leaf — documented, not a
row-count guarantee.
max_depth=0 means a constant model (the weighted mean), as in a depth-0 CART; XGBoost itself reads 0 as "no limit".
"""

from __future__ import annotations

import math
from numbers import Real
from typing import Any, Sequence

import numpy as np
import pandas as pd
import xgboost as xgb


def _is_number(value: Any) -> bool:
    return value is None or (isinstance(value, Real) and not isinstance(value, (bool, np.bool_)))


class GradientBoostingRegressor:
    def __init__(self, n_estimators: int = 30, learning_rate: float = 0.1,
                 max_depth: int = 2, min_samples_leaf: int = 2):
        if n_estimators < 1 or not 0 < learning_rate <= 1 or max_depth < 0 or min_samples_leaf < 1:
            raise ValueError("invalid boosting configuration")
        self.n_estimators, self.learning_rate = n_estimators, learning_rate
        self.max_depth, self.min_samples_leaf = max_depth, min_samples_leaf
        self.feature_names: list[str] = []
        self.categories: dict[str, list] = {}
        self.booster = None

    def _frame(self, rows: Sequence[dict[str, Any]]) -> pd.DataFrame:
        df = pd.DataFrame([{k: row.get(k) for k in self.feature_names} for row in rows], columns=self.feature_names)
        for name, cats in self.categories.items():
            df[name] = pd.Categorical(df[name].map(repr), categories=cats)
        return df.astype({n: float for n in self.feature_names if n not in self.categories})

    def fit(self, rows: Sequence[dict[str, Any]], targets: Sequence[float], sample_weight: Sequence[float] | None = None):
        if len(rows) != len(targets) or not rows:
            raise ValueError("rows and targets must have same non-zero length")
        weights = np.asarray(sample_weight if sample_weight is not None else [1.0] * len(rows), dtype=float)
        if len(weights) != len(rows) or not np.all(np.isfinite(weights)) or np.any(weights <= 0):
            raise ValueError("sample weights must be finite and positive")
        y = np.asarray(targets, dtype=float)
        if not np.all(np.isfinite(y)):
            raise ValueError("targets must be finite")
        self.feature_names = sorted({k for row in rows for k in row})
        self.categories = {name: sorted({repr(row.get(name)) for row in rows})
                           for name in self.feature_names if not all(_is_number(row.get(name)) for row in rows)}
        self.initial = float(np.average(y, weights=weights))
        self.booster = None
        if not self.feature_names or self.max_depth == 0:
            return self
        params = dict(objective="reg:squarederror", eta=self.learning_rate, max_depth=self.max_depth,
                      min_child_weight=self.min_samples_leaf * float(weights.mean()), reg_lambda=0.0,
                      tree_method="hist", max_cat_to_onehot=1 << 30, base_score=self.initial, nthread=1, verbosity=0)
        dm = xgb.DMatrix(self._frame(rows), y, weight=weights, enable_categorical=True)
        self.booster = xgb.train(params, dm, self.n_estimators)
        return self

    def predict(self, rows: Sequence[dict[str, Any]]) -> list[float]:
        if self.booster is None:
            return [self.initial] * len(rows)
        out = self.booster.predict(xgb.DMatrix(self._frame(rows), enable_categorical=True))
        return [float(v) if math.isfinite(v) else self.initial for v in out]

    def used_features(self) -> set[str]:
        return set(self.booster.get_score(importance_type="weight")) if self.booster is not None else set()
