"""Email capability port: sends approval-request and post-approval notification email on
behalf of agents. `email_gmail.py` is the real implementation (SMTP via a Gmail app password —
see AGENTS.md's Gmail setup section for why an app password rather than OAuth: this is a
personal gmail.com account with no Workspace domain / domain-wide delegation available, and an
app password needs no consent-screen configuration or refresh-token expiry management, at the
honest cost of granting broader mailbox access than an OAuth token scoped to `gmail.send`
would — acceptable for a personal demo account). `email_local.py` is a no-op fallback for
offline dev/tests. Selected by `EMAIL_BACKEND` via `get_email_service()` below, matching the
adapter pattern described in AGENTS.md's "Platform adapter layer" section (same shape as
`armor.py`, not `gateway.py` — `gateway.py`'s factory ignores its own `Backend` setting and
always returns the local adapter, so it is not the pattern to copy here)."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

from config import get_settings

# Every subject line sent through the real adapter is prefixed with this tag so the user can
# set up one Gmail filter (Subject contains this tag -> apply a label) to keep agent-originated
# mail visually separated from the rest of their inbox. Purely organizational — Gmail labels on
# a personal, non-Workspace account are not access-restricted, so this is not a security
# boundary (see AGENTS.md's Gmail setup section).
SUBJECT_TAG = "[Prudently] "


@dataclass(frozen=True)
class EmailSendResult:
    sent: bool
    # True only when the email service itself couldn't be reached/authenticated — distinct
    # from any notion of a declined send (this port has no "declined," unlike ArmorResult;
    # kept for the same reason ArmorResult carries it: callers must not render an outage as a
    # successful — or failed — demo moment without knowing which one actually happened).
    service_error: bool = False
    reason: str | None = None


class EmailService(Protocol):  # pylint: disable=too-few-public-methods
    def send(
        self,
        to: str,
        subject: str,
        body: str,
        cc: list[str] | None = None,
        *,
        html: str | None = None,
    ) -> EmailSendResult: ...  # noqa: E704


@lru_cache
def get_email_service() -> EmailService:
    # Imports are local (not top-level) on purpose — see armor.py's get_armor_service for the
    # identical rationale: avoids a real circular import (both adapters import EmailSendResult
    # from this module) and keeps smtplib usage/Secret Manager calls out of the import graph
    # entirely when EMAIL_BACKEND=local.
    # pylint: disable=import-outside-toplevel,cyclic-import
    if get_settings().email_backend == "gmail":
        from .email_gmail import GmailEmailService

        return GmailEmailService()

    from .email_local import LocalEmailService

    return LocalEmailService()
