from rtb_sdk.optimizer import is_optimization_done

from .wrappers import (
    _first_generate_genetic,
    _next_generate_genetic,
    _optimize_genetic,
)
from .loaders import (
    _unpack_first_generate_genetic,
    _unpack_next_generate_genetic,
    _unpack_optimize_genetic,
    _unpack_is_optimization_done_genetic,
)

GENETIC_FUNCTIONS: dict[str, tuple] = {
    'first_generate_genetic':       (_first_generate_genetic,       _unpack_first_generate_genetic),
    'next_generate_genetic':        (_next_generate_genetic,        _unpack_next_generate_genetic),
    'optimize_genetic':             (_optimize_genetic,             _unpack_optimize_genetic),
    'is_optimization_done_genetic': (is_optimization_done,          _unpack_is_optimization_done_genetic),
}
