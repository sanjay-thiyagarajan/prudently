import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from services.payroll import compute_gross_pay, hours_worked_in_period


def shift(staff_id: str, shift_date: str, hours: float, unit: str = "ER") -> dict:
    return {"staff_id": staff_id, "shift_date": shift_date, "hours": hours, "unit": unit}


def test_hours_worked_in_period_sums_only_matching_staff_within_range():
    shifts = [
        shift("a", "2026-08-01", 8),
        shift("a", "2026-08-02", 12),
        shift("a", "2026-08-15", 8),  # outside the period
        shift("b", "2026-08-01", 8),  # different staff
    ]
    total = hours_worked_in_period("a", date(2026, 8, 1), date(2026, 8, 7), shifts)
    assert total == 20


def test_hours_worked_in_period_inclusive_boundaries():
    shifts = [shift("a", "2026-08-01", 8), shift("a", "2026-08-07", 8)]
    total = hours_worked_in_period("a", date(2026, 8, 1), date(2026, 8, 7), shifts)
    assert total == 16


def test_hours_worked_in_period_no_matching_shifts():
    assert hours_worked_in_period("a", date(2026, 8, 1), date(2026, 8, 7), []) == 0.0


def test_compute_gross_pay():
    assert compute_gross_pay(hours_worked=40.0, hourly_rate=50.0) == 2000.0


def test_compute_gross_pay_rounds_to_cents():
    assert compute_gross_pay(hours_worked=33.333, hourly_rate=48.5) == round(33.333 * 48.5, 2)


def test_compute_gross_pay_zero_hours():
    assert compute_gross_pay(hours_worked=0.0, hourly_rate=110.0) == 0.0
