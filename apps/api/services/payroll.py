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
