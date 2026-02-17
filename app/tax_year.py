"""UK Tax Year logic.

UK tax year runs from 6 April to 5 April of the following year.
Label format: 'YYYY-YYYY' e.g. '2026-2027' means 6 Apr 2026 – 5 Apr 2027.
"""
import datetime
from typing import Tuple, List


def tax_year_label(date: datetime.date) -> str:
    """Return UK tax year label for a given date.

    Examples:
        2026-04-06 -> '2026-2027'
        2026-04-05 -> '2025-2026'
        2026-03-26 -> '2025-2026'
        2027-01-01 -> '2026-2027'
    """
    year = date.year
    boundary = datetime.date(year, 4, 6)
    if date >= boundary:
        return f"{year}-{year + 1}"
    else:
        return f"{year - 1}-{year}"


def _parse_label(label: str) -> Tuple[int, int]:
    """Parse 'YYYY-YYYY' into (start_year, end_year)."""
    parts = label.split("-")
    if len(parts) != 2:
        raise ValueError(f"Invalid tax year label: {label!r}")
    start_year = int(parts[0])
    end_year = int(parts[1])
    if end_year != start_year + 1:
        raise ValueError(
            f"Invalid tax year label: {label!r} — end year must be start + 1"
        )
    return start_year, end_year


def next_tax_year(label: str) -> str:
    """Increment tax year label by 1.  '2026-2027' -> '2027-2028'."""
    start, _ = _parse_label(label)
    return f"{start + 1}-{start + 2}"


def prev_tax_year(label: str) -> str:
    """Decrement tax year label by 1.  '2027-2028' -> '2026-2027'."""
    start, _ = _parse_label(label)
    return f"{start - 1}-{start}"


def tax_year_start(label: str) -> datetime.date:
    """Return start date (6 April) of the given tax year."""
    start, _ = _parse_label(label)
    return datetime.date(start, 4, 6)


def tax_year_end(label: str) -> datetime.date:
    """Return end date (5 April of the following year) of the given tax year."""
    _, end = _parse_label(label)
    return datetime.date(end, 4, 5)


def tax_year_range(label: str) -> Tuple[datetime.date, datetime.date]:
    """Return (start, end) dates for the tax year."""
    return tax_year_start(label), tax_year_end(label)


def all_tax_years_between(start_label: str, end_label: str) -> List[str]:
    """Return list of tax year labels from start_label to end_label inclusive."""
    s_start, _ = _parse_label(start_label)
    e_start, _ = _parse_label(end_label)
    if e_start < s_start:
        return []
    result = []
    current = s_start
    while current <= e_start:
        result.append(f"{current}-{current + 1}")
        current += 1
    return result


def current_tax_year() -> str:
    """Return the tax year label for today."""
    return tax_year_label(datetime.date.today())


def days_remaining_in_tax_year(label: str, from_date: datetime.date | None = None) -> int:
    """Return number of days remaining in the tax year from from_date (default today)."""
    if from_date is None:
        from_date = datetime.date.today()
    end = tax_year_end(label)
    delta = (end - from_date).days
    return max(delta, 0)


def total_days_in_tax_year(label: str) -> int:
    """Return total number of days in the tax year (365 or 366)."""
    start, end = tax_year_range(label)
    return (end - start).days + 1
