"""Pure helpers for extracting financial-year intent from queries."""

import re
from datetime import UTC, datetime
from typing import Any

from ..core.trace_types import YearIntentPayload
from ..core.types import YearMode


_EXPLICIT_YEAR_PATTERN = re.compile(r"(?:fy)?(20\d{2})", re.IGNORECASE)
_LAST_N_YEARS_PATTERN = re.compile(r"last\s+(\d{1,2})\s+years?", re.IGNORECASE)
_SINCE_YEAR_PATTERN = re.compile(r"since\s+(?:fy)?(20\d{2})", re.IGNORECASE)
_RECENT_TERMS = ("recent", "latest", "current")
_BROAD_HORIZON_TERMS = (
    "trend",
    "over time",
    "over the years",
    "historical",
    "year-on-year",
    "yoy",
    "since fy",
    "since 20",
    "last ",
)


def normalize_year_mode(raw_mode: Any) -> YearMode:
    mode = str(raw_mode or "none")
    if mode in {"explicit", "recent", "range", "none"}:
        return mode
    return "none"


def infer_year_intent(original_query: str, revised_query: str, *, current_year: int | None = None) -> YearIntentPayload:
    text = f"{original_query} {revised_query}".lower()
    current_year = int(current_year or datetime.now(UTC).year)
    explicit_years = sorted({int(match) for match in _EXPLICIT_YEAR_PATTERN.findall(text)})
    allow_broad_horizon = any(term in text for term in _BROAD_HORIZON_TERMS)

    range_match = _LAST_N_YEARS_PATTERN.search(text)
    if range_match:
        span = max(1, int(range_match.group(1)))
        return {
            "requested_year_mode": "range",
            "requested_years": [current_year - span + 1, current_year],
            "allow_broad_horizon": True,
        }

    since_match = _SINCE_YEAR_PATTERN.search(text)
    if since_match:
        return {
            "requested_year_mode": "range",
            "requested_years": [int(since_match.group(1)), current_year],
            "allow_broad_horizon": True,
        }

    if explicit_years:
        return {
            "requested_year_mode": "explicit",
            "requested_years": explicit_years,
            "allow_broad_horizon": allow_broad_horizon,
        }

    if any(term in text for term in _RECENT_TERMS):
        return {
            "requested_year_mode": "recent",
            "requested_years": [],
            "allow_broad_horizon": allow_broad_horizon,
        }

    return {
        "requested_year_mode": "none",
        "requested_years": [],
        "allow_broad_horizon": allow_broad_horizon,
    }
