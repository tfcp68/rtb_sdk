"""
Registry of the simulation filter functions under test.

FUNCTIONS: {func_name: (func, unpacker | None)}
  - func     — the function under test
  - unpacker — takes a raw case (dict) and returns a case with already
               assembled objects; None for functions without complex types.
"""

from datetime import datetime

from rtb_sdk.auction.simulation.filters.match_filter import (
    filter_by_precise_match,
    filter_by_fuzzy_match,
    _calc_ad_distance,
)
from rtb_sdk.auction.simulation.filters.fuzzy_targeting_filter import (
    filter_by_fuzzy_targeting_frequency,
    filter_by_fuzzy_targeting_percent_frequency,
)
from rtb_sdk.helpers import (
    create_request,
    create_request_tags,
    load_ad_raw,
    create_ads_dict,
)


# ── low-level builders ────────────────────────────────────────────────

def _build_request(data: dict):
    """Builds a Request from the raw dict of a test case."""
    tags_raw = data.get("tags", {})
    tags = create_request_tags(tags_raw)
    date_raw = data.get("date", "0001-01-01T00:00:00")
    date = datetime.fromisoformat(date_raw) if isinstance(date_raw, str) else date_raw
    return create_request(
        id=data.get("id", "req"),
        user_id=data.get("user_id", "user"),
        date=date,
        tags=tags,
    )


def _build_ads_dict(data: dict):
    """Builds an AdsDict from {ad_id: raw_ad_dict}."""
    return create_ads_dict({ad_id: load_ad_raw(ad_data) for ad_id, ad_data in data.items()})


# ── case unpackers ─────────────────────────────────────────────────────

def _unpack_match_filter(case: dict) -> dict:
    """filter_by_precise_match / filter_by_fuzzy_match: request → Request, ads/output → AdsDict."""
    case["input"]["request"] = _build_request(case["input"]["request"])
    case["input"]["ads"] = _build_ads_dict(case["input"]["ads"])
    if case.get("output") is not None:
        case["output"] = _build_ads_dict(case["output"])
    return case


def _unpack_fuzzy_targeting_filter(case: dict) -> dict:
    """filter_by_fuzzy_targeting_*: ads/output → AdsDict; ad_total_counts stays a plain dict."""
    case["input"]["ads"] = _build_ads_dict(case["input"]["ads"])
    if case.get("output") is not None:
        case["output"] = _build_ads_dict(case["output"])
    return case


def _unpack_calc_ad_distance(case: dict) -> dict:
    """_calc_ad_distance: ad → Ad; request_tag_sets {vocab: list} → {vocab: set}; strict_vocabs list → set."""
    case["input"]["ad"] = load_ad_raw(case["input"]["ad"])
    rs = case["input"].get("request_tag_sets", {})
    case["input"]["request_tag_sets"] = {vocab: set(tags) for vocab, tags in rs.items()}
    sv = case["input"].get("strict_vocabs")
    if sv is not None:
        case["input"]["strict_vocabs"] = set(sv)
    return case


# ── mapping function → (function, unpacker) ───────────────────────────────

FUNCTIONS: dict[str, tuple] = {
    "filter_by_precise_match":               (filter_by_precise_match,               _unpack_match_filter),
    "filter_by_fuzzy_match":                 (filter_by_fuzzy_match,                 _unpack_match_filter),
    "filter_by_fuzzy_targeting_frequency":         (filter_by_fuzzy_targeting_frequency,         _unpack_fuzzy_targeting_filter),
    "filter_by_fuzzy_targeting_percent_frequency": (filter_by_fuzzy_targeting_percent_frequency, _unpack_fuzzy_targeting_filter),
    "_calc_ad_distance":                     (_calc_ad_distance,                     _unpack_calc_ad_distance),
}
