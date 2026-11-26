from rtb_sdk.schemas import (
    AuctionSelectionFunc,
    AuctionTypeId,
    Granularity,
    MinInterval,
    AdwordsAlgorithmId,
)

class SelectionFunc:
    BEST_ONE: AuctionSelectionFunc = 'best_one'
    RANDOM_ONE: AuctionSelectionFunc = 'random_one'
    BEST_PRICE: AuctionSelectionFunc = 'best_price'
    RANDOM_PRICE: AuctionSelectionFunc = 'random_price'
    BEST_VELOCITY: AuctionSelectionFunc = 'best_velocity'
    RANDOM_VELOCITY: AuctionSelectionFunc = 'random_velocity'
    BEST_HEURISTICS: AuctionSelectionFunc = 'best_heuristics'
    RANDOM_HEURISTICS: AuctionSelectionFunc = 'random_heuristics'
    BEST_HYBRID: AuctionSelectionFunc = 'best_hybrid'
    RANDOM_HYBRID: AuctionSelectionFunc = 'random_hybrid'


class AuctionType:
    PRECISE: AuctionTypeId = 'precise'
    FUZZY: AuctionTypeId = 'fuzzy'

MIN_INTERVAL: MinInterval = 'min_interval'

class Gran:
    TEN_MINUTES: Granularity= 't'
    HOUR: Granularity = 'h'
    DAY: Granularity = 'd'
    WEEK: Granularity = 'w'
    MONTH: Granularity = 'm'


class AdwordsAlgorithm:
    A2_SINGLE_VALUED: AdwordsAlgorithmId = 'a2_single_valued'
    A3_SMALL: AdwordsAlgorithmId = 'a3_small'
