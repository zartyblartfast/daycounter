"""Tests for the SRT (Statutory Residency Test) route."""
import pytest
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app
from app.models import db
from app.config_manager import get_config


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


class TestSRTPage:
    """Test the SRT page renders correctly."""

    def test_srt_get_returns_200(self, client):
        """GET /srt/ returns 200."""
        resp = client.get("/srt/")
        assert resp.status_code == 200

    def test_srt_page_contains_heading(self, client):
        """SRT page contains the expected heading."""
        resp = client.get("/srt/")
        assert b"Statutory Residency Test" in resp.data

    def test_srt_page_contains_profile_fields(self, client):
        """SRT page contains input fields for all three profiles."""
        resp = client.get("/srt/")
        html = resp.data.decode()
        for key in ["year_1", "year_2", "year_3_plus"]:
            assert f"{key}_target" in html
            assert f"{key}_limit" in html
            assert f"{key}_buffer" in html

    def test_srt_page_shows_default_values(self, client):
        """SRT page shows the default profile values."""
        resp = client.get("/srt/")
        html = resp.data.decode()
        # Default year_1 target is 30
        assert 'value="30"' in html
        # Default year_2 target is 85
        assert 'value="85"' in html
        # Default year_3_plus target is 120
        assert 'value="120"' in html

    def test_srt_page_contains_about_section(self, client):
        """SRT page contains the collapsible About section."""
        resp = client.get("/srt/")
        html = resp.data.decode()
        assert "aboutSRT" in html
        assert "interactive SRT flowchart" in html


class TestSRTSave:
    """Test saving SRT profile settings."""

    def test_post_saves_profiles(self, app, client):
        """POST /srt/ saves profile values."""
        resp = client.post("/srt/", data={
            "year_1_target": "25",
            "year_1_limit": "80",
            "year_1_buffer": "3",
            "year_2_target": "70",
            "year_2_limit": "85",
            "year_2_buffer": "4",
            "year_3_plus_target": "100",
            "year_3_plus_limit": "110",
            "year_3_plus_buffer": "6",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"saved successfully" in resp.data

        # Verify values persisted
        with app.app_context():
            config = get_config()
            assert config["profiles"]["year_1"]["target_midnights"] == 25
            assert config["profiles"]["year_1"]["stat_limit_midnights"] == 80
            assert config["profiles"]["year_1"]["buffer"] == 3
            assert config["profiles"]["year_2"]["target_midnights"] == 70
            assert config["profiles"]["year_2"]["stat_limit_midnights"] == 85
            assert config["profiles"]["year_2"]["buffer"] == 4
            assert config["profiles"]["year_3_plus"]["target_midnights"] == 100
            assert config["profiles"]["year_3_plus"]["stat_limit_midnights"] == 110
            assert config["profiles"]["year_3_plus"]["buffer"] == 6

    def test_post_values_persist_on_reload(self, app, client):
        """Saved values appear when the page is reloaded."""
        client.post("/srt/", data={
            "year_1_target": "42",
            "year_1_limit": "88",
            "year_1_buffer": "7",
            "year_2_target": "60",
            "year_2_limit": "75",
            "year_2_buffer": "8",
            "year_3_plus_target": "99",
            "year_3_plus_limit": "105",
            "year_3_plus_buffer": "2",
        }, follow_redirects=True)

        resp = client.get("/srt/")
        html = resp.data.decode()
        assert 'value="42"' in html
        assert 'value="88"' in html
        assert 'value="7"' in html

    def test_post_does_not_affect_other_settings(self, app, client):
        """Saving SRT profiles does not overwrite departure_date or other settings."""
        # First verify default departure_date exists
        with app.app_context():
            config = get_config()
            original_departure = config.get("departure_date")

        client.post("/srt/", data={
            "year_1_target": "25",
            "year_1_limit": "80",
            "year_1_buffer": "3",
            "year_2_target": "70",
            "year_2_limit": "85",
            "year_2_buffer": "4",
            "year_3_plus_target": "100",
            "year_3_plus_limit": "110",
            "year_3_plus_buffer": "6",
        }, follow_redirects=True)

        with app.app_context():
            config = get_config()
            assert config.get("departure_date") == original_departure

    def test_post_missing_field_shows_error(self, client):
        """POST with missing fields shows an error flash."""
        resp = client.post("/srt/", data={
            "year_1_target": "25",
            "year_1_limit": "80",
            "year_1_buffer": "3",
            "year_2_target": "",
            "year_2_limit": "85",
            "year_2_buffer": "4",
            "year_3_plus_target": "100",
            "year_3_plus_limit": "110",
            "year_3_plus_buffer": "6",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"Error" in resp.data

    def test_post_negative_value_shows_error(self, client):
        """POST with negative values shows an error flash."""
        resp = client.post("/srt/", data={
            "year_1_target": "-5",
            "year_1_limit": "80",
            "year_1_buffer": "3",
            "year_2_target": "70",
            "year_2_limit": "85",
            "year_2_buffer": "4",
            "year_3_plus_target": "100",
            "year_3_plus_limit": "110",
            "year_3_plus_buffer": "6",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"Error" in resp.data

    def test_post_redirect(self, client):
        """POST /srt/ redirects back to the SRT page."""
        resp = client.post("/srt/", data={
            "year_1_target": "30",
            "year_1_limit": "90",
            "year_1_buffer": "5",
            "year_2_target": "85",
            "year_2_limit": "90",
            "year_2_buffer": "5",
            "year_3_plus_target": "120",
            "year_3_plus_limit": "120",
            "year_3_plus_buffer": "5",
        }, follow_redirects=False)
        assert resp.status_code == 302
        assert "/srt/" in resp.headers["Location"]
