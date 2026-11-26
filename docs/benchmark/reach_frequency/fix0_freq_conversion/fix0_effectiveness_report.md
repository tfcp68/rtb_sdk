# Fix 0: effectiveness check on the real balancer

A report on the A/B check of **fix 0** from
[`../../frequency_accounting_improvements.md`](../../../frequency_accounting_improvements.md)
(weighted freq conversion). The goal is to measure **whether** the fix improves delivery, **by how much**,
and **whether it slows down** the balancer.

> **Conclusion.** The fix is mathematically correct, behaves on the real balancer as
> predicted, **nowhere makes things worse overall**, and **practically does not slow down
> the balancer**. The effect size is **modest**: up to ~14% of delivery for a single campaign
> throttled by its limit (on average ~4.6%), and the revenue gain on a realistic set of
> campaigns ranges from fractions of a percent to ~10% in the best case. The main argument is not the size
> of the gain, but that this is a **bug fix that costs nothing and requires no
> parameter tuning**.

---

## 1. What the fix changes

**In plain words.** A campaign has a daily impression limit (a freq limit, e.g.
100,000 per day). The balancer splits it across hours. It used to divide it **equally**:
100,000 / 24 ≈ 4,166 impressions in each hour — in the evening peak and in the dead of night
alike. But traffic across hours is uneven: in the evening there are many people, at night almost none.
Because of the flat split, the campaign is **throttled in the evening** (it wants to show more than 4,166, but
cannot), and at night the "allowed" 4,166 impressions have no one to be taken from. As a result the campaign
**under-delivers its limit** over the day — not because traffic is scarce, but because of the wrong
split. The fix divides the limit **by the shape of traffic** (more in the evening, less at night), and
the shortfall disappears.

**Technically:** `compute_hour_limit` converts a daily/weekly/monthly freq limit
into an hourly ceiling. It used to be a **flat** division (`freq_d/24`), now it is **weighted**
(`freq_d·w_h`), consistent with how the balancer itself divides traffic volume across hours
(`total·w_h`). `w_h` is the share of traffic falling on an hour (the hour weight).

Implemented as the parameter `build_seasonal_context(..., use_weighted_freq_shares=False)`
(**default `False`** → zero impact on prod; `shares=None` gives byte-for-byte the old
behavior). The flag is not global: it merely controls whether
`build_seasonal_context` fills the `*_share` fields in `AdditionalContext`. Downstream,
`prepare_hour_ads` takes the weighted conversion **by the presence** of `*_share` in the context
(`'day_share' in hour_context`) — the mere presence of the shares is the signal that the fix is enabled,
so no separate flag is needed in `prepare_hour_ads`, and the functions that call it
(`balance_traffic`, `balance_by_sellout`, `add_campaign`, `predict_rebalance`) have nothing
to pass.

**Files affected:**
- `seasonal/balance.py` — `build_seasonal_context` got a kw-only parameter
  `use_weighted_freq_shares: bool = False`; when `True` it fills `day/week/month_share`.
- `seasonal/corrections.py` — `HourShares`, `compute_hour_shares`, `compute_hour_limit`;
  `prepare_hour_ads` uses `shares` by the presence of `*_share` (the global constant
  `USE_WEIGHTED_FREQ_SHARES` was removed).
- `schemas/balancer_schemas.py` — `AdditionalContext` + optional `*_share`.

The `user_frequency_limit` path (`_compute_user_ratio`) is **not migrated yet** — the fix
covers `ad_frequency_limit`.

### Glossary (to read the tables below)

- **freq limit** — a campaign's daily/weekly impression limit.
- **hour weight `w_h`** — what share of the daily traffic falls on this hour (large in the
  evening, small at night).
- **`R` (scarcity)** — how many times the traffic available to the campaign exceeds its limit.
  `R≈1` — the limit is roughly equal to the traffic (the bound really interferes, the effect is maximal);
  a large `R` — the limit is loose, the bound barely interferes (the fix changes nothing).
- **shortfall** — by how much the campaign failed to reach its limit due to the wrong split.
- **attainment** — how much the campaign actually delivered of its limit (100% = fully
  reached).
- **`TV` (Total Variation distance)** — `½·Σ_h |a_h − b_h|`: a single number 0…1
  showing how much two hourly distributions diverge (= what share of "mass"
  has to be moved between hours to turn one into the other). Here we compare the traffic
  profile `w_h` with the uniform one: `TV(w, uniform)` = how uneven the profile is
  (0 = perfectly flat). Numerically it coincides with the maximum shortfall of the old model at
  `R≈1`. We take TV rather than the worst single hour because small per-hour errors are
  systematic (morning −, evening +) and **add up**.
- **old / new** — the balancer with the old (flat) and the new (weighted) formula.
- **conservation** — the total number of impressions has not changed (the fix only redistributes
  them between campaigns/hours, it does not create them out of thin air).
- **no-harm** — the fix does not make things worse: revenue does not fall, cheap ones do not unfairly win against
  expensive ones.
- **no-op** — the fix changes nothing (on a flat profile or a loose limit).
- **infeasible slot** — an hour for which the LP has no feasible solution (an error).

---

## 2. Methodology

1. **Simulation** ([`test_fix0_freqcap.ipynb`](test_fix0_freqcap.ipynb)) on the real
   profile `w_h`: for a single freq-capped ad the balancer reduces to
   `delivered = Σ_h min(cap_h, avail_h)`. This gives an exact analytical prediction.
2. **Real balancer A/B** ([`fix0_ab_balancer.py`](fix0_ab_balancer.py),
   [`fix0_ab_extended.py`](fix0_ab_extended.py)): a run of the real
   `seasonal_balance_traffic` with `use_weighted_freq_shares` off vs on on the same inputs
   (in the harness the context is built with and without `*_share`).
3. **A verdict rule declared in advance** (so as not to move the goalposts after the fact):
   - **Better:** the shortfall of the capped ad `new ≈ 0 < old`; attainment grows.
   - **Guardrails (violation = "worse"):** the invariant (uniform → old==new); infeasible
     does not grow; Σ volume is not inflated (conservation); money does not fall.
   - **No-op:** a loose limit (large R) and a uniform profile → no change.
   - **Validation:** the balancer must reproduce the simulation.

`R = available traffic / freq_d` — the campaign's "scarcity" (the limit binds at `R ≲ 1.7`).

**Correctness regression gate:** `pytest tests/balancer` with the flag off — **635 passed**
(behavior unchanged).

---

## 3. Results

### 3.1 Validation: balancer == simulation (one ad, P=1, real profile)

| R | balancer old | balancer new | sim old | sim new | ideal |
|---|---|---|---|---|---|
| 0.75 | 72,555 | 75,001 | 72,556 | 75,000 | 75,000 |
| **1.0** | **85,875** | **99,999** | 85,883 | 100,000 | 100,000 |
| 1.5 | 95,576 | 99,999 | 95,588 | 100,000 | 100,000 |

The balancer repeats the simulation to within rounding (≤16). On the `real` profile the old
model under-delivers by **14.1%** at R≈1 (= `TV(w,uniform)`), the new one by ~0.

### 3.2 Competition of two advertisers

**The situation in plain words.** In one day 100,000 impressions are available, shared by two
advertisers:

- **"Expensive"** — pays 30 per impression, but with a daily limit of 100,000 (a freq limit).
- **"Cheap"** — pays 10, no limit; it just picks up what the expensive one did not take.

*Before:* the old limit throttles the expensive one in the evening (splits equally across hours, while in the evening there is
a lot of traffic) — it under-delivers and delivers only ~86,000 instead of 100,000. The undelivered
~14,000 evening impressions go to the cheap one.

*After:* the new limit lets the expensive one take its evening share — it delivers all
100,000, and nothing is left for the cheap one.

| Advertiser | before | after | difference |
|---|---|---|---|
| expensive (30 per impression, with limit) | 85,875 (86% of limit) | 99,999 (**100%**) | +14,124 |
| cheap (10 per impression, picks up the rest) | 14,126 | 2 | −14,124 |
| total impressions | 100,001 | 100,001 | 0 (the same) |
| **platform revenue** | 2,717,510 | 2,999,990 | **+10.4%** |

**Meaning:** those ~14,000 impressions that the old limit needlessly gave to the cheap picker-upper (because
it throttled the expensive one), the fix returns to the expensive one. The number of impressions is the same, but now they belong to
whoever pays more → revenue grows. This is the **best case** of the effect (one
throttled valuable campaign); in a real mix it is much more modest (see 3.3).

### 3.3 Extended checks

| Check | Result |
|---|---|
| **Never-worse** (3 profiles × 3 P × 6 R = 54, one ad) | 30 improved, 24 unchanged, **0 worse**, no over-delivery |
| **Small `freq_d`** (floor) | `≥48` → new≥old; at `freq_d=24/day` (1/hour, pathological) new 16 < old 17 (**−1 impression** from rounding) |
| **hour_of_week** (168 buckets) | works, new≥old (693,228 → 699,984) |
| **Realistic mix** (12 ads, 9 capped, real) | **one** capped sagged (competition); money **+0.08%**; conservation intact |
| **Aggregate** (real, R∈[0.5,2]) | mean eliminated shortfall **4.63%**, max **14.1%** (R=1) |

### 3.4 Performance (micro-benchmark in isolation)

| What | Cost |
|---|---|
| `compute_hour_limit` old vs new | **968 ns == 968 ns** (Δ 0 per ad-slot) |
| Building the shares (in `build_seasonal_context`) | 18 µs (hour_of_day) / 0.8 ms (hour_of_week), **once** per profile |
| End-to-end off vs on | within the LP solver's noise (±50%, in places "−24%" — i.e. the cost is below the variance) |

**No significant slowdown** — the fix is structurally almost free.

---

## 4. Verdict on the declared rule

| Criterion | Outcome |
|---|---|
| Better (primary): shortfall new≈0 < old; attainment 85.9%→100% | ✅ |
| Invariant: uniform → old==new | ✅ (99,984 == 99,984) |
| Conservation of Σ | ✅ |
| Infeasible did not grow | ✅ (runs without errors) |
| No-harm: money does not fall | ✅ (+0.08% … +10.4%) |
| No-op at a loose limit / uniform | ✅ |
| Balancer == simulation | ✅ (≤16 rounding) |

**The fix improves things and nowhere makes them worse overall.** One caveat to "never worse":
if there is a single campaign, it always gets no less (except ≤1 impression from rounding
at an absurdly small limit `freq_d=24/day`). If there are **many campaigns and they
compete**, an individual campaign may get slightly less (its evening volume
is taken by a more profitable competitor), but **the total impressions are the same and revenue does not
fall**. That is, there is no guarantee that "every one is no worse off" under competition — but overall things
do not get worse.

---

## 5. Limitations

- The checks were on 1–3 tags/categories; large many-category mixes were not run (except
  perf).
- **The aggregate prod effect is determined by the distribution of `R` across real campaigns**
  (how many of them are really throttled by a limit ≈ traffic) — we **do not know this without the campaign
  configs**. The dramatic +10.4% is a ceiling; the realistic aggregate is closer to fractions of a
  percent.
- `user_frequency_limit` (`_compute_user_ratio`) is not migrated — the fix covers only
  `ad_frequency_limit`.
- The profile in the harness is stylized (`TV≈0.14`, like a real week); for exact numbers
  for a specific week, substitute its `w_h`.
- If enabled in prod — the seasonal tests with exact numbers will break for uneven
  profiles (expected, they need to be updated).

---

## 6. How to reproduce

```bash
# 1. Correctness: flag off -> behavior unchanged
pytest tests/balancer            # 635 passed

# 2. Simulation on the real profile (a parquet profile is needed)
#    -> docs/benchmark/reach_frequency/fix0_freq_conversion/test_fix0_freqcap.ipynb  (Run All)

# 3. Real balancer A/B (pure Python, no parquet needed)
python docs/benchmark/reach_frequency/fix0_freq_conversion/fix0_ab_balancer.py     # scenarios A, B, invariant
python docs/benchmark/reach_frequency/fix0_freq_conversion/fix0_ab_extended.py     # never-worse, floor, hour_of_week, mix, perf
```

Flag: the parameter `build_seasonal_context(..., use_weighted_freq_shares=False)`
(default `False`). The harness builds the `seasonal_context` with `*_share` (on) and without them (off)
for each run — there is no longer any global state that has to be put back.

**Code status:** changes are in the working tree of the `balancer` branch, **not committed**, flag OFF.
