"""
Wrappers around the functions under test (grid search) — return simple, easily comparable values.
"""
from rtb_sdk.optimizer import first_generate, next_generate, optimize
from rtb_sdk.helpers.optimizer import estimate_func
from rtb_sdk.optimizer.grid_search.grid_search import index_to_product


def _first_generate_grid(decision_variables, options):
    """Returns {'n_candidates': int, 'state_index': int}."""
    candidates, state = first_generate(decision_variables=decision_variables, options=options)
    solutions = candidates.get('solution_list', [])
    return {
        'n_candidates': len(solutions),
        'state_index': state.get('index'),
    }


def _next_generate_grid(decision_variables, state):
    """Returns {'n_candidates': int, 'state_index': int}."""
    candidates, new_state = next_generate(decision_variables=decision_variables, state=state)
    solutions = candidates.get('solution_list', [])
    return {
        'n_candidates': len(solutions),
        'state_index': new_state.get('index'),
    }


def _optimize_grid(decision_variables, estimated_candidates, state):
    """Returns {'estimation': float, 'parameters': dict}."""
    result, _ = optimize(
        decision_variables=decision_variables,
        estimated_candidates=estimated_candidates,
        state=state,
    )
    params = result.get('parameters', {}).get('parameters', {})
    return {
        'estimation': result.get('estimation'),
        'parameters': params,
    }


_EQUATIONS = {
    "x_squared":  lambda p: float(p["x"] ** 2),
    "x_plus_y":   lambda p: float(p["x"] + p["y"]),
    "constant_1": lambda p: 1.0,
}


def _estimate_func_wrapper(candidates, equation):
    """Returns the list of scores after applying the equation to all candidates."""
    result_sl = estimate_func(candidates, _EQUATIONS[equation])
    return [s.get("estimation") for s in result_sl.get("solution_list", [])]


def _index_to_product_wrapper(decision_variables, index):
    """Returns the combination by index as a list (tuple → list for JSON)."""
    return list(index_to_product(decision_variables, index))
