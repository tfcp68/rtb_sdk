import pprint
from typing import Any

from rtb_sdk.schemas import Estimation
from rtb_sdk.helpers import (
    get_solution_parameters,
    get_solution_estimation,
    estimate_func,
    create_grid_search_options,
    build_decision_variables
)
from rtb_sdk.optimizer import (
    first_generate,
    optimize,
    is_optimization_done,
    next_generate
)
from rtb_sdk.constants import OptimizationStrategies


# the problem being solved
# x^2 + y^2 - 1 -> minimize

def equation(params: dict[str, Any]) -> Estimation:
    x = params['x']
    y = params['y']
    return x * x + y * y - 1

# run parameters
N_COMBINATIONS = None
N_STEP_COMBINATIONS = 3
OBJECTIVE = OptimizationStrategies.MINIMIZE
vocabs = {
    "x": list(range(-10, 11, 1)), # [-10, 10]
    "y": list(range(-10, 11, 1))
}
VOCABS = build_decision_variables(vocabs)
# creating the options
options = create_grid_search_options(decision_variables=VOCABS,
                                     n_step_combinations=N_STEP_COMBINATIONS,
                                     n_combinations=N_COMBINATIONS,
                                     strategy_type=OBJECTIVE)

# first cycle of the algorithm
candidates, state = first_generate(decision_variables=VOCABS,
                                   options=options)

estimate_candidates = estimate_func(candidates, equation)

result, state = optimize(decision_variables=VOCABS,
                         estimated_candidates=estimate_candidates,
                         state=state)

# remaining cycles of the algorithm

while not is_optimization_done(VOCABS, state):
    candidates, state = next_generate(decision_variables=VOCABS,
                                      state=state)

    estimate_candidates = estimate_func(candidates, equation)

    result, state = optimize(decision_variables=VOCABS,
                             estimated_candidates=estimate_candidates,
                             state=state)

print("done")

if result is not None:
    pprint.pprint(get_solution_parameters(result))
    pprint.pprint(get_solution_estimation(result))
