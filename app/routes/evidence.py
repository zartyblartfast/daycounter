"""Evidence vault routes — upload, list, download evidence files."""
import hashlib
import os
import uuid
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    current_app,
    send_from_directory,
)

from app.models import db, EvidenceFile, Travel, EVIDENCE_CATEGORIES
from app.tax_year import current_tax_year
from app.routes.heatmap import _get_available_tax_years

evidence_bp = Blueprint("evidence", __name__)


def _compute_file_hash(file_storage) -> str:
    """Compute SHA-256 hash of an uploaded file."""
    sha256 = hashlib.sha256()
    file_storage.seek(0)
    for chunk in iter(lambda: file_storage.read(8192), b""):
        sha256.update(chunk)
    file_storage.seek(0)
    return sha256.hexdigest()


@evidence_bp.route("/")
def list_evidence():
    """List all evidence files with optional filters."""
    filter_category = request.args.get("category", "")
    filter_ty = request.args.get("tax_year", "")
    filter_travel = request.args.get("travel_id", "")

    query = EvidenceFile.query.order_by(EvidenceFile.uploaded_at.desc())

    if filter_category:
        query = query.filter(EvidenceFile.category == filter_category)
    if filter_ty:
        query = query.filter(EvidenceFile.tax_year == filter_ty)
    if filter_travel:
        query = query.filter(EvidenceFile.travel_id == int(filter_travel))

    files = query.all()
    travels = Travel.query.order_by(Travel.arrival_date.desc()).all()

    tax_years = _get_available_tax_years()

    return render_template(
        "evidence.html",
        files=files,
        tax_years=tax_years,
        categories=EVIDENCE_CATEGORIES,
        travels=travels,
        filter_category=filter_category,
        filter_ty=filter_ty,
        filter_travel=filter_travel,
    )


@evidence_bp.route("/upload", methods=["POST"])
def upload_evidence():
    """Upload one or more evidence files."""
    if "file" not in request.files:
        flash("No file selected.", "warning")
        return redirect(url_for("evidence.list_evidence"))

    uploaded_files = request.files.getlist("file")
    category = request.form.get("category", "other")
    tags = request.form.get("tags", "").strip()
    tax_year = request.form.get("tax_year", "").strip() or current_tax_year()
    travel_id = request.form.get("travel_id", "").strip()
    travel_id = int(travel_id) if travel_id else None

    vault_path = current_app.config["VAULT_PATH"]
    os.makedirs(vault_path, exist_ok=True)

    count = 0
    for f in uploaded_files:
        if f.filename == "":
            continue

        original_filename = f.filename
        file_hash = _compute_file_hash(f)

        # Generate unique filename preserving extension
        ext = os.path.splitext(original_filename)[1]
        stored_filename = f"{uuid.uuid4().hex}{ext}"

        # Save file
        filepath = os.path.join(vault_path, stored_filename)
        f.save(filepath)

        # Create DB record
        evidence = EvidenceFile(
            travel_id=travel_id,
            filename=stored_filename,
            original_filename=original_filename,
            file_hash=file_hash,
            category=category,
            tags=tags,
            tax_year=tax_year,
        )
        db.session.add(evidence)
        count += 1

    db.session.commit()
    flash(f"{count} file(s) uploaded successfully.", "success")
    return redirect(url_for("evidence.list_evidence"))


@evidence_bp.route("/download/<int:file_id>")
def download_evidence(file_id):
    """Download an evidence file."""
    evidence = db.session.get(EvidenceFile, file_id)
    if not evidence:
        flash("File not found.", "danger")
        return redirect(url_for("evidence.list_evidence"))

    vault_path = current_app.config["VAULT_PATH"]
    return send_from_directory(
        vault_path,
        evidence.filename,
        as_attachment=True,
        download_name=evidence.original_filename,
    )


@evidence_bp.route("/delete/<int:file_id>", methods=["POST"])
def delete_evidence(file_id):
    """Delete an evidence file."""
    evidence = db.session.get(EvidenceFile, file_id)
    if not evidence:
        flash("File not found.", "danger")
    else:
        # Remove physical file
        vault_path = current_app.config["VAULT_PATH"]
        filepath = os.path.join(vault_path, evidence.filename)
        if os.path.exists(filepath):
            os.remove(filepath)
        db.session.delete(evidence)
        db.session.commit()
        flash("Evidence file deleted.", "success")
    return redirect(url_for("evidence.list_evidence"))
