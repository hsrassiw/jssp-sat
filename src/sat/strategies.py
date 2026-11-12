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
    "cryptominisat": "cms",
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


class _Cms:
    """CryptoMiniSat qua pycryptosat, dùng như Solver của PySAT."""

    def __init__(self, clauses: list[list[int]]):
        from pycryptosat import Solver as CmsSolver

        # confl_limit tính cho từng lần solve, gọi lại thì giải tiếp
        self._s = CmsSolver(threads=1, confl_limit=CONFLICT_BUDGET)
        self._model: list[int] | None = None
        for cl in clauses:
            self._s.add_clause(cl)

    def __enter__(self) -> _Cms:
        return self

    def __exit__(self, *exc) -> None:
        pass

    def add_clause(self, clause: list[int]) -> None:
        self._s.add_clause(clause)

    def clear_interrupt(self) -> None:
        raise NotImplementedError

    def conf_budget(self, budget: int) -> None:
        pass

    def solve_limited(self, expect_interrupt: bool = False) -> bool | None:
        sat, values = self._s.solve()
        if sat:
            self._model = [v if values[v] else -v for v in range(1, len(values))]
        return sat

    def get_model(self) -> list[int] | None:
        return self._model


def _new_solver(name: str, clauses: list[list[int]]):
    if name == "cms":
        return _Cms(clauses)
    return Solver(name=name, bootstrap_with=clauses)


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

    with _new_solver(solver_name, enc.clauses) as solver:
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


class _Fresh:
    """SAT nhiều lần: mỗi lần hỏi Cmax <= c thì encode lại với horizon c, solver mới."""

    def __init__(self, inst, cfg, encoding_cls, solver_name, deadline):
        self.inst = inst
        self.encoding_cls = encoding_cls
        self.solver_name = solver_name
        self.deadline = deadline
        self.res = Result.new(inst.name, cfg)

    def check(self, c: int) -> bool | None:
        # True: có lịch với Cmax <= c (lưu vào res), False: UNSAT, None: hết giờ
        res = self.res
        if time.perf_counter() >= self.deadline:
            return None
        t_enc = time.perf_counter()
        enc = self.encoding_cls(self.inst, c)
        res.encode_time_s += time.perf_counter() - t_enc
        res.n_vars = max(res.n_vars, enc.n_vars)
        res.n_clauses = max(res.n_clauses, enc.n_clauses)

        with _new_solver(self.solver_name, enc.clauses) as solver:
            t_solve = time.perf_counter()
            sat = _solve_limited(solver, self.deadline)
            res.solve_time_s += time.perf_counter() - t_solve
            res.n_calls += 1
            if sat:
                res.schedule = enc.decode(solver.get_model())
                res.cmax = makespan(self.inst, res.schedule)
        return sat

    def finish(self) -> Result:
        res = self.res
        if res.schedule is not None:
            res.status = OPT if res.bound == res.cmax else FEAS
        else:
            res.status = NOSOL
        return res


def _solve_lb_up(f: _Fresh, lb0: int, ub0: int) -> Result:
    f.res.bound = lb0
    for c in range(lb0, ub0 + 1):
        sat = f.check(c)
        if sat is None:
            break
        if sat:
            f.res.bound = f.res.cmax
            break
        f.res.bound = c + 1
    return f.finish()


def _solve_ub_down(f: _Fresh, lb0: int, ub0: int) -> Result:
    f.res.bound = lb0
    c = ub0
    while c >= lb0:
        sat = f.check(c)
        if sat is None:
            break
        if not sat:
            f.res.bound = c + 1
            break
        if f.res.cmax <= lb0:
            f.res.bound = f.res.cmax
            break
        c = f.res.cmax - 1
    return f.finish()


def _solve_bisect(f: _Fresh, lb0: int, ub0: int) -> Result:
    # ub0 có lịch greedy nên luôn SAT, nhưng vẫn phải để solver tìm lịch
    lo, hi = lb0, ub0
    while lo < hi:
        mid = (lo + hi) // 2
        sat = f.check(mid)
        if sat is None:
            break
        if sat:
            hi = f.res.cmax
        else:
            lo = mid + 1
    f.res.bound = lo
    if lo == hi and f.res.cmax != hi:
        f.check(hi)
    return f.finish()


def solve(inst: Instance, cfg: Config, *, lb0: int, ub0: int, deadline: float) -> Result:
    encoding_cls = get_encoding(cfg.encoding)
    if cfg.strategy not in STRATEGIES:
        raise ValueError(f"không có chiến lược {cfg.strategy}")
    if cfg.solver not in SOLVERS:
        raise ValueError(f"không có SAT solver {cfg.solver}")
    solver_name = SOLVERS[cfg.solver]

    if cfg.strategy == "incremental":
        return _solve_incremental(
            inst, cfg, encoding_cls, solver_name, lb0=lb0, ub0=ub0, deadline=deadline
        )
    f = _Fresh(inst, cfg, encoding_cls, solver_name, deadline)
    if cfg.strategy == "lb_up":
        return _solve_lb_up(f, lb0, ub0)
    if cfg.strategy == "ub_down":
        return _solve_ub_down(f, lb0, ub0)
    return _solve_bisect(f, lb0, ub0)
