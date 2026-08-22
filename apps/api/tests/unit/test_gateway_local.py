"""Unit tests for LocalGatewayService.before_tool_call — the real interceptor logic behind
the Coordinator's before_tool_callback. Previously only verified ad hoc against synthetic
FakeTool/SimpleNamespace contexts (see AGENTS.md); checked in now since this session's
Observability wiring touched every branch."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from services.platform.gateway_local import LocalGatewayService  # noqa: E402
from services.platform.observability_local import LocalObservabilityService  # noqa: E402
from services.platform.registry import RegistryEntry  # noqa: E402


@dataclass
class FakeTool:
    name: str


class FakeRegistry:
    def __init__(self, entries: dict[str, RegistryEntry]) -> None:
        self._entries = entries

    def get_agent(self, agent_name: str) -> RegistryEntry | None:
        return self._entries.get(agent_name)


def _entry(name: str, status: str = "active") -> RegistryEntry:
    return RegistryEntry(
        agent_name=name,
        role="specialist",
        status=status,
        reasoning_engine_id="123",
        firestore_collections=(),
    )


def _context(agent_name: str) -> SimpleNamespace:
    return SimpleNamespace(agent_name=agent_name)


def _patch_registry(monkeypatch, entries: dict[str, RegistryEntry]) -> None:
    monkeypatch.setattr(
        "services.platform.gateway_local.get_registry_service",
        lambda: FakeRegistry(entries),
    )
    # Force the no-op Observability adapter — hermetic for CI/clean-clone, no GCP credentials
    # or network call needed to exercise the Gateway's decision logic.
    monkeypatch.setattr(
        "services.platform.gateway_local.get_observability_service",
        lambda: LocalObservabilityService(),
    )
    # Same hermeticity goal — every decision branch now also calls log_activity, which would
    # otherwise hit real Firestore on every test run.
    monkeypatch.setattr("services.platform.gateway_local.log_activity", lambda *a, **kw: None)


def test_allows_registered_active_authorized_target(monkeypatch):
    _patch_registry(monkeypatch, {"hr_agent": _entry("hr_agent")})
    result = LocalGatewayService().before_tool_call(
        FakeTool("hr_agent"), {}, _context("coordinator")
    )
    assert result is None


def test_blocks_unregistered_target(monkeypatch):
    _patch_registry(monkeypatch, {})
    result = LocalGatewayService().before_tool_call(
        FakeTool("ghost_agent"), {}, _context("coordinator")
    )
    assert result == {
        "gateway_blocked": True,
        "reason": "Gateway: 'ghost_agent' is not a registered agent.",
    }


def test_blocks_inactive_target(monkeypatch):
    _patch_registry(monkeypatch, {"hr_agent": _entry("hr_agent", status="retired")})
    result = LocalGatewayService().before_tool_call(
        FakeTool("hr_agent"), {}, _context("coordinator")
    )
    assert result == {
        "gateway_blocked": True,
        "reason": "Gateway: 'hr_agent' is registered but not active (retired).",
    }


def test_blocks_unauthorized_caller(monkeypatch):
    _patch_registry(monkeypatch, {"hr_agent": _entry("hr_agent")})
    result = LocalGatewayService().before_tool_call(
        FakeTool("hr_agent"), {}, _context("chaos_continuity_agent")
    )
    assert result == {
        "gateway_blocked": True,
        "reason": "Gateway: 'chaos_continuity_agent' is not authorized to call 'hr_agent'.",
    }
