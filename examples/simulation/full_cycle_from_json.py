"""
Full auction simulation cycle with loading data from JSON files.

Loads ads, requests and tag dictionaries from synthetic examples/generated_samples/,
then runs the full simulation cycle:
  - initializing MockDriver
  - processing a stream of requests
  - a chain of filters for each request
  - precise matching with a fallback to fuzzy
  - updating statistics after each auction

Run from the project root:
    python -m examples.simulation.full_cycle_from_json
"""
import os
from examples.sample_data import ensure_samples

from rtb_sdk.helpers import (
    create_parameters_ads_stats,
    get_ads_dict,
    get_ad_id,
    get_request_user_id,
    get_request_date,
)
from rtb_sdk.constants import SelectionFunc, AuctionType
from rtb_sdk.auction.auction import auction

from rtb_sdk.auction.helpers import (
    load_ads_from_json,
    load_requests_from_json,
    load_vocabs_from_json,
    sort_request,
)
from rtb_sdk.auction.simulation.driver.builder import create_mock_driver
from rtb_sdk.auction.simulation.driver.driver import (
    get_ads,
    get_ad_timestamps,
    get_ad_total_counts,
    get_ad_stats,
    get_user_ad_timestamps,
    get_user_ad_show_times,
    update_statistics,
    reset_statistics_if_needed,
)
from rtb_sdk.auction.simulation.filters.active_filter import filter_by_active
from rtb_sdk.auction.simulation.filters.frequency_filter import filter_by_ad_frequency
from rtb_sdk.auction.simulation.filters.user_frequency_filter import filter_by_user_frequency
from rtb_sdk.auction.simulation.filters.min_interval_filter import filter_by_min_interval
from rtb_sdk.auction.simulation.filters.match_filter import filter_by_precise_match, filter_by_fuzzy_match
from rtb_sdk.auction.simulation.filters.fuzzy_targeting_filter import filter_by_fuzzy_targeting_frequency

# ── paths to the data ─────────────────────────────────────────────────────────────

_DATA_DIR = str(ensure_samples())
ADS_PATH      = os.path.join(_DATA_DIR, 'filtered_ads.json')
REQUESTS_PATH = os.path.join(_DATA_DIR, 'filtered_requests.json')
VOCABS_PATH   = os.path.join(_DATA_DIR, 'vocab.json')

# ── loading the data ───────────────────────────────────────────────────────────

ads    = load_ads_from_json(ADS_PATH)
vocabs = load_vocabs_from_json(VOCABS_PATH)
requests = sort_request(load_requests_from_json(REQUESTS_PATH))

print(f"Loaded announcements: {len(get_ads_dict(ads))}")
print(f"Requests loaded:   {len(requests)}")
print(f"Tag dictionaries:        {list(vocabs.keys())}")
print()

# ── initializing MockDriver ──────────────────────────────────────────────────

driver = create_mock_driver(ads=ads, vocabs=vocabs)

# ── simulation loop ────────────────────────────────────────────────────

hits   = 0
misses = 0

for request in requests:
    user_id      = get_request_user_id(request)
    current_time = get_request_date(request)

    # 1. Reset stale counters
    reset_statistics_if_needed(driver, request)

    # 2. Up-to-date data from the driver
    driver_ads         = get_ads(driver)
    ad_timestamps      = get_ad_timestamps(driver)
    ad_total_counts    = get_ad_total_counts(driver)
    user_ad_timestamps = get_user_ad_timestamps(driver, user_id)
    user_ad_show_times = get_user_ad_show_times(driver, user_id)

    # 3. Chain of base filters
    filtered = filter_by_active(driver_ads, current_time)
    filtered = filter_by_ad_frequency(filtered, ad_timestamps, current_time)
    filtered = filter_by_user_frequency(filtered, user_ad_timestamps, current_time)
    filtered = filter_by_min_interval(filtered, user_ad_show_times, current_time)

    # 4. Tag matching
    precise_ads = filter_by_precise_match(request, filtered)

    if get_ads_dict(precise_ads):
        # 5a. Exact auction
        ad_ids = list(get_ads_dict(precise_ads).keys())
        params = create_parameters_ads_stats(
            auction_type=SelectionFunc.BEST_VELOCITY,
            ads_stats=get_ad_stats(driver, ad_ids),
        )
        winner       = auction(precise_ads, params)
        auction_type = AuctionType.PRECISE
    else:
        # 5b. Fuzzy fallback: fuzzy-targeting filter + fuzzy matching
        fuzzy_targeting_filtered = filter_by_fuzzy_targeting_frequency(filtered, ad_total_counts)
        fuzzy_ads                = filter_by_fuzzy_match(request, fuzzy_targeting_filtered)
        if get_ads_dict(fuzzy_ads):
            ad_ids = list(get_ads_dict(fuzzy_ads).keys())
            params = create_parameters_ads_stats(
                auction_type=SelectionFunc.BEST_PRICE,
                ads_stats=get_ad_stats(driver, ad_ids),
            )
            winner = auction(fuzzy_ads, params)
        else:
            winner = None
        auction_type = AuctionType.FUZZY

    # 6. Updating statistics on HIT
    winner_id = get_ad_id(winner) if winner is not None else None
    update_statistics(driver, request, auction_type, winner_id)

    if winner_id:
        hits += 1
    else:
        misses += 1

# ── final statistics ───────────────────────────────────────────────────────

print(f"Requests processed: {hits + misses}")
print(f"  HIT:  {hits}  ({hits / (hits + misses) * 100:.1f}%)")
print(f"  MISS: {misses}")
print()
print("Ad statistics after simulation:")
for ad_id in get_ads_dict(ads):
    stats = get_ad_stats(driver, [ad_id])
    print(f"  {ad_id}: {stats}")
