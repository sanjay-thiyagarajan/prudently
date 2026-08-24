# Prudently

**The fleet that never waits to be asked.**

![Prudently architecture — Coordinator, Agent Gateway, six specialists, one real A2A trust boundary, and a real-time fleet watch](./architecture.png)

## Inspiration

A hospital runs on things nobody can watch every minute: who's on shift and how tired they are,
what's left in the supply room, which vendors can actually deliver, whether two surgeries just
got double-booked. Those are slow-burning signals a chatbot is bad at and a fleet of specialists
is good at. The Fortified Enterprise Fleet track's seven capabilities — Registry, Identity,
Gateway, Model Armor, Observability, Agent Engine, Memory Bank — read like a real hospital IT
checklist. We built for that checklist, not around it. And the clearest way to prove
"agent-*monitored*," not just "agent-*assisted*," was to make the fleet act before anyone asks.

## What it does

Eight agents run a hospital's staffing, supplies, vendor relationships, and surgical schedule,
live. A **Coordinator** never answers from its own knowledge — every call passes through an
**Agent Gateway**: registry lookup, policy check, trace span, then the call. Behind it: **Shift
Allocation**, **Inventory Management**, **Supply Chain Resiliency** (real generated purchase
orders), **HR** (Shift's escalation target), **Chaos & Continuity** (fault injection against the
fleet itself), and **Surgical Scheduling** — the newest, and the one domain with real-PII-shaped
data. It detects OR/surgeon double-bookings, resolves them, and notifies the patient only with
consent and only after approval; name, DOB, and contact are encrypted field-by-field with
**Cloud KMS** before they reach Firestore. A seventh agent, **Medical Representative**, is
reached only over genuine **Agent2Agent** — the one real external trust boundary — where **Model
Armor** screens every inbound message twice: once before a model sees it, again on the excerpt
the model extracts, because a paraphrased injection slipped past the first layer in testing.

The fleet doesn't wait to be asked. A real-time watch runs against live Firestore state — no
scripted timeline — and wakes the responsible agent the instant something crosses a line.
Anything consequential still comes back to a human: a real HTML email with an approve/reject
link that expires in 14 days, governed by a fail-closed policy. Every agent remembers across
time in its own Vertex AI Memory Bank store. One Cloud Trace span follows every request end to
end, so a blocked event pivots straight to the real waterfall behind it.

None of this is theoretical about who sees what. Firebase custom claims gate `admin`/`clinician`/
`ops`; a patient's decrypted identity is the one thing `ops` never sees. All eight Reasoning
Engines run under their own dedicated identity, not a shared one — Cloud KMS decrypt is scoped
to exactly two of them.

## How we built it

Google ADK for every agent, each its own Vertex AI Reasoning Engine, behind FastAPI and Next.js
on Cloud Run. Firestore holds live state and every agent's audit trail. Coordinator wraps six
specialists as in-process `AgentTool`s. Medical Representative is reached via ADK's `to_a2a()`,
mounted on the same Cloud Run service as the dashboard API. Registry and Gateway are built
honestly on Firestore and ADK primitives — we looked for real GCP products behind each and
documented what we found when we didn't.

Agent Identity started in that same bucket, on a real finding: `adk deploy`'s CLI has no
`--service_account` flag, so every engine ran as one shared identity. What closed it was not
trusting that CLI limitation as a platform one — the SDK underneath (`AgentEngineConfig`) has a
real `service_account` field, reachable through a config file the CLI already reads per agent.
All eight engines now run under their own identity, confirmed live via `effective_identity`, and
Cloud KMS's patient key is scoped to exactly two of them instead of the one shared identity
everyone used to share.

Patient PII gets direct Cloud KMS field-level encryption — every value protected is a few dozen
bytes, well inside a symmetric key's limit, so envelope encryption would add nothing. The
autonomous watch runs its agent turns *in-process*, not through the Reasoning Engine transport
— `stream_query` was flaky from this environment, and the backend already runs the same agent
objects the engines serve. It didn't start this way: for most of the build the fleet only acted
on a scripted 21-day sim clock. The day before submission we tore that out for a background loop
that checks live state on its own, every 90 seconds.

## Challenges we ran into

Nearly every hard bug had the same shape: something that looked like success while the real
thing quietly failed. `adk deploy` exits clean and can still serve a stale sandbox before a cold
start reveals the real error. A misconfigured Memory Bank region silently killed the entire
autonomy pipeline with no error anywhere. A `shift_history` doc-ID collision collapsed 21 days of
fatigue history into one document per person — the flagship risk feature had likely never
actually flagged anyone, in production, until the document count didn't add up.

Hours before submission, a scaling bug in the ambient-consumption tick crashed every SKU to
critical within five minutes of deploying — **26 real approval emails** landed in an actual
inbox before we caught it in Firestore rather than the deploy log. Fixed, redeployed, and forced
one clean cycle: **exactly 11 triggers**, matching live reality precisely.

The very last bug was self-inflicted: a session-revocation improvement made one extra API call
Cloud Run's own identity had no permission for. Every authenticated route 401'd for genuinely
signed-in users — invisibly, because the exception handler swallowed the real cause instead of
logging it. Found from a plain user report, root-caused from Cloud Run's own logs, fixed with
one scoped IAM grant.

## Accomplishments we're proud of

A genuine Agent2Agent hop, confirmed end to end in one Cloud Trace waterfall, not a function
call wearing an A2A costume. A Model Armor boundary whose second layer actually earned its keep
— it caught what the first layer missed. A fleet that proves itself unprompted: real seed data
already critical at plain seed time, the watch wired to act on exactly that. And the one we're
proudest of — refusing to accept our own documentation that Agent Identity "can't be enforced on
this platform." That was true of a CLI flag, not the platform.

## What we learned

"The deploy succeeded" and "the deployed thing works" are different claims, and almost every
real bug here lived in that gap — which is why nearly every milestone ends with a live check,
not a trusted exit code. Pure-logic modules pulled out of ADK orchestration glue paid for
themselves: a same-day rewrite of the autonomy mechanism shipped with 97% coverage and zero
regressions. And a system built to survive being replayed — deterministic seeding, edge-triggered
logic — is the same discipline that makes it trustworthy enough to run unattended at all.

## What's next

A fifth trigger axis for vendor reliability. Real contact information once this moves past
synthetic data. A distributed lock around the watch loop before this runs on more than one Cloud
Run instance. And the one honest gap worth stating plainly: Firestore has no per-collection IAM,
so patient-data access is enforced at the application layer, not by IAM alone — a real, useful,
but not cryptographic boundary. Closing it fully means a bigger architectural call than a
hackathon week has room for.
