"""
Common configuration of the "manager traffic" EDA.

MARKUP: which requests go to the manager (a black box). There are no logs with response codes,
so the segment is defined by a RULE on device_type. The rule is changed here (or via
--markup-json), the rest of the code reads only SEGMENTS.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from benchmarks.source_adapters import device_aliases

_SOURCE_DEVICES = {alias: raw for raw, alias in device_aliases().items()}

HERE = os.path.dirname(os.path.abspath(__file__))
PREPARED = os.path.join(HERE, "..", "logs", "manager_prepared")
CACHE = os.path.join(HERE, "cache")
REPORT = os.path.join(HERE, "..", "..", "docs", "benchmark", "manager_traffic", "reports")

# Device order is stable because EDA caches encode it as integer indices.
ALL_DEVICES = [
    "WEB_BROWSER_A", "ANDROID_SET_TOP_BOX_A", "ANDROID_TV_A", "SET_TOP_BOX_A",
    "SMART_TV_PLATFORM_A", "SMART_TV_PLATFORM_B", "SMART_TV_PLATFORM_C",
    "ANDROID_PHONE_A", "IOS_PHONE_A", "ANDROID_TABLET_A", "IOS_TABLET_A",
    "STREAMING_TV_BOX_A", "OTHER_DEVICE_CLIENT_A",
]
ALL_DEVICES = [_SOURCE_DEVICES.get(d, d) for d in ALL_DEVICES]
DEV_IDX = {d: i for i, d in enumerate(ALL_DEVICES)}   # i < 32 (used in bit packing)

# Devices excluded from the "no web/mobile/tablets" segment.
EXCLUDED_NON_STB = {"WEB_BROWSER_A", "OTHER_DEVICE_CLIENT_A", "ANDROID_PHONE_A", "IOS_PHONE_A", "ANDROID_TABLET_A", "IOS_TABLET_A"}

EXCLUDED_NON_STB = {_SOURCE_DEVICES.get(d, d) for d in EXCLUDED_NON_STB}

# Markups. The key is the name in the reports. 'all' = any device_type from ALL_DEVICES.
SEGMENTS: dict[str, list[str]] = {
    "all": list(ALL_DEVICES),
    "no_web_mobile": [d for d in ALL_DEVICES if d not in EXCLUDED_NON_STB],
}
# And a separate "markup" for each device type: seg "dev:<DEVICE>"
for _d in ALL_DEVICES:
    SEGMENTS[f"dev:{_d}"] = [_d]

PRIMARY_SEGMENT = "no_web_mobile"   # segment for detailed charts (the others are for comparison)

EP_IDX = {"avod": 0, "alive": 1}    # avod = VOD, alive = live
EP_RU = {"avod": "VOD", "alive": "Live"}

# tags for frequencies: column → Russian name
TAGS = {
    "device": "Device", "ep": "Type (VOD/Live)", "place": "ad_place_type", "position": "ad_position",
    "location": "Region", "category": "Category", "channel": "Channel", "contractor": "Contractor",
    "is_child": "Child", "age": "Age", "broadcast": "broadcast_type",
    "client_version": "Client version", "ua": "User-Agent",
}
HIGH_CARD = ["location", "category", "channel", "contractor", "client_version", "ua"]
LOW_CARD = ["device", "ep", "place", "position", "is_child", "age", "broadcast"]

SESSION_GAP = 1800  # seconds of silence → a new session
