"""Real Email adapter — sends via Gmail SMTP using an app password fetched from Secret
Manager, not the Gmail API/OAuth (see email.py's module docstring for why). Credential path
verified live Day 1 against a throwaway probe Reasoning Engine deployment before this file was
written, matching this project's established practice (see AGENTS.md / Chaos's own docstring
for the same "confirmed live with a throwaway probe first" precedent)."""

from __future__ import annotations

import smtplib
from email.mime.text import MIMEText
from functools import lru_cache

from google.cloud import secretmanager

from config import GCP_PROJECT_ID, get_settings

from .email import SUBJECT_TAG, EmailSendResult  # pylint: disable=cyclic-import
from .observability import get_observability_service  # pylint: disable=cyclic-import


@lru_cache
def _app_password() -> str:
    settings = get_settings()
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{GCP_PROJECT_ID}/secrets/{settings.gmail_app_password_secret}/versions/latest"
    response = client.access_secret_version(name=name)
    return response.payload.data.decode("utf-8")


class GmailEmailService:  # pylint: disable=too-few-public-methods
    def send(
        self, to: str, subject: str, body: str, cc: list[str] | None = None
    ) -> EmailSendResult:
        with get_observability_service().span(
            "email.send", {"email.to": to, "email.subject": subject}
        ) as span:
            result = self._send(to, subject, body, cc)
            span.set_attribute("email.sent", result.sent)
            span.set_attribute("email.service_error", result.service_error)
            return result

    def _send(
        self, to: str, subject: str, body: str, cc: list[str] | None = None
    ) -> EmailSendResult:
        settings = get_settings()
        sender = settings.gmail_sender_email
        recipients = [to] + (cc or [])

        message = MIMEText(body)
        message["Subject"] = SUBJECT_TAG + subject
        message["From"] = sender
        message["To"] = to
        if cc:
            message["Cc"] = ", ".join(cc)

        # Fail soft, same rationale as armor_vertex.py: an email adapter that raises and takes
        # a tool call down with it is worse than one that reports a service error the caller
        # can surface honestly.
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
                smtp.login(sender, _app_password())
                smtp.sendmail(sender, recipients, message.as_string())
        except Exception as exc:  # pylint: disable=broad-exception-caught
            return EmailSendResult(
                sent=False, service_error=True, reason=f"Gmail SMTP send failed: {exc}"
            )

        return EmailSendResult(sent=True)
