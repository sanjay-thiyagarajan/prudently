# Day-1 Capability Probe Results

Project: `prudently-hackathon` (new, dedicated to this hackathon; billing linked to
`My Billing Account 2`, account `01060C-C4994C-BEE645`). Region locked below.

Method: `aiplatform.googleapis.com` REST discovery doc inspection + `gcloud services list
--available` + direct discovery-doc fetch for `modelarmor.googleapis.com` and
`discoveryengine.googleapis.com`. The plan's step 4 (manual Vertex AI console click-through)
could **not** be completed in this session — the Claude-in-Chrome browser extension isn't
connected here. That's a 2-minute manual follow-up (see "Open item" below); it can only
promote a `local` row to `vertex`, never the reverse, so it doesn't block Day 2+ work.

| # | Capability | Status | Backend | Env var | Evidence |
|---|---|---|---|---|---|
| 1 | Agent Runtime | **Confirmed** | `vertex` | n/a (no adapter) | `aiplatform.googleapis.com` discovery doc lists `reasoningEngines` resource |
| 2 | Memory Bank | **Confirmed** | `vertex` | n/a (no adapter) | `aiplatform.googleapis.com` discovery doc lists `memoryBanks` resource |
| 3 | Agent Registry | Not found as a distinct resource | `local` | `REGISTRY_BACKEND=local` | No `registries`/`catalogs` resource in `aiplatform` v1 discovery. `discoveryengine.googleapis.com` (Agent Builder) exists and enabled but its discovery doc only surfaces `projects`/`billingAccounts` at depth 1 — nested `engines`/`dataStores` resources weren't enumerated; possible but unconfirmed home for a real registry. Defaulting to local (Firestore catalog) until/unless the manual console check finds otherwise. |
| 4 | Agent Identity | Not found as a distinct resource | `local` | `IDENTITY_BACKEND=local` | No `identities` resource in `aiplatform` v1 discovery, no distinct "Agent Identity" service in the enableable-services list. Using per-agent GCP service accounts + IAM conditions (Workload Identity pattern) as designed. |
| 5 | Agent Gateway | Not found as a lightweight product | `local` | `GATEWAY_BACKEND=local` | No `gateways` resource in `aiplatform` v1 discovery. `apigee.googleapis.com`/`apigeeconnect`/`apigeeregistry` do exist and are enableable, but Apigee requires org-level provisioning (an Apigee organization, network peering) that is disproportionate for an 11-day solo build and was **not** enabled. Using the ADK `before_tool_callback`/`after_tool_callback` interceptor as designed. |
| 6 | Model Armor | **Confirmed real product** | `vertex` | `ARMOR_BACKEND=vertex` | `modelarmor.googleapis.com` is a real, distinct, enableable API (confirmed via discovery doc — `projects`/`folders`/`organizations` resources, i.e. `sanitizeUserPrompt`/`sanitizeModelResponse`-style templates nested under `projects.locations.templates`). Enabled in this project. |
| 7 | Agent Observability | Not found as a distinct dashboard product | `local` | `OBSERVABILITY_BACKEND=local` | No distinct "Agent Observability" service found. Using OpenTelemetry SDK → Cloud Trace + Cloud Logging exporters as designed (`cloudtrace.googleapis.com`, `logging.googleapis.com` enabled). |

## APIs enabled in `prudently-hackathon`

`aiplatform.googleapis.com`, `firestore.googleapis.com`, `pubsub.googleapis.com`,
`run.googleapis.com`, `secretmanager.googleapis.com`, `cloudtrace.googleapis.com`,
`logging.googleapis.com`, `modelarmor.googleapis.com`.

Not enabled (deliberately, cost/scope reasons): `apigee.googleapis.com` and related — see
Agent Gateway row above.

## Region lock (one-way door — decided today, do not change)

- Cloud Run, Pub/Sub, Firestore (regional, Native mode), Vertex AI Reasoning Engine: **`us-central1`**
- Memory Bank residency: **`us`** (multi-region)

Firestore location is immutable after creation — this lock must hold for the rest of the
build. Set in `infra/terraform/envs/dev/terraform.tfvars` before the first `terraform apply`.

## Post-probe verification (same day, before any agent code was written)

The initial probe above only confirmed capabilities exist in the *global* API discovery doc —
not that they're actually usable in this project/region. Verified with live calls before
committing to Day 3+ agent code:

- **Model IDs, tested via direct `generateContent` calls:** `gemini-3.5-pro` does **not**
  exist anywhere (404 in every location tested: `us-central1`, `us-east1`, `us-east5`, `us`,
  `global`) — only `gemini-3.5-flash` is real. `gemini-3.5-flash` is **not** available via the
  Vertex AI publisher-model endpoint in `us-central1` specifically (404), but works in `us`,
  `us-east1`, `us-east5`, and `global`. **Decision: bypass Vertex publisher-model auth
  entirely and call `gemini-3.5-flash` via the direct Gemini API** (`GOOGLE_GENAI_USE_VERTEXAI=false`),
  using Sanjay's existing paid tier-1 API key, stored in Secret Manager as
  `prudently-gemini-api-key` (never committed). Round-trip tested and confirmed working. This
  is explicitly permitted — the hackathon rules allow "Gemini API or Vertex AI." Both
  `MODEL_REASONING` and `MODEL_FAST` are set to `gemini-3.5-flash` since no distinct
  `-pro`/`-lite` 3.5-generation model was found to exist yet.
- **`reasoningEngines` (Agent Runtime):** confirmed live and queryable (`v1beta1` API, HTTP
  200 empty list) in `us-central1` — **no change to the region lock**, since this was the
  capability the Firestore one-way-door decision actually depended on.
- **`memories` (Memory Bank):** confirmed the real resource shape is a sub-resource of a
  *specific deployed Reasoning Engine* (`reasoningEngines/{engine_id}/memories`), not a
  standalone top-level `memoryBanks` collection as first assumed — matches the resource-name
  pattern in the official docs (`projects/.../reasoningEngines/.../memories/...`). This means
  Memory Bank can't be independently smoke-tested until a real agent is deployed to Agent
  Runtime, which is already Day 3 scope — no schedule change needed, just noting *why* it
  wasn't tested standalone today.

## Open item

Manual Vertex AI console pass (Agent Builder / Agent Engine sections) to check for
console-only Registry / Identity / Gateway / Observability surfaces not visible via API
discovery. Low priority — the local fallbacks are being built regardless (legitimate
defense-in-depth per the Memory Bank docs' own "memory poisoning" mitigation guidance), so
this can only *upgrade* a row from `local` to `vertex`, never block anything. Revisit if
there's slack time after the Day 6 checkpoint.

## Honest framing for judges

Two of seven capabilities (Agent Runtime, Memory Bank) and a third (Model Armor) are backed
by real, distinct, currently-enabled GCP APIs. The remaining four (Registry, Identity,
Gateway, Observability) are implemented as architecturally-honest local emulations behind the
same adapter interface a real product would satisfy — not stubs, but working Firestore-backed
catalog, per-agent IAM/service-account identity, an ADK interceptor-based policy chokepoint,
and OpenTelemetry-instrumented tracing. This is stated explicitly in the demo video close and
the architecture diagram, per the build plan.
