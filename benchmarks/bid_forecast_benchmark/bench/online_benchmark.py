"""Online (closed-loop) version of price_benchmark: our bidder runs INSIDE the stand.

Offline (price_benchmark) replays prices z recorded from one stand run without us, so the manager's frequency
limits, min_interval and volume are spent on impressions that we actually won (assumption 1 of REPORT.md).
Here, for every request sent to the manager:
  1. peek: which manager campaign would win and at what cpm z (no side effects);
  2. our bid b for this request from the policy;
  3. b > z  -> the impression is ours, the manager's state is NOT updated (its limits/volume are not spent);
     else   -> the manager serves as usual (state updated exactly as in stand.Seller.serve).
z is therefore path-dependent: it depends on which impressions we took before.
Models are trained exactly as in price_benchmark (same seeds, data, subsamples); only the test changes.
Self-check: with a policy that never bids, every z equals the offline-recorded z.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from . import price_benchmark as pb
from ..cui.cui2011 import CuiForecaster
from ..wang.wang2016 import SurvivalTree, fit_baseline

stand = pb.stand


def peek(seller, t, u, c):
    """Winner index Seller.serve would return, without changing any state."""
    cand = seller.match[c]
    best = -1
    for a in cand:
        if t < seller.until[a] or t >= seller.end[a]:
            continue
        if seller.u_flag[a]:
            st = seller.udict.get(u * seller.K + a)
            if st is not None and (t < st[0] or t < st[1]):
                continue
        if best < 0 or seller.cpm[a] > seller.cpm[best]:
            best = a
    return best


def run_online(prep, days, sample, mgr_ads, our_ads, pool_mask, q, seed, reserve, bid_of):
    """bid_of(combo, v, z, i) -> bid for request number i of the stream (z is passed only so the oracle can use it).

    Returns per-sent-request arrays (combo, z, v, b, won) in stream order."""
    sellers, rows, value = [], [], {}

    class Online(stand.Seller):
        def __init__(self, *args):
            super().__init__(*args)
            sellers.append(self)                     # simulate() builds the manager first, ours second

        def serve(self, t, u, c):
            if self is sellers[0]:
                w = peek(self, t, u, c)
                z = float(self.cpm[w]) if w >= 0 else reserve
                v = value.get(c)
                if v is None:
                    v = value[c] = float(max((sellers[1].cpm[a] for a in sellers[1].match[c]), default=0.0))
                b = float(bid_of(c, v, z, len(rows)))
                won = v > 0 and b > z
                rows.append((c, z, v, b, won))
                if won:                              # ours: the manager never shows, its state stays untouched
                    self.requests += 1
                    return -1
            return super().serve(t, u, c)

    original, stand.Seller = stand.Seller, Online
    try:
        stand.simulate(prep, days, sample, mgr_ads, our_ads, pool_mask, q,
                       lambda: pb.RandomShare(pool_mask, prep.combos, q, seed), 150.0, seed=seed)
    finally:
        stand.Seller = original
    c, z, v, b, won = (np.array(x) for x in zip(*rows))
    return dict(combo=c.astype(np.int64), z=z.astype(float), v=v.astype(float), b=b.astype(float),
                won=won.astype(bool), mgr_shown=int(sellers[0].total_impressions))


# ───────────────────────────── policies ─────────────────────────────

def policy_from_F(F_u, uniq_index):
    """b* = argmax_{g<=v} (v-g) F(g) per combo; F_u rows indexed by uniq_index[combo]."""
    cache = {}

    def bid(c, v, z, i=None):
        if v <= 0:
            return 0.0
        key = (c, v)
        if key not in cache:
            row = F_u[uniq_index[c]]
            exp = (v - pb.GRID) * row
            exp[pb.GRID > v] = -np.inf
            cache[key] = float(pb.GRID[exp.argmax()])
        return cache[key]
    return bid


def run(args):
    prep = stand.load_prepared(args.prepared)
    pool_mask = stand.pool_mask_of(prep, stand.POOL_DEVICES)
    mgr_ads, our_ads = stand.load_ads_file(args.manager_ads), stand.load_ads_file(args.our_ads)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    records, checks = [], []
    test_days = args.test_days
    online = lambda bid_of: run_online(prep, test_days, args.sample, mgr_ads, our_ads, pool_mask, args.q, seed,
                                       args.reserve, bid_of)
    for seed in args.seeds:
        rng = np.random.default_rng(seed)
        train = pb.generate(prep, args.train_days, args.sample, mgr_ads, our_ads, pool_mask, args.q, seed, args.reserve)
        val = pb.generate(prep, args.val_days, args.sample, mgr_ads, our_ads, pool_mask, args.q, seed, args.reserve)
        test_off = pb.generate(prep, test_days, args.sample, mgr_ads, our_ads, pool_mask, args.q, seed, args.reserve)
        tr_idx = rng.choice(len(train["z"]), min(args.train_cap, len(train["z"])), replace=False)
        va_idx = rng.choice(len(val["z"]), min(args.val_cap, len(val["z"])), replace=False)

        # self-check: never bidding must reproduce the offline-recorded prices exactly
        base = online(lambda c, v, z, i: 0.0)
        assert np.array_equal(base["z"], test_off["z"]) and np.array_equal(base["combo"], test_off["combo"]), \
            "online replay with no bids differs from offline log"
        checks.append({"seed": seed, "rows": int(len(base["z"])), "identical_to_offline": True})
        print(f"seed {seed}: self-check ok ({len(base['z'])} rows)", flush=True)

        def add(regime, name, bid_of, offline_profit=None, offline_comp=None):
            t0 = time.time()
            out = online(bid_of)
            won, v, b, z = out["won"], out["v"], out["b"], out["z"]
            # routing does not depend on bids, so every policy sees the same requests in the same order
            assert np.array_equal(out["combo"], test_off["combo"]), "online request stream differs between policies"
            # competed = the manager would have had a campaign without us: one fixed set for all policies.
            # (z > reserve at bid time is path-dependent: a policy that wins more creates more competition.)
            comp = comp_off
            rec = {"seed": seed, "regime": regime, "model": name, "profit": float(((v - b) * won).sum()),
                   "wins": int(won.sum()), "spend": float((b * won).sum()),
                   "win_rate_valued": float(won.sum() / max((v > 0).sum(), 1)),
                   "rows_comp": int(comp.sum()), "rows_competing_online": int(np.sum(z > args.reserve)),
                   "profit_comp": float(((v - b) * won)[comp].sum()),
                   "wins_comp": int(won[comp].sum()),
                   "win_rate_comp": float(won[comp].sum() / max((comp & (v > 0)).sum(), 1)),
                   "offline_profit_comp": offline_comp,
                   "mean_z": float(z.mean()), "share_204": float(np.mean(z == args.reserve)),
                   "mgr_shown": out["mgr_shown"], "offline_profit": offline_profit, "seconds": time.time() - t0}
            records.append(rec)
            print(f"  {regime:9s} {name:28s} online profit {rec['profit']:>10.0f}"
                  + (f"  offline {offline_profit:>10.0f}" if offline_profit is not None else ""), flush=True)

        uniq, inv = np.unique(test_off["combo"], return_inverse=True)
        v_u = np.zeros(len(uniq)); v_u[inv] = test_off["v"]
        eval_idx = rng.integers(np.searchsorted(pb.GRID, args.reserve), np.searchsorted(pb.GRID, args.b_max) + 1,
                                len(test_off["z"]))

        comp_off = test_off["z"] > args.reserve

        def offline(F_u):
            m = pb.evaluate(F_u, inv, test_off["z"], v_u, eval_idx, args.reserve, args.b_max)
            return m["profit"], m["profit_comp"]

        def offline_rule(bids):
            v, z = test_off["v"], test_off["z"]
            return (pb.profit_metrics(v, bids, z)["profit"],
                    pb.profit_metrics(v[comp_off], bids[comp_off], z[comp_off])["profit"])

        # oracle online = knows the current (path-dependent) z and bids z+1 whenever profitable
        add("-", "oracle (knows z)", lambda c, v, z, i: z + 1 if v > z + 1 else 0.0,
            pb.oracle_profit(test_off["v"], test_off["z"]),
            pb.oracle_profit(test_off["v"][comp_off], test_off["z"][comp_off]))
        alpha_profit = {a: pb.profit_metrics(val["v"], a * val["v"], val["z"])["profit"] for a in pb.ALPHAS}
        best_alpha = max(alpha_profit, key=alpha_profit.get)
        add("-", f"shade b=a*v (a={best_alpha})", lambda c, v, z, i: best_alpha * v, *offline_rule(best_alpha * test_off["v"]))
        u = pb.random_bid_u(seed, len(test_off["z"]))
        rbid_off = args.reserve + u * np.maximum(test_off["v"] - args.reserve, 0)
        add("-", "random bid b~U(R, v)", lambda c, v, z, i: args.reserve + u[i] * max(v - args.reserve, 0),
            *offline_rule(rbid_off))
        uniform_F = np.clip((pb.GRID - args.reserve) / (args.b_max - args.reserve), 0, 1)
        Fu = np.tile(uniform_F, (len(uniq), 1))
        add("-", "random: uniform price", policy_from_F(Fu, {int(c): i for i, c in enumerate(uniq)}), *offline(Fu))

        for regime in args.regimes:
            obs, cui_rows = pb.observations(prep, train, tr_idx, regime, rng, args.reserve, args.b_max, seed, "train")
            val_obs, _ = pb.observations(prep, val, va_idx, regime, rng, args.reserve, args.b_max, seed, "val")
            models = {
                "SM (KM global)": lambda: fit_baseline("SM", obs),
                "NM (wins-only global)": lambda: fit_baseline("NM", obs),
                "NTM (tree, wins-only)": lambda: SurvivalTree(args.depth, args.min_leaf, seed, estimator="normal").fit(obs),
                "STM (tree, KM)": lambda: SurvivalTree(args.depth, args.min_leaf, seed).fit(obs),
                "STM pruned (val)": lambda: SurvivalTree(args.depth, args.min_leaf, seed).fit(obs, validation=val_obs),
            }
            fitted = {name: fit() for name, fit in models.items()}
            cui = CuiForecaster(n_estimators=args.cui_estimators, min_impressions=args.cui_min_impressions).fit(cui_rows)
            fitted["Cui lognormal mixture"] = ("cui", cui)
            fitted["Cui point-mean"] = ("cui_point", cui)
            index = {int(c): i for i, c in enumerate(uniq)}
            for name, model in fitted.items():
                F_u = pb.predict_matrix(prep, model, uniq)
                add(regime, name, policy_from_F(F_u, index), *offline(F_u))

    payload = {"args": {k: (list(v) if isinstance(v, tuple) else v) for k, v in vars(args).items()},
               "self_check": checks, "results": records}
    (out_dir / "results_online.json").write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
    return payload


def main(argv=None):
    rng_arg = lambda s: tuple(map(int, s.split(":")))
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--prepared", default=str(pb.ROOT / "benchmarks/logs/prepared_20261012_retry"))
    p.add_argument("--manager-ads", default=str(pb.STAND_DIR / "manager_target50_20261012.json"))
    p.add_argument("--our-ads", default=str(pb.ROOT / "benchmarks/log_benchmark/ads_manual.json"))
    p.add_argument("--output-dir", default=str(Path(__file__).resolve().parents[3] / "docs/benchmark/bid_forecast/results/price"))
    p.add_argument("--seeds", type=lambda s: [int(x) for x in s.split(",")], default=[19, 43, 71])
    p.add_argument("--sample", type=float, default=0.002)
    p.add_argument("--train-days", type=rng_arg, default=(0, 3))
    p.add_argument("--val-days", type=rng_arg, default=(3, 5))
    p.add_argument("--test-days", type=rng_arg, default=(5, 7))
    p.add_argument("--q", type=float, default=0.8)
    p.add_argument("--reserve", type=float, default=50.0)
    p.add_argument("--b-max", type=float, default=360.0)
    p.add_argument("--regimes", nargs="+", default=["full", "censored"], choices=["full", "censored"])
    p.add_argument("--train-cap", type=int, default=30000)
    p.add_argument("--val-cap", type=int, default=15000)
    p.add_argument("--depth", type=int, default=5)
    p.add_argument("--min-leaf", type=int, default=200)
    p.add_argument("--cui-estimators", type=int, default=20)
    p.add_argument("--cui-min-impressions", type=float, default=5)
    args = p.parse_args(argv)
    run(args)
    print(f"saved {args.output_dir}/results_online.json")


if __name__ == "__main__":
    main()
