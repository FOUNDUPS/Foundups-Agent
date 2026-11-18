# -*- coding: utf-8 -*-
"""Bounded Markdown document indexing for HoloIndex.

The general docs corpus retains one summary record per source. Canonical
current HoloIndex contracts additionally receive heading-scoped records so
live status and interface sections are retrievable without granting
historical audit records equivalent authority.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List

from holo_index.document_truth import classify_document_truth


_SECTIONED_CURRENT_CONTRACTS = frozenset(
    {
        "holo_index/README.md",
        "holo_index/INTERFACE.md",
        "holo_index/ROADMAP.md",
        "holo_index/tests/README.md",
        "holo_index/memory/README.md",
        "holo_index/adaptive_learning/README.md",
        "holo_index/adaptive_learning/INTERFACE.md",
    }
)
_CURRENT_SECTIONS_BY_PATH = {
    "holo_index/README.md": frozenset({
        "current operational truth (2026-08-28)", "rsi boundary",
    }),
    "holo_index/INTERFACE.md": frozenset({"current-truth retrieval contract"}),
    "holo_index/ROADMAP.md": frozenset({
        "[2026-08-28] current-truth retrieval and rsi gate",
    }),
    "holo_index/tests/README.md": frozenset({
        "current-truth document retrieval",
    }),
    "holo_index/memory/README.md": frozenset({
        "current truth", "present implementation boundary", "safety contract",
    }),
    "holo_index/adaptive_learning/README.md": frozenset({
        "current implementation boundary",
    }),
    "holo_index/adaptive_learning/INTERFACE.md": frozenset({
        "current truth boundary",
    }),
}


@dataclass(frozen=True)
class DocumentIndexDependencies:
    """Callbacks owned by the parent indexing engine."""

    result_type: type
    source_file_manifest_digest: Callable[..., str]
    classify_document_type: Callable[[Path, str, List[str]], str]
    calculate_document_priority: Callable[[str, Path], int]
    extract_slice_id: Callable[[str, str], str | None]
    resolve_foundup_metadata: Callable[[Path, Path], Dict[str, Any]]
    canonical_source_scope_id: Callable[[str], str]


def chunk_markdown_by_headings(
    text: str,
    max_chunk_chars: int = 1200,
    overlap_chars: int = 100,
) -> List[Dict[str, str]]:
    """Split Markdown into bounded heading-scoped chunks."""

    del overlap_chars  # Retained for API compatibility; chunks never duplicate bytes.
    chunks: List[Dict[str, str]] = []
    heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$")
    section = "Introduction"
    content_lines: List[str] = []

    def flush() -> None:
        content = "".join(content_lines).strip()
        if not content:
            return
        start = 0
        part = 0
        while start < len(content):
            end = min(start + max_chunk_chars, len(content))
            if end < len(content) and content[end] not in " \n":
                boundary = content.rfind(" ", start, end)
                if boundary > start:
                    end = boundary
            value = content[start:end].strip()
            if value:
                suffix = f" (part {part + 1})" if part else ""
                chunks.append({"section": section + suffix, "content": value})
                part += 1
            start = end

    for line in text.splitlines(keepends=True):
        match = heading_pattern.match(line.strip())
        if match:
            flush()
            section = match.group(2).strip()
            content_lines = []
        else:
            content_lines.append(line)
    flush()
    return chunks


def _read_markdown(file_path: Path) -> str:
    raw = file_path.read_bytes()
    if raw[:2] == b"\xff\xfe":
        return raw.decode("utf-16-le", errors="ignore").lstrip("\ufeff")
    return raw.decode("utf-8", errors="ignore")


def _base_metadata(
    *,
    file_path: Path,
    project_root: Path,
    relative_path: str,
    title: str,
    lines: List[str],
    deps: DocumentIndexDependencies,
) -> Dict[str, Any]:
    doc_type = deps.classify_document_type(file_path, title, lines)
    federation = deps.resolve_foundup_metadata(file_path, project_root)
    metadata: Dict[str, Any] = {
        "title": title,
        "path": relative_path,
        "type": doc_type,
        "priority": deps.calculate_document_priority(doc_type, file_path),
        "truth_class": classify_document_truth(
            {"path": relative_path, "type": doc_type}
        ),
        "foundup_id": federation["foundup_id"],
        "tenant_id": federation["tenant_id"],
        "source_scope": federation["source_scope"],
        "external_repo": federation["external_repo"],
    }
    slice_id = deps.extract_slice_id(file_path.name, title)
    if slice_id:
        metadata["slice_id"] = slice_id
    return metadata


def _section_records(
    *, text: str, title: str, index: int, relative_path: str,
    metadata: Dict[str, Any],
) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for section_index, chunk in enumerate(chunk_markdown_by_headings(text), start=1):
        if not _section_is_current(relative_path, chunk["section"]):
            continue
        records.append(
            {
                "id": f"doc_{index}_section_{section_index}",
                "document": f"{title}\n{chunk['section']}\n{chunk['content']}",
                "metadata": {
                    **metadata,
                    "summary": chunk["content"][:400],
                    "record_kind": "document_section",
                    "section_title": chunk["section"],
                },
            }
        )
    return records


def _section_is_current(relative_path: str, section: str) -> bool:
    """Admit only path-bound headings in the reviewed current-truth set."""

    allowed = _CURRENT_SECTIONS_BY_PATH.get(relative_path, ())
    normalized = re.sub(r"\s+\(part \d+\)$", "", section.casefold()).strip()
    return normalized in allowed


def _records_for_file(
    file_path: Path,
    index: int,
    project_root: Path,
    deps: DocumentIndexDependencies,
) -> List[Dict[str, Any]]:
    text = _read_markdown(file_path)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return []
    relative_path = file_path.relative_to(project_root).as_posix()
    title = lines[0].lstrip("# ")
    summary = " ".join(lines[1:6])[:400]
    metadata = _base_metadata(
        file_path=file_path,
        project_root=project_root,
        relative_path=relative_path,
        title=title,
        lines=lines,
        deps=deps,
    )
    records = [
        {
            "id": f"doc_{index}",
            "document": f"{title}\n{summary}",
            "metadata": {
                **metadata,
                "summary": summary,
                "record_kind": "document_summary",
            },
        }
    ]
    if relative_path in _SECTIONED_CURRENT_CONTRACTS:
        records.extend(
            _section_records(
                text=text, title=title, index=index,
                relative_path=relative_path, metadata=metadata,
            )
        )
    return records


def _build_records(
    holo: Any, files: List[Path], deps: DocumentIndexDependencies
) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for index, file_path in enumerate(files, start=1):
        records.extend(_records_for_file(file_path, index, holo.project_root, deps))
    return records


def _empty_result(deps: DocumentIndexDependencies, discovered: int) -> Any:
    if discovered:
        warning = "No docs entries were indexed — all discovered files had empty content"
    else:
        warning = "No docs found to index — discovery returned zero files"
    return deps.result_type(discovered, 0, "navigation_docs", warning)


def index_docs_entries(holo: Any, deps: DocumentIndexDependencies) -> Any:
    """Index the exact governed docs source set into ``navigation_docs``."""

    from holo_index.canonical_source_manifest import _docs_source_files

    files = _docs_source_files(holo)
    if not files:
        holo._log_agent_action("No docs found to index", "WARN")
        return _empty_result(deps, 0)
    manifest_digest = deps.source_file_manifest_digest(
        files, project_root=holo.project_root
    )
    holo._log_agent_action(f"Indexing {len(files)} docs into navigation_docs...", "INDEX")
    holo.docs_collection = holo._reset_collection("navigation_docs")
    records = _build_records(holo, files, deps)
    if not records:
        holo._log_agent_action("No docs entries were indexed", "WARN")
        return _empty_result(deps, len(files))
    documents = [record["document"] for record in records]
    holo.docs_collection.add(
        ids=[record["id"] for record in records],
        embeddings=[holo._get_embedding(document) for document in documents],
        documents=documents,
        metadatas=[record["metadata"] for record in records],
    )
    holo._log_agent_action(f"Docs index refreshed: {len(records)} entries", "OK")
    return deps.result_type(
        discovered_count=len(files),
        indexed_count=len(records),
        collection_name="navigation_docs",
        processed_count=len(files),
        source_manifest_digest=manifest_digest,
        source_scope_id=deps.canonical_source_scope_id("navigation_docs"),
    )
