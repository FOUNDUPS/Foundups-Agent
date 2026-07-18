"""Canonical WSP test-registry indexing with completeness evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from holo_index.core.indexing_engine import (
    IndexResult,
    resolve_foundup_metadata,
    source_file_manifest_digest,
    source_manifest_digest,
)
from holo_index.source_scope import (
    CanonicalSourceScopeError,
    canonical_source_scope_id,
    filter_git_tracked_files,
)


COLLECTION_NAME = "navigation_tests"


def _load_entries(
    registry_path: Path,
) -> tuple[Any, list[dict[str, Any]], int, int]:
    registry_data = json.loads(registry_path.read_text(encoding="utf-8"))
    raw_entries: Any = None
    if isinstance(registry_data, dict):
        if "tests" in registry_data:
            raw_entries = registry_data.get("tests")
        elif registry_data and all(
            isinstance(value, dict) for value in registry_data.values()
        ):
            raw_entries = list(registry_data.values())
    elif isinstance(registry_data, list):
        raw_entries = registry_data
    if not isinstance(raw_entries, list):
        return registry_data, [], 0, 1
    entries = [entry for entry in raw_entries if isinstance(entry, dict)]
    invalid_count = len(raw_entries) - len(entries)
    return registry_data, entries, len(raw_entries), invalid_count


def _record(holo: Any, entry: dict[str, Any], idx: int) -> tuple[str, list[float], str, dict[str, Any]]:
    test_id = str(entry.get("id") or f"test_{idx}")
    path = str(entry.get("path") or "")
    description = str(entry.get("description") or "")
    raw_capabilities = entry.get("capabilities", [])
    capabilities = (
        ", ".join(str(value) for value in raw_capabilities)
        if isinstance(raw_capabilities, list)
        else str(raw_capabilities or "")
    )
    execution_type = str(entry.get("execution_type") or "unknown")
    document = chr(10).join(
        (
            f"Test: {test_id}",
            f"Type: {execution_type}",
            f"Capabilities: {capabilities}",
            f"Description: {description}",
        )
    )
    test_path = Path(path) if Path(path).is_absolute() else holo.project_root / path
    federation = resolve_foundup_metadata(test_path, holo.project_root)
    digest = source_manifest_digest(entry)
    metadata = {
        "test_id": test_id,
        "path": path,
        "description": description[:1000],
        "capabilities": capabilities,
        "type": "test",
        "priority": 8,
        "source_content_digest": digest,
        "foundup_id": federation["foundup_id"],
        "tenant_id": federation["tenant_id"],
        "source_scope": federation["source_scope"],
        "external_repo": federation["external_repo"],
    }
    stable_id = f"test_{digest.removeprefix('sha256:')[:24]}_{idx}"
    return stable_id, holo._get_embedding(document), document, metadata


def _registry_source_manifest(holo: Any, registry_path: Path) -> tuple[str, str]:
    try:
        tracked_registry = filter_git_tracked_files(
            holo.project_root,
            [registry_path],
        )
    except CanonicalSourceScopeError as exc:
        return "", str(exc)
    if not tracked_registry:
        return "", "Canonical test registry is not tracked by Git"
    try:
        digest = source_file_manifest_digest(
            tracked_registry,
            project_root=holo.project_root,
        )
    except OSError as exc:
        return "", f"Canonical test registry could not be read: {exc}"
    return digest, ""


def _registry_failure(
    holo: Any,
    warning: str,
    *,
    level: str,
    discovered_count: int = 0,
    processed_count: int = 0,
    failed_count: int = 0,
    source_manifest_digest: str = "",
    source_scope_id: str = "",
) -> IndexResult:
    holo._log_agent_action(warning, level)
    return IndexResult(
        discovered_count=discovered_count,
        indexed_count=0,
        collection_name=COLLECTION_NAME,
        warning=warning,
        processed_count=processed_count,
        failed_count=failed_count,
        source_manifest_digest=source_manifest_digest,
        source_scope_id=source_scope_id,
    )


def _write_registry_entries(
    holo: Any,
    entries: list[dict[str, Any]],
    *,
    declared_count: int,
    manifest_digest: str,
) -> IndexResult:
    holo._log_agent_action(f"Indexing {len(entries)} test entries...", "INDEX")
    records = [_record(holo, entry, idx) for idx, entry in enumerate(entries, 1)]
    ids, embeddings, documents, metadatas = map(list, zip(*records))
    collection = holo._reset_collection(COLLECTION_NAME)
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )
    holo.test_collection = collection
    holo._log_agent_action(
        f"Test Registry index refreshed on SSD: {len(ids)} entries",
        "OK",
    )
    return IndexResult(
        discovered_count=declared_count,
        indexed_count=len(ids),
        collection_name=COLLECTION_NAME,
        processed_count=declared_count,
        source_manifest_digest=manifest_digest,
        source_scope_id=canonical_source_scope_id(COLLECTION_NAME),
    )


def _malformed_registry_failure(
    holo: Any,
    *,
    entries: list[dict[str, Any]],
    declared_count: int,
    invalid_count: int,
    manifest_digest: str,
) -> IndexResult:
    entry_label = "entry" if invalid_count == 1 else "entries"
    warning = (
        f"WSP Test Registry contains {invalid_count} malformed test {entry_label}"
    )
    return _registry_failure(
        holo,
        warning,
        level="ERROR",
        discovered_count=declared_count,
        processed_count=len(entries),
        failed_count=invalid_count,
        source_manifest_digest=manifest_digest,
        source_scope_id=canonical_source_scope_id(COLLECTION_NAME),
    )


def index_test_registry(holo: Any) -> IndexResult:
    """Index every valid registry row or fail without resetting the collection."""

    registry_path = holo.project_root / "WSP_knowledge" / "WSP_Test_Registry.json"
    if not registry_path.exists():
        return _registry_failure(
            holo,
            "WSP_Test_Registry.json not found",
            level="WARN",
        )
    try:
        registry_data, entries, declared_count, invalid_count = _load_entries(
            registry_path
        )
    except Exception as exc:
        return _registry_failure(
            holo,
            f"Failed to load test registry: {exc}",
            level="ERROR",
        )
    manifest_digest, manifest_error = _registry_source_manifest(holo, registry_path)
    if manifest_error:
        return _registry_failure(
            holo,
            manifest_error,
            level="ERROR",
            discovered_count=declared_count,
            failed_count=1,
        )
    if invalid_count:
        return _malformed_registry_failure(
            holo,
            entries=entries,
            declared_count=declared_count,
            invalid_count=invalid_count,
            manifest_digest=manifest_digest,
        )
    if not entries:
        return _registry_failure(
            holo,
            "WSP Test Registry has no valid test entries",
            level="WARN",
        )
    return _write_registry_entries(
        holo,
        entries,
        declared_count=declared_count,
        manifest_digest=manifest_digest,
    )


__all__ = ["index_test_registry"]
