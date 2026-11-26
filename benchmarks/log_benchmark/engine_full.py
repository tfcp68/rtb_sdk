"""
Engine of the "full" auction on logs.

Replicates the simulation chain from the SDK (rtb_sdk/auction/simulation) in a fast
form, without TypedDict objects in the hot loop:

    active (start/end) → ad_frequency_limit (sliding windows t/h/d/w/m)
    → user_frequency_limit (sliding windows per user×ad pair)
    → min_interval (per user×ad pair) → precise match → winner selection

PRECISE only: the fuzzy branch is not used (per the task statement).

The key speedup idea. The sliding window "n-th from the end impression is inside the window"
changes its value ONLY at the moment of a new impression, so upon an impression
`until` is recomputed — the point in time until which the ad (or the
user×ad pair) is blocked. Checking a candidate in the hot loop is a single comparison
`t < until`. This is exactly equivalent to is_over_limit() from the SDK:
blocked if timestamps[-limit] > t - window  ⇔  t < timestamps[-limit] + window.

An SDK quirk that is reproduced: min_interval is read from
ad_frequency_limit (get_ad_min_interval), but is applied to the user×ad pair.

Velocity/heuristics/hybrid use exactly the same formulas as the SDK:
month_limit = get_real_month_volume(ad) (min of the frequency and date limits),
current = number of impressions over the sliding 30 days.
"""
from __future__ import annotations

import os
import random
import sys
from array import array
from dataclasses import dataclass, field

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (os.path.join(_HERE, ".."), os.path.join(_HERE, "..", "..", "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

INF = 1 << 60
DAY = 86_400
GRAN_SECONDS = {"t": 600, "h": 3_600, "d": DAY, "w": 7 * DAY, "m": 30 * DAY}
GRANS = ("t", "h", "d", "w", "m")

CLASSIC_STRATEGIES = [
    "best_one", "random_one",
    "best_price", "random_price",
    "best_velocity", "random_velocity",
    "best_heuristics", "random_heuristics",
    "best_hybrid_0.2", "best_hybrid_0.4",
    "random_hybrid_0.3", "random_hybrid_0.5", "random_hybrid_0.7",
]
BALANCER = "balancer"
BALANCER_TEMPORAL = "balancer_temporal"
ADWORDS = ["a2_single_valued", "a3_small"]
ALL_ALGORITHMS = CLASSIC_STRATEGIES + [BALANCER, BALANCER_TEMPORAL] + ADWORDS


# ─── Data preparation ─────────────────────────────────────────────────────

@dataclass
class AdPack:
    """Scenario ads as parallel lists (index = auction order)."""
    ids: list[str]
    names: list[str]
    cpm: list[float]
    priority: list[float]
    volume: list[int]
    budget: list[float]
    targets: list[dict[str, list[str]]]
    match_rate: list[float]
    ad_lims: list[tuple]            # ((limit, window_s), ...)
    user_lims: list[tuple]
    min_interval: list[int]
    start_s: list[int]
    end_s: list[int]
    month_limit: list[float]        # get_real_month_volume(ad)
    ad_lims_raw: list[dict] = field(default_factory=list)
    user_lims_raw: list[dict] = field(default_factory=list)

    @property
    def n(self) -> int:
        return len(self.ids)


def build_match_lists(prep, targets: list[dict[str, list[str]]]) -> list[tuple]:
    """For each tag combination — a tuple of indices of matching ads (precise match).

    Precise: for each vocab constraint of the ad the request tag belongs to its set.
    A feature absent from the request (code 0, "<none>") matches only if the ad
    does not explicitly restrict this vocab.
    """
    order = prep.vocab_order
    U = len(prep.combos)
    A = len(targets)
    ok = np.ones((A, U), dtype=bool)
    for ai, tg in enumerate(targets):
        for vi, vname in enumerate(order):
            if vname not in tg:
                continue
            labels = prep.vocabs[vname]
            lut = np.zeros(len(labels), dtype=bool)
            idx = {l: i for i, l in enumerate(labels)}
            for tag in tg[vname]:
                if tag not in idx:
                    raise ValueError(f"Tag {tag!r} not found in the dictionary {vname!r}")
                lut[idx[tag]] = True
            lut[0] = False  # "no feature" never matches explicit targeting
            ok[ai] &= lut[prep.combos[:, vi]]
    okT = ok.T
    return [tuple(np.flatnonzero(row).tolist()) for row in okT]


# ─── Result ─────────────────────────────────────────────────────────────

@dataclass
class RunResult:
    algo: str
    requests: int = 0
    impressions: list[int] = field(default_factory=list)
    revenue: float = 0.0
    miss_nomatch: int = 0        # not a single ad matching by targeting
    miss_filtered: int = 0       # there were matching ones, but all were cut by filters/volume
    miss_algo: int = 0           # the algorithm (adwords) returned None with a non-empty pool
    balancer_fallback: int = 0   # balancer: all pool weights are zero → best_price chosen
    rej_volume: int = 0          # candidate rejections: volume exhausted
    rej_ad_limit: int = 0        # … ad_frequency_limit
    rej_user_limit: int = 0      # … user_frequency_limit
    rej_min_interval: int = 0    # … min_interval
    rej_inactive: int = 0        # … outside start/end
    limit_cut_requests: int = 0  # requests where the limits cut ≥1 candidate
    miss_by_limits: int = 0      # misses where the pool emptied with limits/min_interval involved
    day_impressions: list[int] = field(default_factory=list)
    day_requests: list[int] = field(default_factory=list)
    day_revenue: list[float] = field(default_factory=list)
    seconds: float = 0.0

    @property
    def total_impressions(self) -> int:
        return sum(self.impressions)

    @property
    def fill_rate(self) -> float:
        return self.total_impressions / self.requests if self.requests else 0.0


# ─── Main run ───────────────────────────────────────────────────────

def run_algorithm(
    algo: str,
    pack: AdPack,
    match: list[tuple],
    stream,
    prep,
    seed: int = 0,
    n_requests_hint: int = 0,
    trace: list | None = None,
    period_days: int = 1,
) -> RunResult:
    """Runs one algorithm over the `stream` (an iter_days iterator)."""
    import time
    t_start = time.time()
    rnd = random.Random(seed)
    A = pack.n
    cpm, pri, mlim, vol = pack.cpm, pack.priority, pack.month_limit, pack.volume
    end = pack.end_s
    until = list(pack.start_s)
    cnt = [0] * A
    adts = [array("i") for _ in range(A)]
    ad_lims = pack.ad_lims
    u_lims = pack.user_lims
    mint = pack.min_interval
    u_flag = [bool(u_lims[a]) or mint[a] > 0 for a in range(A)]
    u_keep = [max([l for l, _ in u_lims[a]] + [1]) for a in range(A)]
    K = 1 << max(1, (A - 1).bit_length())
    udict: dict[int, list] = {}

    res = RunResult(algo=algo, impressions=[0] * A)

    # ── winner selection ──
    is_balancer = algo in (BALANCER, BALANCER_TEMPORAL)
    is_adwords = algo in ADWORDS
    pick = None
    hyb = None
    if not (is_balancer or is_adwords):
        name = algo
        if algo.startswith("best_hybrid_"):
            name, hyb = "best_hybrid", float(algo.split("_")[-1])
        elif algo.startswith("random_hybrid_"):
            name, hyb = "random_hybrid", float(algo.split("_")[-1])
        pick = _make_picker(name, hyb, cpm, pri, mlim, cnt, rnd)

    wcache: dict = {}
    weights_fns: list = []
    if algo == BALANCER:
        weights_fns = [_make_balancer_weights(pack, prep, n_requests_hint)]
    elif algo == BALANCER_TEMPORAL:
        weights_fns = _make_temporal_weights(pack, prep, n_requests_hint, period_days)
    n_wf = len(weights_fns)

    adw_state = adw_call = adw_cache = adw_ads = None
    if is_adwords:
        from rtb_sdk.auction.adwords.adwords import initialize_adwords, auction_adwords
        from rtb_sdk.helpers.auction import create_ads_dict
        from auction_benchmark.engine import _build_typed_ads
        ad_data = {pack.ids[a]: {"targets": pack.targets[a], "cpm": cpm[a], "priority": pri[a],
                                 "volume": vol[a], "budget": pack.budget[a]} for a in range(A)}
        adw_ads, full = _build_typed_ads(ad_data)
        random.seed(seed)
        adw_state = initialize_adwords(full, algo)
        adw_call = auction_adwords
        adw_cache = {}
        id_to_idx = {pack.ids[a]: a for a in range(A)}
        mk_dict = create_ads_dict

    for day, ts, user, combo in stream:
        d_imp0, d_rev0, d_req0 = sum(res.impressions), res.revenue, res.requests
        n = len(ts)
        res.requests += n
        for s in range(0, n, 1_000_000):
            ts_l = ts[s:s + 1_000_000].tolist()
            us_l = user[s:s + 1_000_000].tolist()
            co_l = combo[s:s + 1_000_000].tolist()
            for t, u, c in zip(ts_l, us_l, co_l):
                cand = match[c]
                if not cand:
                    res.miss_nomatch += 1
                    continue
                ok = []
                cut = False
                for a in cand:
                    ua = until[a]
                    if t < ua:
                        if ua >= INF:
                            res.rej_volume += 1
                        elif t < pack.start_s[a]:
                            res.rej_inactive += 1
                        else:
                            res.rej_ad_limit += 1
                            cut = True
                        continue
                    if t >= end[a]:
                        res.rej_inactive += 1
                        continue
                    if u_flag[a]:
                        st = udict.get(u * K + a)
                        if st is not None:
                            if t < st[0]:
                                res.rej_user_limit += 1
                                cut = True
                                continue
                            if t < st[1]:
                                res.rej_min_interval += 1
                                cut = True
                                continue
                    ok.append(a)
                if cut:
                    res.limit_cut_requests += 1
                if not ok:
                    res.miss_filtered += 1
                    if cut:
                        res.miss_by_limits += 1
                    continue

                if len(ok) == 1 and not is_adwords:
                    w = ok[0]
                elif pick is not None:
                    w = pick(ok)
                elif is_balancer:
                    di = min(t // DAY, n_wf - 1) if n_wf > 1 else 0
                    wf = weights_fns[di]
                    wd = []
                    tot = 0.0
                    for a in ok:
                        x = _combo_weight(wf, wcache, (di << 40) | (c << 12) | a, c, a)
                        wd.append(x)
                        tot += x
                    if tot <= 0:
                        # the plan allocated no company from the pool (price-dominated ones) —
                        # instead of refusing we take the best by price
                        res.balancer_fallback += 1
                        w = max(ok, key=cpm.__getitem__)
                    else:
                        w = rnd.choices(ok, weights=wd, k=1)[0]
                else:  # adwords
                    key = tuple(ok)
                    ads_dict = adw_cache.get(key)
                    if ads_dict is None:
                        ads_dict = mk_dict({pack.ids[a]: adw_ads[pack.ids[a]] for a in ok})
                        adw_cache[key] = ads_dict
                    r = adw_call(ads_dict, adw_state)
                    adw_state = r["state"]
                    mid = r["matched_ad"]
                    if mid is None:
                        res.miss_algo += 1
                        continue
                    w = id_to_idx[mid]

                # ── recording the impression ──
                if trace is not None:
                    trace.append((t, u, w))
                res.impressions[w] += 1
                res.revenue += cpm[w]
                cnt[w] += 1
                lst = adts[w]
                lst.append(t)
                nb = pack.start_s[w]
                if cnt[w] >= vol[w]:
                    nb = INF
                else:
                    nl = len(lst)
                    for lim, win in ad_lims[w]:
                        if nl >= lim:
                            x = lst[nl - lim] + win
                            if x > nb:
                                nb = x
                until[w] = nb
                if u_flag[w]:
                    k = u * K + w
                    st = udict.get(k)
                    if st is None:
                        st = [0, 0]
                        udict[k] = st
                    st.append(t)
                    over = len(st) - 2 - u_keep[w]
                    if over > 0:
                        del st[2:2 + over]
                    nl = len(st) - 2
                    ub = 0
                    for lim, win in u_lims[w]:
                        if nl >= lim:
                            x = st[2 + nl - lim] + win
                            if x > ub:
                                ub = x
                    st[0] = ub
                    st[1] = t + mint[w] if mint[w] > 0 else 0
        res.day_impressions.append(sum(res.impressions) - d_imp0)
        res.day_revenue.append(res.revenue - d_rev0)
        res.day_requests.append(res.requests - d_req0)

    res.seconds = time.time() - t_start
    return res


# ─── strategies ─────────────────────────────────────────────────────────────

def _make_picker(name, hyb, cpm, pri, mlim, cnt, rnd):
    price = cpm.__getitem__

    def vel(a):
        m = mlim[a]
        return (m - cnt[a]) / m

    if name == "best_one":
        return lambda c: c[0]
    if name == "random_one":
        return rnd.choice
    if name == "best_price":
        return lambda c: max(c, key=price)
    if name == "random_price":
        def f(c):
            mx = max(cpm[a] for a in c)
            return rnd.choices(c, weights=[cpm[a] / mx + 1e-9 for a in c], k=1)[0]
        return f
    if name == "best_velocity":
        return lambda c: max(c, key=vel)
    if name == "random_velocity":
        return lambda c: rnd.choices(c, weights=[vel(a) + 1e-9 for a in c], k=1)[0]
    if name == "best_hybrid":
        def f(c):
            for a in c:
                if 1 - vel(a) < hyb:
                    return max(c, key=vel)
            return max(c, key=price)
        return f
    if name == "random_hybrid":
        def f(c):
            if rnd.random() < hyb:
                return max(c, key=price)
            return max(c, key=vel)
        return f
    if name in ("best_heuristics", "random_heuristics"):
        def scores(c):
            mp = max(cpm[a] for a in c)
            mr = max(pri[a] for a in c)
            return [(cpm[a] / mp) * (pri[a] / mr) * vel(a) for a in c]
        if name == "best_heuristics":
            def f(c):
                s = scores(c)
                return c[s.index(max(s))]
            return f
        return lambda c: rnd.choices(c, weights=[x + 1e-9 for x in scores(c)], k=1)[0]
    raise ValueError(f"Unknown strategy: {name}")


# ─── balancer ─────────────────────────────────────────────────────────

def _tag_probs(prep):
    """Empirical tag probabilities over ALL log requests (combo_counts)."""
    probs: dict[str, dict[str, float]] = {}
    vocabs: dict[str, list[str]] = {}
    for vi, vname in enumerate(prep.vocab_order):
        labels = prep.vocabs[vname]
        c = np.bincount(prep.combos[:, vi], weights=prep.combo_counts, minlength=len(labels))
        tot = c.sum()
        probs[vname] = {labels[i]: float(c[i] / tot) for i in range(len(labels)) if c[i] > 0}
        vocabs[vname] = [labels[i] for i in range(len(labels)) if c[i] > 0]
    return probs, vocabs


def _weights_fn(pack: AdPack, prep, typed, report, params):
    """convert_report_to_auction_data → weight function (combo, ad) = dist × P(req) / P(ad)."""
    from rtb_sdk.balancer import convert_report_to_auction_data
    from rtb_sdk.constants.tag_constants import TAG_EMPTY, TAG_OTHER

    bd = convert_report_to_auction_data(typed, report, params)
    narrow = list(bd["vocabs"])
    tag_probs = bd["tag_probabilities"]
    dist = bd["ads_distribution"]
    ad_probs = bd["ads_probabilities"]
    vidx = {v: i for i, v in enumerate(prep.vocab_order)}

    def fn(c: int, a: int) -> float:
        row = prep.combos[c]
        rp = 1.0
        for v in narrow:
            vi = vidx.get(v)
            tag = prep.vocabs[v][row[vi]] if vi is not None else TAG_EMPTY
            vp = tag_probs.get(v, {})
            rp *= vp.get(tag, vp.get(TAG_OTHER, 0.0))
        ap = ad_probs.get(pack.ids[a], 1.0)
        return dist.get(pack.ids[a], 0) * rp / ap if ap > 0 else 0.0

    fn.planned = sum(report.values())  # type: ignore[attr-defined]
    return fn


def _make_balancer_weights(pack: AdPack, prep, n_requests: int):
    """Static balancer: one plan for the whole period (level-2 balance_traffic).

    The start/end windows and frequency limits cannot be passed here: ad_to_inner hardcodes
    date_factor=1.0, and treats the 'd' limit as a cap for the whole period. They are accounted for
    only by the temporal version.
    """
    from rtb_sdk.balancer import balance_traffic
    from rtb_sdk.helpers.balancer.optimize_params_helpers import create_balancing_params
    from auction_benchmark.engine import _build_typed_ads

    probs, vocabs = _tag_probs(prep)
    ad_data = {pack.ids[a]: {"targets": pack.targets[a], "cpm": pack.cpm[a], "priority": pack.priority[a],
                             "volume": pack.volume[a], "budget": pack.budget[a]} for a in range(pack.n)}
    typed, _ = _build_typed_ads(ad_data)
    params = create_balancing_params(
        total_traffic_volume=max(1, n_requests),
        tag_probabilities_outer=probs,
        vocabs_outer=vocabs,
        objective="maximize_money",
    )
    report = balance_traffic(typed, params)
    return _weights_fn(pack, prep, typed, report, params)


def _make_temporal_weights(pack: AdPack, prep, n_requests: int, days: int) -> list:
    """Temporal balancer: a plan for each day of the period (seasonal_balance_traffic).

    * seasonality — the hour_of_day hourly profile from all logs;
    * the companies' start/end and frequency limits (ad/user) are passed into Ad;
    * user_activity_ratio — saturation by the histogram of requests per user (day 0);
    * volume is spread over the remaining active days, the remainder is reduced by the plan.
    """
    import math
    from datetime import datetime, timedelta, timezone
    from rtb_sdk.balancer.seasonal.balance import seasonal_balance_traffic
    from rtb_sdk.balancer.seasonal.corrections import compute_hour_limit
    from rtb_sdk.helpers.balancer.seasonal_helpers import create_seasonal_balancing_params
    from rtb_sdk.helpers.balancer.optimize_params_helpers import create_balancing_params
    from rtb_sdk.helpers.auction import create_ad, create_frequency_limits, create_target_vector

    gran_key = {"t": "ten_minutes", "h": "hour", "d": "day", "w": "week", "m": "month"}
    probs, vocabs = _tag_probs(prep)

    # hourly profile and user activity — from the full logs
    hours = np.zeros(24)
    for d in range(prep.n_days):
        ts, user, _ = prep.day_arrays(d)
        hours += np.bincount((np.asarray(ts) % DAY) // 3600, minlength=24)
        if d == 0:
            _, ucnt = np.unique(np.asarray(user), return_counts=True)
    weights = hours / hours.sum()

    base = datetime(2026, 10, 1, tzinfo=timezone.utc)
    period_total = days * DAY
    ends = [min(pack.end_s[a], period_total) for a in range(pack.n)]

    def make_ad(a: int, vol: int):
        lim = {gran_key[g]: v for g, v in pack.ad_lims_raw[a].items()}
        ulim = {gran_key[g]: v for g, v in pack.user_lims_raw[a].items()}
        return create_ad(
            id=pack.ids[a], targets=create_target_vector(pack.targets[a]),
            cpm=pack.cpm[a], priority=pack.priority[a], volume=vol, budget=vol * pack.cpm[a],
            start_date=base + timedelta(seconds=pack.start_s[a]),
            end_date=base + timedelta(seconds=ends[a]),
            ad_frequency_limit=create_frequency_limits(**lim, min_interval=pack.min_interval[a]),
            user_frequency_limit=create_frequency_limits(**ulim),
        )

    # saturation: the share of impressions fitting into the user limit per day
    ratio: dict[str, float] = {}
    for a in range(pack.n):
        ulim = pack.user_lims_raw[a]
        if not ulim:
            continue
        freq = make_ad(a, 1)["user_frequency_limit"]
        lim_day = compute_hour_limit(freq) * 24
        if lim_day < float("inf"):
            ratio[pack.ids[a]] = float(np.minimum(ucnt, lim_day).sum() / ucnt.sum())

    ctx = {"mode": "hour_of_day",
           "context": {h: {"weight": float(weights[h]), "user_activity_ratio": ratio,
                           "tags_probability": None} for h in range(24)}}

    remaining = {pack.ids[a]: pack.volume[a] for a in range(pack.n)}
    day_total = max(1, n_requests // days)
    fns = []
    for d in range(days):
        ds, de = d * DAY, (d + 1) * DAY
        ads, act = {}, []
        for a in range(pack.n):
            s, e = pack.start_s[a], ends[a]
            today = max(0, min(e, de) - max(s, ds))
            left = max(0, e - max(s, ds))
            rem = remaining[pack.ids[a]]
            if today <= 0 or rem <= 0:
                continue
            vol = max(1, math.ceil(rem * today / left))
            ads[pack.ids[a]] = make_ad(a, vol)
        if not ads:
            fns.append(lambda c, a: 0.0)
            continue
        sp = create_seasonal_balancing_params(
            total_traffic_volume=day_total, tag_probabilities_outer=probs, vocabs_outer=vocabs,
            seasonal_context=ctx,
            period={"period_start": base + timedelta(seconds=ds), "period_end": base + timedelta(seconds=de)},
            objective="maximize_money")
        report = seasonal_balance_traffic(ads, sp)
        for k, v in report.items():
            remaining[k] = max(0, remaining[k] - v)
        bp = create_balancing_params(total_traffic_volume=day_total, tag_probabilities_outer=probs,
                                     vocabs_outer=vocabs, objective="maximize_money")
        fns.append(_weights_fn(pack, prep, ads, report, bp))
    return fns


def _combo_weight(fn, cache: dict, key: int, c: int, a: int) -> float:
    v = cache.get(key)
    if v is None:
        v = fn(c, a)
        cache[key] = v
    return v
