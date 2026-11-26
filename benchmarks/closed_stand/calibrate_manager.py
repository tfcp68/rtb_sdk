#!/usr/bin/env python3
"""Calibrate simulated manager campaign volumes on a training period.

The objective can be random-policy sell-through or per-campaign sell-out.
This adjusts plans and bounded frequency caps, not targeting, and does not
infer real manager campaigns. The same random traffic is replayed for each candidate.
"""
from __future__ import annotations

import argparse
import copy
import json
import os

import numpy as np

import stand
from ads import AD_LIMIT_PROFILES, load_ads_file
from routers import RandomShare
from stream import load_prepared


def loss(result, target):
    ads = result["hidden_manager"]
    total = sum(a["volume"] for a in ads)
    return sum(abs(a["impressions"] - target * a["volume"]) for a in ads) / total


def objective(result, mode, target, target_sellthrough):
    if mode == "sellthrough":
        return abs(result["sellthrough"] - target_sellthrough)
    return loss(result, target)


def next_weights(ads, result, target, rate, min_weight, max_weight):
    by_id = {a["id"]: a for a in result["hidden_manager"]}
    updated = copy.deepcopy(ads)
    for ad in updated:
        item = by_id[ad["id"]]
        ratio = item["impressions"] / item["volume"]
        # Downweight plans that cannot be delivered; changes are intentionally bounded.
        factor = (max(ratio, 0.01) / target) ** rate
        ad["volume_weight"] = float(np.clip(ad.get("volume_weight", 1.0) * factor, min_weight, max_weight))
    return updated


def scale_frequency_limits(ads, ad_factor, user_factor):
    """Relax existing caps only, preserving windows and unlimited fields."""
    updated = copy.deepcopy(ads)
    for ad in updated:
        if ad_factor != 1:
            relative = dict(AD_LIMIT_PROFILES[ad.get("limits", "none")])
            relative.update(ad.get("ad_limits_rel", {}))
            if relative:
                ad["ad_limits_rel"] = {k: v * ad_factor if v and v > 0 else v for k, v in relative.items()}
            if "ad_frequency_limit" in ad:
                ad["ad_frequency_limit"] = {k: int(np.floor(v * ad_factor)) if v and v > 0 else v
                                             for k, v in ad["ad_frequency_limit"].items()}
        if user_factor != 1 and "user_frequency_limit" in ad:
            ad["user_frequency_limit"] = {k: int(np.floor(v * user_factor)) if v and v > 0 else v
                                          for k, v in ad["user_frequency_limit"].items()}
    return updated


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--prepared", default=stand.PREPARED)
    p.add_argument("--manager-ads", default=os.path.join(stand.HERE, "manager_ads.json"))
    p.add_argument("--our-ads", default=os.path.join(stand.HERE, "..", "log_benchmark", "ads_manual.json"))
    p.add_argument("--out", required=True, help="new JSON, Existing file is not overwritten")
    p.add_argument("--days", default="0:3", help="calibration days")
    p.add_argument("--eval-days", default="3:4", help="postponing, not used in the selection process")
    p.add_argument("--sample", type=float, default=0.002)
    p.add_argument("--q", type=float, default=0.8)
    p.add_argument("--target", type=float, default=0.6)
    p.add_argument("--objective", choices=["sellthrough", "campaign"], default="sellthrough",
                   help="target: 200/gone random ordeal sell-out campaign")
    p.add_argument("--target-sellthrough", type=float, default=0.5)
    p.add_argument("--iterations", type=int, default=4)
    p.add_argument("--rate", type=float, default=0.5)
    p.add_argument("--min-weight", type=float, default=0.25)
    p.add_argument("--max-weight", type=float, default=4.0)
    p.add_argument("--frequency-factors", type=float, nargs="+", default=[1.0, 1.25, 1.5],
                   help="multipliers of user restrictions (1–5)")
    p.add_argument("--ad-frequency-factors", type=float, nargs="+", default=[1.0, 1.25, 1.5],
                   help="campaign constraints multiplier (1–5)")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--pool-devices", nargs="+", default=stand.POOL_DEVICES)
    a = p.parse_args()
    if os.path.exists(a.out):
        p.error("output file already exists; Choose a different name")
    if not (0 < a.sample <= 1 and 0 < a.q <= 1 and 0 < a.target <= 1 and 0 < a.target_sellthrough <= 1 and
            a.iterations >= 0 and 0 < a.rate <= 1 and 0 < a.min_weight <= 1 <= a.max_weight and
            all(np.isfinite(x) and 1 <= x <= 5 for x in a.frequency_factors + a.ad_frequency_factors)):
        p.error("nonpermissible parameters")
    factors = sorted(set(a.frequency_factors) | {1.0})
    ad_factors = sorted(set(a.ad_frequency_factors) | {1.0})
    prep = load_prepared(a.prepared)
    train, test = stand.parse_range(a.days), stand.parse_range(a.eval_days)
    if not (0 <= train[0] < train[1] <= test[0] < test[1] <= prep.n_days):
        p.error("Calibration and deferred days should go in order and do not overlap")
    mask = stand.pool_mask_of(prep, a.pool_devices)
    our_ads = load_ads_file(a.our_ads)
    original = load_ads_file(a.manager_ads)

    def run(ads, days):
        factory = lambda: RandomShare(mask, prep.combos, a.q, a.seed)
        return stand.simulate(prep, days, a.sample, ads, our_ads, mask, a.q, factory, 150.0, seed=a.seed)

    best = None
    candidate = copy.deepcopy(original)
    history = []
    for i in range(a.iterations + 1):
        result = run(candidate, train)
        value = objective(result, a.objective, a.target, a.target_sellthrough)
        history.append(dict(iteration=i, loss=value, sent=result["sent"], ok=result["ok"],
                            sellthrough=result["sellthrough"], campaigns=result["hidden_manager"]))
        print(f"iteration {i}: deviation {value:.4f}, 200/gone {result['sellthrough']:.2%}", flush=True)
        if best is None or value < best[0]:
            best = (value, copy.deepcopy(candidate), i)
        if i < a.iterations:
            candidate = next_weights(candidate, result, a.target, a.rate, a.min_weight, a.max_weight)

    volume_best = copy.deepcopy(best[1])
    frequency_history = []
    # Check pairs against the selected plan; do not repeatedly compound the factors.
    for ad_factor in ad_factors:
        for user_factor in factors:
            candidate = scale_frequency_limits(volume_best, ad_factor, user_factor)
            result = run(candidate, train)
            value = objective(result, a.objective, a.target, a.target_sellthrough)
            frequency_history.append(dict(ad_factor=ad_factor, user_factor=user_factor, loss=value,
                                          sellthrough=result["sellthrough"], campaigns=result["hidden_manager"]))
            print(f"frequency ad={ad_factor:g}, user={user_factor:g}: deviation {value:.4f}, "
                  f"200/gone {result['sellthrough']:.2%}", flush=True)
            if value < best[0] - 1e-12:
                best = (value, candidate, best[2], ad_factor, user_factor)

    baseline, calibrated = run(original, test), run(best[1], test)
    print(f"postponing {test}: deviation {objective(baseline, a.objective, a.target, a.target_sellthrough):.4f} → "
          f"{objective(calibrated, a.objective, a.target, a.target_sellthrough):.4f}; 200/gone {baseline['sellthrough']:.2%} → "
          f"{calibrated['sellthrough']:.2%}", flush=True)
    data = {"meta": {"description": "Calibrated simulated manager; not inferred real campaigns",
                     "prepared_signature": stand.prepared_signature(prep), "source_ads": a.manager_ads,
                     "training_days": train, "evaluation_days": test, "sample": a.sample, "q": a.q,
                     "objective": a.objective, "target": a.target, "target_sellthrough": a.target_sellthrough,
                     "seed": a.seed, "pool_devices": a.pool_devices, "ad_frequency_factors": ad_factors,
                     "best_iteration": best[2], "frequency_factors": factors,
                     "selected_frequency_factors": {"ad": best[3] if len(best) > 3 else 1.0,
                                                    "user": best[4] if len(best) > 4 else 1.0},
                     "history": history, "frequency_history": frequency_history,
                     "evaluation": {"baseline": baseline, "calibrated": calibrated}}, "ads": best[1]}
    with open(a.out, "x", encoding="utf-8") as f:
        json.dump(stand.privacy.campaign_config(data), f, ensure_ascii=False, indent=2)
    print(f"The result: {a.out}")


if __name__ == "__main__":
    main()
