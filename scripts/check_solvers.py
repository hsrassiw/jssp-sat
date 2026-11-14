"""Kiểm tra solver tại máy chạy, --full kiểm tra vượt giới hạn Community."""
import argparse
import importlib.metadata
import sys


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--full',action='store_true')
    p.add_argument('--solvers',nargs='+',choices=['gurobi','cplex','cpsat'],default=['gurobi','cplex','cpsat'])
    args=p.parse_args();failed=False
    for name in args.solvers:
        try:
            if name=='gurobi':
                import gurobipy as gp
                with gp.Env(empty=True) as env:
                    env.setParam('OutputFlag',0);env.start()
                    with gp.Model(env=env) as m:
                        n=2101 if args.full else 2
                        x=m.addVars(n,vtype=gp.GRB.BINARY)
                        m.addConstr(x.sum()>=1);m.setObjective(x.sum())
                        m.Params.Threads=1;m.Params.TimeLimit=10;m.optimize()
                        if m.Status!=gp.GRB.OPTIMAL:raise RuntimeError('Smoke model không tối ưu')
                version=importlib.metadata.version('gurobipy')
            elif name=='cplex':
                import cplex
                with cplex.Cplex() as m:
                    m.set_log_stream(None);m.set_results_stream(None)
                    n=1101 if args.full else 2
                    m.variables.add(obj=[1.0]*n,lb=[0.0]*n,ub=[1.0]*n,types='B'*n)
                    m.linear_constraints.add(lin_expr=[cplex.SparsePair(ind=list(range(n)),val=[1.0]*n)],senses='G',rhs=[1.0])
                    m.parameters.threads.set(1);m.parameters.timelimit.set(10);m.solve()
                    if not m.solution.is_primal_feasible():raise RuntimeError('Không có nghiệm smoke model')
                version=cplex.__version__
            else:
                from ortools.sat.python import cp_model
                m=cp_model.CpModel();x=m.new_bool_var('x');m.add(x==1)
                s=cp_model.CpSolver();s.parameters.num_search_workers=1
                if s.solve(m)!=cp_model.OPTIMAL:raise RuntimeError('CP-SAT smoke lỗi')
                version=importlib.metadata.version('ortools')
            print(f'OK {name} version={version} mode={"size-check" if args.full else "small"}')
        except Exception as exc:
            failed=True;print(f'FAIL {name}: {type(exc).__name__}: {exc}',file=sys.stderr)
    return 1 if failed else 0


if __name__=='__main__':raise SystemExit(main())
