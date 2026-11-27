"""Multi-competitor market: with competitor A alone it must reproduce the single-manager stand bit for bit."""
import numpy as np

from articles_prorotypes.bench import multi_competitor as mc
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


def test_single_competitor_equals_stand_offline_and_online():
    prep, pm, mg, our = _setup()
    off = pb.generate(prep, DAYS, SAMPLE, mg, our, pm, 0.8, 1, 50.0)
    one = mc.run_market(prep, DAYS, SAMPLE, [mg], our, pm, 0.8, 1, 50.0)
    for k in ("combo", "z", "v"):
        assert np.array_equal(one[k], off[k]), k
    bid = lambda c, v, z, i: 0.6 * v                       # any deterministic policy
    a = ob.run_online(prep, DAYS, SAMPLE, mg, our, pm, 0.8, 1, 50.0, bid)
    b = mc.run_market(prep, DAYS, SAMPLE, [mg], our, pm, 0.8, 1, 50.0, bid)
    for k in ("combo", "z", "v", "b", "won"):
        assert np.array_equal(a[k], b[k]), k


def test_our_limits_charge_our_campaigns_for_market_wins():
    prep, pm, mg, our = _setup()
    bid = lambda c, v, z, i: v - 1                          # wins whenever v > z + 1
    free = mc.run_market(prep, DAYS, SAMPLE, [mg], our, pm, 0.8, 1, 50.0, bid)
    real = mc.run_market(prep, DAYS, SAMPLE, [mg], our, pm, 0.8, 1, 50.0, bid, our_limits=True)
    assert np.array_equal(free["combo"], real["combo"])
    # with limits our value can only go down: v is the cpm of one eligible campaign, never above the best match
    assert np.all(real["v"] <= free["v"])
    # some requests end with every matching campaign of ours exhausted, so we do not bid there
    assert np.mean(real["v"] <= 0) > np.mean(free["v"] <= 0)
    assert real["won"].sum() < free["won"].sum()
    # market wins spend our limits, so our campaigns sell less on traffic outside the market
    assert real["our_outside_revenue"] < free["our_outside_revenue"]


def test_random_bid_is_row_aligned_offline_and_in_both_online_modes():
    prep, pm, mg, our = _setup()
    off = mc.run_market(prep, DAYS, SAMPLE, [mg], our, pm, 0.8, 1, 50.0)
    u = pb.random_bid_u(1, len(off["z"]))
    bid = lambda c, v, z, i: 50.0 + u[i] * max(v - 50.0, 0)
    ign = mc.run_market(prep, DAYS, SAMPLE, [mg], our, pm, 0.8, 1, 50.0, bid)
    lim = mc.run_market(prep, DAYS, SAMPLE, [mg], our, pm, 0.8, 1, 50.0, bid, our_limits=True)
    expected_off = 50.0 + u * np.maximum(off["v"] - 50.0, 0)
    assert np.allclose(ign["b"], expected_off)                       # online(ign) == offline rule, row by row
    same_v = (lim["v"] == ign["v"]) & (lim["v"] > 0)
    assert same_v.any() and np.allclose(lim["b"][same_v], ign["b"][same_v])  # same draw wherever v agrees


def test_more_competitors_raise_prices_and_cut_free_requests():
    prep, pm, mg, our = _setup()
    comps = [mg, mc.make_competitor(mg, 1001), mc.make_competitor(mg, 1002)]
    one = mc.run_market(prep, DAYS, SAMPLE, comps[:1], our, pm, 0.8, 1, 50.0)
    three = mc.run_market(prep, DAYS, SAMPLE, comps, our, pm, 0.8, 1, 50.0)
    assert np.array_equal(one["combo"], three["combo"])  # same request stream
    # not per request: B and C take impressions, so A spends its limits differently and can be cheaper somewhere
    assert three["z"].mean() > one["z"].mean()
    assert np.mean(three["z"] == 50) < np.mean(one["z"] == 50)
