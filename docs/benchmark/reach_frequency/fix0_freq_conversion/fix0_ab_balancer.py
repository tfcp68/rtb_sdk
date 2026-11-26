"""A/B of fix 0 on the REAL balancer (seasonal_balance_traffic), flag off vs on."""
import sys, os
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src"))
from datetime import datetime

import numpy as np

from rtb_sdk.balancer.seasonal.corrections import compute_hour_shares
from rtb_sdk.balancer.seasonal.balance import seasonal_balance_traffic

# --- profiles --------------------------------------------------------------
_day = np.array([0.2,0.15,0.1,0.1,0.15,0.2,0.4,0.6,0.8,0.9,1,1,1.3,1.2,
                 0.9,0.9,1,1.1,1.3,1.5,1.8,1.9,1,0.5])
_day = _day / _day.sum()
w_uniform = np.full(24, 1/24)
w_real = 0.55 * _day + 0.45 * w_uniform          # TV≈0.14, like the real week
w_real = w_real / w_real.sum()
w_sharp = _day.copy()                            # TV≈0.26
PROFILES = {"uniform": w_uniform, "real": w_real, "sharp": w_sharp}

def tv_u(w): return 0.5 * float(np.sum(np.abs(w - 1/len(w))))


def build_ctx(w, mode="hour_of_day", use_weighted_freq_shares=False):
    wd = {i: float(w[i]) for i in range(len(w))}
    ctx = {}
    for h in range(len(w)):
        entry = {"weight": float(w[h]), "user_activity_ratio": {},
                 "tags_probability": None}
        # Presence of *_share = the fix is enabled (as build_seasonal_context fills it
        # with use_weighted_freq_shares=True); prepare_hour_ads takes them as they are.
        if use_weighted_freq_shares:
            sh = compute_hour_shares(mode, wd, h)
            entry["day_share"] = sh["day"]
            entry["week_share"] = sh["week"]
            entry["month_share"] = sh["month"]
        ctx[h] = entry
    return {"mode": mode, "context": ctx}


def make_params(w, total, tag_probs, vocabs, use_weighted_freq_shares=False):
    return {
        "total_traffic_volume": int(total),
        "tag_probabilities": tag_probs,
        "vocabs": vocabs,
        "objective": "maximize_money",
        "max_n_categories": 100,
        "min_category_probability": 1e-9,
        "n_threads": 1,
        "seasonal_context": build_ctx(w, use_weighted_freq_shares=use_weighted_freq_shares),
        "period": {"period_start": datetime(2024, 1, 1, 0, 0),
                   "period_end": datetime(2024, 1, 2, 0, 0)},   # 24 h = one cycle
    }


def run_ab(ads, w, total, tag_probs, vocabs):
    """Returns (result_old, result_new): dict[ad_id]->delivered."""
    old = seasonal_balance_traffic(
        dict(ads), make_params(w, total, tag_probs, vocabs, use_weighted_freq_shares=False))
    new = seasonal_balance_traffic(
        dict(ads), make_params(w, total, tag_probs, vocabs, use_weighted_freq_shares=True))
    return old, new


# --- simulation (reference) for a single ad -----------------------------
def sim_delivery(w, freq, total, P, fix):
    avail = total * w * P
    if fix:
        cap = freq * w                      # hour_of_day, 'd'
    else:
        cap = np.full(len(w), freq / 24)
    return float(np.minimum(cap, avail).sum())


# =========================================================================
# Scenario A: one freq-capped ad, P=1, sweep of R. Validation against the sim.
# =========================================================================
print("=" * 78)
print("SCENARY A: one-off, ad_frequency_limit.d=FREQ, P=1, swipe R")
print("=" * 78)
FREQ = 100_000
vocabs = {"geo": ["geo:t"]}
tag_probs = {"geo:t": 1.0}
ad = {"a": {"id": "a", "targets": {"value": {"geo": ["t"]}},
            "volume": 10**9, "cpm": 10.0,
            "ad_frequency_limit": {"value": {"d": FREQ}}}}

for pname, w in PROFILES.items():
    print(f"\n--- profile {pname} (TV(w,uniform)={tv_u(w):.4f}) ---")
    print(f"{'R':>5} {'ideal':>8} {'bal_old':>9} {'bal_new':>9} "
          f"{'sim_old':>9} {'sim_new':>9} {'old==sim':>9} {'new==sim':>9}")
    for R in [0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0]:
        total = int(R * FREQ)                       # P=1 -> avail=total
        old, new = run_ab(ad, w, total, tag_probs, vocabs)
        bo, bn = old["a"], new["a"]
        so = sim_delivery(w, FREQ, total, 1.0, fix=False)
        sn = sim_delivery(w, FREQ, total, 1.0, fix=True)
        ideal = min(FREQ, total)
        print(f"{R:>5} {ideal:>8} {bo:>9} {bn:>9} {so:>9.0f} {sn:>9.0f} "
              f"{abs(bo-so) <= 2:>9} {abs(bn-sn) <= 2:>9}")


# =========================================================================
# Scenario B: two campaigns competing for the same traffic.
#   ad_hi -- expensive, WITHOUT a freq limit; ad_lo -- cheaper, with a freq limit d~R=1.
# We look at redistribution, conservation, money, no-harm.
# =========================================================================
print("\n" + "=" * 78)
print("SCENARY B: valuable freq-capped campaign vs filler (real profile)")
print("=" * 78)
w = w_real
FREQ_CAP = 100_000
TOTAL = 100_000            # R for cap = TOTAL/FREQ_CAP = 1 -> maximum effect
vocabs = {"geo": ["geo:t"]}
tag_probs = {"geo:t": 1.0}
ads2 = {
    "cap":  {"id": "cap", "targets": {"value": {"geo": ["t"]}}, "volume": 10**9,
             "cpm": 30.0, "ad_frequency_limit": {"value": {"d": FREQ_CAP}}},  # valuable + freq-cap
    "fill": {"id": "fill", "targets": {"value": {"geo": ["t"]}}, "volume": 10**9,
             "cpm": 10.0, "ad_frequency_limit": {"value": {"d": 10**9}}},     # cheap filler
}
old, new = run_ab(ads2, w, TOTAL, tag_probs, vocabs)
cpm = {"cap": 30.0, "fill": 10.0}
def money(res): return sum(cpm[a] * v for a, v in res.items())
print(f"total_traffic_volume = {TOTAL}, cap.freq_d = {FREQ_CAP} (R=1), cpm: cap=30 fill=10")
print(f"{'':>6} {'delivered_old':>14} {'delivered_new':>14} {'d(new-old)':>11}")
for a in ("cap", "fill"):
    print(f"{a:>6} {old[a]:>14} {new[a]:>14} {new[a]-old[a]:>+11}")
print(f"{'Σvol':>6} {sum(old.values()):>14} {sum(new.values()):>14} "
      f"{sum(new.values())-sum(old.values()):>+8}   (<= {TOTAL} = conservation)")
print(f"cap attainment old={old['cap']/FREQ_CAP*100:.1f}%  new={new['cap']/FREQ_CAP*100:.1f}%")
print(f"{'money':>6} {money(old):>14.0f} {money(new):>14.0f} "
      f"{money(new)-money(old):>+8.0f}  ({(money(new)/money(old)-1)*100:+.1f}%)")


# =========================================================================
# Invariant: uniform profile -> old == new per ad (the fix = no-op).
# =========================================================================
print("\n" + "=" * 78)
print("INVARIANT: uniform profile -> old == new (fix no-op)")
print("=" * 78)
o, n = run_ab(ad, w_uniform, FREQ, tag_probs, vocabs)
print(f"uniform, R=1: old={o['a']}, new={n['a']}, coincidentally={o['a']==n['a']}")
