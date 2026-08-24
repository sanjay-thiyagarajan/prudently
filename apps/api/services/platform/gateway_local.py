"""Local-emulated Agent Gateway: the actual `before_tool_callback` interceptor logic — see
gateway.py's module docstring for the pipeline and the Model Armor opt-in rationale."""

from __future__ import annotations

from google.adk.agents.context import Context
from google.adk.tools.base_tool import BaseTool

from services.state import log_activity

from .observability import get_observability_service  # pylint: disable=cyclic-import
from .registry import get_registry_service  # pylint: disable=cyclic-import

# Coordinator → specialist authorization — a fixed allow-list rather than a Firestore table,
# since the caller set is exactly {"coordinator"} and a hardcoded policy is easier to audit
# than a mutable one for a fleet this size. Revisit as a Firestore-backed table if a second
# Gateway-routed caller (e.g. Chaos calling into other specialists) shows up.
_POLICY_TABLE: dict[str, frozenset[str]] = {
    "coordinator": frozenset(
        {
            "shift_allocation_agent",
            "inventory_management_agent",
            "supply_chain_resiliency_agent",
            "hr_agent",
            "chaos_continuity_agent",
            "surgical_scheduling_agent",
        }
    ),
}

# Opt-in only — see gateway.py's module docstring for why Armor isn't run on every call.
_ARMOR_SCREENED_AGENTS: frozenset[str] = frozenset()


def _blocked(reason: str) -> dict:
    return {"gateway_blocked": True, "reason": reason}


def _log_routing_decision(
    caller: str, target: str, decision: str, reason: str, trace_id: str | None
) -> None:
    # Best-effort, same as every other audit-log write in this codebase: a Firestore write
    # failing must never take down the routing decision itself, which already happened.
    try:
        log_activity(
            caller,
            "routing_decision",
            reason,
            tool_name=target,
            status=decision,
            trace_id=trace_id,
        )
    except Exception:  # pylint: disable=broad-exception-caught
        pass


class LocalGatewayService:  # pylint: disable=too-few-public-methods
    def before_tool_call(self, tool: BaseTool, args: dict, tool_context: Context) -> dict | None:
        caller = tool_context.agent_name
        target = tool.name

        with get_observability_service().span(
            "gateway.before_tool_call", {"gateway.caller": caller, "gateway.target": target}
        ) as span:
            entry = get_registry_service().get_agent(target)
            if entry is None:
                span.set_attribute("gateway.decision", "blocked_unregistered")
                reason = f"Gateway: '{target}' is not a registered agent."
                _log_routing_decision(caller, target, "blocked_unregistered", reason, span.trace_id)
                return _blocked(reason)
            if entry.status != "active":
                span.set_attribute("gateway.decision", "blocked_inactive")
                reason = f"Gateway: '{target}' is registered but not active ({entry.status})."
                _log_routing_decision(caller, target, "blocked_inactive", reason, span.trace_id)
                return _blocked(reason)

            allowed_targets = _POLICY_TABLE.get(caller)
            if allowed_targets is None or target not in allowed_targets:
                span.set_attribute("gateway.decision", "blocked_unauthorized")
                reason = f"Gateway: '{caller}' is not authorized to call '{target}'."
                _log_routing_decision(caller, target, "blocked_unauthorized", reason, span.trace_id)
                return _blocked(reason)

            if target in _ARMOR_SCREENED_AGENTS:
                # pylint: disable-next=import-outside-toplevel,cyclic-import
                from .armor import get_armor_service

                result = get_armor_service().screen(str(args))
                if result.blocked:
                    span.set_attribute("gateway.decision", "blocked_armor")
                    reason = f"Gateway: Model Armor flagged this call — {result.reason}"
                    _log_routing_decision(caller, target, "blocked_armor", reason, span.trace_id)
                    return _blocked(reason)

            span.set_attribute("gateway.decision", "allowed")
            _log_routing_decision(
                caller, target, "allowed", f"Routed '{caller}' → '{target}'.", span.trace_id
            )
            return None
