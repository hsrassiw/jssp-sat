"""Encoding E1 (Crawford), theo mục 2 paper Koshimura 2010."""
from __future__ import annotations

from src.common.instance import Schedule
from src.sat.base import Clause, SatEncoding


class E1Crawford(SatEncoding):
    name = "E1"

    def build(self) -> None:
        self.pr: dict[tuple[int, int, int, int], int] = {}
        self.sa: dict[tuple[int, int, int], int] = {}
        self.eb: dict[tuple[int, int, int], int] = {}

        L = self.horizon

        if L < 0:
            v = self.new_var()
            self.add([v])
            self.add([-v])
            return

        # Allocate variables sa_{i, t}^l and eb_{i, t}^l for 0 <= t <= L
        for l, job in enumerate(self.inst.jobs):
            for i in range(len(job)):
                for t in range(L + 1):
                    self.sa[(l, i, t)] = self.new_var()
                    self.eb[(l, i, t)] = self.new_var()

        # Rule 1: O_i^l precedes O_{i+1}^l (1 <= l <= n, 1 <= i < q_l)
        for l, job in enumerate(self.inst.jobs):
            for i in range(len(job) - 1):
                v = self.new_var()
                self.pr[(l, i, l, i + 1)] = v
                self.add([v])

        # Rule 2: If M_{O_i^l} == M_{O_j^k}, then pr_{i,j}^{l,k} or pr_{j,i}^{k,l} (1 <= l < k <= n)
        for m in range(self.inst.n_machines):
            m_ops = self.inst.machine_ops(m)
            for idx1 in range(len(m_ops)):
                for idx2 in range(idx1 + 1, len(m_ops)):
                    l, i = m_ops[idx1]
                    k, j = m_ops[idx2]
                    if l == k:
                        continue
                    if l > k:
                        l, i, k, j = k, j, l, i
                    v1 = self.new_var()
                    v2 = self.new_var()
                    self.pr[(l, i, k, j)] = v1
                    self.pr[(k, j, l, i)] = v2
                    self.add([v1, v2])

        # Rule 3: sa_{i, t}^l for t = sum_{u=1}^{i-1} p_u^l
        for l, job in enumerate(self.inst.jobs):
            head = 0
            for i, op in enumerate(job):
                t = head
                if 0 <= t <= L:
                    self.add([self.sa[(l, i, t)]])
                head += op.duration

        # Rule 4: eb_{i, t}^l for t = L - sum_{u=i+1}^{q_l} p_u^l
        for l, job in enumerate(self.inst.jobs):
            total_dur = sum(op.duration for op in job)
            tail = total_dur
            for i, op in enumerate(job):
                tail -= op.duration
                t = L - tail
                if 0 <= t <= L:
                    self.add([self.eb[(l, i, t)]])

        # Rule 5: sa_{i, t}^l -> sa_{i, t-1}^l (1 <= t <= L)
        for l, job in enumerate(self.inst.jobs):
            for i in range(len(job)):
                for t in range(1, L + 1):
                    self.add([-self.sa[(l, i, t)], self.sa[(l, i, t - 1)]])

        # Rule 6: eb_{i, t}^l -> eb_{i, t+1}^l (0 <= t < L)
        for l, job in enumerate(self.inst.jobs):
            for i in range(len(job)):
                for t in range(0, L):
                    self.add([-self.eb[(l, i, t)], self.eb[(l, i, t + 1)]])

        # Rule 7: sa_{i, t}^l -> not eb_{i, t + p_i^l - 1}^l (0 <= t <= L - p_i^l + 1)
        for l, job in enumerate(self.inst.jobs):
            for i, op in enumerate(job):
                p = op.duration
                for t in range(0, L - p + 2):
                    if 0 <= t <= L:
                        t_eb = t + p - 1
                        if 0 <= t_eb <= L:
                            self.add([-self.sa[(l, i, t)], -self.eb[(l, i, t_eb)]])

        # Rule 8: sa_{i, t}^l and pr_{i, j}^{l, k} -> sa_{j, t + p_i^l}^k (0 <= t <= L - p_i^l)
        for (l, i, k, j), pr_var in self.pr.items():
            p_i = self.inst.jobs[l][i].duration
            for t in range(0, L - p_i + 1):
                if 0 <= t <= L:
                    t_next = t + p_i
                    if 0 <= t_next <= L:
                        self.add([-self.sa[(l, i, t)], -pr_var, self.sa[(k, j, t_next)]])

    def tighten(self, c: int) -> list[Clause]:
        if c < 0:
            v = self.new_var()
            return [[v], [-v]]

        clauses: list[Clause] = []
        for l, job in enumerate(self.inst.jobs):
            last_i = len(job) - 1
            p_last = job[last_i].duration

            if c <= self.horizon:
                clauses.append([self.eb[(l, last_i, c)]])

            t_forbid = c - p_last + 1
            if t_forbid <= 0:
                v = self.new_var()
                clauses.append([v])
                clauses.append([-v])
            elif t_forbid <= self.horizon:
                clauses.append([-self.sa[(l, last_i, t_forbid)]])

        return clauses

    def decode(self, model: list[int]) -> Schedule:
        true_vars = {lit for lit in model if lit > 0}
        schedule: Schedule = []
        for l, job in enumerate(self.inst.jobs):
            row: list[int] = []
            for i in range(len(job)):
                start_t = 0
                for t in range(self.horizon, -1, -1):
                    if self.sa[(l, i, t)] in true_vars:
                        start_t = t
                        break
                row.append(start_t)
            schedule.append(row)
        return schedule