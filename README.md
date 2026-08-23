# Prudently

Agent-monitored hospital operations platform, built for the **All Things Agentic Hackathon**
(Fortified Enterprise Fleet track). A Coordinator agent routes through an Agent Gateway to
five specialist agents — Shift Allocation, Inventory Management, Supply Chain Resiliency, HR,
and Chaos & Continuity — plus a Medical Representative agent deployed separately and reached
via genuine Agent2Agent. The dashboard gives a hospital manager an enterprise-grade ops
console (staffing, inventory, payroll, procurement, admissions) with the agents doing the
work underneath, demoed against a scripted flu-outbreak surge at a single hospital.

**Live:**
[prudently-web](https://prudently-web-jnpvbtwpwa-uc.a.run.app) ·
[prudently-api](https://prudently-api-jnpvbtwpwa-uc.a.run.app)

See `AGENTS.md` for the full architecture, agent roster, and build history; `docs/build-plan.md`
for the build plan and demo video script (§6); `docs/day1-probe-results.md` for which of the
seven Fortified Enterprise Fleet capabilities are backed by real GCP products vs.
local-emulated fallbacks.

## Architecture

- **Coordinator** — sole user-facing entry point, routes every specialist call through the
  Agent Gateway (`before_tool_callback`): registry lookup → policy authorization → the real
  tool.
- **Shift Allocation, Inventory Management, Supply Chain Resiliency, HR, Chaos & Continuity** —
  in-process `AgentTool` sub-agents, each also deployed as its own Vertex AI Reasoning Engine.
- **Medical Representative** — deployed and reached separately, over genuine Agent2Agent from
  Supply Chain Resiliency, not through the Gateway. Owns Model Armor screening of inbound
  vendor communications at the one real external-trust boundary in the design.
- **Manager approval workflow** — consequential actions (contacting a vendor, notifying staff)
  are gated behind manager approval by default, configurable per action from the dashboard;
  approve/reject links are emailed and click straight through, no login required.

Every agent's Reasoning Engine ID is in `config.py` / `.env.example`. Region is locked to
`us-central1` across Cloud Run, Reasoning Engine, Firestore, and Memory Bank.

## Repo layout

- `apps/api` — FastAPI + ADK backend: the 7 agents, the platform capability adapters
  (Registry/Identity/Gateway/Model Armor/Observability), and every dashboard route
- `apps/web` — Next.js dashboard
- `packages/datagen` — synthetic hospital data generator (roster, inventory, admissions) plus
  one-off backfill/repair scripts for additive schema changes
- `infra/terraform` — GCP infrastructure as code (IAM, secrets, Cloud Run service shells)
- `docs` — build plan (incl. demo video script) and Day-1 capability probe results

## Setup

Prerequisites: a GCP project, `gcloud` authenticated, `uv`, `node`/`npm`, `terraform`.

```
cp .env.example .env          # fill in your project ID and secrets
make tf-apply                 # provision infra (IAM, secrets, Cloud Run shells)
make seed                     # generate synthetic hospital data into Firestore
make dev                      # run api + web locally (localhost:8000 / localhost:3000)
```

Deploying an agent's Reasoning Engine is a separate step per agent — see "Running / deploying
an agent" in `AGENTS.md` for the exact `adk deploy agent_engine` command per agent (Coordinator's
differs from the others: it needs every specialist folder staged alongside it).

```
make deploy                   # deploy both Cloud Run services (apps/api, apps/web)
```

## Local dev

```
make api-dev   # FastAPI backend only
make web-dev   # Next.js dashboard only
make lint      # pylint (apps/api) + eslint (apps/web)
make test      # pytest, coverage-gated on the pure-logic modules
make probe     # re-run the Day-1 GCP capability probe against your own project
```
