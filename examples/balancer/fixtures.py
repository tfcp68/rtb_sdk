from rtb_sdk.helpers import (
    create_inner_ad,
    raw_tag_dict_to_full_tag_dict,
)

TOTAL_TRAFFIC_VOLUME = 700

VOCABS = {
    'City':   ['Moscow', 'SPb'],
    'Gender':     ['M', 'F'],
    'Age': ['18-25', '26-35', '36-45'],
}

TAG_PROBS = {
    'City':   {'Moscow': 0.5, 'SPb': 0.3},
    'Gender':     {'M': 0.5, 'F': 0.5},
    'Age': {'18-25': 0.3, '26-35': 0.4, '36-45': 0.2},
}

# Updated probabilities: traffic shifted in favor of St. Petersburg and young people
NEW_TAG_PROBS = {
    'City':   {'Moscow': 0.35, 'SPb': 0.55},
    'Gender':     {'M': 0.5, 'F': 0.5},
    'Age': {'18-25': 0.5, '26-35': 0.3, '36-45': 0.1},
}

ad_moscow_m = create_inner_ad(
    id="ad_moscow_m",
    targets=raw_tag_dict_to_full_tag_dict({'City': ['Moscow'], 'Gender': ['M']}),
    price=50,
    min_vol=100,
    max_vol=500,
    freq=500,
)

ad_pair_young = create_inner_ad(
    id="ad_pair_young",
    targets=raw_tag_dict_to_full_tag_dict({'City': ['Moscow', 'SPb'], 'Age': ['18-25']}),
    price=100,
    min_vol=100,
    max_vol=500,
    freq=500,
)

ad_age = create_inner_ad(
    id="ad_age",
    targets=raw_tag_dict_to_full_tag_dict({'Age': ['26-35', '36-45']}),
    price=10,
    min_vol=100,
    max_vol=500,
    freq=500,
)

ad_new_spb = create_inner_ad(
    id="ad_new_spb",
    targets=raw_tag_dict_to_full_tag_dict({'City': ['SPb']}),
    price=50,
    min_vol=50,
    max_vol=300,
    freq=500,
)
