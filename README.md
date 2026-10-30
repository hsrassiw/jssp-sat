# jssp-sat

BTL2 môn Các vấn đề hiện đại KHMT: giải JSSP bằng SAT (encoding E1, E2), so sánh với CP-SAT, CPLEX và Gurobi.

## Cài đặt

Python 3.12:

```
pip install -r requirements.txt
```

## Chạy

Chạy từ thư mục gốc, dùng `python -m`:

```
python -m pytest
python -m src.common.run ft06 --method SAT --encoding E2 --strategy incremental --solver cadical
```

Thêm `--csv results/ten_file.csv` để ghi kết quả ra file.

## Thư mục

```
data/         dữ liệu benchmark, bks.csv
src/common/   đọc dữ liệu, LB/UB, verify, ghi CSV, run.py
src/sat/      e1_crawford.py, e2_order.py, strategies.py
src/cp/       cpsat.py, cplex_cp.py
src/mip/      cplex_mip.py, gurobi_mip.py
results/      file CSV kết quả
report/       báo cáo LaTeX
tests/
```

## Hàm solve

Mỗi phương pháp viết hàm:

```python
def solve(inst, cfg, *, lb0, ub0, deadline) -> Result
```

- `deadline` là mốc thời gian (`time.perf_counter()`), không phải số giây.
- Tự điền vào `Result`: `status`, `bound`, `schedule`, `encode_time_s`, `solve_time_s`, `n_vars`, `n_clauses`. Các cột còn lại `run.py` tự điền.
- Chạy với ft06 phải ra `OPT,55,55`.

Encoding SAT thì kế thừa `SatEncoding` trong `src/sat/base.py`.

Các cột CSV giống mục 5 trong file kế hoạch, cột nào không dùng thì ghi `-`.
