"""Test AMO tự cài: thử mọi cách gán đúng/sai cho n biến."""
import itertools

import pytest
from pysat.solvers import Solver

from src.sat import amo


class Counter:
    # tạo biến phụ, đánh số tiếp sau n biến chính
    def __init__(self, n):
        self.last = n

    def new_var(self):
        self.last += 1
        return self.last


@pytest.mark.parametrize("kind", ["commander", "product"])
@pytest.mark.parametrize("n", range(1, 10))
def test_amo_exact(kind, n):
    lits = list(range(1, n + 1))
    if kind == "commander":
        clauses = amo.commander(lits, Counter(n).new_var)
    else:
        clauses = amo.product(lits, Counter(n).new_var)

    with Solver(name="cadical195", bootstrap_with=clauses) as solver:
        # thử hết 2^n cách gán: thoả được khi và chỉ khi có nhiều nhất một biến đúng
        for values in itertools.product([False, True], repeat=n):
            assumptions = []
            for x, v in zip(lits, values):
                assumptions.append(x if v else -x)
            assert solver.solve(assumptions=assumptions) == (sum(values) <= 1)


def test_fewer_clauses_than_pairwise():
    lits = list(range(1, 31))
    n_pairwise = len(amo.pairwise(lits))
    assert len(amo.commander(lits, Counter(30).new_var)) < n_pairwise
    assert len(amo.product(lits, Counter(30).new_var)) < n_pairwise
