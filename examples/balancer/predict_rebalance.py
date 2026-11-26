from rtb_sdk.balancer import balance_traffic, predict_rebalance

from examples.balancer.fixtures import (
    TOTAL_TRAFFIC_VOLUME, VOCABS, TAG_PROBS, NEW_TAG_PROBS,
    ad_moscow_m, ad_pair_young, ad_age,
)


ads = {
    'ad_moscow_m':   ad_moscow_m,
    'ad_pair_young': ad_pair_young,
    'ad_age':        ad_age,
}

# Initial balancing with the old traffic probabilities
old_params = {
    'total_traffic_volume': TOTAL_TRAFFIC_VOLUME,
    'vocabs':               VOCABS,
    'tag_probabilities':    TAG_PROBS,
    'objective':            'maximize_volume',
}
current_distribution = balance_traffic(ads, old_params)
print("Current distribution (old-school):")
print(dict(sorted(current_distribution.items())))
print()

# Predict how the volumes will change under the new traffic probabilities.
# predict_rebalance does not change the real distribution - it only shows the delta.
new_params = {
    'total_traffic_volume': TOTAL_TRAFFIC_VOLUME,
    'vocabs':               VOCABS,
    'tag_probabilities':    NEW_TAG_PROBS,
    'objective':            'maximize_volume',
}
result = predict_rebalance(
    ads=ads,
    ad_vol_distr=current_distribution,
    params=new_params,
)

print("New optimal report:")
print(dict(sorted(result['report'].items())))
print()

print("Traffic changes (+ more, - less):")
print(dict(sorted(result['volume_delta'].items())))
