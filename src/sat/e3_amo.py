"""Encoding E3: chỉ dùng biến S như E2, ràng buộc máy bằng AMO qua CardEnc của PySAT.

S[i, t]: bước i bắt đầu lúc >= t
R[i, t]: bước i đang chạy tại t
Mỗi máy, mỗi thời điểm t: có nhiều nhất một R[i, t] đúng (AMO).
"""
from __future__ import annotations

from pysat.card import CardEnc, EncType

from src.common.instance import Instance, Schedule
from src.sat.base import Clause, SatEncoding

AMO_TYPES = {
    "pairwise": EncType.pairwise,
    "seqcounter": EncType.seqcounter,
    "bitwise": EncType.bitwise,
    "ladder": EncType.ladder,
}


class E3Amo(SatEncoding):
    name = "E3"

    def __init__(self, inst: Instance, horizon: int, amo: str = "pairwise"):
        if amo not in AMO_TYPES:
            raise ValueError(f"không có kiểu AMO {amo}")
        self.amo = amo
        super().__init__(inst, horizon)

    def ge(self, j: int, k: int, t: int) -> int:
        # biến "bắt đầu lúc >= t"; t ngoài cửa sổ thì lấy S[es] (luôn đúng) hoặc S[ls + 1] (luôn sai)
        t = min(max(t, self.es[j][k]), self.ls[j][k] + 1)
        return self.s[(j, k, t)]

    def build(self) -> None:
        self.s: dict[tuple[int, int, int], int] = {}
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
            self.add([self.s[(j, k, es)]])
            self.add([-self.s[(j, k, ls + 1)]])
            for t in range(es, ls + 1):
                self.add([-self.s[(j, k, t + 1)], self.s[(j, k, t)]])

        # thứ tự trong job: bước k bắt đầu >= t thì bước k + 1 bắt đầu >= t + d
        for j, job in enumerate(self.inst.jobs):
            for k in range(len(job) - 1):
                d = job[k].duration
                for t in range(self.es[j][k], self.ls[j][k] + 1):
                    self.add([-self.ge(j, k, t), self.ge(j, k + 1, t + d)])

        # bắt đầu trong [t - d + 1, t] thì đang chạy tại t
        running: dict[tuple[int, int], list[int]] = {}
        for j, k, op in self.inst.ops():
            d = op.duration
            if d == 0:
                continue
            for t in range(self.es[j][k], self.ls[j][k] + d):
                r = self.new_var()
                self.add([-self.ge(j, k, t - d + 1), self.ge(j, k, t + 1), r])
                running.setdefault((op.machine, t), []).append(r)

        for lits in running.values():
            if len(lits) < 2:
                continue
            cnf = CardEnc.atmost(lits=lits, bound=1, top_id=self.n_vars, encoding=AMO_TYPES[self.amo])
            self.n_vars = max(self.n_vars, cnf.nv)
            for cl in cnf.clauses:
                self.add(cl)

        # bước thời gian 0 không được nằm giữa bước khác cùng máy (giống verify)
        for m in range(self.inst.n_machines):
            m_ops = self.inst.machine_ops(m)
            for jb, kb in m_ops:
                if self.inst.jobs[jb][kb].duration != 0:
                    continue
                for ja, ka in m_ops:
                    pa = self.inst.jobs[ja][ka].duration
                    if pa <= 1:
                        continue
                    for u in range(self.es[jb][kb], self.ls[jb][kb] + 1):
                        after = self.ge(ja, ka, u - pa + 1)
                        before = self.ge(ja, ka, u)
                        if after == before:
                            continue
                        self.add([-self.ge(jb, kb, u), self.ge(jb, kb, u + 1), -after, before])

    def tighten(self, c: int) -> list[Clause]:
        if self._infeasible:
            return []
        clauses: list[Clause] = []
        for j, job in enumerate(self.inst.jobs):
            k_last = len(job) - 1
            # bước cuối phải bắt đầu <= c - d
            clauses.append([-self.ge(j, k_last, c - job[k_last].duration + 1)])
        return clauses

    def decode(self, model: list[int]) -> Schedule:
        true_vars = {lit for lit in model if lit > 0}
        schedule: Schedule = []
        for j, job in enumerate(self.inst.jobs):
            row: list[int] = []
            for k in range(len(job)):
                start_t = self.es[j][k]
                for t in range(self.es[j][k], self.ls[j][k] + 1):
                    if self.s[(j, k, t)] in true_vars:
                        start_t = t
                row.append(start_t)
            schedule.append(row)
        return schedule
