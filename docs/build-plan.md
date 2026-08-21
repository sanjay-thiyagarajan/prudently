# Prudently — Fortified Enterprise Fleet Hackathon Build Plan

## Context

Sanjay is entering the **All Things Agentic Hackathon** (allthingsagentichackathon.devpost.com), targeting the **Fortified Enterprise Fleet** track ($20K track prize, also eligible for the $50K grand prize and bonus categories). Deadline is **Aug 31, 2026, 5pm PDT**, working **solo, full-time**. The project directory `/Users/sanjay/Desktop/OpenSource/prudently` started completely empty on Aug 20 — this is a greenfield build.

The track requires demonstrating seven specific "Gemini Enterprise Agent Platform" capabilities (Agent Registry, Agent Runtime, Memory Bank, Agent Identity, Agent Gateway, Model Armor, Agent Observability) plus the hackathon-wide mandatory stack (Gemini 3.5+, a Google Agent Framework, a GCP infra service). Every unverified capability gets a real vs. local-emulated adapter, resolved by a Day-1 verification spike — see `docs/day1-probe-results.md` for the binding table (Agent Runtime, Memory Bank, and Model Armor confirmed real; Registry, Identity, Gateway, Observability run as local-emulated adapters behind the same interface a real product would satisfy).

The product concept is **Prudently**: an agent-monitored hospital operations fleet for a single hospital, single GCP region, demoed against a scripted flu-outbreak surge.

**Agent roster — expanded Aug 21, after Day 3 shipped.** The original plan had 3 specialists (Shift Allocation, Supply Chain Resiliency, Chaos & Continuity) behind a Coordinator. Sanjay asked mid-build to add an Inventory Management Agent, an HR Agent, and a Medical Representative Agent, with A2A used where it genuinely fits, and confirmed the Day 6 midpoint checkpoint should count the expanded roster as in-scope, not just the original three. The roster is now:

| Agent | Role | Status |
|---|---|---|
| **Coordinator** | Root, sole user-facing entry point, routes through the Gateway | **Deployed & verified, Aug 21** |
| **Shift Allocation** | Fatigue/overtime burndown → reallocation recommendations | **Deployed & verified, Day 3** |
| **Inventory Management** | Tactical: SKU-level stock, par levels, consumption tracking | **Deployed & verified, Aug 21** |
| **Supply Chain Resiliency** | Strategic: vendor lead times, reorder decisions, alternate sourcing | **Deployed & verified, Aug 21** |
| **HR** | Credentialing, and the escalation target when Shift Allocation runs out of reallocation options (activate per-diem pool) | **Deployed & verified, Aug 21** |
| **Medical Representative** | External-facing vendor/pharma liaison; owns the Model Armor "poisoned vendor email" demo moment; talks to Supply Chain via genuine **Agent2Agent**, not the internal Gateway | **Deployed & verified, Aug 21** — Model Armor screening AND the Supply Chain A2A hop both verified live end-to-end |
| **Chaos & Continuity** | Hospital-domain what-if scenarios + fleet-domain fault injection | Not started |

**Why these three, concretely:**
- **Inventory Management** is a free split, not new scope: the original "Supply Chain Agent" conflated tactical stock-tracking with strategic vendor decisions. Splitting them was already the right call before the request; Day 4 hadn't started yet so nothing was rebuilt.
- **Medical Representative** is a genuine upgrade over the original plan, not scope creep: the Model Armor "poisoned vendor email" beat was always going to live somewhere. Giving it a dedicated agent at an explicit external trust boundary — rather than bolting the screening logic onto Supply Chain's tool code — is architecturally more honest, and it turns A2A from a "stretch goal, maybe" into a load-bearing part of the design: Supply Chain ↔ Medical Representative is exactly the boundary where two separately-deployed agents with distinct identities makes sense.
- **HR** is real value (an autonomous escalation path when Shift Allocation alone can't solve a critical burndown) but is explicitly the first thing cut if the schedule slips — see §5.

Sanjay's existing repos (`nerifect-backend`, `nerifect-frontend`, `career-ops`) establish real conventions this project follows: FastAPI + `google-adk` + `uv` + pytest-with-coverage-gate + Makefile-driven workflow on the backend; Next.js/React/TypeScript/MUI/Tailwind on the frontend; `AGENTS.md` as the canonical AI-instruction file, `CLAUDE.md` as a one-line `@AGENTS.md` pointer. This project deliberately deviates from his usual split-repo habit (monorepo instead), because Devpost judging requires a single code repository with reproducible spin-up instructions.

## Goal

Ship a submission-ready, GCP-deployed multi-agent system by Aug 31 that (a) satisfies all mandatory hackathon tech requirements, (b) visibly demonstrates all seven Fortified Enterprise Fleet capabilities (real or honestly-labeled local fallback), (c) demonstrates genuine Agent2Agent between Supply Chain and Medical Representative, and (d) tells a coherent, judgeable story through a flu-surge demo scenario — including one visible Model Armor "blocked" moment. See §1a for a deferred "better than existing enterprise systems" positioning discussion — not part of the Aug 31 scope below.

## 1a. Positioning: what "better than existing enterprise hospital systems" honestly means here (added Aug 21, deferred same day)

Sanjay asked mid-build to refine the plan so Prudently becomes "a better replacement for existing enterprise hospital management systems used globally." Taken literally against Epic, Oracle Health (Cerner), or MEDITECH — full EHR, clinical-documentation, billing, and HIPAA/ONC-certified interoperability platforms with years of regulatory history — that claim doesn't survive contact with reality in an 11-day solo hackathon build, and claiming it anyway would read as naive to judges who know the space.

Prudently's actual competitive category is narrower and the claim *is* achievable there: hospital **operations coordination** — staffing/capacity, inventory, supply chain, vendor risk — the category occupied by point solutions like TeleTracking, Qventus, LeanTaaS iQueue, and Central Logic. Those systems are largely rule-based dashboards operated by a human; they don't have autonomous cross-functional agents that reason and hand off to each other (Shift → HR escalation, Inventory → Supply Chain reorder, Supply Chain → Medical Representative A2A), and they don't ship an AI-native security boundary (Model Armor) or agent governance layer (Registry/Identity/Gateway) at all. That is Prudently's genuine, defensible edge over the *actual* incumbents in its category — "does what TeleTracking/Qventus do, autonomously, with security built in," not "replaces Epic."

The one concrete, buildable-in-days gap separating a hackathon demo from something a hospital IT team could evaluate seriously is **interoperability**: real hospital systems, including the EHRs named above, exchange data via HL7 FHIR R4. A scoped FHIR-compatible read layer (`apps/api/routes/fhir.py`) exposing live staffing/inventory state as standard FHIR resources (Practitioner, PractitionerRole, Schedule/Slot, SupplyDelivery-shaped) was sketched as the concrete deliverable here — additive and read-only, no changes to any deployed agent's logic, no new Firestore writes. **Deferred same day, Aug 21:** Sanjay asked to focus on the planned §5 schedule for now and revisit this positioning/scope question later — nothing below is currently scheduled. Revisit after the Aug 31 submission is stable, or earlier if there's confirmed slack.

## 1. Repo structure (monorepo — flagged deviation from Sanjay's usual split-repo pattern)

```
prudently/
├── AGENTS.md                      # canonical AI-assistant instructions
├── CLAUDE.md                      # "@AGENTS.md" one-liner, matches nerifect-frontend/career-ops
├── README.md                      # judge-facing: architecture, spin-up, deploy
├── Makefile                       # root orchestrator, delegates into apps/api and apps/web
├── .env.example
├── .gitignore
├── docs/
│   ├── architecture.png/.svg      # + editable source
│   ├── day1-probe-results.md      # capability findings, drives adapter selection
│   ├── build-plan.md              # this file
│   └── demo-script.md             # beat-by-beat video script (§6)
├── apps/
│   ├── api/                       # FastAPI + ADK backend — mirrors nerifect-backend conventions
│   │   ├── pyproject.toml / uv.lock
│   │   ├── app.py
│   │   ├── config.py              # MODEL_REASONING/MODEL_FAST, *_BACKEND selectors, GCP_PROJECT_ID
│   │   ├── Makefile
│   │   ├── routes/{sim.py, health.py, armor_events.py, coordinator.py}
│   │   ├── agents/
│   │   │   ├── coordinator/agent.py
│   │   │   ├── shift/{agent.py, burndown.py, requirements.txt}         # deployed, Day 3
│   │   │   ├── inventory/{agent.py, par_levels.py, requirements.txt}   # tactical stock
│   │   │   ├── supply/{agent.py, reorder.py, requirements.txt}         # strategic vendor
│   │   │   ├── hr/{agent.py, credentialing.py, requirements.txt}
│   │   │   ├── medrep/{agent.py, requirements.txt}                     # separate Reasoning Engine, real A2A
│   │   │   └── chaos/{agent.py, fault_injection.py, requirements.txt}
│   │   ├── services/
│   │   │   ├── platform/          # port/adapter layer — see §2
│   │   │   │   ├── registry.py / registry_vertex.py / registry_local.py
│   │   │   │   ├── identity.py / identity_vertex.py / identity_local.py
│   │   │   │   ├── gateway.py / gateway_vertex.py / gateway_local.py
│   │   │   │   ├── armor.py / armor_vertex.py / armor_local.py
│   │   │   │   └── observability.py / observability_vertex.py / observability_local.py
│   │   │   ├── memory.py          # VertexAiMemoryBankService wrapper — working, Day 3
│   │   │   ├── simclock.py        # Pub/Sub tick publisher/subscriber, SIM_SEED, SIM_SPEEDUP
│   │   │   └── state.py           # Firestore live-state accessors
│   │   ├── tests/{unit,integration}/
│   │   └── evals/
│   └── web/                       # Next.js dashboard — mirrors nerifect-frontend conventions
│       └── src/{app, components/{ui,layout,providers,workspace}, contexts, hooks, lib}
├── packages/
│   └── datagen/                   # roster, inventory, admissions (scripted flu surge), seed
└── infra/
    ├── terraform/
    │   ├── providers.tf, variables.tf, outputs.tf, main.tf
    │   ├── modules/{cloud_run_api, cloud_run_web, firestore, pubsub, iam, secrets}
    │   └── envs/dev/{backend.tf, terraform.tfvars}   # local tfstate — deliberate hackathon-scope choice
    └── scripts/{day1_capability_probe.sh, deploy.sh}
```

Each agent directory ships its own `requirements.txt` — required by `adk deploy agent_engine`, which resolves deploy-time dependencies via plain `pip` against that file, not the shared `uv.lock` (confirmed Day 3: the two resolvers can and do diverge).

**No `alembic/`/SQLAlchemy**: Prudently's state is document-shaped and needs to be shared with Vertex tooling — Firestore replaces the relational layer entirely.

**Coverage gate, scoped not dropped:** `pytest --cov-fail-under=80` scoped to pure-logic modules only — `agents.shift.burndown` (100% as of Day 3), `agents.inventory.par_levels`, `agents.supply.reorder`, `agents.hr.credentialing`, `services.simclock`, `services.platform`. ADK orchestration glue (`agent.py` files, `services/memory.py`, `services/state.py`) is excluded — proven Day 3 that even *importing* those modules under pytest triggers live GCP calls unless carefully guarded, which is exactly the kind of fragility the scoping was meant to avoid.

## 2. Capability → GCP mapping, fallback design

| # | Capability | Status (confirmed Day 1) | Real backing | Fallback (`_local.py`) |
|---|---|---|---|---|
| 1 | Agent Runtime | **Confirmed** | Vertex AI Agent Engine (`ReasoningEngine`), ADK "Full Integration", `adk deploy agent_engine` | none needed |
| 2 | Memory Bank | **Confirmed, working end-to-end** | `VertexAiMemoryBankService` — must use the *same region* as its `agent_engine_id` (confirmed Day 3: `us` 404s, `us-central1` works) | none needed |
| 3 | Agent Registry | Not found as distinct product | — | Firestore `agent_registry` collection: `{agent_name, version, owner, description, endpoint_uri, capabilities[], approved}` |
| 4 | Agent Identity | Not found as distinct product | Deployed agents run under Google's own `service-*@gcp-sa-aiplatform-re.iam.gserviceaccount.com`, confirmed Day 3 — **not** any custom per-agent SA; Agent Engine has no `--service_account` deploy flag | Per-agent SAs (`modules/iam`) still used for local dev / any future custom-SA support; the reasoning-engine service agent gets explicit IAM grants alongside them |
| 5 | Agent Gateway | Not found as lightweight product | — | ADK `before_tool_callback`/`after_tool_callback` interceptor in the Coordinator |
| 6 | Model Armor | **Confirmed real product** | `modelarmor.googleapis.com` | Regex/heuristic fallback behind the same `ArmorVerdict` interface |
| 7 | Agent Observability | Not found as distinct dashboard | — | OpenTelemetry SDK → Cloud Trace + Cloud Logging |

Two GCP-specific bugs were root-caused Day 3, both now fixed in code with comments explaining why (see `apps/api/services/state.py` and `apps/api/config.py`) — every subsequent agent inherits the fix automatically:
1. Agent Engine auto-injects `GOOGLE_CLOUD_PROJECT` into the sandbox as the numeric **project number**, silently overriding pydantic-settings' default; Firestore's resource-path resolution rejects the numeric form. Fixed with a hardcoded `GCP_PROJECT_ID` constant, bypassed for anything building a GCP resource path.
2. Memory Bank scoped to a specific Reasoning Engine must use that engine's own region.

## 3. GCP infra service selection

- **Cloud Run** (`prudently-api`, `prudently-web`) — deployed and live since Day 2.
- **Vertex AI Agent Engine (Reasoning Engine)** — **two** engines, not one:
  - **Primary engine**: Coordinator + Shift + Inventory + Supply Chain + HR as `AgentTool` sub-agents under one ADK app, Gateway as an in-process interceptor. This is still the right call for five of six specialists — real routing/policy chokepoint without the overhead of five separately-deployed engines.
  - **Medical Representative engine**: deployed **separately**, invoked from Supply Chain via genuine Agent2Agent. This is no longer a "stretch goal" — it's committed scope, because it's the one boundary in the design that actually warrants a separate deployed identity (external-facing, untrusted-by-default).
  - **Chaos & Continuity**: stays inside the primary engine (its fault-injection targets are internal to the fleet, no boundary-crossing rationale for a separate deployment).
- **Vertex AI Memory Bank** — per-engine, region-matched (see §2).
- **Pub/Sub** — simulation clock + Gateway-intercepted audit-event bus.
- **Firestore** (regional `us-central1`, Native mode) — `staff_roster`, `shift_history`, `inventory`, `vendors`, `admissions_timeseries`, `agent_registry`, `armor_events`, `chaos_experiments`.
- **Secret Manager** — Gemini API key, fetched at runtime by each agent (`config.bootstrap_gemini_credentials()`), never baked into a deploy bundle.
- **Cloud Trace + Cloud Logging** — Observability fallback.
- **IAM** — per-agent SAs (Identity fallback) *and* explicit grants to the real Agent Engine runtime identity (see §2 note #4).

## 4. AGENTS.md content outline

`AGENTS.md` canonical, `CLAUDE.md` = `@AGENTS.md`. Sections: what Prudently is; agent roster table (now 7 rows, including which engine each deploys to and its Memory Bank scope key); the platform adapter layer; local dev commands; running/deploying an agent via ADK CLI (including the per-agent `requirements.txt` requirement and the two root-caused GCP gotchas from §2); service-account/IAM setup; Makefile targets; testing conventions; Terraform apply flow; simulation clock.

## 5. Schedule

**Progress log (why the remaining schedule doesn't map 1:1 to "days since Aug 20"):** Days 0–3 of the original plan — scaffold, GCP provisioning + capability probe, first Cloud Run deploy + datagen + sim clock, and the Shift Allocation Agent fully deployed and verified with working Memory Bank — were all completed by the morning of **Aug 21**, well ahead of the original per-day calendar mapping. That buffer is what makes the roster expansion affordable. The schedule below is anchored to calendar dates going forward, not "Day N" labels.

- **Aug 21 (afternoon/evening) – Aug 22:** ~~Inventory Management Agent (`par_levels.py`, tested) + Supply Chain Resiliency Agent (`reorder.py`, tested), both deployed to the primary engine and verified with real queries against live Firestore, mirroring the exact verification discipline from Shift (a real query with tool-call output, not just deploy exit code 0).~~ **Done, Aug 21 afternoon** — Inventory (`reasoningEngines/6199971796435861504`) and Supply Chain (`reasoningEngines/6129884527234908160`) both deployed and verified via `stream_query` against the live engines with real Firestore-backed tool-call output. Supply Chain's `reorder.py` deliberately re-derives stock status from raw inventory items rather than importing `agents.inventory.par_levels` — cross-agent-folder imports don't survive `adk deploy`'s per-folder staging without extra `--extra_packages` fragility (see `agents/supply/reorder.py` docstring). 38/38 unit tests passing, 100% coverage on both new pure-logic modules individually (the combined `--cov` run under-reports both modules' coverage — not flakiness as first assumed, but a module-import-order issue: coverage's tracer attaches after the module is already imported once, which under-reports the module-level statements specifically; per-file `--cov=<module>` runs confirm real 100%).
- **Aug 23:** ~~HR Agent (`credentialing.py` + escalation-from-Shift logic) + Medical Representative Agent, deployed **separately** to its own Reasoning Engine. Model Armor screening (`services/platform/armor.py` real + local adapters) built into Medical Representative's ingestion path from the start, not bolted on later.~~ **Done, Aug 21 evening.** HR deployed (`reasoningEngines/5467010957081313280`) and verified via `stream_query`; added `credential_expiry` + a per-diem coverage pool to `staff_roster` (see AGENTS.md). Medical Representative deployed separately (`reasoningEngines/6319035711584468992`) with Model Armor wired into its ingestion tool from the start (`services/platform/armor.py` real + local adapters, real template `prudently-vendor-ingest` in `us-central1`) — verified live against the deployed engine with both a clean vendor message (accepted) and a poisoned prompt-injection payload (blocked, `pi_and_jailbreak` filter, model correctly refused to act on the injected instruction). `modelarmor.googleapis.com` had to be manually enabled (Day-1 probe's "enabled in this project" claim was wrong) and the Reasoning Engine runtime SA needed `roles/modelarmor.user` granted by hand + added to Terraform (`terraform plan` confirms clean: 16 to add, 0 destroy — not yet applied). 59/59 unit tests passing, lint clean. A2A wiring from Supply Chain to Medical Representative is still Day 5 scope, not done here. **Known gap, must close before Aug 27 (see `agents/medrep/agent.py` docstring):** `screen_vendor_message` is a `FunctionTool` — the model reads the raw message into its own context to build the tool call *before* Model Armor screens it, so today's screening happens after LLM context exposure, not before it. What's verified is that the model never acts on blocked content, not that the poisoned text never reached the model. Aug 27's "blocked before reaching LLM context" claim needs a real pre-LLM boundary (FastAPI ingestion route or `before_model_callback`) — decide the shape before that day, keep the tool as a second defense-in-depth layer once it lands. Also noted for the "learnings" text: the sanitize response flagged filter version V1 as moving to LEGACY on 2026-09-01 — after the Aug 31 deadline, so not blocking, but worth one sentence if judges review post-submission.
- **Aug 24–25:** ~~Coordinator Agent (root, wraps Shift/Inventory/Supply/HR as `AgentTool` sub-agents) + Gateway interceptor (Registry lookup → Armor check → Observability span → policy table) + Registry (seeded with all 7 agents) + Identity (per-agent SA IAM grants, plus the real Agent Engine runtime identity per §2) + Supply Chain ↔ Medical Representative A2A wiring.~~ **Done, Aug 21 night.** All five pieces built and verified live, not just deployed — see AGENTS.md for the mechanics of each. Coordinator (`reasoningEngines/6956858008810815488`) wraps Shift/Inventory/Supply/HR as `AgentTool`s via a flattened-import trick proven with a disposable probe deploy first; a real query against it correctly called all four specialists and synthesized a cross-agent answer (flagging a General Ward per-diem coverage gap that no single specialist's own output stated directly). Gateway is a real `before_tool_callback` — Registry lookup, then a policy-table authorization check, both verified to actually block (unregistered target, inactive-status target, unauthorized caller — three distinct block paths confirmed with synthetic calls) as well as allow. Registry is `agent_registry` in Firestore, 7 rows, seeded via `apps/api/scripts/seed_registry.py`. Identity is a thin resolver, no invented runtime enforcement — per the Day-1 probe's own honesty framing. A2A required deploying Medical Representative a second way: mounted as a Starlette sub-app inside the existing `prudently-api` Cloud Run service (`google.adk.a2a.utils.agent_to_a2a.to_a2a()`) rather than a separate service, since Vertex AI Agent Engine has no native A2A transport — confirmed by checking, not assuming. Two real bugs found and fixed getting there: `to_a2a`'s routes attach inside its own ASGI lifespan, which a plain `app.mount()` doesn't trigger (fixed with explicit lifespan composition); the Cloud Run service's own identity (`coordinator-agent-sa`) needed its own `roles/modelarmor.user` grant, separate from the Reasoning Engine's. Full path verified end-to-end on deployed infra in both directions: a poisoned vendor message sent to the deployed Supply Chain engine correctly routed through A2A to the Cloud Run-hosted Medical Representative, hit real Model Armor, came back blocked, and Supply Chain refused to act on it; a clean message came back accepted and was reasoned about normally. 59/59 unit tests passing, lint clean. **Caught and fixed same night:** the first Coordinator deploy staged `agents/supply` *before* the A2A wiring was added to it, so the Coordinator's in-process copy of Supply Chain had no `medical_representative_agent` tool — every A2A verification above had hit Supply Chain's standalone engine directly, never through the Coordinator, so the "end-to-end" claim below was true of Supply Chain alone, not of the demo's actual entry point. Redeployed Coordinator in place (`reasoningEngines/6956858008810815488`, same `--extra_packages` set) and re-ran the poisoned-message query directly against it: `supply_chain_resiliency_agent` tool call → its response confirms the message was verified via Medical Representative and blocked by Model Armor → Coordinator refuses to act. `agent_registry` reseeded afterward (`make seed-registry`) so `coordinator`'s `reasoning_engine_id` isn't stale/empty. Also confirmed `/sim/reset` on the live Cloud Run URL still returns 200 after the A2A mount — the catch-all `app.mount("/", medrep_a2a_app)` doesn't shadow it.
- **Aug 25/26 — MIDPOINT CHECKPOINT (expanded scope, per explicit confirmation):** ✅ **Met, Aug 21 night** — Coordinator + Shift + Inventory + Supply Chain + HR + Medical Representative (via A2A) all deployed and verified working end-to-end **on GCP**, ahead of the Aug 25/26 date. Dashboard reading live Firestore and the sim clock driving a compressed flu-surge sequence are NOT yet done (still Aug 29–30 scope) — the checkpoint's agent-fleet bar is met, its dashboard/demo-polish bar is not, and that gap is expected per the original schedule. Chaos is intentionally not part of this checkpoint. **Cut order if behind (now moot — checkpoint met early):** (1) fleet-mode fault injection (Chaos, still Aug 27 scope), (2) Supply Chain's alternate-vendor reasoning depth, (3) dashboard polish. **Never cut:** Memory Bank, the Model Armor blocked moment, the Medical Representative A2A path (it's now load-bearing for the track's own "cross-department" and "Agent2Agent" story), the Cloud Run deployment, the video.
- **Aug 27:** ~~Model Armor end-to-end: poisoned-vendor-email prompt injection hits Medical Representative's ingestion path, blocked *before* reaching LLM context, Memory Bank, or Supply Chain via A2A; `armor_events` persisted; dashboard "BLOCKED" banner. Observability wired: OTel spans across the Gateway *and* the A2A hop, Cloud Trace visible, trace ID on Firestore audit records.~~ **Done (observability + `armor_events` piece), Aug 21 night; dashboard banner and pre-LLM boundary remain open, see below.** Real `services/platform/observability.py` (+ `_local`/`_vertex`) added, same port/adapter pattern as the other platform capabilities — `_vertex.py` exports genuine OTel spans to Cloud Trace via `CloudTraceSpanExporter`, `SimpleSpanProcessor` chosen over `BatchSpanProcessor` deliberately (synchronous export — a dropped background-thread batch on a short-lived sandboxed container would fail silently, same failure signature as the `armor_unavailable` bug). `roles/cloudtrace.agent` granted to both runtime identities *before* writing any span code, not after hitting a live failure this time. Gateway's `before_tool_call` now wraps its whole decision in a real span (`gateway.before_tool_call`, attributes for caller/target/decision — allowed or one of three block reasons); Model Armor's real API call is wrapped in its own span (`armor.sanitize_user_prompt`) nested inside a new parent span in Medical Representative's `screen_vendor_message` (`medrep.screen_vendor_message`) — both verified as real, correctly-nested, real-latency spans by querying the Cloud Trace API directly for the resulting trace IDs, not just "exit code 0." `armor_events` is a new Firestore collection, one doc per screening call (`vendor_name`, `message`, `status`, `matched_filters`, `reason`, `service_error`, `source`, `trace_id`, `timestamp`) — `ArmorResult` gained a `service_error: bool` field (this session's earlier "armor_unavailable renders as a successful security demo" gap) so a real Armor outage is distinguishable from a genuine content block, not string-sniffed. `source` distinguishes Medical Representative's two deployment contexts (`standalone_reasoning_engine` vs. `cloud_run_a2a_mount`, told apart via Cloud Run's auto-injected `K_SERVICE` env var — nothing to configure) so the eventual dashboard feed doesn't show duplicate-looking blocks from the path the demo never uses. **Real regression found and fixed getting here:** `adk deploy agent_engine` stages each agent's Python dependencies from *its own* `requirements.txt`, not `pyproject.toml` (Cloud Run's `prudently-api` does read `pyproject.toml`, via its own Dockerfile — the two deploy paths are not symmetric, confirmed by checking both, not assuming). Coordinator's and Medical Representative's `requirements.txt` didn't list `opentelemetry-sdk`/`opentelemetry-exporter-gcp-trace`, so after redeploying with the Observability wiring, every Coordinator tool delegation (not just the A2A path — even a plain `hr_agent` call) silently broke: `before_tool_callback` raising on import inside the ADK tool-call machinery didn't surface as an exception through `stream_query`, it just truncated the event stream with no error text at all — caught by testing the simplest possible path first (a non-A2A HR query) after the A2A path stalled, isolating the regression from the A2A wiring specifically. Fixed by adding both packages to both `requirements.txt` files and redeploying Coordinator + Medical Representative a second time; full path re-verified afterward: Coordinator → `supply_chain_resiliency_agent` (Gateway span, `decision=allowed`) → Medical Representative via genuine A2A on the live Cloud Run URL → Model Armor (`armor.sanitize_user_prompt` span, 217ms real API latency, `pi_and_jailbreak` match) → blocked → Coordinator refuses, with the resulting `armor_events` doc's `source` confirming `cloud_run_a2a_mount` — the actual demo path, not the standalone engine. Test-probe `armor_events` docs deleted afterward so the collection starts empty for the real demo. **Still open, not today's scope:** genuine cross-process trace-context propagation across the A2A HTTP hop (would need `opentelemetry-instrumentation-httpx` on `RemoteA2aAgent`'s `httpx_client` plus ASGI instrumentation on the Cloud Run mount — each process's spans are real and correctly nested *within* that process, but Supply Chain's own trace and Medical Representative's trace are not yet linked into one); the dashboard "BLOCKED" banner (no dashboard exists yet, Aug 29–30 scope); the pre-LLM screening boundary gap noted in `agents/medrep/agent.py`'s docstring (unchanged by this session's work).
- **Aug 28:** Chaos & Continuity Agent — hospital-domain what-if (through Coordinator/Gateway) + fleet-domain fault injection (kill-agent-mid-task, attempted Memory Bank poisoning also caught by Armor, Gateway latency injection). Run once for real against the deployed stack, persist to `chaos_experiments`, replay from there for the demo — never re-run live during recording.
- **Aug 29–30:** Dashboard build-out — fleet overview (7 registry entries), Inventory panel (stock/par-level/expiry), Supply Chain panel (vendor/reorder recommendations, kept visually distinct from Inventory), HR escalation feed, **A2A trace panel** showing Supply Chain ↔ Medical Representative exchanges distinctly from internal Gateway-routed calls, armor_events feed, chaos_experiments replay, observability/trace panel (`dataviz` skill for chart/color conventions). Architecture diagram finalized (7 agents, 2 Reasoning Engines, A2A hop annotated). README spin-up draft.
- **Aug 30 (late) – Aug 31 (morning):** Clean-clone reproducibility test from a bare `git clone`. Record the ~4 min demo video (§6). Capture GCP Console B-roll (Cloud Run revisions, both Reasoning Engine detail pages, Firestore data, Cloud Trace waterfall including the A2A span).
- **Aug 31, submit by noon PDT:** Devpost submission (description, tech, learnings — the two root-caused bugs from §2 are a legitimate, judge-credible "learnings" story), video upload, hosted URL + repo link, final checklist (§7), submit.

## 6. Demo video narrative beats (~4 min)

1. **0:00–0:30** — Problem/value prop: ops manager's view, burnout risk + stockout risk + no fleet coordination today; name the track.
2. **0:30–1:15** — Fleet overview: Coordinator + 6 specialists, Agent Registry entries, calm-baseline Firestore state. Call out Medical Representative's separate deployment explicitly — this is the A2A boundary.
3. **1:15–2:15** — Flu surge, compressed sim clock: Shift Agent flags rising burndown → reallocation; if reallocation options run out, escalates to HR (activate per-diem pool); Inventory flags falling stock → Supply Chain decides to reorder; all flow through the Gateway with trace IDs; Memory Bank timeline advancing across "weeks" in seconds.
4. **2:15–2:50** — **Model Armor blocked moment:** poisoned vendor email hits Medical Representative's ingestion path, dashboard shows red "BLOCKED" banner + `armor_events` entry; narrate that the block happened before the payload could reach Supply Chain via A2A, LLM context, or Memory Bank.
5. **2:50–3:20** — Chaos & Continuity, both modes: hospital-domain what-if (mass-casualty influx) routed through Coordinator; fleet-domain fault-injection results (killed agent, attempted memory poisoning also caught by Armor, injected latency) replayed from the persisted run.
6. **3:20–3:50** — Proof of GCP deployment: Cloud Run console, **both** Vertex AI Agent Engine detail pages, Cloud Trace detail for the Medical Representative screening span (`medrep.screen_vendor_message` → nested `armor.sanitize_user_prompt`, real API latency) pivoted to from its `armor_events` Firestore doc's `trace_id`, plus the separate Gateway decision span (`gateway.before_tool_call`) from the Coordinator side. **Narration note, decide before recording (Aug 27 finding):** these are two real, correctly-nested traces today, not one linked waterfall across the A2A hop — say "Medical Representative's screening trace" and "the Gateway's routing trace," not "the request's trace" or "one full chain," until/unless cross-process trace-context propagation (`opentelemetry-instrumentation-httpx` + ASGI instrumentation, still unbuilt) lands before Aug 29–30.
7. **3:50–4:00** — Close: architecture diagram, one honest sentence on real-vs-emulated capabilities (a credibility beat, not a weakness to hide).

## 7. Submission-readiness checklist

- **Hosted project URL** — `prudently-web` Cloud Run URL, reachable at submission time.
- **Code repository + README** — monorepo root on GitHub; README verified via the clean-clone test; includes `terraform apply`, `make seed`, `make dev`/`make deploy`, region-lock note, both Reasoning Engine IDs.
- **Architecture diagram** — 7 agents, 2 Reasoning Engines, A2A hop, real-vs-emulated per `docs/day1-probe-results.md`.
- **~4 min demo video** — per §6, including explicit GCP deployment proof for both engines.
- **Text description** (features/tech/data/learnings) — the two root-caused Day 3 bugs and the Inventory/Supply split and MedRep A2A rationale are legitimate "learnings" content.

## Verification

- Every agent deploy: a **real query with tool-call output** against the deployed engine, not just `adk deploy` exit code 0 — proven Day 3 that exit 0 does not mean working (3 of 6 Shift deploys "succeeded" while broken).
- Midpoint checkpoint: end-to-end smoke test triggering the sim clock against the deployed Cloud Run API, confirming Shift/Inventory/Supply/HR recommendations appear in the dashboard, Memory Bank facts accumulate, and the Supply Chain ↔ Medical Representative A2A call is visible in Cloud Trace — all running on GCP, not localhost.
- Model Armor day: manually submit the poisoned-vendor-email payload and confirm it's blocked and logged before touching Memory Bank or crossing the A2A boundary.
- Final: clean-clone reproducibility test must succeed end-to-end from a bare `git clone` following only the README.
