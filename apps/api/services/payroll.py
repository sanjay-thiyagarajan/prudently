"""Payroll pure logic — hours-in-period aggregation and gross-pay computation, kept separate
from routes/payroll.py so the money math is independently unit-tested, matching this
project's agents/*/*.py pure-logic-module convention."""

from __future__ import annotations

from datetime import date, datetime


def _parse_date(value: str) -> date:
    return datetime.fromisoformat(value).date()


def hours_worked_in_period(
    staff_id: str, start: date, end: date, shift_history: list[dict]
) -> float:
    """Sums shift_history hours for `staff_id` within [start, end] inclusive."""
    total = 0.0
    for shift in shift_history:
        if shift["staff_id"] != staff_id:
            continue
        if start <= _parse_date(shift["shift_date"]) <= end:
            total += shift["hours"]
    return total


def compute_gross_pay(hours_worked: float, hourly_rate: float) -> float:
    return round(hours_worked * hourly_rate, 2)


def compute_payroll_register(
    staff: list[dict], shift_history: list[dict], start: date, end: date
) -> dict:
    """Computes one pay-run's register in a single pass across the whole roster, reusing
    hours_worked_in_period/compute_gross_pay per staff member — the "everyone at once" sibling
    of routes/payroll.py's original one-staff-id-at-a-time create_record path. Staff with zero
    hours in the period are skipped (nothing to pay), not zero-filled, matching a real pay
    register's convention of only listing who actually worked."""
    rows: list[dict] = []
    unit_subtotals: dict[str, float] = {}
    total = 0.0
    for member in staff:
        hours = hours_worked_in_period(member["staff_id"], start, end, shift_history)
        if hours <= 0:
            continue
        rate = member.get("hourly_rate", 0.0)
        gross = compute_gross_pay(hours, rate)
        rows.append(
            {
                "staff_id": member["staff_id"],
                "staff_name": member["name"],
                "unit": member["unit"],
                "role": member["role"],
                "hours_worked": hours,
                "hourly_rate": rate,
                "gross_pay": gross,
            }
        )
        total += gross
        unit_subtotals[member["unit"]] = round(unit_subtotals.get(member["unit"], 0.0) + gross, 2)

    rows.sort(key=lambda r: (r["unit"], r["staff_name"]))
    return {
        "rows": rows,
        "staff_count": len(rows),
        "total_gross_pay": round(total, 2),
        "unit_subtotals": unit_subtotals,
    }
