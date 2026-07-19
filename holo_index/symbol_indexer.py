"""Complete, evidence-producing Python symbol index maintenance."""

from __future__ import annotations

import ast
import hashlib
import os
import tokenize
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
    record_id: str,
) -> tuple[str, str, dict[str, Any]]:
    name = str(getattr(node, "name", ""))
    if isinstance(node, ast.ClassDef):
        symbol = f"class {name}"
    else:
        raw_args = getattr(getattr(node, "args", None), "args", ())
        args = [item.arg for item in raw_args if hasattr(item, "arg")]
        symbol = f"{name}({', '.join(args[:8])})"
    line_no = int(getattr(node, "lineno", 1) or 1)
    document = chr(10).join(
        (symbol, ast.get_docstring(node) or "", f"{path}:{line_no}")
    )
    federation = resolve_foundup_metadata(path, project_root)
    metadata = {
        "symbol": symbol,
        "path": str(path),
        "line": line_no,
        "type": "symbol",
        "foundup_id": federation["foundup_id"],
        "tenant_id": federation["tenant_id"],
        "source_scope": federation["source_scope"],
        "external_repo": federation["external_repo"],
    }
    return record_id, document, metadata


def _unparsed_source_record(
    *,
    path: Path,
    project_root: Path,
    record_id: str,
    error: Exception,
) -> tuple[str, str, dict[str, Any]]:
    """Account for a readable source without inventing symbols from it."""

    try:
        relative_path = path.relative_to(project_root).as_posix()
    except ValueError:
        relative_path = path.as_posix()
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
        "path": str(path),
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
            record_id = f"sym_{len(ids) + 1}"
            _, document, metadata = _unparsed_source_record(
                path=path,
                project_root=holo.project_root,
                record_id=record_id,
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
            record_id = f"sym_{len(ids) + 1}"
            _, document, metadata = _symbol_record(
                node=node,
                path=path,
                project_root=holo.project_root,
                record_id=record_id,
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
    for start in range(0, len(ids), 5000):
        end = start + 5000
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
    holo.symbol_collection = holo._reset_collection(collection_name)
    records = _prepare_records(holo, selected_files, max_entries=max_entries)
    ids, documents, metadatas, processed, failed, fallback, entry_truncated = records
    if ids:
        _add_batches(holo, holo.symbol_collection, ids, documents, metadatas)
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
        source_manifest_digest=manifest_digest,
        source_scope_id=scope_id,
    )


__all__ = ["index_symbol_entries"]
