"""Truthful, low-cardinality HoloIndex owner response normalization."""

from __future__ import annotations

import json
import math
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = "holoindex_query_service.v1"


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
    }
    if error in exact:
        return exact[error]
    if error.startswith("REPOSITORY") or error.startswith("REPO_"):
        return "repository_state_unproven"
    if error in {
        "UNAUTHORIZED",
        "AUTH_NOT_CONFIGURED",
        "HOLOINDEX_QUERY_SERVICE_TOKEN_TOO_SHORT",
    }:
        return "query_owner_authentication_failed"
    return "holoindex_owner_query_failed"


def flatten_hits(
    result: Mapping[str, Any],
    limit: int,
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
                (_hit_score(item), bucket_index, item_index, identity, normalized)
            )
    candidates.sort(key=lambda value: (-value[0], value[1], value[2], value[3]))
    return _deduplicated_hits(candidates, limit)


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
    hits: list[Mapping[str, Any]] = []
    seen: set[str] = set()
    for _score, _bucket, _position, identity, normalized in candidates:
        if identity in seen:
            continue
        seen.add(identity)
        hits.append(normalized)
        if len(hits) >= limit:
            break
    return hits


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
) -> dict[str, Any]:
    """Build a response that can never claim CURRENT on a failed operation."""
    from .holo_query_freshness_gate import normalize_binding

    stale = list(_dedupe([str(value) for value in reasons]))
    normalized_freshness = str(freshness or "UNKNOWN").upper()
    if not ok and normalized_freshness != "UNKNOWN":
        normalized_freshness = "STALE"
    if not ok and not stale:
        stale = [failure_reason(error)]
    return {
        "schema_version": SCHEMA_VERSION,
        "ok": ok,
        "source": "holoindex",
        "query": query,
        "freshness": normalized_freshness,
        "hits": list(hits),
        "error": error,
        "stale_reasons": stale,
        "index_gap_detected": bool(stale or not ok),
        "retrieval_mode": mode,
        "raw_result": dict(raw or {}),
        "latency_ms": max(0, int(latency_ms)),
        "no_holoindex_reindex_performed": True,
        **normalize_binding(binding),
    }


__all__ = ["SCHEMA_VERSION", "build_response", "failure_reason", "flatten_hits"]
