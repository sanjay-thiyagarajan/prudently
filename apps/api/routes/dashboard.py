"""Dashboard data aggregation — one endpoint, one payload, read-only. Reuses every
specialist's already-tested pure-logic module (agents/*/{burndown,par_levels,reorder,
credentialing}.py) over live Firestore state rather than re-deriving any of that math here;
this route is a thin aggregator, not a second implementation, matching routes/sim.py's own
"reuse the pure logic, don't duplicate it" precedent."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter

from agents.hr.credentialing import (
    compliance_summary,
    compute_credential_status,
    guest_doctor_hours_summary,
)
from agents.inventory.par_levels import category_summary, compute_par_levels
from agents.shift.burndown import compute_burndown, unit_summary
from agents.supply.reorder import compute_reorders, vendor_summary
from services.admissions import recent_daily_trend, unit_totals
from services.state import (
    get_admissions,
    get_agent_registry,
    get_approvals,
    get_armor_events,
    get_chaos_experiments,
    get_inventory,
    get_shift_history,
    get_staff_roster,
    get_vendors,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def project_approval(record: dict) -> dict:
    """Never expose the manager's real email address or full request/email bodies on a public
    route — shared by this module's overview() and routes/agents.py's per-agent detail
    endpoint, both of which surface approvals publicly."""
    return {
        "task_type": record["task_type"],
        "status": record["status"],
        "recipient_label": record.get("recipient_label", record.get("to")),
        "subject": record["subject"],
        "requested_by": record["requested_by"],
        "timestamp": record["timestamp"],
    }


def build_overview() -> dict:
    """The actual aggregation, factored out of the `/overview` route handler so
    `routes/agents.py`'s per-agent detail endpoint can reuse the exact same computation rather
    than re-deriving any of it — same "reuse, don't duplicate" rationale as this module's own
    docstring."""
    staff = get_staff_roster()
    shifts = get_shift_history()
    items = get_inventory()
    vendors = get_vendors()
    today = date.today()

    burndown_records = compute_burndown(staff, shifts, as_of=today)
    par_records = compute_par_levels(items)
    reorder_decisions = compute_reorders(items, vendors)
    credential_records = compute_credential_status(staff, as_of=today)
    admissions_records = get_admissions()

    return {
        "as_of": today.isoformat(),
        "fleet": get_agent_registry(),
        "shift": {
            "records": burndown_records,
            "unit_summary": unit_summary(burndown_records),
        },
        "inventory": {
            "records": par_records,
            "category_summary": category_summary(par_records),
        },
        "supply": {
            "decisions": reorder_decisions,
            "vendor_summary": vendor_summary(reorder_decisions),
        },
        "hr": {
            "records": credential_records,
            "unit_summary": compliance_summary(credential_records),
        },
        "admissions": {
            "trend": recent_daily_trend(admissions_records),
            "unit_totals": unit_totals(admissions_records),
        },
        "guest_doctor_hours": guest_doctor_hours_summary(staff, shifts, as_of=today),
        "armor_events": get_armor_events(limit=20),
        "chaos_experiments": get_chaos_experiments(limit=20),
        "approvals": [project_approval(a) for a in get_approvals(limit=20)],
    }


@router.get("/overview")
def overview() -> dict:
    return build_overview()
