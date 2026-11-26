"""Optimizer module for optimization algorithms."""

from auto_all import start_all, end_all

start_all()

from .optimizer import (
    first_generate,
    is_optimization_done,
    next_generate,
    optimize,
)

end_all()