"""Cloud Trace / Cloud Logging query routes — on-demand fetches for the agent detail page's
trace/log viewer, not a polled feed. A trace is fetched only when a manager clicks a specific
activity_log entry that carries a trace_id (see services/state.py's log_activity); logs are
fetched per agent, filtered by that agent's own Reasoning Engine resource label. Public, same
rationale as routes/agents.py and routes/dashboard.py: read-only, no financial/PII data, and
judges need the hosted URL reachable without a login present."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from google.cloud import logging as cloud_logging
from google.cloud.trace_v1 import TraceServiceClient

from services.state import FIRESTORE_PROJECT_ID, get_agent_registry

router = APIRouter(tags=["observability"])


@router.get("/traces/{trace_id}")
def get_trace(trace_id: str) -> dict:
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
def get_agent_logs(agent_name: str, limit: int = 50) -> dict:
    """Recent Cloud Logging entries for the Reasoning Engine hosting `agent_name`, filtered by
    that engine's `reasoning_engine_id` resource label (present on every
    aiplatform.googleapis.com/ReasoningEngine log entry). Coordinator's own engine bundles
    Shift/Inventory/Supply/HR/Chaos's flattened logic when reached via
    Coordinator, so log entries returned for those agents when invoked through Coordinator are
    engine-scoped, not cleanly agent-scoped — same caveat as the trace viewer."""
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
