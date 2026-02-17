"""Tests for risk status computation."""
import pytest

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.profiles import compute_risk_status, Profile


def _make_profile(target=30, limit=90, buffer=5):
    return Profile(
        name="test",
        display_name="Test",
        target_midnights=target,
        stat_limit_midnights=limit,
        buffer=buffer,
    )


class TestRiskStatus:
    """Test GREEN/AMBER/RED risk status logic.

    With target=30, buffer=5:
    - GREEN: used <= 25 (target - buffer)
    - AMBER: 25 < used < 30
    - RED: used >= 30
    """

    def test_green_well_below(self):
        profile = _make_profile(target=30, buffer=5)
        assert compute_risk_status(0, profile) == "GREEN"
        assert compute_risk_status(10, profile) == "GREEN"
        assert compute_risk_status(20, profile) == "GREEN"

    def test_green_at_safe_threshold(self):
        """Exactly at target - buffer is still GREEN."""
        profile = _make_profile(target=30, buffer=5)
        assert compute_risk_status(25, profile) == "GREEN"

    def test_amber_just_above_safe(self):
        """One above safe threshold is AMBER."""
        profile = _make_profile(target=30, buffer=5)
        assert compute_risk_status(26, profile) == "AMBER"

    def test_amber_just_below_target(self):
        """One below target is still AMBER."""
        profile = _make_profile(target=30, buffer=5)
        assert compute_risk_status(29, profile) == "AMBER"

    def test_red_at_target(self):
        """Exactly at target is RED."""
        profile = _make_profile(target=30, buffer=5)
        assert compute_risk_status(30, profile) == "RED"

    def test_red_above_target(self):
        """Above target is RED."""
        profile = _make_profile(target=30, buffer=5)
        assert compute_risk_status(35, profile) == "RED"
        assert compute_risk_status(90, profile) == "RED"

    def test_year_2_profile(self):
        """Test with Year 2 profile (target=85, buffer=5)."""
        profile = _make_profile(target=85, limit=90, buffer=5)
        assert compute_risk_status(79, profile) == "GREEN"
        assert compute_risk_status(80, profile) == "GREEN"  # 85-5=80
        assert compute_risk_status(81, profile) == "AMBER"
        assert compute_risk_status(84, profile) == "AMBER"
        assert compute_risk_status(85, profile) == "RED"

    def test_year_3_profile(self):
        """Test with Year 3+ profile (target=120, buffer=5)."""
        profile = _make_profile(target=120, limit=120, buffer=5)
        assert compute_risk_status(114, profile) == "GREEN"
        assert compute_risk_status(115, profile) == "GREEN"  # 120-5=115
        assert compute_risk_status(116, profile) == "AMBER"
        assert compute_risk_status(119, profile) == "AMBER"
        assert compute_risk_status(120, profile) == "RED"

    def test_zero_buffer(self):
        """With buffer=0, there is no AMBER zone."""
        profile = _make_profile(target=30, buffer=0)
        assert compute_risk_status(29, profile) == "GREEN"
        assert compute_risk_status(30, profile) == "RED"  # 30 >= 30
