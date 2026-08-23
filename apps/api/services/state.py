"""Firestore live-state accessors — "what is currently true" (roster, shifts, inventory,
admissions), distinct from Memory Bank's "what an agent remembers/reasoned about"
(services/memory.py). Collections are seeded by packages/datagen/datagen/seed.py."""

from __future__ import annotations

from functools import lru_cache

from google.cloud import firestore

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
    sim_day: int | None = None,
    source: str = "sim_clock",
) -> None:
    """Appends one real stock-movement event (consumption from a sim-day tick, or a receipt
    from a purchase order being marked received) to `inventory_transactions` — the audit trail
    behind Inventory's per-SKU drill-down. Convenience wrapper, same shape as log_activity."""
    get_client().collection("inventory_transactions").add(
        {
            "sku": sku,
            "item_name": item_name,
            "type": tx_type,
            "quantity_delta": quantity_delta,
            "stock_before": stock_before,
            "stock_after": stock_after,
            "sim_day": sim_day,
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
) -> None:
    """Convenience wrapper around write_activity_log for the ~5 call sites that log a
    consequential action inline (approvals, Gateway routing, MedRep screening, Chaos
    experiments) — spares each call site from spelling out the dict shape and
    SERVER_TIMESTAMP by hand."""
    write_activity_log(
        {
            "agent_name": agent_name,
            "activity_type": activity_type,
            "summary": summary,
            "tool_name": tool_name,
            "status": status,
            "trace_id": trace_id,
            "timestamp": firestore.SERVER_TIMESTAMP,
        }
    )


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
