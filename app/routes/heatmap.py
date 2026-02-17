"""Heatmap route — visual calendar of UK presence."""
import datetime
import calendar
from flask import Blueprint, render_template, request

from app.config_manager import get_config
from app.models import Travel, EvidenceFile
from app.tax_year import (
    current_tax_year,
    tax_year_range,
    tax_year_start,
    tax_year_end,
    all_tax_years_between,
    _parse_label,
)
from app.profiles import get_profile_for_tax_year, compute_risk_status, risk_badge_class
from app.uk_midnights import compute_uk_midnights_for_tax_year, compute_country_breakdown

heatmap_bp = Blueprint("heatmap", __name__)


def _build_calendar_data(tax_year_label_str: str, day_status: dict, day_details: dict):
    """Build month-by-month calendar grid data for the heatmap.

    Returns list of dicts, one per month in the tax year:
    [
        {
            'year': 2026, 'month': 4, 'name': 'April 2026',
            'weeks': [  # list of weeks, each week is list of 7 day-cells
                [None, None, ..., {'date': date, 'day': 6, 'status': 'uk', ...}, ...],
                ...
            ]
        },
        ...
    ]
    """
    start, end = tax_year_range(tax_year_label_str)

    # Tax year spans April YYYY to April YYYY+1
    # Months: Apr, May, Jun, Jul, Aug, Sep, Oct, Nov, Dec, Jan, Feb, Mar, (Apr 1-5)
    months = []
    current_date = start
    while current_date <= end:
        y, m = current_date.year, current_date.month
        # Determine first and last day of this month within the tax year
        month_start = max(datetime.date(y, m, 1), start)
        last_day = calendar.monthrange(y, m)[1]
        month_end = min(datetime.date(y, m, last_day), end)

        month_name = f"{calendar.month_name[m]} {y}"
        # Build weeks grid
        # Start from the 1st of the month for proper alignment
        first_weekday = datetime.date(y, m, 1).weekday()  # 0=Mon
        weeks = []
        week = [None] * first_weekday

        for day_num in range(1, last_day + 1):
            d = datetime.date(y, m, day_num)
            if start <= d <= end:
                status = day_status.get(d, "out_of_range")
                detail = day_details.get(d, {})
                cell = {
                    "date": d,
                    "day": day_num,
                    "status": status,
                    "destination": detail.get("destination", ""),
                    "travel_id": detail.get("travel_id"),
                }
            else:
                cell = {
                    "date": d,
                    "day": day_num,
                    "status": "out_of_range",
                    "destination": "",
                    "travel_id": None,
                }
            week.append(cell)
            if len(week) == 7:
                weeks.append(week)
                week = []

        if week:
            week.extend([None] * (7 - len(week)))
            weeks.append(week)

        months.append({
            "year": y,
            "month": m,
            "name": month_name,
            "weeks": weeks,
        })

        # Move to next month
        if m == 12:
            current_date = datetime.date(y + 1, 1, 1)
        else:
            current_date = datetime.date(y, m + 1, 1)

    return months


def _get_available_tax_years():
    """Get list of tax years with data plus current."""
    from app.tax_year import tax_year_label as ty_label
    travels = Travel.query.order_by(Travel.arrival_date).all()
    years = set()
    years.add(current_tax_year())
    for t in travels:
        years.add(ty_label(t.arrival_date))
        if t.return_date:
            years.add(ty_label(t.return_date))
    return sorted(years)


@heatmap_bp.route("/")
def heatmap_view():
    """Render the heatmap page."""
    config = get_config()
    selected_ty = request.args.get("tax_year", current_tax_year())
    available_years = _get_available_tax_years()

    # Get travels and compute midnights
    travels = Travel.query.order_by(Travel.arrival_date).all()
    midnight_data = compute_uk_midnights_for_tax_year(selected_ty, travels)

    # Profile and risk
    profile = get_profile_for_tax_year(selected_ty, config)
    risk_status = "N/A"
    badge_class = "bg-secondary"
    if profile:
        risk_status = compute_risk_status(midnight_data["total"], profile)
        badge_class = risk_badge_class(risk_status)

    # Evidence counts per date
    evidence_counts = {}
    for t in travels:
        if t.evidence_files:
            if t.arrival_date and t.return_date:
                d = t.arrival_date
                while d < t.return_date:
                    evidence_counts[d] = evidence_counts.get(d, 0) + len(
                        t.evidence_files
                    )
                    d += datetime.timedelta(days=1)

    # Per-country breakdown
    country_breakdown = compute_country_breakdown(midnight_data["day_details"])

    # Build calendar grid
    calendar_data = _build_calendar_data(
        selected_ty, midnight_data["day_status"], midnight_data["day_details"]
    )

    return render_template(
        "heatmap.html",
        tax_year=selected_ty,
        available_years=available_years,
        calendar_data=calendar_data,
        midnight_data=midnight_data,
        profile=profile,
        risk_status=risk_status,
        badge_class=badge_class,
        evidence_counts=evidence_counts,
        country_breakdown=country_breakdown,
    )
