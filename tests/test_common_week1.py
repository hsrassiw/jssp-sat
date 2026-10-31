from pathlib import Path
import math
import pytest
from src.common.data import DATA_DIR, ft06, read_instance
from src.common.instance import Instance, makespan
from src.common.bounds import lower_bound, upper_bound, time_windows, _earliest_gap
from src.common.verify import verify


def test_parser_ft06():
    assert read_instance(DATA_DIR / 'ft06.txt') == ft06()


@pytest.mark.parametrize('content', ['', '0 2\n', '1 2\n0 3\n',
    '1 1\n1 3\n', '1 1\n0 -1\n', '1 1\n0 3\n0 4\n'])
def test_parser_rejects_invalid(tmp_path, content):
    p = tmp_path / 'bad.txt'; p.write_text(content)
    with pytest.raises(ValueError): read_instance(p)


def test_bom_comments(tmp_path):
    p = tmp_path / 'small.txt'
    p.write_text('# test\n1 1\n0 3 # duration\n', encoding='utf-8-sig')
    assert read_instance(p).jobs[0][0].duration == 3


@pytest.mark.parametrize('path', sorted(DATA_DIR.glob('*.txt')), ids=lambda p:p.stem)
def test_benchmark_valid(path):
    inst = read_instance(path)
    ub, schedule = upper_bound(inst, trials=2)
    assert verify(inst, schedule) == []
    assert lower_bound(inst) <= ub == makespan(inst, schedule)


def test_greedy_reproducible_and_improves():
    inst = ft06()
    a = upper_bound(inst, trials=500, seed=42)
    assert a == upper_bound(inst, trials=500, seed=42)
    assert verify(inst, a[1]) == []
    assert 55 <= a[0] < 197


def test_zero_budget_fallback():
    ub, schedule = upper_bound(ft06(), time_limit=0)
    assert ub == 197
    assert verify(ft06(), schedule) == []


def test_gap_insertion():
    assert _earliest_gap([(5, 9), (12, 16)], 0, 4) == 0
    assert _earliest_gap([(5, 9), (12, 16)], 6, 3) == 9
    assert _earliest_gap([(5, 9), (12, 16)], 6, 4) == 16


def test_bounds_windows():
    inst = Instance.from_lists('tiny', [[(0, 3), (1, 2)], [(1, 4), (0, 1)]])
    assert lower_bound(inst) == 6
    assert time_windows(inst, 10) == ([[0, 3], [0, 4]], [[5, 8], [5, 9]])
    es, ls = time_windows(inst, 4)
    assert es[0][0] > ls[0][0]  # bất khả thi dưới horizon này
    assert lower_bound(ft06()) == 47


def test_verify_touching_allowed():
    inst = Instance.from_lists('tiny', [[(0, 3)], [(0, 2)]])
    assert verify(inst, [[0], [3]]) == []
    assert verify(inst, [[0], [2]])


@pytest.mark.parametrize('schedule', [[], [[0]], [[-1, 2]], [[0, 2]],
    [[float('nan'), 3]], [[0.0, 3]], [[True, 3]]])
def test_verify_rejects_invalid(schedule):
    inst = Instance.from_lists('tiny', [[(0, 3), (1, 2)]])
    assert verify(inst, schedule)


def test_zero_duration_orb07():
    inst = read_instance(DATA_DIR / 'orb07.txt')
    assert inst.jobs[9][9].duration == 0
    ub, schedule = upper_bound(inst, trials=10)
    assert verify(inst, schedule) == []
