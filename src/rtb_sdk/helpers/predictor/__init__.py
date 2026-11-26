"""
Public API of helpers/predictor — helpers for working with the predictor schemas.
"""
from auto_all import start_all, end_all

start_all()

from .helpers_utils import is_in_class
from rtb_sdk.constants.frequencies_consts import TIMEDELTA_TO_GRAN
from .helpers_model_options import (
    get_model_options_model_type,
    is_valid_model_options,
    create_model_options,
    create_model_options_from_dict,
)
from .helpers_common_model import (
    get_common_model_type,
    get_common_model_resolution,
    get_common_model_description,
    is_valid_common_model,
)
from .helpers_fit_params import (
    get_fit_params_dates,
    get_fit_params_values,
    get_fit_params_resolution,
    is_valid_fit_params,
    create_fit_params,
    create_fit_params_from_dict,
    create_from_timedelta,
    create_fit_params_from_polars_df,
    fit_params_to_polars,
)
from .helpers_predict_params import is_valid_predict_params
from .helpers_predict_result import (
    get_predict_result_training_dates,
    get_predict_result_training_values,
    get_predict_result_predict_dates,
    get_predict_result_predict_values,
    is_valid_predict_result,
    create_predict_result,
    create_predict_result_from_dict,
)
from .helpers_test_params import (
    get_test_params_training_dates,
    get_test_params_training_values,
    get_test_params_expected_dates,
    get_test_params_expected_values,
    get_test_params_resolution,
    is_valid_test_params,
    create_test_params,
    create_test_params_from_dict,
)
from .helpers_test_result import (
    get_test_result_training_dates,
    get_test_result_training_values,
    get_test_result_predict_dates,
    get_test_result_predict_values,
    get_test_result_expected_values,
    get_test_result_resolution,
    is_valid_test_result,
    create_test_result,
    create_test_result_from_dict,
)
from .helpers_test_metrics import (
    get_test_metrics_accuracy,
    get_test_metrics_precision,
    get_test_metrics_mse,
    get_test_metrics_autocorrelation,
    get_test_metrics_mae,
    get_test_metrics_lb_stat,
    get_test_metrics_lb_sq_stat,
    is_valid_test_metrics,
    create_test_metrics,
    create_test_metrics_from_dict,
)
from .serialization import (
    serialize_model_options,
    deserialize_model_options,
    serialize_common_model,
    deserialize_common_model,
    serialize_fit_params,
    deserialize_fit_params,
    serialize_predict_result,
    deserialize_predict_result,
    serialize_test_result,
    deserialize_test_result,
    serialize_test_metrics,
    deserialize_test_metrics,
)
from .metrics import calc_metrics
from .models.prophet_model import (
    # Seasonality (Prophet sub-schema)
    get_seasonality_name,
    get_seasonality_period,
    get_seasonality_fourier_order,
    is_valid_seasonality,
    create_seasonality,
    create_seasonality_from_dict,
    serialize_seasonality,
    deserialize_seasonality,
    # ProphetOptions
    get_prophet_options_growth,
    get_prophet_options_changepoint_prior_scale,
    get_prophet_options_seasonality_mode,
    get_prophet_options_seasonality_prior_scale,
    get_prophet_options_yearly_seasonality,
    get_prophet_options_weekly_seasonality,
    get_prophet_options_n_changepoints,
    get_prophet_options_changepoint_range,
    get_prophet_options_seasonalities,
    get_prophet_options_model_type,
    get_seasonalities_items,
    is_valid_prophet_options,
    create_prophet_options,
    create_prophet_options_from_dict,
    serialize_prophet_options,
    deserialize_prophet_options,
    # ProphetModel
    get_prophet_model_type,
    get_prophet_model_resolution,
    get_prophet_model_description,
    get_prophet_model_model,
    is_valid_prophet_model,
    create_prophet_model,
    create_prophet_model_from_dict,
    serialize_prophet_model,
    deserialize_prophet_model,
    # ProphetModelPredictParams
    get_prophet_model_predict_params_resolution,
    get_prophet_model_predict_params_forecast_periods,
    is_valid_prophet_model_predict_params,
    create_prophet_model_predict_params,
    create_prophet_model_predict_params_from_dict,
    serialize_prophet_model_predict_params,
    deserialize_prophet_model_predict_params,
    # ProphetModelTestParams
    get_prophet_model_test_params_training_dates,
    get_prophet_model_test_params_training_values,
    get_prophet_model_test_params_expected_dates,
    get_prophet_model_test_params_expected_values,
    get_prophet_model_test_params_resolution,
    is_valid_prophet_model_test_params,
    create_prophet_model_test_params,
    create_prophet_model_test_params_from_dict,
    serialize_prophet_model_test_params,
    deserialize_prophet_model_test_params,
)
from .dispatch import (
    serialize_options,
    deserialize_options,
    serialize_model,
    deserialize_model,
    serialize_predict_params,
    deserialize_predict_params,
    serialize_test_params,
    deserialize_test_params,
)

end_all()
