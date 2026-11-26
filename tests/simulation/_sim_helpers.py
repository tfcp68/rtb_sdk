"""
Helper module for the simulation filter tests.

A local copy of the infrastructure with paths pointing to
tests/simulation/cases/ instead of tests/auction/cases/.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Callable, cast

from tests._helpers import run, ids, check_result, Case  # noqa: F401 — re-export from tests/_helpers.py

TESTS_DIR = Path(__file__).parent
CASES_DIR = TESTS_DIR / "cases"

_DATE_FIELDS = {"start_date", "end_date"}


def _resolve(obj):
    """Recursively expands file://... — loads the file and keeps expanding."""
    if isinstance(obj, str) and obj.startswith("file://"):
        fpath = TESTS_DIR / obj[len("file://"):]
        with open(fpath, encoding="utf-8") as fh:
            return _resolve(json.load(fh))
    if isinstance(obj, dict):
        return {k: _resolve(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve(item) for item in obj]
    return obj


def _parse_dates(obj):
    """Recursively converts string dates to datetime for the start_date/end_date fields."""
    if isinstance(obj, dict):
        return {
            k: (datetime.fromisoformat(v) if k in _DATE_FIELDS and isinstance(v, str) else _parse_dates(v))
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_parse_dates(item) for item in obj]
    return obj


def cases(func_name: str, unpacker: Callable | None = None) -> list[Case]:
    """Loads cases from cases/<func_name>.json, applies date parsing and the unpacker."""
    fpath = CASES_DIR / f"{func_name}.json"
    with open(fpath, encoding="utf-8") as fh:
        raw = json.load(fh)
    result = [cast(Case, _parse_dates(_resolve(c))) for c in raw]
    if unpacker is not None:
        result = [cast(Case, unpacker(c)) for c in result]
    return result
