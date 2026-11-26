"""
Case unpackers (genetic search): raw dict → typed objects to pass into the functions under test.
"""
from rtb_sdk.helpers.optimizer import (
    build_decision_variables,
    create_genetic_search_options,
    build_genetic_search_state,
    build_parameters,
)

from ..grid.loaders import _build_estimated_candidates


def _unpack_first_generate_genetic(case: dict) -> dict:
    """decision_variables → DecisionVariables, options → GeneticSearchOptions."""
    inp = case['input']
    dv_raw = inp.get('decision_variables')
    options_raw = inp.get('options')

    if isinstance(dv_raw, dict):
        dv = build_decision_variables(dv_raw)
        inp['decision_variables'] = dv
        if isinstance(options_raw, dict):
            inp['options'] = create_genetic_search_options(**options_raw)

    return case


def _unpack_next_generate_genetic(case: dict) -> dict:
    """decision_variables → DecisionVariables, state → GeneticSearchState.

    best_vectors in state are built from raw dicts as Parameters.
    """
    inp = case['input']
    dv_raw = inp.get('decision_variables')
    state_raw = inp.get('state')

    if isinstance(dv_raw, dict):
        dv = build_decision_variables(dv_raw)
        inp['decision_variables'] = dv
        if isinstance(state_raw, dict):
            state_dict = dict(state_raw)
            if 'best_vectors' in state_dict and isinstance(state_dict['best_vectors'], list):
                state_dict['best_vectors'] = [
                    build_parameters(bv) for bv in state_dict['best_vectors']
                ]
            inp['state'] = build_genetic_search_state(**state_dict)

    return case


def _unpack_optimize_genetic(case: dict) -> dict:
    """decision_variables → DecisionVariables, state → GeneticSearchState,
    estimated_candidates → SolutionList."""
    inp = case['input']
    dv_raw = inp.get('decision_variables')
    state_raw = inp.get('state')
    candidates_raw = inp.get('estimated_candidates')

    if isinstance(dv_raw, dict):
        dv = build_decision_variables(dv_raw)
        inp['decision_variables'] = dv
        if isinstance(state_raw, dict):
            inp['state'] = build_genetic_search_state(**state_raw)
        if isinstance(candidates_raw, list):
            inp['estimated_candidates'] = _build_estimated_candidates(candidates_raw)

    return case


def _unpack_is_optimization_done_genetic(case: dict) -> dict:
    """decision_variables → DecisionVariables, state → GeneticSearchState."""
    inp = case['input']
    dv_raw = inp.get('decision_variables')
    state_raw = inp.get('state')

    if isinstance(dv_raw, dict):
        dv = build_decision_variables(dv_raw)
        inp['decision_variables'] = dv
        if isinstance(state_raw, dict):
            inp['state'] = build_genetic_search_state(**state_raw)

    return case
