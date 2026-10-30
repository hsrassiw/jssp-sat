"""Test solver dừng đúng giờ."""
from __future__ import annotations

import time

import pytest
from pysat.examples.genhard import PHP
from pysat.solvers import Solver

from src.sat.strategies import _solve_limited

SOLVER_NAMES = ["cadical195", "glucose42"]


@pytest.mark.parametrize("name", SOLVER_NAMES)
def test_stops_at_deadline(name: str) -> None:
    # PHP(11) rất khó, không giải xong trong 1s
    with Solver(name=name, bootstrap_with=PHP(11).clauses) as solver:
        t0 = time.perf_counter()
        assert _solve_limited(solver, t0 + 1.0) is None
        assert time.perf_counter() - t0 < 5.0


@pytest.mark.parametrize("name", SOLVER_NAMES)
def test_easy_formula_still_solved(name: str) -> None:
    with Solver(name=name, bootstrap_with=PHP(4).clauses) as solver:
        assert _solve_limited(solver, time.perf_counter() + 10.0) is False
