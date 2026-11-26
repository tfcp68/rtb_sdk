"""
Level-3 recommended bid forecaster (seasonal/forecast.py).

The only public function: forecast_bid(params: BidForecastParams).
The mode is selected via params['mode'] (1..4).
Search direction — params['bid_direction'] ('minimize' | 'maximize').

forecast_bid modes:
    1 — BidForecastResult: binary search, competitors are re-balanced.
    2 — BidForecastResult: binary search, competitors frozen at current_report.
    3 — BidForecastResult: like 1, but accounting for min_vol from the original Ad.
    4 — BidForecastResult: like 1, but with a cannibalization constraint.

Internal functions (not part of forecast_bid):
    _mode1_opportunity — OpportunityResult: maximum impression ceiling without competitors.
    _mode6_curve       — DeliveryResult: sweep curve over [min_bid, max_bid].
"""

from __future__ import annotations

from typing import Callable

from rtb_sdk.schemas.auction_schemas import Ad, AdId
from rtb_sdk.schemas.balancer_schemas import (
    BalanceResult,
    BidDirection,
    BidForecastParams,
    BidForecastResult,
    CannibalizationReport,
    DeliveryPoint,
    DeliveryResult,
    ForecastMode,
    OpportunityResult,
    SeasonalBalancingParams,
)
from rtb_sdk.balancer.seasonal.balance import (
    seasonal_balance_traffic,
    seasonal_add_new_balanced_campaign,
)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _max_volume_from_budget(max_budget: int | float, cpm: float) -> int:
    """LP quota of an ad from the budget constraint."""
    if cpm <= 0:
        return int(1e9)  # practically unlimited
    return int(max_budget * 1000.0 / cpm)


def _compute_cannibalization(
    current_report: BalanceResult,
    result: BalanceResult,
    our_ad_id: AdId,
) -> CannibalizationReport:
    """Δ[ad_id] = current_report[ad_id] - result[ad_id] for competitors."""
    per_ad: dict[AdId, int] = {}
    relative: dict[AdId, float] = {}
    total = 0
    for ad_id, current_vol in current_report.items():
        if ad_id == our_ad_id:
            continue
        new_vol = result.get(ad_id, 0)
        delta = max(0, current_vol - new_vol)
        per_ad[ad_id] = delta
        relative[ad_id] = (delta / current_vol * 100) if current_vol > 0 else 0.0
        total += delta
    return CannibalizationReport(per_ad=per_ad, relative=relative, total=total)


def _binary_search(
    lo: float,
    hi: float,
    accuracy: float,
    check_fn: Callable[[float], tuple[bool, BalanceResult]],
    direction: BidDirection,
) -> tuple[float, BalanceResult]:
    """Binary search: finds the min or max cpm at which check_fn returns True.

    direction='minimize': finds the smallest cpm ∈ [lo, hi] where check_fn is True.
      best_cpm starts at hi and shifts left on every True.
    direction='maximize': finds the largest cpm ∈ [lo, hi] where check_fn is True.
      best_cpm starts at lo and shifts right on every True.

    Returns (recommended_cpm, result_at_that_cpm).
    """
    if direction == 'minimize':
        best_cpm, best_result = hi, {}
        while hi - lo > accuracy:
            mid = (lo + hi) / 2
            ok, result = check_fn(mid)
            if ok:
                best_cpm, best_result = mid, result
                hi = mid
            else:
                lo = mid
    else:  # maximize
        best_cpm, best_result = lo, {}
        while hi - lo > accuracy:
            mid = (lo + hi) / 2
            ok, result = check_fn(mid)
            if ok:
                best_cpm, best_result = mid, result
                lo = mid
            else:
                hi = mid
    return best_cpm, best_result


def _search_bounds(params: BidForecastParams) -> tuple[float, float]:
    """Computes the [lo, hi] range for the binary search.

    lo = min_bid
    hi = min(max_bid if set, effective_budget × 1000 / min_impressions)
    """
    lo = params['min_bid']
    max_budget = params['max_budget']
    min_impressions = params['min_impressions']
    tolerance = params.get('budget_tolerance', 0.0)
    effective_budget = max_budget * (1 + tolerance / 100)
    hi_from_budget = (
        effective_budget * 1000.0 / min_impressions
        if min_impressions > 0
        else float('inf')
    )
    hi = min(params.get('max_bid', float('inf')), hi_from_budget)
    return lo, hi


def _make_check_fn(
    ad: Ad,
    ad_id: AdId,
    params: BidForecastParams,
    seasonal_params: SeasonalBalancingParams,
    lp_call: Callable[[Ad, float], BalanceResult],
) -> Callable[[float], tuple[bool, BalanceResult]]:
    """Factory of the check function for the LP step.

    Checks:
    1. impressions ≥ min_impressions
    2. spend ≤ max_budget × (1 + budget_tolerance/100)
    """
    min_impressions = params['min_impressions']
    max_budget = params['max_budget']
    tolerance = params.get('budget_tolerance', 0.0)
    effective_budget = max_budget * (1 + tolerance / 100)

    def check(cpm: float) -> tuple[bool, BalanceResult]:
        max_vol = _max_volume_from_budget(max_budget, cpm)
        ad_with_cpm = {**ad, 'cpm': cpm, 'volume': max_vol}
        result = lp_call(ad_with_cpm, cpm)
        impressions = result.get(ad_id, 0)
        spend = impressions * cpm / 1000.0
        ok = impressions >= min_impressions and spend <= effective_budget
        return ok, result

    return check


def _extract_seasonal_params(params: BidForecastParams) -> SeasonalBalancingParams:
    """Extracts SeasonalBalancingParams from BidForecastParams."""
    _BID_ONLY_KEYS = frozenset({
        'ad', 'max_budget', 'min_impressions', 'budget_tolerance', 'bid_direction',
        'min_bid', 'ads', 'current_report', 'search_accuracy',
        'max_cannibalization', 'max_bid', 'n_points', 'mode',
    })
    return {k: v for k, v in params.items() if k not in _BID_ONLY_KEYS}  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Six modes
# ---------------------------------------------------------------------------

def _mode1_opportunity(params: BidForecastParams) -> OpportunityResult:
    """Impression ceiling without competitors (a single ad, no budget constraints)."""
    ad = params['ad']
    ad_id = ad['id']
    seasonal_params = _extract_seasonal_params(params)
    result = seasonal_balance_traffic({ad_id: ad}, seasonal_params)
    max_impressions = result.get(ad_id, 0)
    min_bid = params.get('min_bid', 0.0)
    return OpportunityResult(
        max_impressions=max_impressions,
        max_spend=max_impressions * min_bid / 1000.0,
    )


def _mode2_free(params: BidForecastParams) -> BidForecastResult:
    """Binary search by bid_direction. Competitors are re-balanced on every iteration."""
    ad = params['ad']
    ad_id = ad['id']
    direction = params.get('bid_direction', 'minimize')
    accuracy = params.get('search_accuracy', 0.5)
    current_report = params.get('current_report', {})
    seasonal_params = _extract_seasonal_params(params)
    lo, hi = _search_bounds(params)

    def lp_call(ad_with_cpm: Ad, cpm: float) -> BalanceResult:
        all_ads = {**params.get('ads', {}), ad_id: ad_with_cpm}
        return seasonal_balance_traffic(all_ads, seasonal_params)

    check = _make_check_fn(ad, ad_id, params, seasonal_params, lp_call)
    best_cpm, best_result = _binary_search(lo, hi, accuracy, check, direction)
    cannibalization = _compute_cannibalization(current_report, best_result, ad_id)
    impressions = best_result.get(ad_id, 0)
    return BidForecastResult(
        recommended_bid=best_cpm,
        expected_impressions=impressions,
        expected_spend=impressions * best_cpm / 1000.0,
        cannibalization=cannibalization,
    )


def _mode3_fixed(params: BidForecastParams) -> BidForecastResult:
    """Binary search. Competitors are frozen at current_report."""
    ad = params['ad']
    ad_id = ad['id']
    direction = params.get('bid_direction', 'minimize')
    accuracy = params.get('search_accuracy', 0.5)
    current_report = params.get('current_report', {})
    seasonal_params = _extract_seasonal_params(params)
    lo, hi = _search_bounds(params)

    def lp_call(ad_with_cpm: Ad, cpm: float) -> BalanceResult:
        all_ads = {**params.get('ads', {}), ad_id: ad_with_cpm}
        return seasonal_add_new_balanced_campaign(all_ads, current_report, seasonal_params)['report']

    check = _make_check_fn(ad, ad_id, params, seasonal_params, lp_call)
    best_cpm, best_result = _binary_search(lo, hi, accuracy, check, direction)
    impressions = best_result.get(ad_id, 0)
    return BidForecastResult(
        recommended_bid=best_cpm,
        expected_impressions=impressions,
        expected_spend=impressions * best_cpm / 1000.0,
        cannibalization=None,  # by definition cannibalization = 0
    )


def _mode4_min_vol(params: BidForecastParams) -> BidForecastResult:
    """Like mode 2, but min_vol from the original Ad is added to the LP quota."""
    ad = params['ad']
    ad_id = ad['id']
    direction = params.get('bid_direction', 'minimize')
    accuracy = params.get('search_accuracy', 0.5)
    current_report = params.get('current_report', {})
    seasonal_params = _extract_seasonal_params(params)
    lo, hi = _search_bounds(params)
    original_min_vol = ad.get('min_vol', 0)

    def lp_call(ad_with_cpm: Ad, cpm: float) -> BalanceResult:
        ad_with_min_vol = {**ad_with_cpm, 'min_vol': original_min_vol}
        all_ads = {**params.get('ads', {}), ad_id: ad_with_min_vol}
        return seasonal_balance_traffic(all_ads, seasonal_params)

    check = _make_check_fn(ad, ad_id, params, seasonal_params, lp_call)
    best_cpm, best_result = _binary_search(lo, hi, accuracy, check, direction)
    cannibalization = _compute_cannibalization(current_report, best_result, ad_id)
    impressions = best_result.get(ad_id, 0)
    return BidForecastResult(
        recommended_bid=best_cpm,
        expected_impressions=impressions,
        expected_spend=impressions * best_cpm / 1000.0,
        cannibalization=cannibalization,
    )


def _mode5_capped(params: BidForecastParams) -> BidForecastResult:
    """Like mode 2, but with an additional constraint: cannibalization ≤ max_cannibalization."""
    ad = params['ad']
    ad_id = ad['id']
    direction = params.get('bid_direction', 'minimize')
    accuracy = params.get('search_accuracy', 0.5)
    current_report = params.get('current_report', {})
    max_cannib = params['max_cannibalization']
    seasonal_params = _extract_seasonal_params(params)
    lo, hi = _search_bounds(params)
    tolerance = params.get('budget_tolerance', 0.0)
    effective_budget = params['max_budget'] * (1 + tolerance / 100)

    def check(cpm: float) -> tuple[bool, BalanceResult]:
        max_vol = _max_volume_from_budget(params['max_budget'], cpm)
        ad_with_cpm = {**ad, 'cpm': cpm, 'volume': max_vol}
        all_ads = {**params.get('ads', {}), ad_id: ad_with_cpm}
        result = seasonal_balance_traffic(all_ads, seasonal_params)
        impressions = result.get(ad_id, 0)
        spend = impressions * cpm / 1000.0
        cannib = _compute_cannibalization(current_report, result, ad_id)
        ok = (
            impressions >= params['min_impressions']
            and spend <= effective_budget
            and cannib['total'] <= max_cannib
        )
        return ok, result

    best_cpm, best_result = _binary_search(lo, hi, accuracy, check, direction)
    cannibalization = _compute_cannibalization(current_report, best_result, ad_id)
    impressions = best_result.get(ad_id, 0)
    return BidForecastResult(
        recommended_bid=best_cpm,
        expected_impressions=impressions,
        expected_spend=impressions * best_cpm / 1000.0,
        cannibalization=cannibalization,
    )


def _mode6_curve(params: BidForecastParams) -> DeliveryResult:
    """Sweep over [min_bid, max_bid] with n_points equally spaced points.

    bid_direction is not applied. Includes the opportunity from mode 1.

    Raises:
        ValueError: if max_bid <= min_bid.
    """
    min_bid = params['min_bid']
    max_bid = params['max_bid']
    if max_bid <= min_bid:
        raise ValueError(
            f"mode=6 demand max_bid > min_bid, received: max_bid={max_bid}, min_bid={min_bid}"
        )
    n_points = params.get('n_points', 50)
    ad = params['ad']
    ad_id = ad['id']
    seasonal_params = _extract_seasonal_params(params)

    opportunity_result = _mode1_opportunity(params)

    step = (max_bid - min_bid) / max(n_points - 1, 1)
    curve: list[DeliveryPoint] = []
    for i in range(n_points):
        cpm = min_bid + i * step
        max_vol = _max_volume_from_budget(params['max_budget'], cpm)
        ad_with_cpm = {**ad, 'cpm': cpm, 'volume': max_vol}
        all_ads = {**params.get('ads', {}), ad_id: ad_with_cpm}
        result = seasonal_balance_traffic(all_ads, seasonal_params)
        impressions = result.get(ad_id, 0)
        curve.append(DeliveryPoint(
            bid=cpm,
            impressions=impressions,
            spend=impressions * cpm / 1000.0,
        ))

    return DeliveryResult(curve=curve, opportunity=opportunity_result['max_impressions'])


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

_MODE_HANDLERS: dict[int, Callable] = {
    1: _mode2_free,
    2: _mode3_fixed,
    3: _mode4_min_vol,
    4: _mode5_capped,
}


def forecast_bid(
    params: BidForecastParams,
) -> BidForecastResult:
    """Recommended bid forecaster. The mode is set by params['mode'].

    bid_direction='minimize' — find the minimum CPM (default).
    bid_direction='maximize' — find the maximum CPM.

    Args:
        params: BidForecastParams with the required field mode (1..4).

    Returns:
        BidForecastResult for mode=1..4.
    """
    mode: ForecastMode = params['mode']
    handler = _MODE_HANDLERS[mode]
    return handler(params)
