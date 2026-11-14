"""Test E3 (biến S + AMO qua CardEnc) trên ft06."""
from __future__ import annotations

import time

import pytest
from pysat.solvers import Solver

from src.common.data import ft06
from src.common.instance import Instance, makespan
from src.common.result import OPT, Config
from src.common.run import run_one
from src.common.verify import verify
from src.sat.e3_amo import AMO_TYPES, E3Amo
from src.sat.strategies import solve


@pytest.mark.parametrize("amo", AMO_TYPES)
def test_e3_ft06_c55_sat(amo: str) -> None:
    inst = ft06()
    enc = E3Amo(inst, 55, amo)
    with Solver(name="cadical195", bootstrap_with=enc.clauses) as solver:
        assert solver.solve() is True
        sched = enc.decode(solver.get_model())
        assert verify(inst, sched) == []
        assert makespan(inst, sched) == 55


@pytest.mark.parametrize("amo", AMO_TYPES)
def test_e3_ft06_c54_unsat(amo: str) -> None:
    enc = E3Amo(ft06(), 54, amo)
    with Solver(name="cadical195", bootstrap_with=enc.clauses) as solver:
        assert solver.solve() is False


@pytest.mark.parametrize("strategy", ["incremental", "lb_up", "ub_down", "bisect"])
@pytest.mark.parametrize("amo", AMO_TYPES)
def test_e3_strategies(amo: str, strategy: str) -> None:
    cfg = Config(method="SAT", encoding=f"E3-{amo}", strategy=strategy, solver="cadical")
    res = run_one("ft06", cfg)
    assert res.status == OPT
    assert res.cmax == 55


@pytest.mark.parametrize("amo", AMO_TYPES)
def test_e3_zero_duration(amo: str) -> None:
    inst = Instance.from_lists("zero", [[(0, 3), (1, 0), (0, 2)], [(1, 4), (0, 0)], [(0, 0)]])
    cfg = Config(method="SAT", encoding=f"E3-{amo}", strategy="incremental", solver="cadical")
    res = solve(inst, cfg, lb0=5, ub0=12, deadline=time.perf_counter() + 30)
    assert res.status == OPT
    assert res.cmax == 6
    assert verify(inst, res.schedule) == []


def test_e3_unknown_amo() -> None:
    with pytest.raises(ValueError):
        E3Amo(ft06(), 55, "totalizer")
