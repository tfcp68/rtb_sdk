# RTB SDK // Auction simulation

## Table of contents

- [Quick start](#quick-start)
- [Data types](#data-types)
  - [MockDriver](#mockdriver)
  - [MockStatistics](#mockstatistics)
  - [ReportDict](#reportdict)
- [Data loading](#data-loading)
  - [load\_ads\_from\_json](#load_ads_from_json)
  - [load\_requests\_from\_csv](#load_requests_from_csv)
  - [load\_requests\_from\_json](#load_requests_from_json)
  - [load\_vocabs\_from\_json](#load_vocabs_from_json)
  - [save\_report](#save_report)
  - [sort\_request](#sort_request)
- [Ad filters](#ad-filters)
  - [filter\_by\_active](#filter_by_active)
  - [filter\_by\_ad\_frequency](#filter_by_ad_frequency)
  - [filter\_by\_fuzzy\_match](#filter_by_fuzzy_match)
  - [filter\_by\_min\_interval](#filter_by_min_interval)
  - [filter\_by\_fuzzy\_targeting\_frequency](#filter_by_fuzzy_targeting_frequency)
  - [filter\_by\_fuzzy\_targeting\_percent\_frequency](#filter_by_fuzzy_targeting_percent_frequency)
  - [filter\_by\_precise\_match](#filter_by_precise_match)
  - [filter\_by\_user\_frequency](#filter_by_user_frequency)
- [Report generation](#report-generation)
  - [create\_report\_dict](#create_report_dict)
  - [finish\_report](#finish_report)
  - [get\_vocab\_stats](#get_vocab_stats)
  - [make\_gisto](#make_gisto)
  - [save\_logs](#save_logs)
  - [save\_report (report\_creation)](#save_report-report_creation)
  - [update\_report](#update_report)
  - [update\_report\_with\_request\_tags](#update_report_with_request_tags)
- [Simulation control](#simulation-control)
  - [create\_mock\_driver](#create_mock_driver)
  - [get\_ad\_show\_times](#get_ad_show_times)
  - [get\_ad\_stats](#get_ad_stats)
  - [get\_ad\_timestamps](#get_ad_timestamps)
  - [get\_ad\_total\_counts](#get_ad_total_counts)
  - [get\_ads](#get_ads)
  - [get\_user\_ad\_show\_times](#get_user_ad_show_times)
  - [get\_user\_ad\_stats](#get_user_ad_stats)
  - [get\_user\_ad\_timestamps](#get_user_ad_timestamps)
  - [get\_vocabs](#get_vocabs)
  - [reset\_statistics\_if\_needed](#reset_statistics_if_needed)
  - [update\_statistics](#update_statistics)
- [Examples](#examples)
  - [Preparing data for the simulation](#preparing-data-for-the-simulation)
  - [Initializing MockDriver](#initializing-mockdriver)
  - [Applying filters](#applying-filters)
  - [Full simulation cycle](#full-simulation-cycle)
  - [Loading data from files](#loading-data-from-files)

## Quick start

The `simulation/` package reproduces the full operating cycle of an ad auction:
ad filtering, running the auction, and accumulating impression statistics
over a stream of incoming requests.

Statistics are stored as a **list of datetime stamps** (timestamp list) for each
ad. Frequency limits are checked with a **sliding window** method: if
the n-th most recent impression (where n = the limit) falls in the window `[current_time − window,
current_time]`, the limit is exhausted. This eliminates the boundary effect of calendar windows,
where 5 impressions at 12:58 and 5 impressions at 13:02 got around a 5/hour limit.

```python
from auction.simulation.driver.builder import create_mock_driver
from auction.simulation.driver.driver import (
    get_ads, get_ad_timestamps, get_ad_total_counts,
    get_user_ad_timestamps, get_user_ad_show_times,
    get_ad_stats, reset_statistics_if_needed, update_statistics,
)
from auction.simulation.filters.active_filter import filter_by_active
from auction.simulation.filters.frequency_filter import filter_by_ad_frequency
from auction.simulation.filters.match_filter import filter_by_precise_match
from auction.helpers import (
    load_ads_from_json, load_vocabs_from_json, load_requests_from_json,
)
from helpers import create_parameters_ads_stats, get_ads_dict, get_ad_id, get_request_date
from constants import SelectionFunc, AuctionType
from auction.auction import auction

driver = create_mock_driver(
    ads=load_ads_from_json('ads.json'),
    vocabs=load_vocabs_from_json('vocabs.json'),  # → TargetVector
)
requests = load_requests_from_json('requests.json')

for request in requests:
    current_time = get_request_date(request)
    reset_statistics_if_needed(driver, request)

    filtered = filter_by_active(get_ads(driver), current_time)
    filtered = filter_by_ad_frequency(filtered, get_ad_timestamps(driver), current_time)
    precise_ads = filter_by_precise_match(request, filtered)

    if get_ads_dict(precise_ads):
        ad_ids = list(get_ads_dict(precise_ads).keys())
        winner = auction(precise_ads, create_parameters_ads_stats(
            auction_type=SelectionFunc.BEST_VELOCITY,
            ads_stats=get_ad_stats(driver, ad_ids, current_time),
        ))
        update_statistics(driver, request, AuctionType.PRECISE, get_ad_id(winner) if winner else None)
```

## Data types

### MockDriver

The main store of the simulation state.

Created via [`create_mock_driver`](#create_mock_driver) from `auction.simulation.driver.builder`.

| Field    | Type             | Purpose |
| -------- | ---------------- | ------- |
| `ads`    | `AdsDict`        | all ads participating in the simulation |
| `vocabs` | `TargetVector`   | tag vocabularies for fuzzy matching |
| `stats`  | `MockStatistics` | accumulated impression statistics |

MockDriver provides a single interface for working with statistics. Main operations:

| Function | Input attributes | Output type | Purpose |
| -------- | ---------------- | ----------- | ------- |
| [`update_statistics`](#update_statistics) | `driver: MockDriver, request: Request, auction_type: AuctionTypeId, ad_id: AdId \| None` | `None` | Record the result of an impression (HIT/MISS) |
| [`reset_statistics_if_needed`](#reset_statistics_if_needed) | `driver: MockDriver, request: Request` | `None` | Trim stale stamps (> 30 days) |
| [`get_ad_timestamps`](#get_ad_timestamps) | `driver: MockDriver, ad_ids: list[AdId] \| None = None` | `AdTimestamps` | Get timestamp lists for frequency filters |
| [`get_ad_total_counts`](#get_ad_total_counts) | `driver: MockDriver, ad_ids: list[AdId] \| None = None` | `AdTotalCounts` | Get total PRECISE/FUZZY counters |
| [`get_ad_stats`](#get_ad_stats) | `driver: MockDriver, ad_ids: list[AdId] \| None, current_time: datetime \| None` | `AdStats` | Get `AdStats` for auction strategies |
| [`get_ad_show_times`](#get_ad_show_times) | `driver: MockDriver, ad_ids: list[AdId] \| None = None` | `AdShowTimes` | Get the last impression time of each ad |
| [`get_user_ad_timestamps`](#get_user_ad_timestamps) | `driver: MockDriver, user_id: UserId` | `AdTimestamps` | Get timestamp lists for a specific user |
| [`get_user_ad_stats`](#get_user_ad_stats) | `driver: MockDriver, user_id: UserId, current_time: datetime \| None` | `AdStats` | Get the user's `AdStats` |
| [`get_user_ad_show_times`](#get_user_ad_show_times) | `driver: MockDriver, user_id: UserId` | `AdShowTimes` | Get the times of the last impressions to the user |

```python
from auction.simulation.driver.builder import create_mock_driver
from helpers import create_ads_dict, create_target_vector

driver = create_mock_driver(
    ads=create_ads_dict({'ad_1': ad_1, 'ad_2': ad_2}),
    vocabs=create_target_vector({'City': ['Moscow', 'Kazan'], 'Age': ['18-25', '26-35']}),
)
```

### MockStatistics

The internal impression storage structure. It is maintained automatically via
[`update_statistics`](#update_statistics) and [`reset_statistics_if_needed`](#reset_statistics_if_needed).

```python
class MockStatistics(TypedDict):
    # [ad_id] → TimestampList of impressions (oldest first, 30-day sliding window)
    ad_timestamps: AdTimestamps           # dict[AdId, TimestampList]

    # [ad_id][user_id] → TimestampList of impressions to the user
    user_ad_timestamps: UserAdTimestamps  # dict[AdId, dict[UserId, TimestampList]]

    # [ad_id][auction_type] → int (total over the whole simulation)
    ad_total_counts: AdTotalCounts        # dict[AdId, dict[AuctionTypeId, int]]
```

**How it works (rolling window):**

Each impression is recorded as a datetime stamp (`oldest first`). Frequency limits
are checked not by comparing against a period, but by the "n-th most recent impression" method:

```
timestamps = [t1, t2, t3, ... tN]   # sorted ascending
nth_recent = timestamps[-limit]      # n-th most recent = limit-th from the end
window_start = current_time - window

if nth_recent > window_start → the window already holds >= limit impressions → BLOCKED
```

Granularities and window lengths:

| Key  | Window    |
| ---- | --------- |
| `t`  | 10 minutes |
| `h`  | 1 hour    |
| `d`  | 1 day     |
| `w`  | 7 days    |
| `m`  | 30 days   |

Entries older than `MAX_WINDOW_SECONDS = 30 × 86400` are trimmed automatically when
`reset_statistics_if_needed` is called. This controls memory consumption in long simulations.

**ad_total_counts** is an additional counter that is incremented on every impression
and stores the total number of impressions by type (PRECISE/FUZZY) over the whole simulation.
It is used for reporting and for the off-target impression filter.

### ReportDict

A typed structure of the simulation report. Returned by the functions
[`create_report_dict`](#create_report_dict), [`update_report`](#update_report),
[`finish_report`](#finish_report).

```python
# AdReportInfo inherits all fields of Ad (targets, cpm, start_date, end_date,
# ad_frequency_limit, etc.) and adds report-specific fields:
class AdReportInfo(Ad):
    goal: int                      # planned impression volume (= volume)
    target_requests_in_flow: int   # requests matching by tags
    fuzzy_percent: float           # share of impressions with fuzzy targeting
    result: int                    # actual number of impressions
    utilization: float             # utilization (result / min(target_in_flow, goal))

class PeriodStatistics(TypedDict):
    total_by_ads_percent: dict[AdId, float]
    precise_by_ads_percent: dict[AdId, float]
    fuzzy_by_ads_percent: dict[AdId, float]
    hit: int
    precise: int
    fuzzy: int
    miss: int
    total_progress: float
    sellout: float

class ReportPeriod(TypedDict):
    date: datetime
    statistics: PeriodStatistics

class ReportHeader(TypedDict):
    id: int
    title: str
    flow_size: int
    shown_in_flow: int
    rejected_in_flow: int
    total_goal: int
    total_result: int
    utilization: float
    sellout: float
    uniq_users: int
    ads: dict[AdId, AdReportInfo]
    tag_stats: dict[str, dict[str, int]]

class ReportDict(TypedDict):
    header: ReportHeader
    periods: list[ReportPeriod]
```

## Data loading

The file loaders (`load_ads_from_json`, `load_requests_from_json`,
`load_requests_from_csv`, `load_vocabs_from_json`, `sort_request`) live
in `auction.helpers` and are used by both the simulation and the tests.

`auction.simulation.data_loader.loaders` re-exports them for convenience
and adds `save_report`.

### load\_ads\_from\_json

```python
def load_ads_from_json(path: str) -> AdsDict
```

Loads ads from a JSON file.

Accepts the formats:
- a list of objects: `[{...}, {...}]`
- a dictionary `{ad_id: {...}}` (including one with the `__type: AdsDict` wrapper)

Uses `helpers.load_ad_raw` to parse each ad — the same loader
used in the auction tests (`tests/auction/_functions.py`).

```python
from auction.helpers import load_ads_from_json

ads = load_ads_from_json('path/to/ads.json')
```

### load\_requests\_from\_csv

```python
def load_requests_from_csv(path: str, vocabs: TargetVector) -> list[Request]
```

Loads requests from a CSV file (wide format).

Expected CSV format:

```
client_id,date,City,Device,...
user_001,2025-07-15T10:00:00,Moscow,Smartphone,...
```

Column names (except `client_id` and `date`) are matched to the keys of `vocabs`.
Empty cells mean the vocab is absent from the request tags.

| Parameter | Type | Purpose |
| --------- | ---- | ------- |
| `path`    | `str` | path to the CSV file |
| `vocabs`  | `TargetVector` | tag vocabularies for matching columns and validation |

```python
from auction.helpers import load_requests_from_csv, load_vocabs_from_json

vocabs = load_vocabs_from_json('data/vocabs.json')
requests = load_requests_from_csv('data/requests.csv', vocabs)
```

### load\_requests\_from\_json

```python
def load_requests_from_json(path: str) -> list[Request]
```

Loads requests from a JSON file.

Expected fields of each object in the list:

| Field       | Type    | Purpose |
| ----------- | ------- | ------- |
| `client_id` | `str`   | user identifier (mapped to `user_id`) |
| `date`      | `str`   | request date in ISO 8601 format |
| `tags`      | `dict`  | tags in the format `{VocabName: FullTag}` |

```python
from auction.helpers import load_requests_from_json

requests = load_requests_from_json('path/to/requests.json')
```

### load\_vocabs\_from\_json

```python
def load_vocabs_from_json(path: str) -> TargetVector
```

Loads tag vocabularies from a JSON file.

Expected format: `{vocab_name: [raw_tag, ...]}`.

```python
from auction.helpers import load_vocabs_from_json

vocabs = load_vocabs_from_json('path/to/vocabs.json')
```

### save\_report

```python
def save_report(report: dict, path: str) -> None
```

Saves an arbitrary dictionary of simulation results to a JSON file.
Converts `datetime` fields to strings before saving.

| Input attribute | Type   | Purpose |
| --------------- | ------ | ------- |
| `report`        | `dict` | dictionary with results (e.g. `ReportDict`) |
| `path`          | `str`  | path of the file to save to |

| Output type |
| ----------- |
| `None`      |

```python
from auction.simulation.data_loader.loaders import save_report

save_report(report, 'path/to/report.json')
```

### sort\_request

```python
def sort_request(requests: list[Request]) -> list[Request]
```

Sorts a list of requests by date to reproduce a chronological stream.

```python
from auction.helpers import sort_request

ordered_requests = sort_request(requests)
```

## Ad filters

All filters accept and return `AdsDict`. Filters do not modify the input data
and are stateless.

Typical order of application:

```
filter_by_active
  → filter_by_ad_frequency        (needs current_time)
    → filter_by_user_frequency    (needs current_time)
      → filter_by_min_interval
        → filter_by_precise_match
          or filter_by_fuzzy_targeting_frequency + filter_by_fuzzy_match
```

### filter\_by\_active

```python
def filter_by_active(ads: AdsDict, current_date: datetime) -> AdsDict
```

Keeps only active ads whose campaign is in effect on the current date.

```python
from auction.simulation.filters.active_filter import filter_by_active

filtered = filter_by_active(ads, current_date=datetime(2025, 7, 15, 12, 0))
```

### filter\_by\_ad\_frequency

```python
def filter_by_ad_frequency(
    ads: AdsDict,
    ad_timestamps: AdTimestamps,
    current_time: datetime,
) -> AdsDict
```

Filters by global frequency limits (sliding window).

For each ad it checks whether the limit has been reached in the window
`[current_time − window, current_time]` for any granularity.
A value of `0` or `-1` in the limit means no restriction.

```python
from auction.simulation.filters.frequency_filter import filter_by_ad_frequency

# ad_timestamps: AdTimestamps from get_ad_timestamps(driver)
filtered = filter_by_ad_frequency(ads, ad_timestamps, current_time)
```

### filter\_by\_fuzzy\_match

```python
def filter_by_fuzzy_match(
    request: Request,
    ads: AdsDict,
    max_distance: float = 1.0,
    strict_vocabs: list[VocabName] | None = None,
) -> AdsDict
```

Keeps ads with a weighted distance `<= max_distance`.

**Distance algorithm (weighted Jaccard):**

For each vocab of the ad, the similarity to the request is computed:

```
similarity_vocab = weighted_intersection / weighted_union

where:
  intersection = ad_tags ∩ request_tags
  union        = ad_tags ∪ request_tags
  weighted_X   = Σ tag_weights[t]  (for each t ∈ X; the default tag weight = 1.0)

overall similarity:
  similarity = Σ(vocabulary_weights[v] × similarity_v) / Σ(vocabulary_weights[v])
  distance   = 1 − similarity
```

Distance `0.0` = exact match, `1.0` = no intersection.
With `max_distance=1.0`, all ads with any targeting at all pass.

The `strict_vocabs` parameter makes it possible to forbid deviation on specific
vocabularies: for strict vocabs an exact tag intersection is required. If there is
no intersection, the ad is filtered out regardless of `max_distance`.

| Input attribute | Type                      | Description |
| --------------- | ------------------------- | ----------- |
| `request`       | `Request`                 | incoming request |
| `ads`           | `AdsDict`                 | candidate ads |
| `max_distance`  | `float`                   | threshold; `0.0` — exact, `1.0` — any; default `1.0` |
| `strict_vocabs` | `list[VocabName] \| None` | vocabularies requiring an exact match |

| Output type |
| ----------- |
| `AdsDict`   |

```python
from auction.simulation.filters.match_filter import filter_by_fuzzy_match

# Ordinary fuzzy with a distance limit
fuzzy_ads = filter_by_fuzzy_match(request, ads, max_distance=0.7)

# Device and geo must match exactly
fuzzy_ads = filter_by_fuzzy_match(request, ads, max_distance=0.7,
                                   strict_vocabs=['Device', 'City'])
```

### filter\_by\_min\_interval

```python
def filter_by_min_interval(
    ads: AdsDict,
    user_ad_show_times: AdShowTimes,
    current_time: datetime,
) -> AdsDict
```

Filters by the minimum interval between impressions to one user.

```python
from auction.simulation.filters.min_interval_filter import filter_by_min_interval

# user_ad_show_times: AdShowTimes from get_user_ad_show_times(driver, user_id)
filtered = filter_by_min_interval(ads, user_ad_show_times, current_time)
```

### filter\_by\_fuzzy\_targeting\_frequency

```python
def filter_by_fuzzy_targeting_frequency(
    ads: AdsDict,
    ad_total_counts: AdTotalCounts,
) -> AdsDict
```

Filters by the absolute limit of impressions with fuzzy targeting (`parasitic_freq_limit`).

Checks the total number of FUZZY impressions (`ad_total_counts`) against
the monthly limit from the ad's `parasitic_freq_limit`. Applied before fuzzy matching.

```python
from auction.simulation.filters.fuzzy_targeting_filter import filter_by_fuzzy_targeting_frequency

# ad_total_counts: AdTotalCounts from get_ad_total_counts(driver)
filtered = filter_by_fuzzy_targeting_frequency(ads, ad_total_counts)
```

### filter\_by\_fuzzy\_targeting\_percent\_frequency

```python
def filter_by_fuzzy_targeting_percent_frequency(
    ads: AdsDict,
    ad_total_counts: AdTotalCounts,
    percent: float = 0.1,
) -> AdsDict
```

A dynamic limit of off-target impressions: `floor(ad_frequency_limit[m] × percent)`.

```python
from auction.simulation.filters.fuzzy_targeting_filter import filter_by_fuzzy_targeting_percent_frequency

filtered = filter_by_fuzzy_targeting_percent_frequency(ads, ad_total_counts, percent=0.15)
```

### filter\_by\_precise\_match

```python
def filter_by_precise_match(request: Request, ads: AdsDict) -> AdsDict
```

Keeps ads that exactly match the request tags.

```python
from auction.simulation.filters.match_filter import filter_by_precise_match

precise_ads = filter_by_precise_match(request, ads)
```

### filter\_by\_user\_frequency

```python
def filter_by_user_frequency(
    ads: AdsDict,
    user_ad_timestamps: AdTimestamps,
    current_time: datetime,
) -> AdsDict
```

Filters by the frequency limits for a specific user (sliding window).

```python
from auction.simulation.filters.user_frequency_filter import filter_by_user_frequency

# user_ad_timestamps: AdTimestamps from get_user_ad_timestamps(driver, user_id)
filtered = filter_by_user_frequency(ads, user_ad_timestamps, current_time)
```

## Report generation

All functions are in `auction.simulation.report.report_creation`.

### create\_report\_dict

```python
def create_report_dict(
    ads: AdsDict,
    flow_size: int,
    vocab_stats: dict,
    name: str,
) -> ReportDict
```

Creates the initial report dictionary.

```python
from auction.simulation.report.report_creation import create_report_dict, get_vocab_stats

vocab_stats = get_vocab_stats(vocabs, requests)
report = create_report_dict(ads, flow_size=len(requests), vocab_stats=vocab_stats, name='sim_v1')
```

### finish\_report

```python
def finish_report(
    driver: MockDriver,
    res: ReportDict,
    uniq_users: dict,
) -> ReportDict
```

Finalizes the report: computes the final utilization, the share of impressions with fuzzy targeting, and sellout.

```python
from auction.simulation.report.report_creation import finish_report

finish_report(driver, report, uniq_users)
```

### get\_vocab\_stats

```python
def get_vocab_stats(vocabs: TargetVector, requests: list[Request]) -> dict
```

Builds `{vocab_name → {full_tag → count}}` over the request stream.

```python
vocab_stats = get_vocab_stats(vocabs, requests)
```

### make\_gisto

```python
def make_gisto(users: dict, output_dir: str = 'report') -> None
```

Generates `requests_distribution.csv` and `requests_histogram.png`.

```python
make_gisto(uniq_users, output_dir='output/report')
```

### save\_logs

```python
def save_logs(request_to_ad: dict, output_dir: str = 'report') -> None
```

Saves `logs.csv`: the mapping `request_id → ad_id` (the value `-1` on MISS).

```python
save_logs(request_to_ad, output_dir='output/report')
```

### save\_report (report\_creation)

```python
def save_report(res: ReportDict, output_dir: str = 'report') -> None
```

Saves the final JSON report to the file `report.json` inside `output_dir`.

| Input attribute | Type         | Purpose |
| --------------- | ------------ | ------- |
| `res`           | `ReportDict` | the final report from `finish_report()` |
| `output_dir`    | `str`        | folder to save to (created if necessary) |

| Output type |
| ----------- |
| `None`      |

```python
from auction.simulation.report.report_creation import save_report as save_report_full

save_report_full(report, output_dir='output/report')
```

### update\_report

```python
def update_report(
    driver: MockDriver,
    res: ReportDict,
    shown: int,
    date: datetime,
) -> ReportDict
```

Adds a periodic statistics snapshot. `date` is used as the period's timestamp.
Uses the total counters (`ad_total_counts`) from MockDriver.

```python
from auction.simulation.report.report_creation import update_report

update_report(driver, report, shown=n, date=current_time)
```

### update\_report\_with\_request\_tags

```python
def update_report_with_request_tags(
    report: ReportDict,
    ad: Ad,
    request: Request,
) -> None
```

Updates the `target_requests_in_flow` counter for an ad in the report.
Checks for an exact match of the request tags with the ad's targeting (precise logic).

```python
from auction.simulation.report.report_creation import update_report_with_request_tags

for request in requests:
    for ad in get_ads_dict(ads).values():
        update_report_with_request_tags(report, ad, request)
```

## Simulation control

All functions are in `auction.simulation.driver.driver` and `auction.simulation.driver.builder`.

### create\_mock\_driver

```python
def create_mock_driver(ads: AdsDict, vocabs: TargetVector) -> MockDriver
```

```python
from auction.simulation.driver.builder import create_mock_driver

driver = create_mock_driver(ads=ads_dict, vocabs=vocabs_dict)
```

### get\_ad\_show\_times

```python
def get_ad_show_times(driver: MockDriver, ad_ids: list[AdId] | None = None) -> AdShowTimes
```

Returns the last impression time for each ad.

```python
from auction.simulation.driver.driver import get_ad_show_times

show_times = get_ad_show_times(driver)
# AdShowTimes = dict[AdId, datetime]
```

### get\_ad\_stats

```python
def get_ad_stats(
    driver: MockDriver,
    ad_ids: list[AdId] | None = None,
    current_time: datetime | None = None,
) -> AdStats
```

Computes `AdStats` from the timestamp lists for auction strategies.
`current_time` sets the reference point of the sliding windows.

```python
from auction.simulation.driver.driver import get_ad_stats

ad_ids = list(get_ads_dict(filtered_ads).keys())
stats = get_ad_stats(driver, ad_ids, current_time)
```

### get\_ad\_timestamps

```python
def get_ad_timestamps(
    driver: MockDriver,
    ad_ids: list[AdId] | None = None,
) -> AdTimestamps
```

Returns the ads' timestamp lists for the frequency filters.

```python
from auction.simulation.driver.driver import get_ad_timestamps

ad_timestamps = get_ad_timestamps(driver)
# AdTimestamps = dict[AdId, TimestampList]

# Only for specific ads
ad_timestamps = get_ad_timestamps(driver, ad_ids=['ad_1', 'ad_2'])
```

### get\_ad\_total\_counts

```python
def get_ad_total_counts(
    driver: MockDriver,
    ad_ids: list[AdId] | None = None,
) -> AdTotalCounts
```

Returns the total impression counters over the whole simulation by auction type.
Used by the report and by the off-target impression filter.

```python
from auction.simulation.driver.driver import get_ad_total_counts

counts = get_ad_total_counts(driver)
# dict[AdId, dict[AuctionTypeId, int]]
# Example: {'ad_1': {'precise': 320, 'fuzzy': 45}}
```

### get\_ads

```python
def get_ads(driver: MockDriver) -> AdsDict
```

```python
from auction.simulation.driver.driver import get_ads

ads = get_ads(driver)  # AdsDict
```

### get\_user\_ad\_show\_times

```python
def get_user_ad_show_times(driver: MockDriver, user_id: UserId) -> AdShowTimes
```

Returns the times of the last impressions for a specific user.
Used by `filter_by_min_interval`.

```python
from auction.simulation.driver.driver import get_user_ad_show_times

user_show_times = get_user_ad_show_times(driver, user_id)
# AdShowTimes = dict[AdId, datetime]
```

### get\_user\_ad\_stats

```python
def get_user_ad_stats(
    driver: MockDriver,
    user_id: UserId,
    current_time: datetime | None = None,
) -> AdStats
```

Computes the user's `AdStats` from the timestamp lists.

```python
from auction.simulation.driver.driver import get_user_ad_stats

user_stats = get_user_ad_stats(driver, user_id, current_time)
```

### get\_user\_ad\_timestamps

```python
def get_user_ad_timestamps(driver: MockDriver, user_id: UserId) -> AdTimestamps
```

Returns the timestamp lists for a specific user.

```python
from auction.simulation.driver.driver import get_user_ad_timestamps

user_timestamps = get_user_ad_timestamps(driver, user_id)
# AdTimestamps = dict[AdId, TimestampList]
```

### get\_vocabs

```python
def get_vocabs(driver: MockDriver) -> TargetVector
```

```python
from auction.simulation.driver.driver import get_vocabs

vocabs = get_vocabs(driver)
```

### reset\_statistics\_if\_needed

```python
def reset_statistics_if_needed(driver: MockDriver, request: Request) -> None
```

Trims stamps older than `MAX_WINDOW_SECONDS` for all ads
and for the current user.

**Called once at the start of processing each request.**

```python
from auction.simulation.driver.driver import reset_statistics_if_needed

reset_statistics_if_needed(driver, request)
```

### update\_statistics

```python
def update_statistics(
    driver: MockDriver,
    request: Request,
    auction_type: AuctionTypeId,
    ad_id: AdId | None,
) -> None
```

Updates the statistics after an auction result.

- On `HIT` (`ad_id is not None`): adds a datetime stamp to `ad_timestamps` and
  `user_ad_timestamps`, increments `ad_total_counts[ad_id][auction_type]`
- On `MISS` (`ad_id is None`): the statistics are not changed

```python
from auction.simulation.driver.driver import update_statistics
from constants import AuctionType

update_statistics(driver, request, AuctionType.PRECISE, winner_id)
update_statistics(driver, request, AuctionType.PRECISE, None)  # MISS
```

## Examples

### Preparing data for the simulation

#### Ads

```json
[
    {
        "id": "ad_1",
        "active": true,
        "start_date": "2025-07-01T00:00:00",
        "end_date": "2025-07-31T00:00:00",
        "cpm": 1260.0,
        "priority": 1.0,
        "volume": 500,
        "targets": {"City": ["Moscow", "Kazan"]},
        "ad_frequency_limit": {"d": 100, "h": 20, "w": 500, "m": 2000, "t": 10},
        "user_frequency_limit": {"d": 5, "h": 2, "w": 20, "m": 50, "min_interval": 300},
        "parasitic_freq_limit": {"m": 50},
        "vocabulary_weights": {},
        "tag_weights": {}
    }
]
```

#### Requests — JSON

```json
[
    {
        "client_id": "user_001",
        "date": "2025-07-15T10:00:00",
        "tags": {
            "City": "City:Moscow",
            "Device": "Device:Smartphone"
        }
    }
]
```

#### Requests — CSV

```
client_id,date,City,Device
user_001,2025-07-15T10:00:00,Moscow,Smartphone
user_002,2025-07-15T10:01:00,Kazan,Tablet
```

#### Tag vocabularies (Vocabs)

```json
{
    "City": ["Moscow", "Kazan", "Saint Petersburg"],
    "Device": ["Smartphone", "Tablet", "PC"]
}
```

### Initializing MockDriver

```python
from helpers import create_ad, create_ads_dict, create_frequency_limits, create_target_vector, get_ad_id
from auction.simulation.driver.builder import create_mock_driver
from datetime import datetime

ad_1 = create_ad(
    id='ad_1',
    active=True,
    targets=create_target_vector({'City': ['Moscow', 'Kazan']}),
    start_date=datetime(2025, 7, 1),
    end_date=datetime(2025, 7, 31),
    cpm=1260.0,
    priority=1.0,
    volume=500,
    ad_frequency_limit=create_frequency_limits(day=100, hour=20),
    user_frequency_limit=create_frequency_limits(day=5, min_interval=300),
    parasitic_freq_limit=create_frequency_limits(month=50),
)

driver = create_mock_driver(
    ads=create_ads_dict({get_ad_id(ad_1): ad_1}),
    vocabs=create_target_vector({'City': ['Moscow', 'Kazan', 'Saint Petersburg']}),
)
```

### Applying filters

```python
from helpers import get_request_user_id, get_request_date, get_ads_dict
from auction.simulation.driver.driver import (
    get_ads, get_ad_timestamps, get_ad_total_counts,
    get_user_ad_timestamps, get_user_ad_show_times,
    reset_statistics_if_needed,
)
from auction.simulation.filters.active_filter import filter_by_active
from auction.simulation.filters.frequency_filter import filter_by_ad_frequency
from auction.simulation.filters.user_frequency_filter import filter_by_user_frequency
from auction.simulation.filters.min_interval_filter import filter_by_min_interval
from auction.simulation.filters.match_filter import filter_by_precise_match, filter_by_fuzzy_match
from auction.simulation.filters.fuzzy_targeting_filter import filter_by_fuzzy_targeting_frequency

reset_statistics_if_needed(driver, request)

user_id = get_request_user_id(request)
current_time = get_request_date(request)

# Getting the data
ad_timestamps     = get_ad_timestamps(driver)
ad_total_counts   = get_ad_total_counts(driver)
user_ad_timestamps = get_user_ad_timestamps(driver, user_id)
user_show_times   = get_user_ad_show_times(driver, user_id)

# Basic filtering
filtered = filter_by_active(get_ads(driver), current_time)
filtered = filter_by_ad_frequency(filtered, ad_timestamps, current_time)
filtered = filter_by_user_frequency(filtered, user_ad_timestamps, current_time)
filtered = filter_by_min_interval(filtered, user_show_times, current_time)

# Matching: precise → fuzzy fallback
precise_ads = filter_by_precise_match(request, filtered)

if not get_ads_dict(precise_ads):
    fuzzy_targeting_filtered = filter_by_fuzzy_targeting_frequency(filtered, ad_total_counts)
    precise_ads = filter_by_fuzzy_match(request, fuzzy_targeting_filtered, max_distance=0.7)
```

### Full simulation cycle

```python
from helpers import create_parameters_ads_stats, get_ads_dict, get_ad_id
from helpers import get_request_user_id, get_request_date
from constants import SelectionFunc, AuctionType
from auction.auction import auction

from auction.simulation.driver.builder import create_mock_driver
from auction.simulation.driver.driver import (
    get_ads, get_ad_timestamps, get_ad_total_counts, get_ad_stats,
    get_user_ad_timestamps, get_user_ad_show_times,
    reset_statistics_if_needed, update_statistics,
)
from auction.simulation.filters.active_filter import filter_by_active
from auction.simulation.filters.frequency_filter import filter_by_ad_frequency
from auction.simulation.filters.user_frequency_filter import filter_by_user_frequency
from auction.simulation.filters.min_interval_filter import filter_by_min_interval
from auction.simulation.filters.match_filter import filter_by_precise_match, filter_by_fuzzy_match
from auction.simulation.filters.fuzzy_targeting_filter import filter_by_fuzzy_targeting_frequency

driver = create_mock_driver(ads=ads, vocabs=vocabs)

for request in requests:
    user_id = get_request_user_id(request)
    current_time = get_request_date(request)

    # 1. Trim stale stamps
    reset_statistics_if_needed(driver, request)

    # 2. Data for filtering
    ads_snap          = get_ads(driver)
    ad_timestamps     = get_ad_timestamps(driver)
    ad_total_counts   = get_ad_total_counts(driver)
    user_ad_timestamps = get_user_ad_timestamps(driver, user_id)
    user_show_times   = get_user_ad_show_times(driver, user_id)

    # 3. Basic filtering
    filtered = filter_by_active(ads_snap, current_time)
    filtered = filter_by_ad_frequency(filtered, ad_timestamps, current_time)
    filtered = filter_by_user_frequency(filtered, user_ad_timestamps, current_time)
    filtered = filter_by_min_interval(filtered, user_show_times, current_time)

    # 4. Matching
    precise_ads = filter_by_precise_match(request, filtered)

    if get_ads_dict(precise_ads):
        # 5a. Precise auction
        ad_ids = list(get_ads_dict(precise_ads).keys())
        params = create_parameters_ads_stats(
            auction_type=SelectionFunc.BEST_VELOCITY,
            ads_stats=get_ad_stats(driver, ad_ids, current_time),
        )
        winner = auction(precise_ads, params)
        auction_type = AuctionType.PRECISE
    else:
        # 5b. Fuzzy fallback (with a cap on off-target impressions)
        fuzzy_targeting_filtered = filter_by_fuzzy_targeting_frequency(filtered, ad_total_counts)
        fuzzy_ads = filter_by_fuzzy_match(request, fuzzy_targeting_filtered)
        if get_ads_dict(fuzzy_ads):
            ad_ids = list(get_ads_dict(fuzzy_ads).keys())
            params = create_parameters_ads_stats(
                auction_type=SelectionFunc.BEST_PRICE,
                ads_stats=get_ad_stats(driver, ad_ids, current_time),
            )
            winner = auction(fuzzy_ads, params)
        else:
            winner = None
        auction_type = AuctionType.FUZZY

    # 6. Update statistics
    winner_id = get_ad_id(winner) if winner is not None else None
    update_statistics(driver, request, auction_type, winner_id)
```

### Loading data from files

```python
from auction.helpers import (
    load_ads_from_json,
    load_vocabs_from_json,
    load_requests_from_json,
    load_requests_from_csv,
    sort_request,
)
from auction.simulation.data_loader.loaders import save_report
from auction.simulation.driver.builder import create_mock_driver
from auction.simulation.report.report_creation import (
    create_report_dict, get_vocab_stats, update_report_with_request_tags,
    update_report, finish_report,
)

# Loading data (JSON or CSV for requests)
ads    = load_ads_from_json('data/ads.json')
vocabs = load_vocabs_from_json('data/vocabs.json')
requests = sort_request(load_requests_from_json('data/requests.json'))
# or: requests = sort_request(load_requests_from_csv('data/requests.csv', vocabs))

driver = create_mock_driver(ads=ads, vocabs=vocabs)
vocab_stats = get_vocab_stats(vocabs, requests)
report = create_report_dict(ads, flow_size=len(requests), vocab_stats=vocab_stats, name='sim_v1')

# Pre-counting target requests
for req in requests:
    for ad in get_ads_dict(ads).values():
        update_report_with_request_tags(report, ad, req)

last_date = None
# ... simulation loop ...
#     last_date = current_time
#     if n % 1000 == 0:
#         update_report(driver, report, shown=n, date=current_time)

update_report(driver, report, shown=len(requests), date=last_date)
finish_report(driver, report, uniq_users)
save_report(report, 'output/report.json')
```
