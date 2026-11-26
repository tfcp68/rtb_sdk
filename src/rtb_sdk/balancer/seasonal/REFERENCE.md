# Reference: `rtb_sdk.balancer.seasonal` package

## Three-level architecture

| Level | Functions | Meaning | Frequency |
|---------|---------|-------|---------|
| 1 | `optimize` | Clean LP-optimizer within one hour | No |
| 2 | `hour_balance_traffic`, `hour_add_new_balanced_campaign`, `hour_predict_rebalance`, `hour_balance_by_sellout` | One hour with frequency data | Yes: `ad_frequency_limit → hour`, `user_activity_ratio`, tagged by the hour |
| 3 | `seasonal_*` | Date range → clockiteration | Takes ready `SeasonalContext` |

Level-2 functions live in `functions/*.py`. They take `hour_context: AdditionalContext | None = None`:
- with `hour_context=None` - without user coefficients and hourly tags;
- with `hour_context`, `user_activity_ratio` and `tags_probability` are used.

Level-3 functions (`seasonal_*`) in `balance.py` divide the period into time slots and
call the corresponding level-2 functions for each slot.

---

## Package structure

```
seasonal/
├── types.py        — re-export public schemas; interior
├── slots.py        — slotting
├── corrections.py  — slotting
├── seasonality.py  — flow-aggregation CSV-den
└── balance.py      — level-3 function + build_seasonal_context
```

Level-2 function (`hour_balance_traffic`, `hour_add_new_balanced_campaign`,
`hour_predict_rebalance`, `hour_balance_by_sellout`) implemented `balancer/functions/*.py`
and are re-exported from `seasonal/__init__.py` under names with the prefix `hour_`.

---

## Data types (`types.py`)

### Basic aliases

```python
AggregationMode = Literal['hour_of_day', 'hour_of_week']
HourType        = int   # 0–23 (hour_of_day) or 0–167 (hour_of_week)
```

`AggregationMode` is used in all fields of `mode` and `aggregation_mode`.
`HourType` is the key of dictionaries indexed by the time slot.

---

### `PeriodWindow`

```python
class PeriodWindow(TypedDict):
    period_start: datetime   # beginning (aware datetime, recommended UTC)
    period_end:   datetime   # period, non-inclusive
```

Validated pair start/ending. The presence in the signature means «period already checked».

---

### `HourlyWeights`

```python
class HourlyWeights(TypedDict):
    mode:    AggregationMode
    weights: dict[HourType, float]   # sum(weights.values()) ≈ 1.0
```

Normalized seasonality profile.

| mode | keys weights | sense |
|---|---|---|
| `'hour_of_day'` | 0–23 | The profile is applied cyclically to each day |
| `'hour_of_week'` | 0–167 | 7 days × 24 hourly, weekdays/weekend |

Used external `resolve_weights` and `build_seasonality_profile`.
Within a seasonal package, weights are stored inside `AdditionalContext.weight`.

---

### `AdditionalContext`

```python
class AdditionalContext(TypedDict):
    weight: float
    user_activity_ratio: dict[AdId, float]
    tags_probability: dict[VocabName, dict[RawTag, float]] | None
```

Data for one time slot. `build_seasonal_context` is created for each.
`HourType`, entering the period.

| field | type | appointment |
|---|---|---|
| `weight` | `float` | Normalized Share of Traffic for That Hour (full-hour ≈ 1.0) |
| `user_activity_ratio` | `dict[AdId, float]` | saturation `coef ∈ (0, 1]` for each announcement; `coef = Σ min(r_i, lim) / Σ r_i` |
| `tags_probability` | `dict[VocabName, dict[RawTag, float]] \| None` | Probability of tags from the log for this hour; `None` → used `params['tag_probabilities']` |

---

### `SeasonalContext`

```python
class SeasonalContext(TypedDict):
    mode:    AggregationMode
    context: dict[HourType, AdditionalContext]
```

A bundle of hourly data prepared before the balancing functions are called.
It's built `build_seasonal_context`. It's sewn into `BalancingParams['seasonal_context']`.

| field | type | appointment |
|---|---|---|
| `mode` | `AggregationMode` | aggregation: `'hour_of_day'` (0–23) or `'hour_of_week'` (0–167) |
| `context` | `dict[HourType, AdditionalContext]` | data for each active time slot |

---

### `HistoricalLogsConfig`

```python
class HistoricalLogsConfig(TypedDict, total=False):
    path:             str                # mandatory
    timestamp_col:    str                # mandatory
    count_col:        str | None         # None → line = 1 event
    user_id_col:      str | None         # None → user_activity_ratio = 1.0
    chunk_size:       int                # default 10_000
    aggregation_mode: AggregationMode    # default 'hour_of_day'
    timezone:         str                # IANA, default 'UTC'
```

`path` and `timestamp_col` are mandatory in meaning - `build_seasonal_context`
`KeyError` will be picked up if you don't have them. `user_id_col` is needed to calculate.
`user_activity_ratio`; without it, the coefficient is always `1.0`.

---

### `TagCountsByHour`

```python
TagCountsByHour = dict[HourType, dict[VocabName, dict[RawTag, float]]]
```

An intermediate drive before normalization. Filled in via `accumulate_tag_counts`.
It is normalized through `normalize_tag_counts` and enters `AdditionalContext['tags_probability']`.

---

### `LogStreamState`

```python
class LogStreamState(TypedDict):
    counts:              dict[HourType, float]          # {h_type: event_count}
    user_counts_by_hour: dict[HourType, dict[str, int]] # {h_type: {user_id: count}}
    user_counts_total:   dict[str, int]                 # {user_id: total_count}
    tag_counts:          TagCountsByHour
    mode:                AggregationMode
```

Variable state in stream processing. transmitted to `process_log_chunk` and
It's being updated on site.

| field | utilization |
|---|---|
| `counts` | base `AdditionalContext.weight` (normalize `normalize_counts`) |
| `user_counts_by_hour` | per-hour histogram; calculating `user_activity_ratio` clockwise (`h`) limit `user_frequency_limit` |
| `user_counts_total` | histogram; non-hourly (`d`/`w`/`m`) limit — through period-total limit |
| `tag_counts` | for `tags_probability`; hollow dict if `tag_col_map` passed on |

---

## `BalancingParams` Extension

Seasonal functions read the following keys from `params`:

```python
class BalancingParams(TypedDict, total=False):
    # ... field ...

    seasonal_context: SeasonalContext   # sewn build_seasonal_context
    period_start:     datetime          # beginning (aware datetime)
    period_end:       datetime          # period, non-inclusive
```

`seasonal_context`, `period_start` and `period_end` are mandatory for everyone.
three public functions of the seasonal balancer.
In internal `optimize`, these keys are removed from the settings.

---

## Level-2 function (`balancer/functions/*.py`)

They're working within a ** one hour**. They're accepting ads in `Ad` format.
Apply hourly limits and `user_activity_ratio`, then call `optimize`.

All four functions assume an optional parameter:

```python
hour_context: AdditionalContext | None = None
```

With `hour_context=None`, saturation coefficients are equal to `1.0`, tags are taken from `params`.

---

### `hour_balance_traffic`

```python
def balance_traffic(
    ads:          dict[AdId, Ad],
    params:       BalancingParams,
    *,
    hour_context: AdditionalContext | None = None,
) -> BalanceResult   # dict[AdId, int]
```

Balancing within one hour:
1. `prepare_hour_ads(ads, hour_context)` uses `compute_hour_limit` and `user_activity_ratio`.
2.`ad_to_inner` for each ad (freq overlaps max_vol).
3. `outer_to_inner_optimize_params` (tags from `hour_context.tags_probability` if given).
4. `optimize(inner_ads, inner_params)`.

---

### `hour_add_new_balanced_campaign`

```python
def add_new_balanced_campaign(
    ads:          dict[AdId, Ad],
    ad_vol_distr: ProjectedAdVolumes,
    params:       BalancingParams,
    *,
    hour_context: AdditionalContext | None = None,
) -> AddCampaignResult
```

Freezes ads from `ad_vol_distr` (min_vol = max_vol = fixed volume)
Optimizes the remaining traffic for new ads.

---

### `hour_predict_rebalance`

```python
def predict_rebalance(
    ads:          dict[AdId, Ad],
    ad_vol_distr: ProjectedAdVolumes,
    params:       BalancingParams,
    *,
    hour_context: AdditionalContext | None = None,
) -> RebalanceResult
```

Free re-optimization. Returns new distribution and delta relative to
`ad_vol_distr`. It doesn't change the real state.

---

### `hour_balance_by_sellout`

```python
def balance_by_sellout(
    ads:          dict[AdId, Ad],
    params:       BalancingBySelloutParams,
    *,
    hour_context: AdditionalContext | None = None,
) -> BalancingBySelloutResult
```

Binary search on φ*: guarantees a minimum percentage of sales.
Logic is similar to `functions/balance_by_sellout.py`, but works through
`prepare_hour_ads` instead of direct conversion.

---

## Level-3 function (`balance.py`)

### `build_seasonal_context`

```python
def build_seasonal_context(
    config:      HistoricalLogsConfig,
    ads:         dict[AdId, Ad],
    period:      PeriodWindow,
    *,
    tag_col_map: dict[str, str] | None = None,
) -> SeasonalContext
```

Builds `SeasonalContext` for a **one streaming pass** CSV file.

**Input data:**

| parameter | type | description |
|---|---|---|
| `config` | `HistoricalLogsConfig` | fileway, column timestamp, options |
| `ads` | `dict[AdId, Ad]` | pronouncement; calculator `user_activity_ratio` by `user_frequency_limit` each announcement |
| `period` | `PeriodWindow` | balancing-time; used `n_active_hours` |
| `tag_col_map` | `dict[VocabName, str] \| None` | `{VocabName: column_name_in_csv}`; `None` → No tagging |

**In one pass, accumulates:**
- `counts` = normalized slot weights (`AdditionalContext.weight`).
- `user_counts_by_hour` and `user_counts_total` → histograms of user activity
  To calculate `user_activity_ratio` for each ad.
- `tag_counts` → `tags_probability` (if `tag_col_map` is specified).

**Calculation `user_activity_ratio` :**

For every `h` hour slot and every `ad` ad:
- If `user_frequency_limit` contains an hour limit (`'h'` in `value`):
  `coef = Σ min(r_i_h, user_hour_limit) / Σ r_i_h` , where `r_i_h` is a request
  `i` user at this time of year.
- Otherwise (`'d'` /`'w'` /`'m'`):
  `coef = Σ min(r_i, user_period_limit) / Σ r_i`, where `r_i` is summarised
  user for the entire log, `user_period_limit = user_hour_limit × n_hours`.
- If there is no limit or no user data, then `coef = 1.0`.

**Output:** `SeasonalContext` filled with `AdditionalContext`
for each `HourType` from 0 to 23 (or 167).

**Exceptions:** `ValueError` (fileless), `FileNotFoundError`, `KeyError` (no `path` or `timestamp_col`).

**Memory consumption:** O(24/168) for counts + O(H × Users) for `user_counts_by_hour`
+ O(H × Vocabs × Tags) for tags.

---

### `seasonal_balance_traffic`

```python
def seasonal_balance_traffic(
    ads:    dict[AdId, Ad],
    params: BalancingParams,
) -> BalanceResult   # dict[AdId, int]
```

`balance_traffic` mirrors: distributes traffic based on seasonal profile and
hourly frequency limits.

**Mandatory keys in `params` :** `period_start`, `period_end`.
`total_traffic_volume`, `seasonal_context`.

**How it works:**
1. Breaks down `total_traffic_volume` by clock according to `AdditionalContext.weight`.
2. For each active slot: filter out ads, apply pre-computed
   `user_activity_ratio` and `remaining` (cross-slot tracking)
3. Converts `Ad → InnerAd`, calls `optimize(inner_ads, slot_params)`.
4. Write off the assigned volume from `remaining[ad_id]`.
5 sums up the results of all slots.

**Output:** `dict[AdId, int]` — totals for the entire period.

---

### `seasonal_add_new_balanced_campaign`

```python
def seasonal_add_new_balanced_campaign(
    ads:          dict[AdId, Ad],
    ad_vol_distr: ProjectedAdVolumes,   # dict[AdId, int | float]
    params:       BalancingParams,
) -> AddCampaignResult
```

Mirroring `add_new_balanced_campaign`: Adds new campaigns to existing campaigns
distribution.

**Input data:**

| parameter | type | description |
|---|---|---|
| `ads` | `dict[AdId, Ad]` | postings — old and new |
| `ad_vol_distr` | `dict[AdId, int\|float]` | Recorded volumes of existing announcements for the period |
| `params` | `BalancingParams` | same mandatory keys, what `seasonal_balance_traffic` |

**Freeze mechanism:** For each slot, ads from `ad_vol_distr` are received
`min_vol = max_vol = ad_vol_distr[id] // n_active_hours` : The remainder of slot traffic
It's going into new announcements.

**Output:**

```python
class AddCampaignResult(TypedDict):
    report:           dict[AdId, int]   # postings
    new_ads_volumes:  dict[AdId, int]   # new
```

---

### `seasonal_predict_rebalance`

```python
def seasonal_predict_rebalance(
    ads:          dict[AdId, Ad],
    ad_vol_distr: ProjectedAdVolumes,
    params:       BalancingParams,
) -> RebalanceResult
```

Mirror `predict_rebalance`: Calculates the optimal distribution for new
parameter and returns the delta. **Doesn’t change** realization.

**Input data:** same, what `seasonal_add_new_balanced_campaign`.
`ad_vol_distr` here is the current distribution, the base for the delta.

**Output:**

```python
class RebalanceResult(TypedDict):
    report:       dict[AdId, int]   # distribution
    volume_delta: dict[AdId, int]   # new − current
```

---

### `seasonal_balance_by_sellout`

```python
def seasonal_balance_by_sellout(
    ads:    dict[AdId, Ad],
    params: BalancingBySelloutParams,
) -> BalancingBySelloutResult
```

Extension of `balance_by_sellout` for date range, per hour slot
to `hour.balance_by_sellout`.

**Mandatory keys in `params` :** `period_start`, `period_end`.
`total_traffic_volume`, `seasonal_context`, `accuracy_percent`.

**How it works:**
1 breaks down the period into hour slots via `_iter_slots`.
2. For each slot, it calls `hour.balance_by_sellout(slot_ads, slot_params, hour_context=slot_ctx)`.
3 sums up the results of the slots.
4. `sellout_percent = min(result[ad_id] / ad.volume × 100 for ad in ads if ad.volume > 0)`.

Ads with `volume=0` (unlimited) are excluded from the final `sellout_percent` calculation.

**Output:**

```python
class BalancingBySelloutResult(TypedDict):
    report:          dict[AdId, int]   # summaries
    sellout_percent: float             # minimum-share (0–100)
```

---

## Support functions

### `slots.py`

```python
def resolve_weights(context: SeasonalContext) -> HourlyWeights
```
Extracts the weight profile from `SeasonalContext` :
`HourlyWeights(mode=context['mode'], weights={h: ac['weight'] for h, ac in context['context'].items()})`.

```python
def compute_hours(period: PeriodWindow) -> int
```
The number of hours in a period.

```python
def hour_type(dt: datetime, mode: AggregationMode) -> HourType
```
`0–23` at `'hour_of_day'`, `0–167` at `'hour_of_week'`.

```python
def n_active_hours(ad: Any, period: PeriodWindow) -> int
```
The number of period slots in which the campaign is active: O(1) through the overlap formula.
If `start_date` /`end_date` is not specified, it is considered active for the entire period.

---

### `corrections.py`

```python
def is_ad_active(ad: Any, slot_dt: datetime) -> bool
```
`True` if `start_date ≤ slot_dt < end_date`. In the absence of dates, always `True`.

```python
def compute_hour_limit(freq_limits: dict) -> float
```
The most stringent hourly limit of all granularities:

| granularity | displaying/hour |
|---|---|
| `'t'` (10 mine) | `limit × 6` |
| `'h'` | `limit` |
| `'d'` | `limit / 24` |
| `'w'` | `limit / 168` |
| `'m'` | `limit / (30.44 × 24)` |

There are no limits to `float('inf')`.

```python
def compute_period_limit(freq_limits: dict, n_hours: float) -> float
```
The total limit for the entire period of `n_hours` of all granularities. Takes a minimum.
There are no limits to `float('inf')`.
Used in both `prepare_slot_ads` and `_iter_slots` for initialization
`remaining` dictionary (cross-slot budget tracking).

```python
def apply_histogram_correction(
    limit:             float,
    histogram:         list[int] | None,
    user_period_limit: float,
) -> float
```
Multiply the limit by the share of realistically achievable impressions:
`coef = Σ min(r_i, user_period_limit) / Σ r_i`.
`histogram=None` or `user_period_limit=inf` → `coef = 1.0`.

```python
def prepare_hour_ads(
    ads:          dict[AdId, Any],
    hour_context: AdditionalContext | None = None,
) -> dict[AdId, dict]
```
Applies hourly limits and saturation ratio to ads.
Intended for level-2 functions - **does not divide ** volume by number
Active slots, unlike `prepare_slot_ads`.

For each announcement:
1. `hour_limit = compute_hour_limit(ad_frequency_limit)` — screen-limit/hour.
2. `ratio = hour_context['user_activity_ratio'].get(id, 1.0)`.
3. `vol = min(ad.volume, floor(hour_limit)) * ratio`.
4. Skip if `vol <= 0`.

With `hour_context=None`: `ratio=1.0`, the limit is only from `ad_freq`.
In the absence of `ad_frequency_limit` : `lim=inf → vol = ad.volume * ratio`.

```python
def prepare_slot_ads(
    ads:          dict[AdId, Any],
    slot_dt:      datetime,
    period:       PeriodWindow,
    slot_context: AdditionalContext,
    n_active:     dict[AdId, int],
    remaining:    dict[AdId, int] | None = None,
) -> dict[AdId, dict]
```
Returns `Ad` with modified `volume` and `min_vol=0` for a single slot.

The sequence for each ad:
1: Skip inactive at this hour (`is_ad_active`).
2. Skip ads from `n_active == 0`.
3: Skip budget-exhausted ads (`remaining[id] == 0`).
4. Calculate `total_limit = compute_period_limit(ad_freq, n_hours)`.
5. Take the pre-computed `ratio = slot_context['user_activity_ratio'].get(id, 1.0)`.
6. `corrected_max = min(ad_max, int(total_limit × ratio))`.
7 .`slot_max_vol = math.ceil(corrected_max / n_active)` - `ceil` prevents
   Zero low-budget ads with `slot_share < 1`.
8: Limit `remaining[id]` (cross-slot tracking).
9: Skip ads with zero `slot_max_vol` total.

---

### `seasonality.py`

```python
def build_seasonality_profile(config: HistoricalLogsConfig) -> HourlyWeights
```
Builds only a seasonality profile (without user data and tags). O(24/168) memory.
Use `balance.build_seasonal_context` to collect all units simultaneously.

```python
def process_log_chunk(
    chunk:       list[dict[str, str]],
    state:       LogStreamState,
    config:      HistoricalLogsConfig,
    tz:          ZoneInfo,
    tag_col_map: dict[VocabName, str] | None = None,
) -> None
```
Updates `state` in place in one pass on the bunk of the CSV strings.
- Parsite timestamp and adds events to `state['counts']`.
- If `user_id_col` is given, it accumulates `user_counts_by_hour[h][uid]`.
  and `user_counts_total[uid]`.
- If `tag_col_map` is given, it calls `accumulate_tag_counts`.

```python
def normalize_counts(counts: dict[HourType, float]) -> dict[HourType, float]
```
Normalizes to the sum of 1.0. `ValueError` if `total == 0`.

```python
def accumulate_tag_counts(
    row:         dict[str, str],
    h_type:      HourType,
    tag_counts:  TagCountsByHour,
    tag_col_map: dict[VocabName, str],
) -> None
```
Adds single line CSV tags to the `tag_counts[h_type]` drive.

```python
def normalize_tag_counts(tag_counts: TagCountsByHour) -> TagCountsByHour
```
Normalizes tag counters to probabilities: `sum(probs[vocab]) == 1.0` for each vocab and h_type.

---

## Typical use case

```python
from datetime import datetime, timezone
from rtb_sdk.balancer.seasonal import (
    build_seasonal_context,
    seasonal_balance_traffic,
    seasonal_add_new_balanced_campaign,
    seasonal_predict_rebalance,
    HistoricalLogsConfig,
    SeasonalContext,
    AdditionalContext,
    PeriodWindow,
)

# --- Constructing the context from CSV-den ---
config = HistoricalLogsConfig(
    path='logs/impressions.csv',
    timestamp_col='ts',
    user_id_col='uid',
    timezone='Europe/Moscow',
)
period = PeriodWindow(
    period_start=datetime(2024, 6, 1, tzinfo=timezone.utc),
    period_end=datetime(2024, 6, 8, tzinfo=timezone.utc),
)
context = build_seasonal_context(config, ads, period)

# --- Stitching context into params ---
params = {
    'period_start':         datetime(2024, 6, 1, tzinfo=timezone.utc),
    'period_end':           datetime(2024, 6, 8, tzinfo=timezone.utc),
    'total_traffic_volume': 1_000_000,
    'seasonal_context':     context,
}

# --- Balancing ---
result = seasonal_balance_traffic(ads, params)
# {'ad1': 350000, 'ad2': 650000, ...}

# --- Adding new campaigns ---
add_result = seasonal_add_new_balanced_campaign(ads, result, params)
# add_result['report']          → postings
# add_result['new_ads_volumes'] → new

# --- Rebalancing forecast ---
pred = seasonal_predict_rebalance(ads, result, new_params)
# pred['report']       → distribution
# pred['volume_delta'] → change result
```

---

## `_iter_slots` internal generator

`_iter_slots(ads, params)` is a private generator used by all three of them.
Returns the 4 motorcade `(inner_ads, slot_params, n_active, remaining)`.

**Precalculates once:**
- `n_active: dict[AdId, int]` is the number of active hours for each ad.
- `remaining: dict[AdId, int]` - Initial Budget = `min(volume, period_limit)`
  It is mutated after each `optimize()`.
- `base_inner` is the baseline setting for `optimize` (without seasonal keys).

**On each iteration:**
- Takes the `AdditionalContext` for the current watch type.
- Calls `prepare_slot_ads` with current `remaining`.
- Converts `Ad → InnerAd` and substitutes `tag_probabilities`.

**Cross-slot tracking (`remaining` ):**
The calling function debits the actually assigned volume:
```python
remaining[ad_id] = max(0, remaining.get(ad_id, 0) - vol)
```
The generator sees the updates on the next iteration via the mutated link.
This ensures that the total volume does not exceed `period_limit`, even if
`math.ceil` - rounding up individual slots.

---

## Prediction of the recommended rate (proposal)

### New types of data

#### `BidLandscape`

```python
class BidLandscape(TypedDict):
    cdf: list[tuple[float, float]]
    # Empirical function of auction clearing prices distribution.
    # Sorted list of couples (price_cpm, cumulative_win_rate).
    # win_rate(b) = share, wager b.
    # Linear interpolation between points.
    # Example: [(10.0, 0.05), (50.0, 0.30), (100.0, 0.60), (300.0, 0.95)]
```

Built from historical auction logs: for each auction is taken
Clearing price (second place price or floor), data is sorted and rationed.

#### `BidForecastResult`

```python
class BidForecastResult(TypedDict):
    recommended_bid:      float                    # recommended CPM-rate
    expected_impressions: int                      # Expected impressions at the recommended rate
    expected_win_rate:    float                    # middle-class win rate period [0, 1]
    budget_utilization:   float                    # expected_impressions / budget (≤ 1.0)
    delivery_curve:       list[tuple[float, int]]  # [(bid, impressions)] — cut-off
```

`budget_utilization < 1.0` means that targeted traffic is available.
It is not enough to manage the budget, even at the maximum rate.

---

### `predict_recommended_bid`

```python
def predict_recommended_bid(
    budget:           int,
    period:           PeriodWindow,
    targeting:        dict[VocabName, list[RawTag]],
    bid_landscape:    BidLandscape,
    seasonal_context: SeasonalContext,
    total_traffic:    int,
    *,
    ad_frequency_limit:   dict | None = None,
    user_frequency_limit: dict | None = None,
    n_points:             int = 50,
) -> BidForecastResult
```

**Parameters:**

| parameter | type | description |
|---|---|---|
| `budget` | `int` | target volume of impressions for the period |
| `period` | `PeriodWindow` | campaigning |
| `targeting` | `dict[VocabName, list[RawTag]]` | OR inside vocab, AND between vocab |
| `bid_landscape` | `BidLandscape` | clearing-price |
| `seasonal_context` | `SeasonalContext` | pre-computed contextuality `tags_probability` clockwise |
| `total_traffic` | `int` | expected total traffic for the period (target-wise) |
| `ad_frequency_limit` | `dict \| None` | campaign frequency restrictions; influences cap |
| `user_frequency_limit` | `dict \| None` | user-limit; amendment `apply_histogram_correction` |
| `n_points` | `int` | number of points `delivery_curve` visualize |

---

### The algorithm.

**1 . Targeted hourly traffic.**

For each `h` from `seasonal_context['context']`:

```
traffic_h   = total_traffic × context[h]['weight']
match_h     = compute_targeting_match(targeting, context[h]['tags_probability'])
available_h = traffic_h × match_h
```

`compute_targeting_match`: for each `VocabName` sums up the probabilities
When asked for `RawTag` (OR inside vocab), the results are multiplied (AND between vocab).
At `tags_probability is None` → `1.0`.

**2 - Restriction on the frequency of the announcement.**

```
period_limit    = compute_period_limit(ad_frequency_limit, n_hours)
available_total = min(Σ_h available_h, period_limit)
```

**3. Delivery curve.**

For `n_points` bets evenly along the `bid_landscape.cdf` axis:

```
win_rate(b)  = linear interpolation cdf
expected(b)  = min(Σ_h available_h × win_rate(b), available_total)
```

If `user_frequency_limit` is given, `apply_histogram_correction` is used.
`available_total` with `user_period_limit = user_hour_limit × n_hours`.

**4. Recommended rate.**

Binary search for `b*` by delivery curve: `expected(b*) ≈ budget`.

- If `expected(max_bid) < budget` returns to `max_bid`,
  `budget_utilization = expected(max_bid) / budget < 1.0`
  (Target traffic is not enough).
- If `expected(min_bid) ≥ budget` returns, `min_bid` returns.
  (The rate is already excessive, the budget will adjust even at the minimum rate).
