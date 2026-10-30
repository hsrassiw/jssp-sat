"""Lớp cha cho các SAT encoding (E1, E2)."""
from __future__ import annotations

from abc import ABC, abstractmethod

from src.common.bounds import time_windows
from src.common.instance import Instance, Schedule

Clause = list[int]


class SatEncoding(ABC):
    name: str = "?"

    def __init__(self, inst: Instance, horizon: int):
        self.inst = inst
        self.horizon = horizon
        self.es, self.ls = time_windows(inst, horizon)
        self.n_vars = 0
        self.clauses: list[Clause] = []
        self.build()

    def new_var(self) -> int:
        self.n_vars += 1
        return self.n_vars

    def add(self, clause: Clause) -> None:
        self.clauses.append(clause)

    @property
    def n_clauses(self) -> int:
        return len(self.clauses)

    @abstractmethod
    def build(self) -> None:
        # Nếu dùng CardEnc thì nhớ cập nhật self.n_vars = cnf.nv
        ...

    @abstractmethod
    def tighten(self, c: int) -> list[Clause]:
        # Trả về các mệnh đề ép Cmax <= c
        ...

    @abstractmethod
    def decode(self, model: list[int]) -> Schedule:
        ...
