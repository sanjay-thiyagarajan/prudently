"""Shift Allocation Agent — specialist agent (invoked as an AgentTool by the Coordinator,
Day 5). Reasons over live Firestore state through the burndown tool below; the underlying
fatigue/overtime math lives in burndown.py and is fully unit-tested independently of the LLM."""

from __future__ import annotations

from datetime import date

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from config import bootstrap_gemini_credentials, get_settings
from services.platform.approvals import perform_or_request
from services.platform.observability import get_observability_service
from services.state import get_shift_history, get_staff_roster

from .burndown import compute_burndown, unit_summary

bootstrap_gemini_credentials()


def get_shift_burndown() -> dict:
    """Returns current fatigue/overtime burndown for every staff member, plus a per-unit
    risk summary. Use this before recommending any shift reallocation — it tells you who is
    safe, elevated, or critical against their safe weekly hours threshold."""
    staff = get_staff_roster()
    shifts = get_shift_history()
    records = compute_burndown(staff, shifts, as_of=date.today())
    return {
        "as_of": date.today().isoformat(),
        "staff_burndown": records,
        "unit_summary": unit_summary(records),
    }


def notify_staff_reallocation(staff_id: str, new_unit: str, shift_date: str) -> dict:
    """Notifies a staff member of a shift reallocation to `new_unit` on `shift_date` — call
    this after get_shift_burndown to actually notify someone, not to decide the reallocation
    yourself. Gated behind manager approval by default (reconfigurable from the dashboard's
    policy editor); if approval is required, this returns a pending_approval status, not a
    confirmation the staff member was notified — report that honestly. For demo safety, the
    actual email always routes to the operations mailbox rather than the staff member's own
    address (staff_roster carries no real contact email in this dataset — see AGENTS.md's
    Gmail/approvals section), but the staff member's real name is shown to the manager
    throughout."""
    with get_observability_service().span(
        "shift.notify_staff_reallocation", {"staff_id": staff_id, "new_unit": new_unit}
    ) as span:
        staff = {member["staff_id"]: member for member in get_staff_roster()}
        member = staff.get(staff_id)
        if member is None:
            span.set_attribute("shift.notify.error", "unknown_staff_id")
            return {"error": f"Unknown staff_id '{staff_id}'."}

        result = perform_or_request(
            task_type="notify_staff_reallocation",
            to=get_settings().manager_email,
            recipient_label=f"{member['name']} ({member['unit']})",
            subject=f"Shift reallocation: {member['name']} to {new_unit} on {shift_date}",
            body=(
                f"You are being reassigned to {new_unit} for your shift on {shift_date}, "
                "due to a fatigue/overtime burndown risk in your usual unit."
            ),
            requested_by="shift_allocation_agent",
        )
        span.set_attribute("shift.notify.status", result.get("status", "error"))
        return result


root_agent = Agent(
    model=get_settings().model_fast,
    name="shift_allocation_agent",
    description=(
        "Recommends hospital staff shift reallocation based on fatigue/overtime burndown "
        "— cumulative hours worked in the trailing 7 days against each staff member's safe "
        "weekly hours threshold."
    ),
    instruction=(
        "You are the Shift Allocation Agent for a hospital's Fortified Enterprise Fleet. "
        "Call get_shift_burndown to see current fatigue/overtime risk across all staff. "
        "When asked for a recommendation, prioritize staff flagged 'critical', then "
        "'elevated'. Be concrete: name the staff member, their unit, and the specific "
        "action (e.g. reassign an upcoming shift to a named peer with headroom in the same "
        "unit, or across units if none exists). Never recommend anything for staff at "
        "'safe' risk level. If asked about a unit with no at-risk staff, say so plainly. To "
        "actually notify a staff member of a reallocation, call notify_staff_reallocation — "
        "this may require manager approval first, in which case the tool returns a "
        "pending_approval status; report that plainly ('awaiting manager approval') rather "
        "than claiming the staff member was notified."
    ),
    tools=[FunctionTool(get_shift_burndown), FunctionTool(notify_staff_reallocation)],
)
