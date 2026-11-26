"""Low-level helpers for value validation and date parsing."""
import math
import re
from typing import Any
from datetime import datetime, timedelta, timezone
from dateutil import parser as dateutil_parser
import polars as pl

from rtb_sdk.schemas import Granularity
from rtb_sdk.constants.frequencies_consts import GRAN_TO_TIMEDELTA


# ─── Validation primitives ─────────────────────────────────────────────────────

def is_in_class(cls, value) -> bool:
    return value in cls.__dict__.values()


def _is_valid_datetime_value(value: Any) -> bool:
    return isinstance(value, datetime)


def _is_valid_numeric_value(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _is_valid_datetime_list(value: Any) -> bool:
    return isinstance(value, list) and all(_is_valid_datetime_value(item) for item in value)


def _is_valid_numeric_list(value: Any) -> bool:
    return isinstance(value, list) and all(_is_valid_numeric_value(item) for item in value)


def _dates_match_resolution(prev_date: datetime,
                            next_date: datetime,
                            resolution: Granularity) -> bool:
    """Checks that adjacent dates go strictly with the resolution step.

    For a month the range 28..31 days is taken, to cover calendar irregularity.
    """
    try:
        if next_date <= prev_date:
            return False
        if resolution == 'm':
            delta_days = (next_date - prev_date).days
            return 28 <= delta_days <= 31
        expected = GRAN_TO_TIMEDELTA.get(resolution)
        return isinstance(expected, timedelta) and (next_date - prev_date) == expected
    except Exception:
        return False


def _is_valid_datetime_sequence(dates: list[datetime],
                                resolution: Granularity) -> bool:
    if len(dates) < 2:
        return True
    return all(
        _dates_match_resolution(dates[i - 1], dates[i], resolution)
        for i in range(1, len(dates))
    )


# ─── Datetime parsing ──────────────────────────────────────────────────────────

_YEAR_FIRST_PREFIX = re.compile(r"^\d{4}\D")


def _parse_string_datetime(value: Any) -> datetime | None:
    """Universal date-string parser via `dateutil.parser.parse`.

    Determines separators (`-`, `/`, `.`, `T`, space), time zones (`Z`,
    `+03:00`) and the presence of time on its own, without hardcoded masks. A 4-digit prefix
    is recognized as year-first; otherwise `dayfirst=True` is enabled for the
    European format `%d.%m.%Y`. The time zone is normalized to UTC and
    dropped — Predictor works with naive dates.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo is not None else value
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    dayfirst = _YEAR_FIRST_PREFIX.match(text) is None
    try:
        parsed = dateutil_parser.parse(text, dayfirst=dayfirst)
    except (ValueError, TypeError, OverflowError):
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _parse_polars_datetime_column(df: pl.DataFrame,
                                  date_column: str) -> pl.Expr:
    """Returns an expression that casts the date column to a `pl.Datetime` without a time zone.

    For native polars types (`Datetime`/`Date`) — a direct cast. String
    data is parsed via `_parse_string_datetime`, which determines the
    format on its own — no pre-listed masks.
    """
    dtype = df.schema[date_column]
    if dtype == pl.Datetime:
        return pl.col(date_column).dt.replace_time_zone(None)
    if dtype == pl.Date:
        return pl.col(date_column).cast(pl.Datetime)

    return (
        pl.col(date_column)
        .cast(pl.String)
        .map_elements(_parse_string_datetime, return_dtype=pl.Datetime)
    )