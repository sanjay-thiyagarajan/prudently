"""Credential compliance + per-diem escalation: flags staff whose license/credential has
expired or is expiring soon, and finds compliant per-diem pool staff available to cover a
unit — the target HR is escalated to (via the Coordinator, Day 5) when Shift Allocation runs
out of same-unit reallocation options. Pure functions over plain dicts (matching the Firestore
document shape from packages/datagen/datagen/roster.py and services/state.py) — no I/O, no
ADK, so this is cheap to unit-test exhaustively."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

CredentialStatus = Literal["valid", "expiring_soon", "expired"]

# Days-until-expiry at or under which a still-valid credential counts as "expiring_soon".
EXPIRING_SOON_WINDOW_DAYS = 30


def _parse_date(value: str) -> date:
    return datetime.fromisoformat(value).date()


def _credential_status(expiry: date, as_of: date) -> CredentialStatus:
    days_left = (expiry - as_of).days
    if days_left < 0:
        return "expired"
    if days_left <= EXPIRING_SOON_WINDOW_DAYS:
        return "expiring_soon"
    return "valid"


def compute_credential_status(staff: list[dict], as_of: date) -> list[dict]:
    """Returns one credential record per staff member (including per-diem pool staff),
    sorted most-urgent first (expired, then soonest-expiring)."""
    records: list[dict] = []
    for member in staff:
        expiry = _parse_date(member["credential_expiry"])
        status = _credential_status(expiry, as_of)
        records.append(
            {
                "staff_id": member["staff_id"],
                "name": member["name"],
                "role": member["role"],
                "unit": member["unit"],
                "is_per_diem": member.get("is_per_diem", False),
                "credential_expiry": member["credential_expiry"],
                "days_until_expiry": (expiry - as_of).days,
                "credential_status": status,
            }
        )

    records.sort(key=lambda r: r["days_until_expiry"])
    return records


def compliance_summary(credential_records: list[dict]) -> dict[str, dict]:
    """Aggregate per-unit counts of credential status — what the Coordinator/dashboard
    actually wants to show at a glance rather than the full per-staff list."""
    summary: dict[str, dict] = {}
    for record in credential_records:
        unit = record["unit"]
        bucket = summary.setdefault(unit, {"valid": 0, "expiring_soon": 0, "expired": 0})
        bucket[record["credential_status"]] += 1
    return summary


def perdiem_coverage_for_unit(staff: list[dict], unit: str, as_of: date) -> list[dict]:
    """Returns per-diem pool staff for `unit` who are credential-compliant (not expired) and
    therefore eligible to activate right now — an expired credential disqualifies a per-diem
    staff member from being offered as coverage, same as it would for a scheduled shift."""
    eligible: list[dict] = []
    for member in staff:
        if not member.get("is_per_diem", False) or member["unit"] != unit:
            continue
        expiry = _parse_date(member["credential_expiry"])
        status = _credential_status(expiry, as_of)
        if status == "expired":
            continue
        eligible.append(
            {
                "staff_id": member["staff_id"],
                "name": member["name"],
                "role": member["role"],
                "unit": member["unit"],
                "credential_status": status,
            }
        )
    return eligible


def guest_doctor_hours_summary(
    staff: list[dict], shifts: list[dict], as_of: date, window_days: int = 28
) -> list[dict]:
    """Trailing-window hours worked by the per-diem/guest-doctor pool — same trailing-window
    math as agents/shift/burndown.py's compute_burndown, scoped to is_per_diem staff only.
    Explicit output fields (never a raw roster dict passthrough) — this feeds the dashboard's
    public overview, and hourly_rate/credential_expiry must never leak through it."""
    perdiem_ids = {member["staff_id"] for member in staff if member.get("is_per_diem")}
    hours_by_staff: dict[str, float] = {staff_id: 0.0 for staff_id in perdiem_ids}

    for shift in shifts:
        staff_id = shift["staff_id"]
        if staff_id not in hours_by_staff:
            continue
        shift_date = _parse_date(shift["shift_date"])
        age_days = (as_of - shift_date).days
        if 0 <= age_days < window_days:
            hours_by_staff[staff_id] += shift["hours"]

    lookup = {member["staff_id"]: member for member in staff}
    return [
        {
            "staff_id": staff_id,
            "name": lookup[staff_id]["name"],
            "unit": lookup[staff_id]["unit"],
            "role": lookup[staff_id]["role"],
            "hours": hours_by_staff[staff_id],
        }
        for staff_id in sorted(perdiem_ids)
    ]
