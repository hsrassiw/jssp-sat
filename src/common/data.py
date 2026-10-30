"""Đọc dữ liệu benchmark."""
from __future__ import annotations

import csv
from pathlib import Path

from src.common.instance import Instance

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"

# ft06, tối ưu = 55
FT06_ROWS = [
    [(2, 1), (0, 3), (1, 6), (3, 7), (5, 3), (4, 6)],
    [(1, 8), (2, 5), (4, 10), (5, 10), (0, 10), (3, 4)],
    [(2, 5), (3, 4), (5, 8), (0, 9), (1, 1), (4, 7)],
    [(1, 5), (0, 5), (2, 5), (3, 3), (4, 8), (5, 9)],
    [(2, 9), (1, 3), (4, 5), (5, 4), (0, 3), (3, 1)],
    [(1, 3), (3, 3), (5, 9), (0, 10), (4, 4), (2, 1)],
]


def ft06() -> Instance:
    return Instance.from_lists("ft06", FT06_ROWS)


def read_instance(path: str | Path) -> Instance:
    raise NotImplementedError("Người 3: viết hàm đọc file OR-Library")


def load(name_or_path: str | Path) -> Instance:
    if name_or_path == "ft06":
        return ft06()
    path = Path(name_or_path)
    if not path.exists():
        path = DATA_DIR / f"{name_or_path}.txt"
    return read_instance(path)


def load_bks(path: str | Path = DATA_DIR / "bks.csv") -> dict[str, int]:
    bks = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            bks[row["instance"]] = int(row["bks"])
    return bks
