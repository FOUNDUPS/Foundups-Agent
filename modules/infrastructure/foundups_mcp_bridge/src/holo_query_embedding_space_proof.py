"""Embedding-space and resident-generation proof for the HoloIndex owner."""

from __future__ import annotations

from typing import Any, Mapping

from holo_index.embedding_space import normalized_embedding_space_map

from .holo_query_freshness_gate import BASELINE_COLLECTIONS, FreshnessSnapshot


def embedding_space_evidence(
    owner: Any,
    raw: Mapping[str, Any],
    snapshot: FreshnessSnapshot,
) -> tuple[str, tuple[str, ...]]:
    metadata_value = raw.get("metadata")
    metadata = metadata_value if isinstance(metadata_value, Mapping) else {}
    reported = normalized_embedding_space_map(
        metadata.get("collection_embedding_space_map")
    )
    runtime = normalized_embedding_space_map(
        getattr(owner._backend, "collection_embedding_space_map", None)
    )
    reasons: list[str] = []
    mismatched = False
    for name in sorted(BASELINE_COLLECTIONS):
        expected = snapshot.embedding_spaces.get(name, "")
        active = runtime.get(name, "")
        reported_value = reported.get(name, "")
        if not expected or not active or not reported_value:
            reasons.append(f"embedding_space_unproven:{name}")
            continue
        if active != expected:
            mismatched = True
            reasons.append(f"embedding_space_mismatch:{name}")
        if reported_value != active:
            mismatched = True
            reasons.append(f"embedding_space_evidence_mismatch:{name}")
    if mismatched:
        return "EMBEDDING_SPACE_MISMATCH", tuple(reasons)
    if reasons:
        return "EMBEDDING_SPACE_UNPROVEN", tuple(reasons)
    return "", ()


def _generation_pin(snapshot: FreshnessSnapshot) -> tuple[str, str, str]:
    values = (
        snapshot.binding.get("freshness_generation_id", ""),
        snapshot.binding.get("freshness_receipt_digest", ""),
        snapshot.binding.get("repo_head_sha", ""),
    )
    return values


def pin_backend_generation(owner: Any, snapshot: FreshnessSnapshot) -> None:
    if getattr(owner, "_backend_generation_pin", None) is None:
        owner._backend_generation_pin = _generation_pin(snapshot)


def backend_generation_failure(
    owner: Any,
    snapshot: FreshnessSnapshot,
    *,
    query: str,
    started: float,
) -> Mapping[str, Any] | None:
    pinned = getattr(owner, "_backend_generation_pin", None)
    if pinned is None or pinned == _generation_pin(snapshot):
        return None
    owner._poisoned.set()
    return owner._failure(
        "QUERY_OWNER_POISONED",
        query=query,
        snapshot=snapshot,
        reasons=("owner_backend_generation_changed",),
        started=started,
    )


__all__ = [
    "backend_generation_failure",
    "embedding_space_evidence",
    "pin_backend_generation",
]
