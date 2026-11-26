from rtb_sdk.schemas.auction_schemas import AdId, Ad
from rtb_sdk.schemas.balancer_schemas import BalancingParams, ExtendedBalancingParams, ProjectedAdVolumes
from rtb_sdk.errors.balancer import BalancerError, ErrorCodes
from rtb_sdk.helpers.balancer.optimize_params_helpers import (
    is_valid_total_traffic_volume,
    is_valid_tag_probabilities,
    is_valid_tag_probabilities_sum,
    is_valid_vocabs,
    is_valid_ads_tags_in_vocabs,
    is_valid_max_n_categories,
    is_valid_min_category_probability,
    is_valid_n_threads,
    get_optimize_params_total_traffic_volume,
    get_optimize_params_vocabs,
    get_optimize_params_max_n_categories,
    get_optimize_params_min_category_probability,
    get_optimize_params_n_threads,
    get_extended_balancing_params_ad_vol_distr,
)
from rtb_sdk.helpers.balancer.balancing_by_sellout_helpers import (
    is_valid_parameters_accuracy_percent,
    is_valid_parameters_func_replace_infinity,
    get_balance_by_sellout_parameters_accuracy_percent,
    get_balance_by_sellout_parameters_func_replace_infinity,
)

_E = ErrorCodes.INPUT_VALIDATION_ERROR


def _raise(msg: str) -> None:
    raise BalancerError(_E, msg)


def validate_ad(ad_id: AdId, ad: Ad) -> None:
    if not isinstance(ad, dict):
        _raise(f'Ad "{ad_id}" must be a dict')

    id_val = ad.get('id')
    if not isinstance(id_val, str) or not id_val:
        _raise(f'Ad "{ad_id}": id must be a non-empty string')

    targets = ad.get('targets')
    if not isinstance(targets, dict):
        _raise(f'Ad "{ad_id}": targets must be a dict')
    targets_value = targets.get('value')
    if not isinstance(targets_value, dict):
        _raise(f'Ad "{ad_id}": targets.value must be a dict')
    for vocab, tags in targets_value.items():
        if not isinstance(vocab, str):
            _raise(f'Ad "{ad_id}": targets.value keys must be strings')
        if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
            _raise(f'Ad "{ad_id}": targets.value["{vocab}"] must be a list of strings')

    volume = ad.get('volume')
    if not isinstance(volume, int) or isinstance(volume, bool) or volume < 0:
        _raise(f'Ad "{ad_id}": volume must be a non-negative integer')

    cpm = ad.get('cpm')
    if not isinstance(cpm, (int, float)) or isinstance(cpm, bool) or cpm < 0:
        _raise(f'Ad "{ad_id}": cpm must be a non-negative number')


def validate_optimize(ads: dict[AdId, Ad], params: BalancingParams) -> None:
    if not isinstance(ads, dict):
        _raise('ads must be a dict')
    for ad_id, ad in ads.items():
        validate_ad(ad_id, ad)

    total = get_optimize_params_total_traffic_volume(params, default=None)  # type: ignore[arg-type]
    if not is_valid_total_traffic_volume(total):
        _raise('total_traffic_volume must be a non-negative integer')

    tag_probs = params.get('tag_probabilities', None)
    if not is_valid_tag_probabilities(tag_probs):
        _raise('tag_probabilities must be a dict[FullTag, float]')

    vocabs = get_optimize_params_vocabs(params, default=None)  # type: ignore[arg-type]
    if not is_valid_vocabs(vocabs):
        _raise('vocabs must be a dict')

    if not is_valid_tag_probabilities_sum(tag_probs, vocabs):
        _raise('tag_probabilities: sum of probabilities within a single vocab must not exceed 1.0')

    if not is_valid_ads_tags_in_vocabs(ads, vocabs):
        _raise('ads contain tags not present in the provided vocabs')

    max_n = get_optimize_params_max_n_categories(params)  # type: ignore[arg-type]
    if not is_valid_max_n_categories(max_n):
        _raise('max_n_categories must be a positive integer')

    min_prob = get_optimize_params_min_category_probability(params)  # type: ignore[arg-type]
    if not is_valid_min_category_probability(min_prob):
        _raise('min_category_probability must be a non-negative float')

    n_threads = get_optimize_params_n_threads(params)  # type: ignore[arg-type]
    if not is_valid_n_threads(n_threads):
        _raise('n_threads must be an integer >= 1')


def validate_add_campaign(
    ads: dict[AdId, Ad],
    params: ExtendedBalancingParams,
) -> None:
    validate_optimize(ads, params)
    ad_vol_distr = get_extended_balancing_params_ad_vol_distr(params)
    if not isinstance(ad_vol_distr, dict):
        _raise('ad_vol_distr must be a dict')
    for ad_id, vol in ad_vol_distr.items():
        if not isinstance(ad_id, str):
            _raise('ad_vol_distr keys must be strings (AdId)')
        if not isinstance(vol, int) or vol < 0:
            _raise(f'ad_vol_distr["{ad_id}"] must be a non-negative integer')


def validate_predict_rebalance(
    ads: dict[AdId, Ad],
    params: ExtendedBalancingParams,
) -> None:
    validate_add_campaign(ads, params)


def validate_balance_by_sellout(
    ads: dict[AdId, Ad],
    params: BalancingParams,
) -> None:
    validate_optimize(ads, params)

    accuracy_percent = get_balance_by_sellout_parameters_accuracy_percent(params)  # type: ignore[arg-type]
    if not is_valid_parameters_accuracy_percent(accuracy_percent):
        _raise('accuracy_percent must be a positive float')

    func_replace_infinity = get_balance_by_sellout_parameters_func_replace_infinity(params)  # type: ignore[arg-type]
    if not is_valid_parameters_func_replace_infinity(func_replace_infinity):
        _raise('func_replace_infinity must be None or a callable taking a single iterable argument')
