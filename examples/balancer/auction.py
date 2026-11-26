from rtb_sdk.balancer import balance_traffic, convert_report_to_auction_data, auction
from rtb_sdk.helpers import create_parameters_balanced

from examples.balancer.fixtures import (
    TOTAL_TRAFFIC_VOLUME, VOCABS, TAG_PROBS,
    ad_moscow_m, ad_pair_young, ad_age,
)


# --- Step 1: balancing ---

ads = {
    'ad_moscow_m':   ad_moscow_m,
    'ad_pair_young': ad_pair_young,
    'ad_age':        ad_age,
}

params = {
    'total_traffic_volume': TOTAL_TRAFFIC_VOLUME,
    'vocabs':               VOCABS,
    'tag_probabilities':    TAG_PROBS,
    'objective':            'maximize_volume',
}

report = balance_traffic(ads, params)
print("Traffic distribution:")
print(dict(sorted(report.items())))
print()

# --- Step 2: converting the report into data for the auction ---
# convert_report_to_auction_data computes the impression probabilities of each
# ad and stores the data needed for the auction.

balancer_data = convert_report_to_auction_data(ads, report, params)

# --- Step 3: auction for incoming requests ---
# For each user request we create ParametersBalanced and call auction().
# auction() returns the winning ad's dictionary or None.
#
# Note: auction() is a stochastic mechanism for achieving the target
# traffic distribution in aggregate over many requests, not a strict
# targeting matcher. Ad weight = distribution[ad] * P(request) / P(ad).

# ads_payload — data that auction() will return to the winner (an arbitrary dict)
ads_payload = {
    'ad_moscow_m':   {'id': 'ad_moscow_m',   'creative': 'banner_moscow_m.png'},
    'ad_pair_young': {'id': 'ad_pair_young', 'creative': 'banner_pair_young.png'},
    'ad_age':        {'id': 'ad_age',        'creative': 'banner_age.png'},
}

requests = [
    {'City': 'Moscow', 'Gender': 'M', 'Age': '18-25'},
    {'City': 'SPb',    'Gender': 'F', 'Age': '26-35'},
    {'City': 'Moscow', 'Gender': 'M', 'Age': '36-45'},
]

for req in requests:
    auction_params = create_parameters_balanced(
        request=req,
        vocabs=VOCABS,
        balancer_data=balancer_data,
    )
    winner = auction(ads_payload, auction_params)
    print(f"Request {req}  -->  winner: {winner}")
