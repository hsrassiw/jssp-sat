"""MILP big-M, Gurobi một luồng; không lấy lịch greedy làm nghiệm solver."""
from __future__ import annotations
import time
from src.common.result import Result
from src.mip.bigm import formulate, integer_bound, finish


def solve(inst, cfg, *, lb0, ub0, deadline):
    res=Result.new(inst.name,cfg);res.bound=lb0
    if time.perf_counter()>=deadline:return res
    t0=time.perf_counter()
    import gurobipy as gp
    from gurobipy import GRB
    f=formulate(inst,lb0,ub0)
    with gp.Env(empty=True) as env:
        env.setParam('OutputFlag',0);env.start()
        with gp.Model(inst.name,env=env) as model:
            model.Params.Threads=1
            model.Params.Seed=0
            model.Params.MIPGap=0
            model.Params.MIPGapAbs=0
            variables=[model.addVar(lb=lo,ub=hi,vtype=kind,name=name) for name,lo,hi,kind in zip(f.names,f.lbs,f.ubs,f.types)]
            for indices,coefficients,rhs in f.rows:
                model.addConstr(gp.LinExpr(coefficients,[variables[i] for i in indices])>=rhs)
            model.setObjective(variables[f.cmax],GRB.MINIMIZE)
            model.update()
            res.n_vars=model.NumVars;res.n_clauses=model.NumConstrs;res.n_calls=1
            res.encode_time_s=time.perf_counter()-t0
            remaining=deadline-time.perf_counter()
            if remaining<=0:return res
            model.Params.TimeLimit=remaining
            t1=time.perf_counter();model.optimize();res.solve_time_s=time.perf_counter()-t1
            bound=integer_bound(model.ObjBound,lb0)
            values=[v.X for v in variables] if model.SolCount>0 else None
            return finish(res,inst,f,values,bound,optimal=model.Status==GRB.OPTIMAL,
                          bad_status=model.Status in (GRB.INFEASIBLE,GRB.INF_OR_UNBD,GRB.UNBOUNDED,GRB.NUMERIC))
