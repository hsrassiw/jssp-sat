"""LB, UB và ES/LS (bản đơn giản)."""
from __future__ import annotations

from src.common.instance import Instance, Schedule


def lower_bound(inst: Instance) -> int:
    job_len = max(sum(op.duration for op in job) for job in inst.jobs)
    load = [0] * inst.n_machines
    for _, _, op in inst.ops():
        load[op.machine] += op.duration
    return max(job_len, max(load))


def upper_bound(inst: Instance) -> tuple[int, Schedule]:
    # chạy lần lượt từng bước, trả về cả lịch
    start: Schedule = []
    t = 0
    for job in inst.jobs:
        row = []
        for op in job:
            row.append(t)
            t += op.duration
        start.append(row)
    return t, start


def time_windows(inst: Instance, horizon: int) -> tuple[Schedule, Schedule]:
    es: Schedule = []
    ls: Schedule = []
    for job in inst.jobs:
        durations = [op.duration for op in job]
        total = sum(durations)
        head = 0
        es_row, ls_row = [], []
        for d in durations:
            es_row.append(head)
            ls_row.append(horizon - (total - head))
            head += d
        es.append(es_row)
        ls.append(ls_row)
    return es, ls
