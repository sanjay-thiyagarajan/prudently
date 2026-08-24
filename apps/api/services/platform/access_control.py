"""Application-layer access control for patient PII (Part D) — docs/threat-model.md finding 9's
defense-in-depth mitigation, given Agent Engine has no per-agent IAM identity to enforce this at
the platform layer (every deployed agent shares one Reasoning Engine service agent, confirmed in
`infra/terraform/modules/iam/main.tf` — see AGENTS.md's "shared Reasoning Engine identity"
section). Every `patients`/`surgical_cases` accessor in `services/state.py` routes through
`require_access`, which checks the caller's *self-declared* identity against an explicit
allowlist before the read/write proceeds.

**Honest framing, stated plainly because a defense-in-depth control that oversells itself is
worse than none:** this is not cryptographic enforcement. A caller could lie about who it is —
there is no per-agent credential for `require_access` to verify a claimed identity against, the
same platform gap this module exists to work around. What it *does* catch is exactly what it's
for: an accidental cross-agent access — a function added to `hr/agent.py` or `shift/agent.py`
that imports and calls a patient accessor it was never meant to reach, the same class of mistake
per-agent IAM isolation would catch on a platform that supported it. It is a real, useful control
against accidental scope creep inside this codebase, and a real signal in a code review ("why is
a non-surgical-scheduling caller in this allowlist?") — it is not a security boundary against a
genuinely malicious caller with code-execution inside the fleet, which no application-layer check
can be."""

from __future__ import annotations

# Deliberately narrow. "dashboard_route" covers routes/surgical_scheduling.py's own accessors,
# which are separately gated by services/auth.py's require_role("admin", "clinician") before
# ever reaching here — two independent gates, not one doing double duty. "fleet_watch" covers
# services/fleet_watch.py's own conflict-detection read, which only ever calls
# get_surgical_cases (no patient identity on that collection at all — see that accessor's own
# docstring) to feed services/triggers.py's edge-triggered schedule_conflict detection; it never
# touches the patients collection.
_ALLOWED_CALLERS = frozenset({"surgical_scheduling_agent", "dashboard_route", "fleet_watch"})


class AccessDenied(Exception):
    pass


def require_access(caller: str) -> None:
    if caller not in _ALLOWED_CALLERS:
        raise AccessDenied(
            f"{caller!r} is not allowlisted to access patient PII collections. "
            f"Allowed callers: {sorted(_ALLOWED_CALLERS)}."
        )
