from typing import Any, cast

from rtb_sdk.schemas import (
    OptimizationStrategyId,
    GeneticSearchState,
    Parameters,
    OptimizationMethodId,
    MethodState,
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

def get_genetic_state_best_vectors(state: GeneticSearchState,
                                   default: list[Parameters] | None = None) -> list[Parameters] | None:
    return state.get("best_vectors", default)

def get_genetic_state_population_size(state: GeneticSearchState, default: int = 0) -> int:
    return state.get("population_size", default)

def get_genetic_state_best_genome_size(state: GeneticSearchState, default: int = 0) -> int:
    return state.get("best_genome_size", default)

def get_genetic_state_mutants_size(state: GeneticSearchState, default: int = 0) -> int:
    return state.get("mutants_size", default)

def get_genetic_state_crossover_size(state: GeneticSearchState, default: int = 0) -> int:
    return state.get("crossover_size", default)

def get_genetic_state_news_size(state: GeneticSearchState, default: int = 0) -> int:
    return state.get("news_size", default)

def get_genetic_state_n_epochs(state: GeneticSearchState, default: int = 0) -> int:
    return state.get("n_epochs", default)

def get_genetic_state_epoch(state: GeneticSearchState, default: int = 0) -> int:
    return state.get("epoch", default)

def get_genetic_state_mutation_gene_probability(state: GeneticSearchState,
                                                default: float = -1.0) -> float:
    return state.get("mutation_gene_probability", default)

def get_genetic_state_strategy_type(state: GeneticSearchState,
                                    default: OptimizationStrategyId | None = None
                                    ) -> OptimizationStrategyId | None:
    return state.get("strategy_type", default)

def get_genetic_state_method_type(state: GeneticSearchState,
                                  default: OptimizationMethodId | None = None
                                  ) -> OptimizationMethodId | None:
    return state.get("method_type", default)

def is_genetic_search_state(state: MethodState) -> bool:
    return state.get("method_type") == OptimizationMethod.GENETIC_SEARCH

def is_genetic_search_optimization_done(state: GeneticSearchState) -> bool:
    if not check_type(state, DataOptimizerType.GENETIC_SEARCH_STATE):
        raise com_err.OptimizerError(
            com_err.ErrorCodes.PARAMETER_ERROR_CODE,
            "Not valid parameters for GeneticSearchState"
        )
    if not (_is_valid_genetic_state_epoch(state) and _is_valid_genetic_state_n_epochs(state)):
        raise com_err.OptimizerError(
            com_err.ErrorCodes.PARAMETER_ERROR_CODE,
            "Inadmissible values for epoch or n_epochs in GeneticSearchState"
        )
    index = get_genetic_state_epoch(state)
    n_epochs = get_genetic_state_n_epochs(state)
    return index >= n_epochs

# --- _is_valid: checking the type of a field value ---

def _is_valid_genetic_state_best_vectors(state: GeneticSearchState) -> bool:
    if not check_type(state, DataOptimizerType.GENETIC_SEARCH_STATE):
        return False
    best_vectors = get_genetic_state_best_vectors(state)
    if not isinstance(best_vectors, list):
        return False
    return all(isinstance(vec, dict) for vec in best_vectors)

def _is_valid_genetic_state_population_size(state: GeneticSearchState) -> bool:
    if not check_type(state, DataOptimizerType.GENETIC_SEARCH_STATE):
        return False
    population_size = get_genetic_state_population_size(state)
    if not isinstance(population_size, int):
        return False
    return population_size >= 1

def _is_valid_genetic_state_best_genome_size(state: GeneticSearchState) -> bool:
    if not check_type(state, DataOptimizerType.GENETIC_SEARCH_STATE):
        return False
    best_genome_size = get_genetic_state_best_genome_size(state)
    if not isinstance(best_genome_size, int):
        return False
    return best_genome_size >= 1

def _is_valid_genetic_state_mutants_size(state: GeneticSearchState) -> bool:
    if not check_type(state, DataOptimizerType.GENETIC_SEARCH_STATE):
        return False
    mutants_size = get_genetic_state_mutants_size(state)
    if not isinstance(mutants_size, int):
        return False
    return mutants_size >= 1

def _is_valid_genetic_state_crossover_size(state: GeneticSearchState) -> bool:
    if not check_type(state, DataOptimizerType.GENETIC_SEARCH_STATE):
        return False
    crossover_size = get_genetic_state_crossover_size(state)
    if not isinstance(crossover_size, int):
        return False
    return crossover_size >= 1

def _is_valid_genetic_state_news_size(state: GeneticSearchState) -> bool:
    if not check_type(state, DataOptimizerType.GENETIC_SEARCH_STATE):
        return False
    news_size = get_genetic_state_news_size(state)
    if not isinstance(news_size, int):
        return False
    return news_size >= 1

def _is_valid_genetic_state_n_epochs(state: GeneticSearchState) -> bool:
    if not check_type(state, DataOptimizerType.GENETIC_SEARCH_STATE):
        return False
    n_epochs = get_genetic_state_n_epochs(state)
    if not isinstance(n_epochs, int):
        return False
    return n_epochs >= 1

def _is_valid_genetic_state_epoch(state: GeneticSearchState) -> bool:
    if not check_type(state, DataOptimizerType.GENETIC_SEARCH_STATE):
        return False
    epoch = get_genetic_state_epoch(state)
    if not isinstance(epoch, int):
        return False
    return epoch >= 0

def _is_valid_genetic_state_mutation_gene_probability(state: GeneticSearchState) -> bool:
    if not check_type(state, DataOptimizerType.GENETIC_SEARCH_STATE):
        return False
    mutation_gene_probability = get_genetic_state_mutation_gene_probability(state)
    if not isinstance(mutation_gene_probability, float):
        return False
    return 0 <= mutation_gene_probability <= 1

def _is_valid_genetic_state_strategy_type(state: GeneticSearchState) -> bool:
    if not check_type(state, DataOptimizerType.GENETIC_SEARCH_STATE):
        return False
    strategy_type = get_genetic_state_strategy_type(state)
    if not isinstance(strategy_type, str):
        return False
    return is_valid_optimization_strategy(strategy_type)

def _is_valid_genetic_state_method_type(state: GeneticSearchState) -> bool:
    if not check_type(state, DataOptimizerType.GENETIC_SEARCH_STATE):
        return False
    method_type = get_genetic_state_method_type(state)
    if not isinstance(method_type, str):
        return False
    return method_type == OptimizationMethod.GENETIC_SEARCH

CheckGeneticStateList = [
    _is_valid_genetic_state_best_vectors,
    _is_valid_genetic_state_population_size,
    _is_valid_genetic_state_best_genome_size,
    _is_valid_genetic_state_mutants_size,
    _is_valid_genetic_state_crossover_size,
    _is_valid_genetic_state_news_size,
    _is_valid_genetic_state_n_epochs,
    _is_valid_genetic_state_epoch,
    _is_valid_genetic_state_mutation_gene_probability,
    _is_valid_genetic_state_strategy_type,
    _is_valid_genetic_state_method_type
]

# --- _check: checking a field value for validity ---

def _check_fields_genetic_state(state: GeneticSearchState) -> bool:
    for check in CheckGeneticStateList:
        if not check(state):
            return False
    return True

# --- Main validation and checking functions ---

def is_valid_genetic_state(state: Any) -> bool:
    if not check_type(state, DataOptimizerType.GENETIC_SEARCH_STATE):
        return False
    return _check_fields_genetic_state(state)


# --- Builder ---

def build_genetic_search_state(best_vectors: list[Parameters] | None = None,
                               population_size: int = 100,
                               best_genome_size: int = 100,
                               mutants_size: int = 100,
                               crossover_size: int = 100,
                               news_size: int = 100,
                               n_epochs: int = 50,
                               epoch: int = 0,
                               mutation_gene_probability: float = 0.1,
                               strategy_type: OptimizationStrategyId = OptimizationStrategies.MINIMIZE,
                               **kwargs
                               ) -> GeneticSearchState:
    if best_vectors is None:
        best_vectors = []

    res = {
        "best_vectors": best_vectors,
        "population_size": population_size,
        "best_genome_size": best_genome_size,
        "mutants_size": mutants_size,
        "crossover_size": crossover_size,
        "news_size": news_size,
        "n_epochs": n_epochs,
        "epoch": epoch,
        "mutation_gene_probability": mutation_gene_probability,
        "strategy_type": strategy_type,
        "method_type": OptimizationMethod.GENETIC_SEARCH,
        "__type": DataOptimizerType.GENETIC_SEARCH_STATE,
    }
    if is_valid_genetic_state(res):
        return cast(GeneticSearchState, res)
    else:
        raise com_err.OptimizerError(
            com_err.ErrorCodes.PARAMETER_ERROR_CODE,
            "Not valid parameters for GeneticSearchState"
        )

def build_genetic_search_state_from_dict(decision_variables: DecisionVariables,
                                         data: dict) -> GeneticSearchState:
    try:
        return build_genetic_search_state(**data)
    except Exception as e:
        raise com_err.OptimizerError(
            com_err.ErrorCodes.PARAMETER_ERROR_CODE,
            "Not valid parameters for GeneticSearchState"
        )
