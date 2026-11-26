"""
Level-2 free re-optimization returning a delta.

Works in two modes:

    seasonal_context=None — non-temporal mode.
        Validation + ad_to_inner + optimize + delta.

    seasonal_context=AdditionalContext — temporal mode (from ExtendedBalancingParams).
        prepare_hour_ads, build_inner_ads, optimize, delta.
"""

from __future__ import annotations

from rtb_sdk.schemas.auction_schemas import Ad, AdId
from rtb_sdk.schemas.balancer_schemas import (
    ExtendedBalancingParams,
    RebalanceResult,
)
from rtb_sdk.helpers.balancer import (
    ad_to_inner,
    validate_predict_rebalance,
)
from rtb_sdk.helpers.balancer.optimize_params_helpers import (
    get_balancing_params_seasonal_context,
    get_extended_balancing_params_ad_vol_distr,
)


def predict_rebalance(
    ads: dict[AdId, Ad],
    params: ExtendedBalancingParams,
) -> RebalanceResult:
    """Predicts the new optimal traffic distribution when parameters change.

    Does not change the real distribution. Computes what the volumes
    would be under the new tag_probabilities and returns the delta relative to
    the current distribution from params['ad_vol_distr'].

    If params contains seasonal_context (AdditionalContext) — performs
    temporal balancing for a single hourly slot.

    Args:
        ads:    Dictionary of ads.
        params: ExtendedBalancingParams in the inner format (FullTag) containing ad_vol_distr.

    Returns:
        RebalanceResult: Dictionary with two fields:
            - report: the new optimal distribution,
            - volume_delta: difference (new volume − current) for each ad.

    Raises:
        BalancerError: If ads or params failed validation.
    """
    from rtb_sdk.balancer.functions.optimize import optimize

    validate_predict_rebalance(ads, params)
    ad_vol_distr = get_extended_balancing_params_ad_vol_distr(params)
    hour_context = get_balancing_params_seasonal_context(params)

    if hour_context is None:
        inner_ads = {ad_id: ad_to_inner(ad) for ad_id, ad in ads.items()}
        new_report = optimize(inner_ads, params)
        volume_delta = {
            ad_id: new_report.get(ad_id, 0) - ad_vol_distr.get(ad_id, 0)
            for ad_id in ads
        }
        return RebalanceResult(report=new_report, volume_delta=volume_delta)

    from rtb_sdk.balancer.seasonal.corrections import prepare_hour_ads
    from rtb_sdk.balancer.functions._seasonal import build_inner_ads, build_inner_params

    slot_ads = prepare_hour_ads(ads, hour_context)
    if not slot_ads:
        empty: dict[AdId, int] = {ad_id: 0 for ad_id in ads}
        delta: dict[AdId, int] = {
            ad_id: -int(ad_vol_distr.get(ad_id, 0)) for ad_id in ads
        }
        return RebalanceResult(report=empty, volume_delta=delta)
    inner_ads = build_inner_ads(slot_ads)
    inner_params = build_inner_params(params, hour_context)
    result = optimize(inner_ads, inner_params)  # type: ignore[arg-type]
    volume_delta = {
        ad_id: result.get(ad_id, 0) - int(ad_vol_distr.get(ad_id, 0))
        for ad_id in ads
    }
    return RebalanceResult(report=result, volume_delta=volume_delta)
