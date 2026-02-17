"""Tests for UK midnight computation."""
import datetime
import pytest

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.uk_midnights import compute_uk_midnights_for_tax_year


def _travel(arrival, return_date=None, is_uk=True, country="United Kingdom"):
    """Helper to create travel dict."""
    return {
        "id": None,
        "arrival_date": datetime.date.fromisoformat(arrival),
        "return_date": datetime.date.fromisoformat(return_date) if return_date else None,
        "is_uk": is_uk,
        "destination_country": country,
    }


class TestUKMidnights:
    """Test UK midnight day classification."""

    def test_simple_uk_stay(self):
        """A 5-night UK stay: arrival counts, return date does NOT count."""
        travels = [
            _travel("2026-06-01", "2026-06-06", is_uk=True),
        ]
        result = compute_uk_midnights_for_tax_year("2026-2027", travels)
        # Midnights: Jun 1, 2, 3, 4, 5 (NOT Jun 6 — that's departure day)
        assert result["total"] == 5
        assert datetime.date(2026, 6, 1) in result["uk_midnight_dates"]
        assert datetime.date(2026, 6, 5) in result["uk_midnight_dates"]
        assert datetime.date(2026, 6, 6) not in result["uk_midnight_dates"]

    def test_non_uk_stay_not_counted(self):
        """Non-UK stays should not count as UK midnights."""
        travels = [
            _travel("2026-06-01", "2026-06-10", is_uk=False, country="France"),
        ]
        result = compute_uk_midnights_for_tax_year("2026-2027", travels)
        assert result["total"] == 0

    def test_multiple_uk_stays(self):
        """Multiple UK stays in same tax year."""
        travels = [
            _travel("2026-06-01", "2026-06-04", is_uk=True),  # 3 nights
            _travel("2026-09-10", "2026-09-15", is_uk=True),  # 5 nights
        ]
        result = compute_uk_midnights_for_tax_year("2026-2027", travels)
        assert result["total"] == 8

    def test_stay_spanning_tax_year_boundary(self):
        """Stay from 3 April to 8 April spans the 5/6 April boundary."""
        travels = [
            _travel("2027-04-03", "2027-04-08", is_uk=True),
        ]
        # Tax year 2026-2027 ends 5 April 2027
        result_2026 = compute_uk_midnights_for_tax_year("2026-2027", travels)
        # Days in 2026-2027: Apr 3, 4, 5 = 3 midnights
        assert result_2026["total"] == 3

        # Tax year 2027-2028 starts 6 April 2027
        result_2027 = compute_uk_midnights_for_tax_year("2027-2028", travels)
        # Days in 2027-2028: Apr 6, 7 = 2 midnights (Apr 8 is departure)
        assert result_2027["total"] == 2

    def test_ongoing_stay_no_return_date(self):
        """Stay with no return date counts from arrival onwards."""
        travels = [
            _travel("2026-12-28", None, is_uk=True),
        ]
        result = compute_uk_midnights_for_tax_year("2026-2027", travels)
        # From Dec 28 to Apr 5 = 99 days (Dec: 4, Jan: 31, Feb: 28, Mar: 31, Apr: 5)
        # Dec 28,29,30,31 = 4; Jan = 31; Feb = 28; Mar = 31; Apr 1,2,3,4,5 = 5
        # Total = 4 + 31 + 28 + 31 + 5 = 99
        assert result["total"] == 99

    def test_empty_travels(self):
        """No travels means no UK midnights."""
        result = compute_uk_midnights_for_tax_year("2026-2027", [])
        assert result["total"] == 0

    def test_day_status_classification(self):
        """Check day_status dict has correct classifications."""
        travels = [
            _travel("2026-06-01", "2026-06-03", is_uk=True),
            _travel("2026-06-03", "2026-06-05", is_uk=False, country="France"),
        ]
        result = compute_uk_midnights_for_tax_year("2026-2027", travels)
        assert result["day_status"][datetime.date(2026, 6, 1)] == "uk"
        assert result["day_status"][datetime.date(2026, 6, 2)] == "uk"
        assert result["day_status"][datetime.date(2026, 6, 3)] == "non_uk"
        assert result["day_status"][datetime.date(2026, 6, 4)] == "non_uk"

    def test_stay_outside_tax_year_not_counted(self):
        """UK stay entirely outside the queried tax year."""
        travels = [
            _travel("2025-06-01", "2025-06-10", is_uk=True),
        ]
        result = compute_uk_midnights_for_tax_year("2026-2027", travels)
        assert result["total"] == 0

    def test_single_night_stay(self):
        """Arrive and leave next day = 1 midnight."""
        travels = [
            _travel("2026-08-15", "2026-08-16", is_uk=True),
        ]
        result = compute_uk_midnights_for_tax_year("2026-2027", travels)
        assert result["total"] == 1
        assert datetime.date(2026, 8, 15) in result["uk_midnight_dates"]

    def test_same_day_arrival_departure(self):
        """Arrive and leave same day = 0 midnights."""
        travels = [
            _travel("2026-08-15", "2026-08-15", is_uk=True),
        ]
        result = compute_uk_midnights_for_tax_year("2026-2027", travels)
        assert result["total"] == 0
