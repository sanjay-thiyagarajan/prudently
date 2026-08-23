"""Put the live system into a known, clean state before recording a demo.

Recording a demo twice is normal; recording it against leftovers from the last take is not.
After a rehearsal the ward carries pending approvals nobody will click, autonomous actions from
a timeline that no longer exists, and — most damagingly — a `fleet_watch/state` document that
says every SKU is *already* breached, so the fleet stays completely silent on the replay.

What this clears:
  * `autonomous_actions`  — the fleet's unprompted work from the last run
  * `approvals`           — pending requests from the last run
  * `activity_log`        — the audit feed
  * `fleet_watch/state`   — so the next watch cycle sees transitions again
  * `armor_events` and `chaos_experiments`, only with --deep

What it deliberately does NOT touch:
  * `staff_roster`, `shift_history`, `inventory`, `vendors`, `admissions_timeseries` — the ward
    itself. Reseeding those re-anchors every credential expiry and admissions date to today and
    silently changes which staff are flagged, which is the opposite of a reproducible demo.
  * inventory `current_stock` — see --restock if you need it back at baseline.

Usage:
    uv run python -m scripts.demo_reset            # the usual case
    uv run python -m scripts.demo_reset --deep     # also clear armor + chaos evidence
    uv run python -m scripts.demo_reset --restock  # also return stock to its reorder headroom
    uv run python -m scripts.demo_reset --dry-run  # show what would go, delete nothing
"""

from __future__ import annotations

import argparse

from services.state import get_client

# Cleared every time: all of this is "what happened during the last take".
_RUN_ARTEFACTS = ("autonomous_actions", "approvals", "activity_log", "email_log")

# Cleared only with --deep: a blocked Model Armor event and a chaos experiment are *evidence*,
# and a demo often wants at least one of each already on screen rather than an empty panel.
_EVIDENCE = ("armor_events", "chaos_experiments")


def _wipe(collection: str, dry_run: bool) -> int:
    client = get_client()
    docs = list(client.collection(collection).stream())
    if dry_run:
        return len(docs)
    # Chunked well under Firestore's 500-writes-per-commit cap, same reasoning as
    # packages/datagen/datagen/seed.py's own chunking.
    batch = client.batch()
    pending = 0
    for doc in docs:
        batch.delete(doc.reference)
        pending += 1
        if pending == 450:
            batch.commit()
            batch = client.batch()
            pending = 0
    if pending:
        batch.commit()
    return len(docs)


def _restock(dry_run: bool) -> int:
    """Return every SKU to comfortably above its reorder point.

    1.6x rather than a stored original: the seeded value is a random days-of-supply draw, so
    'restore the original' has no single right answer. What a demo actually needs is every SKU
    starting 'ok' with enough runway that the surge takes a few days to bite — which is what
    this produces, deterministically.
    """
    client = get_client()
    docs = list(client.collection("inventory").stream())
    if dry_run:
        return len(docs)
    for doc in docs:
        item = doc.to_dict()
        target = int(item.get("reorder_point", 0) * 1.6)
        doc.reference.update({"current_stock": target})
    return len(docs)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deep", action="store_true", help="also clear armor + chaos evidence")
    parser.add_argument("--restock", action="store_true", help="return stock to baseline runway")
    parser.add_argument("--dry-run", action="store_true", help="report only, delete nothing")
    args = parser.parse_args()

    verb = "Would clear" if args.dry_run else "Cleared"
    collections = list(_RUN_ARTEFACTS) + (list(_EVIDENCE) if args.deep else [])

    for collection in collections:
        count = _wipe(collection, args.dry_run)
        print(f"{verb} {count:>4} doc(s) from {collection}")

    if args.dry_run:
        print("Would clear fleet_watch/state")
    else:
        get_client().document("fleet_watch/state").delete()
        print("Cleared      fleet_watch/state")

    if args.restock:
        count = _restock(args.dry_run)
        print(f"{verb} stock on {count} SKU(s) to 1.6x reorder point")

    print()
    print("Next: POST /watch/reset to clear the watch's last-seen snapshot. The fleet watch")
    print("runs on its own from there — no button to press — or POST /watch/check-now to pull")
    print("the next check forward on camera.")


if __name__ == "__main__":
    main()
