"""Manager approval endpoints — two independent front doors onto the same
`resolve_approval()` state machine (services/platform/approvals.py).

The email-click-through routes below are unauthenticated on purpose: the token in the URL is
the capability, and these must stay clickable straight from an email on a phone with no
dashboard login. GET renders a confirm page; the actual state mutation + real send only
happens on POST — mail clients and security scanners prefetch links for safe-link scanning, so
a plain GET that mutated state on load could fire before a human ever clicked it.

The dashboard front door (`POST /{approval_id}/resolve`, near the bottom of this file) is the
opposite shape on purpose: `require_firebase_auth`-gated JSON, no token in the URL at all — a
signed-in manager approving from the Prudently UI already proved who they are, so this route
authenticates the *person*, not a capability string, and reuses the approval's own Firestore
doc ID (exposed to authenticated dashboard responses only — see services/redaction.py) as the
lookup key into the identical `resolve_approval()` call the email path makes."""

from __future__ import annotations

from datetime import datetime, timezone
from html import escape
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from services.auth import require_firebase_auth
from services.platform.approvals import resolve_approval
from services.platform.email_templates import page_shell
from services.platform.rate_limit import limiter
from services.state import get_approval

router = APIRouter(prefix="/approvals", tags=["approvals"])

# Same dark palette as services/platform/email_templates.py — duplicated rather than imported
# (a handful of hex constants, not worth an import across the routes/services boundary for).
_HERO = "#2dd4c8"
_CRITICAL = "#ff6b5c"
_BG = "#090d0e"
_INK_MUTED = "#617975"


def _page(eyebrow: str, title: str, body_html: str, accent: str = _HERO) -> HTMLResponse:
    return HTMLResponse(
        page_shell(eyebrow=eyebrow, title=title, body_html=body_html, accent=accent)
    )


def _confirm_page(token: str, decision: str) -> HTMLResponse:
    record = get_approval(token)
    if record is None:
        return _page(
            "Approval link",
            "Not found",
            f'<p style="color:{_INK_MUTED};">This approval link is invalid.</p>',
            accent=_CRITICAL,
        )
    if record["status"] != "pending":
        status = escape(record["status"])
        return _page(
            "Approval link",
            f"Already {status}",
            f'<p style="color:{_INK_MUTED};">This request was already decided.</p>',
        )

    expires_at = record.get("expires_at")
    if expires_at is not None and datetime.now(timezone.utc) > expires_at:
        return _page(
            "Approval link",
            "Expired",
            f'<p style="color:{_INK_MUTED};">This approval link is more than 14 days old and is '
            "no longer active. Ask the requesting agent to raise it again if it's still "
            "needed.</p>",
            accent=_CRITICAL,
        )

    # Every interpolated value below can originate from LLM-composed text (Medical
    # Representative's send_vendor_reply builds `subject` from a model-supplied vendor_name) —
    # escape() closes docs/threat-model.md finding 7, a real unescaped-interpolation gap on a
    # fully public page.
    verb = "Approve" if decision == "approve" else "Reject"
    requested_by = escape(record["requested_by"])
    subject = escape(record["subject"])
    recipient = escape(str(record.get("recipient_label", record["to"])))
    button_color = _HERO if decision == "approve" else _CRITICAL
    body_html = (
        f'<p style="color:{_INK_MUTED};font-size:14px;line-height:1.6;margin:0 0 20px;">'
        f"<b>{requested_by}</b> wants to: {subject}<br>To: {recipient}</p>"
        f"<form method='post' action='/approvals/{token}/{decision}'>"
        f'<button type="submit" style="font-size:14px;font-weight:600;padding:11px 22px;'
        f'border-radius:10px;border:none;background:{button_color};color:{_BG};cursor:pointer;">'
        f"{verb}</button></form>"
    )
    return _page("Approval needed", f"{verb} this action?", body_html)


def _error_page(error: str) -> HTMLResponse:
    if error == "expired":
        return _page(
            "Approval link",
            "Expired",
            f'<p style="color:{_INK_MUTED};">This approval link is more than 14 days old and is '
            "no longer active.</p>",
            accent=_CRITICAL,
        )
    return _page("Approval link", escape(error.replace("_", " ").title()), "")


# docs/threat-model.md finding 4: no rate limiting existed on this fully public, no-auth
# surface. 20/minute per endpoint (services/platform/rate_limit.py's key_style="endpoint" —
# see its own docstring for why that matters here specifically) is generous for a real manager
# clicking a real link and tight enough to blunt a brute-force sweep across many candidate
# tokens against one of these four routes.
@router.get("/{token}/approve", response_class=HTMLResponse)
@limiter.limit("20/minute")
# pylint: disable-next=unused-argument
def approve_confirm(request: Request, token: str) -> HTMLResponse:
    return _confirm_page(token, "approve")


@router.get("/{token}/reject", response_class=HTMLResponse)
@limiter.limit("20/minute")
# pylint: disable-next=unused-argument
def reject_confirm(request: Request, token: str) -> HTMLResponse:
    return _confirm_page(token, "reject")


@router.post("/{token}/approve", response_class=HTMLResponse)
@limiter.limit("20/minute")
# pylint: disable-next=unused-argument
def approve(request: Request, token: str) -> HTMLResponse:
    result = resolve_approval(token, "approved")
    if "error" in result:
        return _error_page(result["error"])
    return _page(
        "Approval needed",
        "Approved",
        f'<p style="color:{_INK_MUTED};">The email has been sent.</p>',
    )


@router.post("/{token}/reject", response_class=HTMLResponse)
@limiter.limit("20/minute")
# pylint: disable-next=unused-argument
def reject(request: Request, token: str) -> HTMLResponse:
    result = resolve_approval(token, "rejected")
    if "error" in result:
        return _error_page(result["error"])
    return _page(
        "Approval needed",
        "Rejected",
        f'<p style="color:{_INK_MUTED};">No email was sent.</p>',
    )


class ResolvePayload(BaseModel):
    decision: Literal["approved", "rejected"]


_RESOLVE_ERROR_STATUS = {"not_found": 404, "already_decided": 409, "expired": 410}


@router.post("/{approval_id}/resolve")
@limiter.limit("20/minute")
def resolve_from_dashboard(
    request: Request,  # pylint: disable=unused-argument
    approval_id: str,
    payload: ResolvePayload,
    _uid: str = Depends(require_firebase_auth),
) -> dict:
    """The in-app equivalent of clicking the approve/reject link in the email — same
    `resolve_approval()`, same idempotent "already decided" handling, just reached from a
    signed-in manager's dashboard instead of a mail client. JSON in, JSON out, unlike the
    email path's rendered confirm pages, since the frontend updates the approvals list in
    place rather than navigating to a new page."""
    result = resolve_approval(approval_id, payload.decision)
    if "error" in result:
        raise HTTPException(
            status_code=_RESOLVE_ERROR_STATUS.get(result["error"], 400),
            detail=result["error"],
        )
    return result
