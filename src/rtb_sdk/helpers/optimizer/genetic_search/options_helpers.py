from typing import Any, cast

from rtb_sdk.schemas import (
    OptimizationStrategyId,
    GeneticSearchOptions,
    OptimizationMethodId,
    MethodOptions,
    DecisionVariables
)
from rtb_sdk.constants import (
    OptimizationStrategies,
    OptimizationMethod,
    DataOptimizerType,
)
from rtb_sdk.helpers.type_helpers import check_type
from rtb_sdk.helpers.optimizer.utils import is_valid_optimization_strategy
import rtb_sdk.errors.optimizer as com_err


# --- Getters ---

def get_genetic_options_population_size(options: GeneticSearchOptions, default: int = 0) -> int:
    return options.get("population_size", default)

def get_genetic_options_best_genome_size(options: GeneticSearchOptions, default: int = 0) -> int:
    return options.get("best_genome_size", default)

def get_genetic_options_mutants_size(options: GeneticSearchOptions, default: int = 0) -> int:
    return options.get("mutants_size", default)

def get_genetic_options_crossover_size(options: GeneticSearchOptions, default: int = 0) -> int:
    return options.get("crossover_size", default)

def get_genetic_options_news_size(options: GeneticSearchOptions, default: int = 0) -> int:
    return options.get("news_size", default)

def get_genetic_options_n_epochs(options: GeneticSearchOptions, default: int = 0) -> int:
    return options.get("n_epochs", default)

def get_genetic_options_mutation_gene_probability(options: GeneticSearchOptions,
                                                  default: float = -1.0) -> float:
    return options.get("mutation_gene_probability", default)

def get_genetic_options_objective_type(options: GeneticSearchOptions,
                                       default: OptimizationStrategyId | None = None
                                       ) -> OptimizationStrategyId | None:
    return options.get("strategy_type", default)

def get_genetic_option_method_type(options: GeneticSearchOptions,
                                   default: OptimizationMethodId = OptimizationMethod.GENETIC_SEARCH
                                   ) -> OptimizationMethodId:
    return options.get("method_type", default)

def is_genetic_search_options(options: MethodOptions) -> bool:
    return options.get("method_type") == OptimizationMethod.GENETIC_SEARCH

# --- _is_valid: checking the type of a field value ---

def _is_valid_genetic_options_population_size(options: GeneticSearchOptions) -> bool:
    if not check_type(options, DataOptimizerType.GENETIC_SEARCH_OPTIONS):
        return False
    population_size = get_genetic_options_population_size(options)
    if not isinstance(population_size, int):
        return False
    return population_size >= 1

def _is_valid_genetic_options_best_genome_size(options: GeneticSearchOptions) -> bool:
    if not check_type(options, DataOptimizerType.GENETIC_SEARCH_OPTIONS):
        return False
    best_genome_size = get_genetic_options_best_genome_size(options)
    if not isinstance(best_genome_size, int):
        return False
    return best_genome_size >= 1

def _is_valid_genetic_options_mutants_size(options: GeneticSearchOptions) -> bool:
    if not check_type(options, DataOptimizerType.GENETIC_SEARCH_OPTIONS):
        return False
    mutants_size = get_genetic_options_mutants_size(options)
    if not isinstance(mutants_size, int):
        return False
    return mutants_size >= 1

def _is_valid_genetic_options_crossover_size(options: GeneticSearchOptions) -> bool:
    if not check_type(options, DataOptimizerType.GENETIC_SEARCH_OPTIONS):
        return False
    crossover_size = get_genetic_options_crossover_size(options)
    if not isinstance(crossover_size, int):
        return False
    return crossover_size >= 1

def _is_valid_genetic_options_news_size(options: GeneticSearchOptions) -> bool:
    if not check_type(options, DataOptimizerType.GENETIC_SEARCH_OPTIONS):
        return False
    news_size = get_genetic_options_news_size(options)
    if not isinstance(news_size, int):
        return False
    return news_size >= 1

def _is_valid_genetic_options_n_epochs(options: GeneticSearchOptions) -> bool:
    if not check_type(options, DataOptimizerType.GENETIC_SEARCH_OPTIONS):
        return False
    n_epochs = get_genetic_options_n_epochs(options)
    if not isinstance(n_epochs, int):
        return False
    return n_epochs >= 1

def _is_valid_genetic_options_mutation_gene_probability(options: GeneticSearchOptions) -> bool:
    if not check_type(options, DataOptimizerType.GENETIC_SEARCH_OPTIONS):
        return False
    mutation_gene_probability = get_genetic_options_mutation_gene_probability(options)
    if not isinstance(mutation_gene_probability, float):
        return False
    return 0 <= mutation_gene_probability <= 1

def _is_valid_genetic_options_strategy_type(options: GeneticSearchOptions) -> bool:
    if not check_type(options, DataOptimizerType.GENETIC_SEARCH_OPTIONS):
        return False
    strategy_type = get_genetic_options_objective_type(options)
    if not isinstance(strategy_type, str):
        return True
    return is_valid_optimization_strategy(strategy_type)

def _is_valid_genetic_options_method_type(options: GeneticSearchOptions) -> bool:
    if not check_type(options, DataOptimizerType.GENETIC_SEARCH_OPTIONS):
        return False
    method_type = get_genetic_option_method_type(options)
    if not isinstance(method_type, str):
        return True
    return method_type == OptimizationMethod.GENETIC_SEARCH

CheckGeneticOptionsList = [
    _is_valid_genetic_options_population_size,
    _is_valid_genetic_options_best_genome_size,
    _is_valid_genetic_options_mutants_size,
    _is_valid_genetic_options_crossover_size,
    _is_valid_genetic_options_news_size,
    _is_valid_genetic_options_n_epochs,
    _is_valid_genetic_options_mutation_gene_probability,
    _is_valid_genetic_options_strategy_type,
    _is_valid_genetic_options_method_type
]

# --- _check: checking a field value for validity ---

def _check_fields_genetic_options(options: GeneticSearchOptions) -> bool:
    for check in CheckGeneticOptionsList:
        if not check(options):
            return False
    return True

# --- Main validation and checking functions ---

def is_valid_genetic_options(options: Any) -> bool:
    if not check_type(options, DataOptimizerType.GENETIC_SEARCH_OPTIONS):
        return False
    return _check_fields_genetic_options(options)


# --- Builder ---

def create_genetic_search_options(best_genome_size: int = 100,
                                  mutants_size: int = 100,
                                  crossover_size: int = 100,
                                  news_size: int = 100,
                                  n_epochs: int = 50,
                                  mutation_gene_probability: float = 0.1,
                                  strategy_type: OptimizationStrategyId = OptimizationStrategies.MINIMIZE,
                                  **kwargs
                                  ) -> GeneticSearchOptions:
    population_size = best_genome_size + mutants_size + crossover_size + news_size

    res = {
        "population_size": population_size,
        "best_genome_size": best_genome_size,
        "mutants_size": mutants_size,
        "crossover_size": crossover_size,
        "news_size": news_size,
        "n_epochs": n_epochs,
        "mutation_gene_probability": mutation_gene_probability,
        "strategy_type": strategy_type,
        "method_type": OptimizationMethod.GENETIC_SEARCH,
        "__type": DataOptimizerType.GENETIC_SEARCH_OPTIONS,
    }
    if is_valid_genetic_options(res):
        return cast(GeneticSearchOptions, res)
    else:
        raise com_err.OptimizerError(
            com_err.ErrorCodes.PARAMETER_ERROR_CODE,
            "Not valid parameters for GeneticSearchOptions"
        )

def create_genetic_search_options_from_dict(decision_variables: DecisionVariables,
                                            data: dict) -> GeneticSearchOptions:
    try:
        return create_genetic_search_options(**data)
    except Exception as e:
        raise com_err.OptimizerError(
            com_err.ErrorCodes.PARAMETER_ERROR_CODE,
            "Not valid parameters for GeneticSearchOptions"
        )
