"""S62: Canonical WSP 96 Annex A.2/A.3 holo_search adapter for S1.

This module provides the canonical envelope construction for S1's
`holo_search` tool. It is intentionally DECOUPLED from the FastMCP
decoration in `server.py` so:

  1. The conversion logic (similarity scaling, envelope shape, hit
     unification, error envelopes) can be unit-tested without standing up
     a FastMCP server.
  2. The legacy `semantic_code_search` tool registration in `server.py`
     is not disturbed — back-compat callers continue to receive the
     legacy flat shape.

WSP anchors:
  - WSP 96 Annex A.1 (S1 surface ownership)
  - WSP 96 Annex A.2 (canonical request schema)
  - WSP 96 Annex A.3 (canonical response envelope)
  - WSP 97 (truth distinction — no fabricated similarity)

MCPA6 drift IDs closed by this adapter:
  - D1: tool name `holo_search` (added alongside legacy `semantic_code_search`)
  - D2: canonical envelope `{status, data, meta}`
  - D3: unified `hits[]` array with `type` discriminator
  - D4: `doc_type_filter` request field (canonical name)
  - D5: relevance transformed via `1/(1+distance)` not raw distance
  - D6: quantum/bell-state decoration excluded from canonical envelope
  - D7: `foundup_id` request field accepted (echoed; not enforced — Slice 6)
  - D8: `include_shared` request field accepted (Annex A.2 semantics)
  - D9: empty-query rejection with `EMPTY_QUERY` code
  - D10: `limit` default 10, range 1..50 with truthful clamp warning
  - D11: `meta.surface = "S1"`, `meta.tool = "holo_search"`, `meta.source`
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ============================================================================
# Annex A constants
# ============================================================================

S1_SURFACE_ID = "S1"
"""Surface tag per WSP 96 Annex A.1 — emitted in every meta block."""

ANNEX_A_LIMIT_MAX = 50
"""Annex A.2: hard upper bound on `limit`."""

ANNEX_A_LIMIT_DEFAULT = 10
"""Annex A.2: default `limit` when none supplied."""

ANNEX_A_FALLBACK_RELEVANCE_CAP = 0.6
"""Annex A.3: lexical fallback caps relevance at 0.6."""


# ============================================================================
# Helpers
# ============================================================================


def distance_to_similarity(distance: Any) -> Optional[float]:
    """Convert ChromaDB cosine distance to canonical Annex A.3 relevance.

    Annex A.3: ``relevance = 1 / (1 + distance)``. The formula is applied
    uniformly — ChromaDB cosine distance ranges over [0..2], so a value
    of 1.0 means "orthogonal" (similarity 0.5), not "perfect match".
    Special-casing already-similarity inputs would be ambiguous because
    the engine S1 wraps emits raw `distance`, not pre-converted similarity.

    Surfaces that cannot compute a similarity MUST omit the field rather
    than fabricate a value (WSP 97). Returns None when the input is not
    a usable numeric distance — callers MUST treat None as "omit".

    Special cases:
      - Non-numeric input: returns None.
      - Negative input: returns None (distances are non-negative).
      - Input == 0: returns 1.0 (perfect match per the formula).
    """
    try:
        d = float(distance)
    except (TypeError, ValueError):
        return None
    if d < 0:
        return None
    return 1.0 / (1.0 + d)


def build_ok_envelope(
    *,
    query: str,
    doc_type_filter: str,
    foundup_id: Optional[str],
    include_shared: bool,
    hits: List[dict],
    engine_metadata: Dict[str, Any],
    retrieval_mode: str,
    source: str,
    confidence: float,
    warnings: List[str],
) -> dict:
    """Build the WSP 96 Annex A.3 canonical ok envelope for S1 holo_search."""
    metadata: Dict[str, Any] = {
        "retrieval_mode": retrieval_mode,
        "engine_version": engine_metadata.get("engine_version", "holoindex"),
        "collections_searched": engine_metadata.get("collections_searched", []),
        "warnings": warnings,
    }
    # Pass through extra engine fields without overriding canonical keys.
    for k, v in engine_metadata.items():
        if k not in metadata:
            metadata[k] = v

    return {
        "status": "ok",
        "data": {
            "query": query,
            "doc_type_filter": doc_type_filter,
            "foundup_id": foundup_id,
            # Annex A.2: include_shared only meaningful with foundup_id.
            "include_shared": include_shared if foundup_id is not None else None,
            "hits": hits,
            "hit_count": len(hits),
            "metadata": metadata,
        },
        "meta": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "tool": "holo_search",
            "surface": S1_SURFACE_ID,
            "confidence": confidence,
        },
    }


def build_error_envelope(
    *,
    code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
) -> dict:
    """Build the WSP 96 Annex A.3 canonical error envelope for S1 holo_search."""
    error_obj: Dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        error_obj["details"] = details
    return {
        "status": "error",
        "error": error_obj,
        "meta": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool": "holo_search",
            "surface": S1_SURFACE_ID,
        },
    }


def _safe_truncate(value: Any, n: int = 200) -> str:
    """Truncate any value to n chars; non-string inputs become empty strings."""
    if not isinstance(value, str):
        return ""
    return value[:n]


def _hit_relevance(hit: dict) -> Optional[float]:
    """Extract the engine's relevance signal and convert to canonical similarity.

    Tries `distance` first (raw cosine distance from the engine), then falls
    back to `similarity` (already-transformed value). Returns None when the
    engine produced no usable signal.
    """
    if "distance" in hit:
        return distance_to_similarity(hit["distance"])
    if "similarity" in hit:
        return distance_to_similarity(hit["similarity"])
    return None


def _unify_hits(results: dict, bounded_limit: int) -> List[dict]:
    """Flatten results from multiple collection-specific hit lists into a
    single canonical `hits[]` array with `type` discriminator.

    Anchored to Annex A.3 hit shape:
      {type, path, title?, preview, relevance, line_num?, summary?}

    Hits without a usable relevance signal omit the `relevance` field
    rather than fabricate one (WSP 97).
    """
    unified: List[dict] = []

    # Code hits
    for hit in (results.get("code_hits") or [])[:bounded_limit]:
        item: dict = {
            "type": "code",
            "path": hit.get("path") or hit.get("location"),
            "preview": _safe_truncate(hit.get("preview") or hit.get("content", "")),
        }
        line = hit.get("line")
        if line is not None:
            item["line_num"] = line
        rel = _hit_relevance(hit)
        if rel is not None:
            item["relevance"] = rel
        unified.append(item)

    # WSP hits
    for hit in (results.get("wsp_hits") or [])[:bounded_limit]:
        item = {
            "type": "wsp",
            "path": hit.get("path"),
            "title": hit.get("title") or hit.get("protocol"),
            "preview": _safe_truncate(hit.get("summary") or hit.get("content", "")),
        }
        summary = hit.get("summary")
        if summary:
            item["summary"] = _safe_truncate(summary)
        rel = _hit_relevance(hit)
        if rel is not None:
            item["relevance"] = rel
        unified.append(item)

    # Test hits
    for hit in (results.get("test_hits") or [])[:bounded_limit]:
        item = {
            "type": "test",
            "path": hit.get("path"),
            "preview": _safe_truncate(hit.get("preview") or hit.get("content", "")),
        }
        rel = _hit_relevance(hit)
        if rel is not None:
            item["relevance"] = rel
        unified.append(item)

    # Skill hits
    for hit in (results.get("skill_hits") or [])[:bounded_limit]:
        item = {
            "type": "skill",
            "path": hit.get("path"),
            "title": hit.get("name"),
            "preview": _safe_truncate(hit.get("preview") or hit.get("content", "")),
        }
        rel = _hit_relevance(hit)
        if rel is not None:
            item["relevance"] = rel
        unified.append(item)

    # Docs / knowledge hits (post-CFZ4 collection separation)
    for kind, key in (("docs", "docs_hits"), ("knowledge", "knowledge_hits")):
        for hit in (results.get(key) or [])[:bounded_limit]:
            item = {
                "type": kind,
                "path": hit.get("path"),
                "title": hit.get("title"),
                "preview": _safe_truncate(hit.get("summary") or hit.get("content", "")),
            }
            summary = hit.get("summary")
            if summary:
                item["summary"] = _safe_truncate(summary)
            rel = _hit_relevance(hit)
            if rel is not None:
                item["relevance"] = rel
            unified.append(item)

    # Sort by relevance desc; missing-relevance hits sort to the end.
    unified.sort(
        key=lambda x: x.get("relevance", -1.0),
        reverse=True,
    )
    return unified[:bounded_limit]


# ============================================================================
# Canonical adapter (no FastMCP dependency)
# ============================================================================


async def canonical_holo_search(
    holo_index: Any,
    *,
    query: str = "",
    limit: int = 10,
    doc_type_filter: str = "all",
    foundup_id: Optional[str] = None,
    include_shared: bool = True,
) -> dict:
    """S62: WSP 96 Annex A.2/A.3 canonical holo_search.

    Standalone async function; the FastMCP `@app.tool()` wrapper in
    ``server.py`` is a thin shim around this. Tests can import and call this
    directly without standing up a FastMCP server.

    Args:
        holo_index: A backend object with a synchronous ``.search(query,
            limit, doc_type_filter)`` method. The real S1 server passes
            ``HoloIndex()``; tests pass a stub.
        query: Annex A.2 — required, non-empty.
        limit: Annex A.2 — default 10, range 1..50 (clamped with warning).
        doc_type_filter: Annex A.2 — enum.
        foundup_id: Annex A.2 — federation tenant scope (echoed; not
            enforced at S1 — tracked for MCPA1 Slice 6).
        include_shared: Annex A.2 — federation share flag.

    Returns:
        Annex A.3 canonical envelope.
    """
    warnings: List[str] = []

    # Annex A.2 limit clamp [1..50]
    try:
        requested_limit = int(limit) if limit is not None else ANNEX_A_LIMIT_DEFAULT
    except (TypeError, ValueError):
        requested_limit = ANNEX_A_LIMIT_DEFAULT
        warnings.append(
            f"Invalid limit value {limit!r}; defaulted to "
            f"{ANNEX_A_LIMIT_DEFAULT} per WSP 96 Annex A.2."
        )
    bounded_limit = max(1, min(requested_limit, ANNEX_A_LIMIT_MAX))
    if bounded_limit != requested_limit:
        warnings.append(
            f"limit clamped to Annex A.2 range (1..{ANNEX_A_LIMIT_MAX}): "
            f"requested={requested_limit}, applied={bounded_limit}."
        )

    # Federation honesty (Slice 6 deferred)
    if foundup_id is not None:
        warnings.append(
            "foundup_id received; tenant scoping not yet enforced at S1 "
            "(deferred to MCPA1 Slice 6 / federation auth)."
        )

    # Empty-query rejection (Annex A.2 + WSP 97)
    if not query or not query.strip():
        return build_error_envelope(
            code="EMPTY_QUERY",
            message=(
                "Query cannot be empty. WSP 96 Annex A.2 requires a "
                "non-empty `query` field."
            ),
        )

    # Real backend call
    try:
        results = holo_index.search(
            query, limit=bounded_limit, doc_type_filter=doc_type_filter
        )
    except Exception as e:
        return build_error_envelope(
            code="BACKEND_UNAVAILABLE",
            message=f"HoloIndex backend error: {e}",
        )

    if not isinstance(results, dict):
        return build_error_envelope(
            code="BACKEND_UNAVAILABLE",
            message=(
                f"HoloIndex backend returned non-dict result "
                f"({type(results).__name__}); cannot adapt to Annex A.3."
            ),
        )

    unified_hits = _unify_hits(results, bounded_limit)

    return build_ok_envelope(
        query=query,
        doc_type_filter=doc_type_filter,
        foundup_id=foundup_id,
        include_shared=include_shared,
        hits=unified_hits,
        engine_metadata=results.get("metadata", {}) or {},
        retrieval_mode="semantic",
        source="holoindex",
        confidence=0.8,
        warnings=warnings,
    )
