"""Complete, evidence-producing Python symbol index maintenance."""

from __future__ import annotations

import ast
import hashlib
import os
import tokenize
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Optional

from holo_index.core.indexing_engine import (
    IndexResult,
    resolve_foundup_metadata,
    source_file_manifest_digest,
)
from holo_index.source_scope import (
    CANONICAL_SYMBOL_RELATIVE_ROOTS,
    CanonicalSourceScopeError,
    canonical_source_scope_id,
    filter_git_tracked_files,
    normalized_relative_roots,
)


SKIP_DIRS = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        "node_modules",
        "dist",
        "build",
        ".mypy_cache",
        ".pytest_cache",
    }
)
PreparedSymbolRecords = tuple[
    list[str],
    list[str],
    list[dict[str, Any]],
    int,
    int,
    int,
    bool,
]
DEFAULT_EMBED_BATCH_SIZE = 512
PUBLISH_BATCH_SIZE = 5000


def _relative_path(path: Path, project_root: Path) -> str:
    try:
        return path.relative_to(project_root).as_posix()
    except ValueError:
        return path.as_posix()


def _stable_record_id(
    relative_path: str,
    record_type: str,
    line_no: int,
    symbol: str,
) -> str:
    payload = "\x00".join((relative_path, record_type, str(line_no), symbol))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]
    return f"hidx_nav_symbols_{digest}"


def _roots(holo: Any, roots: Optional[list[Path]]) -> list[Path]:
    values = roots
    if values is None:
        env_roots = os.getenv("HOLO_SYMBOL_ROOTS")
        if env_roots:
            values = [
                Path(value.strip())
                for value in env_roots.split(";")
                if value.strip()
            ]
    if values is None:
        values = [Path(value) for value in CANONICAL_SYMBOL_RELATIVE_ROOTS]
    return [
        value if value.is_absolute() else holo.project_root / value
        for value in values
    ]


def _source_scope_id(holo: Any, roots: list[Path]) -> str:
    canonical = tuple(sorted(CANONICAL_SYMBOL_RELATIVE_ROOTS))
    if normalized_relative_roots(holo.project_root, roots) == canonical:
        return canonical_source_scope_id("navigation_symbols")
    return ""


def _discover_files(roots: list[Path]) -> list[Path]:
    discovered: dict[str, Path] = {}
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            resolved = path.resolve(strict=False)
            discovered.setdefault(os.path.normcase(str(resolved)), resolved)
    return sorted(discovered.values(), key=lambda path: path.as_posix().casefold())


def _symbol_record(
    *,
    node: ast.AST,
    path: Path,
    project_root: Path,
) -> tuple[str, str, dict[str, Any]]:
    name = str(getattr(node, "name", ""))
    if isinstance(node, ast.ClassDef):
        symbol = f"class {name}"
    else:
        raw_args = getattr(getattr(node, "args", None), "args", ())
        args = [item.arg for item in raw_args if hasattr(item, "arg")]
        symbol = f"{name}({', '.join(args[:8])})"
    line_no = int(getattr(node, "lineno", 1) or 1)
    relative_path = _relative_path(path, project_root)
    document = chr(10).join(
        (symbol, ast.get_docstring(node) or "", f"{relative_path}:{line_no}")
    )
    federation = resolve_foundup_metadata(path, project_root)
    metadata = {
        "symbol": symbol,
        "path": relative_path,
        "line": line_no,
        "type": "symbol",
        "foundup_id": federation["foundup_id"],
        "tenant_id": federation["tenant_id"],
        "source_scope": federation["source_scope"],
        "external_repo": federation["external_repo"],
    }
    record_id = _stable_record_id(relative_path, metadata["type"], line_no, symbol)
    return record_id, document, metadata


def _unparsed_source_record(
    *,
    path: Path,
    project_root: Path,
    error: Exception,
) -> tuple[str, str, dict[str, Any]]:
    """Account for a readable source without inventing symbols from it."""

    relative_path = _relative_path(path, project_root)
    error_class = type(error).__name__
    document = "\n".join(
        (
            "Unparsed Python source",
            f"Path: {relative_path}",
            f"Parse status: {error_class}",
            "No verified symbols were extracted from this source.",
        )
    )
    federation = resolve_foundup_metadata(path, project_root)
    metadata = {
        "symbol": "",
        "path": relative_path,
        "line": 1,
        "type": "unparsed_source",
        "parse_status": error_class,
        "source_path_digest": "sha256:"
        + hashlib.sha256(relative_path.encode("utf-8")).hexdigest(),
        "foundup_id": federation["foundup_id"],
        "tenant_id": federation["tenant_id"],
        "source_scope": federation["source_scope"],
        "external_repo": federation["external_repo"],
    }
    record_id = _stable_record_id(relative_path, metadata["type"], 1, "")
    return record_id, document, metadata


def _embedding_batch_size() -> int:
    raw = str(os.getenv("HOLO_SYMBOL_EMBED_BATCH_SIZE", "")).strip()
    if not raw:
        return DEFAULT_EMBED_BATCH_SIZE
    try:
        return max(1, min(int(raw), 5000))
    except ValueError:
        return DEFAULT_EMBED_BATCH_SIZE


def _batch_embeddings(holo: Any, documents: list[str]) -> list[list[float]]:
    """Encode one bounded batch, falling back for minimal/test backends."""

    model = getattr(holo, "model", None)
    encode = getattr(model, "encode", None)
    if callable(encode):
        try:
            values = encode(
                documents,
                batch_size=_embedding_batch_size(),
                show_progress_bar=False,
            )
            rows = values.tolist() if hasattr(values, "tolist") else list(values)
            if len(rows) == len(documents):
                return [row.tolist() if hasattr(row, "tolist") else list(row) for row in rows]
        except (TypeError, ValueError, RuntimeError):
            pass
    return [holo._get_embedding(document) for document in documents]


def _prepare_records(
    holo: Any,
    files: list[Path],
    *,
    max_entries: int,
) -> PreparedSymbolRecords:
    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict[str, Any]] = []
    processed_files = 0
    failed_files = 0
    fallback_files = 0
    for path in files:
        processed_files += 1
        try:
            with tokenize.open(path) as source:
                source_text = source.read()
            tree = ast.parse(source_text)
        except OSError:
            failed_files += 1
            continue
        except (UnicodeError, SyntaxError) as exc:
            if max_entries > 0 and len(ids) >= max_entries:
                return (
                    ids,
                    documents,
                    metadatas,
                    max(0, processed_files - 1),
                    failed_files,
                    fallback_files,
                    True,
                )
            record_id, document, metadata = _unparsed_source_record(
                path=path,
                project_root=holo.project_root,
                error=exc,
            )
            ids.append(record_id)
            documents.append(document)
            metadatas.append(metadata)
            fallback_files += 1
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            if max_entries > 0 and len(ids) >= max_entries:
                return (
                    ids,
                    documents,
                    metadatas,
                    max(0, processed_files - 1),
                    failed_files,
                    fallback_files,
                    True,
                )
            record_id, document, metadata = _symbol_record(
                node=node,
                path=path,
                project_root=holo.project_root,
            )
            ids.append(record_id)
            documents.append(document)
            metadatas.append(metadata)
    return (
        ids,
        documents,
        metadatas,
        processed_files,
        failed_files,
        fallback_files,
        False,
    )


def _add_batches(
    holo: Any,
    collection: Any,
    ids: list[str],
    documents: list[str],
    metadatas: list[dict[str, Any]],
) -> None:
    for start in range(0, len(ids), PUBLISH_BATCH_SIZE):
        end = start + PUBLISH_BATCH_SIZE
        document_batch = documents[start:end]
        embedding_batch = _batch_embeddings(holo, document_batch)
        if len(embedding_batch) != len(document_batch):
            raise ValueError("HOLOINDEX_SYMBOL_EMBEDDING_BATCH_MISMATCH")
        collection.add(
            ids=ids[start:end],
            embeddings=embedding_batch,
            documents=document_batch,
            metadatas=metadatas[start:end],
        )


def _embedding_space_matches(holo: Any, collection: Any) -> bool:
    metadata = getattr(collection, "metadata", None)
    if not isinstance(metadata, Mapping):
        return False
    expected = {
        "embedding_backend": str(getattr(holo, "index_embedding_backend", "") or ""),
        "embedding_model": str(getattr(holo, "index_embedding_model_id", "") or ""),
        "embedding_space_fingerprint": str(
            getattr(holo, "index_embedding_space_fingerprint", "") or ""
        ),
    }
    return bool(expected["embedding_space_fingerprint"]) and all(
        str(metadata.get(key) or "") == value for key, value in expected.items()
    )


def _flat_list(payload: Any, key: str) -> list[Any]:
    if not isinstance(payload, Mapping):
        raise ValueError("HOLOINDEX_SYMBOL_REUSE_INVALID_PAYLOAD")
    raw = payload.get(key, [])
    values = [] if raw is None else list(raw)
    if values and isinstance(values[0], list):
        values = [item for group in values for item in group]
    return values


def _reconciliation_capable(collection: Any) -> bool:
    return all(
        callable(getattr(collection, name, None))
        for name in ("get", "upsert", "update", "delete", "count")
    )


def _reconcile_records(
    holo: Any,
    collection: Any,
    ids: list[str],
    documents: list[str],
    metadatas: list[dict[str, Any]],
) -> int:
    """Retain embeddings only for exact documents in the same embedding space."""

    snapshot = collection.get(include=["metadatas"])
    existing_ids = {str(value) for value in _flat_list(snapshot, "ids")}
    desired_ids = set(ids)
    reused = 0
    for start in range(0, len(ids), PUBLISH_BATCH_SIZE):
        end = start + PUBLISH_BATCH_SIZE
        batch_ids = ids[start:end]
        batch_documents = documents[start:end]
        batch_metadatas = metadatas[start:end]
        current = collection.get(
            ids=batch_ids,
            include=["documents", "metadatas"],
        )
        current_ids = [str(value) for value in _flat_list(current, "ids")]
        current_documents = _flat_list(current, "documents")
        current_metadatas = _flat_list(current, "metadatas")
        by_id = {
            item_id: (document, metadata)
            for item_id, document, metadata in zip(
                current_ids, current_documents, current_metadatas
            )
        }
        changed_ids: list[str] = []
        changed_documents: list[str] = []
        changed_metadatas: list[dict[str, Any]] = []
        metadata_ids: list[str] = []
        metadata_values: list[dict[str, Any]] = []
        for item_id, document, metadata in zip(
            batch_ids, batch_documents, batch_metadatas
        ):
            previous = by_id.get(item_id)
            if previous is None or previous[0] != document:
                changed_ids.append(item_id)
                changed_documents.append(document)
                changed_metadatas.append(metadata)
                continue
            reused += 1
            if previous[1] != metadata:
                metadata_ids.append(item_id)
                metadata_values.append(metadata)
        if changed_ids:
            embeddings = _batch_embeddings(holo, changed_documents)
            if len(embeddings) != len(changed_documents):
                raise ValueError("HOLOINDEX_SYMBOL_EMBEDDING_BATCH_MISMATCH")
            collection.upsert(
                ids=changed_ids,
                embeddings=embeddings,
                documents=changed_documents,
                metadatas=changed_metadatas,
            )
        if metadata_ids:
            collection.update(ids=metadata_ids, metadatas=metadata_values)
    stale_ids = sorted(existing_ids.difference(desired_ids))
    for start in range(0, len(stale_ids), PUBLISH_BATCH_SIZE):
        collection.delete(ids=stale_ids[start : start + PUBLISH_BATCH_SIZE])
    if int(collection.count()) != len(ids):
        raise ValueError("HOLOINDEX_SYMBOL_RECONCILIATION_COUNT_MISMATCH")
    return reused


def _publish_records(
    holo: Any,
    ids: list[str],
    documents: list[str],
    metadatas: list[dict[str, Any]],
) -> int:
    current = getattr(holo, "symbol_collection", None)
    if _embedding_space_matches(holo, current) and _reconciliation_capable(current):
        return _reconcile_records(holo, current, ids, documents, metadatas)
    holo.symbol_collection = holo._reset_collection("navigation_symbols")
    if ids:
        _add_batches(holo, holo.symbol_collection, ids, documents, metadatas)
    return 0


def _canonical_discovered_files(
    holo: Any,
    files: list[Path],
    *,
    scope_id: str,
) -> tuple[list[Path], IndexResult | None]:
    if not scope_id:
        return files, None
    try:
        return filter_git_tracked_files(holo.project_root, files), None
    except CanonicalSourceScopeError as exc:
        return files, IndexResult(
            discovered_count=len(files),
            indexed_count=0,
            collection_name="navigation_symbols",
            warning=str(exc),
            processed_count=0,
            failed_count=1,
            source_scope_id="",
        )


def _discover_symbol_source(
    holo: Any,
    roots: Optional[list[Path]],
) -> tuple[list[Path], str, IndexResult | None]:
    source_roots = _roots(holo, roots)
    scope_id = _source_scope_id(holo, source_roots)
    files = _discover_files(source_roots)
    files, failure = _canonical_discovered_files(
        holo,
        files,
        scope_id=scope_id,
    )
    return files, scope_id, failure


def _symbol_source_manifest(
    holo: Any,
    files: list[Path],
    *,
    scope_id: str,
) -> tuple[str, IndexResult | None]:
    try:
        digest = source_file_manifest_digest(
            files,
            project_root=holo.project_root,
        )
    except OSError as exc:
        return "", IndexResult(
            discovered_count=len(files),
            indexed_count=0,
            collection_name="navigation_symbols",
            warning=f"Symbol source manifest read failed: {exc}",
            processed_count=0,
            failed_count=1,
            source_scope_id=scope_id,
        )
    return digest, None


def _symbol_index_warning(
    *,
    selected_count: int,
    discovered_count: int,
    entry_truncated: bool,
    failed: int,
    fallback: int,
    indexed_count: int,
) -> str:
    if selected_count != discovered_count:
        return "Symbol source file cap truncated the declared source set"
    if entry_truncated:
        return "Symbol entry cap truncated the declared source set"
    if failed:
        return f"Symbol parser failed for {failed} source files"
    if fallback:
        return f"Indexed {fallback} unparseable source files without verified symbols"
    if not indexed_count:
        return "Symbol index empty - no entries added"
    return ""


def index_symbol_entries(
    holo: Any,
    roots: Optional[list[Path]] = None,
) -> IndexResult:
    """Index the declared Python source set or return incomplete evidence."""

    collection_name = "navigation_symbols"
    discovered_files, scope_id, failure = _discover_symbol_source(holo, roots)
    if failure is not None:
        return failure
    max_files = max(0, int(os.getenv("HOLO_SYMBOL_MAX_FILES", "0")))
    max_entries = max(0, int(os.getenv("HOLO_SYMBOL_MAX_ENTRIES", "0")))
    selected_files = discovered_files[:max_files] if max_files else discovered_files
    manifest_digest, failure = _symbol_source_manifest(
        holo,
        discovered_files,
        scope_id=scope_id,
    )
    if failure is not None:
        return failure
    holo._log_agent_action("Indexing symbol entries (functions/classes)...", "INDEX")
    records = _prepare_records(holo, selected_files, max_entries=max_entries)
    ids, documents, metadatas, processed, failed, fallback, entry_truncated = records
    reused = _publish_records(holo, ids, documents, metadatas)
    if ids:
        holo._log_agent_action(f"Symbol index refreshed: {len(ids)} entries", "OK")
    warning = _symbol_index_warning(
        selected_count=len(selected_files),
        discovered_count=len(discovered_files),
        entry_truncated=entry_truncated,
        failed=failed,
        fallback=fallback,
        indexed_count=len(ids),
    )
    return IndexResult(
        discovered_count=len(discovered_files),
        indexed_count=len(ids),
        collection_name=collection_name,
        warning=warning or None,
        processed_count=processed,
        failed_count=failed,
        fallback_count=fallback,
        reused_count=reused,
        source_manifest_digest=manifest_digest,
        source_scope_id=scope_id,
    )


__all__ = ["index_symbol_entries"]
