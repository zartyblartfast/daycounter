"""Tests for heatmap day classification and calendar building."""
import datetime
import pytest

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.uk_midnights import compute_uk_midnights_for_tax_year
from app.tax_year import tax_year_range, total_days_in_tax_year


def _travel(arrival, return_date=None, is_uk=True, country="United Kingdom"):
    return {
        "id": None,
        "arrival_date": datetime.date.fromisoformat(arrival),
        "return_date": datetime.date.fromisoformat(return_date) if return_date else None,
        "is_uk": is_uk,
        "destination_country": country,
    }


class TestHeatmapDayClassification:
    """Test that every day in a tax year gets a status."""

    def test_all_days_have_status(self):
        """Every day in the tax year should have a status entry."""
        ty = "2026-2027"
        travels = [
            _travel("2026-06-01", "2026-06-10", is_uk=True),
        ]
        result = compute_uk_midnights_for_tax_year(ty, travels)
        total = total_days_in_tax_year(ty)
        # day_status should have an entry for every day
        assert len(result["day_status"]) == total

    def test_uk_days_marked_correctly(self):
        """UK stay days should be marked as 'uk'."""
        travels = [
            _travel("2026-07-01", "2026-07-04", is_uk=True),
        ]
        result = compute_uk_midnights_for_tax_year("2026-2027", travels)
        assert result["day_status"][datetime.date(2026, 7, 1)] == "uk"
        assert result["day_status"][datetime.date(2026, 7, 2)] == "uk"
        assert result["day_status"][datetime.date(2026, 7, 3)] == "uk"
        # Departure day is NOT uk
        assert result["day_status"][datetime.date(2026, 7, 4)] != "uk"

    def test_non_uk_days_marked_correctly(self):
        """Non-UK stay days should be marked as 'non_uk'."""
        travels = [
            _travel("2026-07-01", "2026-07-04", is_uk=False, country="Spain"),
        ]
        result = compute_uk_midnights_for_tax_year("2026-2027", travels)
        assert result["day_status"][datetime.date(2026, 7, 1)] == "non_uk"
        assert result["day_status"][datetime.date(2026, 7, 2)] == "non_uk"

    def test_unknown_days(self):
        """Days with no travel data should be 'unknown'."""
        result = compute_uk_midnights_for_tax_year("2026-2027", [])
        # All days should be unknown
        for status in result["day_status"].values():
            assert status == "unknown"

    def test_heatmap_matches_midnight_count(self):
        """Number of 'uk' days in day_status should match total."""
        travels = [
            _travel("2026-06-01", "2026-06-11", is_uk=True),  # 10 nights
            _travel("2026-09-01", "2026-09-06", is_uk=True),  # 5 nights
        ]
        result = compute_uk_midnights_for_tax_year("2026-2027", travels)
        uk_count = sum(1 for s in result["day_status"].values() if s == "uk")
        assert uk_count == result["total"]
        assert uk_count == 15

    def test_day_details_include_destination(self):
        """Day details should include destination country."""
        travels = [
            _travel("2026-08-01", "2026-08-03", is_uk=True, country="United Kingdom"),
        ]
        result = compute_uk_midnights_for_tax_year("2026-2027", travels)
        detail = result["day_details"][datetime.date(2026, 8, 1)]
        assert detail["status"] == "uk"
        assert detail["destination"] == "United Kingdom"
