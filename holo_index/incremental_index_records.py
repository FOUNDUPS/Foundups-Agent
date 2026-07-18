"""Exact-path record preparation for incremental HoloIndex maintenance."""

from __future__ import annotations

import ast
import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from holo_index.incremental_foundup_index import (
    IncrementalFoundUpIndexOperation,
    IncrementalFoundUpIndexPlan,
    stable_index_id,
)


class IncrementalCollectionGateway(Protocol):
    """Injected collection and embedding adapter."""

    def get_collection(self, name: str) -> Any:
        """Return the mutable collection handle for a collection name."""

    def embed(self, text: str) -> list[float]:
        """Return an embedding for the provided text."""


@dataclass(frozen=True)
class PreparedRecord:
    stable_id: str
    document: str
    metadata: dict[str, Any]
    embedding: list[float]


def resolve_repo_path(repo_root: Path, repo_relative_path: str) -> Path:
    root = repo_root.resolve()
    target = (root / repo_relative_path).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"path_outside_repo:{repo_relative_path}") from exc
    return target


def read_indexable_file(path: Path, *, max_file_bytes: int) -> str:
    if not path.exists() or not path.is_file():
        raise ValueError(f"source_file_missing:{path}")
    if max_file_bytes <= 0:
        raise ValueError("max_file_bytes_must_be_positive")
    data = path.read_bytes()
    if len(data) > max_file_bytes:
        raise ValueError(
            f"source_file_exceeds_limit:{len(data)}>{max_file_bytes}"
        )
    return data.decode("utf-8", errors="strict")


def _normalized_path(value: Any) -> str:
    text = str(value or "").replace("\\", "/").strip()
    while text.startswith("./"):
        text = text[2:]
    return text.rstrip("/").casefold()


def _metadata_matches_path(metadata: Any, repo_relative_path: str) -> bool:
    if not isinstance(metadata, Mapping):
        return False
    target = _normalized_path(repo_relative_path)
    for key in ("path", "file_path", "filepath", "source_path"):
        candidate = _normalized_path(metadata.get(key))
        if candidate == target or candidate.endswith("/" + target):
            return True
    return False


def existing_path_ids(
    collection: Any,
    *,
    repo_relative_path: str,
    stable_id: str,
) -> list[str]:
    """Find exact-path records, including legacy positional IDs."""

    payload = collection.get(include=["metadatas"])
    if not isinstance(payload, Mapping):
        raise ValueError("collection_get_invalid_payload")
    raw_ids = list(payload.get("ids") or [])
    raw_metadatas = list(payload.get("metadatas") or [])
    if raw_ids and isinstance(raw_ids[0], list):
        raw_ids = [item for group in raw_ids for item in group]
    if raw_metadatas and isinstance(raw_metadatas[0], list):
        raw_metadatas = [item for group in raw_metadatas for item in group]

    matching: set[str] = set()
    available_ids = {str(item) for item in raw_ids}
    if stable_id in available_ids:
        matching.add(stable_id)
    for item_id, metadata in zip(raw_ids, raw_metadatas):
        if _metadata_matches_path(metadata, repo_relative_path):
            matching.add(str(item_id))
    return sorted(matching)


def _symbol_specs(
    document: str,
    repo_relative_path: str,
) -> list[tuple[str, str, str, int, str]]:
    try:
        tree = ast.parse(document)
    except SyntaxError as exc:
        raise ValueError(
            f"symbol_ast_parse_failed:{repo_relative_path}:{exc.msg}"
        ) from exc

    specs: list[tuple[str, str, str, int, str]] = []

    def visit(node: ast.AST, scope: tuple[str, ...]) -> None:
        for child in ast.iter_child_nodes(node):
            child_scope = scope
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                qualified_name = ".".join((*scope, child.name))
                if isinstance(child, ast.ClassDef):
                    kind = "class"
                    display = f"class {child.name}"
                else:
                    kind = (
                        "async_function"
                        if isinstance(child, ast.AsyncFunctionDef)
                        else "function"
                    )
                    args = [
                        argument.arg
                        for argument in (
                            *getattr(child.args, "posonlyargs", []),
                            *child.args.args,
                        )
                    ]
                    display = f"{child.name}({', '.join(args[:8])})"
                line = int(getattr(child, "lineno", 1) or 1)
                doc = ast.get_docstring(child) or ""
                symbol_document = f"{display}\n{doc}\n{repo_relative_path}:{line}"
                specs.append(
                    (child.name, qualified_name, kind, line, symbol_document)
                )
                child_scope = (*scope, child.name)
            visit(child, child_scope)

    visit(tree, ())
    return specs


def _base_record_metadata(
    operation: IncrementalFoundUpIndexOperation,
    plan: IncrementalFoundUpIndexPlan,
    *,
    receipt_source: str,
    content_digest: str,
) -> dict[str, Any]:
    return {
        "path": operation.repo_relative_path,
        "foundup_id": plan.foundup_id,
        "foundup_root": plan.foundup_root,
        "collection": operation.collection,
        "source": receipt_source,
        "tenant_id": "core",
        "source_scope": "internal_foundup",
        "external_repo": False,
        "source_content_digest": content_digest,
    }


def _symbol_records(
    operation: IncrementalFoundUpIndexOperation,
    document: str,
    plan: IncrementalFoundUpIndexPlan,
    base_metadata: dict[str, Any],
) -> list[tuple[str, str, dict[str, Any]]]:
    records: list[tuple[str, str, dict[str, Any]]] = []
    for name, qualified_name, kind, line, symbol_document in _symbol_specs(
        document,
        operation.repo_relative_path,
    ):
        record_id = stable_index_id(
            operation.collection,
            operation.repo_relative_path,
            foundup_id=plan.foundup_id,
            symbol=name,
            kind=f"{kind}:{qualified_name}",
        )
        metadata = {
            **base_metadata,
            "symbol": symbol_document.splitlines()[0],
            "symbol_name": name,
            "qualified_name": qualified_name,
            "kind": kind,
            "line": line,
            "type": "symbol",
        }
        records.append((record_id, symbol_document, metadata))
    return records


def prepare_records(
    *,
    operation: IncrementalFoundUpIndexOperation,
    document: str,
    plan: IncrementalFoundUpIndexPlan,
    gateway: IncrementalCollectionGateway,
    receipt_source: str,
) -> list[PreparedRecord]:
    content_digest = "sha256:" + hashlib.sha256(
        document.encode("utf-8")
    ).hexdigest()
    base_metadata = _base_record_metadata(
        operation,
        plan,
        receipt_source=receipt_source,
        content_digest=content_digest,
    )
    if operation.collection == "navigation_symbols":
        raw_records = _symbol_records(
            operation,
            document,
            plan,
            base_metadata,
        )
    else:
        raw_records = [(operation.stable_id, document, base_metadata)]

    return [
        PreparedRecord(
            stable_id=record_id,
            document=record_document,
            metadata=metadata,
            embedding=gateway.embed(record_document),
        )
        for record_id, record_document, metadata in raw_records
    ]


def collection_add_records(collection: Any, records: list[PreparedRecord]) -> None:
    if not records:
        return
    payload: dict[str, Any] = {
        "ids": [record.stable_id for record in records],
        "documents": [record.document for record in records],
        "metadatas": [record.metadata for record in records],
    }
    if all(record.embedding for record in records):
        payload["embeddings"] = [record.embedding for record in records]
    collection.add(**payload)


__all__ = [
    "IncrementalCollectionGateway",
    "PreparedRecord",
    "collection_add_records",
    "existing_path_ids",
    "prepare_records",
    "read_indexable_file",
    "resolve_repo_path",
]
