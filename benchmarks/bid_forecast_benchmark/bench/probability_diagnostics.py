"""Evaluator-only probability and local decision-quality metrics for frozen bid policies."""
from __future__ import annotations

import numpy as np

EPSILON = 1e-6  # clipping bound for Bernoulli log-loss
ECE_BINS = 10
VERSION = "chosen-bid-probability-v1"
BOUNDARY_TOLERANCE = 1e-12


def _aligned(F, inv, grid):
    F, inv, grid = np.asarray(F, float), np.asarray(inv, int), np.asarray(grid, float)
    if F.ndim != 2 or F.shape[1] != len(grid) or inv.ndim != 1:
        raise ValueError("probability matrix and grid shape must align")
    if not np.isfinite(F).all() or not np.isfinite(grid).all() or np.any(np.diff(grid) <= 0):
        raise ValueError("probabilities and grid must be finite and grid strictly increasing")
    if np.any((F < -BOUNDARY_TOLERANCE) | (F > 1 + BOUNDARY_TOLERANCE)) or np.any((inv < 0) | (inv >= len(F))):
        raise ValueError("probabilities or row mapping out of range")
    # Normalize only floating-point boundary noise for scoring; the frozen policy matrix stays untouched.
    return np.clip(F, 0.0, 1.0), inv, grid


def probability_metrics(F, inv, grid, bids, z, eligible, values=None):
    """Score exact F-grid bid entries versus strict outcome z < b, on v>0 rows only."""
    F, inv, grid = _aligned(F, inv, grid)
    bids, z, eligible = np.asarray(bids, float), np.asarray(z, float), np.asarray(eligible, bool)
    if not (len(inv) == len(bids) == len(z) == len(eligible)):
        raise ValueError("row arrays must have equal shape")
    if not np.isfinite(bids).all() or not np.isfinite(z).all():
        raise ValueError("bids and prices must be finite")
    idx = np.searchsorted(grid, bids)
    if np.any(idx >= len(grid)) or not np.array_equal(grid[np.minimum(idx, len(grid)-1)], bids):
        raise ValueError("each bid must equal an entry in grid")
    if values is not None:
        values = np.asarray(values, float)
        if values.shape != bids.shape or not np.isfinite(values).all():
            raise ValueError("values must be finite and aligned to bids")
    selected = eligible
    p = F[inv[selected], idx[selected]]
    y = z[selected] < bids[selected]
    bins = []
    bin_idx = np.minimum((p * ECE_BINS).astype(int), ECE_BINS - 1)
    for k in range(ECE_BINS):
        mask = bin_idx == k
        bins.append({"count": int(mask.sum()), "predicted_mean": float(p[mask].mean()) if mask.any() else None,
                     "observed_mean": float(y[mask].mean()) if mask.any() else None})
    n = len(p)
    clipped = np.clip(p, EPSILON, 1 - EPSILON)
    market_profit_actual = float(np.sum((values[selected] - bids[selected]) * y)) if values is not None else None
    return {"status": "available", "n": n, "n_all": len(bids), "positive_bid_n": int(np.sum(selected & (bids > 0))),
            "mean_predicted_win": float(p.mean()) if n else None,
            "mean_observed_win": float(y.mean()) if n else None,
            "gap": float(p.mean() - y.mean()) if n else None,
            "brier": float(np.mean((p-y)**2)) if n else None,
            "logloss": float(-np.mean(y*np.log(clipped) + (~y)*np.log1p(-clipped))) if n else None,
            "logloss_epsilon": EPSILON, "ece": float(sum(x["count"] * abs(x["predicted_mean"] - x["observed_mean"])
                                                            for x in bins if x["count"]) / n) if n else None,
            "ece_bins": bins, "confidently_wrong_count": int(np.sum(((p == 0) & y) | ((p == 1) & ~y))),
            "expected_market_profit": float(np.sum((values[selected] - bids[selected]) * p)) if values is not None else None,
            "actual_market_profit": market_profit_actual,
            "expected_market_profit_per_eligible": float(np.mean((values[selected] - bids[selected]) * p)) if n and values is not None else None,
            "actual_market_profit_per_eligible": market_profit_actual / n if n and market_profit_actual is not None else None,
            "expected_minus_actual_market_profit": (float(np.sum((values[selected] - bids[selected]) * (p-y)))
                                                    if n and values is not None else None)}


def local_oracle_metrics(values, z, bids, grid):
    """Per-row best feasible grid bid knowing current z; strict win requires next grid point > z."""
    values, z, bids, grid = (np.asarray(x, float) for x in (values, z, bids, grid))
    if not (values.shape == z.shape == bids.shape) or grid.ndim != 1 or not np.isfinite(grid).all() or np.any(np.diff(grid) <= 0):
        raise ValueError("oracle inputs must be aligned and grid finite/increasing")
    if not np.isfinite(values).all() or not np.isfinite(z).all() or not np.isfinite(bids).all():
        raise ValueError("oracle row inputs must be finite")
    on_grid = np.isin(bids, grid)
    idx = np.searchsorted(grid, z, side="right")
    feasible = (idx < len(grid)) & (values > 0)
    oracle_bids = np.zeros(len(z), float)
    oracle_bids[feasible] = grid[idx[feasible]]
    feasible &= oracle_bids < values
    oracle_margin = np.where(feasible, values - oracle_bids, 0.)
    actual_margin = np.where((values > 0) & (bids > z), values - bids, 0.)
    return {"oracle_bids": oracle_bids.tolist(), "oracle_margin_sum": float(oracle_margin.sum()),
            "actual_margin_sum": float(actual_margin.sum()), "regret_sum": float((oracle_margin-actual_margin).sum()),
            "actual_bids_all_on_grid": bool(on_grid.all()),
            "interpretation": "grid-constrained regret; may be negative if actual bids are outside GRID",
            "scope": "local instantaneous feasible GRID optimum; not global-budget optimal or deployable"}
