"""Session-management endpoints that don't fit any resource router. Currently just the one
capability `services/auth.py`'s docstring calls out as missing: a way to kill a session from
somewhere other than the device that holds it."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from services.auth import require_firebase_auth

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/sign-out-everywhere")
def sign_out_everywhere(uid: str = Depends(require_firebase_auth)) -> dict:
    """Revokes every refresh token issued to the calling user, server-side. The existing
    client-side `signOut()` (apps/web/src/contexts/AuthContext.tsx) only clears the local
    credential — a token already cached elsewhere (another open tab, a device that never got
    the sign-out click) stays valid until its own ~1hr natural expiry with no way to force it
    dead. This is that force: any ID token issued before this call now fails
    `verify_id_token(..., check_revoked=True)` immediately, not just after it expires."""
    from firebase_admin import auth as firebase_auth  # pylint: disable=import-outside-toplevel

    firebase_auth.revoke_refresh_tokens(uid)
    return {"status": "revoked"}
