# Prudently

[![CI](https://github.com/sanjay-thiyagarajan/prudently/actions/workflows/ci.yml/badge.svg)](https://github.com/sanjay-thiyagarajan/prudently/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**Agent-monitored hospital operations.** Built for the
[All Things Agentic Hackathon](https://allthingsagentichackathon.devpost.com/),
Fortified Enterprise Fleet track.

Eight agents run a hospital's staffing, supplies, vendor relationships, and surgical schedule.
A Coordinator routes every call through an Agent Gateway to six specialists; a seventh sits
across a real trust boundary, reached over genuine Agent2Agent. A real-time watch acts without
being asked — no scripted timeline, no button to press — and anything with a real-world
consequence still comes back to a human for approval. Patient data is encrypted field-by-field
with Cloud KMS, gated by role-based access control, and every deployed agent runs under its own
dedicated identity.

**Live:**
[dashboard](https://prudently-web-jnpvbtwpwa-uc.a.run.app) ·
[API](https://prudently-api-jnpvbtwpwa-uc.a.run.app/dashboard/overview)

**Architecture:** [`docs/architecture.md`](docs/architecture.md) ·
[topology](docs/architecture.svg) ·
[security](docs/security-architecture.png) ·
[deployment](docs/deployment-architecture.png)

---

## What it does

| | |
|---|---|
| **Acts unprompted** | A fleet watch fires on state *transitions* — a SKU crossing par, a nurse crossing fatigue, an OR double-booking — and opens a real agent turn. Nobody typed anything. |
| **Remembers over time** | Each agent has its own Vertex AI Memory Bank store. Ask Shift whether ICU fatigue has been building and it cites when it started. |
| **Catalogs its own fleet** | The Agent Gateway looks every target up in a Firestore registry on every call, and blocks unregistered, inactive, or unauthorized ones. |
| **Screens untrusted input** | Model Armor screens inbound vendor mail before a model sees it, then re-screens the excerpt the model extracts. |
| **Never acts unsupervised** | Contacting a vendor, notifying staff, notifying a patient, replying to a vendor — all approval-gated, fail-closed, 14-day expiry. |
| **Protects what it holds** | Patient PII encrypted with Cloud KMS, decrypted only for `admin`/`clinician` roles. Every agent its own identity, not a shared one. |
| **Proves what happened** | One Cloud Trace spans Coordinator → Gateway → the A2A hop → Model Armor. |

## Repo layout

- `apps/api` — FastAPI + ADK backend: 8 agents, platform adapters, the fleet watch, every route
- `apps/web` — Next.js dashboard
- `packages/datagen` — synthetic hospital data generator
- `infra/terraform` — GCP infra as code (IAM, secrets, KMS, Cloud Run)
- `docs` — architecture, build plan, demo script

---

## Running it

### 0. Prerequisites

A GCP project with billing, and: `gcloud` (authenticated), `uv`, `node` 20+, `terraform`.

```bash
git clone <this repo> && cd prudently
cp .env.example .env      # then edit — see step 1
```

### 1. One-time manual setup

| Step | How | If you skip it |
|---|---|---|
| **Enable APIs** | `gcloud services enable aiplatform.googleapis.com firestore.googleapis.com run.googleapis.com secretmanager.googleapis.com cloudtrace.googleapis.com logging.googleapis.com modelarmor.googleapis.com pubsub.googleapis.com cloudkms.googleapis.com identitytoolkit.googleapis.com` | Deploys fail at the first API call |
| **Gemini API key** | `gcloud secrets create prudently-gemini-api-key --data-file=-` | Every agent fails on its first model call |
| **Model Armor template** | Template `prudently-vendor-ingest` in `us-central1` with `pi_and_jailbreak`, `malicious_uri`, `rai` filters, via the REST API/SDK (`gcloud model-armor` returns spurious `PERMISSION_DENIED`) | Screening fails closed |
| **Firebase Auth** | Attach a Firebase project, enable Email/Password, create one manager account, put web config in `apps/web/.env.local` | Login wall nobody can pass |
| **Assign a role** | `cd apps/api && uv run python -m scripts.set_user_role <email> admin` | Patient-identity and surgical-schedule routes 403 for everyone |

Gmail approvals are optional (`EMAIL_BACKEND=local` skips sending mail; approvals still work).

### 2. Infrastructure and data

```bash
make tf-apply         # IAM, secrets, KMS key ring, Cloud Run shells
make seed             # roster, shift history, inventory, vendors, admissions
make seed-registry    # required — the Gateway blocks every call without it
make seed-policy      # approval policy defaults
```

Patients and surgical cases seed separately, additively (never overwrites live fleet-watch
state), with real Cloud KMS encryption on every write:

```bash
cd packages/datagen
SIM_SEED=42 GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT uv run python -m datagen.backfill_patients
```

### 3. Deploy the agents

Each agent is its own Reasoning Engine, each under its own service account — set via
`.agent_engine_config.json` in each agent's folder, which `adk deploy` reads automatically.

```bash
cd apps/api
for a in shift inventory supply hr chaos medrep surgical_scheduling; do
  adk deploy agent_engine agents/$a \
    --project=$GOOGLE_CLOUD_PROJECT --region=us-central1 \
    --display_name="$a" --otel_to_cloud \
    --extra_packages=services --extra_packages=config.py
done
```

Coordinator imports its specialists as flattened top-level modules, so every specialist folder
stages alongside it:

```bash
adk deploy agent_engine agents/coordinator \
  --project=$GOOGLE_CLOUD_PROJECT --region=us-central1 \
  --display_name="coordinator" --otel_to_cloud \
  --extra_packages=services --extra_packages=config.py \
  --extra_packages=agents/chaos --extra_packages=agents/hr \
  --extra_packages=agents/inventory --extra_packages=agents/shift \
  --extra_packages=agents/supply --extra_packages=agents/surgical_scheduling
```

Put each engine ID into `.env`, then deploy the two Cloud Run services:

```bash
make deploy
```

> `adk deploy` exiting 0 doesn't mean the agent works — Agent Engine can serve a stale sandbox
> for a short window. Query it again a minute later. Redeploy the Coordinator whenever a
> specialist changes; it carries a frozen copy of each.

### 4. Local development

```bash
make dev               # api on :8000, web on :3000
make lint              # black + pylint, eslint
make test              # pytest, 80% coverage gate
make eval              # scenario evals against the agents
```

From `apps/api/`:

```bash
make verify-deploys ARGS="--query"   # confirm every engine actually works, live
make demo-reset ARGS="--restock"     # clean slate so a replay fires triggers again
```

## Driving a demo

A background loop checks live state every `WATCH_INTERVAL_SECONDS` (90s default) from the
moment the API starts. **Run fleet check now** in the dashboard's top strip pulls the next
check forward on demand. `make demo-reset` clears what the watch has already seen, so a fresh
take fires the same triggers again.

[`docs/demo.md`](docs/demo.md) has the shot-by-shot script.

## Known limits

- **Specialists aren't decoupled from the Coordinator.** They're in-process `AgentTool`s copied
  into its image at deploy time — `coordinator-agent-sa` necessarily holds the union of every
  specialist's grants, including KMS decrypt.
- **Firestore has no per-collection IAM.** Every agent identity is real and independently
  auditable, but `roles/datastore.user` is project-wide; `services/platform/access_control.py`'s
  application-layer allowlist is what actually restricts patient-data access.
- **Registry and Gateway are ADK primitives**, not distinct Google Cloud products. Agent
  Identity used to be on this list too — it isn't anymore.
- **The autonomous watch runs in-process**, not through the Agent Engine transport —
  `stream_query` was flaky from this environment. The deployed Reasoning Engines are real and
  independently verified (`make verify-deploys ARGS="--query"`), just not what serves the live
  demo behavior.
