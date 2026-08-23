"""HR Agent — specialist agent (invoked as an AgentTool by the Coordinator). Owns
credential/license compliance monitoring and is the escalation target when the Shift
Allocation Agent runs out of same-unit reallocation options — HR's job at that point is to
find and activate compliant per-diem pool coverage. The underlying compliance and per-diem
matching math lives in credentialing.py and is fully unit-tested independently of the LLM."""

from __future__ import annotations

from datetime import date

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from config import bootstrap_gemini_credentials, get_settings
from services.payroll import compute_payroll_register
from services.platform.approvals import perform_or_request
from services.platform.observability import get_observability_service
from services.state import get_shift_history, get_staff_roster

from .credentialing import (
    compliance_summary,
    compute_credential_status,
    fatigue_risk_by_staff_id,
    flag_payroll_anomalies,
    perdiem_coverage_for_unit,
)

bootstrap_gemini_credentials()


def get_credential_compliance() -> dict:
    """Returns current license/credential compliance status for every staff member (including
    the per-diem pool), plus a per-unit compliance summary. Use this before recommending any
    credentialing action — it tells you who is 'valid', 'expiring_soon' (within 30 days), or
    'expired'."""
    staff = get_staff_roster()
    records = compute_credential_status(staff, as_of=date.today())
    return {
        "as_of": date.today().isoformat(),
        "credential_records": records,
        "unit_summary": compliance_summary(records),
    }


def find_perdiem_coverage(unit: str) -> dict:
    """Returns credential-compliant per-diem staff available to activate for `unit` — call
    this when Shift Allocation reports it has no same-unit reallocation options left for a
    critical-risk staff member. An expired credential disqualifies a per-diem staff member,
    so an empty result means genuinely no eligible coverage, not zero per-diem staff on
    file."""
    staff = get_staff_roster()
    eligible = perdiem_coverage_for_unit(staff, unit, as_of=date.today())
    return {"unit": unit, "eligible_perdiem_staff": eligible}


def flag_payroll_anomalies_for_period(period_start: str, period_end: str) -> dict:
    """Reviews a pay period's register (same computation routes/payroll.py's pay-run endpoint
    uses) against current fatigue risk and flags staff who are both drawing heavy overtime pay
    AND at elevated/critical fatigue risk right now — call this before recommending a pay run
    be approved, to catch staff who should be reallocated instead of kept on overtime. Dates
    are ISO (YYYY-MM-DD). Read-only, same as get_credential_compliance — this doesn't change
    payroll or notify anyone by itself."""
    with get_observability_service().span(
        "hr.flag_payroll_anomalies", {"period_start": period_start, "period_end": period_end}
    ) as span:
        staff = get_staff_roster()
        shift_history = get_shift_history()
        start = date.fromisoformat(period_start)
        end = date.fromisoformat(period_end)

        register = compute_payroll_register(staff, shift_history, start, end)
        risk_by_staff = fatigue_risk_by_staff_id(staff, shift_history, as_of=date.today())
        flagged = flag_payroll_anomalies(
            register["rows"], risk_by_staff, period_days=(end - start).days + 1
        )
        span.set_attribute("hr.flag_payroll_anomalies.flagged_count", len(flagged))

        return {
            "period_start": period_start,
            "period_end": period_end,
            "staff_count": register["staff_count"],
            "total_gross_pay": register["total_gross_pay"],
            "flagged": flagged,
        }


def notify_staff_credential_escalation(staff_id: str, message: str) -> dict:
    """Sends a credential/escalation notice to a specific staff member — call this after
    get_credential_compliance or find_perdiem_coverage to actually notify someone, not to
    decide who to notify. Gated behind manager approval by default (reconfigurable from the
    dashboard's policy editor); if approval is required, this returns a pending_approval
    status, not a confirmation the staff member was notified — report that honestly. For demo
    safety, the actual email always routes to the operations mailbox rather than the staff
    member's own address (staff_roster carries no real contact email in this dataset — see
    AGENTS.md's Gmail/approvals section), but the staff member's real name is shown to the
    manager throughout."""
    with get_observability_service().span(
        "hr.notify_staff_credential_escalation", {"staff_id": staff_id}
    ) as span:
        staff = {member["staff_id"]: member for member in get_staff_roster()}
        member = staff.get(staff_id)
        if member is None:
            span.set_attribute("hr.notify.error", "unknown_staff_id")
            return {"error": f"Unknown staff_id '{staff_id}'."}

        result = perform_or_request(
            task_type="notify_staff_credential_escalation",
            to=get_settings().manager_email,
            recipient_label=f"{member['name']} ({member['unit']})",
            subject=f"Credential/escalation notice for {member['name']}",
            body=message,
            requested_by="hr_agent",
        )
        span.set_attribute("hr.notify.status", result.get("status", "error"))
        return result


root_agent = Agent(
    model=get_settings().model_fast,
    name="hr_agent",
    description=(
        "Monitors hospital staff license/credential compliance and activates compliant "
        "per-diem coverage when a unit has run out of same-unit shift reallocation options."
    ),
    instruction=(
        "You are the HR Agent for a hospital's Fortified Enterprise Fleet. Call "
        "get_credential_compliance to see current license/credential status across all "
        "staff. Prioritize 'expired' over 'expiring_soon'; never flag 'valid' staff. When "
        "asked to cover a unit — typically because the Shift Allocation Agent has run out of "
        "same-unit reallocation options for a critical-risk staff member — call "
        "find_perdiem_coverage for that unit and recommend a named, credential-compliant "
        "per-diem staff member to activate. If find_perdiem_coverage returns no eligible "
        "staff, say so plainly rather than suggesting someone who isn't compliant. To actually "
        "notify a staff member about a credential issue or an escalation, call "
        "notify_staff_credential_escalation — this may require manager approval first, in "
        "which case the tool returns a pending_approval status; report that plainly "
        "('awaiting manager approval') rather than claiming the notice was sent. If asked to "
        "review a pay period before it's approved, call flag_payroll_anomalies_for_period with "
        "the period's start/end dates — it flags staff who are both drawing heavy overtime pay "
        "and at elevated/critical fatigue risk right now, so a manager can reallocate them "
        "before approving the run rather than after. This is read-only: it doesn't change "
        "payroll or notify anyone."
    ),
    tools=[
        FunctionTool(get_credential_compliance),
        FunctionTool(find_perdiem_coverage),
        FunctionTool(notify_staff_credential_escalation),
        FunctionTool(flag_payroll_anomalies_for_period),
    ],
)
