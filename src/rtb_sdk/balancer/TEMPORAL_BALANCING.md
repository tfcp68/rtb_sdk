# Temporal balancing: architecture and algorithms

## Problem.

### What happened before?

The original `balance_traffic` received a scalar `total_traffic_volume` and distributed it.
as a homogeneous flow without reference to time:

- **`date_factor = 1.0` ** - hardcut in `ad_to_inner`; real `start_date` /`end_date`
  The campaigns were ignored.
- **`freq = ad_frequency_limit['d']` ** - only daily granularity was taken and
  used as a cap on **whole** period. Limit «1 000 show-day» upon 30-daytime
  Period means the total cap of 30 000, not 1 000.
- **`BalancingParams` ** did not contain a time window - it is impossible to calculate the correct
  Frequency caps.
- **Seasonality is not counted**: night traffic is much less than day traffic, LP
  He distributed the volumes evenly.

### What's done

1. `BalancingParams` added `period_start`, `period_end`, `temporal_context`.
2: Frequency constraints are correctly translated into all granularities (`t` /`h` /`d` /`w` /`m`).
3.`total_traffic_volume` is broken down into hourly slots according to the seasonal profile of the logs.
4: Campaign activity is accounted for per-slot through `is_ad_active` and `n_active_hours`.
5 Histogram Frequency Restriction Correction Accounts for Superactive Saturation
   Pre-computed per-ad, per-hour in `AdditionalContext.corrected_user_activity_ratio`.
6: Hourly `tag_probabilities`s are stored inside `AdditionalContext.tags_probability`.
7: Cross-slot budget tracking (`remaining`) with `math.ceil` prevents
   zeroing out low-budget slots.

---

## Data structures

### `BalancingParams` Extension

```python
class BalancingParams(TypedDict, total=False):
    # ── already existing ──────────────────────────────────────────────────
    total_traffic_volume:      int
    tag_probabilities:         dict[VocabName, dict[RawTag, float]]
    vocabs:                    OuterVocabs
    objective:                 OBJECTIVES
    max_n_categories:          int
    min_category_probability:  float
    n_threads:                 int

    # ── temporal ──────────────────────────────────────────────────────
    period_start:     datetime         # beginning (aware datetime)
    period_end:       datetime         # period, non-inclusive
    temporal_context: TemporalContext  # constructed build_temporal_context
```

`temporal_context`, `period_start` and `period_end` are mandatory for all three.
Before transferring to `optimize`, these keys are cut out.

---

### `AdditionalContext` - data of one time slot

```python
class AdditionalContext(TypedDict):
    weight:                        float
    corrected_user_activity_ratio: dict[AdId, float]
    tags_probability:              dict[VocabName, dict[RawTag, float]] | None
```

| field | sense |
|---|---|
| `weight` | Percentage of this hour’s traffic from the total: `total_t = total × weight` |
| `corrected_user_activity_ratio` | per-ad saturation `coef ∈ (0, 1]`; pre-computed in `build_temporal_context` |
| `tags_probability` | log-tag probabilities; `None` → fallback on `params['tag_probabilities']` |

---

### `TemporalContext` – Hourly Data Package

```python
class TemporalContext(TypedDict):
    mode:    AggregationMode                   # 'hour_of_day' or 'hour_of_week'
    context: dict[HourType, AdditionalContext] # data for each clock type
```

`TemporalContext` is cached: built once from CSV logs, transmitted to all
Follow-up calls via `params['temporal_context']`.

---

### `HistoricalLogsConfig` – Log Source Configuration

```python
class HistoricalLogsConfig(TypedDict, total=False):
    path:             str                # path CSV-file (mandatory)
    timestamp_col:    str                # column timestamp ISO-8601 (mandatory)
    count_col:        str | None         # event column; None = line = 1
    user_id_col:      str | None         # None → corrected_user_activity_ratio = 1.0
    chunk_size:       int                # default 10_000
    aggregation_mode: AggregationMode    # default 'hour_of_day'
    timezone:         str                # IANA, default 'UTC'
```

---

### `LogStreamState` is the state of the streaming passage

```python
class LogStreamState(TypedDict):
    counts:              dict[HourType, float]          # h_type → event_count
    user_counts_by_hour: dict[HourType, dict[str, int]] # h_type → {uid → count}
    user_counts_total:   dict[str, int]                 # uid → total_count
    tag_counts:          TagCountsByHour
    mode:                AggregationMode
```

In one pass, `process_log_chunk` fills all four aggregates simultaneously.
`user_counts_by_hour` is used to calculate the ratio at the time limits (`h`).
`user_counts_total` is for non-hourly (`d` /`w` /`m`) time-total limits.

---

## 1 Algorithm: Correct Campaign Activity

Instead of `date_factor`, the `is_ad_active(ad, slot_dt)` hourly check is used:
The campaign is included only in those slots when it is really active.

```python
def is_ad_active(ad: Any, slot_dt: datetime) -> bool:
    start = ad.get('start_date')
    end = ad.get('end_date')
    if start is None or end is None:
        return True
    return start <= slot_dt < end
```

The number of active slots in the period is calculated by O(1) using `n_active_hours`:

```python
def n_active_hours(ad: Any, period: PeriodWindow) -> int:
    overlap_start = max(ad.start_date, period.period_start)
    overlap_end   = min(ad.end_date,   period.period_end)
    return max(0, int((overlap_end - overlap_start).total_seconds() // 3600))
```

It is done once outside the loop over slots (O(1) per ad, not O(H)).

---

## 2 Algorithm: Full Frequency Limitations

### `compute_hour_limit` is the hourly limit of all granularities.

Converts every granularity into displays/hour and take a minimum:

| granularity | conversion |
|---|---|
| `'t'` (10 mine) | `limit × 6` |
| `'h'` | `limit` |
| `'d'` | `limit / 24` |
| `'w'` | `limit / 168` |
| `'m'` | `limit / (30.44 × 24)` |

### `compute_period_limit` is the total limit for the period

Converts each granularity to impressions beyond `n_hours` and takes a minimum of:

```python
def compute_period_limit(freq_limits: dict, n_hours: float) -> float:
    # 't': limit × n_hours × 6
    # 'h': limit × n_hours
    # 'd': limit × (n_hours / 24)
    # 'w': limit × (n_hours / 168)
    # 'm': limit × (n_hours / (24 × 30.44))
    return min(caps) if caps else float('inf')
```

Used in two places:
- `_iter_slots` is the initialization of `remaining[ad_id] = min(volume, period_limit)`.
- `prepare_slot_ads` is the calculation of `corrected_max` for the slot.

---

## 3 Algorithm: Histogram Correction of Frequency Limitations

### Motivation.

The distribution of the number of requests per user is strongly skewed to the right: a small number
“Superactive” users generate a disproportionate share of traffic.
Once they reach the custom frequency cap, they stop receiving impressions.
The effective volume is lower than the theoretical.

### Saturation factor

$$\text{coef} = \frac{\sum_i \min(r_i, C)}{\sum_i r_i} \in (0,\; 1]$$

Where $r_i$ is the number of requests of the $i$ user, $C$ is the user cap for the period.

```
  requests
  profitably.
     │
  80 ┤▓
  70 ┤▓▓               ▓ = oversize (circumcised)
  60 ┤▓▓▓
  50 ┤▓▓▓▓
     ├════════════════════════ cap (user_freq_limit period)
  30 ┤░░░░░░░░         ░ = standardization (delivered)
  20 ┤░░░░░░░░░░░░
  10 ┤░░░░░░░░░░░░░░░░░
   5 ┤░░░░░░░░░░░░░░░░░░░░░░░
   0 └────────────────────────────────────────────────
     ←──── active ────→←────────── passive ─────→
```

### Pre-computation in `build_temporal_context`

For each `h` hour and `ad` announcement, `_compute_user_ratio` is called:

```python
def _compute_user_ratio(ad, user_counts_h, user_counts_total, n_hours) -> float:
    user_hour_limit = compute_hour_limit(user_freq)

    if 'h' in user_freq.value:
        # Hour limit → per-hour histogram
        return apply_histogram_correction(1.0, list(user_counts_h.values()), user_hour_limit)
    else:
        # Non-hourly limit → histogram + period-total limit
        user_period_limit = user_hour_limit * n_hours
        return apply_histogram_correction(1.0, list(user_counts_total.values()), user_period_limit)
```

**Why two ways:**
At non-hourly limits (`d` /`w` /`m`), `compute_hour_limit` returns the fraction <1
(e.g. `d=5` → `5/24 ≈ 0.208`) If you use a per-hour histogram with
`user_hour_limit = 0.208`, then `min(r_i_h, 0.208)` for any `r_i_h ≥ 1` will give 0.208.
The coefficient collapses to 0. The right path is to take the total user queries.
For the entire period, compare it to the total period limit.

### Applications in `prepare_slot_ads`

```python
ratio = slot_context['corrected_user_activity_ratio'].get(ad_id, 1.0)
corrected_max = min(ad_max, int(total_limit * ratio))
```

---

## 4 algorithm: hourly LP partitioning

### Formal staging

The `[period_start, period_end)` period contains $H$ of whole hours.
For each hour $t$:

$$total_t = total \times w_{h_t}, \quad \sum_{h=0}^{n-1} w_h = 1$$

where $w_{h_t }$ is the weight of the hour type of the current slot from `AdditionalContext.weight`.

For each ad in the slot:

$$\text{slot\_max\_vol} = \left\lceil \frac{\text{corrected\_max}}{n\_\text{active}} \right\rceil$$

`ceil` instead of `int` prevents the zeroing of low-budget ads
(See the section "Cross-slot tracking").

### Generator `_iter_slots`

```python
def _iter_slots(ads, params):
    # Precalculation (once):
    n_active  = {ad_id: n_active_hours(ad, period) for ad_id, ad in ads.items()}
    remaining = {ad_id: min(volume, int(period_limit)) for ...}

    for t in range(H):
        slot_dt = period_start + timedelta(hours=t)
        h = hour_type(slot_dt, mode)
        slot_ctx = ctx_by_hour.get(h)

        slot_ads = prepare_slot_ads(ads, slot_dt, period, slot_ctx, n_active, remaining)
        inner_ads = {ad_id: ad_to_inner(ad) for ad_id, ad in slot_ads.items()}

        yield inner_ads, slot_params, n_active, remaining
```

For `hour_of_day` with a period of 30 days: 720 slots, 24 unique type of watch.
All three public functions use the same generator.

### Cross-slot budget tracking (`remaining`)

**Problem:** `math.ceil(0.33) = 1`, for 720 slots the sum is 720 >> 240 (`corrected_max`).

**Decision (Variant B):**
```python
# Initialization:
remaining[ad_id] = min(ad_max, int(period_limit))   # without ratio

# In prepare_slot_ads:
slot_max_vol = math.ceil(corrected_max / n)
slot_max_vol = min(slot_max_vol, remaining[ad_id])  # leftover

# In the defiant function after optimize():
remaining[ad_id] = max(0, remaining.get(ad_id, 0) - vol)
```

`remaining` is a mutated vocabulary. The calling function updates it in its cycle.
The generator sees the updates on the next iteration via the same link.

---

## 5 Algorithm: Streaming Log Processing

### Memory consumption

O(24) or O(168) for `counts` plus O(Users) for `user_counts_by_hour` /`user_counts_total`
plus O(H × Vocabs × Tags) for tags. One chunk (~10 000 lines × line width) immediately
released by GC.

### Single pass to `build_temporal_context`

```python
with open(config['path'], newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    chunk = []
    for row in reader:
        chunk.append(row)
        if len(chunk) >= chunk_size:
            process_log_chunk(chunk, state, config, tz, tag_col_map)
            chunk.clear()
    if chunk:
        process_log_chunk(chunk, state, config, tz, tag_col_map)
```

In one pass, `process_log_chunk` accumulates:
- `state['counts']` is for slot scales.
- `state['user_counts_by_hour'][h][uid]` is a per-hour user activity.
- `state['user_counts_total'][uid]` is the total activity for the entire log.
- `state['tag_counts']` is for `tags_probability` (if `tag_col_map` is specified).

After the passage, `AdditionalContext` is built for each watch type.

### `build_seasonality_profile` - Profile only

Simplified version: `counts` only, without user data and tags.
O(24/168) is used when you only need a profile without full context.

---

## General scheme of work

```
╔══════════════════════════════════════════════════════════════════════════╗
║  Step 0 — Preparation of context (once, before calling the balancer)       ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  config: HistoricalLogsConfig  ← path, timestamp_col, user_id_col, …    ║
║  ads:    dict[AdId, Ad]        ← necessary corrected_user_activity_ratio ║
║  period: PeriodWindow          ← { period_start, period_end }            ║
║                            │                                             ║
║                            ▼                                             ║
║              build_temporal_context(config, ads, period)                 ║
║                                                                          ║
║          In a single streaming pass CSV:                                   ║
║          ┌─────────────────┬──────────────────────┐                      ║
║          ▼                 ▼                      ▼                      ║
║  process_log_chunk     accumulation             accumulate_tag_counts       ║
║  normalize_counts      user_counts_by_hour    normalize_tag_counts        ║
║                        user_counts_total                                  ║
║          │                 │                      │                      ║
║          ▼                 ▼                      ▼                      ║
║   weights[h]       _compute_user_ratio(ad, h)  tags_probability[h]       ║
║                    per-ad, per-hour ratio                                 ║
║          └─────────────────┴──────────────────────┘                      ║
║                            │                                             ║
║                            ▼                                             ║
║    TemporalContext {                                                      ║
║        mode: 'hour_of_day',                                              ║
║        context: {                                                         ║
║            h: AdditionalContext {                                         ║
║                weight,                                                    ║
║                corrected_user_activity_ratio: {ad_id: coef},             ║
║                tags_probability,                                          ║
║            }                                                              ║
║        }                                                                  ║
║    }   ← cached; one-time                     ║
║                                                                          ║
╠══════════════════════════════════════════════════════════════════════════╣
║  Step 1 — Stitching context into params                                     ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  params = {                                                              ║
║      'period_start':         ...,                                        ║
║      'period_end':           ...,                                        ║
║      'total_traffic_volume': ...,                                        ║
║      'temporal_context':     context,   ← stepwise 0                     ║
║      # + any other BalancingParams                                    ║
║  }                                                                       ║
║                                                                          ║
╠══════════════════════════════════════════════════════════════════════════╣
║  Step 2 — Calling the balancing function                                   ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  temporal_balance_traffic(ads, params)                                   ║
║                                                                          ║
║  Precalculation (once):                                              ║
║    n_active[ad_id]  = n_active_hours(ad, period)                         ║
║    remaining[ad_id] = min(volume, compute_period_limit(...))             ║
║    base_inner       = outer_to_inner_optimize_params(params)             ║
║                                                                          ║
╠══════════════════════════════════════════════════════════════════════════╣
║  Step 3 — Cycle by H clock-slots                                        ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  H = ⌊(period_end − period_start) / 1 ?⌋                                ║
║                                                                          ║
║  for t in range(H):                                                      ║
║  ┌──────────────────────────────────────────────────────────────────┐    ║
║  │ slot_dt = period_start + timedelta(hours=t)                      │    ║
║  │ h = hour_type(slot_dt, mode)       # 0–23 or 0–167             │    ║
║  │ slot_ctx = context['context'][h]                                 │    ║
║  │ total_t = round(total × slot_ctx['weight'])                      │    ║
║  │                                                                  │    ║
║  │ slot_ads = prepare_slot_ads(                                     │    ║
║  │     ads, slot_dt, period, slot_ctx, n_active, remaining         │    ║
║  │ )   # ceil(corrected_max / n_active), limited remaining        │    ║
║  │                                                                  │    ║
║  │ inner_ads = {ad_to_inner(ad) for ad in slot_ads}                 │    ║
║  │ tag_t = slot_ctx['tags_probability'] or params['tag_probs']      │    ║
║  └──────────────────────────────────────────────────────────────────┘    ║
║                                                                          ║
╠══════════════════════════════════════════════════════════════════════════╣
║  Step 4 — N launches optimize (solver, unchanged)         ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  result_t = optimize(inner_ads, slot_params)                             ║
║                                                                          ║
║  for ad_id, vol in result_t.items():                                     ║
║      result[ad_id] += vol                                                ║
║      remaining[ad_id] = max(0, remaining[ad_id] - vol)  # cross-country-sloth    ║
║                                                                          ║
╠══════════════════════════════════════════════════════════════════════════╣
║  Step 5 — Assembly of the result                                               ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  dict[AdId, int]  — the volume of impressions for the entire period for each ad   ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
```

---

## File summary table

| File | Change of change |
|---|---|
| `schemas/balancer_schemas.py` | Added `temporal_context`, `period_start`, `period_end` in `BalancingParams` |
| `temporal/types.py` | New: `AdditionalContext`, `TemporalContext` (mode + context dict). `LogStreamState`: `user_counts_by_hour` + `user_counts_total` instead `user_counts`. Deleted: `UserActivityHistogram` |
| `temporal/corrections.py` | `compute_period_limit` (public). `prepare_slot_ads`: new signature `slot_context` and `remaining`; `math.ceil` instead `int` |
| `temporal/slots.py` | `resolve_weights` weight out `TemporalContext.context` |
| `temporal/seasonality.py` | `process_log_chunk` accumulate `user_counts_by_hour` and `user_counts_total` simultaneously |
| `temporal/balance.py` | `build_temporal_context`: new-signature `(config, ads, period, *, tag_col_map)`. Public functions: parameter removed `context`, `params` must contain `temporal_context`. `_iter_slots`: `remaining` + yield 4-cortege. `_compute_user_ratio`: two-way/time-limit |

`optimize`, `solver`, `proto_solver`, and `categories` are not affected.

---

## Prediction of the recommended rate (proposal)

### Setting the task

**«What is it? CPM-The campaign will implement the given budget for the period?»**

Objective: to find the minimum rate of `b*` such that the expected volume of impressions
This rate is equal to the target `budget`.
The delivery curve according to the historical auction data.

### New types of data

#### `BidLandscape`

```python
class BidLandscape(TypedDict):
    cdf: list[tuple[float, float]]
    # Empiric CDF auction-price clearing.
    # Sorted list (price_cpm, cumulative_win_rate).
    # win_rate(b) = P(clearing_price ≤ b) — linear interpolation.
    # Example: [(10.0, 0.05), (50.0, 0.30), (100.0, 0.60), (300.0, 0.95)]
```

Built from auction logs in one go: sorting clearing prices,
We have to adjust the accumulated share of `cdf`.

#### `BidForecastResult`

```python
class BidForecastResult(TypedDict):
    recommended_bid:      float                    # recommended CPM-rate
    expected_impressions: int                      # expectation b*
    expected_win_rate:    float                    # middle-class win rate period [0, 1]
    budget_utilization:   float                    # expected_impressions / budget (≤ 1.0)
    delivery_curve:       list[tuple[float, int]]  # [(bid, impressions)] — delivery curve
```

`budget_utilization < 1.0` – traffic in targeting is not enough even when
maximum bet.

### Signature.

```python
def predict_recommended_bid(
    budget:           int,
    period:           PeriodWindow,
    targeting:        dict[VocabName, list[RawTag]],
    bid_landscape:    BidLandscape,
    temporal_context: TemporalContext,
    total_traffic:    int,
    *,
    ad_frequency_limit:   dict | None = None,
    user_frequency_limit: dict | None = None,
    n_points:             int = 50,
) -> BidForecastResult
```

`temporal_context` should be built using `build_temporal_context`
(same context used for balancing. `total_traffic`)
The expected total traffic for the period for all targeting.

### The algorithm.

```
predict_recommended_bid(budget, period, targeting, bid_landscape, temporal_context, total_traffic):

    n_hours = (period_end - period_start).total_seconds() / 3600

    # 1. Targeted traffic by hourly types
    available = {}
    for h, slot_ctx in temporal_context['context'].items():
        traffic_h   = total_traffic × slot_ctx['weight']
        match_h     = compute_targeting_match(targeting, slot_ctx['tags_probability'])
        available[h] = traffic_h × match_h

    # 2. Total drop by frequency of announcement
    period_limit    = compute_period_limit(ad_frequency_limit, n_hours)
    available_total = min(Σ available[h], period_limit)

    # 3. Amendment user_frequency_limit (optionally)
    if user_frequency_limit:
        user_hour_limit   = compute_hour_limit(user_frequency_limit)
        user_period_limit = user_hour_limit × n_hours
        # apply_histogram_correction I need a histogram of user_counts_total —
        # can be transferred separately or received from LogStreamState contextualize
        available_total = apply_histogram_correction(available_total, histogram, user_period_limit)

    # 4. Delivery curve: n_points uniformly cdf
    min_bid, max_bid = bid_landscape.cdf[0][0], bid_landscape.cdf[-1][0]
    curve = []
    for b in linspace(min_bid, max_bid, n_points):
        win_rate    = interpolate_cdf(bid_landscape.cdf, b)
        expected    = min(available_total × win_rate, available_total)
        curve.append((b, int(expected)))

    # 5. Binary search b* such expected(b*) ≈ budget
    if curve[-1][1] < budget:
        # There is not enough traffic, even if max_bid
        b_star = max_bid
    elif curve[0][1] >= budget:
        # The bet is already redundant at min_bid
        b_star = min_bid
    else:
        b_star = binary_search(curve, target=budget)

    win_rate_star     = interpolate_cdf(bid_landscape.cdf, b_star)
    expected_star     = min(int(available_total × win_rate_star), budget_hard_cap)

    return BidForecastResult(
        recommended_bid      = b_star,
        expected_impressions = expected_star,
        expected_win_rate    = win_rate_star,
        budget_utilization   = expected_star / budget,
        delivery_curve       = curve,
    )
```

### `compute_targeting_match`

Auxiliary function: evaluates the share of traffic that falls into targeting,
`tags_probability` slot.

```
compute_targeting_match(targeting, tags_probability) -> float:
    if tags_probability is None:
        return 1.0   # no data → We believe that there is a complete coincidence
    match = 1.0
    for vocab, requested_tags in targeting.items():
        vocab_probs = tags_probability.get(vocab, {})
        # OR inside vocab: summarise the probabilities of the requested tags
        vocab_match = sum(vocab_probs.get(tag, 0.0) for tag in requested_tags)
        # AND between vocab: multiply
        match × = min(vocab_match, 1.0)
    return match
```

**Important limitation:** This model assumes statistical independence vocab
In practice, correlations (e.g., geo × os) may understate or
If you have shared log data, it's more accurate to rank by
Tag intersections, not marginal probabilities.

### Communication with the rest of the package

| component | role predict_recommended_bid |
|---|---|
| `TemporalContext.context[h]['weight']` | traffic rate `h` |
| `TemporalContext.context[h]['tags_probability']` | score `match_h` through `compute_targeting_match` |
| `compute_period_limit` | summative cap campaign (`corrections.py`) |
| `apply_histogram_correction` | correction user_frequency_limit (`corrections.py`) |
| `BidLandscape.cdf` | win rate at this rate (novelty) |
