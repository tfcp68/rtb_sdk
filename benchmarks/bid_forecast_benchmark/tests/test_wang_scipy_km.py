"""wang2016._distribution keeps a hand-written Kaplan-Meier (16x faster than scipy on the tree's tiny nodes);
this pins it to scipy.stats.ecdf on censored data."""
import random

import numpy as np
from scipy import stats

from articles_prorotypes.wang.wang2016 import AuctionObservation, _distribution


def test_hand_written_kaplan_meier_matches_scipy():
    rng = random.Random(1)
    obs = []
    for _ in range(2000):
        z, b = rng.choice([100, 150, 180, 200, 300]), float(rng.randint(50, 360))
        obs.append(AuctionObservation({}, b, b > z, float(z) if b > z else None))
    mine = _distribution(obs)
    t = np.array([o.market_price if o.won else o.bid for o in obs])
    won = np.array([o.won for o in obs])
    cdf = stats.ecdf(stats.CensoredData(uncensored=t[won], right=t[~won])).cdf
    ref = dict(zip(cdf.quantiles.tolist(), np.diff(np.concatenate([[0.0], cdf.probabilities])).tolist()))
    for price in set(ref) | set(mine.masses):
        assert abs(ref.get(price, 0.0) - mine.masses.get(price, 0.0)) < 1e-12
    assert abs((1 - cdf.probabilities[-1]) - mine.tail_probability) < 1e-12
