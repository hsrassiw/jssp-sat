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
    """Đọc một instance: dòng đầu n_jobs n_machines,
    các dòng sau là các cặp machine duration của từng job.
    Máy được đánh số từ 0.
    """
    path = Path(path)
    lines = []

    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        # Bỏ dòng trống và phần chú thích bắt đầu bằng #
        line = raw.split("#", 1)[0].strip()
        if line:
            lines.append(line)

    if not lines:
        raise ValueError(f"File rỗng: {path}")

    header = lines[0].split()
    if len(header) != 2:
        raise ValueError("Dòng đầu phải gồm: n_jobs n_machines")

    n_jobs, n_machines = map(int, header)

    if n_jobs <= 0 or n_machines <= 0:
        raise ValueError("Số job và số máy phải lớn hơn 0")

    if len(lines) - 1 != n_jobs:
        raise ValueError(
            f"Cần {n_jobs} dòng job, nhưng có {len(lines) - 1}"
        )

    rows = []

    for j, line in enumerate(lines[1:]):
        values = list(map(int, line.split()))

        if len(values) != 2 * n_machines:
            raise ValueError(
                f"Job {j}: cần {n_machines} cặp machine duration"
            )

        row = []

        for k in range(n_machines):
            machine = values[2 * k]
            duration = values[2 * k + 1]

            if not 0 <= machine < n_machines:
                raise ValueError(
                    f"Job {j}, bước {k}: máy {machine} ngoài phạm vi"
                )

            if duration < 0:
                raise ValueError(
                    f"Job {j}, bước {k}: thời gian phải lớn hơn hoặc bằng 0"
                )

            row.append((machine, duration))

        rows.append(row)

    inst = Instance.from_lists(path.stem, rows)

    # Giữ số máy được khai báo trong file.
    return Instance(
        name=inst.name,
        n_jobs=n_jobs,
        n_machines=n_machines,
        jobs=inst.jobs,
    )

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
