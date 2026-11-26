"""
Helper infrastructure for the adwords tests.
Independent of tests/collect_constants.py — CASES_DIR points to tests/adwords/cases/.
"""

import json
import pytest
from pathlib import Path
from datetime import datetime
from typing import Any, Callable

from rtb_sdk.errors import AuctionError, ErrorCodes

_CASES_DIR = Path(__file__).parent / "cases"

_ERROR_CODE_MAP: dict[str, int] = {
    name: value
    for name, value in vars(ErrorCodes).items()
    if not name.startswith("_")
}

_DATE_FIELDS = {"start_date", "end_date"}


def _parse_dates(obj):
    if isinstance(obj, dict):
        return {
            k: (datetime.fromisoformat(v) if k in _DATE_FIELDS and isinstance(v, str) else _parse_dates(v))
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_parse_dates(item) for item in obj]
    return obj


def cases(func_name: str, unpacker: Callable | None = None) -> list:
    fpath = _CASES_DIR / f"{func_name}.json"
    with open(fpath, encoding="utf-8") as fh:
        raw = json.load(fh)
    result = [_parse_dates(c) for c in raw]
    if unpacker is not None:
        result = [unpacker(c) for c in result]
    return result


def ids(cases_list: list) -> list[str]:
    return [c.get("description", f"case_{i}") for i, c in enumerate(cases_list)]


def _parse_error_code(error_str: str) -> int:
    for name, code in _ERROR_CODE_MAP.items():
        if name in error_str:
            return code
    raise ValueError(f"Unknown error code: {error_str!r}")


def _check_result(result: Any, case: dict) -> None:
    if case.get("check_output_type"):
        assert result is not None
        assert isinstance(result, dict)
        return
    output = case["output"]
    if output is None:
        assert result is None
    elif isinstance(output, float):
        assert result == pytest.approx(output, abs=1e-9)
    else:
        assert result == output


def run(func, case: dict) -> None:
    if case["error"]:
        expected_code = _parse_error_code(case["error"])
        with pytest.raises(AuctionError) as exc_info:
            func(**case["input"])
        assert exc_info.value.error_code == expected_code
    else:
        result = func(**case["input"])
        _check_result(result, case)
