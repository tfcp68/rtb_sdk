from auto_all import start_all, end_all

start_all()

from .parameters_helpers import (
    get_parameters_parameters,
    build_parameters,
    build_parameters_from_dict,
    is_valid_parameters,
)

from .solution_helpers import (
    build_solution,
    build_solution_from_dict,
    get_solution_parameters,
    get_solution_estimation,
    is_valid_solution,
)

from .solution_list_helpers import (
    get_solution_list,
    build_solution_list,
    build_solution_list_from_dict,
    is_valid_solution_list,
)

from .decision_variables_helpers import (
    get_decision_variables,
    build_decision_variables,
    build_decision_variables_from_dict,
    is_valid_decision_variables,
)

from .method_options_helpers import (
    get_option_strategy_type,
    get_option_method_type,
    build_method_options,
    build_method_options_from_dict,
    is_valid_method_options,
)

from .method_state_helpers import (
    get_state_best_vectors,
    get_state_method_type,
    get_state_strategy_type,
    build_method_state,
    build_method_state_from_dict,
    is_valid_method_state,
)

from .utils import (
    is_valid_optimization_method,
    is_valid_optimization_strategy,
    check_maximize,
    check_minimize,
    validate_optimization_method,
    check_optimization_method,
    estimate_func,
)

from .genetic_search import (
    create_genetic_search_options,
    create_genetic_search_options_from_dict,
    get_genetic_options_population_size,
    get_genetic_options_best_genome_size,
    get_genetic_options_mutants_size,
    get_genetic_options_crossover_size,
    get_genetic_options_news_size,
    get_genetic_options_n_epochs,
    get_genetic_options_mutation_gene_probability,
    get_genetic_options_objective_type,
    get_genetic_option_method_type,
    is_genetic_search_options,
    is_valid_genetic_options,
    build_genetic_search_state,
    build_genetic_search_state_from_dict,
    is_genetic_search_optimization_done,
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
    get_genetic_state_method_type,
    is_genetic_search_state,
    is_valid_genetic_state,
)

from .grid_search import (
    create_grid_search_options,
    create_grid_search_options_from_dict,
    get_grid_options_n_combinations,
    get_grid_options_n_step_combinations,
    get_grid_options_objective_type,
    get_grid_option_method_type,
    is_grid_search_options,
    is_valid_grid_options,
    build_grid_search_state,
    build_grid_search_state_from_dict,
    is_grid_search_optimization_done,
    get_grid_state_best_vectors,
    get_grid_state_n_combinations,
    get_grid_state_n_step_combination,
    get_grid_state_index,
    get_grid_state_n_cartesian_product,
    get_grid_state_strategy_type,
    get_grid_state_method_type,
    is_grid_search_state,
    is_valid_grid_state,
)

end_all()
