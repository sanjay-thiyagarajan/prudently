import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agents.shift.burndown import compute_burndown, unit_summary

TODAY = date(2026, 8, 21)

STAFF = [
    {
        "staff_id": "er-00",
        "name": "Nurse ER-00",
        "role": "nurse",
        "unit": "ER",
        "safe_weekly_hours": 40.0,
    },
    {
        "staff_id": "er-01",
        "name": "Nurse ER-01",
        "role": "nurse",
        "unit": "ER",
        "safe_weekly_hours": 40.0,
    },
    {
        "staff_id": "icu-00",
        "name": "Nurse ICU-00",
        "role": "nurse",
        "unit": "ICU",
        "safe_weekly_hours": 40.0,
    },
]


def shift(staff_id: str, days_ago: int, hours: float, unit: str = "ER") -> dict:
    shift_date = date(2026, 8, 21 - days_ago)
    return {
        "staff_id": staff_id,
        "shift_date": shift_date.isoformat(),
        "hours": hours,
        "unit": unit,
    }


def test_no_shifts_means_zero_hours_and_safe():
    records = compute_burndown(STAFF, [], TODAY)
    assert len(records) == 3
    assert all(r["trailing_hours"] == 0.0 for r in records)
    assert all(r["risk_level"] == "safe" for r in records)
    assert all(r["recommendation"] is None for r in records)


def test_only_counts_shifts_within_trailing_window():
    shifts = [
        shift("er-00", days_ago=1, hours=8),
        shift("er-00", days_ago=6, hours=8),
        shift("er-00", days_ago=8, hours=8),  # outside 7-day window, excluded
    ]
    records = compute_burndown(STAFF, shifts, TODAY)
    er00 = next(r for r in records if r["staff_id"] == "er-00")
    assert er00["trailing_hours"] == 16.0


def test_shift_on_as_of_date_itself_counts():
    shifts = [shift("er-00", days_ago=0, hours=8)]
    records = compute_burndown(STAFF, shifts, TODAY)
    er00 = next(r for r in records if r["staff_id"] == "er-00")
    assert er00["trailing_hours"] == 8.0


def test_risk_level_thresholds():
    # 40 safe hours: safe < 34, elevated 34-44, critical >= 44
    safe = [shift("er-00", d, 4) for d in range(7)]  # 28 hours -> ratio 0.7 -> safe
    records = compute_burndown(STAFF, safe, TODAY)
    assert next(r for r in records if r["staff_id"] == "er-00")["risk_level"] == "safe"

    elevated = [shift("er-01", d, 5) for d in range(7)]  # 35 hours -> ratio 0.875 -> elevated
    records = compute_burndown(STAFF, elevated, TODAY)
    assert next(r for r in records if r["staff_id"] == "er-01")["risk_level"] == "elevated"

    critical = [
        shift("icu-00", d, 8, unit="ICU") for d in range(7)
    ]  # 56 hours -> ratio 1.4 -> critical
    records = compute_burndown(STAFF, critical, TODAY)
    er_icu = next(r for r in records if r["staff_id"] == "icu-00")
    assert er_icu["risk_level"] == "critical"
    assert "reassign" in er_icu["recommendation"]


def test_records_sorted_highest_risk_first():
    shifts = [
        shift("er-00", 0, 4),  # low
        shift("icu-00", 0, 12, unit="ICU"),  # high
    ]
    records = compute_burndown(STAFF, shifts, TODAY)
    assert records[0]["staff_id"] == "icu-00"


def test_shifts_for_unknown_staff_id_are_ignored():
    shifts = [shift("ghost-99", 0, 100)]
    records = compute_burndown(STAFF, shifts, TODAY)
    assert len(records) == 3  # unchanged, no crash


def test_unit_summary_aggregates_risk_counts():
    shifts = [shift("er-00", d, 8) for d in range(7)]  # er-00 critical
    records = compute_burndown(STAFF, shifts, TODAY)
    summary = unit_summary(records)
    assert summary["ER"]["critical"] == 1
    assert summary["ER"]["safe"] == 1  # er-01 untouched
    assert summary["ICU"]["safe"] == 1
