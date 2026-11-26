"""
Mapping of the functions under test: {func_name: (func_or_wrapper, unpacker | None)}
  - func_or_wrapper — the function under test or a wrapper around it
  - unpacker        — takes a raw case (dict) and converts the input data
                      into typed objects; None for functions with primitive types
"""
from .grid.functions import GRID_FUNCTIONS
from .genetic.functions import GENETIC_FUNCTIONS

FUNCTIONS: dict[str, tuple] = {
    **GRID_FUNCTIONS,
    **GENETIC_FUNCTIONS,
}
