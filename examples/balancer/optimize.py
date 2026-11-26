from rtb_sdk.balancer import balance_traffic

from examples.balancer.fixtures import (
    TOTAL_TRAFFIC_VOLUME, VOCABS, TAG_PROBS,
    ad_moscow_m, ad_pair_young, ad_age,
)


ads = {
    'ad_moscow_m':   ad_moscow_m,
    'ad_pair_young': ad_pair_young,
    'ad_age':        ad_age,
}

params_maximize_volume = {
    'total_traffic_volume': TOTAL_TRAFFIC_VOLUME,
    'vocabs':               VOCABS,
    'tag_probabilities':    TAG_PROBS,
    'objective':            'maximize_volume',
}

params_maximize_money = {
    'total_traffic_volume': TOTAL_TRAFFIC_VOLUME,
    'vocabs':               VOCABS,
    'tag_probabilities':    TAG_PROBS,
    'objective':            'maximize_money',
}

result_maximize_volume = balance_traffic(ads, params_maximize_volume)
result_maximize_money = balance_traffic(ads, params_maximize_money)

print("Maximizing volume distribution:")
print(dict(sorted(result_maximize_volume.items())))
print()

print("Income-maximizing distribution:")
print(dict(sorted(result_maximize_money.items())))
