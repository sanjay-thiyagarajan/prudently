"""Per-agent detail aggregation — activities performed, approvals requested, pending
responsibilities, and the manager-configured policy governing that agent's approval-gated
tool, all in one payload for the dashboard's agent detail page. Public, same rationale as
`/dashboard/overview`: read-only aggregation of data that's already shown elsewhere on the
(login-gated) dashboard, not a write path or financial data."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from routes.dashboard import build_overview, project_approval
from services.state import get_activity_log, get_approval_policies, get_approvals

router = APIRouter(prefix="/agents", tags=["agents"])

# Hardcoded, same rationale as the frontend's own TASK_LABEL map
# (apps/web/src/components/workspace/PolicyEditor.tsx) and gateway_local.py's _POLICY_TABLE:
# the caller/task_type set is small and fixed for a fleet this size, easier to audit as a
# literal table than as a Firestore-backed one. Coordinator, Inventory, and Chaos have no
# approval-gated tool, so they're absent here rather than mapped to None.
_AGENT_TASK_TYPE: dict[str, str] = {
    "hr_agent": "notify_staff_credential_escalation",
    "shift_allocation_agent": "notify_staff_reallocation",
    "supply_chain_resiliency_agent": "contact_vendor_for_reorder",
    "medical_representative_agent": "send_vendor_reply",
}

# Same rationale: which slice of /dashboard/overview's payload is this agent's own "current
# responsibilities" state. Coordinator has none of its own (it delegates, it doesn't compute).
_AGENT_LIVE_STATE_KEYS: dict[str, tuple[str, ...]] = {
    "hr_agent": ("hr", "guest_doctor_hours"),
    "shift_allocation_agent": ("shift",),
    "supply_chain_resiliency_agent": ("supply",),
    "inventory_management_agent": ("inventory",),
    "medical_representative_agent": ("armor_events",),
    "chaos_continuity_agent": ("chaos_experiments",),
}


@router.get("/{agent_name}")
def get_agent_detail(agent_name: str) -> dict:
    overview = build_overview()
    registry_entry = next((a for a in overview["fleet"] if a["agent_name"] == agent_name), None)
    if registry_entry is None:
        raise HTTPException(status_code=404, detail=f"Unknown agent '{agent_name}'.")

    task_type = _AGENT_TASK_TYPE.get(agent_name)
    policy = next((p for p in get_approval_policies() if p["task_type"] == task_type), None)

    approvals = [
        project_approval(a) for a in get_approvals(limit=100) if a.get("requested_by") == agent_name
    ]

    return {
        "agent": registry_entry,
        "activity_log": get_activity_log(agent_name=agent_name, limit=100),
        "approvals": approvals,
        "policy": policy,
        "live_state": {key: overview[key] for key in _AGENT_LIVE_STATE_KEYS.get(agent_name, ())},
    }
