"""
Mapping of the functions under test for adwords.
FUNCTIONS: {func_name: (func, unpacker | None)}
"""
from rtb_sdk.auction.adwords import initialize_adwords, auction_adwords
from rtb_sdk.helpers.adwords import is_valid_adwords_algorithm, load_adwords_state
from rtb_sdk.helpers import create_ads_dict, load_ad_raw


def _build_ads_dict_raw(data: dict):
    return create_ads_dict({ad_id: load_ad_raw(ad_data) for ad_id, ad_data in data.items()})


def _unpack_initialize(case: dict) -> dict:
    """initialize_adwords: ads (raw dict) → AdsDict."""
    case['input']['ads'] = _build_ads_dict_raw(case['input']['ads'])
    return case


def _unpack_adwords(case: dict) -> dict:
    """auction_adwords: ads (raw dict) → AdsDict, state (raw dict) → AdwordsState."""
    case['input']['ads'] = _build_ads_dict_raw(case['input']['ads'])
    case['input']['state'] = load_adwords_state(case['input']['state'])
    return case


def _get_matched_ad(ads, state):
    """Wrapper: returns matched_ad from AdwordsMatchResult."""
    result = auction_adwords(ads=ads, state=state)
    return result.get('matched_ad')


FUNCTIONS: dict[str, tuple] = {
    'is_valid_adwords_algorithm': (is_valid_adwords_algorithm, None),
    'initialize_adwords':         (initialize_adwords, _unpack_initialize),
    'auction_adwords_a2':         (_get_matched_ad, _unpack_adwords),
    'auction_adwords_a3':         (_get_matched_ad, _unpack_adwords),
}
