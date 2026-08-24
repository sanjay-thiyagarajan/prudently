"""Central settings, loaded from env vars (see .env.example for the full annotated list)."""

import os
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

Backend = Literal["vertex", "local"]

# Deliberately NOT a Settings field: Vertex AI Agent Engine auto-injects GOOGLE_CLOUD_PROJECT
# into the sandbox as the numeric project *number*, which pydantic-settings picks up and
# silently overrides any Settings field mapped to that env var name — and Firestore's
# resource-path resolution rejects the numeric form outright. Any code building a GCP resource
# path (Firestore, Memory Bank, Secret Manager) should import this constant, not
# get_settings().google_cloud_project.
GCP_PROJECT_ID = "prudently-hackathon"

# Same treatment, same reason: an approval-gated tool running inside a Reasoning Engine
# sandbox needs to write an absolute approve/reject link into an email body, and a plain
# constant can't be clobbered by Agent Engine's env injection the way a Settings field could.
# Get the current value via `gcloud run services describe prudently-api
# --format='value(status.url)'` — matches apps/web/Dockerfile's NEXT_PUBLIC_API_BASE_URL
# default.
PUBLIC_API_BASE_URL = "https://prudently-api-jnpvbtwpwa-uc.a.run.app"


# An agent's ADK name -> the Settings field naming its deployed Reasoning Engine. Lives here,
# not in either consumer, because two very different places need exactly this mapping and they
# must not be able to drift: services/memory.py resolves an agent's own Memory Bank store
# through it, and scripts/seed_registry.py writes the engine ids into the Firestore catalog the
# Gateway reads. A disagreement between those two would mean an agent whose memories live in a
# different engine than the registry advertises.
AGENT_ENGINE_SETTING: dict[str, str] = {
    "coordinator": "coordinator_agent_engine_id",
    "shift_allocation_agent": "shift_agent_engine_id",
    "inventory_management_agent": "inventory_agent_engine_id",
    "supply_chain_resiliency_agent": "supply_agent_engine_id",
    "hr_agent": "hr_agent_engine_id",
    "medical_representative_agent": "medrep_agent_engine_id",
    "chaos_continuity_agent": "chaos_agent_engine_id",
    "surgical_scheduling_agent": "surgical_scheduling_agent_engine_id",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    google_cloud_project: str = GCP_PROJECT_ID
    google_cloud_location: str = "us-central1"
    # Memory Bank scoped to a specific Reasoning Engine (agent_engine_id set) must use that
    # engine's own location, not a separate multi-region — location="us" 404s
    # ("ReasoningEngine does not exist") since our reasoning engines are deployed to
    # us-central1.
    memory_bank_location: str = "us-central1"

    google_genai_use_enterprise: bool = False
    model_reasoning: str = "gemini-3.5-flash"
    model_fast: str = "gemini-3.5-flash"
    gemini_api_key_secret: str = "prudently-gemini-api-key"

    # Reasoning Engine resource IDs, set after each agent's `adk deploy agent_engine`.
    shift_agent_engine_id: str = "6191105334669475840"
    inventory_agent_engine_id: str = "6199971796435861504"
    supply_agent_engine_id: str = "6129884527234908160"
    hr_agent_engine_id: str = "5467010957081313280"
    medrep_agent_engine_id: str = "6319035711584468992"
    chaos_agent_engine_id: str = "2682941962436214784"
    coordinator_agent_engine_id: str = "6956858008810815488"
    surgical_scheduling_agent_engine_id: str = "4989418290347507712"

    registry_backend: Backend = "local"
    identity_backend: Backend = "local"
    gateway_backend: Backend = "local"
    armor_backend: Backend = "vertex"
    observability_backend: Backend = "vertex"
    # Field-level encryption for patient PII (Part D) — "vertex" here follows this file's own
    # existing real-vs-local naming convention (armor_backend/observability_backend), not a
    # literal claim that Cloud KMS is a Vertex AI product.
    crypto_backend: Backend = "vertex"
    # Same pattern as armor_backend/observability_backend: only flips to a real backend once
    # independently verified against the live service.
    email_backend: Literal["gmail", "local"] = "gmail"

    # Manager/approver defaults for the email-approval workflow. Same account for both sender
    # and default approver by deliberate choice — see AGENTS.md's Gmail setup section.
    manager_email: str = "sanjayipscoc@gmail.com"
    gmail_sender_email: str = "sanjayipscoc@gmail.com"
    gmail_app_password_secret: str = "prudently-gmail-app-password"

    # docs/threat-model.md finding 1: the A2A mount has no auth of its own — Cloud Run's
    # `allUsers` invoker grant makes the whole service publicly reachable, and Agent Engine has
    # no per-agent mTLS. This is the pragmatic middle ground: a shared secret both the sender
    # (agents/supply/agent.py's RemoteA2aAgent httpx client) and the receiver (app.py's ASGI
    # gate in front of the mount) fetch from the same Secret Manager entry.
    a2a_shared_secret_secret: str = "prudently-a2a-shared-secret"

    # Cloud KMS key protecting patient PII fields (services/platform/crypto_kms.py). Regional,
    # not multi-region — same "must match the region lock" pattern as memory_bank_location and
    # model_armor_location above.
    kms_location: str = "us-central1"
    kms_key_ring: str = "prudently-patient-data"
    kms_key_id: str = "patient-pii"

    # Model Armor templates are regional, not multi-region — same "must match the region
    # lock" pattern as memory_bank_location above.
    model_armor_location: str = "us-central1"
    model_armor_template_id: str = "prudently-vendor-ingest"

    # Medical Representative is mounted as a sub-route of this same Cloud Run service (app.py)
    # rather than a separate service — see AGENTS.md's A2A section for why. Vertex AI Agent
    # Engine has no native A2A transport, so any Reasoning Engine that needs to reach Medical
    # Representative via A2A — Supply Chain — does so over the public internet at this URL,
    # not an internal call.
    medrep_a2a_host: str = "prudently-api-439570031916.us-central1.run.app"
    medrep_a2a_protocol: str = "https"
    medrep_a2a_rpc_path: str = "a2a/medrep"

    # Still legitimately used — packages/datagen's RNG seed for reproducible synthetic seed
    # data, and services/inventory_sim.py's ongoing consumption-noise generator. Unrelated to
    # the old sim clock (removed) or the real-time watch loop below.
    sim_seed: int = 42
    # How often the real-time fleet watch (services/watch_loop.py) checks live state on its
    # own, unprompted — see AGENTS.md's autonomous fleet watch section.
    watch_interval_seconds: int = 90
    dry_run: bool = True

    firestore_emulator_host: str | None = None
    pubsub_emulator_host: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def a2a_shared_secret() -> str:
    """Fetches the A2A shared secret from Secret Manager, cached for the process lifetime —
    same pattern as services/platform/email_gmail.py's `_app_password()`. Both the A2A sender
    (agents/supply/agent.py) and the receiver (app.py) call this so the two sides can never
    drift onto different values. Deliberately allowed to raise: unlike email (fail-soft is
    correct — a failed send shouldn't crash a tool call) an agent that cannot resolve its own
    A2A credential should fail loudly at startup, not silently send unauthenticated requests
    that the receiver will reject anyway."""
    from google.cloud import secretmanager  # pylint: disable=import-outside-toplevel

    client = secretmanager.SecretManagerServiceClient()
    name = (
        f"projects/{GCP_PROJECT_ID}/secrets/"
        f"{get_settings().a2a_shared_secret_secret}/versions/latest"
    )
    response = client.access_secret_version(name=name)
    return response.payload.data.decode("utf-8")


def medrep_agent_card_url() -> str:
    settings = get_settings()
    return (
        f"{settings.medrep_a2a_protocol}://{settings.medrep_a2a_host}"
        f"/{settings.medrep_a2a_rpc_path}/.well-known/agent-card.json"
    )


def bootstrap_gemini_credentials() -> None:
    """Fetches the Gemini API key from Secret Manager and sets it as GOOGLE_API_KEY, so
    ADK routes model calls through the direct Gemini API instead of Vertex's publisher-model
    endpoint (which 404s on gemini-3.5-flash in us-central1 — see
    docs/day1-probe-results.md). Called at agent module import time, before constructing any
    Agent() — including during plain unit-test collection of sibling pure-logic modules
    (agents/*/agent.py's package __init__.py imports agent.py eagerly, per ADK CLI
    convention), where there may be no GCP credentials available at all. Failures are
    swallowed on purpose: an agent that can't fetch its key will fail loudly and specifically
    when it actually tries to call the model, which is a far more diagnosable failure than a
    crashed import. The raw key is never written to a file or baked into the deploy bundle —
    only fetched at runtime via the caller's IAM identity."""
    if os.environ.get("GOOGLE_API_KEY"):
        return  # already set (e.g. local dev via shell env) — don't overwrite

    try:
        from google.cloud import secretmanager

        settings = get_settings()
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{GCP_PROJECT_ID}/secrets/{settings.gemini_api_key_secret}/versions/latest"
        response = client.access_secret_version(name=name)
        os.environ["GOOGLE_API_KEY"] = response.payload.data.decode("utf-8")
        os.environ["GOOGLE_GENAI_USE_ENTERPRISE"] = "false"
    except Exception:  # noqa: BLE001 — deliberately broad, see docstring
        pass
