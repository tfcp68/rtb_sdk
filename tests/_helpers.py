"""
Common infrastructure for loading and running test cases from tests.json.
"""

import json
import pytest
from pathlib import Path
from datetime import datetime
from typing import Any, Callable, TypedDict, cast

from rtb_sdk.errors import AuctionError

from collect_constants import TESTS_DIR, CASES_DIR, _ERROR_CODE_MAP, _SPECIAL_VALUES


class _CaseRequired(TypedDict):
    input: dict
    output: Any
    error: str | None
    description: str


class Case(_CaseRequired, total=False):
    check_output_type: bool


def _load_file(fpath: Path):
    """Loads a file depending on its extension and returns its contents."""
    suffix = fpath.suffix.lower()

    if suffix == ".json":
        with open(fpath, encoding="utf-8") as fh:
            return _resolve(json.load(fh))

    # --- CSV: loader not implemented, add if needed ---
    if suffix == ".csv":
        pass  # TODO: implement CSV loading via polars or csv.DictReader

    # --- Pickle: loader not implemented, add if needed ---
    if suffix == ".pkl":
        pass  # TODO: implement PKL loading (e.g. via pickle.load)


def _resolve(obj):
    """Recursively expands "file://..." — loads the file and keeps expanding."""
    if isinstance(obj, str) and obj.startswith("file://"):
        fpath = TESTS_DIR / obj[len("file://"):]
        return _load_file(fpath)
    if isinstance(obj, dict):
        return {k: _resolve(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve(item) for item in obj]
    return obj


_DATE_FIELDS = {"start_date", "end_date"}


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
    """Returns the list of cases for a function with file://, dates and objects already expanded."""
    fpath = CASES_DIR / f"{func_name}.json"
    with open(fpath, encoding="utf-8") as fh:
        raw = json.load(fh)
    result = [cast(Case, _parse_dates(_resolve(c))) for c in raw]
    if unpacker is not None:
        result = [cast(Case, unpacker(c)) for c in result]
    return result


def ids(cases_list: list[Case]) -> list[str]:
    return [c.get("description", f"case_{i}") for i, c in enumerate(cases_list)]


def _resolve_output(raw_output):
    if isinstance(raw_output, str) and raw_output in _SPECIAL_VALUES:
        return _SPECIAL_VALUES[raw_output]
    return raw_output


def _parse_error_code(error_str: str) -> int:
    for name, code in _ERROR_CODE_MAP.items():
        if name in error_str:
            return code
    raise ValueError(f"Unknown error code in the line: {error_str!r}")


def check_result(result, case: Case, precision: float = 1e-9) -> None:
    """
    Checks the result against the case's output / check_output_type fields.

    Logic:
      - check_output_type=True           → non-deterministic call,
                                           we only check that a non-None dict (Ad) was returned
      - output=None                      → the result must be None
      - output — float                   → comparison via pytest.approx
      - otherwise                        → strict equality
    """
    if case.get("check_output_type"):
        assert result is not None
        assert isinstance(result, dict)
        return

    output = _resolve_output(case["output"])

    if output is None:
        assert result is None
    elif isinstance(output, float):
        assert result == pytest.approx(output, abs=precision)
    else:
        assert result == output


def run(func, case: Case) -> None:
    """Runs the function with the case data and checks the result or the expected error."""
    if case["error"]:
        expected_code = _parse_error_code(case["error"])
        with pytest.raises(AuctionError) as exc_info:
            func(**case["input"])
        assert exc_info.value.error_code == expected_code
    else:
        result = func(**case["input"])
        check_result(result, case)
