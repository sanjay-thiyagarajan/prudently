"""Manager-facing approval/notification policy config — the dashboard's policy-editor panel
reads and writes through this. Auth-gated (unlike `/dashboard/overview` and `/approvals/*`):
this is write access to manager-facing config, not a read-only feed or a click-through
capability link."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from services.auth import require_firebase_auth
from services.state import get_approval_policies, write_approval_policy

router = APIRouter(prefix="/policy", tags=["policy"])


class ApprovalPolicyPayload(BaseModel):
    requires_approval: bool
    approver_email: str | None = None
    notify_emails: list[str] = []
    notify_on_complete: bool = True


@router.get("/tasks")
def list_tasks(_uid: str = Depends(require_firebase_auth)) -> list[dict]:
    return get_approval_policies()


@router.put("/tasks/{task_type}")
def upsert_task(
    task_type: str, payload: ApprovalPolicyPayload, _uid: str = Depends(require_firebase_auth)
) -> dict:
    policy = {"task_type": task_type, **payload.model_dump()}
    write_approval_policy(task_type, policy)
    return policy
