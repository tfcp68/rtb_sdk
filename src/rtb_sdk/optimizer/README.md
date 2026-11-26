# RTB SDK // Optimizer

## Table of contents

- [RTB SDK // Optimizer](#rtb-sdk--optimizer)
  - [Table of contents](#table-of-contents)
  - [Quick start](#quick-start)
  - [Description](#description)
  - [Data types](#data-types)
    - [OptimizationMethodId](#optimizationmethodid)
    - [OptimizationStrategyId](#optimizationstrategyid)
    - [DecisionVariables](#decisionvariables)
    - [MethodOptions](#methodoptions)
      - [GridSearchOptions](#gridsearchoptions)
      - [GeneticSearchOptions](#geneticsearchoptions)
    - [Parameters](#parameters)
    - [Estimation](#estimation)
    - [Solution](#solution)
    - [SolutionList](#solutionlist)
    - [MethodState](#methodstate)
      - [GridSearchState](#gridsearchstate)
      - [GeneticSearchState](#geneticsearchstate)
  - [Functions](#functions)
    - [first\_generate](#first_generate)
    - [next\_generate](#next_generate)
    - [optimize](#optimize)
    - [is\_optimization\_done](#is_optimization_done)
    - [equation](#equation)
    - [estimate\_func](#estimate_func)
  - [Examples](#examples)
    - [Full optimization cycle (Grid Search)](#full-optimization-cycle-grid-search)
    - [Full optimization cycle (Genetic Search)](#full-optimization-cycle-genetic-search)

## Quick start

A library for optimizing the parameters of arbitrary tasks, supporting two search algorithms: exhaustive enumeration (grid search) and a genetic algorithm (genetic search).

```python
from typing import Any

from rtb_sdk.optimizer import first_generate, optimize, is_optimization_done, next_generate
from rtb_sdk.helpers import build_decision_variables, create_grid_search_options, estimate_func
from rtb_sdk.constants import OptimizationStrategies
from rtb_sdk.schemas import Estimation


# task: minimize x^2 + y^2 - 1
def equation(params: dict[str, Any]) -> Estimation:
    return params['x'] ** 2 + params['y'] ** 2 - 1


VOCABS = build_decision_variables({
    "x": list(range(-10, 11)),
    "y": list(range(-10, 11))
})

options = create_grid_search_options(
    decision_variables=VOCABS,
    n_step_combinations=3,
    strategy_type=OptimizationStrategies.MINIMIZE
)

candidates, state = first_generate(decision_variables=VOCABS, options=options)
estimated = estimate_func(candidates, equation)
result, state = optimize(decision_variables=VOCABS, estimated_candidates=estimated, state=state)

while not is_optimization_done(VOCABS, state):
    candidates, state = next_generate(decision_variables=VOCABS, state=state)
    estimated = estimate_func(candidates, equation)
    result, state = optimize(decision_variables=VOCABS, estimated_candidates=estimated, state=state)

# result — a Solution with the best parameters found
```

## Description

A distinguishing feature of the library is that it can work in distributed systems: the algorithm state is stored explicitly as a serializable `MethodState` object, which allows passing it between services and resuming optimization from any stage.

The optimizer works in the following stages:

1. Cycle initialization — defining the search space (`DecisionVariables`) and the algorithm settings (`MethodOptions`).
2. Forming the initial candidates — `first_generate`.
3. Evaluating the candidates — `estimate_func` with the user-defined `equation` function.
4. Selecting the best parameters — `optimize`.
5. Checking for completion — `is_optimization_done`:
   - if the goal is reached — `result` contains the best solution found;
   - if not — the next generation of candidates is formed via `next_generate`, and the flow returns to step 3.

## Data types

### OptimizationMethodId

Identifier of the optimization algorithm.

```python
type OptimizationMethodId = Literal["grid", "genetic"]
```

A constants class is used to access the values:

```python
class OptimizationMethod:
    GRID_SEARCH: OptimizationMethodId = "grid"
    GENETIC_SEARCH: OptimizationMethodId = "genetic"
```

Example:

```python
from rtb_sdk.constants import OptimizationMethod
from rtb_sdk.schemas import OptimizationMethodId

method: OptimizationMethodId = OptimizationMethod.GENETIC_SEARCH
```

### OptimizationStrategyId

The optimization direction — maximizing or minimizing the objective function.

```python
type OptimizationStrategyId = Literal["maximize", "minimize"]
```

```python
class OptimizationStrategies:
    MAXIMIZE: OptimizationStrategyId = "maximize"
    MINIMIZE: OptimizationStrategyId = "minimize"
```

Example:

```python
from rtb_sdk.constants import OptimizationStrategies
from rtb_sdk.schemas import OptimizationStrategyId

strategy: OptimizationStrategyId = OptimizationStrategies.MAXIMIZE
```

### DecisionVariables

The search space: a dictionary of allowed values for each parameter being optimized.

Created via the `build_decision_variables` constructor from `helpers.optimizer`.

| Field                | Type                       | Description |
| -------------------- | -------------------------- | ----------- |
| `decision_variables` | `dict[str, list[Any]]`     | a dictionary where the key is the parameter name and the value is a list of allowed options |

Example:

```python
from rtb_sdk.helpers import build_decision_variables

VOCABS = build_decision_variables({
    "A": ['A_1', 'A_2', 'A_3'],
    "B": [1, 2, 3, 4, 5],
    "C": [False, True]
})
```

### MethodOptions

The base type of the optimization algorithm settings. The specific parameters depend on the chosen method.

| Field           | Type                                              | Description |
| --------------- | ------------------------------------------------- | ----------- |
| `strategy_type` | [OptimizationStrategyId](#optimizationstrategyid) | optimization direction |
| `method_type`   | [OptimizationMethodId](#optimizationmethodid)     | search algorithm |

#### GridSearchOptions

Exhaustive enumeration settings. Created via `create_grid_search_options` from `helpers.optimizer`.

| Field                 | Type                                              | Optional                   | Description |
| --------------------- | ------------------------------------------------- | -------------------------- | ----------- |
| `strategy_type`       | [OptimizationStrategyId](#optimizationstrategyid) | Yes, default: `"minimize"` | optimization direction |
| `method_type`         | [OptimizationMethodId](#optimizationmethodid)     | No                         | always `"grid"` |
| `n_step_combinations` | `int`                                             | Yes, default: `10`         | number of candidates per step (batch size) |
| `n_combinations`      | `int \| None`                                     | Yes, default: `None`       | maximum total number of combinations to check; `None` — enumerate all |

Example:

```python
from rtb_sdk.helpers import build_decision_variables, create_grid_search_options
from rtb_sdk.constants import OptimizationStrategies

VOCABS = build_decision_variables({"x": [1, 2, 3], "y": [4, 5, 6]})

options = create_grid_search_options(
    decision_variables=VOCABS,
    n_step_combinations=10,
    n_combinations=1000,
    strategy_type=OptimizationStrategies.MINIMIZE
)
```

#### GeneticSearchOptions

Genetic algorithm settings. Created via `create_genetic_search_options` from `helpers.optimizer`.

| Field                       | Type                                              | Optional                      | Description |
| --------------------------- | ------------------------------------------------- | ----------------------------- | ----------- |
| `strategy_type`             | [OptimizationStrategyId](#optimizationstrategyid) | Yes, default: `"minimize"`    | optimization direction |
| `method_type`               | [OptimizationMethodId](#optimizationmethodid)     | No                            | always `"genetic"` |
| `best_genome_size`          | `int`                                             | Yes, default: `100`           | number of best individuals carried over to the next generation |
| `mutants_size`              | `int`                                             | Yes, default: `100`           | number of mutated individuals |
| `crossover_size`            | `int`                                             | Yes, default: `100`           | number of individuals produced by crossover |
| `news_size`                 | `int`                                             | Yes, default: `100`           | number of new random individuals |
| `n_epochs`                  | `int`                                             | Yes, default: `50`            | maximum number of generations |
| `mutation_gene_probability` | `float`                                           | Yes, default: `0.1`           | probability of mutation of an individual gene, `0.0`–`1.0` |

Example:

```python
from rtb_sdk.helpers import create_genetic_search_options
from rtb_sdk.constants import OptimizationStrategies

options = create_genetic_search_options(
    best_genome_size=10,
    mutants_size=10,
    crossover_size=10,
    news_size=10,
    n_epochs=20,
    mutation_gene_probability=0.1,
    strategy_type=OptimizationStrategies.MAXIMIZE
)
```

### Parameters

One specific set of values of the parameters being optimized.

Created via `build_parameters` from `helpers.optimizer`.

| Field        | Type                 | Description |
| ------------ | -------------------- | ----------- |
| `parameters` | `dict[str, Any]`     | specific parameter values |

Example:

```python
from rtb_sdk.helpers import build_parameters

params = build_parameters({"x": 3, "y": -2, "mode": "linear"})
```

### Estimation

A numerical evaluation of a parameter set, returned by the [equation](#equation) function.

```python
type Estimation = float
```

Example:

```python
from rtb_sdk.schemas import Estimation

estimation: Estimation = 0.42
```

### Solution

A parameter set together with its evaluation.

Created via `build_solution_from_dict` from `helpers.optimizer` or returned by the optimizer functions.

| Field         | Type                        | Description |
| ------------- | --------------------------- | ----------- |
| `parameters`  | [Parameters](#parameters)   | the set of parameter values |
| `estimation`  | [Estimation](#estimation)   | evaluation of this set; `-1.0` — not evaluated |

Example:

```python
from rtb_sdk.helpers import build_solution_from_dict

solution = build_solution_from_dict({
    'estimation': 0.42,
    'parameters': {'x': 3, 'y': -2}
})
```

### SolutionList

A list of candidates — parameter sets awaiting or having undergone evaluation.

Created via `build_solution_list` from `helpers.optimizer` or returned by the optimizer functions.

| Field           | Type                        | Description |
| --------------- | --------------------------- | ----------- |
| `solution_list` | `list[Solution]`            | list of solutions |

Example:

```python
from rtb_sdk.helpers import build_solution_list

solution_list = build_solution_list([
    {'estimation': -1.0, 'parameters': {'x': 1, 'y': 4}},
    {'estimation': -1.0, 'parameters': {'x': 2, 'y': 4}},
    {'estimation': -1.0, 'parameters': {'x': 3, 'y': 4}},
])
```

### MethodState

The current state of the optimization algorithm. Stores the history of the best solutions found and service data about progress. Passed between calls to `first_generate`, `next_generate`, and `optimize`.

| Field           | Type                                              | Description |
| --------------- | ------------------------------------------------- | ----------- |
| `best_vectors`  | `list[Parameters]`                                | list of the best parameter sets found |
| `method_type`   | [OptimizationMethodId](#optimizationmethodid)     | the algorithm in use |
| `strategy_type` | [OptimizationStrategyId](#optimizationstrategyid) | optimization direction |

Created automatically by the `first_generate` function and updated on every call to `optimize` and `next_generate`.

#### GridSearchState

The state of the exhaustive enumeration algorithm.

| Field                 | Type  | Description |
| --------------------- | ----- | ----------- |
| `best_vectors`        | `list[Parameters]` | the best parameter sets found |
| `method_type`         | `"grid"` | algorithm type |
| `strategy_type`       | [OptimizationStrategyId](#optimizationstrategyid) | optimization direction |
| `n_combinations`      | `int` | maximum number of combinations |
| `n_step_combinations` | `int` | size of one step (batch) |
| `index`               | `int` | index of the current position in the Cartesian product |
| `n_cartesian_product` | `int` | total number of combinations in the Cartesian product |

Example (serialized form):

```python
{
    'best_vectors': [],
    'method_type': 'grid',
    'strategy_type': 'minimize',
    'index': 10,
    'n_cartesian_product': 55296000,
    'n_combinations': 1000,
    'n_step_combinations': 10
}
```

#### GeneticSearchState

The state of the genetic algorithm.

| Field                       | Type    | Description |
| --------------------------- | ------- | ----------- |
| `best_vectors`              | `list[Parameters]` | the best parameter sets found |
| `method_type`               | `"genetic"` | algorithm type |
| `strategy_type`             | [OptimizationStrategyId](#optimizationstrategyid) | optimization direction |
| `population_size`           | `int`   | population size |
| `best_genome_size`          | `int`   | number of best individuals |
| `mutants_size`              | `int`   | number of mutants |
| `crossover_size`            | `int`   | number of individuals from crossover |
| `news_size`                 | `int`   | number of new random individuals |
| `n_epochs`                  | `int`   | maximum number of generations |
| `epoch`                     | `int`   | current generation number |
| `mutation_gene_probability` | `float` | gene mutation probability |

Example (serialized form):

```python
{
    'best_vectors': [],
    'method_type': 'genetic',
    'strategy_type': 'maximize',
    'population_size': 40,
    'best_genome_size': 10,
    'mutants_size': 10,
    'crossover_size': 10,
    'news_size': 10,
    'n_epochs': 20,
    'epoch': 1,
    'mutation_gene_probability': 0.1
}
```

## Functions

The main optimizer functions implement the following stages of the cycle:

1. `first_generate` — forming the initial candidates;
2. `estimate_func` — evaluating the candidates with the user-defined function;
3. `optimize` — selecting the best parameters from the evaluated candidates;
4. `is_optimization_done` — checking the stopping condition;
5. `next_generate` — forming the next generation of candidates.

### first_generate

Initializes the optimization process and forms the first set of candidates.

```python
def first_generate(
    decision_variables: DecisionVariables,
    options: MethodOptions
) -> tuple[SolutionList, MethodState]:
```

**Parameters:**

- `decision_variables` — [DecisionVariables](#decisionvariables): the search space;
- `options` — [MethodOptions](#methodoptions): algorithm settings (GridSearchOptions or GeneticSearchOptions).

**Returns:**

- `candidates` — [SolutionList](#solutionlist): the first batch of candidates with an evaluation of `-1`;
- `state` — [MethodState](#methodstate): the initial algorithm state.

**Exceptions:**

- `OptimizerError` — if `decision_variables` or `options` have an invalid format or an unsupported algorithm type.

Example:

```python
from rtb_sdk.optimizer import first_generate
from rtb_sdk.helpers import build_decision_variables, create_grid_search_options
from rtb_sdk.constants import OptimizationStrategies

VOCABS = build_decision_variables({"x": list(range(-10, 11)), "y": list(range(-10, 11))})
options = create_grid_search_options(
    decision_variables=VOCABS,
    n_step_combinations=3,
    strategy_type=OptimizationStrategies.MINIMIZE
)

candidates, state = first_generate(decision_variables=VOCABS, options=options)
```

### next_generate

Forms the next set of candidates based on the current algorithm state.

```python
def next_generate(
    decision_variables: DecisionVariables,
    state: MethodState
) -> tuple[SolutionList, MethodState]:
```

**Parameters:**

- `decision_variables` — [DecisionVariables](#decisionvariables): the search space;
- `state` — [MethodState](#methodstate): the current algorithm state.

**Returns:**

- `candidates` — [SolutionList](#solutionlist): a new batch of candidates with an evaluation of `-1`;
- `state` — [MethodState](#methodstate): the updated algorithm state.

**Exceptions:**

- `OptimizerError` — if `decision_variables` or `state` have an invalid format.

Example:

```python
from rtb_sdk.optimizer import next_generate

candidates, state = next_generate(decision_variables=VOCABS, state=state)
```

### optimize

Accepts the evaluated candidates, updates the list of best solutions, and returns the current optimum.

```python
def optimize(
    decision_variables: DecisionVariables,
    estimated_candidates: SolutionList,
    state: MethodState
) -> tuple[Solution, MethodState]:
```

**Parameters:**

- `decision_variables` — [DecisionVariables](#decisionvariables): the search space;
- `estimated_candidates` — [SolutionList](#solutionlist): candidates with computed evaluations;
- `state` — [MethodState](#methodstate): the current algorithm state.

**Returns:**

- `result` — [Solution](#solution): the best candidate found so far;
- `state` — [MethodState](#methodstate): the updated algorithm state.

**Exceptions:**

- `OptimizerError` — if any of the parameters has an invalid format.

Example:

```python
from rtb_sdk.optimizer import optimize

result, state = optimize(
    decision_variables=VOCABS,
    estimated_candidates=estimated,
    state=state
)
print(result['estimation'])   # best evaluation
print(result['parameters'])   # best parameter set
```

### is_optimization_done

Checks whether the algorithm's stopping criterion has been reached.

```python
def is_optimization_done(
    decision_variables: DecisionVariables,
    state: MethodState
) -> bool:
```

**Parameters:**

- `decision_variables` — [DecisionVariables](#decisionvariables): the search space;
- `state` — [MethodState](#methodstate): the current algorithm state.

**Returns:**

- `True` — optimization is finished (all combinations enumerated or epochs exhausted);
- `False` — optimization continues.

**Exceptions:**

- `OptimizerError` — if `state` has an invalid format.

Example:

```python
from rtb_sdk.optimizer import is_optimization_done

if is_optimization_done(VOCABS, state):
    print("Optimization finished")
```

### equation

A user-defined function that evaluates one parameter set. It is created separately for each task.

Prototype:

```python
def equation(params: dict[str, Any]) -> Estimation:
```

**Parameters:**

- `params` — a dictionary with the parameter values of the current candidate (the keys match the keys of `DecisionVariables`).

**Returns:**

- `Estimation` (`float`) — a numerical evaluation of this parameter set.

Example:

```python
from typing import Any
from rtb_sdk.schemas import Estimation

def equation(params: dict[str, Any]) -> Estimation:
    return params['x'] ** 2 + params['y'] ** 2 - 1
```

### estimate_func

Applies the [equation](#equation) function to all candidates in a [SolutionList](#solutionlist) and returns the list with the evaluations filled in.

```python
def estimate_func(
    candidates: SolutionList,
    est_func: Callable[[dict[str, Any]], Estimation]
) -> SolutionList:
```

**Parameters:**

- `candidates` — [SolutionList](#solutionlist): a list of candidates with an evaluation of `-1`;
- `est_func` — the function that evaluates one candidate (`equation`).

**Returns:**

- [SolutionList](#solutionlist) — a list of candidates with the evaluations set.

Example:

```python
from rtb_sdk.helpers import estimate_func

estimated = estimate_func(candidates, equation)
```

## Examples

### Full optimization cycle (Grid Search)

Minimizing the function $f(x, y) = x^2 + y^2 - 1$:

```python
from typing import Any

from rtb_sdk.optimizer import first_generate, optimize, is_optimization_done, next_generate
from rtb_sdk.helpers import build_decision_variables, create_grid_search_options, estimate_func
from rtb_sdk.constants import OptimizationStrategies
from rtb_sdk.schemas import Estimation


def equation(params: dict[str, Any]) -> Estimation:
    return params['x'] ** 2 + params['y'] ** 2 - 1


VOCABS = build_decision_variables({
    "x": list(range(-10, 11)),
    "y": list(range(-10, 11))
})

options = create_grid_search_options(
    decision_variables=VOCABS,
    n_step_combinations=3,
    n_combinations=100,
    strategy_type=OptimizationStrategies.MINIMIZE
)

# first generation
candidates, state = first_generate(decision_variables=VOCABS, options=options)
estimated = estimate_func(candidates, equation)
result, state = optimize(decision_variables=VOCABS, estimated_candidates=estimated, state=state)

# main loop
while not is_optimization_done(VOCABS, state):
    candidates, state = next_generate(decision_variables=VOCABS, state=state)
    estimated = estimate_func(candidates, equation)
    result, state = optimize(decision_variables=VOCABS, estimated_candidates=estimated, state=state)

print(result['estimation'])   # -1.0
print(result['parameters'])   # {'x': 0, 'y': 0}
```

### Full optimization cycle (Genetic Search)

Maximizing the same function with a genetic algorithm:

```python
from typing import Any

from rtb_sdk.optimizer import first_generate, optimize, is_optimization_done, next_generate
from rtb_sdk.helpers import build_decision_variables, create_genetic_search_options, estimate_func
from rtb_sdk.constants import OptimizationStrategies
from rtb_sdk.schemas import Estimation


def equation(params: dict[str, Any]) -> Estimation:
    return params['x'] ** 2 + params['y'] ** 2 - 1


VOCABS = build_decision_variables({
    "x": list(range(-10, 11)),
    "y": list(range(-10, 11))
})

options = create_genetic_search_options(
    best_genome_size=10,
    mutants_size=10,
    crossover_size=10,
    news_size=10,
    n_epochs=20,
    mutation_gene_probability=0.1,
    strategy_type=OptimizationStrategies.MAXIMIZE
)

# first generation
candidates, state = first_generate(decision_variables=VOCABS, options=options)
estimated = estimate_func(candidates, equation)
result, state = optimize(decision_variables=VOCABS, estimated_candidates=estimated, state=state)

# main loop
while not is_optimization_done(VOCABS, state):
    candidates, state = next_generate(decision_variables=VOCABS, state=state)
    estimated = estimate_func(candidates, equation)
    result, state = optimize(decision_variables=VOCABS, estimated_candidates=estimated, state=state)

print(result['estimation'])   # 199.0
print(result['parameters'])   # {'x': -10, 'y': 10} or similar
```
