"""Reports route — generate annual residency statements."""
import datetime
import hashlib
import os
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    current_app,
    send_from_directory,
    make_response,
)

from app.models import db, Travel, EvidenceFile, AnnualStatement
from app.config_manager import get_config
from app.tax_year import (
    current_tax_year,
    tax_year_range,
    all_tax_years_between,
    _parse_label,
)
from app.profiles import get_profile_for_tax_year, compute_risk_status, risk_badge_class
from app.uk_midnights import compute_uk_midnights_for_tax_year

reports_bp = Blueprint("reports", __name__)


def _get_available_tax_years():
    """Get list of tax years with data."""
    from app.tax_year import tax_year_label as ty_label
    travels = Travel.query.order_by(Travel.arrival_date).all()
    years = set()
    years.add(current_tax_year())
    for t in travels:
        years.add(ty_label(t.arrival_date))
        if t.return_date:
            years.add(ty_label(t.return_date))
    return sorted(years)


def _generate_statement_html(tax_year_label_str: str) -> str:
    """Generate the HTML content for an annual statement."""
    config = get_config()
    start, end = tax_year_range(tax_year_label_str)

    travels = Travel.query.order_by(Travel.arrival_date).all()
    midnight_data = compute_uk_midnights_for_tax_year(tax_year_label_str, travels)

    profile = get_profile_for_tax_year(tax_year_label_str, config)
    risk_status = "N/A"
    if profile:
        risk_status = compute_risk_status(midnight_data["total"], profile)

    # UK stays within this tax year
    uk_stays = (
        Travel.query.filter(
            Travel.is_uk == True,
            Travel.arrival_date >= start,
            Travel.arrival_date <= end,
        )
        .order_by(Travel.arrival_date)
        .all()
    )

    # Evidence for this tax year
    evidence_files = (
        EvidenceFile.query.filter(EvidenceFile.tax_year == tax_year_label_str)
        .order_by(EvidenceFile.category, EvidenceFile.uploaded_at)
        .all()
    )

    # Group evidence by category
    evidence_by_cat = {}
    for ef in evidence_files:
        cat = ef.category or "other"
        if cat not in evidence_by_cat:
            evidence_by_cat[cat] = []
        evidence_by_cat[cat].append(ef)

    now = datetime.datetime.utcnow()

    html = render_template(
        "_statement.html",
        tax_year=tax_year_label_str,
        start=start,
        end=end,
        midnight_data=midnight_data,
        profile=profile,
        risk_status=risk_status,
        uk_stays=uk_stays,
        evidence_files=evidence_files,
        evidence_by_cat=evidence_by_cat,
        generated_at=now,
        config=config,
    )
    return html


@reports_bp.route("/")
def list_reports():
    """List generated reports and provide generation form."""
    statements = AnnualStatement.query.order_by(
        AnnualStatement.generated_at.desc()
    ).all()
    available_years = _get_available_tax_years()

    return render_template(
        "reports.html",
        statements=statements,
        available_years=available_years,
    )


@reports_bp.route("/generate", methods=["POST"])
def generate_report():
    """Generate an annual statement for the selected tax year."""
    tax_year_label_str = request.form.get("tax_year", current_tax_year())

    try:
        html_content = _generate_statement_html(tax_year_label_str)
    except Exception as e:
        flash(f"Error generating report: {e}", "danger")
        return redirect(url_for("reports.list_reports"))

    # Save HTML report
    vault_path = current_app.config["VAULT_PATH"]
    reports_dir = os.path.join(vault_path, "reports")
    os.makedirs(reports_dir, exist_ok=True)

    timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"statement_{tax_year_label_str}_{timestamp}.html"
    filepath = os.path.join(reports_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)

    # Compute hash
    file_hash = hashlib.sha256(html_content.encode("utf-8")).hexdigest()

    # Try PDF generation
    pdf_filename = None
    try:
        from weasyprint import HTML
        pdf_filename = f"statement_{tax_year_label_str}_{timestamp}.pdf"
        pdf_path = os.path.join(reports_dir, pdf_filename)
        HTML(string=html_content).write_pdf(pdf_path)
    except ImportError:
        pass  # WeasyPrint not available, HTML only
    except Exception:
        pass  # PDF generation failed, continue with HTML

    # Save record
    statement = AnnualStatement(
        tax_year=tax_year_label_str,
        filename=filename,
        file_hash=file_hash,
    )
    db.session.add(statement)
    db.session.commit()

    msg = f"Statement generated for {tax_year_label_str}."
    if pdf_filename:
        msg += " PDF version also created."
    flash(msg, "success")
    return redirect(url_for("reports.list_reports"))


@reports_bp.route("/view/<int:statement_id>")
def view_report(statement_id):
    """View a generated statement in the browser."""
    statement = db.session.get(AnnualStatement, statement_id)
    if not statement:
        flash("Statement not found.", "danger")
        return redirect(url_for("reports.list_reports"))

    vault_path = current_app.config["VAULT_PATH"]
    reports_dir = os.path.join(vault_path, "reports")
    filepath = os.path.join(reports_dir, statement.filename)

    if not os.path.exists(filepath):
        flash("Statement file not found on disk.", "danger")
        return redirect(url_for("reports.list_reports"))

    with open(filepath, "r", encoding="utf-8") as f:
        html_content = f.read()

    return html_content


@reports_bp.route("/download/<int:statement_id>")
def download_report(statement_id):
    """Download a generated statement."""
    statement = db.session.get(AnnualStatement, statement_id)
    if not statement:
        flash("Statement not found.", "danger")
        return redirect(url_for("reports.list_reports"))

    vault_path = current_app.config["VAULT_PATH"]
    reports_dir = os.path.join(vault_path, "reports")

    # Try PDF first
    pdf_name = statement.filename.replace(".html", ".pdf")
    pdf_path = os.path.join(reports_dir, pdf_name)
    if os.path.exists(pdf_path):
        return send_from_directory(
            reports_dir, pdf_name, as_attachment=True
        )

    return send_from_directory(
        reports_dir, statement.filename, as_attachment=True
    )


@reports_bp.route("/delete/<int:statement_id>", methods=["POST"])
def delete_report(statement_id):
    """Delete a generated statement."""
    statement = db.session.get(AnnualStatement, statement_id)
    if not statement:
        flash("Statement not found.", "danger")
    else:
        vault_path = current_app.config["VAULT_PATH"]
        reports_dir = os.path.join(vault_path, "reports")
        # Remove files
        for ext in [".html", ".pdf"]:
            fname = statement.filename.replace(".html", ext)
            fpath = os.path.join(reports_dir, fname)
            if os.path.exists(fpath):
                os.remove(fpath)
        db.session.delete(statement)
        db.session.commit()
        flash("Statement deleted.", "success")
    return redirect(url_for("reports.list_reports"))
