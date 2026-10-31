"""Chạy một phương pháp trên một instance, in ra một dòng CSV."""
from __future__ import annotations

import argparse
import sys
import time

from src.common.bounds import lower_bound, upper_bound
from src.common.data import load
from src.common.instance import makespan
from src.common.result import ERR, NA, OPT, Config, Result, append_csv
from src.common.verify import verify

TIME_LIMIT = 600.0


def get_solve(cfg: Config):
    # import ở đây để máy chưa cài Gurobi/CPLEX vẫn chạy được
    if cfg.method == "SAT":
        from src.sat.strategies import solve
    elif cfg.method == "CP" and cfg.solver == "cpsat":
        from src.cp.cpsat import solve
    elif cfg.method == "CP" and cfg.solver == "cplex":
        from src.cp.cplex_cp import solve
    elif cfg.method == "MIP" and cfg.solver == "cplex":
        from src.mip.cplex_mip import solve
    elif cfg.method == "MIP" and cfg.solver == "gurobi":
        from src.mip.gurobi_mip import solve
    else:
        raise ValueError(f"không có phương pháp cho cấu hình {cfg}")
    return solve


def run_one(source, cfg: Config, time_limit: float = TIME_LIMIT, solve=None) -> Result:
    t0 = time.perf_counter()
    deadline = t0 + time_limit
    name = str(source)
    try:
        inst = load(source)
        name = inst.name
        lb0 = lower_bound(inst)
        ub0, _ = upper_bound(inst, time_limit=max(0.0, min(5.0, deadline - time.perf_counter())))
        if solve is None:
            solve = get_solve(cfg)
        res = solve(inst, cfg, lb0=lb0, ub0=ub0, deadline=deadline)
        res.instance = inst.name
        res.lb0 = lb0
        res.ub0 = ub0
        _check(inst, res)
    except Exception as e:  # gồm cả MemoryError
        res = Result.new(name, cfg)
        res.status = ERR
        res.note = f"{type(e).__name__}: {e}"
    res.time_s = time.perf_counter() - t0
    if res.note:
        print(f"[{res.status}] {res.key()}: {res.note}", file=sys.stderr)
    return res


def _check(inst, res: Result) -> None:
    if res.schedule is None:
        res.cmax = None
        return

    errors = verify(inst, res.schedule)
    if errors:
        res.status = ERR
        res.cmax = None
        res.note = f"verify lỗi ({len(errors)}): " + "; ".join(errors[:3])
        return

    res.cmax = makespan(inst, res.schedule)
    if res.cmax < res.lb0:
        res.status = ERR
        res.note = f"cmax {res.cmax} < lb0 {res.lb0}"
    elif res.bound is not None and res.bound > res.cmax:
        res.status = ERR
        res.note = f"bound {res.bound} > cmax {res.cmax}"
    elif res.status == OPT and res.bound != res.cmax:
        res.status = ERR
        res.note = f"OPT nhưng bound {res.bound} != cmax {res.cmax}"


def main() -> None:
    # để in được tiếng Việt trên Windows
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

    p = argparse.ArgumentParser(description="Chạy một cấu hình trên một instance")
    p.add_argument("instance", help="ft06, tên instance trong data/, hoặc đường dẫn file")
    p.add_argument("--method", required=True, choices=["SAT", "CP", "MIP"])
    p.add_argument("--encoding", default=NA)
    p.add_argument("--strategy", default=NA)
    p.add_argument("--solver", default=NA)
    p.add_argument("--time-limit", type=float, default=TIME_LIMIT)
    p.add_argument("--csv", help="ghi thêm kết quả vào file CSV này")
    args = p.parse_args()

    cfg = Config(args.method, args.encoding, args.strategy, args.solver)
    res = run_one(args.instance, cfg, args.time_limit)
    print(",".join(res.csv_row().values()))
    if args.csv:
        append_csv(args.csv, res)


if __name__ == "__main__":
    main()
