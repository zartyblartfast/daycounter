"""Operational profile mapping for UK tax residency.

Maps tax years to profile classes (Year 1, Year 2, Year 3+) based on
the first full non-resident tax year, and computes risk status.
"""
from dataclasses import dataclass
from typing import Optional

from app.tax_year import next_tax_year, _parse_label


@dataclass
class Profile:
    name: str            # 'year_1', 'year_2', 'year_3_plus'
    display_name: str    # 'Year 1', 'Year 2', 'Year 3+'
    target_midnights: int
    stat_limit_midnights: int
    buffer: int


DEFAULT_PROFILES = {
    "year_1": {
        "target_midnights": 30,
        "stat_limit_midnights": 90,
        "buffer": 5,
    },
    "year_2": {
        "target_midnights": 85,
        "stat_limit_midnights": 90,
        "buffer": 5,
    },
    "year_3_plus": {
        "target_midnights": 120,
        "stat_limit_midnights": 120,
        "buffer": 5,
    },
}

PROFILE_DISPLAY = {
    "year_1": "Year 1",
    "year_2": "Year 2",
    "year_3_plus": "Year 3+",
}


def get_profile_for_tax_year(
    tax_year_label: str, config: dict
) -> Optional[Profile]:
    """Determine which profile applies to a given tax year.

    Args:
        tax_year_label: e.g. '2026-2027'
        config: dict containing 'first_full_nonresident_tax_year' and 'profiles'

    Returns:
        Profile dataclass or None if tax year is before first full non-resident year.

    Mapping:
        - tax_year == first_full -> year_1
        - tax_year == next(first_full) -> year_2
        - tax_year >= next(next(first_full)) -> year_3_plus
        - tax_year < first_full -> None (pre-departure)
    """
    first_full = config.get("first_full_nonresident_tax_year", "")
    if not first_full:
        return None

    profiles_cfg = config.get("profiles", DEFAULT_PROFILES)

    ty_start, _ = _parse_label(tax_year_label)
    ff_start, _ = _parse_label(first_full)

    offset = ty_start - ff_start

    if offset < 0:
        return None  # pre-departure
    elif offset == 0:
        profile_key = "year_1"
    elif offset == 1:
        profile_key = "year_2"
    else:
        profile_key = "year_3_plus"

    p = profiles_cfg.get(profile_key, DEFAULT_PROFILES[profile_key])
    return Profile(
        name=profile_key,
        display_name=PROFILE_DISPLAY[profile_key],
        target_midnights=p["target_midnights"],
        stat_limit_midnights=p["stat_limit_midnights"],
        buffer=p["buffer"],
    )


def compute_risk_status(midnights_used: int, profile: Profile) -> str:
    """Compute risk status based on midnights used vs profile targets.

    RED:    used >= target
    AMBER:  target - buffer < used < target
    GREEN:  used <= target - buffer

    RED is checked first so that when buffer == 0 the boundary
    value (used == target) is correctly classified as RED.
    """
    if midnights_used >= profile.target_midnights:
        return "RED"
    safe_threshold = profile.target_midnights - profile.buffer
    if midnights_used > safe_threshold:
        return "AMBER"
    return "GREEN"


def risk_badge_class(status: str) -> str:
    """Return Bootstrap badge CSS class for risk status."""
    return {
        "GREEN": "bg-success",
        "AMBER": "bg-warning text-dark",
        "RED": "bg-danger",
    }.get(status, "bg-secondary")
