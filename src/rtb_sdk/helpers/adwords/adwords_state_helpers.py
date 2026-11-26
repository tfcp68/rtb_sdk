from rtb_sdk.schemas import (
    AdwordsAdState,
    AdwordsState,
    AdwordsMatchResult,
    AdwordsAlgorithmId,
    AdId,
)
from rtb_sdk.constants import DataAuctionType, AdwordsAlgorithm
from rtb_sdk.errors import AuctionError, ErrorCodes
from rtb_sdk.helpers.type_helpers import check_type

_VALID_ALGORITHMS = frozenset({AdwordsAlgorithm.A2_SINGLE_VALUED, AdwordsAlgorithm.A3_SMALL})


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------

def is_valid_adwords_algorithm(val) -> bool:
    return val in _VALID_ALGORITHMS


def is_valid_adwords_ad_state(val) -> bool:
    if not check_type(val, 'AdwordsAdState'):
        return False
    if not isinstance(val.get('id'), str) or not val.get('id'):
        return False
    price = val.get('price')
    if not isinstance(price, (int, float)) or isinstance(price, bool):
        return False
    matches = val.get('matches')
    if not isinstance(matches, int) or isinstance(matches, bool):
        return False
    for field in ('remaining_budget', 'real_spend', 'fake_spend'):
        v = val.get(field)
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            return False
    return True


def is_valid_adwords_state(val) -> bool:
    if not check_type(val, 'AdwordsState'):
        return False
    if not is_valid_adwords_algorithm(val.get('algorithm')):
        return False
    ad_states = val.get('ad_states')
    if not isinstance(ad_states, dict):
        return False
    for k, v in ad_states.items():
        if not isinstance(k, str) or not k:
            return False
        if not is_valid_adwords_ad_state(v):
            return False
    query_count = val.get('query_count')
    if not isinstance(query_count, int) or isinstance(query_count, bool):
        return False
    return True


# ---------------------------------------------------------------------------
# Creators
# ---------------------------------------------------------------------------

def create_adwords_ad_state(
        id: AdId,
        price: float,
        matches: int,
        remaining_budget: float,
        real_spend: float,
        fake_spend: float,
) -> AdwordsAdState:
    return {
        '__type': DataAuctionType.ADWORDS_AD_STATE,
        'id': id,
        'price': price,
        'matches': matches,
        'remaining_budget': remaining_budget,
        'real_spend': real_spend,
        'fake_spend': fake_spend,
    }


def create_adwords_state(
        algorithm: AdwordsAlgorithmId,
        ad_states: dict,
        query_count: int,
) -> AdwordsState:
    return {
        '__type': DataAuctionType.ADWORDS_STATE,
        'algorithm': algorithm,
        'ad_states': ad_states,
        'query_count': query_count,
    }


def create_adwords_match_result(
        matched_ad: AdId | None,
        effective_bids: dict,
        state: AdwordsState,
) -> AdwordsMatchResult:
    return {
        '__type': DataAuctionType.ADWORDS_MATCH_RESULT,
        'matched_ad': matched_ad,
        'effective_bids': effective_bids,
        'state': state,
    }


# ---------------------------------------------------------------------------
# Getters
# ---------------------------------------------------------------------------

def get_adwords_ad_state_price(s: AdwordsAdState) -> float:
    return s['price']

def get_adwords_ad_state_matches(s: AdwordsAdState) -> int:
    return s['matches']

def get_adwords_ad_state_remaining_budget(s: AdwordsAdState) -> float:
    return s['remaining_budget']

def get_adwords_ad_state_real_spend(s: AdwordsAdState) -> float:
    return s['real_spend']

def get_adwords_ad_state_fake_spend(s: AdwordsAdState) -> float:
    return s['fake_spend']

def get_adwords_state_algorithm(s: AdwordsState) -> AdwordsAlgorithmId:
    return s['algorithm']

def get_adwords_state_ad_states(s: AdwordsState) -> dict:
    return s['ad_states']

def get_adwords_state_query_count(s: AdwordsState) -> int:
    return s['query_count']

def get_adwords_match_result_matched_ad(r: AdwordsMatchResult) -> AdId | None:
    return r['matched_ad']

def get_adwords_match_result_effective_bids(r: AdwordsMatchResult) -> dict:
    return r['effective_bids']

def get_adwords_match_result_state(r: AdwordsMatchResult) -> AdwordsState:
    return r['state']


# ---------------------------------------------------------------------------
# Loaders (deserialize from raw dict)
# ---------------------------------------------------------------------------

def load_adwords_state(data: dict) -> AdwordsState:
    if not check_type(data, 'AdwordsState'):
        raise AuctionError(
            ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE,
            f"Invalid __type for AdwordsState: {data!r}"
        )
    ad_states_raw = data.get('ad_states', {})
    if not isinstance(ad_states_raw, dict):
        raise AuctionError(
            ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE,
            f"ad_states must be a dict, got: {ad_states_raw!r}"
        )
    ad_states = {}
    for ad_id, raw in ad_states_raw.items():
        if not check_type(raw, 'AdwordsAdState'):
            raise AuctionError(
                ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE,
                f"Invalid AdwordsAdState for id={ad_id!r}: {raw!r}"
            )
        ad_states[ad_id] = create_adwords_ad_state(
            id=raw['id'],
            price=float(raw['price']),
            matches=int(raw['matches']),
            remaining_budget=float(raw['remaining_budget']),
            real_spend=float(raw['real_spend']),
            fake_spend=float(raw['fake_spend']),
        )
    algorithm = data.get('algorithm')
    if not is_valid_adwords_algorithm(algorithm):
        raise AuctionError(
            ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE,
            f"Invalid algorithm: {algorithm!r}"
        )
    return create_adwords_state(
        algorithm=algorithm,
        ad_states=ad_states,
        query_count=int(data.get('query_count', 0)),
    )


def load_adwords_match_result(data: dict) -> AdwordsMatchResult:
    if not check_type(data, 'AdwordsMatchResult'):
        raise AuctionError(
            ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE,
            f"Invalid __type for AdwordsMatchResult: {data!r}"
        )
    return create_adwords_match_result(
        matched_ad=data.get('matched_ad'),
        effective_bids=dict(data.get('effective_bids', {})),
        state=load_adwords_state(data['state']),
    )
