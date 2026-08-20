# Prudently

Agent-monitored hospital operations fleet, built for the **All Things Agentic Hackathon**
(Fortified Enterprise Fleet track). A Coordinator agent routes through an Agent Gateway to
three specialist agents — Shift Allocation, Supply Chain Resiliency, and Chaos & Continuity —
demoed against a scripted flu-outbreak surge at a single hospital. See
`docs/build-plan.md` for the full build plan and `docs/day1-probe-results.md` for which of
the seven Fortified Enterprise Fleet capabilities are backed by real GCP products vs.
local-emulated fallbacks.

## Agent roster

| Agent | Role | File | Memory Bank scope | Firestore collections |
|---|---|---|---|---|
| Coordinator | root ADK agent, sole user-facing entry point | `apps/api/agents/coordinator/agent.py` | `agent_name=coordinator, user=<session>` | `agent_registry` (read) |
| Shift Allocation | specialist (`AgentTool`) | `apps/api/agents/shift/agent.py` | `agent_name=shift, user=<unit>` | `staff_roster`, `shift_history` |
| Supply Chain Resiliency | specialist (`AgentTool`) | `apps/api/agents/supply/agent.py` | `agent_name=supply, user=<sku/vendor>` | `inventory`, `vendors` |
| Chaos & Continuity | specialist (`AgentTool`), dual mode (hospital what-if + fleet fault-injection) | `apps/api/agents/chaos/agent.py` | `agent_name=chaos, user=<scenario>` | `chaos_experiments` |

All specialist calls flow through the Coordinator → Gateway interceptor. Specialists do not
call each other directly (except Chaos's hospital-domain what-if queries, which still route
through the Coordinator/Gateway, not peer-to-peer).

## Platform adapter layer

`apps/api/services/platform/` implements five capabilities (Registry, Identity, Gateway,
Model Armor, Observability) as a port/adapter pair: `<name>.py` defines the `Protocol`,
`<name>_vertex.py` is the real-GCP-product implementation, `<name>_local.py` is the emulated
fallback. Which one is active is controlled by env vars (`REGISTRY_BACKEND`, `IDENTITY_BACKEND`,
`GATEWAY_BACKEND`, `ARMOR_BACKEND`, `OBSERVABILITY_BACKEND`, each `vertex|local`), decided by
the Day-1 probe and recorded in `docs/day1-probe-results.md`. Agent Runtime and Memory Bank
are confirmed real products and are implemented directly (`apps/api/services/memory.py`,
`apps/api/agents/runtime.py`) — no adapter needed for those two.

## Local dev

```
make api-dev     # uv-run FastAPI app (apps/api), Firestore/Pub/Sub emulators expected running
make web-dev      # Next.js dev server (apps/web)
make seed         # regenerate synthetic data via packages/datagen and load into Firestore/emulator
make dev          # api-dev + web-dev together
```

## Running an agent via the ADK CLI

```
adk web apps/api/agents/coordinator     # interactive playground, exercises the full fleet
adk run apps/api/agents/shift "..."     # scripted single-agent invocation
```

## Service accounts / IAM

Per-agent service accounts (`shift-agent-sa@`, `supply-agent-sa@`, `chaos-agent-sa@`,
`coordinator-agent-sa@`) are created in `infra/terraform/modules/iam` with least-privilege
IAM conditions scoping Firestore/Memory Bank access to each agent's own data. Cloud Run and
Reasoning Engine run under these SAs via Application Default Credentials.
**Never commit a service-account key file** — `.gitignore` blocks `service-account*.json`.

## Makefile targets

`dev`, `api-dev`, `web-dev`, `seed`, `probe` (Day-1 capability spike), `tf-plan`, `tf-apply`,
`deploy` (both Cloud Run services), `lint`, `test`, `eval`, `commit`.

## Testing conventions

pytest with a coverage gate (`--cov-fail-under=80`), scoped to pure logic and adapter
contracts only — `agents.shift.burndown`, `agents.supply.reorder`, `services.simclock`,
`services.platform` (see `apps/api/pyproject.toml` `[tool.coverage.run] omit`). ADK
orchestration glue and `packages/datagen` are excluded from the gate; they're covered by
`make eval` (agent eval harness) and manual smoke tests instead. `make commit` runs lint +
tests on staged files before committing, matching the `nerifect-backend` convention.

## Terraform

```
cd infra/terraform/envs/dev && terraform init && terraform plan && terraform apply
```

Local tfstate is a deliberate hackathon-scope choice, not a production pattern — documented,
not accidental. **Region is locked to `us-central1` (Cloud Run/Pub/Sub/Firestore/Reasoning
Engine) and `us` multi-region (Memory Bank) as of the Day-1 probe — do not change post-lock**,
Firestore location is immutable after creation.

## Simulation clock

`SIM_SEED` and `SIM_SPEEDUP` env vars control the synthetic flu-surge timeline
(`apps/api/services/simclock.py`, driven by Pub/Sub `sim-ticks`). Reset via `POST
/sim/reset` before reshooting the demo video to get a deterministic replay.
