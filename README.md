# Prudently

**Agent-monitored hospital operations.** Built for the
[All Things Agentic Hackathon](https://allthingsagentichackathon.devpost.com/),
Fortified Enterprise Fleet track.

Seven agents run a hospital's staffing, supplies, and vendor relationships. A Coordinator
routes every internal call through an Agent Gateway to five specialists; a sixth agent sits on
the far side of a real trust boundary and is reached over genuine Agent2Agent. The fleet does
not wait to be asked — a real-time watch runs continuously, comparing the ward to how it left
it, and wakes the responsible agent the moment something crosses a line. Anything with a
real-world consequence still comes back to a human for approval.

**Live:**
[dashboard](https://prudently-web-jnpvbtwpwa-uc.a.run.app) ·
[API](https://prudently-api-jnpvbtwpwa-uc.a.run.app/dashboard/overview)

**Architecture:** [`docs/architecture.md`](docs/architecture.md) ·
[diagram](docs/architecture.svg)

---

## What it does

| | |
|---|---|
| **Acts unprompted** | A fleet watch fires on state *transitions* — a SKU crossing its par level, a unit gaining another critically fatigued nurse — and opens a real agent turn about it. Nobody typed anything. See the Autonomous activity page. |
| **Remembers over time** | Each agent has its own Vertex AI Memory Bank store on its own Reasoning Engine, scoped per unit or per SKU. Facts are written whenever the fleet watch observes a real change and read back by the agent's own recall tool — ask Shift whether ICU fatigue has been building and it cites when it started. |
| **Catalogs its own fleet** | The Agent Gateway looks every target up in a Firestore registry on every call, and blocks unregistered, inactive, or unauthorized ones before the tool body runs. |
| **Screens untrusted input** | Model Armor screens inbound vendor mail in a `before_model_callback`, so a blocked message never reaches a model at all — then re-screens the excerpt the model extracts. |
| **Never acts unsupervised** | Contacting a vendor, notifying staff, and replying to a vendor are all approval-gated, configurable per action, fail-closed. Approve links render on `GET` and mutate on `POST`. |
| **Proves what happened** | One Cloud Trace spans Coordinator → Gateway → the A2A hop → Model Armor. Any blocked event in Firestore pivots straight to it. |

## Repo layout

- `apps/api` — FastAPI + ADK backend: the 7 agents, the platform capability adapters
  (Registry / Identity / Gateway / Model Armor / Observability), the fleet watch, and every
  dashboard route
- `apps/web` — Next.js dashboard
- `packages/datagen` — synthetic hospital data generator plus one-off backfill scripts
- `infra/terraform` — GCP infrastructure as code (IAM, secrets, Cloud Run service shells)
- `docs` — architecture, build plan and demo script, Day-1 capability probe results

---

## Running it

### 0. Prerequisites

A GCP project with billing, and: `gcloud` (authenticated), `uv`, `node` 20+, `terraform`.

```bash
git clone <this repo> && cd prudently
cp .env.example .env      # then edit — see step 1
```

### 1. One-time manual setup

Four things cannot be provisioned from Terraform and have to be done once by hand. **Skipping
any of them leaves the app running but visibly broken**, so they are listed with the symptom
you get if you miss one.

| Step | How | If you skip it |
|---|---|---|
| **Enable APIs** | `gcloud services enable aiplatform.googleapis.com firestore.googleapis.com run.googleapis.com secretmanager.googleapis.com cloudtrace.googleapis.com logging.googleapis.com modelarmor.googleapis.com pubsub.googleapis.com` | Deploys fail at the first API call |
| **Gemini API key** | `gcloud secrets create prudently-gemini-api-key --data-file=-` (paste the key, Ctrl-D) | Every agent fails on its first model call |
| **Model Armor template** | Create a template named `prudently-vendor-ingest` in `us-central1` with the `pi_and_jailbreak`, `malicious_uri`, and `rai` filters. **Use the REST API or the Python SDK, not `gcloud model-armor`** — that subcommand returns spurious `PERMISSION_DENIED` even under project Owner. | Screening fails closed; every vendor message is reported blocked |
| **Firebase Auth** | In the Firebase Console, attach a Firebase project to this GCP project, enable the Email/Password provider, and create one manager account. Put the web config in `apps/web/.env.local`. | The dashboard shows a login form nobody can get past |

Gmail approvals are optional. To enable them, turn on 2-Step Verification for the sending
account, create an app password, store it as `prudently-gmail-app-password`, and set
`MANAGER_EMAIL` / `GMAIL_SENDER_EMAIL` in `.env`. Leave `EMAIL_BACKEND=local` to run everything
without sending mail — approvals are still created and still resolvable from the dashboard.

### 2. Infrastructure and data

```bash
make tf-apply         # IAM, secrets, Cloud Run service shells. Firestore's location is
                      # immutable — us-central1 is a one-way door.
make seed             # synthetic roster, shift history, inventory, vendors, admissions
make seed-registry    # REQUIRED — the Gateway blocks every call until the registry exists
make seed-policy      # approval policy defaults
```

`make seed-registry` is not optional. Without it, the Agent Gateway's registry lookup returns
nothing and refuses every specialist call as `blocked_unregistered`, which looks like a broken
Coordinator rather than a missing seed.

### 3. Deploy the agents

Each agent is its own Reasoning Engine. Run these from `apps/api/`:

```bash
cd apps/api
for a in shift inventory supply hr chaos medrep; do
  adk deploy agent_engine agents/$a \
    --project=$GOOGLE_CLOUD_PROJECT --region=us-central1 \
    --display_name="$a" --otel_to_cloud \
    --extra_packages=services --extra_packages=config.py
done
```

**The Coordinator's command is different** — it imports its specialists as flattened top-level
modules, so every specialist folder has to be staged alongside it:

```bash
adk deploy agent_engine agents/coordinator \
  --project=$GOOGLE_CLOUD_PROJECT --region=us-central1 \
  --display_name="coordinator" --otel_to_cloud \
  --extra_packages=services --extra_packages=config.py \
  --extra_packages=agents/chaos --extra_packages=agents/hr \
  --extra_packages=agents/inventory --extra_packages=agents/shift \
  --extra_packages=agents/supply
```

Put each resulting engine ID into `.env`. Then deploy the two Cloud Run services:

```bash
make deploy
```

> **`adk deploy` exiting 0 does not mean the agent works.** Agent Engine serves a warm sandbox
> from the previous deploy for a short window, so even a passing smoke test right after a
> deploy can be running old code. Query the engine again a minute later and read the actual
> tool output. Whenever a specialist changes, **redeploy the Coordinator too** — it carries a
> copy of each specialist's source frozen at its own last deploy.

### 4. Local development

```bash
make dev              # api on :8000, web on :3000
make api-dev          # backend only
make web-dev          # dashboard only
make lint             # black + pylint, eslint
make test             # pytest with an 80% coverage gate on the pure-logic modules
make eval             # scenario evals against the agents (needs GCP credentials)
make probe            # re-run the Day-1 capability probe against your own project
```

From `apps/api/`, two more that matter around a demo or a deploy:

```bash
make verify-deploys ARGS="--query"   # confirm every engine actually works, live
make demo-reset ARGS="--restock"     # clean slate so a replay fires triggers again
```

`make verify-deploys` exists because **`adk deploy` prints "Deploy failed" and still exits 0** —
observed live, a mid-deploy connection reset produced exactly that. Deploy outcome has to be
read from the output text and confirmed against the engine's own `update_time`.

## Driving a demo

The fleet watch is what makes the fleet act, and it needs nobody to press anything: a
background loop (`services/watch_loop.py`) checks live state every `WATCH_INTERVAL_SECONDS`
(90s by default) from the moment the API process starts. From the dashboard's top strip:

- **Run fleet check now** — pulls the next check forward immediately instead of waiting out the
  interval on camera. Returns straight away; the agent turns it triggers land in the
  Autonomous activity feed as they finish.

Before a fresh take, `make demo-reset` (see below) clears the watch's memory of what it has
already seen, so the same triggers fire again from a clean slate — `POST /watch/reset` does the
same thing directly.

[`docs/demo.md`](docs/demo.md) has the shot-by-shot script, the pre-flight checklist, and
fallbacks for the things that have actually gone wrong on camera.

## Known limits

Honest ones, because they are the interesting part:

- **The specialists are not decoupled from the Coordinator.** They are in-process `AgentTool`s
  whose source is copied into the Coordinator's image at deploy time. Seven Reasoning Engines
  exist, but the Coordinator path runs one process carrying five frozen copies.
- **Agent Identity does not enforce anything.** Every deployed agent runs as the same shared
  Reasoning Engine service agent; the per-agent service accounts are for local dev. Access
  control lives in the Gateway's policy table, not in identity.
- **Registry, Gateway, and Identity are built on ADK primitives**, not distinct Google Cloud
  products — because the Day-1 probe found no such products.
  [`docs/day1-probe-results.md`](docs/day1-probe-results.md) records what was checked and how.
- **The autonomous watch runs agents in-process**, not through the Agent Engine transport. That
  is deliberate: `stream_query` against a deployed engine reset mid-stream on 3 of 4 attempts
  from a laptop, and the manager-initiated path already exercises that transport.
