"""Staff Directory + per-staff profile — fatigue/credential status is already public
elsewhere (Shift/HR panels), but pay history is compensation data, so this whole router is
auth-gated the same way routes/payroll.py's whole router is, rather than splitting
sensitivity levels within one endpoint. Routes/, not an agent folder, so importing
agents.shift.burndown directly is fine here — no adk-deploy staging constraint applies outside
the agents/*/ folders (see services/fleet_watch.py's identical import for precedent)."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException

from agents.hr.credentialing import compute_credential_status
from agents.shift.burndown import compute_burndown
from services.auth import require_firebase_auth
from services.state import get_payroll_records, get_shift_history, get_staff_roster

router = APIRouter(prefix="/staff", tags=["staff"])

# Both routes below build a staff_id/name/role/unit/is_per_diem-shaped dict, coincidentally
# similar to agents/hr/credentialing.py's perdiem_coverage_for_unit — different projections
# (everyone here vs. eligible per-diem only there), not shared logic worth forcing into one
# helper. Same "deliberate duplication" treatment as services/platform/approvals.py's own
# disable/enable pair.
# pylint: disable=duplicate-code


@router.get("/")
def list_staff(_uid: str = Depends(require_firebase_auth)) -> list[dict]:
    """Roster for the Staff Directory's list view — credential status included, pay data
    excluded (matches routes/payroll.py's own separately-scoped /payroll/staff picker)."""
    staff = get_staff_roster()
    credential_by_id = {
        record["staff_id"]: record
        for record in compute_credential_status(staff, as_of=date.today())
    }
    return [
        {
            "staff_id": member["staff_id"],
            "name": member["name"],
            "role": member["role"],
            "unit": member["unit"],
            "is_per_diem": member.get("is_per_diem", False),
            "credential_status": credential_by_id.get(member["staff_id"], {}).get(
                "credential_status"
            ),
        }
        for member in staff
    ]


@router.get("/{staff_id}")
def get_staff_profile(staff_id: str, _uid: str = Depends(require_firebase_auth)) -> dict:
    """One staff member's profile: fatigue trend, credential status, and pay history —
    assembled from three already-existing pure-logic outputs, no new computation."""
    staff = get_staff_roster()
    member = next((m for m in staff if m["staff_id"] == staff_id), None)
    if member is None:
        raise HTTPException(status_code=404, detail=f"Unknown staff_id '{staff_id}'.")

    shift_history = get_shift_history()
    today = date.today()
    burndown_records = compute_burndown(staff, shift_history, as_of=today)
    fatigue = next((r for r in burndown_records if r["staff_id"] == staff_id), None)
    credential = next(
        (r for r in compute_credential_status(staff, as_of=today) if r["staff_id"] == staff_id),
        None,
    )
    pay_history = [
        record for record in get_payroll_records(limit=200) if record.get("staff_id") == staff_id
    ]

    return {
        "staff_id": member["staff_id"],
        "name": member["name"],
        "role": member["role"],
        "unit": member["unit"],
        "is_per_diem": member.get("is_per_diem", False),
        "hourly_rate": member.get("hourly_rate", 0.0),
        "fatigue": fatigue,
        "credential": credential,
        "pay_history": pay_history,
    }
