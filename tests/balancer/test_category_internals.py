"""Edge cases and complex unit tests that cannot be expressed in JSON cases.

Everything else is in tests/balancer/cases/,
run by the parameterized test_it from test_balancer.py.

Here:
  - _sort_ads_vocabs_tags_by_probability   — checking the sort order
  - _build_ad_log_arrays                   — math.log and _LOG_ZERO
"""
import math
import pytest

from rtb_sdk.balancer.utils.categories import (
    _sort_ads_vocabs_tags_by_probability,
    _build_ad_log_arrays,
)


# ===========================================================================
# _sort_ads_vocabs_tags_by_probability
# ===========================================================================

def test_sort_ads_vocabs_tags_by_probability_orders_vocabs_by_desc_length():
    ads_vt = {
        "ad1": {
            "geo": ["geo:msk", "geo:spb", "geo:ekb"],
            "age": ["age:y", "age:o"],
        }
    }
    tag_probs = {"geo:msk": 0.3, "geo:spb": 0.2, "geo:ekb": 0.5,
                 "age:y": 0.6, "age:o": 0.4}
    result = _sort_ads_vocabs_tags_by_probability(ads_vt, tag_probs)
    ad1_vocabs = result["ad1"]
    vocab_names = list(ad1_vocabs.keys())
    # geo has 3 tags, age has 2 → geo comes first
    assert vocab_names == ["geo", "age"]


def test_sort_ads_vocabs_tags_by_probability_orders_tags_by_desc_prob():
    ads_vt = {
        "ad1": {"geo": ["geo:spb", "geo:msk", "geo:ekb"]},
    }
    tag_probs = {"geo:msk": 0.3, "geo:spb": 0.2, "geo:ekb": 0.5}
    result = _sort_ads_vocabs_tags_by_probability(ads_vt, tag_probs)
    tags = result["ad1"]["geo"]
    # ekb(0.5) > msk(0.3) > spb(0.2)
    probs = [p for _, p in tags]
    assert probs == sorted(probs, reverse=True)
    assert [t for t, _ in tags] == ["geo:ekb", "geo:msk", "geo:spb"]


def test_sort_ads_vocabs_tags_by_probability_multiple_ads():
    ads_vt = {
        "ad1": {"geo": ["geo:a", "geo:b"]},
        "ad2": {"age": ["age:x"]},
    }
    tag_probs = {"geo:a": 0.7, "geo:b": 0.3, "age:x": 1.0}
    result = _sort_ads_vocabs_tags_by_probability(ads_vt, tag_probs)
    assert set(result.keys()) == {"ad1", "ad2"}


def test_sort_ads_vocabs_tags_by_probability_empty_ads():
    result = _sort_ads_vocabs_tags_by_probability({}, {"geo:msk": 0.5})
    assert result == {}


def test_sort_ads_vocabs_tags_by_probability_single_tag():
    ads_vt = {"ad1": {"geo": ["geo:msk"]}}
    result = _sort_ads_vocabs_tags_by_probability(ads_vt, {"geo:msk": 0.7})
    assert result["ad1"]["geo"] == [("geo:msk", 0.7)]


def test_sort_ads_vocabs_tags_by_probability_missing_tag_defaults_to_zero():
    # the tag is missing from tag_probabilities → probability 0.0
    ads_vt = {"ad1": {"geo": ["geo:msk", "geo:spb"]}}
    result = _sort_ads_vocabs_tags_by_probability(ads_vt, {"geo:msk": 0.6})
    tags = result["ad1"]["geo"]
    # spb (0.0) must come after msk (0.6)
    assert tags[0] == ("geo:msk", 0.6)
    assert tags[1] == ("geo:spb", 0.0)


def test_sort_ads_vocabs_tags_by_probability_equal_probs_stable_order():
    # equal probabilities — the order is stable (sorted preserves the original order)
    ads_vt = {"ad1": {"geo": ["geo:a", "geo:b", "geo:c"]}}
    probs = {"geo:a": 0.5, "geo:b": 0.5, "geo:c": 0.5}
    result = _sort_ads_vocabs_tags_by_probability(ads_vt, probs)
    tags = [t for t, _ in result["ad1"]["geo"]]
    assert tags == ["geo:a", "geo:b", "geo:c"]  # original order preserved


def test_sort_ads_vocabs_tags_by_probability_vocab_order_by_tag_count_desc():
    # the dictionary with more tags comes first
    ads_vt = {
        "ad1": {
            "short": ["short:x"],
            "long": ["long:a", "long:b", "long:c"],
        }
    }
    probs = {"short:x": 0.9, "long:a": 0.1, "long:b": 0.2, "long:c": 0.3}
    result = _sort_ads_vocabs_tags_by_probability(ads_vt, probs)
    vocab_names = list(result["ad1"].keys())
    assert vocab_names == ["long", "short"]  # long(3 tags) > short(1 tag)


def test_sort_ads_vocabs_tags_by_probability_multiple_ads_independent():
    # the sort order of each ad is independent
    ads_vt = {
        "ad1": {"geo": ["geo:a", "geo:b"]},
        "ad2": {"geo": ["geo:b", "geo:a"]},
    }
    probs = {"geo:a": 0.8, "geo:b": 0.2}
    result = _sort_ads_vocabs_tags_by_probability(ads_vt, probs)
    # both ads must have the same order: a(0.8) > b(0.2)
    assert result["ad1"]["geo"][0] == ("geo:a", 0.8)
    assert result["ad2"]["geo"][0] == ("geo:a", 0.8)


def test_sort_ads_vocabs_tags_by_probability_preserves_all_tags():
    # all tags must be present in the result, even with zero probability
    ads_vt = {"ad1": {"geo": ["geo:x", "geo:y", "geo:z"]}}
    probs = {"geo:x": 0.1}
    result = _sort_ads_vocabs_tags_by_probability(ads_vt, probs)
    tags = {t for t, _ in result["ad1"]["geo"]}
    assert tags == {"geo:x", "geo:y", "geo:z"}

# ===========================================================================
# _build_ad_log_arrays
# ===========================================================================

def test_build_ad_log_arrays_returns_vtags_and_vlogp():
    vocabs_tags = {
        "geo": [("geo:msk", 0.3), ("geo:spb", 0.2)],
    }
    vtags, vlogp = _build_ad_log_arrays(vocabs_tags)
    assert vtags == [["geo:msk", "geo:spb"]]
    assert len(vlogp) == 1
    assert vlogp[0][0] == pytest.approx(math.log(0.3))


def test_build_ad_log_arrays_zero_prob_uses_log_zero():
    vocabs_tags = {
        "geo": [("geo:msk", 0.0)],
    }
    _, vlogp = _build_ad_log_arrays(vocabs_tags)
    assert vlogp[0][0] == -1e18  # _LOG_ZERO


def test_build_ad_log_arrays_empty_vocabs():
    vtags, vlogp = _build_ad_log_arrays({})
    assert vtags == []
    assert vlogp == []


def test_build_ad_log_arrays_single_tag_single_vocab():
    vocabs_tags = {"geo": [("geo:msk", 0.5)]}
    vtags, vlogp = _build_ad_log_arrays(vocabs_tags)
    assert vtags == [["geo:msk"]]
    assert len(vlogp) == 1
    assert vlogp[0][0] == pytest.approx(math.log(0.5))


def test_build_ad_log_arrays_multiple_vocabs_alignment():
    # vtags[i] and vlogp[i] must have the same length for each dictionary
    vocabs_tags = {
        "geo": [("geo:a", 0.3), ("geo:b", 0.7)],
        "age": [("age:y", 0.6)],
    }
    vtags, vlogp = _build_ad_log_arrays(vocabs_tags)
    assert len(vtags) == 2
    assert len(vlogp) == 2
    assert len(vtags[0]) == len(vlogp[0]) == 2
    assert len(vtags[1]) == len(vlogp[1]) == 1


def test_build_ad_log_arrays_log_values_correct():
    vocabs_tags = {"geo": [("geo:a", 0.1), ("geo:b", 0.9)]}
    _, vlogp = _build_ad_log_arrays(vocabs_tags)
    assert vlogp[0][0] == pytest.approx(math.log(0.1))
    assert vlogp[0][1] == pytest.approx(math.log(0.9))


def test_build_ad_log_arrays_probability_one_gives_log_zero():
    vocabs_tags = {"geo": [("geo:msk", 1.0)]}
    _, vlogp = _build_ad_log_arrays(vocabs_tags)
    assert vlogp[0][0] == pytest.approx(0.0)  # log(1.0) = 0.0


def test_build_ad_log_arrays_small_probability():
    vocabs_tags = {"geo": [("geo:rare", 1e-10)]}
    _, vlogp = _build_ad_log_arrays(vocabs_tags)
    assert vlogp[0][0] == pytest.approx(math.log(1e-10))


def test_build_ad_log_arrays_preserves_tag_order():
    # the order of vtags must exactly match the order of the input tags
    vocabs_tags = {
        "geo": [("geo:z", 0.1), ("geo:a", 0.9), ("geo:m", 0.5)],
    }
    vtags, _ = _build_ad_log_arrays(vocabs_tags)
    assert vtags[0] == ["geo:z", "geo:a", "geo:m"]



