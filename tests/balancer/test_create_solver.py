"""Unit tests for create_solver and its GLOP parameters.

Cover the function that is being changed for DEVEX pricing: verify that
(1) the GLOP parameter string is valid (catches a typo in the rule/enum name),
(2) the assembled solver still solves a known LP to the correct optimum.

The DEVEX speed gain itself is measured separately
(benchmarks/bench_solver_backends.py) — here only correctness.
"""
from ortools.linear_solver import pywraplp

from rtb_sdk.balancer.solver.solver import create_solver, GLOP_SOLVER_PARAMS


def test_glop_solver_params_string_is_accepted_by_glop():
    """The GLOP_SOLVER_PARAMS string must be parsed by GLOP without errors.

    SetSolverSpecificParametersAsString returns False on invalid
    content (e.g. a typo in the DEVEX enum name) — this catches such bugs
    before they quietly disable the tuning in production.
    """
    solver = pywraplp.Solver.CreateSolver('GLOP')
    assert solver is not None
    assert solver.SetSolverSpecificParametersAsString(GLOP_SOLVER_PARAMS) is True


def test_create_solver_solves_known_lp_to_correct_optimum():
    """The solver from create_solver solves a simple LP to a known optimum.

    max x + y  s.t.  x <= 3, y <= 2, x,y >= 0  ⇒  optimum 5 (x=3, y=2).
    Guarantees that the tuning parameters do not break the correctness of the solution.
    """
    solver = create_solver(1)

    x = solver.NumVar(0.0, 3.0, 'x')
    y = solver.NumVar(0.0, 2.0, 'y')
    obj = solver.Objective()
    obj.SetCoefficient(x, 1.0)
    obj.SetCoefficient(y, 1.0)
    obj.SetMaximization()

    status = solver.Solve()

    assert status == pywraplp.Solver.OPTIMAL
    assert abs(obj.Value() - 5.0) < 1e-6
    assert abs(x.solution_value() - 3.0) < 1e-6
    assert abs(y.solution_value() - 2.0) < 1e-6
