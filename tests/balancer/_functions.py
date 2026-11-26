"""
Registry of the balancer functions under test.

FUNCTIONS: {func_name: (func, unpacker | None)}
  func     — the function under test
  unpacker — takes a raw case (dict) and returns a case with ready objects;
             None for functions accepting only plain-dict arguments.

All public balancer functions work with plain dicts (TypedDict),
so most unpackers are not needed.
"""

from rtb_sdk.balancer.balancer import (
    balance_traffic,
    add_new_balanced_campaign,
    predict_rebalance,
    convert_report_to_auction_data,
    auction as balancer_auction,
)
from rtb_sdk.balancer.utils.categories import (
    choose_top_categories_by_probability,
)
from rtb_sdk.balancer.functions.optimize import optimize
from rtb_sdk.balancer.functions.balance_by_sellout import balance_by_sellout
from rtb_sdk.balancer.seasonal import (
    seasonal_balance_traffic,
    seasonal_balance_by_sellout,
    seasonal_add_new_balanced_campaign,
    open_balance_traffic,
)

from datetime import datetime


# ---------------------------------------------------------------------------
# Unpackers (raw JSON → ready objects)
# ---------------------------------------------------------------------------

def _unpack_seasonal(case: dict) -> dict:
    """Prepares a Level-3 function case (seasonal_*/open_*) for running.

    JSON cannot store datetime and int keys, so the unpacker:
      * params.period.period_start / period_end: ISO string → datetime;
      * params.seasonal_context.context: string hour keys → int;
      * ads[*].start_date / end_date: ISO string → datetime (for the activity window).
    """
    params = case["input"]["params"]

    period = params.get("period")
    if period is not None:
        for key in ("period_start", "period_end"):
            value = period.get(key)
            if isinstance(value, str):
                period[key] = datetime.fromisoformat(value)

    seasonal_context = params.get("seasonal_context")
    if seasonal_context is not None:
        ctx = seasonal_context.get("context")
        if isinstance(ctx, dict):
            seasonal_context["context"] = {int(h): v for h, v in ctx.items()}

    ads = case["input"].get("ads")
    if isinstance(ads, dict):
        for ad in ads.values():
            for key in ("start_date", "end_date"):
                value = ad.get(key)
                if isinstance(value, str):
                    ad[key] = datetime.fromisoformat(value)

    return case


# ---------------------------------------------------------------------------
# Mapping: function name → (function, unpacker | None)
# ---------------------------------------------------------------------------

FUNCTIONS: dict[str, tuple] = {
    "balance_traffic":                      (balance_traffic,                      None),
    "optimize":                             (optimize,                             None),
    "balance_by_sellout":                   (balance_by_sellout,                   None),
    "add_new_balanced_campaign":            (add_new_balanced_campaign,            None),
    "predict_rebalance":                    (predict_rebalance,                    None),
    "convert_report_to_auction_data":       (convert_report_to_auction_data,       None),
    "balancer_auction":                     (balancer_auction,                     None),
    "choose_top_categories_by_probability": (choose_top_categories_by_probability, None),
    "seasonal_balance_traffic":             (seasonal_balance_traffic,             _unpack_seasonal),
    "seasonal_balance_by_sellout":          (seasonal_balance_by_sellout,          _unpack_seasonal),
    "seasonal_add_new_balanced_campaign":   (seasonal_add_new_balanced_campaign,   _unpack_seasonal),
    "open_balance_traffic":                 (open_balance_traffic,                 _unpack_seasonal),
}
