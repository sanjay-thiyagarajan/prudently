"""Manager-facing payroll admin — auth-gated (Firebase), same treatment as routes/policy.py:
compensation data, never mixed into the public /dashboard/overview feed (see routes/
dashboard.py's own note on why the approvals feed there is field-projected). Gross pay is
always computed server-side from the roster's own hourly_rate and shift_history, never taken
from the request body, so a client can't set an arbitrary rate or amount."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from google.cloud import firestore
from pydantic import BaseModel

from services.auth import require_firebase_auth
from services.payroll import compute_gross_pay, hours_worked_in_period
from services.state import (
    get_payroll_record,
    get_payroll_records,
    get_shift_history,
    get_staff_roster,
    update_payroll_record,
    write_payroll_record,
)

router = APIRouter(prefix="/payroll", tags=["payroll"])


class PayrollRecordPayload(BaseModel):
    staff_id: str
    pay_period_start: str  # ISO date
    pay_period_end: str  # ISO date


@router.get("/staff")
def list_staff(_uid: str = Depends(require_firebase_auth)) -> list[dict]:
    """Staff roster projected down to exactly what the payroll create-form's picker needs —
    including hourly_rate, safe here since this whole router is auth-gated."""
    return [
        {
            "staff_id": member["staff_id"],
            "name": member["name"],
            "unit": member["unit"],
            "role": member["role"],
            "hourly_rate": member.get("hourly_rate", 0.0),
        }
        for member in get_staff_roster()
    ]


@router.get("/records")
def list_records(_uid: str = Depends(require_firebase_auth)) -> list[dict]:
    return get_payroll_records()


@router.post("/records")
def create_record(payload: PayrollRecordPayload, uid: str = Depends(require_firebase_auth)) -> dict:
    staff = next(
        (member for member in get_staff_roster() if member["staff_id"] == payload.staff_id),
        None,
    )
    if staff is None:
        return {"error": f"Unknown staff_id '{payload.staff_id}'."}

    start = date.fromisoformat(payload.pay_period_start)
    end = date.fromisoformat(payload.pay_period_end)
    hours_worked = hours_worked_in_period(payload.staff_id, start, end, get_shift_history())
    hourly_rate = staff.get("hourly_rate", 0.0)

    record = {
        "staff_id": staff["staff_id"],
        "staff_name": staff["name"],
        "unit": staff["unit"],
        "role": staff["role"],
        "pay_period_start": payload.pay_period_start,
        "pay_period_end": payload.pay_period_end,
        "hours_worked": hours_worked,
        "hourly_rate": hourly_rate,
        "gross_pay": compute_gross_pay(hours_worked, hourly_rate),
        "status": "pending",
        "created_by": uid,
        "timestamp": firestore.SERVER_TIMESTAMP,
        "paid_at": None,
    }
    record_id = write_payroll_record(record)
    return get_payroll_record(record_id)


@router.post("/records/{record_id}/mark-paid")
def mark_paid(record_id: str, _uid: str = Depends(require_firebase_auth)) -> dict:
    """Idempotent, same "already decided" shape as approvals.py's resolve_approval — re-hitting
    an already-paid record returns its current state rather than erroring."""
    record = get_payroll_record(record_id)
    if record is None:
        return {"error": "not_found"}
    if record.get("status") == "paid":
        return {"error": "already_paid", **record}

    update_payroll_record(record_id, {"status": "paid", "paid_at": firestore.SERVER_TIMESTAMP})
    return get_payroll_record(record_id)
