"""Kiểm tra lịch có hợp lệ không."""
from __future__ import annotations

from src.common.instance import Instance, Schedule


def verify(inst: Instance, start: Schedule) -> list[str]:
    # trả về list lỗi, rỗng là lịch đúng
    errors: list[str] = []

    if len(start) != inst.n_jobs:
        return ["sai số job trong lịch"]
    for j in range(inst.n_jobs):
        if len(start[j]) != len(inst.jobs[j]):
            return [f"sai số bước của job {j} trong lịch"]

    # thứ tự trong job
    for j, k, op in inst.ops():
        if start[j][k] < 0:
            errors.append(f"bước ({j},{k}) bắt đầu lúc âm {start[j][k]}")
        if k > 0:
            prev_end = start[j][k - 1] + inst.jobs[j][k - 1].duration
            if start[j][k] < prev_end:
                errors.append(f"job {j}: bước {k} bắt đầu trước khi bước {k - 1} xong")

    # không trùng giờ trên cùng máy
    for m in range(inst.n_machines):
        ops = inst.machine_ops(m)
        for a in range(len(ops)):
            for b in range(a + 1, len(ops)):
                j1, k1 = ops[a]
                j2, k2 = ops[b]
                start1 = start[j1][k1]
                end1 = start1 + inst.jobs[j1][k1].duration
                start2 = start[j2][k2]
                end2 = start2 + inst.jobs[j2][k2].duration
                if start1 < end2 and start2 < end1:
                    errors.append(f"máy {m}: bước ({j1},{k1}) và ({j2},{k2}) trùng giờ")

    return errors
