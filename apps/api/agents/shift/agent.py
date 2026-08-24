"""Shift Allocation Agent — specialist agent (invoked as an AgentTool by the Coordinator).
Reasons over live Firestore state through the burndown tool below; the underlying
fatigue/overtime math lives in burndown.py and is fully unit-tested independently of the LLM."""

from __future__ import annotations

from datetime import date

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from config import bootstrap_gemini_credentials, get_settings
from services.memory import search as search_memory
from services.platform.approvals import perform_or_request
from services.platform.observability import get_observability_service
from services.state import get_shift_history, get_staff_roster

from .burndown import compute_burndown, duty_job_sheet, unit_summary

bootstrap_gemini_credentials()

AGENT_NAME = "shift_allocation_agent"


async def recall_unit_history(unit: str, question: str) -> dict:
    """Recalls what has been observed about a unit at *earlier points* in this operation —
    Memory Bank holds a fact per unit written whenever the real-time fleet watch
    (services/fleet_watch.py) observed conditions changing enough to matter, so this is how you
    answer anything about a trend, a change over time, or "what happened earlier" rather than
    the current snapshot. `unit` is the unit name (e.g. "ICU"); `question` is what you want
    recalled (e.g. "when did critical fatigue first appear"). get_shift_burndown tells you about
    *now*; this tells you about *before*."""
    with get_observability_service().span("shift.recall_unit_history", {"unit": unit}) as span:
        try:
            facts = await search_memory(app_name=AGENT_NAME, user_id=unit, query=question)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            # Memory Bank being unreachable must degrade to "no history available" rather
            # than failing the whole turn — the agent can still answer from live state.
            span.set_attribute("shift.recall.error", type(exc).__name__)
            return {
                "unit": unit,
                "recalled_facts": [],
                "note": "Memory Bank is unavailable right now; answer from current state only.",
            }
        span.set_attribute("shift.recall.fact_count", len(facts))
        return {
            "unit": unit,
            "recalled_facts": facts,
            "note": (
                "No history recorded for this unit yet — the fleet watch may not have observed "
                "a change here yet."
                if not facts
                else f"{len(facts)} fact(s) recalled from earlier in this operation."
            ),
        }


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


def generate_duty_job_sheet(unit: str) -> dict:
    """Returns today's duty roster for `unit`: every assigned staff member, their role, and
    their current fatigue status — the printable sheet a shift supervisor would post. Read-only,
    no approval gate (an informational roster, not a consequential action) — use this when asked
    for "today's roster/duty sheet" for a unit, as distinct from get_shift_burndown's
    fleet-wide risk view."""
    staff = get_staff_roster()
    shifts = get_shift_history()
    records = compute_burndown(staff, shifts, as_of=date.today())
    return duty_job_sheet(staff, records, unit)


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
        "'safe' risk level. If asked about a unit with no at-risk staff, say so plainly. "
        "If the question is about a trend, a change over time, how a unit got here, or "
        "anything that happened on an earlier day, call recall_unit_history for that unit "
        "first — you have a persistent per-unit memory of every earlier day in this "
        "operation, and answering a 'has this been getting worse' question from today's "
        "snapshot alone is wrong. Cite the recalled days explicitly when you use them. To "
        "actually notify a staff member of a reallocation, call notify_staff_reallocation — "
        "this may require manager approval first, in which case the tool returns a "
        "pending_approval status; report that plainly ('awaiting manager approval') rather "
        "than claiming the staff member was notified. When asked for today's duty roster or "
        "job sheet for a unit, call generate_duty_job_sheet rather than get_shift_burndown — "
        "it returns exactly the staff/role/status list for that one unit."
    ),
    tools=[
        FunctionTool(get_shift_burndown),
        FunctionTool(recall_unit_history),
        FunctionTool(notify_staff_reallocation),
        FunctionTool(generate_duty_job_sheet),
    ],
)
