# Prudently

Agent-monitored hospital operations fleet, built for the **All Things Agentic Hackathon**
(Fortified Enterprise Fleet track). A Coordinator agent routes through an Agent Gateway to
five internal specialist agents, plus a Medical Representative agent deployed separately and
reached via genuine Agent2Agent — demoed against a scripted flu-outbreak surge at a single
hospital. See `docs/build-plan.md` for the full build plan and `docs/day1-probe-results.md`
for which of the seven Fortified Enterprise Fleet capabilities are backed by real GCP
products vs. local-emulated fallbacks.

## Agent roster

| Agent | Role | File | Reasoning Engine | Memory Bank scope | Firestore collections |
|---|---|---|---|---|---|
| Coordinator | root ADK agent, sole user-facing entry point | `apps/api/agents/coordinator/agent.py` | primary | `agent_name=coordinator, user=<session>` | `agent_registry` (read) |
| Shift Allocation | specialist (`AgentTool`) — **deployed & verified** | `apps/api/agents/shift/agent.py` | primary | `agent_name=shift_allocation_agent, user=<unit>` | `staff_roster`, `shift_history` |
| Inventory Management | specialist (`AgentTool`) — tactical stock/par-level tracking — **deployed & verified** | `apps/api/agents/inventory/agent.py` | primary | `agent_name=inventory, user=<sku>` | `inventory` |
| Supply Chain Resiliency | specialist (`AgentTool`) — strategic vendor/reorder decisions; calls Medical Representative via **A2A** — **deployed & verified** | `apps/api/agents/supply/agent.py` | primary | `agent_name=supply, user=<vendor>` | `vendors` |
| HR | specialist (`AgentTool`) — credentialing + escalation target when Shift Allocation runs out of reallocation options | `apps/api/agents/hr/agent.py` | primary | `agent_name=hr, user=<unit>` | `staff_roster` (read) |
| Medical Representative | **deployed separately**, external-facing vendor/pharma liaison, owns Model Armor screening of inbound vendor comms | `apps/api/agents/medrep/agent.py` | **separate** (A2A boundary) | `agent_name=medrep, user=<vendor>` | none (ingestion only, writes via Supply Chain) |
| Chaos & Continuity | specialist (`AgentTool`), dual mode (hospital what-if + fleet fault-injection) | `apps/api/agents/chaos/agent.py` | primary | `agent_name=chaos, user=<scenario>` | `chaos_experiments` |

Coordinator → Gateway → specialist is hub-and-spoke for everything except Supply Chain ↔
Medical Representative, which is genuine Agent2Agent across the one boundary in the design
that actually warrants a separately-deployed, separately-identified agent (external-facing,
untrusted by default). Every other specialist call flows through the Gateway interceptor.

**Deploy-time requirement, learned the hard way (Day 3):** `adk deploy agent_engine` resolves
dependencies via plain `pip` against a `requirements.txt` **inside the agent's own folder**,
not the shared `uv.lock` — the two resolvers can diverge. Every agent folder needs its own
`requirements.txt` listing its actual runtime deps (`google-adk[a2a]`,
`google-cloud-aiplatform[adk,agent_engines]`, plus whatever `services/*` modules it imports
transitively need — e.g. `google-cloud-firestore`, `google-cloud-secret-manager`,
`pydantic-settings`).

**Two root-caused GCP gotchas that will bite every agent, not just Shift** (full story in
`apps/api/services/state.py` and `apps/api/config.py` comments):
1. Agent Engine auto-injects `GOOGLE_CLOUD_PROJECT` into the sandbox as the numeric project
   **number**, silently overriding pydantic-settings defaults. Firestore's resource-path
   resolution rejects the numeric form. Use `config.GCP_PROJECT_ID` (a plain constant, not a
   Settings field) for any GCP resource path — Firestore, Memory Bank, Secret Manager.
2. Memory Bank scoped to a specific `agent_engine_id` must use **that engine's own region**
   (`us-central1`), not a separate multi-region — confirmed via a 404 "ReasoningEngine does
   not exist" when using `us`.

**Verification discipline:** `adk deploy` exiting 0 does not mean the agent works — 3 of 6
Shift Allocation deploy attempts "succeeded" while actually broken (missing deps, wrong
credential path, wrong Firestore project resolution), each only discoverable by querying the
deployed engine directly (`client.agent_engines.get(...).stream_query(...)`) and reading the
actual tool-call output, not just checking for the absence of a raised exception. Do this for
every new agent before considering it done.

## Platform adapter layer

`apps/api/services/platform/` implements five capabilities (Registry, Identity, Gateway,
Model Armor, Observability) as a port/adapter pair: `<name>.py` defines the `Protocol`,
`<name>_vertex.py` is the real-GCP-product implementation, `<name>_local.py` is the emulated
fallback. Which one is active is controlled by env vars (`REGISTRY_BACKEND`, `IDENTITY_BACKEND`,
`GATEWAY_BACKEND`, `ARMOR_BACKEND`, `OBSERVABILITY_BACKEND`, each `vertex|local`), decided by
the Day-1 probe and recorded in `docs/day1-probe-results.md`. Agent Runtime and Memory Bank
are confirmed real products and are implemented directly (`apps/api/services/memory.py`) —
no adapter needed for those two.

## Local dev

```
make api-dev     # uv-run FastAPI app (apps/api), Firestore/Pub/Sub emulators expected running
make web-dev      # Next.js dev server (apps/web)
make seed         # regenerate synthetic data via packages/datagen and load into Firestore/emulator
make dev          # api-dev + web-dev together
```

## Running / deploying an agent via the ADK CLI

```
PYTHONPATH=. adk run apps/api/agents/shift "..."     # local, scripted single-agent invocation
                                                       # PYTHONPATH=. required: ADK's loader only
                                                       # adds the agent's parent dir to sys.path,
                                                       # not the apps/api project root

adk deploy agent_engine agents/shift \
  --project=prudently-hackathon --region=us-central1 \
  --agent_engine_id=<id-to-update-in-place> \
  --display_name="..." --extra_packages=services --extra_packages=config.py
```

`--extra_packages` stages `services/` and `config.py` alongside the agent so its
`from services.state import ...` / `from config import ...` absolute imports resolve inside
the deployed sandbox. Run from `apps/api/` (relative agent path).

## Service accounts / IAM

Per-agent service accounts (`shift-agent-sa@`, `supply-agent-sa@`, `chaos-agent-sa@`,
`coordinator-agent-sa@`, ...) are created in `infra/terraform/modules/iam`. **These are not
what deployed agents actually run as** — confirmed Day 3, Agent Engine has no
`--service_account` deploy flag and runs under Google's own
`service-<project-number>@gcp-sa-aiplatform-re.iam.gserviceaccount.com`. Both identities get
IAM grants (`modules/iam`, `modules/secrets`) — the per-agent SAs for local dev / any future
custom-SA support, the reasoning-engine service agent because it's what's actually running in
production right now.
**Never commit a service-account key file** — `.gitignore` blocks `service-account*.json`.

## Makefile targets

`dev`, `api-dev`, `web-dev`, `seed`, `probe` (Day-1 capability spike), `tf-plan`, `tf-apply`,
`deploy` (both Cloud Run services), `lint`, `test`, `eval`, `commit`.

## Testing conventions

pytest with a coverage gate (`--cov-fail-under=80`), scoped to pure logic only —
`agents.shift.burndown` (100% as of Day 3), `agents.inventory.par_levels`,
`agents.supply.reorder`, `agents.hr.credentialing`, `services.simclock`, `services.platform`
(see `apps/api/pyproject.toml` `[tool.coverage.run]`). ADK orchestration glue (`agent.py`
files, `services/memory.py`, `services/state.py`) is excluded — proven Day 3 that even
*importing* those under pytest can trigger live GCP calls (`agent.py`'s module-level
`bootstrap_gemini_credentials()` call) unless carefully guarded; `bootstrap_gemini_credentials`
now swallows failures on purpose so imports never crash, but the gate still shouldn't cover
that code path. `make commit` runs lint + tests on staged files before committing.

## Terraform

```
cd infra/terraform/envs/dev && terraform init && terraform plan && terraform apply
```

Local tfstate is a deliberate hackathon-scope choice, not a production pattern. **Region is
locked to `us-central1`** for Cloud Run/Pub/Sub/Firestore/Reasoning Engine **and Memory Bank**
(not a separate `us` multi-region — see the gotcha #2 above) — do not change post-lock,
Firestore location is immutable after creation.

## Simulation clock

`SIM_SEED` and `SIM_SPEEDUP` env vars control the synthetic flu-surge timeline
(`apps/api/services/simclock.py`). At each simulated-day boundary, `routes/sim.py` computes
current burndown and writes a Memory Bank fact per unit via `services/memory.write_fact` —
this is what gives agents a narrative timeline to reason over across "weeks" compressed into
a demo. Reset via `POST /sim/reset` before reshooting the demo video for a deterministic
replay.
