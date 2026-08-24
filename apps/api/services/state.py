"""Firestore live-state accessors — "what is currently true" (roster, shifts, inventory,
admissions), distinct from Memory Bank's "what an agent remembers/reasoned about"
(services/memory.py). Collections are seeded by packages/datagen/datagen/seed.py."""

from __future__ import annotations

from functools import lru_cache

from google.cloud import firestore

# Module-level, not the usual services/state.py "no ADK/heavy imports at module scope"
# discipline's exception — neither of these two modules imports services.state (no circular
# risk) nor pulls in ADK/model machinery (crypto.py's real Cloud KMS client is itself imported
# lazily inside crypto_kms.py, only on first actual encrypt/decrypt call).
from services.platform.access_control import require_access
from services.platform.crypto import get_crypto_service

# Vertex AI Agent Engine auto-injects GOOGLE_CLOUD_PROJECT into the sandbox as the numeric
# *project number* (e.g. "439570031916"), not the project ID. pydantic-settings picks that env
# var up automatically, silently overriding config.py's "prudently-hackathon" default — so
# get_settings().google_cloud_project resolves to the number at runtime. Firestore's
# resource-path resolution does not accept the numeric form the same way most other GCP APIs
# do, and fails with a confusing "database (default) does not exist" 404 for a database that
# demonstrably exists (Cloud Run, where GOOGLE_CLOUD_PROJECT happens not to collide the same
# way, reaches the same database fine). Hardcoded here, deliberately bypassing config.py,
# specifically to dodge that env var collision.
FIRESTORE_PROJECT_ID = "prudently-hackathon"


@lru_cache
def get_client() -> firestore.Client:
    return firestore.Client(project=FIRESTORE_PROJECT_ID, database="(default)")


def get_staff_roster() -> list[dict]:
    return [doc.to_dict() for doc in get_client().collection("staff_roster").stream()]


def get_shift_history() -> list[dict]:
    return [doc.to_dict() for doc in get_client().collection("shift_history").stream()]


def get_inventory() -> list[dict]:
    return [doc.to_dict() for doc in get_client().collection("inventory").stream()]


def get_vendors() -> list[dict]:
    return [doc.to_dict() for doc in get_client().collection("vendors").stream()]


@firestore.transactional
def _adjust_stock_txn(transaction, doc_ref, delta: int) -> tuple[int, int]:
    snapshot = doc_ref.get(transaction=transaction)
    before = snapshot.get("current_stock")
    after = max(0, before + delta)
    transaction.update(doc_ref, {"current_stock": after})
    return before, after


def adjust_inventory_stock(sku: str, delta: int) -> tuple[int, int]:
    """Transactionally adjusts one SKU's current_stock by `delta` (negative for consumption,
    positive for a received purchase order) and returns (stock_before, stock_after). Wrapped
    in a real Firestore transaction — not a plain read-then-set — because a same-day
    consumption decrement (sim clock) and a purchase-order receipt could otherwise race and
    silently drop one of the two writes."""
    client = get_client()
    doc_ref = client.collection("inventory").document(sku)
    transaction = client.transaction()
    return _adjust_stock_txn(transaction, doc_ref, delta)


# pylint: disable-next=too-many-arguments,too-many-positional-arguments
def write_inventory_transaction(
    sku: str,
    item_name: str,
    tx_type: str,
    quantity_delta: int,
    stock_before: int,
    stock_after: int,
    *,
    source: str = "fleet_watch",
) -> None:
    """Appends one real stock-movement event (consumption noise from a watch-loop cycle, or a
    receipt from a purchase order being marked received) to `inventory_transactions` — the audit
    trail behind Inventory's per-SKU drill-down. Convenience wrapper, same shape as
    log_activity. `timestamp` (real wall-clock, not a day counter) is what the dashboard renders
    relative-time against."""
    get_client().collection("inventory_transactions").add(
        {
            "sku": sku,
            "item_name": item_name,
            "type": tx_type,
            "quantity_delta": quantity_delta,
            "stock_before": stock_before,
            "stock_after": stock_after,
            "source": source,
            "timestamp": firestore.SERVER_TIMESTAMP,
        }
    )


def get_inventory_transactions(sku: str | None = None, limit: int = 200) -> list[dict]:
    """Most recent `inventory_transactions` docs, newest first. Filters by sku in Python, same
    rationale as get_activity_log's agent_name filter — an equality `where` combined with this
    `order_by` would need a composite index this project doesn't provision, and the collection
    is small enough (8 SKUs x up to 21 sim-days, plus PO receipts) for client-side filtering."""
    docs = (
        get_client()
        .collection("inventory_transactions")
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    entries = [{**doc.to_dict(), "id": doc.id} for doc in docs]
    if sku is not None:
        entries = [entry for entry in entries if entry.get("sku") == sku]
    return entries


def get_agent_registry() -> list[dict]:
    """Every `agent_registry` doc, unordered — the dashboard's fleet overview panel reads
    this directly rather than through services/platform/registry.py's `get_agent(name)`
    single-doc lookup, since the panel wants the whole roster, not one entry at a time."""
    return [doc.to_dict() for doc in get_client().collection("agent_registry").stream()]


def get_armor_events(limit: int = 20) -> list[dict]:
    """Most recent `armor_events` docs, newest first — the dashboard's BLOCKED-banner feed."""
    docs = (
        get_client()
        .collection("armor_events")
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    return [doc.to_dict() for doc in docs]


def get_chaos_experiments(limit: int = 20) -> list[dict]:
    """Most recent `chaos_experiments` docs, newest first — the dashboard's replay feed."""
    docs = (
        get_client()
        .collection("chaos_experiments")
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    return [doc.to_dict() for doc in docs]


def write_armor_event(event: dict) -> None:
    """Appends one Model Armor screening outcome to the `armor_events` collection — the
    dashboard's BLOCKED-banner feed reads this. Auto-ID'd (`.add`, not `.set`): events have no
    natural key, and a screening can legitimately repeat for the same vendor/message pair
    (retries, replay)."""
    get_client().collection("armor_events").add(event)


def write_chaos_experiment(event: dict) -> None:
    """Appends one Chaos & Continuity experiment outcome to the `chaos_experiments`
    collection — run once for real, replayed from here for the demo rather than re-run live.
    Auto-ID'd for the same reason as `write_armor_event`."""
    get_client().collection("chaos_experiments").add(event)


def get_approval_policy(task_type: str) -> dict | None:
    """Single-doc read by fixed key (task_type) — the first "get one doc by ID" helper in this
    file; every other reader here is either read-all or read-recent. `services/platform/
    approvals.py`'s check_policy() treats `None` as "no policy configured" and fails closed."""
    doc = get_client().collection("approval_policy").document(task_type).get()
    return doc.to_dict() if doc.exists else None


def get_approval_policies() -> list[dict]:
    """Every `approval_policy` doc — the dashboard's policy-editor panel reads this to render
    the full per-task-type table."""
    return [doc.to_dict() for doc in get_client().collection("approval_policy").stream()]


def write_approval_policy(task_type: str, policy: dict) -> None:
    """Full overwrite on a fixed doc ID (task_type) — safe to re-run, same `set()` semantics as
    `scripts/seed_registry.py`. The dashboard's policy-editor Save button and
    `scripts/seed_policy.py` both call this."""
    get_client().collection("approval_policy").document(task_type).set(policy)


def get_approval(token: str) -> dict | None:
    """Single-doc read by the approval's own token (used as the Firestore doc ID — a bearer
    capability, see approvals.py). `routes/approvals.py`'s confirm-page GET and mutating POST
    handlers both read through this."""
    doc = get_client().collection("approvals").document(token).get()
    return doc.to_dict() if doc.exists else None


def write_approval(token: str, record: dict) -> None:
    """Creates one `approvals` doc with the token as its ID — `.set()`, not `.add()`, since the
    token (not an auto-ID) is the identifier the emailed approve/reject links carry."""
    get_client().collection("approvals").document(token).set(record)


def update_approval(token: str, patch: dict) -> None:
    """Partial update of an existing `approvals` doc by token — the first "update by ID"
    helper in this file. Used by `services/platform/approvals.py`'s resolve_approval() to
    transition a record from `pending` to `approved`/`rejected`."""
    get_client().collection("approvals").document(token).update(patch)


def get_approvals(limit: int = 20) -> list[dict]:
    """Most recent `approvals` docs, newest first — the dashboard's Approvals feed. Fetches
    unfiltered (no `where(status == ...)`) and lets the caller group by status in Python,
    matching every other feed in this file — a `where` combined with `order_by` would need a
    composite Firestore index this project doesn't have."""
    docs = (
        get_client()
        .collection("approvals")
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    return [doc.to_dict() for doc in docs]


def write_email_log(record: dict) -> None:
    """Appends one send-attempt outcome (approval-request emails and the real downstream
    sends alike) to the `email_log` collection — an audit trail, same shape/rationale as
    `write_armor_event`. Auto-ID'd: a send attempt has no natural key."""
    get_client().collection("email_log").add(record)


def get_admissions(limit: int = 100) -> list[dict]:
    """Every `admissions_timeseries` doc up to `limit` (63 exist today: 21 sim-days x 3
    units) — the dashboard's Admissions panel aggregates/sorts in Python, matching every
    other feed's "read, then shape" split. Unordered: doc IDs already encode sim_day+unit,
    there's no natural Firestore sort key worth an index for this."""
    docs = get_client().collection("admissions_timeseries").limit(limit).stream()
    return [doc.to_dict() for doc in docs]


def get_payroll_records(limit: int = 50) -> list[dict]:
    """Most recent `payroll_records` docs, newest first — the payroll panel's list view.
    `doc.to_dict()` never includes the doc's own ID (Firestore doesn't embed it), so it's
    added explicitly here — the frontend needs a real id per record for its list `key` and to
    address the mark-paid endpoint, and every payroll record dict should carry it the same
    way regardless of which route returned it."""
    docs = (
        get_client()
        .collection("payroll_records")
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    return [{**doc.to_dict(), "id": doc.id} for doc in docs]


def write_payroll_record(record: dict) -> str:
    """Auto-ID'd — a payroll record has no natural key (one staff member can have many pay
    periods). Returns the new doc's ID so the caller can echo it back to the client."""
    _, doc_ref = get_client().collection("payroll_records").add(record)
    return doc_ref.id


def get_payroll_record(record_id: str) -> dict | None:
    """Same "always carries its own id" treatment as get_payroll_records — see its docstring."""
    doc = get_client().collection("payroll_records").document(record_id).get()
    return {**doc.to_dict(), "id": doc.id} if doc.exists else None


def update_payroll_record(record_id: str, patch: dict) -> None:
    get_client().collection("payroll_records").document(record_id).update(patch)


def write_payroll_records_batch(records: list[dict]) -> list[str]:
    """Batch-writes a pay run's line items (one per staff member, at most ~34 today, well
    under Firestore's 500-write batch cap) in a single commit. Each record still gets a real
    auto-generated doc ID, same as write_payroll_record's single-record path — Firestore's
    `.document()` with no argument mints one without needing a write."""
    coll = get_client().collection("payroll_records")
    batch = get_client().batch()
    doc_ids: list[str] = []
    for record in records:
        doc_ref = coll.document()
        doc_ids.append(doc_ref.id)
        batch.set(doc_ref, record)
    if doc_ids:
        batch.commit()
    return doc_ids


def get_payroll_records_by_run(run_id: str) -> list[dict]:
    """A pay run's own line items. Single-field equality `where`, no `order_by` alongside it,
    so this needs no composite index — same reasoning `get_activity_log` uses for filtering in
    Python instead, except this filter is cheap and selective enough to push into Firestore
    itself."""
    docs = get_client().collection("payroll_records").where("run_id", "==", run_id).stream()
    return [{**doc.to_dict(), "id": doc.id} for doc in docs]


def mark_payroll_run_records_paid(run_id: str) -> None:
    """Bulk-transitions every payroll_records line item belonging to run_id to paid, in one
    batch commit — the disburse step's counterpart to update_payroll_record's single-record
    mark-paid."""
    coll = get_client().collection("payroll_records")
    docs = coll.where("run_id", "==", run_id).stream()
    batch = get_client().batch()
    count = 0
    for doc in docs:
        batch.update(doc.reference, {"status": "paid", "paid_at": firestore.SERVER_TIMESTAMP})
        count += 1
    if count:
        batch.commit()


def write_payroll_run(run: dict) -> str:
    _, doc_ref = get_client().collection("payroll_runs").add(run)
    return doc_ref.id


def get_payroll_run(run_id: str) -> dict | None:
    doc = get_client().collection("payroll_runs").document(run_id).get()
    return {**doc.to_dict(), "id": doc.id} if doc.exists else None


def get_payroll_runs(limit: int = 50) -> list[dict]:
    docs = (
        get_client()
        .collection("payroll_runs")
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    return [{**doc.to_dict(), "id": doc.id} for doc in docs]


def update_payroll_run(run_id: str, patch: dict) -> None:
    get_client().collection("payroll_runs").document(run_id).update(patch)


def write_purchase_order(po: dict) -> str:
    """Auto-ID'd, same rationale as write_payroll_record — a PO has no natural key. Created
    for real (never fabricated) from services/platform/approvals.py the moment a
    contact_vendor_for_reorder call actually reaches the vendor, whether that was sent
    immediately or only after manager approval."""
    _, doc_ref = get_client().collection("purchase_orders").add(po)
    return doc_ref.id


def get_purchase_order(po_id: str) -> dict | None:
    doc = get_client().collection("purchase_orders").document(po_id).get()
    return {**doc.to_dict(), "id": doc.id} if doc.exists else None


def get_purchase_orders(limit: int = 100) -> list[dict]:
    docs = (
        get_client()
        .collection("purchase_orders")
        .order_by("ordered_at", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    return [{**doc.to_dict(), "id": doc.id} for doc in docs]


def update_purchase_order(po_id: str, patch: dict) -> None:
    get_client().collection("purchase_orders").document(po_id).update(patch)


def write_activity_log(entry: dict) -> None:
    """Appends one consequential agent action to the `activity_log` collection — the audit
    trail behind each agent's detail page. Auto-ID'd, same rationale as `write_armor_event`:
    an activity has no natural key and the same agent can log the same kind of event many
    times. Deliberately narrow: only approval requests/resolutions, MedRep's screening
    decisions, Gateway routing decisions, and Chaos experiments write here — not every
    read-only tool call, which would drown the feed in query telemetry the LLM generates on
    nearly every turn."""
    get_client().collection("activity_log").add(entry)


# pylint: disable-next=too-many-arguments,too-many-positional-arguments
def log_activity(
    agent_name: str,
    activity_type: str,
    summary: str,
    *,
    tool_name: str | None = None,
    status: str | None = None,
    trace_id: str | None = None,
    initiated_by: str = "manager",
) -> None:
    """Convenience wrapper around write_activity_log for the ~5 call sites that log a
    consequential action inline (approvals, Gateway routing, MedRep screening, Chaos
    experiments) — spares each call site from spelling out the dict shape and
    SERVER_TIMESTAMP by hand.

    `initiated_by` distinguishes work the fleet did on its own initiative
    ("autonomous_watch", written by services/autonomy.py) from work a human asked for
    ("manager", the default) — the dashboard renders the two differently, and conflating them
    would let the fleet take credit for acting unprompted when it didn't."""
    write_activity_log(
        {
            "agent_name": agent_name,
            "activity_type": activity_type,
            "summary": summary,
            "tool_name": tool_name,
            "status": status,
            "trace_id": trace_id,
            "initiated_by": initiated_by,
            "timestamp": firestore.SERVER_TIMESTAMP,
        }
    )


# --- Autonomous fleet watch (services/triggers.py + services/autonomy.py) -------------------

# Single document: the watch is a fleet-wide singleton, and a collection of one doc keyed by
# a constant is clearer than inventing a partition key that will only ever have one value.
_WATCH_STATE_DOC = "fleet_watch/state"


def get_watch_state() -> dict | None:
    """The previous tick's snapshot, or None on the very first tick after a reset."""
    doc = get_client().document(_WATCH_STATE_DOC).get()
    return doc.to_dict() if doc.exists else None


def write_watch_state(state: dict) -> None:
    get_client().document(_WATCH_STATE_DOC).set(state)


def clear_watch_state() -> None:
    """Called by POST /watch/reset (an internal ops utility, not a dashboard button) so a fresh
    reseed re-fires the same triggers from a clean slate — without this, a reseeded demo would
    be silent because every SKU/unit/credential is already recorded at its breached status."""
    get_client().document(_WATCH_STATE_DOC).delete()


def write_autonomous_action(record: dict) -> str:
    """One record per trigger the fleet acted on unprompted. Auto-ID'd, same rationale as
    write_activity_log."""
    _, doc_ref = get_client().collection("autonomous_actions").add(record)
    return doc_ref.id


def get_autonomous_actions(limit: int = 30) -> list[dict]:
    docs = (
        get_client()
        .collection("autonomous_actions")
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    return [{**doc.to_dict(), "id": doc.id} for doc in docs]


# --- Facilities job sheets (routes/job_sheets.py) -------------------------------------------
# Plain CRUD, deliberately not agent-backed (see routes/job_sheets.py's module docstring for
# why) — a maintenance ticket has no autonomy story an LLM adds value to.


def write_job_sheet(sheet: dict) -> str:
    _, doc_ref = get_client().collection("job_sheets").add(sheet)
    return doc_ref.id


def get_job_sheets(limit: int = 100) -> list[dict]:
    docs = (
        get_client()
        .collection("job_sheets")
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    return [{**doc.to_dict(), "id": doc.id} for doc in docs]


def get_job_sheet(sheet_id: str) -> dict | None:
    doc = get_client().collection("job_sheets").document(sheet_id).get()
    return {**doc.to_dict(), "id": doc.id} if doc.exists else None


def update_job_sheet(sheet_id: str, patch: dict) -> None:
    get_client().collection("job_sheets").document(sheet_id).update(patch)


def get_activity_log(agent_name: str | None = None, limit: int = 100) -> list[dict]:
    """Most recent `activity_log` docs, newest first. Filters by agent_name in Python rather
    than a Firestore `where`, matching `get_approvals`' rationale — a `where` combined with
    `order_by` needs a composite index this project doesn't provision, and the collection is
    small enough that reading `limit` recent docs and filtering client-side is fine for a
    dashboard feed."""
    docs = (
        get_client()
        .collection("activity_log")
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    entries = [{**doc.to_dict(), "id": doc.id} for doc in docs]
    if agent_name is not None:
        entries = [entry for entry in entries if entry.get("agent_name") == agent_name]
    return entries


# --- Patients / surgical cases (Part D — agents/surgical_scheduling) -------------------------
# Every accessor below requires a `caller` and calls `require_access` first
# (services/platform/access_control.py) — the application-layer mitigation for docs/threat-
# model.md finding 9, given no platform-level per-agent identity exists to enforce this
# instead. PII fields are encrypted at rest via services/platform/crypto.py before every write
# and decrypted only inside these accessors, never left encrypted for a caller to accidentally
# forward ciphertext as if it were plaintext.

_PATIENT_PII_FIELDS = ("name", "date_of_birth", "contact_email", "contact_phone")


def _encrypt_patient_fields(patient: dict) -> dict:
    crypto = get_crypto_service()
    encrypted = dict(patient)
    for field in _PATIENT_PII_FIELDS:
        if encrypted.get(field):
            encrypted[field] = crypto.encrypt_field(encrypted[field])
    return encrypted


def _decrypt_patient_fields(patient: dict) -> dict:
    crypto = get_crypto_service()
    decrypted = dict(patient)
    for field in _PATIENT_PII_FIELDS:
        if decrypted.get(field):
            decrypted[field] = crypto.decrypt_field(decrypted[field])
    return decrypted


def write_patient(patient: dict, *, caller: str) -> None:
    require_access(caller)
    get_client().collection("patients").document(patient["patient_id"]).set(
        _encrypt_patient_fields(patient)
    )


def get_patients(*, caller: str) -> list[dict]:
    require_access(caller)
    docs = [doc.to_dict() for doc in get_client().collection("patients").stream()]
    return [_decrypt_patient_fields(doc) for doc in docs]


def get_patient(patient_id: str, *, caller: str) -> dict | None:
    require_access(caller)
    doc = get_client().collection("patients").document(patient_id).get()
    return _decrypt_patient_fields(doc.to_dict()) if doc.exists else None


def write_surgical_case(case: dict, *, caller: str) -> None:
    require_access(caller)
    get_client().collection("surgical_cases").document(case["case_id"]).set(case)


def get_surgical_cases(*, caller: str) -> list[dict]:
    """No PII on this collection at all — case_id/patient_id (an opaque FK, not a name)/
    procedure/room/times/status — so unlike the patient accessors above there's genuinely
    nothing to encrypt here; require_access still applies, since patient_id itself is enough to
    look a specific patient's case up via get_patient."""
    require_access(caller)
    return [doc.to_dict() for doc in get_client().collection("surgical_cases").stream()]


def get_surgical_case(case_id: str, *, caller: str) -> dict | None:
    require_access(caller)
    doc = get_client().collection("surgical_cases").document(case_id).get()
    return doc.to_dict() if doc.exists else None


def update_surgical_case(case_id: str, patch: dict, *, caller: str) -> None:
    require_access(caller)
    get_client().collection("surgical_cases").document(case_id).update(patch)


def write_patient_notification_log(entry: dict) -> None:
    """PHI-adjacent notification history gets its own audit trail — `patient_notification_log`
    — separate from the general `activity_log` (see agents/surgical_scheduling/agent.py's
    module docstring for why). No `caller`/require_access gate here: this collection carries no
    patient identity, only a `patient_id` FK (an opaque reference, same non-PII shape as
    `surgical_cases` itself), and every call site is already inside a caller that passed
    require_access to reach the patient in the first place. Auto-stamps `timestamp`, same
    convenience `log_activity` gives its own callers."""
    get_client().collection("patient_notification_log").add(
        {**entry, "timestamp": firestore.SERVER_TIMESTAMP}
    )


def get_patient_notification_log(limit: int = 100) -> list[dict]:
    docs = (
        get_client()
        .collection("patient_notification_log")
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    return [{**doc.to_dict(), "id": doc.id} for doc in docs]
