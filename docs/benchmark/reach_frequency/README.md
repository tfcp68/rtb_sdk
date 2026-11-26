# Frequency accounting in the balancer — summary report

An overview of all studies in this folder: the accuracy of the seasonal profile `w_h`, whether a
reach/freq decomposition is needed, and the effectiveness of the fixes from
[`../frequency_accounting_improvements.md`](../../frequency_accounting_improvements.md).

> **Main conclusion.** Most of the "frequency" inaccuracy lives at the **~5%** scale
> (the `w_h` profile is correct to that precision), and improvements within it do not pay off.
> **Exactly one thing is worth deploying — fix 0** (a free correctness fix, up to 14%
> for a throttled campaign).
>
> **Reach decomposition** (A) — an effect of 3–6%, within noise, closed.
>
> **Hypothesis 1** (D) — the only one whose *problem* broke through the noise (a 7–12% gap). The fix is
> **implemented, integrated into the balancer, validated bit-for-bit** and even **speeds up**
> the balancer. Its gain is **split by limit tightness**: tight limits **C=1–2 → 9.0 / 4.8
> pp** (real effect), loose ones **C≥5 → ≤0.9 pp** (within noise — the long profile
> eats the fix). **The decision hinges on one unverified fact: the distribution of
> `user_frequency_limit.d` across real campaigns** — if 1–3 dominate, deploy; if
> ≥5, close (section D.2). The second candidate — the elastic buffer — is **rejected**: it strictly
> loses to the first at every limit.

---

## Folder structure

Each study lives in its own subfolder:

| Folder | Branch | Contents |
|---|---|---|
| [`fix0_freq_conversion/`](fix0_freq_conversion) | C. fix 0 | simulation, A/B on the balancer, report |
| [`reach_vs_volume/`](reach_vs_volume/README.md) | A. reach vs volume | hypothesis, notebook, report generator, `reports/`; its own summary [README](reach_vs_volume/README.md) across all weeks |
| [`profile_backtest/`](profile_backtest) | B. profile backtest | out-of-sample error of `w_h` |
| [`cumulative_freq/`](cumulative_freq/README.md) | D. hypothesis 1 (per-user) | microsimulation, gain measurement, **A/B on the balancer**; its own summary [README](cumulative_freq/README.md) across all three stages |

---

## Notation

- **`C`** — `user_frequency_limit.d`, the daily limit of impressions of one ad per
  user (e.g. "no more than 5 impressions per day to one person"). Its tightness
  is varied in the sweeps C=1,2,3,5,10 throughout branch D: the smaller `C` is, the more the model
  lies; with a loose `C` it is almost a no-op.
- **`TV`** (Total Variation) — the share of impressions "landing in the wrong hour" when comparing two
  hourly distributions of equal total volume (0 = shapes coincide, 1 =
  maximum divergence); purely a **shape** error, not a volume error. The meaning is the same
  everywhere, only the compared distributions change: in branch A — `TV(w_h, reach_share)`,
  in branch B — `TV(profile, uniform)`, in branch D — `TV(prop, true)` (`prop` is what the balancer
  actually does ∝ `w_h`, `true` is the true distribution from the simulation/logs).

---

## Results table

Three branches converged on the same order of magnitude, the fourth (hypothesis 1) broke through it — but
its fix ran into the structure of the profile:

| Measurement | What was measured | Result |
|---|---|---|
| **A. reach vs volume** (TV) | how much `w_h` (volume) diverges from `reach_share` (reach) | **3–6%** per week → within noise |
| **B. backtest** | how much `w_h` misses reality (next week) | **~5%** out-of-sample ← **this is the noise** |
| **C. fix 0** | how much delivery shortfall is eliminated by replacing the flat hourly freq limit (`freq_d/24`) with a weighted one (`freq_d·w_h`) | on average **~4.6%**, up to 14% at peak → **deploy** |
| **D. hypothesis 1** — *problem* | hourly distribution error under a per-user limit | **4–12%** (C=1→12%, C=5→7%, C=10→4%) ← above noise |
| **D.1 hypothesis 1** — *fix gain on logs* | what share of the gap a cheap approximation closes | **~50%** at C=3–10 → the reference was 2–4 pp |
| **D.2 hypothesis 1** — *A/B on the balancer* | what fix B delivers after real deployment | on the 6-day profile: **C=1–2 → 9.0 / 4.8 pp** (real effect), **C≥5 → ≤0.9 pp** (eaten by day-blending) ← the distribution of limits in prod decides |
| **D.2 hypothesis 1** — *fix A (elastic)* | alternative approximation | **strictly loses to B at every limit**, worse than nothing at C≥5 → **rejected** |

---

## A. Reach vs volume hypothesis (is decomposition needed)

**In plain words.** For each hour the balancer knows a single parameter — the "hour weight" `w_h`:
what share of all daily impressions falls on that hour. But the number of impressions in an hour
is made up of two different things: **how many distinct people** showed up (`reach`) and
**how many times on average each of them** was shown an ad (`freq`, frequency). `w_h` is their
product, and it does not distinguish where the volume came from.

The problem is that two hours with the same `w_h` can have very different reach.
Example: in the evening 10,000 distinct people showed up, each shown 1.2 times on average —
12,000 impressions in total. In another hour there is a narrow "core" of just 500 active people,
each shown 24 times — also 12,000 impressions. The `w_h` of both hours is
the same. For an ordinary campaign (with no per-user limit) this doesn't matter — impressions
are impressions. But if the campaign has a **per-user impression limit**
(`user_frequency_limit`), then the real capacity of an hour is not the traffic volume, but
`how many distinct people × their limit`: in the example above — an order of magnitude more for the evening
(10,000 people) than for the "core" (500 people), although `w_h` does not show this.

**The hypothesis question:** how much do `w_h` (volume weight, what the model uses now) and `reach_share` (reach weight, what
would have to be used for user-capped campaigns) diverge on real data? If the divergence is small,
`w_h` is good enough as a reach proxy and nothing needs to change. If it is large, the model needs a
separate `reach_share` for user-capped limits.

Formally: for user-capped campaigns the real ceiling is `reach[h] × limit`, whereas the model
uses the volume `w_h = reach[h] × freq[h]`. Do they diverge enough to introduce
`reach_share` in place of `w_h`?
A summary report across all weeks with a common table and conclusions:
[`reach_vs_volume/README.md`](reach_vs_volume/README.md). Notebook:
[`check_reach_vs_volume.ipynb`](reach_vs_volume/check_reach_vs_volume.ipynb) ·
hypothesis: [`hypothesis.md`](reach_vs_volume/hypothesis.md) · reports: [`reports/`](reach_vs_volume/reports).

| Week | Verdict | CoV(freq) (threshold 0.15) | TV wk. | TV day | EmptyUser |
|---|---|---|---|---|---|
| [601](reach_vs_volume/reports/report-20260601.md) | H0 | 0.141 | 5.78% | 4.05% | 0.002% |
| [608](reach_vs_volume/reports/report-20260608.md) | H1 ⚠️ **corrupt data** | 2.54 | 47% | 47% | 0.001% |
| [615](reach_vs_volume/reports/report-20260615.md) | H1 | 0.156 | 6.23% | 4.41% | 0.001% |
| [622](reach_vs_volume/reports/report-20260622.md) | H0 | 0.092 | 3.26% | 3.25% | 0.001% |

**Conclusions:**

1. **The H0/H1 verdict jumps from week to week, but this is noise at the threshold, not a regime change.**
   CoV(freq) wanders around the 0.15 threshold (0.14 → 0.16 → 0.09), and the label flips
   from week to week. H1 in week 615 is "by a hair" (0.156 vs 0.15). The 0.15 threshold
   (and the secondary `max|w_h − reach_share_h| > 0.05`) was not tuned to this data but
   declared in advance in [`hypothesis.md`](reach_vs_volume/hypothesis.md) (step 5, verification
   plan) before running on real weeks.
2. **The stable signal is not the label but TV: the `w_h`/`reach_share` divergence = ~3–6%**
   (wk.) / ~3–4.5% (day) in all **clean** weeks. This is the real magnitude of the effect —
   small and stable.
3. **Audience composition depends on the hour** (CoV of superactive/bot ~0.24–0.30 in all weeks,
   above 0.15). The signal is real (EmptyUser is negligible, ~0.001%), but exploratory — it was not
   part of the declared rule.
4. **Bottom line: decomposition does not pay off.** A gain of ~3–6% is of the same order as the
   model's own weekly error (branch B) — chasing it makes little sense.

## B. Profile backtest (error against reality)

**Question:** how well does last week's profile predict the hourly distribution of
the next week? Notebook: [`backtest_profile.ipynb`](profile_backtest/backtest_profile.ipynb).

- **Out-of-sample error ~5%** on clean pairs (615→622: TV 5.8%; 601→615: 4.2%).
- **The profile beats uniform by ~67%** (without seasonality ~15% would be missed, with it ~5%).
- **Caught a data bug**: week 608 — a spike at 12:00 (50.9% of weekly traffic in a single
  hour, ~130M extra events = backfill/duplicate load). The guard excluded it.
- climatology vs persistence — the signal is thin (only 3 valid weeks, 2 pairs).

## C. Fix 0 (weighted freq conversion)

**Question:** does replacing the flat freq limit `freq/24` with the weighted `freq·w_h` help?
Simulation: [`test_fix0_freqcap.ipynb`](fix0_freq_conversion/test_fix0_freqcap.ipynb) · real balancer:
[`fix0_ab_balancer.py`](fix0_freq_conversion/fix0_ab_balancer.py), [`fix0_ab_extended.py`](fix0_freq_conversion/fix0_ab_extended.py) ·
full report: [`fix0_effectiveness_report.md`](fix0_freq_conversion/fix0_effectiveness_report.md).

- **Up to ~14% of delivery** for a throttled campaign (at R≈1), **~4.6% on average**
  (averaged over the scarcity sweep `R ∈ [0.5, 2]` for a single ad); on a flat
  profile and a loose limit — 0 (no-op).
- **Never worse overall**: never-worse grid (54 configs) — 0 regressions;
  conservation intact; **money (platform revenue)** — from **+0.08%** (the
  "realistic mix" scenario: 12 ads, 9 of them capped, real `w_h` profile) to
  **+10.4%** (the "ceiling" scenario: two advertisers, the "expensive" one with a limit throttled
  at R≈1, the "cheap" one without a limit picks up the remainder — see 3.2; this is the upper bound of the effect,
  not a typical case).
- **The balancer exactly reproduced the simulation** (validation).
- **Free in terms of speed** (Δ 0 ns per ad-slot) and **safe** (flag OFF,
  `pytest tests/balancer` — 635 passed).
- Caveats: in competition an individual campaign may get slightly less (but not in total);
  the `user_frequency_limit` path (`_compute_user_ratio`) has not been migrated; the aggregate
  prod effect depends on the distribution of R across real campaigns (unknown).

---

## D. Hypothesis 1 — cumulative frequency limits (per-user)

**Question:** the daily per-user impression limit (`user_frequency_limit.d`) is applied
hour by hour independently, without subtracting what was already shown to that person earlier → the model
spreads delivery ∝ `w_h`, whereas reality is front-loaded (people use up their limit and
"drop off"). How large is the error?
Notebook: [`cumulative_freq/test_cumfreq.ipynb`](cumulative_freq/test_cumfreq.ipynb) ·
report: [`cumulative_freq/cumfreq_report.md`](cumulative_freq/cumfreq_report.md).

**Verdict: CONFIRMED** (microsimulation on janus-20260615):

- **The `TV(prop,true)` error = 7% at limit 5, up to 12% at tight 1–2** (falls to 4% at
  a loose limit of 10) — **the largest effect of all branches, above the ~5% noise.**
- **Direction:** evening hours overestimated by **+16.7%** (peak 18–23), mornings underestimated.
- **Driver:** created by a minority — ~14% of volume from users who are both spread
  across hours and exceed the limit (17.8% are active in >1 hour; at C=5, 22% exceed the limit).
- **The mechanism is confirmed by decomposition:** all of the distortion is in the "exceed + many
  hours" group (14% of volume, TV distortion **0.19**, computed as `TV(prop,true)` only
  within this group — not a contribution to the overall TV=0.070, but the shape error of this
  subgroup on its own, if it were alone), the other groups ≈0.
- **`prop` = the balancer exactly** (verified in `_compute_user_ratio`); the assumption is only in
  "reality": greedy delivery with **`P=1`** (the campaign gets an impression on every request of a
  user until their limit is exhausted) — an upper bound on the effect; in reality `P<1`
  and the limit is consumed more slowly.

> **"Confirmed" = the problem is real, not "the fix delivers a gain".** The fix's gain itself
> was measured separately — first on logs (D.1), then A/B on the balancer (D.2).

Orthogonal to fix 0 (which corrects the shape of the hourly ceiling, not the accumulation across hours).

### D.1 How much the fix actually closes the gap (gain measurement)

A separate measurement (not in the original `cumfreq_report.md`): we applied two cheap
approximations from section 1 of `frequency_accounting_improvements.md` **on logs, without touching
the balancer code**, and computed what share of the `TV(prop,true)` gap each closes
(`gap_closed = (TV(prop,true) − TV(fixed,true)) / TV(prop,true)`). Script:
[`measure_fix_gain.py`](cumulative_freq/measure_fix_gain.py), report:
[`fix_gain_report.md`](cumulative_freq/fix_gain_report.md).

| `C` | `TV(prop,true)` | **closed by B** (aggregated headroom, recommended) | **closed by A** (elastic buffer, best β) |
|----:|----:|----:|----:|
| 1 | 0.119 | 10% | **38%** |
| 2 | 0.101 | 26% | 25% |
| 3 | 0.088 | **48%** | 4% |
| 5 | 0.070 | **53%** | −40% |
| 10 | 0.044 | 50% | −180% |

- **B (aggregated `remaining` headroom, recommended)** closes **~50% of the shape gap
  at typical limits C=3–10**, but barely helps at tight C=1 (10%, and
  understates volume down to 0.78×). The remaining ~47–50% is irreducible **user
  heterogeneity** (in `true` each user spends their own personal remainder, in B —
  a shared population one; only an exact per-user LP could remove the difference, and it is
  `O(H×N×U)`, intractable).
- **A (elastic buffer)** — a mirror-image profile: good only at tight limits (C=1:
  38%, C=2: 25%), while at loose ones it **worsens** the shape (C=5: −40%, C=10: −180%), because it
  imposes a monotonic decline over the day where the real curve is only slightly
  flatter than the model's.
- **Conclusion:** approximation B closes roughly half of the "7% problem at C=5" →
  the reference for a future A/B on the balancer is **~2–4 pp** of shape accuracy (not 7–12%), and
  that is still an upper bound (P=1).

> **This reference was not confirmed.** The fix has since been deployed to the balancer and run through A/B —
> reality turned out worse, see D.2.

### D.2 A/B on the real balancer — the fix is deployed, but does not pay off

The **B-forward** fix is implemented in `seasonal/balance.py` (`_headroom_sweep` +
`_compute_user_ratios_cumulative`) behind the kw-only flag
`build_seasonal_context(..., use_cumulative_user_headroom=False)` — the fix 0 convention,
the slot loop is untouched. Spec:
`2026-07-17-hyp1-cumulative-user-headroom-design.md` (historical design note, not included) ·
harness: [`hyp1_ab_balancer.py`](cumulative_freq/hyp1_ab_balancer.py) ·
full report: [`hyp1_ab_report.md`](cumulative_freq/hyp1_ab_report.md).

**Better or worse?** Better — on a realistic profile (6 days) in all cases.
But by how much **depends on the limit tightness**. `TV` = how much the model lies in shape,
lower = better:

| daily limit | before | after | gain | result |
|---|---|---|---|---|
| **1** | 0.1345 | **0.0447** | **−9.0 pp** | **real effect** |
| **2** | 0.1116 | **0.0636** | **−4.8 pp** | **real effect** |
| 3 | 0.0965 | 0.0706 | −2.6 pp | borderline |
| 5 | 0.0765 | 0.0677 | −0.9 pp | within noise |
| 10 | 0.0470 | 0.0448 | −0.2 pp | almost nothing |

**The split by limit is the main thing.** With model noise of ~5% (branch B): tight limits 1–2 give
9.0 / 4.8 pp — **on the order of the noise and larger**, a reproducible effect; loose ones (≥5) drown
in the noise. Limits of 1–3 impressions/day are a common setting in advertising, so the question is not rhetorical.

**Why so little — day-blending.** `seasonality.py:86` does `h = ts.hour`, **dropping
the date**: `user_counts_by_hour[14][uid]` = the user's requests at 14:00 in total **across all days
of the log**. Therefore "7 requests in a single day" (the daily limit cuts hard) and "1 request seven
days in a row" (the limit never bites) are **indistinguishable** to the balancer. And the entire effect of hypothesis 1
is created precisely by burst users (group C). The longer the profile, the more it smears them:

| `C` | 1-day profile | 3 days | **6 days** |
|----:|----:|----:|----:|
| 3 | 66% | 43% | 27% |
| **5** | **58%** | **36%** | **11%** |
| 10 | 41% | 19% | 5% |

The one-day run reproduces the ~53% measured in D.1 (58%) — **the fix works exactly as
promised, but only on a one-day profile.** Prod builds profiles from weeks for the sake of a
stable `w_h` → the gain evaporates. This is a **pre-existing** limitation of the aggregate
histogram (the old `_compute_user_ratio` is blind in the same way), not something the fix introduces.

**The integration quality is perfect** (which is why we trust the numbers above):

| check | result |
|---|---|
| `TV(bal_off, prop)` / `TV(bal_on, fixed)` | ≤ 0.0001 — the balancer reproduces the simulation bit-for-bit |
| `Σon / Σoff` | **1.000×** — renormalization keeps the total volume exact |
| no-op at a loose limit, shape front-loaded | ✅ |
| `pytest tests/balancer` with OFF | **647 passed** |
| Performance | the fix **speeds things up**: 20 ads 10.95 s → 2.60 s |

The speedup is a side effect: the old path called `_compute_user_ratio` for each (ad, hour)
pair, recomputing the **hour-independent** histogram correction 24 times per
ad; the sweep is computed once.

**Fix A (elastic buffer) — deployed and rejected.** Also implemented
(`_compute_user_ratios_elastic`, flag `use_elastic_user_limit` + `elastic_beta`) and run
with a β sweep. On the 6-day profile, best β=0.5: C=1 → +50%, C=2 → +35%, C=3 → +20%,
**C=5 → −12%, C=10 → −117%** — i.e. it **strictly loses to B at every limit**
(B has: 67 / 43 / 27 / 11 / 5%) and at loose limits does **worse than nothing**. The reason:
A imposes a monotonic decline over the whole day, whereas reality is only slightly flatter than traffic.
It also requires calibrating β and loses volume (0.919× at C=10). **This also closes the hybrid idea**
"B + A for tight limits" — B wins there too.

**Next step — the decision blocker:** look at the **distribution of `user_frequency_limit.d`
across real campaigns** (a cheap check against configs):

- **1–3** dominate → fix B pays off, deploy;
- **≥5** dominate → close hypothesis 1.

Exactly the same gap as with fix 0 (where the distribution of the scarcity `R` is unknown). If the limits
turn out loose but the fix is still needed, what remains is to **extend `LogStreamState` to
`(user, day)` resolution** (day-blending disappears, ~58% returns at C=5; the cost is memory
×n_days). Both fixes sit **behind flags, default OFF** → zero impact on prod.

## How the branches relate (important not to confuse)

- **Fix 0** (branch C) and the **reach hypothesis** (branch A) are **different things**. Fix 0 is a
  deterministic correction, uses `w_h` everywhere. The hypothesis is a separate add-on:
  "should `w_h` be replaced with `reach_share` for user-cap?". The hypothesis does **not** test
  the fix; it answers "is this needed as well" → the answer is "no".
- For **`ad_frequency_limit`** (volume) `w_h` is always correct — reach is irrelevant.
- For **`user_frequency_limit`** (per user) the strictly correct weight is `reach_share`;
  `w_h` is acceptable there **only** because branch A showed a small divergence (H0-ish).

## Data: week 608 is corrupted

Independently confirmed twice (backtest guard + reach report): in `janus-20260608.parquet`
~50% of traffic is dumped into the 12:00 hour (backfill/duplicate). Its reach verdict (H1, TV 47%,
CoV 2.54) is an **artifact — disregard it**. A ticket for the log pipeline is worth filing.

---

## File index

**`fix0_freq_conversion/`** — branch C (fix 0):

- [`test_fix0_freqcap.ipynb`](fix0_freq_conversion/test_fix0_freqcap.ipynb) — simulation of the effect on a real profile
- [`fix0_ab_balancer.py`](fix0_freq_conversion/fix0_ab_balancer.py) — A/B on the real balancer
- [`fix0_ab_extended.py`](fix0_freq_conversion/fix0_ab_extended.py) — extended checks + performance
- [`fix0_effectiveness_report.md`](fix0_freq_conversion/fix0_effectiveness_report.md) — full report

**`reach_vs_volume/`** — branch A (reach vs volume):

- [`hypothesis.md`](reach_vs_volume/hypothesis.md) — statement of the hypothesis (H0/H1)
- [`check_reach_vs_volume.ipynb`](reach_vs_volume/check_reach_vs_volume.ipynb) — verification notebook (DuckDB)
- [`make_report.py`](reach_vs_volume/make_report.py) — weekly report generator
- [`reports/`](reach_vs_volume/reports) — reach reports by week (601/608/615/622)
- [`check_reach_vs_volume.py`](reach_vs_volume/check_reach_vs_volume.py), `generate_synthetic_data.py` (local artifact, not included) — early CLI/synthetic data generator

**`profile_backtest/`** — branch B:

- [`backtest_profile.ipynb`](profile_backtest/backtest_profile.ipynb) — out-of-sample profile error + data-quality guard

**`cumulative_freq/`** — branch D (hypothesis 1). Three stages: problem → gain on logs → A/B;
its own summary [`README.md`](cumulative_freq/README.md) comparing all three:

*D. Problem:*
- [`test_cumfreq.ipynb`](cumulative_freq/test_cumfreq.ipynb) — microsimulation + driver + decomposition + verdict
- [`cumfreq_report.md`](cumulative_freq/cumfreq_report.md) — full report (verdict CONFIRMED)

*D.1 Fix gain on logs (balancer untouched):*
- [`measure_fix_gain.py`](cumulative_freq/measure_fix_gain.py) — gain measurement of two approximations (B/A)
- [`fix_gain_report.md`](cumulative_freq/fix_gain_report.md) — report, raw log: `fix_gain_output.txt` (local artifact, not included)

*D.2 A/B on the real balancer:*
- [`hyp1_ab_report.md`](cumulative_freq/hyp1_ab_report.md) — **main A/B report** (starts with "better or worse")
- [`hyp1_ab_balancer.py`](cumulative_freq/hyp1_ab_balancer.py) — harness: real `build_seasonal_context` + slot loop, OFF vs ON
- [`make_ab_log.py`](cumulative_freq/make_ab_log.py) — downsample parquet → CSV (sampling **whole users**; single stream, peak RSS ~0.31 GB)

*Fix code (outside this folder):*
- `src/rtb_sdk/balancer/seasonal/balance.py` — `_headroom_sweep`, `_compute_user_ratios_cumulative`, the flag in `build_seasonal_context`
- `tests/balancer/test_cumulative_user_headroom.py` — unit tests of the sweep (12, numbers checked on paper)
- `spec` (historical design note, not included) — design, verdict rule, predicted day-blending risk
