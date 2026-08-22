"""Local-emulated Email fallback: never actually sends, logs nothing more than what the
caller already returns — used for offline dev/tests and as the safe default until
EMAIL_BACKEND is deliberately flipped to "gmail" (see config.py). Architecturally honest
no-op behind the same `EmailService` interface `email_gmail.py` satisfies, matching
`armor_local.py`'s framing: this exists to keep local dev/tests functional, not to emulate
real delivery."""

from __future__ import annotations

from .email import EmailSendResult  # pylint: disable=cyclic-import


class LocalEmailService:  # pylint: disable=too-few-public-methods
    def send(  # pylint: disable=unused-argument
        self, to: str, subject: str, body: str, cc: list[str] | None = None
    ) -> EmailSendResult:
        return EmailSendResult(sent=True, reason="EMAIL_BACKEND=local — not actually sent.")
