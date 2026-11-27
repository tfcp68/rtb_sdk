"""Online benchmark invariants on a small real stand run: peek == serve, and no bids == offline replay."""
import numpy as np

from articles_prorotypes.bench import online_benchmark as ob
from articles_prorotypes.bench import price_benchmark as pb

st = pb.stand
SAMPLE, DAYS = 0.0003, (5, 6)


def _setup():
    prep = st.load_prepared(pb.ROOT / "benchmarks/logs/prepared_20261012_retry")
    pm = st.pool_mask_of(prep, st.POOL_DEVICES)
    mg = st.load_ads_file(str(pb.STAND_DIR / "manager_target50_20261012.json"))
    our = st.load_ads_file(str(pb.ROOT / "benchmarks/log_benchmark/ads_manual.json"))
    return prep, pm, mg, our


def test_peek_matches_serve_and_no_bid_replay_equals_offline():
    prep, pm, mg, our = _setup()
    mismatches = []

    class Check(st.Seller):
        def serve(self, t, u, c):
            p = ob.peek(self, t, u, c)
            w = super().serve(t, u, c)
            mismatches.append(p != w)
            return w

    original, st.Seller = st.Seller, Check
    try:
        st.simulate(prep, DAYS, SAMPLE, mg, our, pm, 0.8, lambda: pb.RandomShare(pm, prep.combos, 0.8, 1), 150.0, seed=1)
    finally:
        st.Seller = original
    assert mismatches and not any(mismatches)

    off = pb.generate(prep, DAYS, SAMPLE, mg, our, pm, 0.8, 1, 50.0)
    base = ob.run_online(prep, DAYS, SAMPLE, mg, our, pm, 0.8, 1, 50.0, lambda c, v, z, i: 0.0)
    assert np.array_equal(base["z"], off["z"]) and np.array_equal(base["v"], off["v"]) and not base["won"].any()
