"""Frozen, train-only traffic statistics used to construct campaign plans."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class PlanningContext:
    match_counts: tuple[int, ...]
    total_daily_rate: float
    pool_daily_rate: float
    train_days: tuple[int, int]
    sample: float
    pool_mask: tuple[bool, ...]


def build_planning_context(prep, train_days, sample, pool_mask):
    """Count sampled training combinations only; future stream rows/counts are never read."""
    counts = np.zeros(len(prep.combos), dtype=np.int64)
    a, b = train_days
    for day in range(a, b):
        _, user, combo = (np.asarray(x) for x in prep.day_arrays(day))
        if sample < 1:
            combo = combo[user < np.uint32(min(int(sample * 2**32), 2**32 - 1))]
        counts += np.bincount(combo.astype(np.int64), minlength=len(counts))
    days = b - a
    return PlanningContext(tuple(map(int, counts)), float(counts.sum() / days),
                           float(counts[pool_mask].sum() / days), (a, b), float(sample),
                           tuple(map(bool, pool_mask)))


def planned_match_counts(prep, ads, planning, pool_only=False):
    counts = np.asarray(planning.match_counts, dtype=np.float64)
    if pool_only:
        counts = counts * np.asarray(planning.pool_mask)
    result = []
    for ad in ads:
        ok = np.ones(len(counts), dtype=bool)
        for vi, name in enumerate(prep.vocab_order):
            tags = ad.get("targets", {}).get(name)
            if tags is None:
                continue
            lookup = {label: i for i, label in enumerate(prep.vocabs[name])}
            missing = [tag for tag in tags if tag not in lookup]
            if missing:
                raise ValueError(f"[{ad['id']}] нет тегов {missing[:3]} в словаре {name!r}")
            lut = np.zeros(len(lookup), dtype=bool)
            for tag in tags:
                lut[lookup[tag]] = True
            lut[0] = False
            ok &= lut[prep.combos[:, vi]]
        result.append(float(counts[ok].sum()))
    return result


def planned_match_rates(prep, ads, planning, pool_only=False):
    counts = planned_match_counts(prep, ads, planning, pool_only)
    denominator = planning.pool_daily_rate if pool_only else planning.total_daily_rate
    return [count / (denominator * (planning.train_days[1] - planning.train_days[0]))
            if denominator else 0.0 for count in counts]
