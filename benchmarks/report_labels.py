"""Stable report labels that retain the meaning of categorical features."""
from __future__ import annotations

import hashlib
import re

from benchmarks.source_adapters import device_aliases, label_aliases


# Source spellings live in the optional local adapter.
DEVICE_NAMES = device_aliases()
SEMANTIC_NAMES = {
    **DEVICE_NAMES,
    **label_aliases(),
    "mobile": "mobile_device",
    "desktop": "desktop_computer",
    "tablet": "tablet_device",
    "startroll": "session_start_ad",
    "switchroll": "channel_change_ad",
    "midroll": "in_content_ad",
    "preroll": "before_content_ad",
    "postroll": "after_content_ad",
    "pauseroll": "pause_screen_ad",
    "ott": "internet_streaming",
    "iptv": "managed_tv_network",
    "avod": "on_demand_video",
    "alive": "live_video",
    "VOD": "VOD",
    "Live": "Live",
    "M": "male",
    "F": "female",
    "auto": "automotive",
    "finances": "financial_services",
    "property": "real_estate",
    "fashion": "apparel",
    "sport": "sports_fitness",
    "journey": "travel_leisure",
    "technology": "consumer_technology",
    "food": "food_dining",
    "health": "health_wellness",
    "education": "learning",
    "fun": "entertainment",
    "family": "household",
    "Moscow": "MetroCity_A",
    "SPb": "MetroCity_B",
    "Novosibirsk": "City_C",
    "Yekaterinburg": "City_D",
    "Kazan": "City_E",
    "Nizhny_Novgorod": "City_F",
    "Samara": "City_G",
    "Krasnodar": "City_H",
    "Rostov-on-Don": "City_I",
    "Ufa": "City_J",
    "Voronezh": "City_K",
    "Perm": "City_L",
    "Volgograd": "City_M",
    "Krasnoyarsk": "City_N",
    "Saratov": "City_O",
}
PUBLIC_NAMES = set(SEMANTIC_NAMES.values()) | {
    '2.310.5', '2.312.9', '2.316.5',
    '6.76.2-250', '6.78.1-250', '6.78.9-250',
    'ANDROID_PHONE_A', 'ANDROID_SET_TOP_BOX_A', 'ANDROID_TABLET_A',
    'ANDROID_TV_A', 'ANDROID_TV_B', 'ANDROID_TV_C',
    'IOS_PHONE_A', 'IOS_TABLET_A', 'OTHER_DEVICE_CLIENT_A',
    'SET_TOP_BOX_A', 'SMART_TV_CLIENT_E', 'SMART_TV_PLATFORM_A',
    'SMART_TV_PLATFORM_B', 'SMART_TV_PLATFORM_C', 'SMART_TV_PLATFORM_D',
    'STREAMING_SET_TOP_BOX_B', 'STREAMING_TV_BOX_A', 'WEB_BROWSER_A',
    'desktop_computer', 'mobile_device', 'tablet_device',
}
_PREFIXES = ("Bank", "Telecom", "Retail", "Health", "Travel", "Automotive", "Children",
             "Property", "Entertainment", "Education", "Campaign", "Segment", "Device",
             "Region", "Channel", "Category", "Contractor", "Value", "City", "Interest", "Version")
_PUBLIC_LABEL = re.compile(r"(?:" + "|".join(_PREFIXES) + r")_[0-9a-f]{8,16}")


def legacy_label(value) -> str:
    return "tag_" + hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:16]


def label(value, field: str | None = None) -> str:
    value = str(value)
    if (value.lower() in {"true", "false"} or value in PUBLIC_NAMES or _PUBLIC_LABEL.fullmatch(value)
            or re.fullmatch(r"(?:TABLET|PHONE|SET_TOP_BOX|WEB_BROWSER|TV)_CLIENT_[0-9a-f]{16}", value)):
        return value
    # Ages and placement ordinals are measurements, rather than opaque IDs.
    if (field in {"Age", "age"} and value.isdigit() and int(value) <= 120
            or field in {"position", "ad_position"} and value.isdigit() and int(value) <= 100
            or re.fullmatch(r"\d{1,3}(?:-\d{1,3}|\+)", value)):
        return value
    if value in SEMANTIC_NAMES:
        return SEMANTIC_NAMES[value]
    if value.isdigit():
        # Reserve 12-digit IDs starting with 9 for reports. The affine permutation
        # is one-to-one over the supported source-ID domain and hides raw suffixes.
        if re.fullmatch(r"9\d{11,}", value):
            return value
        encoded = int("1" + value)  # Preserve distinctions such as 01 versus 1.
        if encoded < 100_000_000_000:
            return str(900_000_000_000 + (104729 * encoded + 48611) % 100_000_000_000)
        # Larger IDs remain numeric; use a separate, reversible-width domain.
        width = len(value) + 2
        modulus = 10 ** (width - 1)
        return str(9 * modulus + (104729 * encoded + 48611) % modulus)
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    if re.fullmatch(r"\d+(?:\.\d+)+(?:-\d+)?", value):
        if value.startswith("90."):
            return value
        return f"90.{int(digest[:8], 16)}.{int(digest[8:], 16)}"
    # Unknown device clients still advertise their broad hardware category.
    upper = value.upper()
    if field in {"Device", "device", "device_type", "pool_devices"} or any(
            token in upper for token in ("VENDOR_TV", "VENDOR_WEB")):
        kind = next((name for token, name in (("TABLET", "TABLET"), ("PHONE", "PHONE"),
                    ("STB", "SET_TOP_BOX"), ("WEB", "WEB_BROWSER"), ("TV", "TV"))
                     if token in upper), "CLIENT")
        return f"Device_{digest}" if kind == "CLIENT" else f"{kind}_CLIENT_{digest}"
    for needles, kind in (
        (("bank", "financ", "mortgage", "invest"), "Bank"),
        (("telecom", "mobile_op"), "Telecom"),
        (("health", "pharma", "medplus", "medicin"), "Health"),
        (("travel", "journey", "avia", "tur_agency"), "Travel"),
        (("auto", "car_"), "Automotive"),
        (("kids", "child", "detmir"), "Children"),
        (("retail", "market", "fashion", "clothes", "moda"), "Retail"),
        (("realty", "property", "furn"), "Property"),
        (("kino", "cinema", "game", "news", "serial", "series"), "Entertainment"),
        (("school", "education"), "Education"),
    ):
        if any(n in value.lower() for n in needles):
            return f"{kind}_{digest}"
    kind = {"Region": "Region", "location": "Region", "Category": "Category",
            "category": "Category", "Channel": "Channel", "channel": "Channel",
            "contractor": "Contractor", "City": "City", "Interest": "Interest"}.get(field, "Campaign")
    return f"{kind}_{digest}"
