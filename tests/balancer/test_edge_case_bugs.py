"""Edge-case and bug tests of the balancer's computational core.

This module deliberately targets the weak spots:
  * invalid values that pass validation (range checks are absent);
  * division by zero / log(0) at range boundaries;
  * empty structures and zeros;
  * semantic (logic) bugs in the Ad → InnerAd → LP chain.

Originally these tests documented FOUR confirmed bugs (A–D) via
@pytest.mark.xfail. After the bugs were fixed the markers were removed — this is regression protection:
if some bug comes back, the corresponding test fails again.
"""

import pytest

from rtb_sdk.balancer.functions.balance_traffic import balance_traffic
from rtb_sdk.balancer.functions.add_campaign import add_new_balanced_campaign
from rtb_sdk.helpers.balancer.inner_ad_helpers import ad_to_inner, build_ads_real_volumes
from rtb_sdk.errors.balancer import BalancerError


# ---------------------------------------------------------------------------
# Input data factories in the OUTER (Ad / BalancingParams) format
# ---------------------------------------------------------------------------

def _outer_ad(ad_id="ad1", tags=("msk",), cpm=5.0, volume=0, freq_d=None):
    """Outer Ad. freq_d=None → the ad_frequency_limit field is absent altogether
    (the typical real-world case of "no frequency limit")."""
    ad: dict = {
        "id": ad_id,
        "targets": {"value": {"geo": list(tags)}},
        "cpm": cpm,
        "volume": volume,  # 0 == "no upper limit" per the spec
    }
    if freq_d is not None:
        ad["ad_frequency_limit"] = {"value": {"d": freq_d}}
    return ad


def _params(total=100_000, probs=None, **extra):
    if probs is None:
        probs = {"msk": 0.5, "spb": 0.5}
    p: dict = {
        "total_traffic_volume": total,
        "vocabs": {"geo": [f"geo:{k}" for k in probs.keys()]},
        "tag_probabilities": {f"geo:{k}": v for k, v in probs.items()},
    }
    p.update(extra)
    return p


# ===========================================================================
# BUG A (logic, high severity) — FIXED:
#   Previously ad_to_inner() for an Ad without ad_frequency_limit set freq=1, and
#   build_ads_real_volumes() hard-clipped the real maximum volume by freq —
#   the ad got at most 1 impression. Now "no limit" is encoded
#   as MAX_VOL_UNLIMITED, and the frequency cap does not bind the volume.
# ===========================================================================

def test_ad_without_freq_limit_does_not_cap_freq_to_one():
    """Without a frequency limit freq → MAX_VOL_UNLIMITED (the cap does not fire),
    rather than 1 (which would collapse the volume)."""
    from rtb_sdk.constants.balancer_constants import MAX_VOL_UNLIMITED
    inner = ad_to_inner(_outer_ad(freq_d=None))
    assert inner["freq"] == MAX_VOL_UNLIMITED
    # volume=0 is correctly turned into "unlimited"
    assert inner["max_vol"] > 1


def test_build_ads_real_volumes_no_freq_limit_should_not_collapse_to_one():
    """real_max must reflect flow_volume (total*P(ad)), not collapse to 1."""
    inner = ad_to_inner(_outer_ad(freq_d=None))
    rm = build_ads_real_volumes({"ad1": inner}, 100_000, {"ad1": 0.5})
    # expect ~50000 (total*P(ad)), not a collapse to 1
    assert rm["ad1"] == pytest.approx(50_000)


def test_balance_traffic_no_freq_limit_distributes_real_volume():
    """A single ad without a frequency limit should take ~ total*P(ad)."""
    res = balance_traffic({"ad1": _outer_ad(freq_d=None)}, _params(total=100_000))
    assert res["ad1"] == pytest.approx(50_000, rel=0.05)


def test_balance_traffic_with_high_freq_limit_distributes_real_volume():
    """Control: the same case, but with a large explicit freq limit — works correctly."""
    res = balance_traffic({"ad1": _outer_ad(freq_d=10**9)}, _params(total=100_000))
    # P(msk)=0.5 → ~50000
    assert res["ad1"] == pytest.approx(50_000, rel=0.05)


def test_add_campaign_frozen_volume_above_one_without_freq_limit():
    """Freezing an existing ad at a volume > 1 must not fail
    because real_max was collapsed to 1 by the frequency cap."""
    ads = {
        "old": _outer_ad("old", freq_d=None),
        "new": _outer_ad("new", freq_d=None),
    }
    # old is frozen at 300 impressions
    p = _params(total=100_000)
    p['ad_vol_distr'] = {"old": 300}
    result = add_new_balanced_campaign(ads, p)
    assert result["report"]["old"] == 300


# ===========================================================================
# BUG B (validation gap → raw crash):
#   min_category_probability == 0.0 passes is_valid_min_category_probability
#   (which only requires >= 0), but choose_top computes -log(0) → ValueError, rather than
#   BalancerError. The range boundary crashes the process with an unwrapped exception.
# ===========================================================================

def test_min_category_probability_zero_means_no_floor():
    """min_category_probability=0 — "no lower threshold": does not fail with ValueError
    (-math.log(0)), categories are taken up to max_n_categories, the volume is computed correctly."""
    ads = {"ad1": _outer_ad(freq_d=10**9)}
    res = balance_traffic(ads, _params(total=100_000, min_category_probability=0.0))
    assert res["ad1"] == pytest.approx(50_000, rel=0.05)


# ===========================================================================
# BUG C (validation gap):
#   is_valid_outer_tag_probabilities does not check the [0, 1] range.
#   * p > 1 → raw ValueError deep inside choose_top (rather than BalancerError);
#   * p < 0 → silently swallowed, the volume is computed incorrectly (no error).
# ===========================================================================

def test_tag_probability_above_one_should_raise_balancer_error():
    ads = {"ad1": _outer_ad(freq_d=10**9)}
    params = _params(total=1000, probs={"msk": 1.5})
    with pytest.raises(BalancerError):
        balance_traffic(ads, params)


def test_negative_tag_probability_should_raise_balancer_error():
    ads = {"ad1": _outer_ad(freq_d=10**9)}
    params = _params(total=1000, probs={"msk": -0.2, "spb": 0.5})
    with pytest.raises(BalancerError):
        balance_traffic(ads, params)


# ===========================================================================
# Correct boundary cases (regression — must pass)
# ===========================================================================

def test_empty_ads_returns_empty_distribution():
    res = balance_traffic({}, {"total_traffic_volume": 1000, "vocabs": {}, "tag_probabilities": {}})
    assert res == {}


def test_zero_total_traffic_yields_zero_volume():
    res = balance_traffic({"ad1": _outer_ad(freq_d=10**9)}, _params(total=0))
    assert res["ad1"] == 0


def test_ad_targets_tag_absent_from_vocab_should_not_keyerror():
    """An ad tag that is not in the configured dictionary must not crash
    the process with a raw KeyError — we expect a validation error or a correct 0."""
    ads = {"ad1": _outer_ad(tags=("unknown",), freq_d=10**9)}
    params = _params(total=1000, probs={"msk": 0.5, "spb": 0.5})
    with pytest.raises(BalancerError):
        balance_traffic(ads, params)


def test_zero_cpm_maximize_money_does_not_crash():
    """cpm=0 with maximize_money: the objective coefficient is 0 for all variables —
    the LP stays valid, the volume can be anything in the feasible region."""
    ads = {"ad1": _outer_ad(cpm=0.0, freq_d=10**9)}
    res = balance_traffic(ads, _params(total=1000, objective="maximize_money"))
    assert res["ad1"] >= 0
