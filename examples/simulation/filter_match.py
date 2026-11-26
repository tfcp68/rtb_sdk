"""
Example of applying the tag-matching filters.

Demonstrates two modes:
  - filter_by_precise_match: exact match — all vocabs of the ad
                             must intersect with the request tags
  - filter_by_fuzzy_match:   fuzzy match — weighted Jaccard
                             distance <= max_distance

When there are no exact matches, the fuzzy-targeting filter and
fuzzy as a fallback are applied.
"""
from rtb_sdk.helpers import get_ads_dict
from rtb_sdk.auction.simulation.filters.active_filter import filter_by_active
from rtb_sdk.auction.simulation.filters.match_filter import filter_by_precise_match, filter_by_fuzzy_match
from rtb_sdk.auction.simulation.filters.fuzzy_targeting_filter import filter_by_fuzzy_targeting_frequency
from examples.simulation.fixtures import (
    test_ads,
    SIM_DATE,
    request_match,
    request_partial,
    request_no_match,
)

active_ads = filter_by_active(test_ads, SIM_DATE)
ad_total_counts = {}

# ── precise match: the request falls exactly into the targets ───────────────────────────

precise = filter_by_precise_match(request_match, active_ads)
print(f"Precise (req_match):    {list(get_ads_dict(precise).keys())}")
# → ['ad_general', 'ad_targeted']
# ad_general: targets are empty → no vocab to check → always passes
# ad_targeted: City:[Moscow,Kazan] ∩ {Moscow} ≠ ∅
#              Device:[Smartphone] ∩ {Smartphone} ≠ ∅ → passing

# ── precise match: the request partially matches ─────────────────────────────────

precise2 = filter_by_precise_match(request_partial, active_ads)
print(f"Precise (req_partial):  {list(get_ads_dict(precise2).keys())}")
# → ['ad_general']
# ad_targeted: Device:[Smartphone] ∩ {Tablet} = ∅ → does not pass

# ── fuzzy match as a fallback ─────────────────────────────────────────────────

precise3 = filter_by_precise_match(request_no_match, active_ads)
print(f"Precise (req_no_match): {list(get_ads_dict(precise3).keys())}")
# → ['ad_general']  (ad_targeted: City:[Moscow,Kazan] ∩ {SPb} = ∅)

# If a fuzzy fallback is needed — apply the fuzzy-targeting filter and fuzzy
fuzzy_targeting_ads = filter_by_fuzzy_targeting_frequency(active_ads, ad_total_counts)
fuzzy = filter_by_fuzzy_match(request_partial, fuzzy_targeting_ads, max_distance=0.8)
print(f"Fuzzy  (req_partial, max_distance=0.8): {list(get_ads_dict(fuzzy).keys())}")
# ad_targeted: distance ≈ 0.75 (City matches partially, Device does not)
# → passes at max_distance=0.8
