"""Manager approval click-through endpoints — reached from the approve/reject links an
approval-request email carries (services/platform/approvals.py). No auth: the token in the URL
is the capability, and these must be clickable straight from an email on a phone with no
dashboard login.

GET renders a confirm page; the actual state mutation + real send only happens on POST. This
split exists because mail clients and security scanners prefetch links for safe-link scanning
— a plain GET that mutated state on load could fire before a human ever clicked it."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from services.platform.approvals import resolve_approval
from services.state import get_approval

router = APIRouter(prefix="/approvals", tags=["approvals"])

_PAGE_STYLE = "font-family: sans-serif; max-width: 480px; margin: 4rem auto; text-align: center;"


def _page(body: str) -> HTMLResponse:
    return HTMLResponse(f"<html><body style='{_PAGE_STYLE}'>{body}</body></html>")


def _confirm_page(token: str, decision: str) -> HTMLResponse:
    record = get_approval(token)
    if record is None:
        return _page("<h2>Not found</h2><p>This approval link is invalid.</p>")
    if record["status"] != "pending":
        return _page(f"<h2>Already {record['status']}</h2><p>This request was already decided.</p>")

    verb = "Approve" if decision == "approve" else "Reject"
    return _page(
        f"<h2>{verb} this action?</h2>"
        f"<p><b>{record['requested_by']}</b> wants to: {record['subject']}</p>"
        f"<p>To: {record.get('recipient_label', record['to'])}</p>"
        f"<form method='post' action='/approvals/{token}/{decision}'>"
        f"<button type='submit' style='font-size:1.1rem;padding:0.6rem 1.4rem;'>{verb}</button>"
        "</form>"
    )


@router.get("/{token}/approve", response_class=HTMLResponse)
def approve_confirm(token: str) -> HTMLResponse:
    return _confirm_page(token, "approve")


@router.get("/{token}/reject", response_class=HTMLResponse)
def reject_confirm(token: str) -> HTMLResponse:
    return _confirm_page(token, "reject")


@router.post("/{token}/approve", response_class=HTMLResponse)
def approve(token: str) -> HTMLResponse:
    result = resolve_approval(token, "approved")
    if "error" in result:
        return _page(f"<h2>{result['error'].replace('_', ' ').title()}</h2>")
    return _page("<h2>Approved</h2><p>The email has been sent.</p>")


@router.post("/{token}/reject", response_class=HTMLResponse)
def reject(token: str) -> HTMLResponse:
    result = resolve_approval(token, "rejected")
    if "error" in result:
        return _page(f"<h2>{result['error'].replace('_', ' ').title()}</h2>")
    return _page("<h2>Rejected</h2><p>No email was sent.</p>")
