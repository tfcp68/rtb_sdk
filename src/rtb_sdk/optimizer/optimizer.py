from typing import Any, cast

import rtb_sdk.errors.optimizer as com_err
from rtb_sdk.constants.optimizer_constants import OptimizationMethod
from rtb_sdk.schemas import (
    DecisionVariables,
    MethodOptions,
    SolutionList,
    MethodState,
    Solution,
    StateRouterType,
    OptionsRouterType
)
from rtb_sdk.helpers.optimizer import (
    get_option_method_type,
    get_state_method_type,
    build_solution_list_from_dict,
    build_decision_variables_from_dict,
    build_method_options_from_dict,
    build_method_state_from_dict,
    is_valid_decision_variables,
    is_valid_method_state,
    is_valid_method_options,
    is_valid_solution_list,
    create_grid_search_options_from_dict,
    create_genetic_search_options_from_dict,
    build_grid_search_state_from_dict,
    build_genetic_search_state_from_dict,
    is_grid_search_optimization_done,
    is_genetic_search_optimization_done,
)
from .grid_search.grid_search import (
    grid_search_first_generate,
    grid_search_next_generate,
    grid_search_optimize
)
from .genetic_search.genetic_search import (
    genetic_search_first_generate,
    genetic_search_next_generate,
    genetic_search_optimize,
)


state_method_hash: StateRouterType = {
    OptimizationMethod.GRID_SEARCH: {
        'build_state': build_grid_search_state_from_dict,
        'is_optimization_done': is_grid_search_optimization_done,
        'next_generate': grid_search_next_generate,
        'optimizer': grid_search_optimize
    },
    OptimizationMethod.GENETIC_SEARCH: {
        'build_state': build_genetic_search_state_from_dict,
        'is_optimization_done': is_genetic_search_optimization_done,
        'next_generate': genetic_search_next_generate,
        'optimizer': genetic_search_optimize
    }
}

options_method_hash: OptionsRouterType = {
    OptimizationMethod.GRID_SEARCH: {
        'create_options': create_grid_search_options_from_dict,
        'first_generate': grid_search_first_generate,
    },
    OptimizationMethod.GENETIC_SEARCH: {
        'create_options': create_genetic_search_options_from_dict,
        'first_generate': genetic_search_first_generate,
    }
}

'''
    Parameters for functions optimize, first_generate, next_generate, is_optimization_done

    Parameter algorithm: brute-force
    Example:

    class ALGORITHM_TYPES:
        GRID_SEARCH = "grid_search"
        GENETIC_SEARCH = "genetic_search"


    Parameter vocabularies: checklist, It depends on what we’re going through
    Example:
    {
        'changepoint_prior_scale': [0.001, 0.01, 0.1, 1.0],
        'changepoint_range': [0.1, 0.2, 0.3, 0.5],
        'daily_seasonality': [False, True],
        'granularity': ['D'],
        'growth': ['linear', 'flat', 'logistic'],
        'history': [30, 60, 90, 120, 150, 180],
        'interval_width': [0.2, 0.3, 0.4, 0.5, 0.8, 1.0],
        'mcmc_samples': [100, 200, 300, 500, 1000],
        'n_changepoints': [10, 20, 30, 40, 50],
        'scaling': ['absmax', 'minmax'],
        'seasonality_mode': ['additive', 'multiplicative'],
        'seasonality_prior_scale': [0.01, 0.05, 1.0, 10.0],
        'smooth': [False, True],
        'uncertainty_samples': [100, 200, 300, 500, 1000],
        'weekly_seasonality': [False, True],
        'yearly_seasonality': [False, True]
    }

    Parameter options: depends on the model, brute-force initialization
    Example Grid Search:
    {
        'n_combinations': 100,
        'n_step_combinations': 3,
        'objective_type': 'minimize',
        'vocabularies':
            {
                'changepoint_prior_scale': [0.001, 0.01, 0.1, 1.0],
                'changepoint_range': [0.1, 0.2, 0.3, 0.5],
                'daily_seasonality': [False, True],
                'granularity': ['D'],
                'growth': ['linear', 'flat', 'logistic'],
                'history': [30, 60, 90, 120, 150, 180],
                'interval_width': [0.2, 0.3, 0.4, 0.5, 0.8, 1.0],
                'mcmc_samples': [100, 200, 300, 500, 1000],
                'n_changepoints': [10, 20, 30, 40, 50],
                'scaling': ['absmax', 'minmax'],
                'seasonality_mode': ['additive', 'multiplicative'],
                'seasonality_prior_scale': [0.01, 0.05, 1.0, 10.0],
                'smooth': [False, True],
                'uncertainty_samples': [100, 200, 300, 500, 1000],
                'weekly_seasonality': [False, True],
                'yearly_seasonality': [False, True]
            }
    }

    Parameter candidates: candidate
    [
        {
            'estimation': -1.0,
            'parameters':
            {
                'changepoint_prior_scale': 0.001,
                'changepoint_range': 0.1,
                'daily_seasonality': False,
                'granularity': 'D',
                'growth': 'linear',
                'history': 30,
                'interval_width': 0.2,
                'mcmc_samples': 100,
                'n_changepoints': 10,
                'scaling': 'absmax',
                'seasonality_mode': 'additive',
                'seasonality_prior_scale': 0.01,
                'smooth': False,
                'uncertainty_samples': 100,
                'weekly_seasonality': False,
                'yearly_seasonality': False
                }
            },
        {
            'estimation': -1.0,
            'parameters':
            {
                'changepoint_prior_scale': 0.001,
                'changepoint_range': 0.1,
                'daily_seasonality': False,
                'granularity': 'D',
                'growth': 'linear',
                'history': 60,
                'interval_width': 0.2,
                'mcmc_samples': 100,
                'n_changepoints': 10,
                'scaling': 'absmax',
                'seasonality_mode': 'additive',
                'seasonality_prior_scale': 0.01,
                'smooth': False,
                'uncertainty_samples': 100,
                'weekly_seasonality': False,
                'yearly_seasonality': False
            }
        },
        {
            'estimation': -1.0,
            'parameters':
            {
                'changepoint_prior_scale': 0.001,
                'changepoint_range': 0.1,
                'daily_seasonality': False,
                'granularity': 'D',
                'growth': 'linear',
                'history': 90,
                'interval_width': 0.2,
                'mcmc_samples': 100,
                'n_changepoints': 10,
                'scaling': 'absmax',
                'seasonality_mode': 'additive',
                'seasonality_prior_scale': 0.01,
                'smooth': False,
                'uncertainty_samples': 100,
                'weekly_seasonality': False,
                'yearly_seasonality': False
            }
        }
    ]


    Parameter state: state, depending on the brute force algorithm
    Example Grid Search:
    {
        'best_vectors': [],
        'index': 3,
        'n_cartesian_product': 55296000,
        'n_combinations': 100,
        'n_step_combination': 3,
        'objective_type': 'minimize'
    }

    Parameter result: better
    {
        'estimation': 0.4943228018983046,
        'parameters':
        {
            'changepoint_prior_scale': 0.001,
            'changepoint_range': 0.1,
            'daily_seasonality': False,
            'granularity': 'D',
            'growth': 'linear',
            'history': 90,
            'interval_width': 0.2,
            'mcmc_samples': 100,
            'n_changepoints': 10,
            'scaling': 'absmax',
            'seasonality_mode': 'additive',
            'seasonality_prior_scale': 0.01,
            'smooth': False,
            'uncertainty_samples': 100,
            'weekly_seasonality': False,
            'yearly_seasonality': False
        }
    }

'''


def first_generate(decision_variables: DecisionVariables,
                   options: MethodOptions
                   ) -> tuple[SolutionList, MethodState]:
    """Generates the initial set of candidates for optimization.

    Initializes the optimization process by creating the first generation of candidates
    and setting the initial state of the algorithm. The algorithm type is determined by the parameters.

    Args:
        decision_variables (DecisionVariables): Set of parameters to iterate over.
            Must contain a dictionary with the allowed values for each parameter.
        options (MethodOptions): Settings of the search algorithm. Determines the type
            of algorithm (grid search or genetic search) and its configuration.

    Returns:
        tuple[SolutionList, MethodState]: A tuple of:
            - candidates (SolutionList): List of candidates with a score of -1 for each.
            - state (MethodState): Initial state of the search algorithm.

    Raises:
        OptimizerError: If decision_variables or options have an invalid format.
        OptimizerError: If the algorithm type is not supported.

    Example:
        >>> vocabs = {"x": [1, 2, 3], "y": [4, 5, 6]}
        >>> VOCABS = build_decision_variables(vocabs)
        >>> options = create_grid_search_options(
        ...     decision_variables=VOCABS,
        ...     n_step_combinations=3,
        ...     n_combinations=100,
        ...     strategy_type="maximize"
        ... )
        >>> candidates, state = first_generate(VOCABS, options)
        >>> len(candidates['solution_list'])
        3
    """
    if not (is_valid_decision_variables(decision_variables) and
            is_valid_method_options(options)):
        raise com_err.OptimizerError(
            com_err.ErrorCodes.PARAMETER_ERROR_CODE,
            "Incorrect parameters"
        )
    vocab = build_decision_variables_from_dict(cast(dict[str, Any], decision_variables))
    base_options = build_method_options_from_dict(cast(dict[str, Any], options))
    options_type = get_option_method_type(base_options)
    if options_type not in options_method_hash:
        raise com_err.OptimizerError(
            com_err.ErrorCodes.PARAMETER_ERROR_CODE,
            f"Type of algorithm {options_type} not supported in function first_generate"
        )
    method_options = options_method_hash[options_type]['create_options'](decision_variables, options)
    return options_method_hash[options_type]['first_generate'](vocab, method_options)


def is_optimization_done(decision_variables: DecisionVariables,
                         state: MethodState) -> bool:
    """Checks whether the optimization is complete.

    Determines whether the stopping criterion of the optimization algorithm has been reached.
    The check logic depends on the type of algorithm in use.

    Args:
        decision_variables (DecisionVariables): Set of parameters to iterate over.
            Used for validation and for determining the search space.
        state (MethodState): Current state of the search loop. Contains information
            about the algorithm's progress, including the number of completed iterations.

    Returns:
        bool: True if the optimization is complete (the stopping criterion is reached),
              False otherwise.

    Raises:
        OptimizerError: If state has an invalid format.
        Exception: If the algorithm type in state is not supported.

    Example:
        >>> vocabs = {"x": [1, 2, 3], "y": [4, 5, 6]}
        >>> VOCABS = build_decision_variables(vocabs)
        >>> options = create_grid_search_options(
        ...     decision_variables=VOCABS,
        ...     n_step_combinations=2,
        ...     n_combinations=3,
        ...     strategy_type="maximize"
        ... )
        >>> candidates, state = first_generate(VOCABS, options)
        >>> is_optimization_done(VOCABS, state)
        False
    """

    if not (is_valid_method_state(state)):
        raise com_err.OptimizerError(
            com_err.ErrorCodes.PARAMETER_ERROR_CODE,
            "Incorrect parameters"
        )
    base_state = build_method_state_from_dict(cast(dict[str, Any], state))
    state_type = get_state_method_type(base_state)
    if state_type not in state_method_hash:
        raise Exception(
            com_err.ErrorCodes.UNKNOWN_ERROR_CODE,
            f"Type of algorithm {state_type} not supported in function is_optimization_done"
        )
    method_state = state_method_hash[state_type]['build_state'](decision_variables, state)
    return state_method_hash[state_type]['is_optimization_done'](method_state)


def next_generate(decision_variables: DecisionVariables,
                  state: MethodState | None = None
                  ) -> tuple[SolutionList, MethodState]:
    """Generates the next set of candidates for evaluation.

    Forms a new generation of candidates (parameters) to check based on
    the current state of the algorithm. All candidates are initialized with a score of -1.

    Args:
        decision_variables (DecisionVariables): Set of parameters to iterate over.
            Defines the possible parameter values for generating candidates.
        state (MethodState, optional): Current state of the search loop.
            Contains information about previous iterations and the best solutions.
            Defaults to None.

    Returns:
        tuple[SolutionList, MethodState]: A tuple of:
            - candidates (SolutionList): New list of candidates with a score
              of -1 for each until they are computed.
            - state (MethodState): Updated state of the algorithm after
              generating the new candidates.

    Raises:
        OptimizerError: If decision_variables or state have an invalid format.
        Exception: If the algorithm type in state is not supported.

    Example:
        >>> vocabs = {"x": [1, 2, 3], "y": [4, 5, 6]}
        >>> VOCABS = build_decision_variables(vocabs)
        >>> options = create_grid_search_options(
        ...     decision_variables=VOCABS,
        ...     n_step_combinations=2,
        ...     n_combinations=3,
        ...     strategy_type="maximize"
        ... )
        >>> candidates, state = first_generate(VOCABS, options)
        >>> next_candidates, next_state = next_generate(VOCABS, state)
        >>> len(next_candidates['solution_list'])
        1
    """

    if not (is_valid_decision_variables(decision_variables) and
            is_valid_method_state(state)):
        raise com_err.OptimizerError(
            com_err.ErrorCodes.PARAMETER_ERROR_CODE,
            "Incorrect parameters"
        )
    vocab = build_decision_variables_from_dict(cast(dict[str, Any], decision_variables))
    base_state = build_method_state_from_dict(cast(dict[str, Any], state))
    state_type = get_state_method_type(base_state)
    if state_type not in state_method_hash:
        raise Exception(
            com_err.ErrorCodes.UNKNOWN_ERROR_CODE,
            f"Type of algorithm {state_type} not supported in function next_generate"
        )
    method_state = state_method_hash[state_type]['build_state'](decision_variables, state)
    return state_method_hash[state_type]['next_generate'](vocab, method_state)


def optimize(decision_variables: DecisionVariables,
             estimated_candidates: SolutionList,
             state: MethodState
             ) -> tuple[Solution, MethodState]:
    """Selects the best parameters from the evaluated set of candidates.

    Analyzes the scores of all candidates and selects the best parameters according to
    the chosen optimization strategy (maximization or minimization).
    Updates the algorithm state based on the results.

    Args:
        decision_variables (DecisionVariables): Set of parameters to iterate over.
            Used for validating the parameter space.
        estimated_candidates (SolutionList): Candidates (parameter sets)
            with their computed scores. Each candidate contains the parameters
            and the result of their evaluation.
        state (MethodState): Current state of the search loop. Contains the history
            of the best found solutions and other service information of the algorithm.

    Returns:
        tuple[Solution, MethodState]: A tuple of:
            - result (Solution): The best of the evaluated candidates, containing
              the optimal parameters and the corresponding score.
            - state (MethodState): Updated state of the algorithm taking
              the new results into account.

    Raises:
        OptimizerError: If decision_variables, estimated_candidates or state
            have an invalid format.
        Exception: If the algorithm type in state is not supported.

    Example:
        >>> vocabs = {"x": [1, 2, 3], "y": [4, 5, 6]}
        >>> VOCABS = build_decision_variables(vocabs)
        >>> options = create_grid_search_options(
        ...     decision_variables=VOCABS,
        ...     n_step_combinations=2,
        ...     n_combinations=3,
        ...     strategy_type="maximize"
        ... )
        >>> candidates, state = first_generate(VOCABS, options)
        >>> estimated = estimate_func(candidates, equation_func)
        >>> result, new_state = optimize(VOCABS, estimated, state)
        >>> print(result['estimation'])
        0.95
    """

    if not (is_valid_decision_variables(decision_variables) and
            is_valid_method_state(state) and
            is_valid_solution_list(estimated_candidates)):
        raise com_err.OptimizerError(
            com_err.ErrorCodes.PARAMETER_ERROR_CODE,
            "Incorrect parameters"
        )
    vocab = build_decision_variables_from_dict(cast(dict[str, Any], decision_variables))
    solutions = build_solution_list_from_dict(cast(dict[str, Any], estimated_candidates))
    base_state = build_method_state_from_dict(cast(dict[str, Any], state))
    state_type = get_state_method_type(base_state)
    if state_type not in state_method_hash:
        raise Exception(
            com_err.ErrorCodes.UNKNOWN_ERROR_CODE,
            f"Type of algorithm {state_type} not supported in function optimize"
        )
    method_state = state_method_hash[state_type]['build_state'](decision_variables, state)
    return state_method_hash[state_type]['optimizer'](vocab, solutions, method_state)
