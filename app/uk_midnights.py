"""UK Midnights computation.

A "UK midnight" means the person was physically in the UK at midnight
(i.e., they slept in the UK that night). The arrival date counts as a
UK midnight (they are in the UK at midnight that night), but the return/
departure date does NOT count (they leave that day, so they are not in
the UK at midnight).
"""
import datetime
from typing import Dict, List, Any

from app.tax_year import tax_year_range


def compute_uk_midnights_for_tax_year(
    tax_year_label: str, travels: list
) -> Dict[str, Any]:
    """Compute UK midnights for a given tax year from travel records.

    Args:
        tax_year_label: e.g. '2026-2027'
        travels: list of Travel model instances (or dicts with same keys)

    Returns:
        dict with:
            - 'uk_midnight_dates': list of datetime.date where person was in UK at midnight
            - 'total': int count
            - 'day_status': dict mapping date -> 'uk' | 'non_uk' | 'unknown'
            - 'day_details': dict mapping date -> {'status': ..., 'destination': ..., 'travel_id': ...}
    """
    start, end = tax_year_range(tax_year_label)

    # Build a list of UK stay intervals from travel records
    uk_intervals = []
    non_uk_intervals = []

    for t in travels:
        # Support both model objects and dicts
        if isinstance(t, dict):
            arrival = t["arrival_date"]
            return_date = t.get("return_date")
            is_uk = t.get("is_uk", False)
            destination = t.get("destination_country", "")
            travel_id = t.get("id")
        else:
            arrival = t.arrival_date
            return_date = t.return_date
            is_uk = t.is_uk
            destination = t.destination_country
            travel_id = t.id

        # Ensure dates are datetime.date objects
        if isinstance(arrival, str):
            arrival = datetime.date.fromisoformat(arrival)
        if isinstance(return_date, str):
            return_date = datetime.date.fromisoformat(return_date)

        interval = {
            "arrival": arrival,
            "return_date": return_date,
            "is_uk": is_uk,
            "destination": destination,
            "travel_id": travel_id,
        }

        if is_uk:
            uk_intervals.append(interval)
        else:
            non_uk_intervals.append(interval)

    # Build day-by-day status
    day_status = {}
    day_details = {}
    uk_midnight_dates = []

    current = start
    while current <= end:
        status = "unknown"
        detail = {"status": "unknown", "destination": None, "travel_id": None}

        # Check UK intervals first
        for interval in uk_intervals:
            arr = interval["arrival"]
            ret = interval["return_date"]

            # Person is in UK at midnight on arrival_date through the night
            # before return_date. On return_date they depart, so NOT counted.
            if ret is not None:
                if arr <= current < ret:
                    status = "uk"
                    detail = {
                        "status": "uk",
                        "destination": interval["destination"],
                        "travel_id": interval["travel_id"],
                    }
                    break
            else:
                # No return date: assume still in UK from arrival onwards
                if current >= arr:
                    status = "uk"
                    detail = {
                        "status": "uk",
                        "destination": interval["destination"],
                        "travel_id": interval["travel_id"],
                    }
                    break

        # If not UK, check non-UK intervals
        if status == "unknown":
            for interval in non_uk_intervals:
                arr = interval["arrival"]
                ret = interval["return_date"]

                if ret is not None:
                    if arr <= current < ret:
                        status = "non_uk"
                        detail = {
                            "status": "non_uk",
                            "destination": interval["destination"],
                            "travel_id": interval["travel_id"],
                        }
                        break
                else:
                    if current >= arr:
                        status = "non_uk"
                        detail = {
                            "status": "non_uk",
                            "destination": interval["destination"],
                            "travel_id": interval["travel_id"],
                        }
                        break

        day_status[current] = status
        day_details[current] = detail
        if status == "uk":
            uk_midnight_dates.append(current)

        current += datetime.timedelta(days=1)

    return {
        "uk_midnight_dates": uk_midnight_dates,
        "total": len(uk_midnight_dates),
        "day_status": day_status,
        "day_details": day_details,
    }


def compute_uk_midnights_all_years(travels: list) -> Dict[str, Dict[str, Any]]:
    """Compute UK midnights for all tax years that have travel data."""
    from app.tax_year import tax_year_label as ty_label, all_tax_years_between

    if not travels:
        return {}

    # Find date range
    all_dates = []
    for t in travels:
        arr = t.arrival_date if hasattr(t, "arrival_date") else t["arrival_date"]
        if isinstance(arr, str):
            arr = datetime.date.fromisoformat(arr)
        all_dates.append(arr)
        ret = t.return_date if hasattr(t, "return_date") else t.get("return_date")
        if ret:
            if isinstance(ret, str):
                ret = datetime.date.fromisoformat(ret)
            all_dates.append(ret)

    min_date = min(all_dates)
    max_date = max(all_dates)

    start_ty = ty_label(min_date)
    end_ty = ty_label(max_date)
    years = all_tax_years_between(start_ty, end_ty)

    results = {}
    for yr in years:
        results[yr] = compute_uk_midnights_for_tax_year(yr, travels)

    return results


def compute_country_breakdown(day_details: dict) -> list:
    """Aggregate midnight counts by country from day_details.

    Args:
        day_details: dict mapping date -> {'status': ..., 'destination': ..., 'travel_id': ...}

    Returns:
        Sorted list of dicts: [{'country': str, 'midnights': int, 'is_uk': bool}, ...]
        Sorted by midnights descending. Unknown days (no travel record) are grouped
        under 'Unaccounted' if any exist.
    """
    from collections import Counter
    country_counts = Counter()
    uk_countries = set()

    for date, detail in day_details.items():
        status = detail.get("status", "unknown")
        destination = detail.get("destination") or ""

        if status == "uk":
            label = destination if destination else "United Kingdom"
            country_counts[label] += 1
            uk_countries.add(label)
        elif status == "non_uk":
            label = destination if destination else "Non-UK (unspecified)"
            country_counts[label] += 1
        else:  # unknown
            country_counts["Unaccounted"] += 1

    result = []
    for country, count in country_counts.most_common():
        result.append({
            "country": country,
            "midnights": count,
            "is_uk": country in uk_countries,
        })

    return result
