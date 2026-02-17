"""Tests for operational profile mapping."""
import pytest

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.profiles import get_profile_for_tax_year, compute_risk_status, Profile


TEST_CONFIG = {
    "first_full_nonresident_tax_year": "2026-2027",
    "profiles": {
        "year_1": {"target_midnights": 30, "stat_limit_midnights": 90, "buffer": 5},
        "year_2": {"target_midnights": 85, "stat_limit_midnights": 90, "buffer": 5},
        "year_3_plus": {"target_midnights": 120, "stat_limit_midnights": 120, "buffer": 5},
    },
}


class TestGetProfileForTaxYear:
    """Test profile mapping based on first full non-resident tax year."""

    def test_year_1_mapping(self):
        """First full non-resident year maps to year_1."""
        profile = get_profile_for_tax_year("2026-2027", TEST_CONFIG)
        assert profile is not None
        assert profile.name == "year_1"
        assert profile.display_name == "Year 1"
        assert profile.target_midnights == 30
        assert profile.stat_limit_midnights == 90
        assert profile.buffer == 5

    def test_year_2_mapping(self):
        """Second year maps to year_2."""
        profile = get_profile_for_tax_year("2027-2028", TEST_CONFIG)
        assert profile is not None
        assert profile.name == "year_2"
        assert profile.display_name == "Year 2"
        assert profile.target_midnights == 85

    def test_year_3_mapping(self):
        """Third year maps to year_3_plus."""
        profile = get_profile_for_tax_year("2028-2029", TEST_CONFIG)
        assert profile is not None
        assert profile.name == "year_3_plus"
        assert profile.display_name == "Year 3+"
        assert profile.target_midnights == 120

    def test_year_4_still_year_3_plus(self):
        """Fourth and subsequent years also map to year_3_plus."""
        profile = get_profile_for_tax_year("2029-2030", TEST_CONFIG)
        assert profile is not None
        assert profile.name == "year_3_plus"

    def test_year_5_still_year_3_plus(self):
        profile = get_profile_for_tax_year("2030-2031", TEST_CONFIG)
        assert profile is not None
        assert profile.name == "year_3_plus"

    def test_pre_departure_returns_none(self):
        """Tax year before first full non-resident year returns None."""
        profile = get_profile_for_tax_year("2025-2026", TEST_CONFIG)
        assert profile is None

    def test_missing_config_returns_none(self):
        """Missing first_full_nonresident_tax_year returns None."""
        profile = get_profile_for_tax_year("2026-2027", {})
        assert profile is None

    def test_different_anchor_year(self):
        """Test with a different anchor year."""
        config = dict(TEST_CONFIG)
        config["first_full_nonresident_tax_year"] = "2025-2026"
        profile = get_profile_for_tax_year("2025-2026", config)
        assert profile.name == "year_1"
        profile = get_profile_for_tax_year("2026-2027", config)
        assert profile.name == "year_2"
        profile = get_profile_for_tax_year("2027-2028", config)
        assert profile.name == "year_3_plus"
