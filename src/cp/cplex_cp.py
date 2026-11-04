"""Mô hình CPLEX CP Optimizer cho JSSP."""
from __future__ import annotations

import time
from pathlib import Path

from docplex.cp.model import CpoModel

from src.common.bounds import lower_bound, time_windows, upper_bound
from src.common.data import load
from src.common.instance import Instance, Schedule
from src.common.result import FEAS, NOSOL, OPT, Config, Result


def solve(inst: Instance, cfg: Config, *, lb0: int, ub0: int, deadline: float) -> Result:

    if cfg is None:
        cfg = Config(method="CP", solver="cplex")

    if lb0 is None:
        lb0 = lower_bound(inst)
    if ub0 is None:
        ub0, _ = upper_bound(inst)
    if deadline is None:
        deadline = time.perf_counter() + 60.0

    res = Result.new(inst.name, cfg)
    res.lb0 = lb0
    res.ub0 = ub0

    t_enc_start = time.perf_counter()

    # Khởi tạo mô hình CPLEX CP
    mdl = CpoModel(name=inst.name)
    threads = 1
    #cp_path = "/opt/ibm/ILOG/CPLEX_Studio222/cpoptimizer/bin/x86-64_linux/cpoptimizer"
    es, ls = time_windows(inst, ub0)

    # 1. Biến khoảng thời gian (Interval Variables)
    tasks: dict[tuple[int, int], CpoModel.interval_var] = {}
    machine_tasks: dict[int, list] = {m: [] for m in range(inst.n_machines)}

    for j, k, op in inst.ops():
        duration = op.duration
        es_jk, ls_jk = es[j][k], ls[j][k]

        # Giới hạn thời gian bắt đầu trong cửa sổ [es, ls]
        var = mdl.interval_var(
            size=duration,
            start=(es_jk, ls_jk),
            name=f"op_{j}_{k}",
        )
        tasks[(j, k)] = var
        machine_tasks[op.machine].append(var)

    # 2. Ràng buộc thứ tự công đoạn trong cùng Job (Precedence)
    for j, job in enumerate(inst.jobs):
        for k in range(len(job) - 1):
            mdl.add(mdl.end_before_start(tasks[(j, k)], tasks[(j, k + 1)]))

    # 3. Ràng buộc không chồng lấp trên từng Máy (No-Overlap)
    for m in range(inst.n_machines):
        mdl.add(mdl.no_overlap(machine_tasks[m]))

    # 4. Hàm mục tiêu: Tối thiểu hóa Makespan (Cmax)
    job_ends = [mdl.end_of(tasks[(j, len(inst.jobs[j]) - 1)]) for j in range(inst.n_jobs)]
    makespan = mdl.max(job_ends)
    mdl.add(mdl.minimize(makespan))

    res.encode_time_s = time.perf_counter() - t_enc_start

    # 5. Cấu hình Solver & Giới hạn thời gian
    remaining_time = max(0.001, deadline - time.perf_counter())
    res.n_calls = 1

    t_solve_start = time.perf_counter()
    sol = mdl.solve(
        TimeLimit=remaining_time,
        LogVerbosity="Quiet"
    )
    res.solve_time_s = time.perf_counter() - t_solve_start

    # 6. Trích xuất kết quả
    if sol and sol.is_solution():
        cmax_val = int(sol.get_objective_value())
        res.cmax = cmax_val

        status_str = sol.get_solve_status()
        if status_str == "Optimal":
            res.status = OPT
            res.bound = cmax_val
        else:
            res.status = FEAS
            obj_bound = sol.get_objective_bound()
            res.bound = int(obj_bound) if obj_bound is not None else lb0

        # Giải mã lịch biểu (Schedule)
        schedule: Schedule = []
        for j, job in enumerate(inst.jobs):
            job_schedule = [
                sol.get_var_solution(tasks[(j, k)]).get_start()
                for k in range(len(job))
            ]
            schedule.append(job_schedule)
        res.schedule = schedule
    else:
        res.status = NOSOL
        res.cmax = None
        res.bound = None

    return res