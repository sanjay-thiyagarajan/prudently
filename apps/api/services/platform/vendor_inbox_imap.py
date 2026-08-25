"""Real Vendor Inbox adapter — polls the same Gmail mailbox `email_gmail.py` sends from, over
IMAP, using the identical app password already in Secret Manager (`gmail_app_password()`,
exported from that module specifically for this reuse). Not the Gmail API/OAuth: this is a
personal gmail.com account with no Workspace domain/domain-wide delegation, and OAuth's own
cost here would be a consent screen, refresh-token storage, and — for anything resembling a
real push listener — a Pub/Sub topic plus re-arming Gmail API's `users.watch()` every 7 days.
Not SMTP either: SMTP is submission-only and has no read operation at all, regardless of
credential. IMAP is the one protocol that actually reads a mailbox, and it accepts the same
app password SMTP does.

**Scoped to one Gmail label, never raw INBOX.** A live login against the real account (see
AGENTS.md's dated entry) found 33,000+ pre-existing unread messages already sitting in INBOX —
this is a real personal mailbox, not a dedicated vendor address, and searching INBOX directly
would run a manager's entire unrelated backlog through Model Armor the moment this backend is
switched on. `select()`s `config.py`'s `vendor_inbox_gmail_label` instead, which Gmail exposes
as a real IMAP folder once "Show in IMAP" is enabled for that label — only mail explicitly
routed there (by hand, or by a Gmail filter the manager sets up) is ever touched. A label that
doesn't exist yet just returns no messages (fails soft, see below), not an error — the
one-time label-creation step is a manual prerequisite, same shape as the Model Armor template
and the Gmail app password itself.

**Self-mail filtering.** This mailbox is both the sender and the default approver
(`gmail_sender_email == manager_email`, see AGENTS.md's Gmail setup section for why), so an
approval-request/notification email Prudently itself sends would land right back in this same
label if it were ever cc'd or filtered there — Gmail delivers self-addressed mail through real
mail delivery, not just a Sent-folder copy. Filtering by sender address would also exclude a
human manually testing this feature by composing a message to themselves from the same account,
so the filter here is `email.py`'s own `SUBJECT_TAG` instead: every one of Prudently's own
sends carries it, nothing genuinely external does.

**Polling, not push**, matching the rest of this app's own architecture (lib/api/dashboard.ts's
own docstring: "Polling ... makes the demo reproducible") — called once per real-time watch
cycle from services/fleet_watch.py, not a persistent connection.

**Read-tracking**: via IMAP's own `\\Seen` flag, not a second Firestore collection — this
adapter only ever searches `UNSEEN`, and marks a message `\\Seen` right after parsing it, in
the same connection. That's fetch-time, not after the caller has actually screened it: a crash
between this call returning and services/fleet_watch.py finishing the screen would leave that
one message marked read but never screened. Accepted deliberately — re-fetching on every
partial failure would need a second piece of state (which messages were *actually* screened,
not just seen) for a low-stakes polling demo feature, the same "best-effort side effect, not a
compliance ledger" tolerance every other write in this codebase already accepts."""

from __future__ import annotations

import email as email_lib
import imaplib
from email.policy import default as default_policy
from email.utils import parseaddr

from config import get_settings

from .email import SUBJECT_TAG  # pylint: disable=cyclic-import
from .email_gmail import gmail_app_password
from .vendor_inbox import VendorMessage  # pylint: disable=cyclic-import

_IMAP_HOST = "imap.gmail.com"
_IMAP_PORT = 993


def _extract_body(message: email_lib.message.EmailMessage) -> str:
    body_part = message.get_body(preferencelist=("plain", "html"))
    if body_part is None:
        return ""
    content = body_part.get_content()
    return content if isinstance(content, str) else str(content)


def _parse_message(raw: bytes, uid: bytes) -> VendorMessage | None:
    """None means "skip" — either it's Prudently's own outgoing mail looped back to this
    inbox, tagged by SUBJECT_TAG, or nothing worth screening."""
    parsed = email_lib.message_from_bytes(raw, policy=default_policy)
    subject = str(parsed.get("Subject", ""))
    if subject.startswith(SUBJECT_TAG):
        return None

    display_name, from_addr = parseaddr(str(parsed.get("From", "")))
    return VendorMessage(
        vendor_name=display_name or from_addr or "Unknown sender",
        subject=subject,
        body=_extract_body(parsed),
        message_id=str(parsed.get("Message-ID", uid.decode())),
    )


class ImapVendorInboxService:  # pylint: disable=too-few-public-methods
    def fetch_new_messages(self) -> list[VendorMessage]:
        # Fail soft, same rationale as armor_vertex.py/email_gmail.py: a mailbox that's
        # temporarily unreachable (or IMAP not yet enabled on the account) must never take
        # down the rest of the watch cycle.
        try:
            return self._fetch()
        except Exception:  # pylint: disable=broad-exception-caught
            return []

    def _fetch(self) -> list[VendorMessage]:
        settings = get_settings()
        with imaplib.IMAP4_SSL(_IMAP_HOST, _IMAP_PORT) as imap:
            imap.login(settings.gmail_sender_email, gmail_app_password())
            # Never "INBOX" — see this module's own docstring for why that would be a real
            # incident, not a demo feature. A label that doesn't exist yet selects with a
            # non-OK status, same as an empty search — both just mean "nothing to do."
            status, _ = imap.select(f'"{settings.vendor_inbox_gmail_label}"')
            if status != "OK":
                return []
            status, data = imap.search(None, "UNSEEN")
            if status != "OK":
                return []

            messages: list[VendorMessage] = []
            for uid in data[0].split():
                # BODY.PEEK[] — fetches without implicitly marking \Seen, so a message this
                # loop decides to skip (Prudently's own mail) is left UNSEEN exactly as it
                # was, not silently marked read-and-ignored.
                status, msg_data = imap.fetch(uid, "(BODY.PEEK[])")
                if status != "OK" or not msg_data or not isinstance(msg_data[0], tuple):
                    continue
                message = _parse_message(msg_data[0][1], uid)
                if message is None:
                    continue
                messages.append(message)
                imap.store(uid, "+FLAGS", "\\Seen")

            return messages
