"""Generation-bound HoloIndex query receipts.

WSP 97: a query result is only freshness evidence when it is bound to the
HoloIndex generation that served it. Query receipts are read-only artifacts;
they never trigger re-indexing or mutate HoloIndex.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from holo_index.freshness_receipt import (
    HoloIndexFreshnessReceipt,
    freshness_receipt_path,
    load_freshness_receipt,
)


SCHEMA_VERSION = "holoindex_query_receipt.v1"
SEMANTIC_EVIDENCE_SCHEMA_VERSION = "holoindex_semantic_evidence.v1"
MAX_SEMANTIC_EVIDENCE_BYTES = 4 * 1024 * 1024
SEMANTIC_EVIDENCE_BUCKETS = (
    "code_hits",
    "wsp_hits",
    "test_hits",
    "skill_hits",
    "symbol_hits",
    "docs_hits",
    "knowledge_hits",
    "work_ledger_hits",
)
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
    repo_root_digest: str = ""
    workspace_repo_head_sha: str = ""
    authority_repo_head_sha: str = ""
    authority_repo_root_digest: str = ""
    workspace_overlay_present: bool = False
    semantic_evidence_authority: str = ""
    no_authority_worktree_mutation_performed: bool = False
    index_gap_detected: bool = False
    stale_reasons: list[str] = field(default_factory=list)
    no_holoindex_reindex_performed: bool = True
    retrieval_runtime_ranker_digest: str = ""
    receipt_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["hits"] = [hit.to_dict() for hit in self.hits]
        return data


def digest_json(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def canonical_semantic_evidence(
    raw_result: Any,
    *,
    max_bytes: int = MAX_SEMANTIC_EVIDENCE_BYTES,
) -> tuple[str, str, int]:
    """Serialize the exact semantic evidence RedDog may consume."""

    source = raw_result if isinstance(raw_result, Mapping) else {}
    evidence: dict[str, Any] = {
        "schema_version": SEMANTIC_EVIDENCE_SCHEMA_VERSION,
    }
    count = 0
    for bucket in SEMANTIC_EVIDENCE_BUCKETS:
        value = source.get(bucket)
        items = (
            [dict(item) for item in value if isinstance(item, Mapping)]
            if isinstance(value, Sequence) and not isinstance(value, (str, bytes))
            else []
        )
        evidence[bucket] = items
        count += len(items)
    metadata = source.get("metadata")
    evidence["metadata"] = dict(metadata) if isinstance(metadata, Mapping) else {}
    payload = json.dumps(
        evidence,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )
    if len(payload.encode("utf-8")) > max(0, int(max_bytes)):
        raise ValueError("semantic_evidence_too_large")
    digest = "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return payload, digest, count


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
                score=(
                    str(item.get("score"))
                    if item.get("score") is not None
                    else ""
                ),
                digest=digest[:96],
                evidence_ref=evidence_ref[:320],
                source_class=source_class,
            )
        )
    return hits


def _result_binding(
    result: Mapping[str, Any],
    generation_binding: Mapping[str, Any] | None,
) -> dict[str, Any]:
    binding = dict(generation_binding or {})
    if binding:
        return binding
    return {
        "freshness_generation_id": str(
            result.get("freshness_generation_id") or ""
        ),
        "freshness_receipt_digest": str(
            result.get("freshness_receipt_digest") or ""
        ),
        "freshness_receipt_path": str(
            result.get("freshness_receipt_path") or ""
        ),
        "repo_head_sha": str(result.get("repo_head_sha") or ""),
        "repo_root_digest": str(result.get("repo_root_digest") or ""),
    }


def _authority_binding(result: Mapping[str, Any]) -> dict[str, Any]:
    if not result.get("authority_repo_root_digest"):
        return {}
    return {
        "workspace_repo_head_sha": str(
            result.get("workspace_repo_head_sha") or ""
        ),
        "authority_repo_head_sha": str(
            result.get("authority_repo_head_sha") or ""
        ),
        "authority_repo_root_digest": str(
            result.get("authority_repo_root_digest") or ""
        ),
        "workspace_overlay_present": (
            result.get("workspace_overlay_present") is True
        ),
        "semantic_evidence_authority": str(
            result.get("semantic_evidence_authority") or ""
        ),
        "no_authority_worktree_mutation_performed": (
            result.get("no_authority_worktree_mutation_performed") is True
        ),
    }


def _result_stale_reasons(result: Mapping[str, Any]) -> list[str]:
    raw_reasons = result.get("stale_reasons")
    if isinstance(raw_reasons, (str, bytes)) or not isinstance(
        raw_reasons,
        Sequence,
    ):
        return []
    reasons: list[str] = []
    for value in raw_reasons:
        reason = str(value or "").strip()
        if reason and reason not in reasons:
            reasons.append(reason)
    return reasons


def _observed_latency_ms(value: Any) -> float | None:
    if value is None:
        return None
    try:
        latency = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(latency) or latency < 0:
        return None
    return round(latency, 3)


def _enforce_generation_binding(
    *,
    binding: Mapping[str, Any],
    require_generation: bool,
    ok: bool,
    freshness: str,
    error: str,
    stale_reasons: list[str],
) -> tuple[str, str]:
    if not (require_generation and ok and freshness in FRESHNESS_STATES):
        return freshness, error
    missing_generation = "missing_holoindex_generation_id"
    if not str(binding.get("freshness_generation_id") or ""):
        stale_reasons.append(missing_generation)
        return "UNKNOWN", error or missing_generation
    missing_digest = "missing_holoindex_freshness_receipt_digest"
    if not str(binding.get("freshness_receipt_digest") or ""):
        stale_reasons.append(missing_digest)
        return "UNKNOWN", error or missing_digest
    return freshness, error


def _per_target_verdicts(value: Any) -> list[dict[str, Any]] | None:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return None
    return [
        {
            "target": str(item.get("target") or ""),
            "source_class": str(item.get("source_class") or ""),
            "verdict": str(item.get("verdict") or ""),
            "matched_evidence_refs": [
                str(ref)
                for ref in (
                    item.get("matched_evidence_refs")
                    if not isinstance(
                        item.get("matched_evidence_refs"),
                        (str, bytes),
                    )
                    and isinstance(item.get("matched_evidence_refs"), Sequence)
                    else ()
                )
            ],
        }
        for item in value
        if isinstance(item, Mapping)
    ]


def build_query_receipt(
    *,
    source: str,
    source_class: str,
    query: str,
    result: Mapping[str, Any],
    require_generation: bool,
    generation_binding: Mapping[str, Any] | None = None,
    hit_limit: int = 8,
) -> Mapping[str, Any]:
    """Normalize a query result into a deterministic receipt.

    If ``require_generation`` is true, any fresh/current success without a
    generation id is downgraded to UNKNOWN and marked as an INDEX_GAP.
    """

    binding = _result_binding(result, generation_binding)
    freshness = str(result.get("freshness") or "UNKNOWN").upper()
    ok = result.get("ok") is True
    error = str(result.get("error") or "")
    stale_reasons = _result_stale_reasons(result)
    freshness, error = _enforce_generation_binding(
        binding=binding,
        require_generation=require_generation,
        ok=ok,
        freshness=freshness,
        error=error,
        stale_reasons=stale_reasons,
    )
    generation_id = str(binding.get("freshness_generation_id") or "")
    hits = normalize_query_hits(
        result.get("hits"), source_class=source_class, limit=hit_limit
    )
    _, semantic_evidence_digest, semantic_evidence_count = (
        canonical_semantic_evidence(result.get("raw_result"))
    )
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
        "index_gap_detected": bool(
            stale_reasons
            or result.get("index_gap_detected") is True
            or (require_generation and ok and freshness not in FRESHNESS_STATES)
        ),
        "stale_reasons": stale_reasons,
        "no_holoindex_reindex_performed": True,
        "retrieval_runtime_ranker_digest": str(
            result.get("retrieval_runtime_ranker_digest") or ""
        ),
        "semantic_evidence_digest": semantic_evidence_digest,
        "semantic_evidence_count": semantic_evidence_count,
        "observed_latency_ms": _observed_latency_ms(result.get("latency_ms")),
    }
    root_digest = str(binding.get("repo_root_digest") or "")
    if root_digest:
        payload["repo_root_digest"] = root_digest
    payload.update(_authority_binding(result))
    retrieval_verdict = str(result.get("retrieval_verdict") or "").strip()
    if retrieval_verdict:
        payload["retrieval_verdict"] = retrieval_verdict
    per_target = _per_target_verdicts(result.get("per_target_retrieval_verdicts"))
    if per_target is not None:
        payload["per_target_retrieval_verdicts"] = per_target
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
    "MAX_SEMANTIC_EVIDENCE_BYTES",
    "SEMANTIC_EVIDENCE_BUCKETS",
    "SEMANTIC_EVIDENCE_SCHEMA_VERSION",
    "build_query_receipt",
    "canonical_semantic_evidence",
    "digest_json",
    "file_digest",
    "generation_binding_from_receipt",
    "load_generation_binding",
    "normalize_query_hits",
]
