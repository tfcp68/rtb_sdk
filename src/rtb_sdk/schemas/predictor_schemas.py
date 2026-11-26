from typing import Any, Literal, Optional
from datetime import datetime

from .auction_schemas import Granularity
from .discriminated_type_schemas import DiscriminatedTypedDict


type ModelType = Literal["prophet",]

type ReportType = Literal['md', 'json', 'png']

# Prophet options types
type GrowthNameType = Literal['linear', 'logistic']
type SeasonalityModeType = Literal['multiplicative', 'additive']
type SeasonalityNameType = Literal['monthly', 'weekly', 'daily']


class Seasonality(DiscriminatedTypedDict):
    name: SeasonalityNameType
    period: float
    fourier_order: int


class ModelOptions(DiscriminatedTypedDict):
    model_type: ModelType


class ProphetOptions(ModelOptions):
    growth: GrowthNameType
    changepoint_prior_scale: float
    seasonality_mode: SeasonalityModeType
    seasonality_prior_scale: float
    yearly_seasonality: bool
    weekly_seasonality: bool
    n_changepoints: int
    changepoint_range: float
    seasonalities: dict[SeasonalityNameType, Seasonality]


# Model types

class CommonModel(DiscriminatedTypedDict):
    type: ModelType
    resolution: Granularity
    description: Optional[str]


class ProphetModel(CommonModel):
    model: Any


# Fit params

class FitParams(DiscriminatedTypedDict):
    dates: list[datetime]
    values: list[float]
    resolution: Granularity


# Predict params and result

class PredictParams(DiscriminatedTypedDict):
    pass


class ProphetModelPredictParams(PredictParams):
    forecast_periods: int
    resolution: Granularity


class PredictResult(DiscriminatedTypedDict):
    training_dates: list[datetime]
    training_values: list[float]
    predict_dates: list[datetime]
    predict_values: list[float]


# Test params and result

class TestParams(DiscriminatedTypedDict):
    training_dates: list[datetime]
    training_values: list[float]
    expected_dates: list[datetime]
    expected_values: list[float]
    resolution: Granularity


class ProphetModelTestParams(TestParams):
    pass


class TestResult(DiscriminatedTypedDict):
    training_dates: list[datetime]
    training_values: list[float]
    predict_dates: list[datetime]
    predict_values: list[float]
    expected_values: list[float]
    resolution: Granularity


# Metrics

class TestMetrics(DiscriminatedTypedDict):
    accuracy: float
    precision: float
    mse: float
    autocorrelation: float
    mae: float
    lb_stat: float
    lb_sq_stat: float
