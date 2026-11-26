from typing import Optional

from rtb_sdk.schemas.balancer_schemas import (
    OptimizeParams,
    BalancingParams,
    ExtendedBalancingParams,
    InnerAd,
    InnerVocabs,
    AdditionalContext,
    ProjectedAdVolumes,
)
from rtb_sdk.schemas.auction_schemas import AdId, Ad, VocabName, FullTag, RawTag
from rtb_sdk.schemas.balancer_schemas import OuterVocabs
from rtb_sdk.constants.balancer_constants import MAX_MONEY, MAX_VOLUME, MIN_CATEGORY_PROBABILITY, OBJECTIVES
from rtb_sdk.errors.balancer import BalancerError, ErrorCodes
from rtb_sdk.helpers.balancer.inner_ad_helpers import get_inner_ad_targets
from rtb_sdk.helpers.balancer.full_tag_helpers import (
    build_full_tag_other,
    raw_tag_dict_to_full_tag_dict,
    outer_tag_probabilities_to_inner,
    get_raw_tag,
    get_vocab_name,
    build_tag_to_vocab_hash,
)


def is_valid_total_traffic_volume(val) -> bool:
    return isinstance(val, int) and not isinstance(val, bool) and val >= 0


def is_valid_tag_probabilities(val) -> bool:
    if not isinstance(val, dict):
        return False
    for k, v in val.items():
        if not isinstance(k, str):
            return False
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            return False
        if not (0.0 <= v <= 1.0):  # probability must be in [0, 1]
            return False
    return True


def is_valid_tag_probabilities_sum(
    tag_probabilities: dict[FullTag, float],
    vocabs: InnerVocabs,
    tol: float = 1e-6,
) -> bool:
    """The sum of tag probabilities within one dictionary must not exceed 1.0"""
    tag_to_vocab = build_tag_to_vocab_hash(vocabs)
    sums: dict[str, float] = {}
    for tag, prob in tag_probabilities.items():
        vocab = tag_to_vocab.get(tag, get_vocab_name(tag))
        sums[vocab] = sums.get(vocab, 0.0) + prob
    return all(s <= 1.0 + tol for s in sums.values())


def is_valid_outer_tag_probabilities(val) -> bool:
    if not isinstance(val, dict):
        return False
    for k, v in val.items():
        if not isinstance(k, str):
            return False
        if not isinstance(v, dict):
            return False
        for rk, rv in v.items():
            if not isinstance(rk, str):
                return False
            if not isinstance(rv, (int, float)) or isinstance(rv, bool):
                return False
            if not (0.0 <= rv <= 1.0):  # probability must be in [0, 1]
                return False
    return True


def is_valid_vocabs(val) -> bool:
    if not isinstance(val, dict):
        return False
    for k, v in val.items():
        if not isinstance(k, str):
            return False
        if not isinstance(v, list):
            return False
        if not all(isinstance(t, str) for t in v):
            return False
    return True


def is_valid_objective(val) -> bool:
    return val in {MAX_MONEY, MAX_VOLUME}


def is_valid_max_n_categories(val) -> bool:
    return isinstance(val, int) and not isinstance(val, bool) and val > 0


def is_valid_min_category_probability(val) -> bool:
    return isinstance(val, float) and val >= 0


def is_valid_n_threads(val) -> bool:
    return isinstance(val, int) and not isinstance(val, bool) and val >= 1


def is_valid_ads_tags_in_vocabs(ads: dict[AdId, Ad], vocabs: InnerVocabs | None) -> bool:
    # InnerVocabs: {VocabName: [FullTag]}; targets in Ad are RawTag
    # Extract the RawTag from each FullTag to compare with the ads' targets.
    # A dictionary not set in vocabs is skipped — it is normally ignored further on.
    vocab_raw_sets: dict[str, set[str]] = {}
    for vocab_name, full_tags in (vocabs or {}).items():
        vocab_raw_sets[vocab_name] = {get_raw_tag(ft) for ft in full_tags}
    for ad in ads.values():
        targets_value = ad.get('targets', {}).get('value', {})
        for vocab, raw_tags in targets_value.items():
            known = vocab_raw_sets.get(vocab)
            if known is None:
                continue
            if any(t not in known for t in raw_tags):
                return False
    return True


def is_valid_optimize_params(val) -> bool:
    if not isinstance(val, dict):
        return False
    if not is_valid_total_traffic_volume(val.get('total_traffic_volume')):
        return False
    if not is_valid_tag_probabilities(val.get('tag_probabilities')):
        return False
    if not is_valid_vocabs(val.get('vocabs')):
        return False
    if 'objective' in val and not is_valid_objective(val['objective']):
        return False
    if 'max_n_categories' in val and not is_valid_max_n_categories(val['max_n_categories']):
        return False
    if 'min_category_probability' in val and not is_valid_min_category_probability(val['min_category_probability']):
        return False
    if 'n_threads' in val and not is_valid_n_threads(val['n_threads']):
        return False
    return True


def create_optimize_params(
    total_traffic_volume: int,
    tag_probabilities: dict[FullTag, float],
    vocabs: InnerVocabs,
    objective: OBJECTIVES = MAX_MONEY,
    max_n_categories: int = 100,
    min_category_probability: float = MIN_CATEGORY_PROBABILITY,
    n_threads: int = 1,
) -> OptimizeParams:
    validators: dict[str, tuple] = {
        'total_traffic_volume':     (total_traffic_volume,     is_valid_total_traffic_volume,     f"Invalid total_traffic_volume: {total_traffic_volume!r}"),
        'tag_probabilities':        (tag_probabilities,        is_valid_tag_probabilities,        f"Invalid tag_probabilities: {tag_probabilities!r}"),
        'vocabs':                   (vocabs,                   is_valid_vocabs,                   f"Invalid vocabs: {vocabs!r}"),
        'objective':                (objective,                is_valid_objective,                f"Invalid objective: {objective!r}"),
        'max_n_categories':         (max_n_categories,         is_valid_max_n_categories,         f"Invalid max_n_categories: {max_n_categories!r}"),
        'min_category_probability': (min_category_probability, is_valid_min_category_probability, f"Invalid min_category_probability: {min_category_probability!r}"),
        'n_threads':                (n_threads,                is_valid_n_threads,                f"Invalid n_threads: {n_threads!r}"),
    }
    for _field, (value, validator, error_msg) in validators.items():
        if not validator(value):
            raise BalancerError(ErrorCodes.INPUT_VALIDATION_ERROR, error_msg)
    return OptimizeParams(
        total_traffic_volume=total_traffic_volume,
        tag_probabilities=tag_probabilities,
        vocabs=vocabs,
        objective=objective,
        max_n_categories=max_n_categories,
        min_category_probability=min_category_probability,
        n_threads=n_threads,
    )


def load_optimize_params(data: dict) -> OptimizeParams:
    if not is_valid_optimize_params(data):
        raise BalancerError(ErrorCodes.INPUT_VALIDATION_ERROR, f"Invalid OptimizeParams: {data!r}")
    return data  # type: ignore[return-value]


def get_optimize_params_total_traffic_volume(
    params: OptimizeParams,
    default: Optional[int] = None,
) -> Optional[int]:
    return params.get('total_traffic_volume', default)


def get_optimize_params_tag_probabilities(
    params: OptimizeParams,
    default: Optional[dict[FullTag, float]] = None,
) -> Optional[dict[FullTag, float]]:
    return params.get('tag_probabilities', default)


def get_optimize_params_vocabs(
    params: OptimizeParams,
    default: Optional[InnerVocabs] = None,
) -> Optional[InnerVocabs]:
    return params.get('vocabs', default)


def get_optimize_params_objective(params: OptimizeParams, default: str = MAX_MONEY) -> str:
    return params.get('objective', default)


def get_optimize_params_max_n_categories(params: OptimizeParams, default: int = 100) -> int:
    return params.get('max_n_categories', default)


def get_optimize_params_min_category_probability(
    params: OptimizeParams,
    default: float = MIN_CATEGORY_PROBABILITY,
) -> float:
    return params.get('min_category_probability', default)


def get_optimize_params_n_threads(params: OptimizeParams, default: int = 1) -> int:
    return params.get('n_threads', default)


def get_balancing_params_seasonal_context(
    params: BalancingParams,
) -> AdditionalContext | None:
    return params.get('seasonal_context')


def get_extended_balancing_params_ad_vol_distr(
    params: ExtendedBalancingParams,
) -> ProjectedAdVolumes:
    return params.get('ad_vol_distr', {})


def create_balancing_params(
    total_traffic_volume: int,
    tag_probabilities_outer: dict[VocabName, dict[RawTag, float]],
    vocabs_outer: OuterVocabs,
    objective: OBJECTIVES = MAX_MONEY,
    max_n_categories: int = 100,
    min_category_probability: float = MIN_CATEGORY_PROBABILITY,
    n_threads: int = 1,
    seasonal_context: AdditionalContext | None = None,
) -> BalancingParams:
    """Accepts the outer (RawTag) format, converts it to the inner one."""
    inner_vocabs = raw_tag_dict_to_full_tag_dict(vocabs_outer)
    inner_tag_probs = outer_tag_probabilities_to_inner(tag_probabilities_outer)
    result: BalancingParams = {
        'total_traffic_volume': total_traffic_volume,
        'tag_probabilities': inner_tag_probs,
        'vocabs': inner_vocabs,
        'objective': objective,
        'max_n_categories': max_n_categories,
        'min_category_probability': min_category_probability,
        'n_threads': n_threads,
    }
    if seasonal_context is not None:
        result['seasonal_context'] = seasonal_context
    return result


def create_extended_balancing_params(
    total_traffic_volume: int,
    tag_probabilities_outer: dict[VocabName, dict[RawTag, float]],
    vocabs_outer: OuterVocabs,
    ad_vol_distr: ProjectedAdVolumes,
    objective: OBJECTIVES = MAX_MONEY,
    max_n_categories: int = 100,
    min_category_probability: float = MIN_CATEGORY_PROBABILITY,
    n_threads: int = 1,
    seasonal_context: AdditionalContext | None = None,
) -> ExtendedBalancingParams:
    """Accepts the outer (RawTag) format + ad_vol_distr, converts it to the inner one."""
    base = create_balancing_params(
        total_traffic_volume=total_traffic_volume,
        tag_probabilities_outer=tag_probabilities_outer,
        vocabs_outer=vocabs_outer,
        objective=objective,
        max_n_categories=max_n_categories,
        min_category_probability=min_category_probability,
        n_threads=n_threads,
        seasonal_context=seasonal_context,
    )
    return ExtendedBalancingParams(**base, ad_vol_distr=ad_vol_distr)


def outer_to_inner_optimize_params(params: dict) -> OptimizeParams:
    """Converts the outer format (RawTag) to the inner format (FullTag).

    Kept as an internal utility for backward compatibility.
    New code should use create_balancing_params() instead of this function.
    """
    outer_vocabs = params.get('vocabs', {}) or {}
    inner_vocabs: InnerVocabs = raw_tag_dict_to_full_tag_dict(outer_vocabs) if outer_vocabs else {}
    outer_tag_probs = params.get('tag_probabilities', {}) or {}
    # Detect if already in inner format (flat dict[FullTag, float])
    if outer_tag_probs and isinstance(next(iter(outer_tag_probs.values())), dict):
        inner_tag_probs: dict[FullTag, float] = outer_tag_probabilities_to_inner(outer_tag_probs)
    else:
        inner_tag_probs = dict(outer_tag_probs)
    return {**params, 'vocabs': inner_vocabs, 'tag_probabilities': inner_tag_probs}  # type: ignore[return-value]


def build_new_vocabs(
    ads: dict[AdId, InnerAd],
    params: OptimizeParams,
) -> InnerVocabs:
    tag_probabilities = get_optimize_params_tag_probabilities(params, default={}) or {}
    vocabs_full = get_optimize_params_vocabs(params, default={}) or {}
    ads_vocabs_tags = {ad_id: get_inner_ad_targets(ad) for ad_id, ad in ads.items()}

    result: dict[VocabName, set] = {}
    for vocab in vocabs_full:
        for ad_vocabs in ads_vocabs_tags.values():
            if vocab not in result:
                result[vocab] = set()
            if vocab in ad_vocabs:
                result[vocab].update(ad_vocabs[vocab])

    final: InnerVocabs = {}
    for vocab, vocab_full_tags in vocabs_full.items():
        result_vocab = result.get(vocab, set())
        final[vocab] = list(result_vocab)

        result_vocab_prob = sum(tag_probabilities.get(t, 0.0) for t in result_vocab)
        if (len(result_vocab) < len(vocab_full_tags)) or (result_vocab_prob < 1.0):
            tag_other = build_full_tag_other(vocab)
            final[vocab].append(tag_other)

    return final
