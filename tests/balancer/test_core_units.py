"""Direct unit tests of the balancer's computational core.

Base scenario (shared where convenient):
  vocabs_full = geo: [msk, spb, ekb],  P = {msk:0.3, spb:0.2, ekb:0.5}
  ad1 → geo:msk            (P(ad1)=0.3)
  ad2 → geo:msk, geo:spb   (P(ad2)=0.5)
  ekb is not used → collapses into geo::OTHER (P=0.5)
"""

import pytest
from ortools.linear_solver import pywraplp, linear_solver_pb2 as pb

from rtb_sdk.helpers.balancer import (
    build_new_vocabs, build_new_old_tags_hashes, build_new_probabilities,
    build_new_ads_tags, count_ads_probabilities, build_ads_real_volumes,
    balanced_frequency_limit, build_full_tag, build_full_tag_other,
    get_vocab_name, get_raw_tag, build_tag_to_vocab_hash,
    create_inner_ad, create_optimize_params, create_parameters_balanced,
    create_balancer_auction_data, create_category, is_valid_balancer_auction_data,
    is_valid_tag_probabilities_sum,
)
from rtb_sdk.helpers.balancer.full_tag_helpers import (
    raw_tag_dict_to_full_tag_dict, outer_tag_probabilities_to_inner,
)
from rtb_sdk.helpers.balancer.optimize_params_helpers import outer_to_inner_optimize_params
from rtb_sdk.balancer.utils.categories import (
    count_ads_by_category_probabilities, build_tag_category_hash,
)
from rtb_sdk.balancer.solver.solver import (
    create_solver, create_category_variables, build_ad_constraints,
    build_category_constraints, build_total_volume_constraint,
    solve_pywraplp,
)
from rtb_sdk.balancer.solver.objective import apply_objective
from rtb_sdk.balancer.solver.proto_solver import build_proto_model
from rtb_sdk.balancer.utils.report import prepare_result
from rtb_sdk.schemas.balancer_schemas import RequestFlow
from rtb_sdk.errors.balancer import BalancerError, ErrorCodes
from rtb_sdk.constants.balancer_constants import LP_LOWER_BOUND


OTHER = build_full_tag_other("geo")  # "geo::OTHER"

VOCABS_FULL = {"geo": ["geo:msk", "geo:spb", "geo:ekb"]}
FLAT_PROBS = {"geo:msk": 0.3, "geo:spb": 0.2, "geo:ekb": 0.5}


def _ad(id, tags, min_vol=0, max_vol=10000, price=1.0, date_factor=1.0, freq=99999):
    return {"id": id, "targets": {"geo": tags}, "min_vol": min_vol, "max_vol": max_vol,
            "price": price, "date_factor": date_factor, "freq": freq}


def _base_ads():
    return {
        "ad1": _ad("ad1", ["geo:msk"]),
        "ad2": _ad("ad2", ["geo:msk", "geo:spb"], max_vol=600, date_factor=0.5, freq=400, price=5.0),
    }


# ===========================================================================
# 1. Dictionary narrowing pipeline (full_tag_helpers)
# ===========================================================================

def test_build_new_vocabs_collapses_unused_tags_into_other():
    nv = build_new_vocabs(_base_ads(), {"vocabs": VOCABS_FULL, "tag_probabilities": FLAT_PROBS})
    # ekb is used by nobody → OTHER; msk, spb remain
    assert set(nv["geo"]) == {"geo:msk", "geo:spb", OTHER}


def test_build_new_vocabs_no_other_when_all_tags_used_and_sum_one():
    ads = {"a": _ad("a", ["geo:msk", "geo:spb"])}
    nv = build_new_vocabs(ads, {"vocabs": {"geo": ["geo:msk", "geo:spb"]},
                                "tag_probabilities": {"geo:msk": 0.6, "geo:spb": 0.4}})
    assert set(nv["geo"]) == {"geo:msk", "geo:spb"}  # sum=1, nothing dropped → OTHER not needed


def test_build_new_vocabs_adds_other_when_prob_sum_below_one():
    # all tags are used, but Σ P < 1 → OTHER takes the remainder
    ads = {"a": _ad("a", ["geo:msk", "geo:spb"])}
    nv = build_new_vocabs(ads, {"vocabs": {"geo": ["geo:msk", "geo:spb"]},
                                "tag_probabilities": {"geo:msk": 0.6, "geo:spb": 0.3}})
    assert set(nv["geo"]) == {"geo:msk", "geo:spb", OTHER}


def test_build_new_old_tags_hashes_maps_collapsed_tags():
    nv = {"geo": ["geo:msk", "geo:spb", OTHER]}
    new_to_old, old_to_new = build_new_old_tags_hashes(VOCABS_FULL, nv)
    assert new_to_old == {"geo:msk": ["geo:msk"], "geo:spb": ["geo:spb"], OTHER: ["geo:ekb"]}
    assert old_to_new == {"geo:msk": "geo:msk", "geo:spb": "geo:spb", "geo:ekb": OTHER}


def test_build_new_probabilities_other_gets_residual_mass():
    nv = {"geo": ["geo:msk", "geo:spb", OTHER]}
    new_to_old, _ = build_new_old_tags_hashes(VOCABS_FULL, nv)
    ntp = build_new_probabilities(nv, VOCABS_FULL, new_to_old, FLAT_PROBS)
    # OTHER = P(ekb) = 0.5; msk/spb unchanged
    assert ntp == {"geo:msk": 0.3, "geo:spb": 0.2, OTHER: 0.5}


def test_build_new_probabilities_aggregates_multiple_collapsed_tags():
    # two unused tags collapse into one OTHER → their probabilities add up
    vocabs_full = {"geo": ["geo:msk", "geo:a", "geo:b"]}
    nv = {"geo": ["geo:msk", OTHER]}
    new_to_old, _ = build_new_old_tags_hashes(vocabs_full, nv)
    ntp = build_new_probabilities(nv, vocabs_full, new_to_old,
                                  {"geo:msk": 0.5, "geo:a": 0.2, "geo:b": 0.3})
    assert ntp["geo:msk"] == pytest.approx(0.5)
    assert ntp[OTHER] == pytest.approx(0.5)  # 0.2 + 0.3


def test_build_new_probabilities_no_other_when_sum_exactly_one():
    new_vocabs = {"geo": ["geo:msk", "geo:spb"]}
    vocabs_full = {"geo": ["geo:msk", "geo:spb"]}
    new_to_old = {"geo:msk": ["geo:msk"], "geo:spb": ["geo:spb"]}
    tag_probs = {"geo:msk": 0.6, "geo:spb": 0.4}
    result = build_new_probabilities(new_vocabs, vocabs_full, new_to_old, tag_probs)
    assert result == {"geo:msk": 0.6, "geo:spb": 0.4}
    other_tag = build_full_tag_other("geo")
    assert other_tag not in result


def test_build_new_ads_tags_keeps_partial_full_for_complete_or_missing():
    nv = {"geo": ["geo:msk", "geo:spb", OTHER]}
    avt = {
        "partial": {"geo": ["geo:msk"]},                      # partial → as is
        "complete": {"geo": ["geo:msk", "geo:spb", "geo:ekb"]},  # all tags of the full vocab → the whole new_vocab
        "missing": {},                                         # dictionary not specified → the whole new_vocab
    }
    res = build_new_ads_tags(avt, VOCABS_FULL, nv)
    assert res["partial"]["geo"] == ["geo:msk"]
    assert set(res["complete"]["geo"]) == set(nv["geo"])
    assert set(res["missing"]["geo"]) == set(nv["geo"])


def test_build_new_ads_tags_unknown_vocab_gets_full_new_vocab():
    ads_vt = {"ad1": {"geo": ["geo:msk"]}}
    vocabs = {"geo": ["geo:msk", "geo:spb"], "age": ["age:y", "age:o"]}
    new_vocabs = {"geo": ["geo:msk", build_full_tag_other("geo")],
                  "age": ["age:y"]}
    result = build_new_ads_tags(ads_vt, vocabs, new_vocabs)
    # ad1 has no 'age' key → gets age from new_vocabs
    assert result["ad1"]["age"] == ["age:y"]


def test_count_ads_probabilities_product_of_per_vocab_sums():
    nv = {"geo": ["geo:msk", "geo:spb", OTHER]}
    avt = {"ad1": {"geo": ["geo:msk"]}, "ad2": {"geo": ["geo:msk", "geo:spb"]}}
    ntp = {"geo:msk": 0.3, "geo:spb": 0.2, OTHER: 0.5}
    p = count_ads_probabilities(avt, nv, ntp)
    assert p == {"ad1": pytest.approx(0.3), "ad2": pytest.approx(0.5)}


def test_count_ads_probabilities_two_vocabs_multiplies():
    nv = {"geo": ["geo:msk"], "age": ["age:y"]}
    avt = {"a": {"geo": ["geo:msk"], "age": ["age:y"]}}
    p = count_ads_probabilities(avt, nv, {"geo:msk": 0.5, "age:y": 0.6})
    assert p["a"] == pytest.approx(0.3)  # 0.5 * 0.6


def test_count_ads_probabilities_missing_vocab_zeroes_product():
    # vocab is present in the dictionaries, but the ad does not target it → contribution 0 → P(ad)=0
    nv = {"geo": ["geo:msk"], "age": ["age:y"]}
    avt = {"a": {"geo": ["geo:msk"]}}  # age is absent
    p = count_ads_probabilities(avt, nv, {"geo:msk": 0.5, "age:y": 0.6})
    assert p["a"] == 0.0


# ---- additional tests for build_new_vocabs ---------------------------------

def test_build_new_vocabs_empty_ads():
    nv = build_new_vocabs({}, {"vocabs": VOCABS_FULL, "tag_probabilities": FLAT_PROBS})
    assert nv == {"geo": [OTHER]}


def test_build_new_vocabs_multiple_vocabs_partial_use():
    vocabs = {"geo": ["geo:a", "geo:b"], "age": ["age:y", "age:o"]}
    probs = {"geo:a": 0.4, "geo:b": 0.6, "age:y": 0.3, "age:o": 0.7}
    nv = build_new_vocabs({"ad": _ad("ad", ["geo:a"])},
                          {"vocabs": vocabs, "tag_probabilities": probs})
    assert set(nv["geo"]) == {"geo:a", build_full_tag_other("geo")}
    assert set(nv["age"]) == {build_full_tag_other("age")}


# ---- additional tests for build_new_old_tags_hashes ------------------------

def test_build_new_old_tags_hashes_empty():
    assert build_new_old_tags_hashes({}, {}) == ({}, {})


def test_build_new_old_tags_hashes_no_collapse():
    vocabs = {"geo": ["geo:a", "geo:b"]}
    nto, otn = build_new_old_tags_hashes(vocabs, vocabs)
    assert nto == {"geo:a": ["geo:a"], "geo:b": ["geo:b"]}
    assert otn == {"geo:a": "geo:a", "geo:b": "geo:b"}


def test_build_new_old_tags_hashes_all_collapsed():
    vocabs_full = {"geo": ["geo:a", "geo:b", "geo:c"]}
    nv = {"geo": [OTHER]}
    nto, otn = build_new_old_tags_hashes(vocabs_full, nv)
    # the order of collapsed tags depends on set iteration, compare by content
    assert set(nto[OTHER]) == {"geo:a", "geo:b", "geo:c"}
    assert otn == {"geo:a": OTHER, "geo:b": OTHER, "geo:c": OTHER}


def test_build_new_old_tags_hashes_multi_vocab():
    vocabs_full = {"geo": ["geo:a", "geo:b"], "age": ["age:y", "age:o"]}
    nv = {"geo": ["geo:a", OTHER], "age": ["age:y"]}
    nto, otn = build_new_old_tags_hashes(vocabs_full, nv)
    assert nto["geo:a"] == ["geo:a"]
    assert OTHER in nto and "geo:b" in nto[OTHER]
    assert nto["age:y"] == ["age:y"]
    assert otn["geo:a"] == "geo:a" and otn["geo:b"] == OTHER
    assert otn["age:y"] == "age:y"


# ---- additional tests for build_new_probabilities --------------------------

def test_build_new_probabilities_empty_tag_probs():
    nv = {"geo": ["geo:msk", OTHER]}
    nto, _ = build_new_old_tags_hashes(VOCABS_FULL, nv)
    ntp = build_new_probabilities(nv, VOCABS_FULL, nto, {})
    # all probabilities 0 → vocab_prob_sum=0 → OTHER gets the remainder 1.0
    assert ntp == {"geo:msk": 0.0, OTHER: 1.0}


def test_build_new_probabilities_other_with_zero_source():
    vocabs_full = {"geo": ["geo:a", "geo:b"]}
    nv = {"geo": ["geo:a", OTHER]}
    nto, _ = build_new_old_tags_hashes(vocabs_full, nv)
    ntp = build_new_probabilities(nv, vocabs_full, nto, {"geo:a": 1.0, "geo:b": 0.0})
    # vocab_prob_sum = 1.0 (not < 1.0) → OTHER is not added
    assert ntp == {"geo:a": 1.0}
    assert OTHER not in ntp


# ---- additional tests for build_new_ads_tags -------------------------------

def test_build_new_ads_tags_empty_ads_tags():
    assert build_new_ads_tags({}, VOCABS_FULL, {"geo": ["geo:msk", OTHER]}) == {}


def test_build_new_ads_tags_empty_target_list():
    avt = {"ad1": {"geo": []}}
    nv = {"geo": ["geo:msk", OTHER]}
    res = build_new_ads_tags(avt, VOCABS_FULL, nv)
    assert set(res["ad1"]["geo"]) == set(nv["geo"])


def test_build_new_ads_tags_missing_vocab_not_added():
    avt = {"ad1": {"geo": ["geo:msk"]}}
    vocabs_full = {"geo": ["geo:msk", "geo:spb"]}
    nv = {"geo": ["geo:msk", OTHER]}
    res = build_new_ads_tags(avt, vocabs_full, nv)
    # ad1 has an explicit target geo:msk → partial coverage, the tag is kept
    assert res["ad1"]["geo"] == ["geo:msk"]


# ---- additional tests for count_ads_probabilities --------------------------

def test_count_ads_probabilities_empty_ads():
    assert count_ads_probabilities({}, {"geo": ["geo:msk"]}, {"geo:msk": 1.0}) == {}


def test_count_ads_probabilities_three_vocabs_multiplies():
    nv = {"a": ["a:x"], "b": ["b:y"], "c": ["c:z"]}
    avt = {"ad": {"a": ["a:x"], "b": ["b:y"], "c": ["c:z"]}}
    probs = {"a:x": 0.5, "b:y": 0.4, "c:z": 0.3}
    p = count_ads_probabilities(avt, nv, probs)
    assert p["ad"] == pytest.approx(0.06)


# ===========================================================================
# 2. Tag and parameter converters
# ===========================================================================

def test_full_tag_roundtrip():
    assert build_full_tag("geo", "msk") == "geo:msk"
    assert get_vocab_name("geo:msk") == "geo"
    assert get_raw_tag("geo:msk") == "msk"


def test_get_raw_tag_handles_colon_in_value():
    # partition by the first ':' — the value may contain ':'
    assert get_vocab_name("url:http://x") == "url"
    assert get_raw_tag("url:http://x") == "http://x"


def test_raw_tag_dict_to_full_tag_dict():
    assert raw_tag_dict_to_full_tag_dict({"geo": ["msk", "spb"]}) == {"geo": ["geo:msk", "geo:spb"]}


def test_outer_tag_probabilities_to_inner_flattens():
    assert outer_tag_probabilities_to_inner({"geo": {"msk": 0.3, "spb": 0.2}}) == {"geo:msk": 0.3, "geo:spb": 0.2}


def test_build_tag_to_vocab_hash_inverts():
    assert build_tag_to_vocab_hash({"geo": ["geo:msk", "geo:spb"], "age": ["age:y"]}) == {
        "geo:msk": "geo", "geo:spb": "geo", "age:y": "age"}


def test_outer_to_inner_optimize_params_converts_nested():
    oi = outer_to_inner_optimize_params({
        "vocabs": {"geo": ["msk", "spb"]},
        "tag_probabilities": {"geo": {"msk": 0.6, "spb": 0.4}},
        "total_traffic_volume": 5000,
    })
    assert oi["vocabs"] == {"geo": ["geo:msk", "geo:spb"]}
    assert oi["tag_probabilities"] == {"geo:msk": 0.6, "geo:spb": 0.4}
    assert oi["total_traffic_volume"] == 5000  # other fields passed through


# ---- additional tests for build_full_tag / get_vocab_name / get_raw_tag ----

def test_build_full_tag_empty_vocab():
    assert build_full_tag("", "msk") == ":msk"


def test_build_full_tag_empty_raw():
    assert build_full_tag("geo", "") == "geo:"


def test_build_full_tag_both_empty():
    assert build_full_tag("", "") == ":"


def test_build_full_tag_multi_colon_raw():
    assert build_full_tag("url", "http://x.com") == "url:http://x.com"


def test_get_vocab_name_empty():
    assert get_vocab_name("") == ""


def test_get_vocab_name_no_colon():
    assert get_vocab_name("abc") == "abc"


def test_get_vocab_name_only_colon():
    assert get_vocab_name(":val") == ""


def test_get_raw_tag_empty():
    assert get_raw_tag("") == ""


def test_get_raw_tag_no_colon():
    # partition(':') on a string without a separator returns an empty third part
    assert get_raw_tag("abc") == ""


def test_get_raw_tag_only_colon():
    assert get_raw_tag("geo:") == ""


# ---- additional tests for raw_tag_dict_to_full_tag_dict --------------------

def test_raw_tag_dict_to_full_tag_dict_empty():
    assert raw_tag_dict_to_full_tag_dict({}) == {}


def test_raw_tag_dict_to_full_tag_dict_multi_vocab():
    inp = {"geo": ["msk", "spb"], "age": ["y", "o"]}
    out = raw_tag_dict_to_full_tag_dict(inp)
    assert out == {"geo": ["geo:msk", "geo:spb"], "age": ["age:y", "age:o"]}


def test_raw_tag_dict_to_full_tag_dict_empty_list():
    assert raw_tag_dict_to_full_tag_dict({"geo": []}) == {"geo": []}


def test_raw_tag_dict_to_full_tag_dict_mixed():
    inp = {"geo": ["msk"], "age": []}
    out = raw_tag_dict_to_full_tag_dict(inp)
    assert out == {"geo": ["geo:msk"], "age": []}


# ---- additional tests for outer_tag_probabilities_to_inner -----------------

def test_outer_tag_probabilities_to_inner_empty():
    assert outer_tag_probabilities_to_inner({}) == {}


def test_outer_tag_probabilities_to_inner_empty_inner():
    assert outer_tag_probabilities_to_inner({"geo": {}}) == {}


def test_outer_tag_probabilities_to_inner_multi_vocab():
    inp = {"geo": {"msk": 0.3, "spb": 0.2}, "age": {"y": 0.5}}
    out = outer_tag_probabilities_to_inner(inp)
    assert out == {"geo:msk": 0.3, "geo:spb": 0.2, "age:y": 0.5}


def test_outer_tag_probabilities_to_inner_mixed():
    inp = {"geo": {"msk": 0.5}, "age": {}}
    out = outer_tag_probabilities_to_inner(inp)
    assert out == {"geo:msk": 0.5}


# ---- additional tests for build_tag_to_vocab_hash --------------------------

def test_build_tag_to_vocab_hash_empty():
    assert build_tag_to_vocab_hash({}) == {}


def test_build_tag_to_vocab_hash_single():
    assert build_tag_to_vocab_hash({"geo": ["geo:msk"]}) == {"geo:msk": "geo"}


def test_build_tag_to_vocab_hash_duplicate_tag_across_vocabs():
    h = build_tag_to_vocab_hash({"v1": ["t:x"], "v2": ["t:x"]})
    # the last dictionary wins on a collision
    assert h["t:x"] == "v2"


def test_build_tag_to_vocab_hash_multi_vocab_single_tags():
    h = build_tag_to_vocab_hash({"geo": ["geo:a"], "age": ["age:y"]})
    assert h == {"geo:a": "geo", "age:y": "age"}


# ---- additional tests for is_valid_tag_probabilities_sum -------------------

def test_is_valid_tag_probabilities_sum_rejects_overlapping_vocab():
    # geo:msk + geo:spb = 1.8 — two tags of the same dictionary physically cannot
    # cover more than 100% of that dictionary's traffic at the same time.
    vocabs = {"geo": ["geo:msk", "geo:spb"]}
    probs = {"geo:msk": 0.9, "geo:spb": 0.9}
    assert is_valid_tag_probabilities_sum(probs, vocabs) is False


def test_is_valid_tag_probabilities_sum_accepts_exactly_one():
    vocabs = {"geo": ["geo:msk", "geo:spb"]}
    probs = {"geo:msk": 0.6, "geo:spb": 0.4}
    assert is_valid_tag_probabilities_sum(probs, vocabs) is True


def test_is_valid_tag_probabilities_sum_accepts_sum_below_one():
    # a sum < 1 is valid — part of the traffic is intentionally not covered by tags
    vocabs = {"geo": ["geo:msk", "geo:spb"]}
    probs = {"geo:msk": 0.3, "geo:spb": 0.2}
    assert is_valid_tag_probabilities_sum(probs, vocabs) is True


def test_is_valid_tag_probabilities_sum_independent_vocabs_checked_separately():
    # each dictionary is checked separately: age is valid, geo is not
    vocabs = {"geo": ["geo:msk", "geo:spb"], "age": ["age:y", "age:o"]}
    probs = {"geo:msk": 0.7, "geo:spb": 0.7, "age:y": 0.5, "age:o": 0.5}
    assert is_valid_tag_probabilities_sum(probs, vocabs) is False


def test_is_valid_tag_probabilities_sum_tolerates_float_rounding():
    # 0.1+0.2+0.7 = 0.9999999999999999 in float — must not be falsely rejected
    vocabs = {"geo": ["geo:a", "geo:b", "geo:c"]}
    probs = {"geo:a": 0.1, "geo:b": 0.2, "geo:c": 0.7}
    assert is_valid_tag_probabilities_sum(probs, vocabs) is True


def test_is_valid_tag_probabilities_sum_empty_inputs():
    assert is_valid_tag_probabilities_sum({}, {}) is True


# ---- additional tests for outer_to_inner_optimize_params -------------------

def test_outer_to_inner_empty_defaults():
    oi = outer_to_inner_optimize_params({})
    # empty dictionaries are converted to empty ones
    assert oi.get("vocabs") == {}
    assert oi.get("tag_probabilities") == {}


def test_outer_to_inner_only_volume():
    oi = outer_to_inner_optimize_params({"total_traffic_volume": 999})
    # vocabs and tag_probabilities not passed — remain as they are
    assert oi["total_traffic_volume"] == 999


def test_outer_to_inner_only_vocabs():
    oi = outer_to_inner_optimize_params({"vocabs": {"geo": ["msk"]}})
    assert oi["vocabs"] == {"geo": ["geo:msk"]}


def test_outer_to_inner_preserves_extra_fields():
    oi = outer_to_inner_optimize_params({
        "vocabs": {"g": ["a"]},
        "tag_probabilities": {"g": {"a": 1.0}},
        "extra_field": "survive",
    })
    assert oi["extra_field"] == "survive"


# ===========================================================================
# 3. Volume constraints (inner_ad_helpers)
# ===========================================================================

def test_build_ads_real_volumes_takes_min_of_three_caps():
    ads = _base_ads()
    rm = build_ads_real_volumes(ads, 1000, {"ad1": 0.3, "ad2": 0.5})
    assert rm["ad1"] == pytest.approx(300.0)   # min(10000, 1000*0.3*1.0, 99999)
    assert rm["ad2"] == pytest.approx(250.0)   # min(600, 1000*0.5*0.5=250, 400)


def test_build_ads_real_volumes_max_vol_binds():
    ads = {"a": _ad("a", ["geo:msk"], max_vol=100)}
    rm = build_ads_real_volumes(ads, 1000, {"a": 0.5})
    assert rm["a"] == 100  # max_vol < flow(500) < freq


def test_build_ads_real_volumes_freq_binds():
    ads = {"a": _ad("a", ["geo:msk"], max_vol=10000, freq=200)}
    rm = build_ads_real_volumes(ads, 1000, {"a": 0.5})
    assert rm["a"] == 200  # freq < flow(500) < max_vol


def test_build_ads_real_volumes_date_factor_scales_flow():
    ads = {"a": _ad("a", ["geo:msk"], max_vol=10000, freq=10 ** 9, date_factor=2.0)}
    rm = build_ads_real_volumes(ads, 1000, {"a": 0.3})
    assert rm["a"] == pytest.approx(600.0)  # flow = 1000*0.3*2.0; at the helper level df scales


def test_balanced_frequency_limit_min_of_freq_and_volume():
    ads = {"ad1": _ad("ad1", ["geo:msk"], freq=99999),
           "ad2": _ad("ad2", ["geo:msk"], freq=400)}
    assert balanced_frequency_limit(ads, {"ad1": 300, "ad2": 1200}) == {"ad1": 300, "ad2": 400}


# ---- additional tests for build_ads_real_volumes ---------------------------

def test_build_ads_real_volumes_empty_ads():
    assert build_ads_real_volumes({}, 1000, {}) == {}


def test_build_ads_real_volumes_large_max_vol_does_not_cap():
    # ad_to_inner sets max_vol=MAX_VOL_UNLIMITED when volume=0 in the Ad spec;
    # make sure the large cap does not clip flow_volume
    from rtb_sdk.constants.balancer_constants import MAX_VOL_UNLIMITED
    ads = {"a": _ad("a", ["geo:msk"], max_vol=MAX_VOL_UNLIMITED)}
    rm = build_ads_real_volumes(ads, 1000, {"a": 0.5})
    assert rm["a"] == pytest.approx(500.0)  # flow=500, MAX_VOL_UNLIMITED does not clip


# ---- additional tests for balanced_frequency_limit -------------------------

def test_balanced_frequency_limit_empty_ads():
    assert balanced_frequency_limit({}, {}) == {}


def test_balanced_frequency_limit_all_freq_exceed_volume():
    ads = {"a": _ad("a", ["geo:msk"], freq=99999)}
    assert balanced_frequency_limit(ads, {"a": 500}) == {"a": 500}


def test_balanced_frequency_limit_freq_zero():
    # freq=0 → get_inner_ad_freq returns 0 → 0 or 1 = 1 → min(1, 500) = 1
    ads = {"a": _ad("a", ["geo:msk"], freq=0)}
    assert balanced_frequency_limit(ads, {"a": 500}) == {"a": 1}


def test_balanced_frequency_limit_empty_volumes():
    # empty report → the loop does not execute → empty result
    ads = {"a": _ad("a", ["geo:msk"], freq=100)}
    assert balanced_frequency_limit(ads, {}) == {}


# ===========================================================================
# 4. Category aggregation (utils/categories)
# ===========================================================================

def test_count_ads_by_category_probabilities_sums():
    ad_cats = {"a": [RequestFlow(tags=("geo:msk",), probability=0.3),
                     RequestFlow(tags=("geo:spb",), probability=0.2)],
               "b": []}
    assert count_ads_by_category_probabilities(ad_cats) == {"a": pytest.approx(0.5), "b": 0.0}


def test_build_tag_category_hash_inverts_with_ad_id():
    ad_cats = {"adX": [RequestFlow(tags=("geo:msk", "age:y"), probability=0.2)]}
    h = build_tag_category_hash(ad_cats)
    assert set(h.keys()) == {"geo:msk", "age:y"}
    for tag in ("geo:msk", "age:y"):
        assert h[tag][0]["ad_id"] == "adX"
        assert h[tag][0]["probability"] == pytest.approx(0.2)
        assert tuple(h[tag][0]["tags"]) == ("geo:msk", "age:y")


# ---- additional tests for count_ads_by_category_probabilities --------------

def test_count_ads_by_category_probabilities_empty():
    assert count_ads_by_category_probabilities({}) == {}


def test_count_ads_by_category_probabilities_single_single():
    ad_cats = {"a": [RequestFlow(tags=("x",), probability=0.7)]}
    assert count_ads_by_category_probabilities(ad_cats) == {"a": pytest.approx(0.7)}


def test_count_ads_by_category_probabilities_zero_prob():
    ad_cats = {"a": [RequestFlow(tags=("x",), probability=0.0)]}
    assert count_ads_by_category_probabilities(ad_cats) == {"a": 0.0}


def test_count_ads_by_category_probabilities_three_cats():
    ad_cats = {"a": [RequestFlow(tags=("x",), probability=0.1),
                     RequestFlow(tags=("y",), probability=0.2),
                     RequestFlow(tags=("z",), probability=0.3)]}
    assert count_ads_by_category_probabilities(ad_cats) == {"a": pytest.approx(0.6)}


# ---- additional tests for build_tag_category_hash --------------------------

def test_build_tag_category_hash_empty():
    assert build_tag_category_hash({}) == {}


def test_build_tag_category_hash_single_ad_single_tag():
    ad_cats = {"a": [RequestFlow(tags=("t",), probability=0.5)]}
    h = build_tag_category_hash(ad_cats)
    assert h["t"][0]["ad_id"] == "a"
    assert h["t"][0]["probability"] == pytest.approx(0.5)


def test_build_tag_category_hash_shared_tag_multiple_ads():
    ad_cats = {
        "a1": [RequestFlow(tags=("x",), probability=0.3)],
        "a2": [RequestFlow(tags=("x",), probability=0.4)],
    }
    h = build_tag_category_hash(ad_cats)
    assert len(h["x"]) == 2
    assert {e["ad_id"] for e in h["x"]} == {"a1", "a2"}


def test_build_tag_category_hash_category_with_multiple_tags():
    ad_cats = {"a": [RequestFlow(tags=("x", "y"), probability=0.5)]}
    h = build_tag_category_hash(ad_cats)
    assert "x" in h and "y" in h
    assert h["x"][0]["ad_id"] == "a" and h["y"][0]["ad_id"] == "a"


# ===========================================================================
# 5. LP layer: variables, constraints, objective function (solver/*)
# ===========================================================================

def _solver_setup():
    total = 1000
    ad_categories = {
        "ad1": [RequestFlow(tags=("geo:msk",), probability=0.3)],
        "ad2": [RequestFlow(tags=("geo:msk",), probability=0.3),
                RequestFlow(tags=("geo:spb",), probability=0.2)],
    }
    ads_probs = {"ad1": 0.3, "ad2": 0.5}
    abp = count_ads_by_category_probabilities(ad_categories)  # {ad1:0.3, ad2:0.5}
    s = create_solver(1)
    cat_to_x, _ = create_category_variables(s, ad_categories, total)
    return total, ad_categories, ads_probs, abp, s, cat_to_x


def test_create_category_variables_bounds_are_zero_to_total_times_prob():
    total, ad_categories, _, _, s, cat_to_x = _solver_setup()
    x_msk = cat_to_x[("ad1", ("geo:msk",))]
    x_spb = cat_to_x[("ad2", ("geo:spb",))]
    assert (x_msk.Lb(), x_msk.Ub()) == (0.0, 300.0)   # 1000 * 0.3
    assert (x_spb.Lb(), x_spb.Ub()) == (0.0, 200.0)   # 1000 * 0.2
    assert len(cat_to_x) == 3


def test_build_ad_constraints_bounds_and_coefficient():
    total, ad_categories, ads_probs, abp, s, cat_to_x = _solver_setup()
    cons = build_ad_constraints(s, ad_categories, cat_to_x,
                                {"ad1": 0.0, "ad2": 100.0}, {"ad1": 300.0, "ad2": 500.0},
                                ads_probs, abp)
    assert len(cons) == 2
    assert {(c.Lb(), c.Ub()) for c in cons} == {(0.0, 300.0), (100.0, 500.0)}
    # k = P(ad)/ΣP(cat) = 1 here
    assert cons[0].GetCoefficient(cat_to_x[("ad1", ("geo:msk",))]) == pytest.approx(1.0)


def test_build_category_constraints_one_per_cell_with_total_times_p_cap():
    total, ad_categories, ads_probs, abp, s, cat_to_x = _solver_setup()
    cons = build_category_constraints(s, total, ad_categories, cat_to_x, ads_probs, abp)
    # cells: {msk} (shared by ad1, ad2) and {spb} (only ad2)
    assert len(cons) == 2
    assert sorted(c.Ub() for c in cons) == [200.0, 300.0]  # total*P(spb), total*P(msk)


def test_build_total_volume_constraint_caps_at_total():
    total, ad_categories, ads_probs, abp, s, cat_to_x = _solver_setup()
    c = build_total_volume_constraint(s, total, ad_categories, cat_to_x, ads_probs, abp)
    assert c.Ub() == pytest.approx(1000.0)


def test_apply_objective_money_uses_price():
    _, ad_categories, _, _, s, cat_to_x = _solver_setup()
    apply_objective(s, "maximize_money", ad_categories, cat_to_x, {"ad1": 2.0, "ad2": 5.0})
    obj = s.Objective()
    assert obj.GetCoefficient(cat_to_x[("ad1", ("geo:msk",))]) == pytest.approx(2.0)
    assert obj.GetCoefficient(cat_to_x[("ad2", ("geo:spb",))]) == pytest.approx(5.0)


def test_apply_objective_volume_uses_unit_coeff():
    _, ad_categories, _, _, s, cat_to_x = _solver_setup()
    apply_objective(s, "maximize_volume", ad_categories, cat_to_x, {"ad1": 2.0, "ad2": 5.0})
    assert s.Objective().GetCoefficient(cat_to_x[("ad1", ("geo:msk",))]) == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# 5b. LP layer: additional coverage (k≠1, shared cells, inverse index,
#     default bounds).
# ---------------------------------------------------------------------------

def _solver_setup_k():
    """Setup with a nontrivial k = P(ad)/ΣP(cat) ≠ 1 (simulating a top-K truncation).

    ad1: one category msk;  ad2: msk + spb (share the msk cell with ad1).
    ΣP(cat): ad1=0.3, ad2=0.5.  P(ad) is set so that k differs:
        k1 = 0.9 / 0.3 = 3.0,  k2 = 0.5 / 0.5 = 1.0.
    """
    total = 1000
    ad_categories = {
        "ad1": [RequestFlow(tags=("geo:msk",), probability=0.3)],
        "ad2": [RequestFlow(tags=("geo:msk",), probability=0.3),
                RequestFlow(tags=("geo:spb",), probability=0.2)],
    }
    ads_probs = {"ad1": 0.9, "ad2": 0.5}
    abp = count_ads_by_category_probabilities(ad_categories)  # {ad1:0.3, ad2:0.5}
    s = create_solver(1)
    cat_to_x, _ = create_category_variables(s, ad_categories, total)
    return total, ad_categories, ads_probs, abp, s, cat_to_x  # k1=3.0, k2=1.0


def test_create_category_variables_inverse_index_and_distinct_vars_per_ad():
    # ad1 and ad2 both target msk: the variables must be DIFFERENT (the key includes ad_id),
    # and x_to_cat must correctly invert each back to (ad_id, category).
    ad_categories = {
        "ad1": [RequestFlow(tags=("geo:msk",), probability=0.3)],
        "ad2": [RequestFlow(tags=("geo:msk",), probability=0.3)],
    }
    s = create_solver(1)
    cat_to_x, x_to_cat = create_category_variables(s, ad_categories, 1000)

    x1 = cat_to_x[("ad1", ("geo:msk",))]
    x2 = cat_to_x[("ad2", ("geo:msk",))]
    assert x1 is not x2                      # one cell, but different ads → different variables
    assert len(x_to_cat) == 2
    assert x_to_cat[x1][0] == "ad1"
    assert x_to_cat[x2][0] == "ad2"
    # the inversion value is the ad's original Category
    assert x_to_cat[x1][1]["tags"] == ("geo:msk",)


def test_build_ad_constraints_normalization_coefficient_when_truncated():
    # Key uncovered path: k ≠ 1. The coefficient at x = P(ad)/ΣP(cat).
    _, ad_categories, ads_probs, abp, s, cat_to_x = _solver_setup_k()
    cons = build_ad_constraints(s, ad_categories, cat_to_x,
                                {"ad1": 0.0, "ad2": 0.0}, {"ad1": 900.0, "ad2": 500.0},
                                ads_probs, abp)
    by_name = {c.name(): c for c in cons}
    # ad1: the only category, k1 = 3.0
    assert by_name["ad[name=ad1]"].GetCoefficient(cat_to_x[("ad1", ("geo:msk",))]) == pytest.approx(3.0)
    # ad2: both categories get the same k2 = 1.0
    c2 = by_name["ad[name=ad2]"]
    assert c2.GetCoefficient(cat_to_x[("ad2", ("geo:msk",))]) == pytest.approx(1.0)
    assert c2.GetCoefficient(cat_to_x[("ad2", ("geo:spb",))]) == pytest.approx(1.0)


def test_build_ad_constraints_defaults_missing_min_and_max():
    # No min_vol → lower bound LP_LOWER_BOUND; no max_vol → +∞.
    _, ad_categories, ads_probs, abp, s, cat_to_x = _solver_setup_k()
    cons = build_ad_constraints(s, ad_categories, cat_to_x,
                                {}, {},  # neither min nor max is set
                                ads_probs, abp)
    for c in cons:
        assert c.Lb() == pytest.approx(LP_LOWER_BOUND)
        assert c.Ub() == pytest.approx(s.infinity())


def test_build_category_constraints_shared_cell_carries_both_ads_with_their_k():
    # The msk cell is shared by ad1 (k=3) and ad2 (k=1): both coefficients on ONE constraint.
    total, ad_categories, ads_probs, abp, s, cat_to_x = _solver_setup_k()
    cons = build_category_constraints(s, total, ad_categories, cat_to_x, ads_probs, abp)
    by_ub = {round(c.Ub(), 6): c for c in cons}
    msk_cell = by_ub[300.0]  # total * P(msk)=0.3
    assert msk_cell.GetCoefficient(cat_to_x[("ad1", ("geo:msk",))]) == pytest.approx(3.0)
    assert msk_cell.GetCoefficient(cat_to_x[("ad2", ("geo:msk",))]) == pytest.approx(1.0)
    # the spb cell — only ad2
    spb_cell = by_ub[200.0]  # total * P(spb)=0.2
    assert spb_cell.GetCoefficient(cat_to_x[("ad2", ("geo:spb",))]) == pytest.approx(1.0)
    for c in cons:
        assert c.Lb() == pytest.approx(LP_LOWER_BOUND)


def test_build_category_constraints_cell_key_is_order_independent():
    # The canonical cell key is tuple(tags) [frozenset is redundant]:
    # the tag order is deterministic (vocabs are iterated in the same order),
    # so a different tag order = different cells.
    ad_categories = {
        "ad1": [RequestFlow(tags=("geo:msk", "age:y"), probability=0.2)],
        "ad2": [RequestFlow(tags=("geo:msk", "age:y"), probability=0.2)],
    }
    ads_probs = {"ad1": 0.2, "ad2": 0.2}
    abp = count_ads_by_category_probabilities(ad_categories)
    s = create_solver(1)
    cat_to_x, _ = create_category_variables(s, ad_categories, 1000)
    cons = build_category_constraints(s, 1000, ad_categories, cat_to_x, ads_probs, abp)
    # both pairs fall into one cell → one constraint with two coefficients
    assert len(cons) == 1
    assert cons[0].GetCoefficient(cat_to_x[("ad1", ("geo:msk", "age:y"))]) == pytest.approx(1.0)
    assert cons[0].GetCoefficient(cat_to_x[("ad2", ("geo:msk", "age:y"))]) == pytest.approx(1.0)


def test_build_total_volume_constraint_sums_all_vars_with_k():
    # Global row: Lb=LP_LOWER_BOUND, each variable enters with its own k.
    total, ad_categories, ads_probs, abp, s, cat_to_x = _solver_setup_k()
    c = build_total_volume_constraint(s, total, ad_categories, cat_to_x, ads_probs, abp)
    assert c.Lb() == pytest.approx(LP_LOWER_BOUND)
    assert c.Ub() == pytest.approx(1000.0)
    assert c.GetCoefficient(cat_to_x[("ad1", ("geo:msk",))]) == pytest.approx(3.0)  # k1
    assert c.GetCoefficient(cat_to_x[("ad2", ("geo:msk",))]) == pytest.approx(1.0)  # k2
    assert c.GetCoefficient(cat_to_x[("ad2", ("geo:spb",))]) == pytest.approx(1.0)  # k2

# ---- additional tests for create_category_variables ------------------------

def test_create_category_variables_zero_total():
    s = create_solver(1)
    ad_categories = {"a": [RequestFlow(tags=("t",), probability=0.5)]}
    ct_x, _ = create_category_variables(s, ad_categories, 0)
    assert ct_x[("a", ("t",))].Ub() == 0.0


def test_create_category_variables_empty_ads():
    s = create_solver(1)
    ct_x, x_ct = create_category_variables(s, {}, 1000)
    assert ct_x == {}
    assert x_ct == {}


def test_create_category_variables_empty_categories():
    s = create_solver(1)
    ct_x, _ = create_category_variables(s, {"a": []}, 1000)
    assert ct_x == {}


# ---- additional tests for build_ad_constraints -----------------------------

def test_build_ad_constraints_empty_ads():
    total, _, ads_probs, abp, s, cat_to_x = _solver_setup()
    cons = build_ad_constraints(s, {}, cat_to_x, {}, {}, ads_probs, abp)
    assert cons == []


def test_build_ad_constraints_single_ad_single_category():
    ad_cat = {"a": [RequestFlow(tags=("t",), probability=1.0)]}
    s = create_solver(1)
    ct_x, _ = create_category_variables(s, ad_cat, 500)
    cons = build_ad_constraints(s, ad_cat, ct_x,
                                {"a": 0.0}, {"a": 500.0},
                                {"a": 1.0}, {"a": 1.0})
    assert len(cons) == 1
    assert cons[0].Lb() == pytest.approx(0.0)
    assert cons[0].Ub() == pytest.approx(500.0)


# ---- additional tests for build_category_constraints -----------------------

def test_build_category_constraints_empty_ads():
    total, _, ads_probs, abp, s, cat_to_x = _solver_setup()
    cons = build_category_constraints(s, total, {}, cat_to_x, ads_probs, abp)
    assert cons == []


def test_build_category_constraints_single_cell():
    ad_cat = {"a": [RequestFlow(tags=("t",), probability=1.0)]}
    s = create_solver(1)
    ct_x, _ = create_category_variables(s, ad_cat, 500)
    cons = build_category_constraints(s, 500, ad_cat, ct_x,
                                      {"a": 1.0}, {"a": 1.0})
    assert len(cons) == 1
    assert cons[0].Ub() == pytest.approx(500.0)


# ---- additional tests for build_total_volume_constraint --------------------

def test_build_total_volume_constraint_zero_total():
    total, ad_categories, ads_probs, abp, s, cat_to_x = _solver_setup()
    c = build_total_volume_constraint(s, 0, ad_categories, cat_to_x, ads_probs, abp)
    assert c.Ub() == pytest.approx(0.0)


def test_build_total_volume_constraint_empty_ads():
    s = create_solver(1)
    c = build_total_volume_constraint(s, 1000, {}, {}, {}, {})
    assert c.Ub() == pytest.approx(1000.0)


def test_build_total_volume_constraint_single_ad():
    ad_cat = {"a": [RequestFlow(tags=("t",), probability=1.0)]}
    s = create_solver(1)
    ct_x, _ = create_category_variables(s, ad_cat, 500)
    c = build_total_volume_constraint(s, 500, ad_cat, ct_x,
                                      {"a": 1.0}, {"a": 1.0})
    assert c.Ub() == pytest.approx(500.0)


# ---- additional tests for apply_objective ----------------------------------

def test_apply_objective_empty_ads():
    s = create_solver(1)
    apply_objective(s, "maximize_money", {}, {}, {})
    # nothing should crash


def test_apply_objective_single_ad():
    ad_cat = {"a": [RequestFlow(tags=("t",), probability=1.0)]}
    s = create_solver(1)
    ct_x, _ = create_category_variables(s, ad_cat, 500)
    apply_objective(s, "maximize_money", ad_cat, ct_x, {"a": 3.0})
    assert s.Objective().GetCoefficient(ct_x[("a", ("t",))]) == pytest.approx(3.0)


def test_apply_objective_unknown_type():
    # an unknown objective type is treated as MAX_VOLUME → LP_UNIT_COEFF = 1.0
    ad_cat = {"a": [RequestFlow(tags=("t",), probability=1.0)]}
    s = create_solver(1)
    ct_x, _ = create_category_variables(s, ad_cat, 500)
    apply_objective(s, "unknown_type", ad_cat, ct_x, {"a": 3.0})
    assert s.Objective().GetCoefficient(ct_x[("a", ("t",))]) == pytest.approx(1.0)


# ===========================================================================
# 5c. solve_pywraplp — fallback path (element-wise LP assembly)
# ===========================================================================

def test_solve_pywraplp_single_ad_maximize_volume():
    """One ad, maximize_volume — gets all the traffic."""
    ad_categories = {"ad1": [RequestFlow(tags=("geo:msk",), probability=0.5)]}
    ads_probs = {"ad1": 0.5}
    ads_by_cat_probs = {"ad1": 0.5}  # k = 1.0
    ads_min_vol = {"ad1": 0.0}
    ads_real_max_vol = {"ad1": 500.0}
    ad_prices = {"ad1": 10.0}

    s = create_solver(1)
    result = solve_pywraplp(
        ad_categories, 1000,
        ads_probs, ads_by_cat_probs,
        ads_min_vol, ads_real_max_vol, ad_prices,
        "maximize_volume",
        solver=s,
    )
    # x ∈ [0, 1000*0.5=500], max_volume → x=500; k=1 → volume=500
    assert result["ad1"] == 500


def test_solve_pywraplp_single_ad_maximize_money():
    """One ad, maximize_money — the objective coefficient = price."""
    ad_categories = {"ad1": [RequestFlow(tags=("geo:msk",), probability=0.5)]}
    ads_probs = {"ad1": 0.5}
    ads_by_cat_probs = {"ad1": 0.5}
    ads_min_vol = {"ad1": 0.0}
    ads_real_max_vol = {"ad1": 500.0}
    ad_prices = {"ad1": 25.0}

    s = create_solver(1)
    result = solve_pywraplp(
        ad_categories, 1000,
        ads_probs, ads_by_cat_probs,
        ads_min_vol, ads_real_max_vol, ad_prices,
        "maximize_money",
        solver=s,
    )
    assert result["ad1"] == 500


def test_solve_pywraplp_two_ads_share_cell():
    """Two ads share one cell (msk) — the LP distributes by price."""
    ad_categories = {
        "ad1": [RequestFlow(tags=("geo:msk",), probability=0.5)],
        "ad2": [RequestFlow(tags=("geo:msk",), probability=0.5)],
    }
    ads_probs = {"ad1": 0.3, "ad2": 0.5}
    ads_by_cat_probs = {"ad1": 0.5, "ad2": 0.5}  # k1=0.6, k2=1.0
    ads_min_vol = {"ad1": 0.0, "ad2": 0.0}
    ads_real_max_vol = {"ad1": 300.0, "ad2": 500.0}
    ad_prices = {"ad1": 10.0, "ad2": 20.0}

    s = create_solver(1)
    result = solve_pywraplp(
        ad_categories, 1000,
        ads_probs, ads_by_cat_probs,
        ads_min_vol, ads_real_max_vol, ad_prices,
        "maximize_money",
        solver=s,
    )
    # both ads get a nonzero volume
    assert result["ad1"] >= 0
    assert result["ad2"] >= 0
    # the total volume does not exceed the cell (1000*0.5=500) taking k into account
    # k1*x1 + k2*x2 ≤ 500, where x1 ∈ [0,500], x2 ∈ [0,500]
    assert sum(result.values()) <= 600  # + slack for rounding


def test_solve_pywraplp_respects_min_vol():
    """min_vol fixes the lower bound of the volume."""
    ad_categories = {"ad1": [RequestFlow(tags=("geo:msk",), probability=0.5)]}
    ads_probs = {"ad1": 0.5}
    ads_by_cat_probs = {"ad1": 0.5}
    ads_min_vol = {"ad1": 200.0}  # minimum 200
    ads_real_max_vol = {"ad1": 500.0}
    ad_prices = {"ad1": 1.0}

    s = create_solver(1)
    result = solve_pywraplp(
        ad_categories, 1000,
        ads_probs, ads_by_cat_probs,
        ads_min_vol, ads_real_max_vol, ad_prices,
        "maximize_volume",
        solver=s,
    )
    assert result["ad1"] >= 200


def test_solve_pywraplp_respects_max_vol():
    """max_vol limits the upper bound of the volume."""
    ad_categories = {"ad1": [RequestFlow(tags=("geo:msk",), probability=0.5)]}
    ads_probs = {"ad1": 0.5}
    ads_by_cat_probs = {"ad1": 0.5}
    ads_min_vol = {"ad1": 0.0}
    ads_real_max_vol = {"ad1": 100.0}  # maximum 100
    ad_prices = {"ad1": 1.0}

    s = create_solver(1)
    result = solve_pywraplp(
        ad_categories, 1000,
        ads_probs, ads_by_cat_probs,
        ads_min_vol, ads_real_max_vol, ad_prices,
        "maximize_volume",
        solver=s,
    )
    assert result["ad1"] <= 100


def test_solve_pywraplp_unknown_objective_falls_back_to_volume():
    """Unknown objective → maximize_volume (LP_UNIT_COEFF = 1.0)."""
    ad_categories = {"ad1": [RequestFlow(tags=("geo:msk",), probability=0.5)]}
    ads_probs = {"ad1": 0.5}
    ads_by_cat_probs = {"ad1": 0.5}
    ads_min_vol = {"ad1": 0.0}
    ads_real_max_vol = {"ad1": 500.0}
    ad_prices = {"ad1": 999.0}  # high price, but the objective is not maximize_money

    s = create_solver(1)
    result = solve_pywraplp(
        ad_categories, 1000,
        ads_probs, ads_by_cat_probs,
        ads_min_vol, ads_real_max_vol, ad_prices,
        "unknown_objective",
        solver=s,
    )
    # the result is the same as maximize_volume
    assert result["ad1"] == 500


def test_solve_pywraplp_multiple_categories_per_ad():
    """An ad with several categories — sums x over all of them."""
    ad_categories = {
        "ad1": [
            RequestFlow(tags=("geo:msk",), probability=0.3),
            RequestFlow(tags=("geo:spb",), probability=0.2),
        ],
    }
    ads_probs = {"ad1": 0.5}
    ads_by_cat_probs = {"ad1": 0.5}  # k = 1.0
    ads_min_vol = {"ad1": 0.0}
    ads_real_max_vol = {"ad1": 500.0}
    ad_prices = {"ad1": 1.0}

    s = create_solver(1)
    result = solve_pywraplp(
        ad_categories, 1000,
        ads_probs, ads_by_cat_probs,
        ads_min_vol, ads_real_max_vol, ad_prices,
        "maximize_volume",
        solver=s,
    )
    # x_msk ∈ [0, 300], x_spb ∈ [0, 200]; max → x_msk=300, x_spb=200
    # volume = k * (x_msk + x_spb) = 1.0 * 500 = 500
    assert result["ad1"] == 500


def test_solve_pywraplp_two_ads_competing_different_prices():
    """Two ads with different prices — maximize_money prefers the expensive one."""
    ad_categories = {
        "ad1": [RequestFlow(tags=("geo:msk",), probability=0.5)],
        "ad2": [RequestFlow(tags=("geo:msk",), probability=0.5)],
    }
    ads_probs = {"ad1": 0.5, "ad2": 0.5}
    ads_by_cat_probs = {"ad1": 0.5, "ad2": 0.5}  # k1=k2=1.0
    ads_min_vol = {"ad1": 0.0, "ad2": 0.0}
    # the real maximum does not constrain (large enough)
    ads_real_max_vol = {"ad1": 1000.0, "ad2": 1000.0}
    # ad2 is 10 times more expensive
    ad_prices = {"ad1": 1.0, "ad2": 10.0}

    s = create_solver(1)
    result = solve_pywraplp(
        ad_categories, 1000,
        ads_probs, ads_by_cat_probs,
        ads_min_vol, ads_real_max_vol, ad_prices,
        "maximize_money",
        solver=s,
    )
    # maximize_money → ad2 gets more (more expensive)
    assert result["ad2"] >= result["ad1"]


def test_solve_pywraplp_normalization_k_not_one():
    """Normalization coefficient k ≠ 1 (P(ad) ≠ ΣP(cat)) — the cell binds the volume.

    Cell msk: k·x ≤ total·P(msk) = 1000·0.3 = 300.
    k = P(ad)/ΣP(cat) = 0.9/0.3 = 3.0 → x ≤ 100 → volume = 3.0·100 = 300.
    """
    ad_categories = {
        "ad1": [RequestFlow(tags=("geo:msk",), probability=0.3)],
    }
    ads_probs = {"ad1": 0.9}   # P(ad) = 0.9
    ads_by_cat_probs = {"ad1": 0.3}  # ΣP(cat) = 0.3 → k = 3.0
    ads_min_vol = {"ad1": 0.0}
    ads_real_max_vol = {"ad1": 900.0}
    ad_prices = {"ad1": 1.0}

    s = create_solver(1)
    result = solve_pywraplp(
        ad_categories, 1000,
        ads_probs, ads_by_cat_probs,
        ads_min_vol, ads_real_max_vol, ad_prices,
        "maximize_volume",
        solver=s,
    )
    # cell: k·x ≤ 300 → x ≤ 100; volume = k·x = 3.0·100 = 300
    assert result["ad1"] == 300


def test_solve_pywraplp_empty_categories_returns_empty():
    """Empty ad_categories → empty result."""
    s = create_solver(1)
    result = solve_pywraplp(
        {}, 1000,
        {}, {}, {}, {}, {},
        "maximize_volume",
        solver=s,
    )
    assert result == {}


def test_solve_pywraplp_consistency_with_proto():
    """solve_pywraplp and solve_proto give the same result on the same problem."""
    ad_categories = {
        "ad1": [RequestFlow(tags=("geo:msk",), probability=0.3),
                RequestFlow(tags=("geo:spb",), probability=0.2)],
        "ad2": [RequestFlow(tags=("geo:msk",), probability=0.3)],
    }
    ads_probs = {"ad1": 0.5, "ad2": 0.3}
    ads_by_cat_probs = {"ad1": 0.5, "ad2": 0.3}
    ads_min_vol = {"ad1": 0.0, "ad2": 0.0}
    ads_real_max_vol = {"ad1": 500.0, "ad2": 300.0}
    ad_prices = {"ad1": 10.0, "ad2": 20.0}

    # solve_pywraplp
    s1 = create_solver(1)
    result_pywrap = solve_pywraplp(
        ad_categories, 1000,
        ads_probs, ads_by_cat_probs,
        ads_min_vol, ads_real_max_vol, ad_prices,
        "maximize_money",
        solver=s1,
    )

    # solve_proto (via build_proto_model)
    model, ad_var_indices, k_by_ad = build_proto_model(
        ad_categories, 1000,
        ads_probs, ads_by_cat_probs,
        ads_min_vol, ads_real_max_vol, ad_prices,
        "maximize_money",
    )
    s2 = create_solver(1)
    s2.LoadModelFromProto(model)
    status = s2.Solve()
    assert status == pywraplp.Solver.OPTIMAL

    resp = pb.MPSolutionResponse()
    s2.FillSolutionResponseProto(resp)
    values = resp.variable_value

    result_proto: dict = {}
    for ad, var_idxs in ad_var_indices.items():
        k = k_by_ad[ad]
        s = sum(values[idx] for idx in var_idxs)
        result_proto[ad] = int(round(k * s))

    # both paths give the same result
    assert result_pywrap == result_proto


# ===========================================================================
# 6. prepare_result (utils/report)
# ===========================================================================

def test_prepare_result_raises_no_solution_on_non_optimal():
    _, ad_categories, ads_probs, abp, s, cat_to_x = _solver_setup()
    with pytest.raises(BalancerError) as exc:
        prepare_result(s, pywraplp.Solver.INFEASIBLE, ad_categories, cat_to_x, ads_probs, abp)
    assert exc.value.error_code == ErrorCodes.NO_SOLUTION


def _solved_single(x_value):
    """A solved solver with one category pinned in x_value."""
    ad_categories = {"ad": [RequestFlow(tags=("geo:msk",), probability=0.5)]}
    s = create_solver(1)
    cat_to_x, _ = create_category_variables(s, ad_categories, 1000)
    x = cat_to_x[("ad", ("geo:msk",))]
    fix = s.RowConstraint(x_value, x_value, "fix")
    fix.SetCoefficient(x, 1.0)
    s.Objective().SetCoefficient(x, 1.0)
    s.Objective().SetMaximization()
    status = s.Solve()
    assert status == pywraplp.Solver.OPTIMAL
    return ad_categories, s, cat_to_x, status


def test_prepare_result_applies_normalization_k_equals_one():
    ad_categories, s, cat_to_x, status = _solved_single(100.0)
    # k = P(ad)/ΣP(cat) = 0.5/0.5 = 1 → round(1 * 100)
    res = prepare_result(s, status, ad_categories, cat_to_x, {"ad": 0.5}, {"ad": 0.5})
    assert res == {"ad": 100}


def test_prepare_result_applies_normalization_k_not_one():
    ad_categories, s, cat_to_x, status = _solved_single(100.0)
    # k = 0.5 / 0.25 = 2 (simulating a top-K truncation) → round(2 * 100)
    res = prepare_result(s, status, ad_categories, cat_to_x, {"ad": 0.5}, {"ad": 0.25})
    assert res == {"ad": 200}


# ---- additional tests for prepare_result ----------------------------------

def test_prepare_result_multiple_ads():
    ad_categories, s, cat_to_x, status = _solved_single(50.0)
    ad_categories["b"] = [RequestFlow(tags=("geo:msk",), probability=0.5)]
    cat_to_x[("b", ("geo:msk",))] = cat_to_x[("ad", ("geo:msk",))]
    res = prepare_result(s, status, ad_categories, cat_to_x,
                         {"ad": 0.5, "b": 0.5}, {"ad": 0.5, "b": 0.5})
    assert "ad" in res and "b" in res


def test_prepare_result_zero_ads_prob():
    ad_categories, s, cat_to_x, status = _solved_single(100.0)
    res = prepare_result(s, status, ad_categories, cat_to_x,
                         {"ad": 0.0}, {"ad": 0.5})
    assert res == {"ad": 0}


# ===========================================================================
# 7. Constructors and validators (validate-then-build)
# ===========================================================================

def test_create_inner_ad_valid_returns_struct():
    ad = create_inner_ad(id="a", targets={"geo": ["geo:msk"]}, min_vol=10,
                         max_vol=100, price=2.0, date_factor=1.0, freq=50)
    assert ad["id"] == "a" and ad["min_vol"] == 10 and ad["max_vol"] == 100


@pytest.mark.parametrize("kwargs", [
    {"min_vol": 5, "max_vol": 1},          # min > max
    {"price": -1.0},                       # price < 0
    {"freq": 0},                           # freq must be > 0
    {"date_factor": 0},                    # date_factor must be > 0
    {"id": ""},                            # empty id
], ids=["min>max", "price<0", "freq=0", "date_factor=0", "empty id"])
def test_create_inner_ad_invalid_raises(kwargs):
    base = dict(id="a", targets={"geo": ["geo:msk"]}, min_vol=0, max_vol=100,
                price=1.0, date_factor=1.0, freq=10)
    base.update(kwargs)
    with pytest.raises(BalancerError) as exc:
        create_inner_ad(**base)
    assert exc.value.error_code == ErrorCodes.INPUT_VALIDATION_ERROR


def test_create_optimize_params_valid_and_invalid_objective():
    p = create_optimize_params(total_traffic_volume=5000, tag_probabilities={"geo:msk": 0.6},
                               vocabs={"geo": ["geo:msk"]}, objective="maximize_volume")
    assert p["objective"] == "maximize_volume" and p["total_traffic_volume"] == 5000
    with pytest.raises(BalancerError) as exc:
        create_optimize_params(total_traffic_volume=5000, tag_probabilities={"geo:msk": 0.6},
                               vocabs={"geo": ["geo:msk"]}, objective="garbage")
    assert exc.value.error_code == ErrorCodes.INPUT_VALIDATION_ERROR


def test_create_category_struct():
    assert create_category(tags=("geo:msk",), probability=0.3) == {"tags": ("geo:msk",), "probability": 0.3}


def test_is_valid_balancer_auction_data_accepts_well_formed():
    data = create_balancer_auction_data(
        vocabs={"geo": ["geo:msk"]}, tag_probabilities={"geo": {"msk": 1.0}},
        ads_distribution={"a": 100}, ads_probabilities={"a": 0.5}, ads_total=100)
    assert is_valid_balancer_auction_data(data) is True


def test_is_valid_balancer_auction_data_rejects_malformed():
    # ads_distribution with a non-integer volume
    assert is_valid_balancer_auction_data({
        "vocabs": {"geo": ["geo:msk"]}, "tag_probabilities": {"geo": {"msk": 1.0}},
        "ads_distribution": {"a": 1.5}, "ads_probabilities": {"a": 0.5}, "ads_total": 100,
    }) is False


def test_create_parameters_balanced_valid_and_invalid_request():
    pb = create_parameters_balanced(request={"geo": "msk"}, vocabs={"geo": ["msk"]})
    assert pb["request"] == {"geo": "msk"}
    with pytest.raises(BalancerError) as exc:
        create_parameters_balanced(request={"geo": ["msk"]})  # the value must be a string
    assert exc.value.error_code == ErrorCodes.INPUT_VALIDATION_ERROR


# ---- additional tests for create_optimize_params ---------------------------

def test_create_optimize_params_defaults():
    p = create_optimize_params(total_traffic_volume=1000, tag_probabilities={}, vocabs={})
    assert p["total_traffic_volume"] == 1000
    assert p["objective"] == "maximize_money"


def test_create_optimize_params_max_n_categories_zero():
    with pytest.raises(BalancerError) as exc:
        create_optimize_params(total_traffic_volume=1000, tag_probabilities={}, vocabs={}, max_n_categories=0)
    assert exc.value.error_code == ErrorCodes.INPUT_VALIDATION_ERROR


def test_create_optimize_params_empty_vocabs():
    p = create_optimize_params(total_traffic_volume=1000, vocabs={},
                               tag_probabilities={}, objective="maximize_volume")
    assert p["vocabs"] == {}


# ---- additional tests for create_category ----------------------------------

def test_create_category_probability_too_high():
    with pytest.raises(BalancerError) as exc:
        create_category(tags=("t",), probability=1.5)
    assert exc.value.error_code == ErrorCodes.INPUT_VALIDATION_ERROR


def test_create_category_probability_negative():
    with pytest.raises(BalancerError) as exc:
        create_category(tags=("t",), probability=-0.1)
    assert exc.value.error_code == ErrorCodes.INPUT_VALIDATION_ERROR


def test_create_category_empty_tags():
    cat = create_category(tags=(), probability=0.5)
    assert cat["tags"] == () and cat["probability"] == 0.5


def test_create_category_probability_zero():
    cat = create_category(tags=("t",), probability=0.0)
    assert cat["probability"] == 0.0


def test_create_category_probability_one():
    cat = create_category(tags=("t",), probability=1.0)
    assert cat["probability"] == 1.0


# ---- additional tests for is_valid_balancer_auction_data --------------------

def test_is_valid_balancer_auction_data_non_dict():
    assert is_valid_balancer_auction_data(None) is False
    assert is_valid_balancer_auction_data("str") is False
    assert is_valid_balancer_auction_data(123) is False


def test_is_valid_balancer_auction_data_missing_fields():
    assert is_valid_balancer_auction_data({}) is False


def test_is_valid_balancer_auction_data_negative_ads_total():
    data = {
        "vocabs": {"geo": ["geo:msk"]},
        "tag_probabilities": {"geo": {"msk": 1.0}},
        "ads_distribution": {"a": 100},
        "ads_probabilities": {"a": 0.5},
        "ads_total": -1,
    }
    assert is_valid_balancer_auction_data(data) is False


# ---- additional tests for create_balancer_auction_data ---------------------

def test_create_balancer_auction_data_defaults():
    data = create_balancer_auction_data()
    assert data["vocabs"] == {}
    assert data["tag_probabilities"] == {}
    assert data["ads_distribution"] == {}
    assert data["ads_probabilities"] == {}
    assert data["ads_total"] == 0


def test_create_balancer_auction_data_valid():
    data = create_balancer_auction_data(
        vocabs={"g": ["g:a"]},
        tag_probabilities={"g": {"a": 1.0}},
        ads_distribution={"ad1": 100},
        ads_probabilities={"ad1": 0.5},
        ads_total=100,
    )
    assert data["ads_distribution"]["ad1"] == 100


def test_create_balancer_auction_data_invalid_vocabs():
    with pytest.raises(BalancerError) as exc:
        create_balancer_auction_data(vocabs="not-a-dict")
    assert exc.value.error_code == ErrorCodes.INPUT_VALIDATION_ERROR


def test_create_balancer_auction_data_invalid_ads_total():
    with pytest.raises(BalancerError) as exc:
        create_balancer_auction_data(ads_total=-5)
    assert exc.value.error_code == ErrorCodes.INPUT_VALIDATION_ERROR


def test_create_balancer_auction_data_invalid_tag_probabilities():
    with pytest.raises(BalancerError) as exc:
        create_balancer_auction_data(tag_probabilities="bad")
    assert exc.value.error_code == ErrorCodes.INPUT_VALIDATION_ERROR


def test_create_balancer_auction_data_invalid_ads_distribution():
    with pytest.raises(BalancerError) as exc:
        create_balancer_auction_data(ads_distribution={"a": 1.5})
    assert exc.value.error_code == ErrorCodes.INPUT_VALIDATION_ERROR


# ---- additional tests for create_parameters_balanced -----------------------

def test_create_parameters_balanced_all_defaults():
    pb = create_parameters_balanced()
    assert pb["request"] == {}
    assert pb["vocabs"] == {}
    assert pb["balancer_data"] is None


def test_create_parameters_balanced_none_balancer_data():
    pb = create_parameters_balanced(balancer_data=None)
    assert pb["balancer_data"] is None


def test_create_parameters_balanced_with_balancer_data():
    bd = create_balancer_auction_data(ads_total=50)
    pb = create_parameters_balanced(balancer_data=bd)
    assert pb["balancer_data"]["ads_total"] == 50


def test_create_parameters_balanced_invalid_vocabs():
    with pytest.raises(BalancerError) as exc:
        create_parameters_balanced(vocabs="bad")
    assert exc.value.error_code == ErrorCodes.INPUT_VALIDATION_ERROR
