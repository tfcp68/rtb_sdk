from ortools.linear_solver import pywraplp

from rtb_sdk.schemas.auction_schemas import Ad, AdId, VocabName, RawTag
from rtb_sdk.schemas.balancer_schemas import (
    RequestFlow, BalanceResult, ProjectedAdVolumes, BalancerAuctionData,
    BalancingParams,
)
from rtb_sdk.errors.balancer import BalancerError, ErrorCodes
from rtb_sdk.helpers.balancer import (
    get_category_tags,
    get_optimize_params_vocabs,
    get_optimize_params_tag_probabilities,
    get_inner_ad_targets,
    ad_to_inner,
    build_new_vocabs,
    build_new_old_tags_hashes,
    build_new_probabilities,
    build_new_ads_tags,
    count_ads_probabilities,
    get_vocab_name,
    get_raw_tag,
)
import math


def prepare_result(
    solver: pywraplp.Solver,
    status: int,
    ad_categories: dict[AdId, list[RequestFlow]],
    cat_to_x: dict[tuple, pywraplp.Variable],
    ads_probs: dict[AdId, float],
    ads_by_cat_probs: dict[AdId, float],
) -> BalanceResult:
    """Forms the final volume distribution from the LP solution.

    Sums the LP variable values x over each ad's categories,
    applying the normalizing coefficient k = P(ad) / Σ P(category)
    to convert the "raw" variable values into the real traffic volume.

    Args:
        solver (pywraplp.Solver): LP solver after the Solve() call.
        status (int): Solution status.
        ad_categories (dict[AdId, list[RequestFlow]]): Ad categories
            with probabilities.
        cat_to_x (dict[tuple, pywraplp.Variable]): LP variables
            indexed by the tuple (ad_id, category tags).
        ads_probs (dict[AdId, float]): P(ad) for each ad.
        ads_by_cat_probs (dict[AdId, float]): Σ P(category) for each
            ad (normalizing denominator).

    Returns:
        BalanceResult: Dictionary {ad_id: volume} with traffic volumes
            rounded to integers.

    Raises:
        BalancerError: If the solution status is not OPTIMAL.
    """

    # The LP problem was not solved optimally — a correct distribution cannot be built
    if status != pywraplp.Solver.OPTIMAL:
        raise BalancerError(ErrorCodes.NO_SOLUTION, 'No optimal solution found.')

    result: BalanceResult = {}
    for ad_id, categories in ad_categories.items():
        # k = P(ad) / Σ P(category) — the normalizing coefficient converting
        # the "raw" values of variables x into the ad's real traffic volume.
        # More about k — see the comments in solver/solver.py :: build_ad_constraints.

        # normalization: divide P(ad) by the total probability of the selected categories
        k = ads_probs[ad_id] / ads_by_cat_probs[ad_id]

        # sum the normalized volumes over all categories of the ad
        total = sum(
            k * cat_to_x[(ad_id, get_category_tags(cat))].solution_value()
            for cat in categories
        )

        # round to integers: traffic volumes are discrete quantities
        result[ad_id] = int(math.floor(total))

    return result


def convert_report_to_auction_data(
    ads: dict[AdId, Ad],
    report: ProjectedAdVolumes,
    params: BalancingParams,
) -> BalancerAuctionData:
    """Converts the balance_traffic result into data for the auction.

    Repeats the dictionary narrowing steps from optimize() to obtain the same
    narrowed dictionaries and probabilities for which the volumes
    in report were computed. Converts probabilities from the flat format {FullTag: p}
    to the nested {VocabName: {RawTag: p}} required by auction().

    Args:
        ads (dict[AdId, Ad]): Ads used in the
            balance_traffic call.
        report (ProjectedAdVolumes): Result of balance_traffic —
            {ad_id: volume}.
        params (BalancingParams): The same parameters that were passed
            to balance_traffic.

    Returns:
        BalancerAuctionData: Structure with narrowed dictionaries, tag
            probabilities, the target distribution and ad probabilities.
    """
    # Convert Ad → InnerAd for LP operations
    inner_ads = {ad_id: ad_to_inner(ad) for ad_id, ad in ads.items()}

    # params is already in the inner format (FullTag) — use it directly

    # full dictionaries before narrowing
    vocabs_full = get_optimize_params_vocabs(params, default={}) or {}

    # narrowed dictionaries: only tags used by ads
    new_vocabs = build_new_vocabs(inner_ads, params)

    # mapping of new tags to old ones (for redistributing probabilities into TAG_OTHER)
    new_to_old, _ = build_new_old_tags_hashes(vocabs_full, new_vocabs)
    _tag_probs = get_optimize_params_tag_probabilities(params, default={})

    # tag probabilities for the narrowed dictionaries (unused tags are collected into TAG_OTHER)
    new_tag_probs = build_new_probabilities(
        new_vocabs, vocabs_full, new_to_old,
        _tag_probs if _tag_probs is not None else {},
    )

    # tags of each ad by dictionaries
    ads_vocabs_tags = {ad_id: get_inner_ad_targets(inner_ad) for ad_id, inner_ad in inner_ads.items()}

    # remap the ads' tags to the narrowed dictionaries
    new_ads_vocabs_tags = build_new_ads_tags(ads_vocabs_tags, vocabs_full, new_vocabs)

    # P(ad) = probability that a random request falls into the target
    ads_probabilities = count_ads_probabilities(new_ads_vocabs_tags, new_vocabs, new_tag_probs)

    # total traffic volume from the balancer report
    ads_total = sum(report.values())

    # Convert dict[FullTag, float] → dict[VocabName, dict[RawTag, float]]
    # auction() expects the nested format, while new_tag_probs is flat {FullTag: p}
    outer_tag_probs: dict[VocabName, dict[RawTag, float]] = {}
    for full_tag, prob in new_tag_probs.items():
        # extract the dictionary name from FullTag (the part before the first ':')
        vocab = get_vocab_name(full_tag)

        # extract RawTag from FullTag (the part after the first ':')
        raw = get_raw_tag(full_tag)

        # group by dictionary
        outer_tag_probs.setdefault(vocab, {})[raw] = prob

    # Convert new_vocabs (InnerVocabs with FullTags) to OuterVocabs (RawTags)
    outer_vocabs = {
        vocab: [get_raw_tag(tag) for tag in tags]
        for vocab, tags in new_vocabs.items()
    }

    return BalancerAuctionData(
        vocabs=outer_vocabs,           # narrowed dictionaries in RawTag format
        tag_probabilities=outer_tag_probs,  # probabilities in the format {VocabName: {RawTag: p}}
        ads_distribution=dict(report),  # target traffic distribution {ad_id: volume}
        ads_probabilities=ads_probabilities,  # P(ad) for the auction formula
        ads_total=ads_total,            # total volume (for information)
    )
