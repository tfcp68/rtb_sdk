"""
Level-2 adding of new campaigns to an existing distribution.

Works in two modes:

    seasonal_context=None — non-temporal mode.
        Validation + ad_to_inner + freezing volumes + optimize.

    seasonal_context=AdditionalContext — temporal mode (from ExtendedBalancingParams).
        prepare_hour_ads, build_inner_ads, freezing to the slot proportion, optimize.
"""

from __future__ import annotations

from rtb_sdk.schemas.auction_schemas import Ad, AdId
from rtb_sdk.schemas.balancer_schemas import (
    AddCampaignResult,
    ExtendedBalancingParams,
)
from rtb_sdk.helpers.balancer import (
    ad_to_inner,
    validate_add_campaign,
)
from rtb_sdk.helpers.balancer.optimize_params_helpers import (
    get_balancing_params_seasonal_context,
    get_extended_balancing_params_ad_vol_distr,
)


def add_new_balanced_campaign(
    ads: dict[AdId, Ad],
    params: ExtendedBalancingParams,
) -> AddCampaignResult:
    """Adds new ads to an existing distribution without changing the fixed volumes.

    Ads from params['ad_vol_distr'] are "frozen": their min_vol and max_vol
    are set equal to the fixed volume so that the LP solver cannot
    change them. The remaining traffic is distributed among the new ads.

    If params contains seasonal_context (AdditionalContext) — performs
    temporal balancing for a single hourly slot.

    Args:
        ads:    Full dictionary of ads — old and new.
        params: ExtendedBalancingParams in the inner format (FullTag) containing ad_vol_distr.

    Returns:
        AddCampaignResult: Dictionary with two fields:
            - report: the full distribution over all ads,
            - new_ads_volumes: volumes of the new ads only.

    Raises:
        BalancerError: If ads or params failed validation.
    """
    from rtb_sdk.balancer.functions.optimize import optimize

    validate_add_campaign(ads, params)
    ad_vol_distr = get_extended_balancing_params_ad_vol_distr(params)
    hour_context = get_balancing_params_seasonal_context(params)

    if hour_context is None:
        inner_ads = {ad_id: ad_to_inner(ad) for ad_id, ad in ads.items()}
        frozen_ads = {
            ad_id: (
                {**inner_ad, 'min_vol': ad_vol_distr[ad_id], 'max_vol': ad_vol_distr[ad_id]}
                if ad_id in ad_vol_distr
                else inner_ad
            )
            for ad_id, inner_ad in inner_ads.items()
        }
        report = optimize(frozen_ads, params)  # type: ignore[arg-type]
        new_ads_volumes = {ad_id: vol for ad_id, vol in report.items() if ad_id not in ad_vol_distr}
        return AddCampaignResult(report=report, new_ads_volumes=new_ads_volumes)

    from rtb_sdk.balancer.seasonal.corrections import prepare_hour_ads
    from rtb_sdk.balancer.functions._seasonal import build_inner_ads, build_inner_params

    slot_ads = prepare_hour_ads(ads, hour_context)
    if not slot_ads:
        empty: dict[AdId, int] = {ad_id: 0 for ad_id in ads}
        return AddCampaignResult(
            report=empty,
            new_ads_volumes={ad_id: 0 for ad_id in ads if ad_id not in ad_vol_distr},
        )
    inner_ads = build_inner_ads(slot_ads)
    for ad_id in list(inner_ads):
        if ad_id in ad_vol_distr:
            fixed = int(ad_vol_distr[ad_id])
            inner_ads[ad_id] = {
                **inner_ads[ad_id],
                'min_vol': fixed,
                'max_vol': fixed,
                'freq': max(fixed, 1),
            }
    inner_params = build_inner_params(params, hour_context)
    result = optimize(inner_ads, inner_params)  # type: ignore[arg-type]
    new_ads_volumes = {ad_id: vol for ad_id, vol in result.items() if ad_id not in ad_vol_distr}
    return AddCampaignResult(report=result, new_ads_volumes=new_ads_volumes)
