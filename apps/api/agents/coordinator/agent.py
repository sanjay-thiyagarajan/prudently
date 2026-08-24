"""Coordinator Agent — root, sole user-facing entry point. Wraps Shift Allocation, Inventory
Management, Supply Chain Resiliency, HR, Chaos & Continuity, and Surgical Scheduling as
`AgentTool` sub-agents (in-process, not over a network — each specialist's module is staged
alongside this one via `adk deploy`'s `--extra_packages` and imported directly; see AGENTS.md's
"Running / deploying an agent" section for the flattened top-level import this relies on).

Every specialist call from this agent routes through the Gateway interceptor
(services/platform/gateway.py, registered below as `before_tool_callback`) — Registry lookup,
policy-table authorization, then the real tool executes. Medical Representative is
deliberately NOT one of this agent's AgentTool sub-agents: it's reached exclusively via
genuine Agent2Agent from Supply Chain Resiliency (agents/supply/agent.py), not through this
Coordinator/Gateway path — that's the one boundary in the design that actually warrants a
separately-deployed, separately-identified agent."""

from __future__ import annotations

from google.adk.agents import Agent
from google.adk.tools import AgentTool

from config import bootstrap_gemini_credentials, get_settings
from services.platform.gateway import get_gateway_service

# pylint can't resolve these — they only exist as top-level packages once `adk deploy`'s
# --extra_packages flattens agents/shift, agents/inventory, etc. to /app/shift, /app/inventory
# or once ADK's own loader adds this file's parent dir (agents/) to sys.path for `adk
# run`/local dev. Neither is true for a plain `pylint agents` invocation from apps/api.
# pylint: disable-next=import-error,wrong-import-order
from chaos.agent import root_agent as chaos_agent

# pylint: disable-next=import-error,wrong-import-order
from hr.agent import root_agent as hr_agent

# pylint: disable-next=import-error,wrong-import-order
from inventory.agent import root_agent as inventory_agent

# pylint: disable-next=import-error,wrong-import-order
from shift.agent import root_agent as shift_agent

# pylint: disable-next=import-error,wrong-import-order
from supply.agent import root_agent as supply_agent

# pylint: disable-next=import-error,wrong-import-order
from surgical_scheduling.agent import root_agent as surgical_scheduling_agent

bootstrap_gemini_credentials()

root_agent = Agent(
    model=get_settings().model_reasoning,
    name="coordinator",
    description=(
        "Root agent for a hospital's Fortified Enterprise Fleet — the sole user-facing "
        "entry point, routing every specialist call through the Agent Gateway."
    ),
    instruction=(
        "You are the Coordinator for a hospital's Fortified Enterprise Fleet. You have six "
        "specialist sub-agents: shift_allocation_agent (fatigue/overtime, staff "
        "reallocation), inventory_management_agent (stock/par-level status), "
        "supply_chain_resiliency_agent (reorder decisions, vendor selection), hr_agent "
        "(credential compliance, per-diem coverage), chaos_continuity_agent "
        "(hospital-domain 'what if' surge projections, and fleet-domain fault-injection "
        "experiments), and surgical_scheduling_agent (operating-room/surgeon double-booking "
        "detection, patient status notifications). Delegate to whichever specialist(s) the "
        "question actually needs — don't guess at an answer yourself. For a broad status "
        "question (e.g. 'how are we doing'), check multiple specialists and synthesize a "
        "single coherent answer rather than dumping each one's raw output. If Shift reports a "
        "critical-risk staff member with no same-unit reallocation option, escalate to "
        "hr_agent to check per-diem coverage for that unit before telling the user nothing "
        "can be done. Only delegate to chaos_continuity_agent when the user explicitly asks a "
        "hypothetical 'what if' question or explicitly asks to run a fault-injection "
        "experiment — never invoke it to answer a normal operational question. You do not "
        "have direct access to Medical Representative — that agent is reached only by Supply "
        "Chain Resiliency via Agent2Agent, not by you directly. Several specialist actions "
        "(contacting a vendor, notifying staff, notifying a patient) are gated behind manager "
        "approval and return a pending_approval status rather than confirming the action "
        "happened — when a specialist reports that, relay it to the user honestly as awaiting "
        "manager approval, never as done."
    ),
    tools=[
        AgentTool(shift_agent),
        AgentTool(inventory_agent),
        AgentTool(supply_agent),
        AgentTool(hr_agent),
        AgentTool(chaos_agent),
        AgentTool(surgical_scheduling_agent),
    ],
    before_tool_callback=get_gateway_service().before_tool_call,
)
