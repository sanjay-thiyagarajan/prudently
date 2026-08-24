# Prudently

Agent-monitored hospital operations fleet, built for the **All Things Agentic Hackathon**
(Fortified Enterprise Fleet track). A Coordinator agent routes through an Agent Gateway to
five internal specialist agents, plus a Medical Representative agent deployed separately and
reached via genuine Agent2Agent — demoed live against a real-time fleet watch (see "De-
simulation" below) over seeded baseline hospital data, not a scripted, manually-advanced
timeline. See `docs/build-plan.md` for the full build plan and `docs/day1-probe-results.md`
for which of the seven Fortified Enterprise Fleet capabilities are backed by real GCP
products vs. local-emulated fallbacks.

## Agent roster

| Agent | Role | File | Reasoning Engine | Memory Bank scope | Firestore collections |
|---|---|---|---|---|---|
| Coordinator | root ADK agent, sole user-facing entry point — **deployed & verified** | `apps/api/agents/coordinator/agent.py` | primary | `app_name=coordinator, user=<session>` (unused — it delegates) | `agent_registry` (read) |
| Shift Allocation | specialist (`AgentTool`) — **deployed & verified** | `apps/api/agents/shift/agent.py` | primary | `app_name=shift_allocation_agent, user=<unit>` | `staff_roster`, `shift_history` |
| Inventory Management | specialist (`AgentTool`) — tactical stock/par-level tracking — **deployed & verified** | `apps/api/agents/inventory/agent.py` | primary | `app_name=inventory_management_agent, user=<sku>` | `inventory` |
| Supply Chain Resiliency | specialist (`AgentTool`) — strategic vendor/reorder decisions; calls Medical Representative via **A2A** — **deployed & verified** | `apps/api/agents/supply/agent.py` | primary | `app_name=supply_chain_resiliency_agent, user=<vendor>` | `vendors` |
| HR | specialist (`AgentTool`) — credentialing + escalation target when Shift Allocation runs out of reallocation options — **deployed & verified** | `apps/api/agents/hr/agent.py` | primary | `app_name=hr_agent, user=<unit>` | `staff_roster` (read) |
| Medical Representative | **deployed separately**, external-facing vendor/pharma liaison, owns Model Armor screening of inbound vendor comms — **deployed & verified** | `apps/api/agents/medrep/agent.py` | **separate** (A2A boundary) | deliberately none — adversarial input, see note below | `armor_events` (write, one doc per screening call) |
| Chaos & Continuity | specialist (`AgentTool`), dual mode (hospital what-if + fleet fault-injection) — **deployed & verified** | `apps/api/agents/chaos/agent.py` | primary | `app_name=chaos_continuity_agent, user=<scenario>` | `chaos_experiments` (write) |

`staff_roster` also holds a per-diem coverage pool (`is_per_diem=true`, `staff_id` prefixed
`pd-`, one unit's worth of shift_history-free staff — see `packages/datagen/datagen/roster.py`
`_generate_perdiem_pool`) and a `credential_expiry` field per staff member, both added Day 4
for the HR Agent. Deployed via a scoped one-off script (`merge=True` into existing docs, plain
`set` for the new per-diem docs) rather than a full `make seed` reseed. `shift_history` had a
doc-ID collision bug and an unchunked >500-write batch at the time; **both were fixed Aug 22**
(`_doc_id_for` keys `shift_history` by `{staff_id}__{shift_date}`, and `write_firestore` chunks
at 450) — see "Data-layer bug fix" below for the full story. An earlier revision of this
section described them as still open; that was stale and is corrected here.

**Memory Bank is scoped per agent as of Aug 23, and the read path exists.** Both halves of
this used to be missing and the roster table above used to overstate them, so it is worth
being precise about what changed:

* `get_memory_service()` used to hardcode `agent_engine_id` to Shift's engine, so *every*
  agent's memories landed in Shift's store regardless of the `app_name` they were written
  under — the per-agent scopes in the roster table were aspirational. `services/memory.py` now
  resolves each agent to its own deployed engine through `_AGENT_ENGINE_SETTING`.
* Nothing ever *read* a memory. `write_fact` had two callers; `search()` had none, no agent
  declared a memory tool, and a repo-wide grep for `load_memory`/`preload_memory`/
  `memory_service=` came back empty. Facts accumulated every simulated day and were never
  recalled — which made the track's "context across weeks of asynchronous operations"
  requirement unmet in the one way that mattered. Shift now has `recall_unit_history` and
  Inventory has `recall_sku_history`, both `FunctionTool`s over `search()`, and both agents'
  instructions require calling them for any question about a trend or an earlier day.
  Verified live: an autonomously-triggered Shift turn answered with "sim_day 0 (Baseline): all
  staff members were in the 'safe' zone", i.e. it recalled and cited a fact from an earlier
  day rather than describing the current snapshot.
* `routes/sim.py` now writes Inventory facts per SKU as well as Shift facts per unit, and only
  for SKUs actually under pressure — writing every SKU every day would make a recall query
  return twenty near-identical "still fine" lines and bury the day that mattered.

**Medical Representative is still deliberately not wired to Memory Bank**, but the reason has
changed and is now a choice rather than a limitation. The old blocker (its writes would land
in Shift's store, inverting the trust boundary) is gone. It stays unwired because it is the one
agent whose input is adversarial by definition: giving a prompt-injection target a durable
write into any memory store is a liability with no demo payoff. `agents/medrep/agent.py`'s
docstring says the same.

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
blocked event in Firestore can be pivoted straight to its Cloud Trace detail.

**Pre-LLM Model Armor boundary (closed Aug 22, was an open gap since Aug 23):** the original
design only screened inside `screen_vendor_message`, a `FunctionTool` — the model had already
read the raw message into its own context to build that tool call before Model Armor ever saw
it, so "blocked before reaching LLM context" wasn't literally true. Fixed with
`_pre_llm_vendor_screen`, an ADK `before_model_callback` on `medical_representative_agent`
(`agents/medrep/agent.py`) — ADK runs this before the underlying Gemini call for every turn, and
returning an `LlmResponse` from it skips that model call entirely, so a blocked message never
reaches the model at all. Verified live against the deployed engine: a raw poisoned message
produces a single event (blocked, no tool call ever made); a clean message proceeds normally
and `screen_vendor_message` still runs as a second, defense-in-depth layer. That second layer
turned out to matter in practice, not just in theory: verified live through the real
Coordinator → Supply Chain → A2A path (not a synthetic direct call), Supply Chain's own
instruction has it *paraphrase* an inbound report before delegating ("Verify if this is
anomalous... Message received: '&lt;quoted text&gt;'") — Model Armor's real classifier scored
that wrapped framing as clean, letting the pre-LLM layer pass it through, and it was
`screen_vendor_message`'s re-screen of the *isolated* quoted excerpt the model itself extracted
that caught it. Net result was still a correct block; see `agents/medrep/agent.py`'s docstring
for the full finding. First deploy of this fix reported exit 0 but was actually still stale
server-side (the "adk deploy... exit 0 doesn't mean working" pattern recurring) — caught by
testing live rather than trusting the CLI output, confirmed via `update_time` and a clean
redeploy.

**Cross-process trace linking over the A2A hop (closed Aug 22, was an open gap through the
Aug 29–30 dashboard build):** `opentelemetry-instrumentation-httpx` instruments Supply Chain's
outbound `RemoteA2aAgent` calls (`agents/supply/agent.py` — `HTTPXClientInstrumentor().
instrument()` at module import, after a warm-up span forces our Cloud-Trace-exporting
`TracerProvider` to become the process-global one, since instrumentors resolve their tracer
once at `instrument()` time, not lazily); `opentelemetry.instrumentation.asgi.
OpenTelemetryMiddleware` wraps the Cloud Run A2A mount (`app.py`, same warm-up-then-instrument
ordering).

First verification attempt (querying the deployed Coordinator → Supply Chain → A2A path and
checking the resulting trace_id) produced a trace containing every Medical Representative span
plus non-zero `parent_span_id`s pointing outside the trace — suggestive, but not conclusive on
its own (see below: Reasoning-Engine spans don't export at all right now, so "the parent isn't
in this trace" doesn't distinguish "propagated from a real caller" from "propagated from
somewhere whose spans never appear anyway"). **The actual proof is a local discriminating
test**, run directly against the same instrumented `medical_representative_agent`
(`RemoteA2aAgent`) object from a local process — where span export is independently confirmed
working (`supply.bootstrap_tracing` lands in Cloud Trace every time) — hitting the real, deployed
Cloud Run A2A endpoint: the resulting trace shows a real httpx client span (`POST`, id
`13547533483764031046`) that Cloud Run's own ASGI root span (`/a2a/medrep`) lists as its exact
`parent_span_id`, with the rest of the chain (`invoke_agent medical_representative_agent` →
`a2a.client.transports.jsonrpc.JsonRpcTransport.send_message` → the httpx `POST` span → Cloud
Run's `/a2a/medrep` → the a2a.server.* machinery → `medrep.pre_llm_screen` →
`armor.sanitize_user_prompt` → `execute_tool screen_vendor_message` → `medrep.screen_vendor_message`
→ a second `armor.sanitize_user_prompt`) all landing in one trace, correctly nested end to end.
That's unambiguous: `HTTPXClientInstrumentor` is instrumenting the right client, injecting a
real W3C `traceparent`, and `OpenTelemetryMiddleware` on the Cloud Run mount is extracting and
honoring it.

**Separate gap found while verifying the above, since closed (Aug 22):** Reasoning-Engine-hosted
spans (Coordinator, Supply Chain's own deployed engine, Medical Representative's *standalone*
engine — as opposed to the Cloud Run A2A mount, which the test above confirms exports correctly)
weren't reaching Cloud Trace at all, confirmed with a plain HR query that touches none of this
session's code, so it wasn't something introduced that day. IAM checked out
(`coordinator-agent-sa` and the Reasoning Engine's shared service agent both hold
`roles/cloudtrace.agent`); `SimpleSpanProcessor` swallows exporter failures without surfacing
them, which is exactly why this went unnoticed while tool calls kept working.

First hypothesis — that `vertexai/agent_engines/templates/adk.py`'s own telemetry setup calls
`_override_active_span_processor(...)` and wipes out our span processor — was wrong, and
disproven directly: that override only runs from inside
`_default_instrumentor_builder`, which returns `None` immediately when `enable_tracing` and
`enable_logging` are both falsy. The real cause is simpler — nothing was turning Agent Engine's
own telemetry pipeline on at all. `_tracing_enabled()`'s truth table requires an explicit
`enable_tracing=True`, wired through the `adk deploy agent_engine --otel_to_cloud` CLI flag (or
an env-var + adk-version combination); without it, Agent Engine's `AdkApp` serving template never
sets up tracing, our span processor included, so there was nothing to wipe out.

Confirmed by redeploying HR's Reasoning Engine with `--otel_to_cloud` and querying it twice: the
resulting Cloud Trace traces contain real Agent-Engine-native spans (`invoke_workflow hr_agent`,
`invoke_agent hr_agent`, `call_llm`, `generate_content gemini-3.5-flash`, `execute_tool
get_credential_compliance`) *and* our own custom spans
(`hr.notify_staff_credential_escalation`, `approvals.perform_or_request`, `email.send`) correctly
nested inside the same trace — proving the flag doesn't just enable Agent Engine's own spans, it
coexists cleanly with `observability_vertex.py`'s custom instrumentation rather than overriding
it. Cloud Run never runs this template code at all (it's a plain FastAPI app, not an
`AdkApp`-served Reasoning Engine), which is consistent with Cloud Run having exported fine the
whole time while every Reasoning Engine didn't. Rolled out to every Reasoning Engine (Aug 22,
same session) and confirmed live: driving the real demo path (Coordinator → Gateway → Supply
Chain → genuine A2A → Cloud Run → MedRep's pre-LLM screen, real prompt-injection payload) and
pulling the resulting `armor_events` doc's trace_id produced one 81-span trace containing
`gateway.before_tool_call` (`gateway.decision=allowed`) all the way down to
`armor.sanitize_user_prompt` (`armor.blocked=true`, `matched_filters=pi_and_jailbreak`) —
Cloud Trace pivoting from an `armor_events` record now genuinely shows the *full*
Coordinator-to-MedRep waterfall in one trace, not stitched together after the fact.

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

**Coordinator's deploy command is different — it needs every specialist folder staged too,
not just `services`/`config.py`** (found the hard way, Aug 22: deploying Coordinator with only
the generic form above produces a clean `exit 0` and a real `stream_query` response — because
Agent Engine served a stale warm sandbox from the *previous* deploy for a few calls — then
fails outright on the next cold start with `ModuleNotFoundError: No module named 'chaos'`,
`stream_query` finally surfacing the error instead of silently truncating the event stream
this time). Coordinator's `agent.py` imports `chaos.agent`, `hr.agent`, `inventory.agent`,
`shift.agent`, `supply.agent` as flattened top-level modules (see that file's own docstring),
so its real deploy command is:

```
adk deploy agent_engine agents/coordinator \
  --project=prudently-hackathon --region=us-central1 \
  --agent_engine_id=<id-to-update-in-place> \
  --display_name="coordinator" \
  --extra_packages=services --extra_packages=config.py \
  --extra_packages=agents/chaos --extra_packages=agents/hr \
  --extra_packages=agents/inventory --extra_packages=agents/shift \
  --extra_packages=agents/supply
```

Confirmed live: the incomplete command deploys "successfully" (the stale-sandbox window makes
`exit 0` doubly untrustworthy here — even a live smoke-test call can pass on old code before
the real breakage shows up), so treat a Coordinator redeploy as unverified until a *fresh*
`stream_query` call against it round-trips cleanly, not just the first one after deploying.

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

## Simulation clock (removed Aug 23 — see "De-simulation" near the end of this file)

Historical record of the original design, kept for context rather than as current behavior:
`SIM_SEED` and `SIM_SPEEDUP` env vars controlled the synthetic flu-surge timeline
(`apps/api/services/simclock.py`). At each simulated-day boundary, `routes/sim.py` computed
current burndown and wrote a Memory Bank fact per unit via `services/memory.write_fact` — this
is what gave agents a narrative timeline to reason over across "weeks" compressed into a demo.
Reset via `POST /sim/reset` before reshooting the demo video for a deterministic replay.

**None of the file paths or endpoints in this section exist any more.** `services/simclock.py`
and `routes/sim.py` are deleted; the fleet watch now runs on real wall-clock time via
`services/fleet_watch.py` + `services/watch_loop.py`, exposed at `routes/watch.py`
(`GET /watch/status`, `POST /watch/check-now`, `POST /watch/reset`). `SIM_SEED` survives as
`sim_seed`, now purely an RNG seed for `packages/datagen` and the ongoing consumption-noise
generator; `SIM_SPEEDUP`/`timeline_days` are gone. See the "De-simulation" section for the full
story of what replaced this and why.

## Dashboard (apps/web)

**Was a single scrolling page through Aug 22 morning; rebuilt into a multi-route app with a
persistent sidebar the same day** — see "Multi-page enterprise UI" below for the full design
and the four real bugs found building it. `/` (the fleet overview) still polls
`GET /dashboard/overview` (new, `apps/api/routes/dashboard.py`) every 4s via
SWR (`src/lib/api/dashboard.ts`) rather than a Firestore realtime listener — the API is the
only place with Firestore credentials, and polling means the demo operator controls exactly
what the page shows when a listener firing mid-narration would not. The endpoint itself is a
thin aggregator, not a second implementation: it reuses every specialist's already-tested
pure-logic module (`burndown`, `par_levels`, `reorder`, `credentialing`) over live Firestore
state, plus `services/state.py` accessors for `agent_registry`, `armor_events`, and
`chaos_experiments` (newest-first).

Custom Tailwind v4 (CSS-first `@theme` in `globals.css`, no JS config file) over MUI (still a
dependency, just not used for the hero surfaces — MUI defaults read as generic) +
framer-motion for animation + `next/font/google` (Space Grotesk, Inter) self-hosted at build
time. The fleet overview (`src/components/workspace/FleetOverview.tsx`) renders all 7
`agent_registry` entries as hero cards — Coordinator prominent, the four Gateway-routed
specialists plus Chaos in a row, and Medical Representative rendered visually distinct below
its own divider (dashed border, A2A badge), since it's reached by genuine Agent2Agent, not the
Gateway — the panel would otherwise imply a hub-and-spoke topology the real architecture
doesn't have.

**Two deploy-time gotchas found live, both the same shape as earlier ones this session —
verify, don't assume, after any frontend change:**
1. `framer-motion`'s `whileInView` scroll-triggered entrance animation silently never fires
   for below-the-fold content in some capture/render paths — `Panel.tsx` uses mount-triggered
   `animate` instead, deliberately, not `whileInView`.
2. `NEXT_PUBLIC_API_BASE_URL` is inlined into the client bundle at `next build` time, not read
   at container runtime. Terraform's `cloud_run_web` module sets it as a Cloud Run runtime
   `env{}` block — correct for a server-read var, inert for a `NEXT_PUBLIC_*` one, since
   `gcloud run deploy --source`'s Cloud Build never sees it. Fixed with a Dockerfile `ARG`
   default (`apps/web/Dockerfile`) pointing at the known-stable deployed API URL — `gcloud run
   deploy --source` has no `--build-arg` flag for Dockerfile builds, so build-tooling plumbing
   wasn't an option. The Terraform env var is left in place but documented as inert.

No visual browser-automation tool was available in this environment session — verified
visually via a throwaway headless-Chromium (`playwright`) screenshot script instead of
skipping visual verification. Both `prudently-api` and `prudently-web` are deployed and
verified live end-to-end (zero console errors, real fleet data) against their actual Cloud Run
URLs, not just `npm run build` exiting 0.

## Manager approval workflow + auth (Gmail, Firebase)

Added after the fleet build was already complete and deployed. The user's original ask was
much larger (Gmail integration "for all agents", a full enterprise command-center with
payroll/attendance/admissions pages, real auth) — scoped down deliberately after a direct
conversation about the Aug 31 deadline: **agentic story first** (email approval-before-action +
manager-configurable policy, for actions that already exist), the four new enterprise CRUD
domains explicitly skipped (this track is judged on agent behavior, not CRUD breadth), auth
added with a judge-accessible path.

**Which agents, and why not all 7:** Supply Chain (`contact_vendor_for_reorder`), HR
(`notify_staff_credential_escalation`), Shift (`notify_staff_reallocation`), Medical
Representative (`send_vendor_reply`, only after `screen_vendor_message` returns `accepted`).
Inventory and Chaos deliberately excluded — Inventory has no natural outbound contact (internal
stock computation only), and Chaos's fault-injection tools simulate faults against the fleet
itself and never take real consequential actions; giving it a real-email tool would blur a line
this codebase has deliberately kept sharp (see `agents/chaos/agent.py`'s own docstring).
Coordinator gets no new tool of its own — delegation to the four specialists above covers it —
but its instruction now has one sentence about relaying a `pending_approval` status honestly
rather than claiming an action already happened.

**Gmail: SMTP + app password, not OAuth/the Gmail API.** Originally designed as OAuth (a
personal gmail.com account, no Workspace domain, so no domain-wide delegation), then switched
after weighing it directly: an app password needs no consent-screen configuration, no client
ID, and no refresh-token "Testing vs. In production" expiry trap (a Testing-status OAuth client
issues tokens that expire in ~7 days — with judging happening after Aug 31, a token minted
early in the build could be dead by judging day). It also needs zero new pip dependency —
`smtplib`/`email.mime.text` are stdlib, so `google-api-python-client`/`google-auth` never
entered the dependency-table risk that bit this project twice already (Aug 27's
`requirements.txt`-vs-`pyproject.toml` gap). Setup (manual, one-time, requires 2-Step
Verification already on for the sending account): generate an app password at
`myaccount.google.com/apppasswords`, then `gcloud secrets create prudently-gmail-app-password`
(value provided interactively, never through chat/history — see the git log for how this was
actually done). `sanjayipscoc@gmail.com` is both the sender and the default `manager_email` —
deliberate, not an oversight (reads well on camera: "the manager checks their inbox and clicks
approve"). Every subject line is prefixed `[Prudently] ` (`email.py`'s `SUBJECT_TAG`) so the
account owner can set up one Gmail filter (Subject contains `[Prudently]` → apply a label) to
keep agent mail visually separated — a personal Gmail label is not access-restricted, so this
is organizational only, not a security boundary.

**Day 1 de-risking, before any other code was written:** a throwaway probe agent
(`agents/probe_email`, deployed then deleted — same "verify live with a disposable deploy
first" precedent as Coordinator's own build) sent one real email from inside an actual
Reasoning Engine sandbox, confirming the Secret Manager IAM grant and outbound SMTP egress both
work under the Reasoning Engine service agent's real runtime identity, not just under a local
dev ADC identity. Caught nothing broken, but this was the single biggest unknown in the whole
feature and was verified before `services/platform/email.py` was written on top of the
assumption.

**Approval design — why GET renders, POST mutates.** `services/platform/gateway.py`'s
`before_tool_call` is fully synchronous with no pending/wait/queue mechanism anywhere in this
codebase, and is wired only on Coordinator — so an approval-gated tool call can't pause
mid-turn. `services/platform/approvals.py`'s `perform_or_request` (called directly from inside
each new tool's body, mirroring `agents/chaos/agent.py`'s existing direct-call-to-platform-
services pattern, not `before_tool_callback`) either sends immediately or writes a pending
`approvals/{token}` Firestore doc (`token = secrets.token_urlsafe(24)` used as the doc ID — a
bearer capability, no signing library needed) and emails the approver two links. Those links
are a `GET` that only *renders* a confirm page — the actual mutation happens on the button's
`POST` (`routes/approvals.py`) — because mail clients and security scanners prefetch links for
safe-link scanning, and a plain mutating `GET` could fire before a human ever clicks it. This
was verified for real (Day 1 of this feature): a live approval-shaped link was sent and the
Firestore record confirmed still `pending` immediately after, before any click.

**`recipient_label` vs. `to`:** neither `staff_roster` nor `vendors` carries a real contact
email in this dataset (confirmed by reading the datagen schema directly), and fabricating one
risks emailing an address nobody controls. Every approval-gated send therefore routes `to` the
operations mailbox (`manager_email`) regardless of who the "real" recipient conceptually is,
but carries a separate `recipient_label` (e.g. `"MedSupply Primary"`, `"Tech ER-00 (ER)"`) that
the Firestore record, the confirm page, and the pending-approval message all show instead — so
the demo reads as "contacting the vendor," not "contacting the ops mailbox," while the actual
send target stays safe. `check_policy()` fails closed: a task type with no `approval_policy`
doc requires approval, so an unconfigured task never silently auto-sends.

**Auth: Firebase Authentication (Email/Password), one demo/judge account, inline gating — no
new route.** `RequireAuth` swaps what `page.tsx`'s single route renders (a login form vs. the
dashboard) rather than adding a `/login` page, deliberately preserving the "scroll position is
the navigation" design philosophy from the Dashboard section above instead of contradicting it
on the very next feature. `/dashboard/overview` and `/approvals/*` stay unauthenticated (judges
need the URL reachable without the user present; the approval links must be clickable from a
phone with no dashboard login; the feed has never carried real PII) — only `/policy/*`
(manager-facing config writes) is gated, via `services/auth.py`'s `require_firebase_auth`
FastAPI dependency. `firebase_admin.initialize_app()` is called with an **explicit**
`projectId` (not inferred from the environment) — the same numeric-project-number-injection
bug that has already cost two incidents this build (see `services/state.py`'s
`FIRESTORE_PROJECT_ID` docstring) would otherwise silently verify tokens against the wrong
audience. The Firebase project itself (attached to `prudently-hackathon`, Email/Password
provider enabled, one demo account created) is a manual, one-time step done via the Firebase
Console — not scriptable from here, same treatment as the Model Armor template and the Gemini
secret. Demo/judge credentials: `manager@prudently.app` / see the submission text or ask the
repo owner — deliberately not written in plaintext into a committed file.

**Fallback, written down but not built (auth worked on the first pass):** a single shared
password → server-set signed cookie checked by a small FastAPI dependency, no new GCP product,
no `firebase-admin`, no new npm package — the plan for if Firebase Auth hadn't been working
end-to-end by roughly day 6 of the 9-day window.

**Dependency table** (the actual failure-prone part, per the `requirements.txt`-vs-
`pyproject.toml` asymmetry documented above): `opentelemetry-sdk` +
`opentelemetry-exporter-gcp-trace` added to `agents/supply`, `agents/hr`, `agents/shift`'s
`requirements.txt` (they didn't have it — their new tools call `get_observability_service()`
for the first time); `firebase-admin` added to `apps/api/pyproject.toml` **only**, never to any
agent's `requirements.txt` (never imported by agent code, dead weight in a sandbox).
`google-auth-oauthlib`/`google-api-python-client` were never added anywhere — the OAuth design
was abandoned before either was needed.

**Deploy order, same discipline as every prior milestone:** Supply, HR, Shift, MedRep
redeployed and individually smoke-tested standalone via `stream_query` first, Coordinator last
(`--extra_packages=agents/shift --extra_packages=agents/inventory --extra_packages=agents/
supply --extra_packages=agents/hr --extra_packages=agents/chaos`), to avoid the stale-bundled-
copy bug that has already hit this project twice. `EMAIL_BACKEND` stayed `local` (no-op) through
the entire backend-build phase, flipped to `gmail` only after the whole redeploy wave, which
meant a *second* full redeploy wave (config.py changes propagate the same way any other code
change does — confirmed, not assumed). Two more transient `Connection reset by peer` failures
hit during this second wave (same class as documented elsewhere in this file) — both resolved
by checking live `update_time` on the Reasoning Engine before retrying, not by blindly retrying
into a race.

**Live end-to-end verification, not exit-code-0:** a real `contact_vendor_for_reorder` call
created a real pending `approvals` doc, a real email arrived (subject `[Prudently] Approval
needed: ...`), clicking through the confirm page and hitting Approve flipped Firestore to
`approved` and sent a real second email — all confirmed by reading the actual Firestore
documents afterward, not by trusting the click. Test records deleted afterward so the
dashboard's Approvals feed starts empty for the real demo, same "delete probe/test data before
demo day" discipline as the Model Armor and Chaos milestones.

**Known gap:** the four new tools were verified directly (calling the Python function against
real Firestore/Secret Manager/SMTP) rather than exclusively through natural LLM conversation,
because the current simulated dataset has no low-stock SKU or at-risk staff member to trigger
one organically without the model correctly refusing a fabricated scenario (a good sign, not a
bug — see the guardrail behavior in Supply Chain's own instruction text). Re-verify once the
sim clock has advanced into a real surge.

**Known gap:** the policy editor's `requires_approval`, `approver_email`, and `notify_emails`
fields are all manager-editable from the dashboard (PUT verified live end-to-end: unchecked
"Requires manager approval" on `contact_vendor_for_reorder`, saved, confirmed `False` in the
actual Firestore doc, then restored to the demo default `True`). `notify_on_complete` is stored
per-policy and read on every save, but has no UI control yet — it always round-trips unchanged.
The "whom should be notified" half of the requirement is covered by `notify_emails`; toggling
*whether* to notify on completion is the piece left for a future pass.

## Data-layer bug fix: shift_history doc-ID collision (Aug 22)

Found as a side effect of building the payroll feature below, not something introduced by it.
`packages/datagen/datagen/seed.py`'s `write_firestore` keyed every Firestore doc by
`record.get("staff_id")`. That's correct for `staff_roster`/`inventory`/`vendors` (one doc per
entity), but `shift_history` has one row per staff member *per day* — keying it by staff_id
alone meant every day's `batch.set()` for the same person overwrote the previous one. Confirmed
live: 24 non-per-diem staff produced exactly 24 `shift_history` docs, not the ~600+ a 28-day
trailing history should contain — each holding only the single most-recently-written day.

This silently degraded `agents/shift/burndown.py`'s trailing-hours calculation, the Shift
Allocation Agent's core value proposition and demo beat 3 (`docs/build-plan.md` §6): with one
~8-hour shift on record per person instead of a real trailing accumulation, every burndown
ratio was trivially low, and the fleet's flagship fatigue-risk signal had likely never been
able to surface anyone as genuinely elevated or critical in the deployed system.

Fixed in `seed.py`: a `_doc_id_for` helper now keys `shift_history` by `f"{staff_id}__
{shift_date}"`, and `write_firestore` chunks batches at 450 (Firestore's hard cap is 500
writes/commit — `shift_history` alone now writes ~600+ records, which the old unchunked
single-batch code would also have silently failed on once the ID collision was fixed).
`packages/datagen/pyproject.toml` gained its own `[tool.black]` block (line-length 100,
matching `apps/api`) — it had none, so the first reformat here silently used black's 88-char
default instead of this project's convention.

The live Firestore data was already seeded and demo-relevant (HR's flagged-credential set,
specific burndown numbers), so this was **not** repaired by rerunning the full `make seed` —
`generate_roster`/`generate_admissions` default to `today=date.today()`, and a full reseed
would re-anchor every credential_expiry and admissions calendar_date to today's date, silently
changing which staff are flagged for no reason. Instead, `packages/datagen/datagen/
resync_shift_history.py` (new, one-off, reusable) regenerates only the `shifts` half of
`generate_roster`'s output and replaces `shift_history` alone — deletes the 24 stale docs,
writes the corrected ~600+. Verified live by calling `compute_burndown` directly against the
repaired data: real, varied risk levels (`ic-01` `Nurse IC-01` 60.0 trailing hours, `critical`)
replaced the previous near-uniform low-hours result across the whole roster.

## Enterprise command center: admissions, guest-doctor hours, payroll (Aug 22)

The user's original ask included a full enterprise command-center (payroll, attendance,
admissions/discharge, guest-doctor time tracking, supplies inventory) — deferred on Aug 22 to
ship the agentic story first (see the Manager approval workflow section above). Asked to
proceed on the deferred scope; scoped down again after a data-model audit (admissions_
timeseries exists but was completely unused — no accessor, no agent, not on the dashboard; HR
already tracks `is_per_diem` and per-shift hours but nothing called "guest doctor"; no
case-level patient/doctor-assignment concept exists anywhere) to **admissions/discharge** (read-
only, over the already-seeded `admissions_timeseries`) + **guest-doctor/per-diem hours** (read-
only) + **payroll** (real CRUD, per explicit request to include it despite the cost/agentic-
payoff trade-off being flagged directly). Supplies inventory was already fully built (Inventory
Management Agent + dashboard panel) — nothing to add. True case-level admission/discharge
tracking with doctor assignment stayed out of scope: it would mean inventing a whole new
patient/case data model from scratch, which an operations platform (not an EHR) doesn't need.

**New data**, generated by `generate_roster` (own rng streams, `seed+3`/`seed+4`, additive —
same discipline as `_assign_credential_expiry`/`_generate_perdiem_pool`, never perturbs the
shift-history random draws): `hourly_rate` on every `StaffMember` (role-based
`HOURLY_RATE_BASE`, +-10% spread — physician > pharmacist > nurse > tech, not sourced from real
wage data); sparse (`GUEST_SHIFT_PROBABILITY = 0.18`) coverage shifts for the per-diem pool,
who otherwise carry zero `shift_history` by design. Backfilled onto the already-seeded live
Firestore via `packages/datagen/datagen/backfill_payroll_data.py` (new, one-off) — additive
only: `.update({"hourly_rate": ...})` per `staff_roster` doc (never touches `credential_expiry`
or any other field), `.set()` for brand-new per-diem `shift_history` docs (never touches a
regular staff member's just-repaired history). Same "don't run a full reseed" reasoning as the
bug fix above.

**Backend**: `services/admissions.py` (pure aggregation: `unit_totals`, `recent_daily_trend`) and
`services/payroll.py` (pure: `hours_worked_in_period`, `compute_gross_pay`) follow this
project's `agents/*/*.py` pure-logic-module convention — no I/O, independently unit-tested,
added to `pyproject.toml`'s coverage `source` list. `guest_doctor_hours_summary` lives in
`agents/hr/credentialing.py` alongside the other per-diem logic it's a sibling of, same
trailing-window math as `compute_burndown`. All three build explicit output dicts only — never
a raw roster/shift passthrough — since `hourly_rate` must never leak onto the public
`/dashboard/overview` feed (checked all three existing consumers of `get_staff_roster()` for a
`**member` spread before adding the field at all: none exist). `admissions` and
`guest_doctor_hours` are safe to add to the public overview (no PII/financial data); payroll is
not — `routes/payroll.py` is a new router, every endpoint `Depends(require_firebase_auth)`,
confirmed with unauthenticated `curl` against all four routes both locally and against the
deployed Cloud Run URL (401 on every one). Gross pay is always computed server-side from the
roster's own `hourly_rate` and `shift_history`, never taken from the request body — a client
can't set an arbitrary rate or amount. `mark-paid` is idempotent, same "already decided" shape
as `approvals.py`'s `resolve_approval`.

**No agent or Reasoning Engine touches any of this** — first milestone this build where
verification is Cloud-Run-only, no `adk deploy`, no Coordinator-last redeploy ordering, no
stale-bundle risk.

**Real bug caught during verification, fixed before shipping:** `GET /payroll/records`
(`services/state.py`'s `get_payroll_records`) returned Firestore docs via `doc.to_dict()`,
which never includes the doc's own ID. The frontend's `PayrollPanel.tsx` used `record.id` as
its list `key` and to address the mark-paid endpoint — every record's key was `undefined`,
surfaced as a real React "missing key" console warning caught live via Playwright, not
something guessed at from reading the code. Fixed by having `get_payroll_records`/
`get_payroll_record` always embed `{**doc.to_dict(), "id": doc.id}`, centralizing it in
`state.py` rather than each route stitching it in separately.

**Verified live, not exit-code-0:** full create → list → mark-paid cycle exercised via
Playwright against both localhost and the deployed production URL — real staff picker
populated from `GET /payroll/staff`, a created record's `gross_pay` independently confirmed
against `hours_worked x hourly_rate` by reading the actual Firestore document (e.g. 116h @
$47.89/hr = $5555.24, exact), mark-paid transitions `status` to `paid` with a real `paid_at`
timestamp, all with zero console errors. Test records deleted from both local and production
Firestore afterward. 97/97 unit tests passing (81 prior + 16 new), lint 10.00/10 on both apps.

## Multi-page enterprise UI + real activity log + Cloud Trace/Logging in the UI (Aug 22)

The single scrolling page (see the Dashboard section above) became a persistent-sidebar,
multi-route app the same day, at the user's explicit request — clicking an agent's card now
opens `/agents/[agentName]`, showing that agent's activities, approvals, pending
responsibilities, and permissions (the policy editor, moved off the old single page onto each
agent's own detail page) in one place. Two more explicit choices, both overriding a smaller
recommendation: a *real* new `activity_log` collection rather than reusing existing feeds, and
genuine Cloud Trace/Logging data surfaced in the UI rather than left as an outbound link.

**`activity_log` — narrow by design.** Written from exactly 5 call sites:
`services/platform/approvals.py`'s `perform_or_request`/`resolve_approval` (covers every
approval-gated tool across Shift/Supply/HR/MedRep), `gateway_local.py`'s `before_tool_call`
(every Coordinator routing decision — Coordinator has no tool functions of its own, so this is
its *only* form of activity), `medrep/agent.py`'s `screen_vendor_message`/
`_pre_llm_vendor_screen`, and `chaos/agent.py`'s `_persist` (covers all 4 chaos tools, one call
site). Deliberately does **not** log the 5 read-only "recommendation" tools every specialist
has (`get_shift_burndown`, par-levels, reorder recommendations, credential compliance,
per-diem coverage) — the LLM calls these on nearly every turn regardless of what the user
actually asked, and logging them would drown the feed in query telemetry rather than the
"activities performed, approvals provided" the request asked for. Each agent's live computed
state is already shown in its own "current responsibilities" panel, sourced from
`/dashboard/overview`'s existing per-agent slices, not from this log.

**`GET /agents/{agent_name}`** (`routes/agents.py`, public — same rationale as
`/dashboard/overview`) reuses `routes/dashboard.py`'s `build_overview()` rather than
re-deriving the same Firestore reads, and reuses its `project_approval()` helper (factored out
during this pass) so the manager's real email and full request/email bodies can't leak here
either — the first draft of this route returned raw `get_approvals()` docs before that
factoring, caught by re-reading `app.py`'s own comment about why the public overview projects
its approvals list down, not by any runtime failure. `_AGENT_TASK_TYPE`/
`_AGENT_LIVE_STATE_KEYS` are hardcoded maps, same rationale as the frontend's own
`TASK_LABEL` and `gateway_local.py`'s `_POLICY_TABLE` — the agent set is small and fixed.

**`routes/traces.py`** — `GET /traces/{trace_id}` fetches one trace on demand (only when a
manager clicks a specific `activity_log` entry that carries a trace_id — never polled, matching
this project's existing "public feed, not a background listener" philosophy). `GET
/agents/{agent_name}/logs` filters Cloud Logging by `resource.labels.reasoning_engine_id`,
confirmed present on every `aiplatform.googleapis.com/ReasoningEngine` log entry via a direct
`gcloud logging read` before designing the filter around it, not assumed. Same caveat as
Coordinator's own logs generally: its engine bundles Shift/Inventory/Supply/HR/Chaos's
flattened logic (see "Running / deploying an agent" below), so log/trace entries for those
agents when reached *through* Coordinator are engine-scoped, not cleanly agent-scoped — labeled
as such in the UI rather than implying more precision than the infrastructure actually has.
`google-cloud-trace`/`google-cloud-logging` added as explicit `pyproject.toml` deps (were only
transitive via the OTel exporters before) — this code runs in `prudently-api`'s Cloud Run
container specifically, which reads `pyproject.toml` via its own Dockerfile, not any agent's
`requirements.txt`, so no deploy-staging risk here the way the Aug 27 `requirements.txt` gap
had.

**Frontend**: `src/app/(dashboard)/layout.tsx` wraps every page in `RequireAuth` + the new
persistent `Sidebar` (Fleet/Payroll/Admissions/Security & Resilience/Approvals). `AGENT_META`
(icons/labels/blurbs/accent colors) factored out of `FleetOverview.tsx` into
`src/lib/agentMeta.ts` so the sidebar and the agent detail page share one source of truth
instead of drifting. The agent detail page reuses the *existing* Shift/Inventory/Supply/HR/
Armor/Chaos/GuestDoctorHours panels against the new per-agent payload rather than duplicating
them — only genuinely new components were `ActivityFeed`, `TraceViewer` (a simple waterfall,
spans sorted by start time with a relative-offset bar, not a full parent/child tree — judged
enough for a demo dashboard), `AgentLogViewer`, and `AgentPolicyEditor` (a thin wrapper around
`PolicyEditor.tsx`'s existing `PolicyRow` + save logic, scoped to one `task_type`, exported for
reuse rather than copied). The top-level Approvals page keeps only the fleet-wide feed now —
the policy editor lives exclusively on each agent's own page, per the request.

**Full `--otel_to_cloud` rollout closed in this pass** (flagged as unfinished, HR-only, in the
Observability section above): every Reasoning Engine (Shift, Inventory, Supply, HR, Chaos,
MedRep standalone + Cloud Run, Coordinator) redeployed with the flag, each smoke-tested live
via `stream_query` before moving to the next, Coordinator last. Driving the real demo path
afterward (Coordinator → Gateway → Supply Chain → genuine A2A → Cloud Run → MedRep's pre-LLM
screen, real prompt-injection payload) and pulling the resulting trace via the new
`/traces/{id}` endpoint produced one 81-span trace: `invoke_workflow coordinator` →
`gateway.before_tool_call` (`gateway.decision=allowed`) → `invoke_workflow
supply_chain_resiliency_agent` → the real A2A hop (`POST /a2a/medrep`) → Cloud Run's ASGI
handling → `medrep.pre_llm_screen` → `armor.sanitize_user_prompt`
(`armor.blocked=true`, `matched_filters=pi_and_jailbreak`) — the full waterfall the demo script
wants to narrate is now demonstrated, not aspirational (see docs/build-plan.md §6).

**Four real bugs found and fixed getting here, each a different failure class:**

1. **Coordinator's deploy command was silently incomplete** — see "Running / deploying an
   agent via the ADK CLI" above for the full root-cause and the corrected command. Worth
   restating the shape of the bug here: `exit 0`, plus a *correct* `stream_query` answer on the
   first call, both looked like success — the container was still serving the previous deploy's
   warm sandbox. Only a cold-start call surfaced `ModuleNotFoundError: No module named
   'chaos'`. Root-caused with a temporary `print(..., file=sys.stderr)`, a redeploy, and reading
   the real traceback in Cloud Logging — not guessed at.
2. **A new write on the Gateway's hot path broke `test_gateway_local.py`'s deliberate
   hermeticity.** That test's own comment says it stays "hermetic for CI/clean-clone, no GCP
   credentials or network call needed" by monkeypatching Registry and Observability — it didn't
   know about the new `log_activity` call inside `before_tool_call` and started writing real
   test data (`ghost_agent`, synthetic caller/target pairs) into production Firestore on every
   `pytest` run. Same gap in `test_approvals.py`. Fixed by monkeypatching `log_activity` to a
   no-op in both files; the 24 test-probe docs already written before the fix were found (by
   pattern-matching the synthetic agent/task names) and deleted from the real collection.
3. **A permission-denied 500 looked exactly like a CORS bug.** The browser console showed
   "blocked by CORS policy: No 'Access-Control-Allow-Origin' header" for `/agents/{name}/logs`
   and (transiently) `/traces/{id}`, even though `app.py`'s CORS middleware allows `*`
   globally — FastAPI/Starlette's CORS middleware only attaches headers to responses that
   complete normally through the stack, so an unhandled exception's response never gets them,
   and the browser reports it as a CORS failure. Reading Cloud Run's own logs directly (not the
   browser) showed the real error: `google.api_core.exceptions.PermissionDenied`.
   `coordinator-agent-sa` — `prudently-api`'s Cloud Run runtime identity, confirmed via `gcloud
   run services describe` to be a *different* identity from the Reasoning Engines' shared
   `service-<project-number>@gcp-sa-aiplatform-re.iam.gserviceaccount.com` — had
   `roles/cloudtrace.agent` (write spans, granted for the Observability work) but not
   `roles/cloudtrace.user` (read traces) or `roles/logging.viewer` (read logs). Granted live,
   verified against real trace/log data returned with `200`, then backfilled into
   `infra/terraform/modules/iam/main.tf` so a future `terraform apply` doesn't silently revert
   the live grant.
4. **The new public agent-detail route almost leaked what the public overview deliberately
   doesn't.** First draft of `routes/agents.py` returned raw `get_approvals()` docs — including
   the manager's real email and full request/email bodies — before `project_approval()` was
   factored out of `routes/dashboard.py` and reused. Caught by re-reading `app.py`'s own CORS
   comment (which explains *why* the public overview's approvals list is projected down) before
   shipping, not by a scanner or a runtime failure.

**Verified live, not exit-code-0, at every layer:** 97/97 unit tests, lint 10.00/10 on every
changed file; the full 7-engine + Cloud Run redeploy wave smoke-tested one at a time; the
multi-page frontend clicked through end-to-end via Playwright both on `localhost` and against
the deployed `prudently-web`/`prudently-api` Cloud Run URLs — sidebar nav, all four section
pages, an agent detail page's activity feed → trace modal → Cloud Logging viewer, zero console
errors on either environment. The CORS-shaped IAM bug above was caught by this production
Playwright pass specifically, not by local testing (the local dev API runs under the
operator's own `gcloud` credentials, which already have every role) — a reminder that
"verified locally" and "verified in the deployed identity's own permissions" are genuinely
different checks for anything IAM-gated.

## Autonomous fleet watch (Aug 23) — the fleet acts without being asked

Until this, every agent action in Prudently began with a human typing a question. The sim clock
advanced stock and staffing, the dashboard rendered the consequences, and the agents sat idle
until asked — which made "agent-monitored hospital operations" a description of the UI, not of
the fleet. Two modules close that:

- **`services/triggers.py`** — pure, fully unit-tested. Turns a state snapshot plus the previous
  snapshot into a list of `Trigger`s. Everything is **edge-triggered, never level-triggered**: a
  SKU that is still low today because it was low yesterday is not a new event. Without that, a
  21-day demo would email the manager about the same box of gloves 21 times. `next_watch_state`
  produces the snapshot the next tick compares against, and the round-trip property (feed a
  tick's own output back in, get zero triggers) is asserted in `test_triggers.py`.
- **`services/autonomy.py`** — impure. Opens a real ADK `Runner` over the responsible
  specialist and runs one genuine turn: real model call, real tool calls, real Gateway and
  approval paths.

**Why in-process rather than `stream_query` against the deployed engine.** Two reasons, one
principled and one measured. Principled: `apps/api` already *is* the fleet — it runs the same
agent objects the Reasoning Engines serve, so invoking them in-process is a real agent turn,
not a simulation of one. Measured: `stream_query` against a deployed engine reset mid-stream
(`httpx.ReadError: [Errno 54] Connection reset by peer`) on **3 of 4 attempts** from this
environment against a stable deploy. A demo beat that fails three times in four is not a demo
beat. The one thing the in-process path does not exercise is the Agent Engine transport itself,
which the manager-initiated path through the dashboard already covers.

**Autonomy stops at the approval gate.** A triggered agent reaches exactly the same
`perform_or_request` path a manager-initiated one does. Autonomy here means the fleet decides
*when to raise something*, never that it acquired permission to act unsupervised — so the blast
radius of a false trigger is one email. `log_activity` gained an `initiated_by` field
(`"autonomous_watch"` vs the default `"manager"`) so the dashboard can render the two
differently; conflating them would let the fleet take credit for acting unprompted when it
didn't.

**`POST /sim/advance` fires and returns rather than awaiting** — found the hard way. The first
version awaited the day boundary, and a boundary that trips three fatigue triggers runs three
real agent turns back to back: the request took **over two minutes** and the dashboard's "Next
day" button would have sat spinning through all of it. It now schedules the work exactly as the
clock's own tick does (8ms response), and the dashboard's polling fills the feed in as each turn
lands — which is also the better thing to watch on camera.

**`/sim/reset` clears `fleet_watch/state`.** Without that, a replayed demo is silent: every SKU
is already recorded at its breached status, so nothing reads as a *new* crossing. The demo would
only have worked once.

**Verified live** against real Firestore with `EMAIL_BACKEND=local`: one `/sim/advance` fired
three fatigue triggers, ran three completed agent turns at 3 tool calls each, and the responses
show the agents recalling earlier days from Memory Bank by name ("sim_day 0 (Baseline): all
staff members were in the 'safe' zone", "Day 1 History: the General Ward already had 2 staff
members at critical risk").

## Public-feed redaction (Aug 23)

`/dashboard/overview` and `/agents/{name}` are public by design — a judge needs them to work
without a login. But they were returning `shift.records[]` (32 named staff with unit, trailing
hours, and fatigue risk) and `hr.records[]` (named staff with credential expiry and an
"expired" status) to **anonymous callers**. The data is synthetic, so nothing real leaked; the
shape is an unauthenticated endpoint publishing per-employee fatigue and credentialing records,
which does not survive being pointed at a real roster.

This project had already reasoned about leakage at *field* granularity — `project_approval()`
keeps the manager's address off these same feeds, and every payroll projection was audited for
`hourly_rate`. `services/redaction.py` applies the same care at *endpoint* granularity.

**Redact, don't gate.** Hard-401ing these routes would have fixed the exposure and broken the
judge-accessible URL. Instead `services/auth.py` gained `optional_firebase_auth` (returns a uid
or None, never raises — an *invalid* token is treated as no token, so a viewer whose session
quietly expired sees the public view rather than a broken dashboard), and the anonymous payload
keeps every aggregate while dropping the individual rows. Shape is preserved: a redacted list is
an empty list plus a sibling `_redacted` block with the count and reason, so the dashboard
renders "sign in to see staff-level detail" instead of an ambiguous empty state.

**The frontend counterpart is load-bearing and easy to miss.** `lib/api/dashboard.ts` now
attaches the manager's Firebase ID token *and puts it in the SWR key*. Without the token a
signed-in manager silently gets the anonymous payload and every staff panel renders empty —
indistinguishable from a data outage. Without it in the key, SWR would serve one posture's
cached payload after a sign-in or sign-out.

## The coverage gate was hanging, not slow (Aug 23)

`make test` did not complete. Not "took a while" — it hung indefinitely, which read as slowness
and meant the project's own quality gate had silently stopped being a gate.

Root cause: `[tool.coverage.run] source` listed **importable module names**. Coverage re-imports
each named module at report time to account for files the run never touched, so naming
`agents.supply.reorder` dragged in `agents/supply/__init__.py` → `agent.py`, which constructs a
`RemoteA2aAgent` and installs the global httpx instrumentor — and under coverage's tracer that
import never returned. Bisected by running `--cov=<module>` one at a time: every other module
finished in ~3s, `agents.supply.reorder` hung every time. The plain import (no coverage) takes
3.7s, so the module itself is fine; it is the combination.

Fixed by switching to `include` with **path globs**, which filters by path and imports nothing.
Same scope in spirit — pure-logic modules only, ADK orchestration still excluded. `make test`
now runs in ~3.3s, and the gate covers 12 modules at 97% (the Gateway, triggers, and redaction
were added at the same time).

## Scenario evals (`make eval`)

`make eval` previously pointed at `python -m evals.run` with an **empty `evals/` directory** — a
committed Makefile target that crashed. `evals/run.py` now runs behavioural scenarios against
the real agents over real Firestore state.

They assert on **tool calls and load-bearing facts, never on phrasing**: did Shift call
`recall_unit_history` for a question explicitly about earlier days; did Inventory refuse to
claim it placed an order; did Supply Chain delegate a prompt-injection-laced vendor message to
Medical Representative over A2A instead of reading it itself. Deliberately not part of
`make test` — real model calls, real cost, non-deterministic wording. Run before a demo or a
deploy wave: `make eval`, or `make eval ARGS="--only shift"`.

## De-simulation + mission-control redesign (Aug 23)

Two problems for a grand-prize submission, both closed the same session: the fleet only ever
acted when a human pressed **Next day** on a scripted 21-day sim clock, and the UI was a
deliberately calm, light "ward board" — a prior session's own explicit rejection of a
"sci-fi dashboard" look (see the old `globals.css` header comment, now rewritten). Both
undercut the actual claim being judged: a fleet that manages a live hospital on its own.

**The sim clock is gone.** `services/simclock.py` and `routes/sim.py` are deleted. In their
place: `services/fleet_watch.py` (`run_watch_cycle()` — deplete a little inventory noise,
observe live state, write Memory Bank facts, detect + act on edge-triggered changes, all four
stages independently isolated the same way the old `_advance_day` was) and
`services/watch_loop.py` (a background asyncio loop, started from `app.py`'s lifespan the
moment the API process starts — no button, fully unprompted — that calls `run_watch_cycle()`
every `WATCH_INTERVAL_SECONDS`, default 90s). `routes/watch.py` replaces `routes/sim.py`:
`GET /watch/status`, `POST /watch/check-now` (fire-and-return, same reasoning as the old
`/sim/advance` — a multi-trigger cycle can run several real agent turns back to back), and
`POST /watch/reset` (an internal ops utility now, not a dashboard button). `sim_day` is gone
as a concept everywhere it was purely a label — `services/triggers.py`'s `Trigger.memory_fact`
and the persisted `fleet_watch/state`/`autonomous_actions`/`inventory_transactions` records use
real timestamps instead. This was a rename, not a redesign of the trigger logic itself:
`detect_all`'s edge-triggered state-diff never actually needed a day number, only something to
invoke it periodically with fresh state — confirmed by reading it before touching anything.

**A third trigger kind, and organic seed-time material for two of the three axes.**
`services/triggers.py` gained `credential_breach` (`detect_credential_triggers`, over the
already-existing `compute_credential_status`), targeting `hr_agent`'s existing
`notify_staff_credential_escalation` — HR was already autonomy-capable
(`services/autonomy.py`'s `_AGENT_MODULES`) but had no trigger kind that ever reached it before
this. Checked against the real seed generators rather than assumed: at plain seed time (no
watch cycle needed), ~22 of 24 staff are already at critical fatigue and several credentials
are already expired, so fatigue and credential triggers fire on the very first watch cycle with
zero manual interaction. Inventory was the one axis structurally always `ok` at seed time
(`days_on_hand` floor of 8 always exceeded the 5-day reorder point) — fixed by giving two SKUs
(`N95-001`, `O2-006`) a deliberately tight seed range in `packages/datagen/datagen/inventory.py`
so Supply Chain has genuine reorder material immediately too, without a scripted depletion
curve. `services/inventory_sim.py`'s consumption-noise function is still called, but now once
per real watch cycle (a monotonic counter persisted in `fleet_watch/state`) rather than once
per sim day, purely to keep a long-running demo showing continued movement.

**Visual redesign: dark mission-control over the previous light "ward board."** User-directed
pivot, confirmed explicitly given the prior session's own reasoning against it. `globals.css`
keeps every piece of the old design discipline that was actually about *legibility* (status
colour reserved for real triage meaning, `--color-autonomous` indigo/violet reserved
exclusively for fleet-initiated work, one decorative `--color-hero` accent) and just re-tunes
it for a glowing dark palette, plus new `--glow-*` shadow tokens live elements (the watch
strip's pulse, an active topology node) actually use. Light mode is preserved byte-for-byte as
the previous ward-board palette, now reachable via the existing light/dark/system
`ThemeToggle` rather than being the default. `BoardStrip.tsx` lost its Run/Pause/Next-day/Reset
toolbar entirely, replaced by a live "checked Ns ago / next check in Ns" reading (from
`GET /watch/status`) and one "Run fleet check now" button. `FleetOverview.tsx`'s topology
diagram — already the strongest "this is a fleet" visual in the app — moved from the bottom of
the homepage to the top and gained a signature touch: an animated highlight that continuously
travels along the rails between the Coordinator and its specialists (`--animate-rail-flow`),
so the diagram reads as live infrastructure rather than a static box-and-line drawing between
real tool calls. Unused `@mui/material`/`@emotion/*` dependencies (confirmed zero imports
anywhere in `src`) were removed.

**Verified:** full backend test suite (155 tests, 97% coverage on the pure-logic gate),
`pylint agents routes services` at 10.00/10, `black --check .` clean, a direct wiring check of
`compute_credential_status` → `detect_all` producing a real `credential_breach` trigger, and a
direct run of `generate_inventory(42)` confirming N95-001 seeds `critical` and O2-006 seeds
`low`. Frontend: `tsc --noEmit` clean, `eslint .` clean, `next build` clean, and both
light/dark themes screenshotted via a headless Playwright pass against the (unauthenticated)
login gate — full dashboard pages are behind real Firebase Auth in this environment with no
judge/demo credentials available, so the authenticated views were not visually verified this
session. **Known follow-up, not yet done:** per this file's own "Coordinator's sub-agents are
baked-in copies" discipline, `agents/shift/agent.py`, `agents/inventory/agent.py`,
`services/triggers.py`, and the fleet-watch path all changed — Shift, Inventory, Supply, HR
need redeploying (each smoke-tested live via `stream_query`), then Coordinator last with its
full `--extra_packages` set, before any of this is live in the deployed engines rather than
just local dev.

**A real bug, caught live in production within minutes of the first deploy — not in a test.**
`services/inventory_sim.py`'s ongoing consumption-noise generator applied a full day's worth of
depletion on *every* watch cycle instead of a scaled-down fraction of one. At the default 90s
interval, every SKU crashed to critical/zero stock within about five minutes of `prudently-api`
going live, and Supply Chain's real `contact_vendor_for_reorder` approval flow fired once per
SKU — **26 real approval-request emails landed in the manager's actual Gmail inbox** before it
was caught (`email_log`, cross-checked directly against Firestore, not assumed from the code).
The fix: scale the delta by `interval_seconds / REAL_SECONDS_PER_CONSUMPTION_DAY` (a 1-hour
"consumption day" pacing knob, not a sim-clock day) so ambient movement takes on the order of an
hour per SKU instead of one cycle. Verified by redeploying, clearing the flooded audit
collections (`demo_reset --deep --restock`), restoring the two deliberately-tight SKUs, and
forcing a clean `POST /watch/reset` + `POST /watch/check-now`: exactly 11 triggers fired — 4
units' fatigue, 5 expired credentials, 2 tight SKUs — matching the live data precisely, with
`triggers_fired_total` stable afterward (no further growth). The irony is on-brand for this
project: the fastest way to prove the fleet watch's edge-triggering logic was correct was to
watch it get raced by a real timing bug and then confirm the *next* clean run produced exactly
the right count, live, against real Firestore state — not a unit test with synthetic input.

## Real-PII-ready security hardening + HTML email + four new features (Aug 23-24)

User-directed: the logo/favicon weren't rendering, session management needed a real design, and
"this platform is meant for hospital data (PII)" — so it should be **architected for real PII
from day one**, with a real threat model and a fix for every finding, real HTML email instead of
plain text, and four new features (staff duty job sheets, facilities job sheets, purchase-order
documents, surgical scheduling + patient notifications) built together with the hardening rather
than after it, since the new features are exactly what the hardening has to hold up against.
**Resolving principle, stated explicitly because it's the one real tension in this brief:** the
*controls* are built to real-PII standards (field-level encryption, RBAC, consent-gated
notifications, audit logging) — the *data actually entered* stays fabricated test data, same
honest-synthetic discipline `packages/datagen` already uses everywhere else. Never real people.

**Threat model: `docs/threat-model.md`.** Ten STRIDE findings, each backed by a file:line
citation, not assumed — an unauthenticated A2A mount and unauthenticated mutating watch routes
(Spoofing/DoS), fully public `traces`/`inventory`/`vendors` routes and an `activity_log`
redaction gap that leaked staff names to anonymous callers, approval tokens with no expiry or
rate limit, no session revocation, no RBAC, unescaped HTML interpolation on the approvals
confirm page, wildcard CORS, the shared Reasoning Engine identity's blast radius, and no CI/
dependency scanning. Every finding maps to a specific fix below; the doc's closing table is the
actual remediation plan, not just a list of problems.

**Security remediation, one fix per finding.** `services/auth.py`: `verify_id_token(...,
check_revoked=True)` (revocation now actually checked, not just token-signature-valid), a
generic 401 detail instead of echoing verifier internals, `require_role(*roles)` built on
`require_firebase_auth` reading a `role` custom claim (`scripts/set_user_role.py`, a one-time
admin CLI), and `POST /auth/sign-out-everywhere` (`routes/auth.py`) calling
`firebase_auth.revoke_refresh_tokens(uid)` server-side — wired to a real "Sign out everywhere"
control in `Sidebar.tsx`, plus a 15-minute client-side idle timeout in `AuthContext.tsx`.
`app.py` gained a `SharedSecretASGIMiddleware` on the A2A mount (`X-A2A-Shared-Secret`, Secret
Manager-backed, fail-closed if the secret is unreachable — `agents/supply/agent.py`'s
`RemoteA2aAgent` sends it via an httpx event hook) and an explicit CORS origin allowlist
replacing `["*"]`. `routes/watch.py`'s mutating routes, `routes/traces.py`, and the GET routes
on `routes/inventory.py`/`routes/vendors.py` moved onto `require_firebase_auth`.
`services/redaction.py`'s `redact_agent_detail` now also strips `activity_log[].summary` for
anonymous callers. `routes/approvals.py`'s confirm page runs every interpolated value through
`html.escape()`. `services/platform/approvals.py` gained a 14-day `expires_at` on every
approval, checked before a token can resolve. `services/platform/rate_limit.py` (new) wraps
`slowapi`, applied to every public POST — **two real bugs found live, not in review**: slowapi's
default `key_func=get_remote_address` reads `request.client.host`, which behind Cloud Run's load
balancer is the LB's own connection peer rather than a stable per-client key (fixed with a
custom `_real_client_ip` reading `X-Forwarded-For`'s first hop), and slowapi's default
`key_style="url"` folds the literal request path — including an interpolated `{token}` path
segment — into the bucket key, so a burst using a *different* candidate token per request (the
realistic brute-force case) never rate-limited even with a stable IP key (fixed with
`key_style="endpoint"`). Both were isolated by hitting the *same* path repeatedly first (which
did rate-limit correctly, proving the decorator/middleware wiring was never the problem) before
tracing the discrepancy to path-keying specifically. `.github/workflows/ci.yml` (lint + test on
PR) and `.github/dependabot.yml` (npm + pip, weekly) are new — this repo had neither before.
`services/platform/access_control.py` (new) is this project's honestly-framed answer to the one
finding with no platform-level fix available: Agent Engine has no per-agent `--service_account`,
so every deployed agent shares one Reasoning Engine identity with a project-wide
`roles/datastore.user` grant. `require_access(caller)` checks a self-declared caller identity
against an explicit allowlist (`surgical_scheduling_agent`, `dashboard_route`, `fleet_watch`)
before any `patients`/`surgical_cases` accessor in `services/state.py` proceeds — its own
docstring is explicit that this is a real, useful catch against *accidental* cross-agent access
(a function added to the wrong agent module) and not cryptographic enforcement against a
genuinely malicious caller, which no application-layer check can be on this platform.

**HTML email: `services/platform/email_templates.py` (new).** One dark-branded shell (inlined
base64 logo, matching the dashboard's mission-control palette) plus five render functions —
`approval_request`, `action_sent`, `purchase_order`, `job_sheet`, `patient_notification` — each
returning `(plain_text, html)`. `email_gmail.py` now builds a real `MIMEMultipart("alternative")`
carrying both parts; every `EmailService.send()` call site across `services/platform/
approvals.py`, the new job-sheets route, and the supply/surgical-scheduling agents passes
through a template function instead of a raw f-string. `routes/approvals.py`'s confirm page gets
the same shell. **Caught by an actual Playwright screenshot pass, not code review:** the Reject
button's unfilled/outline style rendered with no visible border at all — invisible, not just
plain — fixed by giving `_button(..., filled: bool)` an explicit outlined style for the unfilled
case.

**Four new features.** (1) **Staff duty job sheets** — `agents/shift/burndown.py` gained a pure
`duty_job_sheet(staff, burndown_records, unit)`; `routes/job_sheets.py`'s `GET /job-sheets/
duty/{unit}` calls it directly with no LLM turn (a read-only reformat of data Shift's tools
already compute identically would be pure latency spent on nothing). (2) **Facilities job
sheets** — deliberately **not** a new agent: a maintenance ticket doesn't need a model to reason
about it, and a new Reasoning Engine (its own Terraform SA, `requirements.txt`, Gateway policy
entry, Coordinator `--extra_packages`, deploy step) is real infrastructure spent on a domain
with no autonomy story. Plain CRUD against a new `job_sheets` Firestore collection,
`require_firebase_auth`-gated. (3) **Purchase-order documents** — no new agent or data model;
`agents/supply/agent.py`'s existing `contact_vendor_for_reorder` now renders a real PO through
the `purchase_order` template instead of a plain-text body. (4) **Surgical scheduling + patient
notifications** — the one genuinely new domain, and where the real-PII architecture actually
lives. New `patients`/`surgical_cases` Firestore collections (`packages/datagen/datagen/
patients.py`, same honest-fabrication discipline as `roster.py` — a small combinatorial name
pool, never a real-person source). `services/platform/crypto.py` (new platform adapter,
`crypto_kms.py`/`crypto_local.py`) does direct per-field Cloud KMS encrypt/decrypt — not
envelope encryption with a local DEK, since every protected value (a name, a DOB, an email, a
phone number) is a few dozen bytes, comfortably inside KMS's payload limit, so a locally-managed
DEK would buy nothing a direct call doesn't already provide. `infra/terraform/modules/kms/` (new)
provisions the key ring/key with 90-day rotation and IAM scoped to only the shared Reasoning
Engine identity + Coordinator's own SA. `services/state.py` encrypts `name`/`date_of_birth`/
`contact_email`/`contact_phone` on every `patients` write and decrypts only for callers that
already passed `require_access`. `agents/surgical_scheduling/` (new agent, `AGENT_NAME =
"surgical_scheduling_agent"`) has four tools: `get_surgical_schedule`/
`detect_scheduling_conflicts` (never decrypt or return patient identity — a schedule/conflict
view only ever needs case_id/room/surgeon/time, and the fewer tools that ever see a decrypted
name, the smaller the surface a compromised turn could leak it through), `update_case_status`
(not approval-gated — an internal record change), and `notify_patient_of_status_change`
(approval-gated through the existing `perform_or_request`, sends only if
`notification_consent_email` is true, every send/decline logged to a dedicated
`patient_notification_log` — separate from `activity_log` because PHI-adjacent access deserves
its own audit trail). Conflict detection (`agents/surgical_scheduling/conflicts.py`) is a pure
function over plain dicts, unit-tested exhaustively (11 tests) the same way as `burndown.py`/
`par_levels.py`; `services/triggers.py` gained a `schedule_conflict` trigger kind
(`detect_schedule_conflict_triggers`), same edge-triggered discipline as the other three axes.
`services/fleet_watch.py` computes conflicts every real-time cycle (`caller="fleet_watch"`, the
one non-agent, non-route entry in `access_control.py`'s allowlist, since this read never touches
`patients` — only the PII-free `surgical_cases` collection) and feeds them into `detect_all`.
`routes/surgical_scheduling.py` (new) gives the dashboard `GET /cases` (any authenticated role —
no patient identity on this shape at all) and `GET/POST /cases/{case_id}` +
`.../status`/`.../notify` (`require_role("admin", "clinician")` — the one place decrypted
identity reaches the browser, closing threat-model finding 6 for real). The manual notify route
reuses the agent tool's own logic (`notify_patient_of_status_change_as`, exported specifically
for this) rather than re-implementing the encryption/consent/approval/audit path a second time —
but with its own `caller="dashboard_route"`/`requested_by="manager_dashboard"` rather than
silently borrowing the agent's identity, which would misattribute a human-initiated action to
the fleet, the same conflation this file's autonomous-watch section calls out for `initiated_by`
in the opposite direction. `notify_patient_of_status_change`'s tool-facing signature deliberately
does **not** take `caller`/`requested_by` as parameters, even though the reusable core does:
ADK's `FunctionTool` only strips a `tool_context` parameter from what it hands the model, so a
`caller` kwarg on the LLM-facing function would let the model (or a successful prompt injection)
supply its own value for either, reaching the access-control allowlist and the approval audit
trail. Only trusted Python call sites choose those two values. Wired into the Coordinator
(sixth `AgentTool`) and the Gateway's `_POLICY_TABLE`; `scripts/seed_registry.py` and
`scripts/seed_policy.py` both gained the new agent's entries; `routes/dashboard.py`'s
`build_overview()` gained a `surgical_schedule` slice (cases + conflicts, no PII, safe on the
public feed like admissions); `routes/agents.py`'s `_AGENT_TASK_TYPE`/`_AGENT_LIVE_STATE_KEYS`
and the frontend's `AGENT_META`/`TASK_LABEL` maps all got the new agent's entries too — a
registry row with no frontend meta entry was the most likely way the fleet overview would have
silently broken.

**A generator bug caught before it ever reached a live watch cycle, not after.** The first
version of `generate_surgical_cases` cycled a small physician pool (as few as 4 in some seeds)
across 10 cases with only 4 distinct time slots across 3 rooms — pigeonhole guaranteed far more
than the two *deliberately* engineered conflicts; a direct run produced **12** incidental
conflicts. Traced forward through the code just wired rather than dismissed as a data-shape
curiosity: `detect_schedule_conflict_triggers` emits one trigger per new conflict key,
`run_triggers` runs them strictly sequentially (by design, so a viewer can follow one causal
chain), each trigger opens a real agent turn with `TURN_TIMEOUT_SECONDS = 90` — 12 conflicts on
the very first watch cycle after seeding could mean up to 18 minutes in one cycle and a dozen
approval emails, directly violating both `autonomy.py`'s own "well under
`WATCH_INTERVAL_SECONDS`" invariant and the autonomous-watch safety claim that "the blast radius
of a false trigger is one email." Fixed by building the baseline schedule to have *zero*
incidental overlap (each room's cases laid out back-to-back with a buffer; at most one case per
surgeon) and forcing exactly two conflicts afterward via `dataclasses.replace` — verified by
regenerating and running the real `detect_conflicts` against the output: exactly 2 conflicts,
both the intended ones.

**Frontend.** New `/surgical-schedule` and `/job-sheets` pages (`Sidebar.tsx` nav entries under
"Ward"), both consuming the same `authedFetcher<T>` SWR pattern `staff.ts`/`payroll.ts` already
established. The surgical-schedule page shows the case table + a conflict banner to any signed-in
role; clicking a case attempts the identity-bearing detail fetch and renders a plain "restricted
to admin/clinician" message on a 403 rather than a broken panel, so an `ops`-role viewer sees a
real least-privilege boundary, not an error. `AuthContext.tsx`'s `signIn` now force-refreshes the
ID token (`getIdToken(true)`) immediately after sign-in, closing the gap where `set_user_role.py`
sets a custom claim moments before (or during) a session and the cached token wouldn't otherwise
carry it until Firebase's natural ~1-hour refresh — the difference between `require_role`
correctly 403ing a real non-admin and incorrectly 403ing a judge whose role was set correctly.

**Verified:** `black --check .`, `pylint agents routes services` at 10.00/10, full backend suite
(187 tests, 97.17% coverage), a live rate-limit burst test that 429'd only after both bugs above
were fixed, and `tsc --noEmit`/`eslint .`/`next build` all clean on the frontend including the
two new pages. **Cross-package KMS round-trip, specifically checked rather than assumed:**
`packages/datagen`'s `crypto.py` is a deliberate small duplicate of `apps/api`'s
`crypto_kms.py` (packages/datagen and apps/api are independent uv projects with no shared
workspace — see `services/triggers.py`'s own precedent for this shape of duplication), so
nothing before this actually proved a value one encrypts, the other decrypts. Checked directly
against the real deployed `prudently-patient-data`/`patient-pii` key: `datagen.crypto.
encrypt_field("Test Patient Name")` produced real ciphertext, and `apps/api`'s own
`KmsCryptoService.decrypt_field` on that exact ciphertext returned `"Test Patient Name"` back —
confirmed the two implementations are genuinely interoperable, not just individually
self-consistent.

**Deploy wave — done, and a real bug caught mid-sequence, not in review.** Shift and Supply
redeployed in place (existing engine ids); Surgical Scheduling deployed fresh (new engine id
`4989418290347507712`, written into `config.py`); Coordinator redeployed last with
`--extra_packages=agents/surgical_scheduling` added — the first Coordinator attempt hit the
exact `Connection reset by peer`-with-`exit 0` failure this file's "Running / deploying an
agent" section already documents, and the retry then hit a second, previously-unseen variant of
the same underlying flakiness: `400 FAILED_PRECONDITION ... not in ACTIVE state. Current state:
UPDATING`, because the first "failed" attempt had actually landed server-side and was still
applying. Confirmed via the engine's own `operations` list (`GET .../operations`, not assumed)
that the in-flight update was genuinely progressing, not stuck; a clean redeploy once it reached
`ACTIVE` succeeded, and a fresh `stream_query` round-tripped cleanly per this section's own
"unverified until a fresh call round-trips" rule. `scripts/verify_deploys.py` gained a smoke
prompt for `surgical_scheduling_agent`; every one of the 8 engines verified live (`--query`).
`scripts/seed_registry.py`/`scripts/seed_policy.py` re-run to add the new agent and task type —
the first live Coordinator→Surgical-Scheduling routing attempt, before this, genuinely failed
with "the Surgical Scheduling Agent is currently not registered" (the Gateway's real
authorization check working exactly as designed, not a bug) until the registry write landed.
`bash infra/scripts/deploy.sh` redeployed `prudently-api`/`prudently-web`; both live, and the
site's `<title>`/favicon/apple-icon all confirmed 200 from the deployed URL, closing the
original "logo, favicon are all not visible" complaint that opened this entire body of work.
`scripts/set_user_role.py manager@prudently.app admin` set the real demo account's role,
confirmed via a direct Admin SDK read of its custom claims (`{'role': 'admin'}`), not just the
script's own stdout.

**The live end-to-end pass happened on its own, not as a scripted step — real patient data was
seeded via the new `packages/datagen/datagen/backfill_patients.py`** (an additive backfill
against the live project, deliberately not a full `make seed` rerun — see that script's own
docstring for why re-running the whole generator would have overwritten weeks of accumulated
live fleet-watch state in `staff_roster`/`inventory`/etc.). Within roughly a minute of
`prudently-api` going live with the already-running background watch loop, the fleet noticed
the two deliberately-seeded conflicts on its own: `activity_log` shows two real
`autonomous_action` entries for `schedule_conflict` (CASE-0000/CASE-0001 in OR-1, CASE-0002/
CASE-0003 sharing surgeon `pd-er-00`), each followed by the agent calling `update_case_status`
(one case in each pair moved to `delayed`) and `notify_patient_of_status_change` — which,
correctly, produced a `pending_approval` status rather than actually sending anything, and
generated two real approval-request emails to the manager inbox
(`manager_email` = the platform owner's own address), exactly matching how every other
approval-gated action in this fleet already behaves — not a new behavior, not a bug, just this
feature's first live instance of it. `patient_notification_log` shows the matching
`pending`→`pending_approval` audit trail, with plain-language messages ("your procedure has
been rescheduled to avoid a scheduling conflict") carrying no internal jargon, per the agent's
own instruction. A direct Firestore read of `patients/PT-0000` confirmed ciphertext (not
plaintext) for every PII field, and `get_patient(caller="dashboard_route")` against that same
document round-tripped to the correct decrypted values. This is the plan's own "Verification"
section's live end-to-end pass, achieved without a single scripted trigger call — the fleet did
it unprompted, which is the entire thesis of this project. **One piece deliberately not
claimed as verified:** an actual authenticated HTTP round-trip through
`require_role("admin", "clinician")` against the deployed API, using a real ID token minted for
`manager@prudently.app`. The demo account's password isn't something this session has or should
obtain, so what's confirmed instead is each piece independently — the custom claim is correctly
set on the real account (read back via the Admin SDK, not just the setter script's stdout), and
`require_role`'s 401/403 branching is covered by the existing unit-test suite — not the full
signed-in-browser path together in one live call. `docs/threat-model.md`'s finding 6 stays
marked Fixed on the strength of those two pieces plus the routes existing and passing local
tests; a real browser sign-in as the demo account would be the remaining confirmation.

**One live side effect worth naming plainly:** the two approval-request emails above are real
mail in a real inbox, generated by testing this feature against production, not by any user
action — consistent with the platform's existing behavior for every other approval-gated
action, but worth surfacing explicitly rather than leaving a judge (or the project owner) to
discover two unexplained emails on their own.

## Agent Identity, actually fixed — finding 9 closed for real (Aug 24)

A hackathon-judge evaluation of this project (scored against the actual published rubric —
Innovation 40%, Architecture 30%, Demo/Production Readiness 30% — fetched live, not assumed)
called out `docs/threat-model.md` finding 9 as the weakest piece of an otherwise strong
Architectural Discipline score: **Agent Identity is a mandatory Fortified Enterprise Fleet
component**, and every deployed Reasoning Engine ran under one shared Google-managed identity
(`service-<project-number>@gcp-sa-aiplatform-re.iam.gserviceaccount.com`) with a project-wide
`roles/datastore.user` grant. The finding, and this file's own earlier notes, treated that as a
hard platform limitation — "Agent Engine has no per-agent service account support," confirmed
(so it seemed) by `adk deploy agent_engine --help` showing no `--service_account` flag.

**That premise was wrong, and checking it instead of restating it is what actually closed this
finding.** `adk deploy`'s CLI has no such flag — but the underlying API it calls does:
`vertexai._genai.types.common.AgentEngineConfig` (confirmed by reading the installed SDK
directly, `AgentEngineConfig.model_fields`) has a real `service_account` field, and the proto it
maps to (`ReasoningEngineSpec.service_account`) documents exactly this use: "the service account
that the Reasoning Engine artifact runs as... If not specified, the Vertex AI Reasoning Engine
Service Agent in the project will be used." `adk deploy`'s own `.agent_engine_config.json`
mechanism (already in the CLI, reading a JSON file from each agent's own folder and merging its
keys into the same config the CLI itself builds) is the way in — no new deploy tooling, no fork
of `adk`, just a JSON file per agent.

**What actually shipped.** `infra/terraform/modules/iam` already provisioned one dedicated SA
per agent (`<agent>-agent-sa`) — they existed since early in this project but were never bound
to anything, a fact the finding's own evidence should have been a bigger flag than it was. Added
the 8th (`surgical-scheduling-agent-sa` — hyphenated, not underscored: GCP service account ids
reject `_`), gave it the same baseline grants every other per-agent SA already had
(`aiplatform.user`, `aiplatform.memoryEditor`, `datastore.user`, Secret Manager access to the
Gemini key and Gmail password), and additionally scoped Cloud KMS `patient-pii` decrypt to it
specifically (plus `coordinator-agent-sa`, for the reason below) instead of the shared identity.
A new `.agent_engine_config.json` — `{"service_account": "<agent>-agent-sa@...iam.gserviceaccount
.com"}` — went into each of the 8 agent folders. Redeployed all 8 via the exact same `adk deploy
agent_engine` commands this file already documents, no flag changes. Two of the eight hit the
same transport flakiness this file already has a name for (`Connection reset by peer` with `exit
0`, and — a variant not seen before — `400 FAILED_PRECONDITION ... not in ACTIVE state` on an
immediate retry, because the "failed" attempt had actually landed and was still applying);
confirmed via each engine's own `operations` list before retrying, same discipline as the
Coordinator redeploy flakiness already documented here.

**Verified live, not assumed from the Terraform diff.** `client.agent_engines.get(...)
.api_resource.spec.effective_identity` read back as each agent's own dedicated SA for all 8 —
`shift-agent-sa`, `supply-agent-sa`, ..., `surgical-scheduling-agent-sa` — not the shared
identity. Before removing the shared identity's grants, two functional checks specifically
chosen to exercise the capabilities that would break first: a live `stream_query` against the
deployed `surgical_scheduling_agent` asking it to notify a patient with `notification_consent_
email=False` (CASE-0009 / Elena Patel) — genuinely called `get_patient()`, genuinely decrypted
through Cloud KMS under the new SA, correctly returned `consent_declined` with zero side
effects (no email, no approval created) — and a live `stream_query` against `medical_
representative_agent`, which on the very first attempt under its new SA responded "Blocked by
Model Armor... Model Armor call failed" — a real regression, caught immediately rather than
missed: `medrep-agent-sa` had never been granted `roles/modelarmor.user` (only the shared
identity and `coordinator-agent-sa` had it, from before any agent had its own SA). Fixed with a
dedicated `medrep_sa_modelarmor_user` grant; re-verified clean. The same audit also caught that
Cloud Trace span export (`roles/cloudtrace.agent`) had only ever been granted to `coordinator-
agent-sa` and the shared identity — meaning every other agent's spans would have silently
stopped exporting under its own new identity (a dropped span, not a raised exception, so nothing
would have *looked* broken) — fixed with a `for_each` grant across all 8 SAs before it ever
shipped silently broken.

**Only then** — after every engine's own functionality was independently reverified under its
new identity — were the shared Reasoning Engine service agent's now-vestigial grants removed:
`roles/datastore.user`, `roles/modelarmor.user`, `roles/cloudtrace.agent` (all project-level),
plus its Secret Manager access to the Gemini key, Gmail password, and A2A shared secret. The A2A
shared secret's grant moved to `supply-agent-sa` specifically (the standalone deployed
`supply_chain_resiliency_agent` engine's own identity when invoked directly, e.g. via
`stream_query` — distinct from the live in-process A2A path, which already runs as
`coordinator-agent-sa` via Cloud Run and was never affected). The shared identity now holds
**zero** grants on this project's Firestore, Model Armor, Cloud Trace, Secret Manager, or Cloud
KMS resources — confirmed by reading the Terraform plan's diff, not assumed from the intent.

**What this does not fix, stated the same way the original finding did.** Firestore has no
native per-collection IAM, so `roles/datastore.user` is still project-wide on every per-agent
SA — identity separation is real (independent audit trail, independent revocation, independent
rotation), but it is not per-collection least privilege by itself; `services/platform/
access_control.py`'s application-layer allowlist is still the actual mechanism restricting which
agents may touch `patients`/`surgical_cases`, now backed by a real distinct credential instead
of a self-declared string riding on shared IAM. And `coordinator-agent-sa` necessarily keeps
broad access, because Coordinator's "frozen copies" architecture executes every specialist's
tool code in-process inside both Coordinator's own Reasoning Engine and `prudently-api`'s Cloud
Run container (which also runs as `coordinator-agent-sa`) — an inherent consequence of in-process
bundling, not something reachable by a different IAM setup without re-architecting how
Coordinator invokes specialists.

**Docs updated to match:** `docs/threat-model.md` finding 9 rewritten from "Accepted, as
designed" to "Fixed," with the two residual limits above stated explicitly rather than left
implicit. `docs/security-architecture.png`/`.svg` regenerated — the "Shared Reasoning Engine
identity" card that read Accepted/red now reads Fixed/green as "Per-agent Reasoning Engine
identity," and the "Application access control" card's framing updated to "now backed by real
per-agent identity, not a self-declared caller on shared IAM." No Cloud Run redeploy was needed
— `prudently-api`'s own runtime identity was already `coordinator-agent-sa` via `modules/
cloud_run_api/main.tf`, untouched by this change; only the 8 Reasoning Engine deploys and two
Terraform applies (IAM/KMS grants, then Secret Manager grants) were required.
