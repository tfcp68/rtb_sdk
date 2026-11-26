"""
Splitting traffic into hourly slots.

Pure functions without side effects: they work only with the period,
weights and numbers. They know nothing about the LP solver or ad formats.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from rtb_sdk.balancer.seasonal.types import HourlyWeights, PeriodWindow, SeasonalContext


# ---------------------------------------------------------------------------
# Resolving the weight profile
# ---------------------------------------------------------------------------

def resolve_weights(context: SeasonalContext) -> HourlyWeights:
    """Extracts the weight profile from SeasonalContext.

    Assembles HourlyWeights from the weight fields of AdditionalContext.
    """
    return HourlyWeights(
        mode=context['mode'],
        weights={h: ac['weight'] for h, ac in context['context'].items()},
    )


# ---------------------------------------------------------------------------
# Iterating over hourly slots
# ---------------------------------------------------------------------------

def compute_hours(period: PeriodWindow) -> int:
    """Number of whole hours in the balancing period."""
    return int((period['period_end'] - period['period_start']).total_seconds() // 3600)


def hour_type(dt: datetime, mode: str) -> int:
    """Hour type of a timestamp.

    mode='hour_of_day'  → 0-23 (hour of the day).
    mode='hour_of_week' → 0-167 (hour number within the week: weekday*24 + hour).
    """
    if mode == 'hour_of_week':
        return dt.weekday() * 24 + dt.hour
    return dt.hour


# ---------------------------------------------------------------------------
# Campaign activity within the period
# ---------------------------------------------------------------------------

def n_active_hours(ad: Any, period: PeriodWindow) -> int:
    """Number of hourly slots of the period in which the campaign is active.

    Uses an O(1) overlap formula instead of an O(H) iteration over slots.
    If the ad has no start_date / end_date — it is considered
    active for the whole period.

    Returns:
        int ≥ 0.
    """
    start = ad.get('start_date')
    end = ad.get('end_date')
    if start is None or end is None:
        return compute_hours(period)

    overlap_start = max(start, period['period_start'])
    overlap_end = min(end, period['period_end'])
    if overlap_end <= overlap_start:
        return 0
    return max(0, int((overlap_end - overlap_start).total_seconds() // 3600))
