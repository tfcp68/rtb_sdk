"""
Public API of the adwords module (Adwords/Vazirani algorithm).

Functions:
  initialize_adwords(ads, algorithm) -> AdwordsState
  auction_adwords(ads, state) -> AdwordsMatchResult
"""
from rtb_sdk.schemas import AdsDict, AdwordsState, AdwordsAlgorithmId, AdwordsMatchResult
from rtb_sdk.constants import AdwordsAlgorithm
from rtb_sdk.helpers.auction import is_valid_auction_ads_dict, get_ads_list
from rtb_sdk.helpers.adwords import is_valid_adwords_algorithm, is_valid_adwords_state
from rtb_sdk.errors import AuctionError, ErrorCodes
from .functions.a2_single_valued import a2_initialize, a2_auction_step
from .functions.a3_small import a3_initialize, a3_auction_step

_ALGORITHMS = {
    AdwordsAlgorithm.A2_SINGLE_VALUED: (a2_initialize, a2_auction_step),
    AdwordsAlgorithm.A3_SMALL:         (a3_initialize, a3_auction_step),
}


def _validate_a3_budgets(ads: AdsDict) -> None:
    """Checks that all ads have budget > 0 (an A3 requirement)."""
    for ad in get_ads_list(ads):
        budget = ad.get('budget', 0.0)
        if budget <= 0:
            raise AuctionError(
                ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE,
                f"A3 demand budget > 0 for each announcement, "
                f"received budget={budget!r} for ad id={ad.get('id')!r}",
            )


def initialize_adwords(ads: AdsDict, algorithm: AdwordsAlgorithmId) -> AdwordsState:
    """Initializes the state of the Adwords auction (once per session).

    Args:
        ads:       Dictionary of ads (non-empty).
        algorithm: Algorithm identifier ('a2_single_valued' or 'a3_small').

    Returns:
        AdwordsState with random prices pj = exp(wj - 1).

    Raises:
        AuctionError: If algorithm is invalid, ads is empty,
                      or A3 + budget <= 0 for any ad.
    """
    if not is_valid_adwords_algorithm(algorithm):
        raise AuctionError(
            ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE,
            f"Failed algorithm Adwords: {algorithm!r}",
        )
    if not is_valid_auction_ads_dict(ads) or not ads.get('value'):
        raise AuctionError(
            ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE,
            "ads must be unempty AdsDict",
        )
    if algorithm == AdwordsAlgorithm.A3_SMALL:
        _validate_a3_budgets(ads)
    init_fn, _ = _ALGORITHMS[algorithm]
    return init_fn(ads, algorithm)


def auction_adwords(ads: AdsDict, state: AdwordsState) -> AdwordsMatchResult:
    """Performs one step of the Adwords auction.

    Args:
        ads:   Dictionary of candidate ads (may be empty).
        state: Current session state (obtained from initialize_adwords
               or from the previous auction_adwords call).

    Returns:
        AdwordsMatchResult with matched_ad (or None), effective_bids and the new state.

    Raises:
        AuctionError: If ads or state failed validation.
    """
    if not is_valid_auction_ads_dict(ads):
        raise AuctionError(
            ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE,
            f"Disabled ads: {ads!r}",
        )
    if not is_valid_adwords_state(state):
        raise AuctionError(
            ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE,
            f"Disabled AdwordsState: {state!r}",
        )
    algorithm = state['algorithm']
    _, step_fn = _ALGORITHMS[algorithm]
    return step_fn(ads, state)
