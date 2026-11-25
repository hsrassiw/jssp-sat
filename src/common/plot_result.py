"""Script tổng hợp bảng và vẽ hình bằng cnsplots từ kết quả CSV."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import cnsplots as cns
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.common.data import load, load_bks
from src.common.result import Config, FEAS, NOSOL, OPT
from src.common.run import run_one

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"
OUT_FIGS = ROOT / "report" / "figs"
OUT_TABLES = ROOT / "report" / "tables"


# ---------------------------------------------------------------------------
# 1. Đọc dữ liệu, cộng preprocess_time_s và tính BKS gap
# ---------------------------------------------------------------------------
def load_preprocess_times(bounds_path: Path) -> dict[str, float]:
    """Đọc preprocess_time_s từ data/bounds.json."""
    if not bounds_path.exists():
        return {}
    with open(bounds_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    prep: dict[str, float] = {}
    for inst, val in raw.items():
        if isinstance(val, dict):
            prep[inst] = float(val.get("preprocess_time_s", 0.0))
        else:
            prep[inst] = float(val)
    return prep


def instance_group(name: str) -> str:
    """Tách nhóm bài từ tên instance (vd: ft06 -> ft, la01 -> la, abz8 -> abz)."""
    m = re.match(r"^([a-zA-Z]+)", str(name))
    return m.group(1).lower() if m else "other"


def load_results_from_dir(
    results_dir: Path,
    exclude_files: set[str],
    bounds_path: Path,
    bks_path: Path,
) -> pd.DataFrame:
    """Gộp toàn bộ CSV trong results/ (trừ file 3600s), cộng preprocess_time_s."""
    csv_files = sorted(
        p for p in results_dir.glob("*.csv") if p.name not in exclude_files
    )
    if not csv_files:
        raise FileNotFoundError(f"Không tìm thấy file CSV nào trong {results_dir}")

    df = pd.concat((pd.read_csv(p) for p in csv_files), ignore_index=True)

    # Giữ bản ghi mới nhất nếu trùng cấu hình (instance, method, encoding, strategy, solver)
    key_cols = ["instance", "method", "encoding", "strategy", "solver"]
    df = df.drop_duplicates(subset=key_cols, keep="last").reset_index(drop=True)

    # Cộng preprocess_time_s vào time_s
    prep_map = load_preprocess_times(bounds_path)
    df["preprocess_time_s"] = df["instance"].map(prep_map).fillna(0.0)
    df["time_s"] = pd.to_numeric(df["time_s"], errors="coerce").fillna(0.0) + df["preprocess_time_s"]

    # Gắn BKS và tính Gap (%)
    bks_map = load_bks(bks_path) if bks_path.exists() else {}
    df["bks"] = df["instance"].map(bks_map)
    df["cmax"] = pd.to_numeric(df["cmax"], errors="coerce")
    df["gap_pct"] = np.where(
        df["cmax"].notna() & df["bks"].notna() & (df["bks"] > 0),
        100.0 * (df["cmax"] - df["bks"]) / df["bks"],
        np.nan,
    )

    df["group"] = df["instance"].map(instance_group)
    df["config_label"] = df.apply(_format_config_label, axis=1)
    return df


def _format_config_label(row: pd.Series) -> str:
    if row["method"] == "SAT":
        return f"SAT-{row['encoding']}-{row['strategy']}-{row['solver']}"
    return f"{row['method']}-{row['solver']}"


# ---------------------------------------------------------------------------
# 2. Vẽ 4 biểu đồ Cactus Plot bằng cnsplots
# ---------------------------------------------------------------------------
def _build_cactus_df(df: pd.DataFrame, group_col: str, time_limit: float = 600.0) -> pd.DataFrame:
    """Chuyển dữ liệu nghiệm OPT thành bảng (số bài giải được, thời gian tích lũy/từng bài)."""
    rows = []
    opt_df = df[(df["status"] == OPT) & (df["time_s"] <= time_limit)].copy()
    for label, sub in opt_df.groupby(group_col):
        times = np.sort(sub["time_s"].to_numpy())
        for idx, t in enumerate(times, start=1):
            rows.append({
                group_col: label,
                "solved_count": idx,
                "time_s": max(float(t), 1e-3),
            })
    return pd.DataFrame(rows)


def plot_single_cactus(
    cactus_df: pd.DataFrame,
    hue_col: str,
    title: str,
    out_path: Path,
    time_limit: float = 600.0,
) -> None:
    if cactus_df.empty:
        print(f"[WARN] Không có dữ liệu OPT cho biểu đồ: {title}")
        return

    cns.setup_matplotlib()
    fig = cns.figure(width=3.6, height=2.6)
    ax = fig.gca()

    cns.lineplot(
        data=cactus_df,
        x="solved_count",
        y="time_s",
        hue=hue_col,
        marker="o",
        markersize=3.5,
        linewidth=1.4,
        ax=ax,
    )
    ax.set_yscale("log")
    ax.set_ylim(1e-2, time_limit * 1.2)
    ax.axhline(time_limit, color="gray", linestyle="--", linewidth=0.8, label=f"Limit ({int(time_limit)}s)")
    ax.set_xlabel("Số bài giải tối ưu (OPT)")
    ax.set_ylabel("Thời gian giải (s, log scale)")
    ax.set_title(title)
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.legend(frameon=False, fontsize=7, loc="upper left")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    fig.savefig(out_path.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)


def generate_all_cactus_plots(df: pd.DataFrame, out_dir: Path, time_limit: float = 600.0) -> None:
    sat_df = df[df["method"] == "SAT"].copy()

    # (a) So sánh 4 chiến lược (cố định encoding & solver phổ biến nhất hoặc lấy theo từng cặp)
    if not sat_df.empty:
        # Lọc các cấu hình thuộc 4 chiến lược trên cùng encoding/solver chính (vd E2 + cadical nếu có)
        base_enc = "E2" if "E2" in sat_df["encoding"].values else sat_df["encoding"].iloc[0]
        base_sol = "cadical" if "cadical" in sat_df["solver"].values else sat_df["solver"].iloc[0]

        df_strat = sat_df[(sat_df["encoding"] == base_enc) & (sat_df["solver"] == base_sol)]
        c_strat = _build_cactus_df(df_strat, "strategy", time_limit)
        plot_single_cactus(
            c_strat,
            "strategy",
            f"So sánh 4 chiến lược SAT ({base_enc}, {base_sol})",
            out_dir / "cactus_strategies.png",
            time_limit,
        )

        # (b) So sánh 3 SAT solver (cadical, glucose, cryptominisat)
        base_str = "incremental" if "incremental" in sat_df["strategy"].values else sat_df["strategy"].iloc[0]
        df_solv = sat_df[(sat_df["encoding"] == base_enc) & (sat_df["strategy"] == base_str)]
        c_solv = _build_cactus_df(df_solv, "solver", time_limit)
        plot_single_cactus(
            c_solv,
            "solver",
            f"So sánh 3 SAT Solver ({base_enc}, {base_str})",
            out_dir / "cactus_sat_solvers.png",
            time_limit,
        )

        # (c) So sánh E1, E2, E3 (gộp biến thể E3 chuẩn)
        df_enc = sat_df[(sat_df["strategy"] == base_str) & (sat_df["solver"] == base_sol)].copy()
        df_enc["enc_family"] = df_enc["encoding"].str.extract(r"^(E[123])")[0].fillna(df_enc["encoding"])
        df_enc = df_enc.sort_values("time_s").drop_duplicates(subset=["instance", "enc_family"])
        c_enc = _build_cactus_df(df_enc, "enc_family", time_limit)
        plot_single_cactus(
            c_enc,
            "enc_family",
            f"So sánh Encoding E1, E2, E3 ({base_str}, {base_sol})",
            out_dir / "cactus_encodings.png",
            time_limit,
        )

    # (d) So sánh SAT tốt nhất với CP-SAT, CPLEX CP, Gurobi, CPLEX MIP
    comp_frames = []
    if not sat_df.empty:
        # Tìm cấu hình SAT giải được nhiều OPT nhất (ưu tiên tổng thời gian nhỏ hơn)
        sat_rank = (
            sat_df[sat_df["status"] == OPT]
            .groupby("config_label")
            .agg(n_opt=("instance", "count"), sum_t=("time_s", "sum"))
            .sort_values(["n_opt", "sum_t"], ascending=[False, True])
        )
        if not sat_rank.empty:
            best_sat_cfg = sat_rank.index[0]
            best_sat = sat_df[sat_df["config_label"] == best_sat_cfg].copy()
            best_sat["family"] = f"Best SAT ({best_sat_cfg.replace('SAT-', '')})"
            comp_frames.append(best_sat)

    non_sat = df[df["method"].isin(["CP", "MIP"])].copy()
    if not non_sat.empty:
        name_map = {
            ("CP", "cpsat"): "CP-SAT",
            ("CP", "cplex"): "CPLEX CP",
            ("MIP", "gurobi"): "Gurobi MIP",
            ("MIP", "cplex"): "CPLEX MIP",
        }
        non_sat["family"] = non_sat.apply(
            lambda r: name_map.get((r["method"], r["solver"]), f"{r['method']}-{r['solver']}"),
            axis=1,
        )
        comp_frames.append(non_sat)

    if comp_frames:
        df_comp = pd.concat(comp_frames, ignore_index=True)
        c_comp = _build_cactus_df(df_comp, "family", time_limit)
        plot_single_cactus(
            c_comp,
            "family",
            "SAT tốt nhất vs CP-SAT, CPLEX CP, Gurobi, CPLEX MIP",
            out_dir / "cactus_all_methods.png",
            time_limit,
        )


# ---------------------------------------------------------------------------
# 3. Tạo các bảng tổng hợp (Markdown + LaTeX)
# ---------------------------------------------------------------------------
def _save_table(df_tbl: pd.DataFrame, out_dir: Path, name: str, caption: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / f"{name}.md"
    tex_path = out_dir / f"{name}.tex"

    md_path.write_text(df_tbl.to_markdown(index=False), encoding="utf-8")
    tex_path.write_text(
        df_tbl.to_latex(index=False, caption=caption, label=f"tab:{name}", float_format="%.2f"),
        encoding="utf-8",
    )


def generate_summary_tables(
    df: pd.DataFrame,
    df_3600: pd.DataFrame | None,
    out_dir: Path,
) -> None:
    # Bảng 1: Số bài OPT / FEAS / NOSOL theo cấu hình và nhóm bài
    status_counts = (
        df.groupby(["config_label", "group", "status"])["instance"]
        .count()
        .unstack(fill_value=0)
        .reset_index()
    )
    for col in (OPT, FEAS, NOSOL):
        if col not in status_counts.columns:
            status_counts[col] = 0
    status_counts = status_counts[["config_label", "group", OPT, FEAS, NOSOL]]
    _save_table(
        status_counts,
        out_dir,
        "table_status_by_group",
        "Số bài OPT/FEAS/NOSOL theo cấu hình và nhóm bài",
    )

    # Bảng 2: Kích thước mô hình (n_vars, n_clauses), bao gồm cả 4 loại AMO của E3
    size_df = (
        df.groupby(["method", "encoding", "solver"], as_index=False)
        .agg(
            mean_vars=("n_vars", "mean"),
            max_vars=("n_vars", "max"),
            mean_clauses=("n_clauses", "mean"),
            max_clauses=("n_clauses", "max"),
        )
        .sort_values(["method", "encoding", "solver"])
    )
    _save_table(
        size_df,
        out_dir,
        "table_model_size",
        "Kích thước mô hình (n_vars, n_clauses) theo phương pháp và encoding (gồm các AMO của E3)",
    )

    # Bảng 3: Số lần gọi solver (n_calls)
    calls_df = (
        df.groupby(["config_label"], as_index=False)
        .agg(
            n_instances=("instance", "count"),
            mean_calls=("n_calls", "mean"),
            median_calls=("n_calls", "median"),
            max_calls=("n_calls", "max"),
            mean_time_s=("time_s", "mean"),
        )
        .sort_values("config_label")
    )
    _save_table(
        calls_df,
        out_dir,
        "table_solver_calls",
        "Thống kê số lần gọi solver và thời gian trung bình theo cấu hình",
    )

    # Bảng 4: Gap so với BKS ở nhóm bài lớn (ví dụ abz, yn, swv, ta, hoặc la lớn)
    large_df = df[df["group"].isin(["abz", "yn", "swv", "ta", "orb"]) | (df["n_vars"] > 50000)].copy()
    if large_df.empty:
        large_df = df.copy()
    gap_df = (
        large_df.groupby(["config_label", "group"], as_index=False)
        .agg(
            solved_opt=("status", lambda s: int((s == OPT).sum())),
            feasible=("status", lambda s: int((s == FEAS).sum())),
            mean_gap_pct=("gap_pct", "mean"),
            min_gap_pct=("gap_pct", "min"),
        )
        .sort_values(["group", "mean_gap_pct"])
    )
    _save_table(
        gap_df,
        out_dir,
        "table_large_bks_gap",
        "Độ lệch (Gap %) so với BKS trên các bộ dữ liệu lớn",
    )

    # Bảng 5: So sánh đợt 600s và đợt bổ sung 3600s
    if df_3600 is not None and not df_3600.empty:
        keys = ["instance", "method", "encoding", "strategy", "solver"]
        merged = pd.merge(
            df[keys + ["status", "cmax", "bound", "time_s", "gap_pct"]],
            df_3600[keys + ["status", "cmax", "bound", "time_s", "gap_pct"]],
            on=keys,
            suffixes=("_600s", "_3600s"),
        )
        _save_table(
            merged,
            out_dir,
            "table_600s_vs_3600s",
            "So sánh kết quả chạy 600s và đợt bổ sung 3600s",
        )


# ---------------------------------------------------------------------------
# 4. Vẽ biểu đồ Gantt cho 1 bài (ft06 hoặc la01)
# ---------------------------------------------------------------------------
def plot_gantt_chart(inst_name: str, out_path: Path) -> None:
    """Giải nhanh bài toán bằng CP-SAT và vẽ biểu đồ Gantt bằng cnsplots."""
    inst = load(inst_name)
    cfg = Config(method="CP", solver="cpsat")
    res = run_one(inst_name, cfg, time_limit=30.0)
    if res.schedule is None:
        raise RuntimeError(f"Không tìm thấy lịch biểu hợp lệ cho {inst_name}")

    cns.setup_matplotlib()
    fig = cns.figure(width=5.2, height=2.8)
    ax = fig.gca()

    palette = cns.palettes("tableau10") if hasattr(cns, "palettes") else plt.cm.tab10.colors

    for j, job in enumerate(inst.jobs):
        color = palette[j % len(palette)]
        for k, op in enumerate(job):
            start = res.schedule[j][k]
            dur = op.duration
            m = op.machine
            ax.barh(
                y=m,
                width=dur,
                left=start,
                height=0.62,
                color=color,
                edgecolor="black",
                linewidth=0.6,
                alpha=0.9,
            )
            if dur >= 2:
                ax.text(
                    start + dur / 2.0,
                    m,
                    f"J{j}",
                    ha="center",
                    va="center",
                    color="white",
                    fontsize=6.5,
                    fontweight="bold",
                )

    ax.axvline(res.cmax, color="crimson", linestyle="--", linewidth=1.1)
    ax.text(
        res.cmax,
        inst.n_machines - 0.35,
        f" Cmax = {res.cmax}",
        color="crimson",
        fontsize=7.5,
        fontweight="bold",
        va="bottom",
    )

    ax.set_yticks(range(inst.n_machines))
    ax.set_yticklabels([f"M{m}" for m in range(inst.n_machines)])
    ax.invert_yaxis()
    ax.set_xlabel("Thời gian")
    ax.set_ylabel("Máy")
    ax.set_title(f"Biểu đồ Gantt lịch gia công tối ưu — {inst.name} (Cmax = {res.cmax})")
    ax.grid(True, axis="x", linestyle=":", alpha=0.5)

    handles = [
        mpatches.Patch(color=palette[j % len(palette)], label=f"Job {j}")
        for j in range(inst.n_jobs)
    ]
    ax.legend(
        handles=handles,
        ncol=min(inst.n_jobs, 6),
        frameon=False,
        fontsize=6.5,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.18),
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    fig.savefig(out_path.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# 5. Điểm chạy chính
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="Vẽ hình và xuất bảng kết quả JSSP bằng cnsplots")
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument("--extra-3600", type=Path, default=RESULTS_DIR / "extra_3600s.csv")
    parser.add_argument("--bounds-json", type=Path, default=DATA_DIR / "bounds.json")
    parser.add_argument("--bks-csv", type=Path, default=DATA_DIR / "bks.csv")
    parser.add_argument("--gantt-instance", default="ft06", choices=["ft06", "la01"])
    parser.add_argument("--time-limit", type=float, default=600.0)
    args = parser.parse_args()

    exclude = {args.extra_3600.name} if args.extra_3600 else set()
    df_main = load_results_from_dir(args.results_dir, exclude, args.bounds_json, args.bks_csv)

    df_3600 = None
    if args.extra_3600 and args.extra_3600.exists():
        df_3600 = load_results_from_dir(
            args.extra_3600.parent,
            {p.name for p in args.extra_3600.parent.glob("*.csv") if p.name != args.extra_3600.name},
            args.bounds_json,
            args.bks_csv,
        )

    generate_all_cactus_plots(df_main, OUT_FIGS, time_limit=args.time_limit)
    generate_summary_tables(df_main, df_3600, OUT_TABLES)
    plot_gantt_chart(args.gantt_instance, OUT_FIGS / f"gantt_{args.gantt_instance}.png")
    print(f"Đã xuất hình tại {OUT_FIGS} và bảng tại {OUT_TABLES}")


if __name__ == "__main__":
    main()