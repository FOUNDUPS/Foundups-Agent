"""Read-only query receipts for governed Memex projection records.

Memex projection records are historical memory evidence. They can support
project continuity and prior-decision recall, but they cannot prove current code
or authoritative work state. This module performs deterministic local matching
over already-projected records and returns a generation-bound query receipt.
It never mutates Memex or HoloIndex.
"""

from __future__ import annotations

import re
from dataclasses import asdict, is_dataclass
from typing import Any, Mapping, Sequence

from holo_index.memex_projection_adapter import (
    MemexProjectionRecord,
    MemexProjectionResult,
    MemexSnapshotProjectionReceipt,
)
from holo_index.query_receipt import SOURCE_CLASS_MEMEX, build_query_receipt


SCHEMA_VERSION = "holoindex_memex_query_routing.v1"
MEMEX_QUERY_SOURCE = "memex_projection"

_TERM_RE = re.compile(r"[A-Za-z0-9_]{2,}")


def build_memex_projection_query_receipt(
    *,
    query: str,
    projection: MemexProjectionResult | Mapping[str, Any],
    limit: int = 8,
) -> Mapping[str, Any]:
    """Build a read-only query receipt from a Memex projection result."""

    query_text = str(query or "").strip()
    records, receipt, projection_ok, error = _normalize_projection(projection)
    terms = _query_terms(query_text)
    if not query_text or not terms:
        projection_ok = False
        error = error or "empty_memex_query"
    if not receipt:
        projection_ok = False
        error = error or "missing_memex_projection_receipt"

    hits = []
    if projection_ok and receipt:
        hits = _rank_records(records, terms=terms, limit=limit)

    result = {
        "ok": projection_ok,
        "query": query_text,
        "freshness": "CURRENT" if projection_ok else "UNKNOWN",
        "hits": hits,
        "error": error,
    }
    generation_binding = {
        "freshness_generation_id": receipt.holoindex_generation_id if receipt else "",
        "freshness_receipt_digest": receipt.receipt_id if receipt else "",
        "freshness_receipt_path": "",
        "repo_head_sha": receipt.source_revision if receipt else "",
    }
    return build_query_receipt(
        source=MEMEX_QUERY_SOURCE,
        source_class=SOURCE_CLASS_MEMEX,
        query=query_text,
        result=result,
        require_generation=True,
        generation_binding=generation_binding,
    )


def _normalize_projection(
    projection: MemexProjectionResult | Mapping[str, Any],
) -> tuple[tuple[MemexProjectionRecord, ...], MemexSnapshotProjectionReceipt | None, bool, str]:
    if isinstance(projection, MemexProjectionResult):
        return (
            tuple(projection.records),
            projection.receipt,
            projection.accepted and projection.receipt is not None,
            "" if projection.accepted else ",".join(projection.rejection_reasons),
        )
    if not isinstance(projection, Mapping):
        return (), None, False, "projection_not_mapping"
    raw_records = projection.get("records")
    records = tuple(
        record
        for record in (_record_from_mapping(item) for item in raw_records or ())
        if record is not None
    )
    receipt = _receipt_from_mapping(projection.get("receipt"))
    accepted = projection.get("accepted") is True and receipt is not None
    reasons = projection.get("rejection_reasons")
    error = ",".join(str(item) for item in reasons) if isinstance(reasons, Sequence) else ""
    return records, receipt, accepted, error


def _record_from_mapping(value: Any) -> MemexProjectionRecord | None:
    if isinstance(value, MemexProjectionRecord):
        return value
    if not isinstance(value, Mapping):
        return None
    try:
        return MemexProjectionRecord(
            record_id=str(value.get("record_id") or ""),
            source_class=str(value.get("source_class") or ""),
            foundup_id=str(value.get("foundup_id") or ""),
            memex_snapshot_id=str(value.get("memex_snapshot_id") or ""),
            source_scope=str(value.get("source_scope") or ""),
            source_revision=str(value.get("source_revision") or ""),
            title=str(value.get("title") or ""),
            text=str(value.get("text") or ""),
            metadata=dict(value.get("metadata") or {}),
            content_digest=str(value.get("content_digest") or ""),
        )
    except Exception:
        return None


def _receipt_from_mapping(value: Any) -> MemexSnapshotProjectionReceipt | None:
    if isinstance(value, MemexSnapshotProjectionReceipt):
        return value
    if not isinstance(value, Mapping):
        return None
    try:
        return MemexSnapshotProjectionReceipt(
            schema_version=str(value.get("schema_version") or ""),
            memex_snapshot_id=str(value.get("memex_snapshot_id") or ""),
            source_scope=str(value.get("source_scope") or ""),
            source_revision=str(value.get("source_revision") or ""),
            content_manifest_digest=str(value.get("content_manifest_digest") or ""),
            created_at=str(value.get("created_at") or ""),
            access_policy_digest=str(value.get("access_policy_digest") or ""),
            records_indexed=int(value.get("records_indexed") or 0),
            records_rejected=int(value.get("records_rejected") or 0),
            holoindex_generation_id=str(value.get("holoindex_generation_id") or ""),
            verification=str(value.get("verification") or ""),
            rejected_reasons=tuple(value.get("rejected_reasons") or ()),
            no_holoindex_write_performed=bool(value.get("no_holoindex_write_performed", True)),
            no_memex_write_performed=bool(value.get("no_memex_write_performed", True)),
            no_brain_write_performed=bool(value.get("no_brain_write_performed", True)),
            no_breadcrumb_write_performed=bool(
                value.get("no_breadcrumb_write_performed", True)
            ),
            receipt_id=str(value.get("receipt_id") or ""),
        )
    except Exception:
        return None


def _query_terms(query: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(match.group(0).lower() for match in _TERM_RE.finditer(query)))


def _rank_records(
    records: Sequence[MemexProjectionRecord],
    *,
    terms: Sequence[str],
    limit: int,
) -> list[dict[str, Any]]:
    ranked = []
    for record in records:
        haystack = f"{record.title}\n{record.text}".lower()
        matched = tuple(term for term in terms if term in haystack)
        if not matched:
            continue
        score = len(matched) / max(1, len(terms))
        ranked.append(
            {
                "path": f"memex://{record.memex_snapshot_id}/{record.record_id}",
                "title": record.title,
                "score": round(score, 6),
                "digest": record.content_digest,
                "evidence_ref": (
                    f"memex:{record.memex_snapshot_id}:{record.record_id}:"
                    f"{record.metadata.get('section', '')}"
                ),
            }
        )
    ranked.sort(key=lambda item: (-float(item["score"]), str(item["path"])))
    return ranked[: max(0, int(limit or 0))]


def projection_to_plain_dict(value: MemexProjectionResult) -> dict[str, Any]:
    """Return a plain dict for callers that persist projection results."""

    data = value.to_dict()
    if value.receipt and is_dataclass(value.receipt):
        data["receipt"] = asdict(value.receipt)
    return data


__all__ = [
    "MEMEX_QUERY_SOURCE",
    "SCHEMA_VERSION",
    "build_memex_projection_query_receipt",
    "projection_to_plain_dict",
]
