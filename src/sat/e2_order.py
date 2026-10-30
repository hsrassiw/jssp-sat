"""Encoding E2 theo mục 5.1 paper Nguyen et al., bỏ SAT-6 đến SAT-8.

S[i, t]: bước i bắt đầu lúc >= t
X[i, t]: bước i bắt đầu đúng lúc t
"""
from __future__ import annotations

from src.common.instance import Schedule
from src.sat.base import Clause, SatEncoding


class E2Order(SatEncoding):
    name = "E2"

    def build(self) -> None:
        self.s: dict[tuple[int, int, int], int] = {}
        self.x: dict[tuple[int, int, int], int] = {}
        self._infeasible = False

        # horizon quá nhỏ thì cho UNSAT luôn
        for j, k, _ in self.inst.ops():
            if self.es[j][k] > self.ls[j][k]:
                self._infeasible = True
                v = self.new_var()
                self.add([v])
                self.add([-v])
                return

        for j, k, _ in self.inst.ops():
            es, ls = self.es[j][k], self.ls[j][k]
            for t in range(es, ls + 2):
                self.s[(j, k, t)] = self.new_var()
            for t in range(es, ls + 1):
                self.x[(j, k, t)] = self.new_var()

        for j, k, _ in self.inst.ops():
            es, ls = self.es[j][k], self.ls[j][k]
            # SAT-1
            self.add([self.s[(j, k, es)]])
            self.add([-self.s[(j, k, ls + 1)]])

            for t in range(es, ls + 1):
                s_curr = self.s[(j, k, t)]
                s_next = self.s[(j, k, t + 1)]
                x_curr = self.x[(j, k, t)]

                # SAT-2
                self.add([-s_next, s_curr])

                # SAT-3
                self.add([-x_curr, s_curr])
                self.add([-x_curr, -s_next])
                self.add([-s_curr, s_next, x_curr])

        # SAT-4: thứ tự trong job
        for j, job in enumerate(self.inst.jobs):
            for k in range(len(job) - 1):
                d = job[k].duration
                es, ls = self.es[j][k], self.ls[j][k]
                es_next, ls_next = self.es[j][k + 1], self.ls[j][k + 1]
                for t in range(es, ls + 1):
                    t_next = t + d
                    if t_next < es_next:
                        continue
                    if t_next <= ls_next:
                        self.add([-self.x[(j, k, t)], self.s[(j, k + 1, t_next)]])
                    else:
                        self.add([-self.x[(j, k, t)]])

        # SAT-5: không trùng máy
        for m in range(self.inst.n_machines):
            m_ops = self.inst.machine_ops(m)
            for j1, k1 in m_ops:
                d1 = self.inst.jobs[j1][k1].duration
                es1, ls1 = self.es[j1][k1], self.ls[j1][k1]
                for j2, k2 in m_ops:
                    if (j1, k1) == (j2, k2):
                        continue
                    d2 = self.inst.jobs[j2][k2].duration
                    es2, ls2 = self.es[j2][k2], self.ls[j2][k2]
                    for t in range(es1, ls1 + 1):
                        t_after = t + d1
                        t_before = t - d2 + 1
                        if t_after <= es2 or t_before > ls2:
                            continue
                        clause = [-self.x[(j1, k1, t)]]
                        if t_after <= ls2:
                            clause.append(self.s[(j2, k2, t_after)])
                        if t_before > es2:
                            clause.append(-self.s[(j2, k2, t_before)])
                        self.add(clause)

    def tighten(self, c: int) -> list[Clause]:
        if self._infeasible:
            return []
        clauses: list[Clause] = []
        for j, job in enumerate(self.inst.jobs):
            k_last = len(job) - 1
            d_last = job[k_last].duration
            es, ls = self.es[j][k_last], self.ls[j][k_last]
            # bước cuối phải bắt đầu <= c - d_last
            t_forbid = c - d_last + 1
            if t_forbid <= es:
                clauses.append([-self.s[(j, k_last, es)]])
            elif t_forbid <= ls:
                clauses.append([-self.s[(j, k_last, t_forbid)]])
        return clauses

    def decode(self, model: list[int]) -> Schedule:
        true_vars = {lit for lit in model if lit > 0}
        schedule: Schedule = []
        for j, job in enumerate(self.inst.jobs):
            row: list[int] = []
            for k in range(len(job)):
                es, ls = self.es[j][k], self.ls[j][k]
                start_t = es
                for t in range(es, ls + 1):
                    if self.x[(j, k, t)] in true_vars:
                        start_t = t
                        break
                else:
                    for t in range(ls, es - 1, -1):
                        if self.s[(j, k, t)] in true_vars:
                            start_t = t
                            break
                row.append(start_t)
            schedule.append(row)
        return schedule
