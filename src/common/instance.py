"""Instance và Schedule. Job, bước, máy đều đánh số từ 0."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, NamedTuple

# start[j][k] = giờ bắt đầu bước k của job j
Schedule = list[list[int]]


class Op(NamedTuple):
    machine: int
    duration: int


@dataclass(frozen=True)
class Instance:
    name: str
    n_jobs: int
    n_machines: int
    jobs: tuple[tuple[Op, ...], ...]

    @classmethod
    def from_lists(cls, name: str, rows: list[list[tuple[int, int]]]) -> Instance:
        jobs = tuple(tuple(Op(m, d) for m, d in row) for row in rows)
        n_machines = 1 + max(op.machine for job in jobs for op in job)
        return cls(name, len(jobs), n_machines, jobs)

    def ops(self) -> Iterator[tuple[int, int, Op]]:
        for j, job in enumerate(self.jobs):
            for k, op in enumerate(job):
                yield j, k, op

    def machine_ops(self, m: int) -> list[tuple[int, int]]:
        return [(j, k) for j, k, op in self.ops() if op.machine == m]

    def total_duration(self) -> int:
        return sum(op.duration for _, _, op in self.ops())


def makespan(inst: Instance, start: Schedule) -> int:
    return max(start[j][-1] + inst.jobs[j][-1].duration for j in range(inst.n_jobs))
