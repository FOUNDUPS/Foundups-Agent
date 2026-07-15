"""Generation-bound HoloIndex query receipts.

WSP 97: a query result is only freshness evidence when it is bound to the
HoloIndex generation that served it. Query receipts are read-only artifacts;
they never trigger re-indexing or mutate HoloIndex.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from holo_index.freshness_receipt import (
    HoloIndexFreshnessReceipt,
    freshness_receipt_path,
    load_freshness_receipt,
)


SCHEMA_VERSION = "holoindex_query_receipt.v1"
SOURCE_CLASS_HOLOINDEX = "holoindex"
SOURCE_CLASS_CODEINDEX = "codeindex"
SOURCE_CLASS_MEMEX = "memex"
SOURCE_CLASS_BRAIN = "brain"
SOURCE_CLASS_BREADCRUMB = "breadcrumb"
FRESHNESS_STATES = frozenset({"CURRENT", "FRESH"})


@dataclass(frozen=True)
class HoloIndexQueryHit:
    """Bounded query hit normalized for RedDog/WRE receipts."""

    path: str
    title: str = ""
    score: Any = None
    digest: str = ""
    evidence_ref: str = ""
    source_class: str = SOURCE_CLASS_HOLOINDEX

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class HoloIndexQueryReceipt:
    """Read-only query receipt bound to a HoloIndex generation."""

    schema_version: str
    source: str
    source_class: str
    ok: bool
    query: str
    freshness: str
    hits: list[HoloIndexQueryHit] = field(default_factory=list)
    error: str = ""
    freshness_generation_id: str = ""
    freshness_receipt_digest: str = ""
    freshness_receipt_path: str = ""
    repo_head_sha: str = ""
    index_gap_detected: bool = False
    stale_reasons: list[str] = field(default_factory=list)
    no_holoindex_reindex_performed: bool = True
    receipt_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["hits"] = [hit.to_dict() for hit in self.hits]
        return data


def digest_json(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def file_digest(path: Path | str) -> str:
    receipt_path = Path(path)
    try:
        return "sha256:" + hashlib.sha256(receipt_path.read_bytes()).hexdigest()
    except Exception:
        return ""


def load_generation_binding(
    *,
    ssd_path: Path | str | None = None,
    receipt_path: Path | str | None = None,
) -> Mapping[str, str]:
    """Load public freshness-generation fields without mutating HoloIndex."""

    path = Path(receipt_path) if receipt_path else freshness_receipt_path(Path(ssd_path or "E:/HoloIndex"))
    try:
        receipt = load_freshness_receipt(path)
    except Exception:
        return {
            "freshness_generation_id": "",
            "freshness_receipt_digest": "",
            "freshness_receipt_path": str(path),
            "repo_head_sha": "",
        }
    return generation_binding_from_receipt(receipt, receipt_path=path)


def generation_binding_from_receipt(
    receipt: HoloIndexFreshnessReceipt | Mapping[str, Any] | None,
    *,
    receipt_path: Path | str | None = None,
) -> Mapping[str, str]:
    """Return generation fields from a loaded freshness receipt."""

    if receipt is None:
        return {
            "freshness_generation_id": "",
            "freshness_receipt_digest": "",
            "freshness_receipt_path": str(receipt_path or ""),
            "repo_head_sha": "",
        }
    if isinstance(receipt, HoloIndexFreshnessReceipt):
        generation_id = receipt.generation_id
        repo_head_sha = receipt.repo_head_sha
        digest = digest_json(receipt.to_dict())
    elif isinstance(receipt, Mapping):
        generation_id = str(receipt.get("generation_id") or "")
        repo_head_sha = str(receipt.get("repo_head_sha") or "")
        digest = digest_json(receipt)
    else:
        generation_id = ""
        repo_head_sha = ""
        digest = ""
    if receipt_path:
        disk_digest = file_digest(receipt_path)
        if disk_digest:
            digest = disk_digest
    return {
        "freshness_generation_id": generation_id,
        "freshness_receipt_digest": digest,
        "freshness_receipt_path": str(receipt_path or ""),
        "repo_head_sha": repo_head_sha,
    }


def normalize_query_hits(value: Any, *, source_class: str, limit: int = 8) -> list[HoloIndexQueryHit]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    hits: list[HoloIndexQueryHit] = []
    for item in value[: max(0, int(limit or 0))]:
        if not isinstance(item, Mapping):
            continue
        path = str(item.get("path") or item.get("file") or "").replace("\\", "/").strip()
        digest = str(item.get("digest") or item.get("content_digest") or "").strip()
        evidence_ref = str(item.get("evidence_ref") or "").strip()
        hits.append(
            HoloIndexQueryHit(
                path=path[:240],
                title=str(item.get("title") or "")[:160],
                score=item.get("score"),
                digest=digest[:96],
                evidence_ref=evidence_ref[:320],
                source_class=source_class,
            )
        )
    return hits


def build_query_receipt(
    *,
    source: str,
    source_class: str,
    query: str,
    result: Mapping[str, Any],
    require_generation: bool,
    generation_binding: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    """Normalize a query result into a deterministic receipt.

    If ``require_generation`` is true, any fresh/current success without a
    generation id is downgraded to UNKNOWN and marked as an INDEX_GAP.
    """

    binding = dict(generation_binding or {})
    if not binding:
        binding = {
            "freshness_generation_id": str(result.get("freshness_generation_id") or ""),
            "freshness_receipt_digest": str(result.get("freshness_receipt_digest") or ""),
            "freshness_receipt_path": str(result.get("freshness_receipt_path") or ""),
            "repo_head_sha": str(result.get("repo_head_sha") or ""),
        }
    freshness = str(result.get("freshness") or "UNKNOWN").upper()
    ok = result.get("ok") is True
    error = str(result.get("error") or "")
    stale_reasons: list[str] = []
    generation_id = str(binding.get("freshness_generation_id") or "")
    if require_generation and ok and freshness in FRESHNESS_STATES and not generation_id:
        freshness = "UNKNOWN"
        stale_reasons.append("missing_holoindex_generation_id")
        error = error or "missing_holoindex_generation_id"
    if (
        require_generation
        and ok
        and freshness in FRESHNESS_STATES
        and not str(binding.get("freshness_receipt_digest") or "")
    ):
        freshness = "UNKNOWN"
        stale_reasons.append("missing_holoindex_freshness_receipt_digest")
        error = error or "missing_holoindex_freshness_receipt_digest"
    hits = normalize_query_hits(result.get("hits"), source_class=source_class)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "source": str(source or ""),
        "source_class": str(source_class or ""),
        "ok": ok,
        "query": str(result.get("query") or query),
        "freshness": freshness,
        "hits": [hit.to_dict() for hit in hits],
        "error": error,
        "freshness_generation_id": generation_id,
        "freshness_receipt_digest": str(binding.get("freshness_receipt_digest") or ""),
        "freshness_receipt_path": str(binding.get("freshness_receipt_path") or ""),
        "repo_head_sha": str(binding.get("repo_head_sha") or ""),
        "index_gap_detected": bool(stale_reasons or result.get("index_gap_detected") is True),
        "stale_reasons": stale_reasons,
        "no_holoindex_reindex_performed": True,
    }
    return {**payload, "receipt_id": digest_json(payload)}


__all__ = [
    "FRESHNESS_STATES",
    "HoloIndexQueryHit",
    "HoloIndexQueryReceipt",
    "SCHEMA_VERSION",
    "SOURCE_CLASS_BRAIN",
    "SOURCE_CLASS_BREADCRUMB",
    "SOURCE_CLASS_CODEINDEX",
    "SOURCE_CLASS_HOLOINDEX",
    "SOURCE_CLASS_MEMEX",
    "build_query_receipt",
    "digest_json",
    "file_digest",
    "generation_binding_from_receipt",
    "load_generation_binding",
    "normalize_query_hits",
]
