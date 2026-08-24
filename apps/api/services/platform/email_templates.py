"""Shared HTML email shell + per-type render functions. Before this module, every email body
in this codebase was a raw f-string assembled inline at each call site (services/platform/
approvals.py's three send sites, plus the four agent tools that build the subject/body those
sites forward) — `smtplib`/`MIMEText` only, no HTML capability anywhere. Every render function
here returns `(plain_text, html)`: the plain text is what the four existing call sites already
built (unchanged in substance, so nothing about the approval flow's actual content or the
`recipient_label`-vs-`to` safety property changes — see approvals.py's own docstring for why
that distinction matters), and the HTML is the same content in the app's dark mission-control
visual language, with the logo mark inlined as a data URI so it renders in mail clients that
block remote images by default (which is most of them).

Long-line and too-many-arguments checks are disabled file-wide: this module is HTML string
templates and named render parameters (recipient/subject/body/urls/expiry), not logic — wrapping
raw markup mid-tag to satisfy an 100-column limit would hurt readability without catching any
real defect, and each render function's parameter list is exactly the fields that email type
needs, not an accumulation worth restructuring into an object.
"""

# pylint: disable=line-too-long,too-many-arguments,too-many-positional-arguments

from __future__ import annotations

from datetime import date

# 64x64 PNG, the same mark used for the app's own favicon/sidebar badge
# (apps/web/src/app/icon.png), inlined so no external image request is needed to render it.
_LOGO_DATA_URI = (
    "data:image/png;base64,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"
)

_HERO = "#2dd4c8"
_AUTONOMOUS = "#a78bfa"
_BG = "#090d0e"
_SURFACE = "#111a1c"
_BORDER = "#1e2c2e"
_INK = "#eaf4f2"
_INK_SECONDARY = "#9db3b0"
_INK_MUTED = "#617975"


def page_shell(*, eyebrow: str, title: str, body_html: str, accent: str = _HERO) -> str:
    """Public alias of the email shell, reused by routes/approvals.py's confirm page — the
    manager reaches that page by clicking a link *out of* an email this module rendered, so it
    should look like the same product, not a bare unbranded form."""
    return _shell(eyebrow=eyebrow, title=title, body_html=body_html, accent=accent)


def _shell(*, eyebrow: str, title: str, body_html: str, accent: str = _HERO) -> str:
    """The one shared visual frame every email type renders through. Table-based layout, no
    flexbox/grid, inline styles only — the constraints real email clients (Gmail/Outlook web
    and desktop) actually require, not a stylistic choice."""
    return f"""\
<!DOCTYPE html>
<html>
  <body style="margin:0;padding:0;background:{_BG};font-family:'Instrument Sans',ui-sans-serif,system-ui,sans-serif;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{_BG};padding:32px 16px;">
      <tr>
        <td align="center">
          <table role="presentation" width="480" cellpadding="0" cellspacing="0" style="max-width:480px;width:100%;background:{_SURFACE};border:1px solid {_BORDER};border-radius:16px;overflow:hidden;">
            <tr>
              <td style="padding:28px 32px 20px;border-bottom:1px solid {_BORDER};">
                <table role="presentation" cellpadding="0" cellspacing="0">
                  <tr>
                    <td style="padding-right:10px;">
                      <img src="{_LOGO_DATA_URI}" width="32" height="32" alt="Prudently" style="display:block;border-radius:7px;">
                    </td>
                    <td>
                      <div style="font-size:16px;font-weight:650;color:{_INK};letter-spacing:-0.01em;">Prudently</div>
                      <div style="font-family:ui-monospace,'JetBrains Mono',monospace;font-size:10px;letter-spacing:0.14em;color:{accent};text-transform:uppercase;margin-top:2px;">{eyebrow}</div>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding:28px 32px 8px;">
                <div style="font-size:19px;font-weight:650;color:{_INK};margin:0 0 16px;">{title}</div>
                {body_html}
              </td>
            </tr>
            <tr>
              <td style="padding:20px 32px 28px;border-top:1px solid {_BORDER};margin-top:20px;">
                <div style="font-family:ui-monospace,'JetBrains Mono',monospace;font-size:10px;letter-spacing:0.08em;color:{_INK_MUTED};text-transform:uppercase;">
                  Prudently &middot; Fortified Enterprise Fleet &middot; {date.today().isoformat()}
                </div>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>"""


def _button(label: str, url: str, *, filled: bool) -> str:
    """`filled=False` renders an outlined secondary button (Reject) — a transparent fill with
    no border at all read as a missing/broken element in a real render check, not a deliberate
    secondary action, so the outline is load-bearing, not decorative."""
    if filled:
        style = f"background:{_HERO};color:{_BG};border:1px solid {_HERO};"
    else:
        style = f"background:transparent;color:{_INK_SECONDARY};border:1px solid {_BORDER};"
    return (
        f'<a href="{url}" style="display:inline-block;{style}font-weight:600;font-size:14px;'
        f'text-decoration:none;padding:10px 21px;border-radius:10px;margin-right:10px;">{label}</a>'
    )


def _field(label: str, value: str) -> str:
    return (
        f'<div style="margin-bottom:14px;"><div style="font-family:ui-monospace,'
        f"'JetBrains Mono',monospace;font-size:10px;letter-spacing:0.1em;color:{_INK_MUTED};"
        f'text-transform:uppercase;margin-bottom:3px;">{label}</div>'
        f'<div style="font-size:14px;color:{_INK};line-height:1.5;">{value}</div></div>'
    )


def approval_request(
    *,
    requested_by: str,
    subject: str,
    recipient_label: str,
    body: str,
    approve_url: str,
    reject_url: str,
    expires_at: date,
) -> tuple[str, str]:
    """The approval-request email — services/platform/approvals.py's `_request_approval`.
    Preserves the exact same functional content the plain-text version always sent (who's
    asking, what for, who it's to, the approve/reject links, the expiry) — this is a rendering
    upgrade, not a content change."""
    plain = (
        f"{requested_by} wants to: {subject}\n\nTo: {recipient_label}\n\n{body}\n\n"
        f"Approve: {approve_url}\n"
        f"Reject: {reject_url}\n\n"
        f"This link expires {expires_at.isoformat()}.\n"
    )
    html_body = (
        _field("Requested by", requested_by)
        + _field("Action", subject)
        + _field("To", recipient_label)
        + f'<div style="font-size:14px;color:{_INK_SECONDARY};line-height:1.6;margin:4px 0 22px;">{body}</div>'
        + f'<div style="margin-bottom:16px;">{_button("Approve", approve_url, filled=True)}{_button("Reject", reject_url, filled=False)}</div>'
        + f'<div style="font-size:12px;color:{_INK_MUTED};">This link expires {expires_at.isoformat()}.</div>'
    )
    return plain, _shell(
        eyebrow="Approval needed", title=subject, body_html=html_body, accent=_HERO
    )


def action_sent(*, subject: str, recipient_label: str, body: str) -> tuple[str, str]:
    """Covers both `perform_or_request`'s immediate-send path and `resolve_approval`'s
    approved-and-sent path — the two share identical content shape today (a subject/recipient/
    body triple with no approve/reject links), so one render function serves both call sites."""
    plain = f"To: {recipient_label}\n\n{body}\n"
    html_body = (
        _field("To", recipient_label)
        + f'<div style="font-size:14px;color:{_INK_SECONDARY};line-height:1.6;">{body}</div>'
    )
    return plain, _shell(eyebrow="Sent", title=subject, body_html=html_body, accent=_HERO)


def purchase_order(
    *,
    vendor_name: str,
    sku: str,
    item_name: str,
    quantity: int,
    unit_cost: float,
    category: str,
) -> tuple[str, str]:
    """The vendor-facing reorder document — agents/supply/agent.py's `contact_vendor_for_reorder`.
    Replaces the previous plain `f"Please supply {quantity} units..."` body with a real
    itemized document while keeping the same operational facts."""
    total = round(unit_cost * quantity, 2)
    plain = (
        f"Purchase order for {vendor_name}\n\n"
        f"Item: {item_name} (SKU {sku})\nCategory: {category}\n"
        f"Quantity: {quantity}\nUnit cost: ${unit_cost:,.2f}\nTotal: ${total:,.2f}\n\n"
        "Requested by the Supply Chain Resiliency Agent."
    )
    html_body = (
        _field("Vendor", vendor_name)
        + _field("Item", f"{item_name} &middot; SKU {sku} &middot; {category}")
        + f"""<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:18px 0;border:1px solid {_BORDER};border-radius:10px;overflow:hidden;">
          <tr style="background:{_BG};">
            <td style="padding:10px 14px;font-family:ui-monospace,monospace;font-size:11px;color:{_INK_MUTED};">Quantity</td>
            <td style="padding:10px 14px;font-family:ui-monospace,monospace;font-size:11px;color:{_INK_MUTED};" align="right">Unit cost</td>
            <td style="padding:10px 14px;font-family:ui-monospace,monospace;font-size:11px;color:{_INK_MUTED};" align="right">Total</td>
          </tr>
          <tr>
            <td style="padding:12px 14px;font-size:14px;color:{_INK};">{quantity}</td>
            <td style="padding:12px 14px;font-size:14px;color:{_INK};" align="right">${unit_cost:,.2f}</td>
            <td style="padding:12px 14px;font-size:14px;font-weight:650;color:{_HERO};" align="right">${total:,.2f}</td>
          </tr>
        </table>"""
        + f'<div style="font-size:12px;color:{_INK_MUTED};">Requested by the Supply Chain Resiliency Agent.</div>'
    )
    return plain, _shell(
        eyebrow="Purchase order",
        title=f"{quantity} × {item_name}",
        body_html=html_body,
        accent=_HERO,
    )


def job_sheet(
    *,
    title: str,
    kind: str,
    location: str,
    assigned_to: str,
    priority: str,
    description: str,
) -> tuple[str, str]:
    """Both job-sheet flavors (facilities work orders and staff duty rosters) render through
    this one function — same document shape, different `kind`/content."""
    plain = (
        f"{title}\n\nKind: {kind}\nLocation: {location}\nAssigned to: {assigned_to}\n"
        f"Priority: {priority}\n\n{description}\n"
    )
    html_body = (
        _field("Location", location)
        + _field("Assigned to", assigned_to)
        + _field("Priority", priority.title())
        + f'<div style="font-size:14px;color:{_INK_SECONDARY};line-height:1.6;margin-top:4px;">{description}</div>'
    )
    return plain, _shell(eyebrow=kind, title=title, body_html=html_body, accent=_AUTONOMOUS)


def patient_notification(
    *, patient_name: str, procedure_name: str, status_message: str, scheduled_at: str
) -> tuple[str, str]:
    """Part D's patient-facing surgery-status email — the one email type in this codebase sent
    to a real individual rather than the operations mailbox. Deliberately plainer than the
    other templates (no internal jargon, no agent attribution) since the reader is a patient,
    not staff."""
    plain = (
        f"Hello {patient_name},\n\n{status_message}\n\n"
        f"Procedure: {procedure_name}\nScheduled: {scheduled_at}\n\n"
        "If you have questions, please contact the hospital directly."
    )
    html_body = (
        f'<div style="font-size:14px;color:{_INK_SECONDARY};line-height:1.7;margin-bottom:18px;">'
        f"Hello {patient_name},<br><br>{status_message}</div>"
        + _field("Procedure", procedure_name)
        + _field("Scheduled", scheduled_at)
        + f'<div style="font-size:12px;color:{_INK_MUTED};margin-top:8px;">If you have questions, please contact the hospital directly.</div>'
    )
    return plain, _shell(
        eyebrow="Your care",
        title="An update on your procedure",
        body_html=html_body,
        accent=_AUTONOMOUS,
    )
