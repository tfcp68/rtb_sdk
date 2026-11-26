from ortools.linear_solver import pywraplp, linear_solver_pb2 as pb

from rtb_sdk.schemas.auction_schemas import AdId
from rtb_sdk.schemas.balancer_schemas import RequestFlow, BalanceResult
from rtb_sdk.constants.balancer_constants import LP_LOWER_BOUND, MAX_MONEY
from rtb_sdk.errors.balancer import BalancerError, ErrorCodes
from rtb_sdk.helpers.balancer import get_category_tags, get_category_probability
from rtb_sdk.balancer.solver.solver import create_solver
import math


INF = float('inf')


def build_proto_model(
    ad_categories: dict[AdId, list[RequestFlow]],
    total: int,
    ads_probs: dict[AdId, float],
    ads_by_cat_probs: dict[AdId, float],
    ads_min_vol: dict[AdId, float],
    ads_real_max_vol: dict[AdId, float],
    ad_prices: dict[AdId, float],
    objective: str,
) -> tuple[pb.MPModelProto, dict[AdId, list[int]], dict[AdId, float]]:
    """Builds the LP model via MPModelProto (batch assembly, no per-element FFI).

    Returns the tuple (model, ad_var_indices, k_by_ad):
      - model: filled MPModelProto, ready for solver.LoadModelFromProto()
      - ad_var_indices: {ad_id: [variable indices]} for bulk extraction
      - k_by_ad: {ad_id: k} normalizing coefficients for post-processing

    Builds the same variables, constraints and objective function as the chain
    create_category_variables + build_ad_constraints + build_category_constraints
    + build_total_volume_constraint + apply_objective, but directly through
    the repeated fields of MPModelProto, without per-element pywraplp FFI calls.

    Args:
        ad_categories: Top-K categories for each ad.
        total: Total traffic volume.
        ads_probs: P(ad) for each ad.
        ads_by_cat_probs: Σ P(category) for each ad.
        ads_min_vol: Minimum volume for each ad.
        ads_real_max_vol: Maximum real volume for each ad.
        ad_prices: Price per impression for each ad.
        objective: Optimization mode (MAX_MONEY or other).

    Returns:
        (model, ad_var_indices, k_by_ad) — the model, the index of variables
        by ad, the normalizing coefficients.

    """
    model = pb.MPModelProto()
    model.maximize = True

    # Normalizing coefficient k = P(ad) / Σ P(category)
    k_by_ad = {ad: ads_probs[ad] / ads_by_cat_probs[ad] for ad in ad_categories}

    # var_ad[i] → ad_id (needed when building cell constraints)
    var_ad: list[AdId] = []
    # cells: frozenset(tags) → (P(cell), [var_index, ...])
    cells: dict[frozenset, tuple[float, list[int]]] = {}
    # ad_id → [variable indices]
    ad_var_indices: dict[AdId, list[int]] = {}
    add_var = model.variable.add
    idx = 0

    for ad, categories in ad_categories.items():
        price = ad_prices.get(ad, LP_LOWER_BOUND)
        coeff = price if objective == MAX_MONEY else 1.0
        ad_list = ad_var_indices.setdefault(ad, [])
        for cat in categories:
            tags = get_category_tags(cat)
            prob = get_category_probability(cat)

            v = add_var()
            v.lower_bound = LP_LOWER_BOUND
            v.upper_bound = total * prob
            v.objective_coefficient = coeff

            var_ad.append(ad)
            ad_list.append(idx)

            key = frozenset(tags)  # canonical cell key
            cell = cells.get(key)
            if cell is None:
                cells[key] = (prob, [idx])
            else:
                cell[1].append(idx)

            idx += 1

    # --- Per-ad constraints: min_vol ≤ Σ k·x ≤ max_vol ---
    for ad, var_idxs in ad_var_indices.items():
        k = k_by_ad[ad]
        c = model.constraint.add()
        c.lower_bound = ads_min_vol.get(ad, LP_LOWER_BOUND)
        c.upper_bound = ads_real_max_vol.get(ad, INF)
        c.var_index.extend(var_idxs)
        c.coefficient.extend([k] * len(var_idxs))

    # --- Cell constraints: Σ k·x ≤ total·P(cell) ---
    # The global ceiling Σ k·x ≤ total is NOT added: it is mathematically redundant.
    # Cells are disjoint, Σ P(cell) ≤ 1, so the sum of all cell constraints
    # already gives Σ k·x ≤ total·Σ P(cell) ≤ total. The extra dense row (the worst for
    # the simplex) was removed. The feasible region and the maximum revenue do NOT change (rel. diff ~1e-16).
    # NB: among alternative optima the vertex may differ — on degenerate
    # instances the per-ad volume flows between a pair of ads while Σvol and revenue are preserved.
    for key, (prob, members) in cells.items():
        c = model.constraint.add()
        c.lower_bound = LP_LOWER_BOUND
        c.upper_bound = total * prob
        c.var_index.extend(members)
        c.coefficient.extend([k_by_ad[var_ad[i]] for i in members])

    # --- Global constraint Σ k·x ≤ total (OFF by default, redundant) ---
    # Uncomment if you need a deterministic vertex pinning among
    # alternative optima (stability of per-ad volumes) at the cost of one dense row.
    # c = model.constraint.add()
    # c.lower_bound = LP_LOWER_BOUND
    # c.upper_bound = float(total)
    # for ad, var_idxs in ad_var_indices.items():
    #     k = k_by_ad[ad]
    #     c.var_index.extend(var_idxs)
    #     c.coefficient.extend([k] * len(var_idxs))

    return model, ad_var_indices, k_by_ad


def solve_proto(
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
    """Builds, solves and extracts the LP via MPModelProto (batch path, default).

    Model assembly — build_proto_model (no per-element FFI), loading with a single
    LoadModelFromProto, extracting the solution at once via FillSolutionResponseProto.
    ~×2 on assembly and ~×3-4 on extraction versus the element-wise solve_pywraplp,
    the result is revenue-equivalent.

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

    Raises:
        BalancerError: If the solution is not OPTIMAL (NO_SOLUTION).

    """
    if solver is None:
        solver = create_solver(n_threads)

    model, ad_var_indices, k_by_ad = build_proto_model(
        ad_categories, total, ads_probs, ads_by_cat_probs,
        ads_min_vol, ads_real_max_vol, ad_prices, objective,
    )
    solver.LoadModelFromProto(model)
    status = solver.Solve()

    # prepare_result accepts only OPTIMAL; we keep the same contract
    if status != pywraplp.Solver.OPTIMAL:
        raise BalancerError(ErrorCodes.NO_SOLUTION, 'No optimal solution found.')

    # bulk extraction: the whole variable_value as a single array
    resp = pb.MPSolutionResponse()
    solver.FillSolutionResponseProto(resp)
    values = resp.variable_value

    # GLOP through the proto interface may return OPTIMAL with an empty/incomplete solution
    # vector if the model contains a contradictory constraint (lower_bound > upper_bound,
    # e.g. min_vol above the real volume ceiling real_max). The status then stays
    # OPTIMAL, so the check above does not fire, and extraction would fail with an IndexError.
    # We treat an incomplete solution as no solution — the same NO_SOLUTION contract
    # that the pywraplp backend gives on "contradictory bounds".
    if len(values) < len(model.variable):
        raise BalancerError(ErrorCodes.NO_SOLUTION, 'No optimal solution found.')

    result: BalanceResult = {}
    for ad, var_idxs in ad_var_indices.items():
        k = k_by_ad[ad]
        s = 0.0
        for idx in var_idxs:
            s += values[idx]
        result[ad] = int(math.floor(k * s))
    return result
