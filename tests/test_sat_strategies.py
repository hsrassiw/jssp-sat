"""Test các chiến lược tối ưu và 3 SAT solver trên ft06."""
from __future__ import annotations

import time

import pytest
from pysat.examples.genhard import PHP

from src.common.data import ft06
from src.common.result import FEAS, NOSOL, OPT, Config
from src.common.run import run_one
from src.common.verify import verify
from src.sat import strategies
from src.sat.strategies import STRATEGIES, _Cms, _solve_limited, solve

SOLVERS = ["cadical", "glucose", "cryptominisat"]


@pytest.mark.parametrize("solver", SOLVERS)
@pytest.mark.parametrize("strategy", STRATEGIES)
def test_ft06_opt(strategy: str, solver: str) -> None:
    cfg = Config(method="SAT", encoding="E2", strategy=strategy, solver=solver)
    res = run_one("ft06", cfg)
    assert res.status == OPT
    assert res.cmax == 55
    assert res.bound == 55


@pytest.mark.parametrize("strategy", ["lb_up", "ub_down", "bisect"])
def test_from_loose_bounds(strategy: str) -> None:
    # ub0 = tổng thời gian để có nhiều lần gọi solver
    inst = ft06()
    cfg = Config(method="SAT", encoding="E2", strategy=strategy, solver="cadical")
    res = solve(inst, cfg, lb0=47, ub0=70, deadline=time.perf_counter() + 60)
    assert res.status == OPT
    assert res.cmax == 55
    assert verify(inst, res.schedule) == []
    assert res.n_calls >= 2


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_no_time(strategy: str) -> None:
    cfg = Config(method="SAT", encoding="E2", strategy=strategy, solver="cadical")
    res = solve(ft06(), cfg, lb0=47, ub0=70, deadline=time.perf_counter())
    assert res.status in (NOSOL, FEAS)
    assert res.bound <= 55


@pytest.mark.parametrize("strategy", ["incremental", "ub_down", "bisect"])
def test_save_progress(strategy: str, monkeypatch) -> None:
    saved = []
    monkeypatch.setattr(strategies, "save_progress", lambda res: saved.append(res.cmax))
    cfg = Config(method="SAT", encoding="E2", strategy=strategy, solver="cadical")
    solve(ft06(), cfg, lb0=47, ub0=70, deadline=time.perf_counter() + 60)
    assert any(c is not None and c <= 70 for c in saved)


def test_cms_stops_at_deadline() -> None:
    with _Cms(PHP(11).clauses) as solver:
        t0 = time.perf_counter()
        assert _solve_limited(solver, t0 + 1.0) is None
        assert time.perf_counter() - t0 < 5.0


def test_cms_easy_formula() -> None:
    with _Cms(PHP(4).clauses) as solver:
        assert _solve_limited(solver, time.perf_counter() + 10.0) is False
