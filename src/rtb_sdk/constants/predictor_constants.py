from rtb_sdk.schemas.predictor_schemas import (
    SeasonalityModeType,
    GrowthNameType,
    SeasonalityNameType,
    ModelType
)


class SeasonalityMode:
    multiplicative: SeasonalityModeType = 'multiplicative'
    additive: SeasonalityModeType = 'additive'

class GrowthName:
    linear: GrowthNameType = 'linear'
    logistic: GrowthNameType = 'logistic'

class SeasonalityName:
    monthly: SeasonalityNameType = 'monthly'
    weekly: SeasonalityNameType = 'weekly'
    daily: SeasonalityNameType = 'daily'

class ModelTypeName:
    PROPHET: ModelType = 'prophet'

class CoreColumnConstants:
    DS_COLUMN = "ds"
    Y_COLUMN = "y"
    YHAT_COLUMN = "yhat"
