from rtb_sdk.schemas.discriminated_type_schemas import DiscriminatedPredictorType
from rtb_sdk.schemas import DiscriminatedAuctionType, DiscriminatedOptimizerType


class DataPredictorType:
    PROPHET_OPTIONS: DiscriminatedPredictorType = 'ProphetOptions'
    SEASONALITY: DiscriminatedPredictorType = 'Seasonality'
    MODEL_OPTIONS: DiscriminatedPredictorType = 'ModelOptions'
    COMMON_MODEL: DiscriminatedPredictorType = 'CommonModel'
    PROPHET_MODEL: DiscriminatedPredictorType = 'ProphetModel'
    FIT_PARAMS: DiscriminatedPredictorType = 'FitParams'
    PREDICT_PARAMS: DiscriminatedPredictorType = 'PredictParams'
    PROPHET_MODEL_PREDICT_PARAMS: DiscriminatedPredictorType = 'ProphetModelPredictParams'
    PREDICT_RESULT: DiscriminatedPredictorType = 'PredictResult'
    TEST_PARAMS: DiscriminatedPredictorType = 'TestParams'
    PROPHET_MODEL_TEST_PARAMS: DiscriminatedPredictorType = 'ProphetModelTestParams'
    TEST_RESULT: DiscriminatedPredictorType = 'TestResult'
    TEST_METRICS: DiscriminatedPredictorType = 'TestMetrics'

class DataAuctionType:
    AD: DiscriminatedAuctionType = 'Ad'
    REQUEST: DiscriminatedAuctionType = 'Request'
    PARAMETERS_ADS_STATS: DiscriminatedAuctionType = 'ParametersAdsStats'
    ADS_DICT: DiscriminatedAuctionType = 'AdsDict'
    AD_STATS: DiscriminatedAuctionType = 'AdStats'
    AUCTION_STATS: DiscriminatedAuctionType = 'AuctionStats'
    FREQUENCY: DiscriminatedAuctionType = 'Frequency'
    FREQUENCY_LIMITS: DiscriminatedAuctionType = 'FrequencyLimits'
    FULL_TAG_VECTOR: DiscriminatedAuctionType = 'FullTagVector'
    GRANULATED_COUNTER: DiscriminatedAuctionType = 'GranulatedCounter'
    TARGET_VECTOR: DiscriminatedAuctionType = 'TargetVector'
    REQUEST_TAGS: DiscriminatedAuctionType = 'RequestTags'
    ADWORDS_AD_STATE: DiscriminatedAuctionType = 'AdwordsAdState'
    ADWORDS_STATE: DiscriminatedAuctionType = 'AdwordsState'
    ADWORDS_MATCH_RESULT: DiscriminatedAuctionType = 'AdwordsMatchResult'

class DataOptimizerType:
    PARAMETERS: DiscriminatedOptimizerType = 'Parameters'
    METHOD_OPTIONS: DiscriminatedOptimizerType = 'MethodOptions'
    SOLUTION: DiscriminatedOptimizerType = 'Solution'
    METHOD_STATE: DiscriminatedOptimizerType = 'MethodState'
    SOLUTION_LIST: DiscriminatedOptimizerType = 'SolutionList'
    DECISION_VARIABLES: DiscriminatedOptimizerType = 'DecisionVariables'
    GENETIC_SEARCH_OPTIONS: DiscriminatedOptimizerType = 'GeneticSearchOptions'
    GENETIC_SEARCH_STATE: DiscriminatedOptimizerType = 'GeneticSearchState'
    GRID_SEARCH_OPTIONS: DiscriminatedOptimizerType = 'GridSearchOptions'
    GRID_SEARCH_STATE: DiscriminatedOptimizerType = 'GridSearchState'
