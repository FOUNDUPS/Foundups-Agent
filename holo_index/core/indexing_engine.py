# -*- coding: utf-8 -*-
"""HoloIndex Indexing Engine — extracted indexing surface.

Provides the indexing pipeline previously inlined in HoloIndex.
All public functions accept a ``holo`` (HoloIndex instance) parameter so
they can access collections, model, embeddings, and logging without
coupling to the class hierarchy.

Methods that only need ``holo`` for logging / collection management call
back via ``holo._get_embedding()``, ``holo._reset_collection()``, etc.
to preserve existing test stubs.

WSP Compliance: WSP 87 (Size Limits), WSP 72 (Block Independence)
"""

from __future__ import annotations

import ast
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .holo_index import HoloIndex

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Stateless helpers (no holo parameter needed)
# ---------------------------------------------------------------------------

def _extract_wsp_id(filename: str, title: str) -> str:
    """Extract WSP identifier from filename or title."""
    match = re.search(r"WSP[_-]?(\d+)", filename)
    if match:
        return f"WSP {match.group(1)}"
    match = re.search(r"WSP\s*(\d+)", title, re.IGNORECASE)
    if match:
        return f"WSP {match.group(1)}"
    return title.split()[0] if title else "WSP"


def _classify_document_type(file_path: Path, title: str, lines: List[str]) -> str:
    """Classify document type based on filename, path, and content patterns.

    Returns one of: wsp_protocol, module_readme, roadmap, interface,
    modlog, documentation, test_documentation, readme, other.
    """
    filename = file_path.name.lower()
    path_str = str(file_path).lower()

    if filename.startswith('wsp') and filename.endswith('.md'):
        return "wsp_protocol"

    if filename == 'readme.md':
        parent_dir = file_path.parent
        if any((parent_dir / d).exists() for d in ['src', 'tests', 'docs']):
            return "module_readme"
        return "readme"

    if filename == 'roadmap.md':
        return "roadmap"
    if filename == 'interface.md':
        return "interface"
    if filename == 'modlog.md':
        return "modlog"

    if 'docs/' in path_str or 'docs\\' in path_str:
        return "documentation"

    if 'test' in filename and 'readme' in filename:
        return "test_documentation"

    return "other"


def _calculate_document_priority(doc_type: str, file_path: Path) -> int:
    """Calculate document priority for search ranking (1-10, higher = more important)."""
    priority_map = {
        "wsp_protocol": 10,
        "interface": 9,
        "module_readme": 8,
        "documentation": 7,
        "roadmap": 6,
        "modlog": 5,
        "readme": 4,
        "test_documentation": 3,
        "other": 2,
    }

    base_priority = priority_map.get(doc_type, 2)

    path_str = str(file_path).lower()
    if 'wsp_framework' in path_str:
        base_priority += 1
    elif 'modules/' in path_str and 'platform_integration' in path_str:
        base_priority += 1

    return min(base_priority, 10)


# ---------------------------------------------------------------------------
# Web asset helpers
# ---------------------------------------------------------------------------

def _resolve_web_index_roots(holo: "HoloIndex") -> List[Path]:
    """Resolve web asset roots for semantic indexing."""
    roots_env = os.getenv("HOLO_WEB_INDEX_ROOTS", "public")
    roots: List[Path] = []
    for raw_root in roots_env.split(";"):
        candidate = raw_root.strip()
        if not candidate:
            continue
        root_path = Path(candidate)
        if not root_path.is_absolute():
            root_path = holo.project_root / root_path
        roots.append(root_path)
    return roots


def _collect_web_asset_entries(holo: "HoloIndex") -> List[Dict[str, str]]:
    """Collect HTML/JS/CSS assets so UI artifacts are semantically retrievable."""
    enabled = os.getenv("HOLO_INDEX_WEB", "1").lower() in {"1", "true", "yes", "on"}
    if not enabled:
        return []

    roots = _resolve_web_index_roots(holo)
    if not roots:
        return []

    extensions_env = os.getenv("HOLO_WEB_INDEX_EXTENSIONS", ".html;.js;.mjs;.cjs;.css")
    allowed_extensions = {
        ext.strip().lower() for ext in extensions_env.split(";") if ext.strip()
    }
    if not allowed_extensions:
        allowed_extensions = {".html", ".js", ".mjs", ".cjs", ".css"}

    max_files = int(os.getenv("HOLO_WEB_INDEX_MAX_FILES", "300"))
    max_chars = int(os.getenv("HOLO_WEB_INDEX_MAX_CHARS", "5000"))
    skip_dirs = {
        ".git", "__pycache__", "node_modules", "dist", "build", ".next", "coverage"
    }

    entries: List[Dict[str, str]] = []
    for root in roots:
        if len(entries) >= max_files:
            break
        if not root.exists() or not root.is_dir():
            continue

        for file_path in root.rglob("*"):
            if len(entries) >= max_files:
                break
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in allowed_extensions:
                continue
            if any(part in skip_dirs for part in file_path.parts):
                continue

            try:
                raw_text = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if not raw_text.strip():
                continue

            normalized = re.sub(r"\s+", " ", raw_text).strip()
            snippet = normalized[:max_chars]
            try:
                location = str(file_path.relative_to(holo.project_root)).replace("\\", "/")
            except ValueError:
                location = str(file_path).replace("\\", "/")

            token_hint = re.sub(r"[_\\-\\.]+", " ", file_path.stem).strip()
            need = f"web asset {file_path.name}"
            keyword_excerpt = snippet[:1200]
            summary = f"{location} ({file_path.suffix.lower()}) {snippet[:240]}"
            payload = (
                f"Web asset path: {location}\n"
                f"Filename: {file_path.name}\n"
                f"Token hint: {token_hint}\n"
                f"Content: {snippet}"
            )
            entries.append({
                "need": need,
                "location": location,
                "summary": summary,
                "keywords": keyword_excerpt,
                "payload": payload,
            })

    return entries


# ---------------------------------------------------------------------------
# Index orchestrators
# ---------------------------------------------------------------------------

def index_code_entries(holo: "HoloIndex") -> None:
    """Index NAVIGATION code entries and web assets into ChromaDB."""
    nav_entries = list(holo.need_to.items())
    web_assets = _collect_web_asset_entries(holo)

    if not nav_entries and not web_assets:
        holo._log_agent_action("No code or web entries to index", "WARN")
        return

    holo._log_agent_action(f"Indexing {len(nav_entries)} code navigation entries...", "INDEX")
    if web_assets:
        holo._log_agent_action(f"Indexing {len(web_assets)} web assets from public roots...", "INDEX")
    holo.code_collection = holo._reset_collection("navigation_code")

    ids, embeddings, documents, metadatas = [], [], [], []
    for i, (need, location) in enumerate(nav_entries, start=1):
        ids.append(f"code_{i}")
        embeddings.append(holo._get_embedding(need))
        documents.append(location)
        cube = holo._infer_cube_tag(need, location)
        meta: Dict[str, Any] = {
            "need": need,
            "type": "code",
            "source": "NAVIGATION.py",
        }
        if cube:
            meta["cube"] = cube
        metadatas.append(meta)

    next_idx = len(ids) + 1
    for web_asset in web_assets:
        ids.append(f"code_{next_idx}")
        next_idx += 1
        embeddings.append(holo._get_embedding(web_asset["payload"]))
        documents.append(web_asset["location"])
        cube = holo._infer_cube_tag(web_asset["need"], web_asset["location"], web_asset["summary"])
        meta = {
            "need": web_asset["need"],
            "type": "web_asset",
            "source": "public_asset_index",
            "path": web_asset["location"],
            "summary": web_asset["summary"],
            "keywords": web_asset["keywords"],
            "priority": 4,
        }
        if cube:
            meta["cube"] = cube
        metadatas.append(meta)

    holo.code_collection.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
    holo._log_agent_action("Code index refreshed on SSD", "OK")

    # Also index symbols for self-maintaining semantic search (opt-in)
    if os.getenv("HOLO_INDEX_SYMBOLS", "0").lower() in {"1", "true", "yes", "on"}:
        try:
            index_symbol_entries(holo)
        except Exception as exc:
            holo._log_agent_action(f"Symbol index skipped: {exc}", "WARN")


def index_symbol_entries(holo: "HoloIndex", roots: Optional[List[Path]] = None) -> None:
    """Index Python symbols (functions/classes) for semantic discovery.

    HIA6A: Critical infrastructure paths are listed first to ensure they're
    indexed before the 20,000 entry limit is hit. Order matters because
    modules/ alone has 2350+ files with many symbols.
    """
    env_roots = os.getenv("HOLO_SYMBOL_ROOTS")
    if env_roots:
        roots = [holo.project_root / Path(r.strip()) for r in env_roots.split(";") if r.strip()]
    else:
        # HIA6A: Priority ordering ensures critical files are indexed first:
        # - holo_index/core: search_engine.py (core search infrastructure)
        # - wre_core/src: foundup_job_router.py (job routing)
        # - Then bulk directories fill remaining slots
        roots = roots or [
            holo.project_root / "holo_index" / "core",                      # P1: search infrastructure
            holo.project_root / "modules" / "infrastructure" / "wre_core" / "src",  # P1: job routing
            holo.project_root / "modules",                                  # P2: bulk modules
            holo.project_root / "scripts",                                  # P3: scripts
            holo.project_root / "holo_index",                               # P3: remaining holo_index
        ]

    max_files = int(os.getenv("HOLO_SYMBOL_MAX_FILES", "5000"))
    max_entries = int(os.getenv("HOLO_SYMBOL_MAX_ENTRIES", "20000"))
    skip_dirs = {
        ".git", ".venv", "venv", "__pycache__", "node_modules",
        "dist", "build", ".mypy_cache", ".pytest_cache",
    }

    holo._log_agent_action("Indexing symbol entries (functions/classes)...", "INDEX")
    holo.symbol_collection = holo._reset_collection("navigation_symbols")

    ids: List[str] = []
    embeddings: List[List[float]] = []
    documents: List[str] = []
    metadatas: List[Dict[str, Any]] = []

    file_count = 0
    entry_count = 0

    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            if any(part in skip_dirs for part in path.parts):
                continue
            file_count += 1
            if file_count > max_files:
                break
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
                tree = ast.parse(text)
            except Exception:
                continue

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    name = node.name
                    if isinstance(node, ast.ClassDef):
                        symbol = f"class {name}"
                    else:
                        args = []
                        for a in getattr(node, "args", []).args:
                            if hasattr(a, "arg"):
                                args.append(a.arg)
                        sig = ", ".join(args[:8])
                        symbol = f"{name}({sig})"
                    doc = ast.get_docstring(node) or ""
                    line_no = getattr(node, "lineno", None)
                    doc_text = f"{symbol}\n{doc}\n{path}:{line_no or 1}"

                    ids.append(f"sym_{len(ids)+1}")
                    embeddings.append(holo._get_embedding(doc_text))
                    documents.append(doc_text)
                    metadatas.append({
                        "symbol": symbol,
                        "path": str(path),
                        "line": int(line_no) if line_no else 1,
                        "type": "symbol",
                    })

                    entry_count += 1
                    if entry_count >= max_entries:
                        break
                if entry_count >= max_entries:
                    break
            if entry_count >= max_entries:
                break
        if entry_count >= max_entries:
            break

    if ids:
        # ChromaDB has a max batch size (~5000). Batch to avoid InternalError.
        batch_size = 5000
        for start in range(0, len(ids), batch_size):
            end = start + batch_size
            holo.symbol_collection.add(
                ids=ids[start:end],
                embeddings=embeddings[start:end],
                documents=documents[start:end],
                metadatas=metadatas[start:end],
            )
        holo._log_agent_action(f"Symbol index refreshed: {entry_count} entries", "OK")
    else:
        holo._log_agent_action("Symbol index empty - no entries added", "WARN")


def index_wsp_entries(holo: "HoloIndex") -> None:
    """Index WSP protocol documents into ChromaDB.

    CFZ4: ONLY indexes true WSP protocols from WSP_framework/src/WSP_*.md.
    Module docs, papers, and other content go to separate collections.
    """
    # CFZ4: WSP protocols ONLY from WSP_framework/src
    wsp_src_path = holo.project_root / "WSP_framework" / "src"

    if not wsp_src_path.exists():
        holo._log_agent_action(f"WSP source path not found: {wsp_src_path}", "WARN")
        return

    # Only WSP_*.md files are true protocols
    all_wsp_files = sorted(wsp_src_path.glob("WSP_*.md"))
    files = [
        f for f in all_wsp_files
        if not any(part.startswith('.') for part in f.parts)
        and '_backup' not in str(f).lower()
    ]

    if not files:
        holo._log_agent_action("No WSP documents found to index", "WARN")
        return

    holo._log_agent_action(f"Indexing {len(files)} WSP documents...", "INDEX")
    holo.wsp_collection = holo._reset_collection("navigation_wsp")

    ids, embeddings, documents, metadatas = [], [], [], []
    summary_cache: Dict[str, Dict[str, str]] = {}

    for idx, file_path in enumerate(files, start=1):
        # Detect UTF-16 LE (BOM FF FE) and decode correctly (WSP 90)
        raw_head = file_path.read_bytes()[:2]
        if raw_head == b'\xff\xfe':
            text = file_path.read_bytes().decode('utf-16-le', errors='ignore').lstrip('\ufeff')
            holo._log_agent_action(f"UTF-16 detected: {file_path.name} (decoded)", "WARN")
        else:
            text = file_path.read_text(encoding='utf-8', errors='ignore')
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            continue

        title = lines[0].lstrip('# ')
        summary = ' '.join(lines[1:6])[:400]
        wsp_id = _extract_wsp_id(file_path.name, title)
        doc_type = _classify_document_type(file_path, title, lines)
        doc_payload = f"{title}\n{summary}"

        ids.append(f"wsp_{idx}")
        embeddings.append(holo._get_embedding(doc_payload))
        documents.append(doc_payload)
        cube = holo._infer_cube_tag(title, summary, str(file_path))
        metadata: Dict[str, Any] = {
            "wsp": wsp_id,
            "title": title,
            "path": str(file_path),
            "summary": summary,
            "type": doc_type,
            "priority": _calculate_document_priority(doc_type, file_path),
        }
        if cube:
            metadata["cube"] = cube
        metadatas.append(metadata)
        summary_cache[wsp_id] = {
            "title": title,
            "path": str(file_path),
            "summary": summary,
        }

    if embeddings:
        if os.getenv("HOLO_VERBOSE", "").lower() in {"1", "true", "yes"}:
            holo._log_agent_action(
                f"WSP Index counts: ids={len(ids)} docs={len(documents)} embeds={len(embeddings)}",
                "DEBUG",
            )
        holo.wsp_collection.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
        holo.wsp_summary = summary_cache
        holo.wsp_summary_file.write_text(json.dumps(holo.wsp_summary, indent=2), encoding='utf-8')
        holo._log_agent_action("WSP index refreshed and summary cache saved", "OK")
    else:
        holo._log_agent_action("No WSP entries were indexed (empty content)", "WARN")


def index_docs_entries(holo: "HoloIndex") -> None:
    """CFZ4: Index module/root docs into navigation_docs collection.

    Content: modules/**, docs/**, holo_index/docs/**, WSP_framework/docs/**
    ID prefix: doc_
    """
    doc_paths = [
        holo.project_root / "modules",
        holo.project_root / "docs",
        holo.project_root / "holo_index" / "docs",
        holo.project_root / "WSP_framework" / "docs",
    ]

    files: List[Path] = []
    for base in doc_paths:
        if base.exists():
            all_doc_files = sorted(list(base.rglob("*.md")))
            filtered_files = [
                f for f in all_doc_files
                if 'node_modules' not in str(f)
                and 'CHANGELOG' not in f.name.upper()
                and 'package-lock' not in f.name.lower()
                and not any(part.startswith('.') for part in f.parts)
                and '_backup' not in str(f).lower()
                and '/archive/' not in str(f).lower()
                and '\\archive\\' not in str(f).lower()
            ]
            files.extend(filtered_files)

    if not files:
        holo._log_agent_action("No docs found to index", "WARN")
        return

    holo._log_agent_action(f"Indexing {len(files)} docs into navigation_docs...", "INDEX")
    holo.docs_collection = holo._reset_collection("navigation_docs")

    ids, embeddings, documents, metadatas = [], [], [], []

    for idx, file_path in enumerate(files, start=1):
        raw_head = file_path.read_bytes()[:2]
        if raw_head == b'\xff\xfe':
            text = file_path.read_bytes().decode('utf-16-le', errors='ignore').lstrip('\ufeff')
        else:
            text = file_path.read_text(encoding='utf-8', errors='ignore')
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            continue

        title = lines[0].lstrip('# ')
        summary = ' '.join(lines[1:6])[:400]
        doc_type = _classify_document_type(file_path, title, lines)
        doc_payload = f"{title}\n{summary}"

        ids.append(f"doc_{idx}")
        embeddings.append(holo._get_embedding(doc_payload))
        documents.append(doc_payload)
        metadatas.append({
            "title": title,
            "path": str(file_path),
            "summary": summary,
            "type": doc_type,
            "priority": _calculate_document_priority(doc_type, file_path),
        })

    if embeddings:
        holo.docs_collection.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
        holo._log_agent_action(f"Docs index refreshed: {len(ids)} entries", "OK")
    else:
        holo._log_agent_action("No docs entries were indexed", "WARN")


def index_knowledge_entries(holo: "HoloIndex") -> None:
    """CFZ4: Index papers/research into navigation_knowledge collection.

    Content: WSP_knowledge/docs/Papers/**
    ID prefix: paper_
    """
    knowledge_path = holo.project_root / "WSP_knowledge" / "docs" / "Papers"

    if not knowledge_path.exists():
        holo._log_agent_action(f"Knowledge path not found: {knowledge_path}", "WARN")
        return

    all_files = sorted(knowledge_path.rglob("*.md"))
    files = [
        f for f in all_files
        if not any(part.startswith('.') for part in f.parts)
        and '_backup' not in str(f).lower()
        and '/archive/' not in str(f).lower()
        and '\\archive\\' not in str(f).lower()
    ]

    if not files:
        holo._log_agent_action("No knowledge files found to index", "WARN")
        return

    holo._log_agent_action(f"Indexing {len(files)} papers into navigation_knowledge...", "INDEX")
    holo.knowledge_collection = holo._reset_collection("navigation_knowledge")

    ids, embeddings, documents, metadatas = [], [], [], []

    for idx, file_path in enumerate(files, start=1):
        raw_head = file_path.read_bytes()[:2]
        if raw_head == b'\xff\xfe':
            text = file_path.read_bytes().decode('utf-16-le', errors='ignore').lstrip('\ufeff')
        else:
            text = file_path.read_text(encoding='utf-8', errors='ignore')
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            continue

        title = lines[0].lstrip('# ')
        summary = ' '.join(lines[1:6])[:400]
        doc_payload = f"{title}\n{summary}"

        ids.append(f"paper_{idx}")
        embeddings.append(holo._get_embedding(doc_payload))
        documents.append(doc_payload)
        metadatas.append({
            "title": title,
            "path": str(file_path),
            "summary": summary,
            "type": "paper",
            "priority": 6,
        })

    if embeddings:
        holo.knowledge_collection.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
        holo._log_agent_action(f"Knowledge index refreshed: {len(ids)} papers", "OK")
    else:
        holo._log_agent_action("No knowledge entries were indexed", "WARN")


def index_test_registry(holo: "HoloIndex") -> None:
    """WSP 98: Ingest the WSP Test Registry into ChromaDB for semantic search."""
    registry_path = holo.project_root / "WSP_knowledge" / "WSP_Test_Registry.json"

    if not registry_path.exists():
        holo._log_agent_action("WSP_Test_Registry.json not found", "WARN")
        return

    try:
        registry_data = json.loads(registry_path.read_text(encoding='utf-8'))
    except Exception as e:
        holo._log_agent_action(f"Failed to load test registry: {e}", "ERROR")
        return

    if not registry_data:
        holo._log_agent_action("WSP Test Registry is empty", "WARN")
        return

    holo._log_agent_action(f"Indexing {len(registry_data)} test entries...", "INDEX")
    holo.test_collection = holo._reset_collection("navigation_tests")

    ids, embeddings, documents, metadatas = [], [], [], []

    for idx, entry in enumerate(registry_data.values(), start=1):
        test_id = entry.get('id', f'test_{idx}')
        path = entry.get('path', '')
        description = entry.get('description', '')
        capabilities = ", ".join(entry.get('capabilities', []))
        execution_type = entry.get('execution_type', 'unknown')

        doc_payload = f"Test: {test_id}\nType: {execution_type}\nCapabilities: {capabilities}\nDescription: {description}"

        ids.append(f"test_{idx}")
        embeddings.append(holo._get_embedding(doc_payload))
        documents.append(doc_payload)

        metadatas.append({
            "test_id": test_id,
            "path": path,
            "description": description[:1000],
            "capabilities": capabilities,
            "type": "test",
            "priority": 8,
        })

    if embeddings:
        holo.test_collection.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
        holo._log_agent_action("Test Registry index refreshed on SSD", "OK")
    else:
        holo._log_agent_action("No test entries indexed", "WARN")


def index_skillz_entries(holo: "HoloIndex") -> None:
    """WSP 95: Index SKILLz files for agent discovery."""
    import glob
    import yaml

    skillz_patterns = [
        str(holo.project_root / "modules" / "**" / "skills" / "*" / "SKILLz.md"),
        str(holo.project_root / "modules" / "**" / "skillz" / "*" / "SKILLz.md"),
        str(holo.project_root / "holo_index" / "skillz" / "*" / "SKILLz.md"),
        str(holo.project_root / "holo_index" / "qwen_advisor" / "skills" / "*" / "SKILLz.md"),
        str(holo.project_root / ".claude" / "skills" / "*" / "SKILLz.md"),
        str(holo.project_root / ".claude" / "skillz" / "*" / "SKILLz.md"),
    ]

    files: List[Path] = []
    for pattern in skillz_patterns:
        found = glob.glob(pattern, recursive=True)
        files.extend(Path(f) for f in found)

    if not files:
        holo._log_agent_action("No SKILLz files found to index", "WARN")
        return

    holo._log_agent_action(f"Indexing {len(files)} SKILLz files...", "INDEX")
    holo.skill_collection = holo._reset_collection("navigation_skills")

    ids, embeddings, documents, metadatas = [], [], [], []

    for idx, file_path in enumerate(files, start=1):
        try:
            text = file_path.read_text(encoding='utf-8', errors='ignore')

            # Parse YAML frontmatter
            frontmatter: Dict[str, Any] = {}
            if text.startswith('---'):
                parts = text.split('---', 2)
                if len(parts) >= 3:
                    try:
                        frontmatter = yaml.safe_load(parts[1]) or {}
                    except Exception:
                        pass
                    content = parts[2]
                else:
                    content = text
            else:
                content = text

            name = str(frontmatter.get('name', file_path.parent.name) or file_path.parent.name)
            description_raw = frontmatter.get('description', '')
            description = str(description_raw) if description_raw is not None else ''
            agents = frontmatter.get('agents', [])
            primary_agent = str(frontmatter.get('primary_agent', 'unknown') or 'unknown')
            intent_type = str(frontmatter.get('intent_type', 'unknown') or 'unknown')
            promotion_state = str(frontmatter.get('promotion_state', 'prototype') or 'prototype')

            lines = content.strip().split('\n')
            summary = ' '.join(lines[:10])[:500]
            doc_payload = (
                f"Skillz: {name}\n"
                f"Agent: {primary_agent}\n"
                f"Type: {intent_type}\n"
                f"Description: {description}\n"
                f"{summary}"
            )
            metadata: Dict[str, Any] = {
                "skill_name": name,
                "description": description[:500],
                "agents": ','.join(agents) if isinstance(agents, list) else str(agents),
                "primary_agent": primary_agent,
                "intent_type": intent_type,
                "promotion_state": promotion_state,
                "path": str(file_path),
                "type": "skillz",
                "priority": 9,
            }

            embedding = holo._get_embedding(doc_payload)
            ids.append(f"skill_{idx}")
            embeddings.append(embedding)
            documents.append(doc_payload)
            metadatas.append(metadata)

        except Exception as e:
            holo._log_agent_action(f"Failed to parse SKILLz {file_path}: {e}", "WARN")
            continue

    if embeddings:
        if not (len(ids) == len(embeddings) == len(documents) == len(metadatas)):
            holo._log_agent_action(
                (
                    "SKILLz index length mismatch detected "
                    f"(ids={len(ids)}, embeddings={len(embeddings)}, "
                    f"documents={len(documents)}, metadatas={len(metadatas)}). "
                    "Aborting collection add."
                ),
                "ERROR",
            )
            return
        holo.skill_collection.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
        holo._log_agent_action(f"SKILLz index refreshed: {len(embeddings)} skills indexed", "OK")
    else:
        holo._log_agent_action("No SKILLz entries were indexed", "WARN")
