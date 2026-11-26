"""Probability diagnostics with explicit tie handling and user-cluster uncertainty."""
from __future__ import annotations

import numpy as np


def calibration(y, p, bins=10):
    group = np.minimum((p * bins).astype(int), bins - 1)
    rows = []
    for b in range(bins):
        m = group == b
        if m.any():
            rows.append(dict(bin=b, low=b / bins, high=(b + 1) / bins, n=int(m.sum()),
                             predicted=float(p[m].mean()), actual=float(y[m].mean()),
                             gap=float(p[m].mean() - y[m].mean())))
    return rows


def ranking(y, p):
    # Equal scores enter together: AP uses threshold groups, AUC gives ties half credit.
    order = np.argsort(-p, kind="stable")
    yy, pp = y[order], p[order]
    ends = np.r_[np.flatnonzero(pp[1:] != pp[:-1]) + 1, len(y)]
    positives = np.diff(np.r_[0, np.cumsum(yy)[ends - 1]])
    negatives = np.diff(np.r_[0, ends]) - positives
    total_pos, total_neg = y.sum(), len(y) - y.sum()
    ap = float(np.sum(positives / total_pos * np.cumsum(positives) / ends)) if total_pos else None
    auc = float(np.sum(positives * (total_neg - np.cumsum(negatives) + .5 * negatives)) /
                (total_pos * total_neg)) if total_pos and total_neg else None
    return auc, ap


def selection(y, p, quotas):
    order = np.argsort(-p, kind="stable")
    yy, pp = y[order], p[order]
    rows = []
    for q in sorted(set(quotas)):
        k = max(1, int(np.ceil(q * len(y))))
        threshold = pp[k - 1]
        above, equal = pp > threshold, pp == threshold
        # Expected successes under uniform random tie breaking; no outcome-dependent ordering.
        successes = yy[above].sum() + (k - above.sum()) * yy[equal].mean()
        st = float(successes / k)
        rows.append(dict(q=q, selected=k, threshold=float(threshold), sellthrough=st,
                         lift=st / float(y.mean()) if y.any() else None))
    return rows


def selection_over_time(y, p, ts, quota=.8, interval=3600):
    """Retrospective top-quota selection within each observed time bucket."""
    y, p, ts = np.asarray(y), np.asarray(p), np.asarray(ts)
    if y.ndim != 1 or y.shape != p.shape or y.shape != ts.shape:
        raise ValueError('Need aligned one-dimensional outcomes, probabilities and times')
    if not 0 < quota <= 1 or interval <= 0:
        raise ValueError('Need quota in (0,1] and interval > 0')
    order = np.argsort(ts, kind='stable')
    buckets = ts[order] // interval
    bounds = np.r_[0, np.flatnonzero(buckets[1:] != buckets[:-1]) + 1, len(ts)]
    rows = []
    for start, end in zip(bounds[:-1], bounds[1:]):
        ii = order[start:end]
        if not len(ii):
            continue
        selected = selection(y[ii], p[ii], [quota])[0]
        rows.append(dict(start_s=int(buckets[start] * interval),
                         end_s=int((buckets[start] + 1) * interval),
                         n=len(ii), actual=float(y[ii].mean()), **selected))
    return rows


def metrics(y, p, baseline, bins=10, quota=.8):
    y, p = np.asarray(y, dtype=float), np.asarray(p, dtype=float)
    if not len(y) or p.shape != y.shape or not np.isin(y, [0, 1]).all():
        raise ValueError("Need nonempty aligned binary outcomes and probabilities")
    if not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise ValueError("Probabilities must be finite and in [0,1]")
    clipped = np.clip(p, 1e-15, 1 - 1e-15)
    brier = float(np.mean((p - y) ** 2))
    reference = float(np.mean((baseline - y) ** 2))
    cal = calibration(y, p, bins)
    auc, ap = ranking(y, p)
    return dict(n=len(y), actual=float(y.mean()), predicted=float(p.mean()), brier=brier,
                logloss=float(np.mean(-y * np.log(clipped) - (1 - y) * np.log1p(-clipped))),
                brier_skill=1 - brier / reference if reference else None,
                bias=float(np.mean(p - y)),
                ece=sum(r['n'] * abs(r['gap']) for r in cal) / len(y),
                rmsce=float(np.sqrt(sum(r['n'] * r['gap'] ** 2 for r in cal) / len(y))),
                roc_auc=auc, average_precision=ap, calibration=cal,
                selection=selection(y, p, [i / 10 for i in range(1, 11)] + [quota]))


def cluster_intervals(y, p, user, bins=10, repeats=200, seed=42):
    """Percentile bootstrap: resample whole users, preserving their correlated requests."""
    _, inv = np.unique(user, return_inverse=True)
    n_users = int(inv.max()) + 1
    if n_users < 2 or repeats < 2:
        return dict(users=n_users, repeats=repeats, metrics={}, calibration={})
    p = np.asarray(p, dtype=float)
    y = np.asarray(y, dtype=float)
    pc = np.clip(p, 1e-15, 1 - 1e-15)
    losses = {'brier': (p-y)**2, 'logloss': -y*np.log(pc)-(1-y)*np.log1p(-pc), 'bias': p-y}
    counts = np.bincount(inv)
    sums = {name: np.bincount(inv, weights=v) for name, v in losses.items()}
    groups = np.minimum((p * bins).astype(int), bins - 1)
    bc = np.zeros((n_users, bins)); by = bc.copy(); bp = bc.copy()
    np.add.at(bc, (inv, groups), 1)
    np.add.at(by, (inv, groups), y)
    np.add.at(bp, (inv, groups), p)
    rng = np.random.default_rng(seed)
    samples = {name: [] for name in sums}
    actual, gap = [], []
    for _ in range(repeats):
        weights = np.bincount(rng.integers(n_users, size=n_users), minlength=n_users)
        denom = weights @ counts
        for name, v in sums.items():
            samples[name].append(float(weights @ v / denom))
        c = weights @ bc
        a = np.divide(weights @ by, c, out=np.full(bins, np.nan), where=c > 0)
        pred = np.divide(weights @ bp, c, out=np.full(bins, np.nan), where=c > 0)
        actual.append(a); gap.append(pred - a)
    def interval(v):
        v = np.asarray(v); v = v[np.isfinite(v)]
        return np.quantile(v, [.025, .975]).tolist() if len(v) else None
    return dict(users=n_users, repeats=repeats,
                metrics={k: interval(v) for k, v in samples.items()},
                calibration={str(b): dict(actual=interval(np.asarray(actual)[:, b]),
                                          gap=interval(np.asarray(gap)[:, b])) for b in range(bins)})
