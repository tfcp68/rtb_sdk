"""
Companies for the log benchmark: JSON loading, scaling for a scenario.

File format (see ads_manual.json / gen_ads.py):

{
  "meta": {...},
  "ads": [
    {
      "id": "fed_bank", "name": "FederalBank", "cpm": 280.0, "priority": 5.0,
      "targets": {"Region": ["100001", "700001"], "Device": ["WEB_BROWSER_A"]},
      "volume_weight": 1.0,                    # multiplier of targeting-based plan share
      "limits": "normal",                       # ad-limits profile (loose/normal/tight/none)
      "ad_limits_rel": {"h": 2.5, "d": 1.3},    # or explicit multipliers of the uniform rate
      "ad_frequency_limit": {"h": 500},         # or absolute values (take precedence)
      "user_frequency_limit": {"d": 4, "w": 10},
      "min_interval": 120,                      # seconds, per user×ad pair
      "start_frac": 0.0, "end_frac": 1.0        # display window as a share of the period
    }, ...
  ]
}

Ad limits are set relative to the "uniform rate" volume/period:
    limit_g = ceil(volume / period_seconds * window_g * slack_g)
and therefore automatically scale together with volume and the period.
User limits are absolute (4 impressions per day is 4 impressions per day).
"""
from __future__ import annotations

import sys as _privacy_sys
from pathlib import Path as _PrivacyPath
_privacy_sys.path.insert(0, str(_PrivacyPath(__file__).resolve().parents[2]))
from benchmarks import report_privacy as privacy

import json
import math
from typing import Any

import numpy as np

try:
    from .engine_full import AdPack, GRAN_SECONDS, GRANS, DAY
except ImportError:
    from engine_full import AdPack, GRAN_SECONDS, GRANS, DAY

# Multiplier profiles relative to the uniform rate. The daily traffic profile is uneven
# (the hourly peak ≈ 1.8× the average), so the "normal" hourly limit is slightly above the peak.
AD_LIMIT_PROFILES: dict[str, dict[str, float]] = {
    "none":   {},
    "loose":  {"h": 3.5, "d": 1.8},
    "normal": {"t": 3.0, "h": 2.0, "d": 1.3},
    "tight":  {"t": 2.2, "h": 1.5, "d": 1.1, "w": 1.03},
}
BASE_VOLUME_FACTOR = 1.3
TRAFFIC_FACTORS = {"balanced": 1.0, "shortage": 0.5, "excess": 2.0}


def load_ads_file(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    ads = data["ads"] if isinstance(data, dict) else data
    ids = [a["id"] for a in ads]
    if len(set(ids)) != len(ids):
        raise ValueError("There are repetitive companies in the file id")
    for ad in ads:
        privacy.register([ad["id"], ad.get("name", ad["id"])])
    return ads


def _resolve_report_targets(prep, ads: list[dict]) -> list[dict]:
    """Allow exported campaign snapshots to replay against original log labels."""
    reverse = {name: {alias: v for v in values for alias in (privacy.tag_label(v, name), privacy.legacy_label(v))}
               for name, values in prep.vocabs.items()}
    return [dict(ad, targets={name: [reverse.get(name, {}).get(v, v) for v in values]
                              for name, values in ad.get("targets", {}).items()})
            for ad in ads]


def compute_match_rates(prep, ads: list[dict]) -> list[float]:
    """Share of requests (over all days of the logs) that fall under the targeting (precise)."""
    ads = _resolve_report_targets(prep, ads)
    order = prep.vocab_order
    w = prep.combo_counts.astype(np.float64)
    tot = w.sum()
    rates = []
    for ad in ads:
        ok = np.ones(len(w), dtype=bool)
        for vi, vname in enumerate(order):
            tags = ad.get("targets", {}).get(vname)
            if tags is None:
                continue
            labels = prep.vocabs[vname]
            idx = {l: i for i, l in enumerate(labels)}
            missing = [t for t in tags if t not in idx]
            if missing:
                raise ValueError(f"[{ad['id']}] tagless {missing[:3]} dictionary {vname!r}")
            lut = np.zeros(len(labels), dtype=bool)
            for t in tags:
                lut[idx[t]] = True
            lut[0] = False
            ok &= lut[prep.combos[:, vi]]
        rates.append(float(w[ok].sum() / tot))
    return rates


def build_pack(
    prep,
    ads: list[dict],
    n_nominal: int,
    period_days: int,
    volume_factor: float = BASE_VOLUME_FACTOR,
    limits_enabled: bool = True,
) -> AdPack:
    """Scales the companies for a scenario: volume, budget, limits, display window."""
    from rtb_sdk.helpers.auction import create_ad, create_frequency_limits
    from rtb_sdk.auction.functions.utils import get_real_month_volume

    ads = _resolve_report_targets(prep, ads)
    rates = compute_match_rates(prep, ads)
    multipliers = [float(ad.get("volume_weight", 1.0)) for ad in ads]
    if any(not math.isfinite(w) or w <= 0 for w in multipliers):
        raise ValueError("volume_weight It should be a positive finite number")
    weights = [rate * multiplier for rate, multiplier in zip(rates, multipliers)]
    tot_rate = sum(weights) or 1.0
    period_s = period_days * DAY
    gran_key = {"t": "ten_minutes", "h": "hour", "d": "day", "w": "week", "m": "month"}

    cols: dict[str, list] = {k: [] for k in (
        "ids names cpm priority volume budget targets match_rate ad_lims user_lims "
        "min_interval start_s end_s month_limit ad_lims_raw user_lims_raw").split()}

    for ad, rate, weight in zip(ads, rates, weights):
        volume = max(1, round(n_nominal * volume_factor * weight / tot_rate))
        # ── ad limits ──
        raw: dict[str, int] = {}
        if limits_enabled:
            rel = dict(AD_LIMIT_PROFILES[ad.get("limits", "none")])
            rel.update(ad.get("ad_limits_rel", {}))
            for g, slack in rel.items():
                if slack and slack > 0:
                    raw[g] = max(1, math.ceil(volume / period_s * GRAN_SECONDS[g] * slack))
            for g, v in ad.get("ad_frequency_limit", {}).items():
                raw[g] = int(v)
        uraw: dict[str, int] = {}
        mi = 0
        if limits_enabled:
            uraw = {g: int(v) for g, v in ad.get("user_frequency_limit", {}).items() if v and v > 0}
            mi = int(ad.get("min_interval", 0))
        start_s = int(period_s * ad.get("start_frac", 0.0))
        end_s = int(period_s * ad.get("end_frac", 1.0))
        if end_s >= period_s:
            end_s = 1 << 60

        # month_limit from the SDK
        sdk_ad = create_ad(
            id=ad["id"], volume=volume, cpm=ad["cpm"], priority=ad["priority"],
            ad_frequency_limit=create_frequency_limits(
                **{gran_key[g]: v for g, v in raw.items()}, min_interval=mi),
        )
        cols["ids"].append(ad["id"])
        cols["names"].append(ad.get("name", ad["id"]))
        cols["cpm"].append(float(ad["cpm"]))
        cols["priority"].append(float(ad["priority"]))
        cols["volume"].append(volume)
        cols["budget"].append(volume * float(ad["cpm"]))
        cols["targets"].append(ad.get("targets", {}))
        cols["match_rate"].append(rate)
        cols["ad_lims"].append(tuple((v, GRAN_SECONDS[g]) for g, v in raw.items()))
        cols["user_lims"].append(tuple((v, GRAN_SECONDS[g]) for g, v in uraw.items()))
        cols["min_interval"].append(mi)
        cols["start_s"].append(start_s)
        cols["end_s"].append(end_s)
        cols["month_limit"].append(float(get_real_month_volume(sdk_ad)))
        cols["ad_lims_raw"].append(raw)
        cols["user_lims_raw"].append(uraw)
    return AdPack(**cols)
