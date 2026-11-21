"""Encoding E4: giống hệt E2, chỉ thay ràng buộc máy bằng biến thứ tự kiểu Crawford.

Dùng để tìm xem vì sao E1 thắng E2 trên bài lớn:
E2 và E4 chỉ khác nhau đúng một chỗ là cách cấm hai bước cùng máy chạy chồng lên nhau.
  - E2 (SAT-5): xét từng mốc t, "A bắt đầu đúng lúc t thì B phải xong trước t hoặc bắt đầu sau A".
  - E4: mỗi cặp bước cùng máy có một biến y, y đúng là A trước B, y sai là B trước A.
    A trước B: A bắt đầu >= t thì B bắt đầu >= t + d_A (giống luật 8 của Crawford).
Biến S, X, cửa sổ [ES, LS], SAT-1 đến SAT-4, tighten và decode giữ nguyên như E2.
"""
from src.sat.e2_order import E2Order


class E4OrderPr(E2Order):
    name = "E4"

    def ge(self, j, k, t):
        # biến "bước k của job j bắt đầu lúc >= t"
        # t ngoài cửa sổ thì lấy S[es] (luôn đúng) hoặc S[ls + 1] (luôn sai)
        t = max(t, self.es[j][k])
        t = min(t, self.ls[j][k] + 1)
        return self.s[(j, k, t)]

    def build(self):
        self.s = {}
        self.x = {}
        self.y = {}
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

        # ----- Phần khác E2: thay SAT-5 bằng biến thứ tự máy -----

        for m in range(self.inst.n_machines):
            m_ops = self.inst.machine_ops(m)
            for a in range(len(m_ops)):
                for b in range(a + 1, len(m_ops)):
                    ja, ka = m_ops[a]
                    jb, kb = m_ops[b]
                    if ja == jb:
                        # cùng job thì thứ tự trong job đã lo
                        continue
                    da = self.inst.jobs[ja][ka].duration
                    db = self.inst.jobs[jb][kb].duration
                    # cửa sổ không chồng nhau thì thứ tự đã cố định, không cần biến
                    if self.ls[ja][ka] + da <= self.es[jb][kb]:
                        continue
                    if self.ls[jb][kb] + db <= self.es[ja][ka]:
                        continue
                    # y đúng: A trước B. y sai: B trước A.
                    y = self.new_var()
                    self.y[(ja, ka, jb, kb)] = y
                    self.add_before(y, ja, ka, jb, kb)   # y đúng thì A xong B mới bắt đầu
                    self.add_before(-y, jb, kb, ja, ka)  # y sai thì B xong A mới bắt đầu

    def add_before(self, lit, ja, ka, jb, kb):
        # lit đúng thì bước A xong rồi bước B mới bắt đầu:
        # A bắt đầu >= t thì B bắt đầu >= t + d_A
        d = self.inst.jobs[ja][ka].duration
        for t in range(self.es[ja][ka], self.ls[ja][ka] + 1):
            if t + d <= self.es[jb][kb]:
                # B lúc nào cũng bắt đầu >= t + d, mệnh đề luôn đúng
                continue
            self.add([-lit, -self.ge(ja, ka, t), self.ge(jb, kb, t + d)])
