from rtb_sdk.optimizer import is_optimization_done
from rtb_sdk.optimizer.grid_search.grid_search import product_to_index
from rtb_sdk.helpers.optimizer import (
    is_valid_optimization_method,
    is_valid_optimization_strategy,
    check_maximize,
    check_minimize,
    check_optimization_method,
)

from .wrappers import (
    _first_generate_grid,
    _next_generate_grid,
    _optimize_grid,
    _estimate_func_wrapper,
    _index_to_product_wrapper,
)
from .loaders import (
    _unpack_first_generate_grid,
    _unpack_next_generate_grid,
    _unpack_optimize_grid,
    _unpack_is_optimization_done_grid,
    _unpack_estimate_func,
    _unpack_index_to_product,
    _unpack_product_to_index,
)

GRID_FUNCTIONS: dict[str, tuple] = {
    'first_generate_grid':             (_first_generate_grid,             _unpack_first_generate_grid),
    'next_generate_grid':              (_next_generate_grid,              _unpack_next_generate_grid),
    'optimize_grid':                   (_optimize_grid,                   _unpack_optimize_grid),
    'is_optimization_done_grid':       (is_optimization_done,             _unpack_is_optimization_done_grid),
    'estimate_func':                   (_estimate_func_wrapper,           _unpack_estimate_func),
    'index_to_product':                (_index_to_product_wrapper,        _unpack_index_to_product),
    'product_to_index':                (product_to_index,                 _unpack_product_to_index),
    'is_valid_optimization_method':    (is_valid_optimization_method,     None),
    'is_valid_optimization_strategy':  (is_valid_optimization_strategy,   None),
    'check_maximize':                  (check_maximize,                   None),
    'check_minimize':                  (check_minimize,                   None),
    'check_optimization_method':       (check_optimization_method,        None),
}
