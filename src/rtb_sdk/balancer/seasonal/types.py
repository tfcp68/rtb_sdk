"""
Data types of the seasonal balancer.

The public types (AdditionalContext, SeasonalContext, PeriodWindow, HourlyWeights,
HistoricalLogsConfig, AggregationMode, HourType) are defined in
rtb_sdk.schemas.balancer_schemas and re-exported from here for
convenient imports inside the package.

Only the internal types of streaming log processing live here
(LogStreamState, TagCountsByHour).
"""

from __future__ import annotations

from typing import TypedDict

# Public types — defined in schemas, re-exported here
from rtb_sdk.schemas.balancer_schemas import (
    AdditionalContext,
    AggregationMode,
    HistoricalLogsConfig,
    HourlyWeights,
    HourType,
    PeriodWindow,
    SeasonalContext,
)

from rtb_sdk.schemas.auction_schemas import RawTag, VocabName


# ---------------------------------------------------------------------------
# Internal types of streaming log processing
# ---------------------------------------------------------------------------

# Accumulator of tag counts before normalization.
# {h_type: {VocabName: {RawTag: accumulated_count}}}
TagCountsByHour = dict[HourType, dict[VocabName, dict[RawTag, float]]]


class LogStreamState(TypedDict):
    """Mutable intermediate state during streaming log processing.

    Passed to process_log_chunk and updated in place.
    After a pass over the whole file it holds the aggregates for normalization.
    """
    counts: dict[HourType, float]
    # {h_type: accumulated_event_count} — basis for HourlyWeights.

    user_counts_by_hour: dict[HourType, dict[str, int]]
    # {h_type: {user_id: request_count}} — hourly user activity.
    # Used to compute the ratio for hourly (h) user_frequency_limit limits.
    # Empty dict if user_id_col is not set in the config.

    user_counts_total: dict[str, int]
    # {user_id: total_request_count} — total user activity over the period.
    # Used to compute the ratio for non-hourly (d/w/m) user_frequency_limit limits.
    # Empty dict if user_id_col is not set in the config.

    tag_counts: TagCountsByHour
    # {h_type: {VocabName: {RawTag: count}}} — for tags_probability.
    # Empty dict if tag_col_map is not passed to process_log_chunk.

    mode: AggregationMode
    # Aggregation mode, copied from HistoricalLogsConfig.
