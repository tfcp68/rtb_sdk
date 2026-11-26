"""
Routers: for each request of the pool decide "send to the manager or not".

route(ts, user, combo) -> bool mask of the chunk (True only inside the pool)
observe(ts, user, combo, sent, codes) — feedback after the chunk: codes of the sent requests (200/204)

Chunk = a control interval (1 hour by default): the model, the threshold and the quota correction are
updated between the chunks, inside a chunk everything is vectorized.
"""
from __future__ import annotations

import numpy as np


class Router:
    name = "base"

    def __init__(self, pool_mask: np.ndarray, combos: np.ndarray, seed: int = 0):
        self.pool_mask = pool_mask
        self.combos = combos
        self.rng = np.random.default_rng(seed)

    def route(self, ts, user, combo) -> np.ndarray:
        raise NotImplementedError

    def observe(self, ts, user, combo, sent, codes) -> None:
        pass


class SendAll(Router):
    name = "all"

    def route(self, ts, user, combo):
        return self.pool_mask[combo]


class RandomShare(Router):
    """Random share q of the pool — the baseline and the unbiased policy of the open run."""
    name = "random"

    def __init__(self, pool_mask, combos, q: float, seed: int = 0):
        super().__init__(pool_mask, combos, seed)
        self.q = q

    def route(self, ts, user, combo):
        return self.pool_mask[combo] & (self.rng.random(len(combo)) < self.q)


class ThresholdQuota(Router):
    """
    strategy.md §3: send if p̂(x) ≥ τ(t), τ is the quantile of p̂ over the recent pool requests such that
    the share of sent ones is q. Plus:
      * ε — a share of uniformly random pool requests (unbiased estimates, §5);
      * ties at the threshold are broken randomly (many profiles have an equal p̂);
      * quota feedback: q_eff = q + gain·(planned − sent)/expected_chunk_pool.
    The model is updated online with the outcomes of the sent requests.
    """

    def __init__(self, pool_mask, combos, predictor, q: float, eps: float = 0.02, seed: int = 0,
                 ref_chunks: int = 24, ref_sample: int = 20_000, gain: float = 0.5, seed_ref=None, ts_shift: int = 0):
        super().__init__(pool_mask, combos, seed)
        self.pred, self.q, self.eps = predictor, q, eps
        # the predictor lives in the global time of the logs (user state by days); the stand gives time from the range start
        self.ts_shift = ts_shift
        # predictors with the per-user state: the score depends on the moment, so the reference sample keeps
        # the scores made at route time instead of rescoring old requests with the current state
        self.stateful = getattr(predictor, "stateful", False)
        self._pending = None
        self.ref_chunks, self.ref_sample, self.gain = ref_chunks, ref_sample, gain
        self.name = f"{predictor.name}"
        self.ref: list[tuple] = []       # (ts, user, tags) of the pool requests of the last chunks
        self.pool_counts: list[int] = []
        self.pool_seen = 0
        self.sent_total = 0
        if seed_ref is not None:
            self.ref.append(seed_ref)

    def _threshold(self, f: float):
        if self.stateful:
            s = np.sort(np.concatenate(self.ref))[::-1]
        else:
            ts = np.concatenate([r[0] for r in self.ref]); us = np.concatenate([r[1] for r in self.ref])
            tg = np.concatenate([r[2] for r in self.ref])
            s = np.sort(self.pred.score(tg, ts, us))[::-1]
        f = min(max(f, 0.0), 1.0)
        if f >= 1.0:
            return -np.inf, 1.0
        if f <= 0.0:
            return np.inf, 0.0
        tau = s[min(int(f * len(s)), len(s) - 1)]
        gt, eq = float((s > tau).mean()), float((s == tau).mean())
        return tau, min(max((f - gt) / eq, 0.0), 1.0) if eq > 0 else 0.0

    def route(self, ts, user, combo):
        in_pool = self.pool_mask[combo]
        idx = np.flatnonzero(in_pool)
        send = np.zeros(len(combo), dtype=bool)
        if len(idx) == 0:
            return send
        if hasattr(self.pred, "observe_pool"):   # our own pool traffic of the chunk; features look only before each t
            self.pred.observe_pool(ts[idx], user[idx])
        q_eff = self.q
        if self.pool_counts:
            expected = self.pool_counts[-24] if len(self.pool_counts) >= 24 else self.pool_counts[-1]
            err = self.q * self.pool_seen - self.sent_total
            q_eff = self.q + self.gain * err / max(expected, 1)
        q_thr = (min(max(q_eff, 0.0), 1.0) - self.eps) / (1 - self.eps)
        if not self.ref:
            send[idx] = self.rng.random(len(idx)) < self.q
            if self.stateful:
                self._pending = self.pred.score(self.combos[combo[idx]], ts[idx] + self.ts_shift, user[idx])
            return send
        tau, tie_p = self._threshold(q_thr)
        p = self.pred.score(self.combos[combo[idx]], ts[idx] + self.ts_shift, user[idx])
        self._pending = p
        pick = (p > tau) | ((p == tau) & (self.rng.random(len(idx)) < tie_p))
        pick |= self.rng.random(len(idx)) < self.eps
        send[idx] = pick
        return send

    def observe(self, ts, user, combo, sent, codes):
        idx = np.flatnonzero(self.pool_mask[combo])
        self.pool_seen += len(idx)
        self.pool_counts.append(len(idx))
        self.sent_total += int(sent.sum())
        if len(idx):
            sub = idx if len(idx) <= self.ref_sample else self.rng.choice(idx, self.ref_sample, replace=False)
            if self.stateful:
                pos = np.arange(len(idx)) if len(idx) <= self.ref_sample else self.rng.choice(len(idx), self.ref_sample, replace=False)
                self.ref.append(self._pending[pos])
            else:
                self.ref.append((ts[sub], user[sub], self.combos[combo[sub]]))
            self.ref = self.ref[-self.ref_chunks:]
        si = np.flatnonzero(sent)
        if len(si):
            self.pred.update(self.combos[combo[si]], (np.asarray(codes) == 200), ts[si] + self.ts_shift, user[si])
