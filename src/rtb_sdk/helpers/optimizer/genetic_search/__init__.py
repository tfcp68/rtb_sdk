from auto_all import start_all, end_all

start_all()

from .options_helpers import (
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
)

from .state_helpers import (
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

end_all()