# Architecture

![Prudently architecture](./architecture.svg)

`architecture.svg` is the source of truth; `architecture.png` is a raster of the same file for
the Devpost submission form. Both are also served by the dashboard at `/architecture.svg`. Two
companion diagrams go deeper on one layer each: [`security-architecture.png`](./security-architecture.png)
(every control, perimeter through identity) and
[`deployment-architecture.png`](./deployment-architecture.png) (every deployed component and
real connection between them, including the one genuine Agent2Agent network hop).

## The shape of it in one paragraph

A hospital operations manager talks to exactly one agent. The **Coordinator** — a root ADK
agent on Vertex AI Agent Engine — never answers from its own knowledge; it delegates. Every
internal delegation passes through the **Agent Gateway**, an ADK `before_tool_callback` that
looks the target up in a Firestore agent registry, checks a policy table, opens a Cloud Trace
span, and only then lets the call through. Six specialists sit behind it — the newest,
**Surgical Scheduling**, owns the one domain in this fleet with real-PII-shaped data (patient
name, DOB, contact), encrypted field-by-field with Cloud KMS before it ever reaches Firestore.
One specialist, Supply Chain, reaches a seventh agent — the **Medical Representative** — across
a real trust boundary over Agent2Agent, at the same public agent-card URL any outside client
would use. That agent exists to handle untrusted vendor mail, and **Model Armor** screens
everything it receives before a model sees any of it. Nothing with a real-world consequence
happens without the manager clicking approve in their inbox, and every one of those
approval-gated, RBAC-gated, and encryption-gated routes runs on real, verifiable infrastructure —
real GCP identities, real encryption keys, real audit records, not diagram conventions.

## What runs where

| Component | Deployment | Notes |
|---|---|---|
| Coordinator | Vertex AI Agent Engine, own service account | Root agent, sole user-facing entry point |
| Shift, Inventory, Supply Chain, HR, Chaos, Surgical Scheduling | In-process `AgentTool`s **and** one Reasoning Engine each, each its own service account | Coordinator stages each folder via `--extra_packages`; each engine's own `.agent_engine_config.json` binds it to a dedicated `<agent>-agent-sa` |
| Medical Representative | Own Reasoning Engine, own service account, **and** a Cloud Run A2A mount | `/a2a/medrep` on `prudently-api` |
| `prudently-api` | Cloud Run, `coordinator-agent-sa` | FastAPI: dashboard routes, approvals, the A2A mount, the fleet watch |
| `prudently-web` | Cloud Run | Next.js dashboard |

## Three things the diagram is making a point about

**The Gateway is on the hot path, not beside it.** Every specialist call is intercepted before
the tool body runs. An agent that is not in the registry, or is registered but inactive, or is
not on the caller's allow-list, is refused and the refusal is logged with a trace ID. This is
how the fleet is "cataloged for cross-department use" in a way that has teeth: the catalog is
consulted on every call rather than published and ignored.

**The trust boundary is a network hop, not a diagram convention.** Supply Chain does not have a
privileged path to the Medical Representative. It builds a `RemoteA2aAgent` against the public
agent-card URL and goes out over the internet to a separately deployed agent. Model Armor then
screens inbound content twice: once in a `before_model_callback`, which returns an
`LlmResponse` and so skips the Gemini call entirely, and again on the quoted excerpt the model
itself extracts. The second layer is not belt-and-braces theatre — it is what actually caught a
paraphrase-wrapped injection that the first layer passed.

**Autonomy stops at the approval gate.** The fleet watch decides *when to raise something*; it
never acquired permission to act unsupervised. A trigger wakes an agent, the agent decides, and
the moment that decision touches the outside world it becomes a pending approval in the
manager's inbox. `check_policy()` fails closed, so a task type nobody has configured requires
approval rather than silently auto-sending.

**Agent Identity is real, not a diagram convention either.** Every one of the 8 deployed
Reasoning Engines runs as its own dedicated service account — `effective_identity` confirmed
live for each, not assumed from a Terraform diff. This closed the one Fortified Enterprise
Fleet capability this project had been honestly documenting as unenforced: `adk deploy`'s CLI
has no `--service_account` flag, which earlier notes here took as a hard platform limit, but
the underlying `AgentEngineConfig` API it calls does — reachable through the same
`.agent_engine_config.json` mechanism the CLI already reads per agent folder.

## Where the data lives

- **Firestore** — roster, shift history, inventory, vendors, purchase orders, payroll, surgical
  cases, plus the audit surfaces: `activity_log`, `approvals`, `armor_events`,
  `chaos_experiments`, `autonomous_actions`, `patient_notification_log`, and `fleet_watch/state`.
- **Cloud KMS** — direct field-level encrypt/decrypt on patient `name`/`date_of_birth`/
  `contact_email`/`contact_phone` (never a bulk export or envelope encryption — every protected
  value is a few dozen bytes). Grants scoped to exactly two identities:
  `surgical-scheduling-agent-sa` and `coordinator-agent-sa`.
- **Vertex AI Memory Bank** — one store per agent, on that agent's own Reasoning Engine, scoped
  by `(app_name, user_id)`: Shift by unit, Inventory by SKU. Written whenever the real-time
  fleet watch observes a real change and read back by each agent's own recall tool.
- **Cloud Trace + Cloud Logging** — one trace spans Coordinator → Gateway → Supply Chain → the
  A2A hop → Cloud Run's ASGI handler → the pre-LLM screen → Model Armor. Any `armor_events`
  record can be pivoted straight to that waterfall.

## Region

`us-central1` for Cloud Run, Firestore, every Reasoning Engine, Memory Bank, Cloud KMS, and the
Model Armor template. Firestore's location is immutable after creation, so this was decided
once and has not moved since. See [`day1-probe-results.md`](./day1-probe-results.md) for which
of the seven Fortified Enterprise Fleet capabilities were originally backed by a real, distinct
Google Cloud product and which were built on ADK primitives — Agent Identity has since moved
from the second category into the first.
