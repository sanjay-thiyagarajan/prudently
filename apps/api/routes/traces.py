"""Cloud Trace / Cloud Logging query routes — on-demand fetches for the agent detail page's
trace/log viewer, not a polled feed. A trace is fetched only when a manager clicks a specific
activity_log entry that carries a trace_id (see services/state.py's log_activity); logs are
fetched per agent, filtered by that agent's own Reasoning Engine resource label.

Auth-gated, unlike routes/agents.py/routes/dashboard.py (docs/threat-model.md finding 2): a raw
trace's span attributes carry the real manager_email and unredacted subjects (email_gmail.py
sets them as span attributes on every send), and raw log payloads are unfiltered text — neither
went through services/redaction.py, so this surface bypassed every redaction path built for the
public overview. This is the agent detail page's own "technical detail" drill-down, not the
judge-facing overview, so gating it costs nothing a judge needs."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from google.cloud import logging as cloud_logging
from google.cloud.trace_v1 import TraceServiceClient

from services.auth import require_firebase_auth
from services.memory import search as search_memory
from services.state import FIRESTORE_PROJECT_ID, get_agent_registry

router = APIRouter(tags=["observability"])

# Which agents actually have a Memory Bank store, and what a fact is scoped *to* for each — see
# services/memory.py's module docstring (per-agent engine, per-(unit|SKU|staff_id) isolation)
# and services/fleet_watch.py/services/triggers.py for where each one is actually written.
# Coordinator and Medical Representative are absent on purpose: Coordinator only delegates, and
# wiring an adversarial-input agent to a memory store it could poison was the one thing Memory
# Bank was deliberately never given (services/memory.py's own docstring).
_MEMORY_SUBJECT_LABEL: dict[str, str] = {
    "shift_allocation_agent": "unit",
    "inventory_management_agent": "SKU",
    "supply_chain_resiliency_agent": "SKU",
    "hr_agent": "staff member",
    "surgical_scheduling_agent": "conflict",
    "chaos_continuity_agent": "experiment",
}

_DEFAULT_RECALL_QUERY = "what has changed here recently, and when"


@router.get("/traces/{trace_id}")
def get_trace(trace_id: str, _uid: str = Depends(require_firebase_auth)) -> dict:
    """Fetches one Cloud Trace trace by ID and returns its spans as a flat list the frontend
    can render as a waterfall, sorted by start time. 404s (rather than a 500) for a trace ID
    that doesn't exist or hasn't finished exporting yet — Cloud Trace's own export is
    asynchronous, so a trace_id logged moments ago may briefly 404 before it lands."""
    client = TraceServiceClient()
    try:
        trace = client.get_trace(project_id=FIRESTORE_PROJECT_ID, trace_id=trace_id)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        raise HTTPException(
            status_code=404, detail=f"Trace '{trace_id}' not found (or not exported yet)."
        ) from exc

    spans = [
        {
            "span_id": str(span.span_id),
            "parent_span_id": str(span.parent_span_id) if span.parent_span_id else None,
            "name": span.name,
            "start_time": span.start_time.isoformat() if span.start_time else None,
            "end_time": span.end_time.isoformat() if span.end_time else None,
            "labels": dict(span.labels),
        }
        for span in trace.spans
    ]
    spans.sort(key=lambda s: s["start_time"] or "")
    return {"trace_id": trace_id, "spans": spans}


@router.get("/agents/{agent_name}/logs")
def get_agent_logs(
    agent_name: str, limit: int = 50, _uid: str = Depends(require_firebase_auth)
) -> dict:
    """Recent Cloud Logging entries for the Reasoning Engine hosting `agent_name`, filtered by
    that engine's `reasoning_engine_id` resource label (present on every
    aiplatform.googleapis.com/ReasoningEngine log entry). Coordinator's own engine bundles
    Shift/Inventory/Supply/HR/Chaos's flattened logic when reached via
    Coordinator, so log entries returned for those agents when invoked through Coordinator are
    engine-scoped, not cleanly agent-scoped — same caveat as the trace viewer."""
    limit = min(limit, 200)  # was unbounded — a caller-supplied limit shouldn't drive an
    # arbitrarily large Cloud Logging read.
    entry = next((a for a in get_agent_registry() if a["agent_name"] == agent_name), None)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Unknown agent '{agent_name}'.")
    reasoning_engine_id = entry.get("reasoning_engine_id")
    if not reasoning_engine_id:
        return {"agent_name": agent_name, "logs": []}

    client = cloud_logging.Client(project=FIRESTORE_PROJECT_ID)
    filter_str = (
        'resource.type="aiplatform.googleapis.com/ReasoningEngine" '
        f'AND resource.labels.reasoning_engine_id="{reasoning_engine_id}"'
    )
    entries = client.list_entries(
        filter_=filter_str, order_by=cloud_logging.DESCENDING, max_results=limit
    )

    def _text(log_entry) -> str:
        payload = log_entry.payload
        return payload if isinstance(payload, str) else str(payload)

    logs = [
        {
            "timestamp": log_entry.timestamp.isoformat() if log_entry.timestamp else None,
            "severity": log_entry.severity,
            "text": _text(log_entry),
        }
        for log_entry in entries
    ]
    return {"agent_name": agent_name, "logs": logs}


@router.get("/agents/{agent_name}/memory")
async def get_agent_memory(
    agent_name: str,
    subject: str,
    query: str = _DEFAULT_RECALL_QUERY,
    _uid: str = Depends(require_firebase_auth),
) -> dict:
    """What this agent actually recalls for one subject — the same Memory Bank similarity
    search its own `recall_*` tool runs (agents/shift/agent.py's `recall_unit_history` and
    inventory's equivalent), just reachable from the dashboard instead of only from a model
    turn. 404s for an agent with no memory store rather than a generic 502, so the frontend can
    tell "nothing recalled yet" apart from "this agent doesn't have memory"."""
    if agent_name not in _MEMORY_SUBJECT_LABEL:
        raise HTTPException(status_code=404, detail=f"'{agent_name}' has no Memory Bank store.")
    try:
        facts = await search_memory(app_name=agent_name, user_id=subject, query=query)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        raise HTTPException(status_code=502, detail=f"Memory Bank unavailable: {exc}") from exc
    return {
        "agent_name": agent_name,
        "subject": subject,
        "subject_label": _MEMORY_SUBJECT_LABEL[agent_name],
        "query": query,
        "facts": facts,
    }
