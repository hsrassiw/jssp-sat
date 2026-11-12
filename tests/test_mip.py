import itertools
import time
import pytest
from src.common.instance import Instance, makespan
from src.common.data import ft06
from src.common.verify import verify
from src.common.bounds import lower_bound
from src.common.result import Config, OPT, NOSOL
from src.mip.bigm import formulate


def solver(name):
    pytest.importorskip('gurobipy' if name=='gurobi' else 'cplex')
    if name=='gurobi':from src.mip.gurobi_mip import solve
    else:from src.mip.cplex_mip import solve
    return solve


@pytest.mark.parametrize('name',['gurobi','cplex'])
def test_ft06_loose_ub(name):
    # Không dùng UB=55: solver phải tự tìm tối ưu từ horizon tuần tự 197.
    res=solver(name)(ft06(),Config('MIP',solver=name),lb0=47,ub0=197,deadline=time.perf_counter()+30)
    assert res.status==OPT and res.cmax==res.bound==55
    assert verify(ft06(),res.schedule)==[]
    assert res.n_vars==127 and res.n_clauses==216


@pytest.mark.parametrize('name',['gurobi','cplex'])
def test_deadline_expired(name):
    res=solver(name)(ft06(),Config('MIP',solver=name),lb0=47,ub0=55,deadline=time.perf_counter()-1)
    assert res.status==NOSOL and res.schedule is None


@pytest.mark.parametrize('rows',[
    [[(0,2),(1,1)],[(1,2),(0,1)]],
    [[(0,0),(1,2)],[(1,1),(0,2)]],
    [[(0,1),(0,2)],[(0,1),(1,1)]],
])
def test_mip_matches_exhaustive_small(rows):
    inst=Instance.from_lists('tiny',rows);h=inst.total_duration()
    optimum=h
    for flat in itertools.product(range(h+1),repeat=4):
        schedule=[list(flat[:2]),list(flat[2:])]
        if verify(inst,schedule)==[]:optimum=min(optimum,makespan(inst,schedule))
    for name in ['gurobi','cplex']:
        result=solver(name)(inst,Config('MIP',solver=name),lb0=lower_bound(inst),ub0=h,deadline=time.perf_counter()+10)
        assert result.status==OPT and result.cmax==optimum
