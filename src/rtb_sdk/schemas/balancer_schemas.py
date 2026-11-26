from __future__ import annotations

from datetime import datetime
from typing import Callable, Iterable, Literal, TypedDict

from rtb_sdk.schemas.auction_schemas import Ad, AdId, FullTag, VocabName, RawTag
from rtb_sdk.constants.balancer_constants import OBJECTIVES


# input and output - RawTags
# inside - FullTags


type InnerVocab = list[FullTag]
type InnerVocabs = dict[VocabName, InnerVocab]

type OuterVocab = list[RawTag]
type OuterVocabs = dict[VocabName, OuterVocab]


class RequestFlow(TypedDict):
    tags: tuple[FullTag, ...]
    probability: float

class RequestFlowWithAd(RequestFlow):
    ad_id: AdId


type ProjectedAdVolumes = dict[AdId, int]
type BalanceResult = ProjectedAdVolumes

class InnerAd(TypedDict):
    id: AdId
    targets: dict[VocabName, list[FullTag]]
    min_vol: int
    max_vol: int
    price: float
    date_factor: float
    freq: int


class FullTagWithProbability(TypedDict):
    tag: FullTag
    probability: float


# ---------------------------------------------------------------------------
# Seasonal mode: data types
# ---------------------------------------------------------------------------

# Aggregation mode: by hour of day (24 values) or by hour of week (168 values).
AggregationMode = Literal['hour_of_day', 'hour_of_week']

# Hourly slot index: 0–23 for 'hour_of_day', 0–167 for 'hour_of_week'.
HourType = int


class PeriodWindow(TypedDict):
    """Validated pair of start/end of the balancing period.

    Both fields are required — unlike BalancingParams, where they are
    optional. The presence of PeriodWindow in a signature means "the period
    has already been validated".
    """
    period_start: datetime  # start of the period (aware datetime, UTC recommended)
    period_end: datetime    # end of the period, exclusive (aware datetime)


class HourlyWeights(TypedDict):
    """Normalized seasonality profile.

    mode='hour_of_day'  → 24 keys (0-23); the profile is applied
                          cyclically to each day of the period.
    mode='hour_of_week' → 168 keys (0-167 = 7 days × 24 hours);
                          stores the weekday/weekend difference.

    Invariant: sum(weights.values()) ≈ 1.0  (±ε).
    """
    mode: AggregationMode
    weights: dict[HourType, float]


class AdditionalContext(TypedDict):
    """Data for a single hourly slot within a SeasonalContext.

    Created by build_seasonal_context for each HourType falling
    within the balancing period.
    """
    weight: float
    # Normalized weight of the slot in the period's total traffic (sum over all
    # hours ≈ 1.0). Determines the share of total_traffic_volume for the given hour.

    user_activity_ratio: dict[AdId, float]
    # Saturation coefficient by frequency limit for each ad.
    # coef = Σ min(r_i, user_hour_limit) / Σ r_i, where r_i is the number of requests
    # of the i-th user in this hour from the log. coef = 1.0 if there is no limit.

    tags_probability: dict[VocabName, dict[RawTag, float]] | None
    # Tag probabilities from the log for this hour. None → params['tag_probabilities']
    # is used (global, without regard to the hour).


class SeasonalContext(TypedDict):
    """Bundle of hourly data prepared before calling seasonal_balance_traffic.

    Built by build_seasonal_context from CSV logs and ads.
    Embedded into SeasonalBalancingParams['seasonal_context'] before calling
    the seasonal balancing functions.
    """
    mode: AggregationMode
    # Aggregation mode: 'hour_of_day' (0-23) or 'hour_of_week' (0-167).

    context: dict[HourType, AdditionalContext]
    # Data for each active hourly slot.


class HistoricalLogsConfig(TypedDict, total=False):
    """Configuration of streaming CSV log loading.

    All fields are optional at the TypedDict level (total=False), but path and
    timestamp_col are required in meaning — build_seasonal_context
    will raise KeyError if they are missing.
    """
    path: str                # path to the CSV file
    timestamp_col: str       # name of the column with the timestamp (ISO-8601)

    count_col: str | None
    # Column with the event count; None = count each row as 1 event.

    user_id_col: str | None
    # Column with the user identifier.
    # If present — build_seasonal_context collects per-hour user counts
    # for computing user_activity_ratio. None → coef = 1.0.

    chunk_size: int
    # Rows per chunk; default 10_000.

    aggregation_mode: AggregationMode
    # 'hour_of_day'  → 24-element profile
    # 'hour_of_week' → 168-element profile
    # Default 'hour_of_day'.

    timezone: str
    # IANA timezone, e.g. 'Europe/Moscow'; default 'UTC'.


# ---------------------------------------------------------------------------
# Balancing parameter hierarchy
# ---------------------------------------------------------------------------

# Level 1 — internal, FullTag format, base of the hierarchy
class OptimizeParams(TypedDict, total=False):
    total_traffic_volume:     int                       # Total traffic volume (≥ 0)
    objective:                OBJECTIVES                # Default: MAX_MONEY
    max_n_categories:         int                       # Default: 100
    min_category_probability: float                     # Default: MIN_CATEGORY_PROBABILITY
    n_threads:                int                       # Default: 1
    tag_probabilities:        dict[FullTag, float]      # FullTag: "vocab:rawtag"
    vocabs:                   InnerVocabs


# Level 2 — public, inherits OptimizeParams
class BalancingParams(OptimizeParams, total=False):
    seasonal_context:         AdditionalContext | None  # one hour (None = no seasonality)


class ExtendedBalancingParams(BalancingParams, total=False):
    ad_vol_distr:             ProjectedAdVolumes        # for add_campaign, predict_rebalance


class BalancingBySelloutParams(BalancingParams, total=False):
    accuracy_percent:         float
    func_replace_infinity:    Callable[[Iterable[float]], int] | None


# Level 3 — seasonal, inherits OptimizeParams directly
class SeasonalBalancingParams(OptimizeParams, total=False):
    seasonal_context:         SeasonalContext           # the whole period, all hours
    period:                   PeriodWindow              # replaces period_start + period_end


class SeasonalBalancingBySelloutParams(SeasonalBalancingParams, total=False):
    accuracy_percent:         float
    func_replace_infinity:    Callable[[Iterable[float]], int] | None


class AddCampaignResult(TypedDict):
    report: BalanceResult
    new_ads_volumes: ProjectedAdVolumes


class RebalanceResult(TypedDict):
    report: BalanceResult
    volume_delta: ProjectedAdVolumes


# Single type: vocabs contains RawTags (OuterVocabs)
class BalancerAuctionData(TypedDict):
    vocabs: OuterVocabs
    tag_probabilities: dict[VocabName, dict[RawTag, float]]
    ads_distribution: ProjectedAdVolumes
    ads_probabilities: dict[AdId, float]
    ads_total: int


class AuctionParamsBalanced(TypedDict):
    request: dict[VocabName, RawTag]
    vocabs: OuterVocabs
    balancer_data: BalancerAuctionData | None


class BalancingBySelloutResult(TypedDict):
    report: BalanceResult
    sellout_percent: float


# ---------------------------------------------------------------------------
# Level-3 recommended bid forecaster
# ---------------------------------------------------------------------------

BidDirection = Literal['minimize', 'maximize']
ForecastMode = Literal[1, 2, 3, 4]


class BidForecastParams(SeasonalBalancingParams, total=False):
    """Parameters of the recommended bid forecaster.

    Inherits SeasonalBalancingParams:
      seasonal_context, period, total_traffic_volume,
      tag_probabilities, vocabs, objective.

    Does not contain sellout fields (accuracy_percent, func_replace_infinity).
    """
    ad:                  Ad                     # our ad
    max_budget:          int | float            # maximum campaign budget (money)
    min_impressions:     int                    # minimum required number of impressions
    budget_tolerance:    float                  # allowed budget overrun, % (default 0)
    bid_direction:       BidDirection           # 'minimize' | 'maximize'
    min_bid:             float                  # lower CPM bound for the search
    ads:                 dict[AdId, Ad]         # competitors (modes 1–4)
    current_report:      BalanceResult          # current distribution (basis for the cannibalization Δ)
    search_accuracy:     float                  # accuracy of the binary search over CPM
    max_cannibalization: float                  # cannibalization threshold (mode 4 only)
    max_bid:             float                  # upper bound of the sweep (internal mode)
    n_points:            int                    # sweep points (internal mode, default 50)
    mode:                ForecastMode           # 1..4


# ---------------------------------------------------------------------------
# Level-3 results of the bid forecaster
# ---------------------------------------------------------------------------

class CannibalizationReport(TypedDict):
    per_ad:   dict[AdId, int]    # impression loss of each campaign (≥ 0)
    relative: dict[AdId, float]  # % of current_report[ad_id]
    total:    int                # total loss across all competitors


class BidForecastResult(TypedDict):
    recommended_bid:      float                         # found CPM (min or max)
    expected_impressions: int                           # impressions at recommended_bid
    expected_spend:       float                         # expected_impressions × recommended_bid / 1000
    cannibalization:      CannibalizationReport | None  # None if there are no competitors


class OpportunityResult(TypedDict):
    max_impressions: int    # impression ceiling without competitors
    max_spend:       float  # max_impressions × min_bid / 1000


class DeliveryPoint(TypedDict):
    bid:         float
    impressions: int
    spend:       float


class DeliveryResult(TypedDict):
    curve:       list[DeliveryPoint]
    opportunity: int    # absolute ceiling (from mode 1)
