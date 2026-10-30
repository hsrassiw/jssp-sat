"""Mô hình CP-SAT của OR-Tools (Người 2)."""
from __future__ import annotations

from src.common.instance import Instance
from src.common.result import Config, Result


def solve(inst: Instance, cfg: Config, *, lb0: int, ub0: int, deadline: float) -> Result:
    raise NotImplementedError("Người 2: mô hình OR-Tools CP-SAT")
