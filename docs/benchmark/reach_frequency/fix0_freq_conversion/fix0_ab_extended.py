"""Extended checks of fix 0: never-worse grid, floor regression, hour_of_week,
multi-ad mix, aggregate under a distribution of R, performance."""
import sys, os, time, random
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src"))
from datetime import datetime
import numpy as np

from rtb_sdk.balancer.seasonal.corrections import compute_hour_shares
from rtb_sdk.balancer.seasonal.balance import seasonal_balance_traffic

_day = np.array([0.2,0.15,0.1,0.1,0.15,0.2,0.4,0.6,0.8,0.9,1,1,1.3,1.2,
                 0.9,0.9,1,1.1,1.3,1.5,1.8,1.9,1,0.5]); _day/=_day.sum()
w_uniform = np.full(24, 1/24)
w_real = 0.55*_day + 0.45*w_uniform; w_real/=w_real.sum()
w_sharp = _day.copy()
def tv_u(w): return 0.5*float(np.sum(np.abs(w-1/len(w))))

# hour_of_week: weekdays follow _day, weekends are flatter and shifted
_wend = 0.5*_day + 0.5*w_uniform; _wend/=_wend.sum()
w_week = np.concatenate([_day]*5 + [_wend]*2); w_week/=w_week.sum()


def build_ctx(w, mode="hour_of_day", use_weighted_freq_shares=False):
    wd = {i: float(w[i]) for i in range(len(w))}
    ctx = {}
    for h in range(len(w)):
        entry = {"weight": float(w[h]), "user_activity_ratio": {}, "tags_probability": None}
        # Presence of *_share = the fix is enabled (as build_seasonal_context fills it
        # with use_weighted_freq_shares=True); prepare_hour_ads takes them as they are.
        if use_weighted_freq_shares:
            sh = compute_hour_shares(mode, wd, h)
            entry.update({k+"_share": sh[k] for k in ("day", "week", "month")})
        ctx[h] = entry
    return {"mode": mode, "context": ctx}


def make_params(w, total, tag_probs, vocabs, mode="hour_of_day", days=1,
                use_weighted_freq_shares=False):
    return {"total_traffic_volume": int(total), "tag_probabilities": tag_probs,
            "vocabs": vocabs, "objective": "maximize_money", "max_n_categories": 200,
            "min_category_probability": 1e-9, "n_threads": 1,
            "seasonal_context": build_ctx(w, mode, use_weighted_freq_shares),
            "period": {"period_start": datetime(2024,1,1,0,0),
                       "period_end": datetime(2024,1,1+days,0,0)}}


def run_ab(ads, w, total, tag_probs, vocabs, mode="hour_of_day", days=1):
    old = seasonal_balance_traffic(
        dict(ads), make_params(w, total, tag_probs, vocabs, mode, days, use_weighted_freq_shares=False))
    new = seasonal_balance_traffic(
        dict(ads), make_params(w, total, tag_probs, vocabs, mode, days, use_weighted_freq_shares=True))
    return old, new


# ========== 1. NEVER-WORSE GRID: profiles × R × P (gran='d') ================
print("="*78); print("1. NEVER-WORSE: capped-declaration, profiles × R × P (gran d)"); print("="*78)
vocabs = {"geo": ["geo:a", "geo:b"]}
n_better = n_same = n_worse = 0
worse_cases = []
for pname, w in [("real", w_real), ("sharp", w_sharp), ("uniform", w_uniform)]:
    for P in (1.0, 0.5, 0.3):
        tag_probs = {"geo:a": P, "geo:b": round(1-P, 3)}
        for R in (0.5, 0.75, 1.0, 1.25, 1.5, 2.0):
            FREQ = 100_000
            total = int(R*FREQ/P)                      # avail=total*P=R*FREQ
            ad = {"a": {"id":"a","targets":{"value":{"geo":["a"]}},"volume":10**9,
                        "cpm":10.0,"ad_frequency_limit":{"value":{"d":FREQ}}}}
            old, new = run_ab(ad, w, total, tag_probs, vocabs)
            ideal = min(FREQ, total*P)
            bo, bn = old["a"], new["a"]
            if bn > bo + 20:   n_better += 1
            elif bn < bo - 20: n_worse += 1; worse_cases.append((pname,P,R,bo,bn))
            else:              n_same += 1
            if bn > ideal + 20:                        # must not exceed the ideal
                worse_cases.append(("OVER", pname, P, R, bn, ideal))
print(f"improved: {n_better}, changeless: {n_same}, Worse: {n_worse}")
print("regression:", worse_cases or "no")


# ========== 2. FLOOR REGRESSION: small freq_d (dead hours -> floor 0) ========
print("\n"+"="*78); print("2. FLOOR-setback: petty freq_d on sharp profile"); print("="*78)
vocabs1 = {"geo": ["geo:a"]}; tp1 = {"geo:a": 1.0}
print(f"{'freq_d':>7} {'old':>7} {'new':>7} {'ideal':>7} {'new>=old':>9}")
for FREQ in (24, 48, 120, 240, 1000):
    total = FREQ                                       # R=1
    ad = {"a":{"id":"a","targets":{"value":{"geo":["a"]}},"volume":10**9,
               "cpm":10.0,"ad_frequency_limit":{"value":{"d":FREQ}}}}
    old, new = run_ab(ad, w_sharp, total, tp1, vocabs1)
    print(f"{FREQ:>7} {old['a']:>7} {new['a']:>7} {min(FREQ,total):>7} {new['a']>=old['a']:>9}")


# ========== 3. HOUR_OF_WEEK (168 buckets, weekdays/weekends) ==================
print("\n"+"="*78); print("3. hour_of_week: capped d-limit, 7-daytime"); print("="*78)
FREQ = 700_000
ad = {"a":{"id":"a","targets":{"value":{"geo":["a"]}},"volume":10**9,
           "cpm":10.0,"ad_frequency_limit":{"value":{"w":FREQ}}}}
total_daily = FREQ                                     # weekly limit vs weekly traffic ~R=1
old, new = run_ab(ad, w_week, total_daily*7, tp1, vocabs1, mode="hour_of_week", days=7)
print(f"w-limit={FREQ}, TV(week,uniform)={tv_u(w_week):.4f}")
print(f"old={old['a']}, new={new['a']}, ideal≈{min(FREQ, total_daily*7):.0f}, new>=old={new['a']>=old['a']}")


# ========== 4. MULTI-AD MIX: money + per-capped never-worse ==
print("\n"+"="*78); print("4. Realistic mix (real profile): 12 announcements"); print("="*78)
rng = random.Random(7)
vocabsM = {"geo": ["geo:a", "geo:b", "geo:c"]}
tag_probsM = {"geo:a": 0.5, "geo:b": 0.3, "geo:c": 0.2}
adsM = {}
capped_ids = []
for i in range(12):
    tag = rng.choice(["a","b","c"])
    cpm = round(rng.uniform(5, 40), 1)
    has_cap = rng.random() < 0.5
    freq = rng.choice([50_000, 100_000, 200_000]) if has_cap else 10**9
    adsM[f"ad{i}"] = {"id":f"ad{i}","targets":{"value":{"geo":[tag]}},"volume":10**9,
                      "cpm":cpm,"ad_frequency_limit":{"value":{"d":freq}}}
    if has_cap: capped_ids.append(f"ad{i}")
TOTAL = 300_000
old, new = run_ab(adsM, w_real, TOTAL, tag_probsM, vocabsM)
cpmM = {a: adsM[a]["cpm"] for a in adsM}
mo = sum(cpmM[a]*old[a] for a in adsM); mn = sum(cpmM[a]*new[a] for a in adsM)
print(f"capped announcements: {len(capped_ids)}, everything 12, total={TOTAL}")
worse = [a for a in capped_ids if new[a] < old[a]-20]
print(f"capped, whomever new<old (setback): {worse or 'no'}")
print(f"Σ volume old={sum(old.values())} new={sum(new.values())} (conservation <= {TOTAL})")
print(f"money old={mo:.0f} new={mn:.0f}  ({(mn/mo-1)*100:+.2f}%)")


# ========== 5. AGGREGATE: average gain under uniform R∈[0.5,2] ==========
print("\n"+"="*78); print("5. Aggregate: middle. fixation capped-pronouncement, real"); print("="*78)
gains = []
for R in np.linspace(0.5, 2.0, 16):
    FREQ = 100_000; total = int(R*FREQ)
    ad = {"a":{"id":"a","targets":{"value":{"geo":["a"]}},"volume":10**9,
               "cpm":10.0,"ad_frequency_limit":{"value":{"d":FREQ}}}}
    old, new = run_ab(ad, w_real, total, tp1, vocabs1)
    ideal = min(FREQ, total)
    gains.append((new["a"]-old["a"])/ideal)
print(f"real profile (TV=0.14): defection R~[0.5..2], mean="
      f"{np.mean(gains)*100:.2f}%, max={max(gains)*100:.2f}% (upon R=1)")


# ========== 6. PERFORMANCE off vs on ==============================
print("\n"+"="*78); print("6. Productivity seasonal_balance_traffic off vs on"); print("="*78)
def gen_mix(n_ads, seed=1):
    rng = random.Random(seed)
    tags = ["a","b","c","d"]
    vocabs = {"geo": [f"geo:{t}" for t in tags]}
    tp = {f"geo:{t}": p for t,p in zip(tags, [0.4,0.3,0.2,0.1])}
    ads = {}
    for i in range(n_ads):
        t = rng.choice(tags); cap = rng.choice([50_000,100_000,10**9])
        ads[f"ad{i}"] = {"id":f"ad{i}","targets":{"value":{"geo":[t]}},"volume":10**9,
                         "cpm":round(rng.uniform(5,40),1),
                         "ad_frequency_limit":{"value":{"d":cap}}}
    return ads, tp, vocabs

def timeit(flag, ads, w, total, tp, vocabs, runs=3):
    ts = []
    for _ in range(runs):
        p = make_params(w, total, tp, vocabs, use_weighted_freq_shares=flag)
        s = time.perf_counter(); seasonal_balance_traffic(dict(ads), p); ts.append(time.perf_counter()-s)
    return min(ts)

# warm-up
_a,_tp,_v = gen_mix(20); timeit(False,_a,w_real,100_000,_tp,_v,1)
print(f"{'n_ads':>6} {'off, ms':>9} {'on, ms':>9} {'overhead':>10}")
for n in (10, 50, 200, 500):
    ads, tp, vocabs = gen_mix(n)
    t_off = timeit(False, ads, w_real, 300_000, tp, vocabs)
    t_on  = timeit(True,  ads, w_real, 300_000, tp, vocabs)
    ov = (t_on/t_off - 1)*100 if t_off>0 else 0
    print(f"{n:>6} {t_off*1000:>9.1f} {t_on*1000:>9.1f} {ov:>+9.1f}%")
