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

# HR Agent (Day 4) credentialing + per-diem escalation pool.
PERDIEM_PER_UNIT = 2
CREDENTIAL_EXPIRY_SPREAD_DAYS = 400  # some staff land in the past (expired) or <30d (expiring)


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
    credential_expiry: str = ""  # ISO date
    is_per_diem: bool = False


def _assign_credential_expiry(
    staff: list[StaffMember], rng: random.Random, today: date
) -> list[StaffMember]:
    """Spreads credential expiry dates from -50 days (already expired) out to
    CREDENTIAL_EXPIRY_SPREAD_DAYS in the future, so the demo has a genuine mix of expired/
    expiring-soon/valid staff rather than an all-green roster. Uses its own rng instance
    (seeded independently from the roster/shift generation above) so this is purely additive
    and never perturbs the already-deployed shift_history data."""
    return [
        StaffMember(
            **{
                **asdict(member),
                "credential_expiry": (
                    today + timedelta(days=rng.randint(-50, CREDENTIAL_EXPIRY_SPREAD_DAYS))
                ).isoformat(),
            }
        )
        for member in staff
    ]


def _generate_perdiem_pool(rng: random.Random, today: date) -> list[StaffMember]:
    """Per-diem staff are a separate coverage pool, not part of the regular unit rotation —
    generated with no shift_history of their own so they read as genuinely available for HR
    to activate when Shift Allocation runs out of same-unit reallocation options."""
    pool: list[StaffMember] = []
    for unit in UNITS:
        for i in range(PERDIEM_PER_UNIT):
            role = rng.choice(ROLES[unit])
            pool.append(
                StaffMember(
                    staff_id=f"pd-{unit[:2].lower()}-{i:02d}",
                    name=f"Per-Diem {role.title()} {unit[:2].upper()}-{i:02d}",
                    role=role,
                    unit=unit,
                    credential_expiry=(
                        today + timedelta(days=rng.randint(-50, CREDENTIAL_EXPIRY_SPREAD_DAYS))
                    ).isoformat(),
                    is_per_diem=True,
                )
            )
    return pool


def generate_roster(
    seed: int, today: date | None = None
) -> tuple[list[StaffMember], list[ShiftRecord]]:
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

    # Credentialing + per-diem pool draw from their own rng streams (seed+1, seed+2) rather
    # than continuing to consume `rng` here, so this addition can never shift the shift-history
    # random draws above and change already-seeded/verified Shift Allocation demo data.
    credential_rng = random.Random(seed + 1)
    staff = _assign_credential_expiry(staff, credential_rng, today)
    perdiem_rng = random.Random(seed + 2)
    staff = staff + _generate_perdiem_pool(perdiem_rng, today)

    return staff, shifts


def as_dicts(staff: list[StaffMember], shifts: list[ShiftRecord]) -> tuple[list[dict], list[dict]]:
    return [asdict(s) for s in staff], [asdict(sh) for sh in shifts]
