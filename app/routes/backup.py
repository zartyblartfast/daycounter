"""Backup & Restore routes — download/upload full application state.

Includes scheduled backup support (cron-callable endpoint) and
automatic retention pruning of server-stored backups.
"""
import datetime
import io
import json
import os
import shutil
import sqlite3
import tempfile
import zipfile

from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

from app.models import db
from app.config_manager import get_config, update_config

backup_bp = Blueprint("backup", __name__)

APP_VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _db_path():
    """Resolve the SQLite database file path."""
    uri = current_app.config["SQLALCHEMY_DATABASE_URI"]
    if uri.startswith("sqlite:////"):
        return uri[len("sqlite:///"):]
    elif uri.startswith("sqlite:///"):
        return uri[len("sqlite:///"):]
    return None


def _vault_path():
    """Resolve the evidence vault directory."""
    return current_app.config.get(
        "VAULT_PATH",
        os.path.join(current_app.root_path, "..", "vault"),
    )


def _backup_dir():
    """Resolve (and create) the server backup directory."""
    d = os.path.join(current_app.root_path, "..", "backups")
    os.makedirs(d, exist_ok=True)
    return d


def _safe_db_backup(db_file, dest_file):
    """Create a consistent SQLite backup using the backup API."""
    src = sqlite3.connect(db_file)
    dst = sqlite3.connect(dest_file)
    src.backup(dst)
    dst.close()
    src.close()


def _list_vault_files(vault_dir):
    """Recursively list all files in the vault with relative paths."""
    files = []
    if os.path.isdir(vault_dir):
        for root, _dirs, filenames in os.walk(vault_dir):
            for fn in filenames:
                full = os.path.join(root, fn)
                rel = os.path.relpath(full, vault_dir)
                size = os.path.getsize(full)
                files.append({"path": rel, "size": size})
    return files


def _create_backup_zip():
    """Build a backup zip in memory and return (BytesIO, zip_name)."""
    db_file = _db_path()
    vault_dir = _vault_path()
    timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    zip_name = f"daytracker_backup_{timestamp}.zip"

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # Database
        if db_file and os.path.exists(db_file):
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
                tmp_path = tmp.name
            try:
                _safe_db_backup(db_file, tmp_path)
                zf.write(tmp_path, "data/daytracker.db")
            finally:
                os.unlink(tmp_path)

        # Vault files
        vault_files = []
        if os.path.isdir(vault_dir):
            for root, _dirs, filenames in os.walk(vault_dir):
                for fn in filenames:
                    full = os.path.join(root, fn)
                    rel = os.path.relpath(full, vault_dir)
                    zf.write(full, f"vault/{rel}")
                    vault_files.append(rel)

        # Manifest
        manifest = {
            "app": "DayTracker",
            "version": APP_VERSION,
            "created_utc": datetime.datetime.utcnow().isoformat() + "Z",
            "contents": {
                "database": "data/daytracker.db",
                "vault_files": [f"vault/{f}" for f in vault_files],
            },
            "db_size_bytes": (
                os.path.getsize(db_file)
                if db_file and os.path.exists(db_file)
                else 0
            ),
            "vault_file_count": len(vault_files),
        }
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))

    buf.seek(0)
    return buf, zip_name


def _apply_retention():
    """Delete oldest server-stored backups exceeding the retention limit.

    Returns the number of backups deleted.
    """
    cfg = get_config()
    retention = cfg.get("backup_retention_count", 10)
    if retention <= 0:          # 0 = unlimited
        return 0

    bdir = _backup_dir()
    zips = sorted(
        [f for f in os.listdir(bdir) if f.endswith(".zip")],
        reverse=True,           # newest first
    )

    deleted = 0
    for old in zips[retention:]:
        os.unlink(os.path.join(bdir, old))
        deleted += 1
    return deleted


def _list_local_backups():
    """Return a list of dicts describing server-stored backups."""
    bdir = _backup_dir()
    backups = []
    for fn in sorted(os.listdir(bdir), reverse=True):
        if fn.endswith(".zip"):
            fp = os.path.join(bdir, fn)
            backups.append({
                "name": fn,
                "size": os.path.getsize(fp),
                "created": datetime.datetime.fromtimestamp(
                    os.path.getmtime(fp)
                ).strftime("%Y-%m-%d %H:%M:%S"),
            })
    return backups


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@backup_bp.route("/")
def backup_page():
    """Render the backup & restore page."""
    db_file = _db_path()
    vault_dir = _vault_path()

    db_size = os.path.getsize(db_file) if db_file and os.path.exists(db_file) else 0
    vault_files = _list_vault_files(vault_dir)
    vault_size = sum(f["size"] for f in vault_files)

    cfg = get_config()
    retention = cfg.get("backup_retention_count", 10)

    return render_template(
        "backup.html",
        db_size=db_size,
        vault_file_count=len(vault_files),
        vault_size=vault_size,
        local_backups=_list_local_backups(),
        retention=retention,
    )


@backup_bp.route("/retention", methods=["POST"])
def update_retention():
    """Update the backup retention count setting."""
    try:
        count = int(request.form.get("retention_count", 10))
        if count < 0:
            count = 0
        update_config({"backup_retention_count": count})
        # Immediately apply new retention limit
        pruned = _apply_retention()
        msg = f"Retention set to {count if count else 'unlimited'} backups."
        if pruned:
            msg += f" {pruned} old backup(s) pruned."
        flash(msg, "success")
    except ValueError:
        flash("Invalid retention count.", "danger")
    return redirect(url_for("backup.backup_page"))


@backup_bp.route("/create", methods=["POST"])
def create_backup():
    """Create a zip backup and either download it or store locally."""
    action = request.form.get("action", "download")

    try:
        buf, zip_name = _create_backup_zip()

        if action == "store":
            dest = os.path.join(_backup_dir(), zip_name)
            with open(dest, "wb") as f:
                f.write(buf.read())
            pruned = _apply_retention()
            msg = f"Backup saved: {zip_name}"
            if pruned:
                msg += f" ({pruned} old backup(s) pruned)"
            flash(msg, "success")
            return redirect(url_for("backup.backup_page"))
        else:
            return send_file(
                buf,
                mimetype="application/zip",
                as_attachment=True,
                download_name=zip_name,
            )

    except Exception as e:
        flash(f"Backup failed: {e}", "danger")
        return redirect(url_for("backup.backup_page"))


@backup_bp.route("/cron", methods=["GET"])
def cron_backup():
    """Endpoint for cron / systemd to trigger a server-stored backup.

    Protected by a simple token passed as ?token=<BACKUP_CRON_TOKEN>.
    Set BACKUP_CRON_TOKEN in your .env file.

    Returns JSON with the result.
    """
    expected = current_app.config.get("BACKUP_CRON_TOKEN", "")
    provided = request.args.get("token", "")

    if not expected:
        return jsonify({"error": "BACKUP_CRON_TOKEN not configured"}), 500
    if provided != expected:
        return jsonify({"error": "Invalid or missing token"}), 403

    try:
        buf, zip_name = _create_backup_zip()
        dest = os.path.join(_backup_dir(), zip_name)
        with open(dest, "wb") as f:
            f.write(buf.read())
        pruned = _apply_retention()
        return jsonify({
            "status": "ok",
            "backup": zip_name,
            "pruned": pruned,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@backup_bp.route("/download/<filename>")
def download_backup(filename):
    """Download a previously stored local backup."""
    if "/" in filename or "\\" in filename or not filename.endswith(".zip"):
        flash("Invalid filename.", "danger")
        return redirect(url_for("backup.backup_page"))

    filepath = os.path.join(_backup_dir(), filename)
    if not os.path.exists(filepath):
        flash("Backup file not found.", "danger")
        return redirect(url_for("backup.backup_page"))

    return send_file(filepath, as_attachment=True, download_name=filename)


@backup_bp.route("/delete/<filename>", methods=["POST"])
def delete_backup(filename):
    """Delete a local backup file."""
    if "/" in filename or "\\" in filename or not filename.endswith(".zip"):
        flash("Invalid filename.", "danger")
        return redirect(url_for("backup.backup_page"))

    filepath = os.path.join(_backup_dir(), filename)
    if os.path.exists(filepath):
        os.unlink(filepath)
        flash(f"Deleted: {filename}", "success")
    else:
        flash("File not found.", "warning")

    return redirect(url_for("backup.backup_page"))


@backup_bp.route("/restore", methods=["POST"])
def restore_backup():
    """Restore from an uploaded or local backup zip."""
    source = request.form.get("source", "upload")

    try:
        if source == "upload":
            if "backup_file" not in request.files:
                flash("No file uploaded.", "danger")
                return redirect(url_for("backup.backup_page"))
            file = request.files["backup_file"]
            if not file.filename or not file.filename.endswith(".zip"):
                flash("Please upload a .zip backup file.", "danger")
                return redirect(url_for("backup.backup_page"))
            zip_data = io.BytesIO(file.read())
        else:
            filename = request.form.get("filename", "")
            if not filename or "/" in filename or "\\" in filename:
                flash("Invalid filename.", "danger")
                return redirect(url_for("backup.backup_page"))
            filepath = os.path.join(_backup_dir(), filename)
            if not os.path.exists(filepath):
                flash("Backup file not found.", "danger")
                return redirect(url_for("backup.backup_page"))
            with open(filepath, "rb") as f:
                zip_data = io.BytesIO(f.read())

        with zipfile.ZipFile(zip_data, "r") as zf:
            names = zf.namelist()
            if "manifest.json" not in names:
                flash("Invalid backup: missing manifest.json", "danger")
                return redirect(url_for("backup.backup_page"))

            manifest = json.loads(zf.read("manifest.json"))
            if manifest.get("app") != "DayTracker":
                flash("Invalid backup: not a DayTracker backup.", "danger")
                return redirect(url_for("backup.backup_page"))

            db_file = _db_path()
            vault_dir = _vault_path()
            pre_restore_ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")

            pre_bak = None
            if db_file and os.path.exists(db_file):
                pre_bak = db_file + f".pre_restore_{pre_restore_ts}"
                shutil.copy2(db_file, pre_bak)

            db.session.remove()
            db.engine.dispose()

            if "data/daytracker.db" in names:
                os.makedirs(os.path.dirname(db_file), exist_ok=True)
                with zf.open("data/daytracker.db") as src:
                    with open(db_file, "wb") as dst:
                        dst.write(src.read())

            vault_entries = [
                n for n in names
                if n.startswith("vault/") and not n.endswith("/")
            ]
            if vault_entries:
                if os.path.isdir(vault_dir):
                    shutil.rmtree(vault_dir)
                os.makedirs(vault_dir, exist_ok=True)
                for entry in vault_entries:
                    rel = entry[len("vault/"):]
                    dest = os.path.join(vault_dir, rel)
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    with zf.open(entry) as src:
                        with open(dest, "wb") as dst:
                            dst.write(src.read())

        created = manifest.get("created_utc", "unknown")
        pre_msg = (
            f" Pre-restore database saved as {os.path.basename(pre_bak)}."
            if pre_bak
            else ""
        )
        flash(
            f"Restore complete from backup created {created}.{pre_msg}",
            "success",
        )

    except zipfile.BadZipFile:
        flash("Invalid file: not a valid zip archive.", "danger")
    except Exception as e:
        flash(f"Restore failed: {e}", "danger")

    return redirect(url_for("backup.backup_page"))
