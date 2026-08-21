"""Local-emulated Agent Gateway: the actual `before_tool_callback` interceptor logic — see
gateway.py's module docstring for the pipeline and the Model Armor opt-in rationale."""

from __future__ import annotations

from google.adk.agents.context import Context
from google.adk.tools.base_tool import BaseTool

from .gateway import start_observability_span  # pylint: disable=cyclic-import
from .registry import get_registry_service  # pylint: disable=cyclic-import

# Coordinator → specialist authorization — a fixed allow-list rather than a Firestore table,
# since the caller set is exactly {"coordinator"} today (Day 5) and a hardcoded policy is
# easier to audit than a mutable one for a fleet this size. Revisit as a Firestore-backed
# table if a second Gateway-routed caller (e.g. Chaos calling into other specialists) shows up.
_POLICY_TABLE: dict[str, frozenset[str]] = {
    "coordinator": frozenset(
        {
            "shift_allocation_agent",
            "inventory_management_agent",
            "supply_chain_resiliency_agent",
            "hr_agent",
        }
    ),
}

# Opt-in only — see gateway.py's module docstring for why Armor isn't run on every call.
_ARMOR_SCREENED_AGENTS: frozenset[str] = frozenset()


def _blocked(reason: str) -> dict:
    return {"gateway_blocked": True, "reason": reason}


class LocalGatewayService:  # pylint: disable=too-few-public-methods
    def before_tool_call(self, tool: BaseTool, args: dict, tool_context: Context) -> dict | None:
        caller = tool_context.agent_name
        target = tool.name

        entry = get_registry_service().get_agent(target)
        if entry is None:
            return _blocked(f"Gateway: '{target}' is not a registered agent.")
        if entry.status != "active":
            return _blocked(f"Gateway: '{target}' is registered but not active ({entry.status}).")

        allowed_targets = _POLICY_TABLE.get(caller)
        if allowed_targets is None or target not in allowed_targets:
            return _blocked(f"Gateway: '{caller}' is not authorized to call '{target}'.")

        if target in _ARMOR_SCREENED_AGENTS:
            # pylint: disable-next=import-outside-toplevel,cyclic-import
            from .armor import get_armor_service

            result = get_armor_service().screen(str(args))
            if result.blocked:
                return _blocked(f"Gateway: Model Armor flagged this call — {result.reason}")

        start_observability_span(caller, target)
        return None
