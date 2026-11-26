"""
Example of applying the activity filter.

filter_by_active keeps only the ads that:
  - active == True
  - start_date <= current_date <= end_date
"""
from rtb_sdk.helpers import get_ads_dict
from rtb_sdk.auction.simulation.filters.active_filter import filter_by_active
from examples.simulation.fixtures import test_ads, SIM_DATE

filtered = filter_by_active(test_ads, SIM_DATE)

print(f"To the filter:    {list(get_ads_dict(test_ads).keys())}")
print(f"After the filter: {list(get_ads_dict(filtered).keys())}")
# Expected result: ['ad_general', 'ad_targeted']
# ad_inactive — not active (active=False)
# ad_expired  — the campaign has ended (end_date=2025-06-30 < SIM_DATE)
