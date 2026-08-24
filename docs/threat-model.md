# Threat model

Every finding below is confirmed against the actual code (file:line), not assumed. STRIDE
categories are noted per finding. Severity is rated against what the system will hold once Part D
(surgical scheduling, real-PII-shaped patient data) ships — several findings are rated higher
than their *current* impact, because today's data model has no PII in it at all
(`packages/datagen/datagen/roster.py`'s `StaffMember` carries no email/phone/SSN; every name is
procedurally generated, e.g. `f"{role.title()} {unit[:2].upper()}-{i:02d}"` → "Nurse IC-01"). That
absence is the only reason this system is low-risk *today*; it is not a control, and it stops
being true the moment `patients`/`surgical_cases` exist. This document is written assuming they
do.

Status column: **Fixed** (shipped in the same change as this document), **Planned** (designed,
not yet shipped), **Accepted** (a documented, deliberate residual risk with its reasoning).

---

## 1. Unauthenticated agent-turn triggers

| | |
|---|---|
| **Component** | `app.py` — `/a2a/medrep` mount; `routes/watch.py` — `POST /watch/check-now`, `POST /watch/reset` |
| **STRIDE** | Spoofing, Denial of Service, Elevation of Privilege |
| **Evidence** | `infra/terraform/modules/cloud_run_api/main.tf:56-62` grants `roles/run.invoker` to `allUsers` on the whole `prudently-api` service — the A2A mount included. It is a Starlette sub-app (`app.py`'s `to_a2a(...)`) with no `Depends()` of any kind; FastAPI's auth system doesn't touch it. `routes/watch.py`'s `check-now`/`reset` have no `Depends` either. |
| **Impact** | Anyone on the internet who has (or discovers) the URL can drive real Gemini/Vertex AI calls, real Model Armor calls, and — via Medical Representative's `send_vendor_reply` → `perform_or_request` — a real approval-request email to the manager's inbox, with no rate limit (§7) to bound the cost. `POST /watch/reset` can also grief a live demo by wiping the fleet's edge-triggered memory mid-session. |
| **Mitigating factor** | Content is still screened: Model Armor's dual-layer defense (`agents/medrep/agent.py`'s `_pre_llm_vendor_screen` + `screen_vendor_message`) means a malicious *payload* is still caught even though the *request itself* isn't access-controlled. This bounds the "what can it make the agent do" risk but not the cost/DoS risk. |
| **Fix** | `routes/watch.py`'s two mutating routes → `require_firebase_auth`. The A2A mount gets a shared-secret header (`X-A2A-Shared-Secret`, Secret-Manager-held) checked before the request reaches the ADK app — the pragmatic middle ground between "fully open" and mTLS infrastructure Agent Engine doesn't support. |
| **Status** | Fixed and verified live: `POST /watch/check-now`/`reset` and `POST /a2a/medrep` without the header all return 401 against the deployed service; `/dashboard/overview` and `/watch/status` (intentionally public) still return 200. |

## 2. Public routes with no auth and no redaction

| | |
|---|---|
| **Component** | `routes/traces.py` (both routes), `routes/inventory.py` (3 GET routes), `routes/vendors.py` |
| **STRIDE** | Information Disclosure |
| **Evidence** | None of these routes carry a `Depends(require_firebase_auth)` or `Depends(optional_firebase_auth)`, confirmed by reading every route file. `routes/traces.py` returns raw Cloud Trace span `labels` and raw Cloud Logging entry text with no filtering. `email_gmail.py:34-36` sets `email.to`/`email.subject` as span attributes on every `email.send` span — `to` is `approver_email` (defaults to the real `manager_email`, `config.py:81`), `subject` is the **unredacted** original subject, which for HR/Shift task types contains a staff member's name (`agents/hr/agent.py:110`, `agents/shift/agent.py:95`). |
| **Impact** | Any `trace_id` (itself public via `activity_log`, see finding 3) lets an anonymous caller pull the real manager email address and an unredacted, name-bearing subject straight out of `GET /traces/{trace_id}` — bypassing every redaction path built for `/dashboard/overview` and `/agents/{name}` entirely, through a route those redaction efforts never touched. `routes/inventory.py`'s PO endpoints expose `unit_cost`/`total_cost` with no gate, inconsistent with `payroll`'s hard auth requirement on the same class of financial data. |
| **Fix** | `traces.py`, `inventory.py`, `vendors.py` GET routes → `require_firebase_auth`, matching the precedent already set by `payroll.py`/`staff.py` for anything beyond the judge-facing overview. |
| **Status** | Fixed and verified live: all five routes return 401 unauthenticated against the deployed service. |

## 3. Redaction gap: `activity_log[].summary`

| | |
|---|---|
| **Component** | `services/redaction.py`'s `redact_agent_detail()`, consumed by `routes/agents.py:58` |
| **STRIDE** | Information Disclosure |
| **Evidence** | `redact_agent_detail()` (`services/redaction.py:165-184`) redacts `live_state`, `autonomous_actions`, `approvals`, and `chaos_experiments` for anonymous callers — it never touches the `activity_log` key also present in the same response payload. `log_activity(...)`'s `summary` argument is populated directly from each tool's `subject` string (`services/platform/approvals.py`'s `_request_approval`, `perform_or_request`, `resolve_approval`), and those subjects embed staff names verbatim for HR and Shift task types. |
| **Impact** | `GET /agents/hr_agent` or `GET /agents/shift_allocation_agent`, called anonymously, returns exactly the per-employee data class the `approvals` list was specifically redacted to hide — through a sibling field on the same response the redaction module's own docstring cites as the reason it exists. |
| **Fix** | Extend `redact_agent_detail()` to genericize `activity_log[].summary` for anonymous callers using the same per-task-type approach already applied to `approvals[].subject`. |
| **Status** | Fixed, unit-tested (`tests/unit/test_redaction.py`).|

## 4. Approval tokens: no expiry, no rate limiting

| | |
|---|---|
| **Component** | `services/platform/approvals.py` (`_request_approval`, `resolve_approval`), `routes/approvals.py` |
| **STRIDE** | Tampering (of intent, not the token itself), Denial of Service |
| **Evidence** | `token = secrets.token_urlsafe(24)` (`approvals.py:123`) — 192 bits of CSPRNG entropy, not brute-forceable by any practical means. But no record (`services/state.py`'s `write_approval`/`update_approval`) carries a TTL, and `resolve_approval` checks only `record["status"] != "pending"` — never an age. A token is a valid, permanent bearer capability until someone clicks it, however long that takes. No rate limiting exists anywhere in the stack (confirmed absent from `pyproject.toml`, `app.py`, and Cloud Run config — the 3-instance scaling cap in `main.tf:43-46` is a cost ceiling, not a throttle). |
| **Impact** | A token leaked from a compromised mailbox, a forwarded email, or an intermediate mail-security scanner's log remains exercisable indefinitely. Nothing throttles repeated hits against `/approvals/{token}/*`, `/watch/*`, or the A2A mount. |
| **Mitigating factor** | `resolve_approval` is confirmed idempotent (`approvals.py:249-255`) — a replay after the first decision is a no-op, not a re-send. GET is non-mutating by design specifically to tolerate mail-scanner link-prefetching. |
| **Fix** | Add `expires_at` (14 days) to the approval record, checked by `resolve_approval` and the confirm-page GET, rendering a clear "expired" state. Add `slowapi`-based per-IP rate limiting on every public POST and a looser per-uid limit on authenticated routes. |
| **Status** | Fixed — and not on the first attempt. Two real bugs found by testing live, not by inspecting the code: (1) slowapi's default key function (`request.client.host`) doesn't stay constant per real client behind Cloud Run's load balancer, so a 25-request burst against a deployed, decorated route never triggered a single 429 — fixed by keying on `X-Forwarded-For`'s first hop instead (`services/platform/rate_limit.py`). (2) Even after that fix, a burst using a *different* candidate token on every request — the actual brute-force/scanning shape this limit exists to blunt — still never triggered a 429, because slowapi's `Limiter` defaults to `key_style="url"`, folding the literal `{token}` path segment into the bucket key so every distinct token got its own fresh bucket. Fixed with `key_style="endpoint"`, scoping the bucket to the route itself. Verified live post-fix: 20 requests through, then 429s, with a varying token on every request. |

## 5. No session revocation; client-only sign-out

| | |
|---|---|
| **Component** | `services/auth.py` (`require_firebase_auth`, `optional_firebase_auth`), `apps/web/src/contexts/AuthContext.tsx` |
| **STRIDE** | Elevation of Privilege (via a token that should be dead but isn't) |
| **Evidence** | `verify_id_token(id_token)` (`services/auth.py:51`) is called with no options — no `check_revoked=True`. Grepping the whole backend for `check_revoked`/`revoke` returns zero hits. `AuthContext.tsx`'s `signOut()` (lines 46-48) calls only the client-side `firebaseSignOut(auth)` — no backend call, no `revoke_refresh_tokens`. Firebase's client SDK uses default `browserLocalPersistence` (no `setPersistence()` call found anywhere in `apps/web/src`), so a refresh token written to IndexedDB survives indefinitely until explicit sign-out or revocation. |
| **Impact** | Disabling a user in the Firebase Console, or any attempt to force a session dead (a stolen device, a compromised token), has no effect on an already-issued ID token until its own short natural expiry (~1hr) — and even then the refresh token can mint a new one indefinitely, since nothing ever revokes it. There is no way to kill a session from another device. |
| **Fix** | `check_revoked=True` on every `verify_id_token` call. New `POST /auth/sign-out-everywhere` (authenticated) calling `firebase_admin.auth.revoke_refresh_tokens(uid)` server-side, wired to a real control in `Sidebar.tsx`. Client-side 15-minute idle timeout as a clinical-system-standard belt-and-suspenders measure. |
| **Status** | Fixed and verified live: `check_revoked=True` active, `/auth/sign-out-everywhere` deployed, idle timeout wired client-side. |

## 6. No authorization model (RBAC)

| | |
|---|---|
| **Component** | `services/auth.py` — every route gated by `require_firebase_auth` alone |
| **STRIDE** | Elevation of Privilege |
| **Evidence** | `require_firebase_auth` returns only `decoded["uid"]` (`services/auth.py:55`) — no custom claims are read or checked anywhere. Every successfully-authenticated caller is treated identically. |
| **Impact** | Fine for a one-account demo. The moment `patients`/`surgical_cases` (Part D) exist, this means anyone who can sign in — including a future second account added for any reason — sees every patient's identity with no least-privilege boundary at all. |
| **Fix** | Firebase custom claims (`role: "admin" \| "clinician" \| "ops"`), set via a one-time admin script. `require_role(*roles)` built on top of `require_firebase_auth`. Patient-identity-bearing responses require `admin`/`clinician`; an `ops`-role caller sees case/status/OR data without the patient's decrypted name. |
| **Status** | Fixed. `require_role("admin", "clinician")` gates `routes/surgical_scheduling.py`'s `GET /cases/{case_id}` (the one route that returns decrypted patient identity), plus its status-update and notify routes; `GET /cases` (schedule + conflicts, no patient identity) stays on plain `require_firebase_auth`, giving an `ops`-role caller the schedule without who's on it — the least-privilege cut this finding called for. |

## 7. Unescaped HTML interpolation on a public page

| | |
|---|---|
| **Component** | `routes/approvals.py`'s `_confirm_page` |
| **STRIDE** | Tampering (stored/reflected XSS) |
| **Evidence** | `_confirm_page` builds `HTMLResponse` via raw f-string interpolation of `record['requested_by']`, `record['subject']`, and `record.get('recipient_label', record['to'])` (lines 36-39) with no escaping. `subject` for Medical Representative approvals derives from `send_vendor_reply(vendor_name, message)` (`agents/medrep/agent.py:139-148`), where `vendor_name` is model-supplied text that has passed Model Armor's injection/jailbreak/malicious-URI screening but was never specifically checked for HTML-significant characters — Model Armor's filters target prompt injection and malicious URIs, not markup. |
| **Impact** | A crafted vendor name or subject that survives Model Armor screening (a narrower bar than "contains no `<`/`>`/quote characters") could inject markup/script into a fully public, unauthenticated page. |
| **Fix** | `html.escape()` on every interpolated value before building the response — zero new dependency, stdlib only. |
| **Status** | Fixed. |

## 8. CORS wildcard

| | |
|---|---|
| **Component** | `app.py:68-73` |
| **STRIDE** | Information Disclosure |
| **Evidence** | `CORSMiddleware(allow_origins=["*"], allow_methods=["GET","POST","PUT"], allow_headers=["*"])`, no `allow_credentials`. |
| **Impact** | Bearer-token auth means this isn't classic cookie-CSRF exposure, but any website can read every public GET response cross-origin and issue unauthenticated POSTs cross-origin to the endpoints findings 1/4 already cover — wildcard CORS removes the browser same-origin speed bump on top of routes that should be access-controlled regardless. Becomes materially worse once patient data exists behind any route that's under-gated. |
| **Fix** | Explicit origin allowlist (the deployed dashboard URL + localhost dev origins), not `"*"`. |
| **Status** | Fixed and verified live: browser-origin behavior unchanged for the deployed dashboard; an arbitrary third-party origin is no longer permitted. |

## 9. Blast radius of the shared Reasoning Engine identity

| | |
|---|---|
| **Component** | Every deployed Reasoning Engine (`infra/terraform/modules/iam/main.tf`) |
| **STRIDE** | Elevation of Privilege |
| **Original evidence** | Every agent ran as the same Google-managed `service-<project-number>@gcp-sa-aiplatform-re.iam.gserviceaccount.com` — `adk deploy agent_engine`'s CLI has no `--service_account` flag, which earlier notes in this codebase (and this finding) took as "Agent Engine has no per-agent service account support." That conclusion was wrong: the CLI has no flag, but the underlying API it calls (`vertexai._genai.types.common.AgentEngineConfig`) has a real `service_account` field, and `adk deploy`'s own `.agent_engine_config.json` mechanism merges arbitrary config keys into that call before it's made. |
| **Original impact** | A compromised tool call in any one agent inherited the full shared-identity grant set: read/write on every Firestore collection, Model Armor, Cloud Trace, and — once Part D shipped — `roles/cloudkms.cryptoKeyEncrypterDecrypter` on the patient-PII key. |
| **Fix, actually applied** | Each of the 8 deployed Reasoning Engines now runs as its own dedicated per-agent service account (`infra/terraform/modules/iam` — `<agent>-agent-sa`, already provisioned but never bound before this), set via a new `.agent_engine_config.json` in each agent's folder and picked up automatically by the existing `adk deploy agent_engine` command — no new deploy tooling. Verified live: every engine's `effective_identity` (`client.agent_engines.get(...)`) now reads back as its own SA, not the shared one; a live KMS decrypt through `surgical_scheduling_agent` and a live Model Armor screen through `medical_representative_agent` both confirmed working under the new identities before the shared identity's grants were removed. The Cloud KMS patient-PII key's accessor list now names exactly two identities — `surgical-scheduling-agent-sa` and `coordinator-agent-sa` — not the shared Reasoning Engine service agent, which as of this fix has **zero** grants on this project's Firestore, Model Armor, Cloud Trace, or Secret Manager resources. |
| **Two honest residual limits, distinct from the identity problem this finding was about** | (1) Firestore has no native per-collection IAM, so `roles/datastore.user` is still project-wide on every per-agent SA — identity separation is real now (independent audit trail, independent revocation, independent rotation per agent), but it does not by itself give per-collection least privilege; `services/platform/access_control.py`'s application-layer allowlist remains the actual mechanism restricting *which* agents may touch `patients`/`surgical_cases`, now backed by a real distinct identity instead of a self-declared one riding on a shared credential. (2) `coordinator-agent-sa` necessarily keeps broad access — Coordinator's "frozen copies" architecture executes every specialist's tool code in-process inside Coordinator's own Reasoning Engine (and, separately, inside `prudently-api`'s Cloud Run container, which also runs as `coordinator-agent-sa`), so its identity has to be able to do anything any specialist it wraps can do. This is an inherent consequence of the in-process bundling design, not something a different IAM setup could fix without re-architecting how Coordinator invokes specialists. |
| **Status** | **Fixed.** Per-agent Agent Identity is real, live, and verified for all 8 engines; the shared-identity blast radius this finding described no longer exists. The two residual limits above are separate, smaller, and already independently mitigated (`access_control.py` for the first, an inherent architectural tradeoff for the second) — noted here for honesty, not left implicit. |

## 10. No CI, no dependency scanning

| | |
|---|---|
| **Component** | Repository-wide |
| **STRIDE** | Tampering (supply chain) |
| **Evidence** | No `.github/` directory exists (confirmed by direct listing). No Dependabot/Renovate config anywhere. `apps/api/pyproject.toml` lists no SAST/dependency-audit tool (`pip-audit`, `safety`, `bandit` all absent). `make lint`/`make test` exist and are real, but nothing runs them automatically on a PR — enforcement is entirely manual/local. |
| **Impact** | A vulnerable dependency (backend Python or frontend npm) can sit unnoticed indefinitely; a regression can be merged without the existing test/lint gates ever running. |
| **Fix** | `.github/workflows/ci.yml` running `make lint`/`make test` on every PR; `.github/dependabot.yml` for npm + pip, weekly. |
| **Status** | Fixed. |

---

## Prioritized remediation table

| Priority | Finding | Fix location |
|---|---|---|
| Critical | 1 — Unauthenticated agent-turn triggers | `routes/watch.py`, `app.py` A2A shared secret |
| Critical | 6 — No RBAC | `services/auth.py` `require_role`, Part D routes |
| High | 2 — Public traces/inventory/vendors | `routes/traces.py`, `routes/inventory.py`, `routes/vendors.py` |
| High | 3 — `activity_log` redaction gap | `services/redaction.py` |
| High | 5 — No session revocation | `services/auth.py`, `AuthContext.tsx`, new `/auth/sign-out-everywhere` |
| Medium | 4 — Approval token expiry/rate limiting | `services/platform/approvals.py`, new `slowapi` middleware |
| Medium | 7 — Unescaped HTML | `routes/approvals.py` |
| Medium | 8 — CORS wildcard | `app.py` |
| Medium | 9 — Shared-identity blast radius | `infra/terraform/modules/iam`, per-agent `.agent_engine_config.json`, `services/platform/access_control.py` |
| Low | 10 — No CI/dependency scanning | new `.github/` |

Every "Planned" item above ships in this same change (see `AGENTS.md`'s dated entry for this
work for the verified-live confirmation of each, following this project's own "verify live, not
exit-code-0" discipline).
