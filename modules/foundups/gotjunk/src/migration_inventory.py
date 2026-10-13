"""Offline, metadata-only GotJunk -> Mall migration inventory (no writes).

Input must be an export produced by an authorized operator. This module does
NOT access Firestore, Firebase Storage, IndexedDB, credentials or production.
It never emits raw owner IDs, source IDs, private locations or media URLs.
A supplied sha256 is an *unverified export assertion*, not proof of bytes.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
import re
import sys
from typing import Any, Mapping, Sequence

FOUNDUP_ID = "gotjunk_001"
_SOURCE_SYSTEMS = frozenset({"gotjunk_firestore", "gotjunk_indexeddb", "gotjunk_storage"})
_STATUSES = frozenset({
    "review", "kept", "deleted", "draft", "listed", "browsing",
    "in_cart", "skipped", "purchased",
})
_ALLOWED = frozenset({
    "source_system", "foundup_id", "source_item_id", "owner_uid",
    "content_sha256", "status",
})
_ID = re.compile(r"[A-Za-z0-9_-]{1,128}\Z")
_HASH = re.compile(r"[a-f0-9]{64}\Z")


def plan_inventory(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Return deterministic internal-only counts and resumable-key digest.

    Duplicate identical exports deduplicate. Conflicting owner/content for a
    source-system + item ID are blocked together (not silently first-wins).
    This report is NOT a cutover grant or a content validation receipt.
    """
    if not isinstance(rows, (list, tuple)) or len(rows) > 2000:
        raise ValueError("Expected at most 2000 export metadata rows")
    valid = []
    blocked = Counter()
    for record in rows:
        if not isinstance(record, Mapping) or set(record) != _ALLOWED:
            blocked["fields_invalid_or_sensitive"] += 1
            continue
        system, tenant, item, owner, digest, status = (
            record["source_system"], record["foundup_id"],
            record["source_item_id"], record["owner_uid"],
            record["content_sha256"], record["status"],
        )
        if system not in _SOURCE_SYSTEMS or tenant != FOUNDUP_ID:
            blocked["source_or_tenant_invalid"] += 1
            continue
        if (not isinstance(item, str) or not _ID.fullmatch(item)
                or not isinstance(owner, str) or not _ID.fullmatch(owner)):
            blocked["identity_unresolved"] += 1
            continue
        if not isinstance(digest, str) or not _HASH.fullmatch(digest):
            blocked["digest_unverified_or_invalid"] += 1
            continue
        if not isinstance(status, str) or status not in _STATUSES:
            blocked["status_unknown"] += 1
            continue
        valid.append((system, tenant, item, owner, digest, status))

    grouping = defaultdict(set)
    for row in valid:
        grouping[(row[0], row[2])].add((row[3], row[4], row[5]))
    conflicting = {key for key, variants in grouping.items() if len(variants) > 1}

    deduped = set()
    duplicates = 0
    for row in valid:
        if (row[0], row[2]) in conflicting:
            blocked["owner_digest_or_state_conflict"] += 1
            continue
        if row in deduped:
            duplicates += 1
        deduped.add(row)

    stable_keys = sorted(
        hashlib.sha256("\0".join(row[:2] + (row[2], row[4])).encode("utf-8")).hexdigest()
        for row in deduped
    )
    checksum = hashlib.sha256("\n".join(stable_keys).encode("ascii")).hexdigest()
    counts = Counter(row[5] for row in deduped)
    return {
        "dry_run": True, "source_authority": "operator_export_only",
        "foundup_id": FOUNDUP_ID,
        "input_rows": len(rows), "unique_candidates": len(deduped),
        "duplicate_rows": duplicates,
        "blocked_rows": sum(blocked.values()),
        "blocked_reasons": dict(sorted(blocked.items())),
        "status_counts": dict(sorted(counts.items())),
        "idempotency_set_sha256": checksum,
        "source_digests_verified": False,
        "cutover_authorized": False, "writes": 0,
    }


def main(argv: Sequence[str] | None = None) -> int:
    if list(sys.argv[1:] if argv is None else argv) != ["--dry-run"]:
        print("Only explicit --dry-run is supported", file=sys.stderr)
        return 2
    # Bounded input; no live data fetch, no output file, no raw private records.
    data = sys.stdin.buffer.read(1024 * 1024 + 1)
    if len(data) > 1024 * 1024:
        print("Export exceeds 1 MiB metadata-only bound", file=sys.stderr)
        return 2
    try:
        records = json.loads(data.decode("utf-8"))
        result = plan_inventory(records)
    except (ValueError, UnicodeError, TypeError):
        print("Invalid metadata-only export", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True))
    return 0 if result["blocked_rows"] == 0 else 3


if __name__ == "__main__":
    raise SystemExit(main())
