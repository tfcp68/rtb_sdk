from dataclasses import dataclass

import numpy as np

from articles_prorotypes.bench import multi_competitor as mc


@dataclass
class FakePrep:
    combos: np.ndarray
    combo_counts: np.ndarray
    vocab_order: list
    vocabs: dict
    day_combos: list
    root: str = "fixture"
    @property
    def n_days(self): return len(self.day_combos)
    def day_arrays(self, day):
        combo = np.asarray(self.day_combos[day])
        return np.arange(len(combo)), np.zeros(len(combo), dtype=np.uint32), combo
    @property
    def meta(self): return {"days": [{"name": str(i)} for i in self.day_combos]}


def _prep(day_combos):
    combos = np.array([[0], [1], [2]], dtype=np.uint16)
    counts = np.bincount(np.concatenate(day_combos), minlength=len(combos))
    return FakePrep(combos, counts, ["device"], {"device": ["none", "a", "b"]}, day_combos)


def _ads():
    return [
        {"id": "a", "cpm": 10, "priority": 1, "targets": {"device": ["a"]}},
        {"id": "b", "cpm": 10, "priority": 1, "targets": {"device": ["b"]}},
    ]


def test_train_plan_ignores_future_counts_and_data_and_changes_with_training():
    from articles_prorotypes.bench.planning import build_planning_context

    train = [[1, 1, 1, 2], [1, 2, 2], [1, 1, 2, 2, 2]]
    prep = _prep(train + [[1] * 100, [2] * 100, [1] * 100])
    context = build_planning_context(prep, (0, 3), 1.0, np.array([False, True, True]))
    changed_future = _prep(train + [[2] * 500, [1] * 300, [2] * 200])
    context_future = build_planning_context(changed_future, (0, 3), 1.0, np.array([False, True, True]))
    assert context == context_future

    changed_train = _prep([[1] * 8, [1] * 8, [1] * 8] + [[1] * 100, [2] * 100, [1] * 100])
    context_train = build_planning_context(changed_train, (0, 3), 1.0, np.array([False, True, True]))
    assert context_train.match_counts != context.match_counts
    assert context_train.total_daily_rate != context.total_daily_rate


def test_simulate_and_market_build_identical_train_planned_volumes(monkeypatch):
    from articles_prorotypes.bench.planning import build_planning_context

    prep = _prep([[1, 1, 1, 2], [1, 2, 2], [1, 1, 2, 2, 2], [2] * 40, [1] * 30, [2] * 20])
    pool = np.array([False, True, True])
    context = build_planning_context(prep, (0, 3), 1.0, pool)
    ours, competitors = _ads(), [_ads()]
    packs = []
    class Pack:
        ids = ["a", "b"]
        names = ids
        cpm = [10, 10]
        volume = [1, 1]
        n = 2
        targets = [{}, {}]
    calls = []
    class Seller:
        def __init__(self, pack, *_):
            packs.append(pack)
            self.pack = pack
            self.impressions = [0, 0]
            self.total_impressions = self.requests = self.miss_nomatch = self.miss_filtered = 0
            self.revenue = 0
        def serve(self, *_): return -1
    import benchmarks.closed_stand.stand as stand
    monkeypatch.setattr(mc, "stand", stand)
    monkeypatch.setattr(stand, "count_requests", lambda *a: (70, 40))
    monkeypatch.setattr(stand, "build_pack", lambda *a, **kw: (calls.append((a[2], a[3], kw.get("planning_pool_only"))) or Pack()))
    monkeypatch.setattr(stand, "Seller", Seller)
    monkeypatch.setattr(stand, "build_match_lists", lambda *a: None)
    monkeypatch.setattr(stand, "iter_chunks", lambda *a: iter(()))
    stand.simulate(prep, (3, 4), 1.0, ours, ours, pool, .8, lambda: None, 150,
                   planning=context)
    stand_volumes = calls[:]
    calls.clear()
    monkeypatch.setattr(stand, "build_pack", lambda *a, **kw: (calls.append((a[2], a[3], kw.get("planning_pool_only"))) or Pack()))
    mc.build_market(prep, pool, competitors, .8, 1.0, (3, 4), planning=context)
    market_volumes = calls[:]
    assert stand_volumes[0] == market_volumes[0]
    assert stand_volumes[1][:2] == (4, 1)


def test_legacy_simulate_planning_argument_defaults_to_none():
    import inspect
    import benchmarks.closed_stand.stand as stand

    assert inspect.signature(stand.simulate).parameters["planning"].default is None
