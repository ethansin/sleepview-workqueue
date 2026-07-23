#!/usr/bin/env python3
"""Backfill role1_data.date_of_birth / clinical_note_expiration to MM/DD/YYYY.

Older items may still have these fields stored as YYYY-MM-DD (the format
used before the upload form switched to paste-friendly text inputs). This
walks every workflow_items document, converts any YYYY-MM-DD value to
MM/DD/YYYY, and leaves everything else untouched.

Usage:
    # Preview only, no writes:
    python scripts/backfill_date_format.py --project your-gcp-project-id

    # Apply the changes, attributing them to your account in the audit log:
    python scripts/backfill_date_format.py --project your-gcp-project-id \
        --actor you@westlakesleep.com --apply

Requires Application Default Credentials with access to the target
Firestore database (e.g. `gcloud auth application-default login`).
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone

from google.cloud import firestore

ITEMS_COLLECTION = "workflow_items"
AUDIT_COLLECTION = "audit_log"

ISO_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
US_DATE = re.compile(r"^\d{2}/\d{2}/\d{4}$")

DATE_FIELDS = ("date_of_birth", "clinical_note_expiration")


def to_mm_dd_yyyy(value: str) -> str | None:
    """Convert a YYYY-MM-DD string to MM/DD/YYYY. Returns None if not ISO-formatted."""
    m = ISO_DATE.match(value.strip())
    if not m:
        return None
    year, month, day = m.groups()
    return f"{month}/{day}/{year}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project", required=True, help="GCP project ID hosting Firestore.")
    parser.add_argument("--actor", default=None, help="Email to attribute writes to in the audit log (required with --apply).")
    parser.add_argument("--apply", action="store_true", help="Actually write changes. Without this, only prints a preview.")
    args = parser.parse_args()

    if args.apply and not args.actor:
        parser.error("--actor is required when using --apply, for the audit trail.")

    db = firestore.Client(project=args.project)

    converted = 0
    already_ok = 0
    unrecognized = []

    for doc in db.collection(ITEMS_COLLECTION).stream():
        data = doc.to_dict() or {}
        role1 = data.get("role1_data")
        if not role1:
            continue

        updates: dict[str, str] = {}
        for field in DATE_FIELDS:
            value = role1.get(field)
            if not value:
                continue
            if US_DATE.match(value):
                continue
            converted_value = to_mm_dd_yyyy(value)
            if converted_value is None:
                unrecognized.append((doc.id, field, value))
                continue
            updates[f"role1_data.{field}"] = converted_value

        if not updates:
            already_ok += 1
            continue

        converted += 1
        print(f"{doc.id}: {updates}")

        if args.apply:
            doc.reference.update(updates)
            db.collection(AUDIT_COLLECTION).add(
                {
                    "actor": args.actor,
                    "action": "backfill_date_format",
                    "item_id": doc.id,
                    "detail": f"fields={list(updates.keys())}",
                    "timestamp": datetime.now(timezone.utc),
                }
            )

    print()
    print(f"{converted} item(s) {'converted' if args.apply else 'would be converted'}")
    print(f"{already_ok} item(s) already in MM/DD/YYYY or had no date fields")
    if unrecognized:
        print(f"{len(unrecognized)} item(s) had a date in neither format — needs manual review:")
        for item_id, field, value in unrecognized:
            print(f"  {item_id}: {field}={value!r}")

    if not args.apply and converted:
        print()
        print("Dry run only — re-run with --actor <you> --apply to write these changes.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
