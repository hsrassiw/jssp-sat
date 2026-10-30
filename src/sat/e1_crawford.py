"""Encoding E1 (Người 2), theo mục 2 paper Koshimura 2010."""
from __future__ import annotations

from src.common.instance import Schedule
from src.sat.base import Clause, SatEncoding


class E1Crawford(SatEncoding):
    name = "E1"

    def build(self) -> None:
        raise NotImplementedError("Người 2: biến pr, sa, eb và 8 luật")

    def tighten(self, c: int) -> list[Clause]:
        raise NotImplementedError

    def decode(self, model: list[int]) -> Schedule:
        raise NotImplementedError
