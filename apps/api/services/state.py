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


def get_inventory() -> list[dict]:
    return [doc.to_dict() for doc in get_client().collection("inventory").stream()]


def get_vendors() -> list[dict]:
    return [doc.to_dict() for doc in get_client().collection("vendors").stream()]


def get_agent_registry() -> list[dict]:
    """Every `agent_registry` doc, unordered — the dashboard's fleet overview panel reads
    this directly rather than through services/platform/registry.py's `get_agent(name)`
    single-doc lookup, since the panel wants the whole roster, not one entry at a time."""
    return [doc.to_dict() for doc in get_client().collection("agent_registry").stream()]


def get_armor_events(limit: int = 20) -> list[dict]:
    """Most recent `armor_events` docs, newest first — the dashboard's BLOCKED-banner feed."""
    docs = (
        get_client()
        .collection("armor_events")
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    return [doc.to_dict() for doc in docs]


def get_chaos_experiments(limit: int = 20) -> list[dict]:
    """Most recent `chaos_experiments` docs, newest first — the dashboard's replay feed."""
    docs = (
        get_client()
        .collection("chaos_experiments")
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    return [doc.to_dict() for doc in docs]


def write_armor_event(event: dict) -> None:
    """Appends one Model Armor screening outcome to the `armor_events` collection — the
    dashboard's BLOCKED-banner feed (Aug 27, docs/build-plan.md §5) reads this. Auto-ID'd
    (`.add`, not `.set`): events have no natural key, and a screening can legitimately repeat
    for the same vendor/message pair (retries, replay)."""
    get_client().collection("armor_events").add(event)


def write_chaos_experiment(event: dict) -> None:
    """Appends one Chaos & Continuity experiment outcome to the `chaos_experiments`
    collection — run once for real, replayed from here for the demo rather than re-run live
    (docs/build-plan.md §5, Aug 28). Auto-ID'd for the same reason as `write_armor_event`."""
    get_client().collection("chaos_experiments").add(event)
