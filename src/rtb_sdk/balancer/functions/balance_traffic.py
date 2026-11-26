"""
Level-2 traffic balancing.

Works in two modes:

    seasonal_context=None — non-temporal mode.
        Validation + ad_to_inner + optimize (params are already in the inner format).

    seasonal_context=AdditionalContext — temporal mode (from BalancingParams).
        prepare_hour_ads (hourly limits + user_activity_ratio),
        build_inner_ads (freq is overridden by the slot's max_vol),
        build_inner_params (hourly tags),
        optimize.
"""

from __future__ import annotations

from rtb_sdk.schemas.auction_schemas import Ad, AdId
from rtb_sdk.schemas.balancer_schemas import BalancingParams, BalanceResult
from rtb_sdk.helpers.balancer import (
    ad_to_inner,
    validate_optimize,
)
from rtb_sdk.helpers.balancer.optimize_params_helpers import get_balancing_params_seasonal_context


def balance_traffic(
    ads: dict[AdId, Ad],
    params: BalancingParams,
) -> BalanceResult:
    """Balances traffic between ads, maximizing the selected KPI.

    Public API of the balancer. Accepts parameters in the inner format (FullTag)
    and runs LP optimization. Returns the distribution of volumes across ads.

    If params contains seasonal_context (AdditionalContext) — performs
    temporal balancing for a single hourly slot.

    Args:
        ads:    ads {AdId: Ad}.
        params: BalancingParams in the inner format (FullTag).

    Returns:
        dict[AdId, int] — distribution of volumes (BalanceResult).

    Raises:
        BalancerError: If ads or params failed validation.
    """
    from rtb_sdk.balancer.functions.optimize import optimize

    validate_optimize(ads, params)
    hour_context = get_balancing_params_seasonal_context(params)

    if hour_context is None:
        inner_ads = {ad_id: ad_to_inner(ad) for ad_id, ad in ads.items()}
        return optimize(inner_ads, params)

    from rtb_sdk.balancer.seasonal.corrections import prepare_hour_ads
    from rtb_sdk.balancer.functions._seasonal import build_inner_ads, build_inner_params

    slot_ads = prepare_hour_ads(ads, hour_context)
    if not slot_ads:
        return {ad_id: 0 for ad_id in ads}
    inner_ads = build_inner_ads(slot_ads)
    inner_params = build_inner_params(params, hour_context)
    return optimize(inner_ads, inner_params)  # type: ignore[arg-type]
