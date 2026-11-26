"""
Local loader and runner of cases for the predictor tests.

Mirrors tests/_helpers.py, but:
  - reads cases from tests/predictor/cases
  - expects PredictorError instead of AuctionError
"""
import json
import pytest
from pathlib import Path
from typing import Any, Callable, TypedDict, cast

from rtb_sdk.errors.predictor import PredictorError, ErrorCodes
from rtb_sdk.predictor.io.report import WrongDataFormatError


CASES_DIR = Path(__file__).parent / "cases"


_ERROR_CODE_MAP: dict[str, int] = {
    name: value
    for name, value in vars(ErrorCodes).items()
    if not name.startswith("_")
}
# Special marker for functions that raise WrongDataFormatError instead of PredictorError
_WRONG_FORMAT_ERROR = "WRONG_DATA_FORMAT"


class _CaseRequired(TypedDict):
    input: dict
    output: Any
    error: str | None
    description: str


class Case(_CaseRequired, total=False):
    check_output_type: bool


def cases(func_name: str, unpacker: Callable | None = None) -> list[Case]:
    """Returns the list of cases for a function."""
    fpath = CASES_DIR / f"{func_name}.json"
    if not fpath.exists():
        return []
    with open(fpath, encoding="utf-8") as fh:
        raw = json.load(fh)
    result = [cast(Case, c) for c in raw]
    if unpacker is not None:
        result = [cast(Case, unpacker(c)) for c in result]
    return result


def ids(cases_list: list[Case]) -> list[str]:
    return [c.get("description", f"case_{i}") for i, c in enumerate(cases_list)]


def _parse_error_code(error_str: str) -> int:
    for name, code in _ERROR_CODE_MAP.items():
        if name in error_str:
            return code
    raise ValueError(f"Unknown error code in the line: {error_str!r}")


def check_result(result, case: Case, precision: float = 1e-9) -> None:
    if case.get("check_output_type"):
        assert result is not None
        return

    output = case["output"]
    if output is None:
        assert result is None
    elif isinstance(output, float):
        assert result == pytest.approx(output, abs=precision)
    else:
        assert result == output


def run(func, case: Case) -> None:
    """Runs the function with the case data and checks the result / error."""
    if case.get("error"):
        error_str = cast(str, case["error"])
        if error_str == _WRONG_FORMAT_ERROR:
            with pytest.raises(WrongDataFormatError):
                func(**case["input"])
        else:
            expected_code = _parse_error_code(error_str)
            with pytest.raises(PredictorError) as exc_info:
                func(**case["input"])
            assert exc_info.value.error_code == expected_code
    else:
        result = func(**case["input"])
        check_result(result, case)
