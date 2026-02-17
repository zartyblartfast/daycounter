"""Tests for UK tax year logic."""
import datetime
import pytest

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.tax_year import (
    tax_year_label,
    next_tax_year,
    prev_tax_year,
    tax_year_start,
    tax_year_end,
    tax_year_range,
    all_tax_years_between,
    current_tax_year,
    days_remaining_in_tax_year,
    total_days_in_tax_year,
)


class TestTaxYearLabel:
    """Test tax_year_label() around 5/6 April boundaries."""

    def test_on_6_april(self):
        """6 April is the FIRST day of the new tax year."""
        assert tax_year_label(datetime.date(2026, 4, 6)) == "2026-2027"

    def test_on_5_april(self):
        """5 April is the LAST day of the previous tax year."""
        assert tax_year_label(datetime.date(2026, 4, 5)) == "2025-2026"

    def test_before_april(self):
        """Dates before April belong to the tax year starting previous year."""
        assert tax_year_label(datetime.date(2026, 3, 26)) == "2025-2026"
        assert tax_year_label(datetime.date(2026, 1, 1)) == "2025-2026"
        assert tax_year_label(datetime.date(2027, 1, 1)) == "2026-2027"

    def test_after_april(self):
        """Dates after 6 April belong to the current calendar year's tax year."""
        assert tax_year_label(datetime.date(2026, 7, 15)) == "2026-2027"
        assert tax_year_label(datetime.date(2026, 12, 31)) == "2026-2027"

    def test_boundary_7_april(self):
        assert tax_year_label(datetime.date(2026, 4, 7)) == "2026-2027"

    def test_boundary_4_april(self):
        assert tax_year_label(datetime.date(2026, 4, 4)) == "2025-2026"

    def test_various_years(self):
        assert tax_year_label(datetime.date(2020, 4, 6)) == "2020-2021"
        assert tax_year_label(datetime.date(2020, 4, 5)) == "2019-2020"
        assert tax_year_label(datetime.date(2030, 6, 1)) == "2030-2031"


class TestNextPrevTaxYear:
    """Test next_tax_year() and prev_tax_year()."""

    def test_next_tax_year(self):
        assert next_tax_year("2026-2027") == "2027-2028"
        assert next_tax_year("2020-2021") == "2021-2022"

    def test_prev_tax_year(self):
        assert prev_tax_year("2027-2028") == "2026-2027"
        assert prev_tax_year("2021-2022") == "2020-2021"

    def test_next_then_prev(self):
        label = "2026-2027"
        assert prev_tax_year(next_tax_year(label)) == label

    def test_invalid_label(self):
        with pytest.raises(ValueError):
            next_tax_year("2026")
        with pytest.raises(ValueError):
            next_tax_year("2026-2028")  # end != start + 1


class TestTaxYearStartEnd:
    """Test tax_year_start() and tax_year_end()."""

    def test_start(self):
        assert tax_year_start("2026-2027") == datetime.date(2026, 4, 6)

    def test_end(self):
        assert tax_year_end("2026-2027") == datetime.date(2027, 4, 5)

    def test_range(self):
        start, end = tax_year_range("2026-2027")
        assert start == datetime.date(2026, 4, 6)
        assert end == datetime.date(2027, 4, 5)

    def test_total_days_normal_year(self):
        # 2026-2027: 6 Apr 2026 to 5 Apr 2027 = 365 days
        total = total_days_in_tax_year("2026-2027")
        assert total == 365

    def test_total_days_leap_year(self):
        # 2027-2028: 6 Apr 2027 to 5 Apr 2028 (2028 is leap year)
        # Feb 2028 has 29 days, so this tax year has 366 days
        total = total_days_in_tax_year("2027-2028")
        assert total == 366


class TestAllTaxYearsBetween:
    """Test all_tax_years_between()."""

    def test_single_year(self):
        result = all_tax_years_between("2026-2027", "2026-2027")
        assert result == ["2026-2027"]

    def test_multiple_years(self):
        result = all_tax_years_between("2026-2027", "2028-2029")
        assert result == ["2026-2027", "2027-2028", "2028-2029"]

    def test_reversed_returns_empty(self):
        result = all_tax_years_between("2028-2029", "2026-2027")
        assert result == []


class TestDaysRemaining:
    """Test days_remaining_in_tax_year()."""

    def test_from_start(self):
        remaining = days_remaining_in_tax_year(
            "2026-2027", datetime.date(2026, 4, 6)
        )
        assert remaining == 364  # 5 Apr 2027 - 6 Apr 2026 = 364

    def test_from_end(self):
        remaining = days_remaining_in_tax_year(
            "2026-2027", datetime.date(2027, 4, 5)
        )
        assert remaining == 0

    def test_past_end(self):
        remaining = days_remaining_in_tax_year(
            "2026-2027", datetime.date(2027, 5, 1)
        )
        assert remaining == 0
