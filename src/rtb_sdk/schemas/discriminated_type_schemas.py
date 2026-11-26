from typing import Literal, TypedDict


type DiscriminatedPredictorType = Literal[
    'ProphetOptions',
    'Seasonality',
    'ModelOptions',
    'CommonModel',
    'ProphetModel',
    'FitParams',
    'PredictParams',
    'ProphetModelPredictParams',
    'PredictResult',
    'TestParams',
    'ProphetModelTestParams',
    'TestResult',
    'TestMetrics',
]

type DiscriminatedOptimizerType = Literal[
    'Parameters',
    'MethodOptions',
    'Solution',
    'MethodState',
    'SolutionList',
    'DecisionVariables',
    'GeneticSearchOptions',
    'GeneticSearchState',
    'GridSearchOptions',
    'GridSearchState'
]

type DiscriminatedAuctionType = Literal[
    'Ad', 'Request', 'ParametersAdsStats',
    'AdsDict', 'AdStats', 'AuctionStats', 'Frequency', 'FrequencyLimits',
    'FullTagVector', 'GranulatedCounter', 'TargetVector', 'RequestTags',
    'AdwordsAdState', 'AdwordsState', 'AdwordsMatchResult',
]

type GenericDiscriminatedType = (
    DiscriminatedAuctionType
    | DiscriminatedOptimizerType
    | DiscriminatedPredictorType
)


class DiscriminatedTypedDict(TypedDict):
    __type: GenericDiscriminatedType
