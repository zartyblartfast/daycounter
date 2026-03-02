"""Settings route — edit application configuration."""
import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash

from app.config_manager import get_config, update_config, reset_config

settings_bp = Blueprint("settings", __name__)


@settings_bp.route("/", methods=["GET"])
def settings_page():
    """Render the settings page."""
    config = get_config()
    return render_template("settings.html", config=config)


@settings_bp.route("/save", methods=["POST"])
def save_settings():
    """Save updated settings."""
    try:
        departure_date = request.form.get("departure_date", "").strip()
        first_full = request.form.get("first_full_nonresident_tax_year", "").strip()

        # Validate departure date
        if departure_date:
            datetime.date.fromisoformat(departure_date)

        # Validate tax year format
        if first_full:
            parts = first_full.split("-")
            if len(parts) != 2 or int(parts[1]) != int(parts[0]) + 1:
                raise ValueError(f"Invalid tax year format: {first_full}")

        new_data = {}
        if departure_date:
            new_data["departure_date"] = departure_date
        if first_full:
            new_data["first_full_nonresident_tax_year"] = first_full

        update_config(new_data)
        flash("Settings saved successfully.", "success")
    except (ValueError, KeyError) as e:
        flash(f"Error saving settings: {e}", "danger")

    return redirect(url_for("settings.settings_page"))


@settings_bp.route("/reset", methods=["POST"])
def reset_settings():
    """Reset settings to defaults."""
    reset_config()
    flash("Settings reset to defaults.", "info")
    return redirect(url_for("settings.settings_page"))
