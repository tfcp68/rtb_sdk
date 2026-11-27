"""Rigorous paired strategy-vs-random validation on fixed time windows.

This focused runner reuses the market/model machinery in ``multi_competitor``.
Environment seeds and bidding RNG replicates are deliberately separate: the
100 replicates quantify policy randomization conditional on one environment,
not 100 independent traffic samples.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import time
from pathlib import Path

import numpy as np

from . import multi_competitor as mc
from . import online_benchmark as ob
from . import price_benchmark as pb
from ..cui.cui2011 import CuiForecaster
from ..wang.wang2016 import SurvivalTree, fit_baseline


def validate_windows(train, val, test, n_days):
    windows = [tuple(map(int, x)) for x in (train, val, test)]
    if any(a < 0 or a >= b or b > n_days for a, b in windows):
        raise ValueError("windows must be non-empty and within available days")
    if not (windows[0][1] <= windows[1][0] and windows[1][1] <= windows[2][0]):
        raise ValueError("train, validation, and test windows must be ordered and disjoint")
    return windows


def paired_summary(strategy, random_runs):
    strategy, random_runs = np.asarray(strategy, float), np.asarray(random_runs, float)
    if strategy.ndim != 1 or strategy.shape != random_runs.shape or not len(strategy):
        raise ValueError("strategy and random runs must be non-empty, paired 1-D arrays")
    delta = strategy - random_runs
    rel = np.divide(delta, np.abs(random_runs), out=np.full_like(delta, np.nan), where=random_runs != 0)
    return {"strategy_mean": float(strategy.mean()), "random_mean": float(random_runs.mean()),
            "random_sd": float(random_runs.std(ddof=1)) if len(random_runs) > 1 else 0.0,
            "random_p05": float(np.quantile(random_runs, .05)), "random_p50": float(np.quantile(random_runs, .5)),
            "random_p95": float(np.quantile(random_runs, .95)),
            "fraction_random_runs_beaten": float(np.mean(strategy > random_runs)),
            "delta_mean": float(delta.mean()), "delta_median": float(np.median(delta)),
            "relative_delta_mean": float(np.nanmean(rel)) if np.isfinite(rel).any() else None,
            "paired_deltas": delta.tolist()}


def window_bootstrap(values, seed, n_boot=10000):
    """Percentile CI resampling temporal windows, never request or RNG rows."""
    x = np.asarray(values, float)
    if x.ndim != 1 or len(x) < 2:
        return {"n_windows": int(len(x)), "mean": float(x.mean()) if len(x) else None,
                "ci95": None, "warning": "fewer than two temporal windows"}
    rng = np.random.default_rng(seed)
    means = x[rng.integers(0, len(x), size=(n_boot, len(x)))].mean(axis=1)
    return {"n_windows": int(len(x)), "mean": float(x.mean()),
            "ci95": [float(np.quantile(means, .025)), float(np.quantile(means, .975))],
            "warning": "exploratory: windows share users and one seven-day source"}


def random_bids(v, reserve, seed, replicate):
    """Per-request U(R,v) random bids; same seed aligns these across policies/modes."""
    values = np.asarray(v, float)
    u = np.random.default_rng(seed).random(len(values))
    return reserve + u * np.maximum(values - reserve, 0), u


def _daily_folds(n_days):
    # Progressive, leakage-free folds; all labels used for fit/selection precede test.
    return [(tuple(range(0, 3)), tuple(range(3, 4)), tuple(range(4, 5))),
            (tuple(range(0, 4)), tuple(range(4, 5)), tuple(range(5, 6))),
            (tuple(range(0, 5)), tuple(range(5, 6)), tuple(range(6, 7)))] if n_days >= 7 else []


def _span(days):
    return (days[0], days[-1] + 1)


def _sha(path):
    h = hashlib.sha256()
    p = Path(path)
    files = [p] if p.is_file() else sorted(x for x in p.iterdir() if x.is_file())
    for f in files:
        h.update(f.name.encode())
        with f.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                h.update(block)
    return h.hexdigest()


def run(args):
    prep = mc.stand.load_prepared(args.prepared)
    pool = mc.stand.pool_mask_of(prep, mc.stand.POOL_DEVICES)
    base_ads = mc.stand.load_ads_file(args.manager_ads)
    our_ads = mc.stand.load_ads_file(args.our_ads)
    competitors = [base_ads] + [mc.make_competitor(base_ads, 1000 + i, vocabs=prep.vocabs, independent=True)
                                for i in range(1, args.competitors)]
    folds = _daily_folds(prep.n_days)
    if not folds:
        raise ValueError(f"requires at least 7 available days; found {prep.n_days}")
    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = outdir / "strategy_validation_checkpoint.json"
    raw, fold_results = [], []
    completed_folds = set()
    completed_reps = {}
    if args.resume and checkpoint_path.exists():
        checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        old_rows = checkpoint.get("raw_runs", [])
        raw = old_rows
        completed_reps = {int(k): int(v) for k, v in checkpoint.get("completed_reps", {}).items()}
        completed_folds = {int(x) for x in checkpoint.get("completed_folds", [])}
        # Backward-compatible restart from the earlier checkpoint shape.
        if not completed_folds and checkpoint.get("last_complete_fold") is not None:
            completed_folds = set(range(int(checkpoint["last_complete_fold"]) + 1))
        fold_results = checkpoint.get("folds_completed", [])
        if not checkpoint:
            completed_folds.clear()
            completed_reps.clear()
            fold_results.clear()
    raw = [r for r in raw if r.get("protocol_version") == 2]
    for f in range(len(folds)):
        random_rows = [r for r in raw if r.get("fold") == f and r.get("strategy") == "random bid U(R,v)"]
        reps = {int(r["replicate"]) for r in random_rows}
        if not reps:
            completed_reps[f] = 0
        else:
            complete = all(sum(r.get("fold") == f and r.get("replicate") == rep and r.get("mode") == mode
                               for r in raw) >= 8 for rep in reps
                           for mode in ("offline", "online_no_our_limits", "online_our_limits"))
            if not complete:
                raw = [r for r in raw if r.get("fold") != f]
                completed_reps[f] = 0
            else:
                completed_reps[f] = min(args.random_replicates, len(reps))
        print(f"resuming; preserving {len(raw)} records from folds {sorted(completed_folds)}", flush=True)
    for fold_i, (train_d, val_d, test_d) in enumerate(folds):
        if completed_reps.get(fold_i, 0) >= args.random_replicates:
            continue
        train_days, val_days, test_days = map(_span, (train_d, val_d, test_d))
        validate_windows(train_days, val_days, test_days, prep.n_days)
        env_seed = args.environment_seed + fold_i
        t0 = time.time()
        train = mc.run_market(prep, train_days, args.sample, competitors, our_ads, pool, args.q, env_seed, args.reserve)
        val = mc.run_market(prep, val_days, args.sample, competitors, our_ads, pool, args.q, env_seed, args.reserve)
        test = mc.run_market(prep, test_days, args.sample, competitors, our_ads, pool, args.q, env_seed, args.reserve)
        rng = np.random.default_rng(env_seed)
        tr_idx = rng.choice(len(train["z"]), min(args.train_cap, len(train["z"])), replace=False)
        va_idx = rng.choice(len(val["z"]), min(args.val_cap, len(val["z"])), replace=False)
        uniq = np.unique(test["combo"])
        index = {int(c): i for i, c in enumerate(uniq)}
        # Fit all available model variants once per fold/regime; never per bidding replicate.
        strategies = {}
        train_combo = train["combo"][tr_idx]
        for regime in ("full", "censored"):
            obs, cui_rows = pb.observations(prep, train, tr_idx, regime, rng, args.reserve, args.b_max, env_seed, "train")
            val_obs, _ = pb.observations(prep, val, va_idx, regime, rng, args.reserve, args.b_max, env_seed, "val")
            fitted = {
                "SM (KM global)": fit_baseline("SM", obs),
                "NM (wins-only global)": fit_baseline("NM", obs),
                "NTM (tree, wins-only)": SurvivalTree(5, 200, env_seed, estimator="normal").fit(obs),
                "STM (tree, KM)": SurvivalTree(5, 200, env_seed).fit(obs),
                "STM pruned (val)": SurvivalTree(5, 200, env_seed).fit(obs, validation=val_obs),
            }
            fitted["Cui lognormal mixture"] = ("cui", CuiForecaster(
                n_estimators=args.cui_estimators, min_impressions=args.cui_min_impressions).fit(cui_rows))
            fitted["Cui point-mean"] = ("cui_point", fitted["Cui lognormal mixture"][1])
            for model_name, model in fitted.items():
                F = pb.predict_matrix(prep, model, uniq)
                strategies[(regime, model_name)] = ob.policy_from_F(F, index)

        alpha_grid = pb.ALPHAS
        val_profits = [pb.profit_metrics(val["v"], a * val["v"], val["z"])["profit"] for a in alpha_grid]
        best_alpha = float(alpha_grid[int(np.argmax(val_profits))])
        strategies[("baseline", "shade alpha*v")] = lambda c, v, z, i: best_alpha * v

        # One deterministic no-bid test establishes the common request sequence and competitor reset.
        reference = mc.run_market(prep, test_days, args.sample, competitors, our_ads, pool, args.q, env_seed,
                                  args.reserve, lambda c, v, z, i: 0.0)
        base_market = mc.run_market(prep, test_days, args.sample, competitors, our_ads, pool, args.q, env_seed,
                                    args.reserve)
        if not (np.array_equal(reference["combo"], base_market["combo"]) and
                np.array_equal(reference["z"], base_market["z"])):
            raise AssertionError("fresh market state failed no-bid reset check")
        test_n = len(test["z"])
        policy_draws = [np.random.default_rng(args.bid_seed + fold_i * 1_000_000 + rep).random(test_n)
                        for rep in range(args.random_replicates)]
        existing_reps = {int(r["replicate"]) for r in raw if r.get("fold") == fold_i and
                          r.get("strategy") == "random bid U(R,v)"}
        for rep in range(args.random_replicates):
            if rep in existing_reps:
                continue
            u = policy_draws[rep]
            bid_seed = args.bid_seed + fold_i * 1_000_000 + rep
            random_policy = lambda c, v, z, i, u=u: args.reserve + u[i] * max(v - args.reserve, 0)
            random_bid = args.reserve + u * np.maximum(test["v"] - args.reserve, 0)
            random_won = (test["v"] > 0) & (random_bid > test["z"])
            random_offline_profit = float(((test["v"] - random_bid) * random_won).sum())
            if rep == 0 and not any(r.get("fold") == fold_i and r.get("strategy") == "STM (tree, KM)" and
                                     r.get("protocol_version") == 2 for r in raw):
                for (regime, name), policy in strategies.items():
                    bid = np.array([policy(c, v, z, i) for i, (c, v, z) in enumerate(zip(test["combo"], test["v"], test["z"]))])
                    won = (test["v"] > 0) & (bid > test["z"])
                    raw.append({"fold": fold_i, "environment_seed": env_seed, "replicate": rep,
                                "bid_seed": bid_seed, "regime": regime, "strategy": name, "mode": "offline",
                                "alpha_val": best_alpha, "profit": float(((test["v"] - bid) * won).sum()),
                                "wins": int(won.sum()), "spend": float((bid * won).sum()),
                                "paired_random_profit": random_offline_profit, "protocol_version": 2})
                    for mode, limits in (("online_no_our_limits", False), ("online_our_limits", True)):
                        online = mc.run_market(prep, test_days, args.sample, competitors, our_ads, pool, args.q,
                                               env_seed, args.reserve, policy, our_limits=limits)
                        if not np.array_equal(online["combo"], test["combo"]):
                            raise AssertionError("online request stream differs from fixed market")
                        online_won = online["won"]
                        online_profit = float(((online["v"] - online["b"]) * online_won).sum())
                        raw.append({"fold": fold_i, "environment_seed": env_seed, "replicate": rep,
                                    "bid_seed": bid_seed, "regime": regime, "strategy": name, "mode": mode,
                                    "alpha_val": best_alpha, "profit": online_profit,
                                    "wins": int(online_won.sum()), "spend": float((online["b"] * online_won).sum()),
                                    "outside_revenue": online["our_outside_revenue"],
                                    "total_profit_vs_no_market": online_profit + online["our_outside_revenue"] - base_market["our_outside_revenue"],
                                    "shown_by_competitor": online["shown"], "paired_random_profit": None,
                                    "protocol_version": 2})
            raw.append({"fold": fold_i, "environment_seed": env_seed, "replicate": rep,
                        "bid_seed": bid_seed, "regime": "baseline", "strategy": "random bid U(R,v)",
                        "mode": "offline", "alpha_val": best_alpha, "profit": random_offline_profit,
                        "wins": int(random_won.sum()), "spend": float((random_bid * random_won).sum()),
                        "share_random_bid_draw": float(u.mean()), "protocol_version": 2})
            for mode, limits in (("online_no_our_limits", False), ("online_our_limits", True)):
                online = mc.run_market(prep, test_days, args.sample, competitors, our_ads, pool, args.q,
                                       env_seed, args.reserve, random_policy, our_limits=limits)
                online_won = online["won"]
                online_profit = float(((online["v"] - online["b"]) * online_won).sum())
                raw.append({"fold": fold_i, "environment_seed": env_seed, "replicate": rep,
                            "bid_seed": bid_seed, "regime": "baseline", "strategy": "random bid U(R,v)",
                            "mode": mode, "alpha_val": best_alpha, "profit": online_profit,
                            "wins": int(online_won.sum()), "spend": float((online["b"] * online_won).sum()),
                            "outside_revenue": online["our_outside_revenue"],
                            "total_profit_vs_no_market": online_profit + online["our_outside_revenue"] - base_market["our_outside_revenue"],
                            "shown_by_competitor": online["shown"], "share_random_bid_draw": float(u.mean()),
                            "protocol_version": 2})
            completed_reps[fold_i] = len({int(r["replicate"]) for r in raw if r.get("fold") == fold_i and
                                          r.get("strategy") == "random bid U(R,v)"})
            checkpoint_path.write_text(json.dumps({"configuration": vars(args),
                "completed_reps": {str(k): v for k, v in completed_reps.items()},
                "completed_folds": sorted(completed_folds), "folds_completed": fold_results,
                "raw_runs": raw}, indent=1, ensure_ascii=False), encoding="utf-8")
        fold_results.append({"fold": fold_i, "train_days": list(train_days), "val_days": list(val_days),
                             "test_days": list(test_days), "environment_seed": env_seed, "rows": len(test["z"]),
                             "random_runs": args.random_replicates, "alpha_val": best_alpha,
                             "seconds": time.time() - t0,
                              "markets": {"train": int(len(train["z"])), "validation": int(len(val["z"])),
                                          "test": int(len(test["z"]))}})
        completed_folds.add(fold_i)
        checkpoint = {"configuration": vars(args), "completed_folds": sorted(completed_folds),
                      "folds_completed": fold_results, "raw_runs": raw}
        checkpoint_path.write_text(json.dumps(checkpoint, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"fold {fold_i}: days {test_days}, {test_n} test rows, alpha={best_alpha}, "
              f"{time.time()-t0:.1f}s", flush=True)

    groups = {}
    for row in raw:
        groups.setdefault((row["fold"], row["mode"], row["regime"], row["strategy"]), []).append(row)
    summaries = []
    by_key = {k: v for k, v in groups.items()}
    for (fold, mode, regime, name), values in by_key.items():
        randkey = (fold, mode, "baseline", "random bid U(R,v)")
        if name == "random bid U(R,v)" or randkey not in by_key:
            continue
        strategy_by_rep = {int(r["replicate"]): r["profit"] for r in values}
        random_by_rep = {int(r["replicate"]): r["profit"] for r in by_key[randkey]}
        common = sorted(strategy_by_rep.keys() & random_by_rep.keys())
        if not common:
            continue
        summaries.append({"fold": fold, "mode": mode, "regime": regime, "strategy": name,
                          **paired_summary([strategy_by_rep[i] for i in common],
                                           [random_by_rep[i] for i in common])})
    # Environment-level uncertainty: average over bid RNG first, then resample only distinct time windows.
    window_deltas = {}
    for s in summaries:
        window_deltas.setdefault((s["mode"], s["regime"], s["strategy"]), []).append(s["delta_mean"])
    intervals = [{"mode": k[0], "regime": k[1], "strategy": k[2],
                  **window_bootstrap(v, args.environment_seed)} for k, v in window_deltas.items()]
    payload = {"configuration": vars(args), "provenance": {"prepared_sha256": _sha(args.prepared),
                "manager_ads_sha256": _sha(args.manager_ads), "our_ads_sha256": _sha(args.our_ads),
                "python": platform.python_version(), "numpy": np.__version__,
                "source_days": prep.n_days, "source_t0_unix": prep.meta.get("t0"),
                "folds": fold_results, "interpretation": "100 bids are conditional replicates within each fixed environment; not independent temporal samples."},
                "raw_runs": raw, "paired_summaries": summaries, "window_level_intervals": intervals}
    (outdir / "strategy_validation_raw.json").write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
    return payload


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--prepared", required=True)
    p.add_argument("--manager-ads", required=True)
    p.add_argument("--our-ads", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--sample", type=float, default=.002)
    p.add_argument("--q", type=float, default=.8)
    p.add_argument("--reserve", type=float, default=50.)
    p.add_argument("--b-max", type=float, default=360.)
    p.add_argument("--competitors", type=int, default=3)
    p.add_argument("--train-cap", type=int, default=30000)
    p.add_argument("--val-cap", type=int, default=15000)
    p.add_argument("--cui-estimators", type=int, default=20)
    p.add_argument("--cui-min-impressions", type=float, default=5)
    p.add_argument("--random-replicates", type=int, default=100)
    p.add_argument("--environment-seed", type=int, default=1900)
    p.add_argument("--bid-seed", type=int, default=1000)
    p.add_argument("--resume", action="store_true")
    args = p.parse_args(argv)
    if args.random_replicates != 100:
        p.error("the requested protocol fixes exactly 100 bidding RNG replicates")
    run(args)


if __name__ == "__main__":
    main()
