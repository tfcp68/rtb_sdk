"""Property-based (randomized) tests of the balancer.

Unlike the data-driven cases in cases/*.json (pointwise examples), these tests
run hundreds of random instances and check:

  * mathematical invariants of the balance_traffic LP solution
    (volume >= 0, <= volume, <= ad_frequency_limit.d, Σ <= total);
  * the closed form of the optimum in two structural cases
    (non-competing ads and a shared cell);
  * correctness of the top-K choose_top against full enumeration (including ties);
  * that the validator NEVER lets garbage through as a raw exception —
    only BalancerError(INPUT_VALIDATION_ERROR).

Seeds are fixed → the tests are deterministic and reproducible. This is a different
class of coverage than the JSON cases: it catches regressions broadly, not on a single input.
"""
import math
import random
from itertools import product

import pytest

from rtb_sdk.balancer.balancer import balance_traffic
from rtb_sdk.balancer.utils.categories import choose_top_categories_by_probability
from rtb_sdk.errors.balancer import BalancerError, ErrorCodes


# ---------------------------------------------------------------------------
# Random input generators
# ---------------------------------------------------------------------------

def _rand_vocabs_and_probs(rng, n_vocabs, ties=False):
    """Random dictionaries + tag probabilities in the inner (FullTag) format."""
    vocabs, probs = {}, {}
    tievals = [0.5, 0.25, 0.2]
    for vi in range(n_vocabs):
        vn = f"v{vi}"
        raw_tags = [f"t{ti}" for ti in range(rng.randint(1, 3))]
        full_tags = [f"{vn}:{t}" for t in raw_tags]
        if ties:
            pr = {ft: rng.choice(tievals) for ft in full_tags}
        else:
            raw = [rng.random() + 0.05 for _ in full_tags]
            s = sum(raw) + rng.random()  # leave mass for OTHER
            pr = {ft: round(r / s, 4) for ft, r in zip(full_tags, raw)}
        vocabs[vn] = full_tags
        probs.update(pr)
    return vocabs, probs


def _rand_ads(rng, vocabs, n_ads, min_vol=0):
    # New outer Ad: targets.value (raw tags), volume (=inner max_vol),
    # cpm (=price), ad_frequency_limit.value.d (=freq). min_vol in the outer Ad
    # no longer exists (inner is always 0) — the parameter is kept for call compatibility.
    # vocabs now contains full tags (FullTag: "vocab:raw"), so
    # when forming targets.value we extract the raw part from the full tags.
    ads = {}
    for ai in range(n_ads):
        targets_value = {}
        for vn, full_tags in vocabs.items():
            if rng.random() < 0.7:
                k = rng.randint(1, len(full_tags))
                sampled = rng.sample(full_tags, k)
                targets_value[vn] = [ft.split(':', 1)[1] for ft in sampled]
        ads[f"ad{ai}"] = {
            "id": f"ad{ai}",
            "targets": {"value": targets_value},
            "volume": rng.choice([100, 1000, 10000, 10 ** 9]),
            "cpm": round(rng.random() * 10, 2),
            "ad_frequency_limit": {"value": {"d": rng.choice([50, 500, 10 ** 9])}},
        }
    return ads


# ---------------------------------------------------------------------------
# 1. Invariants of the LP solution
# ---------------------------------------------------------------------------

def test_balance_traffic_invariants_hold_over_random_instances():
    """Any LP solution respects the basic constraints (min_vol=0 ⇒ always feasible)."""
    rng = random.Random(20240601)
    for _ in range(400):
        vocabs, probs = _rand_vocabs_and_probs(rng, rng.randint(1, 3))
        ads = _rand_ads(rng, vocabs, rng.randint(1, 4), min_vol=0)
        total = rng.choice([1000, 5000, 100000])
        params = {
            "total_traffic_volume": total, "tag_probabilities": probs,
            "vocabs": vocabs, "objective": rng.choice(["maximize_money", "maximize_volume"]),
            "max_n_categories": rng.choice([1, 3, 100]),
            "min_category_probability": 1e-9, "n_threads": 1,
        }
        # vocabs and probs are already in the inner (FullTag) format from _rand_vocabs_and_probs
        res = balance_traffic(ads, params)

        assert set(res.keys()) == set(ads.keys()), "The result should cover exactly the same ads"
        for ad_id, vol in res.items():
            assert vol >= 0, f"{ad_id}: negative {vol}"
            vmax = ads[ad_id]["volume"]
            assert vol <= vmax + 1, f"{ad_id}: {vol} > volume {vmax}"
            freq = ads[ad_id]["ad_frequency_limit"]["value"]["d"]
            assert vol <= freq + 1, f"{ad_id}: {vol} > freq {freq}"
        # the total volume does not exceed the available traffic (+ slack for rounding)
        assert sum(res.values()) <= total + len(ads), f"Σ {sum(res.values())} > total {total}"


# ---------------------------------------------------------------------------
# 2. Closed form of the optimum: non-competing ads
# ---------------------------------------------------------------------------

def test_non_competing_ads_each_reach_total_times_p():
    """Ads on non-overlapping tags (partial coverage) under maximize_volume
    and with limits removed get exactly total*P(tag)."""
    rng = random.Random(7)
    for _ in range(800):
        n = rng.randint(1, 4)
        raw_tags = [f"t{i}" for i in range(n)] + ["extra"]  # extra ⇒ no ad covers the whole dictionary
        full_tags = [f"geo:{t}" for t in raw_tags]
        raw = [rng.random() + 0.1 for _ in full_tags]
        s = sum(raw) + rng.random()
        probs = {ft: round(r / s, 5) for ft, r in zip(full_tags, raw)}
        total = rng.choice([1000, 5000, 100000])
        ads = {f"ad{i}": {"id": f"ad{i}", "targets": {"value": {"geo": [f"t{i}"]}},
                          "volume": 10 ** 9, "cpm": 1.0,
                          "ad_frequency_limit": {"value": {"d": 10 ** 9}}}
               for i in range(n)}
        params = {"total_traffic_volume": total, "tag_probabilities": probs,
                  "vocabs": {"geo": full_tags}, "objective": "maximize_volume",
                  "max_n_categories": 100, "min_category_probability": 1e-9, "n_threads": 1}
        res = balance_traffic(ads, params)
        for i in range(n):
            assert abs(res[f"ad{i}"] - total * probs[f"geo:t{i}"]) <= 2


# ---------------------------------------------------------------------------
# 3. Closed form: a shared cell binds the total volume
# ---------------------------------------------------------------------------

def test_shared_cell_sum_binds_to_total_times_p():
    """K ads on one tag under maximize_volume with limits removed:
    Σ volumes == total*P(tag) (the cell ceiling is active)."""
    rng = random.Random(99)
    for _ in range(800):
        k = rng.randint(2, 5)
        p_msk = round(rng.uniform(0.1, 0.85), 4)
        total = rng.choice([1000, 5000, 100000])
        ads = {f"ad{i}": {"id": f"ad{i}", "targets": {"value": {"geo": ["msk"]}},
                          "volume": 10 ** 9, "cpm": 1.0,
                          "ad_frequency_limit": {"value": {"d": 10 ** 9}}}
               for i in range(k)}
        params = {"total_traffic_volume": total,
                  "tag_probabilities": {"geo:msk": p_msk, "geo:spb": round(1 - p_msk - 0.01, 4)},
                  "vocabs": {"geo": ["geo:msk", "geo:spb"]}, "objective": "maximize_volume",
                  "max_n_categories": 100, "min_category_probability": 1e-9, "n_threads": 1}
        res = balance_traffic(ads, params)
        assert abs(sum(res.values()) - total * p_msk) <= 2


# ---------------------------------------------------------------------------
# 4. Correctness of top-K against full enumeration (including ties)
# ---------------------------------------------------------------------------

def test_choose_top_matches_bruteforce_ranking_with_ties():
    """Properties of top-K on random inputs (including mass ties):
    sorted in descending order, P=∏P(tags), no duplicates, and NO excluded
    category beats a returned one in probability."""
    rng = random.Random(123)
    TOL = 1e-9
    for _ in range(2000):
        n_vocabs = rng.randint(1, 4)
        ties = rng.random() < 0.5
        vt, flat = {}, {}
        for vi in range(n_vocabs):
            tags = [f"v{vi}:t{ti}" for ti in range(rng.randint(1, 4))]
            tievals = [0.5, 0.25, 0.2]
            pr = {t: (rng.choice(tievals) if ties else round(rng.uniform(0.01, 0.99), 3)) for t in tags}
            vt[f"v{vi}"] = tags
            flat.update(pr)
        max_n = rng.choice([1, 2, 3, 5, 1000])
        min_p = rng.choice([1e-12, 0.01, 0.05, 0.1, 0.3])
        res = choose_top_categories_by_probability(
            {"ad": vt}, {k: list(v) for k, v in vt.items()}, flat,
            max_n_categories=max_n, min_category_probability=min_p,
        )["ad"]
        rp = [c["probability"] for c in res]

        # sorted in descending order
        assert rp == sorted(rp, reverse=True)
        # all >= threshold
        assert all(p >= min_p - TOL for p in rp)
        # P = product of the tag probabilities
        for c in res:
            prod = 1.0
            for t in c["tags"]:
                prod *= flat[t]
            assert math.isclose(prod, c["probability"], rel_tol=1e-9, abs_tol=1e-12)
        # no duplicates
        tup = [tuple(c["tags"]) for c in res]
        assert len(set(tup)) == len(tup)
        # true top-K: no excluded category is better than the worst returned one
        sv = sorted(vt.items(), key=lambda kv: len(kv[1]), reverse=True)
        allp = sorted(
            (math.prod(flat[t] for t in combo) for combo in product(*[t for _, t in sv])
             if math.prod(flat[t] for t in combo) >= min_p),
            reverse=True,
        )
        k = len(rp)
        if k > 0 and len(allp) > k:
            assert allp[k] <= min(rp) + TOL


# ---------------------------------------------------------------------------
# 5. The validator does not let garbage through as a raw exception
# ---------------------------------------------------------------------------

def _valid_base():
    ads = {"a": {"id": "a", "targets": {"value": {"geo": ["msk"]}},
                 "volume": 1000, "cpm": 1.0,
                 "ad_frequency_limit": {"value": {"d": 100}}}}
    params = {"total_traffic_volume": 5000, "tag_probabilities": {"geo:msk": 0.6, "geo:spb": 0.4},
              "vocabs": {"geo": ["geo:msk", "geo:spb"]}, "objective": "maximize_money",
              "max_n_categories": 100, "min_category_probability": 1e-6, "n_threads": 1}
    return ads, params


# (mutator, human-readable name) — each mutation makes the input certainly INVALID
_MUTATIONS = [
    (lambda a, p: p.__setitem__("total_traffic_volume", -1),           "total=-1"),
    (lambda a, p: p.__setitem__("total_traffic_volume", 5.5),          "total=float"),
    (lambda a, p: p.__setitem__("max_n_categories", 0),                "max_n=0"),
    (lambda a, p: p.__setitem__("n_threads", 0),                       "n_threads=0"),
    (lambda a, p: p.__setitem__("vocabs", ["geo"]),                    "vocabs=list"),
    # --- mutations of the fields of the new outer Ad (what validate_ad rejects) ---
    (lambda a, p: a["a"].__setitem__("volume", -1),                    "volume<0"),
    (lambda a, p: a["a"].__setitem__("volume", 1.5),                   "volume=float"),
    (lambda a, p: a["a"].pop("volume"),                                "no volume"),
    (lambda a, p: a["a"].__setitem__("cpm", -1.0),                     "cpm<0"),
    (lambda a, p: a["a"].pop("cpm"),                                   "no cpm"),
    (lambda a, p: a["a"].__setitem__("targets", {"value": ["geo"]}),   "targets.value=list"),
    (lambda a, p: a["a"].__setitem__("id", ""),                        "empty id"),
]


@pytest.mark.parametrize("mutate, name", _MUTATIONS, ids=[m[1] for m in _MUTATIONS])
def test_invalid_input_always_raises_balancer_error(mutate, name):
    """Any known-invalid mutation → BalancerError(INPUT_VALIDATION_ERROR),
    rather than a raw ValueError/KeyError/TypeError."""
    ads, params = _valid_base()
    mutate(ads, params)
    with pytest.raises(BalancerError) as exc:
        balance_traffic(ads, params)
    assert exc.value.error_code == ErrorCodes.INPUT_VALIDATION_ERROR
