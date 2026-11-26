# optimizer / examples

Full-cycle Optimizer examples: candidate generation, evaluation with an objective function, state updates, and selection of the best solution for grid search and genetic search.

Run from the repository root as modules so that the project's root packages are imported without manually changing `sys.path`.

---

## Commands

```powershell
python -m examples.optimizer.grid_search_minimization_equation
python -m examples.optimizer.genetic_search_optimize_equation

python -m pytest tests/optimizer
```

## grid_search_minimization_equation

Shows the full enumeration cycle on a minimization problem:

```python
f(x, y) = x ** 2 + y ** 2 - 1
```

Scenario:

1. Creates the `DecisionVariables` search space for `x` and `y`.
2. Creates `GridSearchOptions` with `N_COMBINATIONS` and the step size `N_STEP_COMBINATIONS`.
3. Gets the first set of candidates via `first_generate`.
4. Evaluates the candidates via `estimate_func`.
5. Updates the best solution via `optimize`.
6. Repeats `next_generate / estimate_func / optimize` until `is_optimization_done` returns `True`.

Prints the found parameters and the objective function value.

## genetic_search_optimize_equation

Shows the full genetic search cycle on the same function, but in maximization mode.

Scenario:

1. Creates the `DecisionVariables` search space for `x` and `y`.
2. Creates `GeneticSearchOptions`: sizes of the best genomes, mutants, crossover, new random candidates, the number of epochs, and the mutation probability.
3. Generates the initial population via `first_generate`.
4. Evaluates the population via `estimate_func`.
5. Updates the state via `optimize`.
6. Repeats the cycle until the epoch limit is reached.

The genetic search result may differ between runs because the algorithm uses random generation.

## Input data

The examples do not read external files. The search space and algorithm parameters are defined inside the scripts:

| Name | Description |
|---|---|
| `vocabs` | Allowed values of the `x` and `y` parameters |
| `equation` | Objective function returning an `Estimation` |
| `options` | Settings of the specific optimization method |

## Output data

The scripts do not save anything to disk. The result is printed to stdout:

| Output | Description |
|---|---|
| `parameters` | The best parameter set found |
| `estimation` | Objective function value for the best solution |

## Related tests

Optimizer tests are located in `tests/optimizer/`.

| Path | Responsibility |
|---|---|
| `test_optimizer.py` | Runs parameterized optimizer cases |
| `cases/` | JSON cases for optimizer functions |
| `grid/` | Wrappers, loaders, and functions for grid search |
| `genetic/` | Wrappers, loaders, and functions for genetic search |
| `reports/` | Generated test reports |
