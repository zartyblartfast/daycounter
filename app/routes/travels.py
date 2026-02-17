"""Travel CRUD routes."""
import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash

from app.models import db, Travel
from app.tax_year import (
    current_tax_year,
    tax_year_label,
    tax_year_range,
    all_tax_years_between,
)

travels_bp = Blueprint("travels", __name__)


def _get_available_tax_years():
    """Get list of tax years that have travel data, plus current."""
    travels = Travel.query.order_by(Travel.arrival_date).all()
    years = set()
    years.add(current_tax_year())
    for t in travels:
        years.add(tax_year_label(t.arrival_date))
        if t.return_date:
            years.add(tax_year_label(t.return_date))
    return sorted(years)


@travels_bp.route("/")
def list_travels():
    """List all travel records with optional tax year filter."""
    filter_ty = request.args.get("tax_year", "")
    available_years = _get_available_tax_years()

    query = Travel.query.order_by(Travel.arrival_date.desc())

    if filter_ty:
        try:
            start, end = tax_year_range(filter_ty)
            query = query.filter(
                Travel.arrival_date >= start,
                Travel.arrival_date <= end,
            )
        except ValueError:
            flash(f"Invalid tax year filter: {filter_ty}", "warning")

    travels = query.all()

    return render_template(
        "travels.html",
        travels=travels,
        filter_ty=filter_ty,
        available_years=available_years,
    )


@travels_bp.route("/add", methods=["GET", "POST"])
def add_travel():
    """Add a new travel record."""
    if request.method == "POST":
        try:
            travel = Travel(
                departure_date=datetime.date.fromisoformat(
                    request.form["departure_date"]
                ),
                arrival_date=datetime.date.fromisoformat(
                    request.form["arrival_date"]
                ),
                destination_country=request.form["destination_country"].strip(),
                is_uk="is_uk" in request.form,
                return_date=(
                    datetime.date.fromisoformat(request.form["return_date"])
                    if request.form.get("return_date")
                    else None
                ),
                notes=request.form.get("notes", "").strip() or None,
            )
            db.session.add(travel)
            db.session.commit()
            flash("Travel record added successfully.", "success")
            return redirect(url_for("travels.list_travels"))
        except (ValueError, KeyError) as e:
            flash(f"Error adding travel: {e}", "danger")

    return render_template("travel_form.html", travel=None, action="Add")


@travels_bp.route("/edit/<int:travel_id>", methods=["GET", "POST"])
def edit_travel(travel_id):
    """Edit an existing travel record."""
    travel = db.session.get(Travel, travel_id)
    if not travel:
        flash("Travel record not found.", "danger")
        return redirect(url_for("travels.list_travels"))

    if request.method == "POST":
        try:
            travel.departure_date = datetime.date.fromisoformat(
                request.form["departure_date"]
            )
            travel.arrival_date = datetime.date.fromisoformat(
                request.form["arrival_date"]
            )
            travel.destination_country = request.form[
                "destination_country"
            ].strip()
            travel.is_uk = "is_uk" in request.form
            travel.return_date = (
                datetime.date.fromisoformat(request.form["return_date"])
                if request.form.get("return_date")
                else None
            )
            travel.notes = request.form.get("notes", "").strip() or None
            db.session.commit()
            flash("Travel record updated successfully.", "success")
            return redirect(url_for("travels.list_travels"))
        except (ValueError, KeyError) as e:
            flash(f"Error updating travel: {e}", "danger")

    return render_template("travel_form.html", travel=travel, action="Edit")


@travels_bp.route("/delete/<int:travel_id>", methods=["POST"])
def delete_travel(travel_id):
    """Delete a travel record."""
    travel = db.session.get(Travel, travel_id)
    if not travel:
        flash("Travel record not found.", "danger")
    else:
        db.session.delete(travel)
        db.session.commit()
        flash("Travel record deleted.", "success")
    return redirect(url_for("travels.list_travels"))
