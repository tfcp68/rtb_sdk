"""
Seasonal balancing package.

Public exports:

    Types (types.py):
        AggregationMode, HourType
        PeriodWindow, HourlyWeights
        AdditionalContext, SeasonalContext
        HistoricalLogsConfig, LogStreamState, TagCountsByHour

    Splitting into slots (slots.py):
        resolve_weights, compute_hours, hour_type, n_active_hours

    Ad correction (corrections.py):
        prepare_slot_ads, prepare_hour_ads
        is_ad_active, compute_hour_limit, apply_histogram_correction

    Streaming log aggregation (seasonality.py):
        build_seasonality_profile
        process_log_chunk, normalize_counts
        accumulate_tag_counts, normalize_tag_counts

    Level-2 functions (functions/*.py) — one hour:
        hour_balance_traffic
        hour_add_new_balanced_campaign
        hour_predict_rebalance
        hour_balance_by_sellout

    Level-3 functions — date range:

        balance.py (with targeting / seasonal):
            build_seasonal_context
            seasonal_balance_traffic
            seasonal_balance_by_sellout

        open.py (without targeting / RoN):
            open_balance_traffic
"""

from rtb_sdk.balancer.seasonal.types import (
    AdditionalContext,
    AggregationMode,
    HistoricalLogsConfig,
    HourlyWeights,
    HourType,
    LogStreamState,
    PeriodWindow,
    TagCountsByHour,
    SeasonalContext,
)

from rtb_sdk.balancer.seasonal.slots import (
    compute_hours,
    hour_type,
    n_active_hours,
    resolve_weights,
)

from rtb_sdk.balancer.seasonal.corrections import (
    apply_histogram_correction,
    compute_hour_limit,
    compute_period_limit,
    is_ad_active,
    prepare_hour_ads,
    prepare_slot_ads,
)

from rtb_sdk.balancer.seasonal.seasonality import (
    accumulate_tag_counts,
    build_seasonality_profile,
    normalize_counts,
    normalize_tag_counts,
    process_log_chunk,
)

from rtb_sdk.balancer.functions.balance_traffic import balance_traffic as hour_balance_traffic
from rtb_sdk.balancer.functions.add_campaign import add_new_balanced_campaign as hour_add_new_balanced_campaign
from rtb_sdk.balancer.functions.predict_rebalance import predict_rebalance as hour_predict_rebalance
from rtb_sdk.balancer.functions.balance_by_sellout import balance_by_sellout as hour_balance_by_sellout

from rtb_sdk.balancer.seasonal.balance import (
    build_seasonal_context,
    seasonal_add_new_balanced_campaign,
    seasonal_balance_by_sellout,
    seasonal_balance_traffic,
)

from rtb_sdk.balancer.seasonal.open import open_balance_traffic

from rtb_sdk.balancer.seasonal.forecast import forecast_bid

__all__ = [
    # types
    "AggregationMode",
    "HourType",
    "PeriodWindow",
    "HourlyWeights",
    "AdditionalContext",
    "SeasonalContext",
    "HistoricalLogsConfig",
    "LogStreamState",
    "TagCountsByHour",
    # slots
    "resolve_weights",
    "compute_hours",
    "hour_type",
    "n_active_hours",
    # corrections
    "prepare_slot_ads",
    "prepare_hour_ads",
    "is_ad_active",
    "compute_hour_limit",
    "compute_period_limit",
    "apply_histogram_correction",
    # seasonality
    "build_seasonality_profile",
    "process_log_chunk",
    "normalize_counts",
    "accumulate_tag_counts",
    "normalize_tag_counts",
    # level-2 functions (hour.py)
    "hour_balance_traffic",
    "hour_add_new_balanced_campaign",
    "hour_predict_rebalance",
    "hour_balance_by_sellout",
    # level-3 functions (balance.py) — seasonal / with targeting
    "build_seasonal_context",
    "seasonal_balance_traffic",
    "seasonal_balance_by_sellout",
    "seasonal_add_new_balanced_campaign",
    # level-3 functions (open.py) — RoN / without targeting
    "open_balance_traffic",
    # level-3 functions (forecast.py) — bid forecaster
    "forecast_bid",
]
