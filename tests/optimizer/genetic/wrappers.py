"""
Wrappers around the functions under test (genetic search) — return simple, easily comparable values.
"""
from rtb_sdk.optimizer import first_generate, next_generate, optimize


def _first_generate_genetic(decision_variables, options):
    """Returns the tuple (SolutionList, GeneticSearchState) — check_output_type."""
    candidates, state = first_generate(decision_variables=decision_variables, options=options)
    return candidates, state


def _next_generate_genetic(decision_variables, state):
    """Returns the tuple (SolutionList, GeneticSearchState) — check_output_type."""
    candidates, new_state = next_generate(decision_variables=decision_variables, state=state)
    return candidates, new_state


def _optimize_genetic(decision_variables, estimated_candidates, state):
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
