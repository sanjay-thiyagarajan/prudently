"""Manager approval click-through endpoints — reached from the approve/reject links an
approval-request email carries (services/platform/approvals.py). No auth: the token in the URL
is the capability, and these must be clickable straight from an email on a phone with no
dashboard login.

GET renders a confirm page; the actual state mutation + real send only happens on POST. This
split exists because mail clients and security scanners prefetch links for safe-link scanning
— a plain GET that mutated state on load could fire before a human ever clicked it."""

from __future__ import annotations

from datetime import datetime, timezone
from html import escape

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

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
