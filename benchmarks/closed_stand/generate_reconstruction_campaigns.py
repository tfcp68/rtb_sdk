"""Synthetic, bounded targeting for reconstruction only; never imported by stand.py."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def generate_campaigns(profiles, weights, order, vocabs, *, seed=42, count=8,
                       min_coverage=0.025, max_coverage=0.20, max_iou=0.60,
                       max_union=0.85, scenario="targeting"):
    """Sample rectangles anchored in observed TRAIN profiles, rejecting broad/duplicate ones.

    Lists are OR within a field, fields are AND. Zero is never targeted. Coverage
    and IoU refer to the supplied traffic, not a Cartesian product of vocabularies.
    Fail explicitly when the requested diversity cannot be built on this domain.
    """
    weights = np.asarray(weights, dtype=float)
    if (count < 1 or not 0 < min_coverage <= max_coverage < 1
            or not 0 <= max_iou < 1 or not 0 < max_union < 1
            or scenario not in ("targeting", "dynamic")):
        raise ValueError("Invalid campaign generation settings")
    if (profiles.ndim != 2 or profiles.shape[1] != len(order)
            or len(weights) != len(profiles) or np.any(~np.isfinite(weights))
            or np.any(weights < 0) or weights.sum() <= 0):
        raise ValueError("Need nonempty profiles and finite nonnegative traffic weights")
    weights = weights / weights.sum()
    rng = np.random.default_rng(seed)
    ads, masks, diagnostics = [], [], []
    union = np.zeros(len(profiles), dtype=bool)
    for _ in range(max(2000, count * 1000)):
        if len(ads) == count:
            break
        anchor = profiles[rng.choice(len(profiles), p=weights)]
        available = np.flatnonzero(anchor != 0)
        if not len(available):
            continue
        # Cycle widths to exercise individual fields, pairs and triples.
        width = min(1 + len(ads) % 3, len(available))
        fields = sorted(rng.choice(available, width, replace=False))
        mask = np.ones(len(profiles), dtype=bool)
        target = {}
        for field in fields:
            values = [int(anchor[field])]
            choices = np.unique(profiles[:, field])
            choices = choices[(choices != 0) & (choices != anchor[field])]
            if len(choices):
                extra = int(rng.integers(0, min(2, len(choices)) + 1))
                values.extend(int(v) for v in rng.choice(choices, extra, replace=False))
            mask &= np.isin(profiles[:, field], values)
            target[order[field]] = [vocabs[order[field]][v] for v in sorted(values)]
        coverage = float(weights[mask].sum())
        if not min_coverage <= coverage <= max_coverage:
            continue
        if weights[union | mask].sum() > max_union or weights[mask & ~union].sum() < 0.1 * coverage:
            continue
        ious = [float(weights[mask & old].sum() / weights[mask | old].sum()) for old in masks]
        if any(iou > max_iou for iou in ious):
            continue
        # Keep a visible exclusive region for EVERY campaign, including earlier
        # ones. Otherwise several later rectangles can completely hide a seller.
        proposed = masks + [mask]
        if any(weights[old & ~np.logical_or.reduce(proposed[:i] + proposed[i + 1:])].sum()
               < 0.10 * weights[old].sum()
               for i, old in enumerate(proposed) if len(proposed) > 1):
            continue
        index = len(ads)
        ad = dict(id=f"recon_{index + 1:02d}", name=f"Reconstruction {index + 1:02d}",
                  targets=target, cpm=int(rng.integers(90, 301)), priority=1,
                  limits="none", min_interval=0)
        if scenario == "dynamic":
            ad.update(limits=("none", "loose", "normal")[index % 3],
                      min_interval=(0, 30, 120, 300)[index % 4],
                      user_frequency_limit={"d": (4, 8, 16)[index % 3]})
        ads.append(ad)
        masks.append(mask)
        union |= mask
        diagnostics.append(dict(id=ad["id"], coverage=coverage, max_previous_iou=max(ious, default=0.0)))
    if len(ads) != count:
        raise ValueError(f"Could generate only {len(ads)}/{count} diverse campaigns; "
                         "reduce --campaign-count or relax coverage/overlap constraints")
    for i, item in enumerate(diagnostics):
        other = np.logical_or.reduce(masks[:i] + masks[i + 1:]) if count > 1 else np.zeros(len(profiles), dtype=bool)
        item["exclusive_coverage"] = float(weights[masks[i] & ~other].sum())
    return dict(meta=dict(generator="reconstruction_rectangles_v1", seed=seed, scenario=scenario,
                          min_coverage=min_coverage, max_coverage=max_coverage, max_iou=max_iou,
                          max_union=max_union, union_coverage=float(weights[union].sum()),
                          campaigns=diagnostics), ads=ads)


def training_counts(prep, days, sample, pool_devices):
    # Import locally so the generator itself only needs numpy.
    try:
        from . import stand
    except ImportError:
        import stand
    counts = np.zeros(len(prep.combos), dtype=np.int64)
    pool = stand.pool_mask_of(prep, pool_devices)
    for _, _, _, combo in stand.iter_chunks(prep, days, sample):
        counts += np.bincount(combo[pool[combo]], minlength=len(counts))
    return counts


def from_prepared(prep, days, sample, pool_devices, **settings):
    try:
        from . import stand
    except ImportError:
        import stand
    counts = training_counts(prep, days, sample, pool_devices)
    seen = counts > 0
    result = generate_campaigns(prep.combos[seen], counts[seen], prep.vocab_order, prep.vocabs, **settings)
    result["meta"].update(training_days=list(days), sample=sample, pool_devices=pool_devices,
                           prepared_signature=stand.prepared_signature(prep))
    return result, counts


def main():
    try:
        from . import stand
    except ImportError:
        import stand
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", required=True)
    p.add_argument("--prepared", default=stand.PREPARED)
    p.add_argument("--train-days", default="0:3")
    p.add_argument("--sample", type=float, default=0.002)
    p.add_argument("--pool-devices", nargs="+", default=stand.POOL_DEVICES)
    add_generation_arguments(p)
    args = p.parse_args()
    days = stand.parse_range(args.train_days)
    prep = stand.load_prepared(args.prepared)
    if not 0 <= days[0] < days[1] <= prep.n_days or not 0 < args.sample <= 1:
        p.error("Require valid train-days and sample in (0, 1]")
    if Path(args.out).exists():
        raise FileExistsError(args.out)
    result, _ = from_prepared(prep, days, args.sample, args.pool_devices, **generation_settings(args))
    with open(args.out, "x", encoding="utf-8") as f:
        json.dump(stand.privacy.campaign_config(result), f, ensure_ascii=False, indent=2)
    print(f"Generated {len(result['ads'])} campaigns: {args.out}")


def add_generation_arguments(p):
    p.add_argument("--campaign-seed", type=int, default=42)
    p.add_argument("--campaign-count", type=int, default=8)
    p.add_argument("--campaign-min-coverage", type=float, default=0.025)
    p.add_argument("--campaign-max-coverage", type=float, default=0.20)
    p.add_argument("--campaign-max-iou", type=float, default=0.60)
    p.add_argument("--campaign-max-union", type=float, default=0.85)
    p.add_argument("--campaign-scenario", choices=("targeting", "dynamic"), default="targeting")


def generation_settings(args):
    return dict(seed=args.campaign_seed, count=args.campaign_count,
                min_coverage=args.campaign_min_coverage, max_coverage=args.campaign_max_coverage,
                max_iou=args.campaign_max_iou, max_union=args.campaign_max_union,
                scenario=args.campaign_scenario)


if __name__ == "__main__":
    main()
