"""Win-probability and bid-optimality benchmark of Wang (2016) / Cui (2011) on closed-stand logs.

Labels come from the stand itself (benchmarks/closed_stand/stand.py::simulate, unchanged):
  z  market price of a request sent to the manager = cpm of the winner of the manager's internal best_price
     auction (all stand filters applied), or the reserve R when the manager answers 204;
  v  our value = max cpm of our campaigns (ads_manual.json) whose targeting matches the request.
The manager's auction is first-price (winner pays its own cpm), so we bid b and get (v - b)·1[b > z].

Training regimes (what the bidder saw in the past):
  full      z observed on every training request (platform view, Cui's setting);
  censored  random exploration bids b ~ U(R, B_MAX): on a win z is observed, on a loss only z >= b (Wang's setting).
Test labels z are evaluator-only. Replay assumption: our winning does not change the manager's state.
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.special import ndtr

from ..cui.cui2011 import CuiForecaster, lognormal_parameters
from ..wang.wang2016 import AuctionObservation, SurvivalTree, fit_baseline

ROOT = Path(__file__).resolve().parents[2]
STAND_DIR = ROOT / "benchmarks" / "closed_stand"
sys.path.insert(0, str(STAND_DIR))
stand = importlib.import_module("stand")
RandomShare = importlib.import_module("routers").RandomShare

GRID = np.arange(0, 401, dtype=float)      # integer bids; F[:, j] = P(z < GRID[j])
TARGETS = (0.5, 0.8, 0.95)                  # target win rates for benchmark 1
ALPHAS = np.round(np.arange(0.3, 1.001, 0.05), 2)


# ───────────────────────────── data ─────────────────────────────

def generate(prep, days, sample, mgr_ads, our_ads, pool_mask, q, seed, reserve):
    """Run the stand once and return per-sent-request (combo, ts, z, v)."""
    sellers = []

    class Recording(stand.Seller):
        def __init__(self, *args):
            super().__init__(*args)
            self.winners = []
            sellers.append(self)

        def serve(self, t, u, c):
            w = super().serve(t, u, c)
            self.winners.append(w)
            return w

    original, stand.Seller = stand.Seller, Recording
    try:
        res = stand.simulate(prep, days, sample, mgr_ads, our_ads, pool_mask, q,
                             lambda: RandomShare(pool_mask, prep.combos, q, seed), 150.0,
                             seed=seed, collect_log=True)
    finally:
        stand.Seller = original
    mgr, ours = sellers                      # simulate() builds the manager first
    ts, _, combo, codes = res["_log"]
    w = np.asarray(mgr.winners)
    assert len(w) == len(codes) and np.array_equal(w >= 0, codes == 200), "winner log out of sync with stand log"
    z = np.where(w >= 0, np.asarray(mgr.cpm, float)[np.maximum(w, 0)], reserve)
    value = np.array([max((ours.cpm[a] for a in m), default=0.0) for m in ours.match], dtype=float)
    return dict(combo=combo.astype(np.int64), ts=ts, z=z, v=value[combo], sellthrough=res["sellthrough"])


def exploration_bids(seed, phase, n, reserve, b_max):
    """Censored-regime exploration bids: own generator per (seed, phase), so every script trains the same models."""
    return np.random.default_rng([seed, 7, {"train": 0, "val": 1}[phase]]).uniform(reserve, b_max, n)


def random_bid_u(seed, n):
    """One uniform per test row for the random-bid policy b = R + u·(v − R): identical offline and in every online mode."""
    return np.random.default_rng([seed, 1000]).random(n)


def observations(prep, data, idx, regime, rng, reserve, b_max, seed=None, phase="train"):
    names = prep.vocab_order
    tags = prep.combos[data["combo"][idx]].tolist()
    z = data["z"][idx]
    if regime == "full":
        bids = z + 1.0
    else:
        bids = exploration_bids(seed, phase, len(idx), reserve, b_max)
    obs, cui_rows = [], []
    for t, zi, b in zip(tags, z.tolist(), bids.tolist()):
        f = dict(zip(names, t))
        won = b > zi
        obs.append(AuctionObservation(f, b, won, zi if won else None))
        if won:                              # Cui only ever sees observed prices
            cui_rows.append({"target": f, "features": {}, "bid": zi})
    return obs, cui_rows


# ───────────────────────────── models → CDF on GRID ─────────────────────────────

def cdf_of_distribution(dist):
    prices = np.array(sorted(dist.masses), dtype=float)
    cum = np.concatenate([[0.0], np.cumsum([dist.masses[p] for p in sorted(dist.masses)])])
    return cum[np.searchsorted(prices, GRID, side="left")]


def cdf_lognormal(mean, std, point=False):
    if point or std <= 0:
        return (GRID > mean).astype(float)
    mu, sigma = lognormal_parameters(mean, std)
    with np.errstate(divide="ignore"):
        return ndtr((np.log(GRID) - mu) / sigma)


def predict_matrix(prep, model, uniq):
    names = prep.vocab_order
    feats = [dict(zip(names, t)) for t in prep.combos[uniq].tolist()]
    if isinstance(model, tuple):             # ("cui"|"cui_point", forecaster)
        point = model[0] == "cui_point"
        return np.vstack([cdf_lognormal(s.mean, s.std, point) for s in model[1].predict_samples(feats)])
    return np.vstack([cdf_of_distribution(model.predict(f)) for f in feats])


def empirical_matrix(combo, z, uniq):
    """Evaluator-only ceiling: empirical CDF of the TEST z per tag combination."""
    out = np.empty((len(uniq), len(GRID)))
    order = np.argsort(combo, kind="stable")
    sc, sz = combo[order], z[order]
    starts = np.searchsorted(sc, uniq, "left")
    ends = np.searchsorted(sc, uniq, "right")
    for i, (s, e) in enumerate(zip(starts, ends)):
        zs = np.sort(sz[s:e])
        out[i] = np.searchsorted(zs, GRID, "left") / len(zs)
    return out


# ───────────────────────────── metrics ─────────────────────────────

def probability_metrics(F_u, inv, z, eval_idx, reserve, b_max, rows=None):
    """Benchmark 1 on rows (all if None). F_u: (n_unique, |GRID|) P(z < g); inv maps rows to unique combos."""
    if rows is not None:
        inv, z, eval_idx = inv[rows], z[rows], eval_idx[rows]
    y = z < GRID[eval_idx]
    p = F_u[inv, eval_idx]
    pc = np.clip(p, 1e-6, 1 - 1e-6)
    bins = np.minimum((p * 10).astype(int), 9)
    ece = sum(abs(p[bins == k].mean() - y[bins == k].mean()) * (bins == k).sum() for k in range(10) if (bins == k).any())
    band = (GRID >= reserve) & (GRID <= b_max)
    crps = 0.0
    for s in range(0, len(z), 20000):
        sl = slice(s, s + 20000)
        crps += ((F_u[inv[sl]][:, band] - (z[sl, None] < GRID[band])) ** 2).sum()
    out: dict[str, float | None] = {"brier": float(np.mean((p - y) ** 2)),
           "log_loss": float(-np.mean(y * np.log(pc) + (~y) * np.log1p(-pc))),
           "ece": float(ece / len(p)),
           "crps": float(crps / (len(z) * band.sum()))}
    for target in TARGETS:
        ok = F_u >= target
        reachable = ok.any(1)[inv]
        idx = np.where(ok.any(1), ok.argmax(1), len(GRID) - 1)[inv]
        out[f"reachable@{target}"] = float(reachable.mean())
        out[f"win@{target}"] = float(np.mean(z[reachable] < GRID[idx[reachable]])) if reachable.any() else None
        out[f"bid@{target}"] = float(np.mean(GRID[idx[reachable]])) if reachable.any() else None
        fallback = ~reachable
        out[f"fallback_win@{target}"] = float(np.mean(z[fallback] < GRID[idx[fallback]])) if fallback.any() else None
        out[f"fallback_bid@{target}"] = float(np.mean(GRID[idx[fallback]])) if fallback.any() else None
    return out


def conditional_on_competition(F_u, reserve):
    """P(z < g | z > reserve) from the model's own F: exact conditioning, uses no test data.

    F(g) = P(z < g); mass at the reserve is P(z <= reserve) = F(reserve + 1) on the integer grid."""
    at_reserve = F_u[:, np.searchsorted(GRID, reserve) + 1]
    rest = 1.0 - at_reserve
    cond = np.where(rest[:, None] > 1e-12, (F_u - at_reserve[:, None]) / np.maximum(rest, 1e-12)[:, None], 0.0)
    return np.clip(np.where(GRID[None, :] <= reserve, 0.0, cond), 0.0, 1.0)


def evaluate(F_u, inv, z, v_u, eval_idx, reserve, b_max):
    """Both benchmarks on all test rows, plus the same on competed rows (z > reserve) with suffix _comp.

    Bids are always the model's own b* (it does not know which rows are free); competed-row profit uses those bids."""
    assert z.max() < GRID[-1] and v_u.max() <= GRID[-1], "price or value beyond the bid grid: extend GRID"
    F_u = np.clip(F_u, 0.0, 1.0)
    out = probability_metrics(F_u, inv, z, eval_idx, reserve, b_max)
    comp = z > reserve
    cond = probability_metrics(conditional_on_competition(F_u, reserve), inv, z, eval_idx, reserve, b_max, comp)
    out.update({f"{k}_comp": val for k, val in cond.items()})
    # benchmark 2: b* = argmax_{g <= v} (v - g) F(g); v depends only on the combo
    expected = (v_u[:, None] - GRID) * F_u
    expected[GRID[None, :] > v_u[:, None]] = -np.inf
    b_u = GRID[expected.argmax(1)]
    b_u[v_u <= 0] = 0.0
    v, b = v_u[inv], b_u[inv]
    out.update(profit_metrics(v, b, z))
    out.update({f"{k}_comp": val for k, val in profit_metrics(v[comp], b[comp], z[comp]).items()})
    out["expected_profit"] = float(np.where(v_u > 0, expected.max(1), 0)[inv].sum())
    return out


def profit_metrics(v, b, z):
    won = (z < b) & (v > 0)
    return {"profit": float(((v - b) * won).sum()), "wins": int(won.sum()), "spend": float((b * won).sum()),
            "win_rate_valued": float(won.sum() / max((v > 0).sum(), 1))}


def oracle_profit(v, z):
    return float(np.clip(v - z - 1, 0, None)[v > 0].sum())


# ───────────────────────────── run ─────────────────────────────

def run(args):
    prep = stand.load_prepared(args.prepared)
    pool_mask = stand.pool_mask_of(prep, stand.POOL_DEVICES)
    mgr_ads, our_ads = stand.load_ads_file(args.manager_ads), stand.load_ads_file(args.our_ads)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    records, data_stats = [], []
    for seed in args.seeds:
        rng = np.random.default_rng(seed)
        phases = {}
        for phase, days in (("train", args.train_days), ("val", args.val_days), ("test", args.test_days)):
            t0 = time.time()
            phases[phase] = generate(prep, days, args.sample, mgr_ads, our_ads, pool_mask, args.q, seed, args.reserve)
            d = phases[phase]
            data_stats.append({"seed": seed, "phase": phase, "days": list(days), "rows": len(d["z"]),
                               "share_204": float(np.mean(d["z"] == args.reserve)),
                               "rows_competed": int(np.sum(d["z"] > args.reserve)),
                               "share_valued": float(np.mean(d["v"] > 0)),
                               "mean_z": float(d["z"].mean()), "mean_v_valued": float(d["v"][d["v"] > 0].mean()),
                               "sellthrough": d["sellthrough"], "seconds": time.time() - t0})
            print(f"seed {seed} {phase}: {len(d['z'])} sent, 204 {data_stats[-1]['share_204']:.3f}", flush=True)
        train, val, test = phases["train"], phases["val"], phases["test"]
        tr_idx = rng.choice(len(train["z"]), min(args.train_cap, len(train["z"])), replace=False)
        va_idx = rng.choice(len(val["z"]), min(args.val_cap, len(val["z"])), replace=False)
        uniq, inv = np.unique(test["combo"], return_inverse=True)
        v_u = np.zeros(len(uniq))
        v_u[inv] = test["v"]
        eval_idx = rng.integers(np.searchsorted(GRID, args.reserve), np.searchsorted(GRID, args.b_max) + 1, len(test["z"]))
        ceiling = oracle_profit(test["v"], test["z"])
        comp = test["z"] > args.reserve
        ceiling_comp = oracle_profit(test["v"][comp], test["z"][comp])

        def add(regime, model, metrics, fit_s=0.0, pred_s=0.0):
            records.append({"seed": seed, "regime": regime, "model": model, "fit_s": fit_s, "predict_s": pred_s,
                            "profit_vs_oracle": metrics["profit"] / ceiling if ceiling else None,
                            "profit_vs_oracle_comp": metrics["profit_comp"] / ceiling_comp
                            if ceiling_comp and "profit_comp" in metrics else None, **metrics})

        def rule(bids):                      # rule-based policy: same metrics on all and on competed rows
            m = profit_metrics(test["v"], bids, test["z"])
            m.update({f"{k}_comp": x for k, x in profit_metrics(test["v"][comp], bids[comp], test["z"][comp]).items()})
            return m

        # rule-based references (no landscape model)
        alpha_profit = {a: profit_metrics(val["v"], a * val["v"], val["z"])["profit"] for a in ALPHAS}
        best_alpha = max(alpha_profit, key=alpha_profit.get)
        add("-", "truthful b=v", rule(test["v"]))
        add("-", f"shade b=a*v (a={best_alpha} on val)", rule(best_alpha * test["v"]))
        add("-", "oracle (knows z)", {"profit": ceiling, "profit_comp": ceiling_comp})
        u = random_bid_u(seed, len(test["z"]))
        add("-", "random bid b~U(R, v)", rule(args.reserve + u * np.maximum(test["v"] - args.reserve, 0)))
        uniform_F = np.clip((GRID - args.reserve) / (args.b_max - args.reserve), 0, 1)
        add("-", "random: uniform price U(R, B_MAX)",
            evaluate(np.tile(uniform_F, (len(uniq), 1)), inv, test["z"], v_u, eval_idx, args.reserve, args.b_max))
        add("-", "ceiling: test-empirical per combo",
            evaluate(empirical_matrix(test["combo"], test["z"], uniq), inv, test["z"], v_u, eval_idx, args.reserve, args.b_max))

        for regime in args.regimes:
            obs, cui_rows = observations(prep, train, tr_idx, regime, rng, args.reserve, args.b_max, seed, "train")
            val_obs, _ = observations(prep, val, va_idx, regime, rng, args.reserve, args.b_max, seed, "val")
            models = {
                "SM (KM global)": lambda: fit_baseline("SM", obs),
                "NM (wins-only global)": lambda: fit_baseline("NM", obs),
                "NTM (tree, wins-only)": lambda: SurvivalTree(args.depth, args.min_leaf, seed, estimator="normal").fit(obs),
                "STM (tree, KM)": lambda: SurvivalTree(args.depth, args.min_leaf, seed).fit(obs),
                "STM pruned (val)": lambda: SurvivalTree(args.depth, args.min_leaf, seed).fit(obs, validation=val_obs),
            }
            for name, fit in models.items():
                t0 = time.time()
                model = fit()
                fit_s, t1 = time.time() - t0, time.time()
                F_u = predict_matrix(prep, model, uniq)
                add(regime, name, evaluate(F_u, inv, test["z"], v_u, eval_idx, args.reserve, args.b_max),
                    fit_s, time.time() - t1)
                print(f"  {regime:9s} {name:24s} fit {fit_s:.1f}s profit/oracle {records[-1]['profit_vs_oracle']:.3f}", flush=True)
            t0 = time.time()
            cui = CuiForecaster(n_estimators=args.cui_estimators, min_impressions=args.cui_min_impressions).fit(cui_rows)
            fit_s = time.time() - t0
            for kind, name in (("cui", "Cui lognormal mixture"), ("cui_point", "Cui point-mean")):
                t1 = time.time()
                F_u = predict_matrix(prep, (kind, cui), uniq)
                add(regime, name, evaluate(F_u, inv, test["z"], v_u, eval_idx, args.reserve, args.b_max),
                    fit_s, time.time() - t1)
                print(f"  {regime:9s} {name:24s} fit {fit_s:.1f}s profit/oracle {records[-1]['profit_vs_oracle']:.3f}", flush=True)

    payload = {"args": {k: (list(v) if isinstance(v, tuple) else v) for k, v in vars(args).items()},
               "data": data_stats, "results": records}
    (out_dir / "results.json").write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
    (out_dir / "results.md").write_text(report(payload), encoding="utf-8")
    return payload


def _agg(rows, key, fmt):
    vals = [r[key] for r in rows if r.get(key) is not None]
    if not vals:
        return ""
    return fmt.format(np.mean(vals)) + (f" ± {fmt.format(np.std(vals))}" if len(vals) > 1 else "")


def report(payload):
    rows = payload["results"]
    groups = {}
    for r in rows:
        groups.setdefault((r["regime"], r["model"]), []).append(r)
    a = payload["args"]
    L = ["# Бенчмарк ставок на логах стенда (Wang 2016, Cui 2011)", "",
         f"Seeds {a['seeds']}, sample {a['sample']}, train/val/test дни {a['train_days']}/{a['val_days']}/{a['test_days']}, "
         f"резерв R={a['reserve']}, обучение до {a['train_cap']} строк. Среднее ± std по seed.", "",
         "## Данные (запросы, ушедшие менеджеру)", "",
         "| seed | фаза | строк | доля 204 (z=R) | доля с нашей ценностью v>0 | mean z | mean v (v>0) |",
         "|---:|---|---:|---:|---:|---:|---:|"]
    L += [f"| {d['seed']} | {d['phase']} | {d['rows']} | {d['share_204']:.3f} | {d['share_valued']:.3f} | "
          f"{d['mean_z']:.1f} | {d['mean_v_valued']:.1f} |" for d in payload["data"]]
    head = ["режим", "модель", "Brier", "log-loss", "ECE", "CRPS"] + [f"win@{t} (бид; coverage; fallback win/бид)" for t in TARGETS]
    L += ["", "## 1. Вероятность показа", "",
          "Brier/log-loss/ECE — прогноз P(win) при случайной ставке U(R, B_MAX) на тесте; CRPS — по всей сетке ставок. "
          "win@p и ставка считаются только по строкам, где F достигает p; coverage — их доля. Для недостижимых строк отдельно показаны win-rate и ставка GRID[-1]. Если строк нет, метрики равны ‘—’.", "",
          "| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    for (regime, model), g in groups.items():
        if "brier" not in g[0]:
            continue
        cells = [regime, model] + [_agg(g, k, "{:.4f}") for k in ("brier", "log_loss", "ece", "crps")]
        cells += [f"{_agg(g, f'win@{t}', '{:.3f}')} ({_agg(g, f'bid@{t}', '{:.0f}')}; {_agg(g, f'reachable@{t}', '{:.3f}')}; "
                  f"{_agg(g, f'fallback_win@{t}', '{:.3f}')}/{_agg(g, f'fallback_bid@{t}', '{:.0f}')})" for t in TARGETS]
        L.append("| " + " | ".join(cells) + " |")
    head = ["режим", "модель", "прибыль / oracle", "прибыль", "показы", "win-rate (v>0)", "расход", "ожид./факт прибыль"]
    L += ["", "## 2. Оптимальность цены", "",
          "First-price: ставка b* = argmax_{b≤v} (v−b)·F̂(b). Прибыль = Σ(v−b)·1[b>z] на тесте. "
          "oracle знает z и ставит z+1 — верхняя граница. «ожид./факт» — откалиброванность прогноза прибыли (1 = точно).", "",
          "| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    for (regime, model), g in groups.items():
        ratio = [r["expected_profit"] / r["profit"] for r in g if r.get("expected_profit") is not None and r["profit"]]
        cells = [regime, model, _agg(g, "profit_vs_oracle", "{:.3f}"), _agg(g, "profit", "{:.0f}"),
                 _agg(g, "wins", "{:.0f}"), _agg(g, "win_rate_valued", "{:.3f}"), _agg(g, "spend", "{:.0f}"),
                 f"{np.mean(ratio):.2f}" if ratio else ""]
        L.append("| " + " | ".join(cells) + " |")
    head = ["режим", "модель", "Brier", "log-loss", "ECE", "CRPS"] + [f"win@{t} (бид; coverage; fallback win/бид)" for t in TARGETS]
    L += ["", "## 1c. Вероятность показа — только запросы с конкуренцией (z > R)", "",
          "Прогноз модели условлен на z > R: P(z < b | z > R) = (F(b) − F(R+1)) / (1 − F(R+1)) — "
          "это операция над прогнозом, тестовые данные в ней не участвуют.", "",
          "| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    for (regime, model), g in groups.items():
        if "brier_comp" not in g[0]:
            continue
        cells = [regime, model] + [_agg(g, f"{k}_comp", "{:.4f}") for k in ("brier", "log_loss", "ece", "crps")]
        cells += [f"{_agg(g, f'win@{t}_comp', '{:.3f}')} ({_agg(g, f'bid@{t}_comp', '{:.0f}')}; "
                  f"{_agg(g, f'reachable@{t}_comp', '{:.3f}')}; {_agg(g, f'fallback_win@{t}_comp', '{:.3f}')}/"
                  f"{_agg(g, f'fallback_bid@{t}_comp', '{:.0f}')})" for t in TARGETS]
        L.append("| " + " | ".join(cells) + " |")
    head = ["режим", "модель", "прибыль / oracle", "прибыль", "показы", "win-rate (v>0)", "расход"]
    L += ["", "## 2c. Оптимальность цены — только запросы с конкуренцией (z > R)", "",
          "Ставки те же, что выше: модель не знает, какой запрос бесплатный. Прибыль и oracle — по тем же запросам.", "",
          "| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    for (regime, model), g in groups.items():
        if "profit_comp" not in g[0]:
            continue
        L.append("| " + " | ".join([regime, model, _agg(g, "profit_vs_oracle_comp", "{:.3f}"),
                                     _agg(g, "profit_comp", "{:.0f}"), _agg(g, "wins_comp", "{:.0f}"),
                                     _agg(g, "win_rate_valued_comp", "{:.3f}"), _agg(g, "spend_comp", "{:.0f}")]) + " |")
    L += ["", "## Ограничения", "",
          "- Replay: наш выигрыш не меняет состояние менеджера (частоты/объёмы) — стандартное допущение офлайн-оценки RTB.",
          "- v не учитывает частотные лимиты и объёмы наших кампаний — только таргетинг и cpm.",
          "- Цены менеджера — дискретная лестница cpm; логнормаль Cui для неё заведомо неточна.",
          "- censored: при выигрыше видим z (feedback «минимальная ставка для выигрыша»), при проигрыше только z ≥ b."]
    return "\n".join(L) + "\n"


def main(argv=None):
    rng_arg = lambda s: tuple(map(int, s.split(":")))
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--prepared", default=str(ROOT / "benchmarks/logs/prepared_20261012_retry"))
    p.add_argument("--manager-ads", default=str(STAND_DIR / "manager_target50_20261012.json"))
    p.add_argument("--our-ads", default=str(ROOT / "benchmarks/log_benchmark/ads_manual.json"))
    p.add_argument("--output-dir", default=str(Path(__file__).resolve().parents[3] / "docs/benchmark/bid_forecast/results/price"))
    p.add_argument("--seeds", type=lambda s: [int(x) for x in s.split(",")], default=[19, 43, 71])
    p.add_argument("--sample", type=float, default=0.002, help="доля пользователей стенда")
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
    print(f"saved {args.output_dir}/results.md")


if __name__ == "__main__":
    main()
