"""Truthful, low-cardinality HoloIndex owner response normalization."""

from __future__ import annotations

from copy import deepcopy
import json
import math
import time
from typing import Any, Mapping, Sequence

from holo_index.query_result_contract import validate_search_result
from holo_index.document_truth import current_truth_rank
from holo_index.retrieval_runtime_binding import (
    retrieval_ranker_binding,
    runtime_environment_binding,
)
from holo_index.tier0_retrieval import (
    infer_explicit_module_target,
    module_path_from_hit,
    module_tier0_paths,
)

from .holo_query_path_projection import project_result_hit

SCHEMA_VERSION = "holoindex_query_service.v1"
_REPLICA_PUBLIC_FIELDS = (
    "query_replica_descriptor_digest",
    "query_replica_generation_id",
    "query_replica_id",
    "query_replica_path_identity_digest",
)


def _dedupe(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value))


def failure_reason(error: str) -> str:
    """Map service errors to stable, low-cardinality stale reasons."""
    exact = {
        "QUERY_TIMEOUT": "holoindex_query_timeout",
        "QUERY_OWNER_POISONED": "query_owner_poisoned",
        "QUERY_QUEUE_TIMEOUT": "query_owner_queue_timeout",
        "OWNER_BUSY": "query_owner_busy",
        "SEMANTIC_BACKEND_UNAVAILABLE": "semantic_backend_unavailable",
        "HOLOINDEX_MODULE_INTENT_SNAPSHOT_UNAVAILABLE": (
            "module_intent_snapshot_unavailable"
        ),
        "HOLOINDEX_TIER0_INCOMPLETE": "module_tier0_incomplete",
        "HOLOINDEX_TIER0_LOOKUP_FAILED": "module_tier0_lookup_failed",
    }
    if error in exact:
        return exact[error]
    if error.startswith("REPOSITORY") or error.startswith("REPO_"):
        return "repository_state_unproven"
    if error in {
        "UNAUTHORIZED", "AUTH_NOT_CONFIGURED",
        "HOLOINDEX_QUERY_SERVICE_TOKEN_TOO_SHORT",
    }:
        return "query_owner_authentication_failed"
    return "holoindex_owner_query_failed"


def normalize_result_paths(
    result: Mapping[str, Any], repo_root: str, *, expected_query: str
) -> dict[str, Any]:
    """Validate the canonical result schema and project all hit paths."""
    validate_search_result(result, expected_query=expected_query)
    normalized: dict[str, Any] = {}
    try:
        for key, values in result.items():
            if key == "metadata":
                if not isinstance(values, Mapping):
                    raise ValueError("query_evidence_schema_invalid")
                normalized[key] = deepcopy(dict(values))
                continue
            normalized[key] = [
                project_result_hit(item, str(repo_root)) for item in values
            ]
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("query_evidence_copy_failed") from exc
    return normalized


def flatten_hits(
    result: Mapping[str, Any],
    limit: int,
    *,
    query: str = "",
) -> list[Mapping[str, Any]]:
    """Flatten typed buckets into one deterministic global score order."""
    candidates: list[tuple[float, int, int, str, Mapping[str, Any]]] = []
    buckets = (
        ("code_hits", "code"),
        ("wsp_hits", "wsp"),
        ("docs_hits", "docs"),
        ("knowledge_hits", "knowledge"),
        ("test_hits", "test"),
        ("skill_hits", "skill"),
        ("symbol_hits", "symbol"),
        ("work_ledger_hits", "work_ledger"),
    )
    for bucket_index, (key, kind) in enumerate(buckets):
        values = result.get(key)
        if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
            continue
        for item_index, item in enumerate(values):
            if not isinstance(item, Mapping):
                continue
            path = str(
                item.get("path") or item.get("file") or item.get("location") or ""
            ).replace("\\", "/").strip()
            identity = path or json.dumps(item, sort_keys=True, default=str)
            normalized = dict(item)
            normalized.setdefault("type", kind)
            candidates.append(
                (
                    _hit_score(item) + 10.0 * current_truth_rank(query, normalized),
                    bucket_index, item_index, identity, normalized,
                )
            )
    candidates.sort(key=lambda value: (-value[0], value[1], value[2], value[3]))
    metadata = result.get("metadata")
    attested_target = (
        metadata.get("tier0_module_target")
        if isinstance(metadata, Mapping) else None
    )
    candidates = _reserve_module_tier0(candidates, query, attested_target)
    return _deduplicated_hits(candidates, limit)


def _reserve_module_tier0(
    candidates: list[tuple[float, int, int, str, Mapping[str, Any]]],
    query: str,
    attested_target: object,
) -> list[tuple[float, int, int, str, Mapping[str, Any]]]:
    """Reserve one complete producer-attested exact Tier-0 pair."""
    target = attested_target if isinstance(attested_target, str) else ""
    target_paths = module_tier0_paths(target)
    inferred = infer_explicit_module_target(
        query, (candidate[4] for candidate in candidates)
    )
    if not target_paths or not inferred or inferred.casefold() != target.casefold():
        return candidates
    by_module: dict[str, dict[str, tuple]] = {}
    duplicate_modules: set[str] = set()
    for candidate in candidates:
        item = candidate[4]
        if item.get("retrieval_provenance") != "exact_metadata":
            continue
        module = module_path_from_hit(item)
        expected = {path.lower() for path in module_tier0_paths(module)}
        identity = candidate[3].replace("\\", "/").lower()
        if module and identity in expected:
            module_key = module.lower()
            module_rows = by_module.setdefault(module_key, {})
            if identity in module_rows:
                duplicate_modules.add(module_key)
            else:
                module_rows[identity] = candidate
    if len(by_module) != 1:
        return candidates
    module, by_path = next(iter(by_module.items()))
    if module != target.casefold() or module in duplicate_modules:
        return candidates
    if any(path.casefold() not in by_path for path in target_paths):
        return candidates
    reserved = [by_path[path.casefold()] for path in target_paths]
    reserved_ids = {candidate[3] for candidate in reserved}
    return [*reserved, *(c for c in candidates if c[3] not in reserved_ids)]


def _hit_score(item: Mapping[str, Any]) -> float:
    raw = item.get("score")
    if raw is None:
        raw = item.get("similarity")
    try:
        text = str(raw or "").strip()
        percent = text.endswith("%")
        score = float(text[:-1] if percent else text)
    except (TypeError, ValueError):
        return -math.inf
    if percent:
        score /= 100.0
    return score if math.isfinite(score) else -math.inf


def _deduplicated_hits(
    candidates: Sequence[tuple[float, int, int, str, Mapping[str, Any]]],
    limit: int,
) -> list[Mapping[str, Any]]:
    if limit <= 0:
        return []
    hits: list[Mapping[str, Any]] = []
    seen: set[str] = set()
    for _score, _bucket, _position, identity, normalized in candidates:
        normalized_identity = identity.replace("\\", "/").casefold()
        if normalized_identity in seen:
            continue
        seen.add(normalized_identity)
        hits.append(normalized)
        if len(hits) >= limit:
            break
    return hits


def _response_content(
    ok: bool, freshness: str, error: str, reasons: Sequence[str],
    hits: Sequence[Mapping[str, Any]], raw: Mapping[str, Any] | None,
) -> tuple[list[str], str, list[Mapping[str, Any]], dict[str, Any]]:
    stale = list(_dedupe([str(value) for value in reasons]))
    normalized = str(freshness or "UNKNOWN").upper()
    if not ok and normalized != "UNKNOWN":
        normalized = "STALE"
    if not ok and not stale:
        stale = [failure_reason(error)]
    response_hits = [] if not ok else list(hits)
    response_raw = {} if not ok else dict(raw or {})
    return stale, normalized, response_hits, response_raw


def build_response(
    *,
    ok: bool,
    query: str,
    freshness: str,
    error: str,
    reasons: Sequence[str] = (),
    binding: Mapping[str, Any] | None = None,
    raw: Mapping[str, Any] | None = None,
    hits: Sequence[Mapping[str, Any]] = (),
    mode: str = "unknown",
    latency_ms: int = 0,
    retrieval_runtime_ranker_digest: str = "",
    runtime_environment_digest: str = "",
    runtime_environment_exact_closure_verified: bool = False,
) -> dict[str, Any]:
    """Build a response that can never claim CURRENT on a failed operation."""
    from .holo_query_freshness_gate import normalize_binding

    stale, normalized_freshness, response_hits, response_raw = _response_content(
        ok, freshness, error, reasons, hits, raw
    )
    canonical_binding = normalize_binding(binding)
    # The absolute canonical receipt and private replica paths remain internal.
    canonical_binding["freshness_receipt_path"] = ""
    replica_binding = {
        key: str((binding or {}).get(key) or "") for key in _REPLICA_PUBLIC_FIELDS
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "ok": ok,
        "source": "holoindex",
        "query": query,
        "freshness": normalized_freshness,
        "hits": response_hits,
        "error": error,
        "stale_reasons": stale,
        "index_gap_detected": bool(stale or not ok),
        "retrieval_mode": mode,
        "raw_result": response_raw,
        "latency_ms": max(0, int(latency_ms)),
        "no_holoindex_reindex_performed": True,
        **retrieval_ranker_binding(retrieval_runtime_ranker_digest),
        **runtime_environment_binding(runtime_environment_digest),
        "runtime_environment_exact_closure_verified": (
            runtime_environment_exact_closure_verified is True
        ),
        **canonical_binding,
        **replica_binding,
    }


def semantic_canary_empty_response(result: Mapping[str, Any]) -> dict[str, Any]:
    """Convert an empty successful canary into an evidence-free failure."""
    return build_response(
        ok=False, query="", freshness="STALE", error="SEMANTIC_CANARY_EMPTY",
        reasons=("semantic_canary_empty",), binding=result,
        mode=str(result.get("retrieval_mode") or "unknown"),
        latency_ms=int(result.get("latency_ms") or 0),
        retrieval_runtime_ranker_digest=str(
            result.get("retrieval_runtime_ranker_digest") or ""
        ),
        runtime_environment_digest=str(
            result.get("runtime_environment_digest") or ""
        ),
        runtime_environment_exact_closure_verified=(
            result.get("runtime_environment_exact_closure_verified") is True
        ),
    )


def semantic_success_response(
    *, owner: Any, query: str, limit: int, raw: Mapping[str, Any],
    after: Any, started: float,
) -> Mapping[str, Any]:
    """Project, flatten, and bind one already-proven semantic success."""
    try:
        normalized = normalize_result_paths(raw, owner.repo_root, expected_query=query)
    except ValueError as exc:
        error = {
            "query_evidence_copy_failed": "QUERY_EVIDENCE_COPY_FAILED",
            "query_evidence_path_outside_repository": (
                "QUERY_EVIDENCE_PATH_OUTSIDE_REPOSITORY"
            ),
        }.get(str(exc), "QUERY_EVIDENCE_INVALID")
        return owner._failure(error, query=query)
    binding = dict(after.binding)
    binding.update(owner.replica_public_binding)
    return build_response(
        ok=True, query=query, freshness="CURRENT", error="", binding=binding,
        raw=normalized, hits=flatten_hits(normalized, limit, query=query),
        mode="semantic", latency_ms=int((time.monotonic() - started) * 1000),
        retrieval_runtime_ranker_digest=owner.retrieval_runtime_ranker_digest,
        runtime_environment_digest=owner.runtime_environment_digest,
        runtime_environment_exact_closure_verified=(
            owner.runtime_environment_exact_closure_verified
        ),
    )


__all__ = [
    "SCHEMA_VERSION", "build_response", "failure_reason", "flatten_hits",
    "normalize_result_paths", "semantic_canary_empty_response",
    "semantic_success_response",
]
