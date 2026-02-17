"""Tests for overlap detection logic."""
import datetime
import pytest

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.uk_midnights import detect_overlaps


def _travel(arrival, return_date=None, is_uk=True, country="United Kingdom", tid=None):
    """Helper to create travel dict."""
    return {
        "id": tid,
        "arrival_date": datetime.date.fromisoformat(arrival),
        "return_date": datetime.date.fromisoformat(return_date) if return_date else None,
        "is_uk": is_uk,
        "destination_country": country,
    }


class TestDetectOverlaps:
    """Test overlap detection between travel records."""

    def test_no_overlaps(self):
        """Non-overlapping trips produce no warnings."""
        travels = [
            _travel("2026-06-01", "2026-06-05", country="France", tid=1),
            _travel("2026-06-05", "2026-06-10", country="Spain", tid=2),
        ]
        warnings = detect_overlaps(travels)
        assert len(warnings) == 0

    def test_overlapping_different_destinations(self):
        """Overlapping trips with different destinations produce a warning."""
        travels = [
            _travel("2026-06-01", "2026-06-10", country="France", tid=1),
            _travel("2026-06-08", "2026-06-15", country="Spain", tid=2),
        ]
        warnings = detect_overlaps(travels)
        assert len(warnings) == 1
        w = warnings[0]
        assert w["trip_a"]["destination"] == "France"
        assert w["trip_b"]["destination"] == "Spain"
        assert w["overlap_start"] == datetime.date(2026, 6, 8)
        assert w["overlap_end"] == datetime.date(2026, 6, 10)

    def test_same_destination_no_warning(self):
        """Overlapping trips with the SAME destination produce no warning."""
        travels = [
            _travel("2026-06-01", "2026-06-10", country="France", tid=1),
            _travel("2026-06-08", "2026-06-15", country="France", tid=2),
        ]
        warnings = detect_overlaps(travels)
        assert len(warnings) == 0

    def test_open_ended_trip_overlap(self):
        """Open-ended trip (no return_date) uses today as effective end."""
        today = datetime.date.today()
        # Trip A is open-ended starting well before today
        travels = [
            _travel("2026-01-01", None, country="France", tid=1),
            _travel(
                (today - datetime.timedelta(days=5)).isoformat(),
                (today + datetime.timedelta(days=5)).isoformat(),
                country="Spain",
                tid=2,
            ),
        ]
        warnings = detect_overlaps(travels)
        # Should detect overlap since France open-ended overlaps with Spain
        assert len(warnings) >= 1

    def test_adjacent_trips_no_overlap(self):
        """Trips that are exactly adjacent (end == start) do not overlap."""
        travels = [
            _travel("2026-06-01", "2026-06-05", country="France", tid=1),
            _travel("2026-06-05", "2026-06-10", country="Germany", tid=2),
        ]
        warnings = detect_overlaps(travels)
        assert len(warnings) == 0

    def test_fully_contained_trip(self):
        """Trip B fully contained within trip A with different destination."""
        travels = [
            _travel("2026-06-01", "2026-06-20", country="France", tid=1),
            _travel("2026-06-05", "2026-06-10", country="Spain", tid=2),
        ]
        warnings = detect_overlaps(travels)
        assert len(warnings) == 1
        w = warnings[0]
        assert w["overlap_start"] == datetime.date(2026, 6, 5)
        assert w["overlap_end"] == datetime.date(2026, 6, 10)

    def test_empty_travels(self):
        """No travels produce no warnings."""
        warnings = detect_overlaps([])
        assert len(warnings) == 0

    def test_single_travel(self):
        """Single travel record produces no warnings."""
        travels = [
            _travel("2026-06-01", "2026-06-10", country="France", tid=1),
        ]
        warnings = detect_overlaps(travels)
        assert len(warnings) == 0

    def test_same_day_trip_no_overlap(self):
        """Same-day trip (arrival == return) is zero-length, no overlap."""
        travels = [
            _travel("2026-06-05", "2026-06-05", country="France", tid=1),
            _travel("2026-06-01", "2026-06-10", country="Spain", tid=2),
        ]
        warnings = detect_overlaps(travels)
        # Zero-length trip should be skipped
        assert len(warnings) == 0

    def test_multiple_overlaps(self):
        """Three trips where two pairs overlap."""
        travels = [
            _travel("2026-06-01", "2026-06-10", country="France", tid=1),
            _travel("2026-06-08", "2026-06-15", country="Spain", tid=2),
            _travel("2026-06-12", "2026-06-20", country="Germany", tid=3),
        ]
        warnings = detect_overlaps(travels)
        # France-Spain overlap (Jun 8-10), Spain-Germany overlap (Jun 12-15),
        # France-Germany no overlap (France ends Jun 10, Germany starts Jun 12)
        assert len(warnings) == 2

    def test_overlap_message_content(self):
        """Overlap warning message contains destination names."""
        travels = [
            _travel("2026-06-01", "2026-06-10", country="France", tid=1),
            _travel("2026-06-08", "2026-06-15", country="Spain", tid=2),
        ]
        warnings = detect_overlaps(travels)
        assert len(warnings) == 1
        assert "France" in warnings[0]["message"]
        assert "Spain" in warnings[0]["message"]

    def test_two_open_ended_different_destinations(self):
        """Two open-ended trips with different destinations overlap."""
        travels = [
            _travel("2026-01-01", None, country="France", tid=1),
            _travel("2026-02-01", None, country="Spain", tid=2),
        ]
        warnings = detect_overlaps(travels)
        assert len(warnings) == 1
        assert warnings[0]["overlap_start"] == datetime.date(2026, 2, 1)
