"""Mô hình chung: s nguyên, Cmax nguyên, y nhị phân; M theo miền ES/LS."""
from __future__ import annotations
import math
from itertools import combinations
from dataclasses import dataclass
from src.common.bounds import time_windows
from src.common.instance import makespan
from src.common.verify import verify
from src.common.result import ERR, FEAS, NOSOL, OPT

@dataclass
class Formulation:
    names: list
    lbs: list
    ubs: list
    types: list
    rows: list  # (indices, coefficients, rhs), tất cả là >=
    starts: dict
    cmax: int


def formulate(inst, lb0, ub0):
    es, ls = time_windows(inst, ub0)
    f = Formulation([], [], [], [], [], {}, 0)
    def var(name, lb, ub, kind):
        if lb > ub: raise ValueError('Miền biến rỗng; kiểm tra UB cache')
        i=len(f.names); f.names.append(name); f.lbs.append(lb); f.ubs.append(ub); f.types.append(kind)
        return i
    for j,k,op in inst.ops(): f.starts[j,k]=var(f's_{j}_{k}',es[j][k],ls[j][k],'I')
    f.cmax=var('Cmax',lb0,ub0,'I')
    for j,job in enumerate(inst.jobs):
        for k in range(1,len(job)):
            f.rows.append(([f.starts[j,k],f.starts[j,k-1]],[1,-1],job[k-1].duration))
        f.rows.append(([f.cmax,f.starts[j,len(job)-1]],[1,-1],job[-1].duration))
    for m in range(inst.n_machines):
        for a,b in combinations(inst.machine_ops(m),2):
            if a[0]==b[0]: continue  # đã được quyết định bởi thứ tự job
            ja,ka=a; jb,kb=b
            pa=inst.jobs[ja][ka].duration; pb=inst.jobs[jb][kb].duration
            y=var(f'y_{ja}_{ka}_{jb}_{kb}',0,1,'B')
            mab=max(0,ls[ja][ka]+pa-es[jb][kb])
            mba=max(0,ls[jb][kb]+pb-es[ja][ka])
            # y=1: a trước b; y=0: b trước a.
            f.rows.append(([f.starts[b],f.starts[a],y],[1,-1,-mab],pa-mab))
            f.rows.append(([f.starts[a],f.starts[b],y],[1,-1,mba],pb))
    return f


def integer_bound(value, lb0):
    if value is None or not math.isfinite(value) or abs(value)>1e18:return lb0
    return max(lb0, math.ceil(value-1e-6))


def finish(res, inst, form, values, bound, *, optimal=False, bad_status=False):
    res.bound=bound
    if bad_status:
        res.status=ERR;res.note='Solver báo mô hình infeasible/unbounded/numerical; kiểm tra mô hình, cận và log.'
        return res
    if values is None:
        res.status=NOSOL
        return res
    raw=[values[form.starts[j,k]] for j,k,_ in inst.ops()]
    if any(not math.isfinite(v) or abs(v-round(v))>1e-4 for v in raw):
        res.status=ERR;res.note='Nghiệm trả về không nguyên trong dung sai';return res
    schedule=[[int(round(values[form.starts[j,k]])) for k in range(len(job))] for j,job in enumerate(inst.jobs)]
    errors=verify(inst,schedule)
    if errors:
        res.status=ERR;res.note='; '.join(errors[:3]);return res
    res.schedule=schedule;res.cmax=makespan(inst,schedule)
    if optimal:res.bound=res.cmax
    if res.bound>res.cmax:
        res.status=ERR;res.note='Cận solver lớn hơn makespan';res.schedule=None;res.cmax=None;return res
    res.status=OPT if res.bound==res.cmax else FEAS
    return res
