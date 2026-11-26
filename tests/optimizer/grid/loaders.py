"""
Case unpackers (grid search): raw dict → typed objects to pass into the functions under test.
"""
from rtb_sdk.schemas.optimizer_schemas import SolutionList
from rtb_sdk.helpers.optimizer import (
    build_decision_variables,
    create_grid_search_options,
    build_grid_search_state,
    build_solution,
    build_solution_list,
    build_parameters,
)


def _build_estimated_candidates(candidates_raw: list) -> SolutionList:
    """Converts a raw list [{parameters: dict, estimation: float}] → SolutionList."""
    solutions = []
    for sol in candidates_raw:
        params = build_parameters(sol['parameters'])
        solutions.append(build_solution(parameters=params, estimation=sol['estimation']))
    return build_solution_list(solutions)


def _unpack_first_generate_grid(case: dict) -> dict:
    """decision_variables → DecisionVariables, options → GridSearchOptions."""
    inp = case['input']
    dv_raw = inp.get('decision_variables')
    options_raw = inp.get('options')

    if isinstance(dv_raw, dict):
        dv = build_decision_variables(dv_raw)
        inp['decision_variables'] = dv
        if isinstance(options_raw, dict):
            inp['options'] = create_grid_search_options(dv, **options_raw)

    return case


def _unpack_next_generate_grid(case: dict) -> dict:
    """decision_variables → DecisionVariables, state → GridSearchState."""
    inp = case['input']
    dv_raw = inp.get('decision_variables')
    state_raw = inp.get('state')

    if isinstance(dv_raw, dict):
        dv = build_decision_variables(dv_raw)
        inp['decision_variables'] = dv
        if isinstance(state_raw, dict):
            inp['state'] = build_grid_search_state(dv, **state_raw)

    return case


def _unpack_optimize_grid(case: dict) -> dict:
    """decision_variables → DecisionVariables, state → GridSearchState,
    estimated_candidates → SolutionList."""
    inp = case['input']
    dv_raw = inp.get('decision_variables')
    state_raw = inp.get('state')
    candidates_raw = inp.get('estimated_candidates')

    if isinstance(dv_raw, dict):
        dv = build_decision_variables(dv_raw)
        inp['decision_variables'] = dv
        if isinstance(state_raw, dict):
            inp['state'] = build_grid_search_state(dv, **state_raw)
        if isinstance(candidates_raw, list):
            inp['estimated_candidates'] = _build_estimated_candidates(candidates_raw)

    return case


def _unpack_is_optimization_done_grid(case: dict) -> dict:
    """decision_variables → DecisionVariables, state → GridSearchState."""
    inp = case['input']
    dv_raw = inp.get('decision_variables')
    state_raw = inp.get('state')

    if isinstance(dv_raw, dict):
        dv = build_decision_variables(dv_raw)
        inp['decision_variables'] = dv
        if isinstance(state_raw, dict):
            inp['state'] = build_grid_search_state(dv, **state_raw)

    return case


def _unpack_estimate_func(case: dict) -> dict:
    """candidates → SolutionList."""
    inp = case['input']
    candidates_raw = inp.get('candidates')
    if isinstance(candidates_raw, list):
        inp['candidates'] = _build_estimated_candidates(candidates_raw)
    return case


def _unpack_index_to_product(case: dict) -> dict:
    """decision_variables → DecisionVariables."""
    inp = case['input']
    dv_raw = inp.get('decision_variables')
    if isinstance(dv_raw, dict):
        inp['decision_variables'] = build_decision_variables(dv_raw)
    return case


def _unpack_product_to_index(case: dict) -> dict:
    """decision_variables → DecisionVariables."""
    inp = case['input']
    dv_raw = inp.get('decision_variables')
    if isinstance(dv_raw, dict):
        inp['decision_variables'] = build_decision_variables(dv_raw)
    return case
