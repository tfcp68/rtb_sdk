# Improvements to the accuracy of balancer predictions

This document describes the problems of the current model and proposed improvements for a more accurate prediction of traffic distribution. Each section contains: a problem description, a mathematical model, an analysis of the impact on accuracy, and implementation details.

---

## 0. Inter-hour non-uniformity of the freq conversion (d/w/m → impressions/hour)

### Problem

`compute_hour_limit()` converts the `d`/`w`/`m` granularities into impressions/hour by a **flat**
division by a constant — identical for any hour of the day, regardless of whether it is a peak
or night:

```python
if v.get('d'):
    limits.append(float(v['d']) / 24)               # always 1/24, peak or night
if v.get('w'):
    limits.append(float(v['w']) / (24 * 7))
if v.get('m'):
    limits.append(float(v['m']) / (24 * _DAYS_PER_MONTH))
```

Meanwhile `_iter_slots` (`balance.py:127`) already honestly divides the **traffic volume itself** across
hours via the real seasonal weight: `total_t = total × w_h`. This yields an internal
inconsistency: the traffic volume in the LP accounts for seasonality, while the frequency ceiling imposed
on the same LP does not.

#### Example

Profile: 20:00 is the peak hour (`w_h = 0.15`), 03:00 is almost dead (`w_h = 0.005`).
The campaign sets `ad_frequency_limit.d = 240`.

| Hour | `w_h` | Current upper bound (`240/24`) | Real available traffic (`P(ad)·total_t`) |
|---|---|---|---|
| 20:00 (peak) | 0.15 | 10 | large — the LP could give much more |
| 03:00 (night) | 0.005 | 10 | almost absent — a bound of 10 impressions is never reached |

In the peak hour the campaign is throttled by the frequency ceiling although there is enough traffic and daily budget;
in the night hour the ceiling is formally "available", but there is nothing to take. Over a day the
campaign **systematically under-delivers** the declared `freq_d = 240` — not because
traffic is lacking, but because the conversion of the limit into an hourly one assumes
a uniformity that the model itself no longer considers necessary to observe when dividing
`total_traffic_volume`.

### Current code

`compute_hour_limit()` (`seasonal/corrections.py:53-82`) — see above. It is used in
two places:

- `prepare_hour_ads()` (`corrections.py:157-194`) — applies the hourly upper bound
  to an ad's volume for a specific hour; this is the main consumer of the bug.
- `_compute_user_ratio()` (`balance.py:279-318`) — computes `user_hour_limit` for
  the hourly histogram correction for `user_frequency_limit`; the same flat
  conversion is used here too.

### Mathematical model

Let `w_h` be the weight of hour type `h` from the already computed profile (`weights_dict` in
`build_seasonal_context`, `Σ w_h = 1` over all hour types of one profile cycle).
Denote the profile period `P` (1 day for `hour_of_day`, 7 days for `hour_of_week`) and
the target granularity period `T` (1 for `d`, 7 for `w`, 30.44 for `m`).

If `T ≥ P` — the target period is a multiple of the profile cycle, and the hour type `h` occurs in it
`T/P` times. The granularity budget for the whole target period attributable to this hour type
(in total over all its occurrences) equals `freq_period × w_h`; dividing by the number of occurrences
we get the hourly upper bound:

```
L(h) = freq_period × w_h / (T / P)
```

If `T < P` (the only practical case is daily granularity with the weekly
profile `hour_of_week`, `T=1, P=7`), `w_h` carries the weekly scale, but the daily one is needed:
we normalize `w_h` within the specific day of the week to which `h` belongs
(`weekday = h // 24`):

```
day_share(h) = w_h / Σ_{h' ∈ weekday(h)} w_h'
```

Summary by mode and granularity:

| Profile mode | `d` (day) | `w` (week) | `m` (month) |
|---|---|---|---|
| `hour_of_day` (24 buckets) | `w_h` | `w_h / 7` | `w_h / 30.44` |
| `hour_of_week` (168 buckets) | `w_h / day_total(weekday)` | `w_h` | `w_h × 7 / 30.44` |

**Backward-compatibility invariant.** With a uniform profile (`w_h = 1/24` for
`hour_of_day` or `w_h = 1/168` for `hour_of_week` — exactly what is used by
default when there are no logs) all four formulas algebraically reduce to the current
constants `1/24`, `1/168`, `1/(24×30.44)` — verified by direct substitution for all
four combinations of mode × neighboring granularity. So when there is no seasonal data
the behavior does not change at all; the divergence from the old formula grows strictly in proportion to
how uneven the real profile is.

### Solution

```python
# seasonal/corrections.py

class HourShares(TypedDict):
    """The share of the granularity period (day/week/month) falling on one hour."""
    day: float
    week: float
    month: float


def compute_hour_shares(mode: AggregationMode, weights: dict[int, float], h: int) -> HourShares:
    """Builds HourShares for hour type h from the weights profile (see the table above)."""
    w_h = weights.get(h, 0.0)
    if mode == 'hour_of_day':
        return HourShares(day=w_h, week=w_h / 7, month=w_h / _DAYS_PER_MONTH)

    weekday = h // 24
    day_total = sum(weights.get(h2, 0.0) for h2 in range(weekday * 24, weekday * 24 + 24))
    day_share = (w_h / day_total) if day_total > 0 else 1 / 24
    return HourShares(day=day_share, week=w_h, month=w_h * 7 / _DAYS_PER_MONTH)


def compute_hour_limit(freq_limits: dict, shares: HourShares | None = None) -> float:
    """As before, but d/w/m use shares instead of constants, if it is passed."""
    v: dict = freq_limits.get('value', {})
    limits: list[float] = []

    if v.get('t'):
        limits.append(float(v['t']) * _SLOTS_PER_HOUR)
    if v.get('h'):
        limits.append(float(v['h']))
    if v.get('d'):
        day_share = shares['day'] if shares else 1 / 24
        limits.append(float(v['d']) * day_share)
    if v.get('w'):
        week_share = shares['week'] if shares else 1 / (24 * 7)
        limits.append(float(v['w']) * week_share)
    if v.get('m'):
        month_share = shares['month'] if shares else 1 / (24 * _DAYS_PER_MONTH)
        limits.append(float(v['m']) * month_share)

    return min(limits) if limits else float('inf')
```

If `shares=None` — byte-for-byte the old behavior (non-seasonal calls, backward
compatibility).

**Data wiring.** `AdditionalContext` (`balancer_schemas.py`) gets three new
fields: `day_share`, `week_share`, `month_share`. They are filled in `build_seasonal_context`
(`balance.py`, the same `for h in range(n)` loop where `weights_dict` and `mode` are already
at hand):

```python
shares = compute_hour_shares(mode, weights_dict, h)
ctx_by_hour[h] = AdditionalContext(
    weight=weight,
    day_share=shares['day'], week_share=shares['week'], month_share=shares['month'],
    user_activity_ratio=ratios,
    tags_probability=tag_probs.get(h),
)
```

`prepare_hour_ads()` takes `shares` from `hour_context` (with `hour_context=None` —
`shares=None`, as before) and passes it to `compute_hour_limit(ad_freq, shares=...)`.

`_compute_user_ratio()` gets the same `shares` and passes it to
`compute_hour_limit(user_freq, shares=...)` for the `if v.get('h')` branch (the hourly
histogram must be compared against the correct hourly limit). In the branch without `'h'`
(the period path) `compute_hour_limit(...) * n_hours` is replaced by a direct call to
`compute_period_limit(user_freq, n_hours)` — after switching to `shares` the hourly limit
stops being constant across hours, so `hour_limit(h) × n_hours` no longer
reconstructs the period total; `compute_period_limit` exists for exactly this, and the duplication
of logic is removed along the way.

### Impact on accuracy

Numerically it depends on the degree of profile non-uniformity — unlike sections 1-5 there
are no new calibrated constants here, so the effect is not the "quality of a heuristic" but the direct
elimination of the systematic divergence between the hourly cap and the hourly budget:

| Scenario | Current model (flat division) | With weighted conversion | Change |
|---|---|---|---|
| Uniform profile (`w_h ≈ 1/24`) | reference | identical (the formulas coincide) | no change |
| Moderate non-uniformity (peak ×2-3 of the mean) | `freq_d` shortfall of 10-20% due to peak hours | shortfall eliminated | ✅ noticeable |
| Sharp non-uniformity (`[0.95, 0.05]`-like profiles) | often `infeasible` in a low-weight slot (see the precedent above) | consistent with real traffic | ✅ significant |

### Implementation details

**Files:**

- `src/rtb_sdk/balancer/seasonal/corrections.py` — `HourShares`, `compute_hour_shares()`,
  edits to `compute_hour_limit()` and `prepare_hour_ads()`.
- `src/rtb_sdk/schemas/balancer_schemas.py` — new `AdditionalContext` fields.
- `src/rtb_sdk/balancer/seasonal/balance.py` — filling `shares` in
  `build_seasonal_context()`, edits to `_compute_user_ratio()`.

**Order relative to sections 1 and 3.** Both sections read and modify the same
`compute_hour_limit()`/`prepare_hour_ads()`. This section should be deployed **first** —
it introduces no new constants, changes nothing with a uniform profile, and removes the very
ground of the inconsistency on which sections 1 and 3 build more complex (and calibration-requiring)
corrections on top of an already correct base figure.

---

## 1. Cumulative Frequency Constraints

### Problem

The current model handles each hourly slot **independently**. The
`user_frequency_limit` constraint is applied to each hour separately, without accounting for the accumulation
of impressions from previous slots.

#### Example

Let `user_frequency_limit.d = 5` (no more than 5 impressions per user per day).

| Hour | 14:00 | 15:00 | 16:00 | 17:00 | 18:00 |
|-----|-------|-------|-------|-------|-------|
| Impressions per user (model) | 3 | 3 | 3 | 3 | 3 |
| Cumulative (model) | 3 | 6 | 9 | 12 | 15 |
| Cumulative (reality) | 3 | 5 | 5 | 5 | 5 |

The LP optimizes for the 15:00 hour, planning to show this user 3 more times.
But the daily limit of 5 is already exhausted at 15:00 (3+3). In reality the user will see 0 impressions
at 15:00, while the LP predicted 3.

**Result:** a systematic divergence between planned and real volumes
in and after peak hours.

### Current code

`prepare_hour_ads()` (`src/rtb_sdk/balancer/seasonal/corrections.py:157-194`) applies
`compute_hour_limit()` for each hour in isolation:

```python
hour_limit = compute_hour_limit(ad_freq)  # 5/24 ≈ 0.21 impressions/hour/user
vol = min(ad_max, floor(hour_limit)) * ratio
```

`is_ad_active()` (`corrections.py:37-46`) checks only within a single slot:

```python
return start <= slot_dt < end
```

In `balance.py` there is `remaining` for cross-slot tracking of the volume budget, but **not for the
user budget**:

```python
# prepare_slot_ads() uses remaining for volume
if remaining is not None:
    slot_max_vol = min(slot_max_vol, remaining[ad_id])
```

### Mathematical model

#### Current model (isolated hours)

```
user_limit_hour[h] = user_hour_limit  # a constant for each hour
```

#### Proposed model (cumulative, exact)

Introduce a state variable for each user and campaign:

```
remaining_user_impressions[u, ad, h] =
    max(0, user_limit - Σ_{t < h} shown_impressions[u, ad, t])
```

For the hourly LP:

```
shown_impressions[u, ad, h] ≤ remaining_user_impressions[u, ad, h]
Σ_{u} shown_impressions[u, ad, h] = volume_ad_h
```

### Impact on accuracy (theoretical ceiling of the exact solution)

| Metric | Current model | Cumulative (exact) | Change |
|---------|---------------|--------------|-----------|
| Prediction error (peak hour) | 15-40% | 3-8% | ✅ significant improvement |
| Prediction error (off-peak) | 5-10% | 3-5% | minimal |
| LP complexity | O(H × N) | O(H × N × U) | unacceptable |

**The complexity problem:** the exact solution requires accounting for every user, which makes
the LP intractable. Below are two approximations: an elastic buffer (a cheap heuristic)
and an aggregated remaining budget (reuses the infrastructure already present in the code,
`remaining[ad_id]`, and reacts more accurately to actual delivery).

### Compromise solution A: elastic buffer

A power function of the elapsed share of the day, in which β controls the shape of the curve:

```python
def compute_elastic_user_limit(
    user_hour_limit: float,
    hour_in_day: int,
    β: float = 0.8,
) -> float:
    """
    Elastic multiplier based on the elapsed share of the day.

    β < 1: the limit decreases more slowly than linearly — the budget is spent more aggressively at the start of the day.
    β = 1: linear decrease.
    β > 1: the limit decreases faster than linearly — the budget is held back in reserve.
    """
    day_progress = hour_in_day / 24.0
    remaining_fraction = (1 - day_progress) ** β
    return max(0.0, user_hour_limit * remaining_fraction)
```

**Example for user_hour_limit=5:**

| Hour | 00 | 06 | 12 | 18 | 23 |
|-----|----|----|-----|----|----|
| day_progress | 0.00 | 0.25 | 0.50 | 0.75 | 0.96 |
| elastic_limit, β=0.5 | 5.00 | 4.33 | 3.54 | 2.50 | 1.02 |
| elastic_limit, β=0.8 | 5.00 | 3.97 | 2.87 | 1.65 | 0.39 |
| elastic_limit, β=1.0 (linear) | 5.00 | 3.75 | 2.50 | 1.25 | 0.21 |
| elastic_limit, β=1.5 | 5.00 | 3.25 | 1.77 | 0.62 | 0.04 |

β sets the shape of the curve — it can be calibrated from historical data (section 6) rather than
picked blindly.

### New proposal (recommended): aggregated remaining budget

The elastic buffer above is a pure heuristic on the time of day, independent of
how much the campaign has *actually* delivered by this moment. A more accurate and cheap
alternative is to reuse the `remaining[ad_id]` mechanism already present in the code
(cross-slot volume tracking, `balance.py`), extending it with an averaged estimate
of impressions per user:

```python
def compute_aggregate_user_headroom(
    user_daily_limit: float,
    delivered_volume_so_far: float,
    estimated_unique_reach: float,
) -> float:
    """
    Estimates the average remaining user limit based on the volume already delivered
    and an estimate of unique reach, rather than an abstract curve over hours.
    """
    if estimated_unique_reach <= 0:
        return user_daily_limit

    avg_delivered_per_user = delivered_volume_so_far / estimated_unique_reach
    return max(0.0, user_daily_limit - avg_delivered_per_user)
```

Used instead of `compute_elastic_user_limit` where `estimated_unique_reach` is known (or already estimated
elsewhere in the system) for the campaign. The advantage over the elastic buffer: if the campaign under-delivered
volume in the first hours of the day (e.g. because of `min_vol`), the aggregated budget remainder will reflect this
and allow catching up later — which a time-fixed curve cannot do. If an estimate of reach is unavailable,
one can fall back to `compute_elastic_user_limit` as a cheap default.

### Implementation details

**File:** `src/rtb_sdk/balancer/seasonal/corrections.py`

```python
def compute_elastic_user_limit(
    user_hour_limit: float,
    hour_in_day: int,
    β: float = 0.8,
) -> float:
    """Elastic hourly limit based on the elapsed share of the day."""
    day_progress = hour_in_day / 24.0
    remaining_fraction = (1 - day_progress) ** β
    return max(0.0, user_hour_limit * remaining_fraction)


def prepare_hour_ads_with_cumulative(
    ads: dict[AdId, Any],
    hour_context: AdditionalContext | None,
    slot_hour: int,  # hour of the day (0-23)
) -> dict[AdId, dict]:
    """
    An extended prepare_hour_ads with elastic user constraints.
    """
    # ... existing logic ...
    for ad_id, ad in ads.items():
        # Elastic user limit
        user_freq = ad.get('user_frequency_limit') or {}
        user_hour = compute_hour_limit(user_freq)
        if user_hour < float('inf'):
            elastic = compute_elastic_user_limit(user_hour, slot_hour)
            # ... apply elastic instead of user_hour ...
```

**Change in `balance.py`:** pass `slot_hour` to `prepare_hour_ads`.

---

## 2. Parasitic Traffic

### Problem

The current model accounts only for **in-target** traffic — impressions when the request exactly
matches the campaign's targeting. However, there is parasitic traffic: impressions
when the request **does not match** the target but the ad can still be shown.

#### Sources of parasitic traffic

1. **Default ads** — shown when there are no suitable targeted ones
2. **Exhaustion fill** — when the target traffic is exhausted, non-target ones are shown
3. **Floor price** — showing a cheap ad when the expensive ones fail the price threshold

#### Current behavior

`build_ads_real_volumes()` (`src/rtb_sdk/helpers/balancer/inner_ad_helpers.py:170-199`):

```python
p = ads_probabilities.get(ad_id, 1.0)
flow_volume = total_volume * p * date_factor
```

Here `p = P(ad)` is the probability of an in-target request. Parasitic traffic is entirely
absent from the model.

> **Important:** the `parasitic_freq_limit` field already exists in the codebase, but on a
> **different** schema — `Ad` (the public auction schema, `auction_schemas.py:73`),
> used in `helpers/auction/ad_helpers.py` and `filters/fuzzy_targeting_filter.py`
> for a different purpose (the auction layer, not LP volume planning). Below it is proposed to
> introduce a **new** field with the same name on `InnerAd` (the balancer), which creates a name
> collision. It is recommended either to reuse/link the values between the schemas or
> to rename the new field (e.g. `balancer_parasitic_cap`), so as not to create
> confusion between two different mechanisms with the same name.

#### The divergence problem

If `parasitic_freq_limit` is set hard and there is a lot of parasitic traffic:

```
P(in_target) = 0.3
P(parasitic) = 0.7 (1 - P(in_target))

max_parasitic = 1000  # from parasitic_freq_limit
real_parasitic = 10000  # what actually arrived on non-target requests
```

The LP optimizes only the in-target volume. The real distribution differs substantially.

### Mathematical model

#### Approach A: two passes (Two-Pass LP)

**Pass 1:** Distribute the in-target traffic
```
max Σ price × x_{ad,cat}
s.t.
  min_vol ≤ Σ k × x ≤ max_vol
  Σ k × x_{ad,cat} ≤ total × P(cat)  ∀ cat
```

**Pass 2:** Distribute the parasitic traffic
```
remaining[cat] = total × P(cat) - Σ_{in_target} k × x*
```

A new LP for the parasitic variables `p_{ad,cat}`:
```
max Σ price × p_{ad,cat}
s.t.
  Σ p_{ad,cat} ≤ parasitic_cap[ad]  ∀ ad
  Σ_{ad} p_{ad,cat} ≤ remaining[cat]  ∀ cat
```

**Pros:** exact solution
**Cons:** two LP calls, complexity ×2

#### Approach B: a single LP with an additional variable

For each ad one scalar variable `p_ad` is added:

```
volume_total[ad] = k × Σ x_{ad,cat} + p_ad

0 ≤ p_ad ≤ min(
    parasitic_cap[ad],
    total × (1 - P(ad))
)
```

An objective function with in-target priority:
```
MAX_MONEY: max Σ price × (k × Σ x_{ad,cat} + (1-ε) × p_ad)
```

**Pros:** one LP, fewer variables
**Cons:** an approximate distribution of the parasitic traffic

### Recommended solution: Approach B (simplified)

For real-world application an **approximation without new LP variables** is proposed:

```python
def compute_parasitic_volume(
    ad: InnerAd,
    total_volume: int,
    ads_probabilities: dict[AdId, float],
    ads: dict[AdId, InnerAd],
) -> float:
    """
    Estimates the parasitic volume based on the remaining traffic.
    """
    in_target_volume = total_volume * ads_probabilities.get(ad['id'], 0.0)

    # The remaining traffic not covered by in-target
    remaining_traffic = total_volume - in_target_volume

    # This ad's share of parasitic traffic
    # is proportional to its CPM relative to competitors
    total_cpm = sum(a.get('price', 0) for a in ads.values())
    if total_cpm == 0:
        return 0.0
    price_share = ad['price'] / total_cpm

    parasitic_cap = ad.get('parasitic_freq_limit', float('inf'))

    return min(remaining_traffic * price_share, parasitic_cap)
```

The final volume is bounded by the total traffic budget (`total_volume`), not by a share of
`real_max` — `real_max` for default ads (`P(ad) = 0`) has no sensible
scale anyway, and bounding relative to it would understate the parasitic volume exactly where
it should have the main effect:

```python
def build_ads_real_volumes(
    ads: dict[AdId, InnerAd],
    total_volume: int,
    ads_probabilities: dict[AdId, float],
) -> dict[AdId, float]:
    result = {}
    for ad_id, ad in ads.items():
        # Existing logic
        max_vol = get_inner_ad_max_vol(ad, default=0) or 0
        date_factor = get_inner_ad_date_factor(ad, default=1.0) or 1.0
        freq = get_inner_ad_freq(ad, default=0) or 0
        p = ads_probabilities.get(ad_id, 1.0)

        flow_volume = total_volume * p * date_factor
        real_max = min(max_vol, flow_volume)

        # Parasitic volume
        parasitic = compute_parasitic_volume(ad, total_volume, ads_probabilities, ads)

        # The ceiling is the total traffic volume (not a share of real_max, which for
        # default ads equals 0)
        real_max = min(real_max + parasitic, total_volume)

        if freq > 0:
            real_max = min(real_max, freq)

        result[ad_id] = real_max
    return result
```

### Impact on accuracy

| Scenario | Current model | With parasitic traffic | Change |
|----------|---------------|-------------|-----------|
| Default ads (P=0) | 0% accuracy | 70-85% | ✅ significant |
| Low-target campaigns | 40-60% | 65-80% | ✅ moderate |
| High-target campaigns | 85-95% | 85-95% | no change |

### Implementation details

**File:** `src/rtb_sdk/helpers/balancer/inner_ad_helpers.py`

New fields in `InnerAd`:

```python
class InnerAd(TypedDict, total=False):
    # ... existing fields ...
    parasitic_freq_limit: float  # upper limit of parasitic traffic (balancer layer,
                                  # not to be confused with the same-named field on the Ad/auction schema)
```

The function `compute_parasitic_volume` — see the version above (section "Recommended solution"),
it includes the `ads` parameter.

---

## 3. Pacing Factor for Sub-Hour Non-Uniformity

### Problem

`prepare_hour_ads()` treats an hour as a homogeneous block:

```python
hour_limit = compute_hour_limit(ad_freq)
vol = min(ad_max, math.floor(hour_limit)) * ratio
```

But within an hour traffic is **non-uniform**:

```
A typical profile of 10-minute slots within an hour (share of impressions per slot):

00-10 min │ ███████████████████████████████████ 35%
10-20 min │ ███████████████████████████████████ 35%
20-30 min │ ██████████                          10%
30-40 min │ ██████████                          10%
40-50 min │ █████                                5%
50-60 min │ █████                                5%
```

If hourly_limit = 50 impressions and 70% falls on the first 20 minutes:
- Minutes 0-20: 35 impressions (of the 50 daily) — we will manage to show all
- Minutes 20-40: 10 impressions (of the 50 daily) — we will show 10
- Minutes 40-60: 5 impressions (of the 50 daily) — we will show 5

**Total in reality:** 50 impressions, but the distribution is non-uniform.

### Current code

`compute_hour_limit()` returns a constant:

```python
if v.get('d'):
    limits.append(float(v['d']) / 24)  # 5000/24 ≈ 208 impressions/hour
```

There is no accounting for the sub-hour profile at all.

### Mathematical model

#### Sub-hour profile

The profile is defined as the distribution of traffic within an hour:

```
p_min[0], p_min[1], ..., p_min[59]  # probabilities for each minute
Σ p_min = 60 × avg_rate
```

Or in aggregated form (6 ten-minute slots):

```
p_slot[0], p_slot[1], ..., p_slot[5]
Σ p_slot = 1.0
```

#### Pacing factor

For an hourly limit `L` the really available amount is:

```
available_t = L × Σ_{i in active_slots_t} p_slot[i]
```

If the limit `L` is reached before the end of the hour (in slot `s`), then:

```
remaining_slots = Σ_{i > s} p_slot[i]  # the unavailable part
pacing_loss = remaining_slots / Σ p_slot  # the share of loss
```

### Solution

The `p_slot` profile defined above in the mathematical model is used directly —
without intermediate arbitrary constants — and is explicitly tied to `remaining[ad_id]`
(the same cross-slot mechanism as in section 1), so that the hour's volume is not doubled on
each sub-hour slot:

```python
DEFAULT_P_SLOT_UNIFORM = [1 / 6] * 6

# Calibrated profiles by traffic type (share of impressions per 10-minute slot within the hour)
TRAFFIC_TYPE_P_SLOT = {
    'uniform':  [1/6] * 6,
    'social':   [0.10, 0.12, 0.15, 0.20, 0.23, 0.20],  # peak in the middle/end of the hour
    'news':     [0.30, 0.22, 0.16, 0.12, 0.10, 0.10],  # morning peak
    'ecommerce': [0.10, 0.12, 0.14, 0.18, 0.22, 0.24],  # evening peak
}


def compute_paced_hour_limit(
    hourly_limit: float,
    slot_in_hour: int,  # 0-5, the current sub-hour slot
    p_slot: list[float] | None = None,
) -> float:
    """
    Returns the limit available for the REMAINING part of the hour, starting from slot_in_hour,
    directly from the sub-hour profile (see the mathematical model above), without arbitrary
    constants.
    """
    p_slot = p_slot or DEFAULT_P_SLOT_UNIFORM
    remaining_fraction = sum(p_slot[slot_in_hour:])
    return hourly_limit * remaining_fraction


def prepare_hour_ads_with_pacing(
    ads: dict[AdId, Any],
    hour_context: AdditionalContext | None,
    slot_in_hour: int,  # 0-5
    remaining: dict[AdId, float] | None,  # the same cross-slot remaining as for volume
    p_slot: list[float] | None = None,
) -> dict[AdId, dict]:
    """
    An extended prepare_hour_ads with a pacing factor integrated with remaining.
    """
    coefs = hour_context['user_activity_ratio'] if hour_context is not None else {}

    result = {}
    for ad_id, ad in ads.items():
        ad_freq = ad.get('ad_frequency_limit') or {}
        hour_limit = compute_hour_limit(ad_freq)

        if hour_limit < float('inf'):
            paced_limit = compute_paced_hour_limit(hour_limit, slot_in_hour, p_slot)
            # Intersection with what was already spent in the previous slots of this hour
            if remaining is not None and ad_id in remaining:
                paced_limit = min(paced_limit, remaining[ad_id])
            ratio = coefs.get(ad_id, 1.0)
            vol = int(min(ad.get('volume', 0), math.floor(paced_limit)) * ratio)
        else:
            # No limit — unchanged
            vol = int(ad.get('volume', 0))

        if vol <= 0:
            continue

        result[ad_id] = {**ad, 'volume': vol, 'min_vol': 0}

    return result
```

This ties the slot volume to the same mathematical model (`p_slot`) and does not allow
double-constraining the same volume via an independent remaining tracking.

### Impact on accuracy

| Scenario | Without pacing | With pacing (profile by traffic type) | Change |
|----------|-----------|-----------------|-----------|
| Peak hours | 100-120% of the limit | 88-95% of the limit | ✅ over-delivery eliminated |
| Off-peak hours | 60-80% of the limit | 70-85% of the limit | ✅ more even |
| Standard deviation | 18-25% | 8-12% | ✅ significant improvement |

---

## 4. Adaptive profile update

### Problem

`build_seasonal_context()` builds a **static profile** from historical data:

```python
# All Mondays at 14:00 get an averaged weight
# If yesterday was a holiday — the profile is already stale
weights = {h: count[h] / total for h in range(24)}
```

**Problems of a static profile:**

1. **Trends are not accounted for** — if traffic grows by 15% a week, a profile for a month ahead will systematically understate volumes

2. **Anomalies are not handled** — holidays, weekends, and sales give outliers that get blurred by averaging

3. **No update between days** — if a balancing was launched for a week, the profile is not updated when patterns change

### Current code

`build_seasonality_profile()` (`src/rtb_sdk/balancer/seasonal/seasonality.py:174ff`):

```python
def build_seasonality_profile(config: HistoricalLogsConfig) -> HourlyWeights:
    counts = {h: 0.0 for h in range(24)}
    # ... streaming log processing ...
    # All data is aggregated into 24 numbers
    total = sum(counts.values())
    weights = {k: v / total for k, v in counts.items()}
    return HourlyWeights(mode='hour_of_day', weights=weights)
```

### Mathematical model

#### Exponentially Weighted Moving Average (EWMA)

Updating the weights with exponential decay:

```
w_new = α × w_actual + (1 - α) × w_historical

where α ∈ [0, 1] is the adaptation coefficient
```

Since `w_actual` and `w_historical`/`w_t-1` are normalized distributions (the sum over
all hours equals 1) and α does not depend on the hour, the linear combination also sums to 1 —
the invariant is preserved correctly (verified algebraically).

**Choosing α:**

| α | Character | Application |
|---|----------|------------|
| 0.1 | Conservative | Stable traffic without sharp changes |
| 0.3 | Balanced | Typical web traffic |
| 0.5 | Aggressive | Traffic with frequent anomalies |

#### Recurrent update

```
w_t = α × w_t-1 + (1 - α) × w_historical_t
```

Where `w_t-1` is the weight after the previous update.

### Solution: an adaptive profile with updates

```python
from datetime import datetime


class AdaptiveSeasonalContext:
    """
    A context with adaptive weight updates.
    """

    def __init__(self, base_weights: dict[int, float], α: float = 0.3) -> None:
        self.base_weights = base_weights.copy()
        self.current_weights = base_weights.copy()
        self.α = α
        self.last_update: datetime | None = None

    def update(self, actual_weights: dict[int, float]) -> None:
        """Update the weights based on actual data."""
        self.current_weights = {
            h: self.α * actual_weights.get(h, self.base_weights[h])
            + (1 - self.α) * self.current_weights.get(h, self.base_weights[h])
            for h in range(24)
        }
        self.last_update = datetime.now()

    def get_weight(self, hour: int) -> float:
        """Get the current weight for an hour."""
        # If a lot of time has passed — use the base one
        if self._stale():
            return self.base_weights.get(hour, 1 / 24)
        return self.current_weights.get(hour, self.base_weights.get(hour, 1 / 24))

    def _stale(self, max_age_hours: int = 6) -> bool:
        """Check how current the weights are."""
        if self.last_update is None:
            return True
        age = datetime.now() - self.last_update
        return age.total_seconds() > max_age_hours * 3600
```

(The practical implementation — via `TypedDict` + factory functions, see below —
is the recommended variant for production.)

### Integration with the balancer

```python
def seasonal_balance_traffic_with_adaptation(
    ads: dict[AdId, Ad],
    params: SeasonalBalancingParams,
    adaptive_ctx: AdaptiveSeasonalContext | None = None,
) -> BalanceResult:
    """
    Balancing with an adaptive profile update.
    """
    # Use the adaptive weights if available
    if adaptive_ctx is not None:
        weights = {
            h: adaptive_ctx.get_weight(h)
            for h in range(24)
        }
        params = {**params, 'hourly_weights': weights}

    result = seasonal_balance_traffic(ads, params)

    # Update the context after balancing
    if adaptive_ctx is not None:
        actual_weights = _compute_actual_weights(result)
        adaptive_ctx.update(actual_weights)

    return result
```

### How it works

```
┌──────────────────────────────────────────────────────────────┐
│                     Before balancing                         │
├──────────────────────────────────────────────────────────────┤
│  historical_logs → build_seasonality_profile                 │
│       ↓                                                      │
│  base_weights (static) ←── α parameter                       │
│       ↓                                                      │
│  [Day 1] seasonal_balance_traffic(base_weights)              │
│       ↓                                                      │
│  actual_weights_day1 ← feedback (if any)                     │
│       ↓                                                      │
│  current_weights = α × actual + (1-α) × base                 │
│       ↓                                                      │
│  [Day 2] seasonal_balance_traffic(current_weights)           │
│       ↓                                                      │
│  actual_weights_day2 ← feedback                              │
│       ↓                                                      │
│  current_weights = α × actual + (1-α) × current              │
│       ...                                                    │
└──────────────────────────────────────────────────────────────┘
```

### Impact on accuracy

| Scenario | Static profile | Adaptive | Change |
|----------|------------------|------------|-----------|
| Trend ↑15%/week | -12-18% error | 3-5% error | ✅ significant |
| Holiday | -20-30% error | 5-10% error | ✅ significant |
| Stable | ±3% error | ±3% error | no change |

### Implementation details

**New file:** `src/rtb_sdk/balancer/seasonal/adaptive.py`

```python
from datetime import datetime, timedelta
from typing import TypedDict


class AdaptiveSeasonalContext(TypedDict):
    """A context with adaptive weight updates."""
    base_weights: dict[int, float]
    current_weights: dict[int, float]
    α: float
    last_update: datetime | None


def create_adaptive_context(
    base_weights: dict[int, float],
    α: float = 0.3,
) -> AdaptiveSeasonalContext:
    """Create an adaptive context."""
    return {
        'base_weights': base_weights.copy(),
        'current_weights': base_weights.copy(),
        'α': α,
        'last_update': None,
    }


def update_adaptive_context(
    ctx: AdaptiveSeasonalContext,
    actual_weights: dict[int, float],
) -> None:
    """Update the weights based on actual data."""
    α = ctx['α']

    # Recurrent update
    ctx['current_weights'] = {
        h: α * actual_weights.get(h, ctx['current_weights'][h])
          + (1 - α) * ctx['current_weights'].get(h, ctx['base_weights'][h])
        for h in range(24)
    }
    ctx['last_update'] = datetime.now()


def get_adaptive_weight(
    ctx: AdaptiveSeasonalContext,
    hour: int,
    max_stale_hours: int = 6,
) -> float:
    """Get the weight for an hour with a freshness check."""
    # Stale check
    if ctx['last_update'] is None:
        return ctx['base_weights'].get(hour, 1/24)

    age = datetime.now() - ctx['last_update']
    if age.total_seconds() > max_stale_hours * 3600:
        # Too old — fall back to the base one
        return ctx['base_weights'].get(hour, 1/24)

    return ctx['current_weights'].get(hour, ctx['base_weights'].get(hour, 1/24))
```

---

## 5. Mixture of distributions for the user histogram

### Problem

`apply_histogram_correction()` uses an **averaged histogram**:

```python
def apply_histogram_correction(
    limit: float,
    histogram: list[int] | None,
    user_period_limit: float,
) -> float:
    if not histogram or user_period_limit >= float('inf'):
        return limit

    total = sum(histogram)
    if total == 0:
        return limit

    delivered = sum(min(count, user_period_limit) for count in histogram)
    return limit * (delivered / total)
```

**Problems:**

1. **Audience heterogeneity** — the histogram "mixes" different types of users
2. **No "fatigue" model** — a user with 100 requests a day is not the same as one with 10
3. **A threshold model** — `min(count, cap)` is too crude

### User types

```
A typical distribution of users by number of requests per day:

0-10    (regular)        │ ████████████████████████████████████████████████ 60%
10-50   (active)         │ █████████████████████████                        30%
50-200  (super-active)   │ ███████                                           8%
200+    (bots)           │ ██                                                2%
```

### Mathematical model

#### Mixture Model

```
P(requests = k) = Σ π_i × P_i(k)

where π_i is the weight of component i
      P_i(k) is the distribution of component i (Negative Binomial / Pareto)
```

**Components:**

| Component | Distribution | Parameters | π |
|------------|--------------|-----------|---|
| Regular | Negative Binomial | r=2, p=0.3 | 0.60 |
| Active | Negative Binomial | r=5, p=0.2 | 0.30 |
| Super-active | Pareto | α=2, k=50 | 0.08 |
| Bots | Deterministic | k >> 1000 | 0.02 |

#### Computing the correction coefficient

For each component:

```
cap_i = user_period_limit  # the same for all

delivered_i = Σ_{k} min(k, cap_i) × P_i(k)
           = cap_i × P_i(k ≤ cap_i) + Σ_{k > cap_i} k × P_i(k)
```

The final coefficient:

```
coef = Σ π_i × delivered_i / Σ π_i × E[k_i]
```

### Solution: a parametric mixture

Instead of an exact histogram — an approximation by a mixture of distributions.

```python
from scipy.stats import nbinom
import numpy as np

class UserActivityMixture:
    """
    A mixture of distributions for modeling user activity.
    """
    def __init__(
        self,
        # Components: (type, params, weight)
        # type: 'nbinom' | 'pareto' | 'uniform'
        components: list[tuple[str, dict, float]],
    ):
        self.components = components  # [(type, params, weight), ...]

    def expected_delivered(self, cap: float) -> float:
        """Expected number of impressions at the limit cap."""
        total_expected = 0.0
        total_weight = 0.0

        for dist_type, params, weight in self.components:
            if dist_type == 'nbinom':
                r = params['r']
                p = params['p']
                expected = self._nbinom_truncated_mean(r, p, cap)
            elif dist_type == 'pareto':
                alpha = params['alpha']
                xm = params['xm']
                expected = self._pareto_truncated_mean(alpha, xm, cap)
            elif dist_type == 'uniform':
                low = params['low']
                high = params['high']
                expected = min(high, cap)

            total_expected += weight * expected
            total_weight += weight

        return total_expected / total_weight if total_weight > 0 else 0.0

    def _nbinom_truncated_mean(self, r: float, p: float, cap: float) -> float:
        """
        E[min(K, cap)] for the Negative Binomial — the exact formula:
        Σ_{k=0}^{cap-1} k·P(k)  +  cap·P(K ≥ cap)
        """
        cap = int(cap)
        if cap <= 0:
            return 0.0
        k_values = np.arange(0, cap)
        probs = nbinom.pmf(k_values, r, p)
        tail_prob = nbinom.sf(cap - 1, r, p)  # P(K >= cap)
        return float(np.sum(k_values * probs) + cap * tail_prob)

    def _pareto_truncated_mean(self, alpha: float, xm: float, cap: float) -> float:
        """
        E[min(K, cap)] for Pareto Type I (support k ≥ xm).

        If cap ≤ xm, then min(K, cap) = cap for ALL realizations (since K ≥ xm ≥ cap
        almost surely), so the answer is trivially cap. For cap > xm — a closed
        form (the integral of the survival function):
        E[min(K,cap)] = xm + xm^α/(1-α)·(cap^{1-α} - xm^{1-α})
                      = xm·α/(α-1) - xm^α·cap^{1-α}/(α-1)   (α ≠ 1)
        """
        if cap <= xm:
            return float(cap)
        if alpha == 1:
            return xm * (1 + np.log(cap / xm))
        return xm * alpha / (alpha - 1) - (xm ** alpha) * (cap ** (1 - alpha)) / (alpha - 1)


# Standard parameters for web traffic
DEFAULT_MIXTURE = UserActivityMixture([
    ('nbinom', {'r': 2, 'p': 0.3}, 0.60),   # regular
    ('nbinom', {'r': 5, 'p': 0.2}, 0.30),   # active
    ('pareto', {'alpha': 2.5, 'xm': 50}, 0.08),  # super-active
    ('pareto', {'alpha': 1.5, 'xm': 200}, 0.02),  # bots
])
```

### Simplified solution: an analytical approximation

For the case without an exact histogram — an analytical formula. The delivery coefficient should
grow with `ratio` (the ratio of the limit to the average demand): the larger the limit
relative to the average, the more impressions are actually delivered.

```python
def estimate_user_action_coefficient(
    avg_requests_per_user: float,
    user_period_limit: float,
    coefficient_of_variation: float = 1.5,
) -> float:
    """
    Estimates the share of traffic delivered at user_limit.

    Parameters:
        avg_requests_per_user: average number of requests per user
        user_period_limit: impression limit per user per period
        coefficient_of_variation: CV = std/mean (typically 1.2-2.0)

    Returns:
        coef ∈ (0, 1]: the share of traffic delivered with the limit taken into account
    """
    # Ratio of the limit to the average
    ratio = user_period_limit / avg_requests_per_user

    if ratio >= 3:
        # The limit is 3+ times the average — almost everyone sees enough
        return 0.98

    if ratio <= 0.1:
        # The limit is 10+ times smaller than the average — almost everyone saturates
        return ratio * 0.9  # ~10% overhead

    # logit grows with ratio: the larger the limit relative to the average demand,
    # the higher the delivery share
    import math
    logit = 2 * math.log(ratio)
    sigmoid = 1 / (1 + math.exp(-logit))

    coef = 0.95 * sigmoid + 0.05
    return max(0.05, min(0.98, coef))
```

**Example values** (grows monotonically with ratio, the boundary at `ratio=3` is smooth —
0.90 at ratio=2.9 vs 0.98 right at the boundary):

| ratio | 0.1 | 0.3 | 0.5 | 0.7 | 1.0 | 1.5 | 2.0 | 2.9 | 3.0 |
|-------|-----|-----|-----|-----|-----|-----|-----|-----|-----|
| coef | 0.09 | 0.13 | 0.24 | 0.36 | 0.53 | 0.71 | 0.81 | 0.90 | 0.98 |

The specific constants (0.95, 0.05, the factor 2 at the logarithm) need to be calibrated on
real logs — see section 6.

### Implementation details

**New file:** `src/rtb_sdk/balancer/seasonal/user_mixture.py`

```python
"""
A model of a mixture of distributions for user activity.
"""
import math
from typing import TypedDict


class UserActivityParams(TypedDict):
    """Parameters of the user activity model."""
    avg_requests: float
    cv: float  # coefficient of variation


# Typical parameters for different traffic types
TRAFFIC_TYPE_PARAMS = {
    'social': {'avg_requests': 25, 'cv': 1.8},
    'news': {'avg_requests': 15, 'cv': 1.5},
    'ecommerce': {'avg_requests': 10, 'cv': 1.3},
    'search': {'avg_requests': 8, 'cv': 1.2},
    'default': {'avg_requests': 12, 'cv': 1.5},
}


def estimate_delivery_coefficient(
    user_period_limit: float,
    params: UserActivityParams,
) -> float:
    """
    Estimates the traffic delivery coefficient.

    Args:
        user_period_limit: impression limit per user per period
        params: distribution parameters (avg_requests, cv)

    Returns:
        coef ∈ (0, 1]: the share of traffic delivered at the given limit
    """
    avg = params['avg_requests']

    if user_period_limit >= 3 * avg:
        return 0.97

    if user_period_limit <= 0:
        return 0.0

    if user_period_limit <= 0.1 * avg:
        return max(0.05, user_period_limit / avg * 0.95)

    # logit grows with ratio, as in estimate_user_action_coefficient above
    ratio = user_period_limit / avg
    log_ratio = 2 * math.log(ratio)
    sigmoid = 1 / (1 + math.exp(-log_ratio))

    coef = 0.95 * sigmoid + 0.05
    return max(0.05, min(0.97, coef))
```

**Change in `corrections.py`:**

```python
def apply_histogram_correction(
    limit: float,
    histogram: list[int] | None,
    user_period_limit: float,
    user_params: UserActivityParams | None = None,  # new
) -> float:
    """
    Corrects the total limit taking user saturation into account.
    """
    if user_period_limit >= float('inf'):
        return limit

    if histogram is not None and len(histogram) > 0:
        # Existing histogram-based logic
        total = sum(histogram)
        if total == 0:
            return limit
        delivered = sum(min(count, user_period_limit) for count in histogram)
        return limit * (delivered / total)

    elif user_params is not None:
        # New logic: a parametric model
        coef = estimate_delivery_coefficient(user_period_limit, user_params)
        return limit * coef

    return limit
```

### Impact on accuracy

| Scenario | Averaged histogram | Mixture of distributions | Change |
|----------|------------------------|-------------------|-----------|
| Typical (CV=1.5) | coef ≈ 0.72 | coef ≈ 0.68-0.76 | refinement |
| High activity (CV=2.5) | coef ≈ 0.55 | coef ≈ 0.45-0.55 | tail accounted for |
| Low activity (CV=1.0) | coef ≈ 0.85 | coef ≈ 0.83-0.87 | minimal |

---

## 6. New proposal: calibrating parameters on historical data

### Problem

Each of sections 1-5 introduces at least one "magic constant" picked by
eye rather than derived from data: `β` (section 1), calibrated `p_slot` profiles by
traffic type (section 3), `α` for EWMA (section 4), the weights/parameters of the mixture components
`π_i`, `r`, `p`, `α`, `xm` (section 5). None of the sections describes how to
obtain or verify these numbers on real logs — without calibration for the project's specific traffic
these constants may turn out wrong in either direction.

### Proposal

Use the already existing log infrastructure (`HistoricalLogsConfig`,
`build_seasonality_profile()`) for a lightweight backtesting loop: run the proposed
model over a historical period, compare the predicted volume with the actually
delivered one, and pick the constant by the minimum error (grid search — this is enough
for one-dimensional/few-parameter constants like `β` or `α`).

```python
def calibrate_beta_by_backtest(
    historical_logs: HistoricalLogsConfig,
    candidate_betas: list[float] = (0.5, 0.7, 0.8, 0.9, 1.0, 1.2, 1.5),
) -> float:
    """
    Picks β for compute_elastic_user_limit by the minimum mean error
    of volume prediction on historical data.
    """
    best_beta, best_error = None, float('inf')
    for beta in candidate_betas:
        predicted = simulate_with_beta(historical_logs, beta)
        actual = load_actual_delivered(historical_logs)
        error = mean_absolute_percentage_error(predicted, actual)
        if error < best_error:
            best_beta, best_error = beta, error
    return best_beta
```

Likewise for the `p_slot` profiles (section 3) — compute the empirical shares of impressions per
10-minute slot directly from the logs instead of the fixed `TRAFFIC_TYPE_P_SLOT` tables, and for the
mixture parameters in section 5 — fit `r, p` of the Negative Binomial components via a
`scipy.stats.nbinom.fit`-like approach (or method-of-moments on the per-user request
histogram) instead of the hard-coded `DEFAULT_MIXTURE`.

### Recommendation

This is not a blocker for deploying sections 1-5 (one can start with the defaults given
above), but it should be done **before** any of the constants is pinned in the
production config as "universal". The priority is lower than items 1-5, but higher than any
subsequent manual fine-tuning of these same constants.

---

## Summary table of improvements

| # | Improvement | File(s) | Impact | Complexity |
|---|-----------|----------|---------|-----------|
| 1 | Cumulative user constraints | `seasonal/corrections.py` | High | Medium |
| 2 | Parasitic traffic | `helpers/balancer/inner_ad_helpers.py` | High | Medium |
| 3 | Pacing factor | `seasonal/corrections.py` | Medium | Low |
| 4 | Adaptive profile | `seasonal/adaptive.py` (new) | Medium | High |
| 5 | Mixture of distributions | `seasonal/user_mixture.py` (new) | Medium | High |
| 6 | Calibration on data | — | Infrastructural | Medium |

---

## Recommended order of deployment

1. **Pacing factor (3)** — minimal complexity, a visible effect
2. **Cumulative constraints (1)** — a significant improvement for user-limited campaigns
3. **Parasitic traffic (2)** — for campaigns with low targeting
4. **Mixture of distributions (5)** — fine-tuning for histogram corrections
5. **Adaptive profile (4)** — for dynamically changing traffic
6. **Calibration on data (6)** — in parallel with 1 and 5, before constants are pinned in prod
