"""
Filters of ads by tag match with the request.

Two modes:
  - precise: an ad passes only if all of its vocab groups
             have at least one intersection with the request tags
  - fuzzy:   an ad passes if the weighted distance <= max_distance

For fuzzy matching you can set a list strict_vocabs — vocabularies that
require an exact match (e.g. 'device', 'geo'). If a strict
vocab has no intersection, the ad is filtered out regardless of max_distance.
"""
from rtb_sdk.schemas import AdsDict, Ad, Request, FullTag, VocabName
from rtb_sdk.helpers import (
    get_request_tags,
    get_ad_targetvector,
    get_fulltags,
    get_full_tag_vector_dict,
    get_request_tags_dict,
    get_ads_dict,
    create_ads_dict,
)


# ── precise match ──────────────────────────────────────────────────────────────

def _request_to_full_tag_set(request: Request) -> dict[VocabName, set[FullTag]]:
    """
    Converts request tags to {vocab_name → set(full_tag)}.

    RequestTags holds one tag string per vocab. Each tag is wrapped
    in a set for uniform comparison with the ad's tags.

    Args:
        request: Request

    Returns:
        dict: {vocab_name → set(full_tag)} for fast intersection lookup
    """
    tags = get_request_tags(request)
    tags_dict = get_request_tags_dict(tags)  # {vocab: single_full_tag_str}
    return {vocab: {full_tag} for vocab, full_tag in tags_dict.items()}


def _ad_to_full_tag_sets(ad: Ad) -> dict[VocabName, set[FullTag]]:
    """
    Converts the ad's targets to {vocab_name → set(full_tag)}.

    Args:
        ad: Ad

    Returns:
        dict: {vocab_name → set(full_tag)}
    """
    tv = get_ad_targetvector(ad)
    ftv = get_fulltags(tv)
    return {vocab: set(tags) for vocab, tags in get_full_tag_vector_dict(ftv).items()}


def _is_precise_match(
    ad_tag_sets: dict[VocabName, set[FullTag]],
    request_tag_sets: dict[VocabName, set[FullTag]],
) -> bool:
    """
    Exact match: for each vocab of the ad there must be at least
    one intersection with the request tags from the same vocab.

    Args:
        ad_tag_sets: ad tags {vocab → set(full_tag)}
        request_tag_sets: request tags {vocab → set(full_tag)}

    Returns:
        bool: True if the ad exactly matches the request
    """
    for vocab, ad_tags in ad_tag_sets.items():
        req_tags = request_tag_sets.get(vocab, set())
        if not (ad_tags & req_tags):
            return False
    return True


def filter_by_precise_match(
    request: Request,
    ads: AdsDict,
) -> AdsDict:
    """
    Keeps the ads that exactly match the request tags.

    For each vocab in the ad's targets checks for an intersection
    with the request tags from the same vocab. All vocabs must intersect.

    Args:
        request: current request
        ads: AdsDict of candidate ads

    Returns:
        AdsDict: ads with distance == 0
    """
    request_tag_sets = _request_to_full_tag_set(request)
    result = {}
    for ad_id, ad in get_ads_dict(ads).items():
        ad_tag_sets = _ad_to_full_tag_sets(ad)
        if _is_precise_match(ad_tag_sets, request_tag_sets):
            result[ad_id] = ad
    return create_ads_dict(result)


# ── fuzzy match ────────────────────────────────────────────────────────────────

def _calc_ad_distance(
    ad: Ad,
    request_tag_sets: dict[VocabName, set[FullTag]],
    strict_vocabs: set[VocabName] | None = None,
) -> float | None:
    """
    Computes the weighted distance between the ad and the request.

    Algorithm (Jaccard-like):
      - for each vocab: weighted intersection / weighted union
      - overall similarity = weighted average over vocabulary_weights
      - overall distance = 1 - similarity

    If strict_vocabs is set: for each strict vocab of the ad
    an exact intersection is required (as in precise match). If there is no
    intersection — returns None (the ad is filtered out).

    Args:
        ad: the ad (targets, vocabulary_weights, tag_weights are used)
        request_tag_sets: request tags {vocab → set(full_tag)}
        strict_vocabs: set of vocabs requiring an exact match; None — no restrictions

    Returns:
        float: distance from 0.0 (exact match) to 1.0 (no intersections);
        None if a strict vocab failed the check
    """
    ad_tag_sets = _ad_to_full_tag_sets(ad)
    vocab_weights: dict[VocabName, float] = ad.get('vocabulary_weights', {})
    tag_weights: dict[FullTag, float] = ad.get('tag_weights', {})

    # check the strict vocabs (an exact intersection is required)
    if strict_vocabs:
        for vocab in strict_vocabs:
            if vocab not in ad_tag_sets:
                continue
            ad_tags = ad_tag_sets[vocab]
            req_tags = request_tag_sets.get(vocab, set())
            if not (ad_tags & req_tags):
                return None

    total_weight = 0.0
    total_sim = 0.0

    for vocab, ad_tags in ad_tag_sets.items():
        req_tags = request_tag_sets.get(vocab, set())

        intersection = ad_tags & req_tags
        union = ad_tags | req_tags

        weighted_intersection = sum(tag_weights.get(t, 1.0) for t in intersection)
        weighted_union = sum(tag_weights.get(t, 1.0) for t in union)

        sim = weighted_intersection / weighted_union if weighted_union > 0 else 0.0

        w = vocab_weights.get(vocab, 1.0)
        total_weight += w
        total_sim += w * sim

    if total_weight == 0:
        return 1.0

    return 1.0 - (total_sim / total_weight)


def filter_by_fuzzy_match(
    request: Request,
    ads: AdsDict,
    max_distance: float = 1.0,
    strict_vocabs: list[VocabName] | None = None,
) -> AdsDict:
    """
    Keeps the ads whose distance to the request is <= max_distance.

    Used as a fallback after a failed precise match.
    Takes the ad's vocabulary_weights and tag_weights into account.

    The strict_vocabs parameter lets you block fuzzy deviation
    on specific vocabularies: an ad passes the filter only if
    every strict vocab has an exact intersection with the request.

    Example: strict_vocabs=['device', 'geo'] — device and geolocation
    must not deviate, even if the overall distance is small.

    Args:
        request: current request
        ads: AdsDict of candidate ads
        max_distance: distance threshold (0.0 = exact, 1.0 = any)
        strict_vocabs: list of vocabs requiring an exact match;
                       None — no restrictions

    Returns:
        AdsDict: ads with distance <= max_distance
                 that passed the strict vocab check
    """
    request_tag_sets = _request_to_full_tag_set(request)
    strict_set = set(strict_vocabs) if strict_vocabs else None
    result = {}
    for ad_id, ad in get_ads_dict(ads).items():
        distance = _calc_ad_distance(ad, request_tag_sets, strict_set)
        if distance is not None and distance <= max_distance:
            result[ad_id] = ad
    return create_ads_dict(result)
