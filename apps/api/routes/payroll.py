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
from services.payroll import compute_gross_pay, compute_payroll_register, hours_worked_in_period
from services.state import (
    get_payroll_record,
    get_payroll_records,
    get_payroll_records_by_run,
    get_payroll_run,
    get_payroll_runs,
    get_shift_history,
    get_staff_roster,
    mark_payroll_run_records_paid,
    update_payroll_record,
    update_payroll_run,
    write_payroll_record,
    write_payroll_records_batch,
    write_payroll_run,
)

router = APIRouter(prefix="/payroll", tags=["payroll"])


class PayrollRecordPayload(BaseModel):
    staff_id: str
    pay_period_start: str  # ISO date
    pay_period_end: str  # ISO date


class PayrollRunPayload(BaseModel):
    period_start: str  # ISO date
    period_end: str  # ISO date


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


@router.get("/runs")
def list_runs(_uid: str = Depends(require_firebase_auth)) -> list[dict]:
    return get_payroll_runs()


@router.post("/runs")
def create_run(payload: PayrollRunPayload, uid: str = Depends(require_firebase_auth)) -> dict:
    """Computes a pay-run register for the whole roster in one pass (compute_payroll_register)
    and persists it immediately as a draft run plus one payroll_records line item per staff
    member — "review the register" means viewing this draft, not holding unsaved state on the
    client. approve/disburse below transition it forward."""
    start = date.fromisoformat(payload.period_start)
    end = date.fromisoformat(payload.period_end)
    register = compute_payroll_register(get_staff_roster(), get_shift_history(), start, end)

    run = {
        "period_start": payload.period_start,
        "period_end": payload.period_end,
        "status": "draft",
        "created_at": firestore.SERVER_TIMESTAMP,
        "created_by": uid,
        "staff_count": register["staff_count"],
        "total_gross_pay": register["total_gross_pay"],
        "unit_subtotals": register["unit_subtotals"],
    }
    run_id = write_payroll_run(run)

    records = [
        {
            **row,
            "pay_period_start": payload.period_start,
            "pay_period_end": payload.period_end,
            "run_id": run_id,
            "status": "pending",
            "created_by": uid,
            "timestamp": firestore.SERVER_TIMESTAMP,
            "paid_at": None,
        }
        for row in register["rows"]
    ]
    write_payroll_records_batch(records)

    return {**get_payroll_run(run_id), "records": get_payroll_records_by_run(run_id)}


@router.get("/runs/{run_id}")
def get_run(run_id: str, _uid: str = Depends(require_firebase_auth)) -> dict:
    run = get_payroll_run(run_id)
    if run is None:
        return {"error": "not_found"}
    return {**run, "records": get_payroll_records_by_run(run_id)}


@router.post("/runs/{run_id}/approve")
def approve_run(run_id: str, _uid: str = Depends(require_firebase_auth)) -> dict:
    """Idempotent, same "already decided" shape as mark_paid above."""
    run = get_payroll_run(run_id)
    if run is None:
        return {"error": "not_found"}
    if run.get("status") in ("approved", "disbursed"):
        return run

    update_payroll_run(run_id, {"status": "approved", "approved_at": firestore.SERVER_TIMESTAMP})
    return get_payroll_run(run_id)


@router.post("/runs/{run_id}/disburse")
def disburse_run(run_id: str, _uid: str = Depends(require_firebase_auth)) -> dict:
    """Only fires from `approved` — a manager must approve before money moves. Idempotent
    against a repeat call once disbursed, same shape as every other terminal-state transition
    in this router."""
    run = get_payroll_run(run_id)
    if run is None:
        return {"error": "not_found"}
    if run.get("status") == "disbursed":
        return run
    if run.get("status") != "approved":
        return {"error": "must_be_approved_first", **run}

    mark_payroll_run_records_paid(run_id)
    update_payroll_run(run_id, {"status": "disbursed", "disbursed_at": firestore.SERVER_TIMESTAMP})
    return get_payroll_run(run_id)
