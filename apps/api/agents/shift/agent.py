"""Shift Allocation Agent — specialist agent (invoked as an AgentTool by the Coordinator,
Day 5). Reasons over live Firestore state through the burndown tool below; the underlying
fatigue/overtime math lives in burndown.py and is fully unit-tested independently of the LLM."""

from __future__ import annotations

from datetime import date

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from config import bootstrap_gemini_credentials, get_settings
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
        "'safe' risk level. If asked about a unit with no at-risk staff, say so plainly."
    ),
    tools=[FunctionTool(get_shift_burndown)],
)
