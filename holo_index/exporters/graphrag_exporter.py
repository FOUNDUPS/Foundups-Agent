# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Dict, Any, List, Optional, Set


class GraphRAGExporter:
    """
    Export HoloIndex knowledge base entries into a folder structure
    compatible with the Microsoft GraphRAG quickstart pipeline.

    The exporter gathers content referenced by HoloIndex search results
    and writes plain-text documents under `<output>/input/`. A companion
    metadata file captures provenance so downstream GraphRAG runs can
    inspect the original sources.
    """

    DEFAULT_QUERIES: List[str] = [
        "module architecture",
        "compliance guardrails",
        "semantic search",
        "navigation roadmap",
    ]

    SUPPORTED_SUFFIXES: Set[str] = {".md", ".py", ".txt"}

    def __init__(self, holo_index: Any):
        self._holo_index = holo_index
        project_root = getattr(holo_index, "project_root", None)
        self._project_root = Path(project_root).resolve() if project_root else None

    def _resolve_source_path(self, raw_path: Any) -> Optional[Path]:
        """Bind source hits to the explicit Holo authority root."""
        if self._project_root is None:
            return None
        candidate = Path(str(raw_path or ""))
        resolved = (
            candidate.resolve()
            if candidate.is_absolute()
            else (self._project_root / candidate).resolve()
        )
        try:
            resolved.relative_to(self._project_root)
        except ValueError:
            return None
        return resolved

    # ------------------------------------------------------------------ #
    # Collection helpers
    # ------------------------------------------------------------------ #

    def collect_documents(
        self,
        queries: Optional[Iterable[str]] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Run a set of HoloIndex searches and collect unique file contents.

        Args:
            queries: iterable of search queries (defaults to DEFAULT_QUERIES).
            limit: maximum number of hits to inspect per query.
        """
        queries = list(queries) if queries else self.DEFAULT_QUERIES
        collected: Dict[str, Dict[str, Any]] = {}

        for query in queries:
            try:
                results = self._holo_index.search(query, limit=limit)
            except Exception:  # pragma: no cover - defensive
                continue

            hits = results.get("code", []) + results.get("wsps", [])
            for hit in hits:
                path = hit.get("path")
                if not path:
                    continue
                file_path = self._resolve_source_path(path)
                if file_path is None:
                    continue
                if not file_path.exists():
                    continue
                if file_path.suffix.lower() not in self.SUPPORTED_SUFFIXES:
                    continue

                try:
                    text = file_path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    text = file_path.read_text(encoding="latin-1", errors="ignore")

                key = file_path.resolve().as_posix()
                collected[key] = {
                    "title": hit.get("need") or hit.get("title") or file_path.name,
                    "path": key,
                    "query": query,
                    "type": hit.get("type"),
                    "content": text,
                }

        return list(collected.values())

    # ------------------------------------------------------------------ #
    # Export helpers
    # ------------------------------------------------------------------ #

    def export(
        self,
        output_dir: Path | str,
        queries: Optional[Iterable[str]] = None,
        limit: int = 10,
    ) -> Path:
        """
        Run collection and materialise documents inside ``output_dir``.

        Returns:
            The path to the generated directory.
        """
        output_dir = Path(output_dir).resolve()
        input_dir = output_dir / "input"
        input_dir.mkdir(parents=True, exist_ok=True)

        documents = self.collect_documents(queries=queries, limit=limit)
        metadata_path = output_dir / "metadata.json"
        manifest: List[Dict[str, Any]] = []

        for index, doc in enumerate(documents, start=1):
            filename = input_dir / f"doc_{index:04d}.txt"
            filename.write_text(doc["content"], encoding="utf-8")
            manifest.append(
                {
                    "id": index,
                    "title": doc.get("title"),
                    "path": doc.get("path"),
                    "query": doc.get("query"),
                    "type": doc.get("type"),
                    "relative_path": filename.relative_to(output_dir).as_posix(),
                }
            )

        metadata_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        # Write a short README to guide the user through GraphRAG quickstart
        readme_path = output_dir / "README_GRAPHRAG.txt"
        readme_path.write_text(
            _GRAPHRAG_README_TEMPLATE.strip() + "\n",
            encoding="utf-8",
        )

        return output_dir


_GRAPHRAG_README_TEMPLATE = """
GraphRAG Export Bundle
======================

This directory was generated by `GraphRAGExporter` in HoloIndex.
It contains plain-text documents under `input/` alongside metadata
about the originating modules and queries.

To index this dataset with Microsoft's GraphRAG project:

1. Install GraphRAG (see https://github.com/microsoft/graphrag).
2. Copy this directory into your GraphRAG workspace.
3. Run `python -m graphrag.index --input input --config <your-config.toml>`.

The `metadata.json` file preserves the original HoloIndex file paths,
which can be consulted during evaluation or debugging.
"""
