"""JSON API endpoints for programmatic access."""
import datetime
from flask import Blueprint, jsonify, request

from app.config_manager import get_config
from app.models import db, Travel, EvidenceFile
from app.tax_year import (
    current_tax_year,
    tax_year_range,
    days_remaining_in_tax_year,
    total_days_in_tax_year,
    tax_year_label,
)
from app.profiles import get_profile_for_tax_year, compute_risk_status
from app.uk_midnights import compute_uk_midnights_for_tax_year

api_bp = Blueprint("api", __name__)


@api_bp.route("/status")
def api_status():
    """Get current tax year status summary."""
    config = get_config()
    ty = request.args.get("tax_year", current_tax_year())

    travels = Travel.query.order_by(Travel.arrival_date).all()
    midnight_data = compute_uk_midnights_for_tax_year(ty, travels)

    profile = get_profile_for_tax_year(ty, config)
    risk_status = "N/A"
    profile_info = None
    if profile:
        risk_status = compute_risk_status(midnight_data["total"], profile)
        profile_info = {
            "name": profile.name,
            "display_name": profile.display_name,
            "target_midnights": profile.target_midnights,
            "stat_limit_midnights": profile.stat_limit_midnights,
            "buffer": profile.buffer,
        }

    return jsonify({
        "tax_year": ty,
        "midnights_used": midnight_data["total"],
        "profile": profile_info,
        "risk_status": risk_status,
        "days_remaining": days_remaining_in_tax_year(ty),
        "total_days": total_days_in_tax_year(ty),
    })


@api_bp.route("/midnights")
def api_midnights():
    """Get UK midnight dates for a tax year."""
    ty = request.args.get("tax_year", current_tax_year())
    travels = Travel.query.order_by(Travel.arrival_date).all()
    midnight_data = compute_uk_midnights_for_tax_year(ty, travels)

    return jsonify({
        "tax_year": ty,
        "total": midnight_data["total"],
        "dates": [d.isoformat() for d in midnight_data["uk_midnight_dates"]],
    })


@api_bp.route("/travels")
def api_travels():
    """Get all travel records as JSON."""
    filter_ty = request.args.get("tax_year", "")
    query = Travel.query.order_by(Travel.arrival_date.desc())

    if filter_ty:
        try:
            start, end = tax_year_range(filter_ty)
            query = query.filter(
                Travel.arrival_date >= start,
                Travel.arrival_date <= end,
            )
        except ValueError:
            pass

    travels = query.all()
    result = []
    for t in travels:
        result.append({
            "id": t.id,
            "departure_date": t.departure_date.isoformat(),
            "arrival_date": t.arrival_date.isoformat(),
            "destination_country": t.destination_country,
            "is_uk": t.is_uk,
            "return_date": t.return_date.isoformat() if t.return_date else None,
            "notes": t.notes,
            "evidence_count": len(t.evidence_files),
        })

    return jsonify({"travels": result})


@api_bp.route("/heatmap")
def api_heatmap():
    """Get day-by-day status for heatmap rendering."""
    ty = request.args.get("tax_year", current_tax_year())
    travels = Travel.query.order_by(Travel.arrival_date).all()
    midnight_data = compute_uk_midnights_for_tax_year(ty, travels)

    day_data = {}
    for date, status in midnight_data["day_status"].items():
        detail = midnight_data["day_details"].get(date, {})
        day_data[date.isoformat()] = {
            "status": status,
            "destination": detail.get("destination", ""),
            "travel_id": detail.get("travel_id"),
        }

    return jsonify({
        "tax_year": ty,
        "total_uk_midnights": midnight_data["total"],
        "days": day_data,
    })


@api_bp.route("/config")
def api_config():
    """Get current configuration."""
    config = get_config()
    return jsonify(config)
