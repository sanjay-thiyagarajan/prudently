# Prudently

**Agent-monitored hospital operations.** Built for the
[All Things Agentic Hackathon](https://allthingsagentichackathon.devpost.com/),
Fortified Enterprise Fleet track.

Eight agents run a hospital's staffing, supplies, vendor relationships, and surgical schedule.
A Coordinator routes every internal call through an Agent Gateway to six specialists; a seventh
agent sits on the far side of a real trust boundary and is reached over genuine Agent2Agent. The
fleet does not wait to be asked — a real-time watch runs continuously, comparing the ward to how
it left it, and wakes the responsible agent the moment something crosses a line. Anything with a
real-world consequence still comes back to a human for approval. The one domain here with
real-PII-shaped data — a patient's name, date of birth, contact details — is encrypted
field-by-field with Cloud KMS before it ever reaches Firestore, gated behind role-based access
control, with every deployed agent running under its own dedicated identity rather than a
shared one.

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
| **Acts unprompted** | A fleet watch fires on state *transitions* — a SKU crossing its par level, a unit gaining another critically fatigued nurse, an OR double-booking — and opens a real agent turn about it. Nobody typed anything. See the Autonomous activity page. |
| **Remembers over time** | Each agent has its own Vertex AI Memory Bank store on its own Reasoning Engine, scoped per unit or per SKU. Facts are written whenever the fleet watch observes a real change and read back by the agent's own recall tool — ask Shift whether ICU fatigue has been building and it cites when it started. |
| **Catalogs its own fleet** | The Agent Gateway looks every target up in a Firestore registry on every call, and blocks unregistered, inactive, or unauthorized ones before the tool body runs. |
| **Screens untrusted input** | Model Armor screens inbound vendor mail in a `before_model_callback`, so a blocked message never reaches a model at all — then re-screens the excerpt the model extracts. |
| **Never acts unsupervised** | Contacting a vendor, notifying staff, notifying a patient, and replying to a vendor are all approval-gated, configurable per action, fail-closed. Approve links render on `GET` and mutate on `POST`, and expire after 14 days. |
| **Protects what it holds** | Patient name/DOB/contact fields are encrypted with Cloud KMS before every Firestore write, decrypted only for `admin`/`clinician`-role callers, and every deployed agent now runs under its own dedicated identity — not a shared one. |
| **Proves what happened** | One Cloud Trace spans Coordinator → Gateway → the A2A hop → Model Armor. Any blocked event in Firestore pivots straight to it. |

## Repo layout

- `apps/api` — FastAPI + ADK backend: the 8 agents, the platform capability adapters
  (Registry / Identity / Gateway / Model Armor / Observability / Crypto), the fleet watch, and
  every dashboard route
- `apps/web` — Next.js dashboard
- `packages/datagen` — synthetic hospital data generator plus one-off backfill scripts
- `infra/terraform` — GCP infrastructure as code (IAM, secrets, KMS, Cloud Run service shells)
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

Five things cannot be provisioned from Terraform and have to be done once by hand. **Skipping
any of them leaves the app running but visibly broken**, so they are listed with the symptom
you get if you miss one.

| Step | How | If you skip it |
|---|---|---|
| **Enable APIs** | `gcloud services enable aiplatform.googleapis.com firestore.googleapis.com run.googleapis.com secretmanager.googleapis.com cloudtrace.googleapis.com logging.googleapis.com modelarmor.googleapis.com pubsub.googleapis.com cloudkms.googleapis.com identitytoolkit.googleapis.com` | Deploys fail at the first API call; `identitytoolkit` specifically breaks session revocation checking with a silently-swallowed 401 on every authenticated route |
| **Gemini API key** | `gcloud secrets create prudently-gemini-api-key --data-file=-` (paste the key, Ctrl-D) | Every agent fails on its first model call |
| **Model Armor template** | Create a template named `prudently-vendor-ingest` in `us-central1` with the `pi_and_jailbreak`, `malicious_uri`, and `rai` filters. **Use the REST API or the Python SDK, not `gcloud model-armor`** — that subcommand returns spurious `PERMISSION_DENIED` even under project Owner. | Screening fails closed; every vendor message is reported blocked |
| **Firebase Auth** | In the Firebase Console, attach a Firebase project to this GCP project, enable the Email/Password provider, and create one manager account. Put the web config in `apps/web/.env.local`. | The dashboard shows a login form nobody can get past |
| **Assign a role** | `cd apps/api && uv run python -m scripts.set_user_role <email> admin` (also accepts `clinician`, `ops`) | `require_role`-gated routes — patient identity, surgical case status/notify — 403 for every account, including your own |

Gmail approvals are optional. To enable them, turn on 2-Step Verification for the sending
account, create an app password, store it as `prudently-gmail-app-password`, and set
`MANAGER_EMAIL` / `GMAIL_SENDER_EMAIL` in `.env`. Leave `EMAIL_BACKEND=local` to run everything
without sending mail — approvals are still created and still resolvable from the dashboard.

### 2. Infrastructure and data

```bash
make tf-apply         # IAM (including per-agent service accounts and the firebaseauth.viewer
                      # grant check_revoked needs), secrets, Cloud KMS key ring, Cloud Run
                      # service shells. Firestore's location is immutable — us-central1 is a
                      # one-way door.
make seed             # synthetic roster, shift history, inventory, vendors, admissions
make seed-registry    # REQUIRED — the Gateway blocks every call until the registry exists
make seed-policy      # approval policy defaults, including notify_patient_of_status_change
```

`make seed-registry` is not optional. Without it, the Agent Gateway's registry lookup returns
nothing and refuses every specialist call as `blocked_unregistered`, which looks like a broken
Coordinator rather than a missing seed.

Patients and surgical cases are seeded separately, additively, from `packages/datagen` — not
part of `make seed`, so re-running the main seed never overwrites accumulated fleet-watch state:

```bash
cd packages/datagen
SIM_SEED=42 GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT uv run python -m datagen.backfill_patients
```

Patient PII fields are encrypted through the real Cloud KMS key before this script ever writes
to Firestore — a raw console read of the `patients` collection should show ciphertext, never a
name.

### 3. Deploy the agents

Each agent is its own Reasoning Engine, and each runs under its own dedicated service account —
not a shared one. That identity comes from a `.agent_engine_config.json` file already committed
in each agent's folder (`{"service_account": "<agent>-agent-sa@$GOOGLE_CLOUD_PROJECT.iam.gserviceaccount.com"}`);
`adk deploy`'s CLI has no `--service_account` flag, but it reads this file automatically and
merges it into the same config the flag would have set, so no extra step is needed beyond
`make tf-apply` having already created the SAs. Run these from `apps/api/`:

```bash
cd apps/api
for a in shift inventory supply hr chaos medrep surgical_scheduling; do
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
  --extra_packages=agents/supply --extra_packages=agents/surgical_scheduling
```

Put each resulting engine ID into `.env`, then confirm every engine actually runs as its own
identity rather than the platform default (`client.agent_engines.get(...).api_resource.spec
.effective_identity` should read `<agent>-agent-sa@...`, not `service-<project-number>@gcp-sa
-aiplatform-re.iam.gserviceaccount.com`). Then deploy the two Cloud Run services:

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
  whose source is copied into the Coordinator's image at deploy time. Eight Reasoning Engines
  exist, but the Coordinator path runs one process carrying six frozen copies — which means
  `coordinator-agent-sa` necessarily has the union of every specialist's grants, including Cloud
  KMS decrypt. This is an inherent consequence of in-process bundling, not something a different
  IAM setup could fix without re-architecting how Coordinator invokes specialists.
- **Firestore has no native per-collection IAM.** Every per-agent service account holds
  project-wide `roles/datastore.user` — identity separation is real (independent audit trail,
  independent revocation, independent rotation per agent), but it is not per-collection least
  privilege by itself. `services/platform/access_control.py`'s application-layer allowlist is
  the actual mechanism restricting which agents may touch `patients`/`surgical_cases`, now
  backed by a real distinct credential per caller instead of a self-declared one on shared IAM.
- **Registry and Gateway are built on ADK primitives**, not distinct Google Cloud products —
  because the Day-1 probe found no such products. Agent Identity used to be on this list too;
  it isn't anymore, now that every deployed engine runs under its own dedicated service account.
  [`docs/day1-probe-results.md`](docs/day1-probe-results.md) records the original Day-1 findings.
- **The autonomous watch runs agents in-process**, not through the Agent Engine transport. That
  is deliberate: `stream_query` against a deployed engine reset mid-stream on 3 of 4 attempts
  from a laptop, and the manager-initiated path already exercises that transport. The deployed
  Reasoning Engines are independently real and independently verified (`make verify-deploys
  ARGS="--query"`), just not what serves the live autonomous demo behavior.
