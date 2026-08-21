"""Firestore live-state accessors — "what is currently true" (roster, shifts, inventory,
admissions), distinct from Memory Bank's "what an agent remembers/reasoned about"
(services/memory.py). Collections are seeded by packages/datagen/datagen/seed.py."""

from __future__ import annotations

from functools import lru_cache

from google.cloud import firestore

# Root-caused via a live diagnostic tool deployed to Agent Engine (see git history / Day 3
# notes): Vertex AI Agent Engine auto-injects GOOGLE_CLOUD_PROJECT into the sandbox as the
# numeric *project number* (e.g. "439570031916"), not the project ID. pydantic-settings
# picks that env var up automatically, silently overriding config.py's "prudently-hackathon"
# default — so get_settings().google_cloud_project resolves to the number at runtime.
# Firestore's resource-path resolution does not accept the numeric form the same way most
# other GCP APIs do, and fails with a confusing "database (default) does not exist" 404 for
# a database that demonstrably exists (confirmed reachable via the identical code path from
# Cloud Run, where GOOGLE_CLOUD_PROJECT happens not to collide the same way). Hardcoded
# here, deliberately bypassing config.py, specifically to dodge that env var collision.
FIRESTORE_PROJECT_ID = "prudently-hackathon"


@lru_cache
def get_client() -> firestore.Client:
    return firestore.Client(project=FIRESTORE_PROJECT_ID, database="(default)")


def get_staff_roster() -> list[dict]:
    return [doc.to_dict() for doc in get_client().collection("staff_roster").stream()]


def get_shift_history() -> list[dict]:
    return [doc.to_dict() for doc in get_client().collection("shift_history").stream()]
