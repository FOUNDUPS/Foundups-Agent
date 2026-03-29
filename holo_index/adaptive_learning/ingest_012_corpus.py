#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import io

"""
# === UTF-8 ENFORCEMENT (WSP 90) ===
# Prevent UnicodeEncodeError on Windows systems
# Only apply when running as main script, not during import
if __name__ == '__main__' and sys.platform.startswith('win'):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except (OSError, ValueError):
        # Ignore if stdout/stderr already wrapped or closed
        pass
# === END UTF-8 ENFORCEMENT ===

012.txt Corpus Ingestor (WSP 60)
---------------------------------

Ingests the 012.txt operational log into module memory for adaptive learning.

Outputs (under holo_index/adaptive_learning/012_corpus/memory/):
- 012_chunks.ndjson: one JSON object per chunk with labels and references
- 012_ingest_meta.json: run metadata and basic stats
- 012_queries.json: derived queries for retrieval and intent testing

Design:
- Deterministic heuristics first; optional Holo search for WSP refs
- Cheap labeling intended to be validated by qemma3/Qwen in later passes
"""

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def read_lines(path: Path) -> List[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return text.splitlines()


def chunk_lines(lines: List[str], max_lines: int) -> List[Tuple[int, List[str]]]:
    chunks: List[Tuple[int, List[str]]] = []
    buf: List[str] = []
    start_idx = 0
    for i, line in enumerate(lines):
        buf.append(line)
        if len(buf) >= max_lines:
            chunks.append((start_idx, buf))
            buf = []
            start_idx = i + 1
    if buf:
        chunks.append((start_idx, buf))
    return chunks


WSP_PATTERN = re.compile(r"\bWSP[\s_\-]?(\d+)\b", re.IGNORECASE)
PATH_PATTERN = re.compile(r"(modules/[\w_\-/]+\.(?:py|md)|holo_index/[\w_\-/]+\.(?:py|md)|WSP_framework/src/[\w_\-/]+\.md)")
CMD_PATTERN = re.compile(r"^(?:python|pip|git|rg|ls|Get-ChildItem|pytest|poetry)\b", re.IGNORECASE)


def label_intent(text: str) -> str:
    t = text.lower()
    if "wsp" in t or "protocol" in t or "scoring" in t:
        return "DOC_LOOKUP"
    if any(k in t for k in ["find", "where", "path", "location", "search code"]):
        return "CODE_LOCATION"
    if any(k in t for k in ["violation", "compliance", "health", "alerts"]):
        return "MODULE_HEALTH"
    if any(k in t for k in ["research", "benchmark", "compare", "mcp"]):
        return "RESEARCH"
    return "GENERAL"


def extract_refs(text: str) -> Dict[str, Any]:
    wsps = sorted({f"WSP {m}" for m in WSP_PATTERN.findall(text)})
    paths = PATH_PATTERN.findall(text)
    commands = [ln.strip() for ln in text.splitlines() if CMD_PATTERN.search(ln.strip())]
    return {"wsp_refs": wsps, "paths": paths, "commands": commands}


def resolve_source_path(repo_root: Path, source_arg: str) -> Optional[Path]:
    """
    Resolve 012 corpus source path with deterministic fallback order.

    Priority:
    1. Explicit absolute path provided by --source
    2. Explicit repo-relative path provided by --source
    3. Local root scratchpad: 012.txt
    4. Local ignored corpus mirror: holo_index/data/012.txt
    5. Optional docs mirror: docs/012_moshpit/012.txt
    """
    source = (source_arg or "").strip()
    if source and source.lower() not in {"auto", "default"}:
        candidate = Path(source)
        if not candidate.is_absolute():
            candidate = repo_root / source
        return candidate if candidate.exists() else None

    import os
    env_corpus = os.getenv("OPENCLAW_TRAINING_CORPUS", "012.txt")
    candidates = [
        repo_root / env_corpus,
        repo_root / "holo_index" / "data" / env_corpus,
        repo_root / "docs" / "012_moshpit" / env_corpus,
        repo_root / "012.txt",  # Fallback
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest 012.txt into adaptive learning memory (WSP 60)")
    parser.add_argument("--source", default="auto", help="Path to 012 corpus file (default: auto)")
    parser.add_argument("--chunk_lines", type=int, default=40, help="Max lines per chunk")
    args = parser.parse_args()

    # Script lives at <repo>/holo_index/adaptive_learning/ingest_012_corpus.py
    # parents[2] = <repo>
    repo_root = Path(__file__).resolve().parents[2]
    source_path = resolve_source_path(repo_root, args.source)
    if not source_path:
        print(
            "[WARN] Source not found. Tried explicit path or defaults: "
            "holo_index/data/012.txt, docs/012_moshpit/012.txt, 012.txt"
        )
        return

    memory_dir = Path(__file__).resolve().parent / "012_corpus" / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)

    lines = read_lines(source_path)
    chunks = chunk_lines(lines, args.chunk_lines)

    ndjson_path = memory_dir / "012_chunks.ndjson"
    queries_path = memory_dir / "012_queries.json"
    meta_path = memory_dir / "012_ingest_meta.json"

    total = 0
    wsp_queries: List[str] = []
    code_queries: List[str] = []

    with ndjson_path.open("w", encoding="utf-8") as out:
        for idx, (start, chunk) in enumerate(chunks, 1):
            text = "\n".join(chunk).strip()
            if not text:
                continue
            refs = extract_refs(text)
            intent = label_intent(text)
            record = {
                "chunk_id": idx,
                "start_line": start + 1,
                "end_line": start + len(chunk),
                "intent": intent,
                "wsp_refs": refs["wsp_refs"],
                "paths": refs["paths"],
                "commands": refs["commands"],
                "text": text[:2000]  # cap
            }
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            total += 1

            # Build derived queries
            for w in refs["wsp_refs"]:
                wsp_queries.append(w)
            for p in refs["paths"]:
                code_queries.append(f"Where is {Path(p).name}?")

    # Deduplicate queries and cap
    wsp_queries = sorted(set(wsp_queries))[:200]
    code_queries = sorted(set(code_queries))[:200]
    queries = {"wsp": wsp_queries, "code": code_queries}
    queries_path.write_text(json.dumps(queries, indent=2), encoding="utf-8")

    meta = {
        "source": str(source_path),
        "chunks": total,
        "chunk_lines": args.chunk_lines,
        "outputs": {"chunks": str(ndjson_path), "queries": str(queries_path)},
    }
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"[OK] Ingested {total} chunks -> {ndjson_path}")


if __name__ == "__main__":
    main()
