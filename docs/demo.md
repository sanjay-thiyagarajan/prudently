# Demo recording kit

A ~4 minute video, shot by shot. **The fleet acts without being asked, and it remembers** —
everything else is supporting evidence. Lead with it.

---

## Pre-flight (every take, not just the first)

```bash
cd apps/api

# 1. Clean slate — without this the watch stays silent on a replay.
uv run python -m scripts.demo_reset --restock

# 2. Clear what the watch has already seen.
curl -X POST https://prudently-api-jnpvbtwpwa-uc.a.run.app/watch/reset

# 3. Confirm the fleet is up.
curl -s https://prudently-api-jnpvbtwpwa-uc.a.run.app/dashboard/overview \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d['fleet']),'agents', \
    [a['status'] for a in d['fleet']])"
```

Sign in as the manager account, pick a theme and stay in it, leave the tab on Fleet overview.
Open a second tab on the Cloud console's Agent Engine list for beat 6.

---

## Beat 1 · 0:00–0:25 — The problem

**On screen:** Fleet overview at calm baseline.

> A hospital runs on things nobody can watch continuously: who's on shift and how tired, what's
> in the supply room, which vendors can deliver, whether two surgeries just got double-booked.
> Prudently puts eight agents on that, on Google Cloud. Fortified Enterprise Fleet track.

Point at the top strip: 8 of 8 active.

---

## Beat 2 · 0:25–1:05 — The fleet acts on its own

**The beat that wins or loses it. Give it the most time.**

**On screen:** press **Run fleet check now**. Talk while the feed fills in.

> Nobody's asking an agent anything here — I'm just pulling the next check forward. It fires
> only on *transitions*: a SKU crossing par, a nurse crossing fatigue, a credential expiring.
> Still bad because it was bad a minute ago isn't news.

Expand a row with **What it did**.

> The watch woke Shift Allocation about the ICU. Real agent turn, real model call, real tools.

Point at the recalled fact — the money shot:

> This line cites what the watch observed earlier — a real timestamp, not today's snapshot
> restated. Every agent has its own Vertex AI Memory Bank store, written when the watch sees
> something worth remembering, read back by that agent's own recall tool.

---

## Beat 3 · 1:05–1:35 — But it can't act unsupervised

**On screen:** Approvals page, a pending request from the autonomous run.

> The fleet decided *when* to raise this. It didn't get permission to act — the moment a
> decision touches the outside world, it's an approval request.

Switch to your inbox, show the real email, click **Approve**, land on the confirm page.

> Real email from the deployed system. The link renders a page — it doesn't act. The change only
> happens on the button press.

Press it, return to the dashboard, show the status flipped.

> Policy is per-action, manager-editable, and fails closed by default.

---

## Beat 4 · 1:35–2:10 — The topology, and the one real boundary

**On screen:** scroll to the fleet topology.

> One way in. The Coordinator delegates, never answers from its own knowledge. Every internal
> call goes through the Agent Gateway — registry lookup, policy check, trace span — before the
> tool body runs.
>
> Below the dashed line isn't a diagram convention. Medical Representative is a separately
> deployed agent, reached over genuine Agent2Agent at the same public URL any outside client
> would use. Supply Chain has no privileged path to it.

---

## Beat 5 · 2:10–2:50 — Untrusted input gets blocked

**On screen:** Security & resilience page. Send the poisoned vendor message:

> A vendor emails us. Except it's a prompt injection telling the fleet to wire money to a new
> account.

Show the blocked `armor_events` entry.

> Model Armor caught it before a model ever saw it — that's a `before_model_callback`. It
> screens again on the excerpt the model extracts, and that second layer is real: it's what
> caught a paraphrased version of this in testing.

---

## Beat 6 · 2:50–3:30 — Proof it's really on Google Cloud

**On screen:** Cloud console tab.

> Eight Reasoning Engines, each its own service account. Two Cloud Run services. All
> us-central1 — Cloud Run, Firestore, every engine, Memory Bank, KMS, Model Armor.

Click a trace link from the activity feed.

> One trace: Coordinator, the Gateway's decision, the A2A hop, the pre-LLM screen, Model Armor
> returning blocked. Not stitched together after the fact — one trace ID from the blocked event.

---

## Beat 7 · 3:30–4:00 — Close on the honest bit

**On screen:** the architecture diagram.

> The track names seven capabilities. Agent Engine, Memory Bank, and Agent Identity are real
> Google Cloud products, used as such. Model Armor's real too, at the one place with an external
> trust boundary.
>
> Agent Identity almost didn't make that list — `adk deploy`'s CLI has no `--service_account`
> flag, and for most of this build we called that a platform limitation. It wasn't. The SDK
> underneath has a real `service_account` field the CLI just doesn't expose. Every engine now
> runs under its own identity because we checked the layer below the tool.
>
> Registry and Gateway we couldn't find as distinct products, so we built them honestly on ADK
> primitives and said so.
>
> That's Prudently. Eight agents that notice things, remember them, run under their own
> identities, and still ask before they act.

---

## Fallbacks

| If | Then |
|---|---|
| No autonomous rows appear | Watch already saw this state. `demo_reset --restock`, `POST /watch/reset`, try again. Most likely failure. |
| A turn shows **turn failed** | Leave it — a failed turn is recorded, not hidden. Press **Run fleet check now** again. |
| Stock never goes low | N95-001/O2-006 should be low right after `make seed`. Press check a few times, or `demo_reset --restock`. |
| An engine call hangs | Don't narrate over a live `stream_query` — flaky from a laptop. Every beat above drives the UI instead. |
| **Public view** banner | You're signed out — sign in. |

## Submission checklist

- [ ] Hosted URL: the `prudently-web` Cloud Run URL
- [ ] Demo credentials in the submission text
- [ ] Repository access (private — add judges or share via the form)
- [ ] Architecture diagram(s): `docs/architecture.png`, `docs/security-architecture.png`,
      `docs/deployment-architecture.png`
- [ ] Video, per the beats above
- [ ] Text description: features, technologies, data sources, learnings — see
      `docs/devpost-writeup.md`
