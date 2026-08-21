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
| Coordinator | root ADK agent, sole user-facing entry point — **deployed & verified** | `apps/api/agents/coordinator/agent.py` | primary | `agent_name=coordinator, user=<session>` | `agent_registry` (read) |
| Shift Allocation | specialist (`AgentTool`) — **deployed & verified** | `apps/api/agents/shift/agent.py` | primary | `agent_name=shift_allocation_agent, user=<unit>` | `staff_roster`, `shift_history` |
| Inventory Management | specialist (`AgentTool`) — tactical stock/par-level tracking — **deployed & verified** | `apps/api/agents/inventory/agent.py` | primary | `agent_name=inventory, user=<sku>` | `inventory` |
| Supply Chain Resiliency | specialist (`AgentTool`) — strategic vendor/reorder decisions; calls Medical Representative via **A2A** — **deployed & verified** | `apps/api/agents/supply/agent.py` | primary | `agent_name=supply, user=<vendor>` | `vendors` |
| HR | specialist (`AgentTool`) — credentialing + escalation target when Shift Allocation runs out of reallocation options — **deployed & verified** | `apps/api/agents/hr/agent.py` | primary | `agent_name=hr, user=<unit>` | `staff_roster` (read) |
| Medical Representative | **deployed separately**, external-facing vendor/pharma liaison, owns Model Armor screening of inbound vendor comms — **deployed & verified** | `apps/api/agents/medrep/agent.py` | **separate** (A2A boundary) | not wired yet — see note below | `armor_events` (write, one doc per screening call) |
| Chaos & Continuity | specialist (`AgentTool`), dual mode (hospital what-if + fleet fault-injection) — **deployed & verified** | `apps/api/agents/chaos/agent.py` | primary | `agent_name=chaos, user=<scenario>` | `chaos_experiments` (write) |

`staff_roster` also holds a per-diem coverage pool (`is_per_diem=true`, `staff_id` prefixed
`pd-`, one unit's worth of shift_history-free staff — see `packages/datagen/datagen/roster.py`
`_generate_perdiem_pool`) and a `credential_expiry` field per staff member, both added Day 4
for the HR Agent. Deployed via a scoped one-off script (`merge=True` into existing docs, plain
`set` for the new per-diem docs) rather than a full `make seed` reseed — `shift_history` has a
pre-existing doc-ID collision bug (all ~26 days of one staff member's shifts share a single
Firestore doc, since `write_firestore`'s `doc_id` falls back to bare `staff_id` for any
collection without its own unique key) plus a >500-write batch limit (real shift_history
volume is ~620 records) that `write_firestore` doesn't chunk for. Both are real, still-open
bugs — fix before relying on a from-scratch `make seed` (needed for the Aug 30 clean-clone
test), not fixed yet because reseeding would perturb the already-deployed/verified Shift
Allocation Agent's demo data with no benefit to Day 4 scope.

**Medical Representative is deliberately not wired to Memory Bank yet.**
`services/memory.py`'s `get_memory_service()` hardcodes `agent_engine_id` to Shift's engine —
writing through it from Medical Representative would mean this external-facing, adversarial-
input agent writes into Shift's memory store, inverting the trust boundary the agent exists
to demonstrate. Revisit once Memory Bank scoping is per-agent rather than hardcoded (Day 5
Coordinator/Gateway work).

Coordinator → Gateway → specialist is hub-and-spoke for everything except Supply Chain ↔
Medical Representative, which is genuine Agent2Agent across the one boundary in the design
that actually warrants a separately-deployed, separately-identified agent (external-facing,
untrusted by default). Every other specialist call flows through the Gateway interceptor.

**Coordinator's sub-agents are in-process AgentTool wraps, not network calls — this relies on
a flattened import that only works under two specific conditions, confirmed live Day 5.**
`agents/coordinator/agent.py` does `from shift.agent import root_agent`, not
`from agents.shift.agent import root_agent`. This resolves because:
1. **Locally** (`adk run agents/coordinator`): ADK's own loader adds the agent's parent dir
   (`agents/`) to `sys.path`, so every sibling folder (`shift`, `inventory`, `supply`, `hr`)
   is importable by its bare name.
2. **Deployed**: `adk deploy`'s `--extra_packages` stages each entry at `/app/<basename>`
   (per its own `--help` text) — `--extra_packages=agents/shift` lands at `/app/shift`, not
   `/app/agents/shift`. Deploying Coordinator needs `--extra_packages=agents/shift
   --extra_packages=agents/inventory --extra_packages=agents/supply --extra_packages=agents/hr`
   in addition to the usual `services`/`config.py`.

Verified with a disposable one-sub-agent probe deploy before committing to the real four-agent
Coordinator (see docs/build-plan.md Day 5), and the same "verify live, not just exit code 0"
discipline applied again adding Chaos as the fifth (`--extra_packages=agents/chaos`, Day 6).
`pylint agents` can't resolve these imports either way (it isn't running under either sys.path
condition) — see the `# pylint: disable-next=import-error,wrong-import-order` comments in
`agents/coordinator/agent.py`.

**Corollary — the flattened import means Coordinator has its own baked-in copy of every
sub-agent's source, frozen at Coordinator's last deploy time, not a live reference.** `adk
deploy`'s `--extra_packages` copies source into the image at deploy time; editing
`agents/supply/agent.py` after Coordinator was last deployed does not change what the
Coordinator's in-process `supply_chain_resiliency_agent` AgentTool actually runs, even though
Supply Chain's *own* standalone Reasoning Engine picks up the change on its own next deploy.
Caught live Day 5: Supply Chain's A2A wiring to Medical Representative was added and Supply
Chain was redeployed, but Coordinator wasn't — so every "verified via A2A" claim up to that
point had exercised Supply Chain's standalone engine, never the Coordinator → Supply Chain →
Medical Representative path a real user/demo actually takes. **Whenever any AgentTool
sub-agent's source changes, redeploy Coordinator too** (`--agent_engine_id=<coordinator-id>`,
same `--extra_packages` set) — a green test suite and a successful standalone-engine
verification do not imply the composed path works.

**Genuine A2A: Supply Chain → Medical Representative.** Vertex AI Agent Engine has no native
A2A transport (confirmed Day 5: no `a2a` fields anywhere in the Vertex SDK, no A2A flags on
`adk deploy agent_engine`) — `stream_query` and A2A are two different transports for two
different deployment shapes. Medical Representative is reached over A2A via
`google.adk.a2a.utils.agent_to_a2a.to_a2a()`, mounted as a sub-route of the `prudently-api`
Cloud Run service (`apps/api/app.py`, `/a2a/medrep`) rather than a separate Cloud Run service
— its own Reasoning Engine deployment already satisfies "separately deployed, separately
identified"; a third Cloud Run service would only buy structural purity, not anything a judge
can observe. `config.py`'s `medrep_a2a_*` settings + `medrep_agent_card_url()` build the
advertised card URL; `agents/supply/agent.py` reaches it via
`AgentTool(RemoteA2aAgent(agent_card=medrep_agent_card_url()))` — Supply Chain has no special
internal path to Medical Representative, it's the same public URL any A2A client would use.

Two gotchas, both found live Day 5, both would silently 404/misbehave without the fix:
1. **`to_a2a()`'s Starlette app attaches its JSON-RPC + agent-card routes inside its own
   ASGI lifespan** (building the agent card is async), and `Starlette.mount()` does **not**
   auto-forward the outer app's lifespan to a mounted sub-app. Without the fix, `app.mount()`
   succeeds silently but every mounted route 404s. Fix: give the outer `FastAPI(...)` an
   explicit `lifespan=` that does `async with medrep_a2a_app.router.lifespan_context(
   medrep_a2a_app): yield` — see `app.py`.
2. **The Cloud Run service and the Reasoning Engine runtime call Model Armor as two different
   identities.** `prudently-api` runs as `coordinator-agent-sa` (see `modules/cloud_run_api`),
   not the Reasoning Engine service agent — it needs its own `roles/modelarmor.user` grant
   (`modules/iam/main.tf`'s `coordinator_sa_modelarmor_user`). Without it, every A2A call
   through the mounted endpoint fails closed with `matched_filters=["armor_unavailable"]`
   instead of the real filter result — indistinguishable from a real block unless you check
   Cloud Run's own logs.

**Deploy-time requirement, learned the hard way (Day 3):** `adk deploy agent_engine` resolves
dependencies via plain `pip` against a `requirements.txt` **inside the agent's own folder**,
not the shared `uv.lock` — the two resolvers can diverge. Every agent folder needs its own
`requirements.txt` listing its actual runtime deps (`google-adk[a2a]`,
`google-cloud-aiplatform[adk,agent_engines]`, plus whatever `services/*` modules it imports
transitively need — e.g. `google-cloud-firestore`, `google-cloud-secret-manager`,
`pydantic-settings`).

**The two deploy paths are not symmetric — confirmed the hard way again, Day 5.** Cloud Run's
`prudently-api` builds from `apps/api/Dockerfile`, which runs `uv sync` against
`pyproject.toml` — it picks up every dependency listed there automatically. `adk deploy
agent_engine` does not: it only installs what that agent's own `requirements.txt` lists, full
stop, regardless of what's in `pyproject.toml`. Adding `opentelemetry-sdk` +
`opentelemetry-exporter-gcp-trace` to `pyproject.toml` for the Observability work (below) was
enough for Cloud Run but silently left Coordinator's and Medical Representative's
`requirements.txt` (and therefore their deployed sandboxes) without those packages. Symptom
was severe and non-obvious: `services/platform/observability_vertex.py` failing to import
inside `before_tool_callback` didn't raise a visible exception through `stream_query` — it
just truncated the event stream after the tool call with no error text at all, so *every*
Coordinator delegation broke, not just the one path being changed. Caught by testing the
simplest possible query (a plain `hr_agent` call, no A2A involved) after the actual A2A path
under test stalled, which isolated the regression from Observability generally rather than
from A2A specifically. Whenever a new dependency is added for `services/platform/` or any
other module a deployed agent imports, add it to that agent's `requirements.txt` too — adding
it to `pyproject.toml` alone is silently insufficient for anything deployed via `adk deploy
agent_engine`.

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

`apps/api/services/platform/` implements the five capabilities the Day-1 probe didn't confirm
as distinct real GCP products (Registry, Identity, Gateway, Model Armor, Observability) behind
a `<name>.py` Protocol. Model Armor and Observability each have both a real (`_vertex.py`) and
local (`_local.py`) implementation, selected by `ARMOR_BACKEND` / `OBSERVABILITY_BACKEND`
(both default `vertex`) — Registry, Identity, and Gateway are local-only by design (the Day-1
probe found no real GCP product backing any of them; see `docs/day1-probe-results.md` rows
#3–5), so `registry.py`/`gateway.py` have no `_vertex.py` counterpart and raise loudly if
`REGISTRY_BACKEND=vertex` is ever set. Agent Runtime and Memory Bank are confirmed real
products and are implemented directly (`apps/api/services/memory.py`) — no adapter needed for
those two. Status as of Day 5: Model Armor (Day 4, wired into `agents/medrep/agent.py`),
Registry (`registry.py`/`registry_local.py`, Firestore `agent_registry` collection, seeded by
`apps/api/scripts/seed_registry.py` / `make seed-registry`), Gateway
(`gateway.py`/`gateway_local.py`, the Coordinator's `before_tool_callback` — Registry lookup →
policy-table authorization → real Observability span, all inside one span covering the whole
decision; Model Armor is deliberately *not* run on every Gateway call, see `gateway.py`'s
module docstring), Identity (`identity.py`, a thin resolver over the Terraform-provisioned
per-agent SAs plus the one runtime service agent every deployed agent actually authenticates
as — no runtime enforcement, that's infra-layer per the Day-1 probe's own "honest framing for
judges"), and Observability (`observability.py`/`_local.py`/`_vertex.py`, real OTel spans
exported to Cloud Trace via `CloudTraceSpanExporter`, `SimpleSpanProcessor` not
`BatchSpanProcessor` — see `observability_vertex.py`'s docstring for why) are all built.
`armor_vertex.py`'s real Model Armor call and `gateway_local.py`'s whole decision are each
wrapped in their own span; `medrep/agent.py`'s `screen_vendor_message` wraps both in an outer
`medrep.screen_vendor_message` span and writes the resulting `trace_id` onto the
`armor_events` Firestore record it persists (`services/state.py`'s `write_armor_event`) — so a
blocked event in Firestore can be pivoted straight to its Cloud Trace detail. **Known gap:**
that trace_id is only valid within the process that created it — there is no cross-process
trace-context propagation across the A2A HTTP hop yet (would need
`opentelemetry-instrumentation-httpx` on `RemoteA2aAgent`'s `httpx_client` plus ASGI
instrumentation on the Cloud Run mount), so Supply Chain's own trace and Medical
Representative's trace are two separate, unlinked traces today, not one distributed trace.

**Model Armor setup, Day 4:** `modelarmor.googleapis.com` had to be enabled by hand
(`gcloud services enable modelarmor.googleapis.com`) — the Day-1 probe's claim that it was
"enabled in this project" was wrong; discovery-doc inspection confirmed the API *exists*, not
that it was turned on for `prudently-hackathon`. The `gcloud model-armor` CLI subcommand
group returns spurious `PERMISSION_DENIED` on both reads and writes even under project
Owner — confirmed a CLI/auth quirk, not a real permission gap, since the identical call
succeeds via a direct REST call and via the `google-cloud-modelarmor` Python SDK immediately
after; the template (`prudently-vendor-ingest`, `us-central1`, `pi_and_jailbreak` +
`malicious_uri` + `rai` filters) was created via REST, everything else uses the SDK. The
deployed Reasoning Engine runtime identity
(`service-<project-number>@gcp-sa-aiplatform-re.iam.gserviceaccount.com`, same one from the
Firestore gotcha above) needs `roles/modelarmor.user` — granted by hand Day 4
(`gcloud projects add-iam-policy-binding`), also added to
`infra/terraform/modules/iam/main.tf` for `terraform apply` to catch up.

## Local dev

```
make api-dev       # uv-run FastAPI app (apps/api), Firestore/Pub/Sub emulators expected running
make web-dev       # Next.js dev server (apps/web)
make seed          # regenerate synthetic data via packages/datagen and load into Firestore/emulator
make dev           # api-dev + web-dev together
cd apps/api && make seed-registry   # (re)seed the agent_registry Firestore collection the Gateway reads
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
