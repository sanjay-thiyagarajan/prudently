"""Chaos & Continuity Agent — specialist agent (invoked as an AgentTool by the Coordinator,
like every specialist except Medical Representative). Dual mode:

1. **Hospital-domain what-if** (`run_mass_casualty_whatif`): a read-only projection of what a
   mass-casualty patient surge would do to staffing burndown and inventory runway — see
   whatif.py for the pure math. Nothing here mutates live state; it's a hypothetical, not a
   simulation tick.

2. **Fleet-domain fault injection** — three experiments, each real against real infrastructure
   (Registry, Gateway, Model Armor, Memory Bank, Observability), not fabricated data:
   - `inject_kill_agent_fault`: does NOT take any real Reasoning Engine offline — that would be
     a destructive action against shared infrastructure this codebase has no standing
     authorization to take. Instead it calls the real Gateway (`before_tool_call`) exactly as
     Coordinator would, targeting an agent the Gateway will genuinely refuse — demonstrating
     the real code path a killed/unreachable agent triggers (a real block, a real span, real
     block text) without touching the target's actual deployment.
   - `inject_memory_poisoning_fault`: screens a real prompt-injection payload through the real
     Model Armor before ever calling `write_fact` — the write only happens if Armor accepts it,
     so a poisoned fact never actually reaches Memory Bank.
   - `inject_gateway_latency_fault`: sleeps for real inside Chaos's own Observability span, not
     inside the Gateway itself — deliberately not touching `gateway_local.py`'s before_tool_call
     (the one code path every Coordinator delegation traverses) for a demo-only feature.

Every experiment persists one record to `chaos_experiments` (services/state.py) — run once for
real against the deployed stack, replayed from there for the demo, never re-run live during
recording."""

from __future__ import annotations

import time
from datetime import date
from types import SimpleNamespace

from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from google.cloud import firestore

from config import bootstrap_gemini_credentials, get_settings
from services.memory import write_fact
from services.platform.armor import get_armor_service
from services.platform.gateway import get_gateway_service
from services.platform.observability import get_observability_service
from services.state import (
    get_inventory,
    get_shift_history,
    get_staff_roster,
    log_activity,
    write_chaos_experiment,
)

from .whatif import project_mass_casualty_surge

bootstrap_gemini_credentials()


def _persist(experiment_type: str, summary: str, result: dict, trace_id: str | None) -> None:
    # Best-effort, same as armor_events: a Firestore write failing must never take down the
    # experiment itself — the real action (Gateway call, Armor screen, sleep) already happened.
    try:
        write_chaos_experiment(
            {
                "experiment_type": experiment_type,
                "summary": summary,
                "result": result,
                "trace_id": trace_id,
                "timestamp": firestore.SERVER_TIMESTAMP,
            }
        )
    except Exception:  # pylint: disable=broad-exception-caught
        pass

    # Deliberately duplicated at each log_activity call site rather than factored into a
    # shared wrapper — same rationale as approvals.py's _log: this best-effort try/except is
    # five lines, not worth the fragility of sharing across agent-folder boundaries.
    # pylint: disable-next=duplicate-code
    try:
        log_activity(
            "chaos_continuity_agent",
            "chaos_experiment",
            summary,
            tool_name=experiment_type,
            trace_id=trace_id,
        )
    except Exception:  # pylint: disable=broad-exception-caught
        pass


def run_mass_casualty_whatif(additional_patients: int, unit: str, surge_days: int = 3) -> dict:
    """Hospital-domain what-if: projects staffing burndown and inventory runway impact if
    `additional_patients` arrived over `surge_days`, absorbed by `unit`. Read-only — pulls
    current staff_roster/shift_history/inventory from Firestore but writes nothing back and
    triggers no real escalation. Use this to answer "what would happen if" questions, not to
    actually initiate a surge response."""
    with get_observability_service().span(
        "chaos.mass_casualty_whatif",
        {"unit": unit, "additional_patients": additional_patients, "surge_days": surge_days},
    ) as span:
        staff = get_staff_roster()
        shifts = get_shift_history()
        items = get_inventory()
        result = project_mass_casualty_surge(
            staff, shifts, items, additional_patients, unit, surge_days, as_of=date.today()
        )
        span.set_attribute("chaos.would_need_hr_escalation", result["would_need_hr_escalation"])
        span.set_attribute(
            "chaos.would_need_expedited_reorder", result["would_need_expedited_reorder"]
        )
        _persist(
            "hospital_whatif",
            f"{additional_patients} additional patients into {unit} over {surge_days} days",
            result,
            span.trace_id,
        )
        return result


def inject_kill_agent_fault(target_agent: str) -> dict:
    """Fleet-domain fault injection: simulates `target_agent` being unreachable mid-task by
    calling the real Gateway exactly as if Chaos itself, not Coordinator, tried to reach it
    directly — and reporting whether the Gateway blocked the call and why. Does not take any
    real Reasoning Engine offline — see this module's docstring for why that's deliberately
    out of scope. Always blocks by design, on the caller-authorization rule (the Gateway's
    policy table only authorizes 'coordinator' as a caller — see gateway_local.py — so no
    other caller can ever reach a specialist directly, regardless of any agent's own registry
    status). Deliberately not keyed off `target_agent`'s registry status: that field can
    change out from under this tool on a later redeploy (an agent moving from 'planned' to
    'active' would silently flip this experiment from blocked to allowed), where the
    caller-authorization rule cannot — Chaos is never added to the policy table as an
    authorized caller."""
    with get_observability_service().span(
        "chaos.kill_agent_fault", {"target_agent": target_agent}
    ) as span:
        simulated_tool = SimpleNamespace(name=target_agent)
        # Not "coordinator": simulating Chaos itself attempting a direct specialist call,
        # which the Gateway's policy table never authorizes — see docstring above.
        simulated_context = SimpleNamespace(agent_name="chaos_continuity_agent")
        gateway_result = get_gateway_service().before_tool_call(
            simulated_tool, {}, simulated_context
        )
        blocked = gateway_result is not None
        span.set_attribute("chaos.blocked", blocked)

        result = {
            "target_agent": target_agent,
            "gateway_result": gateway_result,
            "would_be_blocked": blocked,
        }
        _persist(
            "fleet_kill_agent",
            f"Simulated {target_agent} unreachable — Gateway "
            + ("blocked" if blocked else "allowed")
            + " the call.",
            result,
            span.trace_id,
        )
        return result


async def inject_memory_poisoning_fault(poisoned_fact: str) -> dict:
    """Fleet-domain fault injection: screens a real prompt-injection payload through Model
    Armor before it would ever be written to Memory Bank via write_fact. If Armor blocks it
    (expected for a real injection payload), the write never happens — demonstrating the
    Memory Bank ingestion boundary is defended, not just the vendor-message one Medical
    Representative owns."""
    with get_observability_service().span("chaos.memory_poisoning_fault") as span:
        armor_result = get_armor_service().screen(poisoned_fact)
        span.set_attribute("chaos.blocked", armor_result.blocked)

        wrote_to_memory = False
        if not armor_result.blocked:
            await write_fact(
                app_name="chaos_continuity_agent",
                user_id="chaos-poisoning-experiment",
                fact=poisoned_fact,
                author="chaos_experiment",
            )
            wrote_to_memory = True

        result = {
            "blocked": armor_result.blocked,
            "matched_filters": list(armor_result.matched_filters),
            "reason": armor_result.reason,
            "wrote_to_memory": wrote_to_memory,
        }
        _persist(
            "fleet_memory_poisoning",
            (
                "Blocked before reaching Memory Bank"
                if armor_result.blocked
                else "Armor accepted it — written to Memory Bank"
            ),
            result,
            span.trace_id,
        )
        return result


def inject_gateway_latency_fault(inject_seconds: float = 2.0) -> dict:
    """Fleet-domain fault injection: sleeps for `inject_seconds` inside its own Observability
    span to demonstrate what a slow specialist hop looks like in Cloud Trace. Deliberately
    does not touch the real Gateway's before_tool_callback — see this module's docstring."""
    with get_observability_service().span(
        "chaos.latency_injection", {"chaos.inject_seconds": inject_seconds}
    ) as span:
        start = time.monotonic()
        time.sleep(inject_seconds)
        elapsed = time.monotonic() - start
        span.set_attribute("chaos.measured_elapsed_seconds", elapsed)

        result = {"inject_seconds": inject_seconds, "measured_elapsed_seconds": round(elapsed, 3)}
        _persist(
            "fleet_latency_injection",
            f"Injected {inject_seconds}s latency, measured {round(elapsed, 3)}s",
            result,
            span.trace_id,
        )
        return result


root_agent = Agent(
    model=get_settings().model_fast,
    name="chaos_continuity_agent",
    description=(
        "Dual-mode: hospital-domain what-if projections (mass-casualty surge impact on "
        "staffing and inventory) and fleet-domain fault injection (simulated agent outage, "
        "attempted Memory Bank poisoning, injected latency) — every experiment persisted to "
        "chaos_experiments."
    ),
    instruction=(
        "You are the Chaos & Continuity Agent for a hospital's Fortified Enterprise Fleet. "
        "For hospital-domain 'what if' questions about a patient surge, call "
        "run_mass_casualty_whatif with the additional patient count, the unit absorbing it, "
        "and the surge duration in days; report the staffing and inventory projections "
        "plainly, and say clearly whether HR escalation or an expedited reorder would be "
        "needed — this is a projection, not a real action, so never claim you actually "
        "escalated or reordered anything. For fleet-domain fault-injection requests, use "
        "inject_kill_agent_fault to test how the Gateway handles an unreachable agent, "
        "inject_memory_poisoning_fault to test whether Model Armor catches a poisoned memory "
        "write before it reaches Memory Bank, and inject_gateway_latency_fault to measure "
        "injected latency. Report each result precisely — blocked or not, and why — since "
        "these results get persisted and replayed later; never round up an ambiguous result "
        "to look more dramatic than it was."
    ),
    tools=[
        FunctionTool(run_mass_casualty_whatif),
        FunctionTool(inject_kill_agent_fault),
        FunctionTool(inject_memory_poisoning_fault),
        FunctionTool(inject_gateway_latency_fault),
    ],
)
