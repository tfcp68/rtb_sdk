"""
Preparing ads for an hourly slot.

Three consecutive correction stages:
1. Campaign activity share — filters out inactive ones and divides max_vol by the number of active slots.
2. Frequency limit computation — converts all granularities to impressions/hour.
3. Limit correction by the activity histogram — accounts for saturation of super-active users.

The output is a dict[AdId, Ad] with a modified max_vol — ready to be passed to ad_to_inner().
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any

from rtb_sdk.schemas.auction_schemas import AdId

from rtb_sdk.balancer.seasonal.types import (
    AdditionalContext,
)


# ---------------------------------------------------------------------------
# Helper constants
# ---------------------------------------------------------------------------

_DAYS_PER_MONTH = 30.44   # average number of days in a month (gregorian)
_SLOTS_PER_HOUR = 6       # ten-minute slots per hour


# ---------------------------------------------------------------------------
# Campaign activity share
# ---------------------------------------------------------------------------

def is_ad_active(ad: Any, slot_dt: datetime) -> bool:
    """The campaign is active in the given hour.

    If the ad has no start_date or end_date — it is considered always active.
    """
    start = ad.get('start_date')
    end = ad.get('end_date')
    if start is None or end is None:
        return True
    return start <= slot_dt < end


# ---------------------------------------------------------------------------
# Frequency limit computation
# ---------------------------------------------------------------------------

def compute_hour_limit(freq_limits: dict) -> float:
    """The strictest hourly limit across all granularities.

    Converts each granularity to impressions/hour:
      't' (10 min) → limit × 6
      'h'          → limit
      'd'          → limit / 24
      'w'          → limit / 168
      'm'          → limit / (30.44 × 24)

    Returns the minimum over all SET granularities.
    A granularity with value 0 (or absent) is considered unset —
    the convention `0 = no limit`.
    If no granularity is set → float('inf').
    """
    v: dict = freq_limits.get('value', {})
    limits: list[float] = []

    if v.get('t'):
        limits.append(float(v['t']) * _SLOTS_PER_HOUR)
    if v.get('h'):
        limits.append(float(v['h']))
    if v.get('d'):
        limits.append(float(v['d']) / 24)
    if v.get('w'):
        limits.append(float(v['w']) / (24 * 7))
    if v.get('m'):
        limits.append(float(v['m']) / (24 * _DAYS_PER_MONTH))

    return min(limits) if limits else float('inf')


def compute_period_limit(freq_limits: dict, n_hours: float) -> float:
    """Total campaign limit over the whole period.

    Converts each SET granularity to impressions over n_hours and takes the minimum.
    A granularity with value 0 (or absent) is considered unset
    (convention `0 = no limit`). If none is set → float('inf').
    Used both in prepare_slot_ads and in _iter_slots to initialize
    remaining — the dictionary of budget remainders for cross-slot tracking.
    """
    n_days = n_hours / 24
    n_weeks = n_hours / (24 * 7)
    n_months = n_hours / (24 * _DAYS_PER_MONTH)

    v: dict = freq_limits.get('value', {})
    limits: list[float] = []

    if v.get('t'):
        limits.append(float(v['t']) * n_hours * _SLOTS_PER_HOUR)
    if v.get('h'):
        limits.append(float(v['h']) * n_hours)
    if v.get('d'):
        limits.append(float(v['d']) * n_days)
    if v.get('w'):
        limits.append(float(v['w']) * n_weeks)
    if v.get('m'):
        limits.append(float(v['m']) * n_months)

    return min(limits) if limits else float('inf')


# ---------------------------------------------------------------------------
# Limit correction by the activity histogram
# ---------------------------------------------------------------------------

def apply_histogram_correction(
    limit: float,
    histogram: list[int] | None,
    user_period_limit: float,
) -> float:
    """Adjusts the campaign's total limit accounting for saturation of super-active users.

    Computes the share of traffic actually deliverable with user_period_limit impressions per user:
        coef = Σ min(r_i, user_period_limit) / Σ r_i

    where r_i is the number of requests of the i-th user over the period.

    coef = 1.0 if there are no super-active users or histogram is not set.
    coef < 1.0 if part of the traffic is physically undeliverable due to the frequency cap.

    Args:
        limit:             total limit before correction.
        histogram:         list of request counts per user; None → no correction.
        user_period_limit: impression limit for a single user over the period.

    Returns:
        Adjusted limit: limit × coef.
    """
    if not histogram or user_period_limit >= float('inf'):
        return limit

    total = sum(histogram)
    if total == 0:
        return limit

    delivered = sum(min(count, user_period_limit) for count in histogram)
    return limit * (delivered / total)


# ---------------------------------------------------------------------------
# Preparing ads for a slot
# ---------------------------------------------------------------------------

def prepare_hour_ads(
    ads: dict[AdId, Any],
    hour_context: AdditionalContext | None = None,
) -> dict[AdId, dict]:
    """Applies the hourly limits and the saturation coefficient to the ads.

    For each ad:
    1. hour_limit = compute_hour_limit(ad_frequency_limit)  # all granularities → impressions/hour
    2. ratio      = hour_context['user_activity_ratio'].get(id, 1.0)  # 1.0 if context=None
    3. vol        = min(ad.volume, floor(hour_limit)) * ratio
    4. Skip if vol <= 0

    With hour_context=None: ratio=1.0, the limit comes only from ad_freq.
    If ad_frequency_limit is absent: limit=inf → vol = ad.volume * ratio.

    Returns:
        dict[AdId, Ad] with modified volume, min_vol=0.
    """
    coefs: dict[AdId, float] = hour_context['user_activity_ratio'] if hour_context is not None else {}

    result: dict[AdId, dict] = {}
    for ad_id, ad in ads.items():
        ad_freq: dict = ad.get('ad_frequency_limit') or {}
        hour_limit = compute_hour_limit(ad_freq)
        ratio = coefs.get(ad_id, 1.0)

        ad_max = int(ad.get('volume', 0))
        if hour_limit < float('inf'):
            vol = int(min(ad_max, math.floor(hour_limit)) * ratio)
        else:
            vol = int(ad_max * ratio) if ratio < 1.0 else ad_max

        if vol <= 0:
            continue

        result[ad_id] = {**ad, 'volume': vol, 'min_vol': 0}

    return result


def prepare_slot_ads(
    ads: dict[AdId, Any],
    slot_dt: datetime,
    n_active: dict[AdId, int],
    remaining: dict[AdId, int] | None = None,
    slot_weight: float | None = None,
    active_weight: dict[AdId, float] | None = None,
) -> dict[AdId, dict]:
    """Turns the period's ads into ads of a single slot.

    The function's only responsibility is the "period → slot" transition:
    1. Whom to include in the slot: the activity window filter (is_ad_active, n_active).
    2. What volume to give the slot: the share of volume proportional to the slot
       weight (slot_weight / active_weight[id]) with a cross-slot cap
       by the remainder remaining[id]. Without weight information — uniformly
       ceil(volume / n_active) (compatibility with old calls).

    Proportional slicing is needed because of sharply uneven seasonal
    profiles: uniform ceil(volume / n_active) gives a slot with a small
    weight (and hence a small traffic pool) the same share of volume as
    a slot with a large weight — the share does not fit in the slot's pool → LP infeasible,
    even though over the whole period horizon the volume is feasible.

    The frequency limit, user_activity_ratio and the real max_vol are applied BELOW —
    in prepare_hour_ads at Level-2 (called by all hourly functions when
    seasonal_context is present). They are intentionally NOT applied here, to avoid
    double counting (ratio² and a double freq cap).

    Args:
        ads:           original ads {AdId: Ad}.
        slot_dt:       start timestamp of the hourly slot (aware datetime).
        n_active:      precomputed {AdId: n_active_hours}; passed in from outside
                       the loop to avoid an O(H × N) recomputation.
        remaining:     budget remainders from _iter_slots; None → no cross-slot tracking.
        slot_weight:   weight of the current slot from SeasonalContext; None → uniform slicing.
        active_weight: {AdId: sum of weights of the ad's active slots over the period};
                        None → uniform slicing.

    Returns:
        dict[AdId, Ad] with volume divided per slot and min_vol zeroed
        (the slot does not carry the period's contractual minimum).
    """
    result: dict[AdId, dict] = {}

    for ad_id, ad in ads.items():
        # The campaign is inactive this hour — skip
        if not is_ad_active(ad, slot_dt):
            continue

        n = n_active.get(ad_id, 0)
        if n <= 0:
            continue

        # Budget exhausted — skip
        if remaining is not None and remaining.get(ad_id, 0) <= 0:
            continue

        # Share of the period for this slot. ceil instead of int: slot_share < 1 does not
        # zero out low-budget ads. Proportional to the slot weight if
        # it is known, otherwise uniformly over the number of active slots.
        ad_max = int(ad.get('volume', 0))
        ad_active_weight = active_weight.get(ad_id, 0.0) if active_weight is not None else 0.0
        if slot_weight is not None and ad_active_weight > 0:
            slot_max_vol = math.ceil(ad_max * slot_weight / ad_active_weight)
        else:
            slot_max_vol = math.ceil(ad_max / n)

        # Cross-slot tracking: do not exceed the period's budget remainder
        if remaining is not None:
            slot_max_vol = min(slot_max_vol, remaining[ad_id])

        if slot_max_vol <= 0:
            continue

        result[ad_id] = {**ad, 'volume': slot_max_vol, 'min_vol': 0}

    return result
