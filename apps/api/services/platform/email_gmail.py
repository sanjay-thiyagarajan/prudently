"""Real Email adapter — sends via Gmail SMTP using an app password fetched from Secret
Manager, not the Gmail API/OAuth (see email.py's module docstring for why). Credential path
verified via a throwaway probe Reasoning Engine deployment before this file was written,
matching this project's established practice of verifying a new GCP integration live before
building on top of it."""

from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
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
    def send(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        to: str,
        subject: str,
        body: str,
        cc: list[str] | None = None,
        *,
        html: str | None = None,
    ) -> EmailSendResult:
        with get_observability_service().span(
            "email.send", {"email.to": to, "email.subject": subject}
        ) as span:
            result = self._send(to, subject, body, cc, html)
            span.set_attribute("email.sent", result.sent)
            span.set_attribute("email.service_error", result.service_error)
            return result

    def _send(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        to: str,
        subject: str,
        body: str,
        cc: list[str] | None = None,
        html: str | None = None,
    ) -> EmailSendResult:
        settings = get_settings()
        sender = settings.gmail_sender_email
        recipients = [to] + (cc or [])

        # MIMEMultipart("alternative") only when a caller actually supplied HTML — every send
        # site still passes a real plain-text body, since email clients that show plain text
        # (or that fail to render the HTML part at all) need something real to fall back to,
        # not the HTML source dumped as text. Plain MIMEText for callers that don't (there
        # currently are none — services/platform/approvals.py's three send sites all route
        # through services/platform/email_templates.py now — but the branch stays so the
        # `html` parameter is genuinely optional at the interface level, not just in practice).
        if html:
            message = MIMEMultipart("alternative")
            message.attach(MIMEText(body, "plain"))
            message.attach(MIMEText(html, "html"))
        else:
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
