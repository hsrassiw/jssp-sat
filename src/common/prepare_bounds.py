"""Tính LB/UB một lần, lưu sau từng instance; mặc định bỏ qua cận đã có."""
from __future__ import annotations
import argparse
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from src.common.bounds import lower_bound, upper_bound
from src.common.bounds_cache import DEFAULT_BOUNDS_FILE, SCHEMA_VERSION, instance_hash, read_cache, validate_entry, write_cache
from src.common.data import DATA_DIR, load


def compute_entry(inst, *, time_limit=5.0, seed=0):
    t0 = time.perf_counter()
    lb = lower_bound(inst)
    ub, schedule = upper_bound(inst, time_limit=time_limit, seed=seed)
    entry = dict(lb0=lb, ub0=ub, schedule=schedule, instance_sha256=instance_hash(inst),
                 algorithm='randomized_greedy_gap_insertion_v1', seed=seed,
                 greedy_time_limit_s=time_limit, preprocess_time_s=time.perf_counter()-t0,
                 created_at=datetime.now(timezone.utc).isoformat())
    validate_entry(inst, entry)
    return entry


def prepare(sources, *, output=DEFAULT_BOUNDS_FILE, time_limit=5.0, seed=0, overwrite=False):
    if not math.isfinite(time_limit) or time_limit < 0:
        raise ValueError('time_limit phải hữu hạn và không âm')
    output = Path(output)
    cache = read_cache(output) if output.exists() else dict(schema_version=SCHEMA_VERSION, instances={})
    for source in sources:
        inst = load(source)
        if inst.name in cache['instances'] and not overwrite:
            validate_entry(inst, cache['instances'][inst.name])
            print(f'SKIP {inst.name}', flush=True)
            continue
        entry = compute_entry(inst, time_limit=time_limit, seed=seed)
        cache['instances'][inst.name] = entry
        write_cache(cache, output)
        print(f"SAVE {inst.name}: LB={entry['lb0']} UB={entry['ub0']}", flush=True)
    return cache


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('instances', nargs='*', help='Tên hoặc đường dẫn; bỏ trống để tính mọi data/*.txt')
    p.add_argument('--output', type=Path, default=DEFAULT_BOUNDS_FILE)
    p.add_argument('--time-limit', type=float, default=5.0, help='Số giây greedy mỗi instance')
    p.add_argument('--seed', type=int, default=0)
    p.add_argument('--overwrite', action='store_true', help='Chủ động tính lại cận đã có')
    args = p.parse_args()
    sources = args.instances or sorted(DATA_DIR.glob('*.txt'))
    prepare(sources, output=args.output, time_limit=args.time_limit, seed=args.seed, overwrite=args.overwrite)


if __name__ == '__main__': main()
