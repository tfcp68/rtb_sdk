#!/usr/bin/env python3
"""
Generator of companies for log-based targeting.

The profile follows the synthetic set (benchmarks/auction_benchmark/seeds.py):
for each of the first 40 base companies its match rate, cpm, priority and
number of targeted dictionaries are taken, and the tag set is chosen so that the share of
matching LOG requests is close to the original match rate. Further (n > 40) —
random companies with a log-uniform match rate on [0.02; 0.5].

Targeted vocabs: Region (region), Device (device), Child (child), Category (category), Channel (channel).
Category (VOD) and Channel (live) are mutually exclusive — a company targets at most
one of them, and is not required to target them at all.

Run:
    python benchmarks/log_benchmark/gen_ads.py --n 30 --seed 1 --out benchmarks/log_benchmark/ads_generated.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))

from stream import load_prepared  # noqa: E402
from benchmarks import report_privacy as privacy

VOCAB_PICK_WEIGHT = {"Region": 0.34, "Device": 0.30, "Category": 0.16, "Channel": 0.12, "Child": 0.08}
LIMIT_PROFILES = (["loose"] * 3 + ["normal"] * 5 + ["tight"] * 2)


def _search(rng, prep, w, tot, marg, rate, k, trials=500):
    names = list(VOCAB_PICK_WEIGHT)
    pw = np.array([VOCAB_PICK_WEIGHT[n] for n in names])
    pw = pw / pw.sum()
    best = (math.inf, None, 0.0)
    for _ in range(trials):
        vs = list(rng.choice(names, size=k, replace=False, p=pw))
        if "Category" in vs and "Channel" in vs:
            continue
        shares = rng.dirichlet(np.ones(k)) * math.log(max(rate, 1e-4))
        mask = np.ones(len(w), dtype=bool)
        sets = {}
        for v, ls in zip(vs, shares):
            vi = prep.vocab_order.index(v)
            m = marg[v]                                   # {code: share}
            codes = list(m)
            if rng.random() < 0.5:      # "top-N by frequency" (like _CITY_TOP10 in the synthetic set)
                order = sorted(range(len(codes)), key=lambda j: -m[codes[j]] * rng.uniform(0.8, 1.25))
            else:                       # a random set biased toward frequent tags
                p = np.array([m[c] for c in codes]) ** 0.6
                order = rng.choice(len(codes), size=len(codes), replace=False, p=p / p.sum())
            r_i, acc, chosen = math.exp(ls), 0.0, []
            for oi in order:
                chosen.append(codes[oi])
                acc += m[codes[oi]]
                if acc >= r_i:
                    break
            sets[v] = chosen
            lut = np.zeros(len(prep.vocabs[v]), dtype=bool)
            lut[chosen] = True
            mask &= lut[prep.combos[:, vi]]
        got = float(w[mask].sum() / tot)
        if got <= 0:
            continue
        err = abs(math.log(got / rate)) + 0.05 * sum(len(cs) / len(marg[v]) for v, cs in sets.items())
        if err < best[0]:
            best = (err, {v: [prep.vocabs[v][c] for c in sorted(cs)] for v, cs in sets.items()}, got)
    return best


def generate(prep, n: int, seed: int) -> dict:
    from auction_benchmark.seeds import BASE_COMPANIES, compute_match_rate

    rng = np.random.default_rng(seed)
    w = prep.combo_counts.astype(np.float64)
    tot = w.sum()
    marg = {}
    for vi, v in enumerate(prep.vocab_order):
        c = np.bincount(prep.combos[:, vi], weights=w, minlength=len(prep.vocabs[v])) / tot
        marg[v] = {i: float(c[i]) for i in range(2, len(c)) if c[i] > 0}

    ads = []
    for i in range(n):
        if i < len(BASE_COMPANIES):
            base = BASE_COMPANIES[i]
            rate = compute_match_rate(base["targets"])
            k = min(3, max(1, len(base["targets"])))
            cpm, pri, name = base["cpm"], base["priority"], base["name"]
        else:
            rate = float(math.exp(rng.uniform(math.log(0.02), math.log(0.5))))
            k = int(rng.choice([1, 2, 3], p=[0.3, 0.5, 0.2]))
            cpm = float(round(rng.lognormal(math.log(150), 0.4), 1))
            pri = float(round(rng.uniform(3.0, 5.0), 1))
            name = f"Gen-{i:03d}"
        rate = min(max(rate, 0.01), 0.7)
        err, targets, got = _search(rng, prep, w, tot, marg, rate, k)
        if targets is None:
            raise RuntimeError(f"We have not been able to target for {name}")
        ud = int(rng.choice([12, 16, 20, 25, 30]))
        ad = {
            "id": f"log_{i:03d}",
            "name": name,
            "cpm": cpm,
            "priority": pri,
            "targets": targets,
            "limits": str(rng.choice(LIMIT_PROFILES)),
            "user_frequency_limit": {"d": ud, "w": ud * int(rng.choice([2, 3, 4]))},
            "min_interval": int(rng.choice([0, 0, 0, 30, 60, 120])),
            "_wanted_match": round(rate, 4),
            "_got_match": round(got, 4),
        }
        if rng.random() < 0.15:
            s = float(round(rng.uniform(0.0, 0.5), 2))
            ad["start_frac"] = s
            ad["end_frac"] = float(round(min(1.0, s + rng.uniform(0.3, 0.6)), 2))
        ads.append(ad)
    return {"meta": {"generator": "gen_ads.py", "n": n, "seed": seed}, "ads": ads}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--prepared", default=os.path.join(HERE, "..", "logs", "prepared_20261012"))
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", default=os.path.join(HERE, "ads_generated.json"))
    a = ap.parse_args()
    prep = load_prepared(a.prepared)
    data = generate(prep, a.n, a.seed)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(privacy.campaign_config(data), f, ensure_ascii=False, indent=1)
    errs = [abs(x["_got_match"] / x["_wanted_match"] - 1) for x in data["ads"]]
    print(f"Save {len(data['ads'])} company → {a.out}")
    print(f"Deviation match rate targetless: median {np.median(errs):.0%}, max {max(errs):.0%}")


if __name__ == "__main__":
    main()
