"""
Level-3 balancing functions without targeting (RoN — Run of Network).

A mirror of seasonal_* — the same slots, the same _iter_slots, the same LP solver,
but all ads compete for the whole traffic: targets are replaced with empty ones
before being passed to seasonal_balance_traffic.

Practical meaning: "network" (run-of-network) campaigns, budget packages
without segmentation, forecasting inventory capacity before introducing targeting.
"""

from __future__ import annotations

from rtb_sdk.schemas.auction_schemas import Ad, AdId
from rtb_sdk.schemas.balancer_schemas import BalanceResult, SeasonalBalancingParams
from rtb_sdk.helpers.auction import create_target_vector
from rtb_sdk.balancer.seasonal.balance import seasonal_balance_traffic


def _strip_targets(ads: dict[AdId, Ad]) -> dict[AdId, Ad]:
    """Replaces each ad's targets with empty ones (= all traffic).

    All other fields (volume, cpm, ad_frequency_limit, start_date, end_date)
    remain untouched — they still take part in the optimization.

    With empty targets the ad covers all categories (RequestFlow),
    P(ad) ≈ 1.0, and the constraints min_vol ≤ Σ x ≤ max_vol apply to the entire
    traffic flow as a whole.
    """
    return {
        ad_id: {**ad, 'targets': create_target_vector({})}
        for ad_id, ad in ads.items()
    }


def open_balance_traffic(
    ads: dict[AdId, Ad],
    params: SeasonalBalancingParams,
) -> BalanceResult:
    """Balances traffic ignoring targeting (RoN).

    Identical to seasonal_balance_traffic, but before balancing replaces
    the targets of all ads with empty ones — each competes for the whole traffic.

    Required keys in params: period, total_traffic_volume, seasonal_context.

    Args:
        ads:    ads {AdId: Ad}; targets are ignored.
        params: SeasonalBalancingParams in the inner format.

    Returns:
        dict[AdId, int] — total volumes for the period.
    """
    return seasonal_balance_traffic(_strip_targets(ads), params)
