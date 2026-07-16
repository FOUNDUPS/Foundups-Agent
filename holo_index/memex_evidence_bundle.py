"""Content-bearing evidence bundles for governed Memex projection hits.

Memex content is historical memory evidence. It can provide project continuity
and prior-decision context, but it cannot prove current repository state. This
module only bundles content from an already verified projection and a matching
query receipt. It never writes Memex, HoloIndex, Brain, Breadcrumbs, or repo
state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from holo_index.memex_projection_integrity import verify_and_rehydrate_memex_projection
from holo_index.query_receipt import SOURCE_CLASS_MEMEX, digest_json


SCHEMA_VERSION = "holoindex_memex_content_evidence_bundle.v1"
BUNDLE_READY = "MEMEX_CONTENT_EVIDENCE_BUNDLE_READY"
BUNDLE_REJECTED = "MEMEX_CONTENT_EVIDENCE_BUNDLE_REJECTED"
DEFAULT_MAX_RECORD_CHARS = 4_000


@dataclass(frozen=True)
class MemexContentEvidenceBundleResult:
    accepted: bool
    status: str
    bundle: Mapping[str, Any] | None
    rejection_reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "status": self.status,
            "bundle": dict(self.bundle) if self.bundle else None,
            "rejection_reasons": list(self.rejection_reasons),
        }


def build_memex_content_evidence_bundle(
    *,
    query_receipt: Mapping[str, Any],
    projection: Any,
    max_record_chars: int = DEFAULT_MAX_RECORD_CHARS,
) -> MemexContentEvidenceBundleResult:
    """Build a content bundle for query-hit records from a verified projection."""

    if not isinstance(query_receipt, Mapping):
        return _reject("query_receipt_not_mapping")
    if query_receipt.get("ok") is not True:
        return _reject("query_receipt_not_ok")
    if query_receipt.get("source_class") != SOURCE_CLASS_MEMEX:
        return _reject("query_receipt_source_class_not_memex")
    projection_receipt_id = str(query_receipt.get("freshness_receipt_digest") or "").strip()
    if not projection_receipt_id:
        return _reject("missing_projection_receipt_binding")

    gate = verify_and_rehydrate_memex_projection(projection)
    if not gate.accepted or gate.projection is None or gate.projection.receipt is None:
        return _reject("projection_integrity_failed", *gate.rejection_reasons)
    if gate.projection.receipt.receipt_id != projection_receipt_id:
        return _reject("query_projection_receipt_mismatch")

    hit_refs = tuple(
        str(hit.get("evidence_ref") or "").strip()
        for hit in query_receipt.get("hits") or ()
        if isinstance(hit, Mapping) and str(hit.get("evidence_ref") or "").strip()
    )
    record_by_ref = {
        _record_evidence_ref(record): record
        for record in gate.projection.records
    }
    records = []
    for ref in hit_refs:
        record = record_by_ref.get(ref)
        if record is None:
            return _reject("query_hit_not_in_projection")
        text = record.text
        limit = max(0, int(max_record_chars or 0))
        truncated = len(text) > limit
        records.append(
            {
                "evidence_ref": ref,
                "source_class": SOURCE_CLASS_MEMEX,
                "memex_snapshot_id": record.memex_snapshot_id,
                "record_id": record.record_id,
                "section": str(record.metadata.get("section") or ""),
                "title": record.title,
                "content_digest": record.content_digest,
                "text": text[:limit],
                "text_truncated": truncated,
                "trust_boundary": "memex_memory_not_current_code_proof",
            }
        )

    payload = {
        "schema_version": SCHEMA_VERSION,
        "projection_receipt_id": gate.projection.receipt.receipt_id,
        "query_receipt_id": str(query_receipt.get("receipt_id") or ""),
        "record_count": len(records),
        "record_digests": tuple(record["content_digest"] for record in records),
        "no_memex_write_performed": True,
        "no_holoindex_write_performed": True,
        "no_brain_write_performed": True,
        "no_breadcrumb_write_performed": True,
    }
    bundle = {
        **payload,
        "records": tuple(records),
        "bundle_id": digest_json(payload),
    }
    return MemexContentEvidenceBundleResult(
        accepted=True,
        status=BUNDLE_READY,
        bundle=bundle,
        rejection_reasons=(),
    )


def _record_evidence_ref(record: Any) -> str:
    return (
        f"memex:{record.memex_snapshot_id}:{record.record_id}:"
        f"{record.metadata.get('section', '')}"
    )


def _reject(*reasons: str) -> MemexContentEvidenceBundleResult:
    return MemexContentEvidenceBundleResult(
        accepted=False,
        status=BUNDLE_REJECTED,
        bundle=None,
        rejection_reasons=tuple(dict.fromkeys(reason for reason in reasons if reason)),
    )


__all__ = [
    "BUNDLE_READY",
    "BUNDLE_REJECTED",
    "DEFAULT_MAX_RECORD_CHARS",
    "MemexContentEvidenceBundleResult",
    "SCHEMA_VERSION",
    "build_memex_content_evidence_bundle",
]
