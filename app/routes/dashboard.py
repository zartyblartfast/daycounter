"""Dashboard route — main landing page."""
import datetime
from flask import Blueprint, render_template

from app.config_manager import get_config
from app.models import db, Travel
from app.tax_year import (
    current_tax_year,
    tax_year_range,
    days_remaining_in_tax_year,
    total_days_in_tax_year,
    next_tax_year,
    _parse_label,
)
from app.profiles import get_profile_for_tax_year, compute_risk_status, risk_badge_class
from app.uk_midnights import (
    compute_uk_midnights_for_tax_year,
    compute_country_breakdown,
    detect_overlaps,
)

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def index():
    """Render the main dashboard."""
    config = get_config()
    ty = current_tax_year()
    start, end = tax_year_range(ty)
    today = datetime.date.today()

    # Get profile for current tax year
    profile = get_profile_for_tax_year(ty, config)

    # Determine why profile might be None
    first_full = config.get("first_full_nonresident_tax_year", "")
    profiles_cfg = config.get("profiles", {})
    pre_departure = False
    if not profile and first_full and profiles_cfg:
        # Config exists but current tax year is before first full non-resident year
        try:
            ty_start, _ = _parse_label(ty)
            ff_start, _ = _parse_label(first_full)
            if ty_start < ff_start:
                pre_departure = True
        except (ValueError, TypeError):
            pass

    # Get all travels
    travels = Travel.query.order_by(Travel.arrival_date).all()

    # Compute UK midnights
    midnight_data = compute_uk_midnights_for_tax_year(ty, travels)
    midnights_used = midnight_data["total"]

    # Per-country breakdown
    country_breakdown = compute_country_breakdown(midnight_data["day_details"])

    # Overlap detection
    overlap_warnings = detect_overlaps(travels)

    # Risk status
    risk_status = "N/A"
    badge_class = "bg-secondary"
    if profile:
        risk_status = compute_risk_status(midnights_used, profile)
        badge_class = risk_badge_class(risk_status)

    # Days remaining
    days_left = days_remaining_in_tax_year(ty)
    total_days = total_days_in_tax_year(ty)
    days_elapsed = total_days - days_left

    # Progress percentages
    target_pct = 0
    limit_pct = 0
    used_pct = 0
    if profile:
        target_pct = min(
            (profile.target_midnights / profile.stat_limit_midnights) * 100, 100
        )
        used_pct = min(
            (midnights_used / profile.stat_limit_midnights) * 100, 100
        )
        limit_pct = 100

    # TNR 5-Year Clock
    tnr_data = None
    if first_full:
        ff_start, _ = _parse_label(first_full)
        completed = 0
        current_start, _ = _parse_label(ty)
        if current_start >= ff_start:
            completed = min(current_start - ff_start, 5)
            # If we are within the current tax year, check if it's complete
            if today > end:
                completed = min(completed + 1, 5)
        target_completion_year = f"{ff_start + 4}-{ff_start + 5}"
        tnr_safe_date = datetime.date(ff_start + 5, 4, 6)
        tnr_data = {
            "first_full": first_full,
            "completed": completed,
            "target_completion": target_completion_year,
            "safe_date": tnr_safe_date,
            "pct": (completed / 5) * 100,
        }

    # Next planned travel
    next_travel = (
        Travel.query.filter(Travel.arrival_date >= today)
        .order_by(Travel.arrival_date)
        .first()
    )

    # Departure info for pre-departure display
    departure_date_str = config.get("departure_date", "")
    departure_date = None
    days_to_departure = None
    if departure_date_str:
        try:
            departure_date = datetime.date.fromisoformat(departure_date_str)
            if departure_date > today:
                days_to_departure = (departure_date - today).days
        except ValueError:
            pass

    return render_template(
        "dashboard.html",
        tax_year=ty,
        start=start,
        end=end,
        today=today,
        profile=profile,
        pre_departure=pre_departure,
        first_full=first_full,
        departure_date=departure_date,
        days_to_departure=days_to_departure,
        midnights_used=midnights_used,
        risk_status=risk_status,
        badge_class=badge_class,
        days_left=days_left,
        total_days=total_days,
        days_elapsed=days_elapsed,
        target_pct=target_pct,
        used_pct=used_pct,
        limit_pct=limit_pct,
        tnr_data=tnr_data,
        next_travel=next_travel,
        config=config,
        country_breakdown=country_breakdown,
        overlap_warnings=overlap_warnings,
    )
