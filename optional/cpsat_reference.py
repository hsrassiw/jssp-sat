"""CP-SAT tham chiếu để test batch khi chưa ghép code của Quang.
Copy vào src/cp/cpsat.py CHỈ nếu file đó vẫn là stub.
"""
from __future__ import annotations
import time
from src.common.bounds import time_windows
from src.common.result import Result, ERR, FEAS, OPT
from src.mip.bigm import integer_bound


def solve(inst,cfg,*,lb0,ub0,deadline):
    res=Result.new(inst.name,cfg);res.bound=lb0
    if time.perf_counter()>=deadline:return res
    t0=time.perf_counter()
    from ortools.sat.python import cp_model
    model=cp_model.CpModel();es,ls=time_windows(inst,ub0)
    starts={};ends={};machines=[[] for _ in range(inst.n_machines)]
    for j,k,op in inst.ops():
        s=model.new_int_var(es[j][k],ls[j][k],f's_{j}_{k}')
        e=model.new_int_var(es[j][k]+op.duration,ls[j][k]+op.duration,f'e_{j}_{k}')
        interval=model.new_interval_var(s,op.duration,e,f'o_{j}_{k}')
        starts[j,k]=s;ends[j,k]=e;machines[op.machine].append(interval)
    for intervals in machines:model.add_no_overlap(intervals)
    for j,job in enumerate(inst.jobs):
        for k in range(1,len(job)):model.add(starts[j,k]>=ends[j,k-1])
    cmax=model.new_int_var(lb0,ub0,'Cmax')
    model.add_max_equality(cmax,[ends[j,len(job)-1] for j,job in enumerate(inst.jobs)])
    model.minimize(cmax)
    res.n_vars=len(model.proto.variables);res.n_clauses=len(model.proto.constraints)
    res.encode_time_s=time.perf_counter()-t0
    remaining=deadline-time.perf_counter()
    if remaining<=0:return res
    solver=cp_model.CpSolver();solver.parameters.num_search_workers=1
    solver.parameters.random_seed=0;solver.parameters.max_time_in_seconds=remaining
    t1=time.perf_counter();status=solver.solve(model);res.solve_time_s=time.perf_counter()-t1
    if status in (cp_model.INFEASIBLE,cp_model.MODEL_INVALID):
        res.status=ERR;res.note='CP-SAT báo infeasible hoặc model invalid';return res
    res.bound=integer_bound(solver.best_objective_bound,lb0)
    if status in (cp_model.OPTIMAL,cp_model.FEASIBLE):
        res.schedule=[[solver.value(starts[j,k]) for k in range(len(job))] for j,job in enumerate(inst.jobs)]
        res.cmax=solver.value(cmax)
        if status==cp_model.OPTIMAL:res.bound=res.cmax
        res.status=OPT if res.bound==res.cmax else FEAS
    return res
