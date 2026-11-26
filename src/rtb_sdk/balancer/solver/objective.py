from ortools.linear_solver import pywraplp

from rtb_sdk.schemas.auction_schemas import AdId
from rtb_sdk.schemas.balancer_schemas import RequestFlow
from rtb_sdk.constants.balancer_constants import MAX_MONEY, LP_LOWER_BOUND, LP_UNIT_COEFF
from rtb_sdk.helpers.balancer import get_category_tags


def apply_objective(
    solver: pywraplp.Solver,
    objective: str,
    ad_categories: dict[AdId, list[RequestFlow]],
    cat_to_x: dict[tuple, pywraplp.Variable],
    ad_prices: dict[AdId, float],
) -> None:
    """Sets the objective function of the LP problem.

    Supports two maximization modes:
    - MAX_MONEY: revenue maximization — the variable's coefficient equals the ad's
      price.
    - MAX_VOLUME: maximization of total traffic — the coefficient equals
      LP_UNIT_COEFF for all variables.

    The real volume ≈ k·x, but k is the same for all categories of one ad,
    so for relative optimization the coefficient k can be omitted.

    Args:
        solver (pywraplp.Solver): Initialized LP solver.
        objective (str): Optimization mode — the MAX_MONEY constant or
            any other value (treated as MAX_VOLUME).
        ad_categories (dict[AdId, list[Category]]): Top-K categories
            for each ad.
        cat_to_x (dict[tuple, pywraplp.Variable]): Index of variables
            by the pair (ad_id, tags).
        ad_prices (dict[AdId, float]): Price per impression for each ad
            (used only in MAX_MONEY mode).

    Returns:
        None

    """
    obj = solver.Objective()

    for ad, categories in ad_categories.items():
        coeff = ad_prices.get(ad, LP_LOWER_BOUND) if objective == MAX_MONEY else LP_UNIT_COEFF
        for category in categories:
            x = cat_to_x[(ad, get_category_tags(category))]
            obj.SetCoefficient(x, coeff)

    obj.SetMaximization()
