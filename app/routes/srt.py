"""SRT (Statutory Residency Test) route — residency profile configuration."""
from flask import Blueprint, render_template, request, redirect, url_for, flash

from app.config_manager import get_config, update_config

srt_bp = Blueprint("srt", __name__)


@srt_bp.route("/", methods=["GET"])
def srt_page():
    """Render the SRT configuration page."""
    config = get_config()
    return render_template("srt.html", config=config)


@srt_bp.route("/", methods=["POST"])
def save_srt():
    """Save updated SRT profile values."""
    try:
        profiles = {}
        for key in ["year_1", "year_2", "year_3_plus"]:
            target = request.form.get(f"{key}_target", "").strip()
            limit = request.form.get(f"{key}_limit", "").strip()
            buffer = request.form.get(f"{key}_buffer", "").strip()
            if target and limit and buffer:
                t = int(target)
                l = int(limit)
                b = int(buffer)
                if t < 0 or l < 0 or b < 0:
                    raise ValueError(f"Values for {key} must be non-negative.")
                if t > 366 or l > 366:
                    raise ValueError(f"Midnight values for {key} cannot exceed 366.")
                if b > 50:
                    raise ValueError(f"Buffer for {key} cannot exceed 50.")
                profiles[key] = {
                    "target_midnights": t,
                    "stat_limit_midnights": l,
                    "buffer": b,
                }
            else:
                raise ValueError(f"All fields are required for {key}.")

        update_config({"profiles": profiles})
        flash("SRT profile settings saved successfully.", "success")
    except (ValueError, KeyError) as e:
        flash(f"Error saving SRT settings: {e}", "danger")

    return redirect(url_for("srt.srt_page"))
