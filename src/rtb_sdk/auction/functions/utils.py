from typing import Optional
from rtb_sdk.schemas import (
    FullTag,
    AdStats,
    GranulatedCounter,
    AdId,
    AuctionTypeId,
    Ad,
    AuctionStats,
    FullTagVector,
)
from rtb_sdk.helpers import (
    get_date_month_volume,
    get_ad_frequency_limit,
    get_real_month_ad_frequency,
    get_actual_args,
    create_auction_stats,
    create_granulated_counter,
)
from rtb_sdk.constants import (
    INT_MAX,
    FLOAT_MAX,
)
from rtb_sdk.errors import AuctionError, ErrorCodes


def is_auction_type(val: str) -> bool:
    """Checks whether a string is a valid auction type identifier.

    Args:
        val (str): The string to check.

    Returns:
        bool: True if val belongs to the set of valid
            AuctionTypeId values, otherwise False.

    Example:
        >>> is_auction_type("precise")
        True
        >>> is_auction_type("unknown")
        False
    """
    return val in get_actual_args(AuctionTypeId.__value__)


def calc_rarity(ad_tags: FullTagVector,
                tag_probs: dict[FullTag, float]
                ) -> float:
    """Computes the "rarity" of an ad based on the probabilities of its tags.

    For each of the ad's tag dictionaries, sums the probabilities of the
    individual tags, then multiplies the results across all dictionaries.
    The lower the total tag probability, the higher the ad's rarity.

    Args:
        ad_tags (FullTagVector): "Vocabulary name → list of tags" dictionary
            for the given ad.
        tag_probs (dict[FullTag, float]): Global probabilities
            of each tag appearing in the auction.

    Returns:
        float: Product of the total probabilities over all dictionaries.
            A value close to 0 means a very rare ad.

    Example:
        >>> calc_rarity({"cat": ["sports"]}, {"sports": 0.1})
        0.1
    """
    result = 1.0
    for vocab_name in ad_tags:
        tags = ad_tags[vocab_name]
        probs = [tag_probs[tag] for tag in tags]
        vocab_prob = sum(probs)
        result *= vocab_prob
    return result
        


def rarity_factor(rarity: float
                  ) -> float:
    """Converts the ad's rarity into a normalized auction factor.

    The rarer the ad (the lower the rarity), the higher the returned factor,
    and vice versa. Formula: 1 - rarity.

    Args:
        rarity (float): Ad rarity in the range [0.0, 1.0],
            where 0.0 is the rarest, 1.0 is very common.

    Returns:
        float: Normalized rarity factor in the range [0.0, 1.0].

    Example:
        >>> rarity_factor(0.3)
        0.7
    """
    return 1 - rarity


def price_factor(price:float,
                 max_price:float
                 ) -> float:
    """Computes the ad's normalized price factor.

    Normalizes the ad's price by the maximum price among
    all candidates: factor = price / max_price. The ad with the
    maximum price gets factor=1.0.

    Args:
        price (float): Price of the current ad. A falsy value
            is treated as 0.
        max_price (float): Maximum price among all ads.
            Must not be zero.

    Returns:
        float: Normalized price factor in the range [0.0, 1.0].

    Raises:
        AuctionError: If max_price is zero (division by zero).

    Example:
        >>> price_factor(5.0, 10.0)
        0.5
    """
    if not price:
        price = 0
    if max_price == 0:
        raise AuctionError(ErrorCodes.AUCTION_MATH_ERROR_CODE, "zero division")
    return price / max_price
    

def priority_factor(priority:float,
                    max_priority:float
                    ) -> float:
    """Computes the ad's normalized priority factor.

    Normalizes the ad's priority by the maximum priority
    among all candidates: factor = priority / max_priority. The ad
    with the maximum priority gets factor=1.0.

    Args:
        priority (float): Priority of the current ad.
        max_priority (float): Maximum priority among all
            ads. Must not be zero.

    Returns:
        float: Normalized priority factor in the range [0.0, 1.0].

    Raises:
        AuctionError: If max_priority is zero (division by zero).

    Example:
        >>> priority_factor(3.0, 10.0)
        0.3
    """
    if max_priority == 0:
        raise AuctionError(ErrorCodes.AUCTION_MATH_ERROR_CODE, "zero division")
    return priority / max_priority
    

def velocity_factor(current_month_volume: float,
                    month_limit: float,
                    max_volume: float,
                    ) -> float:
    """Computes the ad's "under-delivery" factor relative to the monthly limit.

    If the ad's limit is not set or is infinite, the factor is computed
    relative to the maximum limit among all candidates:
    (max_volume - current) / max_volume. Otherwise — relative to
    its own limit: (month_limit - current) / month_limit.
    The larger the remaining part of the limit, the higher the factor.

    Args:
        current_month_volume (float): Actual number of impressions of the
            ad in the current month.
        month_limit (float): Monthly impression limit of the ad.
            None, INT_MAX or a value <= 0 is treated as "no limit".
        max_volume (float): Maximum monthly limit among all
            ads (used when the ad has no limit of its own).

    Returns:
        float: Under-delivery factor. May be negative if the
            current volume exceeded the limit.

    Raises:
        AuctionError: If max_volume is zero when there is no
            own limit (division by zero).

    Example:
        >>> velocity_factor(200.0, 1000.0, 5000.0)
        0.8
    """
    if (month_limit is None) or (month_limit == INT_MAX) or (month_limit <= 0):
        if max_volume == 0:
            raise AuctionError(ErrorCodes.AUCTION_MATH_ERROR_CODE, "zero division")
        return (max_volume - current_month_volume) / max_volume
    else:
        return (month_limit - current_month_volume) / month_limit
    

def heuristic_function_simplest(priority_factor: float,
                                price_factor: float,
                                velocity_factor: float
                                ) -> float:
    """Computes the ad's final heuristic score as the product of three factors.

    The simplest heuristic: score = priority_factor * price_factor *
    velocity_factor. All factors are normalized to [0.0, 1.0], so
    the result also lies in this range.

    Args:
        priority_factor (float): Normalized priority factor.
        price_factor (float): Normalized price factor.
        velocity_factor (float): Normalized under-delivery factor.

    Returns:
        float: Product of the three factors in the range [0.0, 1.0].

    Example:
        >>> heuristic_function_simplest(0.8, 0.5, 0.6)
        0.24
    """
    return priority_factor * price_factor * velocity_factor
    

def get_frequency_month_volume(ad: Ad,
                               delta_date_factor: float = 1.0
                               ) -> Optional[float]:
    """Returns the ad's monthly impression limit based on its frequency cap.

    Computes the actual monthly volume from the ad's frequency limit,
    taking the date correction factor into account.

    Args:
        ad (Ad): The ad for which the limit is computed.
        delta_date_factor (float, optional): Correction factor
            accounting for the elapsed share of the month. Defaults to 1.0.

    Returns:
        Optional[float]: Monthly limit by frequency, or None if
            no frequency cap is set.

    Example:
        >>> get_frequency_month_volume(ad)
        30000.0
    """
    freq_limit = get_ad_frequency_limit(ad)
    return get_real_month_ad_frequency(freq_limit,
                                                   delta_date_factor)
  
def get_real_month_volume(ad: Ad,
                          delta_date_factor: float = 1.0
                          ) -> float:
    """Returns the effective monthly impression limit of the ad.

    Takes the minimum of the frequency and date limits. If one of them
    is not set or is not positive, it is replaced with FLOAT_MAX so as not to
    constrain the result.

    Args:
        ad (Ad): The ad for which the limit is computed.
        delta_date_factor (float, optional): Correction factor
            accounting for the elapsed share of the month. Defaults to 1.0.

    Returns:
        float: The smaller of the two limits (frequency and date).
            Always a positive value.

    Example:
        >>> get_real_month_volume(ad)
        15000.0
    """
    freq_volume = get_frequency_month_volume(ad,
                                             delta_date_factor)
    if (freq_volume is None) or (freq_volume <= 0):
        freq_volume = FLOAT_MAX
    
    date_volume = get_date_month_volume(ad)
    if (date_volume is None) or (date_volume <= 0):
        date_volume = FLOAT_MAX
    
    return min(freq_volume, date_volume)

def get_statistics_by_id(statistics: AdStats,
                         id: AdId) -> AuctionStats:
    """Returns auction statistics for a specific ad.

    Looks up the record by ad identifier within the overall statistics.
    If there is no record, returns an empty AuctionStats structure.

    Args:
        statistics (AdStats): Overall statistics for all ads.
        id (AdId): Identifier of the required ad.

    Returns:
        AuctionStats: The ad's statistics, or an empty AuctionStats
            if the ad is not found.

    Example:
        >>> stats = get_statistics_by_id(all_stats, "ad_42")
        >>> isinstance(stats, dict)
        True
    """
    return statistics.get('value', {}).get(id, create_auction_stats())

def get_statistics_by_auction_type(statistics: AuctionStats,
                                   auction_type: AuctionTypeId
                                   ) -> GranulatedCounter:
    """Returns the granulated counter for the given auction type.

    Filters the ad's statistics by auction type (e.g. PRECISE
    or FUZZY). If there is no counter for the given type, returns
    an empty GranulatedCounter.

    Args:
        statistics (AuctionStats): Statistics of a specific ad
            across all auction types.
        auction_type (AuctionTypeId): Auction type identifier.
            Must be a valid AuctionTypeId value.

    Returns:
        GranulatedCounter: Impression counter broken down by period, or
            an empty counter if the type is not found.

    Raises:
        AuctionError: If auction_type is not a valid
            auction type identifier.

    Example:
        >>> counter = get_statistics_by_auction_type(ad_stats, "precise")
        >>> isinstance(counter, dict)
        True
    """
    if not is_auction_type(auction_type):
        raise AuctionError(ErrorCodes.WRONG_DATA_FORMAT_ERROR_CODE, "Wrong data format")
    return statistics.get('value', {}).get(auction_type, create_granulated_counter())