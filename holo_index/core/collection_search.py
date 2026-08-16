"""Bounded vector collection-search orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from holo_index.tier0_retrieval import infer_explicit_module_target, module_tier0_paths

from .backend_routing import resolve_backend_for_collection
from .collection_injections import (
    inject_module_tier0_candidates,
    inject_wsp_alias_candidates,
)


@dataclass(frozen=True)
class CollectionSearchOps:
    """Callbacks owned by ``search_engine`` and consumed by this pipeline."""

    strict_owner: Callable[[Any], bool]
    lexical_search: Callable[..., list[dict[str, Any]]]
    run_with_timeout: Callable[..., Any]
    resolve_alias_wsps: Callable[[str], list[str]]
    extract_wsp_numbers: Callable[[str], list[str]]
    score_result: Callable[..., dict[str, Any] | None]
    encode_timeout: float


def _collection_is_available(collection: Any, strict: bool) -> bool:
    """Return whether a collection can be searched, preserving strict errors."""
    if collection is None:
        return False
    try:
        count = collection.count()
    except Exception:
        if strict:
            raise RuntimeError("HOLOINDEX_STRICT_COLLECTION_COUNT_FAILED")
        return False
    if count:
        return True
    if strict:
        raise RuntimeError("HOLOINDEX_STRICT_COLLECTION_EMPTY")
    return False


def _collection_model(holo: Any, collection: Any) -> Any:
    """Resolve the routed embedder, then the legacy test-compatible model."""
    embedders = getattr(holo, "embedders", None) or None
    backend_key = resolve_backend_for_collection(
        getattr(collection, "name", "") or "",
        routing_active=bool(getattr(holo, "routing_active", False)),
        available_backends=embedders,
    )
    model = embedders.get(backend_key) if embedders is not None else None
    return model if model is not None else getattr(holo, "model", None)


def _encode_query(holo: Any, model: Any, query: str, ops: CollectionSearchOps) -> Any:
    """Encode under the owner deadline or the bounded non-owner timeout."""
    if ops.strict_owner(holo):
        return model.encode(query, show_progress_bar=False).tolist()
    return ops.run_with_timeout(
        lambda: model.encode(query, show_progress_bar=False).tolist(),
        timeout_sec=ops.encode_timeout,
        default=None,
        error_msg="model.encode() timed out",
    )


def _inject_exact_rows(
    holo: Any, collection: Any, query: str, kind: str,
    module_path: str | None, docs: list, metas: list, dists: list,
    ops: CollectionSearchOps,
) -> None:
    """Inject bounded module Tier-0 or WSP-alias rows."""
    if kind == "docs" and module_path:
        missing = inject_module_tier0_candidates(
            collection, docs, metas, dists, module_path,
            strict=ops.strict_owner(holo),
        )
        if missing:
            holo._log_agent_action(
                "Tier-0 module evidence incomplete: " + ", ".join(missing), "WARN"
            )
    if kind == "wsp":
        inject_wsp_alias_candidates(
            collection, docs, metas, dists, ops.resolve_alias_wsps(query),
            ops.extract_wsp_numbers,
        )


def _rank_rows(
    rows: tuple[list, list, list], query: str, kind: str, limit: int,
    doc_type_filter: str, module_path: str | None, ops: CollectionSearchOps,
) -> list[dict[str, Any]]:
    """Score, order, and remove internal sort keys from collection rows."""
    docs, metas, dists = rows
    ranked = []
    for doc, meta, distance in zip(docs, metas, dists):
        result = ops.score_result(kind, query, doc_type_filter, doc, meta, distance)
        if result is not None:
            ranked.append(result)
    ranked.sort(key=lambda item: item["_sort_key"], reverse=True)
    if kind == "docs" and module_path:
        order = {
            path.lower(): index
            for index, path in enumerate(module_tier0_paths(module_path))
        }
        ranked.sort(key=lambda item: order.get(
            str(item.get("path") or "").replace("\\", "/").lower(), len(order)
        ))
    return [
        {key: value for key, value in result.items() if key != "_sort_key"}
        for result in ranked[:limit]
    ]


def search_collection(
    holo: Any, collection: Any, query: str, limit: int, kind: str,
    doc_type_filter: str, module_path_hint: str | None,
    ops: CollectionSearchOps,
) -> list[dict[str, Any]]:
    """Search one collection with strict-owner and truthful fallback behavior."""
    if limit <= 0:
        return []
    strict = ops.strict_owner(holo)
    if not _collection_is_available(collection, strict):
        return []
    model = _collection_model(holo, collection)
    if model is None:
        if strict:
            raise RuntimeError("HOLOINDEX_STRICT_EMBEDDING_MODEL_UNAVAILABLE")
        holo._log_agent_action(
            "Embedding model not available - semantic search degraded to lexical. "
            "Knowledge/paper results may be missing. Check HOLO_MODEL_IMPORT_TIMEOUT if cold-process.",
            "WARN",
        )
        return ops.lexical_search(holo, collection, query, limit, kind, doc_type_filter)
    embedding = _encode_query(holo, model, query, ops)
    if embedding is None:
        if strict:
            raise RuntimeError("HOLOINDEX_STRICT_EMBEDDING_FAILED")
        holo._log_agent_action(
            "Encoding timed out - falling back to lexical search", "WARN"
        )
        return ops.lexical_search(holo, collection, query, limit, kind, doc_type_filter)
    results = collection.query(query_embeddings=[embedding], n_results=limit)
    rows = tuple(results.get(name, [[]])[0] for name in (
        "documents", "metadatas", "distances"
    ))
    if kind == "docs" and not module_path_hint:
        module_path_hint = infer_explicit_module_target(query, rows[1])
    _inject_exact_rows(holo, collection, query, kind, module_path_hint, *rows, ops)
    return _rank_rows(
        rows, query, kind, limit, doc_type_filter, module_path_hint, ops
    )


__all__ = ["CollectionSearchOps", "search_collection"]
