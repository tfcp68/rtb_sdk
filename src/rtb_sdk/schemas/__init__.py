from auto_all import start_all, end_all

start_all()

from .auction_schemas import (
    # Type aliases
    AdId,
    AdShowTimes,
    AdStats,
    AuctionStats,
    AuctionParams,
    AuctionTypeId,
    AuctionSelectionFunc,
    Frequency,
    FrequencyLimits,
    FullTag,
    FullTagVector,
    Granularity,
    MinInterval,
    GranulatedCounter,
    RawTag,
    RequestId,
    TargetVector,
    RequestTags,
    TimestampList,
    UserId,
    VocabName,
    # Classes
    ParametersAdsStats,
    Ad,
    Request,
    AdsDict,
    # Adwords
    AdwordsAlgorithmId,
    AdwordsAdState,
    AdwordsState,
    AdwordsMatchResult,
)

from .optimizer_schemas import (
    OptimizationMethodId,
    OptimizationStrategyId,
    StateRouterType,
    OptionsRouterType,
    Estimation,
    Parameters,
    DecisionVariables,
    Solution,
    MethodOptions,
    MethodState,
    SolutionList,
    GeneticSearchOptions,
    GeneticSearchState,
    GridSearchOptions,
    GridSearchState,
)

from .predictor_schemas import (
    ModelType,
    ReportType,
    GrowthNameType,
    SeasonalityModeType,
    SeasonalityNameType,
    Seasonality,
    ModelOptions,
    ProphetOptions,
    CommonModel,
    ProphetModel,
    FitParams,
    PredictParams,
    ProphetModelPredictParams,
    PredictResult,
    TestParams,
    ProphetModelTestParams,
    TestResult,
    TestMetrics,
)

from .discriminated_type_schemas import (
    DiscriminatedPredictorType,
    DiscriminatedOptimizerType,
    DiscriminatedAuctionType,
    GenericDiscriminatedType,
    DiscriminatedTypedDict,
)

from .balancer_schemas import (
    InnerVocab,
    InnerVocabs,
    OuterVocab,
    OuterVocabs,
    RequestFlow,
    RequestFlowWithAd,
    ProjectedAdVolumes,
    BalanceResult,
    InnerAd,
    FullTagWithProbability,
    BalancingParams,
    OptimizeParams,
    AddCampaignResult,
    RebalanceResult,
    BalancerAuctionData,
    AuctionParamsBalanced,
    BalancingBySelloutParams,
    BalancingBySelloutResult,
)

end_all()
