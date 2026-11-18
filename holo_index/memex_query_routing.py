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
from holo_index.memex_projection_integrity import verify_and_rehydrate_memex_projection
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
    verdicts = _per_target_verdicts(records, terms=terms) if projection_ok else []

    result = {
        "ok": projection_ok,
        "query": query_text,
        "freshness": "CURRENT" if projection_ok else "UNKNOWN",
        "hits": hits,
        "error": error,
        "retrieval_verdict": "FOUND" if hits else "MISS",
        "per_target_retrieval_verdicts": verdicts,
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
    gate = verify_and_rehydrate_memex_projection(projection)
    if not gate.accepted or gate.projection is None:
        return (), None, False, ",".join(gate.rejection_reasons)
    return (
        tuple(gate.projection.records),
        gate.projection.receipt,
        gate.accepted and gate.projection.receipt is not None,
        "",
    )


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


def _per_target_verdicts(
    records: Sequence[MemexProjectionRecord],
    *,
    terms: Sequence[str],
) -> list[dict[str, Any]]:
    verdicts = []
    for term in terms:
        matched_refs = []
        for record in records:
            haystack = f"{record.title}\n{record.text}".lower()
            if term not in haystack:
                continue
            matched_refs.append(_record_evidence_ref(record))
        verdicts.append(
            {
                "target": term,
                "source_class": SOURCE_CLASS_MEMEX,
                "verdict": "FOUND" if matched_refs else "MISS",
                "matched_evidence_refs": matched_refs,
            }
        )
    return verdicts


def _record_evidence_ref(record: MemexProjectionRecord) -> str:
    return (
        f"memex:{record.memex_snapshot_id}:{record.record_id}:"
        f"{record.metadata.get('section', '')}"
    )


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
