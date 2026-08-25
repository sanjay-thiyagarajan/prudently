"""Fleet-wide audit log — one drilldown table over `activity_log`, the same collection every
approval, Gateway routing decision, Model Armor screening, chaos experiment, and autonomous
action already writes to (see services/state.py's `write_activity_log` docstring for the exact
five call sites). `/agents/{agent_name}` already exposes this per agent; this route is the
unscoped view an operations manager actually wants for "what did the fleet do, across every
agent, and why" — auth-gated for the same reason routes/traces.py's drill-down routes are: full
fidelity here (unredacted subjects), unlike the public overview."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from services.auth import require_firebase_auth
from services.state import get_activity_log

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/log")
def get_audit_log(
    limit: int = 500,
    agent_name: str | None = None,
    _uid: str = Depends(require_firebase_auth),
) -> dict:
    """Newest-first, optionally scoped to one agent. `limit` caps at 1000 — a manager reviewing
    a long-running demo shouldn't be able to force an unbounded Firestore read from the client."""
    limit = min(max(limit, 1), 1000)
    entries = get_activity_log(agent_name=agent_name, limit=limit)
    return {"entries": entries}
