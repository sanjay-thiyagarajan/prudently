"""Vendor inbox capability port: polls the same Gmail mailbox `email_gmail.py` sends from for
genuine incoming vendor mail, and hands each one to Medical Representative's own
`screen_vendor_message` — the identical real Model Armor path a live A2A conversation uses, not
a second implementation. `vendor_inbox_imap.py` is the real adapter (IMAP over the same app
password already in Secret Manager — see that module's own docstring for why IMAP, not the
Gmail API/OAuth, and why not SMTP: SMTP has no read operation at all, it's submission-only).
`vendor_inbox_local.py` is a true no-op for offline dev and for every deployment that hasn't
opted in.

Off by default (`VENDOR_INBOX_BACKEND` defaults to `"local"`), unlike `armor_backend`/
`observability_backend`/`email_backend`, which all default to their real adapter — this is a
brand-new integration with a real personal mailbox, and this file's own docstring convention
(see armor.py) is explicit that a backend "only flips to real once independently verified
against the live service." Flip it to `"imap"` once you've confirmed IMAP access is enabled on
the account (Gmail Settings → Forwarding and POP/IMAP → Enable IMAP — a per-account toggle this
code cannot set for you)."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

from config import get_settings


@dataclass(frozen=True)
class VendorMessage:
    vendor_name: str
    subject: str
    body: str
    message_id: str


class VendorInboxService(Protocol):  # pylint: disable=too-few-public-methods
    def fetch_new_messages(self) -> list[VendorMessage]: ...  # noqa: E704


@lru_cache
def get_vendor_inbox_service() -> VendorInboxService:
    # Same import-locality rationale as armor.py's get_armor_service: keeps imaplib's real
    # network path out of the import graph entirely when the backend is local, and avoids a
    # circular import (both adapters import VendorMessage from this module).
    # pylint: disable=import-outside-toplevel,cyclic-import
    if get_settings().vendor_inbox_backend == "imap":
        from .vendor_inbox_imap import ImapVendorInboxService

        return ImapVendorInboxService()

    from .vendor_inbox_local import LocalVendorInboxService

    return LocalVendorInboxService()
