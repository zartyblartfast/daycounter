"""Tests for compute_country_breakdown."""
import datetime
import unittest

from app.uk_midnights import compute_country_breakdown


class TestCountryBreakdown(unittest.TestCase):
    """Test per-country midnight aggregation."""

    def test_empty_details(self):
        """Empty day_details returns empty list."""
        result = compute_country_breakdown({})
        self.assertEqual(result, [])

    def test_all_unknown(self):
        """Days with no travel records are grouped as Unaccounted."""
        details = {
            datetime.date(2026, 4, 6): {"status": "unknown", "destination": None, "travel_id": None},
            datetime.date(2026, 4, 7): {"status": "unknown", "destination": None, "travel_id": None},
            datetime.date(2026, 4, 8): {"status": "unknown", "destination": None, "travel_id": None},
        }
        result = compute_country_breakdown(details)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["country"], "Unaccounted")
        self.assertEqual(result[0]["midnights"], 3)
        self.assertFalse(result[0]["is_uk"])

    def test_uk_only(self):
        """UK stays are correctly identified."""
        details = {
            datetime.date(2026, 6, 1): {"status": "uk", "destination": "United Kingdom", "travel_id": 1},
            datetime.date(2026, 6, 2): {"status": "uk", "destination": "United Kingdom", "travel_id": 1},
        }
        result = compute_country_breakdown(details)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["country"], "United Kingdom")
        self.assertEqual(result[0]["midnights"], 2)
        self.assertTrue(result[0]["is_uk"])

    def test_mixed_countries(self):
        """Multiple countries are correctly aggregated and sorted by count."""
        details = {
            datetime.date(2026, 6, 1): {"status": "uk", "destination": "United Kingdom", "travel_id": 1},
            datetime.date(2026, 6, 2): {"status": "uk", "destination": "United Kingdom", "travel_id": 1},
            datetime.date(2026, 6, 3): {"status": "non_uk", "destination": "France", "travel_id": 2},
            datetime.date(2026, 6, 4): {"status": "non_uk", "destination": "France", "travel_id": 2},
            datetime.date(2026, 6, 5): {"status": "non_uk", "destination": "France", "travel_id": 2},
            datetime.date(2026, 6, 6): {"status": "non_uk", "destination": "Spain", "travel_id": 3},
            datetime.date(2026, 6, 7): {"status": "unknown", "destination": None, "travel_id": None},
        }
        result = compute_country_breakdown(details)
        # Should be sorted by count descending: France(3), UK(2), Spain(1), Unaccounted(1)
        self.assertEqual(len(result), 4)
        self.assertEqual(result[0]["country"], "France")
        self.assertEqual(result[0]["midnights"], 3)
        self.assertFalse(result[0]["is_uk"])
        self.assertEqual(result[1]["country"], "United Kingdom")
        self.assertEqual(result[1]["midnights"], 2)
        self.assertTrue(result[1]["is_uk"])
        self.assertEqual(result[2]["country"], "Spain")
        self.assertEqual(result[2]["midnights"], 1)
        self.assertFalse(result[2]["is_uk"])
        self.assertEqual(result[3]["country"], "Unaccounted")
        self.assertEqual(result[3]["midnights"], 1)

    def test_non_uk_no_destination(self):
        """Non-UK stays without a destination get a fallback label."""
        details = {
            datetime.date(2026, 6, 1): {"status": "non_uk", "destination": "", "travel_id": 1},
            datetime.date(2026, 6, 2): {"status": "non_uk", "destination": None, "travel_id": 2},
        }
        result = compute_country_breakdown(details)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["country"], "Non-UK (unspecified)")
        self.assertEqual(result[0]["midnights"], 2)

    def test_uk_no_destination_defaults(self):
        """UK stays without a destination default to 'United Kingdom'."""
        details = {
            datetime.date(2026, 6, 1): {"status": "uk", "destination": "", "travel_id": 1},
            datetime.date(2026, 6, 2): {"status": "uk", "destination": None, "travel_id": 1},
        }
        result = compute_country_breakdown(details)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["country"], "United Kingdom")
        self.assertTrue(result[0]["is_uk"])

    def test_total_midnights_match(self):
        """Sum of all country midnights equals total days in input."""
        details = {
            datetime.date(2026, 6, d): {
                "status": "uk" if d <= 10 else "non_uk" if d <= 20 else "unknown",
                "destination": "United Kingdom" if d <= 10 else "France" if d <= 20 else None,
                "travel_id": 1 if d <= 10 else 2 if d <= 20 else None,
            }
            for d in range(1, 31)
        }
        result = compute_country_breakdown(details)
        total = sum(entry["midnights"] for entry in result)
        self.assertEqual(total, 30)


if __name__ == "__main__":
    unittest.main()
