"""Synthetic staff roster + rolling shift history for the Shift Allocation Agent's
fatigue/overtime burndown calculation (see apps/api/agents/shift/burndown.py, Day 3)."""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass
from datetime import date, timedelta

UNITS = ["ER", "ICU", "General Ward", "Pharmacy"]
ROLES = {
    "ER": ["nurse", "physician", "tech"],
    "ICU": ["nurse", "physician"],
    "General Ward": ["nurse", "tech"],
    "Pharmacy": ["pharmacist", "tech"],
}
STAFF_PER_UNIT = 6
HISTORY_DAYS = 28  # trailing 4 weeks, matches the burndown window in the plan
SAFE_SHIFT_HOURS = 8
OVERTIME_SHIFT_HOURS = 12


@dataclass(frozen=True)
class ShiftRecord:
    staff_id: str
    shift_date: str  # ISO date
    hours: float
    unit: str


@dataclass(frozen=True)
class StaffMember:
    staff_id: str
    name: str
    role: str
    unit: str
    safe_weekly_hours: float = 40.0


def generate_roster(seed: int, today: date | None = None) -> tuple[list[StaffMember], list[ShiftRecord]]:
    """Deterministic given `seed` — same seed always produces the same roster/history."""
    rng = random.Random(seed)
    today = today or date.today()

    staff: list[StaffMember] = []
    shifts: list[ShiftRecord] = []

    for unit in UNITS:
        for i in range(STAFF_PER_UNIT):
            role = rng.choice(ROLES[unit])
            staff_id = f"{unit[:2].lower()}-{i:02d}"
            staff.append(
                StaffMember(
                    staff_id=staff_id,
                    name=f"{role.title()} {unit[:2].upper()}-{i:02d}",
                    role=role,
                    unit=unit,
                )
            )

    for day_offset in range(HISTORY_DAYS, 0, -1):
        shift_date = today - timedelta(days=day_offset)
        for member in staff:
            # Most days: one safe shift. ~15% chance of a double/overtime shift, biased
            # slightly higher for ER/ICU to give the burndown metric something real to flag
            # even before the scripted flu surge kicks in.
            overtime_bias = 0.22 if member.unit in ("ER", "ICU") else 0.12
            if rng.random() < 0.08:
                continue  # day off
            hours = OVERTIME_SHIFT_HOURS if rng.random() < overtime_bias else SAFE_SHIFT_HOURS
            shifts.append(
                ShiftRecord(
                    staff_id=member.staff_id,
                    shift_date=shift_date.isoformat(),
                    hours=hours,
                    unit=member.unit,
                )
            )

    return staff, shifts


def as_dicts(staff: list[StaffMember], shifts: list[ShiftRecord]) -> tuple[list[dict], list[dict]]:
    return [asdict(s) for s in staff], [asdict(sh) for sh in shifts]
