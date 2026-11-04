import json
import sys
from pathlib import Path
import pytest
from src.common.batch import run_batch, execute, read_rows
from src.common.bounds_cache import DEFAULT_BOUNDS_FILE
from src.common.result import Config, Result, ERR, OPT, NOSOL


def test_resume_and_cache_manifest(tmp_path,monkeypatch):
    calls=[]
    def fake(source,cfg,**kwargs):
        calls.append(cfg.key());r=Result.new('ft06',cfg);r.status=OPT;r.cmax=55;r.bound=55;r.lb0=47;r.ub0=55
        return r
    monkeypatch.setattr('src.common.batch.execute',fake)
    path=tmp_path/'results.csv';cfg=[Config('SAT','E2','incremental','cadical'),Config('CP',solver='cpsat')]
    run_batch(['ft06'],cfg,csv_path=path)
    before=path.read_bytes();run_batch(['ft06'],cfg,csv_path=path)
    assert len(calls)==2 and path.read_bytes()==before
    bounds=tmp_path/'bounds.json';cache=json.loads(DEFAULT_BOUNDS_FILE.read_text());cache['instances']['ft06']['seed']=77
    bounds.write_text(json.dumps(cache))
    with pytest.raises(ValueError,match='đổi'):run_batch(['ft06'],cfg,csv_path=path,bounds_file=bounds)
    assert path.read_bytes()==before


def test_err_retried_and_partial_resume(tmp_path,monkeypatch):
    path=tmp_path/'r.csv';cfg=[Config('CP',solver='cpsat')];calls=[]
    def fake(source,cfg,**kwargs):
        calls.append(source);r=Result.new(source,cfg);r.status=ERR if len(calls)==1 else NOSOL;return r
    monkeypatch.setattr('src.common.batch.execute',fake)
    run_batch(['ft06'],cfg,csv_path=path);run_batch(['ft06'],cfg,csv_path=path)
    assert len(calls)==2
    run_batch(['ft06'],cfg,csv_path=path)
    assert len(calls)==2 and len(read_rows(path))==2


def test_watchdog_terminates_child(tmp_path,monkeypatch):
    import subprocess,time
    original=subprocess.Popen
    def sleeper(args, **kw):
    # Chỉ giả lập worker; để taskkill chạy bình thường.
        if isinstance(args, (list, tuple)) and "src.common.batch_worker" in args:
            return original(
                [sys.executable, "-c", "import time; time.sleep(60)"],
                **kw,
            )
        return original(args, **kw)
    monkeypatch.setattr('src.common.batch.subprocess.Popen',sleeper)
    t0=time.perf_counter()
    res=execute('ft06',Config('CP',solver='cpsat'),bounds_file=DEFAULT_BOUNDS_FILE,time_limit=.2,log_path=tmp_path/'timeout.log')
    assert time.perf_counter()-t0<3
    assert res.status==NOSOL and res.cmax is None
    assert 'Watchdog' in res.note


def test_batch_real_e2_cpsat(tmp_path):
    pytest.importorskip('ortools');pytest.importorskip('pysat')
    configs=[Config('SAT','E2','incremental','cadical'),Config('CP',solver='cpsat')]
    rows=run_batch(['ft06'],configs,csv_path=tmp_path/'smoke.csv',time_limit=20,cpsat_reference=True)
    assert len(rows)==2
    assert all(r['status']=='OPT' and r['cmax']=='55' for r in rows)
    assert len({(r['lb0'],r['ub0']) for r in rows})==1
