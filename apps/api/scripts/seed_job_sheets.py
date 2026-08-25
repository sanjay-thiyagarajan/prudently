"""Seeds the `job_sheets` Firestore collection (routes/job_sheets.py's facilities work-order
CRUD) with a representative spread of tickets — plain-CRUD data with no LLM/agent behind it
(see that module's own docstring for why), so seeding it directly here is the same honest-
synthetic move as packages/datagen's roster/inventory generators, not a shortcut around
anything real. Run via `uv run python -m scripts.seed_job_sheets` from apps/api.

Not idempotent the way seed_policy.py is (fixed doc IDs) — job sheets are auto-ID'd, matching
how a manager actually creates one via POST /job-sheets/facilities. Re-running adds a second
copy of each; only run once per fresh Firestore project."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from config import get_settings
from services.state import update_job_sheet, write_job_sheet

_NOW = datetime.now(timezone.utc)

# One per unit this fleet already tracks (ICU, ER, General Ward, Pharmacy, Respiratory,
# Facilities itself) — spread across every open/in_progress/completed status and every
# priority, so the dashboard's job-sheets table and the "Facilities" scoreboard both have
# real variety to show rather than one lonely ticket.
TICKETS: list[dict] = [
    {
        "title": "Replace ICU bed 4's IV pump",
        "description": "Pump is throwing an occlusion alarm intermittently; bed is out of "
        "rotation until replaced.",
        "location": "ICU",
        "assigned_to": "Biomed BM-01",
        "priority": "urgent",
        "status": "in_progress",
        "age_days": 1,
    },
    {
        "title": "Repair jammed door — ICU isolation room 2",
        "description": "Door latch sticks; isolation protocol can't be maintained until fixed.",
        "location": "ICU",
        "assigned_to": "Facilities FA-02",
        "priority": "urgent",
        "status": "open",
        "age_days": 0,
    },
    {
        "title": "Calibrate O2 monitoring station 3",
        "description": "Readings drifting ~2% high against the reference cylinder.",
        "location": "Respiratory",
        "assigned_to": "Biomed BM-02",
        "priority": "high",
        "status": "open",
        "age_days": 2,
    },
    {
        "title": "Repair leaking faucet — General Ward supply room",
        "description": "Slow drip, minor water pooling near the linen shelving.",
        "location": "General Ward",
        "assigned_to": "Facilities FA-01",
        "priority": "normal",
        "status": "open",
        "age_days": 3,
    },
    {
        "title": "Replace HVAC filter — General Ward unit 4",
        "description": "Scheduled quarterly filter swap.",
        "location": "General Ward",
        "assigned_to": "Facilities FA-01",
        "priority": "normal",
        "status": "in_progress",
        "age_days": 1,
    },
    {
        "title": "Fix flickering light — Pharmacy storage",
        "description": "Ballast likely failing; not urgent but distracting during counts.",
        "location": "Pharmacy",
        "assigned_to": "Facilities FA-02",
        "priority": "low",
        "status": "open",
        "age_days": 4,
    },
    {
        "title": "Replace broken wheelchair wheel — ER bay 2",
        "description": "Front caster wheel cracked; wheelchair pulled from service.",
        "location": "ER",
        "assigned_to": "Facilities FA-01",
        "priority": "low",
        "status": "completed",
        "age_days": 6,
    },
    {
        "title": "Monthly backup generator check",
        "description": "Routine load test and fuel-level check.",
        "location": "Facilities",
        "assigned_to": "Facilities FA-01",
        "priority": "normal",
        "status": "completed",
        "age_days": 8,
    },
]


def main() -> None:
    get_settings()  # fail fast on a broken .env before touching Firestore
    written = 0
    for ticket in TICKETS:
        created_at = _NOW - timedelta(days=ticket["age_days"])
        sheet = {
            "title": ticket["title"],
            "description": ticket["description"],
            "location": ticket["location"],
            "assigned_to": ticket["assigned_to"],
            "priority": ticket["priority"],
            "status": "open",
            "created_by": "seed_script",
            "created_at": created_at,
            "completed_at": None,
        }
        sheet_id = write_job_sheet(sheet)
        if ticket["status"] != "open":
            patch: dict = {"status": ticket["status"]}
            if ticket["status"] == "completed":
                patch["completed_at"] = created_at + timedelta(hours=6)
            update_job_sheet(sheet_id, patch)
        written += 1

    print(f"wrote {written} job_sheets docs")


if __name__ == "__main__":
    main()
