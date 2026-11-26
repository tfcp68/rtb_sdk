# Balancer — internal types and conversion

> This file is intended **only for balancer developers**. Users of the public API do not need it.
>
> Purpose: a reference document for **code generation and refactoring**. Code changes will soon be made to bring the public API in line with the README: functions will accept `Ad` instead of `InnerAd`, and the conversion will move inside.

---

## Open design questions

### BalancerAuctionData.vocabs — assess the necessity

The `vocabs: OuterVocabs` field in `BalancerAuctionData` duplicates the key structure already represented in `tag_probabilities: dict[VocabName, dict[RawTag, float]]`. Options:

| Option | Pros | Cons |
|---------|-------|--------|
| Keep `vocabs` | an explicit list of all vocabulary tags (including tags with zero probability) | duplication |
| Remove `vocabs` | a simpler type | loss of the explicit tag enumeration |
| Replace `vocabs` with `set[VocabName]` | easier for checks | we lose the tag list |

The decision requires analyzing the real use of `vocabs` inside `auction()`.

### auction — moving to the auction module

The function `balancer.auction` is a balancer-specific ad selection strategy. It logically belongs to `rtb_sdk/auction`. It should be moved together with `AuctionParamsBalanced` and `BalancerAuctionData` as a new `AuctionSelectionFunc` type or a separate module.

---

## Internal data types

### InnerVocab / InnerVocabs

```python
type InnerVocab  = list[FullTag]              # ['geo:msk', 'geo:spb']
type InnerVocabs = dict[VocabName, InnerVocab]  # {'geo': ['geo:msk', 'geo:spb']}
```

Built from `OuterVocabs` via `outer_to_inner_optimize_params`. After `build_new_vocabs` they may contain the synthetic tag `TAG_OTHER` to merge unused vocabulary values.

---

### InnerAd

The internal representation of an ad. Not used in the public API — created inside functions from `Ad`.

```python
class InnerAd(TypedDict):
    id:          AdId
    targets:     dict[VocabName, list[FullTag]]  # tags in FullTag format (already with the vocab prefix)
    min_vol:     int                              # minimum impression volume
    max_vol:     int                              # maximum impression volume
    price:       float                            # CPM price (for MAX_MONEY)
    date_factor: float                            # seasonal coefficient
    freq:        int                              # hard cap of impressions
```

An empty list of tags for a vocabulary is interpreted as "all tags of the vocabulary".

---

### RequestFlow

The result of the category selection algorithm. Stores a specific combination of tags (one from each vocabulary) and its probability.

> Former name in the code: `Category`. To be renamed during refactoring.

```python
class RequestFlow(TypedDict):
    tags:        tuple[FullTag, ...]  # a tuple of tags
    probability: float                # Π P(tag) over all tags of the category
```

---

### RequestFlowWithAd

Extends `RequestFlow` with the field `ad_id`. Used in `build_tag_category_hash` to build the inverted `tag → flows` index.

> Former name in the code: `AdCategory`. To be renamed during refactoring.

```python
class RequestFlowWithAd(RequestFlow):
    ad_id: AdId
```

---

### FullTagWithProbability

A tag with a probability. Formed when vocabularies are rebuilt inside `optimize`.

> Former name in the code: `InnerTag`. To be renamed during refactoring.

```python
class FullTagWithProbability(TypedDict):
    tag:         FullTag
    probability: float
```

---

### OptimizeParams

The internal parameters type. Accepted only by the `optimize` function. Built from `BalancingParams` via `outer_to_inner_optimize_params`.

Inherits all `BalancingParams` fields and **overrides** two fields in `FullTag` format:

```python
class OptimizeParams(BalancingParams, total=False):
    tag_probabilities: dict[FullTag, float]        # flat format: 'geo:msk' → float
    vocabs:            dict[VocabName, list[FullTag]]  # {'geo': ['geo:msk', 'geo:spb']}
```

The remaining fields (`total_traffic_volume`, `objective`, `max_n_categories`, `min_category_probability`, `n_threads`) are inherited from `BalancingParams` unchanged.

---


## Ad → InnerAd conversion

Performed inside each public offline function before calling `optimize`.

| `InnerAd` field | Source in `Ad` | Note |
|----------------|-----------------|------------|
| `id` | `Ad.id` | unchanged |
| `targets` | `Ad.targets.value` | `RawTag → FullTag`: the prefix `VocabName:` is added to each tag |
| `max_vol` | `Ad.volume` | `0` in `Ad` → no upper bound |
| `price` | `Ad.cpm` | unchanged |
| `freq` | `Ad.ad_frequency_limit.value['d']` | daily limit; `0` → no limit |
| `min_vol` | — | always `0` (not represented in `Ad`) |
| `date_factor` | — | always `1.0` (not represented in `Ad`) |

> `min_vol` and `date_factor` are balancer concepts absent from `Ad`. If needed they can be added to `BalancingParams` as an override dictionary `dict[AdId, ...]`.

---

## BalancingParams → OptimizeParams conversion

Performed via `outer_to_inner_optimize_params`.

| Field | Transformation |
|------|----------------|
| `vocabs` | `{"geo": ["msk", "spb"]}` → `{"geo": ["geo:msk", "geo:spb"]}` |
| `tag_probabilities` | `{"geo": {"msk": 0.6}}` → `{"geo:msk": 0.6}` (nested → flat, the vocab prefix is added) |
| other fields | unchanged |

---

## What needs to change in the code

Below is a list of code changes that will bring the implementation in line with the updated README.

### 1. Public function signatures

Files: `functions/balance_traffic.py`, `functions/add_campaign.py`, `functions/predict_rebalance.py`, `utils/report.py`

- Replace `dict[AdId, InnerAd]` → `dict[AdId, Ad]` in the function parameters
- Add an `ad_to_inner(ad)` conversion step before calling `optimize`

### 2. The Ad → InnerAd converter

Add to `helpers/balancer/inner_ad_helpers.py` the function:

```python
def ad_to_inner(ad: Ad, vocabs: OuterVocabs) -> InnerAd:
    """Converts a public Ad into an InnerAd for LP optimization."""
    targets: dict[VocabName, list[FullTag]] = {
        vocab: [f'{vocab}:{tag}' for tag in tags]
        for vocab, tags in get_ad_targetvector(ad).get('value', {}).items()
    }
    freq_limits = get_ad_frequency_limit(ad)
    freq = int(freq_limits['value'].get('d', 0))
    return create_inner_ad(
        id=get_ad_id(ad),
        targets=targets,
        min_vol=0,
        max_vol=get_ad_volume(ad),
        price=get_ad_price(ad),
        date_factor=1.0,
        freq=freq if freq > 0 else 1,
    )
```

### 3. Validation

- `validate_helpers.py`: update `validate_optimize` for `dict[AdId, Ad]` instead of `dict[AdId, InnerAd]`
- Run the conversion **after** validation

### 4. Type renames

Files: `schemas/balancer_schemas.py`, `helpers/balancer/category_helpers.py`, `helpers/balancer/full_tag_helpers.py`, `helpers/balancer/optimize_params_helpers.py`, `helpers/balancer/validate_helpers.py`, `balancer/functions/*.py`, `balancer/utils/categories.py`, `balancer/solver/solver.py`

| Old name | New name |
|------------|-----------|
| `Category` | `RequestFlow` |
| `AdCategory` | `RequestFlowWithAd` |
| `InnerTag` | `FullTagWithProbability` |
| `OuterOptimizeParams` | `BalancingParams` |
| `AdVolumesDistribution` | `ProjectedAdVolumes` |
| `ParametersBalanced` | `AuctionParamsBalanced` |

- Rename `helpers/balancer/category_helpers.py` → `request_flow_helpers.py`
- Rename `helpers/balancer/parameters_balanced_helpers.py` → `auction_params_balanced_helpers.py`
- Update all imports and type annotations in the affected files

### 5. BalancerAuctionData — a single type (remove InnerBalancerAuctionData)

Files: `schemas/balancer_schemas.py`, `helpers/balancer/balancer_auction_data_helpers.py`, `balancer/functions/auction.py`, `balancer/utils/report.py`

```python
# Remove the class InnerBalancerAuctionData.
# BalancerAuctionData is now a single type with OuterVocabs:

class BalancerAuctionData(TypedDict):
    vocabs:            OuterVocabs                           # dict[VocabName, list[RawTag]]
    tag_probabilities: dict[VocabName, dict[RawTag, float]]
    ads_distribution:  ProjectedAdVolumes
    ads_probabilities: dict[AdId, float]
    ads_total:         int
```

Inside `auction()` the conversion of `tag_probabilities` from nested to flat is performed locally (without a separate type).

### 6. BalanceResult — an alias for ProjectedAdVolumes

File: `schemas/balancer_schemas.py`

```python
# Was:
type BalanceResult = dict[AdId, int]

# Now:
type BalanceResult = ProjectedAdVolumes
```

### 8. OptimizeParams — inheriting from BalancingParams

File: `schemas/balancer_schemas.py`

```python
# Was:
class OptimizeParams(TypedDict, total=False):
    total_traffic_volume:     int
    tag_probabilities:        dict[FullTag, float]
    vocabs:                   InnerVocabs
    objective:                OBJECTIVES
    max_n_categories:         int
    min_category_probability: float
    n_threads:                int

# Now:
class OptimizeParams(BalancingParams, total=False):
    tag_probabilities: dict[FullTag, float]
    vocabs:            dict[VocabName, list[FullTag]]
```

### 9. Tests and fixtures

- `tests/balancer/fixtures/` — update the `ads` format from `InnerAd` dictionaries to `Ad` objects via `create_ad()`
- `tests/balancer/cases/*.json` — update the input data format
