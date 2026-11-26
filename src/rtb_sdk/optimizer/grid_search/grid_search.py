from typing import Any, Iterable, Sequence, cast

from rtb_sdk.schemas.optimizer_schemas import (
    GridSearchState,
    OptimizationStrategyId,
    Solution,
    DecisionVariables,
    SolutionList,
    GridSearchOptions,
    Parameters,
)
from rtb_sdk.helpers.optimizer import (
    build_solution,
    get_solution_parameters,
    get_solution_estimation,
    check_minimize,
    get_grid_options_n_step_combinations,
    get_grid_options_n_combinations,
    get_grid_options_objective_type,
    get_grid_state_n_step_combination,
    get_grid_state_n_combinations,
    get_grid_state_n_cartesian_product,
    get_grid_state_index,
    get_grid_state_best_vectors,
    get_grid_state_strategy_type,
    build_grid_search_state,
    get_decision_variables,
    build_solution_list,
    get_solution_list,
    build_parameters
)
from rtb_sdk.helpers.optimizer.grid_search.options_helpers import _cartesian_product_size
import rtb_sdk.errors.optimizer as com_err


def index_to_product(decision_variables: DecisionVariables,
                     index: int) -> tuple:
    vocab = cast(dict[str, list[Any]], get_decision_variables(decision_variables))
    if index > _cartesian_product_size(decision_variables):
        raise com_err.OptimizerError(
            com_err.ErrorCodes.PARAMETER_ERROR_CODE,
            "The index exceeds the number of combinations in a function index_to_product")
    result = []
    for seq in reversed(list(vocab)):
        seq = vocab[seq]
        index, pos = divmod(index, len(seq))
        result.append(seq[pos])
    return tuple(reversed(result))

def product_to_index(decision_variables: DecisionVariables,
                     combination: Sequence) -> int:
    vocab = cast(dict[str, list[Any]], get_decision_variables(decision_variables))
    index = 0
    multiplier = 1
    combo = list(combination)
    for seq, elem in zip(reversed(list(vocab)), reversed(combo)):
        seq = vocab[seq]
        elem = combination[elem]
        pos = list(seq).index(elem)
        index += pos * multiplier
        multiplier *= len(seq)
    return index

def grid_search_first_generate(vocabularies: DecisionVariables,
                               options: GridSearchOptions
                               ) -> tuple[SolutionList, GridSearchState]:
    n_step_combinations = get_grid_options_n_step_combinations(options)
    n_combinations = get_grid_options_n_combinations(options)
    objective_type = get_grid_options_objective_type(options)
    state = build_grid_search_state(decision_variables=vocabularies,
                                    n_combinations=n_combinations,
                                    n_step_combinations=n_step_combinations,
                                    strategy_type=cast(OptimizationStrategyId, objective_type))
    candidates, state = grid_search_next_generate(decision_variables=vocabularies,
                                                  state=state)
    return candidates, state

def grid_search_next_generate(decision_variables: DecisionVariables,
                              state: GridSearchState
                              ) -> tuple[SolutionList, GridSearchState]:
    vocab = cast(dict[str, list[Any]], get_decision_variables(decision_variables))
    n_step = get_grid_state_n_step_combination(state)
    n_combinations = get_grid_state_n_combinations(state)
    cart_prod = get_grid_state_n_cartesian_product(state)
    index = get_grid_state_index(state)
    n_step = min(n_step, min(n_combinations, cart_prod) - index)
    result = []
    for i in range(index, index + n_step):
        values = index_to_product(decision_variables, i)
        idx_dict = build_parameters(dict(zip(vocab.keys(), values)))
        idx_estimate_dict = build_solution(parameters=idx_dict)
        result.append(idx_estimate_dict)
    results = build_solution_list(result)
    state = build_grid_search_state(decision_variables=decision_variables,
                                    best_vectors=get_grid_state_best_vectors(state),
                                    n_combinations=n_combinations,
                                    n_step_combinations=n_step,
                                    index=index + n_step,
                                    strategy_type=cast(OptimizationStrategyId, get_grid_state_strategy_type(state)))
    return results, state

def grid_search_optimize(decision_variables: DecisionVariables,
                         results: SolutionList,
                         state: GridSearchState
                         ) -> tuple[Solution, GridSearchState]:
    obj_type = cast(OptimizationStrategyId, get_grid_state_strategy_type(state))
    vectors = cast(list[Parameters], get_grid_state_best_vectors(state))
    if not results:
        raise com_err.OptimizerError(
            com_err.ErrorCodes.PARAMETER_ERROR_CODE,
            "results They cannot be empty in function optimize")
    result_list = cast(list[Solution], get_solution_list(results))
    best_result: Solution
    if check_minimize(obj_type):
        best_result = min(result_list, key=get_solution_estimation)
    else:
        best_result = max(result_list, key=get_solution_estimation)
    if len(vectors) != 0:
        last_best = cast(Solution, vectors[0])
        if check_minimize(obj_type):
            if get_solution_estimation(last_best) < get_solution_estimation(best_result):
                best_result = last_best
        else:
            if get_solution_estimation(last_best) > get_solution_estimation(best_result):
                best_result = last_best
    new_vectors: list[Parameters] = [cast(Parameters, best_result)]
    n_combinations = get_grid_state_n_combinations(state)
    state_idx = get_grid_state_index(state)
    state = build_grid_search_state(decision_variables=decision_variables,
                        best_vectors=new_vectors,
                        n_combinations=n_combinations,
                        n_step_combinations=get_grid_state_n_step_combination(state),
                        index=state_idx,
                        strategy_type=obj_type)
    result = build_solution(
        parameters=get_solution_parameters(best_result),
        estimation=get_solution_estimation(best_result))
    return result, state
