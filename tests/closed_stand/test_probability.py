import json

import numpy as np
import pytest

from benchmarks.closed_stand.probability_metrics import metrics, cluster_intervals, selection_over_time


def test_hourly_selection_uses_local_quota_and_random_ties():
    y = np.array([1, 0, 1, 0, 0, 1])
    ts = np.array([0, 10, 3599, 3600, 3610, 10800])
    p = np.array([.9, .5, .5, .5, .5, .1])
    rows = selection_over_time(y, p, ts, quota=.5)
    assert [r['start_s'] for r in rows] == [0, 3600, 10800]
    assert [r['n'] for r in rows] == [3, 2, 1]
    assert [r['selected'] for r in rows] == [2, 1, 1]
    assert rows[0]['sellthrough'] == .75
    assert rows[0]['lift'] == pytest.approx(.75 / (2 / 3))
    assert rows[1]['sellthrough'] == 0 and rows[1]['lift'] is None
    assert rows[2]['sellthrough'] == 1
    ii = np.array([5, 3, 1, 4, 0, 2])
    assert rows == selection_over_time(y[ii], p[ii], ts[ii], quota=.5)
    assert all(r['sellthrough'] == r['actual'] for r in selection_over_time(y, p, ts, quota=1))
    baseline = selection_over_time(y, np.full(len(y), .5), ts, quota=.5)
    assert all(r['sellthrough'] == r['actual'] for r in baseline)
    assert selection_over_time([], [], []) == []


def test_known_probability_losses_and_calibration():
    y, p = np.array([1, 0, 1, 0]), np.array([.9, .9, .1, .1])
    m = metrics(y, p, .5, bins=2)
    assert m['brier'] == pytest.approx(.41)
    assert m['logloss'] == pytest.approx(-.5 * (np.log(.9) + np.log(.1)))
    assert m['ece'] == pytest.approx(.4)
    assert m['rmsce'] == pytest.approx(.4)
    assert m['bias'] == pytest.approx(0)
    assert m['roc_auc'] == pytest.approx(.5)
    assert m['average_precision'] == pytest.approx(.5)
    assert m['brier_skill'] == pytest.approx(1 - .41 / .25)


def test_tied_selection_is_order_invariant_and_one_class_is_explicit():
    tied = metrics([1, 0, 1, 0], [.9, .5, .5, .1], .5)
    assert tied['roc_auc'] == pytest.approx(.875)
    assert tied['average_precision'] == pytest.approx(5 / 6)
    for y in (np.array([1, 1, 0, 0]), np.array([0, 1, 0, 1])):
        m = metrics(y, np.full(4, .5), .5, quota=.5)
        assert m['roc_auc'] == .5 and m['average_precision'] == .5
        assert all(s['sellthrough'] == .5 and s['lift'] == 1 for s in m['selection'])
    m = metrics(np.zeros(4), np.zeros(4), 0)
    assert m['brier'] == 0 and m['brier_skill'] is None
    assert m['roc_auc'] is None and m['average_precision'] is None
    assert m['selection'][0]['lift'] is None
    m = metrics(np.array([0, 1]), np.array([0, 1]), .5)
    assert m['roc_auc'] == 1 and m['average_precision'] == 1
    assert m['calibration'][-1]['bin'] == 9
    assert np.isfinite(m['logloss'])


def test_cluster_bootstrap_resamples_users_and_is_repeatable():
    # Each user has 100 identical observations. Request bootstrap would be much narrower.
    y = np.repeat([0, 1], 100)
    user = np.repeat([11, 22], 100)
    p = np.full(200, .5)
    first = cluster_intervals(y, p, user, repeats=100)
    assert first == cluster_intervals(y, p, user, repeats=100)
    assert first['metrics']['bias'] == [-.5, .5]
    assert first['metrics']['brier'] == [.25, .25]
    assert first['calibration']['5']['actual'] == [0, 1]
    assert cluster_intervals(y, p, np.zeros(200))['metrics'] == {}


def test_metrics_reject_invalid_probabilities():
    for p in ([np.nan], [-.1], [1.1]):
        with pytest.raises(ValueError):
            metrics([1], p, .5)


def test_both_modes_alignment_artifacts_and_no_overwrite(tmp_path):
    from benchmarks.closed_stand import benchmark_probability as bench
    prepared = tmp_path / 'prepared'
    prepared.mkdir()
    fields = ['Region', 'Device', 'Child', 'Category', 'Channel']
    vocabs = {f: ['<none>', 'A', 'B'] for f in fields}
    vocabs['Device'] = ['<none>', 'ANDROID_TV_A', 'SET_TOP_BOX_A']
    meta = dict(vocab_order=fields, t0=0, vocabs=vocabs, days=[{'name': str(d)} for d in range(3)])
    (prepared / 'meta.json').write_text(json.dumps(meta))
    np.save(prepared / 'combos.npy', np.array([[1]*5, [2]*5], dtype=np.uint16))
    np.save(prepared / 'combo_counts.npy', np.array([150, 150]))
    for d in range(3):
        np.save(prepared / f'{d}_ts.npy', d * 86400 + np.arange(100)*60)
        np.save(prepared / f'{d}_user.npy', np.arange(100, dtype=np.uint32) % 10)
        np.save(prepared / f'{d}_combo.npy', np.arange(100) % 2)
        status = np.where(np.arange(100) % 2, 204, 200)
        status[0] = 500
        np.save(prepared / f'{d}_status.npy', status)
    ads = tmp_path / 'ads.json'
    ads.write_text(json.dumps([dict(id='a', name='A', cpm=100, priority=1, limits='none', targets={'Region': ['A']})]))
    args = bench.parser().parse_args(['--name', 'case', '--prepared', str(prepared), '--manager-ads', str(ads),
                                     '--output-root', str(tmp_path / 'out'), '--days', '0:3', '--split-day', '2',
                                     '--sample', '1', '--q', '1', '--bootstrap', '10', '--slice-min', '5',
                                     '--min-support', '5'])
    reports = bench.run(args)
    assert reports['historical']['source']['excluded_statuses'] == 3
    assert reports['historical']['test_n'] == 99
    assert reports['simulator']['test_n'] == 100
    for mode, report in reports.items():
        root = tmp_path / 'out' / 'case' / mode
        frame = bench.pl.read_parquet(root / 'test_predictions.parquet')
        assert frame.height == report['test_n']
        expected = [204 if (t % 86400 // 60) % 2 else 200 for t in frame['ts'].to_list()]
        assert frame['actual_status'].to_list() == expected
        observations = bench.pl.read_parquet(root / 'observations.parquet')
        assert observations['status'].to_numpy()[frame['row'].to_numpy()].tolist() == expected
        assert (root / 'diagnostics.png').stat().st_size > 100
        assert (root / 'sellout_over_time.png').stat().st_size > 100
        text = (root / 'report.md').read_text()
        assert 'Guide: interpreting probability quality' in text and 'Charts and tables' in text
        assert '| Region |' not in text
        assert report['time_series']['origin_unix'] == 0
        for result in report['algorithms'].values():
            assert all(s['field'] != 'Region' for s in result['slices'])
            rows = result['selection_over_time']
            assert sum(r['n'] for r in rows) == report['test_n']
            assert all(r['q'] == args.quota for r in rows)
        assert len(report['algorithms']) == 9
    with pytest.raises(FileExistsError):
        bench.run(args)


def test_online_scores_do_not_see_current_hour_labels(monkeypatch):
    from types import SimpleNamespace
    from benchmarks.closed_stand import benchmark_probability as bench
    class FakeModel:
        def __init__(self, *a, **kw):
            self.total = 0
        def update(self, tags, y, ts, user):
            self.total += int(y.sum())
        def score(self, tags, ts, user):
            return np.full(len(ts), self.total / 100)
    monkeypatch.setattr(bench.stand, 'HierBeta', FakeModel)
    prep = SimpleNamespace(combos=np.ones((1, 5)), vocab_order=[])
    log = dict(combo=np.zeros(4, dtype=int), status=np.array([200]*4),
               ts=np.array([0, 3600, 3601, 7200]), user=np.ones(4))
    args = SimpleNamespace(m=20)
    p = bench.predict('hier_beta', prep, log, np.array([True, False, False, False]), args)
    assert p.tolist() == [.01, .01, .03]
    log['status'][1:3] = 204
    changed = bench.predict('hier_beta', prep, log, np.array([True, False, False, False]), args)
    assert changed.tolist() == [.01, .01, .01]
