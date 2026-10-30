"""Kết quả và ghi file CSV."""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

from src.common.instance import Schedule

OPT = "OPT"
FEAS = "FEAS"
NOSOL = "NOSOL"
ERR = "ERR"
NA = "-"

CSV_COLUMNS = [
    "instance", "method", "encoding", "strategy", "solver", "status",
    "cmax", "bound", "lb0", "ub0",
    "time_s", "encode_time_s", "solve_time_s", "n_vars", "n_clauses", "n_calls",
]


@dataclass(frozen=True)
class Config:
    method: str
    encoding: str = NA
    strategy: str = NA
    solver: str = NA

    def key(self) -> tuple[str, str, str, str]:
        return (self.method, self.encoding, self.strategy, self.solver)


@dataclass
class Result:
    instance: str
    method: str
    encoding: str
    strategy: str
    solver: str
    status: str = NOSOL
    cmax: int | None = None
    bound: int | None = None
    lb0: int | None = None
    ub0: int | None = None
    time_s: float = 0.0
    encode_time_s: float = 0.0
    solve_time_s: float = 0.0
    n_vars: int = 0
    n_clauses: int = 0
    n_calls: int = 0
    # 2 trường dưới không ghi vào CSV
    schedule: Schedule | None = field(default=None, repr=False)
    note: str = ""

    @classmethod
    def new(cls, instance: str, cfg: Config) -> Result:
        return cls(instance, cfg.method, cfg.encoding, cfg.strategy, cfg.solver)

    def key(self) -> tuple[str, str, str, str, str]:
        return (self.instance, self.method, self.encoding, self.strategy, self.solver)

    def csv_row(self) -> dict[str, str]:
        row = {}
        for name in CSV_COLUMNS:
            value = getattr(self, name)
            if value is None:
                row[name] = ""
            elif isinstance(value, float):
                row[name] = f"{value:.3f}"
            else:
                row[name] = str(value)
        return row


def append_csv(path: str | Path, result: Result) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    new_file = not path.exists() or path.stat().st_size == 0
    with open(path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        if new_file:
            writer.writeheader()
        writer.writerow(result.csv_row())


def done_keys(path: str | Path) -> set[tuple[str, str, str, str, str]]:
    # các cấu hình đã chạy xong, để chạy tiếp khi bị ngắt
    path = Path(path)
    if not path.exists():
        return set()
    done = set()
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            key = (row["instance"], row["method"], row["encoding"], row["strategy"], row["solver"])
            done.add(key)
    return done
