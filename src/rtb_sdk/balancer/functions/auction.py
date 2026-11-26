import random
from typing import Optional

from rtb_sdk.schemas.auction_schemas import AdId
from rtb_sdk.schemas.balancer_schemas import AuctionParamsBalanced
from rtb_sdk.constants.tag_constants import TAG_EMPTY, TAG_OTHER
from rtb_sdk.helpers.balancer import (
    get_parameters_balanced_request,
    get_parameters_balanced_balancer_data,
    get_balancer_auction_data_vocabs,
    get_balancer_auction_data_tag_probabilities,
    get_balancer_auction_data_ads_distribution,
    get_balancer_auction_data_ads_probabilities,
)


def auction(
    ads: dict[AdId, dict],
    params: AuctionParamsBalanced,
) -> Optional[dict]:
    """Picks the auction winner according to the target traffic distribution.

    Stochastic mechanism: the weight of each ad is computed as
        distribution[ad] * P(request) / P(ad). 
    
    In aggregate over many requests the balancer's target traffic distribution is achieved.
    Targeting is not checked — ads must be filtered beforehand.
    Request tags missing from the narrowed dictionary fall back to
    the :OTHER bucket.

    Args:
        ads (dict[AdId, dict]): Arbitrary payload dictionaries of the ads
            participating in the auction.
        params (ParametersBalanced): Parameters including the user's request
            and the balancer data (vocabs, tag probabilities,
            distribution and ad probabilities).

    Returns:
        Optional[dict]: Payload of the winning ad, or None if
            ads is empty, balancer_data is not set, or the total weight is zero.
    """
    if not ads:  # nothing to draw
        return None

    # user's request: {VocabName: RawTag}
    request = get_parameters_balanced_request(params) 

    # data from convert_report_to_auction_data
    balancer_data = get_parameters_balanced_balancer_data(params)

    # no balancer data — the auction is impossible
    if balancer_data is None:  
        return None

    # narrowed dictionaries (only tags used by ads)
    vocabs = get_balancer_auction_data_vocabs(balancer_data)

    # {VocabName: {RawTag: float}} tag probabilities
    tag_probabilities = get_balancer_auction_data_tag_probabilities(balancer_data)

    # target traffic shares per ad from the balancer
    ads_distribution = get_balancer_auction_data_ads_distribution(balancer_data)

    # P(ad) — probability that a random request falls into the ad's target
    ads_probabilities = get_balancer_auction_data_ads_probabilities(balancer_data)

    req_prob = 1.0  # P(request) — computed as the product of tag probabilities over all dictionaries
    for vocab_name in vocabs:
        # take the tag from the request or an "empty" tag if the dictionary is not specified
        raw_tag = request[vocab_name] if vocab_name in request else TAG_EMPTY

        # probabilities of all tags of this dictionary
        vocab_probs = tag_probabilities.get(vocab_name, {})  

        # fallback to TAG_OTHER if the tag is missing from the narrowed dictionary
        prob = vocab_probs.get(raw_tag, vocab_probs.get(TAG_OTHER, 0.0))  

        # accumulate the product of probabilities over all dictionaries
        req_prob *= prob  

    volumes: dict[AdId, float] = {}  # weight of each ad for this request
    for ad_id in ads:
        
        # P(ad) — share of traffic covered by the ad's target
        ad_prob = ads_probabilities.get(ad_id, 1.0)  

        if ad_prob <= 0:
            volumes[ad_id] = 0.0  # an ad with zero P(ad) gets zero weight
        else:
            # weight = target_share * P(req) / P(ad)
            volumes[ad_id] = ads_distribution.get(ad_id, 0) * req_prob / ad_prob

    # total weight of all ads (normalizing denominator)
    total_volume = sum(volumes.values())

    if total_volume <= 0:
        return None

    # normalize the weights into probabilities (sum == 1)
    weights = [volumes[ad_id] / total_volume for ad_id in ads]
    chosen_id = random.choices(list(ads.keys()), weights=weights, k=1)[0]
    return ads[chosen_id]
