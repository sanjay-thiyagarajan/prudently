"""Unit tests for services/platform/approvals.py — the fail-closed policy check, the
pending/immediate-send branch, and idempotent approve/reject. All Firestore and email calls
are faked/monkeypatched; nothing here touches real GCP or sends a real email."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from services.platform import approvals  # noqa: E402
from services.platform.email import EmailSendResult  # noqa: E402
from services.platform.observability_local import LocalObservabilityService  # noqa: E402


class FakeEmailService:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    def send(self, to, subject, body, cc=None):
        self.sent.append({"to": to, "subject": subject, "body": body, "cc": cc})
        return EmailSendResult(sent=True)


def _patch_common(monkeypatch, fake_email, policies=None, approvals_store=None):
    policies = policies or {}
    approvals_store = approvals_store if approvals_store is not None else {}

    monkeypatch.setattr(approvals, "get_email_service", lambda: fake_email)
    monkeypatch.setattr(approvals, "get_observability_service", LocalObservabilityService)
    monkeypatch.setattr(approvals, "get_approval_policy", policies.get)
    monkeypatch.setattr(approvals, "write_approval", approvals_store.__setitem__)
    monkeypatch.setattr(approvals, "get_approval", approvals_store.get)
    monkeypatch.setattr(
        approvals,
        "update_approval",
        lambda token, patch: approvals_store[token].update(patch),
    )
    monkeypatch.setattr(approvals, "write_email_log", lambda record: None)
    return approvals_store


def test_check_policy_fails_closed_when_unconfigured(monkeypatch):
    _patch_common(monkeypatch, FakeEmailService())
    policy = approvals.check_policy("some_unconfigured_task")
    assert policy["requires_approval"] is True


def test_check_policy_returns_configured_values(monkeypatch):
    _patch_common(
        monkeypatch,
        FakeEmailService(),
        policies={"vendor_reorder": {"requires_approval": False, "notify_emails": ["a@b.com"]}},
    )
    policy = approvals.check_policy("vendor_reorder")
    assert policy["requires_approval"] is False
    assert policy["notify_emails"] == ["a@b.com"]


def test_perform_or_request_sends_immediately_when_not_required(monkeypatch):
    fake_email = FakeEmailService()
    _patch_common(
        monkeypatch,
        fake_email,
        policies={"vendor_reorder": {"requires_approval": False}},
    )
    result = approvals.perform_or_request(
        "vendor_reorder",
        "vendor@example.com",
        "MedSupply Primary",
        "Reorder gloves",
        "body",
        "supply_chain_agent",
    )
    assert result["status"] == "sent"
    assert result["sent"] is True
    assert len(fake_email.sent) == 1
    assert fake_email.sent[0]["to"] == "vendor@example.com"


def test_perform_or_request_creates_pending_approval_when_required(monkeypatch):
    fake_email = FakeEmailService()
    store = _patch_common(
        monkeypatch,
        fake_email,
        policies={"vendor_reorder": {"requires_approval": True, "approver_email": "mgr@x.com"}},
    )
    result = approvals.perform_or_request(
        "vendor_reorder",
        "vendor@example.com",
        "MedSupply Primary",
        "Reorder gloves",
        "body",
        "supply_chain_agent",
    )
    assert result["status"] == "pending_approval"
    token = result["approval_id"]
    assert token in store
    assert store[token]["status"] == "pending"
    assert store[token]["to"] == "vendor@example.com"
    assert store[token]["recipient_label"] == "MedSupply Primary"
    # Exactly one email sent so far: the approval request to the manager, not the real send.
    assert len(fake_email.sent) == 1
    assert fake_email.sent[0]["to"] == "mgr@x.com"


def test_resolve_approval_approved_sends_the_real_email(monkeypatch):
    fake_email = FakeEmailService()
    store = _patch_common(
        monkeypatch,
        fake_email,
        policies={"vendor_reorder": {"requires_approval": True, "approver_email": "mgr@x.com"}},
    )
    result = approvals.perform_or_request(
        "vendor_reorder",
        "vendor@example.com",
        "MedSupply Primary",
        "Reorder gloves",
        "body",
        "supply_chain_agent",
    )
    token = result["approval_id"]
    fake_email.sent.clear()

    outcome = approvals.resolve_approval(token, "approved")
    assert outcome["status"] == "approved"
    assert store[token]["status"] == "approved"
    assert len(fake_email.sent) == 1
    assert fake_email.sent[0]["to"] == "vendor@example.com"


def test_resolve_approval_rejected_never_sends(monkeypatch):
    fake_email = FakeEmailService()
    store = _patch_common(
        monkeypatch,
        fake_email,
        policies={"vendor_reorder": {"requires_approval": True, "approver_email": "mgr@x.com"}},
    )
    result = approvals.perform_or_request(
        "vendor_reorder",
        "vendor@example.com",
        "MedSupply Primary",
        "Reorder gloves",
        "body",
        "supply_chain_agent",
    )
    token = result["approval_id"]
    fake_email.sent.clear()

    outcome = approvals.resolve_approval(token, "rejected")
    assert outcome["status"] == "rejected"
    assert store[token]["status"] == "rejected"
    assert len(fake_email.sent) == 0


def test_resolve_approval_is_idempotent(monkeypatch):
    fake_email = FakeEmailService()
    _patch_common(
        monkeypatch,
        fake_email,
        policies={"vendor_reorder": {"requires_approval": True, "approver_email": "mgr@x.com"}},
    )
    result = approvals.perform_or_request(
        "vendor_reorder",
        "vendor@example.com",
        "MedSupply Primary",
        "Reorder gloves",
        "body",
        "supply_chain_agent",
    )
    token = result["approval_id"]

    first = approvals.resolve_approval(token, "approved")
    assert first["status"] == "approved"
    sent_count_after_first = len(fake_email.sent)

    second = approvals.resolve_approval(token, "approved")
    assert second == {"error": "already_decided", "status": "approved"}
    # No second real send fired on the re-hit.
    assert len(fake_email.sent) == sent_count_after_first


def test_resolve_approval_unknown_token(monkeypatch):
    _patch_common(monkeypatch, FakeEmailService())
    result = approvals.resolve_approval("does-not-exist", "approved")
    assert result == {"error": "not_found"}
