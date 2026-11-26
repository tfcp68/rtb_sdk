from ortools.linear_solver import pywraplp

from rtb_sdk.schemas.auction_schemas import AdId
from rtb_sdk.schemas.balancer_schemas import RequestFlow, BalanceResult
from rtb_sdk.errors.balancer import BalancerError, ErrorCodes
from rtb_sdk.constants.balancer_constants import LP_LOWER_BOUND, MAX_MONEY, LP_UNIT_COEFF
from rtb_sdk.helpers.balancer import (
    get_category_tags,
    get_category_probability,
)
from rtb_sdk.balancer.utils.report import prepare_result


# GLOP parameters (text proto GlopParameters). The default pricing rule
# STEEPEST_EDGE is more expensive per iteration; DEVEX gives ~18-19% speedup of solver.Solve() on
# large problems (≥0.5M variables) without loss of accuracy.
GLOP_SOLVER_PARAMS = 'optimization_rule: DEVEX feasibility_rule: DEVEX'


def create_solver(threads: int) -> pywraplp.Solver:
    """Creates a GLOP LP solver with the given number of threads.

    Applies DEVEX pricing (GLOP_SOLVER_PARAMS) — speeds up solve on large
    problems without changing the result.

    Args:
        threads (int): Number of threads for the solver.

    Returns:
        pywraplp.Solver: Initialized GLOP solver.

    Raises:
        BalancerError: If the solver could not be created.

    """
    solver = pywraplp.Solver.CreateSolver('GLOP')
    if not solver:
        raise BalancerError(
            ErrorCodes.COMPUTATION_ERROR,
            'Solver not created.',
        )
    solver.SetSolverSpecificParametersAsString(GLOP_SOLVER_PARAMS)
    solver.SetNumThreads(threads)
    return solver


def create_category_variables(
    solver: pywraplp.Solver,
    ad_categories: dict[AdId, list[RequestFlow]],
    total: int,
) -> tuple[dict[tuple, pywraplp.Variable], dict[pywraplp.Variable, tuple]]:
    """Creates LP variables for each (ad, category) pair.

    For each ad category a continuous variable
    x ∈ [0, total * P(category)] is created. The upper bound limits the "raw"
    category volume to the statistically possible traffic through all of its tags.

    Key in cat_to_x: (ad_id, tags) — a unique ad+category pair.
    x_to_cat — an inverted index, needed when forming the report.

    Args:
        solver (pywraplp.Solver): Initialized LP solver.
        ad_categories (dict[AdId, list[Category]]): Top-K categories
            for each ad.
        total (int): Total traffic volume.

    Returns:
        tuple[dict[tuple, pywraplp.Variable], dict[pywraplp.Variable, tuple]]:
            The pair (cat_to_x, x_to_cat) — forward and inverted indices
            of the variables by categories.

    """
    cat_to_x: dict[tuple, pywraplp.Variable] = {}
    x_to_cat: dict[pywraplp.Variable, tuple] = {}

    for ad_id, categories in ad_categories.items():
        for category in categories:
            tags = get_category_tags(category)
            prob = get_category_probability(category)
            key = (ad_id, tags)
            upper = total * prob
            name = f'({ad_id} {tags})'

            x = solver.NumVar(LP_LOWER_BOUND, upper, name)
            cat_to_x[key] = x
            x_to_cat[x] = (ad_id, category)

    return cat_to_x, x_to_cat


def build_ad_constraints(
    solver: pywraplp.Solver,
    ad_categories: dict[AdId, list[RequestFlow]],
    cat_to_x: dict[tuple, pywraplp.Variable],
    ads_min_vol: dict[AdId, float],
    ads_real_max_vol: dict[AdId, float],
    ads_probs: dict[AdId, float],
    ads_by_cat_probs: dict[AdId, float],
) -> list[pywraplp.Constraint]:
    """Builds the traffic volume constraints for each ad.

    For each ad adds the constraint:
        min_vol ≤ Σ k·x_cat ≤ max_vol,
    where k = P(ad) / Σ P(category) is the normalizing coefficient
    that converts the "raw" variables x into the real traffic volume.

    The sum Σ x_cat is not directly equal to the real volume: only the
    top-K categories enter the LP, covering the share α = Σ P(cat) / P(ad) ≤ 1 of the probability
    space of the ad, and k = 1/α restores the scale. (The categories themselves
    are disjoint and do not overlap — the reason is precisely the truncation to top-K.)

    Args:
        solver (pywraplp.Solver): Initialized LP solver.
        ad_categories (dict[AdId, list[Category]]): Top-K categories
            for each ad.
        cat_to_x (dict[tuple, pywraplp.Variable]): Index of variables
            by the pair (ad_id, tags).
        ads_min_vol (dict[AdId, float]): Minimum volume for each
            ad (from the campaign settings).
        ads_real_max_vol (dict[AdId, float]): Maximum allowed
            volume taking the total traffic into account.
        ads_probs (dict[AdId, float]): P(ad) — probability that a
            request falls into the ad.
        ads_by_cat_probs (dict[AdId, float]): Σ P(category) — sum of the
            probabilities of the ad's selected categories.

    Returns:
        list[pywraplp.Constraint]: List of the added constraints.

    """

    result = []
    for ad, categories in ad_categories.items():
        min_vol = ads_min_vol.get(ad, LP_LOWER_BOUND)

        # absence of a key = ad without an upper volume limit
        max_vol = ads_real_max_vol.get(ad, solver.infinity())
        constraint = solver.RowConstraint(min_vol, max_vol, f'ad[name={ad}]')

        # k = P(ad)/ΣP(cat): converts "raw" x into the real traffic volume
        k = ads_probs[ad] / ads_by_cat_probs[ad]
        for category in categories:
            x = cat_to_x[(ad, get_category_tags(category))]
            constraint.SetCoefficient(x, k)

        result.append(constraint)
    return result


def build_category_constraints(
    solver: pywraplp.Solver,
    total: int,
    ad_categories: dict[AdId, list[RequestFlow]],
    cat_to_x: dict[tuple, pywraplp.Variable],
    ads_probs: dict[AdId, float],
    ads_by_cat_probs: dict[AdId, float],
) -> list[pywraplp.Constraint]:
    """Builds the traffic volume constraints for each category (cell).

    Each category is a full cell of the request space: exactly one tag
    from each dictionary. Cells are mutually disjoint, so the total
    real volume assigned to a cell by all ads cannot exceed
    the number of requests physically falling into it:

        Σ (k · x_cat) ≤ total · P(category),

    where the sum is taken over all (ad, cat) pairs with the given cell,
    and k = P(ad) / Σ P(category) is the normalizing coefficient.

    Different ads can share one cell. Grouping is done by
    the canonical key frozenset(tags).

    Args:
        solver (pywraplp.Solver): Initialized LP solver.
        total (int): Total traffic volume.
        ad_categories (dict[AdId, list[Category]]): Top-K categories
            for each ad.
        cat_to_x (dict[tuple, pywraplp.Variable]): Index of variables
            by the pair (ad_id, tags).
        ads_probs (dict[AdId, float]): P(ad) for each ad.
        ads_by_cat_probs (dict[AdId, float]): Σ P(category) for each
            ad.

    Returns:
        list[pywraplp.Constraint]: List of the added constraints.

    """
    # k = P(ad)/ΣP(cat) per ad: once instead of recomputing for each
    # (ad, cell) pair in the loop below
    k_by_ad = {ad: ads_probs[ad] / ads_by_cat_probs[ad] for ad in ad_categories}

    # canonical cell key -> (P(cell), list of (ad, tags) pairs for this cell)
    cells: dict[frozenset, tuple[float, list[tuple]]] = {}
    for ad, categories in ad_categories.items():
        for category in categories:
            tags = get_category_tags(category)
            key = frozenset(tags)
            if key not in cells:
                # P(cell) is the same for all ads with this cell, take it from the first
                cells[key] = (get_category_probability(category), [])
            cells[key][1].append((ad, tags))

    result = []
    for key, (prob, members) in cells.items():
        # P(cell)·total — the physical ceiling of traffic through the cell
        cell_volume = total * prob
        constraint = solver.RowConstraint(LP_LOWER_BOUND, cell_volume, f'cat[{sorted(key)}]')

        for ad, tags in members:
            # the entire volume k·x of the (ad, cat) pair falls on this cell
            constraint.SetCoefficient(cat_to_x[(ad, tags)], k_by_ad[ad])

        result.append(constraint)
    return result


def build_total_volume_constraint(
    solver: pywraplp.Solver,
    total: int,
    ad_categories: dict[AdId, list[RequestFlow]],
    cat_to_x: dict[tuple, pywraplp.Variable],
    ads_probs: dict[AdId, float],
    ads_by_cat_probs: dict[AdId, float],
) -> pywraplp.Constraint:
    """Builds the global constraint on the total traffic volume.

    Guarantees that the total traffic across all ads does not exceed
    the available volume: Σ k·x_cat ≤ total.
    The same coefficient k is used as in the per-ad constraints.

    Args:
        solver (pywraplp.Solver): Initialized LP solver.
        total (int): Total traffic volume.
        ad_categories (dict[AdId, list[Category]]): Top-K categories
            for each ad.
        cat_to_x (dict[tuple, pywraplp.Variable]): Index of variables
            by the pair (ad_id, tags).
        ads_probs (dict[AdId, float]): P(ad) for each ad.
        ads_by_cat_probs (dict[AdId, float]): Σ P(category) for each
            ad.

    Returns:
        pywraplp.Constraint: The added global constraint.

    """
    constraint = solver.RowConstraint(LP_LOWER_BOUND, float(total), 'total_volume')

    for ad, categories in ad_categories.items():
        # the same k = P(ad)/ΣP(cat) as in build_ad_constraints
        k = ads_probs[ad] / ads_by_cat_probs[ad]
        for category in categories:
            x = cat_to_x[(ad, get_category_tags(category))]
            constraint.SetCoefficient(x, k)

    return constraint


def solve_pywraplp(
    ad_categories: dict[AdId, list[RequestFlow]],
    total: int,
    ads_probs: dict[AdId, float],
    ads_by_cat_probs: dict[AdId, float],
    ads_min_vol: dict[AdId, float],
    ads_real_max_vol: dict[AdId, float],
    ad_prices: dict[AdId, float],
    objective: str,
    n_threads: int = 1,
    solver: pywraplp.Solver | None = None,
) -> BalanceResult:
    """Builds, solves and extracts the LP element-wise via pywraplp (fallback path).

    Merged loop (P6): a single pass over categories creates the variables and accumulates
    data for all constraints and the objective function, then builds the constraints
    in batches. Extraction — via prepare_result. Equivalent to the proto path
    (solve_proto) in result, but without MPModelProto — for debugging or
    in case of proto-API incompatibility.

    Args:
        ad_categories: Top-K categories for each ad.
        total: Total traffic volume.
        ads_probs: P(ad) for each ad.
        ads_by_cat_probs: Σ P(category) for each ad.
        ads_min_vol: Minimum volume for each ad.
        ads_real_max_vol: Maximum real volume for each ad.
        ad_prices: Price per impression for each ad.
        objective: Optimization mode (MAX_MONEY or other → MAX_VOLUME).
        n_threads: Number of threads for the freshly created GLOP solver
            (used only if solver is not passed).
        solver: Injection point for tests. None by default — the function itself
            creates a fresh empty GLOP solver and does not mutate an external object.

    Returns:
        BalanceResult: {ad_id: volume} (without ads that have no categories — they
            are added by the calling optimize).

    """
    if solver is None:
        solver = create_solver(n_threads)

    cat_to_x: dict[tuple, pywraplp.Variable] = {}
    k_by_ad: dict[AdId, float] = {}
    ad_var_pairs: dict[AdId, list[tuple[pywraplp.Variable, float]]] = {}
    cells: dict[frozenset, tuple[float, list[tuple[AdId, tuple]]]] = {}
    obj_pairs: list[tuple[pywraplp.Variable, float]] = []

    for ad_id, categories in ad_categories.items():
        k = ads_probs[ad_id] / ads_by_cat_probs[ad_id]
        k_by_ad[ad_id] = k
        obj_coeff = ad_prices.get(ad_id, LP_LOWER_BOUND) if objective == MAX_MONEY else LP_UNIT_COEFF
        ad_var_pairs[ad_id] = []

        for category in categories:
            tags = get_category_tags(category)
            prob = get_category_probability(category)
            upper = total * prob
            name = f'({ad_id} {tags})'

            x = solver.NumVar(LP_LOWER_BOUND, upper, name)
            cat_to_x[(ad_id, tags)] = x

            # for the ad constraint
            ad_var_pairs[ad_id].append((x, k))

            # for the category (cell) constraint
            key = frozenset(tags)
            if key not in cells:
                cells[key] = (prob, [])
            cells[key][1].append((ad_id, tags))

            # for the objective function
            obj_pairs.append((x, obj_coeff))

    # --- batch constraints ---
    for ad_id in ad_categories:
        min_v = ads_min_vol.get(ad_id, LP_LOWER_BOUND)
        max_v = ads_real_max_vol.get(ad_id, solver.infinity())
        constraint = solver.RowConstraint(min_v, max_v, f'ad[name={ad_id}]')
        for x, coeff in ad_var_pairs[ad_id]:
            constraint.SetCoefficient(x, coeff)

    for key, (prob, members) in cells.items():
        cell_volume = total * prob
        constraint = solver.RowConstraint(LP_LOWER_BOUND, cell_volume, f'cat[{sorted(key)}]')
        for ad_id, tags in members:
            constraint.SetCoefficient(cat_to_x[(ad_id, tags)], k_by_ad[ad_id])

    # The global constraint Σ k·x ≤ total is NOT added: redundant (Σ P(cell) ≤ 1
    # ⇒ the sum of cell constraints already gives Σ k·x ≤ total). Revenue does not change;
    # the vertex among alternative optima may differ. See proto_solver.
    # Uncomment for deterministic pinning of per-ad volumes:
    # total_constraint = solver.RowConstraint(LP_LOWER_BOUND, float(total), 'total_volume')
    # for pairs in ad_var_pairs.values():
    #     for x, coeff in pairs:
    #         total_constraint.SetCoefficient(x, coeff)

    obj = solver.Objective()
    for x, coeff in obj_pairs:
        obj.SetCoefficient(x, coeff)
    obj.SetMaximization()

    status = solver.Solve()
    return prepare_result(solver, status, ad_categories, cat_to_x, ads_probs, ads_by_cat_probs)

