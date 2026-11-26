from typing import Literal, Any, Callable
from .discriminated_type_schemas import DiscriminatedTypedDict


type OptimizationMethodId = Literal["grid", "genetic"]
type OptimizationStrategyId = Literal["maximize", "minimize"]

type StateMethodHashStage = Literal['build_state', 'is_optimization_done', 'next_generate', 'optimizer']
type OptionsMethodHashStage = Literal['create_options', 'first_generate']

type StateRouterType = dict[OptimizationMethodId, dict[StateMethodHashStage, Callable]]
type OptionsRouterType = dict[OptimizationMethodId, dict[OptionsMethodHashStage, Callable]]

type Estimation = float

class Parameters(DiscriminatedTypedDict):
    parameters: dict[str, Any]

class MethodOptions(DiscriminatedTypedDict):
    strategy_type: OptimizationStrategyId
    method_type: OptimizationMethodId

class Solution(DiscriminatedTypedDict):
    parameters: Parameters
    estimation: Estimation

class MethodState(DiscriminatedTypedDict):
    best_vectors: list[Parameters]
    method_type: OptimizationMethodId
    strategy_type: OptimizationStrategyId

class SolutionList(DiscriminatedTypedDict):
    solution_list: list[Solution]

class DecisionVariables(DiscriminatedTypedDict):
    decision_variables: dict[str, list[Any]]

class GeneticSearchOptions(MethodOptions):
    population_size: int
    best_genome_size: int
    mutants_size: int
    crossover_size: int
    news_size: int
    n_epochs: int
    mutation_gene_probability: float

class GeneticSearchState(MethodState):
    population_size: int
    best_genome_size: int
    mutants_size: int
    crossover_size: int
    news_size: int
    n_epochs: int
    epoch: int
    mutation_gene_probability: float

class GridSearchOptions(MethodOptions):
    n_step_combinations: int
    n_combinations: int

class GridSearchState(MethodState):
    n_combinations: int
    n_step_combinations: int
    index: int
    n_cartesian_product: int
