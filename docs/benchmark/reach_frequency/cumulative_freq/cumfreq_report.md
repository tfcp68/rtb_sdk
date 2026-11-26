# Hypothesis 1: cumulative frequency limits — report

A check of section 1 of
[`../../frequency_accounting_improvements.md`](../../../frequency_accounting_improvements.md).
Notebook: [`test_cumfreq.ipynb`](test_cumfreq.ipynb). Data: one clean week,
`janus-20260615`.

> **Verdict: the hypothesis is CONFIRMED.** An error of **~7% at a daily limit of 5** (up to **~12%**
> at tight limits of 1–2), directed at **overestimating evening hours** and created by
> a specific minority of users (~14% of volume). This is the **largest effect** of
> all branches — the only one that goes beyond the model's ~5% noise. The cheap
> approximation from section 1 **is worth implementing**.
>
> **Update.** The gain from the approximation has since been measured: first on logs
> ([`fix_gain_report.md`](fix_gain_report.md)), then in a real A/B on the balancer
> ([`hyp1_ab_report.md`](hyp1_ab_report.md)) — the outcome is more modest than expected here.

**What "confirmed" means (important, so it is not misread).** What is confirmed is that the
**problem is real** — the current model distributes delivery across hours differently from
cumulative reality (a 7–12% gap). It does **NOT** mean the fix will deliver that gain:

1. **"Reality" here is a simulation, not delivery logs** (there are none): greedy cumulative
   filling, P=1. A conscientious proxy, but not a fact. More precisely: "the problem exists under
   a conscientious model of reality".
2. **The gain from the fix has not been measured yet.** No fix has been implemented or A/B-tested.
   The cheap approximation will close only **part** of the gap, and a real P<1 will reduce it →
   the gain is almost certainly **less** than 7–12%. How much — only implementation + A/B will show
   (as for fix 0). Right now we are at the first line: the problem is real, the fix effect is TBD.

---

## 1. What the problem is (in plain words)

A campaign has a **daily per-user impression limit** (`user_frequency_limit.d = C`
— e.g. no more than 5 impressions per day to one person). The balancer plans **each hour
independently** and **does not subtract** what it has already shown that person in previous hours.

- The total **daily volume** is computed correctly by the model (via the full histogram).
- But **across hours** it distributes proportionally to the traffic `w_h` (which has an evening peak).
- Reality, however, is **front-loaded**: people use up their limit over the course of the day and "drop off"
  — by evening their remainder is already small.

→ The model **overestimates evening hours** and underestimates morning ones.

**Difference from fix 0:** fix 0 corrected the *shape* of the hourly ceiling (flat → weighted);
hypothesis 1 is about *accumulation across hours*. These are **different, orthogonal** problems.

---

## 2. How it was tested

A microsimulation on `(user_id, hour, day)` logs. For a daily limit `C` we compute delivery
per user-day in two ways and compare the **hourly curves**:

- **`true`** (reality) — cumulatively: budget `C`, walk through the hours 0→23, in each hour
  `min(requests, remaining)`, subtract. A user who has exhausted the limit sees 0 afterwards.
- **`prop`** (the current model) — the same daily volume, shape ∝ `w_h`.

**Metric — `TV(prop, true)`**: the share of impressions landing "in the wrong hour" (0 = they coincide).
`true` and `prop` have the **same total volume**, so TV is purely a shape error.

**How "balancer-like" this is.** `prop` is **exactly** what the balancer does for a
`'d'` limit: verified in the code of `_compute_user_ratio` — it gives an hour-**constant**
coefficient = `Σmin(count,C)/Σcount`, applied to a volume ∝ `w_h`. The only
assumption is on the **reality** side (`true`): greedy cumulative delivery, P=1 (an impression
on every request until the limit is exhausted), since there are no logs of actual delivery. P=1 is an
**upper bound**; at P<1 the scale is smaller, the shape is the same.

---

## 3. Results

### 3.1 Magnitude: sweep over the daily limit `C`

| Daily limit `C` | `TV(prop,true)` | comment |
|---|---|---|
| 1 | **0.119 (11.9%)** | tight limit — the error is maximal |
| 2 | 0.101 | |
| 3 | 0.088 | |
| 5 | **0.070** | typical limit |
| 10 | 0.044 | loose — already around the ~5% noise |

The error **grows with the tightness of the limit**: the smaller the limit, the faster users
exhaust it → the stronger the front-loading → the stronger the divergence from ∝`w_h`.

### 3.2 Direction: overestimation of evening hours

The peak hours by real delivery are **18–23**, and the `prop` model **overestimates** them by
**+16.7%** (at `C=5`). Morning hours are, symmetrically, underestimated. Exactly as the doc claims.

### 3.3 Driver: how users are distributed

The error can only be created by users who are **both spread across hours AND exceed the
limit**:

- **Active in more than 1 hour: 17.8%** of user-days (the other 82% sit in a single
  hour — they cannot produce a cross-hour error).
- **Exceed the daily limit** (the limit "bites" only on them): `C=1` → 62%, `C=3` → 46%,
  `C=5` → 22%, `C=10` → 12%.

### 3.4 Decomposition: who creates the error (`C=5`)

| User group | share of volume | shape distortion |
|---|---|---|
| **A** — do not exceed the limit | 62% | **0.000** |
| **B** — exceed, active in 1 hour | 24% | 0.019 |
| **C** — exceed AND spread across hours | **14%** | **0.190** |

**All of the distortion sits in group C** (A and B ≈ 0). This is the "smoking gun": the mechanism is **precisely
the cumulative cross-hour one**, not something else (e.g. not intra-hour saturation of
group B). The effect is created by a **minority of ~14% of volume**.

### 3.5 Verdict (rule declared in advance)

The rule was fixed BEFORE the run. The hypothesis is confirmed if all three conditions hold:

| Condition | Value | Outcome |
|---|---|---|
| (1) `TV(prop,true) > 0.05` at `C≤5` | 0.070 | ✅ |
| (2) overestimation of peak hours `> 0` | +16.7% | ✅ |
| (3) effect from the cross-hour group C | share 14%, distortion 0.19 | ✅ |

→ **CONFIRMED.**

---

## 4. How large — compared with other branches

| Branch | Effect | Within the ~5% noise? |
|---|---|---|
| A. reach vs volume | 3–6% | yes |
| B. profile backtest | ~5% | — (this is the noise) |
| C. fix 0 | ~4.6% (up to 14% at peak) | borderline |
| **D. hypothesis 1 (cumulative)** | **7–12%** (tight limits) | **NO — goes beyond the noise** |

Hypothesis 1 is the **only** one whose effect is consistently above the model's own weekly
noise, especially for tight per-user limits. Unlike the reach decomposition (within
the noise, does not pay off), this one **is worth** taking through to implementation.

---

## 5. Limitations

- **P=1 is an upper bound** (the ad is shown on every request until the limit is exhausted);
  at a real P<1 the scale is smaller, the direction and shape are the same.
- **`true` is a simulation**, not delivery logs (there are none); the balancer side `prop`
  was verified exactly in the code, reality is a model (greedy cumulative filling).
- Affects only campaigns with a **daily** `user_frequency_limit.d`; the share of such ones in prod
  is unknown.
- One week; the file has `n_days=8` (2 partial days at the MSK boundaries) — a slight artifact,
  the 7–12% order is stable, but for cleanliness the full days should be filtered and the run repeated on
  1–2 other weeks.

---

## 6. Recommendation

**Status: done, see D.1/D.2 in the [general README](../README.md).** The plan below describes
what was done next — gain measurement on logs and an A/B on the balancer; the outcome is
more modest than expected (day-blending eats the gain at loose limits).

**Implement** — but the **cheap approximation**, not the exact per-user LP (it is intractable). From
section 1 of the doc: **aggregated `remaining` headroom** (reuses the existing
cross-slot `remaining[ad_id]`, subtracting the average estimate of impressions per user), with a
fallback to the elastic buffer. The order is the same as for fix 0:

1. Clean up the partial-day artifact + run on 1–2 other clean weeks.
2. Estimate with a realistic P<1.
3. Implement the approximation **behind a flag** + an A/B on the real `seasonal_balance_traffic`
   (as was done for fix 0), with a "better/worse" rule declared in advance.

The priority is **higher** than the reach decomposition (which is within the noise) and possibly comparable to fix 0
(fix 0 is free but its effect is more modest; hypothesis 1 is larger but requires an approximation).

---

## 7. How to reproduce

1. In [`test_cumfreq.ipynb`](test_cumfreq.ipynb) set `PROFILE_FILE` to a clean week
   (by default `janus-20260615`), run **Run All**.
2. Look at: the sweep chart (TV vs `C`), the per-hour error chart, the driver histogram,
   the decomposition table, and the verdict cell.

The microsimulation computes the heavy window `cum` **once**, after which the sweep is cheap; a parquet
for the balancer is not needed (this is a simulation on logs).
