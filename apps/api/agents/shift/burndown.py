"""Fatigue/overtime burndown: tracks each staff member's cumulative hours worked in a
trailing window against a safe threshold, and flags reallocation risk as it rises. Pure
functions over plain dicts (matching the Firestore document shape from packages/datagen and
services/state.py) — no I/O, no ADK, so this is cheap to unit-test exhaustively."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

TRAILING_WINDOW_DAYS = 7
RiskLevel = Literal["safe", "elevated", "critical"]

# Ratio of trailing-window hours to safe_weekly_hours at which risk level changes.
ELEVATED_THRESHOLD = 0.85
CRITICAL_THRESHOLD = 1.10


def _parse_date(value: str) -> date:
    return datetime.fromisoformat(value).date()


def _risk_level(ratio: float) -> RiskLevel:
    if ratio >= CRITICAL_THRESHOLD:
        return "critical"
    if ratio >= ELEVATED_THRESHOLD:
        return "elevated"
    return "safe"


def _recommendation(risk: RiskLevel, staff_name: str, unit: str) -> str | None:
    if risk == "critical":
        return (
            f"{staff_name} ({unit}) is over the safe hours threshold — "
            "reassign upcoming shifts to a peer with headroom."
        )
    if risk == "elevated":
        return (
            f"{staff_name} ({unit}) is approaching the safe hours threshold — "
            "avoid adding overtime shifts this week."
        )
    return None


def compute_burndown(
    staff: list[dict],
    shifts: list[dict],
    as_of: date,
    window_days: int = TRAILING_WINDOW_DAYS,
) -> list[dict]:
    """Returns one burndown record per staff member, sorted highest-risk first."""
    hours_by_staff: dict[str, float] = {s["staff_id"]: 0.0 for s in staff}

    for shift in shifts:
        shift_date = _parse_date(shift["shift_date"])
        age_days = (as_of - shift_date).days
        if 0 <= age_days < window_days:
            staff_id = shift["staff_id"]
            if staff_id in hours_by_staff:
                hours_by_staff[staff_id] += shift["hours"]

    records: list[dict] = []
    for member in staff:
        staff_id = member["staff_id"]
        trailing_hours = hours_by_staff[staff_id]
        safe_hours = member.get("safe_weekly_hours", 40.0)
        ratio = trailing_hours / safe_hours if safe_hours else 0.0
        risk = _risk_level(ratio)

        records.append(
            {
                "staff_id": staff_id,
                "name": member["name"],
                "unit": member["unit"],
                "trailing_hours": trailing_hours,
                "safe_weekly_hours": safe_hours,
                "burndown_ratio": round(ratio, 3),
                "risk_level": risk,
                "recommendation": _recommendation(risk, member["name"], member["unit"]),
            }
        )

    records.sort(key=lambda r: r["burndown_ratio"], reverse=True)
    return records


def duty_job_sheet(staff: list[dict], burndown_records: list[dict], unit: str) -> dict:
    """A per-unit duty roster: who's assigned, their role, and their current fatigue status —
    the thing a shift supervisor would actually pin to a board. Built from the same
    `burndown_records` `compute_burndown` already produced, not a second computation over
    `shifts` — this function never touches Firestore or the raw shift history itself."""
    risk_by_id = {r["staff_id"]: r for r in burndown_records}
    roster = [
        {
            "staff_id": member["staff_id"],
            "name": member["name"],
            "role": member["role"],
            "risk_level": risk_by_id.get(member["staff_id"], {}).get("risk_level", "safe"),
            "trailing_hours": risk_by_id.get(member["staff_id"], {}).get("trailing_hours", 0.0),
        }
        for member in staff
        if member["unit"] == unit
    ]
    roster.sort(key=lambda r: (r["role"], r["name"]))
    return {"unit": unit, "staff": roster}


def unit_summary(burndown_records: list[dict]) -> dict[str, dict]:
    """Aggregate per-unit counts of at-risk staff — what the Coordinator/dashboard actually
    wants to show at a glance rather than the full per-staff list."""
    summary: dict[str, dict] = {}
    for record in burndown_records:
        unit = record["unit"]
        bucket = summary.setdefault(unit, {"safe": 0, "elevated": 0, "critical": 0})
        bucket[record["risk_level"]] += 1
    return summary
