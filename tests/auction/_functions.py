"""
Header file: imports and re-exports all functions under test.
The root test file uses FUNCTIONS to build the describe_ blocks.

FUNCTIONS: {func_name: (func, unpacker | None)}
  - func     — the function under test
  - unpacker — takes a raw case (dict) and returns a case with already
               assembled objects; None for functions without complex types.
"""
from rtb_sdk.auction.functions.utils import (
    is_auction_type,
    calc_rarity,
    rarity_factor,
    price_factor,
    priority_factor,
    velocity_factor,
    heuristic_function_simplest,
    get_statistics_by_id,
    get_statistics_by_auction_type,
)
from rtb_sdk.auction.functions.auction_one import auction_first_one, auction_random_one
from rtb_sdk.auction.functions.auction_price import auction_best_price, auction_random_price
from rtb_sdk.auction.functions.auction_velocity import auction_best_velocity, auction_random_velocity
from rtb_sdk.auction.functions.auction_heuristics import auction_best_heuristics, auction_random_heuristics
from rtb_sdk.auction.functions.auction_hybrid import auction_best_hybrid, auction_random_hybrid
from rtb_sdk.helpers import (
    get_real_month_ad_frequency,
    create_granulated_counter,
    create_frequency_limits,
    create_target_vector,
    create_auction_stats,
    create_ad_stats,
    create_ad,
    create_ads_dict,
    load_ad_raw,
    merge_granulated_counters,
    is_valid_auction_selection_func,
)
from rtb_sdk.helpers.auction.ad_helpers import _GRAN_PARAM_MAP

# ---------------------------------------------------------------------------
# Low-level builders (raw dict → typed object)
# ---------------------------------------------------------------------------

def _build_granulated_counter_raw(data: dict):
    kwargs = {_GRAN_PARAM_MAP[k]: v for k, v in data.items() if k in _GRAN_PARAM_MAP}
    return create_granulated_counter(**kwargs)


def _build_frequency_limits_raw(data: dict):
    kwargs: dict = {}
    for k, v in data.items():
        if k in _GRAN_PARAM_MAP:
            kwargs[_GRAN_PARAM_MAP[k]] = v
        elif k == 'min_interval':
            kwargs['min_interval'] = v
    return create_frequency_limits(**kwargs)


def _build_auction_stats_raw(data: dict):
    precise = _build_granulated_counter_raw(data.get('precise', {}))
    fuzzy   = _build_granulated_counter_raw(data.get('fuzzy',   {}))
    return create_auction_stats(precise, fuzzy)


def _build_ad_stats_raw(data: dict):
    return create_ad_stats({k: _build_auction_stats_raw(v) for k, v in data.items()})


def _build_ads_dict_raw(data: dict):
    return create_ads_dict({ad_id: load_ad_raw(ad_data) for ad_id, ad_data in data.items()})


# ---------------------------------------------------------------------------
# Case unpackers (by schema groups)
# ---------------------------------------------------------------------------

def _unpack_freq_limits(case: dict) -> dict:
    """get_real_month_ad_frequency: ad_frequencies → FrequencyLimits."""
    case['input']['ad_frequencies'] = _build_frequency_limits_raw(case['input']['ad_frequencies'])
    return case


def _unpack_stats_by_id(case: dict) -> dict:
    """get_statistics_by_id: statistics → AdStats, output → AuctionStats."""
    case['input']['statistics'] = _build_ad_stats_raw(case['input']['statistics'])
    if case.get('output') is not None:
        case['output'] = _build_auction_stats_raw(case['output'])
    return case


def _unpack_stats_by_type(case: dict) -> dict:
    """get_statistics_by_auction_type: statistics → AuctionStats, output → GranulatedCounter."""
    case['input']['statistics'] = _build_auction_stats_raw(case['input']['statistics'])
    if case.get('output') is not None:
        case['output'] = _build_granulated_counter_raw(case['output'])
    return case


def _unpack_merge_counters(case: dict) -> dict:
    """merge_granulated_counters: a, b → GranulatedCounter, output → GranulatedCounter."""
    case['input']['a'] = _build_granulated_counter_raw(case['input']['a'])
    case['input']['b'] = _build_granulated_counter_raw(case['input']['b'])
    if case.get('output') is not None:
        case['output'] = _build_granulated_counter_raw(case['output'])
    return case


def _unpack_auction_ads(case: dict) -> dict:
    """auction_*: ads → AdsDict, parameters.ads_stats → AdStats (if present), output → Ad."""
    inp = case['input']
    inp['ads'] = _build_ads_dict_raw(inp['ads'])
    params = inp.get('parameters', {})
    if 'ads_stats' in params:
        params['ads_stats'] = _build_ad_stats_raw(params['ads_stats'])
    if not case.get('check_output_type') and case.get('output') is not None:
        case['output'] = load_ad_raw(case['output'])
    return case


# ---------------------------------------------------------------------------
# Mapping: function name → (function, unpacker | None)
# ---------------------------------------------------------------------------

FUNCTIONS: dict[str, tuple] = {
    'is_auction_type':                (is_auction_type,                None),
    'is_valid_auction_selection_func': (is_valid_auction_selection_func, None),
    'merge_granulated_counters':      (merge_granulated_counters,      _unpack_merge_counters),
    'calc_rarity':                    (calc_rarity,                    None),
    'rarity_factor':                  (rarity_factor,                  None),
    'price_factor':                   (price_factor,                   None),
    'priority_factor':                (priority_factor,                None),
    'velocity_factor':                (velocity_factor,                None),
    'heuristic_function_simplest':    (heuristic_function_simplest,    None),
    'get_real_month_ad_frequency':    (get_real_month_ad_frequency,    _unpack_freq_limits),
    'get_statistics_by_id':           (get_statistics_by_id,           _unpack_stats_by_id),
    'get_statistics_by_auction_type': (get_statistics_by_auction_type, _unpack_stats_by_type),
    'auction_first_one':              (auction_first_one,              _unpack_auction_ads),
    'auction_random_one':             (auction_random_one,             _unpack_auction_ads),
    'auction_best_price':             (auction_best_price,             _unpack_auction_ads),
    'auction_random_price':           (auction_random_price,           _unpack_auction_ads),
    'auction_best_velocity':          (auction_best_velocity,          _unpack_auction_ads),
    'auction_random_velocity':        (auction_random_velocity,        _unpack_auction_ads),
    'auction_best_heuristics':        (auction_best_heuristics,        _unpack_auction_ads),
    'auction_random_heuristics':      (auction_random_heuristics,      _unpack_auction_ads),
    'auction_best_hybrid':            (auction_best_hybrid,            _unpack_auction_ads),
    'auction_random_hybrid':          (auction_random_hybrid,          _unpack_auction_ads),
}
