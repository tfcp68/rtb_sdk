"""
Private helpers for the seasonal mode of the public functions.

Used by balance_traffic and balance_by_sellout
in the seasonal path (from seasonal/balance.py via BalancingParams.seasonal_context).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rtb_sdk.schemas.auction_schemas import AdId
from rtb_sdk.helpers.balancer import ad_to_inner, is_valid_tag_probabilities_sum
from rtb_sdk.errors.balancer import BalancerError, ErrorCodes

if TYPE_CHECKING:
    from rtb_sdk.balancer.seasonal.types import AdditionalContext


# Keys that are NOT part of OptimizeParams and must be removed when passing to optimize()
_NON_OPTIMIZE_KEYS = frozenset({'seasonal_context', 'ad_vol_distr', 'accuracy_percent', 'func_replace_infinity'})


def outer_to_inner_probs(outer: dict[str, dict[str, float]]) -> dict[str, float]:
    """Converts {VocabName: {RawTag: p}} → {FullTag: p}."""
    result: dict[str, float] = {}
    for vocab, tags in outer.items():
        for tag, prob in tags.items():
            result[f'{vocab}:{tag}'] = prob
    return result


def build_inner_ads(slot_ads: dict[AdId, dict]) -> dict[AdId, dict]:
    """Converts Ad → InnerAd, overriding freq with the slot's maximum volume.

    Applied only in the seasonal mode, where max_vol has already been reduced
    to the slot share: overriding freq guarantees that the LP solver
    can assign up to max_vol impressions.
    """
    inner_ads: dict[AdId, dict] = {}
    for ad_id, ad in slot_ads.items():
        inner = dict(ad_to_inner(ad))
        slot_max = inner.get('max_vol', 1)
        inner['freq'] = max(inner['freq'], slot_max if slot_max > 0 else 1)
        inner_ads[ad_id] = inner
    return inner_ads


def build_inner_params(
    params: dict,
    hour_context: AdditionalContext | None,
) -> dict:
    """Builds inner_params for optimize (seasonal mode).

    params is already in the inner format (FullTag). Removes non-optimize keys.
    If hour_context.tags_probability is set — replaces params['tag_probabilities'].
    """
    base = {k: v for k, v in params.items() if k not in _NON_OPTIMIZE_KEYS}
    if hour_context is not None and hour_context.get('tags_probability') is not None:
        base['tag_probabilities'] = outer_to_inner_probs(
            hour_context['tags_probability']  # type: ignore[arg-type]
        )
        if not is_valid_tag_probabilities_sum(base['tag_probabilities'], base.get('vocabs', {})):
            raise BalancerError(
                ErrorCodes.INPUT_VALIDATION_ERROR,
                'seasonal tags_probability: sum of probabilities within a single vocab must not exceed 1.0',
            )
    return base
