# RTB SDK // Using the auction

## Table of contents

- [RTB SDK // Using the auction](#rtb-sdk--using-the-auction)
  - [Table of contents](#table-of-contents)
  - [Quick start](#quick-start)
  - [Data types](#data-types)
    - [AdId](#adid)
    - [Ad](#ad)
    - [AdStats](#adstats)
    - [AuctionParams](#auctionparams)
    - [AuctionSelectionFunc](#auctionselectionfunc)
    - [AuctionStats](#auctionstats)
    - [AuctionTypeId](#auctiontypeid)
    - [Frequency](#frequency)
    - [FrequencyLimits](#frequencylimits)
    - [FullTag](#fulltag)
    - [FullTagVector](#fulltagvector)
    - [Granularity](#granularity)
    - [GranulatedCounter](#granulatedcounter)
    - [RawTag](#rawtag)
    - [RequestId](#requestid)
    - [Request](#request)
    - [RequestTags](#requesttags)
    - [TargetVector](#targetvector)
    - [UserId](#userid)
    - [VocabName](#vocabname)
  - [Working with the auction](#working-with-the-auction)
    - [Calling the auction](#calling-the-auction)
    - [Selection functions](#selection-functions)
      - [BEST\_ONE](#best_one)
      - [RANDOM\_ONE](#random_one)
      - [BEST\_PRICE](#best_price)
      - [RANDOM\_PRICE](#random_price)
      - [BEST\_HEURISTICS](#best_heuristics)
      - [RANDOM\_HEURISTICS](#random_heuristics)
      - [BEST\_VELOCITY](#best_velocity)
      - [RANDOM\_VELOCITY](#random_velocity)
      - [BEST\_HYBRID](#best_hybrid)
      - [RANDOM\_HYBRID](#random_hybrid)
    - [Helper methods](#helper-methods)
      - [get\_request\_tags](#get_request_tags)
      - [get\_ad\_targetvector](#get_ad_targetvector)
      - [get\_fulltags](#get_fulltags)
  - [Examples](#examples)
    - [Preparing data for the auction](#preparing-data-for-the-auction)
      - [Ads](#ads)
      - [Request](#request-1)
      - [Vocabularies (Vocabs)](#vocabularies-vocabs)
      - [Ad statistics (AdStats)](#ad-statistics-adstats)
    - [Data conversion](#data-conversion)
    - [Running the auction](#running-the-auction)
    - [Full testing cycle](#full-testing-cycle)

## Quick start

An SDK for working with an ad auction that selects ads by exact match between the request tags and the ad campaign.

```python
from rtb_sdk import auction
from rtb_sdk.schemas import AuctionParams
from rtb_sdk.constants import SelectionFunc
from rtb_sdk.helpers import create_parameters_ads_stats

# ads - an array of ad campaigns from which the ad to show is selected
# filtering by frequency and targets must be implemented separately

# configuring the auction type
params: AuctionParams = create_parameters_ads_stats(
    auction_type=SelectionFunc.BEST_VELOCITY,
    ads_stats=ad_stats
)

# returns an Ad or None
adToShow = auction(ads=adsToPickFrom, parameters=params)
```

## Data types

### AdId

An ad campaign identifier, an alias for `str`. Limited to 64 characters.

Example:

```python
from rtb_sdk.schemas import AdId

some_ad_id: AdId = "ad_8"
```

### Ad

A model of an ad campaign/flight containing the display conditions of that flight.

Created via the `create_ad` constructor from `rtb_sdk.helpers`.

| Attribute            | Type                                            | Optional                         | Purpose |
| -------------------- | ----------------------------------------------- | -------------------------------- | ------- |
| `id`                 | [AdId](#adid)                                   | No                               | unique identifier of the campaign |
| `targets`            | [TargetVector](#targetvector)                   | No                               | campaign targets by [request](#request) attributes. See also [VocabName](#vocabname) and [RawTag](#rawtag) |
| `active`             | `bool`                                          | No                               | campaign activity flag |
| `start_date`         | `datetime`                                      | Yes, default: `None`             | Campaign rotation start date per the media plan. If not specified — the date is unbounded on the left |
| `end_date`           | `datetime`                                      | Yes, default: `None`             | Campaign rotation end date per the media plan. If not specified — the date is unbounded on the right |
| `cpm`                | `float`                                         | Yes, default: `0`                | price per thousand impressions, `>=0` |
| `priority`           | `float`                                         | Yes, default: `1.0`              | relative priority of the campaign in rotation, `0.0`–`1.0` |
| `volume`             | `int`                                           | Yes, default: `0`                | maximum number of campaign impressions, `>=0`, where `0` means no limit |
| `ad_frequency_limit` | [FrequencyLimits](#frequencylimits)             | Yes, default: `None`             | maximum frequency of ad impressions per unit of time |
| `user_frequency_limit` | [FrequencyLimits](#frequencylimits)           | Yes, default: `None`             | maximum frequency of ad impressions per unit of time per unique user |
| `parasitic_freq_limit` | [FrequencyLimits](#frequencylimits)           | Yes, default: `None`             | maximum frequency of ad impressions per unit of time outside the specified targets |
| `vocabulary_weights` | `dict[VocabName, float]`                        | Yes, default: `None`             | relative weights (priorities) of various [categories](#vocabname) |
| `tag_weights`        | `dict[FullTag, float]`                          | Yes, default: `None`             | relative weights (priorities) of individual [tags](#fulltag) |

Example:

```python
from rtb_sdk.helpers import create_ad, create_target_vector, create_frequency_limits
from datetime import datetime

ad: Ad = create_ad(
    id='ad_2',
    active=True,
    targets=create_target_vector(),
    start_date=datetime(2025, 7, 1, 0, 0),
    end_date=datetime(2025, 7, 29, 0, 0),
    cpm=1260.0,
    priority=1.0,
    volume=200,
    ad_frequency_limit=create_frequency_limits(day=40, hour=20),
    user_frequency_limit=create_frequency_limits(day=5, ten_minutes=3, week=20, min_interval=180),
    parasitic_freq_limit=create_frequency_limits(),
    vocabulary_weights={},
    tag_weights={}
)
```

### AdStats

An object describing the [time statistics](#granulatedcounter) of an arbitrary number of [ad campaigns](#ad).

Created via the `create_ad_stats` constructor from `rtb_sdk.helpers`.

```python
type AdStats = Dict[AdId, AuctionStats]
```

Example:

```python
from rtb_sdk.helpers import create_ad_stats, create_auction_stats, create_granulated_counter

ad_stats = create_ad_stats({
    'ad_1': create_auction_stats(
        precise_counter=create_granulated_counter(day=57, hour=57, month=57, ten_minutes=57, week=57)
    ),
    'ad_2': create_auction_stats(
        precise_counter=create_granulated_counter(day=36, hour=36, month=36, ten_minutes=13, week=36),
        fuzzy_counter=create_granulated_counter(day=10, hour=10, month=10, week=10)
    ),
})
```

### AuctionParams

A container for the call parameters of the [main auction method](#calling-the-auction).

Created via the `create_parameters_ads_stats` constructor from `rtb_sdk.helpers`.

| Field          | Type                            | Description |
| -------------- | ------------------------------- | ----------- |
| `auction_type` | [AuctionSelectionFunc](#auctionselectionfunc) | Identifier of the [selection function](#selection-functions) |
| `ads_stats`    | [AdStats](#adstats)             | An additional container with statistics for the participating [ad campaigns](#ad) |
| `price_probability` | `float`, optional         | Probability (in the range `(0, 1)`) of [BEST\_PRICE](#best_price) winning in [RANDOM\_HYBRID](#random_hybrid). The field is optional in `AuctionParams` as a whole, but required if `auction_type=RANDOM_HYBRID` |
| `velocity_threshold` | `float`, optional        | Lower plan-completion threshold (`1 − share of under-delivery`, range `[0, 1]`) used by [BEST\_HYBRID](#best_hybrid). The field is optional in `AuctionParams` as a whole, but required if `auction_type=BEST_HYBRID` |

Example:

```python
from rtb_sdk.helpers import create_parameters_ads_stats
from rtb_sdk.constants import SelectionFunc

# preparing ad_stats: AdStats...

params = create_parameters_ads_stats(
    auction_type=SelectionFunc.BEST_VELOCITY,
    ads_stats=ad_stats
)
```

### AuctionSelectionFunc

A type and constants for describing the various [selection functions](#selection-functions)

```python
class SelectionFunc:
    BEST_ONE: AuctionSelectionFunc = 'best_one'
    RANDOM_ONE: AuctionSelectionFunc = 'random_one'
    BEST_PRICE: AuctionSelectionFunc = 'best_price'
    RANDOM_PRICE: AuctionSelectionFunc = 'random_price'
    BEST_VELOCITY: AuctionSelectionFunc = 'best_velocity'
    RANDOM_VELOCITY: AuctionSelectionFunc = 'random_velocity'
    BEST_HEURISTICS: AuctionSelectionFunc = 'best_heuristics'
    RANDOM_HEURISTICS: AuctionSelectionFunc = 'random_heuristics'
    BEST_HYBRID: AuctionSelectionFunc = 'best_hybrid'
    RANDOM_HYBRID: AuctionSelectionFunc = 'random_hybrid'

auctionStatKey: AuctionSelectionFunc = SelectionFunc.BEST_PRICE
```

Example: see [Selection functions](#selection-functions)

### AuctionStats

Statistics of a single [ad campaign](#ad), broken down by [algorithm kinds](#auctiontypeid).

Created via the `create_auction_stats` constructor from `rtb_sdk.helpers`.

```python
type AuctionStats = Dict[AuctionTypeId, GranulatedCounter]
```

Example:

```python
from rtb_sdk.helpers import create_auction_stats, create_granulated_counter

stats = create_auction_stats(
    precise_counter=create_granulated_counter(day=57, hour=57, week=57),
    fuzzy_counter=create_granulated_counter(day=10, hour=10, week=10),
)
```

### AuctionTypeId

Constants describing qualitatively different kinds of auction algorithms

```python
class AuctionType:
    PRECISE: AuctionTypeId = 'precise'
    FUZZY: AuctionTypeId = 'fuzzy'

auctionStatKey: AuctionTypeId = AuctionType.PRECISE
```

| AuctionTypeId | Description |
| ------------- | ----------- |
| `precise`     | The *precise* class of algorithms — the goal of the auction is to achieve the aggregate maximum of the ad campaigns' KPIs |
| `fuzzy`       | The *conditional* class of algorithms — the goal of the auction is to maximize the ad campaigns' KPIs by means of limited "blurring" of the targeting |

Example:

```python
from rtb_sdk.schemas import AuctionTypeId
from rtb_sdk.constants import AuctionType

precise_type: AuctionTypeId = 'precise'
fuzzy_type: AuctionTypeId = AuctionType.FUZZY
```

### Frequency

A fractional (`float`) counter of aggregated data across various [granularities](#granularity), also used to specify the frequency characteristics of an [ad campaign](#ad).

Created via the `create_frequency` constructor from `rtb_sdk.helpers`.

Example:

```python
from rtb_sdk.helpers import create_frequency

counter = create_frequency(ten_minutes=0.8, day=15.0, month=50.0)
```

### FrequencyLimits

A model describing the frequency restrictions on running an ad campaign [by interval](#granularity).

Created via the `create_frequency_limits` constructor from `rtb_sdk.helpers`.

| Constructor parameter | Type    | Optional | Purpose |
| --------------------- | ------- | -------- | ------- |
| `ten_minutes`         | `float` | Yes      | maximum number of impressions in the last 10 minutes |
| `hour`                | `float` | Yes      | maximum number of impressions in the last 60 minutes |
| `day`                 | `float` | Yes      | maximum number of impressions in the last 24 hours |
| `week`                | `float` | Yes      | maximum number of impressions in the last 168 hours |
| `month`               | `float` | Yes      | maximum number of impressions in the last 720 hours |
| `min_interval`        | `float` | Yes      | minimum number of seconds since the time of the last impression |

Example:

```python
from rtb_sdk.helpers import create_frequency_limits

ad_limits = create_frequency_limits(day=2.5, month=50, min_interval=180)
```

### FullTag

An alias for `str` used to store the values of a [category](#targetvector) together with the category itself. It is formed by concatenating [VocabName](#vocabname) and [RawTag](#rawtag) with a colon. Every `FullTag` is globally unique and case-sensitive.

```python
from rtb_sdk.schemas import FullTag

age_group: FullTag = 'Age:18-25'
cities: List[FullTag] = ['City:Moscow', 'City:Saint Petersburg', 'City:Novy Urengoy']
```

### FullTagVector

An analog of [TargetVector](#targetvector) with [full tags](#fulltag) instead of basic ones.

Created via the `create_full_tag_vector` constructor from `rtb_sdk.helpers`.

Example:

```python
from rtb_sdk.helpers import create_full_tag_vector

fv = create_full_tag_vector({
    'City': ['City:Moscow', 'City:Kazan'],
    'Age': ['Age:18-25', 'Age:26-35'],
})
```

### Granularity

An enumerated type identifying the various metric aggregation intervals.
All interval events, including [statistics](#adstats) and forecasts, are collected broken down by these intervals, which in most cases are available simultaneously:

- 10 minutes
- hour
- day
- week
- month

```python
type Granularity = Literal['t', 'h', 'd', 'w', 'm']
```

An additional dictionary of constants is used to access the type's values:

```python
class Gran:
    TEN_MINUTES: Granularity = 't'
    HOUR: Granularity = 'h'
    DAY: Granularity = 'd'
    WEEK: Granularity = 'w'
    MONTH: Granularity = 'm'
```

Depending on the scenario and context, these intervals can mean either calendar time or an offset into the past from the current moment. In the latter case the time interval is calculated to the second, e.g. "day" is a sample over the last 86400 seconds from the moment of the request.

Example:

```python
from rtb_sdk.schemas import Granularity
from rtb_sdk.constants import Gran

granKey: Granularity = Gran.WEEK
```

### GranulatedCounter

An integer counter of aggregated data across various [granularities](#granularity).

Created via the `create_granulated_counter` constructor from `rtb_sdk.helpers`.

| Constructor parameter | Type  | Optional | Purpose |
| --------------------- | ----- | -------- | ------- |
| `ten_minutes`         | `int` | Yes      | counter for the last 10 minutes |
| `hour`                | `int` | Yes      | counter for the last 60 minutes |
| `day`                 | `int` | Yes      | counter for the last 24 hours |
| `week`                | `int` | Yes      | counter for the last 168 hours |
| `month`               | `int` | Yes      | counter for the last 720 hours |

Example:

```python
from rtb_sdk.helpers import create_granulated_counter

counter = create_granulated_counter(ten_minutes=1, hour=1, day=1, week=1, month=1)
```

### RawTag

An alias for `str` used to store the possible values of a [category](#targetvector).

The same value may be used in different categories, but within one category all values are unique. `RawTag` values are case-sensitive.

Example:

```python
from rtb_sdk.schemas import RawTag

age_group: RawTag = '18-25'
cities: List[RawTag] = ['Moscow', 'Saint Petersburg', 'Novy Urengoy']
```

### RequestId

An alias for `str` used as a globally unique identifier of a [request](#request).

Example:

```python
from rtb_sdk.schemas import RequestId

request_id: RequestId = '1234-5678-abcdef-abcdef-1234'
```

### Request

A unique ad request containing [targeting](#requesttags) attributes.

Created via the `create_request` constructor from `rtb_sdk.helpers`.

| Attribute | Type                            | Optional | Purpose |
| --------- | ------------------------------- | -------- | ------- |
| `id`      | [RequestId](#requestid)         | No       | locally unique request identifier |
| `user_id` | [UserId](#userid)               | No       | globally unique user identifier in the system |
| `date`    | `datetime`                      | No       | server time the request was received |
| `tags`    | [RequestTags](#requesttags)     | Yes      | targeting parameters as a combination of [category](#vocabname) and [value](#fulltag) |

Example:

```python
from rtb_sdk.helpers import create_request, create_request_tags
from datetime import datetime

request = create_request(
    id="01995746-67a7-7950-88fc-a6df4ec45bcc",
    user_id="abcdef12-1234-1234-1234-123456789ab",
    date=datetime(2025, 7, 29, 0, 0),
    tags=create_request_tags({
        "City": "City:Moscow",
        "Age": "Age:18-25",
        "Domain": "Domain:example.com",
    })
)
```

### RequestTags

A dictionary of [FullTag](#fulltag) values indexed by [VocabName](#vocabname). Describes the set of targeting parameters of a specific [request](#request).

Created via the `create_request_tags` constructor from `rtb_sdk.helpers`.

```python
type RequestTags = Dict[VocabName, FullTag]
```

Example:

```python
from rtb_sdk.helpers import create_request_tags

tags = create_request_tags({
    'City': 'City:Moscow',
    'Age': 'Age:18-25',
})
```

### TargetVector

A dictionary of categorized [tags](#rawtag), split by [category names](#vocabname). Within each category the tag list contains no repetitions.

Used for targeting [campaigns](#ad) and other representations of the correspondence between tags and categories.

Created via the `create_target_vector` constructor from `rtb_sdk.helpers`.

```python
type TargetVector = Dict[VocabName, list[RawTag]]
```

Example:

```python
from rtb_sdk.helpers import create_target_vector

tv = create_target_vector({
    'City': ['Moscow', 'Kazan'],
    'Age': ['18-25', '26-35'],
})
```

### UserId

An alias for `str` used as a globally unique user identifier.

Example:

```python
from rtb_sdk.schemas import UserId

uid: UserId = '1234-5678-abcdef-abcdef-1234'
```

### VocabName

An alias for `str`, a globally unique name of a [category](#targetvector), also used as its identifier.

```python
from rtb_sdk.schemas import VocabName

vocab_name: VocabName = 'City'
```

## Working with the auction

### Calling the auction

After the ad campaigns have been filtered by:

- impression frequency per ad campaign
- impression frequency per user
- tag similarity (matching the targeting),

the auction's main task comes down to selecting a single campaign from all those selected so as to optimize one or more KPIs of *all* ad campaigns participating in rotation at the time of the request, including the filtered-out ones.

The auction is called by the `auction` function from the main module:

```python
from rtb_sdk import auction
from rtb_sdk.helpers import create_parameters_ads_stats
from rtb_sdk.constants import SelectionFunc

params = create_parameters_ads_stats(auction_type=SelectionFunc.BEST_ONE)

# ads - a list of Ad from which the ad to show is selected
adToShow = auction(ads=ads, parameters=params)  # returns an Ad or None
```

**Accepted parameters:**

`ads`: a set of [campaigns](#ad) filtered for the incoming [request](#request)

`params` — the auction [parameter container](#auctionparams), containing the single required field [auction_type](#selection-functions)

**Returns:**

The best-fitting [campaign](#ad), or `None` if no suitable campaign is found

### Selection functions

The optimization function that defines the campaign selection algorithm, also called the *selection function*, is implemented as [constants in the SDK](#auctionselectionfunc), and depending on the specific algorithm the set of parameters in `AuctionParams` may vary.

The following auction types are available in the system:

#### BEST_ONE

Returns the first ad by priority among the relevant ones

```python
from rtb_sdk import auction
from rtb_sdk.helpers import create_parameters_ads_stats
from rtb_sdk.constants import SelectionFunc

ad = auction(ads=ads, parameters=create_parameters_ads_stats(
    auction_type=SelectionFunc.BEST_ONE
))
```

#### RANDOM_ONE

Returns a random ad among the relevant ones

```python
from rtb_sdk import auction
from rtb_sdk.helpers import create_parameters_ads_stats
from rtb_sdk.constants import SelectionFunc

ad = auction(ads=ads, parameters=create_parameters_ads_stats(
    auction_type=SelectionFunc.RANDOM_ONE
))
```

#### BEST_PRICE

Returns the ad with the highest price among the relevant ones

```python
from rtb_sdk import auction
from rtb_sdk.helpers import create_parameters_ads_stats
from rtb_sdk.constants import SelectionFunc

ad = auction(ads=ads, parameters=create_parameters_ads_stats(
    auction_type=SelectionFunc.BEST_PRICE
))
```

#### RANDOM_PRICE

Returns an ad selected randomly with a probability proportional to its price

```python
from rtb_sdk import auction
from rtb_sdk.helpers import create_parameters_ads_stats
from rtb_sdk.constants import SelectionFunc

ad = auction(ads=ads, parameters=create_parameters_ads_stats(
    auction_type=SelectionFunc.RANDOM_PRICE
))
```

#### BEST_HEURISTICS

Returns the ad that heuristically best fits the media plan.

A fuzzy-logic selection function that uses the following parameters:

- priority
- price
- delivery velocity
- rarity of the ad campaign.

For this auction to work, pre-computed data is required for all campaigns in rotation:

```python
from rtb_sdk import auction
from rtb_sdk.helpers import create_parameters_ads_stats
from rtb_sdk.constants import SelectionFunc

ad = auction(ads=ads, parameters=create_parameters_ads_stats(
    auction_type=SelectionFunc.BEST_HEURISTICS,
    ads_stats=ad_stats  # loaded separately
))
```

#### RANDOM_HEURISTICS

Returns the ad with a heuristically weighted-average fit to the media plan. In other words, the same thing happens as in [BEST_HEURISTICS](#best_heuristics), but a random choice is made from the distribution described by the heuristic function.

```python
from rtb_sdk import auction
from rtb_sdk.helpers import create_parameters_ads_stats
from rtb_sdk.constants import SelectionFunc

ad = auction(ads=ads, parameters=create_parameters_ads_stats(
    auction_type=SelectionFunc.RANDOM_HEURISTICS,
    ads_stats=ad_stats  # loaded separately
))
```

#### BEST_VELOCITY

Returns the ad with the largest share of under-delivery relative to the plan:

```python
from rtb_sdk import auction
from rtb_sdk.helpers import create_parameters_ads_stats
from rtb_sdk.constants import SelectionFunc

ad = auction(ads=ads, parameters=create_parameters_ads_stats(
    auction_type=SelectionFunc.BEST_VELOCITY,
    ads_stats=ad_stats  # loaded separately
))
```

#### RANDOM_VELOCITY

Returns an ad chosen at random in proportion to the share of under-delivery among all campaigns competing for this impression:

```python
from rtb_sdk import auction
from rtb_sdk.helpers import create_parameters_ads_stats
from rtb_sdk.constants import SelectionFunc

ad = auction(ads=ads, parameters=create_parameters_ads_stats(
    auction_type=SelectionFunc.RANDOM_VELOCITY,
    ads_stats=ad_stats  # loaded separately
))
```

#### BEST_HYBRID

Deterministically chooses between [BEST_PRICE](#best_price) and [BEST_VELOCITY](#best_velocity): an ad's plan completion is computed as `1 − share of under-delivery` (the share of the monthly limit already delivered). If at least one of the supplied ads has not reached the `velocity_threshold` of plan completion, [BEST_VELOCITY](#best_velocity) is used; if all ads have reached the threshold — [BEST_PRICE](#best_price) is used.

```python
from rtb_sdk import auction
from rtb_sdk.helpers import create_parameters_ads_stats
from rtb_sdk.constants import SelectionFunc

ad = auction(ads=ads, parameters=create_parameters_ads_stats(
    auction_type=SelectionFunc.BEST_HYBRID,
    ads_stats=ad_stats,  # loaded separately
    velocity_threshold=0.2
))
```

#### RANDOM_HYBRID

Randomly chooses between [BEST_PRICE](#best_price) and [BEST_VELOCITY](#best_velocity): with probability `price_probability` [BEST_PRICE](#best_price) is used, otherwise — [BEST_VELOCITY](#best_velocity).

```python
from rtb_sdk import auction
from rtb_sdk.helpers import create_parameters_ads_stats
from rtb_sdk.constants import SelectionFunc

ad = auction(ads=ads, parameters=create_parameters_ads_stats(
    auction_type=SelectionFunc.RANDOM_HYBRID,
    ads_stats=ad_stats,  # loaded separately
    price_probability=0.7
))
```

### Helper methods

#### get_request_tags

Returns [RequestTags](#requesttags) from a [request](#request)

```python
from rtb_sdk.schemas import Request, RequestTags
from rtb_sdk.helpers import get_request_tags

# r: Request = create_request(...)

tags: RequestTags = get_request_tags(r)
```

#### get_ad_targetvector

Returns a [TargetVector](#targetvector) structure from the [campaign](#ad) data

```python
from rtb_sdk.schemas import Ad, TargetVector
from rtb_sdk.helpers import get_ad_targetvector

# ad: Ad = create_ad(...)

target: TargetVector = get_ad_targetvector(ad)
```

#### get_fulltags

Expands structures that use [RawTag](#rawtag) to equivalent ones that use [FullTag](#fulltag). If `FullTag` is passed in the source values, the data is not changed.

```python
from rtb_sdk.schemas import VocabName, RawTag, FullTag, TargetVector, FullTagVector
from rtb_sdk.helpers import get_fulltags

vocab: VocabName = 'Age'
tag_list: list[RawTag] = ['18-25', '26-35']
# ['Age:18-25', 'Age:26-35']
full_tag_list: list[FullTag] = get_fulltags(vocab, tag_list)

r: Dict[VocabName, RawTag] = {
    'Age': '18-25',
    'City': 'Moscow'
}
# {'Age': 'Age:18-25', 'City': 'City:Moscow'}
fulltag_r: Dict[VocabName, FullTag] = get_fulltags(r)

v: TargetVector = create_target_vector({
    'Age': ['18-25', '26-35']
})
# TargetVector with {'Age': ['Age:18-25', 'Age:26-35']}
fulltag_v: FullTagVector = get_fulltags(v)
```

## Examples

Stages of the auction's operation:

### Preparing data for the auction

For the auction function to work correctly, all ads must first be filtered: by frequency, by per-user frequency, and by tag match.

For uniformity, we assume that data is loaded into the auction in JSON format.

#### Ads

```json
{
    "ad_1": {
        "__type": "Ad",
        "active": true,
        "ad_frequency_limit": {
            "__type": "FrequencyLimits",
            "value": {"d": 40, "h": 20, "m": 200, "t": 20, "w": 75, "min_interval": 0}
        },
        "end_date": "2025-07-29T00:00:00",
        "id": "ad_2",
        "cpm": 1010.0,
        "priority": 2.0,
        "start_date": "2025-07-01T00:00:00",
        "targets": {"__type": "TargetVector", "value": {}},
        "user_frequency_limit": {
            "__type": "FrequencyLimits",
            "value": {"d": 5, "h": 5, "m": 50, "t": 5, "w": 20, "min_interval": 0}
        },
        "vocabulary_weights": {},
        "tag_weights": {},
        "volume": 200
    }
}
```

#### Request

```json
{
    "__type": "Request",
    "date": "2025-07-01T00:00:00",
    "id": "01995746-67a7-7950-88fc-a6df4ec45bcc",
    "tags": {
        "__type": "RequestTags",
        "value": {
            "ad_category": "ad_category:avod",
            "ad_place_type": "ad_place_type:midroll",
            "content_id": "content_id:149580661",
            "device_type": "device_type:WEB_BROWSER_A",
            "domain": "domain:streaming.example"
        }
    },
    "user_id": "hQDjE9EPALa8wNavLyczO"
}
```

#### Vocabularies (Vocabs)

```json
{
    "ad_category": ["avod", "alive"],
    "ad_place_type": ["preroll", "pauseroll", "midroll"],
    "ad_position": ["1", "2", "3", "4"],
    "channel_id": ["1000174", "1125460", "1000069", "1130915"],
    "content_id": ["106998387", "149580661", "149591846", "92787100", "91925529"],
    "device_type": ["WEB_BROWSER_A", "ANDROID_TV_A", "ANDROID_PHONE_A"],
    "domain": ["streaming.example", "series-a.example", "series-b.example"],
    "embedded": ["false", "true", "p1"],
    "is_paid": ["false"],
    "location": ["700001", "100001", "1000187"],
    "service": ["rt"]
}
```

#### Ad statistics (AdStats)

```json
{
    "__type": "AdStats",
    "value": {
        "ad_1": {
            "__type": "AuctionStats",
            "value": {
                "precise": {
                    "__type": "GranulatedCounter",
                    "value": {"d": 537, "h": 57, "m": 7412, "t": 2, "w": 5751}
                }
            }
        },
        "ad_2": {
            "__type": "AuctionStats",
            "value": {
                "precise": {
                    "__type": "GranulatedCounter",
                    "value": {"d": 1136, "h": 336, "m": 36415, "t": 13, "w": 4553}
                }
            }
        }
    }
}
```

### Data conversion

Besides the basic JSON conversion by the module of the same name, you need to standardize the date format before loading, and also load the objects via the corresponding `load_*` helpers:

```python
from dateutil import parser
from rtb_sdk.helpers import load_ad, load_request, load_ad_stats

def parse_dates_recursive(obj):
    if isinstance(obj, dict):
        return {key: parse_dates_recursive(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [parse_dates_recursive(item) for item in obj]
    elif isinstance(obj, str):
        try:
            dt = parser.parse(obj)
            if len(obj) > 5:
                return dt
        except (ValueError, OverflowError):
            pass
    return obj

# After parsing the JSON and dates — loading via the helpers
ad = load_ad(parse_dates_recursive(raw_ad_dict))
request = load_request(parse_dates_recursive(raw_request_dict))
ad_stats = load_ad_stats(raw_ad_stats_dict)
```

### Running the auction

To call the corresponding auction function, you need to import the previously prepared data, the `auction` function from the sdk, and auxiliary types/constants if needed:

```python
from datetime import datetime
from dateutil import parser
import json

from rtb_sdk import auction
from rtb_sdk.helpers import load_ad, load_request, load_ad_stats, create_parameters_ads_stats
from rtb_sdk.constants import SelectionFunc

request = load_request(parse_dates_recursive(json.loads(request_json)))
vocabs = json.loads(vocabs_json)
ads = [load_ad(parse_dates_recursive(v)) for v in json.loads(ads_json).values()]
ad_stats = load_ad_stats(json.loads(ad_stats_json))

params = create_parameters_ads_stats(
    auction_type=SelectionFunc.BEST_VELOCITY,
    ads_stats=ad_stats
)

ad = auction(ads=ads, parameters=params)
```

### Full testing cycle

```python
from datetime import datetime
from pprint import pprint
from dateutil import parser
import json

from rtb_sdk import auction
from rtb_sdk.helpers import (
    load_ad, load_request, load_ad_stats,
    create_parameters_ads_stats,
)
from rtb_sdk.constants import SelectionFunc


def parse_dates_recursive(obj):
    """Recursively traverses a JSON structure and converts strings to datetime."""
    if isinstance(obj, dict):
        return {key: parse_dates_recursive(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [parse_dates_recursive(item) for item in obj]
    elif isinstance(obj, str):
        try:
            dt = parser.parse(obj)
            if len(obj) > 5:
                return dt
        except (ValueError, OverflowError):
            pass
    return obj


request_json = """
{
    "__type": "Request",
    "date": "2025-07-01T00:00:00",
    "id": "01995746-67a7-7950-88fc-a6df4ec45bcc",
    "tags": {
        "__type": "RequestTags",
        "value": {
            "ad_category": "ad_category:avod",
            "ad_place_type": "ad_place_type:midroll",
            "content_id": "content_id:149580661",
            "device_type": "device_type:WEB_BROWSER_A",
            "domain": "domain:streaming.example",
            "service": "service:rt"
        }
    },
    "user_id": "hQDjE9EPALa8wNavLyczO"
}
"""

ads_json = """
{
    "ad_1": {
        "__type": "Ad",
        "active": true,
        "ad_frequency_limit": {
            "__type": "FrequencyLimits",
            "value": {"d": 40, "h": 20, "m": 200, "t": 20, "w": 75, "min_interval": 0}
        },
        "end_date": "2025-07-29T00:00:00",
        "id": "ad_1",
        "cpm": 1260.0,
        "priority": 1.0,
        "start_date": "2025-07-01T00:00:00",
        "targets": {"__type": "TargetVector", "value": {}},
        "user_frequency_limit": {
            "__type": "FrequencyLimits",
            "value": {"d": 5, "h": 5, "m": 50, "t": 5, "w": 20, "min_interval": 0}
        },
        "parasitic_freq_limit": {
            "__type": "FrequencyLimits",
            "value": {"d": -1, "h": -1, "m": -1, "t": -1, "w": -1, "min_interval": 0}
        },
        "vocabulary_weights": {},
        "tag_weights": {},
        "volume": 200
    }
}
"""

ad_stats_json = """
{
    "__type": "AdStats",
    "value": {
        "ad_1": {
            "__type": "AuctionStats",
            "value": {
                "precise": {
                    "__type": "GranulatedCounter",
                    "value": {"d": 57, "h": 57, "m": 57, "t": 57, "w": 57}
                }
            }
        }
    }
}
"""

request = load_request(parse_dates_recursive(json.loads(request_json)))
ads = [load_ad(parse_dates_recursive(v)) for v in json.loads(ads_json).values()]
ad_stats = load_ad_stats(json.loads(ad_stats_json))

params = create_parameters_ads_stats(
    auction_type=SelectionFunc.BEST_VELOCITY,
    ads_stats=ad_stats,
)
best_ad = auction(ads=ads, parameters=params)
pprint(best_ad)
```
