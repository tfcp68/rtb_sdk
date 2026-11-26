from typing import Any

from rtb_sdk.constants.data_types import DataPredictorType
from rtb_sdk.helpers.type_helpers import check_predictor_type


# ─── PredictParams ─────────────────────────────────────────────────────────────

def is_valid_predict_params(data: Any) -> bool:
    return (check_predictor_type(data, DataPredictorType.PREDICT_PARAMS)
            or check_predictor_type(data, DataPredictorType.PROPHET_MODEL_PREDICT_PARAMS))
