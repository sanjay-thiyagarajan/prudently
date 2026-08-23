# Demo recording kit

A ~4 minute video, shot by shot. The one thing worth internalising before recording: **the
strongest claim this project can make is that the fleet acts without being asked, and that it
remembers.** Everything else — the topology, the Gateway, Model Armor, the trace waterfall —
is supporting evidence for that. Lead with it, don't build up to it.

---

## Pre-flight (do this every take, not just the first)

```bash
cd apps/api

# 1. Clean slate. Without this the fleet stays SILENT on a replay — the watch already
#    remembers every SKU as breached, so nothing reads as a new crossing.
uv run python -m scripts.demo_reset --restock

# 2. Clear the watch's memory of what it has already seen (it keeps checking on its own —
#    this only resets what counts as "new").
curl -X POST https://prudently-api-jnpvbtwpwa-uc.a.run.app/watch/reset

# 3. Confirm the fleet is up and every engine is active.
curl -s https://prudently-api-jnpvbtwpwa-uc.a.run.app/dashboard/overview \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d['fleet']),'agents', \
    [a['status'] for a in d['fleet']])"
```

Then, in the browser: sign in as the manager account, set the theme deliberately (light reads
better on most projectors; dark reads better on a dark slide deck — just pick one and stay in
it), and leave the tab on the Fleet overview.

**Have a second tab open** on the Google Cloud console, already signed in, showing the Agent
Engine list. You will need it for beat 6 and fumbling for it on camera is the most common way
these run long.

---

## Beat 1 · 0:00–0:25 — The problem

**On screen:** the Fleet overview at calm baseline.

> A hospital's operations run on three things that nobody can watch continuously: who is on
> shift and how tired they are, what's in the supply room, and which vendors can actually
> deliver. Prudently puts seven agents on that, on Google Cloud. Fortified Enterprise Fleet
> track.

Point at the top strip: the live pulse, fleet 7 of 7 active, signals needing attention.

---

## Beat 2 · 0:25–1:05 — The fleet acts on its own

**This is the beat that wins or loses it. Give it the most time.**

**On screen:** press **Run fleet check now** in the top strip. It returns instantly. Talk while
the autonomous feed fills in.

> Nobody is going to ask an agent anything in this shot. I'm pulling the fleet's next check
> forward, and it's going to notice things by itself — it would have noticed them on its own
> within the next minute or two anyway, this just puts it on camera now.
>
> The watch runs continuously, comparing the ward to the snapshot it kept from the last check.
> It only fires on *transitions* — a SKU crossing its par level, a unit gaining another
> critically fatigued nurse, a credential expiring. Something that's still bad now because it
> was bad a minute ago is not news, and a fleet that emails you about the same box of gloves on
> every single check is worse than no fleet at all.

As rows appear, expand one with **What it did**.

> Here's what actually happened. The watch woke Shift Allocation about the ICU. That's a real
> agent turn — real model call, real tools — and this is its answer.

**Point at the recalled fact explicitly.** This is the money shot:

> And look at this line. It's citing what the watch observed earlier — a real timestamp, not
> today's snapshot restated. That's Vertex AI Memory Bank: every agent has its own store on its
> own Reasoning Engine, written whenever the watch sees something worth remembering and read
> back by that agent's own recall tool. It's telling me when this started, not just where it
> stands now.

---

## Beat 3 · 1:05–1:35 — But it can't act unsupervised

**On screen:** the Approvals page, showing a pending request the autonomous run created.

> The fleet decided *when to raise this*. It did not get permission to act. The moment a
> decision touches the outside world it becomes an approval request.

Switch to your inbox, show the real email, click **Approve**, land on the confirm page.

> That's a real email from the deployed system. The link renders a page — it doesn't act.
> Mail scanners prefetch links, so the actual change only happens on the button press.

Press it, then return to the dashboard and show the status flipped.

> And the policy is per-action and manager-editable. If nobody's configured a task type, it
> requires approval — it fails closed.

---

## Beat 4 · 1:35–2:10 — The topology, and the one real boundary

**On screen:** scroll to the fleet topology.

> One way in. The Coordinator delegates and never answers from its own knowledge. Every
> internal call goes through the Agent Gateway — registry lookup, policy check, trace span —
> and an agent that isn't registered, or isn't active, or isn't on the caller's list, is
> refused before its tool body runs.
>
> Below the dashed line is the part that isn't a diagram convention. Medical Representative is
> a separately deployed agent, reached over genuine Agent2Agent at the same public agent-card
> URL any outside client would use. Supply Chain has no privileged path to it.

---

## Beat 5 · 2:10–2:50 — Untrusted input gets blocked

**On screen:** Security & resilience page.

Send the poisoned vendor message (have this ready to paste):

> A vendor emails us. Except it isn't a vendor — it's a prompt injection telling the fleet to
> wire money to a new account.

Show the blocked `armor_events` entry.

> Model Armor caught it. And note *where*: this is a `before_model_callback`, so the message
> never reached a model at all — not Supply Chain's, not the Medical Representative's. It's
> screened again on the excerpt the model itself pulls out, and that second layer is not
> theatre: it's what actually caught a version of this where the agent paraphrased the message
> before passing it on.

---

## Beat 6 · 2:50–3:30 — Proof it's really on Google Cloud

**On screen:** Cloud console tab.

> Seven Reasoning Engines on Vertex AI Agent Engine. Two Cloud Run services. All us-central1 —
> Cloud Run, Firestore, every engine, Memory Bank, and the Model Armor template. Firestore's
> location is immutable, so that was a one-way door decided on day one.

Back in the dashboard, click a trace link from the activity feed.

> And this is one trace. Coordinator, the Gateway's routing decision, the A2A hop, Cloud Run
> receiving it, the pre-LLM screen, Model Armor returning blocked. Not stitched together
> afterwards — one trace ID, pivoted to straight from the blocked event in Firestore.

---

## Beat 7 · 3:30–4:00 — Close on the honest bit

**On screen:** the architecture diagram (`/architecture.svg`).

> Last thing, and it's the part I'd want to be asked about. The track names seven platform
> capabilities. Two of them — Agent Engine and Memory Bank — are real Google Cloud products and
> we use them as such. Model Armor is real and we use it at the one place in this design that
> actually has an external trust boundary.
>
> The other three — Agent Registry, Agent Identity, Agent Gateway — we went looking for and
> could not find as distinct products, so we built them on ADK primitives and wrote down
> exactly what we checked. The Gateway is a `before_tool_callback` on the hot path. The
> registry is a Firestore catalog it consults on every call. Identity resolves metadata and
> enforces nothing, because on Agent Engine every agent runs as the same service agent — so
> access control lives in the Gateway's policy table instead, which is where we say it lives.
>
> That's Prudently. Seven agents that notice things, remember them, and still ask before they
> act.

---

## Fallbacks

Things that have actually gone wrong, and what to do on camera.

| If | Then |
|---|---|
| **Run fleet check now** produces no autonomous rows | The watch has already seen this state. Run `demo_reset --restock`, `POST /watch/reset`, and press it again. This is the single most likely failure. |
| A turn shows **turn failed** | Leave it on screen and say so — a failed turn is recorded rather than hidden, and that's a feature. Press **Run fleet check now** again. |
| Stock never goes low | The two seeded-tight SKUs (N95-001, O2-006) should already be low/critical right after a fresh `make seed` — if they're not, the ongoing consumption noise is gradual by design; press **Run fleet check now** a few times before the take, or run `demo_reset --restock` and start from a lower baseline deliberately. |
| An engine call hangs | Don't narrate over a live `stream_query`. Three of four bare calls reset mid-stream from a laptop; the dashboard path is polling-based and doesn't have this problem, which is why every beat above drives the UI rather than a terminal. |
| The dashboard shows a **Public view** banner | You're signed out. Staff-level rows are withheld from anonymous callers by design — sign in. |

## Submission checklist

- [ ] Hosted URL: the `prudently-web` Cloud Run URL
- [ ] **Demo credentials in the submission text** — the dashboard opens on a login wall and a
      judge who can't get past it sees nothing
- [ ] Repository access — it is private; add the judges or share via the form
- [ ] Architecture diagram: `docs/architecture.png`
- [ ] Video, per the beats above
- [ ] Text description: features, technologies, data sources, learnings. The genuinely good
      "learnings" material is in `AGENTS.md` — the coverage gate that hung rather than failed,
      the `requirements.txt`-vs-`pyproject.toml` asymmetry, the stale warm sandbox that makes
      `exit 0` untrustworthy, and the redaction gap on the public feed.
