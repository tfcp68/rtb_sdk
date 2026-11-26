"""
Models of P(200 | request): the probability that the manager (the external auction) sells a pool request.

Every model has the same interface; inside each one works with the data in its own way:

    fit(tags, y, ts, user)      train on a log of answered requests (y = 1 for 200), replacing the model. Models with
                                a viewer history take the log's pool requests from observe_pool() calls made before fit.
    update(tags, y, ts, user)   online answers of the manager after the requests were sent; on an unfitted model = fit.
    observe_pool(ts, user)      online pool requests of the viewers (sent or not); no-op for models without a history.
    score(tags, ts, user)       p̂ for each request.
    save(path) / load(path)     a directory with meta.json + state.npz (+ the GBM's own model file).

Inputs: `tags` — an (n × n_tags) matrix of integer codes, one column per vocab in the order of `vocab_order`
(codes < 512); `ts` — integer seconds that count from a local midnight (the hour of day is ts % 86400 // 3600);
`user` — a non-negative integer id of the viewer (a hash, < 2^31). The models must not know the manager's
campaigns — only the request features and the 200/other outcomes.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

BITS = 9            # vocab sizes < 512
H = 3_600
DAY = 86_400
BIG = 10 ** 7       # history key = user·BIG + ts (ts < 10^7 s ≈ 115 days)
NO_PREV = 2 * DAY   # dt_prev_pool of a viewer without a previous pool request


def with_hour(tags, ts) -> np.ndarray:
    """tags + a column with the hour of the local day."""
    return np.column_stack([np.asarray(tags, dtype=np.int64), (np.asarray(ts, dtype=np.int64) % DAY) // H])


def pack_tags(tags: np.ndarray) -> np.ndarray:
    out = np.zeros(len(tags), dtype=np.int64)
    for i in range(tags.shape[1]):
        out |= tags[:, i].astype(np.int64) << (BITS * i)
    return out


def _key(user, ts) -> np.ndarray:
    return np.asarray(user, dtype=np.int64) * BIG + np.asarray(ts, dtype=np.int64)


class Predictor:
    name = "base"
    stateful = False
    n_tags: int | None = None   # expected number of tag columns, None = not checked

    def fit(self, tags, y, ts, user) -> "Predictor":
        raise NotImplementedError

    def update(self, tags, y, ts, user) -> None:
        raise NotImplementedError

    def observe_pool(self, ts, user) -> None:
        pass

    def score(self, tags, ts, user) -> np.ndarray:
        raise NotImplementedError

    def _check(self, tags=None, **cols) -> int:
        """Validates the input at the boundary; returns the number of rows."""
        n = None
        if tags is not None:
            tags = np.asarray(tags)
            if tags.ndim != 2 or (self.n_tags is not None and tags.shape[1] != self.n_tags):
                raise ValueError(f"{self.name}: tags must be an (n × {self.n_tags}) matrix, got shape {tags.shape}")
            n = len(tags)
        for k, v in cols.items():
            if v is None:
                continue
            if np.ndim(v) != 1 or (n is not None and len(v) != n):
                raise ValueError(f"{self.name}: {k} must be 1-d with {n} rows, got shape {np.shape(v)}")
            n = len(v)
        return n or 0

    # ── persistence: meta.json (class + constructor config) + state.npz (+ the model file) ──
    def _config(self) -> dict:
        return {}

    def _arrays(self) -> dict:
        return {}

    def _set_arrays(self, z) -> None:
        pass

    def _save_model(self, path: Path) -> dict:
        return {}

    def _load_model(self, path: Path, meta: dict) -> None:
        pass

    def save(self, path) -> None:
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        extra = self._save_model(path)
        np.savez(path / "state.npz", **self._arrays())
        (path / "meta.json").write_text(json.dumps(dict(cls=type(self).__name__, config=self._config(), **extra),
                                                   ensure_ascii=False, indent=1), encoding="utf-8")

    @staticmethod
    def load(path) -> Predictor:
        path = Path(path)
        meta = json.loads((path / "meta.json").read_text(encoding="utf-8"))
        obj = MODEL_CLASSES[meta["cls"]](**meta["config"])
        with np.load(path / "state.npz") as z:
            obj._set_arrays(z)
        obj._load_model(path, meta)
        return obj


class ConstPredictor(Predictor):
    """The share of 200 over everything seen: a baseline without features."""
    name = "const"

    def __init__(self):
        self.k = self.n = 0

    def fit(self, tags, y, ts=None, user=None):
        self.k = self.n = 0
        self.update(tags, y)
        return self

    def update(self, tags, y, ts=None, user=None):
        self._check(y=y)
        self.k += int(np.sum(y))
        self.n += len(y)

    def score(self, tags, ts=None, user=None):
        return np.full(self._check(tags), self.k / self.n if self.n else 0.5)

    def _arrays(self):
        return {"k": self.k, "n": self.n}

    def _set_arrays(self, z):
        self.k, self.n = int(z["k"]), int(z["n"])


class HierBeta(Predictor):
    """strategy.md §4.1: Beta posterior over the hierarchy of profiles with shrinkage to the parent.

        p̂(profile) = (k + m · p̂(parent)) / (n + m)

    Levels are nested subsets of vocabs. A profile that was never seen gets the p̂ of the deepest known ancestor.
    The counters are updated online with every answer.
    """
    name = "hier_beta"

    DEFAULT_LEVELS = (
        (),
        ("Device",),
        ("Device", "Region"),
        ("Device", "Region", "Category", "Channel"),
        ("Device", "Region", "Child", "Category", "Channel"),
    )

    def __init__(self, vocab_order: list[str], levels=DEFAULT_LEVELS, m: float = 20.0):
        self.vocab_order, self.levels, self.m = list(vocab_order), tuple(tuple(lv) for lv in levels), m
        self.n_tags = len(self.vocab_order)
        self.masks = []
        for lv in self.levels:
            mask = 0
            for v in lv:
                mask |= ((1 << BITS) - 1) << (BITS * self.vocab_order.index(v))
            self.masks.append(mask)
        self._clear()

    def _clear(self):
        L = len(self.masks)
        self.keys = [np.zeros(0, np.int64) for _ in range(L)]
        self.k = [np.zeros(0) for _ in range(L)]
        self.n = [np.zeros(0) for _ in range(L)]
        self.p = [np.zeros(0) for _ in range(L)]
        self.root = 0.5
        self.total_n = 0

    def fit(self, tags, y, ts=None, user=None):
        self._clear()
        self.update(tags, y)
        return self

    def update(self, tags, y, ts=None, user=None):
        if self._check(tags, y=y) == 0:
            return
        packed = pack_tags(np.asarray(tags))
        y = np.asarray(y, dtype=np.float64)
        for li, mask in enumerate(self.masks):
            u, inv = np.unique(packed & mask, return_inverse=True)
            nk = np.bincount(inv, weights=y, minlength=len(u))
            nn = np.bincount(inv, minlength=len(u)).astype(np.float64)
            allk = np.concatenate([self.keys[li], u])
            uu, inv2 = np.unique(allk, return_inverse=True)
            self.k[li] = np.bincount(inv2, weights=np.concatenate([self.k[li], nk]), minlength=len(uu))
            self.n[li] = np.bincount(inv2, weights=np.concatenate([self.n[li], nn]), minlength=len(uu))
            self.keys[li] = uu
        self.total_n += len(y)
        self._refresh()

    def _refresh(self):
        # level 0 is the root (mask == 0 → a single key 0)
        k0, n0 = self.k[0].sum(), self.n[0].sum()
        self.root = k0 / n0 if n0 else 0.5
        self.p[0] = np.array([self.root])
        for li in range(1, len(self.masks)):
            parent_keys = self.keys[li] & self.masks[li - 1]
            pi = np.searchsorted(self.keys[li - 1], parent_keys)
            pp = self.p[li - 1][pi]
            self.p[li] = (self.k[li] + self.m * pp) / (self.n[li] + self.m)

    def score_loo(self, tags, y):
        """p̂ of the deepest level for the rows that are already inside the statistics, without their own outcome
        (leave-one-out): the training features of a second-stage model must not see their own label."""
        packed = pack_tags(np.asarray(tags))
        y = np.asarray(y, dtype=np.float64)
        li = len(self.masks) - 1
        q = packed & self.masks[li]
        idx = np.searchsorted(self.keys[li], q)
        pp = self.p[li - 1][np.searchsorted(self.keys[li - 1], q & self.masks[li - 1])]
        return (self.k[li][idx] - y + self.m * pp) / (self.n[li][idx] - 1 + self.m)

    def score(self, tags, ts=None, user=None):
        n = self._check(tags)
        if self.total_n == 0:
            return np.full(n, 0.5)
        packed = pack_tags(np.asarray(tags))
        p = np.full(n, self.root)
        for li in range(1, len(self.masks)):
            q = packed & self.masks[li]
            idx = np.searchsorted(self.keys[li], q)
            idx[idx >= len(self.keys[li])] = 0
            found = self.keys[li][idx] == q
            p[found] = self.p[li][idx[found]]
        return p

    def _config(self):
        return {"vocab_order": self.vocab_order, "levels": self.levels, "m": self.m}

    def _arrays(self):
        arr = {f"{a}{i}": getattr(self, a)[i] for a in ("keys", "k", "n") for i in range(len(self.masks))}
        return arr | {"total_n": self.total_n}

    def _set_arrays(self, z):
        L = len(self.masks)
        self.keys, self.k, self.n = ([z[f"{a}{i}"] for i in range(L)] for a in ("keys", "k", "n"))
        self.total_n = int(z["total_n"])
        if self.total_n:
            self._refresh()


class CatBoostPredictor(Predictor):
    """Model B (log_eda/models/catboost_model.py): CatBoost on the 5 tags (categorical) + hour.

    fit trains on the log (at most max_rows, uniform subsample). Online, update collects the answers and every
    `refit_every` updates (once per hour → once per day) the model is refit from scratch on the log + everything seen,
    keeping at most keep_rows of the latest rows. Trees: early stopping on a random 10% holdout.
    score predicts once per unique (tags, hour). After load() online refits use only the rows seen since the load.
    """
    name = "catboost"

    def __init__(self, vocab_order: list[str], refit_every: int = 24, max_rows: int = 500_000,
                 keep_rows: int = 5_000_000, seed: int = 0, **params):
        self.vocab_order = list(vocab_order)
        self.n_tags = len(self.vocab_order)
        self.cols = self.vocab_order + ["An hour"]
        self.params = {
            "loss_function": "Logloss",
            "iterations": 500,
            "learning_rate": 0.2,
            "depth": 6,
            "max_ctr_complexity": 2,
            "od_type": "Iter",
            "od_wait": 30,
            "random_seed": seed,
            "thread_count": 4,
            "verbose": False,
            "allow_writing_files": False
        } | params
        self.refit_every, self.max_rows, self.keep_rows, self.seed = refit_every, max_rows, keep_rows, seed
        self.rng = np.random.default_rng(seed)
        self.X, self.y = [], []
        self.pending = 0
        self.model = None

    def fit(self, tags, y, ts, user=None):
        self._check(tags, y=y, ts=ts)
        self.X, self.y, self.pending = [], [], 0
        self._append(tags, y, ts)
        self._fit()
        return self

    def update(self, tags, y, ts, user=None):
        if self._check(tags, y=y, ts=ts) == 0:
            return
        if self.model is None:
            self.fit(tags, y, ts, user)
            return
        self._append(tags, y, ts)
        self.pending += 1
        if self.pending >= self.refit_every:
            self._fit()

    def _append(self, tags, y, ts):
        self.X.append(with_hour(tags, ts).astype(np.int32))
        self.y.append(np.asarray(y, dtype=np.int8))

    def _fit(self):
        X, y = np.concatenate(self.X)[-self.keep_rows:], np.concatenate(self.y)[-self.keep_rows:]
        self.X, self.y, self.pending = [X], [y], 0
        self._train(X, y)

    def _frame(self, X):
        import pandas as pd
        df = pd.DataFrame(X, columns=self.cols)
        df[self.cols[:self.n_tags]] = df[self.cols[:self.n_tags]].astype(np.int64)   # tags are categorical, the rest numeric
        return df

    def _subsample(self, X, y):
        if len(y) > self.max_rows:
            i = self.rng.choice(len(y), self.max_rows, replace=False)
            X, y = X[i], y[i]
        return X, y, self.rng.random(len(y)) < 0.1

    def _train(self, X, y):
        from catboost import CatBoostClassifier
        X, y, hold = self._subsample(X, y)
        df = self._frame(X)
        self.model = CatBoostClassifier(**self.params, cat_features=self.cols[:self.n_tags]).fit(
            df[~hold], y[~hold], eval_set=(df[hold], y[hold]), use_best_model=True)

    def _predict(self, X) -> np.ndarray:
        if self.model is None:
            raise ValueError(f"{self.name}: the model is not fitted")
        return self.model.predict_proba(self._frame(X))[:, 1]

    def score(self, tags, ts, user=None):
        self._check(tags, ts=ts)
        X = with_hour(tags, ts)
        _, first, inv = np.unique(pack_tags(X), return_index=True, return_inverse=True)
        return self._predict(X[first])[inv.ravel()]

    def _config(self):
        params = {k: v for k, v in self.params.items() if k != "random_seed"}
        return dict(vocab_order=self.vocab_order, refit_every=self.refit_every, max_rows=self.max_rows,
                    keep_rows=self.keep_rows, seed=self.seed, **params)

    def _save_model(self, path):
        self.model.save_model(str(path / "model.cbm"))
        return {}

    def _load_model(self, path, meta):
        from catboost import CatBoostClassifier
        self.model = CatBoostClassifier()
        self.model.load_model(str(path / "model.cbm"))


class UserCatBoost(CatBoostPredictor):
    """CatBoost on tags + hour + the viewer's history. Every feature of a request (t, u) uses only the strict past:

      feedback (only needs update)   the manager's answers to u known before the current hour hs = t // H · H
                                     (answers arrive once per hour): n200_24h, nsent_24h over [hs − 24h, hs);
                                     n200_all and last_status (1/0, −1 = none) before hs.
      stream (stream=True)           our own pool requests of u, passed via observe_pool: npool_1h, npool_24h over
                                     [t − w, t), dt_prev_pool = t − the previous pool request (NO_PREV if none).
                                     Requests at ≥ t that are already in the history are outside every window.

    fit: the log's pool requests come from observe_pool() calls before it; the features are built on the whole log,
    the model is fit once, then the history is cleared (online the manager starts afresh). No online refit.

    The history is kept for `history_s` (2 days + 3 h): enough for requests up to ~26 h old, which covers re-scoring
    the last day of requests. Older events are folded into per-viewer aggregates (200s and the last answer, the last
    pool request), aggregates of viewers silent for `ttl_s` are dropped. history_s=None keeps everything.
    """
    STREAM = ["npool_1h", "npool_24h", "dt_prev_pool"]
    FEEDBACK = ["n200_24h", "nsent_24h", "n200_all", "last_status"]

    def __init__(self, vocab_order: list[str], stream: bool, max_rows: int = 700_000, seed: int = 0,
                 history_s: int | None = 2 * DAY + 3 * H, ttl_s: int = 7 * DAY, **params):
        super().__init__(vocab_order, max_rows=max_rows, seed=seed, **params)
        self.stream, self.history_s, self.ttl_s = stream, history_s, ttl_s
        self.name = "catboost_user" if stream else "catboost_fb"
        self.cols += (self.STREAM if stream else []) + self.FEEDBACK
        self._reset()

    def _reset(self):
        self.pool = np.zeros(0, np.int64)                                     # sorted keys of pool requests
        self.sent, self.sent_y = np.zeros(0, np.int64), np.zeros(0, np.int8)  # sorted keys of answered requests, y
        self.cum = np.zeros(1, np.int64)                                      # prefix sums of sent_y
        # aggregates of the events that left the history, per viewer (sorted by user)
        self.agg_user = np.zeros(0, np.int64)
        self.agg_200 = np.zeros(0, np.int64)       # 200s
        self.agg_last = np.zeros(0, np.int8)       # the last answer (−1 = none)
        self.agg_prev = np.zeros(0, np.int64)      # the last pool request (−1 = none)
        self.agg_seen = np.zeros(0, np.int64)      # the latest of these events, for ttl
        self.now = 0
        self.pruned_at = 0

    def observe_pool(self, ts, user):
        if not self.stream or self._check(ts=ts, user=user) == 0:
            return
        self.pool = np.sort(np.concatenate([self.pool, _key(user, ts)]))
        self._advance(int(np.max(ts)))

    def fit(self, tags, y, ts, user):
        self._check(tags, y=y, ts=ts, user=user)
        if self.stream and not len(self.pool):
            raise ValueError(f"{self.name}: observe_pool(pool log) must come before fit")
        self._add_answers(y, ts, user)
        self._train(self.features(tags, ts, user), np.asarray(y, np.int8))
        self._reset()
        return self

    def update(self, tags, y, ts, user):
        if self._check(tags, y=y, ts=ts, user=user) == 0:
            return
        if self.model is None:
            self.fit(tags, y, ts, user)
            return
        self._add_answers(y, ts, user)
        self._advance(int(np.max(ts)))

    def _add_answers(self, y, ts, user):
        k = np.concatenate([self.sent, _key(user, ts)])
        o = np.argsort(k, kind="stable")
        self.sent, self.sent_y = k[o], np.concatenate([self.sent_y, np.asarray(y, np.int8)])[o]
        self.cum = np.concatenate([[0], np.cumsum(self.sent_y)])

    # ── bounded history ──
    def _advance(self, ts_max: int):
        self.now = max(self.now, ts_max)
        if self.model is not None and self.history_s is not None and self.now - self.pruned_at >= H:
            self._prune(self.now - self.history_s)
            self.pruned_at = self.now

    def _prune(self, cutoff: int):
        old = (self.pool % BIG) < cutoff
        if old.any():
            k = self.pool[old]
            last = np.flatnonzero(np.r_[k[1:] // BIG != k[:-1] // BIG, True])   # the last old request of each viewer
            self._merge(k[last] // BIG, prev=k[last] % BIG)
            self.pool = self.pool[~old]
        old = (self.sent % BIG) < cutoff
        if old.any():
            k, y = self.sent[old], self.sent_y[old]
            first = np.flatnonzero(np.r_[True, k[1:] // BIG != k[:-1] // BIG])
            last = np.r_[first[1:] - 1, len(k) - 1]
            self._merge(k[first] // BIG, n200=np.add.reduceat(y.astype(np.int64), first), last=y[last], seen=k[last] % BIG)
            self.sent, self.sent_y = self.sent[~old], self.sent_y[~old]
            self.cum = np.concatenate([[0], np.cumsum(self.sent_y)])
        alive = self.agg_seen >= self.now - self.ttl_s
        if not alive.all():
            for a in ("agg_user", "agg_200", "agg_last", "agg_prev", "agg_seen"):
                setattr(self, a, getattr(self, a)[alive])

    def _merge(self, users, n200=None, last=None, prev=None, seen=None):
        """Folds events of `users` (unique, sorted) into the aggregates."""
        allu = np.union1d(self.agg_user, users)
        i_old, i_new = np.searchsorted(allu, self.agg_user), np.searchsorted(allu, users)
        n = len(allu)
        a200, alast, aprev, aseen = np.zeros(n, np.int64), np.full(n, -1, np.int8), np.full(n, -1, np.int64), np.zeros(n, np.int64)
        a200[i_old], alast[i_old], aprev[i_old], aseen[i_old] = self.agg_200, self.agg_last, self.agg_prev, self.agg_seen
        if n200 is not None:
            a200[i_new] += n200
            alast[i_new] = last
        if prev is not None:
            aprev[i_new] = prev
        aseen[i_new] = np.maximum(aseen[i_new], prev if prev is not None else seen)
        self.agg_user, self.agg_200, self.agg_last, self.agg_prev, self.agg_seen = allu, a200, alast, aprev, aseen

    def _agg(self, user, values, default):
        i = np.minimum(np.searchsorted(self.agg_user, user), max(len(self.agg_user) - 1, 0))
        if not len(self.agg_user):
            return np.full(len(user), default, dtype=values.dtype)
        return np.where(self.agg_user[i] == user, values[i], default)

    def features(self, tags, ts, user) -> np.ndarray:
        ts = np.asarray(ts, np.int64)
        uid = np.asarray(user, np.int64)
        u = uid * BIG
        f = [with_hour(tags, ts)]
        if self.stream:
            p = self.pool
            now = np.searchsorted(p, u + ts)
            prev = np.append(p, -1)[now - 1]                                  # −1 if nothing before
            agg_prev = self._agg(uid, self.agg_prev, -1)
            dt = np.where(prev >= u, u + ts - prev, np.where(agg_prev >= 0, ts - agg_prev, NO_PREV))
            f += [now - np.searchsorted(p, u + np.maximum(ts - H, 0)), now - np.searchsorted(p, u + np.maximum(ts - DAY, 0)), dt]
        hs = ts // H * H
        hi, lo, l0 = (np.searchsorted(self.sent, u + x) for x in (hs, np.maximum(hs - DAY, 0), 0))
        last = np.where(hi > l0, np.append(self.sent_y, -1)[hi - 1], self._agg(uid, self.agg_last, -1))
        f += [self.cum[hi] - self.cum[lo], hi - lo, self.cum[hi] - self.cum[l0] + self._agg(uid, self.agg_200, 0), last]
        return np.column_stack(f).astype(np.float64)

    def score(self, tags, ts, user=None):
        self._check(tags, ts=ts, user=user)
        return self._predict(self.features(tags, ts, user))

    def _config(self):
        return super()._config() | dict(stream=self.stream, history_s=self.history_s, ttl_s=self.ttl_s)

    def _arrays(self):
        names = ("pool", "sent", "sent_y", "agg_user", "agg_200", "agg_last", "agg_prev", "agg_seen")
        return {a: getattr(self, a) for a in names} | dict(now=self.now)

    def _set_arrays(self, z):
        for a in ("pool", "sent", "sent_y", "agg_user", "agg_200", "agg_last", "agg_prev", "agg_seen"):
            setattr(self, a, z[a])
        self.cum = np.concatenate([[0], np.cumsum(self.sent_y)])
        self.now = self.pruned_at = int(z["now"])


class _XGB:
    """XGBoost instead of CatBoost with the same data path: max_rows subsample, the same random 10% holdout,
    early stopping after 30 rounds, up to 500 trees, 4 threads. The tags use native categorical splits (hist):
    their codes are the categories, the feature types are stored in the booster, prediction goes straight from numpy.
    Params picked on a small grid (300k rows, the same holdout): CatBoost's lr 0.2 / depth 6 overfit (in the
    statistical sense) the high-cardinality tags within 25–100 trees."""

    def _xgb_init(self, n_cats, seed):
        self.n_cats = [int(c) for c in n_cats]
        self.xparams = {
            "learning_rate": 0.1,
            "max_depth": 8,
            "min_child_weight": 50,
            "reg_lambda": 5,
            "max_cat_threshold": 16,
            "tree_method": "hist",
            "objective": "binary:logistic",
            "eval_metric": "logloss",
            "nthread": 4,
            "seed": seed
        }
        self.n_trees, self.early_stopping = 500, 30

    def _train(self, X, y):
        import xgboost as xgb
        X, y, hold = self._subsample(X, y)
        X = X.astype(np.float32)
        types = ["c"] * self.n_tags + ["q"] * (X.shape[1] - self.n_tags)
        dm = lambda m: xgb.DMatrix(X[m], y[m], feature_types=types, enable_categorical=True)
        self.model = xgb.train(self.xparams, dm(~hold), self.n_trees, evals=[(dm(hold), "holdout")],
                               early_stopping_rounds=self.early_stopping, verbose_eval=False)

    def _predict(self, X) -> np.ndarray:
        if self.model is None:
            raise ValueError(f"{self.name}: the model is not fitted")
        return self.model.inplace_predict(np.asarray(X, np.float32), iteration_range=(0, self.model.best_iteration + 1))

    def _save_model(self, path):
        self.model.save_model(path / "model.json")
        return {"best_iteration": self.model.best_iteration}

    def _load_model(self, path, meta):
        import xgboost as xgb
        self.model = xgb.Booster()
        self.model.load_model(path / "model.json")
        self.model.set_attr(best_iteration=str(meta["best_iteration"]))


class XGBPredictor(_XGB, CatBoostPredictor):
    """`catboost` with XGBoost: tags + hour, refit every 24 updates."""
    name = "xgboost"

    def __init__(self, vocab_order, n_cats, seed: int = 0, **kw):
        super().__init__(vocab_order, seed=seed, **kw)
        self._xgb_init(n_cats, seed)

    def _config(self):
        return {"vocab_order": self.vocab_order, "n_cats": self.n_cats, "seed": self.seed, "refit_every": self.refit_every,
                    "max_rows": self.max_rows, "keep_rows": self.keep_rows}


class UserXGB(_XGB, UserCatBoost):
    """`catboost_fb` / `catboost_user` with XGBoost: the same viewer-history features, fit once on the log."""

    def __init__(self, vocab_order, n_cats, stream: bool, seed: int = 0, **kw):
        super().__init__(vocab_order, stream=stream, seed=seed, **kw)
        self.name = "xgb_user" if stream else "xgb_fb"
        self._xgb_init(n_cats, seed)

    def _config(self):
        return {"vocab_order": self.vocab_order, "n_cats": self.n_cats, "stream": self.stream, "seed": self.seed,
                    "max_rows": self.max_rows, "history_s": self.history_s, "ttl_s": self.ttl_s}


MODEL_CLASSES = {c.__name__: c for c in (ConstPredictor, HierBeta, CatBoostPredictor, UserCatBoost, XGBPredictor, UserXGB)}


class RuleTrie(Predictor):
    """Sparse tries over complementary targeting subsets, with parent smoothing.

    Each trie is stored as sorted packed prefix keys and counts. Combining
    their predictions by averaging avoids assuming that overlapping rules are
    independent campaigns. These are predictive segments, not campaign IDs.
    """
    name = "rule_trie"
    PATHS = (
        ("Child",), ("Device",), ("Region",),
        ("Category",), ("Channel",),
        ("Child", "Device"), ("Device", "Region"),
        ("Device", "Category"), ("Device", "Channel"),
    )

    def __init__(self, vocab_order, m=20.0):
        self.tries = [HierBeta(vocab_order, levels=((),) + tuple(path[:i]
                      for i in range(1, len(path) + 1)), m=m) for path in self.PATHS]

    def update(self, tags, y, ts=None, user=None):
        for trie in self.tries:
            trie.update(tags, y, ts, user)

    def score(self, tags, ts=None, user=None):
        return np.mean([trie.score(tags, ts, user) for trie in self.tries], axis=0)

    def top_rules(self, vocab_order, vocabs, min_count=100, limit=15):
        rules = []
        for path, trie in zip(self.PATHS, self.tries):
            for key, n, k, p in zip(trie.keys[-1], trie.n[-1], trie.k[-1], trie.p[-1]):
                if n < min_count:
                    continue
                values = {v: vocabs[v][int((int(key) >> (BITS * vocab_order.index(v))) & ((1 << BITS) - 1))]
                          for v in path}
                rules.append(dict(tags=values, count=int(n), successes=int(k), probability=float(p),
                                  lift=float(p - trie.root)))
        return sorted(rules, key=lambda r: abs(r["lift"]) * np.sqrt(r["count"]), reverse=True)[:limit]


DAY = 86_400
_SENT_EDGES = np.array([1, 2, 3, 5, 9])                       # sent to the manager today
_K200_EDGES = np.array([1, 2, 3])                             # of them 200 today
_SINCE_EDGES = np.array([120, 300, 600, 1200, 3600, 10800])   # seconds since the user's previous sent request
_NTOT_EDGES = np.array([1, 3, 10])                            # sent over the whole history


def _onehot(idx: np.ndarray, n: int) -> np.ndarray:
    """One-hot without the 0-th (baseline) column."""
    out = np.zeros((len(idx), n - 1), dtype=np.float32)
    nz = np.flatnonzero(idx > 0)
    out[nz, idx[nz] - 1] = 1.0
    return out


def _fit_logit(X: np.ndarray, y: np.ndarray, w0: np.ndarray, l2: float = 1.0, iters: int = 8) -> np.ndarray:
    """Ridge logistic regression by IRLS (the first column is the bias, it is not penalized)."""
    w = w0.copy()
    reg = np.full(X.shape[1], l2)
    reg[0] = 0.0
    for _ in range(iters):
        g = -reg * w
        H = np.diag(reg) + 1e-6 * np.eye(X.shape[1])
        for start in range(0, len(y), 50_000):
            xb = X[start:start + 50_000].astype(np.float64)
            yb = y[start:start + 50_000]
            p = 1.0 / (1.0 + np.exp(-np.clip(xb @ w, -30, 30)))
            g += xb.T @ (yb - p)
            H += xb.T @ (xb * (p * (1 - p))[:, None])
        step = np.linalg.solve(H, g)
        w += step
        if np.abs(step).max() < 1e-4:
            break
    return w


class HierBetaUser(Predictor):
    """strategy.md §4.1 + §4.2: the profile estimate and the user features in one model.

    Stage 1 is HierBeta (p̂ of the profile). Stage 2 is a logistic regression
        logit p = a + b·logit(p̂_profile) + user features
    The user features come from the history of the requests *sent to the manager* (only they have outcomes, and
    the training log contains only them, so train and online features are built the same way):
      * how many requests were sent to this user today, how many of them were 200  (hypothesis (a): the manager has
        its own frequency limits → p(200) falls with the number of sends);
      * the time since the previous sent request of the user (frequency windows, min_interval, VOD rhythm (b));
      * the outcome of the previous one;
      * the "lift" of the user: (200 − Σp̂) / (n + c) over the whole history, plus the history length.
    The state is a dict by user; during the training every row sees the state *before* itself.
    The profile part for the training rows is leave-one-out, otherwise the model over-trusts it.
    The second stage is refitted on the accumulated rows every `refit_every` updates (hours of the closed run).
    """
    name = "hier_user"
    stateful = True   # the score depends on the per-user state → the router keeps the scores made at route time

    def __init__(self, vocab_order: list[str], m: float = 20.0, l2: float = 1.0, refit_every: int = 24,
                 max_rows: int = 800_000, lift_c: float = 3.0):
        self.hier = HierBeta(vocab_order, m=m)
        self.l2, self.refit_every, self.max_rows, self.lift_c = l2, refit_every, max_rows, lift_c
        # user -> [day, sent_today, k200_today, last_ts, last_y, n_tot, k_tot, sum_p_tot]
        self.state: dict[int, list] = {}
        self.buf_X: list[np.ndarray] = []
        self.buf_y: list[np.ndarray] = []
        self.buf_n = 0
        self.w: np.ndarray | None = None
        self.updates = 0

    # ---- features ----
    def _gather(self, ts, user):
        n = len(ts)
        a = np.zeros((n, 8))
        get = self.state.get
        days = (np.asarray(ts) // DAY).tolist()
        for i, u in enumerate(np.asarray(user).tolist()):
            st = get(u)
            if st is not None:
                a[i] = st
                if st[0] != days[i]:       # a new day: the daily counters start from zero
                    a[i, 1] = a[i, 2] = 0.0
                    a[i, 3] = -1.0
        return a

    def _features(self, a, ts, p):
        ts = np.asarray(ts)
        sent_today, k_today, last_ts, last_y, n_tot, k_tot, sp_tot = (a[:, i] for i in range(1, 8))
        lp = np.log(np.clip(p, 1e-4, 1 - 1e-4) / (1 - np.clip(p, 1e-4, 1 - 1e-4)))
        since = np.where(last_ts >= 0, ts - last_ts, -1)
        since_b = np.where(since < 0, 0, 1 + np.searchsorted(_SINCE_EDGES, since, side="right"))
        lift = (k_tot - sp_tot) / (n_tot + self.lift_c)
        last = np.where(n_tot == 0, 0, np.where(last_y > 0, 2, 1))
        return np.hstack([
            np.ones((len(p), 1), np.float32), lp[:, None].astype(np.float32),
            _onehot(np.searchsorted(_SENT_EDGES, sent_today, side="right"), len(_SENT_EDGES) + 1),
            _onehot(np.searchsorted(_K200_EDGES, k_today, side="right"), len(_K200_EDGES) + 1),
            _onehot(since_b.astype(int), len(_SINCE_EDGES) + 2),
            _onehot(last.astype(int), 3),
            _onehot(np.searchsorted(_NTOT_EDGES, n_tot, side="right"), len(_NTOT_EDGES) + 1),
            lift[:, None].astype(np.float32),
        ])

    # ---- interface ----
    def update(self, tags, y, ts, user):
        if len(y) == 0:
            return
        tags, ts, user = np.asarray(tags), np.asarray(ts).astype(np.int64), np.asarray(user).astype(np.int64)
        yb = np.asarray(y, dtype=np.float64)
        if self.hier.total_n == 0:                      # the first (bulk) update: in-sample → leave-one-out
            self.hier.update(tags, yb)
            p = self.hier.score_loo(tags, yb)
        else:                                           # online: the rows are new for the model
            p = self.hier.score(tags)
            self.hier.update(tags, yb)
        # Process every row in chronological order, but retain only the newest
        # max_rows feature rows; do not materialize the whole training matrix.
        st_get, state = self.state.get, self.state
        keep_from = max(0, len(yb) - self.max_rows)
        for start in range(0, len(ts), 50_000):
            end = min(start + 50_000, len(ts))
            begin_keep = min(end, max(start, keep_from))
            a = np.zeros((end - begin_keep, 8))
            for i in range(start, end):
                u, d = int(user[i]), int(ts[i] // DAY)
                st = st_get(u)
                if st is None:
                    st = [d, 0, 0, -1, 0, 0, 0, 0.0]
                    state[u] = st
                elif st[0] != d:
                    st[0], st[1], st[2], st[3] = d, 0, 0, -1
                if i >= begin_keep:
                    a[i - begin_keep] = st
                st[1] += 1
                st[2] += yb[i]
                st[3] = int(ts[i])
                st[4] = yb[i]
                st[5] += 1
                st[6] += yb[i]
                st[7] += p[i]
            if begin_keep < end:
                self.buf_X.append(self._features(a, ts[begin_keep:end], p[begin_keep:end]))
                self.buf_y.append(yb[begin_keep:end].astype(np.float32))
                self.buf_n += end - begin_keep
                while self.buf_n > self.max_rows:
                    extra = min(self.buf_n - self.max_rows, len(self.buf_y[0]))
                    if extra == len(self.buf_y[0]):
                        self.buf_X.pop(0)
                        self.buf_y.pop(0)
                    else:
                        self.buf_X[0] = self.buf_X[0][extra:].copy()
                        self.buf_y[0] = self.buf_y[0][extra:].copy()
                    self.buf_n -= extra
        self.updates += 1
        if self.w is None or self.updates % self.refit_every == 0:
            self._fit()

    def _fit(self):
        X, y = np.concatenate(self.buf_X), np.concatenate(self.buf_y)
        w0 = np.zeros(X.shape[1])
        w0[1] = 1.0
        if self.w is not None:
            w0 = self.w
        self.w = _fit_logit(X, y, w0, self.l2)

    def score(self, tags, ts, user):
        p = self.hier.score(tags)
        if self.w is None:
            return p
        ts = np.asarray(ts).astype(np.int64)
        X = self._features(self._gather(ts, user), ts, p)
        return 1.0 / (1.0 + np.exp(-np.clip(X.astype(np.float64) @ self.w, -30, 30)))

    def seed_scores(self, n: int, rng) -> np.ndarray:
        """Scores of the training rows made with the features as of then: the start sample for the router threshold."""
        X = np.concatenate(self.buf_X)
        idx = rng.choice(len(X), min(n, len(X)), replace=False)
        return 1.0 / (1.0 + np.exp(-np.clip(X[idx].astype(np.float64) @ self.w, -30, 30)))
