"""
Request stream from the prepared logs (see prepare_logs.py).

What it can do:
  * period: how many days to run (1 / 7 / 30). If there are more days than
    in the logs, the week is repeated "in a circle" without remapping users, but
    with slight noise: a time shift of ±jitter seconds, random drops/duplicates
    of requests (the noise share);
  * sample: the share of users (by the hash of client_id). Per-user frequencies
    are preserved, while the total volume drops proportionally;
  * traffic_factor: <1 — thinning of requests (traffic shortage), >1 —
    duplication of requests with a small shift (traffic excess).

The stream is deterministic with a fixed seed: all algorithms see the same thing.
"""
from __future__ import annotations

import sys as _privacy_sys
from pathlib import Path as _PrivacyPath
_privacy_sys.path.insert(0, str(_PrivacyPath(__file__).resolve().parents[2]))
from benchmarks import report_privacy as privacy

import json
import os
from dataclasses import dataclass
from typing import Iterator

import numpy as np

VOCAB_NAMES = {"\u0420\u0435\u0433\u0438\u043e\u043d": "Region", "\u0423\u0441\u0442\u0440\u043e\u0439\u0441\u0442\u0432\u043e": "Device", "\u0420\u0435\u0431\u0451\u043d\u043e\u043a": "Child", "\u041a\u0430\u0442\u0435\u0433\u043e\u0440\u0438\u044f": "Category", "\u041a\u0430\u043d\u0430\u043b": "Channel"}

DAY = 86_400


@dataclass
class Prepared:
    root: str
    meta: dict
    combos: np.ndarray          # U×5 uint16
    combo_counts: np.ndarray    # U int64 (over all days of the logs)

    @property
    def n_days(self) -> int:
        return len(self.meta["days"])

    @property
    def vocab_order(self) -> list[str]:
        return [VOCAB_NAMES.get(n, n) for n in self.meta["vocab_order"]]

    @property
    def vocabs(self) -> dict[str, list[str]]:
        return {VOCAB_NAMES.get(n, n): v for n, v in self.meta["vocabs"].items()}

    def day_arrays(self, base_day: int):
        n = self.meta["days"][base_day]["name"]
        ld = lambda s: np.load(os.path.join(self.root, f"{n}_{s}.npy"), mmap_mode="r")
        return ld("ts"), ld("user"), ld("combo")


def load_prepared(root: str) -> Prepared:
    with open(os.path.join(root, "meta.json"), encoding="utf-8") as f:
        meta = json.load(f)
    prep = Prepared(
        root=root,
        meta=meta,
        combos=np.load(os.path.join(root, "combos.npy")),
        combo_counts=np.load(os.path.join(root, "combo_counts.npy")),
    )

    privacy.register_prepared(prep)
    return prep


def _user_mask(user: np.ndarray, sample: float) -> np.ndarray | None:
    if sample >= 1.0:
        return None
    return user < np.uint32(min(int(sample * 2**32), 2**32 - 1))


def sampled_day_sizes(prep: Prepared, sample: float) -> list[int]:
    """Number of requests in each base day after sampling users."""
    sizes = []
    for d in range(prep.n_days):
        _, user, _ = prep.day_arrays(d)
        m = _user_mask(np.asarray(user), sample)
        sizes.append(len(user) if m is None else int(m.sum()))
    return sizes


def nominal_requests(prep: Prepared, days: int, sample: float) -> int:
    """Nominal number of requests of the period (before traffic_factor) — the basis for volume."""
    sizes = sampled_day_sizes(prep, sample)
    return int(sum(sizes[d % prep.n_days] for d in range(days)))


def iter_days(
    prep: Prepared,
    days: int,
    sample: float = 1.0,
    traffic_factor: float = 1.0,
    seed: int = 42,
    jitter: int = 120,
    noise: float = 0.02,
) -> Iterator[tuple[int, np.ndarray, np.ndarray, np.ndarray]]:
    """Yields (day_idx, ts int32, user uint32, combo int32) per day, ts sorted."""
    cycle = prep.n_days * DAY
    for d in range(days):
        base = d % prep.n_days
        rep = d // prep.n_days
        ts, user, combo = prep.day_arrays(base)
        ts, user, combo = np.asarray(ts), np.asarray(user), np.asarray(combo)
        m = _user_mask(user, sample)
        if m is not None:
            ts, user, combo = ts[m], user[m], combo[m]
        rng = np.random.default_rng([seed, d])
        changed = False
        ts = ts.astype(np.int64) + rep * cycle
        if rep > 0:
            if noise > 0:
                r = rng.random(len(ts))
                dup = r < noise / 2                          # [0, noise/2): duplicate
                keep = ~((r >= noise / 2) & (r < noise))     # [noise/2, noise): drop
                ts = np.concatenate([ts[keep], ts[dup]])
                user = np.concatenate([user[keep], user[dup]])
                combo = np.concatenate([combo[keep], combo[dup]])
            if jitter > 0:
                ts = ts + rng.integers(-jitter, jitter + 1, size=len(ts))
            changed = True
        if traffic_factor < 1.0:
            keep = rng.random(len(ts)) < traffic_factor
            ts, user, combo = ts[keep], user[keep], combo[keep]
        elif traffic_factor > 1.0:
            whole = int(traffic_factor)
            extra = rng.random(len(ts)) < (traffic_factor - whole)
            ts_p, us_p, co_p = [ts], [user], [combo]
            for _ in range(whole - 1):
                ts_p.append(ts + rng.integers(1, 301, size=len(ts)))
                us_p.append(user)
                co_p.append(combo)
            if extra.any():
                ts_p.append(ts[extra] + rng.integers(1, 301, size=int(extra.sum())))
                us_p.append(user[extra])
                co_p.append(combo[extra])
            ts, user, combo = np.concatenate(ts_p), np.concatenate(us_p), np.concatenate(co_p)
            changed = True
        if changed:
            order = np.argsort(ts, kind="stable")
            ts, user, combo = ts[order], user[order], combo[order]
        yield d, np.maximum(ts, 0).astype(np.int32), user, combo.astype(np.int32)
