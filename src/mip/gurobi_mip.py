"""Mô hình MILP giải bằng Gurobi (Người 3)."""
from __future__ import annotations

from src.common.instance import Instance
from src.common.result import Config, Result


def solve(inst: Instance, cfg: Config, *, lb0: int, ub0: int, deadline: float) -> Result:
    raise NotImplementedError("Người 3: mô hình MILP cho Gurobi")
