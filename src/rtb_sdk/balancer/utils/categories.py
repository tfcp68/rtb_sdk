import math
import heapq

from rtb_sdk.schemas.auction_schemas import AdId, FullTag, VocabName
from rtb_sdk.schemas.balancer_schemas import RequestFlow, RequestFlowWithAd, InnerVocabs
from rtb_sdk.constants.balancer_constants import MIN_CATEGORY_PROBABILITY
from rtb_sdk.helpers.balancer import (
    get_category_tags,
    get_category_probability,
    get_internal_category_ad_id,
    get_internal_category_tags,
)


# -1e18 instead of -inf: safe for arithmetic (log(0) → -inf would break sums)
_LOG_ZERO = -1e18

# Tolerance at the min_p threshold. A category's neg_log_prob accumulates incrementally along the heap path
# (nlp = neg + logP[k] - logP[k+1]), so for a category with P exactly == min_p
# the sum may end up 1-2 ULP above the exact -log(min_p) and a strict comparison
# `> threshold` would wrongly drop it (along with all equally probable ones further down the heap).
# 1e-9 is orders of magnitude larger than the drift (~1e-15) and corresponds to a negligible probability
# factor exp(1e-9) ≈ 1 + 1e-9, i.e. the boundary is included
_THRESHOLD_EPS = 1e-9


def _sort_ads_vocabs_tags_by_probability(
    ad_vocab_tags: dict[AdId, dict[VocabName, list[FullTag]]],
    tag_probabilities: dict[FullTag, float],
) -> dict[AdId, dict[VocabName, list[tuple[FullTag, float]]]]:
    """Sorts the ads' dictionaries and tags in descending order of probability.

    Dictionaries are sorted by descending number of tags: the dictionary with
    greater branching is placed first so that the heap algorithm traverses the
    category space faster. Tags within each dictionary are ordered
    by descending probability — the profile (0,0,...,0) always corresponds to
    the best category.

    Args:
        ad_vocab_tags (dict[AdId, dict[VocabName, list[FullTag]]]): Ad tags
            by dictionaries.
        tag_probabilities (dict[FullTag, float]): Tag probabilities in
            flat format.

    Returns:
        dict[AdId, dict[VocabName, list[tuple[FullTag, float]]]]]:
            Dictionary with ordered tags in the form (tag, probability).
    """
    result = {}
    for ad, vocabs in ad_vocab_tags.items():
        sorted_vocabs = dict(
            # more tags - dictionary first
            sorted(vocabs.items(), key=lambda item: len(item[1]), reverse=True)
        )
        sorted_vocab_tags: dict[VocabName, list[tuple[FullTag, float]]] = {}
        for vocab, tags in sorted_vocabs.items():
            # tags in descending order of probability
            sorted_tags = sorted(tags, key=lambda t: tag_probabilities.get(t, 0.0), reverse=True)

            # (tag, probability) pair
            sorted_vocab_tags[vocab] = [(t, tag_probabilities.get(t, 0.0)) for t in sorted_tags]

        result[ad] = sorted_vocab_tags
    return result


def _build_ad_log_arrays(
    vocabs_tags: dict[VocabName, list[tuple[FullTag, float]]],
) -> tuple[list[list[FullTag]], list[list[float]]]:
    """Lays out the ad's tags into positional arrays for the heap traversal.

    Turns {vocab: [(tag, prob), ...]} into two aligned structures
    indexed by the dictionary position i and the tag position n:
      vtags[i][n] — the tag, vlogp[i][n] — its log P.

    This lets the heap traversal work with categories as integers
    (mixed-radix) and pure index arithmetic instead of dict.get on strings.
    log P is taken directly from the tag's stored probability.

    Args:
        vocabs_tags (dict[VocabName, list[tuple[FullTag, float]]]): Tags
            of the ad by dictionaries, ordered by descending probability.

    Returns:
        tuple[list[list[FullTag]], list[list[float]]]: The pair (vtags, vlogp),
            where the outer index is the dictionary position in iteration order.
    """
    vtags: list[list[FullTag]] = []
    vlogp: list[list[float]] = []
    for tags in vocabs_tags.values():
        vtags.append([t for t, _ in tags])
        vlogp.append([math.log(p) if p > 0 else _LOG_ZERO for _, p in tags])
    return vtags, vlogp


def choose_top_categories_by_probability(
    ads_vocabs_tags: dict[AdId, dict[VocabName, list[FullTag]]],
    new_vocabs: InnerVocabs,
    tag_probabilities: dict[FullTag, float],
    max_n_categories: int = 100,
    min_category_probability: float = MIN_CATEGORY_PROBABILITY,
) -> dict[AdId, list[RequestFlow]]:
    """Finds the top-K most probable categories for each ad.

    A category is one tag from each of the ad's dictionaries (a row of the Cartesian
    product). Full enumeration is infeasible with a large number of tags,
    so a greedy heap traversal is used: starting from the best category,
    we expand neighbors in turn up to the required count or probability threshold.
    Complexity O(K · D · log K), D is the number of the ad's dictionaries.

    Args:
        ads_vocabs_tags: Ad tags grouped by dictionaries.
        new_vocabs: Narrowed dictionaries (only the tags in use).
        tag_probabilities: Tag probabilities in flat format.
        max_n_categories: Maximum number of categories per ad.
        min_category_probability: Lower probability threshold; categories
            below this threshold are not included in the result.

    Returns:
        dict[AdId, list[RequestFlow]]: List of RequestFlow(tags, probability)
            for each ad, descending by probability.

    Raises:
        ValueError: If the ad's best category has a positive
            log-probability (log P > 0, i.e. P > 1) — this means some
            tag has a probability greater than one, which is invalid input.
    """
    sorted_ads_vocabs_tags = _sort_ads_vocabs_tags_by_probability(
        ads_vocabs_tags, tag_probabilities
    )  # sort dictionaries and tags for the heap algorithm to work correctly

    # threshold -log(min_prob): hoisted out of the loop, the value is deterministic.
    # min_category_probability <= 0 means "no lower threshold" — take all
    # categories up to max_n_categories. -math.log(0) is invalid (ValueError),
    # so this case is treated as +∞ (the threshold never fires).
    neg_log_threshold = (
        math.inf if min_category_probability <= 0
        else -math.log(min_category_probability)
    )

    result: dict[AdId, list[RequestFlow]] = {}

    for ad in sorted_ads_vocabs_tags:
        result[ad] = []

        # positional arrays of tags/log-probabilities by dictionaries
        vtags, vlogp = _build_ad_log_arrays(sorted_ads_vocabs_tags[ad])
        n_vocabs = len(vtags)
        sizes = [len(t) for t in vtags]

        # mixed-radix: a category is encoded as a single int id = Σ idx[i]·prefix[i].
        # prefix[i] = ∏ sizes[j] for j>i — the "digit weight" of dictionary i (dictionary 0
        # is the most significant). The neighbor along dictionary i = id + prefix[i], and the index in the dictionary
        # i = (id // prefix[i]) % sizes[i].
        prefix = [1] * n_vocabs
        for i in range(n_vocabs - 2, -1, -1):
            prefix[i] = prefix[i + 1] * sizes[i + 1]

        # best category = id 0 (first = the most probable tag in each dictionary);
        # log P is computed with the same left-to-right addition as the former _get_category
        best_log_prob = 0.0
        for i in range(n_vocabs):
            best_log_prob += vlogp[i][0]

        # log_prob of the best category must be <= 0 (probability in (0, 1]).
        # If log_prob > 0, then at least one tag has P > 1, which is invalid.
        if best_log_prob > 0:
            raise ValueError(f'Ad {ad} has a tag with probability > 1 (log P(category) > 0)')

        # minus sign: min-heap ↔ max by probability. We store only (-logP, id);
        # the path and indices are restored from the id on extraction.
        heap: list = [(-best_log_prob, 0)]

        # the path buffer is reused between iterations — no allocation in the loop
        path_buf: list = [None] * n_vocabs

        emitted = 0
        while heap:
            # extract the category with the maximum probability
            neg_log_prob, cid = heapq.heappop(heap)

            # reached the category limit
            if emitted >= max_n_categories:
                break

            emitted += 1

            # probability is zero (P=0, e.g. a tag is missing from tag_probabilities) —
            # the category is unreachable regardless of the threshold. Without this check, with
            # min_category_probability<=0 (threshold disabled, neg_log_threshold=inf)
            # such a category passes through, and Σ P(cat)=0 crashes the LP with a division by zero.
            probability = math.exp(-neg_log_prob)
            if probability <= 0.0:
                break

            # neg_log_prob > -log(min_prob) ⟺ exp(-neg_log_prob) < min_prob
            # probability below the threshold — stop. _THRESHOLD_EPS absorbs the float drift
            # of the incremental log-sum so that categories exactly at the threshold are not lost.
            if neg_log_prob > neg_log_threshold + _THRESHOLD_EPS:
                break

            # decode the id into per-dictionary indices; also collect the path
            idx = [0] * n_vocabs
            for i in range(n_vocabs):
                k = (cid // prefix[i]) % sizes[i]
                idx[i] = k
                path_buf[i] = vtags[i][k]

            # convert back from log-space and save the category
            result[ad].append(RequestFlow(tags=tuple(path_buf), probability=probability))

            # Lazy unique generation: each category is generated exactly once.
            # Incrementing dictionary i is allowed only if all lower dictionaries (j>i)
            # are at zero, i.e. cid % prefix[i] == 0. Then the category's parent is
            # the decrement of its most significant nonzero digit, and it is unique →
            # no visited set is needed.
            for i in range(n_vocabs):
                k = idx[i]
                if k + 1 < sizes[i] and cid % prefix[i] == 0:
                    # -log P(neighbor) = -log P(current) + logP(tag_i) - logP(tag_{i+1}).
                    nlp = neg_log_prob + vlogp[i][k] - vlogp[i][k + 1]
                    heapq.heappush(heap, (nlp, cid + prefix[i]))

    return result


def count_ads_by_category_probabilities(
    ad_categories: dict[AdId, list[RequestFlow]],
) -> dict[AdId, float]:
    """Sums the probabilities of all selected categories of each ad.

    The result is used as the normalizing denominator Σ P(category)
    when building the coefficient k = P(ad) / Σ P(cat) in the LP problem.
    Without normalization the LP variables would work with "raw" probabilities
    rather than with real traffic volumes.

    Args:
        ad_categories (dict[AdId, list[RequestFlow]]): Ad categories,
            usually from choose_top_categories_by_probability.

    Returns:
        dict[AdId, float]: Dictionary {ad_id: sum_of_category_probabilities}.
    """
    result: dict[AdId, float] = {}
    for ad, categories in ad_categories.items():
        # Σ P(category) over all selected categories of the ad
        result[ad] = sum(get_category_probability(cat) for cat in categories)

    return result


def build_tag_category_hash(
    ad_categories: dict[AdId, list[RequestFlow]],
) -> dict[FullTag, list[RequestFlowWithAd]]:
    """Builds an inverted index "tag → categories containing this tag".

    RequestFlowWithAd extends RequestFlow with an ad_id field: the base type RequestFlow does not
    store it, but when building tag constraints in the LP problem we need to
    know which ad each category belongs to.

    Args:
        ad_categories (dict[AdId, list[RequestFlow]]): Ad categories.

    Returns:
        dict[FullTag, list[RequestFlowWithAd]]: Dictionary where each tag
            is mapped to a list of all categories (with ad_id) that contain it.
    """

    tag_cat_hash: dict[FullTag, list[RequestFlowWithAd]] = {}
    for ad_id, categories in ad_categories.items():
        for category in categories:
            internal = RequestFlowWithAd(
                # tags of this category
                tags=get_category_tags(category),  # type: ignore[arg-type]

                # probability of the category
                probability=get_category_probability(category),

                # ad identifier (absent from the base RequestFlow)
                ad_id=ad_id,
            )

            for tag in get_category_tags(category):
                # initialize the list on the first encountered tag
                if tag not in tag_cat_hash:
                    tag_cat_hash[tag] = []

                # add the category to this tag's list
                tag_cat_hash[tag].append(internal)

    return tag_cat_hash
