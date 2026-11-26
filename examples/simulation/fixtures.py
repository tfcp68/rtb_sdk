from datetime import datetime
from rtb_sdk.helpers import (
    create_ad,
    create_request,
    create_request_tags,
    create_frequency_limits,
    create_target_vector,
    create_ads_dict,
    get_ad_id,
)

# Common date of the requests in the simulation
SIM_DATE = datetime(2025, 7, 15, 12, 0, 0)

# ── ads ────────────────────────────────────────────────────────────────

# An ad without tag restrictions — responds to any request
ad_general = create_ad(
    id='ad_general',
    active=True,
    targets=create_target_vector(),
    start_date=datetime(2025, 7, 1),
    end_date=datetime(2025, 7, 31),
    cpm=1000.0,
    priority=1.0,
    volume=500,
    ad_frequency_limit=create_frequency_limits(day=100, hour=20),
    user_frequency_limit=create_frequency_limits(day=5, min_interval=300),
    parasitic_freq_limit=create_frequency_limits(day=20),
)

# An ad targeted by city and device
ad_targeted = create_ad(
    id='ad_targeted',
    active=True,
    targets=create_target_vector({
        'City': ['Moscow', 'Kazan'],
        'Device': ['Smartphone'],
    }),
    start_date=datetime(2025, 7, 1),
    end_date=datetime(2025, 7, 31),
    cpm=2000.0,
    priority=1.0,
    volume=200,
    ad_frequency_limit=create_frequency_limits(day=50, hour=10),
    user_frequency_limit=create_frequency_limits(day=3, min_interval=600),
    parasitic_freq_limit=create_frequency_limits(day=5),
)

# An inactive ad — must not pass the activity filter
ad_inactive = create_ad(
    id='ad_inactive',
    active=False,
    targets=create_target_vector(),
    start_date=datetime(2025, 7, 1),
    end_date=datetime(2025, 7, 31),
    cpm=500.0,
    priority=1.0,
    volume=100,
    ad_frequency_limit=create_frequency_limits(day=100),
    user_frequency_limit=create_frequency_limits(day=10),
)

# An expired ad — the campaign ended before SIM_DATE
ad_expired = create_ad(
    id='ad_expired',
    active=True,
    targets=create_target_vector(),
    start_date=datetime(2025, 6, 1),
    end_date=datetime(2025, 6, 30),
    cpm=800.0,
    priority=1.0,
    volume=100,
    ad_frequency_limit=create_frequency_limits(day=100),
    user_frequency_limit=create_frequency_limits(day=10),
)

test_ads = create_ads_dict({
    get_ad_id(ad_general): ad_general,
    get_ad_id(ad_targeted): ad_targeted,
    get_ad_id(ad_inactive): ad_inactive,
    get_ad_id(ad_expired): ad_expired,
})

# ── tag dictionaries ─────────────────────────────────────────────────────────────

test_vocabs = create_target_vector({
    'City': ['Moscow', 'Kazan', 'Saint-Petersburg', 'Novosibirsk'],
    'Device': ['Smartphone', 'Tablet', 'PC'],
    'Age': ['18-25', '26-35', '36-45'],
})

# ── requests ───────────────────────────────────────────────────────────────────

# The request falls exactly into the targets of ad_targeted
request_match = create_request(
    id='req_1',
    user_id='user_001',
    date=datetime(2025, 7, 15, 10, 0, 0),
    tags=create_request_tags({
        'City': 'City:Moscow',
        'Device': 'Device:Smartphone',
        'Age': 'Age:26-35',
    }),
)

# The request partially matches ad_targeted (Kazan is present, Tablet is not)
request_partial = create_request(
    id='req_2',
    user_id='user_002',
    date=datetime(2025, 7, 15, 11, 0, 0),
    tags=create_request_tags({
        'City': 'City:Kazan',
        'Device': 'Device:Tablet',
        'Age': 'Age:18-25',
    }),
)

# The request does not match the targets of ad_targeted
request_no_match = create_request(
    id='req_3',
    user_id='user_001',
    date=datetime(2025, 7, 15, 12, 30, 0),
    tags=create_request_tags({
        'City': 'City:Saint-Petersburg',
        'Device': 'Device:PC',
    }),
)

test_requests = [request_match, request_partial, request_no_match]
