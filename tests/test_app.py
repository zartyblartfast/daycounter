"""Integration tests for the Flask application."""
import pytest
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app
from app.models import db


@pytest.fixture
def app():
    """Create a test Flask application."""
    tmp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    tmp_db.close()
    tmp_vault = tempfile.mkdtemp()

    test_config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_db.name}",
        "VAULT_PATH": tmp_vault,
        "SECRET_KEY": "test-secret",
    }
    app = create_app(test_config)
    yield app

    os.unlink(tmp_db.name)


@pytest.fixture
def client(app):
    return app.test_client()


class TestAppRoutes:
    """Test that all main routes return 200."""

    def test_dashboard(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"Dashboard" in resp.data

    def test_heatmap(self, client):
        resp = client.get("/heatmap/")
        assert resp.status_code == 200
        assert b"Heatmap" in resp.data

    def test_travels(self, client):
        resp = client.get("/travels/")
        assert resp.status_code == 200
        assert b"Travel" in resp.data

    def test_evidence(self, client):
        resp = client.get("/evidence/")
        assert resp.status_code == 200
        assert b"Evidence" in resp.data

    def test_reports(self, client):
        resp = client.get("/reports/")
        assert resp.status_code == 200
        assert b"Statement" in resp.data

    def test_settings(self, client):
        resp = client.get("/settings/")
        assert resp.status_code == 200
        assert b"Settings" in resp.data

    def test_srt(self, client):
        resp = client.get("/srt/")
        assert resp.status_code == 200
        assert b"Statutory Residency Test" in resp.data

    def test_api_status(self, client):
        resp = client.get("/api/status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "tax_year" in data
        assert "midnights_used" in data

    def test_api_config(self, client):
        resp = client.get("/api/config")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "departure_date" in data
        assert "first_full_nonresident_tax_year" in data
