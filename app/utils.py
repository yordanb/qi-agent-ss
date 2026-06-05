"""Utility functions for cleaning Excel data."""

import re
from datetime import date, datetime


def clean_text(val) -> str:
    """Clean whitespace from a value."""
    if val is None or val == "":
        return ""
    s = str(val).strip()
    s = re.sub(r"[\t\n\r]+", " ", s)
    s = re.sub(r"\s{2,}", " ", s)
    return s.strip()


def parse_date(val) -> date | None:
    """Parse DD/MM/YYYY string or datetime to date."""
    if val is None or val == "":
        return None
    s = str(val).strip()
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", s)
    if m:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        pass
    return None


def parse_num(val) -> float | None:
    """Parse numeric value, return None if empty."""
    if val is None or val == "":
        return None
    if isinstance(val, (int, float)):
        return float(val)
    cleaned = re.sub(r"[^0-9.\-]", "", str(val))
    try:
        return float(cleaned)
    except ValueError:
        return None


ALLOWED_DEPT = ["SPL2", "STYR"]
