"""
Algorithm A3 (Small) from the Vazirani paper.
The budget is monetary (budget). Uses fake spend (fake_spend).
Eligibility condition: remaining_budget > 0.
Winner update: real_spend += min(Lj, bid), fake_spend += max(0, bid - Lj).
"""
import math
import random

from rtb_sdk.schemas import AdsDict, AdwordsAlgorithmId, AdwordsState, AdwordsMatchResult
from rtb_sdk.helpers.auction import get_ads_list
from rtb_sdk.helpers.adwords import (
    create_adwords_ad_state,
    create_adwords_state,
    create_adwords_match_result,
    get_adwords_state_ad_states,
    get_adwords_state_algorithm,
    get_adwords_state_query_count,
    get_adwords_ad_state_matches,
    get_adwords_ad_state_price,
    get_adwords_ad_state_remaining_budget,
    get_adwords_ad_state_real_spend,
    get_adwords_ad_state_fake_spend,
)
from .effective_bid import compute_effective_bid


def a3_initialize(ads: AdsDict, algorithm: AdwordsAlgorithmId) -> AdwordsState:
    """Initializes the A3 state: prices pj = exp(wj-1), remaining_budget = budget."""
    ad_states = {}
    for ad in get_ads_list(ads):
        wj = random.uniform(0, 1)
        pj = math.exp(wj - 1)
        ad_id = ad['id']
        ad_states[ad_id] = create_adwords_ad_state(
            id=ad_id,
            price=pj,
            matches=0,
            remaining_budget=float(ad.get('budget', 0.0)),
            real_spend=0.0,
            fake_spend=0.0,
        )
    return create_adwords_state(algorithm=algorithm, ad_states=ad_states, query_count=0)


def a3_auction_step(ads: AdsDict, state: AdwordsState) -> AdwordsMatchResult:
    """One step of the A3 auction (algorithm from the paper).

    Eligibility condition: remaining_budget > 0 (Lj > 0).
    Winner update:
      real_spend  += min(Lj, bid)
      fake_spend  += max(0, bid - Lj)
      remaining_budget -= min(Lj, bid)
    """
    ad_states = get_adwords_state_ad_states(state)
    effective_bids: dict = {}
    eligible_ads: dict = {}  # ad_id → ad object

    for ad in get_ads_list(ads):
        ad_id = ad['id']
        ad_state = ad_states.get(ad_id)
        if ad_state is None:
            continue
        if get_adwords_ad_state_remaining_budget(ad_state) <= 0:
            continue
        effective_bids[ad_id] = compute_effective_bid(
            ad['cpm'], get_adwords_ad_state_price(ad_state)
        )
        eligible_ads[ad_id] = ad

    matched_ad = max(effective_bids, key=effective_bids.get) if effective_bids else None

    new_ad_states = dict(ad_states)
    if matched_ad is not None:
        old = new_ad_states[matched_ad]
        bid = float(eligible_ads[matched_ad]['cpm'])
        lj = get_adwords_ad_state_remaining_budget(old)
        real_delta = min(lj, bid)
        fake_delta = max(0.0, bid - lj)
        new_ad_states[matched_ad] = create_adwords_ad_state(
            id=old['id'],
            price=old['price'],
            matches=old['matches'] + 1,
            remaining_budget=lj - real_delta,
            real_spend=old['real_spend'] + real_delta,
            fake_spend=old['fake_spend'] + fake_delta,
        )

    new_state = create_adwords_state(
        algorithm=get_adwords_state_algorithm(state),
        ad_states=new_ad_states,
        query_count=get_adwords_state_query_count(state) + 1,
    )
    return create_adwords_match_result(
        matched_ad=matched_ad,
        effective_bids=effective_bids,
        state=new_state,
    )
