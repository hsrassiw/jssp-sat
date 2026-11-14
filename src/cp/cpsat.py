"""Mô hình CP-SAT của OR-Tools."""
from __future__ import annotations

import time
from ortools.sat.python import cp_model

from src.common.bounds import time_windows
from src.common.instance import Instance, Schedule
from src.common.result import FEAS, NOSOL, OPT, Config, Result


def solve(inst: Instance, cfg: Config, *, lb0: int, ub0: int, deadline: float) -> Result:
    res = Result.new(inst.name, cfg)
    res.lb0 = lb0
    res.ub0 = ub0

    t_enc_start = time.perf_counter()

    # Khởi tạo mô hình CP-SAT
    model = cp_model.CpModel()
    es, ls = time_windows(inst, ub0)

    # 1. Biến quyết định (Start, End, Interval)
    all_tasks: dict[tuple[int, int], tuple[cp_model.IntVar, cp_model.IntVar, cp_model.IntervalVar]] = {}
    machine_intervals: dict[int, list[cp_model.IntervalVar]] = {m: [] for m in range(inst.n_machines)}

    for j, k, op in inst.ops():
        duration = op.duration
        es_jk, ls_jk = es[j][k], ls[j][k]

        start_var = model.NewIntVar(es_jk, ls_jk, f"start_{j}_{k}")
        end_var = model.NewIntVar(es_jk + duration, ls_jk + duration, f"end_{j}_{k}")
        interval_var = model.NewIntervalVar(start_var, duration, end_var, f"interval_{j}_{k}")

        all_tasks[(j, k)] = (start_var, end_var, interval_var)
        machine_intervals[op.machine].append(interval_var)

    # 2. Ràng buộc thứ tự công đoạn trong từng Job (Precedence Constraints)
    for j, job in enumerate(inst.jobs):
        for k in range(len(job) - 1):
            start_next, _, _ = all_tasks[(j, k + 1)]
            _, end_curr, _ = all_tasks[(j, k)]
            model.Add(start_next >= end_curr)

    # 3. Ràng buộc không chồng lấp trên từng Máy (No-Overlap Constraints)
    for m in range(inst.n_machines):
        model.AddNoOverlap(machine_intervals[m])

    # 4. Hàm mục tiêu: Tối thiểu hóa Makespan (Cmax)
    makespan = model.NewIntVar(lb0, ub0, "makespan")
    job_ends = [all_tasks[(j, len(inst.jobs[j]) - 1)][1] for j in range(inst.n_jobs)]
    model.AddMaxEquality(makespan, job_ends)
    model.Minimize(makespan)

    res.encode_time_s = time.perf_counter() - t_enc_start
    proto = model.Proto()
    res.n_vars = len(proto.variables)
    res.n_clauses = len(proto.constraints)

    # 5. Cấu hình Solver & Giới hạn thời gian
    solver = cp_model.CpSolver()
    solver.parameters.num_workers = 1
    remaining_time = max(0.001, deadline - time.perf_counter())
    solver.parameters.max_time_in_seconds = float(remaining_time)

    res.n_calls = 1
    t_solve_start = time.perf_counter()
    status_code = solver.Solve(model)
    res.solve_time_s = time.perf_counter() - t_solve_start

    # 6. Trích xuất kết quả
    if status_code in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        res.cmax = int(solver.ObjectiveValue())
        if status_code == cp_model.OPTIMAL:
            res.status = OPT
            res.bound = res.cmax
        else:
            res.status = FEAS
            res.bound = max(lb0, int(solver.BestObjectiveBound()))

        # Giải mã lịch biểu (Schedule)
        schedule: Schedule = []
        for j, job in enumerate(inst.jobs):
            job_schedule = [solver.Value(all_tasks[(j, k)][0]) for k in range(len(job))]
            schedule.append(job_schedule)
        res.schedule = schedule
    else:
        res.status = NOSOL
        res.cmax = None
        res.bound = lb0

    return res