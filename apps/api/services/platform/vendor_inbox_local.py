"""No-op Vendor Inbox adapter — never opens a network connection, matches every other *_local
adapter in this package (armor_local.py, observability_local.py). The default (see
vendor_inbox.py's module docstring for why this backend defaults to local, unlike its
siblings)."""

from __future__ import annotations

from .vendor_inbox import VendorMessage


class LocalVendorInboxService:  # pylint: disable=too-few-public-methods
    def fetch_new_messages(self) -> list[VendorMessage]:
        return []
