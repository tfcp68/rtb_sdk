from rtb_sdk.schemas.auction_schemas import AdId
from rtb_sdk.schemas.balancer_schemas import InnerAd, OptimizeParams, BalanceResult
from rtb_sdk.helpers.balancer import (
    get_inner_ad_targets,
    get_inner_ad_min_vol,
    get_inner_ad_price,
    get_optimize_params_total_traffic_volume,
    get_optimize_params_vocabs,
    get_optimize_params_tag_probabilities,
    get_optimize_params_objective,
    get_optimize_params_max_n_categories,
    get_optimize_params_min_category_probability,
    get_optimize_params_n_threads,
    build_new_vocabs,
    build_new_old_tags_hashes,
    build_new_probabilities,
    build_new_ads_tags,
    count_ads_probabilities,
    build_tag_to_vocab_hash,
    build_ads_real_volumes,
)
from rtb_sdk.balancer.utils.categories import (
    choose_top_categories_by_probability,
    count_ads_by_category_probabilities,
)
from rtb_sdk.balancer.solver.solver import solve_pywraplp
from rtb_sdk.balancer.solver.proto_solver import solve_proto
from rtb_sdk.errors.balancer import BalancerError, ErrorCodes


def optimize(
    ads: dict[AdId, InnerAd],
    params: OptimizeParams,
    use_proto: bool = True,
) -> BalanceResult:
    """Solves the LP problem of distributing traffic between ads.

    Internal function of the balancer. Accepts parameters in the internal
    (flat) format. Goes through 5 phases:
    1. Narrowing the dictionaries — keep only the tags used by ads.
    2. Rebuilding the ads' tags for the narrowed dictionaries.
    3. Computing P(ad) and the top-K categories (tag combinations) by probability.
    4. Building the LP problem: variables, constraints, objective function.
    5. Solving the LP and forming the final distribution.

    Args:
        ads (dict[AdId, InnerAd]): Dictionary of ads in the internal
            format with flat FullTag tags.
        params (OptimizeParams): Optimization parameters in the internal
            format, where tag_probabilities is a flat dictionary
            {FullTag: float}.

    Returns:
        BalanceResult: Dictionary {ad_id: volume} with the optimal
            traffic distribution.

    """
    # total traffic volume for the period — upper bound for the whole LP problem;
    # `or 0` guards against None, which helpers return when the field is absent
    total: int = get_optimize_params_total_traffic_volume(params, default=0) or 0

    # objective function: MAX_MONEY — maximize revenue, otherwise — traffic volume
    objective = get_optimize_params_objective(params)

    # maximum number of categories (tag combinations) per ad;
    # limits the LP size: with K dictionaries the number of categories grows exponentially
    max_n_categories = get_optimize_params_max_n_categories(params)

    # minimum category probability for inclusion in the LP;
    # cuts off nearly impossible tag combinations and reduces the problem size
    min_category_probability = get_optimize_params_min_category_probability(params)

    # number of threads for the GLOP solver
    n_threads = get_optimize_params_n_threads(params)

    # --- Phase 1: narrowing the dictionaries ---

    # Unused tags collapse into TAG_OTHER so that Σ P(tag) = 1 in each dictionary.

    # full dictionaries from the parameters — contain all tags, including those not used by ads
    vocabs_full = get_optimize_params_vocabs(params, default={}) or {}

    # narrowed dictionaries: only tags targeted by at least one ad;
    # they reduce the category space and exclude "dead" tags from the LP
    new_vocabs = build_new_vocabs(ads, params)

    # new_to_old — dictionary {new_tag: old_tag} for translating probabilities;
    # the second element (old_to_new) is not needed here — ignored via _
    new_to_old, _ = build_new_old_tags_hashes(vocabs_full, new_vocabs)

    # recompute tag probabilities for the narrowed dictionaries:
    # each removed tag adds its probability to TAG_OTHER,
    # so Σ P(tag) = 1 still holds in each dictionary
    new_tag_probs = build_new_probabilities(
        new_vocabs, vocabs_full, new_to_old,
        get_optimize_params_tag_probabilities(params, default={}) or {},
    )

    # --- Phase 2: preparing ad tags for the new dictionaries ---

    # extract each ad's targets in the format {VocabName: [FullTag]};
    # these are the original tags before recomputing for the narrowed dictionaries
    ads_vocabs_tags = {ad_id: get_inner_ad_targets(ad) for ad_id, ad in ads.items()}

    # rebuild the ads' tags so that they reference tags from new_vocabs;
    # tags that disappeared during narrowing are replaced with TAG_OTHER of their dictionary
    new_ads_vocabs_tags = build_new_ads_tags(ads_vocabs_tags, vocabs_full, new_vocabs)

    # flat reverse index {FullTag: VocabName} over the narrowed dictionaries;
    # needed when building tag constraints, where the tag's dictionary must be known
    new_tag_to_vocab = build_tag_to_vocab_hash(new_vocabs)

    # --- Phase 3: ad and category probabilities ---

    # ads_by_cat_probs = Σ P(category) over the selected top-K categories;
    # together with ads_probs forms k = P(ad)/Σ P(cat) in all LP constraints.

    # P(ad) = product of the total tag probabilities over all dictionaries;
    # shows what share of incoming traffic potentially falls into the ad
    ads_probs = count_ads_probabilities(new_ads_vocabs_tags, new_vocabs, new_tag_probs)

    # top-K categories for each ad — the Cartesian product of tags over dictionaries,
    # filtered by max_n_categories and min_category_probability;
    # each category is a specific tag combination corresponding to one LP variable
    ad_categories = choose_top_categories_by_probability(
        new_ads_vocabs_tags,
        new_vocabs,
        new_tag_probs,
        max_n_categories=max_n_categories,
        min_category_probability=min_category_probability,
    )

    # Ads for which no category passed the min_category_probability threshold
    # (not even the best one) have no statistically reachable traffic. Their Σ P(cat) = 0, and
    # the coefficient k = P(ad)/Σ P(cat) would cause a division by zero in all LP builders and
    # prepare_result. We exclude them from the LP and give them volume 0.
    empty_ads = [ad_id for ad_id, cats in ad_categories.items() if not cats]
    if empty_ads:
        ad_categories = {ad_id: cats for ad_id, cats in ad_categories.items() if cats}

    # Σ P(category) over the selected categories of each ad;
    # used as the denominator of the normalizing coefficient k = P(ad) / Σ P(cat),
    # which converts the "raw" LP variables x into the real traffic volume
    ads_by_cat_probs = count_ads_by_category_probabilities(ad_categories)

    # --- Phase 4: building the LP problem ---

    # minimum guaranteed number of impressions for each ad —
    # taken from the campaign settings; lower bound in the per-ad constraint
    ads_min_vol: dict[AdId, float] = {ad_id: float(get_inner_ad_min_vol(ad, default=0) or 0) for ad_id, ad in ads.items()}

    # maximum realistic volume: total * P(ad);
    # prevents assigning more traffic than statistically passes through the ad
    ads_real_max_vol = build_ads_real_volumes(ads, total, ads_probs)

    # price per impression for each ad — coefficient in the MAX_MONEY objective function
    ad_prices: dict[AdId, float] = {ad_id: get_inner_ad_price(ad, default=0.0) or 0.0 for ad_id, ad in ads.items()}

    # Quick rejection of obviously infeasible problems before building and solving the LP.
    # The per-ad constraint is min_vol ≤ Σ k·x ≤ real_max;
    # when min_vol > real_max its bounds are contradictory and the problem is infeasible.
    # The comparison is exact: these are the same ads_min_vol/ads_real_max_vol values that go into the bounds
    # of the constraint, so a strict `>` suffices and no tolerance is needed. Correctness
    # is guaranteed by the solver itself (solve_proto/solve_pywraplp → NO_SOLUTION); this check is
    # merely an optimization to avoid building a heavy LP on infeasible probes.
    # We check only ads in the LP (ad_categories); empty ones were excluded earlier and get volume 0.
    for ad_id in ad_categories:
        if ads_min_vol[ad_id] > ads_real_max_vol[ad_id]:
            raise BalancerError(
                ErrorCodes.NO_SOLUTION,
                f'Ad {ad_id}: min_vol ({ads_min_vol[ad_id]}) exceeds reachable '
                f'volume ({ads_real_max_vol[ad_id]}).',
            )

    # --- Phase 4-5: building the LP, solving, extracting the result ---
    # Two revenue-equivalent build+solve+extract implementations; each
    # creates a fresh GLOP solver (n_threads) — without external mutation:
    #   solve_proto    — batch assembly via MPModelProto (default, faster);
    #   solve_pywraplp — element-wise assembly via pywraplp (fallback).
    solve = solve_proto if use_proto else solve_pywraplp
    result = solve(
        ad_categories, total,
        ads_probs, ads_by_cat_probs,
        ads_min_vol, ads_real_max_vol, ad_prices, objective,
        n_threads,
    )

    # ads without passing categories did not participate in the LP — volume 0
    for ad_id in empty_ads:
        result[ad_id] = 0

    return result
