"""Seeds the `approval_policy` Firestore collection read by services/platform/approvals.py's
check_policy(). Run via `uv run python -m scripts.seed_policy` from apps/api, or `make
seed-policy`. Safe to re-run: every write is a full `set()` on a fixed doc ID (the task type),
not an incremental update -- same pattern as scripts/seed_registry.py.

Run this before flipping EMAIL_BACKEND to "gmail" -- check_policy() fails closed, so an
unseeded collection means every one of these task types requires approval regardless of what's
written here (correct-but-noisy, not broken), which should be a deliberate state, not a
surprise found mid-demo."""

from __future__ import annotations

from config import get_settings
from services.state import get_client

# One entry per approval-gated tool added across Supply Chain, HR, Shift, Medical
# Representative, and Surgical Scheduling (see AGENTS.md's Gmail/approvals section for why
# these five and not all 7 agents). requires_approval=True by default for all of them -- the
# manager can relax any of these from the dashboard's policy-editor panel; this script only
# sets the initial state.
POLICIES: list[dict] = [
    {
        "task_type": "contact_vendor_for_reorder",
        "requires_approval": True,
        "approver_email": None,
        "notify_emails": [],
        "notify_on_complete": True,
    },
    {
        "task_type": "notify_staff_credential_escalation",
        "requires_approval": True,
        "approver_email": None,
        "notify_emails": [],
        "notify_on_complete": True,
    },
    {
        "task_type": "notify_staff_reallocation",
        "requires_approval": True,
        "approver_email": None,
        "notify_emails": [],
        "notify_on_complete": True,
    },
    {
        "task_type": "send_vendor_reply",
        "requires_approval": True,
        "approver_email": None,
        "notify_emails": [],
        "notify_on_complete": True,
    },
    {
        "task_type": "notify_patient_of_status_change",
        "requires_approval": True,
        "approver_email": None,
        "notify_emails": [],
        "notify_on_complete": True,
    },
]


def main() -> None:
    get_settings()  # fail fast on a broken .env before touching Firestore
    client = get_client()
    batch = client.batch()

    for policy in POLICIES:
        batch.set(client.collection("approval_policy").document(policy["task_type"]), policy)

    batch.commit()
    print(f"wrote {len(POLICIES)} approval_policy docs")


if __name__ == "__main__":
    main()
