"""Batch tuần tự, watchdog từng tiến trình, CSV nguyên tử và resume có manifest."""
from __future__ import annotations
import argparse
import csv
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import signal
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from src.common.bounds_cache import DEFAULT_BOUNDS_FILE, instance_hash, load_bounds
from src.common.data import load
from src.common.result import CSV_COLUMNS, Config, Result, ERR, NOSOL
from src.common.run import _check

ROOT=Path(__file__).resolve().parents[2]
KEY_COLUMNS=('instance','method','encoding','strategy','solver')


def atomic_text(path,text):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(dir=path.parent,prefix=path.name+'.',suffix='.tmp')
    try:
        with os.fdopen(fd,'w',encoding='utf-8',newline='') as f:
            f.write(text);f.flush();os.fsync(f.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)


@contextmanager
def csv_lock(path):
    """OS lock tự nhả khi process chết, dùng được trên Linux và Windows."""
    path=Path(str(path)+'.lock');path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a+b') as f:
        if f.tell()==0:f.write(b'0');f.flush()
        f.seek(0)
        if os.name=='nt':
            import msvcrt
            msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:yield
        finally:
            f.seek(0)
            if os.name=='nt':msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
            else:fcntl.flock(f,fcntl.LOCK_UN)


def read_rows(path):
    if not path.exists():return []
    with path.open(encoding='utf-8',newline='') as f:
        reader=csv.DictReader(f)
        if reader.fieldnames!=CSV_COLUMNS:raise ValueError('CSV khác format; chọn tên file mới')
        rows=list(reader)
    if any(set(row)!=set(CSV_COLUMNS) or any(v is None for v in row.values()) for row in rows):
        raise ValueError('CSV bị thiếu/corrupt; kiểm tra file trước khi resume')
    return rows


def save_rows(path,rows):
    import io
    buf=io.StringIO(newline='');w=csv.DictWriter(buf,fieldnames=CSV_COLUMNS)
    w.writeheader();w.writerows(rows);atomic_text(path,buf.getvalue())


def fingerprint(sources,configs,bounds_file,time_limit,cpsat_reference):
    files=sorted((ROOT/'src').rglob('*.py'))
    if cpsat_reference:files+=sorted((ROOT/'optional').glob('*.py'))
    digest=hashlib.sha256()
    for p in files:
        digest.update(str(p.relative_to(ROOT)).encode());digest.update(p.read_bytes())
    versions={}
    for package in ['python-sat','ortools','gurobipy','cplex','docplex']:
        try:versions[package]=importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:versions[package]=None
    return dict(format_version=1, source_sha256=digest.hexdigest(),
                bounds_sha256=hashlib.sha256(bounds_file.read_bytes()).hexdigest(),
                instances={load(s).name:instance_hash(load(s)) for s in sources},
                configs=[asdict(c) for c in configs],time_limit=time_limit,
                cpsat_reference=cpsat_reference,python=platform.python_version(),
                platform=platform.platform(),machine=platform.node(),versions=versions,
                timing='worker read+cache+build+solve; watchdog includes process startup; greedy excluded')


def guard_manifest(csv_path,manifest):
    path=Path(str(csv_path)+'.meta.json')
    if path.exists():
        if json.loads(path.read_text(encoding='utf-8'))!=manifest:
            raise ValueError('Code/cận/dữ liệu/cấu hình/môi trường đã đổi. Dùng --csv tên_mới.csv để tránh trộn kết quả.')
    elif csv_path.exists():
        raise ValueError('CSV cũ thiếu manifest; dùng --csv tên_mới.csv')
    else:atomic_text(path,json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')


def stop_process(proc):
    if proc.poll() is not None:return
    if os.name=='nt':
        subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        if proc.poll() is None:proc.kill()
    else:
        try:os.killpg(proc.pid,signal.SIGKILL)
        except ProcessLookupError:pass
    proc.wait()


def execute(source,cfg,*,bounds_file,time_limit,log_path,cpsat_reference=False):
    inst=load(source);lb,ub=load_bounds(inst,bounds_file)
    res=Result.new(inst.name,cfg);res.lb0=lb;res.ub0=ub;res.bound=lb
    t0=time.perf_counter()
    with tempfile.TemporaryDirectory(prefix='jssp-worker-') as directory:
        request=Path(directory)/'request.json';output=Path(directory)/'result.json'
        request.write_text(json.dumps(dict(source=str(source),config=asdict(cfg),bounds_file=str(bounds_file),
            deadline=t0+time_limit-min(1.0,time_limit*0.05),cpsat_reference=cpsat_reference)),encoding='utf-8')
        log_path.parent.mkdir(parents=True,exist_ok=True)
        with log_path.open('w',encoding='utf-8') as log:
            proc=subprocess.Popen([sys.executable,'-m','src.common.batch_worker','--request',str(request),'--output',str(output)],
                cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,start_new_session=os.name!='nt',
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name=='nt' else 0)
            try:
                proc.wait(timeout=max(.001,t0+time_limit-time.perf_counter()))
            except subprocess.TimeoutExpired:
                stop_process(proc);res.status=NOSOL
                res.note='Watchdog hết giờ: chưa nhận kết quả worker; không lấy lịch UB làm nghiệm.'
            except BaseException:
                stop_process(proc);raise
            else:
                if proc.returncode!=0 or not output.exists():
                    res.status=ERR;res.note=f'Worker exit={proc.returncode}; xem {log_path}'
                else:
                    try:
                        res=Result(**json.loads(output.read_text(encoding='utf-8')))
                        if res.key()!=(inst.name,*cfg.key()) or (res.lb0,res.ub0)!=(lb,ub):
                            # run_one trả ERR có thể chưa điền cận: vẫn lưu cận chung cho chẩn đoán.
                            if res.status!=ERR:raise ValueError('Worker trả khác cấu hình/cận')
                            res.lb0=lb;res.ub0=ub
                        _check(inst,res)
                    except Exception as exc:
                        res=Result.new(inst.name,cfg);res.status=ERR;res.lb0=lb;res.ub0=ub
                        res.note=f'Kết quả worker không hợp lệ: {exc}'
    if res.status in (ERR,NOSOL) and res.time_s==0:res.time_s=time.perf_counter()-t0
    atomic_text(Path(str(log_path)+'.result.json'),json.dumps(asdict(res),ensure_ascii=False,indent=2)+'\n')
    return res


def run_batch(sources,configs,*,csv_path,bounds_file=DEFAULT_BOUNDS_FILE,time_limit=600,cpsat_reference=False):
    if not math.isfinite(time_limit) or time_limit<=0:raise ValueError('time-limit phải hữu hạn và >0')
    csv_path=Path(csv_path).resolve();bounds_file=Path(bounds_file).resolve()
    sources=[str(Path(s).resolve()) if Path(s).exists() else str(s) for s in sources]
    names=[load(s).name for s in sources]
    if len(names)!=len(set(names)):raise ValueError('Danh sách instance trùng tên')
    for s in sources:load_bounds(load(s),bounds_file)  # lỗi cận: dừng trước khi chạy
    with csv_lock(csv_path):
        guard_manifest(csv_path,fingerprint(sources,configs,bounds_file,time_limit,cpsat_reference))
        rows=read_rows(csv_path)
        latest={tuple(r[k] for k in KEY_COLUMNS):r for r in rows}
        for source in sources:
            for cfg in configs:
                key=(load(source).name,*cfg.key())
                if key in latest and latest[key]['status'] in ('OPT','FEAS','NOSOL'):
                    print('SKIP',key,flush=True);continue
                label=hashlib.sha256(repr(key).encode()).hexdigest()[:16]
                log=csv_path.parent/(csv_path.stem+'_logs')/(label+'.log')
                res=execute(source,cfg,bounds_file=bounds_file,time_limit=time_limit,log_path=log,cpsat_reference=cpsat_reference)
                row=res.csv_row();rows.append(row);latest[key]=row
                save_rows(csv_path,rows)
                print(f'{res.instance} {cfg.key()} {res.status} cmax={res.cmax} bound={res.bound}',flush=True)
        return rows


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--instances',nargs='+',default=['ft06'])
    p.add_argument('--methods',nargs='+',choices=['SAT','CP','MIP'],default=['SAT','CP'])
    p.add_argument('--encodings',nargs='+',default=['E2'])
    p.add_argument('--strategies',nargs='+',default=['incremental'])
    p.add_argument('--sat-solvers',nargs='+',default=['cadical'])
    p.add_argument('--cp-solvers',nargs='+',choices=['cpsat','cplex'],default=['cpsat'])
    p.add_argument('--mip-solvers',nargs='+',choices=['gurobi','cplex'],default=['gurobi','cplex'])
    p.add_argument('--csv',type=Path,default=Path('results/batch.csv'))
    p.add_argument('--bounds-file',type=Path,default=DEFAULT_BOUNDS_FILE)
    p.add_argument('--time-limit',type=float,default=600)
    p.add_argument('--cpsat-reference',action='store_true',help='Dùng optional/cpsat_reference.py thay cho adapter chính')
    a=p.parse_args();configs=[]
    for method in dict.fromkeys(a.methods):
        if method=='SAT':
            for enc in a.encodings:
                for strategy in a.strategies:
                    for solver in a.sat_solvers:configs.append(Config('SAT',enc,strategy,solver))
        else:
            for solver in a.cp_solvers if method=='CP' else a.mip_solvers:
                configs.append(Config(method,solver=solver))
    configs=list(dict.fromkeys(configs))
    try:run_batch(a.instances,configs,csv_path=a.csv,bounds_file=a.bounds_file,time_limit=a.time_limit,cpsat_reference=a.cpsat_reference)
    except (ValueError,OSError) as exc:p.exit(2,f'{exc}\n')


if __name__=='__main__':main()
