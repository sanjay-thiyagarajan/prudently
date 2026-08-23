"""Agent Gateway capability port — local-emulated only, by design (Day-1 probe found no
lightweight `gateways` resource in the `aiplatform` v1 discovery doc, and Apigee requires
org-level provisioning disproportionate to this build; see docs/day1-probe-results.md #5).
Implemented as an ADK `before_tool_callback` interceptor attached to the Coordinator: every
Coordinator → specialist call runs Registry lookup → policy-table check → (optional) Model
Armor → an Observability span hook, in that order, before the real tool executes.

Model Armor is intentionally NOT run on every Gateway call. Coordinator → specialist tool
args are model-generated from an operator's own request, not untrusted external input —
Armor's job is screening content at the one boundary where untrusted input actually enters
(Medical Representative's ingestion tool, services/platform/armor.py). Running a sanitize
round trip on every internal hop would cost real latency on the demo's hot path for no
security benefit. `_ARMOR_SCREENED_AGENTS` is the opt-in list for the rare Gateway-routed call
that should get it anyway — empty by default. Adding a name to that set makes Coordinator's
own deployed sandbox import `armor_vertex.py`, which imports `observability.py` — Coordinator's
`requirements.txt` must list `opentelemetry-sdk`/`opentelemetry-exporter-gcp-trace` (it does)
or that branch fails the same silent-truncation way the Observability rollout itself did the
first time (see AGENTS.md's "two deploy paths are not symmetric" note).

The Observability step wraps the whole decision (registry lookup, policy check, optional
Armor) in one real OTel span via services/platform/observability.py, not just a point-in-time
marker at the end — see gateway_local.py."""

from __future__ import annotations

from functools import lru_cache
from typing import Protocol

from google.adk.agents.context import Context
from google.adk.tools.base_tool import BaseTool


class GatewayService(Protocol):  # pylint: disable=too-few-public-methods
    def before_tool_call(
        self, tool: BaseTool, args: dict, tool_context: Context
    ) -> dict | None: ...  # noqa: E704


@lru_cache
def get_gateway_service() -> GatewayService:
    # pylint: disable-next=import-outside-toplevel,cyclic-import
    from .gateway_local import LocalGatewayService

    return LocalGatewayService()
