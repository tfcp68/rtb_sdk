"""
Constants for the tests: paths, error mappings and special values.
"""

from pathlib import Path

from rtb_sdk.errors import ErrorCodes
from rtb_sdk.constants import INT_INFINITY

_DATE_FIELDS = {"start_date", "end_date"}

# --- Paths ---

TESTS_DIR = Path(__file__).parent / "auction"
CASES_DIR = TESTS_DIR / "cases"


# --- Automatically collected mapping of error codes from the fields of the ErrorCodes class ---

_ERROR_CODE_MAP: dict[str, int] = {
    name: value
    for name, value in vars(ErrorCodes).items()
    if not name.startswith("_")
}


# --- Special values used in the cases' output ---

_SPECIAL_VALUES: dict[str, object] = {
    "INT_INFINITY": INT_INFINITY,
}
