"""Compare frozen policies with bid-randomized U(R,v) runs on one fixed scenario."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
from pathlib import Path


def finite(value, name):
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


def online_metrics(out):
    v, b, won = (list(out[k]) for k in ("v", "b", "won"))
    if not (len(v) == len(b) == len(won)) or any(not math.isfinite(float(x)) for x in v + b):
        raise ValueError("online arrays must have equal shapes and finite numeric values")
    profit = sum((float(value) - float(bid)) * bool(win) for value, bid, win in zip(v, b, won))
    outside = finite(out["our_outside_revenue"], "outside revenue")
    return {"market_profit": profit, "ours_total": profit + outside, "outside_revenue": outside,
            "spend": sum(float(bid) * bool(win) for bid, win in zip(b, won)), "wins": sum(map(bool, won))}


def profit_metrics(v, bids, z):
    profit = sum((float(value) - float(bid)) for value, bid, price in zip(v, bids, z) if value > 0 and bid > price)
    return {"profit": profit}


def select_alpha(scores):
    if not scores or any(not math.isfinite(float(v)) for v in scores.values()):
        raise ValueError("alpha scores must be a non-empty finite mapping")
    alpha = max(scores, key=scores.get)
    return {"selected_alpha": float(alpha), "scores": {str(k): float(v) for k, v in scores.items()}}


def compare_runs(strategy, random_runs, shading_total=None):
    s = finite(strategy, "strategy total")
    x = [finite(value, "random total") for value in random_runs]
    if not x:
        raise ValueError("random runs must be a non-empty finite 1-D sequence")
    ordered = sorted(x)
    delta = [s - value for value in x]
    def qlinear(q):
        pos = (len(ordered) - 1) * q
        lo = math.floor(pos)
        return ordered[lo] + (ordered[min(lo + 1, len(ordered) - 1)] - ordered[lo]) * (pos - lo)
    p05, p50, p95 = qlinear(.05), qlinear(.5), qlinear(.95)
    shade = s if shading_total is None else finite(shading_total, "shading total")
    return {"strategy_ours_total": s, "random_mean": sum(x) / len(x), "delta_mean": sum(delta) / len(delta),
            "delta_min": min(delta), "delta_max": max(delta), "delta_vs_shading": s - shade,
            "delta_vs_shading_mean": s - shade,
            "random_min": min(x),
            "random_max": max(x), "random_p05": p05,
            "random_p50": p50, "random_p95": p95,
            "fraction_random_runs_beaten": sum(s > value for value in x) / len(x), "ties": sum(s == value for value in x),
            "deltas": delta, "paired_deltas": delta, "exceeds_random_p95": bool(s > p95),
            "interpretation": "descriptive conditional distribution; not a confidence interval"}


def write_report(directory, payload):
    directory = Path(directory)
    if directory.exists() and any(directory.iterdir()):
        raise FileExistsError(f"refusing to overwrite non-empty output directory: {directory}")
    directory.mkdir(parents=True, exist_ok=True)
    paths = (directory / "fixed_scenario_validation.json", directory / "fixed_scenario_validation.md")
    if any(p.exists() for p in paths):
        raise FileExistsError(f"refusing to overwrite report: {next(p for p in paths if p.exists())}")
    rows = payload["comparisons"]
    lines = ["# Fixed-scenario strategy validation", "", "Conditional descriptive results; bid seeds are not independent traffic periods.",
             "", "| Strategy | Total | Random mean | Strategy delta vs frozen shading | Delta vs random min/max | p05 | p50 | p95 | Strictly beaten | Ties | Exceeds p95 |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    lines += [f"| {r['strategy']} | {r['strategy_ours_total']:.4g} | {r['random_mean']:.4g} | "
              f"{r['delta_vs_shading']:.4g} | {r['delta_min']:.4g}/{r['delta_max']:.4g} | "
              f"{r['random_p05']:.4g} | {r['random_p50']:.4g} | {r['random_p95']:.4g} | "
              f"{r['fraction_random_runs_beaten']:.3f} | "
              f"{r['ties']} | {r['exceeds_random_p95']} |" for r in rows]
    paths[0].write_text(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    paths[1].write_text("\n".join(lines) + "\n", encoding="utf-8")
    return paths


def sha256(path):
    p = Path(path)
    files = [p] if p.is_file() else sorted(x for x in p.rglob("*") if x.is_file())
    if not files:
        raise FileNotFoundError(f"source contains no files: {p}")
    digest = hashlib.sha256()
    for f in files:
        digest.update(f.relative_to(p).as_posix().encode() if p.is_dir() else f.name.encode())
        with f.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    return digest.hexdigest()


def run(args):
    try:
        environment_seed, bid_seed = int(args.environment_seed), int(args.bid_seed)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("environment and bid seeds must be integers") from exc
    if isinstance(args.environment_seed, bool) or isinstance(args.bid_seed, bool) or \
            environment_seed != args.environment_seed or bid_seed != args.bid_seed:
        raise ValueError("environment and bid seeds must be integers")
    if environment_seed < 0 or bid_seed < 0:
        raise ValueError("environment and bid seeds must be non-negative")
    if args.random_replicates != 100 or min(args.competitors, args.train_cap, args.val_cap,
                                           args.cui_estimators, args.depth, args.min_leaf) < 1:
        raise ValueError("random_replicates must be 100 and model/count settings positive")
    if not all(math.isfinite(x) for x in (args.sample, args.q, args.reserve, args.b_max, args.cui_min_impressions)):
        raise ValueError("numeric arguments must be finite")
    if not 0 < args.sample <= 1 or not 0 < args.q <= 1 or args.reserve < 0 or args.b_max <= args.reserve:
        raise ValueError("require 0<sample,q<=1 and 0<=reserve<b_max")
    if args.cui_min_impressions < 0:
        raise ValueError("cui_min_impressions must be non-negative")
    args.environment_seed, args.bid_seed = environment_seed, bid_seed
    for label, path in (("prepared data", args.prepared), ("manager ads", args.manager_ads), ("our ads", args.our_ads)):
        if not Path(path).exists():
            raise FileNotFoundError(f"{label} not found: {path}")
    import numpy as np

    from . import multi_competitor as mc
    from . import online_benchmark as ob
    from . import price_benchmark as pb
    from . import probability_diagnostics as pd
    from ..cui.cui2011 import CuiForecaster
    from ..wang.wang2016 import SurvivalTree, fit_baseline

    if Path(args.output_dir).exists() and any(Path(args.output_dir).iterdir()):
        raise FileExistsError(f"output directory is not empty: {args.output_dir}")
    prep = mc.stand.load_prepared(args.prepared)
    if prep.n_days < 7:
        raise ValueError(f"fixed split requires at least 7 days; found {prep.n_days}")
    pool = mc.stand.pool_mask_of(prep, mc.stand.POOL_DEVICES)
    from .planning import build_planning_context
    planning = build_planning_context(prep, (0, 3), args.sample, pool)
    manager, ours = mc.stand.load_ads_file(args.manager_ads), mc.stand.load_ads_file(args.our_ads)
    competitors = [manager] + [mc.make_competitor(manager, 1000 + i, vocabs=prep.vocabs, independent=True)
                               for i in range(1, args.competitors)]
    args.environment_seed = int(args.environment_seed)
    split_config = {"train": [0, 3], "validation": [3, 5], "test": [5, 7]}
    print("Generating fixed train/validation/test observations...", flush=True)
    phases = {phase: mc.run_market(prep, days, args.sample, competitors, ours, pool, args.q,
                                   args.environment_seed, args.reserve, planning=planning)
              for phase, days in (("train", (0, 3)), ("validation", (3, 5)), ("test", (5, 7)))}
    train, val, test = (phases[k] for k in ("train", "validation", "test"))
    if any(len(phases[k]["z"]) == 0 for k in ("train", "validation", "test")):
        raise ValueError("each fixed time split must contain at least one request")
    rng = np.random.default_rng(args.environment_seed)
    tr_idx = rng.choice(len(train["z"]), min(args.train_cap, len(train["z"])), replace=False)
    va_idx = rng.choice(len(val["z"]), min(args.val_cap, len(val["z"])), replace=False)
    # Feature IDs define prediction rows; test labels/prices are not used to construct this domain.
    uniq = np.unique(np.concatenate([train["combo"], val["combo"], test["combo"]]))
    index = {int(c): i for i, c in enumerate(uniq)}
    strategies = {}
    predictors = {}
    settings = {"tree_depth": args.depth, "min_leaf": args.min_leaf, "cui_estimators": args.cui_estimators,
                "cui_min_impressions": args.cui_min_impressions}
    for regime in ("full", "censored"):
        print(f"Fitting {regime} models once...", flush=True)
        obs, cui_rows = pb.observations(prep, train, tr_idx, regime, rng, args.reserve, args.b_max,
                                         args.environment_seed, "train")
        val_obs, _ = pb.observations(prep, val, va_idx, regime, rng, args.reserve, args.b_max,
                                     args.environment_seed, "val")
        fitted = {"SM (KM global)": fit_baseline("SM", obs), "NM (wins-only global)": fit_baseline("NM", obs),
                  "NTM (tree, wins-only)": SurvivalTree(args.depth, args.min_leaf, args.environment_seed, estimator="normal").fit(obs),
                  "STM (tree, KM)": SurvivalTree(args.depth, args.min_leaf, args.environment_seed).fit(obs),
                  "STM pruned (validation)": SurvivalTree(args.depth, args.min_leaf, args.environment_seed).fit(obs, validation=val_obs)}
        cui = CuiForecaster(n_estimators=args.cui_estimators, min_impressions=args.cui_min_impressions).fit(cui_rows)
        fitted.update({"Cui lognormal mixture": ("cui", cui), "Cui point-mean": ("cui_point", cui)})
        for name, model in fitted.items():
            F = pb.predict_matrix(prep, model, uniq)
            if F.shape != (len(uniq), len(pb.GRID)) or not np.isfinite(F).all():
                raise ValueError("model probability matrix must be finite and aligned to GRID")
            strategies[(regime, name)] = ob.policy_from_F(F, index)
            predictors[(regime, name)] = F
    scores = {}
    for a in pb.ALPHAS:
        alpha = float(a)
        val_online = mc.run_market(prep, (3, 5), args.sample, competitors, ours, pool, args.q,
                                   args.environment_seed, args.reserve,
                                    lambda c, v, z, i, a=alpha: a * v, our_limits=True, planning=planning)
        scores[alpha] = online_metrics(val_online)["ours_total"]
        print(f"Validation alpha={alpha:g}: ours_total={scores[alpha]:.6g}", flush=True)
    alpha = select_alpha(scores)
    strategies[("baseline", "shade alpha*v")] = lambda c, v, z, i: alpha["selected_alpha"] * v
    strategies[("baseline", "truthful b=v")] = lambda c, v, z, i: v
    n = len(test["z"])
    raw, grouped = [], {}
    for rep in range(args.random_replicates):
        if rep % 10 == 0:
            print(f"Random online replay {rep + 1}/{args.random_replicates}...", flush=True)
        u = np.random.default_rng(args.bid_seed + rep).random(n)
        seed = args.bid_seed + rep
        policy = lambda c, v, z, i, u=u: args.reserve + u[i] * max(v - args.reserve, 0)
        out = mc.run_market(prep, (5, 7), args.sample, competitors, ours, pool, args.q, args.environment_seed,
                            args.reserve, policy, our_limits=True, planning=planning)
        if not np.array_equal(out["combo"], test["combo"]):
            raise AssertionError("request stream differs between fixed-scenario runs")
        metrics = online_metrics(out)
        eligible = out["v"] > 0
        local = pd.local_oracle_metrics(out["v"], out["z"], out["b"], pb.GRID)
        record = {"strategy": "random bid U(R,v)", "replicate": rep, "bid_seed": seed,
                  "environment_seed": args.environment_seed, **metrics,
                  "actual_decision_quality": {"status": "probability_not_available",
                      "eligible_n": int(eligible.sum()), "n_all": len(out["v"]),
                      "eligible_win_rate": float(out["won"][eligible].mean()) if eligible.any() else None,
                      "eligible_mean_bid": float(out["b"][eligible].mean()) if eligible.any() else None,
                      "eligible_spend": float(np.sum(out["b"] * out["won"] * eligible)),
                      "eligible_actual_margin": float(np.sum((out["v"] - out["b"]) * out["won"] * eligible)),
                      "local_oracle_margin_sum": local["oracle_margin_sum"],
                      "actual_margin_sum": local["actual_margin_sum"], "local_regret_sum": local["regret_sum"],
                      "actual_bids_all_on_grid": local["actual_bids_all_on_grid"],
                      "oracle_scope": local["scope"]}}
        raw.append(record)
    print("Replaying each frozen policy once...", flush=True)
    for name, fixed in strategies.items():
        result = mc.run_market(prep, (5, 7), args.sample, competitors, ours, pool, args.q,
                                args.environment_seed, args.reserve, fixed, our_limits=True, planning=planning)
        if not np.array_equal(result["combo"], test["combo"]):
            raise AssertionError("request stream differs between policies")
        metric = online_metrics(result)
        raw.append({"strategy": name[1], "regime": name[0], "replicate": None,
                    "environment_seed": args.environment_seed, **metric})
        grouped[name] = metric
    comparisons = [{"strategy": f"{regime}: {name}", **compare_runs(metrics["ours_total"],
                    [r["ours_total"] for r in raw if r["strategy"] == "random bid U(R,v)"],
                    shading_total=grouped[("baseline", "shade alpha*v")]["ours_total"])}
                    for (regime, name), metrics in grouped.items()]
    # A single RNG-generated test bid per row forms the common off-policy probe for every frozen model.
    probe_rng = np.random.default_rng(args.bid_seed + 1000003)
    probe_idx = probe_rng.integers(np.searchsorted(pb.GRID, args.reserve),
                                   np.searchsorted(pb.GRID, args.b_max) + 1, n)
    probe_bids = pb.GRID[probe_idx]
    common_probe = {"seed": args.bid_seed + 1000003, "rows": n,
                    "positive_bid_n": int(np.sum((test["v"] > 0) & (probe_bids > 0))),
                    "input_sha256": hashlib.sha256(np.asarray(test["combo"], dtype=np.int64).tobytes() +
                                                    np.asarray(test["v"], dtype=np.float64).tobytes() +
                                                    np.asarray(test["z"], dtype=np.float64).tobytes() +
                                                    np.asarray(probe_bids, dtype=np.float64).tobytes()).hexdigest(),
                    "description": "static off-policy counterfactual; same request/value/price/bid rows for all models; not their endogenous trajectories",
                    "bids": probe_bids.tolist()}
    diagnostics = {}
    # Replay records above are enriched from deterministic policy reruns without altering the bids.
    for key, policy in strategies.items():
        result = mc.run_market(prep, (5, 7), args.sample, competitors, ours, pool, args.q,
                               args.environment_seed, args.reserve, policy, our_limits=True, planning=planning)
        F = predictors.get(key)
        idx_unique = np.searchsorted(uniq, result["combo"])
        if F is None:
            metrics = {"status": "not_available", "reason": "policy has no probability predictor"}
            probe = {"status": "not_available", "reason": "policy has no probability predictor"}
        else:
            metrics = pd.probability_metrics(F, idx_unique, pb.GRID, result["b"], result["z"],
                                             result["v"] > 0, result["v"])
            probe = pd.probability_metrics(F, np.searchsorted(uniq, test["combo"]), pb.GRID, probe_bids, test["z"],
                                          test["v"] > 0, test["v"])
        local = pd.local_oracle_metrics(result["v"], result["z"], result["b"], pb.GRID)
        actual = online_metrics(result)
        eligible = result["v"] > 0
        actual.update({"eligible_win_rate": float(result["won"][eligible].mean()) if eligible.any() else None,
                       "eligible_mean_bid": float(result["b"][eligible].mean()) if eligible.any() else None,
                       "eligible_spend": float(np.sum(result["b"] * result["won"] * eligible)),
                       "eligible_actual_margin": float(np.sum((result["v"] - result["b"]) * result["won"] * eligible))})
        diagnostics[f"{key[0]}: {key[1]}"] = {"chosen_bid_probability": metrics, "common_probe": probe,
                                                "local_oracle": local, "actual_replay": actual}
    import articles_prorotypes.cui.cui2011 as cui_module
    import articles_prorotypes.wang.wang2016 as wang_module
    source_files = {"fixed_scenario_validation.py": Path(__file__),
                    "probability_diagnostics.py": Path(pd.__file__),
                    "multi_competitor.py": Path(mc.__file__), "online_benchmark.py": Path(ob.__file__),
                    "price_benchmark.py": Path(pb.__file__),
                     "stand.py": Path(getattr(mc.stand, "__file__", Path(mc.__file__).parents[2] / "benchmarks" / "closed_stand" / "stand.py")),
                     "ads.py": Path(__import__("ads").__file__),
                     "stream.py": Path(__import__("stream").__file__),
                     "planning.py": Path(__import__("articles_prorotypes.bench.planning", fromlist=["__file__"]).__file__),
                    "wang2016.py": Path(wang_module.__file__), "cui2011.py": Path(cui_module.__file__)}
    payload = {"configuration": vars(args), "provenance": {"source_hashes": {"prepared": sha256(args.prepared),
               "manager_ads": sha256(args.manager_ads), "our_ads": sha256(args.our_ads)},
               "code_sha256": {name: sha256(path) for name, path in source_files.items()},
               "python": platform.python_version(), "numpy": np.__version__, "source_days": prep.n_days,
                "split": split_config, "request_counts": {phase: int(len(data["z"])) for phase, data in phases.items()},
                "campaign_planning": {"training_days": list(planning.train_days),
                    "training_combo_counts": list(planning.match_counts),
                    "total_daily_requests": planning.total_daily_rate,
                    "pool_daily_requests": planning.pool_daily_rate,
                    "sample": planning.sample,
                    "formula": "volume=max(1, round(training_daily_nominal * phase_days * volume_factor * weighted_match_rate / sum_weighted_match_rates))",
                    "plans": {phase: phases[phase]["campaign_plans"]
                              for phase in phases}},
               "environment_seed": args.environment_seed, "model_settings": settings,
                "interpretation": "Bidding-seed variation is conditional on one fixed environment; no traffic CI.",
                "probability_diagnostics": {"version": pd.VERSION, "grid_clipping": "none; exact GRID bid lookup required",
                    "probe": common_probe, "metrics": diagnostics}},
               "validation_alpha": alpha, "raw_runs": raw, "comparisons": comparisons}
    write_report(args.output_dir, payload)
    return payload


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", required=True)
    parser.add_argument("--manager-ads", required=True)
    parser.add_argument("--our-ads", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--sample", type=float, default=.002)
    parser.add_argument("--q", type=float, default=.8)
    parser.add_argument("--reserve", type=float, default=50.)
    parser.add_argument("--b-max", type=float, default=360.)
    parser.add_argument("--competitors", type=int, default=3)
    parser.add_argument("--train-cap", type=int, default=30000)
    parser.add_argument("--val-cap", type=int, default=15000)
    parser.add_argument("--cui-estimators", type=int, default=20)
    parser.add_argument("--cui-min-impressions", type=float, default=5.)
    parser.add_argument("--random-replicates", type=int, default=100)
    parser.add_argument("--environment-seed", type=int, default=1900)
    parser.add_argument("--bid-seed", type=int, default=1000)
    parser.add_argument("--depth", type=int, default=5)
    parser.add_argument("--min-leaf", type=int, default=200)
    args = parser.parse_args(argv)
    if args.random_replicates != 100:
        parser.error("the protocol fixes exactly 100 random bid seeds")
    if not all(math.isfinite(x) for x in (args.sample, args.q, args.reserve, args.b_max, args.cui_min_impressions)):
        parser.error("numeric arguments must be finite")
    if not 0 < args.sample <= 1 or not 0 < args.q <= 1 or args.reserve < 0 or args.b_max <= args.reserve:
        parser.error("require 0<sample,q<=1 and 0<=reserve<b-max")
    if min(args.competitors, args.train_cap, args.val_cap, args.cui_estimators, args.depth, args.min_leaf) < 1 or args.cui_min_impressions < 0:
        parser.error("counts must be positive and cui-min-impressions non-negative")
    try:
        run(args)
    except (FileNotFoundError, FileExistsError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
