"""
Getters and creators for the seasonal-mode types of the balancer.

Cover: AdditionalContext, SeasonalContext, PeriodWindow, HistoricalLogsConfig,
           SeasonalBalancingParams, SeasonalBalancingBySelloutParams.
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Iterable

from rtb_sdk.schemas.balancer_schemas import (
    AdditionalContext,
    AggregationMode,
    HistoricalLogsConfig,
    HourType,
    HourlyWeights,
    PeriodWindow,
    SeasonalContext,
    SeasonalBalancingParams,
    SeasonalBalancingBySelloutParams,
    OptimizeParams,
    OuterVocabs,
)
from rtb_sdk.schemas.auction_schemas import AdId, VocabName, RawTag, FullTag
from rtb_sdk.constants.balancer_constants import (
    MAX_MONEY,
    MIN_CATEGORY_PROBABILITY,
    DEFAULT_ACCURACY_PERCENT,
    DEFAULT_FUNC_REPLACE_INFINITY,
    OBJECTIVES,
)
from rtb_sdk.helpers.balancer.full_tag_helpers import (
    raw_tag_dict_to_full_tag_dict,
    outer_tag_probabilities_to_inner,
)


# ---------------------------------------------------------------------------
# AdditionalContext
# ---------------------------------------------------------------------------

def create_additional_context(
    weight: float,
    user_activity_ratio: dict[AdId, float],
    tags_probability: dict[VocabName, dict[RawTag, float]] | None = None,
) -> AdditionalContext:
    """Creates an AdditionalContext for a single hourly slot."""
    return AdditionalContext(
        weight=weight,
        user_activity_ratio=user_activity_ratio,
        tags_probability=tags_probability,
    )


def get_additional_context_weight(ctx: AdditionalContext) -> float:
    """Normalized weight of the slot in the period's total traffic."""
    return ctx['weight']


def get_additional_context_user_activity_ratio(ctx: AdditionalContext) -> dict[AdId, float]:
    """User saturation coefficients per ad."""
    return ctx['user_activity_ratio']


def get_additional_context_tags_probability(
    ctx: AdditionalContext,
) -> dict[VocabName, dict[RawTag, float]] | None:
    """Tag probabilities from the log for this hour (None → use the global ones)."""
    return ctx.get('tags_probability')


# ---------------------------------------------------------------------------
# SeasonalContext
# ---------------------------------------------------------------------------

def create_seasonal_context(
    mode: AggregationMode,
    context: dict[HourType, AdditionalContext],
) -> SeasonalContext:
    """Creates a SeasonalContext from the aggregation mode and hourly data."""
    return SeasonalContext(mode=mode, context=context)


def get_seasonal_context_mode(ctx: SeasonalContext) -> AggregationMode:
    """Aggregation mode: 'hour_of_day' or 'hour_of_week'."""
    return ctx['mode']


def get_seasonal_context_context(ctx: SeasonalContext) -> dict[HourType, AdditionalContext]:
    """Dictionary of hourly data {HourType: AdditionalContext}."""
    return ctx['context']


# ---------------------------------------------------------------------------
# PeriodWindow
# ---------------------------------------------------------------------------

def create_period_window(
    period_start: datetime,
    period_end: datetime,
) -> PeriodWindow:
    """Creates a PeriodWindow from the start and end of the period."""
    return PeriodWindow(period_start=period_start, period_end=period_end)


def get_period_window_start(pw: PeriodWindow) -> datetime:
    """Start of the balancing period (inclusive)."""
    return pw['period_start']


def get_period_window_end(pw: PeriodWindow) -> datetime:
    """End of the balancing period (exclusive)."""
    return pw['period_end']


# ---------------------------------------------------------------------------
# HourlyWeights
# ---------------------------------------------------------------------------

def create_hourly_weights(
    mode: AggregationMode,
    weights: dict[HourType, float],
) -> HourlyWeights:
    """Creates HourlyWeights from the mode and normalized weights."""
    return HourlyWeights(mode=mode, weights=weights)


def get_hourly_weights_mode(hw: HourlyWeights) -> AggregationMode:
    return hw['mode']


def get_hourly_weights_weights(hw: HourlyWeights) -> dict[HourType, float]:
    return hw['weights']


# ---------------------------------------------------------------------------
# HistoricalLogsConfig
# ---------------------------------------------------------------------------

def create_historical_logs_config(
    path: str,
    timestamp_col: str,
    *,
    count_col: str | None = None,
    user_id_col: str | None = None,
    chunk_size: int = 10_000,
    aggregation_mode: AggregationMode = 'hour_of_day',
    timezone: str = 'UTC',
) -> HistoricalLogsConfig:
    """Creates a HistoricalLogsConfig with explicit parameters (all optional ones have defaults)."""
    return HistoricalLogsConfig(
        path=path,
        timestamp_col=timestamp_col,
        count_col=count_col,
        user_id_col=user_id_col,
        chunk_size=chunk_size,
        aggregation_mode=aggregation_mode,
        timezone=timezone,
    )


def get_historical_logs_config_path(cfg: HistoricalLogsConfig) -> str:
    return cfg['path']


def get_historical_logs_config_timestamp_col(cfg: HistoricalLogsConfig) -> str:
    return cfg['timestamp_col']


def get_historical_logs_config_aggregation_mode(cfg: HistoricalLogsConfig) -> AggregationMode:
    return cfg.get('aggregation_mode', 'hour_of_day')


def get_historical_logs_config_timezone(cfg: HistoricalLogsConfig) -> str:
    return cfg.get('timezone', 'UTC')


def get_historical_logs_config_chunk_size(cfg: HistoricalLogsConfig) -> int:
    return cfg.get('chunk_size', 10_000)


# ---------------------------------------------------------------------------
# SeasonalBalancingParams (Level 3)
# ---------------------------------------------------------------------------

def create_seasonal_balancing_params(
    total_traffic_volume: int,
    tag_probabilities_outer: dict[VocabName, dict[RawTag, float]],
    vocabs_outer: OuterVocabs,
    seasonal_context: SeasonalContext,
    period: PeriodWindow,
    objective: OBJECTIVES = MAX_MONEY,
    max_n_categories: int = 100,
    min_category_probability: float = MIN_CATEGORY_PROBABILITY,
    n_threads: int = 1,
) -> SeasonalBalancingParams:
    """Accepts the outer (RawTag) format, converts it to the inner one."""
    inner_vocabs = raw_tag_dict_to_full_tag_dict(vocabs_outer)
    inner_tag_probs = outer_tag_probabilities_to_inner(tag_probabilities_outer)
    return SeasonalBalancingParams(
        total_traffic_volume=total_traffic_volume,
        tag_probabilities=inner_tag_probs,
        vocabs=inner_vocabs,
        objective=objective,
        max_n_categories=max_n_categories,
        min_category_probability=min_category_probability,
        n_threads=n_threads,
        seasonal_context=seasonal_context,
        period=period,
    )


def get_seasonal_balancing_params_period(params: SeasonalBalancingParams) -> PeriodWindow:
    """Balancing period from SeasonalBalancingParams."""
    return params['period']


def get_seasonal_balancing_params_seasonal_context(params: SeasonalBalancingParams) -> SeasonalContext:
    """Seasonal context from SeasonalBalancingParams."""
    return params['seasonal_context']


def create_seasonal_balance_by_sellout_params(
    total_traffic_volume: int,
    tag_probabilities_outer: dict[VocabName, dict[RawTag, float]],
    vocabs_outer: OuterVocabs,
    seasonal_context: SeasonalContext,
    period: PeriodWindow,
    objective: OBJECTIVES = MAX_MONEY,
    max_n_categories: int = 100,
    min_category_probability: float = MIN_CATEGORY_PROBABILITY,
    n_threads: int = 1,
    accuracy_percent: float = DEFAULT_ACCURACY_PERCENT,
    func_replace_infinity: Callable[[Iterable[float]], int] | None = DEFAULT_FUNC_REPLACE_INFINITY,
) -> SeasonalBalancingBySelloutParams:
    """Accepts the outer (RawTag) format + sellout parameters."""
    base = create_seasonal_balancing_params(
        total_traffic_volume=total_traffic_volume,
        tag_probabilities_outer=tag_probabilities_outer,
        vocabs_outer=vocabs_outer,
        seasonal_context=seasonal_context,
        period=period,
        objective=objective,
        max_n_categories=max_n_categories,
        min_category_probability=min_category_probability,
        n_threads=n_threads,
    )
    return SeasonalBalancingBySelloutParams(
        **base,
        accuracy_percent=accuracy_percent,
        func_replace_infinity=func_replace_infinity,
    )
