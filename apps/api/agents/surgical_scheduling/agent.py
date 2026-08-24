"""Surgical Scheduling Agent — specialist agent (invoked as an AgentTool by the Coordinator).
Owns the surgical case schedule and the one patient-facing notification channel in this
codebase. The conflict-detection math lives in conflicts.py and is fully unit-tested
independently of the LLM, matching this project's agents/*/*.py pure-logic-module convention.

**Patient PII discipline, stated once here rather than per-tool:** every accessor this agent's
tools call passes `caller="surgical_scheduling_agent"` through to services/state.py, which
checks it against services/platform/access_control.py's allowlist before touching the
`patients`/`surgical_cases` collections — see that module's own docstring for exactly what this
does and does not protect against. `get_surgical_schedule`/`detect_scheduling_conflicts`
deliberately never decrypt or return patient identity — a schedule/conflict view only ever needs
case_id/room/surgeon/time, and the fewer tools that ever see a decrypted name, the smaller the
surface a compromised turn could leak it through. Only `notify_patient_of_status_change` reaches
patient identity at all, and only the one field it needs (name) to address the notification."""

from __future__ import annotations

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from config import bootstrap_gemini_credentials, get_settings
from services.platform.approvals import perform_or_request
from services.platform.email_templates import patient_notification
from services.platform.observability import get_observability_service
from services.state import (
    get_patient,
    get_surgical_case,
    get_surgical_cases,
    update_surgical_case,
    write_patient_notification_log,
)

from .conflicts import detect_conflicts

bootstrap_gemini_credentials()

AGENT_NAME = "surgical_scheduling_agent"
_CALLER = AGENT_NAME  # the self-declared identity every state.py accessor call below passes


def get_surgical_schedule() -> dict:
    """Returns every active surgical case: procedure, specialty, surgeon, operating room, and
    scheduled window. No patient identity — this is the schedule, not the chart. Use this
    before recommending anything about a case."""
    return {"cases": get_surgical_cases(caller=_CALLER)}


def detect_scheduling_conflicts() -> dict:
    """Returns every pair of cases that double-book the same operating room or the same
    surgeon at an overlapping time. Call this to check for conflicts before recommending a
    reschedule — don't just eyeball get_surgical_schedule's list."""
    conflicts = detect_conflicts(get_surgical_cases(caller=_CALLER))
    return {"conflicts": conflicts}


def update_case_status(case_id: str, new_status: str) -> dict:
    """Updates a case's own status (e.g. to 'delayed' or 'confirmed') — an internal scheduling
    record change, not an external action, so this is not approval-gated (unlike
    notify_patient_of_status_change below). Call this first when resolving a conflict — decide
    which case moves and update its status — then notify the affected patient separately."""
    with get_observability_service().span(
        "surgical_scheduling.update_case_status", {"case_id": case_id, "new_status": new_status}
    ) as span:
        case = get_surgical_case(case_id, caller=_CALLER)
        if case is None:
            span.set_attribute("surgical_scheduling.error", "unknown_case_id")
            return {"error": f"Unknown case_id '{case_id}'."}
        update_surgical_case(case_id, {"status": new_status}, caller=_CALLER)
        return {"case_id": case_id, "status": new_status}


def notify_patient_of_status_change(case_id: str, message: str) -> dict:
    """Notifies the patient on `case_id` of a status change (a delay, a reschedule, a
    confirmation) — call this after update_case_status, not instead of it. Approval-gated by
    default (reconfigurable from the dashboard's policy editor), same "nothing runs unattended"
    discipline every other consequential action in this fleet follows. Sends only if the
    patient has opted into email notifications (notification_consent_email) — if they haven't,
    this returns a `consent_declined` status and does not send anything, regardless of approval
    policy. Every send or decline is written to a dedicated `patient_notification_log` entry,
    separate from the general activity feed, because PHI-adjacent notification history deserves
    its own audit trail."""
    return notify_patient_of_status_change_as(
        case_id, message, caller=_CALLER, requested_by=AGENT_NAME
    )


def notify_patient_of_status_change_as(
    case_id: str, message: str, *, caller: str, requested_by: str
) -> dict:
    """The reusable core of the tool above, exported so routes/surgical_scheduling.py's
    manager-triggered notify endpoint can call the identical encryption/consent/approval/audit
    logic with its own identity (`caller="dashboard_route"`, `requested_by="manager_dashboard"`)
    instead of silently borrowing the agent's — attributing a human-initiated action to the
    agent would be the same conflation AGENTS.md's autonomous-watch section calls out for
    `initiated_by` ("would let the fleet take credit for acting unprompted when it didn't"), just
    in the opposite direction.

    Deliberately **not** exposed as tool parameters on `notify_patient_of_status_change` itself:
    ADK's FunctionTool only strips a `tool_context` parameter from what it hands the model, so a
    `caller`/`requested_by` kwarg on the tool-facing function would let the LLM supply its own
    value for either — an attacker-controlled or merely hallucinated identity string reaching
    services/platform/access_control.py's allowlist check and approvals.py's audit trail. Only
    trusted Python call sites (this agent's own tool wrapper, the dashboard route) may choose
    those two values."""
    with get_observability_service().span(
        "surgical_scheduling.notify_patient", {"case_id": case_id}
    ) as span:
        case = get_surgical_case(case_id, caller=caller)
        if case is None:
            span.set_attribute("surgical_scheduling.error", "unknown_case_id")
            return {"error": f"Unknown case_id '{case_id}'."}
        patient = get_patient(case["patient_id"], caller=caller)
        if patient is None:
            span.set_attribute("surgical_scheduling.error", "unknown_patient")
            return {"error": f"Unknown patient_id '{case['patient_id']}'."}

        _log_notification(case, patient, message, status="pending", span=span)

        if not patient.get("notification_consent_email"):
            span.set_attribute("surgical_scheduling.consent", "declined")
            _log_notification(case, patient, message, status="consent_declined", span=span)
            name = patient["name"]
            return {
                "status": "consent_declined",
                "message": f"{name} has not opted into email notifications — nothing sent.",
            }

        plain, html = patient_notification(
            patient_name=patient["name"],
            procedure_name=case["procedure_name"],
            status_message=message,
            scheduled_at=case["scheduled_start"],
        )
        result = perform_or_request(
            task_type="notify_patient_of_status_change",
            to=get_settings().manager_email,
            recipient_label=f"{patient['name']} ({case_id})",
            subject=f"Update on your {case['procedure_name']}",
            body=plain,
            requested_by=requested_by,
            html=html,
        )
        _log_notification(case, patient, message, status=result.get("status", "error"), span=span)
        span.set_attribute("surgical_scheduling.notify_status", result.get("status", "error"))
        return result


def _log_notification(case: dict, patient: dict, message: str, *, status: str, span) -> None:
    """Best-effort, same 'a Firestore write failing must never take down the action that
    already happened' discipline as services/platform/approvals.py's own _log. Writes to
    `patient_notification_log`, not `activity_log` — PHI-adjacent access needs its own audit
    trail, not folded into the general fleet activity feed (see this file's module docstring)."""
    try:
        write_patient_notification_log(
            {
                "case_id": case["case_id"],
                "patient_id": patient["patient_id"],
                "channel": "email",
                "message": message,
                "status": status,
                "trace_id": span.trace_id,
            }
        )
    except Exception:  # pylint: disable=broad-exception-caught
        pass


root_agent = Agent(
    model=get_settings().model_fast,
    name=AGENT_NAME,
    description=(
        "Owns the surgical case schedule — detects operating-room/surgeon double-bookings and "
        "notifies patients of status changes."
    ),
    instruction=(
        "You are the Surgical Scheduling Agent for a hospital's Fortified Enterprise Fleet. "
        "Call get_surgical_schedule to see the current case list, and "
        "detect_scheduling_conflicts to check for OR/surgeon double-bookings — always check "
        "for conflicts before recommending anything. When you find a conflict, decide which of "
        "the two cases should move (prefer moving the case with the later scheduled_start, "
        "unless one procedure is clearly more time-sensitive), call update_case_status on that "
        "case with a new status of 'delayed', and then call notify_patient_of_status_change "
        "with a clear, plain-language explanation — the patient is not hospital staff, so "
        "never use internal jargon like 'OR conflict' or 'double-booked'; say something like "
        "'your procedure has been rescheduled to avoid a scheduling conflict.' "
        "notify_patient_of_status_change may require manager approval first, in which case it "
        "returns a pending_approval status — report that plainly rather than claiming the "
        "patient was already notified. If the patient has not consented to email notification, "
        "the tool returns consent_declined — report that plainly too, and do not attempt any "
        "other notification channel. Never invent a conflict that detect_scheduling_conflicts "
        "did not return."
    ),
    tools=[
        FunctionTool(get_surgical_schedule),
        FunctionTool(detect_scheduling_conflicts),
        FunctionTool(update_case_status),
        FunctionTool(notify_patient_of_status_change),
    ],
)
