# -*- coding: utf-8 -*-
"""HoloIndex Search Engine — extracted search surface.

Provides the core search pipeline previously inlined in HoloIndex.
All public functions accept a ``holo`` (HoloIndex instance) parameter so
they can access collections, model, cache, and logging without coupling
to the class hierarchy.

WSP Compliance: WSP 87 (Size Limits), WSP 72 (Block Independence)
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .holo_index import HoloIndex

# Re-use the module-level timeout helper already in holo_index.py
from .holo_index import _run_with_timeout, HOLO_ENCODE_TIMEOUT

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _tokenize_query(query: str) -> List[str]:
    """Split *query* into lowercase alphanumeric tokens."""
    return [token for token in re.findall(r"[a-z0-9_]+", query.lower()) if token]


def _is_symbol_query(query: str) -> bool:
    """Heuristic: detect symbol-like queries (identifiers, paths, function calls)."""
    if not query:
        return False
    if "/" in query or "\\" in query or query.endswith(".py"):
        return True
    if "(" in query and ")" in query:
        return True
    if "_" in query:
        return True
    if query.isidentifier():
        return True
    return False


def _merge_hits(
    primary: List[Dict[str, Any]],
    secondary: List[Dict[str, Any]],
    limit: int,
) -> List[Dict[str, Any]]:
    """Merge hit lists with robust de-duplication and cap to *limit*.

    WSP 87 noise reduction: Normalizes paths (forward slashes, lowercase)
    to prevent duplicate entries from path format variations.
    """
    seen: set[str] = set()
    merged: List[Dict[str, Any]] = []

    def _normalize_key(raw_key: str) -> str:
        k = raw_key.replace("\\", "/").lower().strip()
        for prefix in ("o:/foundups-agent/", "o:\\foundups-agent\\"):
            if k.startswith(prefix):
                k = k[len(prefix):]
        return k

    for hit in primary + secondary:
        raw_key = hit.get("path") or hit.get("location") or hit.get("id") or hit.get("title")
        if not raw_key:
            continue
        key = _normalize_key(raw_key)
        if key in seen:
            continue
        seen.add(key)
        merged.append(hit)
        if len(merged) >= limit:
            break
    return merged


# ---------------------------------------------------------------------------
# ripgrep symbol fallback
# ---------------------------------------------------------------------------

def _rg_symbol_search(project_root, query: str, limit: int) -> List[Dict[str, Any]]:
    """Fallback: exact symbol search via ripgrep for NAVIGATION gaps."""
    try:
        root = str(project_root).replace("\\", "/")
        rg_path = shutil.which("rg") or "rg"
        cmd = [
            rg_path,
            "-n",
            "--no-heading",
            f"--max-count={max(1, limit * 3)}",
            "-S",
            query,
            root,
        ]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
    except Exception:
        return []

    if proc.returncode not in (0, 1):  # 1 = no matches
        return []

    hits: List[Dict[str, Any]] = []
    for line in (proc.stdout or "").splitlines():
        match = re.match(r"^([A-Za-z]:\\\\.*?):(\d+):(.*)$", line)
        if not match:
            match = re.match(r"^(.*?):(\d+):(.*)$", line)
        if not match:
            continue
        path = match.group(1).strip()
        line_no = match.group(2).strip()
        location = f"{path}:{line_no}"
        hits.append({
            "need": query,
            "location": location,
            "path": path,
            "line": int(line_no) if line_no.isdigit() else None,
            "type": "code",
            "priority": 10,
        })
    if not hits:
        return []

    def _ext_rank(p: str) -> int:
        p = p.lower()
        if p.endswith((".py", ".ts", ".tsx", ".js", ".jsx")):
            return 0
        if p.endswith((".md", ".rst", ".txt")):
            return 2
        return 1

    hits.sort(key=lambda h: (_ext_rank(h.get("path", "")), h.get("path", "")))
    filtered: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for hit in hits:
        path = hit.get("path")
        if not path or path in seen:
            continue
        seen.add(path)
        filtered.append(hit)
        if len(filtered) >= limit:
            break
    return filtered


# ---------------------------------------------------------------------------
# Collection search (vector + hybrid scoring)
# ---------------------------------------------------------------------------

def _search_collection(
    holo: "HoloIndex",
    collection,
    query: str,
    limit: int,
    kind: str,
    doc_type_filter: str = "all",
) -> List[Dict[str, Any]]:
    """Search a ChromaDB *collection* using vector embeddings with hybrid keyword scoring.

    Falls back to lexical search when the embedding model is unavailable.
    """
    if collection is None:
        return []

    try:
        if collection.count() == 0:
            return []
    except Exception:
        return []

    model = getattr(holo, "model", None)
    if model is None:
        holo._log_agent_action("Embedding model not available - using offline lexical scan", "WARN")
        return _lexical_search_collection(holo, collection, query, limit, kind, doc_type_filter)

    # WSP 97: Encode with timeout to prevent indefinite hangs
    embedding = _run_with_timeout(
        lambda: model.encode(query, show_progress_bar=False).tolist(),
        timeout_sec=HOLO_ENCODE_TIMEOUT,
        default=None,
        error_msg=f"model.encode() timed out for query '{query[:50]}'",
    )
    if embedding is None:
        holo._log_agent_action("Encoding timed out - falling back to lexical search", "WARN")
        return _lexical_search_collection(holo, collection, query, limit, kind, doc_type_filter)

    results = collection.query(query_embeddings=[embedding], n_results=limit)

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    dists = results.get("distances", [[]])[0]

    doc_count = len(docs)
    if doc_count == 0:
        return []

    min_similarity = float(os.getenv("HOLO_MIN_SIMILARITY", "0.35"))

    raw_results: List[Dict[str, Any]] = []
    for i in range(doc_count):
        doc = docs[i]
        meta = metas[i]
        distance = dists[i]

        similarity = 1.0 / (1.0 + float(distance))

        if similarity < min_similarity:
            continue
        doc_type = meta.get("type", "other")
        priority = meta.get("priority", 1)

        keyword_score = 0.0
        ql = query.lower()
        title = (meta.get("title") or "").lower()
        path = (meta.get("path") or "").lower()
        summary = (meta.get("summary") or "").lower()
        keywords = (meta.get("keywords") or "").lower()
        test_id = (meta.get("test_id") or "").lower()
        capabilities = (meta.get("capabilities") or "").lower()

        for token in set(ql.split()):
            if not token:
                continue
            if token in title:
                keyword_score += 2.0
            if token in path:
                keyword_score += 1.0
            if token in summary:
                keyword_score += 0.5
            if token in keywords:
                keyword_score += 1.25
            if token in test_id:
                keyword_score += 3.0
            if token in capabilities:
                keyword_score += 1.5

        if doc_type_filter != "all" and not doc_type.startswith(doc_type_filter):
            continue

        result = _format_hit(kind, meta, doc, similarity, keyword_score, priority)
        raw_results.append(result)

    raw_results.sort(key=lambda x: x["_sort_key"], reverse=True)

    formatted = []
    for result in raw_results[:limit]:
        result_copy = result.copy()
        del result_copy["_sort_key"]
        formatted.append(result_copy)
    return formatted


# ---------------------------------------------------------------------------
# Lexical search fallback
# ---------------------------------------------------------------------------

def _lexical_search_collection(
    holo: "HoloIndex",
    collection,
    query: str,
    limit: int,
    kind: str,
    doc_type_filter: str = "all",
) -> List[Dict[str, Any]]:
    """Keyword-based search used when embedding model is unavailable."""
    tokens = _tokenize_query(query)
    if not tokens:
        return []

    try:
        total = collection.count()
    except Exception:
        return []
    if total == 0:
        return []

    batch_size = int(os.getenv("HOLO_LEXICAL_BATCH", "500"))
    max_docs_env = os.getenv("HOLO_LEXICAL_MAX_DOCS")
    max_docs = int(max_docs_env) if max_docs_env else total

    raw_results: List[Dict[str, Any]] = []
    offset = 0
    scanned = 0
    include = ["documents", "metadatas"]

    while offset < total and scanned < max_docs:
        batch_limit = min(batch_size, total - offset, max_docs - scanned)
        try:
            chunk = collection.get(include=include, limit=batch_limit, offset=offset)
        except TypeError:
            chunk = collection.get(include=include)
            offset = total
            scanned = total
        docs = chunk.get("documents", [])
        metas = chunk.get("metadatas", [])

        if docs and isinstance(docs[0], list):
            docs = docs[0]
        if metas and isinstance(metas[0], list):
            metas = metas[0]

        for doc, meta in zip(docs, metas):
            meta = meta or {}
            doc_type = meta.get("type", "other")

            if doc_type_filter != "all" and doc_type != doc_type_filter:
                continue

            keyword_score = 0.0
            title = (meta.get("title") or "").lower()
            path = (meta.get("path") or "").lower()
            summary = (meta.get("summary") or "").lower()
            keywords = (meta.get("keywords") or "").lower()
            test_id = (meta.get("test_id") or "").lower()
            capabilities = (meta.get("capabilities") or "").lower()
            description = (meta.get("description") or "").lower()
            need = (meta.get("need") or "").lower()
            doc_text = (doc or "").lower()

            for token in tokens:
                if token in title:
                    keyword_score += 2.0
                if token in path:
                    keyword_score += 1.0
                if token in summary:
                    keyword_score += 0.5
                if token in keywords:
                    keyword_score += 1.25
                if token in need:
                    keyword_score += 2.0
                if token in doc_text:
                    keyword_score += 0.25
                if token in test_id:
                    keyword_score += 3.0
                if token in capabilities:
                    keyword_score += 1.5
                if token in description:
                    keyword_score += 0.5

            if keyword_score <= 0:
                continue

            similarity = min(1.0, keyword_score / max(1.0, len(tokens) * 2.5))
            priority = meta.get("priority", 1)

            result = _format_hit(kind, meta, doc, similarity, keyword_score, priority)
            raw_results.append(result)

        offset += batch_limit
        scanned += batch_limit

    if not raw_results:
        return []

    raw_results.sort(key=lambda x: x["_sort_key"], reverse=True)
    formatted = []
    for result in raw_results[:limit]:
        result_copy = result.copy()
        del result_copy["_sort_key"]
        formatted.append(result_copy)
    return formatted


# ---------------------------------------------------------------------------
# Hit formatting (shared between vector and lexical paths)
# ---------------------------------------------------------------------------

def _format_hit(
    kind: str,
    meta: Dict[str, Any],
    doc: str,
    similarity: float,
    keyword_score: float,
    priority: int,
) -> Dict[str, Any]:
    """Build a single search hit dict with ``_sort_key`` for ranking."""
    sim_str = f"{similarity * 100:.1f}%"

    if kind == "code":
        return {
            "need": meta.get("need"),
            "location": doc,
            "similarity": sim_str,
            "cube": meta.get("cube"),
            "type": meta.get("type", "other"),
            "priority": priority,
            "_sort_key": (0.5 * priority + 0.3 * similarity + 0.2 * keyword_score, similarity, priority),
        }
    if kind == "test":
        return {
            "test_id": meta.get("test_id"),
            "path": meta.get("path"),
            "description": meta.get("description"),
            "capabilities": meta.get("capabilities"),
            "similarity": sim_str,
            "type": "test",
            "priority": priority,
            "_sort_key": (0.5 * priority + 0.3 * similarity + 0.2 * keyword_score, similarity, priority),
        }
    if kind == "skill":
        return {
            "skill_name": meta.get("skill_name"),
            "description": meta.get("description"),
            "primary_agent": meta.get("primary_agent"),
            "intent_type": meta.get("intent_type"),
            "promotion_state": meta.get("promotion_state"),
            "path": meta.get("path"),
            "similarity": sim_str,
            "type": "skillz",
            "priority": priority,
            "_sort_key": (0.6 * priority + 0.3 * similarity + 0.1 * keyword_score, similarity, priority),
        }
    # WSP / default
    return {
        "wsp": meta.get("wsp"),
        "title": meta.get("title"),
        "summary": meta.get("summary"),
        "path": meta.get("path"),
        "similarity": sim_str,
        "cube": meta.get("cube"),
        "type": meta.get("type", "other"),
        "priority": priority,
        "_sort_key": (0.5 * priority + 0.3 * similarity + 0.2 * keyword_score, similarity, priority),
    }


# ---------------------------------------------------------------------------
# HoloDAE notification
# ---------------------------------------------------------------------------

def _notify_holodae_search() -> None:
    """Notify HoloDAE of recent search activity for agent attribution."""
    try:
        import sys as _sys
        for module_name, module in _sys.modules.items():
            if module_name.startswith("holo_index.qwen_advisor.autonomous_holodae"):
                if hasattr(module, "AutonomousHoloDAE"):
                    for obj in __import__("gc").get_referrers(module.AutonomousHoloDAE):
                        if isinstance(obj, module.AutonomousHoloDAE):
                            try:
                                obj.record_search_activity()
                            except Exception:
                                pass
                    break
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Main search entry point
# ---------------------------------------------------------------------------

def execute_search(
    holo: "HoloIndex",
    query: str,
    limit: int = 10,
    doc_type_filter: str = "all",
) -> Dict[str, Any]:
    """Run a full HoloIndex search and return the canonical result payload.

    This is the extracted core of ``HoloIndex.search()``.
    """
    try:
        # Fast path: check cache first (WSP 91 performance optimization)
        search_cache = getattr(holo, "search_cache", None)
        if search_cache is not None:
            cached = search_cache.get(query, doc_type_filter)
            if cached is not None:
                holo._log_agent_action(f"[CACHE HIT] '{query}' (limit={limit})", "FAST")
                return cached

        holo._log_agent_action(f"Searching: '{query}' (limit={limit}, type={doc_type_filter})")

        code_hits: List[Dict[str, Any]] = []
        wsp_hits: List[Dict[str, Any]] = []
        test_hits: List[Dict[str, Any]] = []
        skill_hits: List[Dict[str, Any]] = []
        symbol_results: List[Dict[str, Any]] = []

        symbol_query = _is_symbol_query(query)
        force_symbol_scan = os.getenv("HOLO_FORCE_SYMBOL_SCAN", "0").lower() in {"1", "true", "yes", "on"}
        model = getattr(holo, "model", None)
        should_scan_symbols = force_symbol_scan or symbol_query or (model is not None)

        code_collection = getattr(holo, "code_collection", None)
        symbol_collection = getattr(holo, "symbol_collection", None)
        wsp_collection = getattr(holo, "wsp_collection", None)
        test_collection = getattr(holo, "test_collection", None)
        skill_collection = getattr(holo, "skill_collection", None)

        # Search code index
        if doc_type_filter in ["code", "all"] and code_collection is not None:
            code_results = _search_collection(holo, code_collection, query, limit, kind="code")
            code_hits = holo._enhance_code_results_with_previews(code_results)
            if should_scan_symbols and symbol_collection is not None:
                symbol_results = _search_collection(holo, symbol_collection, query, limit, kind="symbol")
            if symbol_results:
                code_hits = _merge_hits(symbol_results, code_hits, limit)

        # Search WSP index
        if doc_type_filter not in ["code", "test"] and wsp_collection is not None:
            wsp_hits = _search_collection(holo, wsp_collection, query, limit, kind="wsp", doc_type_filter=doc_type_filter)

        # Search Test index
        if doc_type_filter in ["test", "all"] and test_collection is not None:
            test_hits = _search_collection(holo, test_collection, query, limit, kind="test", doc_type_filter=doc_type_filter)

        # Search Skillz index
        if doc_type_filter == "all" and skill_collection is not None:
            try:
                skill_hits = _search_collection(holo, skill_collection, query, limit, kind="skill")
            except Exception:
                skill_hits = []

        # Symbol-query fallback: lexical + rg for exact identifiers/paths
        if symbol_query:
            if doc_type_filter in ["code", "all"] and code_collection is not None:
                lexical_code = _lexical_search_collection(holo, code_collection, query, limit, kind="code")
                if lexical_code:
                    code_hits = _merge_hits(code_hits, lexical_code, limit)
                rg_hits = _rg_symbol_search(holo.project_root, query, limit)
                if rg_hits:
                    code_hits = _merge_hits(rg_hits, code_hits, limit)
            if doc_type_filter in ["all"] and not wsp_hits and wsp_collection is not None:
                lexical_wsp = _lexical_search_collection(holo, wsp_collection, query, limit, kind="wsp", doc_type_filter=doc_type_filter)
                if lexical_wsp:
                    wsp_hits = _merge_hits(wsp_hits, lexical_wsp, limit)

        holo._log_agent_action(
            f"Search complete: {len(code_hits)} code, {len(wsp_hits)} WSP, "
            f"{len(test_hits)} Tests, {len(skill_hits)} Skillz"
        )

        payload: Dict[str, Any] = {
            "code_hits": code_hits,
            "wsp_hits": wsp_hits,
            "test_hits": test_hits,
            "code": code_hits,
            "wsps": wsp_hits,
            "tests": test_hits,
            "skills": skill_hits,
            "skill_hits": skill_hits,
            "symbol_hits": symbol_results,
            "metadata": {
                "query": query,
                "code_count": len(code_hits),
                "wsp_count": len(wsp_hits),
                "test_count": len(test_hits),
                "skill_count": len(skill_hits),
                "symbol_count": len(symbol_results),
                "timestamp": datetime.now().isoformat(),
                "cached": False,
                # FX1-D: Surface retrieval mode in search results
                "retrieval_mode": getattr(holo, "retrieval_mode", "unknown"),
            },
        }

        if search_cache is not None:
            search_cache.put(query, doc_type_filter, payload)

        return payload

    except Exception as e:
        holo._log_agent_action(f"Search error: {str(e)}", "ERROR")
        return {
            "code_hits": [],
            "wsp_hits": [],
            "code": [],
            "wsps": [],
            "metadata": {"error": str(e)},
        }
