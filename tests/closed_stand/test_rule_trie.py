import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "benchmarks" / "closed_stand"))
from predictors import RuleTrie
from routers import RandomShare, ThresholdQuota


VOCABS = ["Region", "Device", "Child", "Category", "Channel"]


def test_rule_trie_learns_channel_independently_of_other_tags():
    tags = np.array([[1, 1, 0, 0, 1], [2, 2, 1, 0, 2]] * 100, dtype=np.uint16)
    model = RuleTrie(VOCABS, m=5)
    model.update(tags, np.tile([1, 0], 100))
    assert model.score(tags[:1])[0] > model.score(tags[1:2])[0]
    assert np.isfinite(model.score(np.array([[3, 3, 1, 0, 3]]))).all()
    labels = {v: ["none", "one", "two", "three"] for v in VOCABS}
    rules = model.top_rules(VOCABS, labels, min_count=100, limit=100)
    assert any(r["tags"] == {"Channel": "one"} and r["successes"] == 100 for r in rules)


def test_routers_never_send_outside_pool():
    combos = np.array([[1, 1, 0, 0, 1], [2, 2, 1, 0, 2]], dtype=np.uint16)
    mask = np.array([True, False])
    model = RuleTrie(VOCABS)
    model.update(combos, np.array([1, 0]))
    for router in (RandomShare(mask, combos, 0.8), ThresholdQuota(mask, combos, model, 0.8)):
        choice = router.route(np.arange(200), np.arange(200), np.tile([0, 1], 100))
        assert not choice[1::2].any()
