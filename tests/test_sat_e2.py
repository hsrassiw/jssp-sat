"""Test E2 và incremental trên ft06."""
from __future__ import annotations

from pysat.solvers import Solver

from src.common.data import ft06
from src.common.instance import makespan
from src.common.result import OPT, Config
from src.common.run import run_one
from src.common.verify import verify
from src.sat.e2_order import E2Order


def test_e2_ft06_c55_sat() -> None:
    inst = ft06()
    enc = E2Order(inst, 55)
    with Solver(name="cadical195", bootstrap_with=enc.clauses) as solver:
        assert solver.solve() is True
        model = solver.get_model()
        assert model is not None
        sched = enc.decode(model)
        assert verify(inst, sched) == []
        assert makespan(inst, sched) == 55


def test_e2_ft06_c54_unsat() -> None:
    inst = ft06()
    enc = E2Order(inst, 54)
    with Solver(name="cadical195", bootstrap_with=enc.clauses) as solver:
        assert solver.solve() is False


def test_e2_incremental_ft06_cadical() -> None:
    cfg = Config(method="SAT", encoding="E2", strategy="incremental", solver="cadical")
    res = run_one("ft06", cfg)
    assert res.status == OPT
    assert res.cmax == 55
    assert res.bound == 55
    assert res.n_calls >= 2


def test_e2_incremental_ft06_glucose() -> None:
    cfg = Config(method="SAT", encoding="E2", strategy="incremental", solver="glucose")
    res = run_one("ft06", cfg)
    assert res.status == OPT
    assert res.cmax == 55
    assert res.bound == 55
    assert res.n_calls >= 2

