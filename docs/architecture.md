# Architecture

![Prudently architecture](./architecture.svg)

`architecture.svg` is the source of truth; `architecture.png` is a pre-rendered raster for
places that can't render SVG. Two companion diagrams go deeper on one layer each:
[`security-architecture.png`](./security-architecture.png)
(every control, perimeter through identity) and
[`deployment-architecture.png`](./deployment-architecture.png) (every deployed component and
real connection, including the one genuine Agent2Agent network hop).

## The shape of it

A hospital operations manager talks to exactly one agent. The **Coordinator** never answers
from its own knowledge — it delegates. Every internal call passes through the **Agent
Gateway**: a Firestore registry lookup, a policy check, a trace span, then the call. Six
specialists sit behind it. The newest, **Surgical Scheduling**, owns the one domain with
real-PII-shaped data — patient name, DOB, contact — encrypted field-by-field with **Cloud KMS**
before it reaches Firestore. One specialist, Supply Chain, reaches a seventh agent — **Medical
Representative** — across a real trust boundary over Agent2Agent, where **Model Armor** screens
everything before a model sees it. Nothing with a real-world consequence happens without a
manager clicking approve.

## What runs where

| Component | Deployment |
|---|---|
| Coordinator | Vertex AI Agent Engine, own service account |
| Shift, Inventory, Supply Chain, HR, Chaos, Surgical Scheduling | In-process `AgentTool`s **and** one Reasoning Engine each, own service account |
| Medical Representative | Own Reasoning Engine, own service account, **and** a Cloud Run A2A mount (`/a2a/medrep`) |
| `prudently-api` | Cloud Run, `coordinator-agent-sa` |
| `prudently-web` | Cloud Run |

## Four things worth knowing

**The Gateway is on the hot path.** Every specialist call is intercepted before the tool body
runs. Unregistered, inactive, or unauthorized — refused, logged with a trace ID.

**The trust boundary is a network hop, not a diagram convention.** Supply Chain builds a
`RemoteA2aAgent` against Medical Representative's public agent-card URL and goes out over the
internet. Model Armor screens twice — once before the model, once on the excerpt it extracts.
The second layer caught a paraphrase-wrapped injection the first one missed.

**Autonomy stops at the approval gate.** The fleet watch decides *when* to raise something, not
whether it may act. `check_policy()` fails closed — an unconfigured task type requires approval.

**Agent Identity is real.** All 8 Reasoning Engines run under their own dedicated service
account — `effective_identity` confirmed live for each. `adk deploy`'s CLI has no
`--service_account` flag, but the `AgentEngineConfig` API underneath it does, reachable through
the same `.agent_engine_config.json` file the CLI already reads per agent folder.

## Where the data lives

- **Firestore** — roster, shifts, inventory, vendors, purchase orders, payroll, surgical cases,
  plus the audit trail (`activity_log`, `approvals`, `armor_events`, `autonomous_actions`,
  `patient_notification_log`, `fleet_watch/state`).
- **Cloud KMS** — direct field-level encrypt/decrypt on patient name/DOB/email/phone. Grants
  scoped to two identities: `surgical-scheduling-agent-sa` and `coordinator-agent-sa`.
- **Vertex AI Memory Bank** — one store per agent, scoped `(app_name, user_id)`: Shift by unit,
  Inventory by SKU. Written on every real change, read back by each agent's recall tool.
- **Cloud Trace + Logging** — one trace spans Coordinator → Gateway → Supply Chain → the A2A
  hop → Model Armor. Any blocked event pivots straight to it.

## Region

`us-central1` for Cloud Run, Firestore, every Reasoning Engine, Memory Bank, KMS, and Model
Armor. Firestore's location is immutable — decided once, hasn't moved.
