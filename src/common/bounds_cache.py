"""Cận cố định dùng chung giữa các phương pháp; không tự tính lại khi chạy solver."""
from __future__ import annotations
import hashlib
import json
import os
import tempfile
from pathlib import Path
from src.common.data import DATA_DIR
from src.common.instance import Instance, makespan
from src.common.verify import verify

DEFAULT_BOUNDS_FILE = DATA_DIR / 'bounds.json'
SCHEMA_VERSION = 1


def instance_hash(inst: Instance) -> str:
    payload = [inst.n_jobs, inst.n_machines, inst.jobs]
    return hashlib.sha256(json.dumps(payload, separators=(',', ':')).encode()).hexdigest()


def read_cache(path: str | Path = DEFAULT_BOUNDS_FILE) -> dict:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f'{path}: chạy python -m src.common.prepare_bounds trước')
    cache = json.loads(path.read_text(encoding='utf-8'))
    if cache.get('schema_version') != SCHEMA_VERSION or not isinstance(cache.get('instances'), dict):
        raise ValueError(f'Định dạng bounds cache không hợp lệ: {path}')
    return cache


def validate_entry(inst: Instance, entry: dict) -> tuple[int, int]:
    if entry.get('instance_sha256') != instance_hash(inst):
        raise ValueError(f'{inst.name}: dữ liệu khác cache; tạo lại cận bằng --overwrite')
    lb, ub = entry.get('lb0'), entry.get('ub0')
    if type(lb) is not int or type(ub) is not int or not 0 <= lb <= ub:
        raise ValueError(f'{inst.name}: lb0/ub0 không hợp lệ')
    schedule = entry.get('schedule')
    if not isinstance(schedule, list) or any(not isinstance(row, list) for row in schedule):
        raise ValueError(f'{inst.name}: thiếu lịch chứng minh UB')
    errors = verify(inst, schedule)
    if errors or makespan(inst, schedule) != ub:
        raise ValueError(f'{inst.name}: lịch UB không hợp lệ hoặc makespan không khớp')
    return lb, ub


def load_bounds(inst: Instance, path: str | Path = DEFAULT_BOUNDS_FILE) -> tuple[int, int]:
    cache = read_cache(path)
    if inst.name not in cache['instances']:
        raise ValueError(f'{inst.name}: chưa có cận; chạy python -m src.common.prepare_bounds {inst.name}')
    return validate_entry(inst, cache['instances'][inst.name])


def write_cache(cache: dict, path: str | Path = DEFAULT_BOUNDS_FILE) -> None:
    """Ghi file tạm rồi replace: gián đoạn không làm hỏng bản đã lưu."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write('\n')
        os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)
