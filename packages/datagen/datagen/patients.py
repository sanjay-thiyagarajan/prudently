"""Synthetic patients + surgical case schedule for the Surgical Scheduling Agent
(apps/api/agents/surgical_scheduling). Same honest-fabrication discipline as roster.py and
inventory.py: every value is procedurally generated from a small, clearly-combinatorial name
pool, never sourced from a real-person or real-record dataset — nobody could reasonably read a
name out of this generator as a specific real individual, since the same ~15x12 first/last-name
pool produces every patient in every seed. Unlike staff (`"Nurse IC-01"`), patients get
human-shaped full names on purpose: the point of this data is to give the field-level encryption
(services/platform/crypto.py) and RBAC (services/auth.py's require_role) something genuinely
PII-shaped to protect — a code-shaped identifier wouldn't exercise either control meaningfully.
"""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass, replace
from datetime import date, datetime, time, timedelta

_FIRST_NAMES = [
    "Margaret", "James", "Elena", "Marcus", "Priya", "Daniel", "Sofia", "Wei",
    "Amara", "Lucas", "Fatima", "Noah", "Yuki", "Diego", "Grace",
]
_LAST_NAMES = [
    "Chen", "Okafor", "Rossi", "Patel", "Nguyen", "Kowalski", "Silva", "Haddad",
    "Johansson", "Kim", "Delgado", "Novak", "Andersson", "Osei", "Rivera",
]

PROCEDURES = [
    ("Appendectomy", "General Surgery", 90),
    ("Total knee replacement", "Orthopedics", 150),
    ("Cataract surgery", "Ophthalmology", 45),
    ("Coronary bypass", "Cardiothoracic", 240),
    ("Hernia repair", "General Surgery", 75),
    ("Spinal fusion", "Orthopedics", 210),
    ("Gallbladder removal", "General Surgery", 80),
    ("Hip replacement", "Orthopedics", 165),
]

OPERATING_ROOMS = ["OR-1", "OR-2", "OR-3"]
CASE_COUNT = 10
CASE_STATUSES = ["scheduled", "confirmed"]


@dataclass(frozen=True)
class Patient:
    patient_id: str
    name: str
    date_of_birth: str  # ISO date — encrypted at write time, see services/state.py
    contact_email: str
    contact_phone: str
    notification_consent_email: bool


@dataclass(frozen=True)
class SurgicalCase:
    case_id: str
    patient_id: str
    procedure_name: str
    specialty: str
    surgeon_staff_id: str | None
    operating_room: str
    scheduled_start: str  # ISO datetime
    scheduled_end: str  # ISO datetime
    status: str


def _generate_name(rng: random.Random) -> str:
    return f"{rng.choice(_FIRST_NAMES)} {rng.choice(_LAST_NAMES)}"


def generate_patients(seed: int, count: int = CASE_COUNT) -> list[Patient]:
    """Deterministic given `seed`. One patient per case by design — this dataset models a
    day's surgical schedule, not a hospital-wide patient registry, so a 1:1 ratio is the
    honest shape rather than an oversimplification."""
    rng = random.Random(seed)
    patients: list[Patient] = []
    for i in range(count):
        dob = date(1945, 1, 1) + timedelta(days=rng.randint(0, 28000))  # ~1945-2021
        patients.append(
            Patient(
                patient_id=f"PT-{i:04d}",
                name=_generate_name(rng),
                date_of_birth=dob.isoformat(),
                contact_email=f"patient{i:04d}@example-mail.test",
                contact_phone=f"+1-555-01{i:02d}",
                notification_consent_email=rng.random() < 0.85,
            )
        )
    return patients


def generate_surgical_cases(
    patients: list[Patient],
    staff_surgeon_ids: list[str],
    seed: int,
    today: date | None = None,
) -> list[SurgicalCase]:
    """One case per patient, scheduled today, deliberately including exactly two genuine
    OR/surgeon double-bookings so `agents/surgical_scheduling/conflicts.py`'s conflict
    detection has something real to find at plain seed time — the same "organic pressure at
    seed time, no scripted trigger needed" discipline `AGENTS.md` documents for staff fatigue
    and inventory stock.

    The baseline schedule below is built to have **zero** incidental overlaps (each room's
    cases are laid out back-to-back with a buffer; at most one case per surgeon), then exactly
    two conflicts are forced afterward via `dataclasses.replace`. This is deliberate, not
    incidental precision: an earlier version cycled a handful of physician ids across every
    case with only 4 distinct time slots across 3 rooms, which produced a dozen *incidental*
    conflicts by pigeonhole — enough to fire a dozen autonomous-watch triggers in a single
    cycle (services/triggers.py's detect_schedule_conflict_triggers emits one per new conflict
    key, and services/autonomy.py's run_triggers runs them sequentially), well past the "one
    email" blast-radius the autonomous watch is designed around."""
    rng = random.Random(seed + 5)  # own stream — must never perturb patient generation above
    today = today or date.today()

    room_next_start = {room: datetime.combine(today, time(7, 0)) for room in OPERATING_ROOMS}
    cases: list[SurgicalCase] = []

    for i, patient in enumerate(patients):
        procedure_name, specialty, duration_min = rng.choice(PROCEDURES)
        room = OPERATING_ROOMS[i % len(OPERATING_ROOMS)]
        start = room_next_start[room]
        end = start + timedelta(minutes=duration_min)
        room_next_start[room] = end + timedelta(minutes=30)  # buffer before that room's next case
        # At most one case per surgeon in the baseline schedule — with only a handful of
        # physician-role staff on a given seed, cycling one surgeon across many cases is what
        # produced the incidental pileup described above. Cases past the surgeon pool's size
        # simply have no surgeon assigned yet, same as a real not-yet-staffed case.
        surgeon_id = staff_surgeon_ids[i] if i < len(staff_surgeon_ids) else None

        cases.append(
            SurgicalCase(
                case_id=f"CASE-{i:04d}",
                patient_id=patient.patient_id,
                procedure_name=procedure_name,
                specialty=specialty,
                surgeon_staff_id=surgeon_id,
                operating_room=room,
                scheduled_start=start.isoformat(),
                scheduled_end=end.isoformat(),
                status=rng.choice(CASE_STATUSES),
            )
        )

    if len(cases) > 1:
        # Deliberate conflict #1: case 1 double-booked into case 0's room and time.
        cases[1] = replace(
            cases[1],
            operating_room=cases[0].operating_room,
            scheduled_start=cases[0].scheduled_start,
            scheduled_end=cases[0].scheduled_end,
        )
    if len(cases) > 3 and cases[2].surgeon_staff_id is not None:
        # Deliberate conflict #2: case 3 double-booked into case 2's room, time, and surgeon.
        # Room is overridden too (not just time/surgeon) so case 3 doesn't collide with
        # whatever else its own *default* room/time slot would otherwise land on — matching
        # case 2's slot exactly keeps this a clean, isolated pair, same as conflict #1 above.
        cases[3] = replace(
            cases[3],
            operating_room=cases[2].operating_room,
            surgeon_staff_id=cases[2].surgeon_staff_id,
            scheduled_start=cases[2].scheduled_start,
            scheduled_end=cases[2].scheduled_end,
        )

    return cases


def as_dicts(
    patients: list[Patient], cases: list[SurgicalCase]
) -> tuple[list[dict], list[dict]]:
    return [asdict(p) for p in patients], [asdict(c) for c in cases]
