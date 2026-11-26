from typing import Literal

MAX_MONEY = 'maximize_money'
MAX_VOLUME = 'maximize_volume'
MIN_CATEGORY_PROBABILITY = 1e-6

# Precision of the binary search in balance_by_sellout — a share in percent (0.1 → ε=0.001).
DEFAULT_ACCURACY_PERCENT = 0.1

DEFAULT_FUNC_REPLACE_INFINITY = None

OBJECTIVES = Literal['maximize_money', 'maximize_volume']

LP_LOWER_BOUND = 0.0
LP_UNIT_COEFF = 1.0

# Ad.volume=0 per the spec means "no upper limit";
# stored in InnerAd.max_vol as this large number instead of 0,
# so as not to conflict with "frozen volume = 0" in add_new_balanced_campaign.
MAX_VOL_UNLIMITED = 10 ** 9
