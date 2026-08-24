"""Firebase Authentication verification for manager-facing routes — see AGENTS.md's Firebase
setup section for the one manual prerequisite (Firebase project creation, Email/Password
provider, one demo/judge account, done via the Firebase Console — not scriptable from here).

Three postures, deliberately distinct:

* `require_firebase_auth` — hard 401. Anything that writes manager config, or reads pay,
  hours, or an individual's record.
* `require_role(*roles)` — hard 401/403. Built on top of `require_firebase_auth`; also checks
  the token's `role` custom claim. Used for anything that touches patient identity — a signed-in
  session alone is not enough once real-PII-shaped data exists (see docs/threat-model.md
  finding 6).
* `optional_firebase_auth` — returns a uid or None, never raises. Used by the read-only feeds
  (`/dashboard/overview`, `/agents/{name}`) which must stay reachable without a login (a judge
  needs the URL to work cold) but must not hand per-employee fatigue and credentialing records
  to an anonymous caller. Signed in, the caller sees the full payload; signed out, staff-level
  detail is replaced by the aggregate — see `services/redaction.py`.
* No dependency at all — the approval click-through links (`/approvals/*`), which have to be
  clickable from a phone with no dashboard session.

This is a plain module, not a `services/platform/` adapter port: there is exactly one real
implementation and no local/offline fallback need — tests override the dependency directly via
FastAPI's `app.dependency_overrides`, not a `_local.py`.
"""

from __future__ import annotations

import logging

from fastapi import Header, HTTPException

from config import GCP_PROJECT_ID

logger = logging.getLogger(__name__)


def _ensure_firebase_app() -> None:
    import firebase_admin  # pylint: disable=import-outside-toplevel

    try:
        firebase_admin.get_app()
    except ValueError:
        # Explicit projectId, not inferred from the environment: Vertex AI Agent Engine
        # auto-injects GOOGLE_CLOUD_PROJECT as the numeric project *number* (see config.py's
        # GCP_PROJECT_ID docstring for the full story) — an inferred project here would
        # verify each token's `aud` against that number instead of "prudently-hackathon",
        # silently 401ing every real token with no diagnosable error.
        firebase_admin.initialize_app(options={"projectId": GCP_PROJECT_ID})


def _verify(id_token: str) -> dict:
    """Shared verification path. Raises HTTPException(401) with a deliberately generic detail
    message — the previous version echoed the raw verifier exception text into the response
    (`f"Invalid token: {exc}"`), which leaks verifier-internal detail (clock-skew specifics,
    library internals) to an unauthenticated caller for no operational benefit.

    The real exception is logged explicitly here, not left to "the normal exception-logging
    path" — that claim was wrong. `HTTPException` is a *handled* response, not an unhandled
    error, so FastAPI never logs the chained `exc` on its own; a `logger.exception` call is the
    only thing that puts it in Cloud Logging at all. Confirmed the hard way: a real permission
    gap (see `check_revoked` below) 401'd every authenticated route on the deployed site with
    zero ERROR-severity log lines to explain why, because this function silently discarded the
    one exception that would have said exactly what was wrong.

    `check_revoked=True`: without it, calling `firebase_admin.auth.revoke_refresh_tokens(uid)`
    (the /auth/sign-out-everywhere endpoint) or disabling a user in the Firebase Console has no
    effect on a token already issued — verification would keep succeeding until the token's own
    short natural expiry. This is the actual revocation check that was missing. It costs one
    extra call to Identity Toolkit's `getAccountInfo`, which needs its own IAM grant on top of
    local JWT verification (`roles/firebaseauth.viewer` on prudently-api's Cloud Run runtime
    identity — `infra/terraform/modules/iam`) — the grant this function's own silent failure
    mode made unusually hard to diagnose."""
    _ensure_firebase_app()
    from firebase_admin import auth as firebase_auth  # pylint: disable=import-outside-toplevel

    try:
        return firebase_auth.verify_id_token(id_token, check_revoked=True)
    except Exception as exc:
        logger.warning("Firebase ID token verification failed: %s: %s", type(exc).__name__, exc)
        raise HTTPException(status_code=401, detail="Invalid or expired session.") from exc


def require_firebase_auth(authorization: str = Header(default="")) -> str:
    """FastAPI dependency verifying `Authorization: Bearer <idToken>`. Returns the verified
    user's uid on success; raises 401 on anything else — missing header, malformed header, a
    token that fails verification (expired, wrong project, tampered), or a token whose session
    has been explicitly revoked."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")
    decoded = _verify(authorization.removeprefix("Bearer "))
    return decoded["uid"]


def require_role(*roles: str):
    """Factory for a FastAPI dependency that requires both a valid session AND one of `roles`
    on the token's `role` custom claim (see scripts/set_user_role.py). Anything that renders a
    patient's decrypted identity (Part D) uses this rather than `require_firebase_auth` alone —
    docs/threat-model.md finding 6 is exactly "every authenticated user is equally privileged,"
    which is fine for a single demo account and not fine the moment patient PII exists.

    A token with no `role` claim at all (every account that predates this change) is rejected,
    not defaulted to any role — fails closed, matching this codebase's approval-policy
    convention (`services/platform/approvals.py`'s `check_policy`)."""

    def _dependency(authorization: str = Header(default="")) -> str:
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing bearer token.")
        decoded = _verify(authorization.removeprefix("Bearer "))
        if decoded.get("role") not in roles:
            raise HTTPException(status_code=403, detail="Not authorized for this resource.")
        return decoded["uid"]

    return _dependency


def optional_firebase_auth(authorization: str = Header(default="")) -> str | None:
    """Same verification, but a missing or invalid token yields None instead of a 401.

    Never raises. A route using this must treat None as "anonymous caller" and redact
    accordingly — the caller decides what an anonymous viewer may see, not this function. An
    *invalid* token is treated exactly like no token rather than as an error: these are public
    feeds, and a viewer whose session quietly expired should see the public view, not a broken
    dashboard.
    """
    if not authorization.startswith("Bearer "):
        return None
    try:
        return require_firebase_auth(authorization)
    except HTTPException:
        return None
