"""One-time admin utility: sets a Firebase custom claim `role` on a user, by email.

Not scriptable from a route — this needs to run under an identity with
`firebase.projects.updateRole`-equivalent Admin SDK access (a developer's own `gcloud auth
application-default login` credentials, same as `make seed-registry`), not the Cloud Run
runtime identity. Mirrors the "manual, one-time, done via a throwaway script" treatment this
project already gives Firebase project creation and the Model Armor template (see AGENTS.md).

A custom claim only takes effect on that user's *next* token refresh (Firebase's client SDK
refreshes roughly hourly, or immediately if the user signs out and back in) — not retroactively
on an already-issued token still sitting in a browser tab.

Usage:
    uv run python -m scripts.set_user_role manager@prudently.app admin
    uv run python -m scripts.set_user_role someone@example.com clinician
"""

from __future__ import annotations

import argparse
import sys

VALID_ROLES = ("admin", "clinician", "ops")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("email", help="the user's sign-in email")
    parser.add_argument("role", choices=VALID_ROLES)
    args = parser.parse_args()

    import firebase_admin
    from firebase_admin import auth as firebase_auth

    from config import GCP_PROJECT_ID

    try:
        firebase_admin.get_app()
    except ValueError:
        firebase_admin.initialize_app(options={"projectId": GCP_PROJECT_ID})

    try:
        user = firebase_auth.get_user_by_email(args.email)
    except firebase_auth.UserNotFoundError:
        print(f"No Firebase user with email {args.email!r}.", file=sys.stderr)
        raise SystemExit(1) from None

    firebase_auth.set_custom_user_claims(user.uid, {"role": args.role})
    print(f"Set role={args.role!r} for {args.email} (uid={user.uid}).")
    print("Takes effect on that user's next token refresh — sign out and back in to force it.")


if __name__ == "__main__":
    main()
