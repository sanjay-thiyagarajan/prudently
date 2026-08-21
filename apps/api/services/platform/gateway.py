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
that should get it anyway — empty by default.

The Observability step is a named no-op today — real OTel span creation is Aug 27 scope (see
docs/build-plan.md §5) — kept as an explicit call so wiring it in later is a one-line change,
not a new interception point."""

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


def start_observability_span(caller: str, target: str) -> None:  # pylint: disable=unused-argument
    """No-op placeholder for the OTel span the Gateway will emit once Observability lands
    (docs/build-plan.md Aug 27) — call site is wired now so that day's change is additive."""
