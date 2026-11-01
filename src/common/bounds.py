"""LB, UB và ES/LS (bản đơn giản)."""
from __future__ import annotations

import random
import time
from bisect import insort

from src.common.instance import Instance, Schedule


def lower_bound(inst: Instance) -> int:
    job_len = max(sum(op.duration for op in job) for job in inst.jobs)
    load = [0] * inst.n_machines
    for _, _, op in inst.ops():
        load[op.machine] += op.duration
    return max(job_len, max(load))

def _earliest_gap(intervals, ready: int, duration: int) -> int:
    """Tìm cả khoảng trống ở giữa các bước đã xếp trên máy."""
    t = ready
    for begin, end in intervals:
        if t + duration <= begin:
            break
        t = max(t, end)
    return t

def upper_bound(
    inst: Instance, *, time_limit: float = 5.0, seed: int = 0,
    trials: int | None = None,
) -> tuple[int, Schedule]:
    """Algorithm 1 cho JSSP thường: chọn job ngẫu nhiên, chèn sớm nhất.

    Mặc định tìm trong 5 giây. trials dùng cho test/tái lập chính xác,
    thay thế time_limit bằng số lượt cố định. Không dùng BKS để chọn lịch.
    Luôn có lịch tuần tự dự phòng, kể cả khi ngân sách bằng 0.
    """
    if time_limit < 0 or (trials is not None and trials < 0):
        raise ValueError("time_limit và trials phải không âm")
    deadline = time.perf_counter() + time_limit
    best: Schedule = []
    ub = 0
    for job in inst.jobs:
        row = []
        for op in job:
            row.append(ub)
            ub += op.duration
        best.append(row)
    rng = random.Random(seed)
    count = 0
    while (count < trials if trials is not None else time.perf_counter() < deadline):
        start = [[0] * len(job) for job in inst.jobs]
        next_op = [0] * inst.n_jobs
        ready = [0] * inst.n_jobs
        machines = [[] for _ in range(inst.n_machines)]
        active = list(range(inst.n_jobs))
        complete = True
        while active:
            if trials is None and time.perf_counter() >= deadline:
                complete = False
                break
            j = rng.choice(active)
            k = next_op[j]
            op = inst.jobs[j][k]
            begin = _earliest_gap(machines[op.machine], ready[j], op.duration)
            end = begin + op.duration
            start[j][k] = begin
            ready[j] = end
            insort(machines[op.machine], (begin, end))
            next_op[j] += 1
            if next_op[j] == len(inst.jobs[j]):
                active.remove(j)
        count += 1
        if complete and max(ready) < ub:
            ub, best = max(ready), start
    return ub, best


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
