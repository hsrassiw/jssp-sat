import copy
import json
import pytest
from src.common.bounds_cache import instance_hash, load_bounds, write_cache, SCHEMA_VERSION
from src.common.data import ft06, DATA_DIR, read_instance
from src.common.instance import Instance
from src.common.prepare_bounds import compute_entry, prepare
from src.common.result import Config, Result, NOSOL, ERR
from src.common.run import run_one


def cache_for(tmp_path):
    inst = ft06()
    entry = compute_entry(inst, time_limit=0)
    path = tmp_path / 'bounds.json'
    write_cache(dict(schema_version=SCHEMA_VERSION, instances={'ft06':entry}), path)
    return path, entry


def test_roundtrip(tmp_path):
    path, entry = cache_for(tmp_path)
    assert load_bounds(ft06(), path) == (47, 197)
    assert instance_hash(ft06()) == instance_hash(read_instance(DATA_DIR/'ft06.txt'))


def test_skip_preserves_bytes(tmp_path, monkeypatch):
    path, _ = cache_for(tmp_path)
    before = path.read_bytes()
    def forbidden(*a, **kw): raise AssertionError('greedy called again')
    monkeypatch.setattr('src.common.prepare_bounds.compute_entry', forbidden)
    prepare(['ft06'], output=path)
    assert path.read_bytes() == before


def test_explicit_overwrite(tmp_path, monkeypatch):
    path, entry = cache_for(tmp_path)
    replacement = dict(entry, seed=9)
    monkeypatch.setattr('src.common.prepare_bounds.compute_entry', lambda *a, **kw:replacement)
    prepare(['ft06'], output=path, overwrite=True)
    assert json.loads(path.read_text())['instances']['ft06']['seed'] == 9


def test_changed_instance_rejected(tmp_path):
    path, _ = cache_for(tmp_path)
    inst=ft06()
    rows=[list(job) for job in inst.jobs]
    rows[0][0]=(2,2)
    changed=Instance.from_lists('ft06',rows)
    with pytest.raises(ValueError, match='cache'):load_bounds(changed,path)


@pytest.mark.parametrize('damage', ['schedule','ub0','missing','schema'])
def test_bad_cache_rejected(tmp_path, damage):
    path, entry=cache_for(tmp_path)
    cache=json.loads(path.read_text())
    if damage=='schedule':cache['instances']['ft06']['schedule'][0][0]=-1
    elif damage=='ub0':cache['instances']['ft06']['ub0']=198
    elif damage=='missing':cache['instances']={}
    else:cache['schema_version']=999
    write_cache(cache,path)
    with pytest.raises(ValueError):load_bounds(ft06(),path)


def test_run_reuses_bounds_for_different_methods(tmp_path, monkeypatch):
    path, _=cache_for(tmp_path)
    def forbidden(*a, **kw): raise AssertionError('bounds recomputed')
    monkeypatch.setattr('src.common.bounds.upper_bound',forbidden)
    monkeypatch.setattr('src.common.bounds.lower_bound',forbidden)
    seen=[]
    def fake_solve(inst,cfg,*,lb0,ub0,deadline):
        seen.append((lb0,ub0))
        return Result.new(inst.name,cfg)
    before=path.read_bytes()
    for method in ['SAT','CP','MIP']:
        result=run_one('ft06',Config(method=method),solve=fake_solve,bounds_file=path)
        assert result.status==NOSOL
        assert (result.lb0,result.ub0)==(47,197)
    assert seen==[(47,197)]*3
    assert path.read_bytes()==before


def test_run_missing_cache_is_error(tmp_path):
    def forbidden(*a,**kw):raise AssertionError('solver must not run')
    result=run_one('ft06',Config(method='SAT'),solve=forbidden,bounds_file=tmp_path/'absent.json')
    assert result.status==ERR
    assert 'prepare_bounds' in result.note


def test_partial_progress_saved(tmp_path):
    path=tmp_path/'bounds.json'
    with pytest.raises(FileNotFoundError):prepare(['ft06', tmp_path/'absent.txt'],output=path,time_limit=0)
    assert load_bounds(ft06(),path)==(47,197)
