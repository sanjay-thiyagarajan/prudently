"""Verify that deployed Reasoning Engines are actually working — not merely deployed.

Two traps this exists to catch, both hit for real on this project:

1. **`adk deploy` prints "Deploy failed" and still exits 0.** Observed live on Aug 23: a
   `Connection reset by peer` mid-deploy produced `Deploy failed: [Errno 54] ...` on stdout and
   an exit code of 0, so any script branching on `$?` records a success. Deploy outcome has to
   be read from the output text, and confirmed against the engine itself.
2. **A successful deploy can still serve the previous build for a short window.** Agent Engine
   keeps a warm sandbox, so even a passing smoke test immediately after deploying can be
   running old code. `update_time` is the honest signal for "the new revision landed".

`stream_query` from a laptop is genuinely flaky — 3 of 4 bare attempts reset mid-stream during
this build — so the live call is retried. A reset is a transport problem, not an agent problem,
and failing the whole verification on one is how you end up chasing a bug that isn't there.

Usage:
    uv run python -m scripts.verify_deploys                 # every engine, metadata only
    uv run python -m scripts.verify_deploys --query         # also run one live turn each
    uv run python -m scripts.verify_deploys --only shift    # one agent
"""

from __future__ import annotations

import argparse
import sys
import time

import vertexai

from config import AGENT_ENGINE_SETTING, GCP_PROJECT_ID, get_settings

# A cheap, read-only question per agent that should always produce a tool call. Deliberately
# nothing consequential: verification must never create an approval or send mail.
_SMOKE_PROMPT = {
    "coordinator": "In one sentence, what is the current staffing risk?",
    "shift_allocation_agent": "How many staff are at critical fatigue risk? Do not notify anyone.",
    "inventory_management_agent": "Which SKUs are low on stock?",
    "supply_chain_resiliency_agent": "Does anything need reordering? Do not contact any vendor.",
    "hr_agent": "Whose credentials have expired?",
    "chaos_continuity_agent": "List the fault-injection experiments you can run.",
    "medical_representative_agent": "What is your role in one sentence?",
}

_QUERY_ATTEMPTS = 3


def _client() -> vertexai.Client:
    return vertexai.Client(project=GCP_PROJECT_ID, location="us-central1")


def _engine_name(engine_id: str) -> str:
    return f"projects/{GCP_PROJECT_ID}/locations/us-central1/reasoningEngines/{engine_id}"


def _run_query(client: vertexai.Client, engine_id: str, prompt: str) -> tuple[bool, str]:
    """Returns (ok, detail). Retries transport resets, which are common and not the agent's
    fault; a genuine agent error surfaces identically on every attempt."""
    last = ""
    for attempt in range(1, _QUERY_ATTEMPTS + 1):
        try:
            engine = client.agent_engines.get(name=_engine_name(engine_id))
            tools: list[str] = []
            text: list[str] = []
            for event in engine.stream_query(message=prompt, user_id="deploy-verify"):
                for part in (event.get("content") or {}).get("parts", []) or []:
                    if "function_call" in part:
                        tools.append(part["function_call"].get("name", "?"))
                    if part.get("text"):
                        text.append(part["text"])
            answer = "".join(text).strip()
            if not answer and not tools:
                last = "empty response — the event stream truncated with no error text"
                continue
            return True, f"tools={tools or '[]'} · {answer[:90]!r}"
        except Exception as exc:  # pylint: disable=broad-exception-caught
            last = f"{type(exc).__name__}: {exc}"
            if attempt < _QUERY_ATTEMPTS:
                time.sleep(4 * attempt)
    return False, last


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify deployed Reasoning Engines.")
    parser.add_argument("--only", help="Only agents whose name contains this substring.")
    parser.add_argument("--query", action="store_true", help="Also run one live turn each.")
    args = parser.parse_args()

    settings = get_settings()
    client = _client()
    failures: list[str] = []

    agents = [a for a in AGENT_ENGINE_SETTING if not args.only or args.only in a]
    if not agents:
        print(f"No agents matched '{args.only}'.")
        return 1

    for agent in agents:
        engine_id = getattr(settings, AGENT_ENGINE_SETTING[agent])
        try:
            engine = client.agent_engines.get(name=_engine_name(engine_id))
            updated = getattr(engine.api_resource, "update_time", None)
            print(f"  {agent:32} engine {engine_id}  updated {updated}")
        except Exception as exc:  # pylint: disable=broad-exception-caught
            print(f"  {agent:32} UNREACHABLE — {type(exc).__name__}: {exc}")
            failures.append(agent)
            continue

        if args.query:
            ok, detail = _run_query(client, engine_id, _SMOKE_PROMPT.get(agent, "Hello."))
            print(f"  {'':32} {'LIVE OK' if ok else 'LIVE FAIL'}  {detail}")
            if not ok:
                failures.append(agent)

    print()
    if failures:
        print(f"{len(failures)} agent(s) need attention: {', '.join(sorted(set(failures)))}")
        return 1
    print(f"All {len(agents)} agent(s) verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
