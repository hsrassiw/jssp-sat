"""Hai kiểu AMO (nhiều nhất một biến đúng) mà PySAT không có: commander và product.

Mỗi hàm nhận danh sách biến và hàm new_var để tạo biến phụ, trả về danh sách mệnh đề.
"""
import math


def pairwise(lits):
    # mỗi cặp biến không được cùng đúng
    clauses = []
    for i in range(len(lits)):
        for j in range(i + 1, len(lits)):
            clauses.append([-lits[i], -lits[j]])
    return clauses


def commander(lits, new_var):
    # Klieber & Kwon (2007): chia thành từng nhóm 3 biến, mỗi nhóm có một biến chỉ huy c.
    #   - trong nhóm: pairwise
    #   - có biến trong nhóm đúng thì c đúng
    #   - c đúng thì trong nhóm có biến đúng
    # rồi làm AMO tiếp trên các biến chỉ huy
    if len(lits) <= 3:
        return pairwise(lits)

    clauses = []
    commanders = []
    for start in range(0, len(lits), 3):
        group = lits[start:start + 3]
        c = new_var()
        clauses += pairwise(group)
        for x in group:
            clauses.append([-x, c])
        clauses.append([-c] + group)
        commanders.append(c)

    return clauses + commander(commanders, new_var)


def product(lits, new_var):
    # Chen (2010): xếp các biến lên bảng p hàng, q cột.
    # Mỗi hàng có một biến row, mỗi cột có một biến col.
    # Biến ở ô (hàng i, cột j) đúng thì row[i] và col[j] đúng.
    # Hai biến khác ô thì khác hàng hoặc khác cột, nên chỉ cần AMO trên row và trên col.
    if len(lits) <= 4:
        return pairwise(lits)

    p = math.ceil(math.sqrt(len(lits)))
    q = math.ceil(len(lits) / p)
    rows = [new_var() for _ in range(p)]
    cols = [new_var() for _ in range(q)]

    clauses = []
    for k in range(len(lits)):
        i = k // q
        j = k % q
        clauses.append([-lits[k], rows[i]])
        clauses.append([-lits[k], cols[j]])

    return clauses + product(rows, new_var) + product(cols, new_var)
