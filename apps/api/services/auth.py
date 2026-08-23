"""Firebase Authentication verification for manager-facing routes (policy config) — see
AGENTS.md's Firebase setup section for the one manual prerequisite (Firebase project creation,
Email/Password provider, one demo/judge account, done via the Firebase Console — not
scriptable from here). Read-only feeds (`/dashboard/overview`) and the approval click-through
links (`/approvals/*`) deliberately stay unauthenticated — see their own route modules and
app.py's CORS comment for why. This is a plain module, not a `services/platform/` adapter port:
there is exactly one real implementation and no local/offline fallback need — tests override
`require_firebase_auth` directly via FastAPI's `app.dependency_overrides`, not a `_local.py`."""

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
