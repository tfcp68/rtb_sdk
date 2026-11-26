import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "benchmarks" / "closed_stand"))
from predictors import HierBetaUser, _fit_logit


def test_bounded_training_preserves_full_user_history():
    vocab = ["Region", "Device", "Child", "Category", "Channel"]
    tags = np.array([[1, 1, 0, 0, 1]] * 30, dtype=np.uint16)
    ts = np.arange(30) * 60
    users = np.arange(30) % 3
    outcomes = np.arange(30) % 2
    full = HierBetaUser(vocab, max_rows=100)
    limited = HierBetaUser(vocab, max_rows=10)
    full.update(tags, outcomes, ts, users)
    limited.update(tags, outcomes, ts, users)
    assert limited.buf_n == 10
    assert limited.state == full.state
    np.testing.assert_allclose(np.concatenate(limited.buf_X), np.concatenate(full.buf_X)[-10:])
    limited.update(tags[:6], outcomes[:6], ts[:6] + 3000, users[:6])
    assert limited.buf_n == 10
    assert sum(map(len, limited.buf_X)) == 10


def test_logit_accumulates_batches_like_dense_irls():
    rng = np.random.default_rng(7)
    X = rng.normal(size=(50_010, 3)).astype(np.float32)
    X[:, 0] = 1
    y = rng.integers(0, 2, len(X))
    w = np.zeros(3)
    p = np.full(len(X), 0.5)
    dense = X.astype(np.float64)
    hessian = dense.T @ (dense * (p * (1 - p))[:, None]) + np.diag([0, 1, 1]) + 1e-6 * np.eye(3)
    expected = np.linalg.solve(hessian, dense.T @ (y - p))
    np.testing.assert_allclose(_fit_logit(X, y, w, iters=1), expected, atol=1e-10)
