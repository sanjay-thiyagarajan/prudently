# Prudently — Fortified Enterprise Fleet Hackathon Build Plan

## Context

Sanjay is entering the **All Things Agentic Hackathon** (allthingsagentichackathon.devpost.com), targeting the **Fortified Enterprise Fleet** track ($20K track prize, also eligible for the $50K grand prize and bonus categories). Deadline is **Aug 31, 2026, 5pm PDT** — **11 days from today (Aug 20)**, working **solo, full-time**. The project directory `/Users/sanjay/Desktop/OpenSource/prudently` is currently empty — this is a greenfield build.

The track requires demonstrating seven specific "Gemini Enterprise Agent Platform" capabilities (Agent Registry, Agent Runtime, Memory Bank, Agent Identity, Agent Gateway, Model Armor, Agent Observability) plus the hackathon-wide mandatory stack (Gemini 3.5+, a Google Agent Framework, a GCP infra service). Only **Agent Runtime** and **Memory Bank** were confirmed in depth via their official docs during research; the other five are named in the track's resource table but not verified as distinct managed products in Sanjay's actual GCP project. This plan is built so that ambiguity doesn't block progress: every unverified capability gets a real vs. local-emulated adapter, resolved by a Day-1 verification spike, not guessed at architecture time.

The product concept — decided with Sanjay via clarifying questions and treated as fixed — is **Prudently**: an agent-monitored hospital operations fleet for a single hospital, single GCP region, demoed against a scripted flu-outbreak surge. Three specialist agents (Shift Allocation, Supply Chain Resiliency, Chaos & Continuity) sit behind a Coordinator agent that is the sole user-facing entry point, matching his chosen "central orchestrator + specialists" topology.

Sanjay's existing repos (`nerifect-backend`, `nerifect-frontend`, `career-ops`) establish real conventions this project should follow: FastAPI + `google-adk` + `uv` + pytest-with-coverage-gate + Makefile-driven workflow on the backend; Next.js/React/TypeScript/MUI/Tailwind on the frontend; and — confirmed consistently in `nerifect-frontend` and `career-ops` — **`AGENTS.md` as the canonical AI-instruction file, with `CLAUDE.md` kept as a one-line `@AGENTS.md` pointer**. This project deliberately deviates from his usual split-repo habit (monorepo instead), because Devpost judging requires a single code repository with reproducible spin-up instructions — flagged explicitly below for his sign-off, not silently assumed.

## Goal

Ship a submission-ready, GCP-deployed multi-agent system by Aug 31 that (a) satisfies all mandatory hackathon tech requirements, (b) visibly demonstrates all seven Fortified Enterprise Fleet capabilities (real or honestly-labeled local fallback), and (c) tells a coherent, judgeable story through a flu-surge demo scenario — including one visible Model Armor "blocked" moment.

## 1. Repo structure (monorepo — flagged deviation from Sanjay's usual split-repo pattern)

```
prudently/
├── AGENTS.md                      # canonical AI-assistant instructions
├── CLAUDE.md                      # "@AGENTS.md" one-liner, matches nerifect-frontend/career-ops
├── README.md                      # judge-facing: architecture, spin-up, deploy
├── Makefile                       # root orchestrator, delegates into apps/api and apps/web
├── .env.example
├── .gitignore                     # *.tfstate*, .env, service-account*.json
├── docs/
│   ├── architecture.png/.svg      # + editable source
│   ├── day1-probe-results.md      # filled Day 1, drives adapter selection, committed
│   └── demo-script.md             # beat-by-beat video script (§6)
├── apps/
│   ├── api/                       # FastAPI + ADK backend — mirrors nerifect-backend conventions
│   │   ├── pyproject.toml         # uv, python >=3.12
│   │   ├── uv.lock
│   │   ├── app.py
│   │   ├── config.py              # MODEL_REASONING/MODEL_FAST + *_BACKEND adapter selectors
│   │   ├── Makefile
│   │   ├── routes/
│   │   │   ├── coordinator.py     # sole user-facing entry point
│   │   │   ├── sim.py             # simulation clock control (start/pause/speed/reset)
│   │   │   ├── armor_events.py    # feed for dashboard "blocked" panel
│   │   │   └── health.py
│   │   ├── agents/
│   │   │   ├── runtime.py         # shared ADK runtime, modeled on nerifect's services/agents/runtime.py
│   │   │   ├── coordinator/agent.py
│   │   │   ├── shift/{agent.py, burndown.py}      # burndown.py = pure fatigue/overtime math
│   │   │   ├── supply/{agent.py, reorder.py}      # reorder.py = pure consumption/lead-time math
│   │   │   └── chaos/{agent.py, fault_injection.py}
│   │   ├── services/
│   │   │   ├── platform/          # port/adapter layer — see §2
│   │   │   │   ├── registry.py / registry_vertex.py / registry_local.py
│   │   │   │   ├── identity.py / identity_vertex.py / identity_local.py
│   │   │   │   ├── gateway.py / gateway_vertex.py / gateway_local.py
│   │   │   │   ├── armor.py / armor_vertex.py / armor_local.py
│   │   │   │   └── observability.py / observability_vertex.py / observability_local.py
│   │   │   ├── memory.py          # VertexAiMemoryBankService wrapper: CreateMemory, GenerateMemories, search
│   │   │   ├── simclock.py        # Pub/Sub tick publisher/subscriber, SIM_SEED, SIM_SPEEDUP
│   │   │   └── state.py           # Firestore live-state accessors (distinct from Memory Bank)
│   │   ├── tests/{unit,integration}/
│   │   └── evals/                 # agent eval harness, `make eval`, mirrors nerifect
│   └── web/                       # Next.js dashboard — mirrors nerifect-frontend conventions
│       ├── package.json           # Next 16, React 19, TS, MUI v9, Tailwind v4, Jest+RTL, ESLint 9
│       └── src/{app, components/{ui,layout,providers,workspace}, contexts, hooks, lib/{api,types,format,theme}}
├── packages/
│   └── datagen/                   # synthetic data generator, standalone uv package
│       └── datagen/{roster.py, inventory.py, admissions.py, seed.py}
└── infra/
    ├── terraform/
    │   ├── providers.tf, variables.tf, outputs.tf, main.tf
    │   ├── modules/{cloud_run_api, cloud_run_web, firestore, pubsub, iam, secrets}
    │   └── envs/dev/{backend.tf, terraform.tfvars}   # local tfstate — deliberate hackathon-scope choice
    └── scripts/
        ├── day1_capability_probe.sh
        ├── enable_apis.sh
        └── deploy.sh
```

**No `alembic/`/SQLAlchemy** (deviation from `nerifect-backend`): Prudently's state (roster, shifts, inventory, admissions, armor events, chaos results) is document-shaped and needs to be shared with Vertex tooling — Firestore replaces the relational layer entirely. No Cloud SQL needed; keeps infra surface smaller for 11 days.

**Coverage gate, scoped not dropped:** keep `pytest --cov-fail-under=80` and the `make commit` staged-test convention, but scope it to `agents.shift.burndown`, `agents.supply.reorder`, `services.simclock`, `services.platform` (pure logic + adapter contracts) via `[tool.coverage.run] omit = ["tests/*", "infra/*", "packages/datagen/*"]`. Full-repo 80% including ADK orchestration glue isn't worth the schedule risk solo; the math and adapter contracts are exactly where an invisible bug would sink a live demo.

## 2. Capability → GCP mapping, Day-1 verification spike, fallback design

| # | Capability | Confidence | Real backing if confirmed | Fallback (`_local.py`) |
|---|---|---|---|---|
| 1 | Agent Runtime | Confirmed | Vertex AI Agent Engine (`ReasoningEngine`), ADK "Full Integration", `adk deploy agent_engine` | none needed |
| 2 | Memory Bank | Confirmed | `VertexAiMemoryBankService`, `CreateMemory`+`GenerateMemories`, `us` residency, IAM `aiplatform.memoryViewer/Editor` | none needed |
| 3 | Agent Registry | Unverified | Vertex AI Agent Builder registry/catalog resource, if present | Firestore `agent_registry` collection: `{agent_name, version, owner, description, endpoint_uri, capabilities[], approved}`; write restricted to a `platform-admin` SA |
| 4 | Agent Identity | Unverified | Distinct "Agent Identity" product, if surfaced | Per-agent GCP service accounts (`shift-agent-sa@`, `supply-agent-sa@`, `chaos-agent-sa@`, `coordinator-agent-sa@`) via Terraform, least-privilege IAM conditions, ADC only — no downloaded keys |
| 5 | Agent Gateway | Unverified | Apigee "agent gateway" product, if present | ADK `before_tool_callback`/`after_tool_callback` interceptor in the Coordinator: Registry lookup → Armor check → Observability span → per-agent rate-limit/tool-allowlist policy table |
| 6 | Model Armor | Likely real (existing Vertex AI product) | `modelarmor.googleapis.com`, `sanitizeUserPrompt`/`sanitizeModelResponse` | Regex/heuristic injection + PII detector behind the same `ArmorVerdict{blocked, reason, category}` interface, `ARMOR_BACKEND=vertex\|local` |
| 7 | Agent Observability | Unverified as a distinct dashboard | Any "Agent Observability" console surface | OpenTelemetry Python SDK → Cloud Trace + Cloud Logging exporters; spans on `gateway.route`, `agent.invoke`, `armor.check`, `memory.write`; trace ID stamped on every Firestore audit record |

**Day-1 verification spike (literal first build step, before deeper architecture code):**
1. `gcloud auth list && gcloud config get-value project`
2. `gcloud services list --available --filter="name~aiplatform OR name~agent OR name~modelarmor OR name~apigee OR name~discoveryengine"`
3. `curl -s "https://aiplatform.googleapis.com/\$discovery/rest?version=v1" | jq '.resources | keys'` — check for `reasoningEngines`, `memoryBanks`, `agents`, `registries`, `identities`
4. Manual console pass: Vertex AI → Agent Builder / Agent Engine — check for Registry / Identity / Gateway / Observability tabs (console-only surfaces won't show in the discovery doc)
5. `gcloud services enable aiplatform.googleapis.com firestore.googleapis.com pubsub.googleapis.com run.googleapis.com secretmanager.googleapis.com cloudtrace.googleapis.com logging.googleapis.com`
6. Write findings to `docs/day1-probe-results.md` as a binding table (`capability → status/backend/env var`) — this file is committed and referenced by name in the architecture diagram and README; never overclaim a managed product judges can't find.
7. **Region lock (one-way door, decide same day):** Firestore location is immutable post-creation and must match the Agent Runtime region and Memory Bank residency. Lock to **`us-central1`** for Cloud Run/Pub/Sub/Firestore/Reasoning Engine, **`us`** multi-region for Memory Bank, before the first `terraform apply`.

`infra/scripts/day1_capability_probe.sh` implements steps 1–3 and 5; output feeds the probe-results doc.

## 3. GCP infra service selection

- **Cloud Run** (`prudently-api`, `prudently-web`) — required by the track; `gcloud run deploy --source` (no separate Cloud Build/Artifact Registry pipeline needed for hackathon speed).
- **Vertex AI Agent Engine (Reasoning Engine)** — hosts the multi-agent ADK app.
- **Vertex AI Memory Bank** — long-term cross-session narrative memory, scoped per `(agent_name, user)`.
- **Pub/Sub** — the simulation clock (`sim-ticks` topic, `SIM_SEED`/`SIM_SPEEDUP`) and Gateway-intercepted audit-event bus (topology stays hub-and-spoke through the Gateway, not peer-to-peer agent messaging).
- **Firestore** (regional `us-central1`, Native mode) — live operational state: `staff_roster`, `shift_history`, `inventory`, `vendors`, `admissions_timeseries`, `agent_registry`, `armor_events`, `chaos_experiments`. Memory Bank = "what an agent remembers/reasoned about"; Firestore = "what is currently true."
- **Secret Manager** — Gemini API key and any other credentials; no `.json` key files in-repo.
- **Cloud Trace + Cloud Logging** — Observability fallback (OTel export).
- **IAM** — per-agent service accounts (Identity fallback) with custom conditions scoping Firestore/Memory Bank access.

**Architecture decision — single Reasoning Engine, Gateway as an in-process interceptor:** Deploy Coordinator + Shift + Supply + Chaos as **one** ADK multi-agent app (Coordinator as root agent, the three specialists as `AgentTool` sub-agents) to a single Vertex AI Agent Runtime. This is the ADK "Full Integration" tier and realistic solo in the time budget. The Gateway is `before_tool_callback`/`after_tool_callback` hooks wrapping every sub-agent call — a real routing/policy chokepoint without standing up and wiring A2A across four separately-deployed Reasoning Engines (higher risk, lower payoff at this scope). **Stretch, only if ahead of schedule after Day 6:** split Chaos into its own Reasoning Engine invoked via A2A to literally demonstrate the protocol.

## 4. AGENTS.md content outline

Mirror the `nerifect-frontend`/`career-ops` pattern exactly: `AGENTS.md` canonical, `CLAUDE.md` = `@AGENTS.md` plus a note that Claude-specific content goes there only if `AGENTS.md` has no equivalent.

Sections: (1) what Prudently is — one paragraph; (2) agent roster table (file location, ADK role, Memory Bank scope key, Firestore collections read/written); (3) the platform adapter layer — `*_vertex.py`/`*_local.py` split, point at `docs/day1-probe-results.md` as source of truth, list the `*_BACKEND` env vars; (4) local dev commands (`make api-dev`, `make web-dev`, `make seed`, emulator setup); (5) running an agent via ADK CLI (`adk web`, `adk run`); (6) service-account/IAM setup, "never commit a key file" rule; (7) full Makefile target list; (8) testing conventions (coverage scope per §1, `make test`, `make eval`); (9) Terraform apply flow, region-lock note; (10) simulation clock (`SIM_SEED`/`SIM_SPEEDUP`, reset/replay for reshooting the demo).

Root `Makefile` targets: `dev`, `api-dev`, `web-dev`, `seed`, `probe`, `tf-plan`, `tf-apply`, `deploy`, `lint`, `test`, `eval`, `commit`.

## 5. Day-by-day schedule (Aug 20 → Aug 31)

- **Day 0 (Aug 20, tonight):** Plan approved → monorepo skeleton created (empty dirs, `pyproject.toml`, `package.json`, `AGENTS.md`/`CLAUDE.md`, root `Makefile`, `.gitignore`).
- **Day 1 (Aug 21):** Verification spike (§2) run, `docs/day1-probe-results.md` written, region locked. APIs enabled. Terraform foundational resources applied (Firestore DB, Pub/Sub topics, per-agent SAs) — no Cloud Run yet.
- **Day 2 (Aug 22):** Cloud Run modules + Secret Manager. Deploy hello-world API and web to Cloud Run — **first real GCP deployment done today**, not deferred. `packages/datagen` (roster/inventory/admissions with scripted flu surge, seed script). Sim clock skeleton with `DRY_RUN` stub mode to avoid burning Gemini quota during dev.
- **Day 3 (Aug 23):** Shift Agent: `burndown.py` (unit-tested, coverage-gated) + ADK agent wired to Firestore state. Memory Bank wrapper live: `CreateMemory` at simulated-day boundaries, `GenerateMemories` from session events.
- **Day 4 (Aug 24):** Supply Agent: `reorder.py` + ADK agent wired to inventory/vendor state, Memory Bank scoped per SKU/vendor. `services/platform/armor.py` Protocol + `armor_local.py` + `armor_vertex.py` stub.
- **Day 5 (Aug 25):** Coordinator Agent (root, wraps Shift+Supply as `AgentTool` sub-agents). Gateway interceptor (Registry lookup → Armor check → Observability span → policy table). Registry (`registry_local.py`, seeded with all 4 agents) + Identity (per-agent SAs via Terraform, IAM conditions).
- **Day 6 (Aug 26) — MIDPOINT CHECKPOINT:** Full vertical slice (Coordinator + Shift + Supply, no Chaos yet) deployed as one Reasoning Engine, fronted by Cloud Run, dashboard reading live Firestore, sim clock driving a compressed flu-surge sequence end-to-end **on GCP**. If not running on GCP by end of day, cut in this order: (1) fleet-mode fault injection, (2) Chaos agent entirely, (3) Supply's alternate-vendor reasoning depth, (4) dashboard polish → fall back to ADK web UI + console screenshots. **Never cut:** Memory Bank, the Model Armor blocked moment, the Cloud Run deployment, the video itself.
- **Day 7 (Aug 27):** Model Armor end-to-end: poisoned-vendor-email prompt-injection scenario in Supply's ingestion path, blocked *before* reaching LLM context or Memory Bank, `armor_events` persisted, dashboard "BLOCKED" banner. Observability wired: OTel spans, Cloud Trace visible, trace ID on Firestore audit records.
- **Day 8 (Aug 28):** Chaos & Continuity Agent — hospital-domain what-if (through Coordinator/Gateway, not peer-to-peer) + fleet-domain fault injection (kill-agent-mid-task, poisoned Memory Bank write attempt also caught by Armor, Gateway latency injection). Run once for real against the deployed stack, persist to `chaos_experiments`. Never re-run live during recording — dashboard replays the persisted run.
- **Day 9 (Aug 29):** Dashboard build-out (fleet overview, registry list, live charts, armor_events feed, chaos_experiments replay, observability/trace panel — use the `dataviz` skill for chart/color conventions). Architecture diagram finalized, annotated real-vs-emulated per probe results. README spin-up draft.
- **Day 10 (Aug 30):** Clean-clone reproducibility test in a scratch dir (`git clone` → README verbatim → fix breakage). Record the ~4 min demo video (§6). Capture GCP Console B-roll (Cloud Run revisions, Reasoning Engine detail, Firestore data, Cloud Trace waterfall).
- **Day 11 (Aug 31, submit by noon PDT):** Devpost submission (description, tech, learnings), video upload, hosted URL + repo link, final checklist (§7), submit.

## 6. Demo video narrative beats (~4 min)

1. **0:00–0:30** — Problem/value prop: ops manager's view, burnout risk + stockout risk + no fleet coordination today; name the track.
2. **0:30–1:15** — Fleet overview: Coordinator + 3 specialists, Agent Registry entries, calm-baseline Firestore state.
3. **1:15–2:15** — Flu surge, compressed sim clock: Shift Agent flags rising fatigue/overtime burndown → reallocation recommendation; Supply Agent flags accelerating consumption vs. lead time → reorder recommendation; both flow through the Gateway with trace IDs; Memory Bank timeline advancing across "weeks" in seconds.
4. **2:15–2:45** — **Model Armor blocked moment:** poisoned vendor email hits Supply's ingestion path, dashboard shows red "BLOCKED" banner + `armor_events` entry; narrate that the block happened before reaching LLM context or Memory Bank.
5. **2:45–3:20** — Chaos & Continuity, both modes: hospital-domain what-if (mass-casualty influx) routed through Coordinator; fleet-domain fault-injection results (killed agent, attempted memory poisoning also caught by Armor, injected latency) replayed from the persisted run.
6. **3:20–3:50** — Proof of GCP deployment: Cloud Run console, Vertex AI Agent Engine detail page, Cloud Trace waterfall for one full Coordinator→Gateway→Specialist→Armor→Memory Bank chain.
7. **3:50–4:00** — Close: architecture diagram, one honest sentence on which capabilities were real managed GCP products vs. local-emulated fallbacks (a credibility beat, not a weakness to hide).

## 7. Submission-readiness checklist

- **Hosted project URL** — `prudently-web` Cloud Run URL, reachable at submission time.
- **Code repository + README** — monorepo root on GitHub; README verified via the Day 10 clean-clone test; includes `terraform apply`, `make seed`, `make dev`/`make deploy`, region-lock note.
- **Architecture diagram** — annotated real-vs-emulated per `docs/day1-probe-results.md`.
- **~4 min demo video** — per §6, including explicit GCP deployment proof.
- **Text description** (features/tech/data/learnings) — drafted Day 9, referencing the probe-results table honestly in "learnings."

## Verification

- Day 1: `docs/day1-probe-results.md` exists and every capability row is filled with a definitive `confirmed`/`not-found` status.
- Day 2: `curl` the deployed Cloud Run API/web URLs and confirm 200s; this is the first real GCP deployment proof artifact.
- Day 3–5: `make test` passes with the scoped 80% coverage gate on `burndown.py`/`reorder.py`/`simclock`/`platform` adapters.
- Day 6: End-to-end smoke test — trigger the sim clock against the deployed Cloud Run API and confirm Shift/Supply recommendations appear in the dashboard and Memory Bank facts accumulate, all running on GCP (not localhost).
- Day 7: Manually submit the poisoned-vendor-email payload and confirm it's blocked and logged before touching Memory Bank.
- Day 10: Clean-clone reproducibility test must succeed end-to-end from a bare `git clone` following only the README.
