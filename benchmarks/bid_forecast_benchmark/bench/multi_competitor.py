"""Several independent competitors instead of one manager.

Competitor A is the stand's manager unchanged; the others are generated from it with a fixed seed: each gets its own
cpm multiplier per campaign, its own subset of campaigns and its own frequency limits (see make_competitor).
Every competitor is a full stand.Seller with its own volumes, frequency windows and min_interval.

The market price of a request is the best competing bid: z = max over competitors of their winner's cpm
(the reserve if nobody can show). Who serves: the competitor with the highest cpm (first-price exchange).
Online: when we win (b > z) no competitor serves, so none of them spends limits or volume.

Implementation: stand.simulate() is used unchanged. Its manager Seller is replaced by MultiSeller, which wraps one
real Seller per competitor and exposes the same serve() / peek interface. With one competitor (A alone) MultiSeller
is the stand's manager bit for bit — checked by tests/test_multi_competitor.py.
"""
from __future__ import annotations

import argparse
import copy
import json
import time
from pathlib import Path

import numpy as np

from . import online_benchmark as ob
from . import price_benchmark as pb
from ..cui.cui2011 import CuiForecaster
from ..wang.wang2016 import SurvivalTree, fit_baseline

stand = pb.stand
TUNE_GRID = [(5, 200), (8, 50), (10, 20), (12, 20)]


def make_competitor(ads, seed, cpm_range=(0.7, 1.4), keep=0.7, limit_range=(0.6, 1.6), vocabs=None,
                    independent=False):
    """A different but plausible competitor derived from the manager's campaigns (deterministic per seed).

    independent=False: same targeting and limit structure, scaled limits and cpm (strongly correlated with A).
    independent=True (needs vocabs = prep.vocabs): each campaign gets its own targeting slice — a random subset of
    values of one or two attributes — its own user-limit structure (which windows, thresholds, min_interval),
    its own ad-limit profile and its own flight window, so competitors run out on different users and hours."""
    rng = np.random.default_rng(seed)
    out = []
    for ad in ads:
        if rng.random() > keep:
            continue
        a = copy.deepcopy(ad)
        a["id"] = f"{ad['id']}_c{seed}"
        a["cpm"] = int(max(60, round(ad["cpm"] * rng.uniform(*cpm_range) / 5) * 5))
        if not independent:
            f = rng.uniform(*limit_range)
            a["user_frequency_limit"] = {g: max(1, int(round(v * f))) for g, v in ad.get("user_frequency_limit", {}).items()}
            if a.get("min_interval"):
                a["min_interval"] = int(round(a["min_interval"] / f))
        else:
            a["targets"] = _random_targets(rng, vocabs)
            windows = [g for g in ("h", "d", "w") if rng.random() < 0.6] or ["d"]
            day = int(rng.integers(3, 25))
            a["user_frequency_limit"] = {"h": max(1, day // int(rng.integers(3, 8))), "d": day,
                                         "w": day * int(rng.integers(3, 7))}
            a["user_frequency_limit"] = {g: a["user_frequency_limit"][g] for g in windows}
            a["min_interval"] = int(rng.choice([0, 10, 30, 60, 120, 300]))
            a["limits"] = str(rng.choice(["none", "loose", "normal", "tight"]))
            a.pop("ad_limits_rel", None)
            start = float(rng.choice([0.0, 0.0, 0.0, rng.uniform(0, 0.5)]))
            a["start_frac"], a["end_frac"] = start, float(min(1.0, start + rng.uniform(0.5, 1.0)))
            a["volume_weight"] = float(rng.uniform(0.3, 1.5))
        out.append(a)
    if not out:                                       # keep at least one campaign
        out = [dict(copy.deepcopy(ads[0]), id=f"{ads[0]['id']}_c{seed}")]
    return out


TARGET_ATTRS = ("Device", "Region", "Category", "Channel")


def _random_targets(rng, vocabs):
    """One or two attributes, each restricted to a random share (30-80 %) of its real values."""
    attrs = rng.choice(TARGET_ATTRS, size=int(rng.integers(1, 3)), replace=False)
    targets = {}
    for attr in attrs:
        values = [v for v in vocabs[attr] if v and not v.startswith("<")]
        k = max(1, int(round(len(values) * rng.uniform(0.3, 0.8))))
        targets[str(attr)] = sorted(rng.choice(values, size=k, replace=False).tolist())
    return targets


class MultiSeller:
    """Looks like one stand.Seller to simulate(); internally a first-price exchange of several Sellers."""

    def __init__(self, sellers):
        self.sellers = sellers
        self.requests = 0
        self.miss_nomatch = 0
        self.miss_filtered = 0
        self.volume = [int(v) for seller in sellers for v in seller.pack.volume]

    # stand.simulate only reads these from the manager seller
    @property
    def total_impressions(self):
        return sum(s.total_impressions for s in self.sellers)

    @property
    def impressions(self):
        return [x for s in self.sellers for x in s.impressions]

    def best(self, t, u, c, avail=None):
        """(competitor index, its campaign index, cpm) of the best competing bid, or (-1, -1, 0).
        avail (optional list) receives, per competitor, whether it had an eligible campaign."""
        best = (-1, -1, 0.0)
        for k, s in enumerate(self.sellers):
            w = ob.peek(s, t, u, c)
            if avail is not None:
                avail.append(w >= 0)
            if w >= 0 and (best[0] < 0 or s.cpm[w] > best[2]):
                best = (k, w, float(s.cpm[w]))
        return best

    def serve(self, t, u, c):
        self.requests += 1
        k, w, _ = self.best(t, u, c)
        if k < 0:
            self.miss_filtered += 1
            return -1
        got = self.sellers[k].serve(t, u, c)
        assert got == w, "peek and serve disagree"
        return got


def build_market(prep, pool_mask, competitor_ads, q, sample, days, volume_factor=1.3, planning=None):
    """One Seller per competitor, volumes split by pool match rates exactly as stand.simulate does for the manager."""
    import dataclasses
    n_days = days[1] - days[0]
    _, pool_n = stand.count_requests(prep, days, sample, pool_mask)
    if planning is not None:
        pool_n = planning.pool_daily_rate * n_days
    pool_prep = dataclasses.replace(prep, combo_counts=prep.combo_counts * pool_mask)
    sellers = []
    for ads in competitor_ads:
        if planning is None:
            pack = stand.build_pack(pool_prep, ads, max(1, round(q * pool_n)), n_days, volume_factor, True)
        else:
            pack = stand.build_pack(pool_prep, ads, max(1, round(q * pool_n)), n_days, volume_factor, True,
                                    planning=planning, planning_pool_only=True)
        sellers.append(stand.Seller(pack, stand.build_match_lists(prep, pack.targets)))
    return MultiSeller(sellers)


def run_market(prep, days, sample, competitor_ads, our_ads, pool_mask, q, seed, reserve, bid_of=None,
               our_limits=False, planning=None):
    """Run the stand with a multi-competitor market. bid_of=None: offline (we never bid, z recorded).
    Otherwise online: bid_of(combo, v, z, i) -> b for request number i; on b > z we take the impression and no
    competitor serves. bid_of is not called when v <= 0 (we have nothing to sell); i keeps policies row-aligned anyway.

    our_limits=False: v = max cpm of our campaigns matching the request by targeting (limits ignored), and an
      impression we win is not charged to any of our campaigns.
    our_limits=True: v = cpm of the campaign our own Seller would pick right now (frequency windows, min_interval,
      volume, flight — the same Seller that serves our traffic outside the market); a win is served by that Seller,
      so it spends that campaign's limits. v = 0 when every matching campaign is exhausted -> we do not bid.

    Returns per-sent-request arrays combo, z, v, b, won, plus serving stats."""
    rows, made = [], {}
    market = build_market(prep, pool_mask, competitor_ads, q, sample, days, planning=planning)
    built = []
    real_seller = stand.Seller

    def factory(*args):
        """simulate() builds the manager Seller first (replaced by the market), then ours (a real Seller)."""
        obj = market if not built else real_seller(*args)
        built.append(obj)
        return obj

    avail, market_wins = [], []

    def market_serve(t, u, c, _serve=MultiSeller.serve.__get__(market)):
        k, w, cpm = market.best(t, u, c, avail)
        z = cpm if k >= 0 else reserve
        ours = built[1]
        if our_limits:
            a = ob.peek(ours, t, u, c)
            v = float(ours.cpm[a]) if a >= 0 else 0.0
        else:
            v = made.get(c)
            if v is None:
                v = made[c] = float(max((ours.cpm[x] for x in ours.match[c]), default=0.0))
        b = 0.0 if bid_of is None or v <= 0 else float(bid_of(c, v, z, len(rows)))
        won = v > 0 and b > z
        rows.append((c, z, v, b, won))
        if won:
            market.requests += 1
            if our_limits:
                got = ours.serve(t, u, c)
                assert got == a, "our peek and serve disagree"
                market_wins.append(1)
            return -1
        return _serve(t, u, c)

    market.serve = market_serve
    stand.Seller = factory
    try:
        stand.simulate(prep, days, sample, competitor_ads[0], our_ads, pool_mask, q,
                       lambda: pb.RandomShare(pool_mask, prep.combos, q, seed), 150.0, seed=seed,
                       planning=planning)
    finally:
        stand.Seller = real_seller
    c, z, v, b, won = (np.array(x) for x in zip(*rows))
    shown = [int(s.total_impressions) for s in market.sellers]
    ours = built[1]
    won_v = float(sum(r[2] for r in rows if r[4])) if our_limits else 0.0
    return dict(combo=c.astype(np.int64), z=z.astype(float), v=v.astype(float), b=b.astype(float),
                won=won.astype(bool), shown=shown, avail=np.array(avail, bool).reshape(len(rows), len(market.sellers)),
                campaign_plans={"competitors": [list(s.pack.volume) for s in market.sellers],
                                "ours": list(built[1].pack.volume)},
                # revenue of our campaigns on traffic that never went to the market (their cpm per impression);
                # with our_limits the market wins are served by the same Seller, so subtract their v
                our_outside_revenue=float(ours.revenue) - won_v, our_shown=int(ours.total_impressions))


def availability_report(avail):
    """Share of requests each competitor can serve, pairwise correlation of that, and share nobody can."""
    share = avail.mean(0)
    k = avail.shape[1]
    corr = {f"{i}-{j}": float(np.corrcoef(avail[:, i], avail[:, j])[0, 1]) for i in range(k) for j in range(i + 1, k)}
    free = float(np.mean(~avail.any(1)))
    independent_free = float(np.prod(1 - share))      # what "free" would be if competitors were independent
    return {"share_available": share.round(3).tolist(), "corr": {p: round(x, 3) for p, x in corr.items()},
            "free": round(free, 3), "free_if_independent": round(independent_free, 3)}


# ───────────────────────────── benchmark ─────────────────────────────

def run(args):
    prep = stand.load_prepared(args.prepared)
    pool_mask = stand.pool_mask_of(prep, stand.POOL_DEVICES)
    base_ads = stand.load_ads_file(args.manager_ads)
    our_ads = stand.load_ads_file(args.our_ads)
    competitors = [base_ads] + [make_competitor(base_ads, 1000 + k, vocabs=prep.vocabs, independent=True)
                                for k in range(1, args.competitors)]
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    records, data_stats, chosen = [], [], []

    for seed in args.seeds:
        rng = np.random.default_rng(seed)
        phases = {}
        for phase, days in (("train", args.train_days), ("val", args.val_days), ("test", args.test_days)):
            t0 = time.time()
            d = run_market(prep, days, args.sample, competitors, our_ads, pool_mask, args.q, seed, args.reserve)
            phases[phase] = d
            data_stats.append({"seed": seed, "phase": phase, "days": list(days), "rows": len(d["z"]),
                               "share_free": float(np.mean(d["z"] == args.reserve)), "mean_z": float(d["z"].mean()),
                               "distinct_z": int(len(np.unique(d["z"]))), "shown_by_competitor": d["shown"],
                               "availability": availability_report(d["avail"]), "seconds": time.time() - t0})
            print(f"seed {seed} {phase}: {len(d['z'])} rows, free {data_stats[-1]['share_free']:.3f}, "
                  f"mean z {d['z'].mean():.1f}, shown {d['shown']}", flush=True)
        train, val, test = phases["train"], phases["val"], phases["test"]
        uniq, inv = np.unique(test["combo"], return_inverse=True)
        v_u = np.zeros(len(uniq)); v_u[inv] = test["v"]
        index = {int(c): i for i, c in enumerate(uniq)}
        eval_idx = rng.integers(np.searchsorted(pb.GRID, args.reserve), np.searchsorted(pb.GRID, args.b_max) + 1,
                                len(test["z"]))
        comp = test["z"] > args.reserve
        z, v = test["z"], test["v"]

        def online(bid_of, our_limits, prefix):
            out = run_market(prep, args.test_days, args.sample, competitors, our_ads, pool_mask, args.q, seed,
                             args.reserve, bid_of, our_limits=our_limits)
            assert np.array_equal(out["combo"], test["combo"]), "request stream differs between policies"
            won = out["won"]
            pr = (out["v"] - out["b"]) * won
            return {f"{prefix}_profit": float(pr.sum()), f"{prefix}_profit_comp": float(pr[comp].sum()),
                    f"{prefix}_wins": int(won.sum()), f"{prefix}_wins_comp": int(won[comp].sum()),
                    f"{prefix}_mean_z": float(out["z"].mean()),
                    f"{prefix}_share_free": float(np.mean(out["z"] == args.reserve)),
                    f"{prefix}_share_v0": float(np.mean(out["v"] <= 0)),
                    f"{prefix}_outside_revenue": out["our_outside_revenue"], f"{prefix}_shown": out["shown"],
                    f"{prefix}_total": float(pr.sum()) + out["our_outside_revenue"]}

        def add(regime, name, offline, bid_of):
            rec = {"seed": seed, "regime": regime, "model": name, **offline}
            if bid_of is not None and args.online:
                rec.update(online(bid_of, False, "online"))
                rec.update(online(bid_of, True, "ours"))
            records.append(rec)
            print(f"  {regime:9s} {name:28s} offline {rec['profit']:>10.0f}"
                  + (f"  online {rec['online_profit']:>10.0f}  with our limits {rec['ours_profit']:>10.0f}"
                     if "online_profit" in rec else ""), flush=True)

        def rule_metrics(bids):
            m = pb.profit_metrics(v, bids, z)
            m.update({f"{k}_comp": x for k, x in pb.profit_metrics(v[comp], bids[comp], z[comp]).items()})
            return m

        def model_entry(regime, name, F_u):
            add(regime, name, pb.evaluate(F_u, inv, z, v_u, eval_idx, args.reserve, args.b_max),
                ob.policy_from_F(F_u, index))

        # baseline for the "total": never bid on the market (outside revenue only), measured in both online modes
        add("-", "no market bids", {"profit": 0.0, "profit_comp": 0.0}, lambda c, vv, zz, i: 0.0)
        add("-", "oracle (knows z)", {"profit": pb.oracle_profit(v, z), "profit_comp": pb.oracle_profit(v[comp], z[comp])},
            lambda c, vv, zz, i: zz + 1 if vv > zz + 1 else 0.0)
        alpha_profit = {a: pb.profit_metrics(val["v"], a * val["v"], val["z"])["profit"] for a in pb.ALPHAS}
        best_alpha = max(alpha_profit, key=alpha_profit.get)
        add("-", f"shade b=a*v (a={best_alpha})", rule_metrics(best_alpha * v), lambda c, vv, zz, i: best_alpha * vv)
        # one uniform per test row, indexed by request number: same draws offline and in both online modes
        u = pb.random_bid_u(seed, len(z))
        rb_off = args.reserve + u * np.maximum(v - args.reserve, 0)
        add("-", "random bid b~U(R, v)", rule_metrics(rb_off),
            lambda c, vv, zz, i: args.reserve + u[i] * max(vv - args.reserve, 0))
        uniform_F = np.clip((pb.GRID - args.reserve) / (args.b_max - args.reserve), 0, 1)
        model_entry("-", "random: uniform price", np.tile(uniform_F, (len(uniq), 1)))
        add("-", "ceiling: test-empirical per combo",
            pb.evaluate(pb.empirical_matrix(test["combo"], z, uniq), inv, z, v_u, eval_idx, args.reserve, args.b_max), None)

        tr_idx = rng.choice(len(train["z"]), min(args.train_cap, len(train["z"])), replace=False)
        va_idx = rng.choice(len(val["z"]), min(args.val_cap, len(val["z"])), replace=False)
        vuniq, vinv = np.unique(val["combo"], return_inverse=True)
        vv_u = np.zeros(len(vuniq)); vv_u[vinv] = val["v"]
        veval = np.random.default_rng(seed).integers(np.searchsorted(pb.GRID, args.reserve),
                                                     np.searchsorted(pb.GRID, args.b_max) + 1, len(val["z"]))
        for regime in args.regimes:
            obs, cui_rows = pb.observations(prep, train, tr_idx, regime, rng, args.reserve, args.b_max, seed, "train")
            val_obs, _ = pb.observations(prep, val, va_idx, regime, rng, args.reserve, args.b_max, seed, "val")
            model_entry(regime, "SM (KM global)", pb.predict_matrix(prep, fit_baseline("SM", obs), uniq))
            model_entry(regime, "NM (wins-only global)", pb.predict_matrix(prep, fit_baseline("NM", obs), uniq))
            model_entry(regime, "NTM (tree, wins-only)", pb.predict_matrix(
                prep, SurvivalTree(args.depth, args.min_leaf, seed, estimator="normal").fit(obs), uniq))
            model_entry(regime, "STM (tree, KM)", pb.predict_matrix(
                prep, SurvivalTree(args.depth, args.min_leaf, seed).fit(obs), uniq))
            # STM tuned: depth/leaf chosen by profit on the validation days (test never seen)
            best = None
            for depth, leaf in TUNE_GRID:
                m = SurvivalTree(depth, leaf, seed).fit(obs)
                p = pb.evaluate(pb.predict_matrix(prep, m, vuniq), vinv, val["z"], vv_u, veval,
                                args.reserve, args.b_max)["profit"]
                if best is None or p > best[0]:
                    best = (p, depth, leaf, m)
            chosen.append({"seed": seed, "regime": regime, "depth": best[1], "min_leaf": best[2]})
            model_entry(regime, f"STM tuned on val", pb.predict_matrix(prep, best[3], uniq))
            cui = CuiForecaster(n_estimators=args.cui_estimators, min_impressions=args.cui_min_impressions).fit(cui_rows)
            model_entry(regime, "Cui lognormal mixture", pb.predict_matrix(prep, ("cui", cui), uniq))

    payload = {"args": {k: (list(x) if isinstance(x, tuple) else x) for k, x in vars(args).items()},
               "competitors": [{"name": "A (stand manager)" if i == 0 else f"generated seed {1000 + i}",
                                "campaigns": len(c), "cpm": sorted(a["cpm"] for a in c)} for i, c in enumerate(competitors)],
               "tuned": chosen, "data": data_stats, "results": records}
    (out_dir / "results_multi.json").write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
    return payload


def main(argv=None):
    rng_arg = lambda s: tuple(map(int, s.split(":")))
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--prepared", default=str(pb.ROOT / "benchmarks/logs/prepared_20261012_retry"))
    p.add_argument("--manager-ads", default=str(pb.STAND_DIR / "manager_target50_20261012.json"))
    p.add_argument("--our-ads", default=str(pb.ROOT / "benchmarks/log_benchmark/ads_manual.json"))
    p.add_argument("--output-dir", default=str(Path(__file__).resolve().parents[3] / "docs/benchmark/bid_forecast/results/price"))
    p.add_argument("--competitors", type=int, default=3)
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
    p.add_argument("--no-online", dest="online", action="store_false")
    args = p.parse_args(argv)
    run(args)
    print(f"saved {args.output_dir}/results_multi.json")


if __name__ == "__main__":
    main()
