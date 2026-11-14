"""Test solver dừng đúng giờ."""
from __future__ import annotations

import time

import pytest
from pysat.examples.genhard import PHP
from pysat.solvers import Solver

from src.sat.strategies import CONFLICT_BUDGET, FIRST_BUDGET, _next_budget, _solve_limited

SOLVER_NAMES = ["cadical195", "glucose42"]


class SlowSolver:
    """Giả lập bài lớn: mỗi conflict mất 1ms, 10000 conflict mất 10s, không bao giờ giải xong."""

    def __init__(self, answer_after: float | None = None):
        self.budget = 0
        self.answer_after = answer_after
        self.t0 = time.perf_counter()

    def clear_interrupt(self) -> None:
        raise NotImplementedError

    def conf_budget(self, budget: int) -> None:
        self.budget = budget

    def solve_limited(self, expect_interrupt: bool = False) -> bool | None:
        time.sleep(self.budget * 0.001)
        if self.answer_after is not None and time.perf_counter() - self.t0 > self.answer_after:
            return True
        return None


@pytest.mark.parametrize("name", SOLVER_NAMES)
def test_stops_at_deadline(name: str) -> None:
    # PHP(11) rất khó, không giải xong trong 1s
    with Solver(name=name, bootstrap_with=PHP(11).clauses) as solver:
        t0 = time.perf_counter()
        assert _solve_limited(solver, t0 + 1.0) is None
        assert time.perf_counter() - t0 < 5.0


def test_slow_chunks_stop_near_deadline() -> None:
    t0 = time.perf_counter()
    assert _solve_limited(SlowSolver(), t0 + 3.0) is None
    assert time.perf_counter() - t0 < 4.0


class LateSolver(SlowSolver):
    """Đợt đầu mất 1.5s rồi mới báo SAT."""

    def solve_limited(self, expect_interrupt: bool = False) -> bool | None:
        time.sleep(1.5)
        return True


def test_answer_after_deadline_not_counted() -> None:
    assert _solve_limited(LateSolver(), time.perf_counter() + 1.0) is None


def test_answer_before_deadline_kept() -> None:
    t0 = time.perf_counter()
    assert _solve_limited(SlowSolver(answer_after=0.5), t0 + 10.0) is True


def test_next_budget() -> None:
    # còn nhiều giờ: gấp đôi, tối đa CONFLICT_BUDGET
    assert _next_budget(100, 0.01, 500) == 200
    assert _next_budget(CONFLICT_BUDGET, 1.0, 500) == CONFLICT_BUDGET
    # 1000 conflict mất 10s, còn 4s: đợt sau 200 conflict (khoảng 2s)
    assert _next_budget(1000, 10.0, 4.0) == 200
    # gần hết giờ vẫn giải ít nhất FIRST_BUDGET
    assert _next_budget(1000, 10.0, 0.01) == FIRST_BUDGET


@pytest.mark.parametrize("name", SOLVER_NAMES)
def test_easy_formula_still_solved(name: str) -> None:
    with Solver(name=name, bootstrap_with=PHP(4).clauses) as solver:
        assert _solve_limited(solver, time.perf_counter() + 10.0) is False
