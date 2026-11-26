import random
from typing import Any, cast

from rtb_sdk.schemas.optimizer_schemas import (
    GeneticSearchOptions,
    OptimizationStrategyId,
    GeneticSearchState,
    Solution,
    DecisionVariables,
    SolutionList,
    Parameters
)
from rtb_sdk.helpers import (
    build_solution,
    get_solution_parameters,
    get_solution_estimation,
    check_minimize,
    check_maximize,
    get_genetic_options_population_size,
    get_genetic_options_best_genome_size,
    get_genetic_options_mutants_size,
    get_genetic_options_crossover_size,
    get_genetic_options_news_size,
    get_genetic_options_n_epochs,
    get_genetic_options_mutation_gene_probability,
    get_genetic_options_objective_type,
    build_genetic_search_state,
    get_genetic_state_best_vectors,
    get_genetic_state_population_size,
    get_genetic_state_best_genome_size,
    get_genetic_state_mutants_size,
    get_genetic_state_crossover_size,
    get_genetic_state_news_size,
    get_genetic_state_n_epochs,
    get_genetic_state_epoch,
    get_genetic_state_mutation_gene_probability,
    get_genetic_state_strategy_type,
    get_decision_variables,
    build_parameters,
    build_solution_list,
    get_solution_list,
    get_parameters_parameters
)
import rtb_sdk.errors.optimizer as com_err


def genetic_search_first_generate(decision_variables: DecisionVariables,
                                  options: GeneticSearchOptions
                                  ) -> tuple[SolutionList, GeneticSearchState]:
    state = __build_state_from_options(options)
    population_size = get_genetic_options_population_size(options)
    population = __create_population(decision_variables, population_size)
    result = list(map(build_solution, population))
    result = build_solution_list(result)
    return result, state

def __build_state_from_options(options: GeneticSearchOptions
                               ) -> GeneticSearchState:
    population_size = get_genetic_options_population_size(options)
    best_genome_size = get_genetic_options_best_genome_size(options)
    mutants_size = get_genetic_options_mutants_size(options)
    crossover_size = get_genetic_options_crossover_size(options)
    news_size = get_genetic_options_news_size(options)
    n_epochs = get_genetic_options_n_epochs(options)
    mutation_gene_probability = get_genetic_options_mutation_gene_probability(options)
    objective_type = get_genetic_options_objective_type(options)
    state = build_genetic_search_state(population_size=population_size,
                                       best_genome_size=best_genome_size,
                                       mutants_size=mutants_size,
                                       crossover_size=crossover_size,
                                       news_size=news_size,
                                       n_epochs=n_epochs,
                                       epoch=1,
                                       mutation_gene_probability=mutation_gene_probability,
                                       strategy_type=cast(OptimizationStrategyId, objective_type))
    return state

def __create_population(decision_variables: DecisionVariables,
                        population: int) -> list[Parameters]:
    vocab = cast(dict[str, list[Any]], get_decision_variables(decision_variables))
    pop: list[Parameters] = []
    for i in range(population):
        indiv = {k: random.choice(v) for k, v in vocab.items()}
        pop.append(build_parameters(indiv))
    return pop

def genetic_search_next_generate(decision_variables: DecisionVariables,
                                 state: GeneticSearchState
                                 ) -> tuple[SolutionList, GeneticSearchState]:
    mutants_size = get_genetic_state_mutants_size(state)
    crossover_size = get_genetic_state_crossover_size(state)
    news_size = get_genetic_state_news_size(state)
    gene_mutation_ration = get_genetic_state_mutation_gene_probability(state)
    parents = cast(list[Parameters], get_genetic_state_best_vectors(state))
    mutation_candidates = __choose_mutation_candidates(parents, mutants_size)
    mutation_parents = __mutation_population(mutation_candidates,
                                             decision_variables,
                                             gene_mutation_ration)
    crossover_parents = __choose_crossover_candidates(parents, crossover_size)
    crossover_children = __crossover_population(crossover_parents,
                                                decision_variables)
    new_children = __create_population(decision_variables, news_size)
    parents.extend(mutation_parents)
    parents.extend(crossover_children)
    parents.extend(new_children)
    state = __next_epoch(state)
    result = list(map(build_solution, parents))
    result = build_solution_list(result)
    return result, state

def __next_epoch(state: GeneticSearchState
                 ) -> GeneticSearchState:
    state = build_genetic_search_state(best_vectors=get_genetic_state_best_vectors(state),
                                       population_size=get_genetic_state_population_size(state),
                                       best_genome_size=get_genetic_state_best_genome_size(state),
                                       mutants_size=get_genetic_state_mutants_size(state),
                                       crossover_size=get_genetic_state_crossover_size(state),
                                       news_size=get_genetic_state_news_size(state),
                                       n_epochs=get_genetic_state_n_epochs(state),
                                       epoch=get_genetic_state_epoch(state) + 1,
                                       mutation_gene_probability=get_genetic_state_mutation_gene_probability(state),
                                       strategy_type=cast(OptimizationStrategyId, get_genetic_state_strategy_type(state)))
    return state


def __choose_mutation_candidates(population: list[Parameters],
                                 n_candidates: int) -> list[Parameters]:
    return [random.choice(population) for _ in range(n_candidates)]

def __mutation_population(mutation_population: list[Parameters],
                          decision_variables: DecisionVariables,
                          gene_mutation_ratio: float = 0.1,
                          ) -> list[Parameters]:
    mutants = []
    for candidate in mutation_population:
        mutant = __mutate_genome(decision_variables,
                                 candidate,
                                 gene_mutation_ratio)
        mutants.append(build_parameters(mutant))
    return mutants

def __mutate_genome(decision_variables: DecisionVariables,
                    candidate: Parameters,
                    gene_mutation_ratio: float = 0.1) -> dict[str, Any]:
    vocab = cast(dict[str, list[Any]], get_decision_variables(decision_variables))
    candidate_params = cast(dict[str, Any], get_parameters_parameters(candidate))
    result = {}
    for gene, gene_list in vocab.items():
        if random.random() <= gene_mutation_ratio:
            result[gene] = __mutate_gene(gene_list)
        else:
            result[gene] = candidate_params[gene]
    return result

def __mutate_gene(gene_list: list[Any]) -> Any:
    return random.choice(gene_list)

def __get_parents_for_crossover(parents: list[Parameters]) -> tuple[Parameters, Parameters]:
    if len(parents) > 1:
        a, b = random.sample(parents, 2)
        return a, b
    else:
        return parents[0], parents[0]

def __choose_crossover_candidates(population: list[Parameters],
                                  n_child_pairs: int) -> list[tuple[Parameters, Parameters]]:
    result: list[tuple[Parameters, Parameters]] = []
    for _ in range(n_child_pairs):
        parent1, parent2 = __get_parents_for_crossover(population)
        result.append((parent1, parent2))
    return result

def __crossover_population(parents: list[tuple[Parameters, Parameters]],
                           decision_variables: DecisionVariables) -> list[Parameters]:
    children = []
    for parent1, parent2 in parents:
        child = __crossover_genome(parent1, parent2, decision_variables)
        children.append(build_parameters(child))
    return children

def __crossover_genome(parent1: Parameters,
                       parent2: Parameters,
                       decision_variables: DecisionVariables) -> dict[str, Any]:
    vocab = cast(dict[str, list[Any]], get_decision_variables(decision_variables))
    child = dict()
    parent1_params = cast(dict[str, Any], get_parameters_parameters(parent1))
    parent2_params = cast(dict[str, Any], get_parameters_parameters(parent2))
    for gene, gene_list in vocab.items():
        child[gene] = __crossover_gene(parent1_params[gene],
                                       parent2_params[gene],
                                       gene_list)
    return child

def __crossover_gene(gene1: Any,
                     gene2: Any,
                     gene_list: list[Any]) -> Any:
    return random.choice([gene1, gene2])

def genetic_search_optimize(decision_variables: DecisionVariables,
                            results: SolutionList,
                            state: GeneticSearchState
                            ) -> tuple[Solution, GeneticSearchState]:
    obj_type = cast(OptimizationStrategyId, get_genetic_state_strategy_type(state))
    sorted_result = __sort_estimated_candidates(results, obj_type)
    sorted_list = cast(list[Solution], get_solution_list(sorted_result))
    top_parents = get_genetic_state_best_genome_size(state)
    result_slice = sorted_list[: top_parents]
    vectors = [cast(Parameters, get_solution_parameters(i)) for i in result_slice]
    result = build_solution_list(result_slice)
    best_candidate = __get_best_candidate(result)
    state = build_genetic_search_state(best_vectors=vectors,
                                       population_size=get_genetic_state_population_size(state),
                                       best_genome_size=get_genetic_state_best_genome_size(state),
                                       mutants_size=get_genetic_state_mutants_size(state),
                                       crossover_size=get_genetic_state_crossover_size(state),
                                       news_size=get_genetic_state_news_size(state),
                                       n_epochs=get_genetic_state_n_epochs(state),
                                       epoch=get_genetic_state_epoch(state),
                                       mutation_gene_probability=get_genetic_state_mutation_gene_probability(state),
                                       strategy_type=cast(OptimizationStrategyId, get_genetic_state_strategy_type(state)))
    result = build_solution(
        parameters=get_solution_parameters(cast(Solution, best_candidate)),
        estimation=get_solution_estimation(cast(Solution, best_candidate)))
    return result, state

def __sort_estimated_candidates(results: SolutionList,
                                objective_type: OptimizationStrategyId) -> SolutionList:
    if not results:
        raise com_err.OptimizerError(
            com_err.ErrorCodes.PARAMETER_ERROR_CODE,
            "Optimization results cannot be empty")
    sort_result: list[Solution] = []
    solutions = cast(list[Solution], get_solution_list(results))
    if check_minimize(objective_type):
        sort_result = sorted(solutions, key=get_solution_estimation)
    elif check_maximize(objective_type):
        sort_result = sorted(solutions, key=get_solution_estimation, reverse=True)
    result = build_solution_list(sort_result)
    return result

def __get_best_candidate(results: SolutionList) -> Solution:
    if not results:
        raise com_err.OptimizerError(
            com_err.ErrorCodes.PARAMETER_ERROR_CODE,
            "Optimization results cannot be empty")
    solutions = cast(list[Solution], get_solution_list(results))
    return solutions[0]
