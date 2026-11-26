"""
Prophet options helpers by schema:
  - `Seasonality` — description of a seasonal component (used inside
    `ProphetOptions.seasonalities`);
  - `ProphetOptions` — Prophet model options.

Each schema is organized uniformly: getters → per-field validators →
`CheckList` → `_check_fields_*` → `is_valid_*` → builders → ser/de.
Low-level utilities are imported from `helpers.predictor.helpers`.
"""
from typing import Any, cast

from rtb_sdk.schemas import (
    ProphetOptions,
    GrowthNameType,
    SeasonalityModeType,
    SeasonalityNameType,
    ModelType,
    Seasonality,
)
from rtb_sdk.constants import (
    GrowthName,
    SeasonalityMode,
    SeasonalityName,
    ModelTypeName,
)
from rtb_sdk.constants.data_types import DataPredictorType
from rtb_sdk.helpers.type_helpers import check_predictor_type
from rtb_sdk.helpers.predictor.helpers_utils import is_in_class
from rtb_sdk.helpers.predictor.serialization import _dumps, _loads
from rtb_sdk.errors.predictor import PredictorError, ErrorCodes


# ─── Seasonality ───────────────────────────────────────────────────────────────

def get_seasonality_name(seasonality: Seasonality,
                         default: SeasonalityNameType | None = None
                         ) -> SeasonalityNameType | None:
    return seasonality.get("name", default)


def get_seasonality_period(seasonality: Seasonality,
                           default: float | None = None
                           ) -> float | None:
    return seasonality.get("period", default)


def get_seasonality_fourier_order(seasonality: Seasonality,
                                  default: int | None = None
                                  ) -> int | None:
    return seasonality.get("fourier_order", default)


def _is_valid_seasonality_name(seasonality: Seasonality) -> bool:
    if not check_predictor_type(seasonality, DataPredictorType.SEASONALITY):
        return False
    name = get_seasonality_name(seasonality)
    if not isinstance(name, str):
        return False
    return is_in_class(SeasonalityName, name)


def _is_valid_seasonality_period(seasonality: Seasonality) -> bool:
    if not check_predictor_type(seasonality, DataPredictorType.SEASONALITY):
        return False
    period = get_seasonality_period(seasonality)
    if not isinstance(period, float):
        return False
    return period > 0


def _is_valid_seasonality_fourier_order(seasonality: Seasonality) -> bool:
    if not check_predictor_type(seasonality, DataPredictorType.SEASONALITY):
        return False
    fourier_order = get_seasonality_fourier_order(seasonality)
    if not isinstance(fourier_order, int):
        return False
    return fourier_order > 0


CheckSeasonalityList = [
    _is_valid_seasonality_name,
    _is_valid_seasonality_period,
    _is_valid_seasonality_fourier_order,
]


def _check_fields_seasonality(seasonality: Seasonality) -> bool:
    for check in CheckSeasonalityList:
        if not check(seasonality):
            return False
    return True


def is_valid_seasonality(seasonality: Any) -> bool:
    if not check_predictor_type(seasonality, DataPredictorType.SEASONALITY):
        return False
    return _check_fields_seasonality(seasonality)


def create_seasonality(name: SeasonalityNameType,
                       period: float,
                       fourier_order: int,
                       **kwargs) -> Seasonality:
    result = {
        "name": name,
        "period": period,
        "fourier_order": fourier_order,
        "__type": DataPredictorType.SEASONALITY,
    }
    if is_valid_seasonality(result):
        return cast(Seasonality, result)
    raise PredictorError(
        ErrorCodes.PARAMETER_ERROR_CODE,
        "Invalid parameters for Seasonality"
    )


def create_seasonality_from_dict(data: dict[str, Any]) -> Seasonality:
    try:
        return create_seasonality(**data)
    except Exception:
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Invalid parameters for Seasonality"
        )


def serialize_seasonality(seasonality: Seasonality) -> str:
    if not is_valid_seasonality(seasonality):
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Invalid parameters for Seasonality"
        )
    return _dumps(seasonality)


def deserialize_seasonality(data: str) -> Seasonality:
    raw = _loads(data)
    if not isinstance(raw, dict):
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Invalid parameters for Seasonality"
        )
    return create_seasonality_from_dict(raw)


# ─── ProphetOptions ────────────────────────────────────────────────────────────

def get_prophet_options_growth(options: ProphetOptions,
                               default: GrowthNameType | None = None
                               ) -> GrowthNameType | None:
    return options.get("growth", default)


def get_prophet_options_changepoint_prior_scale(options: ProphetOptions,
                                                default: float | None = None
                                                ) -> float | None:
    return options.get("changepoint_prior_scale", default)


def get_prophet_options_seasonality_mode(options: ProphetOptions,
                                         default: SeasonalityModeType | None = None
                                         ) -> SeasonalityModeType | None:
    return options.get("seasonality_mode", default)


def get_prophet_options_seasonality_prior_scale(options: ProphetOptions,
                                                default: float | None = None
                                                ) -> float | None:
    return options.get("seasonality_prior_scale", default)


def get_prophet_options_yearly_seasonality(options: ProphetOptions,
                                           default: bool | None = None
                                           ) -> bool | None:
    return options.get("yearly_seasonality", default)


def get_prophet_options_weekly_seasonality(options: ProphetOptions,
                                           default: bool | None = None
                                           ) -> bool | None:
    return options.get("weekly_seasonality", default)


def get_prophet_options_n_changepoints(options: ProphetOptions,
                                       default: int | None = None
                                       ) -> int | None:
    return options.get("n_changepoints", default)


def get_prophet_options_changepoint_range(options: ProphetOptions,
                                          default: float | None = None
                                          ) -> float | None:
    return options.get("changepoint_range", default)


def get_prophet_options_seasonalities(options: ProphetOptions,
                                      default: dict[SeasonalityNameType, Seasonality] | None = None
                                      ) -> dict[SeasonalityNameType, Seasonality] | None:
    return options.get("seasonalities", default)


def get_prophet_options_model_type(options: ProphetOptions,
                                   default: ModelType | None = None
                                   ) -> ModelType | None:
    return options.get("model_type", default)


def get_seasonalities_items(seasonalities: dict[SeasonalityNameType, Seasonality]) -> list[Any]:
    return list(seasonalities.items())


def _is_valid_prophet_options_growth(options: ProphetOptions) -> bool:
    if not check_predictor_type(options, DataPredictorType.PROPHET_OPTIONS):
        return False
    growth = get_prophet_options_growth(options)
    if not isinstance(growth, str):
        return False
    return is_in_class(GrowthName, growth)


def _is_valid_prophet_options_changepoint_prior_scale(options: ProphetOptions) -> bool:
    if not check_predictor_type(options, DataPredictorType.PROPHET_OPTIONS):
        return False
    val = get_prophet_options_changepoint_prior_scale(options)
    if not isinstance(val, float):
        return False
    return val > 0


def _is_valid_prophet_options_seasonality_mode(options: ProphetOptions) -> bool:
    if not check_predictor_type(options, DataPredictorType.PROPHET_OPTIONS):
        return False
    seasonality_mode = get_prophet_options_seasonality_mode(options)
    if not isinstance(seasonality_mode, str):
        return False
    return is_in_class(SeasonalityMode, seasonality_mode)


def _is_valid_prophet_options_seasonality_prior_scale(options: ProphetOptions) -> bool:
    if not check_predictor_type(options, DataPredictorType.PROPHET_OPTIONS):
        return False
    val = get_prophet_options_seasonality_prior_scale(options)
    if not isinstance(val, float):
        return False
    return val > 0


def _is_valid_prophet_options_yearly_seasonality(options: ProphetOptions) -> bool:
    if not check_predictor_type(options, DataPredictorType.PROPHET_OPTIONS):
        return False
    return isinstance(get_prophet_options_yearly_seasonality(options), bool)


def _is_valid_prophet_options_weekly_seasonality(options: ProphetOptions) -> bool:
    if not check_predictor_type(options, DataPredictorType.PROPHET_OPTIONS):
        return False
    return isinstance(get_prophet_options_weekly_seasonality(options), bool)


def _is_valid_prophet_options_n_changepoints(options: ProphetOptions) -> bool:
    if not check_predictor_type(options, DataPredictorType.PROPHET_OPTIONS):
        return False
    val = get_prophet_options_n_changepoints(options)
    if not isinstance(val, int):
        return False
    return val > 0


def _is_valid_prophet_options_changepoint_range(options: ProphetOptions) -> bool:
    if not check_predictor_type(options, DataPredictorType.PROPHET_OPTIONS):
        return False
    val = get_prophet_options_changepoint_range(options)
    if not isinstance(val, (int, float)):
        return False
    return val > 0


def _is_valid_prophet_options_seasonalities(options: ProphetOptions) -> bool:
    if not check_predictor_type(options, DataPredictorType.PROPHET_OPTIONS):
        return False
    seasonalities = get_prophet_options_seasonalities(options)
    if not isinstance(seasonalities, dict):
        return False
    return all(is_in_class(SeasonalityName, k) and is_valid_seasonality(v)
               for k, v in get_seasonalities_items(seasonalities))


def _is_valid_prophet_options_model_type(options: ProphetOptions) -> bool:
    if not check_predictor_type(options, DataPredictorType.PROPHET_OPTIONS):
        return False
    model_type = get_prophet_options_model_type(options)
    if not isinstance(model_type, str):
        return False
    return is_in_class(ModelTypeName, model_type)


CheckProphetOptionsList = [
    _is_valid_prophet_options_growth,
    _is_valid_prophet_options_changepoint_prior_scale,
    _is_valid_prophet_options_seasonality_mode,
    _is_valid_prophet_options_seasonality_prior_scale,
    _is_valid_prophet_options_yearly_seasonality,
    _is_valid_prophet_options_weekly_seasonality,
    _is_valid_prophet_options_n_changepoints,
    _is_valid_prophet_options_changepoint_range,
    _is_valid_prophet_options_seasonalities,
    _is_valid_prophet_options_model_type,
]


def _check_fields_prophet_options(options: ProphetOptions) -> bool:
    for check in CheckProphetOptionsList:
        if not check(options):
            return False
    return True


def is_valid_prophet_options(options: Any) -> bool:
    if not check_predictor_type(options, DataPredictorType.PROPHET_OPTIONS):
        return False
    return _check_fields_prophet_options(options)


def create_prophet_options(growth: GrowthNameType = GrowthName.linear,
                           changepoint_prior_scale: float = 0.001,
                           seasonality_mode: SeasonalityModeType = SeasonalityMode.multiplicative,
                           seasonality_prior_scale: float = 0.05,
                           yearly_seasonality: bool = True,
                           weekly_seasonality: bool = True,
                           n_changepoints: int = 15,
                           changepoint_range: float = 0.5,
                           seasonalities: dict[SeasonalityNameType, Seasonality] | None = None,
                           model_type: ModelType = ModelTypeName.PROPHET,
                           **kwargs) -> ProphetOptions:
    if seasonalities is None:
        seasonalities = {
            SeasonalityName.monthly: create_seasonality(
                name=SeasonalityName.monthly,
                period=30.5,
                fourier_order=5,
            )
        }
    else:
        processed = {}
        for k, v in seasonalities.items():
            if isinstance(v, dict) and '__type' not in v:
                processed[k] = create_seasonality(**v)
            else:
                processed[k] = v
        seasonalities = processed

    result = {
        "growth": growth,
        "changepoint_prior_scale": changepoint_prior_scale,
        "seasonality_mode": seasonality_mode,
        "seasonality_prior_scale": seasonality_prior_scale,
        "yearly_seasonality": yearly_seasonality,
        "weekly_seasonality": weekly_seasonality,
        "n_changepoints": n_changepoints,
        "changepoint_range": changepoint_range,
        "seasonalities": seasonalities,
        "model_type": model_type,
        "__type": DataPredictorType.PROPHET_OPTIONS,
    }
    if is_valid_prophet_options(result):
        return cast(ProphetOptions, result)
    raise PredictorError(
        ErrorCodes.PARAMETER_ERROR_CODE,
        "Invalid parameters for ProphetOptions"
    )


def create_prophet_options_from_dict(data: dict[str, Any]) -> ProphetOptions:
    try:
        return create_prophet_options(**data)
    except Exception:
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Invalid parameters for ProphetOptions"
        )


def serialize_prophet_options(options: ProphetOptions) -> str:
    if not is_valid_prophet_options(options):
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Invalid parameters for ProphetOptions"
        )
    return _dumps(options)


def deserialize_prophet_options(data: str) -> ProphetOptions:
    raw = _loads(data)
    if not isinstance(raw, dict):
        raise PredictorError(
            ErrorCodes.PARAMETER_ERROR_CODE,
            "Invalid parameters for ProphetOptions"
        )
    return create_prophet_options_from_dict(raw)