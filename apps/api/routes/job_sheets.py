"""Job sheets — two genuinely different things sharing one router because they share one
mental model ("a sheet describing work to be done"), not one implementation.

**Duty roster** (`GET /job-sheets/duty/{unit}`) reuses agents/shift/burndown.py's
`duty_job_sheet` pure function directly — same "routes/, not an agent folder, so importing
agent pure-logic modules is fine" precedent routes/staff.py and routes/dashboard.py already
established. No LLM call, no approval gate: it's a read-only report, and paying for a model
call to reformat data the agent tool (agents/shift/agent.py's `generate_duty_job_sheet`) already
computes identically would be pure latency for a dashboard button.

**Facilities work orders** (`/job-sheets/facilities*`) are plain CRUD against a new
`job_sheets` Firestore collection — deliberately **not** a new agent. A maintenance ticket
("replace ICU bed 4's IV pump") doesn't need a model to reason about it the way a reorder
quantity or a reallocation does; adding an eighth Reasoning Engine (its own Terraform SA,
`requirements.txt`, Gateway policy entry, Coordinator `--extra_packages`, deploy step) for pure
CRUD would be infrastructure spent on a domain with no autonomy story. This is a deliberate
scope decision, not an oversight — see docs/threat-model.md and AGENTS.md for this project's
running theme of naming every such call explicitly rather than let it look accidental."""

from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from google.cloud import firestore

from agents.shift.burndown import compute_burndown, duty_job_sheet
from config import get_settings
from services.auth import require_firebase_auth
from services.platform.email import get_email_service
from services.platform.email_templates import job_sheet as render_job_sheet
from services.state import (
    get_job_sheet,
    get_job_sheets,
    get_shift_history,
    get_staff_roster,
    update_job_sheet,
    write_job_sheet,
)

router = APIRouter(prefix="/job-sheets", tags=["job-sheets"])

_VALID_PRIORITIES = {"low", "normal", "high", "urgent"}


@router.get("/duty/{unit}")
def get_duty_job_sheet(unit: str, _uid: str = Depends(require_firebase_auth)) -> dict:
    staff = get_staff_roster()
    shifts = get_shift_history()
    records = compute_burndown(staff, shifts, as_of=date.today())
    return duty_job_sheet(staff, records, unit)


@router.get("/facilities")
def list_facility_job_sheets(_uid: str = Depends(require_firebase_auth)) -> list[dict]:
    return get_job_sheets()


@router.post("/facilities")
def create_facility_job_sheet(body: dict, uid: str = Depends(require_firebase_auth)) -> dict:
    title = (body.get("title") or "").strip()
    if not title:
        raise HTTPException(status_code=422, detail="title is required.")
    priority = body.get("priority", "normal")
    if priority not in _VALID_PRIORITIES:
        raise HTTPException(status_code=422, detail=f"priority must be one of {_VALID_PRIORITIES}.")

    sheet = {
        "title": title,
        "description": body.get("description", ""),
        "location": body.get("location", ""),
        "assigned_to": body.get("assigned_to", "Unassigned"),
        "priority": priority,
        "status": "open",
        "created_by": uid,
        "created_at": firestore.SERVER_TIMESTAMP,
        "completed_at": None,
    }
    sheet_id = write_job_sheet(sheet)

    # Best-effort notification — mirrors services/platform/approvals.py's own "a Firestore/
    # email write failing must never take down the action that already happened" discipline.
    # Not approval-gated: creating a work order is the manager's own direct action, not
    # something an agent is asking permission for.
    try:
        plain, html = render_job_sheet(
            title=title,
            kind="Facilities work order",
            location=sheet["location"] or "Unspecified",
            assigned_to=sheet["assigned_to"],
            priority=priority,
            description=sheet["description"] or "No further detail provided.",
        )
        get_email_service().send(
            get_settings().manager_email, f"New work order: {title}", plain, html=html
        )
    except Exception:  # pylint: disable=broad-exception-caught
        pass

    return get_job_sheet(sheet_id)


@router.post("/facilities/{sheet_id}/start")
def start_facility_job_sheet(sheet_id: str, _uid: str = Depends(require_firebase_auth)) -> dict:
    sheet = get_job_sheet(sheet_id)
    if sheet is None:
        return {"error": "not_found"}
    if sheet["status"] != "open":
        return sheet
    update_job_sheet(sheet_id, {"status": "in_progress"})
    return get_job_sheet(sheet_id)


@router.post("/facilities/{sheet_id}/complete")
def complete_facility_job_sheet(sheet_id: str, _uid: str = Depends(require_firebase_auth)) -> dict:
    """Idempotent, same "already decided" shape as routes/payroll.py's mark_paid /
    routes/inventory.py's invoice_purchase_order."""
    sheet = get_job_sheet(sheet_id)
    if sheet is None:
        return {"error": "not_found"}
    if sheet["status"] == "completed":
        return sheet
    update_job_sheet(sheet_id, {"status": "completed", "completed_at": datetime.now(timezone.utc)})
    return get_job_sheet(sheet_id)
