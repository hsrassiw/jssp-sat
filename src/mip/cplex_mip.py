"""MILP big-M, CPLEX Python API một luồng (bản đầy đủ trên VM)."""
from __future__ import annotations
import time
from src.common.result import Result
from src.mip.bigm import formulate, integer_bound, finish


def solve(inst, cfg, *, lb0, ub0, deadline):
    res=Result.new(inst.name,cfg);res.bound=lb0
    if time.perf_counter()>=deadline:return res
    t0=time.perf_counter()
    import cplex
    f=formulate(inst,lb0,ub0)
    with cplex.Cplex() as model:
        model.set_log_stream(None);model.set_results_stream(None);model.set_warning_stream(None)
        model.parameters.threads.set(1)
        model.parameters.randomseed.set(0)
        model.parameters.clocktype.set(2)  # elapsed wall time
        model.parameters.mip.tolerances.mipgap.set(0)
        model.parameters.mip.tolerances.absmipgap.set(0)
        obj=[0.0]*len(f.names);obj[f.cmax]=1.0
        model.objective.set_sense(model.objective.sense.minimize)
        model.variables.add(obj=obj,lb=f.lbs,ub=f.ubs,types=''.join(f.types),names=f.names)
        model.linear_constraints.add(lin_expr=[cplex.SparsePair(ind=i,val=v) for i,v,_ in f.rows],
                                     senses='G'*len(f.rows),rhs=[r for _,_,r in f.rows])
        res.n_vars=model.variables.get_num();res.n_clauses=model.linear_constraints.get_num()
        res.encode_time_s=time.perf_counter()-t0
        remaining=deadline-time.perf_counter()
        if remaining<=0:return res
        model.parameters.timelimit.set(remaining)
        t1=time.perf_counter();model.solve();res.solve_time_s=time.perf_counter()-t1
        status=model.solution.get_status();ss=model.solution.status
        optimal=status==ss.MIP_optimal
        bad=status in {getattr(ss,n,-999) for n in ['MIP_infeasible','MIP_unbounded','MIP_infeasible_or_unbounded','infeasible','unbounded','infeasible_or_unbounded']}
        bound=integer_bound(model.solution.MIP.get_best_objective(),lb0)
        values=model.solution.get_values() if model.solution.is_primal_feasible() else None
        return finish(res,inst,f,values,bound,optimal=optimal,bad_status=bad)
