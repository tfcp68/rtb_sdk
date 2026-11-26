# RTB SDK // Adwords algorithm (Vazirani)

## Table of contents

- [RTB SDK // Adwords algorithm (Vazirani)](#rtb-sdk--adwords-algorithm-vazirani)
  - [Table of contents](#table-of-contents)
  - [Quick start](#quick-start)
  - [Algorithm description](#algorithm-description)
    - [The Adwords problem](#the-adwords-problem)
    - [Why the greedy algorithm does not work](#why-the-greedy-algorithm-does-not-work)
    - [Relation to the Online Bipartite Matching problem](#relation-to-the-online-bipartite-matching-problem)
    - [The key idea: a random price](#the-key-idea-a-random-price)
    - [Where `e^(wj − 1)` comes from: the link to the MSVV algorithm](#where-ewj--1-comes-from-the-link-to-the-msvv-algorithm)
    - [Why the competitive ratio 1−1/e is optimal](#why-the-competitive-ratio-11e-is-optimal)
    - [A2 vs A3 comparison](#a2-vs-a3-comparison)
  - [Data types](#data-types)
    - [AdwordsAlgorithmId](#adwordsalgorithmid)
    - [AdwordsAdState](#adwordsadstate)
    - [AdwordsState](#adwordsstate)
    - [AdwordsMatchResult](#adwordsmatchresult)
    - [Changes to Ad](#changes-to-ad)
  - [Algorithm A2 (Single-Valued)](#algorithm-a2-single-valued)
    - [A2 initialization](#a2-initialization)
    - [A2 request handling](#a2-request-handling)
    - [Impression limit](#impression-limit)
    - [A2 theoretical guarantees](#a2-theoretical-guarantees)
  - [Algorithm A3 (Small)](#algorithm-a3-small)
    - [A3 initialization](#a3-initialization)
    - [A3 request handling](#a3-request-handling)
    - [Fake money: why it is needed](#fake-money-why-it-is-needed)
    - [The Small applicability condition](#the-small-applicability-condition)
    - [A3 theoretical guarantees](#a3-theoretical-guarantees)
  - [State management](#state-management)
    - [Option 1: explicit AdwordsState](#option-1-explicit-adwordsstate)
    - [Option 2: integration via AdStats](#option-2-integration-via-adstats)
  - [Examples](#examples)
    - [Full A2 cycle (Option 1)](#full-a2-cycle-option-1)
    - [Full A3 cycle (Option 1)](#full-a3-cycle-option-1)
    - [Full A2 cycle (Option 2 via AdStats)](#full-a2-cycle-option-2-via-adstats)

## Quick start

An extension of the base `auction` module for the problem of allocating advertising budgets (Adwords) using Vazirani's algorithm ("Towards a Practical, Budget-Oblivious Algorithm for the Adwords Problem under Small Bids").

The algorithm guarantees a **competitive ratio of 1−1/e** — that is, on average it obtains at least **63.2%** of the revenue that an ideal algorithm knowing all future requests in advance could obtain. The guarantee holds under the condition of small bids (more in the section ["The Small applicability condition"](#the-small-applicability-condition)).

**Option 1 — explicit state (`AdwordsState`):**

```python
from rtb_sdk.auction.adwords import initialize_adwords, auction_adwords
from rtb_sdk.constants import AdwordsAlgorithm

# Initialization once per session
state = initialize_adwords(ads=ads, algorithm=AdwordsAlgorithm.A2_SINGLE_VALUED)

# On every request
result = auction_adwords(ads=filtered_ads, state=state)
ad_id = result['matched_ad']   # AdId or None
state = result['state']         # updated state
```

**Option 2 — via `AdStats` (compatible with `auction()`):**

```python
from rtb_sdk import auction
from rtb_sdk.auction.adwords import initialize_adwords_stats
from rtb_sdk.helpers import create_parameters_ads_stats
from rtb_sdk.constants import SelectionFunc

# Initialization: writes the random prices pj into AdStats
ad_stats = initialize_adwords_stats(ads=ads, ad_stats=existing_stats)

# On every request — the standard auction() call
params = create_parameters_ads_stats(
    auction_type=SelectionFunc.ADWORDS_A2,
    ads_stats=ad_stats
)
ad = auction(ads=filtered_ads, parameters=params)
```

## Algorithm description

### The Adwords problem

In the context of this SDK, a **request** is a single `auction()` call: the moment when the system selects an ad to show to a specific user. Adwords algorithms process the same requests as the base `auction()`, but additionally track accumulated spend and advertiser budgets between requests.

In the Adwords problem there is a stream of requests `i = 1, 2, ...` and a set of advertisers `j`. Each advertiser `j` has:

- a bid `bid(i, j)` — the amount they are willing to pay for an impression on request `i`
- a budget that limits total spend or the maximum number of impressions

The goal is to distribute requests among advertisers so as to maximize total revenue. The algorithm works online: each request is processed immediately without knowledge of future requests.

**Why the problem is hard.** The difficulty arises from three simultaneous constraints:

1. **Online nature**: requests arrive sequentially, and the algorithm makes an irrevocable decision about each request without knowing about subsequent ones. A request cannot be "postponed" and a decision already made cannot be "cancelled".
2. **Budget constraints**: each advertiser can spend no more than `Bj` units. Greedily assigning the best requests to the most profitable advertisers quickly exhausts their budgets, leaving less valuable buyers for the remaining requests.
3. **Uncertainty about the future**: the optimal allocation requires knowing the whole request stream in advance (the offline optimum is a thought-experiment oracle algorithm that knows the entire request stream before it starts), whereas the online algorithm sees only the past and the present.

### Why the greedy algorithm does not work

The greedy algorithm — assigning each request to the advertiser with the highest bid — achieves a competitive ratio of only 0.5 (that is, in the worst case it gets half of the offline optimum).

**Counterexample.** Two advertisers A and B, each with a budget of 100 rubles. 101 requests arrive: for the first 100 requests both value them at 1 ruble each; for the last, 101st request, advertiser A values it at 100 rubles and B at 0.

On the first 100 requests (where bids are equal) the greedy algorithm assigns requests arbitrarily, for example giving A 50 and B 50. Result: A has actually spent 50 rubles and has 50 rubles remaining. On the 101st request A bids 100 rubles, but has only 50 left. If the greedy algorithm blocks participation when the budget is insufficient, A does not participate at all. Revenue: 100 rubles.

The offline oracle knows about the 101st request in advance: it saves A's entire budget (100 rubles) for it and gives the first 100 requests to B. Revenue: 100 (B) + 100 (A on the 101st) = 200 rubles.

The greedy algorithm got 50% of the optimum — which is exactly what a competitive ratio of 0.5 means.

Automated bid-management platforms need a **budget-oblivious** algorithm — one that does not need to know competitors' budgets to make decisions. This is exactly the property that A2 and A3 provide.

### Relation to the Online Bipartite Matching problem

The Adwords problem generalizes the **Online Bipartite Matching (OBM)** problem: there are buyers (requests) and sellers (advertisers), and each buyer must be matched to one seller so as to maximize the total weight of the matches. In OBM the edge weights are binary (0 or 1 — whether the advertiser can take part in this auction), in Adwords they are arbitrary (the bid size).

For OBM there is the **Ranking** algorithm (Karp, Vazirani, Vazirani, 1990), which achieves the optimal competitive ratio 1−1/e:

1. At initialization each advertiser `j` is randomly assigned a rank `rj` — a uniformly random number from 0 to 1.
2. Each incoming request is matched to the advertiser with the highest rank among those whose budget is not yet exhausted.

**Why a random rank is better than a deterministic choice.** Consider an example:

| | Advertiser A | Advertiser B |
|---|---|---|
| Compatible with requests | 1 and 2 | only 1 |
| Budget | 1 impression | 1 impression |

Offline optimum: A → request 2, B → request 1. Revenue = 2. Requests arrive in the order: first request 1, then request 2.

- **Greedy algorithm** (A wins the tie-break): request 1 → A wins → A is exhausted. Request 2 → only A is compatible, but A is exhausted. Revenue = **1**, ratio = 0.5.
- **Ranking**: ranks `rA` and `rB` are assigned randomly.
  - With probability 50%: `rA > rB` → A wins request 1 → A is exhausted → request 2 is not covered. Revenue = 1.
  - With probability 50%: `rB > rA` → B wins request 1 → B is exhausted → A wins request 2. Revenue = 2.
  - Expected revenue = 1.5, ratio = **0.75**.

Randomness "breaks" the deterministic tie-break: now B gets a chance to take its only compatible request, and A is used where it is really needed.

As the competition structure gets more complex — more advertisers with partially overlapping compatibilities — the gain from a random rank grows, and in the worst case the expected share of correct assignments tends to 1−1/e. This limit arises from the same mathematics as the probability of catching the "right" object in a random search: `(1 - 1/n)^n → 1/e` as `n → ∞`.

Algorithms A2 and A3 are direct generalizations of Ranking to the Adwords problem. Instead of a rank `rj`, each advertiser is assigned a **random price** `pj`, and the winner is determined not by the maximum rank but by the maximum **effective bid** `bid × (1 − pj)`.

The meaning of the factor `(1 − pj)`: the higher the advertiser's price `pj`, the more its effective bid is reduced. An advertiser with `pj` close to 1 almost never wins — unless it is the only participant or has a bid far exceeding its competitors'. An advertiser with `pj` close to `1/e ≈ 0.368` gets the minimum penalty and wins more often. Thus the random price plays the role of an "inverse rank": a high rank in Ranking ↔ a low price in A2/A3.

### The key idea: a random price

Both algorithms (A2 and A3) use one technique: at initialization each advertiser `j` is randomly assigned a price once:

```
wj = a uniformly distributed random number from 0 to 1
pj = e^(wj - 1)
```

When processing each request, instead of the original bid `bid(i, j)`, the **effective bid** is used:

```
effective_bid(i, j) = bid(i, j) × (1 − pj)
```

The auction winner is the advertiser with the highest effective bid among those whose budget is not exhausted.

**Why exactly `pj = e^(wj − 1)` and not the linear `pj = wj`?**

The choice of the exponential function is not arbitrary: it is the only form of transformation for which the competitive ratio 1−1/e is achieved. The intuition is as follows.

To prove that the algorithm obtains at least `(1 − 1/e)` of the optimum, one must show that the expected contribution of each advertiser `j` to total revenue is at least `kj × bj × (1 − 1/e)`, where `kj` is the number of requests the offline oracle would have assigned to `j`. With `pj = e^(wj−1)`, the key integral in the expected revenue calculation takes the form:

```
∫₀¹ e^(x−1) dx = 1 − 1/e
```

This value is what fixes the lower bound of the competitive ratio. Any other monotone transformation of `wj` would give a smaller value of this integral. The optimality of `e^(x−1)` is proven via a special linear programming problem that formalizes the trade-off between "betting on the profitable ones" and "saving budget for future requests".

Note that for `wj ∈ [0, 1]` we get `pj ∈ [e^{−1}, 1] ≈ [0.368, 1.0]`, and the effective bid `bid × (1 − pj) ∈ [0, bid × (1 − 1/e)]` — always strictly less than the original bid.

**Why is the price fixed once per session?**

This is the key property that ensures **budget-obliviousness**. The algorithm does not need to know the budgets of other advertisers either at initialization or when processing requests — it is enough to know only whether its own budget is exhausted. If the price were recomputed on every request, justifying optimality would require knowing the full request distribution in advance — which contradicts the online setting.

A **session** is the period between two calls of `initialize_adwords`. The prices `pj` are fixed at initialization and remain unchanged until the next call of `initialize_adwords`, whether that is a service restart, a change in the set of campaigns, or the start of a new billing period.

### Where `e^(wj − 1)` comes from: the link to the MSVV algorithm

To understand why this particular formula, we need to get acquainted with the **MSVV algorithm** (Mehta, Saberi, Vazirani, Vazirani, 2007) — a budget-aware predecessor of A2/A3, which also achieves the competitive ratio 1−1/e but knows the budgets of all advertisers.

**How MSVV works.** On each request MSVV selects the advertiser maximizing the effective bid, where the bid is adjusted depending on what share of the budget has already been spent:

```
effective_bid_MSVV(j) = bj × ψ(xj)   where xj = the share of the budget already spent
ψ(x) = e^(x − 1)
```

- Budget untouched (`xj = 0`): `ψ(0) = e^{-1} ≈ 0.368` — the bid is heavily discounted.
- Half of the budget spent (`xj = 0.5`): `ψ(0.5) = e^{-0.5} ≈ 0.607`.
- Budget almost exhausted (`xj → 1`): `ψ(1) = 1` — the bid at full strength.

The logic is counter-intuitive: an advertiser with a full budget bids lower, one with an almost exhausted budget bids the maximum. This is deliberate: when the budget is running out, the advertiser "fights" for every remaining impression with all its might. When the budget is full, it "saves", giving competitors the chance to win some requests. This prevents a single advertiser from monopolizing all impressions.

**Why exactly `e^(x−1)` and not some other decreasing function?** MSVV proves the competitive ratio via LP duality: for each (request `i`, advertiser `j`) pair from the offline optimum a dual constraint is written. The analysis shows that the competitive ratio equals the average value of the function `ψ(x)`, averaged over all possible levels of budget spend. In other words, competitive ratio = `∫₀¹ ψ(x) dx`. To achieve the maximum possible value, one must choose a function such that this integral is the largest under the given constraints on `ψ`.

The only monotonically increasing function with boundary conditions `ψ(0) = 1/e` and `ψ(1) = 1` for which the integral takes the value `1 − 1/e`:

```
∫₀¹ e^(x−1) dx = [e^(x−1)]₀¹ = e^0 − e^{-1} = 1 − 1/e  ✓
```

Any other function in this class would give a smaller integral — and hence a smaller competitive ratio.

**The transition from MSVV to a budget-oblivious algorithm.** MSVV computes `xj` on every request, and therefore knows the spent budget of all participants. Vazirani asked whether this requirement could be bypassed.

The key observation: the function `ψ(x) = e^{x-1}` is exactly the function that appears in the formula `pj = e^{wj-1}`. If instead of dynamically computing `xj` we simply fix a random point `wj ~ U[0,1]` for the whole session, then:

- In MSVV: `x` runs through values from 0 to 1 as the budget is spent. The integral `∫₀¹ ψ(x) dx = 1−1/e` reflects the total "power" of the discount over the whole session.
- In A2/A3: `wj` is a random fixed point from the same interval `[0,1]`. The expected value of `pj` over all possible sessions:

```
E[pj] = E[e^{wj−1}] = ∫₀¹ e^{x−1} dx = 1 − 1/e
```

This is the essence of the budget-oblivious replacement: instead of dynamically tracking the budget, a single random number whose expected value coincides with the total effect of the MSVV budget discount.

**Why this works in the small-bid limit.** If each individual bid is small compared to the budget, the budget is spent gradually, in "small steps". In this limit, randomly fixing the point `wj` and dynamically tracking `xj` become mathematically indistinguishable in terms of expected revenue. This is exactly why the Small condition (bids ≪ budget) is necessary for A3 but not required for A2 (where the budget is measured in units, not in money).

**In summary: where each element of the formula comes from:**

```
wj ~ U[0, 1]           # a random "point" from the MSVV budget life cycle
pj = e^(wj − 1)        # the value of the discount function ψ at that point
E[pj] = 1 − 1/e        # = competitive ratio = ∫₀¹ e^(x−1) dx
effective_bid = bid × (1 − pj)   # the bid adjusted for the discount
```

The factor `(1 − pj)` is used for selection (whoever has the higher effective bid wins), while `pj` itself appears in the LP-dual certificate as the advertiser's "price". The competitive ratio is determined precisely by the expected value of this "price".

### Why the competitive ratio 1−1/e is optimal

It has been proven that no randomized online algorithm can guarantee a better competitive ratio on an arbitrary request stream. This means that A2 and A3 are **optimal** among all possible online algorithms — not only budget-oblivious ones but also those allowed to know competitors' budgets.

An important nuance: the guarantee `≥ 1 − 1/e` is a guarantee **on average** over the random prices `pj`, not for every individual run. A single run may yield 45% as well as 95% of the optimum. The theorem states that the expected value (the average over many runs with different random `pj`) does not fall below 63.2% of the optimum.

A numerical reference point: `1 − 1/e ≈ 0.632`. In practice (experimental data from the paper) A3's performance is 96–101% of the budget-aware MSVV algorithm operating under the same conditions.

### A2 vs A3 comparison

| Parameter                    | A2 (Single-Valued)                          | A3 (Small)                                         |
| ---------------------------- | ------------------------------------------- | -------------------------------------------------- |
| Budget type                  | Impression counter (`volume`)               | Monetary budget (`budget`)                         |
| Bid                          | Fixed `cpm` for all requests                | May vary across requests                           |
| Effective bid                | `cpm × (1 − pj)`                            | `bid(i,j) × (1 − pj)`                             |
| Participation restriction    | `matches < volume` (when `volume > 0`)      | `remaining_budget >= bid(i, j)`                    |
| Fake money                   | No                                          | Yes (`fake_spend`)                                 |
| Competitive ratio            | 1 − 1/e (optimal, unconditional)            | 1 − 1/e (when the Small condition holds)           |
| Applicability condition      | No restrictions                             | `bid(i,j) << budget_j`                             |
| No-Surpassing Property¹      | Always holds (proven)                       | Holds in ~98% of cases (experimentally)            |

¹ _The No-Surpassing Property is a key property for the theoretical justification; more in the sections ["A2 theoretical guarantees"](#a2-theoretical-guarantees) and ["A3 theoretical guarantees"](#a3-theoretical-guarantees)._

**Choosing between A2 and A3.** Use A2 if the advertiser's bid is the same for any request (a fixed CPM) and the budget is specified as a number of impressions. Use A3 if the budget is monetary and bids may differ across requests — provided that no individual bid makes up a significant share of the total budget.

## Data types

### AdwordsAlgorithmId

An identifier of the Adwords algorithm.

```python
type AdwordsAlgorithmId = Literal['a2_single_valued', 'a3_small']
```

A constants class is used to access the values:

```python
class AdwordsAlgorithm:
    A2_SINGLE_VALUED: AdwordsAlgorithmId = 'a2_single_valued'
    A3_SMALL: AdwordsAlgorithmId = 'a3_small'
```

Example:

```python
from rtb_sdk.schemas import AdwordsAlgorithmId
from rtb_sdk.constants import AdwordsAlgorithm

alg: AdwordsAlgorithmId = AdwordsAlgorithm.A2_SINGLE_VALUED
```

### AdwordsAdState

The state of a single advertiser (ad) between requests. Created automatically at initialization via `initialize_adwords`. Inherits `DiscriminatedTypedDict` with `__type = 'AdwordsAdState'`.

| Attribute          | Type    | Purpose |
| ------------------ | ------- | ------- |
| `id`               | `AdId`  | ad campaign identifier |
| `price`            | `float` | random price `pj = e^(wj−1)`, assigned at initialization, does not change during the session |
| `matches`          | `int`   | counter of won impressions `dj` (for A2: the condition `dj < volume` is checked) |
| `remaining_budget` | `float` | remaining monetary budget `Lj = budget − real_spend` (for A3; not used for A2) |
| `real_spend`       | `float` | real spend — the total cost of all won impressions (for A3) |
| `fake_spend`       | `float` | fake spend — the total cost of all requests for which the advertiser was admitted to the auction, regardless of winning (for A3) |

Example:

```python
from rtb_sdk.schemas import AdwordsAdState, AdId

ad_state: AdwordsAdState = {
    '__type': 'AdwordsAdState',
    'id': 'ad_1',
    'price': 0.6065,         # e^(0.8 - 1) at wj = 0.8
    'matches': 0,
    'remaining_budget': 5000.0,
    'real_spend': 0.0,
    'fake_spend': 0.0,
}
```

### AdwordsState

The top-level container of the Adwords session state. It is passed to `auction_adwords` and returned in updated form after every request. Inherits `DiscriminatedTypedDict` with `__type = 'AdwordsState'`.

| Attribute     | Type                           | Purpose |
| ------------- | ------------------------------ | ------- |
| `algorithm`   | `AdwordsAlgorithmId`           | identifier of the active algorithm (A2 or A3) |
| `ad_states`   | `dict[AdId, AdwordsAdState]`   | states of all advertisers in the current session |
| `query_count` | `int`                          | total number of processed requests (diagnostics) |

Example:

```python
from rtb_sdk.schemas import AdwordsState
from rtb_sdk.constants import AdwordsAlgorithm

state: AdwordsState = {
    '__type': 'AdwordsState',
    'algorithm': AdwordsAlgorithm.A2_SINGLE_VALUED,
    'ad_states': {
        'ad_1': {
            '__type': 'AdwordsAdState',
            'id': 'ad_1', 'price': 0.6065, 'matches': 0,
            'remaining_budget': 0.0, 'real_spend': 0.0, 'fake_spend': 0.0,
        },
        'ad_2': {
            '__type': 'AdwordsAdState',
            'id': 'ad_2', 'price': 0.3679, 'matches': 0,
            'remaining_budget': 0.0, 'real_spend': 0.0, 'fake_spend': 0.0,
        },
    },
    'query_count': 0,
}
```

### AdwordsMatchResult

The result of a single `auction_adwords` call. Contains the auction winner, the effective bids of all participants, and the updated state.

| Attribute        | Type                 | Purpose |
| ---------------- | -------------------- | ------- |
| `matched_ad`     | `AdId \| None`       | identifier of the winning ad; `None` if the budgets of all participants are exhausted or the candidate list is empty |
| `effective_bids` | `dict[AdId, float]`  | effective bids of all admitted auction participants (for debugging and monitoring) |
| `state`          | `AdwordsState`       | updated session state after processing the request |

Example:

```python
from rtb_sdk.schemas import AdwordsMatchResult
from rtb_sdk.auction.adwords import auction_adwords

result: AdwordsMatchResult = auction_adwords(ads=filtered_ads, state=state)

ad_id = result['matched_ad']            # 'ad_1' or None
state = result['state']                  # pass to the next call
ebids = result['effective_bids']         # {'ad_1': 524.5, 'ad_2': 381.2}
```

### Changes to Ad

A new field is added to the existing `Ad` schema:

| Attribute | Type    | Optional                 | Purpose |
| --------- | ------- | ------------------------ | ------- |
| `budget`  | `float` | Yes, default: `0.0`      | the advertiser's monetary budget `Bj`; used only in algorithm A3; ignored in A2 |

The existing `volume` field (`int`) is used in A2 as the maximum number of impressions `kj`. The value `0` means no limit (same as the existing behavior).

Example of creating an ad with a budget for A3:

```python
from rtb_sdk.helpers import create_ad, create_target_vector, create_frequency_limits
from datetime import datetime

ad = create_ad(
    id='ad_3',
    active=True,
    targets=create_target_vector({'City': ['Moscow', 'Saint Petersburg']}),
    start_date=datetime(2026, 8, 1),
    end_date=datetime(2026, 8, 31),
    cpm=1500.0,
    priority=1.0,
    volume=0,              # no impression limit for A3
    budget=10000.0,        # Bj = 10,000 rubles
    ad_frequency_limit=create_frequency_limits(day=80, hour=30),
    user_frequency_limit=create_frequency_limits(day=5, week=20, min_interval=180),
    parasitic_freq_limit=create_frequency_limits(),
    vocabulary_weights={},
    tag_weights={},
)
```

## Algorithm A2 (Single-Valued)

An algorithm for the case where each advertiser uses a single fixed bid `bj = cpm` for all requests. The budget is specified as a number of impressions `kj = volume`. Competitive ratio = 1−1/e (optimal among budget-oblivious algorithms with uniform bids).

### A2 initialization

When `initialize_adwords` is called, a random price is computed once for each advertiser `j` and the counters are zeroed:

**Pseudocode:**

```
for each ad j in ads:
    wj  = random.uniform(0, 1)
    pj  = exp(wj − 1)          # pj ∈ [e^−1, 1] ≈ [0.368, 1.0]
    ad_states[j] = AdwordsAdState(
        id=j, price=pj, matches=0,
        remaining_budget=0.0, real_spend=0.0, fake_spend=0.0
    )
state = AdwordsState(algorithm='a2_single_valued', ad_states=ad_states, query_count=0)
```

**Example:**

```python
from rtb_sdk.auction.adwords import initialize_adwords
from rtb_sdk.constants import AdwordsAlgorithm

state = initialize_adwords(ads=all_ads, algorithm=AdwordsAlgorithm.A2_SINGLE_VALUED)

# The prices are assigned randomly and will not change until the next initialization
print(state['ad_states']['ad_1']['price'])   # e.g. 0.6065
print(state['ad_states']['ad_2']['price'])   # e.g. 0.8187
print(state['ad_states']['ad_1']['matches']) # 0
```

### A2 request handling

For each incoming request, the admitted participants are determined, their effective bids are computed, and a winner is chosen:

**Pseudocode:**

```
# Admitted: those that have not exhausted their impression limit
eligible = [j for j in filtered_ads
            if ad[j].volume == 0 or ad_states[j].matches < ad[j].volume]

if eligible is empty:
    return AdwordsMatchResult(matched_ad=None, ...)

for each j in eligible:
    effective_bid[j] = ad[j].cpm * (1 − ad_states[j].price)

winner = argmax(effective_bid)
ad_states[winner].matches += 1
state.query_count += 1

return AdwordsMatchResult(matched_ad=winner, effective_bids=effective_bid, state=state)
```

If `eligible` contains a single participant, it wins regardless of its price `pj`: `argmax` of one element always returns it.

**Example:**

```python
from rtb_sdk.auction.adwords import auction_adwords

result = auction_adwords(ads=filtered_ads, state=state)

winner_id = result['matched_ad']    # 'ad_1' or None
state = result['state']              # updated matches

# Effective bids are available for monitoring:
# {'ad_1': 487.8, 'ad_2': 163.9}
print(result['effective_bids'])
print(f"ad_1 impressions: {state['ad_states']['ad_1']['matches']}")
```

### Impression limit

Advertiser `j` is excluded from the auction when `matches_j >= volume_j` (when `volume_j > 0`). The value `volume = 0` is interpreted as no limit. After the limit is exhausted, the ad does not participate in auctions until the session is next initialized.

**Why a budget in the form of an impression counter is equivalent to a monetary budget with equal bids.** In Single-Valued, all bids of advertiser `j` are the same and equal to `bj`. A monetary budget `Bj` at a fixed bid means exactly `kj = Bj / bj` impressions. Therefore tracking the remaining money is pointless — a counter is enough.

### A2 theoretical guarantees

**No-Surpassing Property.** This is the key property used in the proof of the competitive ratio. Its meaning is as follows: if we mentally remove advertiser `j` from the auction and rerun the algorithm (such a hypothetical run is a tool of the mathematical proof, not part of the algorithm itself), none of the remaining participants will start winning the requests that `j` won in the real run with an effective bid higher than `bj × (1 − pj)`.

This property **holds unconditionally** for Single-Valued. The reason: with identical bids `bj` for all requests, an advertiser with a higher effective bid behaves identically in the presence and absence of `j` — its decisions do not depend on `j`. Thus removing `j` from consideration does not change the behavior of the other participants.

**What the algorithm guarantees.** It has been proven that the expected total revenue of algorithm A2, on average over the random prices, is:

```
E[W] ≥ (1 − 1/e) × w(P)
```

where `w(P)` is the revenue of the offline-optimal assignment. The algorithm is budget-oblivious, because it never accesses the `volume` of other advertisers — it only knows whether its own limit is exhausted.

## Algorithm A3 (Small)

An algorithm for the case of a monetary budget `Bj = budget`. The bid `bid(i, j)` may vary across requests (in the implementation, `bid(i, j) = cpm` of the ad). It uses fake spend (`fake_spend`) to track potential costs. Conditional ratio = 1−1/e under the Small condition.

### A3 initialization

When `initialize_adwords` is called, a price is computed for each advertiser `j` and the initial budget remainder is set:

**Pseudocode:**

```
for each ad j in ads:
    wj  = random.uniform(0, 1)
    pj  = exp(wj − 1)
    ad_states[j] = AdwordsAdState(
        id=j, price=pj, matches=0,
        remaining_budget=ad[j].budget,    # Lj = Bj
        real_spend=0.0,
        fake_spend=0.0
    )
state = AdwordsState(algorithm='a3_small', ad_states=ad_states, query_count=0)
```

**Example:**

```python
from rtb_sdk.auction.adwords import initialize_adwords
from rtb_sdk.constants import AdwordsAlgorithm

state = initialize_adwords(ads=all_ads, algorithm=AdwordsAlgorithm.A3_SMALL)

print(state['ad_states']['ad_1']['price'])            # e.g. 0.3679
print(state['ad_states']['ad_1']['remaining_budget']) # 10000.0 (= budget)
print(state['ad_states']['ad_1']['real_spend'])       # 0.0
```

### A3 request handling

**Pseudocode:**

```
# Admitted: those with a sufficient remaining budget to pay the bid
eligible = [j for j in filtered_ads
            if ad_states[j].remaining_budget >= ad[j].cpm]

if eligible is empty:
    return AdwordsMatchResult(matched_ad=None, ...)

# Fake spend is charged to all admitted participants
for each j in eligible:
    effective_bid[j] = ad[j].cpm * (1 − ad_states[j].price)
    ad_states[j].fake_spend += ad[j].cpm     # accounting of potential costs

winner = argmax(effective_bid)
ad_states[winner].real_spend += ad[winner].cpm
ad_states[winner].remaining_budget -= ad[winner].cpm
ad_states[winner].matches += 1
state.query_count += 1

return AdwordsMatchResult(matched_ad=winner, effective_bids=effective_bid, state=state)
```

**Example:**

```python
from rtb_sdk.auction.adwords import auction_adwords

result = auction_adwords(ads=filtered_ads, state=state)
winner_id = result['matched_ad']
state = result['state']

if winner_id:
    ad_state = state['ad_states'][winner_id]
    print(f"Winner: {winner_id}")
    print(f"  Remaining budget: {ad_state['remaining_budget']:.2f}")
    print(f"  Real spend: {ad_state['real_spend']:.2f}")
    print(f"  Fake spend: {ad_state['fake_spend']:.2f}")
```

### Fake money: why it is needed

Fake spend (`fake_spend`) is the most non-trivial element of algorithm A3. It was introduced to overcome the structural difficulty of the problem with variable bids.

**The problem to solve.** What to do when advertiser `j`'s remaining budget `Lj` is less than its bid `bid(i, j)`? For example, a budget of 1000 rubles, a bid of 1500 rubles, a remainder of 700 rubles. There are three options:

1. **Forbid participation** — `j` does not bid when `Lj < bid(i, j)`. Intuitively right, but it breaks the competitive ratio.

   _Counterexample:_ two advertisers, budgets of 100 rubles each. The first 100 requests: both value them at 1 ruble each, and money is spent evenly. On the 101st request: A values it at 50 rubles and has 50 rubles left — exactly enough. B values it at 10 rubles and has 50 rubles left. A wins, revenue is 50 rubles. Now the variant where on the 101st request A wants to bid 60 rubles but has 50 left — and we forbid it from participating. B wins for 10 rubles. The offline oracle would have reserved enough of A's budget for this request. A hard ban systematically leads to such losses.

2. **Reduce the bid to the remainder `Lj`** — change the bid size at submission time. This changes the effective bid and violates the mathematical properties needed to prove the algorithm's correctness.

3. **Allow participation, splitting the payment** into `Lj` real money + `bid(i, j) − Lj` fake money. `j` participates in the auction with its full effective bid and wins or loses — but no more than what is in the account is charged, and the shortfall is recorded as fake spend.

Algorithm A3 uses option 3. As a result, total revenue includes real and fake money: `E[W + Wf] ≥ (1 − 1/e) × w(P)`.

**Why `fake_spend` is charged to all admitted participants and not only to the winner.** `fake_spend` answers the question: "how much would the advertiser have spent on this request if it had an unlimited budget?". The answer is `cpm`, and this "potential spend" is recorded regardless of winning. This is needed for the theoretical analysis: the algorithm is mentally compared with a hypothetical run without a particular advertiser, and `fake_spend` shows how much each participant would have "spent" in that hypothetical world.

In practice, `fake_spend` is a diagnostic tool: when the Small condition holds, `real_spend ≈ fake_spend`, which confirms the algorithm is working correctly.

### The Small applicability condition

Algorithm A3 achieves the conditional ratio 1−1/e provided the bids are small relative to the budget:

```
bid(i, j) << budget_j  for all i, j
```

In practice, no bid should make up a significant share of the total budget. If this condition is violated, the competitive ratio may degrade. For large one-off bids (`bid ≈ budget`), alternative approaches should be used.

**Mathematical justification of the Small condition.** Total fake spend is bounded above by the sum of the maximum bids of all advertisers:

```
Wf ≤ Σⱼ max_i { bid(i, j) }
```

The Small condition formally means that the ratio of the maximum bid to the budget tends to zero as the number of requests `n` grows:

```
max_j { max_i bid(i, j) / budget_j } → 0  as n → ∞
```

It follows that `Wf / w(P) → 0`, that is, the share of fake money in total revenue becomes negligible. An algorithm with a predominant share of real money is equivalent to the optimal one: `E[W] ≈ E[W + Wf] ≥ (1 − 1/e) × w(P)`.

**Why the No-Surpassing Property may be violated for A3.** Unlike A2, in A3 bids may differ across requests. This allows a situation where a competitor `j'` places a very large bid on one request — such that in the hypothetical run without `j` the budget of `j'` is exhausted on exactly this request, but in the real run `j'` "outbids" `j` right here. This violates the monotonicity on which the proof is built. Experimentally (Vazirani's paper) the violation occurs in fewer than 2% of cases.

### A3 theoretical guarantees

**What the algorithm guarantees.** When the Small condition holds:

```
E[W] ≥ (1 − 1/e) × w(P)   (asymptotically, as n → ∞)
```

The algorithm is budget-oblivious: it does not access the budget values of other advertisers at any step. All the information it needs is only whether its own `remaining_budget` is exhausted.

**Experimental performance** (from the original paper, 20 advertisers, 2000 requests):
- A3 vs MSVV (budget-aware optimal): 96.5–101.4% depending on the graph density.
- A3 vs the greedy algorithm: 95.8–152.8% (the advantage grows with density).
- No-Surpassing violations: 0.01–1.61%, i.e. the algorithm almost always operates in the theoretically justified regime.

## State management

### Option 1: explicit AdwordsState

Explicit state management is analogous to the Optimizer pattern (`first_generate` → `next_generate`). The state is stored as a serializable `AdwordsState` object, fully controlled by the user.

**`initialize_adwords(ads, algorithm) -> AdwordsState`**

Initializes the state once per session — usually at service start or when the set of campaigns changes. Each call generates new random prices `pj`.

```python
from rtb_sdk.auction.adwords import initialize_adwords
from rtb_sdk.constants import AdwordsAlgorithm

# Called once at the start of the session
state = initialize_adwords(
    ads=all_ads,
    algorithm=AdwordsAlgorithm.A2_SINGLE_VALUED
)
```

**`auction_adwords(ads, state) -> AdwordsMatchResult`**

Performs one auction round. Takes the filtered list of ads and the current state, returns the winner and the new state.

```python
from rtb_sdk.auction.adwords import auction_adwords

result = auction_adwords(ads=filtered_ads, state=state)
ad_id = result['matched_ad']
state = result['state']    # IMPORTANT: update state for the next call
```

**Serializing the state between runs:**

```python
import json

# Saving the state (e.g. to Redis or to disk)
state_json = json.dumps(state)

# Restoring on the next run
from rtb_sdk.helpers import load_adwords_state
state = load_adwords_state(json.loads(state_json))
```

**When to reinitialize the state:**

- When advertisers are added to or removed from rotation
- At the start of a new billing period (day, flight)
- When impression statistics are reset

**Why you should not reinitialize too often.** Each reinitialization generates new random prices `pj`. The theoretical guarantees apply to a single session — a coherent request stream with fixed prices. Frequent reinitialization (e.g. on every request) destroys the statistical properties on which the proof of the competitive ratio is based.

### Option 2: integration via AdStats

Integration with the existing `auction()` through an extension of `AdStats`. The random prices `pj` are stored in `AdStats` under the special `AuctionTypeId = 'adwords_price'`. Impression counters are maintained by the standard mechanisms.

**`initialize_adwords_stats(ads, ad_stats) -> AdStats`**

Writes the random prices `pj` into `AdStats` at session initialization. Existing counters are not affected.

```python
from rtb_sdk.helpers import create_ad_stats
from rtb_sdk.auction.adwords import initialize_adwords_stats

existing_stats = create_ad_stats({})   # or loaded statistics
ad_stats = initialize_adwords_stats(ads=all_ads, ad_stats=existing_stats)
```

**New `SelectionFunc` constants:**

```python
class SelectionFunc:
    # ... existing constants ...
    ADWORDS_A2: AuctionSelectionFunc = 'adwords_a2'
    ADWORDS_A3: AuctionSelectionFunc = 'adwords_a3'
```

**Calling the auction through the standard `auction()`:**

```python
from rtb_sdk import auction
from rtb_sdk.helpers import create_parameters_ads_stats
from rtb_sdk.constants import SelectionFunc

params = create_parameters_ads_stats(
    auction_type=SelectionFunc.ADWORDS_A2,
    ads_stats=ad_stats
)
ad = auction(ads=filtered_ads, parameters=params)
```

**Advantages of Option 2:** full compatibility with the existing filters, simulation, and the `AdStats` update infrastructure; requires no changes to top-level code.

**Limitation of Option 2:** managing `remaining_budget` for algorithm A3 requires additional logic outside the standard `auction()`, since the current `AuctionParams` interface does not provide for returning updated budget states.

## Examples

### Full A2 cycle (Option 1)

```python
from datetime import datetime
from rtb_sdk.helpers import create_ad, create_target_vector, create_frequency_limits
from rtb_sdk.auction.adwords import initialize_adwords, auction_adwords
from rtb_sdk.constants import AdwordsAlgorithm

# Preparing the ads
ad_1 = create_ad(
    id='ad_1',
    active=True,
    targets=create_target_vector({'City': ['Moscow', 'Kazan']}),
    start_date=datetime(2026, 8, 1),
    end_date=datetime(2026, 8, 31),
    cpm=1200.0,
    priority=1.0,
    volume=500,            # kj = 500 impressions at most
    ad_frequency_limit=create_frequency_limits(day=40, hour=20),
    user_frequency_limit=create_frequency_limits(day=5, week=20, min_interval=180),
    parasitic_freq_limit=create_frequency_limits(),
    vocabulary_weights={},
    tag_weights={},
)

ad_2 = create_ad(
    id='ad_2',
    active=True,
    targets=create_target_vector({'City': ['Moscow']}),
    start_date=datetime(2026, 8, 1),
    end_date=datetime(2026, 8, 31),
    cpm=980.0,
    priority=0.8,
    volume=1000,           # kj = 1000 impressions at most
    ad_frequency_limit=create_frequency_limits(day=60),
    user_frequency_limit=create_frequency_limits(day=3, week=15),
    parasitic_freq_limit=create_frequency_limits(),
    vocabulary_weights={},
    tag_weights={},
)

all_ads = [ad_1, ad_2]

# Initialization (once per session)
state = initialize_adwords(ads=all_ads, algorithm=AdwordsAlgorithm.A2_SINGLE_VALUED)

print(f"ad_1 price: {state['ad_states']['ad_1']['price']:.4f}")
print(f"ad_2 price: {state['ad_states']['ad_2']['price']:.4f}")

# Request processing loop
for i in range(10):
    filtered = all_ads   # here: filtering by targets, frequencies, etc.

    result = auction_adwords(ads=filtered, state=state)
    state = result['state']

    winner = result['matched_ad']
    if winner:
        print(f"Request {i+1}: winner={winner}, "
              f"effective_bids={result['effective_bids']}")
    else:
        print(f"Request {i+1}: no winner")

# Final statistics
for ad_id_key, ad_state in state['ad_states'].items():
    print(f"{ad_id_key}: impressions={ad_state['matches']}, "
          f"price={ad_state['price']:.4f}")
print(f"Total requests: {state['query_count']}")
```

### Full A3 cycle (Option 1)

```python
from datetime import datetime
from rtb_sdk.helpers import create_ad, create_target_vector, create_frequency_limits
from rtb_sdk.auction.adwords import initialize_adwords, auction_adwords
from rtb_sdk.constants import AdwordsAlgorithm

# Ads with monetary budgets for A3
ad_1 = create_ad(
    id='ad_1',
    active=True,
    targets=create_target_vector({'Age': ['18-25', '26-35']}),
    start_date=datetime(2026, 8, 1),
    end_date=datetime(2026, 8, 31),
    cpm=1500.0,
    priority=1.0,
    volume=0,              # no impression limit for A3
    budget=8000.0,         # Bj = 8,000 rubles
    ad_frequency_limit=create_frequency_limits(day=80),
    user_frequency_limit=create_frequency_limits(day=5, week=20),
    parasitic_freq_limit=create_frequency_limits(),
    vocabulary_weights={},
    tag_weights={},
)

ad_2 = create_ad(
    id='ad_2',
    active=True,
    targets=create_target_vector({'Age': ['26-35', '36-45']}),
    start_date=datetime(2026, 8, 1),
    end_date=datetime(2026, 8, 31),
    cpm=1100.0,
    priority=0.9,
    volume=0,
    budget=12000.0,        # Bj = 12,000 rubles
    ad_frequency_limit=create_frequency_limits(day=100),
    user_frequency_limit=create_frequency_limits(day=3, week=12),
    parasitic_freq_limit=create_frequency_limits(),
    vocabulary_weights={},
    tag_weights={},
)

all_ads = [ad_1, ad_2]

# A3 initialization
state = initialize_adwords(ads=all_ads, algorithm=AdwordsAlgorithm.A3_SMALL)

# Request processing loop
for i in range(20):
    filtered = all_ads   # filtering by targets and frequencies

    result = auction_adwords(ads=filtered, state=state)
    state = result['state']

    winner = result['matched_ad']
    if winner:
        ad_s = state['ad_states'][winner]
        print(f"Request {i+1}: winner={winner}, "
              f"remaining={ad_s['remaining_budget']:.2f}, "
              f"real spend={ad_s['real_spend']:.2f}")
    else:
        print(f"Request {i+1}: no winner (budgets exhausted)")

# Final A3 statistics
for ad_id_key, ad_state in state['ad_states'].items():
    print(f"\n{ad_id_key}:")
    print(f"  Impressions:       {ad_state['matches']}")
    print(f"  Real spend:        {ad_state['real_spend']:.2f}")
    print(f"  Remaining budget:  {ad_state['remaining_budget']:.2f}")
    print(f"  Fake spend:        {ad_state['fake_spend']:.2f}")
```

### Full A2 cycle (Option 2 via AdStats)

```python
from datetime import datetime
from rtb_sdk import auction
from rtb_sdk.helpers import (
    create_ad, create_target_vector, create_frequency_limits,
    create_ad_stats, create_parameters_ads_stats,
)
from rtb_sdk.auction.adwords import initialize_adwords_stats
from rtb_sdk.constants import SelectionFunc

# Preparing the ads
ad_1 = create_ad(
    id='ad_1',
    active=True,
    targets=create_target_vector({'City': ['Moscow']}),
    start_date=datetime(2026, 8, 1),
    end_date=datetime(2026, 8, 31),
    cpm=1200.0,
    priority=1.0,
    volume=500,
    ad_frequency_limit=create_frequency_limits(day=40, hour=20),
    user_frequency_limit=create_frequency_limits(day=5, week=20),
    parasitic_freq_limit=create_frequency_limits(),
    vocabulary_weights={},
    tag_weights={},
)

ad_2 = create_ad(
    id='ad_2',
    active=True,
    targets=create_target_vector({'City': ['Moscow', 'Kazan']}),
    start_date=datetime(2026, 8, 1),
    end_date=datetime(2026, 8, 31),
    cpm=980.0,
    priority=0.8,
    volume=1000,
    ad_frequency_limit=create_frequency_limits(day=60),
    user_frequency_limit=create_frequency_limits(day=3),
    parasitic_freq_limit=create_frequency_limits(),
    vocabulary_weights={},
    tag_weights={},
)

all_ads = [ad_1, ad_2]

# Initialization: write the random prices pj into AdStats
existing_stats = create_ad_stats({})
ad_stats = initialize_adwords_stats(ads=all_ads, ad_stats=existing_stats)

# Auction parameters — created once
params = create_parameters_ads_stats(
    auction_type=SelectionFunc.ADWORDS_A2,
    ads_stats=ad_stats
)

# Request processing loop through the standard auction()
for i in range(10):
    filtered = all_ads   # filtering by targets and frequencies

    ad = auction(ads=filtered, parameters=params)

    if ad is not None:
        print(f"Request {i+1}: winner={ad['id']}, cpm={ad['cpm']}")
    else:
        print(f"Request {i+1}: no winner")
```
