"""Surgical scheduling — dashboard-facing routes for the fleet's one patient-PII domain.

Two access tiers, matching services/auth.py's own stated rationale for `require_role` existing
at all (docs/threat-model.md finding 6): the schedule/conflict view carries no patient identity
at all (`get_surgical_cases`'s own docstring — case_id/patient_id-as-opaque-FK/procedure/room/
times/status only), so any authenticated user may see it; a case's *decrypted* patient record is
`require_role("admin", "clinician")`-gated, an `ops`-role viewer gets the schedule without who's
on it — a real least-privilege cut, not just a UI hint.

`caller="dashboard_route"` on every services/state.py accessor call below, matching
services/platform/access_control.py's allowlist — the manager/clinician clicking through the
dashboard is a different caller identity than the surgical_scheduling_agent's own LLM-driven
tool calls, even though both are permitted.

`notify_case_status_change` deliberately reuses agents/surgical_scheduling/agent.py's
`notify_patient_of_status_change_as` — the tool's reusable core — rather than re-implementing
the encryption/consent/approval/audit logic here a second time, same "reuse the already-tested
pure/tool logic directly from a route" precedent as routes/job_sheets.py's duty-sheet endpoint
reusing agents/shift/burndown.py's `duty_job_sheet`. It passes this route's own
`caller`/`requested_by` identity rather than the agent's — see that function's own docstring for
why the tool-facing `notify_patient_of_status_change` doesn't take those as parameters."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from agents.surgical_scheduling.agent import notify_patient_of_status_change_as
from agents.surgical_scheduling.conflicts import detect_conflicts
from services.auth import require_firebase_auth, require_role
from services.state import get_patient, get_surgical_case, get_surgical_cases, update_surgical_case

router = APIRouter(prefix="/surgical-schedule", tags=["surgical-schedule"])

_CALLER = "dashboard_route"
_REQUESTED_BY = "manager_dashboard"


class StatusUpdatePayload(BaseModel):
    new_status: str


class NotifyPayload(BaseModel):
    message: str


@router.get("/cases")
def list_cases(_uid: str = Depends(require_firebase_auth)) -> dict:
    """No patient identity in this payload at all — safe for any authenticated role, including
    ops. Conflicts are recomputed live rather than read from the last watch-cycle snapshot, so
    the dashboard always reflects the current schedule even between watch ticks."""
    cases = get_surgical_cases(caller=_CALLER)
    return {"cases": cases, "conflicts": detect_conflicts(cases)}


@router.get("/cases/{case_id}")
def get_case_detail(case_id: str, _uid: str = Depends(require_role("admin", "clinician"))) -> dict:
    """The one endpoint in this router that returns decrypted patient identity — admin/clinician
    only, per this module's own docstring."""
    case = get_surgical_case(case_id, caller=_CALLER)
    if case is None:
        raise HTTPException(status_code=404, detail=f"Unknown case_id '{case_id}'.")
    patient = get_patient(case["patient_id"], caller=_CALLER)
    return {**case, "patient": patient}


@router.post("/cases/{case_id}/status")
def update_case_status_route(
    case_id: str,
    payload: StatusUpdatePayload,
    _uid: str = Depends(require_role("admin", "clinician")),
) -> dict:
    case = get_surgical_case(case_id, caller=_CALLER)
    if case is None:
        raise HTTPException(status_code=404, detail=f"Unknown case_id '{case_id}'.")
    update_surgical_case(case_id, {"status": payload.new_status}, caller=_CALLER)
    return get_surgical_case(case_id, caller=_CALLER)


@router.post("/cases/{case_id}/notify")
def notify_case_status_change(
    case_id: str,
    payload: NotifyPayload,
    _uid: str = Depends(require_role("admin", "clinician")),
) -> dict:
    """Manual, manager-triggered equivalent of the agent's own autonomous notify path — same
    approval gate, same consent check, same audit trail, since it's the identical underlying
    logic, attributed to this route rather than to the agent."""
    return notify_patient_of_status_change_as(
        case_id, payload.message, caller=_CALLER, requested_by=_REQUESTED_BY
    )
