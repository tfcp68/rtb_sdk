# Implementation of algorithms for distribution of impressions according to the plan

> Adaptation of MSVV and A2 from the Vazirani article for long-term optimization of the distribution of impressions between advertising campaigns.

## Contents

1. [The challenge](#task)
2. [Current architecture](#current-architecture)
3. [MSVV — budget-aware algorithm](#msvv--budget-aware-algorithm)
4. [A2 — budget-oblivious algorithm](#a2--budget-oblivious-algorithm)
5. [Horizons: month-to-month](#horizons-month-and-general)
6. [Variations: volume and/or cpm](#variation-volume-or-cpm)
7. [Optional attenuating multiplier A2](#optional-weakening-multiplier-a2)
8. [Summary table of functions](#composite-table-function)
9. [Token Bucket — algorithm pacing](#token-bucket--algorithm-pacing)
10. [Damped Pacing — tuned-out](#damped-pacing--customizable-attenuation)
11. [Thompson Sampling — Bayesian approach](#thompson-sampling--bayesian-approach)
12. [Summary table of all algorithms](#composite-table-everyone-algorithms)
13. [Changes to the code](#change-in-code)

---

## The challenge

### Formulation

**Dan:**
- Set of advertising campaigns `Ad` s `volume` (general/lifetime limit of impressions for the entire flyt campaign) and `cpm` (price-per-thousand)
- `AdStats` statistics - how many impressions have already been made
- Set of filtered `ads` for the current request

**Target:**
- Distribute impressions ** evenly and fairly** relative to plans (`volume` )
- Consider **Value**Impressions (`cpm`) – not only quantity, but also income
- Don’t let go **overexpenditure** plan
- **Performance of plans** by the end of the period

### Why Existing Heuristics Are Not Enough

| Function | Problem |
|---------|----------|
| `best_velocity` | Linear `velocity_factor` — uneven distribution at the end of the period |
| `best_heuristics` | Production of factors — high-end CPM "win" even with little leftover |
| `best_price` | Ignoring the rest of the plan — expensive campaigns dominate |

### Mathematical formalization

Let's go.
- `B_j` – full `j` campaign budget (in screenings or money)
- `L_j(t)`: Budget balance at `t`
- `x_j(t)` - Number of impressions to `t`
- `b_j` - Bet (CPM)

**Target function of MSVV:**
```
Σ_j b_j × x_j  → max
conditionally: x_j ≤ B_j
           Σ_j x_j(t) = t (All requests are distributed)
```

**** An algorithm with a competitive `1 - 1/e` ratio ensures that the result ≥ 63% is optimal.

### Important article: Single-Valued vs Small

Vazirani’s article distinguishes between two productions, and the `1-1/e` warranty for A2 is proven to be **strict for only one of them**:

- **Single-Valued** - each `j` advertiser has exactly one `b_j` bet, and the "budget" is a `k_j` integer cap on the number of matches (b-matching). For this case, A2 (Algorithm 1 from the article) is optimal ** unconditionally**, without any additional assumptions.
- **Small/General** is an advertiser’s fractional money budget `B_j`, which can be partially spent last bet (“fake money”). The extension of A2 in this case requires an unproven **No-Surpassing Property** (the article experimentally confirms that it is violated <2% edges – that is, the guarantee is empirical, not strict).

**How it falls on our data:** `Ad.volume` — whole-limit, It’s not the budget, And one campaign is always traded by one `cpm`. It’s **flatly Single-Valued b-matching**. From here,:

- **`msvv_volume` /A2 by volume** is a Single-Valued case, the `1-1/e` warranty is strict.
- **`msvv_cpm` /`msvv_hybrid` ** artificially converts the volume boundary into a monetary budget (`volume × cpm` ) is already an emulation of Small/General , and the warranty applies only in the sense in which it is justified by MSV07 (not A2 ), with the same empirical (not strict) nature.

The table of competitive ratios below (section "Competitive ratio") should be read with this caveat - see the edit there.

---

## Current architecture

### How Velocity Works Now

```python
# utils.py — velocity_factor
def velocity_factor(current_month_volume, month_limit, max_volume):
    if month_limit <= 0 or month_limit is None:
        return (max_volume - current_month_volume) / max_volume
    return (month_limit - current_month_volume) / month_limit
```

**Problem:** Linear dependency: By the end of the month, all the campaigns are catching up with each other linearly, there's no exponential attenuation.

### How Heuristics Works Now

```python
# utils.py — heuristic_function_simplest
def heuristic_function_simplest(priority_factor, price_factor, velocity_factor):
    return priority_factor * price_factor * velocity_factor
```

**Problem: ** If `price_factor = 1.0` (expensive campaign) and `velocity_factor ≈ 0.1` (nearly exhausted plan), the product of `0.1` - but the expensive campaign still "competes".

### What's available for implementation

| Component | Appointment |
|-----------|-----------|
| `Ad.volume` | Common (lifetime) limit of impressions for the entire flyt campaign — **not** monthly |
| `Ad.cpm` | Price per thousand impressions |
| `AdStats` | Statistics: `{precise: {t,h,d,w,m}, fuzzy: {t,h,d,w,m}}` |
| `GranulatedCounter` | Granulation meter |
| `AuctionParams.ads_stats` | Submitted to auction |

---

## MSVV - budget-aware algorithm

### Idea

MSVV Scaling the advertiser’s rate proportionally **remaining share of the budget**. There’s less left — less effective bid.

### Formula

```
effective_bid(j) = bid_j × (1 − e^(−L_j / B_j))

whereabouts:
  B_j — full budget (volume or volume × cpm)
  L_j — leftover
  bid_j — reference rate (cpm or volume)
```

### Interpretation of the formula

```
L_j/B_j = 1.0 (100% remainder)  → effective_bid ≈ bid × 0.63
L_j/B_j = 0.5 (50% remainder)   → effective_bid ≈ bid × 0.39
L_j/B_j = 0.1 (10% remainder)   → effective_bid ≈ bid × 0.095
L_j/B_j = 0.0 (0% remainder)   → effective_bid = 0
```

### Difference from Linear Velocity

```
Linear:  score = remaining / total
MSVV:      score = 1 - e^(-remaining/total)

remaining = 50%:
  Linear: 0.50
  MSVV:     0.39  ← less, linear

remaining = 10%:
  Linear: 0.10
  MSVV:     0.095 ← similarly

remaining = 90%:
  Linear: 0.90
  MSVV:     0.55  ← noticeably!
```

**Conclusion:** MSVV aggressively reduces score for high-residue campaigns — they "prematurely" lose out, giving others a chance.

---

## A2 - budget-oblivious algorithm

### Idea

A2 assigns each campaign **random price** `p_j ∈ [1/e, 1]` once per period. Effective bid = `bid × (1 - p_j)`. The weakening knife smears impressions without having to know the budget.

### Formula

```
p_j = e^(w_j − 1), whereabouts w_j ~ Uniform[0, 1]

effective_bid(j) = bid_j × (1 − p_j)
```

### Key property

**Budget-oblivious:** The algorithm doesn't need to know `budget_left`. "" A random `p_j` is enough, and on average, campaigns get a fair share.

### Interpreting

```
w_j = 0.0  → p_j = 1/e ≈ 0.37  → (1-p_j) = 0.63  → maximum effective_bid
w_j = 0.5  → p_j = e^(-0.5) ≈ 0.61 → (1-p_j) = 0.39
w_j = 1.0  → p_j = 1.0      → (1-p_j) = 0.0   → minimum effective_bid
```

### Weakening knife

`(1 - p_j)` works **stabbing**: Even an expensive campaign with `p_j ≈ 1` receiver `effective_bid ≈ 0`.

**Effect:** The random component smears the impressions, preventing one ad from dominating.

---

## Horizons: month and total

### Why Two Horizons and Data Limitation

| horizon | `B_j` (limit) | Use of use |
|----------|-------|---------------|
| **A month** | `get_real_month_volume(ad)` — ranking `Ad.volume` until ~30-daily equivalent | Short term implementation of the plan |
| **Common** | `Ad.volume` (full-fledged lifetime-campaigning, how) | Long-term distribution |

**The `AdStats` :** granulation limitation of `GranulatedCounter` (`t/h/d/w/m`) is ** nested sliding windows** ("last N seconds from the current moment"), not non-intersecting packets: an event that hits `t` also hits `h`, `d`, `w`, `m` simultaneously (see `auction/README.md`, Granularity section, and `auction/simulation/statistics/counter.py`).

- **Summarize `t+h+d+w+m` to get "shown for the entire period" is impossible** - the same event is counted up to 5 times.
- The longest window available is the `'m'` (720 hours ≈ 30 days) and there is no “showed over the lifetime of the campaign” meter in the current `AdStats` model.

From-for **`shown` horizonly `month` and `total` It comes from the same meter `'m'`** — differ **limit** (`get_real_month_volume` for `month` raw `Ad.volume` for `total`), not the source "shown". It’s a deliberate simplification, not exact lifetime-tracking: campaigns shorter than a month `month` and `total` give the same result; campaigns longer than a month `total`-horizon will lower `shown` (window `'m'` he doesn’t see shows older 30 days), volt.her. remainder `remaining` will be overstated. If you want to be precise lifetime-counter — This is a separate task for expansion `AdStats`, outside the scope of this document.

### How to calculate the remainder

```python
# Pseudocode

def get_remaining_volume(ad, ads_stats, horizon):
    """Calculate the remaining volume for the horizon"""
    volume = get_limit_for_horizon(ad, horizon)  # quarter-month
    shown = get_shown_for_horizon(ad, ads_stats, horizon)
    return max(0, volume - shown)


def get_limit_for_horizon(ad, horizon):
    if horizon == 'month':
        return get_real_month_volume(ad)  # ranking Ad.volume current-month
    elif horizon == 'total':
        return get_ad_volume(ad)  # full-fledged lifetime-limit Ad.volume how
    else:
        raise ValueError(f"Unknown horizon: {horizon}")


def get_shown_for_horizon(ad, ads_stats, horizon):
    """Get how much is already shown.

    Important: 'm' — This is the only window available, long enough
    both horizons (centimetre. clause above overlapping-granulation).
    Summarize all granulations can not be — It’s relearning the same thing
    precedence 5 once.
    """
    stats = get_ad_stats_by_id(ads_stats, ad.get('id'))
    precise = get_auction_stats_by_type(stats, 'precise')
    fuzzy = get_auction_stats_by_type(stats, 'fuzzy')
    combined = merge_granulated_counters(precise, fuzzy)
    return get_counter_value(combined, 'm')
```

---

## Variations: volume and/or cpm

### 1. MSVV by volume (number of impressions)

```python
def msvv_volume(ad, ads_stats, horizon):
    """MSVV uniformly"""
    volume = get_limit_for_horizon(ad, horizon)
    remaining = get_remaining_volume(ad, ads_stats, horizon)
    
    if volume <= 0:
        return 1.0  # limitless — maximum priority
    
    ratio = remaining / volume
    return 1.0 - math.exp(-ratio)
```

**Usage:** if the goal is **just to execute the screening plan**.

### 2 . MSVV by CPM (Income)

```python
def msvv_cpm(ad, ads_stats, horizon):
    """MSVV optimizing income"""
    volume = get_limit_for_horizon(ad, horizon)
    remaining = get_remaining_volume(ad, ads_stats, horizon)
    cpm = get_ad_cpm(ad)
    
    if volume <= 0:
        effective = cpm  # limitless — full-time
    else:
        ratio = remaining / volume
        decay = 1.0 - math.exp(-ratio)
        effective = cpm * decay
    
    return effective
```

**Usage: ** if the goal is to **maximise revenue** in the execution of plans.

### 3. MSVV by volume × CPM (hybrid)

```python
def msvv_hybrid(ad, ads_stats, horizon):
    """MSVV It takes into account volume and income"""
    volume = get_limit_for_horizon(ad, horizon)
    remaining = get_remaining_volume(ad, ads_stats, horizon)
    cpm = get_ad_cpm(ad)
    
    if volume <= 0:
        return cpm  # limitless — simple CPM
    
    # "Budget in the money"
    total_budget = volume * cpm / 1000  # CPM = price 1000, /1000 = behind 1
    remaining_budget = remaining * cpm / 1000
    
    ratio = remaining_budget / total_budget if total_budget > 0 else 1.0
    decay = 1.0 - math.exp(-ratio)
    
    return cpm * decay
```

**Use of use:** if — **equitable distribution "value"**, not-just-show.

### 4 . MSVV velocity + price (composite)

```python
def msvv_velocity_price(ad, ads_stats, horizon, weight_cpm=0.5):
    """Composite score: velocity MSVV + price MSVV"""
    velocity_score = msvv_volume(ad, ads_stats, horizon)
    price_score = msvv_cpm(ad, ads_stats, horizon)
    
    # Normalize price_score toward 0..1
    # price_score = CPM, It is necessary to normalize relatively max. CPM
    ...
```

---

## Optional Attenuating Multiplier A2

### Why a Disabled Attenuating Multiplier

| Regime | Behavior | When to use |
|-------|-----------|-------------------|
| Without weakening | deterministic MSVV | We want predictable distribution |
| Attenuated | Randomized MSVV | Want it "spread out" impressions, evade |

### Implementation of a weakening multiplier

```python
import math
import random

# Global cache p_j for seed-period
_PJ_CACHE: dict[int, dict[str, float]] = {}
_PJ_SEED: int | None = None


def get_pj(ad_id: str, seed: int) -> float:
    """Receive or generate p_j for ad_id.
    
    p_j ∈ [1/e, 1]. It is generated once on (seed, ad_id) and reused,
    while seed never changed.
    """
    global _PJ_CACHE, _PJ_SEED
    
    if seed != _PJ_SEED:
        # New seed — cash off
        _PJ_CACHE.clear()
        _PJ_SEED = seed
    
    if ad_id not in _PJ_CACHE:
        # Critical: RNG must depend on ad_id, not only seed.
        # random.Random(seed) fixed seed always returns one and
        # same first .random() independently ad_id — if only sitting
        # seed'ome, All campaigns will get the same p_j, algorithm A2
        # normalize best_price (weakening will become a constant).
        rng = random.Random((seed, ad_id))
        # w_j ~ Uniform[0, 1]
        w_j = rng.random()
        # p_j = e^(w_j - 1) ∈ [1/e, 1]
        _PJ_CACHE[ad_id] = math.exp(w_j - 1)
    
    return _PJ_CACHE[ad_id]


def msvv_with_weakening(score: float, ad_id: str, seed: int, use_weakening: bool) -> float:
    """Apply A2-multiplier MSVV score.
    
    Args:
        score: MSVV score (0..1 more)
        ad_id: ID pronouncement
        seed: Seed generational p_j
        use_weakening: Include a weakening multiplier
    
    Returns:
        If use_weakening=True: score × (1 - p_j)
        If use_weakening=False: score
    """
    if not damping:
        return score
    
    p_j = get_pj(ad_id, seed)
    return score * (1 - p_j)
```

### Use of use

```python
def auction_msvv_velocity(
    ads: AdsDict,
    parameters: AuctionParams,
    horizon: str = 'month',
    use_weakening: bool = False,
) -> Optional[Ad]:
    seed = parameters.get('seed', 42)
    ads_stats = get_ad_stats_from_params(parameters)
    ads_value = get_ads_dict(ads)
    
    def score(ad_id):
        ad = ads_value[ad_id]
        base_score = msvv_volume(ad, ads_stats, horizon)
        return msvv_with_weakening(base_score, ad_id, seed, use_weakening)
    
    best_id = max(ads_value, key=score)
    return get_ad_from_ads(ads, best_id)
```

---

## Summary table of functions

### Functions of MSVV

| Function | Score | horizon | Weakening | Description |
|---------|-------|----------|------------|----------|
| `auction_msvv_volume_month` | volume MSVV | month | no | Monthly uniform displays |
| `auction_msvv_volume_total` | volume MSVV | total | no | Uniform displays according to the general plan |
| `auction_msvv_volume_month_weakened` | volume MSVV | month | yes | Same thing + A2 weakening |
| `auction_msvv_cpm_month` | cpm × MSVV | month | no | Optimization of income |
| `auction_msvv_cpm_total` | cpm × MSVV | total | no | Same thing in general |
| `auction_msvv_hybrid_month` | volume × cpm MSVV | month | no | Hybrid |
| `auction_msvv_hybrid_total` | volume × cpm MSVV | total | no | Same thing in general |

### Options with attenuation (on/off)

For each feature above, there may be a version with or without `_weakened`.

### Random Options

Each `best_*` feature has a `random_*` version (weighted by score).

### Total: 7 × 2 (attenuated) × 2 (random/best ) = 28 functions

**Recommendation:** implement basic 6-8, others as an extension.

---

## Example of use

```python
from rtb_sdk import auction
from rtb_sdk.helpers import create_parameters_ads_stats
from rtb_sdk.constants import SelectionFunc

# Monthly uniform distribution (loosely)
params = create_parameters_ads_stats(
    auction_type=SelectionFunc.MSVV_VOLUME_MONTH_BEST,
    ads_stats=ad_stats
)
ad = auction(ads=ads, parameters=params)

# Equal distribution + A2 multiplier (more randomization)
params_weakened = create_parameters_ads_stats(
    auction_type=SelectionFunc.MSVV_VOLUME_MONTH_WEAKENED_BEST,
    ads_stats=ad_stats,
    seed=42  # seed influence p_j
)
ad_weakened = auction(ads=ads, parameters=params_weakened)

# Optimization of income (CPM)
params_cpm = create_parameters_ads_stats(
    auction_type=SelectionFunc.MSVV_CPM_MONTH_BEST,
    ads_stats=ad_stats
)
ad_cpm = auction(ads=ads, parameters=params_cpm)

# Hybrid: and volume and CPM
params_hybrid = create_parameters_ads_stats(
    auction_type=SelectionFunc.MSVV_HYBRID_TOTAL_BEST,
    ads_stats=ad_stats
)
ad_hybrid = auction(ads=ads, parameters=params_hybrid)
```

---

## Competitive ratio

| Algorithm | Guarantee | Conditions | Strictness |
|----------|----------|---------|-----------|
| A2 (volume, multiplier) | `1 - 1/e ≈ 0.63` | Single-Valued b-matching: whole-cap `k_j`, single-handed `b_j` campaign | **Strict**, proved in the article without assumptions |
| MSVV (volume) | `1 - 1/e` | Same thing (b-matching), play-off MSVV07 | Strict |
| MSVV (CPM) | `1 - 1/e` | CPM × volume — money-budget emulation (Small/General) | From MSVV07, non- A2 |
| MSVV/A2 (hybrid) | `1 - 1/e` (rigidly) | Monetary budget + No-Surpassing Property | **Empiric**: NSP breached <2% rib on the experimentation article, theoretically unproven |

**Note:** warranties are proven for the idealized online b-matching/adwords problem (arbitrary adversarial query order, full coverage).For RTB specifics (frequency, targeting, pre-auction filtering) this is a heuristic approximation rather than a formal guarantee of the quality of the final media plan.

---

## Token Bucket - Pacing Algorithm

### Idea

Token Bucket is a classic pacing algorithm used by Google, Meta, Yandex.Every campaign is issued a "bucket of tokens" with a certain rate of replenishment. The display costs 1 token. If there are no tokens, the campaign misses the request.

### Distinction from MSVV

| Aspekt | MSVV | Token Bucket |
|--------|------|-------------|
| Type | Continuous score | Discrete (eat/no token) |
| Accumulation | No (exponential decay) | Yes (until capacity) |
| Predictability | Medium | Tall |
| Complexity | Low | Very low |

### Formula

```
token_count(t) = min(capacity, token_count(t-1) + rate × Δt - spent)

If token_count > 0 → show off
If token_count = 0 → pass-through
```

### Interpreting

- `capacity` – Maximum token stock (you can’t accumulate more)
- `rate` - Replenishment rate (tokens per second)
- `Δt` - Time since the last request
- `spent` – 1 token for current display

### How to calculate the rate

```python
def compute_rate(volume_limit: int, period_seconds: int) -> float:
    """Calculate the rate of replenishment of tokens.
    
    Args:
        volume_limit: Monthly screening limit
        period_seconds: Period (month ≈ 30 days = 2,592,000 sec)
    
    Returns:
        Speed in tokens/moment
    """
    if period_seconds <= 0:
        return 0.0
    return volume_limit / period_seconds


# Example: 10000 monthly
# 30 days = 2,592,000 seconds
# rate = 10000 / 2592000 ≈ 0.00386 token/moment
```

### Implementation

```python
import time
from dataclasses import dataclass, field
from typing import Optional

from rtb_sdk.schemas import Ad, AdsDict, AuctionParams
from rtb_sdk.helpers import (
    get_ad_stats_from_params,
    get_ads_dict,
    get_ad_from_ads,
    is_ads_empty,
    is_valid_auction_ads_dict,
)
# get_real_month_volume resides auction/functions/utils.py, Not in rtb_sdk.helpers
from rtb_sdk.auction.functions.utils import get_real_month_volume


@dataclass
class TokenBucketState:
    """Status of one bucket of tokens."""
    tokens: float
    last_update: float


class TokenBucketPacer:
    """Pacer basis Token Bucket.
    
    KEEPING THE STATE — Requires external storage between requests.
    """
    
    # Time of month in seconds
    MONTH_SECONDS = 30 * 24 * 60 * 60  # ≈ 2,592,000
    
    def __init__(self, ads: AdsDict, ads_stats=None):
        self.ads = ads
        self.ads_stats = ads_stats or {}
        self._states: dict[str, TokenBucketState] = {}
    
    def _get_capacity(self, ad: Ad) -> int:
        """Pocket capacity = monthly limit."""
        volume = get_real_month_volume(ad)
        return int(volume) if volume > 0 else 0
    
    def _get_rate(self, ad: Ad) -> float:
        """Replenishment rate = volume / month_seconds."""
        capacity = self._get_capacity(ad)
        if capacity <= 0:
            return 0.0
        return capacity / self.MONTH_SECONDS
    
    def _get_or_create_state(self, ad_id: str) -> TokenBucketState:
        """Getting or creating a bucket state."""
        if ad_id not in self._states:
            self._states[ad_id] = TokenBucketState(
                tokens=0.0,
                last_update=time.time()
            )
        return self._states[ad_id]
    
    def _refill(self, state: TokenBucketState, capacity: float, rate: float) -> None:
        """Replenish the token bucket."""
        now = time.time()
        elapsed = now - state.last_update
        
        # Adding Tokens at Speed rate
        new_tokens = state.tokens + elapsed * rate
        
        # Do not exceed capacity
        state.tokens = min(capacity, new_tokens)
        state.last_update = now
    
    def can_spend(self, ad: Ad) -> bool:
        """Check it out, Are there tokens for display?."""
        ad_id = ad.get('id')
        capacity = self._get_capacity(ad)
        rate = self._get_rate(ad)
        
        if capacity <= 0:
            return True  # Unlimited ad always available
        
        state = self._get_or_create_state(ad_id)
        self._refill(state, capacity, rate)
        
        return state.tokens >= 1.0
    
    def spend(self, ad: Ad) -> bool:
        """Spend a token on display. Returns True successfully."""
        ad_id = ad.get('id')
        capacity = self._get_capacity(ad)
        rate = self._get_rate(ad)
        
        if capacity <= 0:
            return True
        
        state = self._get_or_create_state(ad_id)
        self._refill(state, capacity, rate)
        
        if state.tokens >= 1.0:
            state.tokens -= 1.0
            return True
        return False
    
    def get_remaining(self, ad: Ad) -> float:
        """Receive the remaining tokens."""
        ad_id = ad.get('id')
        capacity = self._get_capacity(ad)
        rate = self._get_rate(ad)
        
        if capacity <= 0:
            return float('inf')
        
        state = self._get_or_create_state(ad_id)
        self._refill(state, capacity, rate)
        return state.tokens


def auction_token_bucket_best(
    pacer: TokenBucketPacer,
    ads: AdsDict,
) -> Optional[Ad]:
    """Choose the best one ad considerately pacing.
    
    Args:
        pacer: TokenBucketPacer stately
        ads: Dictionary of announcements
    
    Returns:
        Ad most score accessible (tokenized)
    """
    if not is_valid_auction_ads_dict(ads):
        raise AuctionError(...)
    if is_ads_empty(ads):
        return None
    
    ads_value = get_ads_dict(ads)
    
    # Filter only ad tokenized
    available = [ad_id for ad_id in ads_value if pacer.can_spend(ads_value[ad_id])]
    
    if not available:
        return None
    
    # Among the available options, choose best_velocity
    best_id = max(available, key=lambda aid: get_real_month_volume(ads_value[aid]))
    pacer.spend(ads_value[best_id])
    return get_ad_from_ads(ads, best_id)


def auction_token_bucket_random(
    pacer: TokenBucketPacer,
    ads: AdsDict,
) -> Optional[Ad]:
    """Pick a random one ad considerately pacing."""
    if not is_valid_auction_ads_dict(ads):
        raise AuctionError(...)
    if is_ads_empty(ads):
        return None
    
    ads_value = get_ads_dict(ads)
    
    available = [ad_id for ad_id in ads_value if pacer.can_spend(ads_value[ad_id])]
    
    if not available:
        return None
    
    import random
    chosen = random.choice(available)
    pacer.spend(ads_value[chosen])
    return get_ad_from_ads(ads, chosen)
```

### Architectural comment

Token Bucket **keeps state** between requests.
1 : External Storage (`TokenBucketPacer` lives out of auction)
2 : synchronization between instances (Redis/DB )

**It’s different MSVV** — MSVV stateless, Token Bucket stateful.

**Important: This is NOT built into `SelectionFunc`/`AUCTIONS` as it is.** The `auction()` entry point invokes a strategy strictly like `AUCTIONS[auction_type](ads, parameters)` (`auction/auction.py`, `auction = get_auction_func(parameters); return AUCTIONS[auction](ads, parameters)`) - two positional arguments, `pacer` is not among them and there is no way to take it from anywhere. The `auction_token_bucket_best(pacer, ads)` signature does not fit this contract, so:

- Such a function cannot be registered in `AUCTIONS` under any `SelectionFunc.TOKEN_BUCKET_BEST` - the `auction()` calling code cannot transmit `pacer`.
- For Token Bucket to work through the same public `auction(ads, parameters)`, you need one of the options (this document is not worked out, this is a separate task):
  1. Keep the state outside (Redis/DB) inside stateless-function `(ads, parameters)` call out `GET`/`SET` by `ad_id` — Then the signature becomes the compatible price of the network trip for each request of the auction.
  2. Do not attempt to register Token Bucket how `SelectionFunc` generally, use `TokenBucketPacer` separate **pre-auction** (frequency-filtering/targeting, mentioned `auction/README.md`) — Then it is called explicitly in the Pipeline of the calling code, not through `auction()`.

The example below shows the `auction_token_bucket_best(pacer, ads)` call directly, bypassing `auction()` - this is the path (2), it is worth clearly denoting this, rather than feeding the Token Bucket in the same row as the `msvv_*` /`SelectionFunc` constants.

### Use of use

```python
from rtb_sdk import auction
from rtb_sdk.helpers import create_parameters_ads_stats
from rtb_sdk.constants import SelectionFunc

# Create pacer stately
pacer = TokenBucketPacer(ads, ads_stats)

# First request
ad1 = auction_token_bucket_best(pacer, ads)

# Second request (tokens already spent)
ad2 = auction_token_bucket_best(pacer, ads)
```

---

## Damped Pacing – Configurable Attenuation

### Idea

Damped Pacing is a generalization of MSVV with a customizable attenuation parameter. MSVV uses `decay(t) = 1 - e^(-t)`. Damped Pacing allows you to select any attenuation function.

### Formula

```
score = velocity × f(remaining / total)

whereabouts f — attenuation:
  - linear:    f(x) = x
  - msvv:      f(x) = 1 - e^(-x)
  - sigmoid:   f(x) = x / (x + k)      # k — parameter
  - sqrt:      f(x) = √x
  - tanh:      f(x) = tanh(x × c)      # c — factor
```

### Implementation

```python
import math
from typing import Literal, Callable

from rtb_sdk.schemas import Ad, AdsDict, AuctionParams
from rtb_sdk.helpers import (
    get_ad_stats_from_params,
    get_ad_price,
    get_ads_dict,
    get_ad_from_ads,
    get_ad_stats_by_id,
    get_auction_stats_by_type,
    merge_granulated_counters,
    is_ads_empty,
    is_valid_auction_ads_dict,
)
from rtb_sdk.auction.functions.utils import get_real_month_volume
from rtb_sdk.constants import AuctionType


# ============================================================================
# Attenuation functions
# ============================================================================

def decay_linear(remaining_ratio: float) -> float:
    """Linear damping: f(x) = x."""
    return remaining_ratio


def decay_msvv(remaining_ratio: float) -> float:
    """MSVV attenuation: f(x) = 1 - e^(-x)."""
    if remaining_ratio <= 0:
        return 0.0
    return 1.0 - math.exp(-remaining_ratio)


def decay_sqrt(remaining_ratio: float) -> float:
    """The square root: f(x) = √x."""
    if remaining_ratio <= 0:
        return 0.0
    return math.sqrt(remaining_ratio)


def decay_sigmoid(remaining_ratio: float, k: float = 0.5) -> float:
    """sigmoid: f(x) = x / (x + k)."""
    if remaining_ratio <= 0:
        return 0.0
    return remaining_ratio / (remaining_ratio + k)


def decay_tanh(remaining_ratio: float, c: float = 3.0) -> float:
    """Hyperbolic tangent: f(x) = tanh(x × c)."""
    if remaining_ratio <= 0:
        return 0.0
    return math.tanh(remaining_ratio * c)


DECAY_FUNCTIONS: dict[str, Callable[[float], float]] = {
    'linear': decay_linear,
    'msvv': decay_msvv,
    'sqrt': decay_sqrt,
    'sigmoid': decay_sigmoid,
    'tanh': decay_tanh,
}


# ============================================================================
# Damped Pacing
# ============================================================================

def damped_pacing_score(
    ad: Ad,
    ads_stats,
    horizon: str,
    decay_type: str = 'msvv',
    decay_param: float = 1.0,
    use_cpm: bool = False,
) -> float:
    """Calculate damped pacing score.
    
    Args:
        ad: Ad
        ads_stats: Statistics
        horizon: 'month' or 'total'
        decay_type: Type of attenuation ('linear', 'msvv', 'sqrt', 'sigmoid', 'tanh')
        decay_param: Parameter of the attenuation function (k for sigmoid, c for tanh)
        use_cpm: Multiply by CPM
    
    Returns:
        Score choice
    """
    limit = _get_limit(ad, horizon)
    shown = _get_shown(ad, ads_stats, horizon)
    remaining = max(0, limit - shown)
    
    if limit <= 0:
        ratio = 1.0
    else:
        ratio = remaining / limit
    
    # Select the attenuation function
    if decay_type == 'sigmoid':
        decay_fn = lambda x: decay_sigmoid(x, decay_param)
    elif decay_type == 'tanh':
        decay_fn = lambda x: decay_tanh(x, decay_param)
    else:
        decay_fn = DECAY_FUNCTIONS.get(decay_type, decay_msvv)
    
    score = decay_fn(ratio)
    
    if use_cpm:
        cpm = get_ad_price(ad)
        score *= cpm
    
    return score


def auction_damped_best(
    ads: AdsDict,
    parameters: AuctionParams,
    horizon: str = 'month',
    decay_type: str = 'msvv',
    decay_param: float = 1.0,
    use_cpm: bool = False,
) -> Optional[Ad]:
    """Best ad by damped pacing."""
    if not is_valid_auction_ads_dict(ads):
        raise AuctionError(...)
    if is_ads_empty(ads):
        return None
    
    ads_value = get_ads_dict(ads)
    ads_stats = get_ad_stats_from_params(parameters)
    
    def score(ad_id):
        ad = ads_value[ad_id]
        return damped_pacing_score(
            ad, ads_stats, horizon,
            decay_type, decay_param, use_cpm
        )
    
    best_id = max(ads_value, key=score)
    return get_ad_from_ads(ads, best_id)


def auction_damped_random(
    ads: AdsDict,
    parameters: AuctionParams,
    horizon: str = 'month',
    decay_type: str = 'msvv',
    decay_param: float = 1.0,
    use_cpm: bool = False,
) -> Optional[Ad]:
    """Random ad by damped pacing."""
    if not is_valid_auction_ads_dict(ads):
        raise AuctionError(...)
    if is_ads_empty(ads):
        return None
    
    ads_value = get_ads_dict(ads)
    ads_stats = get_ad_stats_from_params(parameters)
    
    def score(ad_id):
        ad = ads_value[ad_id]
        return damped_pacing_score(
            ad, ads_stats, horizon,
            decay_type, decay_param, use_cpm
        )
    
    elements = list(ads_value.keys())
    weights = [score(aid) + 1e-9 for aid in elements]
    import random
    chosen = random.choices(elements, weights=weights, k=1)[0]
    return get_ad_from_ads(ads, chosen)
```

### Comparison with MSVV

| Function | Formula | Characteristic | When to use |
|---------|---------|----------|-------------------|
| MSVV | `1 - e^(-x)` | Fast saturation | Aggressive distribution |
| Sigmoid | `x / (x + k)` | Soft saturation | Smooth distribution |
| Tanh | `tanh(x × c)` | Abrupt transition | Sharp distribution |
| Sqrt | `√x` | Slow saturation | Conservative distribution |

---

## Thompson Sampling - Bayesian Approach

### Idea

Thompson Sampling is a Bayesian method for exploration/exploitation. Every campaign has a ** distribution** probability of execution of the plan. We sample from these distributions and select the campaign with the maximum sample.

**Reservation:** It’s not classic Thompson Sampling primordial (therein Beta(α,β) model the probability of success/cliques based on binomial outcomes — real Bernoulli-signal "click/non-click"). Here Beta-The distribution is reused as a stochastic superstructure over the same value `remaining/limit`, what MSVV/Damped Pacing — How to Introduce Controlled Noise in Ranking, It’s not a Bayesian response model. It works like a heuristic, But don’t give them the same theoretical guarantees/interpretation, genuinely TS, and indicate in a row with MSVV/A2 Competitive relationship tables should not — guarantee `1-1/e` it doesn’t exist.

### Distinction from MSVV

| Aspekt | MSVV | Thompson Sampling |
|--------|------|-------------------|
| Type | deterministic (s random seed) | Probabilistic |
| Model | Score = f(remaining) | Beta/Dirichlet distribution |
| Adaptability | Statistical data | Towards traffic patterns |
| Complexity | Low | Medium |

### Formula

```
For every campaign j:
  α_j = impressions_shown + 1      # succession
  β_j = (impressions_expected - impressions_shown) + 1  # setback

Sampling: θ_j ~ Beta(α_j, β_j)

Choose: argmax_j θ_j
```

### How to calculate α and β

```python
from rtb_sdk.helpers import get_counter_value
from rtb_sdk.auction.functions.utils import get_real_month_volume
from rtb_sdk.constants import AuctionType


def compute_beta_params(ad: Ad, ads_stats, horizon: str = 'month'):
    """Calculate parameters Beta-distribution.
    
    Returns:
        (alpha, beta) for Beta-distribution
    """
    limit = get_real_month_volume(ad)  # preview
    
    stats = get_ad_stats_by_id(ads_stats, ad.get('id'))
    precise = get_auction_stats_by_type(stats, AuctionType.PRECISE)
    fuzzy = get_auction_stats_by_type(stats, AuctionType.FUZZY)
    combined = merge_granulated_counters(precise, fuzzy)
    
    # 'm' — single window, long enough for both horizons;
    # t/h/d/w/m nested (overlapping), can’t be summed up
    # (centimetre. clause "Horizons: month-to-month").
    shown = get_counter_value(combined, 'm')
    
    # alpha = impressions + 1 (prior)
    alpha = shown + 1
    
    # beta = expected - impressions + 1 (prior)
    # remaining = How much is left of the plan?
    remaining = max(0, limit - shown)
    beta = remaining + 1
    
    return alpha, beta
```

### Implementation

```python
import random
import math
from typing import Optional

from rtb_sdk.schemas import Ad, AdsDict, AuctionParams
from rtb_sdk.helpers import (
    get_ad_stats_from_params,
    get_ads_dict,
    get_ad_from_ads,
    get_ad_stats_by_id,
    get_auction_stats_by_type,
    merge_granulated_counters,
    is_ads_empty,
    is_valid_auction_ads_dict,
)
from rtb_sdk.auction.functions.utils import get_real_month_volume
from rtb_sdk.constants import AuctionType


def _sample_beta(alpha: float, beta: float) -> float:
    """Sampl from Beta-distribution.
    
    Use the gamma-distribution: Beta(α, β) = Gamma(α) / (Gamma(α) + Gamma(β))
    """
    if alpha <= 0 or beta <= 0:
        return 0.5  # fallback
    
    # Let’s sample from gamma-distribution
    x = random.gammavariate(alpha, 1.0)
    y = random.gammavariate(beta, 1.0)
    
    if x + y <= 0:
        return 0.5
    
    return x / (x + y)


def thompson_score(ad: Ad, ads_stats, horizon: str) -> float:
    """Calculate Thompson Sampling score."""
    alpha, beta = compute_beta_params(ad, ads_stats, horizon)
    return _sample_beta(alpha, beta)


def auction_thompson_best(
    ads: AdsDict,
    parameters: AuctionParams,
    horizon: str = 'month',
) -> Optional[Ad]:
    """Best ad by Thompson Sampling.
    
    It’s important: It’s a randomized algorithm —
    The result may differ with the same input data.
    """
    if not is_valid_auction_ads_dict(ads):
        raise AuctionError(...)
    if is_ads_empty(ads):
        return None
    
    ads_value = get_ads_dict(ads)
    ads_stats = get_ad_stats_from_params(parameters)
    
    def score(ad_id):
        ad = ads_value[ad_id]
        return thompson_score(ad, ads_stats, horizon)
    
    best_id = max(ads_value, key=score)
    return get_ad_from_ads(ads, best_id)


def auction_thompson_weighted(
    ads: AdsDict,
    parameters: AuctionParams,
    horizon: str = 'month',
) -> Optional[Ad]:
    """Weighted random by Thompson scores.
    
    Use it Thompson score as a weight for random choice.
    """
    if not is_valid_auction_ads_dict(ads):
        raise AuctionError(...)
    if is_ads_empty(ads):
        return None
    
    ads_value = get_ads_dict(ads)
    ads_stats = get_ad_stats_from_params(parameters)
    
    elements = list(ads_value.keys())
    weights = [thompson_score(ads_value[aid], ads_stats, horizon) + 1e-9 for aid in elements]
    chosen = random.choices(elements, weights=weights, k=1)[0]
    return get_ad_from_ads(ads, chosen)
```

### Example of use

```python
from rtb_sdk.helpers import create_parameters_ads_stats
from rtb_sdk.constants import SelectionFunc

# Thompson Sampling (best)
params = create_parameters_ads_stats(
    auction_type=SelectionFunc.THOMPSON_BEST,
    ads_stats=ad_stats
)
ad = auction(ads=ads, parameters=params)

# Thompson Sampling (weighted)
params = create_parameters_ads_stats(
    auction_type=SelectionFunc.THOMPSON_WEIGHTED,
    ads_stats=ad_stats
)
ad = auction(ads=ads, parameters=params)
```

### When to use

| Script | Recommendation |
|----------|--------------|
| Stable traffic | MSVV / Damped Pacing |
| Unstable traffic | Thompson Sampling |
| We need to adapt | Thompson Sampling |
| We need predictability | Damped Pacing (linear) |

---

## Summary table of all algorithms

| Algorithm | Type | Status | Parameters | When to use |
|----------|-----|-----------|-----------|-------------------|
| MSVV volume | Score-based | Stateless | — | Fair distribution of impressions |
| MSVV CPM | Score-based | Stateless | — | Optimization of income |
| MSVV hybrid | Score-based | Stateless | — | Balance of impressions and income |
| A2 weakening | Score-based | Stateless | seed | Blurring without tracking |
| Token Bucket | Pacing | **Stateful** | capacity, rate | Precise pacing timelessly |
| Damped Pacing | Score-based | Stateless | decay_type, decay_param | Adjustable attenuation curve |
| Thompson Sampling | Bayesian | Stateless* | prior | Adaptive distribution |

*Thompson Sampling is stateless in this implementation, but sampling yields different results.

---

## What stays out of the box

1 . **A3 (fake money)** - requires per-request bids, not implemented
2 . **Ranking (OBM)** - solves another problem, does not apply
3 . **Budget in the money** - The current implementation uses `volume` as a "pseudo-budget".

---

## Changes to the code

### 1 .`auction/functions/auction_msvv.py` is a new file

```python
"""MSVV and A2 Algorithms for Fair Distribution."""

import math
import random
from typing import Literal, Optional

from rtb_sdk.schemas import Ad, AdsDict, AuctionParams
from rtb_sdk.helpers import (
    get_ad_stats_from_params,
    get_ad_price,
    get_ads_dict,
    get_ad_from_ads,
    get_ad_stats_by_id,
    get_auction_stats_by_type,
    merge_granulated_counters,
    is_ads_empty,
    is_valid_auction_ads_dict,
)
from rtb_sdk.auction.functions.utils import get_real_month_volume
from rtb_sdk.constants import AuctionType
from rtb_sdk.errors import AuctionError, ErrorCodes


# ============================================================================
# Cash for A2 multiplier
# ============================================================================

_PJ_CACHE: dict[int, dict[str, float]] = {}
_PJ_SEED: int | None = None


def _get_pj(ad_id: str, seed: int) -> float:
    """Receive or generate p_j ∈ [1/e, 1] for ad_id.

    RNG paired (seed, ad_id), not seed: random.Random(seed)
    single-handed seed anything ad_id Always give the same first .random(),
    volt.her. All the campaigns would be the same p_j weakening A2 degenerate
    constant (centimetre. Property10/Algorithm 1 article — p_j must have
    i.i.d. biderally).
    """
    global _PJ_CACHE, _PJ_SEED
    
    if seed != _PJ_SEED:
        _PJ_CACHE.clear()
        _PJ_SEED = seed
    
    if ad_id not in _PJ_CACHE:
        rng = random.Random((seed, ad_id))
        w_j = rng.random()
        _PJ_CACHE[ad_id] = math.exp(w_j - 1)
    
    return _PJ_CACHE[ad_id]


def _clear_pj_cache():
    """Clear the cache p_j. Summon on shift seed."""
    global _PJ_CACHE, _PJ_SEED
    _PJ_CACHE.clear()
    _PJ_SEED = None


# ============================================================================
# Support functions
# ============================================================================

Horizon = Literal['month', 'total']


def _get_limit(ad: Ad, horizon: Horizon) -> float:
    """Get a limit for the horizon."""
    if horizon == 'month':
        return get_real_month_volume(ad)
    elif horizon == 'total':
        return ad.get('volume', 0) or 0
    else:
        raise ValueError(f"Unknown horizon: {horizon}")


def _get_shown(ad: Ad, ads_stats, horizon: Horizon) -> float:
    """Get the current display for the horizon.

    Both horizons take 'm' — It’s the only window GranulatedCounter,
    long enough for both scenarios. Granulation t/h/d/w/m — it
    Nested sliding windows ("last N seconds from now"), ?
    non-overlapping bags (centimetre. auction/README.md, Granularity), therefore
    sum(t,h,d,w,m) Re-report the same event before 5 once — do
    cannot be. Difference month/total gives _get_limit (ranking vs raw
    Ad.volume); longer campaigns ~30 days total-horizon will lower
    shown, volt.toward. 'm' he doesn’t see shows older 720 hours.
    """
    stats = get_ad_stats_by_id(ads_stats, ad.get('id'))
    precise = get_auction_stats_by_type(stats, AuctionType.PRECISE)
    fuzzy = get_auction_stats_by_type(stats, AuctionType.FUZZY)
    combined = merge_granulated_counters(precise, fuzzy)
    return get_counter_value(combined, 'm')


def _msvv_decay(remaining: float, total: float) -> float:
    """MSVV decay: 1 - e^(-remaining/total)."""
    if total <= 0:
        return 1.0  # limitless
    ratio = remaining / total
    return 1.0 - math.exp(-ratio)


# ============================================================================
# Variations MSVV score
# ============================================================================

def msvv_score_volume(ad: Ad, ads_stats, horizon: Horizon) -> float:
    """MSVV score by volume."""
    limit = _get_limit(ad, horizon)
    shown = _get_shown(ad, ads_stats, horizon)
    remaining = max(0, limit - shown)
    return _msvv_decay(remaining, limit)


def msvv_score_cpm(ad: Ad, ads_stats, horizon: Horizon) -> float:
    """MSVV score by CPM (revenue)."""
    limit = _get_limit(ad, horizon)
    shown = _get_shown(ad, ads_stats, horizon)
    remaining = max(0, limit - shown)
    cpm = get_ad_price(ad)
    
    if limit <= 0:
        return cpm
    
    ratio = remaining / limit
    decay = 1.0 - math.exp(-ratio)
    return cpm * decay


def msvv_score_hybrid(ad: Ad, ads_stats, horizon: Horizon) -> float:
    """MSVV score hybrid: volume × CPM / 1000 budget."""
    limit = _get_limit(ad, horizon)
    shown = _get_shown(ad, ads_stats, horizon)
    remaining = max(0, limit - shown)
    cpm = get_ad_price(ad)
    
    if limit <= 0:
        return cpm
    
    # "Budget in the money"
    total_budget = limit * cpm / 1000
    remaining_budget = remaining * cpm / 1000
    
    ratio = remaining_budget / total_budget if total_budget > 0 else 1.0
    decay = 1.0 - math.exp(-ratio)
    return cpm * decay


def msvv_score_weakened(score: float, ad_id: str, seed: int, use_weakening: bool) -> float:
    """Apply A2 multiplier."""
    if not use_weakening:
        return score
    p_j = _get_pj(ad_id, seed)
    return score * (1 - p_j)


# ============================================================================
# Functions of the auction
# ============================================================================

def _auction_msvv_impl(
    ads: AdsDict,
    parameters: AuctionParams,
    horizon: Horizon,
    score_type: Literal['volume', 'cpm', 'hybrid'],
    use_weakening: bool,
    is_random: bool,
) -> Optional[Ad]:
    """Overall implementation MSVV."""
    if not is_valid_auction_ads_dict(ads):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, f"Invalid ads: {ads!r}")
    if is_ads_empty(ads):
        return None
    
    ads_value = get_ads_dict(ads)
    ads_stats = get_ad_stats_from_params(parameters)
    seed = parameters.get('seed', 42)
    
    # Select a function score
    if score_type == 'volume':
        score_fn = lambda ad: msvv_score_volume(ad, ads_stats, horizon)
    elif score_type == 'cpm':
        score_fn = lambda ad: msvv_score_cpm(ad, ads_stats, horizon)
    elif score_type == 'hybrid':
        score_fn = lambda ad: msvv_score_hybrid(ad, ads_stats, horizon)
    else:
        raise ValueError(f"Unknown score_type: {score_type}")
    
    def final_score(ad_id):
        ad = ads_value[ad_id]
        base = score_fn(ad)
        return msvv_score_weakened(base, ad_id, seed, use_weakening)
    
    if is_random:
        elements = list(ads_value.keys())
        weights = [final_score(aid) + 1e-9 for aid in elements]
        chosen = random.choices(elements, weights=weights, k=1)[0]
        return get_ad_from_ads(ads, chosen)
    else:
        best_id = max(ads_value, key=final_score)
        return get_ad_from_ads(ads, best_id)


# --------------------------------------------------------------------------
# BEST_VELOCITY variants
# --------------------------------------------------------------------------

def auction_msvv_volume_month_best(
    ads: AdsDict, parameters: AuctionParams
) -> Optional[Ad]:
    """MSVV volume, month-horizon, loosely, best."""
    return _auction_msvv_impl(ads, parameters, 'month', 'volume', False, False)


def auction_msvv_volume_month_random(
    ads: AdsDict, parameters: AuctionParams
) -> Optional[Ad]:
    """MSVV volume, month-horizon, loosely, random."""
    return _auction_msvv_impl(ads, parameters, 'month', 'volume', False, True)


def auction_msvv_volume_month_weakened_best(
    ads: AdsDict, parameters: AuctionParams
) -> Optional[Ad]:
    """MSVV volume, month-horizon, weakened, best."""
    return _auction_msvv_impl(ads, parameters, 'month', 'volume', True, False)


def auction_msvv_volume_month_weakened_random(
    ads: AdsDict, parameters: AuctionParams
) -> Optional[Ad]:
    """MSVV volume, month-horizon, weakened, random."""
    return _auction_msvv_impl(ads, parameters, 'month', 'volume', True, True)


def auction_msvv_volume_total_best(
    ads: AdsDict, parameters: AuctionParams
) -> Optional[Ad]:
    """MSVV volume, horizon, loosely, best."""
    return _auction_msvv_impl(ads, parameters, 'total', 'volume', False, False)


def auction_msvv_volume_total_random(
    ads: AdsDict, parameters: AuctionParams
) -> Optional[Ad]:
    """MSVV volume, horizon, loosely, random."""
    return _auction_msvv_impl(ads, parameters, 'total', 'volume', False, True)


def auction_msvv_volume_total_weakened_best(
    ads: AdsDict, parameters: AuctionParams
) -> Optional[Ad]:
    """MSVV volume, horizon, weakened, best."""
    return _auction_msvv_impl(ads, parameters, 'total', 'volume', True, False)


def auction_msvv_volume_total_weakened_random(
    ads: AdsDict, parameters: AuctionParams
) -> Optional[Ad]:
    """MSVV volume, horizon, weakened, random."""
    return _auction_msvv_impl(ads, parameters, 'total', 'volume', True, True)


# --------------------------------------------------------------------------
# CPM variants
# --------------------------------------------------------------------------

def auction_msvv_cpm_month_best(
    ads: AdsDict, parameters: AuctionParams
) -> Optional[Ad]:
    """MSVV CPM, month-horizon, loosely, best."""
    return _auction_msvv_impl(ads, parameters, 'month', 'cpm', False, False)


def auction_msvv_cpm_month_random(
    ads: AdsDict, parameters: AuctionParams
) -> Optional[Ad]:
    """MSVV CPM, month-horizon, loosely, random."""
    return _auction_msvv_impl(ads, parameters, 'month', 'cpm', False, True)


def auction_msvv_cpm_month_weakened_best(
    ads: AdsDict, parameters: AuctionParams
) -> Optional[Ad]:
    """MSVV CPM, month-horizon, weakened, best."""
    return _auction_msvv_impl(ads, parameters, 'month', 'cpm', True, False)


def auction_msvv_cpm_month_weakened_random(
    ads: AdsDict, parameters: AuctionParams
) -> Optional[Ad]:
    """MSVV CPM, month-horizon, weakened, random."""
    return _auction_msvv_impl(ads, parameters, 'month', 'cpm', True, True)


def auction_msvv_cpm_total_best(
    ads: AdsDict, parameters: AuctionParams
) -> Optional[Ad]:
    """MSVV CPM, horizon, loosely, best."""
    return _auction_msvv_impl(ads, parameters, 'total', 'cpm', False, False)


def auction_msvv_cpm_total_random(
    ads: AdsDict, parameters: AuctionParams
) -> Optional[Ad]:
    """MSVV CPM, horizon, loosely, random."""
    return _auction_msvv_impl(ads, parameters, 'total', 'cpm', False, True)


def auction_msvv_cpm_total_weakened_best(
    ads: AdsDict, parameters: AuctionParams
) -> Optional[Ad]:
    """MSVV CPM, horizon, weakened, best."""
    return _auction_msvv_impl(ads, parameters, 'total', 'cpm', True, False)


def auction_msvv_cpm_total_weakened_random(
    ads: AdsDict, parameters: AuctionParams
) -> Optional[Ad]:
    """MSVV CPM, horizon, weakened, random."""
    return _auction_msvv_impl(ads, parameters, 'total', 'cpm', True, True)


# --------------------------------------------------------------------------
# Hybrid variants
# --------------------------------------------------------------------------

def auction_msvv_hybrid_month_best(
    ads: AdsDict, parameters: AuctionParams
) -> Optional[Ad]:
    """MSVV hybrid, month-horizon, loosely, best."""
    return _auction_msvv_impl(ads, parameters, 'month', 'hybrid', False, False)


def auction_msvv_hybrid_month_random(
    ads: AdsDict, parameters: AuctionParams
) -> Optional[Ad]:
    """MSVV hybrid, month-horizon, loosely, random."""
    return _auction_msvv_impl(ads, parameters, 'month', 'hybrid', False, True)


def auction_msvv_hybrid_month_weakened_best(
    ads: AdsDict, parameters: AuctionParams
) -> Optional[Ad]:
    """MSVV hybrid, month-horizon, weakened, best."""
    return _auction_msvv_impl(ads, parameters, 'month', 'hybrid', True, False)


def auction_msvv_hybrid_month_weakened_random(
    ads: AdsDict, parameters: AuctionParams
) -> Optional[Ad]:
    """MSVV hybrid, month-horizon, weakened, random."""
    return _auction_msvv_impl(ads, parameters, 'month', 'hybrid', True, True)


def auction_msvv_hybrid_total_best(
    ads: AdsDict, parameters: AuctionParams
) -> Optional[Ad]:
    """MSVV hybrid, horizon, loosely, best."""
    return _auction_msvv_impl(ads, parameters, 'total', 'hybrid', False, False)


def auction_msvv_hybrid_total_random(
    ads: AdsDict, parameters: AuctionParams
) -> Optional[Ad]:
    """MSVV hybrid, horizon, loosely, random."""
    return _auction_msvv_impl(ads, parameters, 'total', 'hybrid', False, True)


def auction_msvv_hybrid_total_weakened_best(
    ads: AdsDict, parameters: AuctionParams
) -> Optional[Ad]:
    """MSVV hybrid, horizon, weakened, best."""
    return _auction_msvv_impl(ads, parameters, 'total', 'hybrid', True, False)


def auction_msvv_hybrid_total_weakened_random(
    ads: AdsDict, parameters: AuctionParams
) -> Optional[Ad]:
    """MSVV hybrid, horizon, weakened, random."""
    return _auction_msvv_impl(ads, parameters, 'total', 'hybrid', True, True)
```

### 2 .`constants/constants.py` - Add constants

```python
class SelectionFunc:
    # ... existing ...
    
    # MSVV — volume
    MSVV_VOLUME_MONTH_BEST: AuctionSelectionFunc = 'msvv_volume_month_best'
    MSVV_VOLUME_MONTH_RANDOM: AuctionSelectionFunc = 'msvv_volume_month_random'
    MSVV_VOLUME_MONTH_WEAKENED_BEST: AuctionSelectionFunc = 'msvv_volume_month_weakened_best'
    MSVV_VOLUME_MONTH_WEAKENED_RANDOM: AuctionSelectionFunc = 'msvv_volume_month_weakened_random'
    MSVV_VOLUME_TOTAL_BEST: AuctionSelectionFunc = 'msvv_volume_total_best'
    MSVV_VOLUME_TOTAL_RANDOM: AuctionSelectionFunc = 'msvv_volume_total_random'
    MSVV_VOLUME_TOTAL_WEAKENED_BEST: AuctionSelectionFunc = 'msvv_volume_total_weakened_best'
    MSVV_VOLUME_TOTAL_WEAKENED_RANDOM: AuctionSelectionFunc = 'msvv_volume_total_weakened_random'
    
    # MSVV — CPM
    MSVV_CPM_MONTH_BEST: AuctionSelectionFunc = 'msvv_cpm_month_best'
    MSVV_CPM_MONTH_RANDOM: AuctionSelectionFunc = 'msvv_cpm_month_random'
    MSVV_CPM_MONTH_WEAKENED_BEST: AuctionSelectionFunc = 'msvv_cpm_month_weakened_best'
    MSVV_CPM_MONTH_WEAKENED_RANDOM: AuctionSelectionFunc = 'msvv_cpm_month_weakened_random'
    MSVV_CPM_TOTAL_BEST: AuctionSelectionFunc = 'msvv_cpm_total_best'
    MSVV_CPM_TOTAL_RANDOM: AuctionSelectionFunc = 'msvv_cpm_total_random'
    MSVV_CPM_TOTAL_WEAKENED_BEST: AuctionSelectionFunc = 'msvv_cpm_total_weakened_best'
    MSVV_CPM_TOTAL_WEAKENED_RANDOM: AuctionSelectionFunc = 'msvv_cpm_total_weakened_random'
    
    # MSVV — Hybrid
    MSVV_HYBRID_MONTH_BEST: AuctionSelectionFunc = 'msvv_hybrid_month_best'
    MSVV_HYBRID_MONTH_RANDOM: AuctionSelectionFunc = 'msvv_hybrid_month_random'
    MSVV_HYBRID_MONTH_WEAKENED_BEST: AuctionSelectionFunc = 'msvv_hybrid_month_weakened_best'
    MSVV_HYBRID_MONTH_WEAKENED_RANDOM: AuctionSelectionFunc = 'msvv_hybrid_month_weakened_random'
    MSVV_HYBRID_TOTAL_BEST: AuctionSelectionFunc = 'msvv_hybrid_total_best'
    MSVV_HYBRID_TOTAL_RANDOM: AuctionSelectionFunc = 'msvv_hybrid_total_random'
    MSVV_HYBRID_TOTAL_WEAKENED_BEST: AuctionSelectionFunc = 'msvv_hybrid_total_weakened_best'
    MSVV_HYBRID_TOTAL_WEAKENED_RANDOM: AuctionSelectionFunc = 'msvv_hybrid_total_weakened_random'
```

### 3 .`auction/auction.py` - register functions

```python
from rtb_sdk.auction.functions.auction_msvv import (
    # volume month
    auction_msvv_volume_month_best,
    auction_msvv_volume_month_random,
    auction_msvv_volume_month_weakened_best,
    auction_msvv_volume_month_weakened_random,
    # volume total
    auction_msvv_volume_total_best,
    auction_msvv_volume_total_random,
    auction_msvv_volume_total_weakened_best,
    auction_msvv_volume_total_weakened_random,
    # cpm month
    auction_msvv_cpm_month_best,
    auction_msvv_cpm_month_random,
    auction_msvv_cpm_month_weakened_best,
    auction_msvv_cpm_month_weakened_random,
    # cpm total
    auction_msvv_cpm_total_best,
    auction_msvv_cpm_total_random,
    auction_msvv_cpm_total_weakened_best,
    auction_msvv_cpm_total_weakened_random,
    # hybrid month
    auction_msvv_hybrid_month_best,
    auction_msvv_hybrid_month_random,
    auction_msvv_hybrid_month_weakened_best,
    auction_msvv_hybrid_month_weakened_random,
    # hybrid total
    auction_msvv_hybrid_total_best,
    auction_msvv_hybrid_total_random,
    auction_msvv_hybrid_total_weakened_best,
    auction_msvv_hybrid_total_weakened_random,
)


AUCTIONS: dict[str, Callable] = {
    # ... existing ...
    
    # MSVV volume month
    'msvv_volume_month_best': auction_msvv_volume_month_best,
    'msvv_volume_month_random': auction_msvv_volume_month_random,
    'msvv_volume_month_weakened_best': auction_msvv_volume_month_weakened_best,
    'msvv_volume_month_weakened_random': auction_msvv_volume_month_weakened_random,
    # MSVV volume total
    'msvv_volume_total_best': auction_msvv_volume_total_best,
    'msvv_volume_total_random': auction_msvv_volume_total_random,
    'msvv_volume_total_weakened_best': auction_msvv_volume_total_weakened_best,
    'msvv_volume_total_weakened_random': auction_msvv_volume_total_weakened_random,
    # MSVV CPM month
    'msvv_cpm_month_best': auction_msvv_cpm_month_best,
    'msvv_cpm_month_random': auction_msvv_cpm_month_random,
    'msvv_cpm_month_weakened_best': auction_msvv_cpm_month_weakened_best,
    'msvv_cpm_month_weakened_random': auction_msvv_cpm_month_weakened_random,
    # MSVV CPM total
    'msvv_cpm_total_best': auction_msvv_cpm_total_best,
    'msvv_cpm_total_random': auction_msvv_cpm_total_random,
    'msvv_cpm_total_weakened_best': auction_msvv_cpm_total_weakened_best,
    'msvv_cpm_total_weakened_random': auction_msvv_cpm_total_weakened_random,
    # MSVV hybrid month
    'msvv_hybrid_month_best': auction_msvv_hybrid_month_best,
    'msvv_hybrid_month_random': auction_msvv_hybrid_month_random,
    'msvv_hybrid_month_weakened_best': auction_msvv_hybrid_month_weakened_best,
    'msvv_hybrid_month_weakened_random': auction_msvv_hybrid_month_weakened_random,
    # MSVV hybrid total
    'msvv_hybrid_total_best': auction_msvv_hybrid_total_best,
    'msvv_hybrid_total_random': auction_msvv_hybrid_total_random,
    'msvv_hybrid_total_weakened_best': auction_msvv_hybrid_total_weakened_best,
    'msvv_hybrid_total_weakened_random': auction_msvv_hybrid_total_weakened_random,
}
```

### 4. `tests/auction/_functions.py` - add tests

```python
# Listed FUNCTIONS add:
MSVV_FUNCTIONS = [
    # volume month
    ('msvv_volume_month_best', auction_msvv_volume_month_best),
    ('msvv_volume_month_random', auction_msvv_volume_month_random),
    ('msvv_volume_month_weakened_best', auction_msvv_volume_month_weakened_best),
    ('msvv_volume_month_weakened_random', auction_msvv_volume_month_weakened_random),
    # volume total
    ('msvv_volume_total_best', auction_msvv_volume_total_best),
    ('msvv_volume_total_random', auction_msvv_volume_total_random),
    ('msvv_volume_total_weakened_best', auction_msvv_volume_total_weakened_best),
    ('msvv_volume_total_weakened_random', auction_msvv_volume_total_weakened_random),
    # cpm month
    ('msvv_cpm_month_best', auction_msvv_cpm_month_best),
    ('msvv_cpm_month_random', auction_msvv_cpm_month_random),
    ('msvv_cpm_month_weakened_best', auction_msvv_cpm_month_weakened_best),
    ('msvv_cpm_month_weakened_random', auction_msvv_cpm_month_weakened_random),
    # cpm total
    ('msvv_cpm_total_best', auction_msvv_cpm_total_best),
    ('msvv_cpm_total_random', auction_msvv_cpm_total_random),
    ('msvv_cpm_total_weakened_best', auction_msvv_cpm_total_weakened_best),
    ('msvv_cpm_total_weakened_random', auction_msvv_cpm_total_weakened_random),
    # hybrid month
    ('msvv_hybrid_month_best', auction_msvv_hybrid_month_best),
    ('msvv_hybrid_month_random', auction_msvv_hybrid_month_random),
    ('msvv_hybrid_month_weakened_best', auction_msvv_hybrid_month_weakened_best),
    ('msvv_hybrid_month_weakened_random', auction_msvv_hybrid_month_weakened_random),
    # hybrid total
    ('msvv_hybrid_total_best', auction_msvv_hybrid_total_best),
    ('msvv_hybrid_total_random', auction_msvv_hybrid_total_random),
    ('msvv_hybrid_total_weakened_best', auction_msvv_hybrid_total_weakened_best),
    ('msvv_hybrid_total_weakened_random', auction_msvv_hybrid_total_weakened_random),
]
```

### 5 Extension of `AuctionParams` schema under `seed` is a must-do step, skipped above

All A2-weakened variants and `_auction_msvv_impl` read `parameters.get('seed', 42)`. `Ad`/`AuctionParams` is a `TypedDict` (regular `dict` without runtime checks), so reading the extra key won't fall by itself. But ** public `create_parameters_ads_stats` constructor now only accepts `auction_type` and `ads_stats` ** (hardcut, without `**kwargs`) is an example in the "UE" section below, causing it with `seed=42` , in its current form will drop to `TypeError`.

```python
# schemas/auction_schemas.py
type AuctionSelectionFunc = Literal[
    'best_one', 'random_one', 'best_price', 'random_price',
    'best_velocity', 'random_velocity', 'best_heuristics', 'random_heuristics',
    # + new msvv_* / a2_* significance — otherwise is_valid_auction_params reject them
    'msvv_volume_month_best', 'msvv_volume_month_random', ...,
]

class ParametersAdsStats(DiscriminatedTypedDict):
    auction_type: AuctionSelectionFunc
    ads_stats: AdStats
    seed: int  # field, optional (.get(..., 42))


# helpers/auction/stats_helpers.py
def create_parameters_ads_stats(
    auction_type: AuctionSelectionFunc,
    ads_stats: AdStats,
    seed: int = 42,
) -> ParametersAdsStats:
    return {
        '__type': 'ParametersAdsStats',
        'auction_type': auction_type,
        'ads_stats': ads_stats,
        'seed': seed,
    }
```

`load_parameters_ads_stats` (deserialization from JSON) also needs to be updated to toss `seed`. Without this step, the entire "Optional Attenuation Multiplier A2" section is not connected to the public API.

