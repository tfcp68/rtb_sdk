"""
External functions of seasonal balancing (Level 3).

Two public functions: seasonal_balance_traffic and seasonal_balance_by_sellout —
add splitting of the period into hourly slots, computation of frequency limits
and accounting for the seasonal traffic profile.

build_seasonal_context — a separate preparation step: builds a SeasonalContext
in a single streaming pass over CSV logs. Takes the ads and the period for
computing user_activity_ratio. The result is passed to
SeasonalBalancingParams via create_seasonal_balancing_params().

Internal pipeline of each call:
    1. Split total_traffic_volume by hours according to the weights from SeasonalContext.
    2. For each slot — prepare Ads with divided volumes.
    3. Call the level-2 functions with BalancingParams (seasonal_context = current hour).
    4. Sum up the slot results.
"""

from __future__ import annotations

import csv
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from rtb_sdk.schemas.auction_schemas import Ad, AdId
from rtb_sdk.schemas.balancer_schemas import (
    AddCampaignResult,
    BalancingBySelloutParams,
    BalancingBySelloutResult,
    BalancingParams,
    BalanceResult,
    ExtendedBalancingParams,
    SeasonalBalancingParams,
    SeasonalBalancingBySelloutParams,
)

from rtb_sdk.balancer.seasonal.types import (
    AdditionalContext,
    AggregationMode,
    HistoricalLogsConfig,
    HourlyWeights,
    HourType,
    LogStreamState,
    PeriodWindow,
    SeasonalContext,
)
from rtb_sdk.balancer.seasonal.slots import (
    compute_hours,
    hour_type,
    n_active_hours,
)
from rtb_sdk.balancer.seasonal.corrections import (
    apply_histogram_correction,
    compute_hour_limit,
    compute_period_limit,
    is_ad_active,
    prepare_slot_ads,
)
from rtb_sdk.balancer.seasonal.seasonality import (
    normalize_counts,
    normalize_tag_counts,
    process_log_chunk,
)
from rtb_sdk.balancer.functions.balance_traffic import balance_traffic as _hour_balance_traffic
from rtb_sdk.balancer.functions.balance_by_sellout import balance_by_sellout as _hour_balance_by_sellout
from rtb_sdk.balancer.functions.add_campaign import add_new_balanced_campaign as _hour_add_new_balanced_campaign


# ---------------------------------------------------------------------------
# Internal helper functions
# ---------------------------------------------------------------------------

def _iter_slots(
    ads: dict[AdId, Any],
    params: SeasonalBalancingParams,
):
    """Generator: for each active hourly slot returns
    (slot_ads, slot_params, n_active, remaining).

    Precomputes once: period, context, n_active, remaining.
    On each step: takes the AdditionalContext for the slot, selects the active
    ads via prepare_slot_ads (with cross-slot remaining).

    slot_ads    — dict[AdId, Ad] with already divided volumes (volume=slot_share).
    slot_params — BalancingParams in the inner format with total_traffic_volume=total_t
                  and seasonal_context=the current AdditionalContext.

    remaining — mutable dictionary of budget remainders. The calling function deducts
    the actually assigned volume after the level-2 call; the generator sees the updates
    on the next iteration via prepare_slot_ads.
    """
    seasonal_context: SeasonalContext = params['seasonal_context']
    mode = seasonal_context['mode']
    ctx_by_hour = seasonal_context['context']

    period: PeriodWindow = params['period']
    total: float = float(params.get('total_traffic_volume', 0))
    H = compute_hours(period)
    n_hours = (period['period_end'] - period['period_start']).total_seconds() / 3600

    n_active: dict[AdId, int] = {
        ad_id: n_active_hours(ad, period) for ad_id, ad in ads.items()
    }

    # Initialize budget remainders: min(volume, frequency_limit_total) without ratio.
    # Ratio is accounted per-slot in prepare_slot_ads; remaining prevents total
    # overspend under ceil rounding of low-budget slots.
    remaining: dict[AdId, int] = {}
    for ad_id, ad in ads.items():
        ad_freq: dict = ad.get('ad_frequency_limit') or {}
        total_limit = compute_period_limit(ad_freq, n_hours)
        ad_max = int(ad.get('volume', 0))
        remaining[ad_id] = min(ad_max, int(total_limit)) if total_limit < float('inf') else ad_max

    # Total weight of active (processed) slots per ad — the denominator
    # of proportional slicing in prepare_slot_ads. A slot is counted only if it
    # will actually be processed below (slot_ctx is set and total_t > 0), otherwise the sum of weights
    # will not match the slots that prepare_slot_ads sees.
    active_weight: dict[AdId, float] = {ad_id: 0.0 for ad_id in ads}
    for t in range(H):
        w_slot_dt: datetime = period['period_start'] + timedelta(hours=t)
        w_h = hour_type(w_slot_dt, mode)
        w_ctx = ctx_by_hour.get(w_h)
        if w_ctx is None:
            continue
        if round(total * w_ctx['weight']) <= 0:
            continue
        for ad_id, ad in ads.items():
            if is_ad_active(ad, w_slot_dt):
                active_weight[ad_id] += w_ctx['weight']

    # Base inner params without seasonal and level-3 keys
    _SEASONAL_KEYS = frozenset({'seasonal_context', 'period'})
    base_params = {k: v for k, v in params.items() if k not in _SEASONAL_KEYS}

    for t in range(H):
        slot_dt: datetime = period['period_start'] + timedelta(hours=t)
        h = hour_type(slot_dt, mode)
        slot_ctx = ctx_by_hour.get(h)
        if slot_ctx is None:
            continue

        total_t = round(total * slot_ctx['weight'])
        if total_t <= 0:
            continue

        slot_ads = prepare_slot_ads(
            ads, slot_dt, n_active, remaining,
            slot_weight=slot_ctx['weight'], active_weight=active_weight,
        )
        if not slot_ads:
            continue

        # Build BalancingParams for the slot (inner format, seasonal_context = current slot)
        slot_params: BalancingParams = {
            **base_params,
            'total_traffic_volume': total_t,
            'seasonal_context': slot_ctx,
        }

        yield slot_ads, slot_params, n_active, remaining


# ---------------------------------------------------------------------------
# External functions (Level 3)
# ---------------------------------------------------------------------------

def seasonal_balance_traffic(
    ads: dict[AdId, Ad],
    params: SeasonalBalancingParams,
) -> BalanceResult:
    """Balances traffic taking the time profile and frequency limits into account.

    Required keys in params: period, total_traffic_volume, seasonal_context.

    Args:
        ads:    ads {AdId: Ad}.
        params: SeasonalBalancingParams in the inner format with seasonal_context and period.

    Returns:
        dict[AdId, int] — total volumes for the period (type compatible with BalanceResult).
    """
    result: dict[AdId, int] = {ad_id: 0 for ad_id in ads}
    for slot_ads, slot_params, _, remaining in _iter_slots(ads, params):
        slot_result = _hour_balance_traffic(slot_ads, slot_params)
        for ad_id, vol in slot_result.items():
            result[ad_id] = result.get(ad_id, 0) + vol
            remaining[ad_id] = max(0, remaining.get(ad_id, 0) - vol)
    return result


def seasonal_balance_by_sellout(
    ads: dict[AdId, Ad],
    params: SeasonalBalancingBySelloutParams,
) -> BalancingBySelloutResult:
    """Level 3: sellout taking the time profile into account.

    Calls balance_by_sellout for each slot.
    The final sellout_percent = minimum over all ads of the share
    (total assigned volume / ad.volume × 100).
    Ads with volume=0 (unlimited) are excluded from the calculation.

    Required keys in params: period, total_traffic_volume,
    seasonal_context, accuracy_percent.

    Args:
        ads:    ads {AdId: Ad}.
        params: SeasonalBalancingBySelloutParams in the inner format.

    Returns:
        BalancingBySelloutResult(report=total volumes, sellout_percent=minimum share).
    """
    result: dict[AdId, int] = {ad_id: 0 for ad_id in ads}

    for slot_ads, slot_params, _, remaining in _iter_slots(ads, params):
        slot_sellout_params: BalancingBySelloutParams = {
            **slot_params,  # type: ignore[misc]
            'accuracy_percent': params['accuracy_percent'],
            'func_replace_infinity': params.get('func_replace_infinity'),
        }
        slot_result = _hour_balance_by_sellout(slot_ads, slot_sellout_params)
        for ad_id, vol in slot_result['report'].items():
            result[ad_id] = result.get(ad_id, 0) + vol
            remaining[ad_id] = max(0, remaining.get(ad_id, 0) - vol)

    # Final sellout_percent: minimum over ads with finite volume
    sellout_percent = 0.0
    fractions = []
    for ad_id, ad in ads.items():
        vol = int(ad.get('volume', 0))
        if vol > 0:
            fractions.append(result.get(ad_id, 0) / vol * 100)
    if fractions:
        sellout_percent = min(fractions)

    return BalancingBySelloutResult(report=result, sellout_percent=sellout_percent)


def seasonal_add_new_balanced_campaign(
    ads: dict[AdId, Ad],
    current_report: BalanceResult,
    params: SeasonalBalancingParams,
) -> AddCampaignResult:
    """Adds new campaigns, freezing competitors at current_report.

    Competitors (keys from current_report) are frozen at their current
    distribution: for each slot their proportional share is fixed
    via ad_vol_distr. New ads (not in current_report) get
    the free remainder of the traffic.

    Required keys in params: period, total_traffic_volume, seasonal_context.

    Args:
        ads:            full dictionary of ads — competitors + new ones.
        current_report: current distribution of competitors {AdId: int}.
        params:         SeasonalBalancingParams in the inner format.

    Returns:
        AddCampaignResult with fields report (all ads) and new_ads_volumes
        (only new ones — not in current_report).
    """
    result: dict[AdId, int] = {ad_id: 0 for ad_id in ads}
    new_ad_ids: set[AdId] = {ad_id for ad_id in ads if ad_id not in current_report}

    # Prepare a version of the ads where competitors have volume = current_report
    # (so that prepare_slot_ads slices them proportionally across slots).
    ads_with_fixed = {
        ad_id: ({**ad, 'volume': current_report[ad_id]} if ad_id in current_report else ad)
        for ad_id, ad in ads.items()
    }

    for slot_ads, slot_params, _, remaining in _iter_slots(ads_with_fixed, params):
        # Use the competitors' slot volumes from slot_ads as frozen volumes.
        ad_vol_distr: dict[AdId, int] = {
            ad_id: slot_ads[ad_id]['volume']
            for ad_id in slot_ads
            if ad_id in current_report
        }

        ext_params: ExtendedBalancingParams = {
            **slot_params,  # type: ignore[misc]
            'ad_vol_distr': ad_vol_distr,
        }
        slot_result = _hour_add_new_balanced_campaign(slot_ads, ext_params)

        for ad_id, vol in slot_result['report'].items():
            result[ad_id] = result.get(ad_id, 0) + vol
            remaining[ad_id] = max(0, remaining.get(ad_id, 0) - vol)

    new_ads_volumes: dict[AdId, int] = {ad_id: result[ad_id] for ad_id in new_ad_ids}
    return AddCampaignResult(report=result, new_ads_volumes=new_ads_volumes)


# ---------------------------------------------------------------------------
# Building SeasonalContext from logs
# ---------------------------------------------------------------------------

def _compute_user_ratio(
    ad: Any,
    user_counts_h: dict[str, int],
    user_counts_total: dict[str, int],
    n_hours: float,
) -> float:
    """Saturation coefficient of an ad for a specific hour.

    Selects the histogram and limit depending on the granularity of user_frequency_limit:

    Hourly limit ('h' present in value):
        coef = Σ min(r_i_h, user_hour_limit) / Σ r_i_h
        r_i_h — requests of the i-th user in the given hour.
        Correctly conveys saturation within the hour.

    Non-hourly limits ('d'/'w'/'m', without 'h'):
        coef = Σ min(r_i, user_period_limit) / Σ r_i
        r_i — total requests of the i-th user over the whole log;
        user_period_limit = user_hour_limit × n_hours — conversion to the period.
        Equivalent to the behavior before the refactoring.

    If there is no limit or no data → 1.0.
    """
    user_freq: dict = ad.get('user_frequency_limit') or {}
    user_hour_limit = compute_hour_limit(user_freq)
    if user_hour_limit >= float('inf'):
        return 1.0

    v: dict = user_freq.get('value', {})
    if v.get('h'):
        # Hourly limit — per-hour histogram
        if not user_counts_h:
            return 1.0
        return apply_histogram_correction(1.0, list(user_counts_h.values()), user_hour_limit)
    else:
        # Non-hourly limit — total histogram + period-total limit
        if not user_counts_total:
            return 1.0
        user_period_limit = user_hour_limit * n_hours
        return apply_histogram_correction(1.0, list(user_counts_total.values()), user_period_limit)


def build_seasonal_context(
    config: HistoricalLogsConfig,
    ads: dict[AdId, Ad],
    period: PeriodWindow,
    *,
    tag_col_map: dict[str, str] | None = None,
) -> SeasonalContext:
    """Builds a SeasonalContext in a single streaming pass over CSV logs.

    In a single pass accumulates:
    - counts → normalized slot weights (weight in AdditionalContext).
    - user_counts_by_hour → per-hour user activity for
      computing user_activity_ratio for each ad.
    - tag_counts → tags_probability (if tag_col_map is set).

    Args:
        config:      HistoricalLogsConfig with path and timestamp_col.
        ads:         ads {AdId: Ad}; needed to compute the ratio from
                     each ad's user_frequency_limit.
        period:      balancing period; used for n_active_hours.
        tag_col_map: {VocabName: column_name_in_csv}; None → no tags.

    Returns:
        SeasonalContext with AdditionalContext filled in for each HourType.

    Raises:
        ValueError:        if the file is empty or no row was recognized.
        FileNotFoundError: if the file at the path is not found.
        KeyError:          if path or timestamp_col is missing from config.
    """
    mode: AggregationMode = config.get('aggregation_mode', 'hour_of_day')
    tz = ZoneInfo(config.get('timezone', 'UTC'))
    chunk_size = int(config.get('chunk_size', 10_000))
    n = 24 if mode == 'hour_of_day' else 168

    state = LogStreamState(
        counts={h: 0.0 for h in range(n)},
        user_counts_by_hour={},
        user_counts_total={},
        tag_counts={},
        mode=mode,
    )

    with open(config['path'], newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        chunk: list[dict[str, str]] = []

        for row in reader:
            chunk.append(row)
            if len(chunk) >= chunk_size:
                process_log_chunk(chunk, state, config, tz, tag_col_map)
                chunk.clear()

        if chunk:
            process_log_chunk(chunk, state, config, tz, tag_col_map)

    weights_dict = normalize_counts(state['counts'])
    tag_probs = normalize_tag_counts(state['tag_counts']) if tag_col_map and state['tag_counts'] else {}
    n_hours = (period['period_end'] - period['period_start']).total_seconds() / 3600

    ctx_by_hour: dict[HourType, AdditionalContext] = {}
    for h in range(n):
        weight = weights_dict.get(h, 0.0)
        user_counts_h = state['user_counts_by_hour'].get(h, {})

        ratios: dict[AdId, float] = {
            ad_id: _compute_user_ratio(ad, user_counts_h, state['user_counts_total'], n_hours)
            for ad_id, ad in ads.items()
        }

        ctx_by_hour[h] = AdditionalContext(
            weight=weight,
            user_activity_ratio=ratios,
            tags_probability=tag_probs.get(h),
        )

    return SeasonalContext(mode=mode, context=ctx_by_hour)
