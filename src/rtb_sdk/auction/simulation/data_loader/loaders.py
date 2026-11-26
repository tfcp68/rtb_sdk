"""
Loading and saving data for the simulation.

File loaders (load_ads_from_json, load_requests_from_json,
load_requests_from_csv, load_vocabs_from_json, sort_request) live
in auction.helpers and are re-exported from here for convenience.

This module re-exports them and adds save_report —
a simulation-specific save function.
"""
import json
from datetime import datetime

from rtb_sdk.auction.helpers import (
    load_ads_from_json,
    load_requests_from_json,
    load_requests_from_csv,
    load_vocabs_from_json,
    sort_request,
)

__all__ = [
    'load_ads_from_json',
    'load_requests_from_json',
    'load_requests_from_csv',
    'load_vocabs_from_json',
    'sort_request',
    'save_report',
]


# ── report ─────────────────────────────────────────────────────────────────────

def save_report(report: dict, path: str) -> None:
    """
    Saves the simulation report to a JSON file.

    Converts datetime fields to strings before saving.

    Args:
        report: arbitrary dictionary with the simulation results
        path: path to save to (creates the file or overwrites it)
    """
    class _DatetimeEncoder(json.JSONEncoder):
        def default(self, o):
            if isinstance(o, datetime):
                return o.isoformat()
            return super().default(o)

    with open(path, 'w') as f:
        json.dump(report, f, cls=_DatetimeEncoder, ensure_ascii=False, indent=2)
