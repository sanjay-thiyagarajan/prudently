"""Autonomous fleet watch — the impure half. services/triggers.py decides *what* the fleet
noticed; this module actually wakes a specialist agent up about it.

**Why this exists.** Until this module, every agent action in Prudently began with a human
typing a question. The sim clock advanced stock and staffing, the dashboard rendered the
consequences, and the agents sat idle until asked — which makes "agent-monitored hospital
operations" a description of the UI, not of the fleet. The watch closes that: at each
simulated-day boundary the fleet compares the world to how it left it, and where something
crossed a line it opens a real agent turn about it with nobody in the room.

**Why an in-process ADK Runner, not a stream_query to the deployed engine.** Two reasons, one
principled and one measured. Principled: this code already *is* the fleet — apps/api runs the
same agent objects the Reasoning Engines serve, so invoking them in-process is a genuine agent
turn (real model call, real tool calls, real Gateway/approval path), not a simulation of one.
Measured: `stream_query` against a deployed engine reset mid-stream on 3 of 4 attempts from
this environment, and a demo beat that fails three times out of four is not a demo beat. The
one thing the in-process path does not exercise is the Agent Engine transport itself, which
the manager-initiated path through the dashboard already covers.

**The approval gate is not bypassed.** An autonomously-triggered agent reaches exactly the same
`perform_or_request` path a manager-initiated one does, so a consequential action still emails
the manager and still waits. Autonomy here means the fleet decides *when to raise something*,
never that it acquired permission to act unsupervised. This is the whole reason the feature is
safe to ship: the blast radius of a false trigger is one email.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from services.memory import write_fact
from services.platform.observability import get_observability_service
from services.state import (
    log_activity,
    write_autonomous_action,
)
from services.triggers import Trigger

# Agent name -> the module path holding its root_agent. Imported lazily inside _agent_for so
# that importing this module (which routes/sim.py does at startup) doesn't pull every agent —
# and therefore every agent's model bootstrap — into the Cloud Run container's import graph
# before it is needed.
_AGENT_MODULES = {
    "shift_allocation_agent": "agents.shift.agent",
    "inventory_management_agent": "agents.inventory.agent",
    "supply_chain_resiliency_agent": "agents.supply.agent",
    "hr_agent": "agents.hr.agent",
}

# A single autonomous turn is one specialist answering one specific, already-scoped question.
# If it hasn't converged by this many events something is wrong (a tool loop, a model asking
# for clarification nobody will give) and the turn should be abandoned rather than left to
# burn tokens against a demo clock.
MAX_EVENTS_PER_TURN = 40

# Hard ceiling on how long the fleet may spend reacting to one trigger. The sim clock ticks
# roughly once a minute at the default speedup; a turn that outlives that would start
# overlapping the next tick.
TURN_TIMEOUT_SECONDS = 90


def _agent_for(agent_name: str):
    """Resolves an agent name to its ADK root_agent, importing the module on first use."""
    import importlib  # pylint: disable=import-outside-toplevel

    module_path = _AGENT_MODULES.get(agent_name)
    if module_path is None:
        raise ValueError(f"No autonomous-capable agent registered for '{agent_name}'.")
    return importlib.import_module(module_path).root_agent


async def _run_agent_turn(trigger: Trigger) -> tuple[str, int]:
    """Opens a real ADK session and runs one turn. Returns (final_text, tool_call_count).

    ADK is imported here rather than at module scope, and it is not a style preference: this
    module is imported by routes/sim.py at Cloud Run startup, and pulling the runner and
    session machinery in at import time pushed the container over its memory limit *during
    startup*. Cloud Run then reports only "the container failed to start and listen on PORT",
    which points at the port and not at memory — an hour of debugging in the wrong place. The
    watch is idle almost all the time; it should cost almost nothing until it fires.
    """
    # pylint: disable=import-outside-toplevel
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types as genai_types

    agent = _agent_for(trigger.agent)
    session_service = InMemorySessionService()
    runner = Runner(
        app_name=trigger.agent,
        agent=agent,
        session_service=session_service,
        auto_create_session=True,
    )

    message = genai_types.Content(role="user", parts=[genai_types.Part(text=trigger.prompt)])
    text_parts: list[str] = []
    tool_calls = 0
    events_seen = 0

    try:
        async for event in runner.run_async(
            user_id="fleet_watch",
            session_id=f"watch-{trigger.kind}-{uuid.uuid4().hex[:8]}",
            new_message=message,
        ):
            events_seen += 1
            if events_seen > MAX_EVENTS_PER_TURN:
                text_parts.append("\n[watch] Turn abandoned after exceeding the event budget.")
                break
            for part in (event.content.parts if event.content else []) or []:
                if getattr(part, "function_call", None):
                    tool_calls += 1
                if getattr(part, "text", None):
                    text_parts.append(part.text)
    finally:
        # Runner holds a plugin/tool lifecycle that must be closed, or the Cloud Run container
        # leaks an httpx client per trigger over a long demo.
        await runner.close()

    return "".join(text_parts).strip(), tool_calls


async def run_trigger(trigger: Trigger, sim_day: int) -> dict:
    """Acts on one trigger end to end: agent turn, audit log, memory write, Firestore record.

    Never raises. A watch that can take down the sim clock is worse than a watch that
    occasionally misses — the failure is recorded as a real `autonomous_actions` document with
    status "failed" so it is visible in the dashboard rather than swallowed.
    """
    with get_observability_service().span(
        "autonomy.run_trigger",
        {"trigger.kind": trigger.kind, "trigger.subject": trigger.subject},
    ) as span:
        record = {
            "trigger_kind": trigger.kind,
            "subject": trigger.subject,
            "agent_name": trigger.agent,
            "severity": trigger.severity,
            "summary": trigger.summary,
            "prompt": trigger.prompt,
            "sim_day": sim_day,
            "context": trigger.context,
            "trace_id": span.trace_id,
            "timestamp": datetime.now(timezone.utc),
        }

        try:
            response, tool_calls = await asyncio.wait_for(
                _run_agent_turn(trigger), timeout=TURN_TIMEOUT_SECONDS
            )
            record.update({"status": "completed", "response": response, "tool_calls": tool_calls})
            span.set_attribute("autonomy.tool_calls", tool_calls)
        except asyncio.TimeoutError:
            record.update(
                {
                    "status": "failed",
                    "response": f"Agent turn exceeded {TURN_TIMEOUT_SECONDS}s and was abandoned.",
                    "tool_calls": 0,
                }
            )
            span.set_attribute("autonomy.error", "timeout")
        except Exception as exc:  # pylint: disable=broad-exception-caught
            record.update(
                {"status": "failed", "response": f"{type(exc).__name__}: {exc}", "tool_calls": 0}
            )
            span.set_attribute("autonomy.error", type(exc).__name__)

        span.set_attribute("autonomy.status", record["status"])

        # Each of the three persistence steps is independently best-effort, matching every
        # other audit write in this codebase: none of them may take down the watch loop, and a
        # failure in one must not skip the others.
        try:
            record["id"] = write_autonomous_action(record)
        except Exception:  # pylint: disable=broad-exception-caught
            pass
        try:
            log_activity(
                trigger.agent,
                "autonomous_action",
                trigger.summary,
                tool_name=trigger.kind,
                status=record["status"],
                trace_id=span.trace_id,
                initiated_by="autonomous_watch",
            )
        except Exception:  # pylint: disable=broad-exception-caught
            pass
        try:
            await write_fact(
                app_name=trigger.agent,
                user_id=trigger.subject,
                fact=trigger.memory_fact,
                author="fleet_watch",
            )
        except Exception:  # pylint: disable=broad-exception-caught
            pass

        return record


async def run_triggers(triggers: list[Trigger], sim_day: int) -> list[dict]:
    """Runs triggers one at a time, not concurrently.

    Deliberate: two agents reacting at once would interleave their approval emails and their
    Cloud Trace spans, and the demo's whole value is that a viewer can follow one causal chain
    from a stock level crossing a line to an email landing in an inbox. Sequential also bounds
    the model spend a single tick can incur.
    """
    return [await run_trigger(trigger, sim_day) for trigger in triggers]
