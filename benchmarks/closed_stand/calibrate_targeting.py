#!/usr/bin/env python3
"""Expand synthetic campaign targeting to approach a random-policy sell-through target."""
from __future__ import annotations

import argparse
import copy
import dataclasses
import json
import os

import numpy as np

import stand
from ads import compute_match_rates, load_ads_file, _resolve_report_targets
from routers import RandomShare
from stream import load_prepared


def proposals(prep, ads, allowed_devices, max_values, limit):
    """Rank single-tag additions by extra matched traffic in the eligible pool."""
    ads = _resolve_report_targets(prep, ads)
    allowed_devices = set(_resolve_report_targets(
        prep, [{"targets": {"Device": list(allowed_devices)}}])[0]["targets"]["Device"])
    rates = compute_match_rates(prep, ads)
    candidates = []
    for i, ad in enumerate(ads):
        for vocab, existing in ad.get("targets", {}).items():
            if vocab not in prep.vocab_order or not existing:
                continue
            pos = prep.vocab_order.index(vocab)
            counts = np.bincount(prep.combos[:, pos], weights=prep.combo_counts,
                                 minlength=len(prep.vocabs[vocab]))
            indices = np.argsort(-counts)
            options = []
            for code in indices:
                label = prep.vocabs[vocab][code]
                if code < 2 or label in existing or counts[code] == 0:
                    continue
                if vocab == "Device" and label not in allowed_devices:
                    continue
                options.append(label)
                if len(options) == max_values:
                    break
            for label in options:
                trial_ad = copy.deepcopy(ad)
                trial_ad["targets"][vocab].append(label)
                gain = compute_match_rates(prep, [trial_ad])[0] - rates[i]
                if gain > 0:
                    candidates.append((gain, i, vocab, label))
    return sorted(candidates, key=lambda x: (-x[0], x[1], x[2], x[3]))[:limit]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--prepared", default=stand.PREPARED)
    ap.add_argument("--manager-ads", required=True)
    ap.add_argument("--our-ads", default=os.path.join(stand.HERE, "..", "log_benchmark", "ads_manual.json"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--days", default="0:3")
    ap.add_argument("--eval-days", default="3:4")
    ap.add_argument("--sample", type=float, default=0.002)
    ap.add_argument("--q", type=float, default=0.8)
    ap.add_argument("--target", type=float, default=0.5)
    ap.add_argument("--steps", type=int, default=3)
    ap.add_argument("--candidates", type=int, default=8)
    ap.add_argument("--values-per-vocab", type=int, default=4)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--pool-devices", nargs="+", default=stand.POOL_DEVICES)
    a = ap.parse_args()
    if os.path.exists(a.out):
        ap.error("output file already exists")
    prep = load_prepared(a.prepared)
    train, test = stand.parse_range(a.days), stand.parse_range(a.eval_days)
    if not (0 <= train[0] < train[1] <= test[0] < test[1] <= prep.n_days and
            0 < a.sample <= 1 and 0 < a.q <= 1 and 0 < a.target < 1 and
            a.steps >= 0 and a.candidates > 0 and a.values_per_vocab > 0):
        ap.error("Unacceptable parameters or overlapping periods")
    mask = stand.pool_mask_of(prep, a.pool_devices)
    pool_prep = dataclasses.replace(prep, combo_counts=prep.combo_counts * mask)
    if not pool_prep.combo_counts.sum():
        ap.error("empty-pool")
    ours = load_ads_file(a.our_ads)
    original = _resolve_report_targets(prep, load_ads_file(a.manager_ads))

    def run(ads, days):
        return stand.simulate(prep, days, a.sample, ads, ours, mask, a.q,
                              lambda: RandomShare(mask, prep.combos, a.q, a.seed), 150.0, seed=a.seed)

    current = copy.deepcopy(original)
    initial = run(current, train)
    value = initial["sellthrough"]
    history = []
    print(f"baseline random: {value:.2%}", flush=True)
    for step in range(a.steps):
        best = None
        options = proposals(pool_prep, current, set(a.pool_devices), a.values_per_vocab, a.candidates)
        for gain, i, vocab, label in options:
            trial = copy.deepcopy(current)
            trial[i]["targets"][vocab].append(label)
            result = run(trial, train)
            error = abs(result["sellthrough"] - a.target)
            record = dict(campaign=trial[i]["id"], vocab=vocab, tag=label, match_gain=gain,
                          sellthrough=result["sellthrough"], error=error)
            print(f"  {record['campaign']} + {vocab}={label}: {result['sellthrough']:.2%}", flush=True)
            if best is None or error < best[0]:
                best = error, trial, result, record
        if best is None or best[0] >= abs(value - a.target):
            break
        current, value = best[1], best[2]["sellthrough"]
        history.append(best[3])
        print(f"step {step + 1}: {history[-1]} ", flush=True)
    baseline, calibrated = run(original, test), run(current, test)
    print(f"postponing {test}: random {baseline['sellthrough']:.2%} → {calibrated['sellthrough']:.2%}", flush=True)
    data = {"meta": {"description": "Synthetic targeting calibrated for random sell-through; not real campaigns",
                     "prepared_signature": stand.prepared_signature(prep), "source_ads": a.manager_ads,
                     "training_days": train, "evaluation_days": test, "sample": a.sample, "q": a.q,
                     "target_sellthrough": a.target, "seed": a.seed, "pool_devices": a.pool_devices,
                     "selected_changes": history, "evaluation": {"baseline": baseline, "calibrated": calibrated}},
            "ads": current}
    with open(a.out, "x", encoding="utf-8") as f:
        json.dump(stand.privacy.campaign_config(data), f, ensure_ascii=False, indent=2)
    print(f"The result: {a.out}")


if __name__ == "__main__":
    main()
