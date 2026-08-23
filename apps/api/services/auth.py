"""Firebase Authentication verification for manager-facing routes — see AGENTS.md's Firebase
setup section for the one manual prerequisite (Firebase project creation, Email/Password
provider, one demo/judge account, done via the Firebase Console — not scriptable from here).

Three postures, deliberately distinct:

* `require_firebase_auth` — hard 401. Anything that writes manager config, or reads pay,
  hours, or an individual's record: `/policy/*`, `/payroll/*`, `/staff/*`.
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

from fastapi import Header, HTTPException

from config import GCP_PROJECT_ID


def require_firebase_auth(authorization: str = Header(default="")) -> str:
    """FastAPI dependency verifying `Authorization: Bearer <idToken>`. Returns the verified
    user's uid on success; raises 401 on anything else — missing header, malformed header, or
    a token that fails verification (expired, wrong project, tampered)."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")
    id_token = authorization.removeprefix("Bearer ")

    import firebase_admin  # pylint: disable=import-outside-toplevel
    from firebase_admin import auth as firebase_auth  # pylint: disable=import-outside-toplevel

    try:
        firebase_admin.get_app()
    except ValueError:
        # Explicit projectId, not inferred from the environment: Vertex AI Agent Engine
        # auto-injects GOOGLE_CLOUD_PROJECT as the numeric project *number* (see config.py's
        # GCP_PROJECT_ID docstring for the full story) — an inferred project here would
        # verify each token's `aud` against that number instead of "prudently-hackathon",
        # silently 401ing every real token with no diagnosable error.
        firebase_admin.initialize_app(options={"projectId": GCP_PROJECT_ID})

    try:
        decoded = firebase_auth.verify_id_token(id_token)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}") from exc

    return decoded["uid"]


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
