from rtb_sdk.balancer import balance_traffic, add_new_balanced_campaign

from examples.balancer.fixtures import (
    TOTAL_TRAFFIC_VOLUME, VOCABS, TAG_PROBS,
    ad_moscow_m, ad_age, ad_new_spb,
)


existing_ads = {
    'ad_moscow_m': ad_moscow_m,
    'ad_age':      ad_age,
}

params = {
    'total_traffic_volume': TOTAL_TRAFFIC_VOLUME,
    'vocabs':               VOCABS,
    'tag_probabilities':    TAG_PROBS,
    'objective':            'maximize_volume',
}

# Get the current distribution for the existing campaigns
current_distribution = balance_traffic(existing_ads, params)
print("Current distribution:")
print(dict(sorted(current_distribution.items())))
print()

# Add a new ad without touching the fixed volumes.
# ad_vol_distr - fixed volumes from the previous optimization.
# The balancer will only distribute the remainder for ad_new_spb.
all_ads = {**existing_ads, 'ad_new_spb': ad_new_spb}
result = add_new_balanced_campaign(
    ads=all_ads,
    ad_vol_distr=current_distribution,
    params=params,
)

print("New distribution:")
print(dict(sorted(result['report'].items())))
print()

print("Volume of new campaigns:")
print(dict(sorted(result['new_ads_volumes'].items())))
