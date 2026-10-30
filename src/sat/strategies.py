"""Các chiến lược tối ưu cho SAT: incremental, lb_up, ub_down, bisect."""
from __future__ import annotations

import threading
import time

from pysat.solvers import Solver

from src.common.instance import Instance, makespan
from src.common.result import FEAS, NOSOL, OPT, Config, Result
from src.sat.base import SatEncoding

SOLVERS = {
    "cadical": "cadical195",
    "glucose": "glucose42",
    "cryptominisat": None,  # chưa cài
}

STRATEGIES = ("incremental", "lb_up", "ub_down", "bisect")


def get_encoding(name: str) -> type[SatEncoding]:
    if name == "E1":
        from src.sat.e1_crawford import E1Crawford
        return E1Crawford
    if name == "E2":
        from src.sat.e2_order import E2Order
        return E2Order
    raise ValueError(f"không có encoding {name}")


CONFLICT_BUDGET = 10000


def _supports_interrupt(solver: Solver) -> bool:
    try:
        solver.clear_interrupt()
        return True
    except NotImplementedError:
        return False


def _solve_limited(solver: Solver, deadline: float) -> bool | None:
    # Trả về None nếu hết giờ.
    # CaDiCaL không dùng được interrupt() nên phải giải từng đợt conf_budget.
    if deadline - time.perf_counter() <= 0:
        return None
    timer = None
    if _supports_interrupt(solver):
        timer = threading.Timer(deadline - time.perf_counter(), solver.interrupt)
        timer.daemon = True
        timer.start()
    try:
        while time.perf_counter() < deadline:
            solver.conf_budget(CONFLICT_BUDGET)
            sat = solver.solve_limited(expect_interrupt=timer is not None)
            if sat is not None:
                return sat
        return None
    finally:
        if timer is not None:
            timer.cancel()
            solver.clear_interrupt()


def _solve_incremental(
    inst: Instance,
    cfg: Config,
    encoding_cls: type[SatEncoding],
    solver_name: str,
    *,
    lb0: int,
    ub0: int,
    deadline: float,
) -> Result:
    res = Result.new(inst.name, cfg)
    res.bound = lb0

    t_enc = time.perf_counter()
    enc = encoding_cls(inst, ub0)
    res.encode_time_s += time.perf_counter() - t_enc
    res.n_vars = enc.n_vars
    res.n_clauses = enc.n_clauses

    with Solver(name=solver_name, bootstrap_with=enc.clauses) as solver:
        target = ub0
        while target >= lb0:
            if time.perf_counter() >= deadline:
                break
            t_solve = time.perf_counter()
            sat = _solve_limited(solver, deadline)
            res.solve_time_s += time.perf_counter() - t_solve
            res.n_calls += 1

            if sat is None:
                break
            if not sat:
                res.bound = max(res.bound, target + 1)
                break

            sched = enc.decode(solver.get_model())
            c = makespan(inst, sched)
            res.schedule = sched
            res.cmax = c

            if c <= lb0:
                res.bound = c
                break

            target = c - 1
            t_enc = time.perf_counter()
            for cl in enc.tighten(target):
                solver.add_clause(cl)
            res.encode_time_s += time.perf_counter() - t_enc

    if res.schedule is not None:
        res.status = OPT if res.bound == res.cmax else FEAS
    else:
        res.status = NOSOL
    return res


def solve(inst: Instance, cfg: Config, *, lb0: int, ub0: int, deadline: float) -> Result:
    encoding_cls = get_encoding(cfg.encoding)
    if cfg.strategy not in STRATEGIES:
        raise ValueError(f"không có chiến lược {cfg.strategy}")
    if cfg.solver not in SOLVERS:
        raise ValueError(f"không có SAT solver {cfg.solver}")
    solver_name = SOLVERS[cfg.solver]
    if solver_name is None:
        raise NotImplementedError(f"SAT solver {cfg.solver} sẽ cài ở tuần 2")

    if cfg.strategy == "incremental":
        return _solve_incremental(
            inst, cfg, encoding_cls, solver_name, lb0=lb0, ub0=ub0, deadline=deadline
        )
    raise NotImplementedError("Người 1: các chiến lược SAT nhiều lần (tuần 2)")
