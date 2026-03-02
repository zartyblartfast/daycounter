"""Flask application factory for the UK Tax Residency Day Tracker."""
import os
from flask import Flask
from app.models import db


def create_app(config_override: dict | None = None) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Default configuration
    basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    data_dir = os.path.join(basedir, "data")
    vault_dir = os.path.join(basedir, "vault")
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(vault_dir, exist_ok=True)

    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(data_dir, 'daytracker.db')}"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["VAULT_PATH"] = os.environ.get("VAULT_PATH", vault_dir)
    app.config["BACKUP_CRON_TOKEN"] = os.environ.get("BACKUP_CRON_TOKEN", "")
    app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB upload limit

    if config_override:
        app.config.update(config_override)

    # Initialize extensions
    db.init_app(app)

    with app.app_context():
        # Import and register blueprints
        from app.routes.dashboard import dashboard_bp
        from app.routes.travels import travels_bp
        from app.routes.heatmap import heatmap_bp
        from app.routes.evidence import evidence_bp
        from app.routes.reports import reports_bp
        from app.routes.settings import settings_bp
        from app.routes.srt import srt_bp
        from app.routes.api import api_bp
        from app.routes.backup import backup_bp

        app.register_blueprint(dashboard_bp)
        app.register_blueprint(travels_bp, url_prefix="/travels")
        app.register_blueprint(heatmap_bp, url_prefix="/heatmap")
        app.register_blueprint(evidence_bp, url_prefix="/evidence")
        app.register_blueprint(reports_bp, url_prefix="/reports")
        app.register_blueprint(settings_bp, url_prefix="/settings")
        app.register_blueprint(srt_bp, url_prefix="/srt")
        app.register_blueprint(api_bp, url_prefix="/api")
        app.register_blueprint(backup_bp, url_prefix="/backup")

        # Create tables
        db.create_all()

        # Ensure default config exists
        from app.config_manager import get_config
        get_config()

    # Template context processors
    @app.context_processor
    def inject_globals():
        from app.tax_year import current_tax_year
        return {
            "current_tax_year_label": current_tax_year(),
        }

    return app
