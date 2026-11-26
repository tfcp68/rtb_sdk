from typing import Literal, NotRequired
from datetime import datetime
from .discriminated_type_schemas import DiscriminatedTypedDict


type AdId = str
type AuctionTypeId = Literal['precise', 'fuzzy']
type AdShowTimes = dict[AdId, datetime]
type TimestampList = list[datetime]

type AuctionSelectionFunc = Literal['best_one',
              'random_one',
              'best_price',
              'random_price',
              'best_velocity',
              'random_velocity',
              'best_heuristics',
              'random_heuristics',
              'best_hybrid',
              'random_hybrid',
              ]

type FullTag = str  # 'City:Moscow'
type Granularity = Literal['t', 'h', 'd', 'w', 'm']
type MinInterval = Literal['min_interval']
type RawTag = str  # 'Moscow'
type RequestId = str
type UserId = str
type VocabName = str


class GranulatedCounter(DiscriminatedTypedDict):
    value: dict[Granularity, int]


class AuctionStats(DiscriminatedTypedDict):
    value: dict[AuctionTypeId, GranulatedCounter]


class AdStats(DiscriminatedTypedDict):
    value: dict[AdId, AuctionStats]


class Frequency(DiscriminatedTypedDict):
    value: dict[Granularity, float]


class FrequencyLimits(DiscriminatedTypedDict):
    value: dict[Granularity | MinInterval, float]


class TargetVector(DiscriminatedTypedDict):
    value: dict[VocabName, list[RawTag]]


class RequestTags(DiscriminatedTypedDict):
    value: dict[VocabName, FullTag]


class FullTagVector(DiscriminatedTypedDict):
    value: dict[VocabName, list[FullTag]]


class Ad(DiscriminatedTypedDict):
    id: AdId
    targets: TargetVector
    active: bool
    start_date: datetime
    end_date: datetime
    cpm: float
    priority: float
    volume: int
    budget: float
    ad_frequency_limit: FrequencyLimits
    user_frequency_limit: FrequencyLimits
    parasitic_freq_limit: FrequencyLimits
    vocabulary_weights: dict[VocabName, float]
    tag_weights: dict[FullTag, float]


class Request(DiscriminatedTypedDict):
    id: RequestId
    user_id: UserId
    date: datetime
    tags: RequestTags


class ParametersAdsStats(DiscriminatedTypedDict):
    auction_type: AuctionSelectionFunc
    ads_stats: AdStats
    price_probability: NotRequired[float]
    velocity_threshold: NotRequired[float]


type AuctionParams = ParametersAdsStats


class AdsDict(DiscriminatedTypedDict):
    value: dict[AdId, Ad]


type AdwordsAlgorithmId = Literal['a2_single_valued', 'a3_small']


class AdwordsAdState(DiscriminatedTypedDict):
    id: AdId
    price: float
    matches: int
    remaining_budget: float
    real_spend: float
    fake_spend: float


class AdwordsState(DiscriminatedTypedDict):
    algorithm: AdwordsAlgorithmId
    ad_states: dict[AdId, AdwordsAdState]
    query_count: int


class AdwordsMatchResult(DiscriminatedTypedDict):
    matched_ad: AdId | None
    effective_bids: dict[AdId, float]
    state: AdwordsState
