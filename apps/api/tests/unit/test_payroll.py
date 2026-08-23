import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from services.payroll import compute_gross_pay, compute_payroll_register, hours_worked_in_period


def shift(staff_id: str, shift_date: str, hours: float, unit: str = "ER") -> dict:
    return {"staff_id": staff_id, "shift_date": shift_date, "hours": hours, "unit": unit}


def member(staff_id: str, name: str, unit: str, role: str, hourly_rate: float) -> dict:
    return {
        "staff_id": staff_id,
        "name": name,
        "unit": unit,
        "role": role,
        "hourly_rate": hourly_rate,
    }


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


def test_compute_payroll_register_computes_per_staff_rows_and_totals():
    staff = [
        member("a", "Nurse A", "ER", "nurse", 48.0),
        member("b", "Nurse B", "ICU", "nurse", 52.0),
    ]
    shifts = [
        shift("a", "2026-08-01", 8, unit="ER"),
        shift("a", "2026-08-02", 12, unit="ER"),
        shift("b", "2026-08-01", 8, unit="ICU"),
    ]
    register = compute_payroll_register(staff, shifts, date(2026, 8, 1), date(2026, 8, 7))

    assert register["staff_count"] == 2
    assert register["total_gross_pay"] == round(20 * 48.0 + 8 * 52.0, 2)
    assert register["unit_subtotals"] == {"ER": round(20 * 48.0, 2), "ICU": round(8 * 52.0, 2)}
    row_a = next(r for r in register["rows"] if r["staff_id"] == "a")
    assert row_a["hours_worked"] == 20
    assert row_a["gross_pay"] == round(20 * 48.0, 2)


def test_compute_payroll_register_skips_staff_with_no_hours_in_period():
    staff = [member("a", "Nurse A", "ER", "nurse", 48.0)]
    register = compute_payroll_register(staff, [], date(2026, 8, 1), date(2026, 8, 7))
    assert register["rows"] == []
    assert register["staff_count"] == 0
    assert register["total_gross_pay"] == 0.0
    assert register["unit_subtotals"] == {}


def test_compute_payroll_register_sorts_rows_by_unit_then_name():
    staff = [
        member("a", "Zed", "ICU", "nurse", 50.0),
        member("b", "Ann", "ER", "nurse", 50.0),
        member("c", "Bob", "ER", "nurse", 50.0),
    ]
    shifts = [shift(s["staff_id"], "2026-08-01", 8, unit=s["unit"]) for s in staff]
    register = compute_payroll_register(staff, shifts, date(2026, 8, 1), date(2026, 8, 7))
    ordered = [(r["unit"], r["staff_name"]) for r in register["rows"]]
    assert ordered == [("ER", "Ann"), ("ER", "Bob"), ("ICU", "Zed")]
