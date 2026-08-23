"""Agent Identity capability port — local-emulated only (Day-1 probe found no distinct
`identities` resource in the `aiplatform` v1 discovery doc; see docs/day1-probe-results.md
#4). This is deliberately a thin resolver over identity metadata that already exists, not a
runtime enforcement layer: actual authentication when an agent calls a GCP API is handled by
Application Default Credentials inside the deployed sandbox, and every deployed agent actually
runs as the single shared Reasoning Engine service agent
(`service-<project-number>@gcp-sa-aiplatform-re.iam.gserviceaccount.com`), not its own
per-agent service account. The per-agent SAs (`infra/terraform/modules/iam/main.tf`) exist for
local dev and any future custom-SA support, and are what this resolver reports as an agent's
'designed' identity — this module does not check or enforce which identity actually
authenticated a call. Any real access-control decision for a Gateway-routed call belongs in
gateway.py's policy table, not here."""

from __future__ import annotations

from typing import Protocol

from config import GCP_PROJECT_ID

# Mirrors infra/terraform/modules/iam/main.tf's `agent_names` local — kept in sync by hand,
# not read from Terraform state, since this only needs to answer "what SA would this agent
# use for local dev," not reflect live IAM policy.
_AGENT_SERVICE_ACCOUNTS = {
    name: f"{name}-agent-sa@{GCP_PROJECT_ID}.iam.gserviceaccount.com"
    for name in ("coordinator", "shift", "inventory", "supply", "hr", "medrep", "chaos")
}

# What every deployed agent actually authenticates as on Vertex AI Agent Engine, regardless
# of the per-agent SA above — see AGENTS.md's "Service accounts / IAM" section. Project
# number, not project ID, per Agent Engine's own resource-path convention.
RUNTIME_SERVICE_AGENT = "service-439570031916@gcp-sa-aiplatform-re.iam.gserviceaccount.com"


class IdentityService(Protocol):  # pylint: disable=too-few-public-methods
    def resolve(self, agent_name: str) -> dict: ...  # noqa: E704


class LocalIdentityService:  # pylint: disable=too-few-public-methods
    def resolve(self, agent_name: str) -> dict:
        return {
            "agent_name": agent_name,
            "designed_service_account": _AGENT_SERVICE_ACCOUNTS.get(agent_name),
            "actual_runtime_identity": RUNTIME_SERVICE_AGENT,
        }


def get_identity_service() -> IdentityService:
    return LocalIdentityService()
