"""Approval-gating helper for agent tool calls that need a real hospital-facing side effect
(contacting a vendor, notifying staff) gated behind manager approval. Not wired via
`before_tool_callback` -- that's Coordinator-only (see gateway.py) and doesn't cover a
standalone/sub-agent's own FunctionTool calls. Called directly from inside each new tool
function's body instead, mirroring agents/chaos/agent.py's existing pattern of calling
platform services (Gateway, Armor, Observability) directly rather than through a callback.

There is no pending/wait/resume mechanism anywhere in this codebase (confirmed against
gateway.py: before_tool_call is fully synchronous, return value only). An approval-gated call
therefore can't pause mid-turn -- perform_or_request returns a "pending_approval" result
immediately, and the real send happens later, fully decoupled, triggered by an HTTP hit from
the manager's email client (routes/approvals.py) -- never replayed against agent logic, since
nothing in this codebase could resume the agent turn that requested it."""

from __future__ import annotations

import secrets

from google.cloud import firestore

from config import PUBLIC_API_BASE_URL, get_settings
from services.platform.email import get_email_service
from services.platform.observability import get_observability_service
from services.state import (
    get_approval,
    get_approval_policy,
    log_activity,
    update_approval,
    write_approval,
    write_email_log,
)

_DEFAULT_POLICY = {
    "requires_approval": True,
    "approver_email": None,
    "notify_emails": [],
    "notify_on_complete": True,
}


def check_policy(task_type: str) -> dict:
    """Reads approval_policy/{task_type} from Firestore. Fails closed: a task type with no
    policy doc requires approval -- an unconfigured task type must never silently auto-send."""
    policy = get_approval_policy(task_type)
    if policy is None:
        return dict(_DEFAULT_POLICY)
    return {**_DEFAULT_POLICY, **policy}


# Deliberately duplicated rather than importing agents/chaos/agent.py's near-identical
# _persist() across an agent-folder boundary — same rationale as agents/supply/reorder.py and
# agents/chaos/whatif.py's own duplicated helpers (adk deploy's per-folder staging doesn't
# survive cross-agent-folder imports; two five-line best-effort persistence wrappers aren't
# worth the fragility of sharing).
# pylint: disable=duplicate-code
def _log(task_type: str, to: str, subject: str, result, trace_id: str | None) -> None:
    # Best-effort, same as write_armor_event/write_chaos_experiment: a Firestore write failing
    # must never take down the real send that already happened.
    try:
        write_email_log(
            {
                "task_type": task_type,
                "to": to,
                "subject": subject,
                "sent": result.sent,
                "service_error": result.service_error,
                "trace_id": trace_id,
                "timestamp": firestore.SERVER_TIMESTAMP,
            }
        )
    except Exception:  # pylint: disable=broad-exception-caught
        pass


# pylint: enable=duplicate-code


# Internal helper, called from exactly one call site (perform_or_request) purely to keep that
# function's own local-variable count under pylint's threshold — the parameter count here is a
# direct consequence of that split, not a design smell worth restructuring further.
# pylint: disable-next=too-many-arguments,too-many-positional-arguments
def _request_approval(
    task_type: str,
    to: str,
    recipient_label: str,
    subject: str,
    body: str,
    requested_by: str,
    policy: dict,
    trace_id,
) -> dict:
    token = secrets.token_urlsafe(24)
    approver_email = policy["approver_email"] or get_settings().manager_email

    write_approval(
        token,
        {
            "task_type": task_type,
            "status": "pending",
            "to": to,
            "recipient_label": recipient_label,
            "subject": subject,
            "body": body,
            "requested_by": requested_by,
            "notify_emails": policy["notify_emails"],
            "notify_on_complete": policy["notify_on_complete"],
            "timestamp": firestore.SERVER_TIMESTAMP,
            "decided_at": None,
        },
    )

    request_body = (
        f"{requested_by} wants to: {subject}\n\nTo: {recipient_label}\n\n{body}\n\n"
        f"Approve: {PUBLIC_API_BASE_URL}/approvals/{token}/approve\n"
        f"Reject: {PUBLIC_API_BASE_URL}/approvals/{token}/reject\n"
    )
    request_result = get_email_service().send(
        approver_email, f"Approval needed: {subject}", request_body
    )
    _log(task_type, approver_email, f"Approval needed: {subject}", request_result, trace_id)

    # Best-effort, same as write_armor_event/write_chaos_experiment: a Firestore write failing
    # must never take down the approval request itself, which already happened.
    try:
        log_activity(
            requested_by,
            "action_requested",
            subject,
            tool_name=task_type,
            status="pending_approval",
            trace_id=trace_id,
        )
    except Exception:  # pylint: disable=broad-exception-caught
        pass

    return {
        "status": "pending_approval",
        "approval_id": token,
        "approver_email": approver_email,
        "message": f"Awaiting manager approval before contacting {recipient_label}.",
    }


# pylint: disable-next=too-many-arguments,too-many-positional-arguments
def perform_or_request(
    task_type: str, to: str, recipient_label: str, subject: str, body: str, requested_by: str
) -> dict:
    """The single entry point every approval-gated tool calls. `to` is the address actually
    used (routed to the operations mailbox for demo safety — see the four agent tools'
    docstrings for why: neither staff_roster nor vendors carries a real contact email in this
    dataset, and fabricating one risks emailing an address nobody controls). `recipient_label`
    is the real-world party a human should see instead ("MedSupply Primary", "Tech ER-00") —
    it's what the pending-approval message, the Firestore record, and the confirm-page all
    show, so the demo reads as "contacting the vendor," not "contacting the ops mailbox."

    If the manager-configured policy for `task_type` doesn't require approval, sends
    immediately (copying any configured notify_emails) and returns a normal success dict. If
    it does, writes a pending `approvals` record, emails the approver an approve/reject link,
    and returns a `pending_approval` dict so the calling LLM reports this honestly instead of
    claiming the action already happened."""
    with get_observability_service().span(
        "approvals.perform_or_request", {"approvals.task_type": task_type}
    ) as span:
        policy = check_policy(task_type)

        if not policy["requires_approval"]:
            span.set_attribute("approvals.decision", "sent_immediately")
            notify = policy["notify_emails"] if policy["notify_on_complete"] else None
            result = get_email_service().send(to, subject, body, cc=notify)
            _log(task_type, to, subject, result, span.trace_id)
            try:
                log_activity(
                    requested_by,
                    "action_sent",
                    subject,
                    tool_name=task_type,
                    status="sent",
                    trace_id=span.trace_id,
                )
            except Exception:  # pylint: disable=broad-exception-caught
                pass
            return {
                "status": "sent",
                "sent": result.sent,
                "service_error": result.service_error,
                "to": recipient_label,
            }

        span.set_attribute("approvals.decision", "pending_approval")
        return _request_approval(
            task_type, to, recipient_label, subject, body, requested_by, policy, span.trace_id
        )


def resolve_approval(token: str, decision: str) -> dict:
    """Used by routes/approvals.py's POST handlers -- the actual state mutation + real send,
    fully decoupled from whatever agent turn originally requested it. Idempotent: re-resolving
    an already-decided token never double-sends, it just reports the prior decision."""
    with get_observability_service().span(
        "approvals.resolve_approval", {"approvals.decision_requested": decision}
    ) as span:
        record = get_approval(token)
        if record is None:
            span.set_attribute("approvals.outcome", "not_found")
            return {"error": "not_found"}
        if record["status"] != "pending":
            span.set_attribute("approvals.outcome", "already_decided")
            return {"error": "already_decided", "status": record["status"]}

        if decision == "approved":
            result = get_email_service().send(
                record["to"],
                record["subject"],
                record["body"],
                cc=record["notify_emails"] if record["notify_on_complete"] else None,
            )
            _log(record["task_type"], record["to"], record["subject"], result, span.trace_id)
            update_approval(
                token,
                {
                    "status": "approved",
                    "decided_at": firestore.SERVER_TIMESTAMP,
                    "sent": result.sent,
                    "service_error": result.service_error,
                },
            )
            span.set_attribute("approvals.outcome", "approved")
            try:
                log_activity(
                    record["requested_by"],
                    "action_resolved",
                    record["subject"],
                    tool_name=record["task_type"],
                    status="approved",
                    trace_id=span.trace_id,
                )
            except Exception:  # pylint: disable=broad-exception-caught
                pass
            return {
                "status": "approved",
                "sent": result.sent,
                "service_error": result.service_error,
            }

        update_approval(token, {"status": "rejected", "decided_at": firestore.SERVER_TIMESTAMP})
        span.set_attribute("approvals.outcome", "rejected")
        try:
            log_activity(
                record["requested_by"],
                "action_resolved",
                record["subject"],
                tool_name=record["task_type"],
                status="rejected",
                trace_id=span.trace_id,
            )
        except Exception:  # pylint: disable=broad-exception-caught
            pass
        return {"status": "rejected"}
