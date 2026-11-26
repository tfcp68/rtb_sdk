"""
Balancer-specific test case infrastructure.

Analogue of tests/_helpers.py, but for the balancer module:
  - uses BalancerError instead of AuctionError
  - looks for cases in tests/balancer/cases/
  - supports an extended check_mode for complex output types
"""

import json
import math
import pytest
from pathlib import Path
from typing import Any, Callable, TypedDict, cast

from rtb_sdk.errors.balancer import BalancerError

BALANCER_TESTS_DIR = Path(__file__).parent
BALANCER_CASES_DIR = BALANCER_TESTS_DIR / "cases"

_BALANCER_ERROR_CODE_MAP: dict[str, int] = {
    "COMPUTATION_ERROR":      1001,
    "INPUT_VALIDATION_ERROR": 1002,
    "NO_SOLUTION":            1003,
}


class _CaseRequired(TypedDict):
    input:       dict
    output:      Any
    error:       str | None
    description: str


class BalancerCase(_CaseRequired, total=False):
    check_mode: str | None


# ---------------------------------------------------------------------------
# Loading and expanding fixtures
# ---------------------------------------------------------------------------

def _load_file(fpath: Path) -> Any:
    if fpath.suffix.lower() == ".json":
        with open(fpath, encoding="utf-8") as fh:
            return _resolve(json.load(fh))
    return None


def _resolve(obj: Any) -> Any:
    """Recursively expands "file://..." links relative to tests/balancer/."""
    if isinstance(obj, str) and obj.startswith("file://"):
        rel = obj[len("file://"):]
        return _load_file(BALANCER_TESTS_DIR / rel)
    if isinstance(obj, dict):
        return {k: _resolve(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve(item) for item in obj]
    return obj


def cases(func_name: str, unpacker: Callable | None = None) -> list[BalancerCase]:
    """Loads and returns the list of cases for the given function."""
    fpath = BALANCER_CASES_DIR / f"{func_name}.json"
    with open(fpath, encoding="utf-8") as fh:
        raw = json.load(fh)
    result = [cast(BalancerCase, _resolve(c)) for c in raw]
    if unpacker is not None:
        result = [cast(BalancerCase, unpacker(c)) for c in result]
    return result


def ids(cases_list: list[BalancerCase]) -> list[str]:
    return [c.get("description", f"case_{i}") for i, c in enumerate(cases_list)]


# ---------------------------------------------------------------------------
# Result checking
# ---------------------------------------------------------------------------

def _check_result(result: Any, case: BalancerCase) -> None:  # noqa: C901 (complexity allowed for dispatcher)
    check_mode = case.get("check_mode")
    output     = case.get("output")

    # --- Type-only (non-deterministic functions) ---
    if check_mode == "output_type":
        assert result is not None
        assert isinstance(result, dict)
        return

    # --- Sum of values ≤ threshold ---
    if check_mode == "total_lte":
        assert isinstance(result, dict)
        assert sum(result.values()) <= output
        return

    # --- Sum of values == exact number ---
    if check_mode == "sum_eq":
        assert isinstance(result, dict)
        assert sum(result.values()) == output
        return

    # --- Result keys == the set from output ---
    if check_mode == "keys_present":
        assert isinstance(result, dict)
        assert set(result.keys()) == set(output)
        return

    # --- result[greater] > result[lesser] ---
    if check_mode == "order_gt":
        assert result[output["greater"]] > result[output["lesser"]]
        return

    # --- Values in result are ordered by descending value according to the key list ---
    if check_mode == "ordered_non_negative":
        prev = None
        for ad_id in output:
            val = result[ad_id]
            assert val >= 0, f"{ad_id}: negative {val}"
            if prev is not None:
                assert prev >= val, f"Order’s broken: prev={prev} < val={val} for {ad_id}"
            prev = val
        return

    # --- result[key] == value ---
    if check_mode == "key_value":
        assert result[output["key"]] == output["value"]
        return

    # --- result[key] <= max ---
    if check_mode == "key_lte":
        assert result[output["key"]] <= output["max"]
        return

    # --- result[key] >= min ---
    if check_mode == "key_gte":
        assert result[output["key"]] >= output["min"]
        return

    # --- AddCampaignResult: volumes of the old campaigns did not change ---
    if check_mode == "report_old_preserved":
        for ad_id, expected_vol in output.items():
            actual = result["report"][ad_id]
            assert actual == expected_vol, (
                f"The old campaign '{ad_id}' changed: expected {expected_vol}, received {actual}"
            )
        return

    # --- AddCampaignResult: new_ads_volumes contains only new keys ---
    if check_mode == "new_ads_volumes_keys":
        assert set(result["new_ads_volumes"].keys()) == set(output)
        return

    # --- report contains all expected keys ---
    if check_mode == "report_keys":
        assert set(result["report"].keys()) == set(output)
        return

    # --- BalancingBySelloutResult: report is compared exactly, sellout_percent approximately ---
    # output = {"report": {ad_id: vol}, "sellout_percent": float}; any field is optional.
    # The percent tolerance covers the binary search discretization (eps) and the min_vol rounding.
    if check_mode == "sellout_eq":
        assert isinstance(result, dict)
        if "report" in output:
            assert result["report"] == output["report"]
        if "sellout_percent" in output:
            assert result["sellout_percent"] == pytest.approx(output["sellout_percent"], abs=0.2)
        return

    # --- report: sum of values ≤ threshold ---
    if check_mode == "report_total_lte":
        assert sum(result["report"].values()) <= output
        return

    # --- RebalanceResult: delta[ad] == new_report[ad] - old_report[ad] ---
    if check_mode == "delta_consistency":
        old_report = output  # output = the old report (dict[AdId, int])
        for ad_id, new_vol in result["report"].items():
            old_vol      = old_report.get(ad_id, 0)
            expected_delta = new_vol - old_vol
            actual_delta   = result["volume_delta"][ad_id]
            assert actual_delta == expected_delta, (
                f"Delta for '{ad_id}': expected {expected_delta}, received {actual_delta}"
            )
        return

    # --- BalancerAuctionData: result[field] == value ---
    if check_mode == "field_eq":
        assert result[output["field"]] == output["value"]
        return

    # --- BalancerAuctionData: compare a nested field ---
    if check_mode == "field_sub_eq":
        assert result[output["field"]][output["key"]] == output["value"]
        return

    # --- result[field][key] >= min ---
    if check_mode == "field_sub_gte":
        assert result[output["field"]][output["key"]] >= output["min"]
        return

    # --- choose_top_categories: exact number of categories per ad ---
    if check_mode == "category_counts":
        assert isinstance(result, dict)
        for ad_id, expected_count in output.items():
            assert ad_id in result, f"Ad '{ad_id}' absent"
            actual = len(result[ad_id])
            assert actual == expected_count, (
                f"Ad '{ad_id}': expected {expected_count} category, received {actual}"
            )
        return

    # --- choose_top_categories: number of categories <= maximum ---
    if check_mode == "categories_max_count":
        assert isinstance(result, dict)
        for ad_id, max_count in output.items():
            if ad_id in result:
                actual = len(result[ad_id])
                assert actual <= max_count, (
                    f"Ad '{ad_id}': {actual} category > max {max_count}"
                )
        return

    # --- choose_top_categories: categories sorted by descending probability ---
    if check_mode == "categories_sorted":
        assert isinstance(result, dict)
        for ad_id, cats in result.items():
            probs = [c["probability"] for c in cats]
            assert probs == sorted(probs, reverse=True), (
                f"Ad '{ad_id}': Categories are not ordered by decreasing probability: {probs}"
            )
        return

    # --- choose_top_categories: all probabilities ≥ output (float) ---
    if check_mode == "categories_min_prob":
        assert isinstance(result, dict)
        threshold = float(output)
        for ad_id, cats in result.items():
            for cat in cats:
                p = cat["probability"]
                assert p >= threshold - 1e-12, (
                    f"Ad '{ad_id}': probability {p} < threshold {threshold}"
                )
        return

    # --- choose_top_categories: probability of the first category == output[ad_id] ---
    if check_mode == "first_cat_prob":
        assert isinstance(result, dict)
        for ad_id, expected_prob in output.items():
            cats = result[ad_id]
            assert len(cats) > 0, f"Ad '{ad_id}': blank-list"
            actual_p = cats[0]["probability"]
            assert actual_p == pytest.approx(expected_prob, abs=1e-9), (
                f"Ad '{ad_id}': P={actual_p}, expected {expected_prob}"
            )
        return

    # --- choose_top_categories: exact brute-force check of the top ---
    # Enumerates the full Cartesian product of each ad's tags,
    # computes P = ∏ P(tag), sorts in descending order, applies max_n/min_p
    # and compares element by element with the function's result. Proves that the heap traversal
    # really returns the true top-K, and not just a sorted prefix.
    if check_mode == "brute_force_topk":
        from itertools import product

        assert isinstance(result, dict)
        inp = case["input"]
        ads_vocabs_tags    = inp["ads_vocabs_tags"]
        tag_probabilities  = inp["tag_probabilities"]
        max_n              = inp.get("max_n_categories", 100)
        min_p              = inp.get("min_category_probability", 1e-18)

        for ad_id, vocabs_tags in ads_vocabs_tags.items():
            # Sort the dictionaries by descending length, as the function does
            # (see _sort_ads_vocabs_tags_by_probability) — this gives
            # the same order of tag tuples as in Category.tags.
            sorted_vocabs = sorted(
                vocabs_tags.items(), key=lambda item: len(item[1]), reverse=True
            )
            vocab_names = [v for v, _ in sorted_vocabs]
            tag_lists   = [tags for _, tags in sorted_vocabs]

            # Full enumeration of the Cartesian product
            all_cats = []
            for combo in product(*tag_lists):
                p = 1.0
                for tag in combo:
                    p *= tag_probabilities.get(tag, 0.0)
                if p >= min_p:
                    all_cats.append((combo, p))

            # Top-K by descending P (a stable sort by P with a tie-break
            # on the tuple makes the order deterministic)
            all_cats.sort(key=lambda x: (-x[1], x[0]))
            expected = all_cats[:max_n]

            actual = result.get(ad_id, [])
            assert len(actual) == len(expected), (
                f"Ad '{ad_id}': brute force expectation {len(expected)} category, "
                f"function {len(actual)}"
            )

            for i, ((exp_tags, exp_p), act_cat) in enumerate(zip(expected, actual)):
                assert tuple(act_cat["tags"]) == exp_tags, (
                    f"Ad '{ad_id}' category[{i}]: tagging {tuple(act_cat['tags'])} "
                    f"They do not coincide with the expected {exp_tags}"
                )
                # math.exp(-∑logP) vs ∏P differ by ~1e-15 because of the summation order
                assert math.isclose(act_cat["probability"], exp_p, rel_tol=1e-9, abs_tol=1e-12), (
                    f"Ad '{ad_id}' category[{i}] {exp_tags}: "
                    f"P={act_cat['probability']}, expected {exp_p}"
                )
        return

    # --- Standard checks ---
    if output is None:
        assert result is None
    elif isinstance(output, float):
        assert result == pytest.approx(output, abs=1e-9)
    else:
        assert result == output


# ---------------------------------------------------------------------------
# Running a case
# ---------------------------------------------------------------------------

def run(func: Callable, case: BalancerCase) -> None:
    """Runs the function with the case data and checks the result or the expected error."""
    if case.get("error"):
        error_str = case["error"]
        assert isinstance(error_str, str)
        expected_code: int | None = None
        for name, code in _BALANCER_ERROR_CODE_MAP.items():
            if name in error_str:
                expected_code = code
                break
        if expected_code is None:
            raise ValueError(f"Unknown error code in the line: {error_str!r}")
        with pytest.raises(BalancerError) as exc_info:
            func(**case["input"])
        assert exc_info.value.error_code == expected_code
    else:
        result = func(**case["input"])
        _check_result(result, case)
