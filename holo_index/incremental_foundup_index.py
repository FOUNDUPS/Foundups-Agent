"""Incremental per-FoundUp HoloIndex planning primitives.

This phase creates deterministic IDs and scoped plans only. It does not call
ChromaDB, run HoloIndex indexing, delete collections, or mutate any semantic
store.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import PurePosixPath
from typing import Iterable, Mapping

from holo_index.freshness_receipt import ALL_COLLECTIONS, collections_for_path


SCHEMA_VERSION = "holoindex_incremental_foundup_index.v1"

DECISION_PLANNED = "PLANNED"
DECISION_NO_INDEXABLE_CHANGES = "NO_INDEXABLE_CHANGES"
DECISION_REJECTED = "REJECTED"

OP_UPSERT_PATH = "upsert_path"
OP_DELETE_PATH_ID = "delete_path_id"

FOUNDUP_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
SYMBOL_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,127}$")


@dataclass(frozen=True)
class IncrementalFoundUpIndexOperation:
    """A non-mutating operation for a future incremental index writer."""

    operation: str
    collection: str
    foundup_id: str
    repo_relative_path: str
    stable_id: str
    delete_where: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class IncrementalFoundUpIndexPlan:
    """Plan for refreshing a FoundUp-scoped subset of HoloIndex."""

    schema_version: str
    decision: str
    foundup_id: str
    foundup_root: str
    changed_paths: list[str] = field(default_factory=list)
    removed_paths: list[str] = field(default_factory=list)
    target_collections: list[str] = field(default_factory=list)
    operations: list[IncrementalFoundUpIndexOperation] = field(default_factory=list)
    rejection_reasons: list[str] = field(default_factory=list)
    no_reindex_performed: bool = True
    no_collection_mutation_performed: bool = True
    no_runtime_reindex_performed: bool = True

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["operations"] = [operation.to_dict() for operation in self.operations]
        return payload


def validate_foundup_id(foundup_id: str) -> bool:
    return bool(FOUNDUP_ID_RE.fullmatch(str(foundup_id or "")))


def foundup_root_for_id(foundup_id: str) -> str:
    if not validate_foundup_id(foundup_id):
        raise ValueError("invalid_foundup_id")
    return f"modules/foundups/{foundup_id}"


def _normalize_repo_path(path: str) -> str:
    text = str(path or "").replace("\\", "/").strip()
    while text.startswith("./"):
        text = text[2:]
    if not text:
        raise ValueError("empty_path")
    if text.startswith("/") or re.match(r"^[A-Za-z]:/", text):
        raise ValueError("absolute_path")
    parts = PurePosixPath(text).parts
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError("path_traversal")
    return "/".join(parts)


def path_is_under_foundup(path: str, foundup_id: str) -> bool:
    normalized = _normalize_repo_path(path)
    root = foundup_root_for_id(foundup_id)
    return normalized == root or normalized.startswith(root + "/")


def stable_index_id(
    collection: str,
    repo_relative_path: str,
    *,
    foundup_id: str,
    symbol: str | None = None,
    kind: str | None = None,
) -> str:
    """Return a deterministic non-positional HoloIndex ID."""

    if collection not in ALL_COLLECTIONS:
        raise ValueError("unknown_collection")
    if not validate_foundup_id(foundup_id):
        raise ValueError("invalid_foundup_id")
    path = _normalize_repo_path(repo_relative_path)
    if symbol is not None and not SYMBOL_RE.fullmatch(symbol):
        raise ValueError("invalid_symbol")
    payload = {
        "collection": collection,
        "foundup_id": foundup_id,
        "kind": kind or "",
        "path": path,
        "symbol": symbol or "",
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
    short_collection = collection.replace("navigation_", "nav_")
    return f"hidx_{short_collection}_{digest}"


def delete_filter_for_foundup(foundup_id: str) -> dict[str, str]:
    if not validate_foundup_id(foundup_id):
        raise ValueError("invalid_foundup_id")
    return {"foundup_id": foundup_id}


def _dedupe_paths(paths: Iterable[str]) -> tuple[list[str], list[str]]:
    normalized: list[str] = []
    rejected: list[str] = []
    seen: set[str] = set()
    for path in paths:
        try:
            clean = _normalize_repo_path(path)
        except ValueError as exc:
            rejected.append(f"{exc.args[0]}:{path}")
            continue
        key = clean.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(clean)
    return normalized, rejected


def _collections_for_scoped_paths(paths: Iterable[str], foundup_id: str) -> tuple[dict[str, list[str]], list[str]]:
    by_path: dict[str, list[str]] = {}
    rejected: list[str] = []
    root = foundup_root_for_id(foundup_id)
    for path in paths:
        if not (path == root or path.startswith(root + "/")):
            rejected.append(f"path_outside_foundup_scope:{path}")
            continue
        collections = sorted(collections_for_path(path))
        if collections:
            by_path[path] = collections
    return by_path, rejected


def plan_incremental_foundup_index(
    *,
    foundup_id: str,
    changed_paths: Iterable[str] = (),
    removed_paths: Iterable[str] = (),
) -> IncrementalFoundUpIndexPlan:
    """Plan a scoped incremental FoundUp index refresh without executing it."""

    if not validate_foundup_id(foundup_id):
        return IncrementalFoundUpIndexPlan(
            schema_version=SCHEMA_VERSION,
            decision=DECISION_REJECTED,
            foundup_id=str(foundup_id or ""),
            foundup_root="",
            rejection_reasons=["invalid_foundup_id"],
        )

    root = foundup_root_for_id(foundup_id)
    normalized_changed, rejected_changed = _dedupe_paths(changed_paths)
    normalized_removed, rejected_removed = _dedupe_paths(removed_paths)
    changed_by_path, changed_rejections = _collections_for_scoped_paths(normalized_changed, foundup_id)
    removed_by_path, removed_rejections = _collections_for_scoped_paths(normalized_removed, foundup_id)
    rejections = rejected_changed + rejected_removed + changed_rejections + removed_rejections
    if rejections:
        return IncrementalFoundUpIndexPlan(
            schema_version=SCHEMA_VERSION,
            decision=DECISION_REJECTED,
            foundup_id=foundup_id,
            foundup_root=root,
            changed_paths=normalized_changed,
            removed_paths=normalized_removed,
            rejection_reasons=rejections,
        )

    operations: list[IncrementalFoundUpIndexOperation] = []
    target_collections: set[str] = set()
    for path, collections in changed_by_path.items():
        for collection in collections:
            target_collections.add(collection)
            operations.append(
                IncrementalFoundUpIndexOperation(
                    operation=OP_UPSERT_PATH,
                    collection=collection,
                    foundup_id=foundup_id,
                    repo_relative_path=path,
                    stable_id=stable_index_id(collection, path, foundup_id=foundup_id),
                    delete_where={"path": path},
                )
            )
    for path, collections in removed_by_path.items():
        for collection in collections:
            target_collections.add(collection)
            operations.append(
                IncrementalFoundUpIndexOperation(
                    operation=OP_DELETE_PATH_ID,
                    collection=collection,
                    foundup_id=foundup_id,
                    repo_relative_path=path,
                    stable_id=stable_index_id(collection, path, foundup_id=foundup_id),
                    delete_where={"path": path},
                )
            )

    decision = DECISION_PLANNED if operations else DECISION_NO_INDEXABLE_CHANGES
    return IncrementalFoundUpIndexPlan(
        schema_version=SCHEMA_VERSION,
        decision=decision,
        foundup_id=foundup_id,
        foundup_root=root,
        changed_paths=normalized_changed,
        removed_paths=normalized_removed,
        target_collections=sorted(target_collections),
        operations=operations,
    )


__all__ = [
    "DECISION_NO_INDEXABLE_CHANGES",
    "DECISION_PLANNED",
    "DECISION_REJECTED",
    "IncrementalFoundUpIndexOperation",
    "IncrementalFoundUpIndexPlan",
    "OP_DELETE_PATH_ID",
    "OP_UPSERT_PATH",
    "SCHEMA_VERSION",
    "delete_filter_for_foundup",
    "foundup_root_for_id",
    "path_is_under_foundup",
    "plan_incremental_foundup_index",
    "stable_index_id",
    "validate_foundup_id",
]
