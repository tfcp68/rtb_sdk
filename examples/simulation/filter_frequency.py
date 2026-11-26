"""
Example of applying the frequency filters.

Demonstrates the sequential application of three filters:
  - filter_by_ad_frequency:   global impression limit of an ad
  - filter_by_user_frequency: impression limit for a specific user
  - filter_by_min_interval:   minimum interval between impressions
"""
from datetime import datetime, timedelta

from rtb_sdk.helpers import get_ads_dict
from rtb_sdk.auction.simulation.filters.active_filter import filter_by_active
from rtb_sdk.auction.simulation.filters.frequency_filter import filter_by_ad_frequency
from rtb_sdk.auction.simulation.filters.user_frequency_filter import filter_by_user_frequency
from rtb_sdk.auction.simulation.filters.min_interval_filter import filter_by_min_interval
from examples.simulation.fixtures import test_ads, SIM_DATE

# ── global timestamp lists of ads ────────────────────────────────────

# ad_general: 99 impressions per day, 10 in the last hour (limits: day=100, hour=20)
# 10 timestamps — in the range [11:00, 11:54], one every 6 minutes
# 89 timestamps — in the range [10:00 yesterday, 10:55 today]
_ad_general_ts = sorted([
    *(SIM_DATE - timedelta(minutes=6 * i) for i in range(1, 11)),
    *(SIM_DATE - timedelta(hours=2, minutes=10 * i) for i in range(89)),
])

# ad_targeted: 5 impressions per day, 2 in the last hour (limits: day=50, hour=10)
_ad_targeted_ts = sorted([
    SIM_DATE - timedelta(minutes=20),
    SIM_DATE - timedelta(minutes=40),
    SIM_DATE - timedelta(hours=3),
    SIM_DATE - timedelta(hours=5),
    SIM_DATE - timedelta(hours=8),
])

ad_timestamps = {
    'ad_general':  _ad_general_ts,
    'ad_targeted': _ad_targeted_ts,
}

# ── timestamp list for user_001 ─────────────────────────────────────────────

# user_001 has already seen ad_targeted 3 times today (limit user_frequency_limit.day=3)
user_ad_timestamps = {
    'ad_targeted': sorted([
        SIM_DATE - timedelta(minutes=30),
        SIM_DATE - timedelta(hours=4),
        SIM_DATE - timedelta(hours=10),
    ])
}

# ── last impression time for user_001 ─────────────────────────────────────

# ad_general was shown 5 minutes ago; min_interval=300 sec → exactly on the boundary
user_ad_show_times = {
    'ad_general': datetime(2025, 7, 15, 11, 55, 0),
}

# ── applying the filters ───────────────────────────────────────────────────────

active_ads = filter_by_active(test_ads, SIM_DATE)
print(f"1. active:         {list(get_ads_dict(active_ads).keys())}")
# → ['ad_general', 'ad_targeted']

freq_ads = filter_by_ad_frequency(active_ads, ad_timestamps, SIM_DATE)
print(f"2. ad_frequency:   {list(get_ads_dict(freq_ads).keys())}")
# → ['ad_general', 'ad_targeted']  (neither exceeded the limits)

user_freq_ads = filter_by_user_frequency(freq_ads, user_ad_timestamps, SIM_DATE)
print(f"3. user_frequency: {list(get_ads_dict(user_freq_ads).keys())}")
# → ['ad_general']  (ad_targeted: the user saw it 3 times, the limit is exhausted)

interval_ads = filter_by_min_interval(user_freq_ads, user_ad_show_times, SIM_DATE)
print(f"4. min_interval:   {list(get_ads_dict(interval_ads).keys())}")
# → ['ad_general']  (300 seconds have passed since the last impression — it passes)
