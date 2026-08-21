"""HR Agent — specialist agent (invoked as an AgentTool by the Coordinator, Day 5). Owns
credential/license compliance monitoring and is the escalation target when the Shift
Allocation Agent runs out of same-unit reallocation options — HR's job at that point is to
find and activate compliant per-diem pool coverage. The underlying compliance and per-diem
matching math lives in credentialing.py and is fully unit-tested independently of the LLM."""

from __future__ import annotations

from datetime import date

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from config import bootstrap_gemini_credentials, get_settings
from services.state import get_staff_roster

from .credentialing import compliance_summary, compute_credential_status, perdiem_coverage_for_unit

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
        "staff, say so plainly rather than suggesting someone who isn't compliant."
    ),
    tools=[FunctionTool(get_credential_compliance), FunctionTool(find_perdiem_coverage)],
)
