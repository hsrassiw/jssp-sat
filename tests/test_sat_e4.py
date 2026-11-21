"""Test E4 (E2 + biến thứ tự máy kiểu Crawford)."""
import random
import time

import pytest
from pysat.solvers import Solver

from src.common.bounds import lower_bound
from src.common.data import ft06
from src.common.instance import Instance, makespan
from src.common.result import OPT, Config
from src.common.run import run_one
from src.common.verify import verify
from src.sat.e4_order_pr import E4OrderPr
from src.sat.strategies import solve


def test_e4_ft06_c55_sat():
    inst = ft06()
    enc = E4OrderPr(inst, 55)
    with Solver(name="cadical195", bootstrap_with=enc.clauses) as solver:
        assert solver.solve() is True
        sched = enc.decode(solver.get_model())
        assert verify(inst, sched) == []
        assert makespan(inst, sched) == 55


def test_e4_ft06_c54_unsat():
    enc = E4OrderPr(ft06(), 54)
    with Solver(name="cadical195", bootstrap_with=enc.clauses) as solver:
        assert solver.solve() is False


@pytest.mark.parametrize("strategy", ["incremental", "lb_up", "ub_down", "bisect"])
def test_e4_strategies(strategy):
    cfg = Config(method="SAT", encoding="E4", strategy=strategy, solver="cadical")
    res = run_one("ft06", cfg)
    assert res.status == OPT
    assert res.cmax == 55


def test_e4_zero_duration():
    # có bước dài 0, và job 0 vào máy 0 hai lần
    inst = Instance.from_lists("zero", [[(0, 3), (1, 0), (0, 2)], [(1, 4), (0, 0)], [(0, 0)]])
    cfg = Config(method="SAT", encoding="E4", strategy="incremental", solver="cadical")
    res = solve(inst, cfg, lb0=5, ub0=12, deadline=time.perf_counter() + 30)
    assert res.status == OPT
    assert res.cmax == 6
    assert verify(inst, res.schedule) == []


def random_instance(seed):
    # 4 job, 3 máy, máy chọn ngẫu nhiên (có thể trùng máy trong một job), có bước dài 0
    rng = random.Random(seed)
    rows = []
    for j in range(4):
        row = []
        for k in range(3):
            row.append((rng.randrange(3), rng.randrange(6)))
        rows.append(row)
    return Instance.from_lists(f"rand{seed}", rows)


@pytest.mark.parametrize("seed", range(20))
def test_e4_same_optimum_as_e2(seed):
    inst = random_instance(seed)
    lb0 = lower_bound(inst)
    ub0 = max(inst.total_duration(), lb0)
    results = {}
    for name in ["E2", "E4"]:
        cfg = Config(method="SAT", encoding=name, strategy="incremental", solver="cadical")
        res = solve(inst, cfg, lb0=lb0, ub0=ub0, deadline=time.perf_counter() + 30)
        assert res.status == OPT
        assert verify(inst, res.schedule) == []
        results[name] = res.cmax
    assert results["E4"] == results["E2"]
