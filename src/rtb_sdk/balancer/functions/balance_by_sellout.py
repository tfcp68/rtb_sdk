"""
Level-2 balancing maximizing the minimum sellout (max-min sellout).

Binary search on φ* — guarantees the minimum sellout percentage among campaigns.

Works in two modes:

    seasonal_context=None — non-temporal mode.
        Validation + ad_to_inner + binary search + optimize.

    seasonal_context=AdditionalContext — temporal mode (from BalancingBySelloutParams).
        prepare_hour_ads, ad_to_inner (without build_inner_ads), binary search, optimize.
"""

from __future__ import annotations

from typing import Callable, Iterable

from rtb_sdk.schemas.auction_schemas import Ad, AdId
from rtb_sdk.schemas.balancer_schemas import (
    BalancingBySelloutParams,
    BalancingBySelloutResult,
    BalanceResult,
    InnerAd,
)
from rtb_sdk.helpers.balancer import (
    ad_to_inner,
    validate_balance_by_sellout,
    get_balance_by_sellout_parameters_accuracy_percent,
    get_balance_by_sellout_parameters_func_replace_infinity,
)
from rtb_sdk.helpers.balancer.optimize_params_helpers import get_balancing_params_seasonal_context
from rtb_sdk.helpers.balancer.inner_ad_helpers import (
    get_inner_ad_max_vol,
    get_inner_ad_min_vol,
    get_inner_ad_freq,
    get_inner_ad_date_factor,
    get_inner_ad_targets,
    get_inner_ad_price,
    create_inner_ad,
)
from rtb_sdk.constants.balancer_constants import MAX_VOL_UNLIMITED
from rtb_sdk.errors.balancer import BalancerError


def balance_by_sellout(
    ads: dict[AdId, Ad],
    params: BalancingBySelloutParams,
) -> BalancingBySelloutResult:
    """Maximizes the minimum sellout percentage among campaigns (max-min).

    Binary search on φ*: finds the largest sellout share φ
    that can be guaranteed to every ad simultaneously.

    If params contains seasonal_context (AdditionalContext) — performs
    temporal balancing for a single hourly slot.

    Args:
        ads:    Ads to sell out {AdId: Ad}.
        params: BalancingBySelloutParams in the inner format (FullTag).

    Returns:
        BalancingBySelloutResult(report=distribution, sellout_percent=achieved percentage).
    """
    from rtb_sdk.balancer.functions.optimize import optimize

    validate_balance_by_sellout(ads, params)

    accuracy_percent = get_balance_by_sellout_parameters_accuracy_percent(params)
    func_replace_infinity = get_balance_by_sellout_parameters_func_replace_infinity(params)
    eps = accuracy_percent / 100
    hour_context = get_balancing_params_seasonal_context(params)

    if hour_context is None:
        inner_ads = {ad_id: ad_to_inner(ad) for ad_id, ad in ads.items()}
        inner_params = _build_params_no_seasonal(params)
    else:
        from rtb_sdk.balancer.seasonal.corrections import prepare_hour_ads
        from rtb_sdk.balancer.functions._seasonal import build_inner_params

        slot_ads = prepare_hour_ads(ads, hour_context)
        if not slot_ads:
            return BalancingBySelloutResult(report={ad_id: 0 for ad_id in ads}, sellout_percent=0.0)
        inner_ads = {ad_id: ad_to_inner(ad) for ad_id, ad in slot_ads.items()}
        inner_params = build_inner_params(params, hour_context)  # type: ignore[arg-type]

    if _all_unlimited(inner_ads):
        report = optimize(inner_ads, inner_params)  # type: ignore[arg-type]
        return BalancingBySelloutResult(
            report=report,
            sellout_percent=_calculate_sellout_percent(inner_ads, report),
        )

    if func_replace_infinity is not None:
        search_ads = _replace_ads_with_infinity_volume(inner_ads, func_replace_infinity)
        unlimited_ads: dict[AdId, InnerAd] = {}
    else:
        search_ads = {
            ad_id: ad for ad_id, ad in inner_ads.items()
            if get_inner_ad_max_vol(ad) != MAX_VOL_UNLIMITED
        }
        unlimited_ads = {
            ad_id: ad for ad_id, ad in inner_ads.items()
            if get_inner_ad_max_vol(ad) == MAX_VOL_UNLIMITED
        }

    min_border, _ = _calculate_fraction_borders(search_ads)

    left = min_border
    right = 1.0
    best_sellout: BalanceResult = {}
    best_search_ads: dict[AdId, InnerAd] = search_ads
    sellout_percent = 0.0

    while abs(left - right) > eps:
        volume_percent = (left + right) / 2

        search_ads_with_new_min_volume = _create_ads_with_new_min_volume(search_ads, volume_percent)

        try:
            balance_result = optimize(search_ads_with_new_min_volume, inner_params)  # type: ignore[arg-type]
        except BalancerError:
            right = volume_percent
            continue

        if _sellout_is_complete(search_ads_with_new_min_volume, balance_result):
            best_sellout = balance_result
            best_search_ads = search_ads_with_new_min_volume
            sellout_percent = _calculate_sellout_percent(search_ads, balance_result)
            left = volume_percent
        else:
            right = volume_percent

    if not best_sellout:
        best_sellout = optimize(search_ads, inner_params)  # type: ignore[arg-type]
        best_search_ads = search_ads
        sellout_percent = _calculate_sellout_percent(search_ads, best_sellout)

    if unlimited_ads:
        report = optimize({**best_search_ads, **unlimited_ads}, inner_params)  # type: ignore[arg-type]
        # sellout_percent must describe the FINAL report: unlimited ads compete for
        # traffic and may push limited ads below their min_volume floor.
        sellout_percent = _calculate_sellout_percent(search_ads, report)
    else:
        report = best_sellout

    return BalancingBySelloutResult(report=report, sellout_percent=sellout_percent)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_params_no_seasonal(params: BalancingBySelloutParams) -> dict:
    """Removes sellout-specific keys, returns a clean OptimizeParams."""
    _SELLOUT_KEYS = frozenset({'accuracy_percent', 'func_replace_infinity', 'seasonal_context'})
    return {k: v for k, v in params.items() if k not in _SELLOUT_KEYS}


def _all_unlimited(inner_ads: dict[AdId, InnerAd]) -> bool:
    return all(
        get_inner_ad_max_vol(ad) == MAX_VOL_UNLIMITED
        for ad in inner_ads.values()
    )


def _replace_ads_with_infinity_volume(
    inner_ads: dict[AdId, InnerAd],
    func_replace_infinity: Callable[[Iterable[float]], int] | None,
) -> dict[AdId, InnerAd]:
    limited_vols = [
        get_inner_ad_max_vol(ad)
        for ad in inner_ads.values()
        if get_inner_ad_max_vol(ad) != MAX_VOL_UNLIMITED
    ]
    if not limited_vols:
        return inner_ads

    new_volume = func_replace_infinity(limited_vols)  # type: ignore[misc]

    new_inner_ads: dict[AdId, InnerAd] = {}
    for ad_id, ad in inner_ads.items():
        max_vol = get_inner_ad_max_vol(ad)
        if max_vol == MAX_VOL_UNLIMITED:
            max_vol = new_volume

        new_inner_ads[ad_id] = create_inner_ad(
            id=ad_id,
            targets=get_inner_ad_targets(ad),
            min_vol=get_inner_ad_min_vol(ad),
            max_vol=max_vol,
            price=get_inner_ad_price(ad),
            date_factor=get_inner_ad_date_factor(ad),
            freq=get_inner_ad_freq(ad),
        )
    return new_inner_ads


def _calculate_sellout_percent(
    inner_ads: dict[AdId, InnerAd],
    balance_result: BalanceResult,
) -> float:
    if not inner_ads:
        return 0.0
    min_fraction = min(
        balance_result[ad_id] / get_inner_ad_max_vol(ad)
        for ad_id, ad in inner_ads.items()
    )
    return min_fraction * 100


def _calculate_fraction_borders(inner_ads: dict[AdId, InnerAd]) -> tuple[float, float]:
    fractions = [
        get_inner_ad_min_vol(ad) / get_inner_ad_max_vol(ad)
        for ad in inner_ads.values()
    ]
    return min(fractions), max(fractions)


def _create_ads_with_new_min_volume(
    inner_ads: dict[AdId, InnerAd],
    volume_percent: float,
) -> dict[AdId, InnerAd]:
    new_inner_ads: dict[AdId, InnerAd] = {}
    for ad_id, ad in inner_ads.items():
        max_vol = get_inner_ad_max_vol(ad)
        new_min_volume = int(max_vol * volume_percent)
        new_inner_ads[ad_id] = create_inner_ad(
            id=ad_id,
            targets=get_inner_ad_targets(ad),
            min_vol=new_min_volume,
            max_vol=max_vol,
            price=get_inner_ad_price(ad),
            date_factor=get_inner_ad_date_factor(ad),
            freq=get_inner_ad_freq(ad),
        )
    return new_inner_ads


def _sellout_is_complete(
    inner_ads: dict[AdId, InnerAd],
    balance_result: BalanceResult,
) -> bool:
    for ad_id, ad in inner_ads.items():
        if balance_result[ad_id] < get_inner_ad_min_vol(ad):
            return False
    return True
