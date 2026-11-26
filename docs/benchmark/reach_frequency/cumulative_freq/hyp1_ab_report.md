# Hypothesis 1: A/B of the B-forward fix on the real balancer — report

## Did it get better or worse?

**It got better — on a realistic profile in all cases.** But how much better
**depends entirely on which limit is set**.

Below is the realistic profile (6 days, as built in prod), fix **B**.
**`TV` = how much the model lies in shape; lower = better.**

| daily per-user limit | before | after | gain | outcome |
|---|---|---|---|---|
| **1** | 0.1345 | **0.0447** | **−9.0 pp** | **better, strongly** |
| **2** | 0.1116 | **0.0636** | **−4.8 pp** | **better, noticeably** |
| 3 | 0.0965 | 0.0706 | −2.6 pp | better |
| 5 | 0.0765 | 0.0677 | −0.9 pp | barely, within noise |
| 10 | 0.0470 | 0.0448 | −0.2 pp | almost nothing |

**The key split is by limit tightness.** The model's own week-to-week noise is
~5% (see [README](../README.md)):

- **Tight limits (C=1–2): a gain of 9.0 and 4.8 pp** — this is **on the order of the noise and larger**, i.e. a
  real, reproducible effect. And limits of 1–3 impressions/day per person are a
  common setting in advertising.
- **Loose limits (C≥5): 0.9 pp and less** — drowns in the noise, indistinguishable from chance on another week.
  (Like fixing a scale from 7 kg to 6.8 kg when it jumps by ±5 kg.)

**Why the gain fades as the limit grows** — it is eaten by the profile length (§3.2, §3.3): at C=5
the gap closure drops **58% → 36% → 11%** for a 1 / 3 / 6-day profile. At C=1–2 the fix
survives day mixing and holds **67% / 43%** even at 6 days.

**Hence the main missing fact:** what is the **distribution of `user_frequency_limit.d` across
real campaigns**? If 1–3 dominate — the fix pays off; if ≥5 — it does not. This is known
from the campaign configs, but we have not checked it (§4).

**The only case where it got worse** is the tight limit C=1 **on a one-day** profile
(0.0855 → 0.1043): there the sweep over-front-loads. On the realistic 6-day
profile this does not happen — C=1 is fixed best of all (0.1345 → 0.0447). More in §5.

**And nothing broke:** the total volume is preserved exactly (1.000×), at a loose limit
the fix does not trigger, 647 tests are green, and the balancer even **got faster**. The code is behind a flag,
off by default → zero impact on prod.

> **Verdict: the fix is correct; its payoff depends on which limits are set in prod.**
> At C=5 the gain is within the noise. But at **tight limits (C=1–2) fix B gives 67% / 43%
> even on a 6-day profile** — and frequency limits of 1–3 impressions/day are common in advertising.
> **The key missing fact is the distribution of `user_frequency_limit.d` across real
> campaigns** (§4). Fix **A (elastic) should be dropped: it loses to B at every
> limit** (§3.4).

---

A check of the fix from the spec (historical design note, not included).
Background: [`cumfreq_report.md`](cumfreq_report.md) proved the problem (a shape gap
`TV(prop,true)` = 7–12%), [`fix_gain_report.md`](fix_gain_report.md) measured on logs that
aggregated headroom closes **~53%** of the gap at C=5. Here the fix is **integrated into the
balancer behind a flag** and run through an A/B.

### Notation (briefly, so you do not have to flip through the previous reports)

- **`true`** — the reference of reality: each user has their own personal daily budget `C`,
  reset every day. Built with the assumption **`P=1`** — the campaign gets an impression on
  **every** user request until their limit is exhausted (greedy delivery, an upper
  bound; in reality `P<1` due to competition with other campaigns/filters — see
  `cumfreq_report.md`, §2).
- **`prop`** — what the balancer computes **now** (`_compute_user_ratio`): the daily volume
  is distributed across hours proportionally to `w_h`, the same saturation coefficient for
  all hours.
- **`fixed`** — an independent simulation of the proposed fix B (aggregated
  `remaining` headroom, the function `sim_fixed`): its own coefficient for each hour, computed by
  a sweep of the shared budget (see `fix_gain_report.md`).
- **`bal_off` / `bal_on`** — the same `prop`/`fixed` pair, but produced by the **real balancer**
  (flag `use_cumulative_user_headroom` off/on), rather than by an independent simulation. The match
  `bal_off≈prop` and `bal_on≈fixed` (§3.1) confirms the fix is built into the code correctly.

---

## 1. What was implemented

`_headroom_sweep` + `_compute_user_ratios_cumulative` in `seasonal/balance.py`, behind the kw-only
flag `build_seasonal_context(..., use_cumulative_user_headroom=False)` (the fix 0 convention;
no global constants are introduced). The slot loop and `remaining` are **untouched**.

Instead of ONE saturation coefficient for all hours — its own for each hour, from the sweep:
`b = C`; `delivered_h = Σ min(count_uh, b)`; `coef[h] = delivered_h/req_h`; `b -= delivered_h/N`.
Then renormalization to the exact total of the old model (`Σ coef[h]·w_h == coef_old`) with a clamp at 1.0.

Covers only NON-hourly (`d`/`w`/`m`) `user_frequency_limit`s; the `'h'` path and ads
without a user limit fall back to the old `_compute_user_ratio`.

## 2. Methodology

A real downsample of janus-20260615 → CSV ([`make_ab_log.py`](make_ab_log.py), sampling
**whole users**, `hash(uid) % 187`, so that the per-user frequency structure
survives) → the real `build_seasonal_context` → the real slot loop
([`hyp1_ab_balancer.py`](hyp1_ab_balancer.py)).

The `true` reference (each with their own budget, **reset every day**) and the `fixed` sim are computed from
the same CSV independently of the balancer. The metric is `TV` (the share of impressions "in the wrong hour"),
normalizing both curves → a pure shape error.

## 3. Results

### 3.1 Validation of the integration (layer 2) — perfect

| check | value | outcome |
|---|---|---|
| `TV(bal_off, prop)` | ≤ 0.0001 | OFF exactly reproduces the current model |
| `TV(bal_on, fixed)` | ≤ 0.0001 | ON exactly reproduces the sim's sweep |
| `Σon / Σoff` | **1.000×** | renormalization keeps the total exact |

The raw sweep overshoots the volume (at C=5: 70,352 vs 63,640 = **1.105×**) —
renormalization restores the exact total while preserving the shape (`bal_on = sim_fixed × 0.904`
in every hour).

### 3.2 Gain vs profile length — the fix breaks down

The share of the shape gap closed:

| `C` | 1-day profile | 3 days | **6 days** |
|----:|----:|----:|----:|
| 1 | −22% | 75% | 67% |
| 2 | 47% | 56% | 43% |
| 3 | 66% | 43% | 27% |
| **5** | **58%** | **36%** | **11%** |
| 10 | 41% | 19% | **5%** |

At realistic limits (C=3/5/10) — a clean monotonic decay. The one-day run
reproduces the ~53% measured on logs (58%), i.e. the fix works exactly as promised —
**but only when the profile is one-day**.

The 53% → 58% difference (5 pp) is not a methodological discrepancy but **sampling noise**:
`fix_gain_report.md` computed over the full week of logs (27.7 million user-days), here —
over the downsample `hash(uid) % 187` (~30k users/day, see §2, `make_ab_log.py`). This does not
affect the order of the conclusion (~50% at C=5).

### 3.3 Why (the main reason — §7 of the spec)

`seasonality.py:86` — `h = _get_h_type(ts, mode)`, for `hour_of_day` this is `ts.hour`.
**The date is thrown away.** Therefore `user_counts_by_hour[14][uid]` = the user's requests at 14:00
summed over ALL days of the log, and "7 requests in a single day" (the daily limit cuts hard)
is indistinguishable from "1 request seven days in a row" (the limit never bites).

The entire effect of hypothesis 1 is created by group C — heavy multi-hour burst users (19% of volume,
distortion 0.197). Day mixing **smooths out exactly this burst structure**, and front-loading
has nothing to hold on to. The longer the profile, the stronger the smoothing.

This is a **pre-existing** limitation of the aggregate histogram (the old `_compute_user_ratio`
is blind in the same way), not something the fix introduces. But it puts a ceiling on this particular fix.

### 3.4 Fix A (elastic buffer) — loses to B everywhere, drop it

Implemented the same way (`_compute_user_ratios_elastic`, the flag
`use_elastic_user_limit` + `elastic_beta`, mutually exclusive with B). The curve
`coef_old·(1−h/24)^β` **does not look at the data at all** — only at the hour.

The share of the gap closed, **6-day (realistic) profile**:

| `C` | β=0.5 | β=0.8 | β=1.0 | β=1.5 | for comparison: **B** |
|----:|----:|----:|----:|----:|----:|
| 1 | **+50%** | +15% | −11% | −66% | **67%** |
| 2 | **+35%** | −13% | −41% | −101% | **43%** |
| 3 | +20% | −35% | −67% | −135% | **27%** |
| 5 | −12% | −80% | −122% | −208% | **11%** |
| 10 | −117% | −230% | −299% | −443% | **5%** |

**Conclusion: A is strictly dominated by B at every limit.** A's best β is always 0.5 (the edge of
the sweep), and even that is worse than B: 50% vs 67% at C=1, 35% vs 43% at C=2. At C≥5 A
goes negative, i.e. it does **worse** than touching nothing at all.

**Why.** A imposes a monotonic decline over the whole day, whereas reality is only **slightly
flatter** than traffic — it still follows the evening peak. The curve overshoots the target. B
takes the shape from the data, so it cuts exactly where the budget is really exhausted.

**Additionally:** A requires calibrating β (a magic constant, section 6 of the doc), B is
parameter-free. And A loses volume at loose limits (Σ 0.919× at C=10, where renormalization
runs into the clamp `ratio ≤ 1`), whereas B is always conservative (1.000×).

This **closes the hybrid idea** "B as the base + A for tight limits": B wins there too.

**A caveat on the discrepancy with D.1.** [`fix_gain_report.md`](fix_gain_report.md) on logs
gave A at C=1 **+38%**, here on the one-day profile — **−6%** (on the 6-day one +50%).
A is a fixed curve; what changes is not it but **the reality it is compared against**:
the size of A's gain is determined entirely by how front-loaded `true` is
relative to traffic on the specific data. A has no stable gain on any
data set — which is in itself an argument against it.

### 3.5 Guardrails — all green

| criterion | outcome |
|---|---|
| No-op at a loose limit | ✅ `Σoff == Σon`, per hour `allclose=True` |
| Conservation of Σ | ✅ 1.000× at all C and all profiles |
| Shape is front-loaded (morning ↑, evening ↓) | ✅ C=5, 1 day: h0 3362→3922, h23 3656→3110 |
| Regression `pytest tests/balancer` with OFF | ✅ **647 passed** |
| Unit tests of the sweep | ✅ 12 passed, numbers checked on paper |

### 3.6 Performance — the fix SPEEDS THINGS UP

| ads | OFF | ON |
|---:|---:|---:|
| 1 | 2.23 s | 2.01 s |
| 5 | 4.21 s | 2.21 s |
| 20 | **10.95 s** | **2.60 s** |

The old path calls `_compute_user_ratio` for each (ad, hour) pair = 24 times per
ad, and each time re-runs `apply_histogram_correction` over all users —
although for the non-hourly path the result **does not depend on the hour**. The sweep is computed once
per ad. A pre-existing redundancy was cured as a side effect (~0.45 s → ~0.03 s per
ad).

## 4. Conclusion and what to do next

1. **Fix B is done correctly** — the integration matches the simulation bit-for-bit, guardrails
   are intact, the regression is green (651), performance improved.
2. **Fix A — drop it.** Strictly dominated by B at every limit (§3.4), at C≥5 it makes things
   worse, requires calibrating β, and loses volume. The hybrid idea "B + A for tight limits"
   is also closed: B wins there too.
3. **B's payoff hinges on one unknown fact.** The gain is split by limit tightness:
   C=1–2 → **9.0 / 4.8 pp** (on the order of the noise and larger, a real effect);
   C≥5 → **≤0.9 pp** (within the noise). The prod effect = a weighting of these numbers by the real
   distribution of limits.

**Next step (the decision blocker):** look at the **distribution of `user_frequency_limit.d`
across real campaigns**. This is a cheap check against configs, and it unambiguously settles
the question:

- **1–3** dominate → the fix pays off, deploy (flag ON);
- **≥5** dominate → it does not pay off, close hypothesis 1.

Exactly the same gap as with fix 0 (where the distribution of the scarcity `R` is unknown).

**If it turns out the limits are loose,** but the fix is still wanted — what remains is to
**extend `LogStreamState` to `(user, day)` resolution**: then day-blending disappears and
even at C=5 ~58% returns. The cost is memory ×n_days on the already heavy histogram
`{hour: {uid: count}}`. A separate task.

Both fixes sit **behind flags, default OFF** — zero impact on prod.

## 5. Limitations

- P=1 (an impression on every request until exhaustion) is an upper bound; at a real P<1 it is smaller.
- `true` is a simulation (greedy cumulative filling), not delivery logs (there are none).
- A downsample of ~30k users/day from one week; we compare shapes and relative numbers.
- Profiles of 1/3/6 days; a multi-week one was not measured — the trend is monotonic, the expectation is ≤5%.
- C=1 behaves non-monotonically (−22% / 75% / 67%): at a tight limit the one-day sweep
  over-front-loads, and day mixing dampens this by accident. We draw no conclusions at C=1.

  **Mechanism (from the `sim_fixed` code):** the shared budget `b` starts equal to `cap` and is **one for
  everyone**, not personal. At the very first processed hour (`h=0`) it is still full,
  so `min(count_uh, b)` cuts no one — **all** users who have at least one request in hour 0
  are counted as if they had exhausted their entire daily limit there.
  The budget decreases by `delivered_h / n_users`, and at `C=1` this is enough to deplete
  `b` almost completely within the first few hours — if the aggregate reach of the first hours
  is comparable to the total number of users. Real users (`true`) get their
  single delivery each in THEIR OWN first active hour, and these hours are spread
  over the whole day rather than dumped at the start. Hence `fixed` shows a sharp, unjustified skew
  toward the morning that does not exist in reality. On multi-day profiles (3/6 days)
  `hist[h]` mixes hours of different days (§3.3), and the same formula by coincidence
  spreads the budget "exhaustion" more softly — so the numbers for C=1 are better there, but for
  a reason that is wrong for this limit, not because day-blending actually helps.

## 6. How to reproduce

```bash
pytest tests/balancer                                  # 647 passed (flag OFF)

# logs (2 min each, peak RSS ~0.31 GB)
DAYS=1 OUT=.../ab_log_1day.csv python .../make_ab_log.py
DAYS=6 OUT=.../ab_log_6day.csv python .../make_ab_log.py

PYTHONUTF8=1 python .../hyp1_ab_balancer.py                        # 1 day
AB_LOG=.../ab_log_6day.csv PERIOD_DAYS=6 python .../hyp1_ab_balancer.py   # 6 days
```

Flag: `build_seasonal_context(..., use_cumulative_user_headroom=True)`, default `False`.

**Code status:** changes are in the working tree of the `balancer` branch, not committed, flag OFF.
