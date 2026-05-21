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


# ---------------------------------------------------------------------------
# HIA3 (2026-04-23): backend quality taxonomy (WSP 97 truth distinction).
#
# These dicts map embedding_backend -> quality claim. They are surfaced on
# every search response's metadata so callers can distinguish a
# default-ready backend (SentenceTransformer fp32) from an experimental
# opt-in backend (TurboQuant ONNX int8) without re-checking env vars.
#
#   backend_quality ∈ {production, experimental, n/a, unknown}
#   quality_gate    ∈ {default_ready, not_default_ready, n/a, unknown}
#
# "n/a" is used when no embedder is loaded (lexical/failed retrieval).
# ---------------------------------------------------------------------------

_BACKEND_QUALITY: Dict[str, str] = {
    "sentence_transformers": "production",
    "turboquant_onnx_int8": "experimental",
    "none": "n/a",
    # TQ3: when per-collection routing is active, the top-level backend
    # is "routed" — a mixed claim. Callers needing per-collection truth
    # read ``collection_backend_map`` on the same metadata block.
    "routed": "mixed",
}

_QUALITY_GATE: Dict[str, str] = {
    "sentence_transformers": "default_ready",
    "turboquant_onnx_int8": "not_default_ready",
    "none": "n/a",
    "routed": "mixed",
}


def _backend_quality(backend: str) -> str:
    """Return the quality claim for *backend*; 'unknown' if not registered."""
    return _BACKEND_QUALITY.get(backend, "unknown")


def _quality_gate(backend: str) -> str:
    """Return the default-promotion gate for *backend*; 'unknown' if not registered."""
    return _QUALITY_GATE.get(backend, "unknown")


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


# ---------------------------------------------------------------------------
# HIA4B: WSP number extraction for exact matching
# ---------------------------------------------------------------------------

_WSP_NUMBER_PATTERN = re.compile(
    r"\bWSP[\s_\-]?(\d+)(?:\b|_)",  # Match WSP 97, WSP_97, WSP-97, WSP_97_xxx
    re.IGNORECASE
)

# HXA Audit Fix: Slice ID pattern for HXA, FX, CFZ
_SLICE_ID_PATTERN = re.compile(
    r"\b(HXA\d+|FX\d+|CFZ\d+)\b",  # Match HXA22, FX1, CFZ4, etc.
    re.IGNORECASE
)


def _extract_wsp_numbers(text: str) -> List[str]:
    """Extract WSP numbers from text (e.g., 'WSP 97', 'WSP_97', 'WSP-97').

    Returns list of normalized WSP numbers like ['97', '00'].
    """
    matches = _WSP_NUMBER_PATTERN.findall(text)
    return [m.lstrip("0") or "0" for m in matches]  # Normalize: '00' -> '0', '97' -> '97'


def _extract_slice_ids(text: str) -> List[str]:
    """HXA Audit Fix: Extract slice IDs from text (e.g., 'HXA22', 'FX1', 'CFZ4').

    Returns list of normalized slice IDs like ['HXA22', 'CFZ4'].
    """
    matches = _SLICE_ID_PATTERN.findall(text)
    return [m.upper() for m in matches]


def _slice_id_match_boost(query: str, path: str, title: str, meta_slice_id: str = "") -> float:
    """HXA Audit Fix: Return keyword boost if query slice ID matches path/title/metadata.

    Boosts exact slice ID matches (HXA22, FX1, CFZ4) to fix retrieval gaps.
    """
    query_slices = _extract_slice_ids(query)
    if not query_slices:
        return 0.0

    # Check path, title, and metadata slice_id
    path_slices = _extract_slice_ids(path)
    title_slices = _extract_slice_ids(title)
    all_target_slices = set(path_slices + title_slices)
    if meta_slice_id:
        all_target_slices.add(meta_slice_id.upper())

    # Strong boost for exact match
    for qslice in query_slices:
        if qslice in all_target_slices:
            return 5.0  # Strong boost for exact slice ID match

    return 0.0


def _normalize_for_match(text: str) -> str:
    """Normalize text for fuzzy matching: lowercase, remove underscores.

    HIA6B: Enables 'holoindex' to match 'holo_index' paths.
    """
    return text.lower().replace("_", "")


# ---------------------------------------------------------------------------
# Work Ledger Boost Functions (FOUNDUPS_WORK_LEDGER_HOLOINDEX_IMPLEMENTATION_PHASE1)
# ---------------------------------------------------------------------------

_PR_NUMBER_PATTERN = re.compile(r"\bPR[\s#]?(\d+)\b", re.IGNORECASE)
_WORKER_PATTERN = re.compile(r"\b(W\d+|0102-[A-G])\b", re.IGNORECASE)
_STATUS_PATTERN = re.compile(
    r"\b(IN_PROGRESS|STAGED_FOR_W10|PR_OPEN|ASSIGNED|PROPOSED|BLOCKED|PARKED|MERGED|CLOSED|SUPERSEDED|ABANDONED)\b",
    re.IGNORECASE
)


def _extract_pr_numbers(text: str) -> List[str]:
    """Extract PR numbers from text (e.g., 'PR 642', 'PR#642', 'PR642')."""
    matches = _PR_NUMBER_PATTERN.findall(text)
    return matches


def _extract_workers(text: str) -> List[str]:
    """Extract worker IDs from text (e.g., 'W9', 'W10', '0102-A')."""
    matches = _WORKER_PATTERN.findall(text)
    return [m.upper() for m in matches]


def _extract_statuses(text: str) -> List[str]:
    """Extract work ledger statuses from text."""
    matches = _STATUS_PATTERN.findall(text)
    return [m.upper() for m in matches]


def _pr_number_match_boost(query: str, meta_pr_number: int) -> float:
    """Return 2.5x boost if query PR number matches metadata pr_number.

    Spec: FOUNDUPS_WORK_LEDGER_HOLOINDEX_INDEXING_SPEC_PHASE1 Section 3.4
    """
    if meta_pr_number <= 0:
        return 0.0

    query_prs = _extract_pr_numbers(query)
    for pr_str in query_prs:
        if int(pr_str) == meta_pr_number:
            return 2.5

    return 0.0


def _owner_worker_match_boost(query: str, meta_owner_worker: str) -> float:
    """Return 2.0x boost if query worker ID matches metadata owner_worker.

    Spec: FOUNDUPS_WORK_LEDGER_HOLOINDEX_INDEXING_SPEC_PHASE1 Section 3.4
    """
    if not meta_owner_worker:
        return 0.0

    query_workers = _extract_workers(query)
    meta_worker_normalized = meta_owner_worker.upper()

    for worker in query_workers:
        if worker == meta_worker_normalized:
            return 2.0

    return 0.0


def _branch_match_boost(query: str, meta_branch: str) -> float:
    """Return 2.0x boost if query branch name matches metadata branch.

    Spec: FOUNDUPS_WORK_LEDGER_HOLOINDEX_INDEXING_SPEC_PHASE1 Section 3.4
    """
    if not meta_branch:
        return 0.0

    query_lower = query.lower()
    branch_lower = meta_branch.lower()

    if branch_lower in query_lower or query_lower in branch_lower:
        return 2.0

    branch_tokens = set(branch_lower.replace("/", "-").replace("_", "-").split("-"))
    query_tokens = set(query_lower.split())
    if len(branch_tokens & query_tokens) >= 2:
        return 1.5

    return 0.0


def _status_match_boost(query: str, meta_status: str) -> float:
    """Return 1.5x boost if query status matches metadata status.

    Spec: FOUNDUPS_WORK_LEDGER_HOLOINDEX_INDEXING_SPEC_PHASE1 Section 3.4
    """
    if not meta_status:
        return 0.0

    query_statuses = _extract_statuses(query)
    meta_status_normalized = meta_status.upper()

    for status in query_statuses:
        if status == meta_status_normalized:
            return 1.5

    query_lower = query.lower()
    if "open" in query_lower and meta_status_normalized in ("IN_PROGRESS", "PR_OPEN", "PROPOSED", "ASSIGNED", "STAGED_FOR_W10"):
        return 1.0
    if "blocked" in query_lower and meta_status_normalized == "BLOCKED":
        return 1.5
    if "merged" in query_lower and meta_status_normalized == "MERGED":
        return 1.5

    return 0.0


def _related_foundup_match_boost(query: str, meta_related_foundup_id: str) -> float:
    """Return 2.0x boost if query contains the related foundup ID.

    Spec: FOUNDUPS_WORK_LEDGER_HOLOINDEX_INDEXING_SPEC_PHASE1 Section 3.4
    """
    if not meta_related_foundup_id:
        return 0.0

    query_lower = query.lower()
    foundup_lower = meta_related_foundup_id.lower()

    # Exact match in query
    if foundup_lower in query_lower:
        return 2.0

    # Match base name without suffix (e.g., "gotjunk" matches "gotjunk_001")
    foundup_base = foundup_lower.split("_")[0] if "_" in foundup_lower else foundup_lower
    if foundup_base and foundup_base in query_lower:
        return 2.0

    return 0.0


def _work_ledger_combined_boost(
    query: str,
    meta: Dict[str, Any],
) -> float:
    """Apply all work ledger boosts and return combined score.

    This is called for work_ledger_slice type entries.
    """
    total = 0.0

    pr_number = meta.get("pr_number", -1)
    if isinstance(pr_number, int):
        total += _pr_number_match_boost(query, pr_number)

    owner_worker = meta.get("owner_worker", "")
    if owner_worker:
        total += _owner_worker_match_boost(query, owner_worker)

    branch = meta.get("branch", "")
    if branch:
        total += _branch_match_boost(query, branch)

    status = meta.get("status", "")
    if status:
        total += _status_match_boost(query, status)

    related_foundup_id = meta.get("related_foundup_id", "")
    if related_foundup_id:
        total += _related_foundup_match_boost(query, related_foundup_id)

    return total


def _wsp_number_match_boost(query: str, path: str, title: str) -> float:
    """Return keyword boost if query WSP number matches path/title WSP number.

    HIA4B: Boosts exact WSP number matches to fix WSP 97 finding WSP 94.
    """
    query_wsps = _extract_wsp_numbers(query)
    if not query_wsps:
        return 0.0

    # Check path and title for WSP numbers
    path_wsps = _extract_wsp_numbers(path)
    title_wsps = _extract_wsp_numbers(title)
    all_target_wsps = set(path_wsps + title_wsps)

    # Strong boost for exact match
    for qwsp in query_wsps:
        if qwsp in all_target_wsps:
            return 5.0  # Strong boost for exact WSP number match

    return 0.0


# ---------------------------------------------------------------------------
# HIA5: WSP alias registry for natural-language recall
# ---------------------------------------------------------------------------

# Maps natural-language operational phrases to WSP numbers.
# When a query matches an alias phrase, the corresponding WSP number
# gets the same boost as if the user had typed "WSP <number>" explicitly.
# No LLM required. Deterministic pattern matching.

_WSP_ALIAS_REGISTRY: Dict[str, List[str]] = {
    "97": [
        "retrieve evidence before stating facts",
        "function agentically",
        "apply cot cor",
        "apply cot/cor",
        "chain of thought chain of reasoning",
        "hard think",
        "dialectic sweep",
        "first principles then execute",
        "first principles execute",
        "holoindex research build follow wsp",
        "holoindex research hard think",
        "retrieve wsp retrieve evidence",
        "micro pass macro pass",
        "agentic activation protocol",
        "execution activation protocol",
        "cot cor verification gates",
    ],
}


def _resolve_alias_wsp_numbers(query: str) -> List[str]:
    """Return WSP numbers whose aliases match the query.

    HIA5: Pure lookup — no LLM, no embeddings.  Returns e.g. ["97"]
    when the query contains "retrieve evidence before stating facts".
    """
    ql = query.lower()
    matched_wsps: List[str] = []

    for wsp_num, aliases in _WSP_ALIAS_REGISTRY.items():
        for alias in aliases:
            if alias in ql:
                matched_wsps.append(wsp_num)
                break

            alias_tokens = set(alias.split())
            query_tokens = set(ql.split())
            overlap = alias_tokens & query_tokens
            if len(alias_tokens) >= 3 and len(overlap) >= 3:
                matched_wsps.append(wsp_num)
                break
            elif len(alias_tokens) == 2 and len(overlap) == 2:
                matched_wsps.append(wsp_num)
                break

    return matched_wsps


def _wsp_alias_match_boost(query: str, path: str, title: str) -> float:
    """Return boost if query matches a known WSP alias phrase.

    HIA5: Bridges the recall gap between natural-language operational
    phrases and their canonical WSP protocol documents.

    Only fires when:
    - The query matches a registered alias phrase
    - The target path/title contains the corresponding WSP number
    """
    matched_wsps = _resolve_alias_wsp_numbers(query)
    if not matched_wsps:
        return 0.0

    path_wsps = _extract_wsp_numbers(path)
    title_wsps = _extract_wsp_numbers(title)
    target_wsps = set(path_wsps + title_wsps)

    for wsp_num in matched_wsps:
        if wsp_num in target_wsps:
            return 5.0

    return 0.0


# ---------------------------------------------------------------------------
# HIA2: Confidence scoring (pure heuristic, no LLM)
# ---------------------------------------------------------------------------

_TYPE_BOOST: Dict[str, float] = {
    "code": 0.1,
    "wsp": 0.1,
    "skillz": 0.08,
    "test": 0.05,
    "symbol": 0.05,
    "docs": 0.03,
    "knowledge": 0.03,
}


def _emit_confidence() -> bool:
    """Return True when HOLO_EMIT_CONFIDENCE=1 is set."""
    return os.getenv("HOLO_EMIT_CONFIDENCE", "0").strip().lower() in {"1", "true", "yes", "on"}


def _compute_confidence(similarity: float, keyword_score: float, result_type: str) -> float:
    """Compute heuristic confidence score (0.0-1.0) without LLM."""
    keyword_bonus = keyword_score / 10.0
    type_boost = _TYPE_BOOST.get(result_type, 0.0)
    return max(0.0, min(1.0, similarity + keyword_bonus + type_boost))


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

    # TQ3: select the embedder routed for this specific collection. The
    # resolver honors ``holo.routing_active`` and the available embedders,
    # so a missing int8 backend degrades truthfully to fp32 (never silent).
    from .backend_routing import resolve_backend_for_collection

    embedders = getattr(holo, "embedders", None) or None
    collection_name = getattr(collection, "name", "") or ""
    routing_active = bool(getattr(holo, "routing_active", False))
    backend_key = resolve_backend_for_collection(
        collection_name,
        routing_active=routing_active,
        available_backends=embedders,
    )
    model = None
    if embedders is not None:
        model = embedders.get(backend_key)
    if model is None:
        # Fallback to the legacy single-model attribute (tests monkeypatch it).
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

    # HIA5: Inject alias-matched WSP docs that vector search missed.
    # WSP_97 sits at vector position 94/116 for natural-language queries,
    # so it never appears in the top-N vector results.  When the query
    # matches a registered alias phrase we fetch the target WSP directly
    # from the collection and splice it into the candidate pool.
    if kind == "wsp":
        alias_wsps = _resolve_alias_wsp_numbers(query)
        if alias_wsps:
            existing_paths = {(m.get("path") or "").lower() for m in metas}
            try:
                all_data = collection.get(include=["documents", "metadatas"])
                all_docs_list = all_data.get("documents", [])
                all_metas_list = all_data.get("metadatas", [])
                alias_set = set(alias_wsps)
                for j, ameta in enumerate(all_metas_list):
                    apath = (ameta.get("path") or "").lower()
                    if apath in existing_paths:
                        continue
                    atitle = (ameta.get("title") or "").lower()
                    target_wsps = set(
                        _extract_wsp_numbers(apath)
                        + _extract_wsp_numbers(atitle)
                    )
                    if alias_set & target_wsps:
                        docs.append(all_docs_list[j])
                        metas.append(ameta)
                        dists.append(1.5)  # Neutral; keyword boost ranks
                        existing_paths.add(apath)
            except Exception:
                pass  # Collection read failed — degrade silently

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

        # HIA6B: Normalized path for fuzzy matching (holoindex ≈ holo_index)
        path_normalized = _normalize_for_match(path)

        for token in set(ql.split()):
            if not token:
                continue
            if token in title:
                keyword_score += 2.0
            if token in path:
                keyword_score += 1.0
            elif _normalize_for_match(token) in path_normalized:
                # HIA6B: Fuzzy path match (underscore-normalized)
                keyword_score += 1.0
            if token in summary:
                keyword_score += 0.5
            if token in keywords:
                keyword_score += 1.25
            if token in test_id:
                keyword_score += 3.0
            if token in capabilities:
                keyword_score += 1.5

        # HIA4B: WSP number exact match boost
        keyword_score += _wsp_number_match_boost(query, path, title)
        # HIA5: WSP alias phrase match boost
        keyword_score += _wsp_alias_match_boost(query, path, title)
        # HXA Audit Fix: Slice ID exact match boost
        meta_slice_id = meta.get("slice_id", "")
        keyword_score += _slice_id_match_boost(query, path, title, meta_slice_id)
        # Work Ledger boost: PR, worker, branch, status, foundup_id
        if doc_type == "work_ledger_slice":
            keyword_score += _work_ledger_combined_boost(query, meta)

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
            # HIA6B: Normalized path for fuzzy matching
            path_normalized = _normalize_for_match(path)

            for token in tokens:
                if token in title:
                    keyword_score += 2.0
                if token in path:
                    keyword_score += 1.0
                elif _normalize_for_match(token) in path_normalized:
                    # HIA6B: Fuzzy path match (underscore-normalized)
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

            # HIA4B: WSP number exact match boost
            keyword_score += _wsp_number_match_boost(query, path, title)
            # HIA5: WSP alias phrase match boost
            keyword_score += _wsp_alias_match_boost(query, path, title)
            # HXA Audit Fix: Slice ID exact match boost
            meta_slice_id = meta.get("slice_id", "")
            keyword_score += _slice_id_match_boost(query, path, title, meta_slice_id)
            # Work Ledger boost: PR, worker, branch, status, foundup_id
            if doc_type == "work_ledger_slice":
                keyword_score += _work_ledger_combined_boost(query, meta)

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
    """Build a single search hit dict with ``_sort_key`` for ranking.

    HIA2: Optionally includes ``confidence`` when HOLO_EMIT_CONFIDENCE=1.
    """
    sim_str = f"{similarity * 100:.1f}%"
    emit_conf = _emit_confidence()

    if kind == "code":
        result_type = meta.get("type", "code")
        result = {
            "need": meta.get("need"),
            "location": doc,
            "similarity": sim_str,
            "cube": meta.get("cube"),
            "type": result_type,
            "priority": priority,
            "_sort_key": (0.5 * priority + 0.3 * similarity + 0.2 * keyword_score, similarity, priority),
        }
        if emit_conf:
            result["confidence"] = _compute_confidence(similarity, keyword_score, result_type)
        return result

    if kind == "test":
        result = {
            "test_id": meta.get("test_id"),
            "path": meta.get("path"),
            "description": meta.get("description"),
            "capabilities": meta.get("capabilities"),
            "similarity": sim_str,
            "type": "test",
            "priority": priority,
            "_sort_key": (0.5 * priority + 0.3 * similarity + 0.2 * keyword_score, similarity, priority),
        }
        if emit_conf:
            result["confidence"] = _compute_confidence(similarity, keyword_score, "test")
        return result

    if kind == "skill":
        result = {
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
        if emit_conf:
            result["confidence"] = _compute_confidence(similarity, keyword_score, "skillz")
        return result

    # HXA Audit Fix: Explicit docs/knowledge handlers to ensure path is always populated
    if kind in ("docs", "knowledge"):
        # Ensure path is never None - fallback to document content or title
        path_value = meta.get("path") or meta.get("title", "")
        result_type = meta.get("type", kind)
        result = {
            "title": meta.get("title"),
            "summary": meta.get("summary"),
            "path": path_value,
            "slice_id": meta.get("slice_id"),  # HXA Audit Fix: Include slice_id
            "similarity": sim_str,
            "type": result_type,
            "priority": priority,
            "_sort_key": (0.5 * priority + 0.3 * similarity + 0.2 * keyword_score, similarity, priority),
        }
        if emit_conf:
            result["confidence"] = _compute_confidence(similarity, keyword_score, result_type)
        return result

    # WSP / default
    result_type = meta.get("type", "wsp")
    result = {
        "wsp": meta.get("wsp"),
        "title": meta.get("title"),
        "summary": meta.get("summary"),
        "path": meta.get("path"),
        "similarity": sim_str,
        "cube": meta.get("cube"),
        "type": result_type,
        "priority": priority,
        "_sort_key": (0.5 * priority + 0.3 * similarity + 0.2 * keyword_score, similarity, priority),
    }
    if emit_conf:
        result["confidence"] = _compute_confidence(similarity, keyword_score, result_type)
    return result


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
        # CFZ4: New hit categories for separated collections
        docs_hits: List[Dict[str, Any]] = []
        knowledge_hits: List[Dict[str, Any]] = []

        symbol_query = _is_symbol_query(query)
        force_symbol_scan = os.getenv("HOLO_FORCE_SYMBOL_SCAN", "0").lower() in {"1", "true", "yes", "on"}
        model = getattr(holo, "model", None)
        should_scan_symbols = force_symbol_scan or symbol_query or (model is not None)

        code_collection = getattr(holo, "code_collection", None)
        symbol_collection = getattr(holo, "symbol_collection", None)
        wsp_collection = getattr(holo, "wsp_collection", None)
        test_collection = getattr(holo, "test_collection", None)
        skill_collection = getattr(holo, "skill_collection", None)
        # CFZ4: New collections
        docs_collection = getattr(holo, "docs_collection", None)
        knowledge_collection = getattr(holo, "knowledge_collection", None)

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

        # CFZ4: Search Docs index (module/root docs)
        if doc_type_filter in ["docs", "all"] and docs_collection is not None:
            try:
                docs_hits = _search_collection(holo, docs_collection, query, limit, kind="docs")
            except Exception:
                docs_hits = []

        # CFZ4: Search Knowledge index (papers/research)
        if doc_type_filter in ["knowledge", "all"] and knowledge_collection is not None:
            try:
                knowledge_hits = _search_collection(holo, knowledge_collection, query, limit, kind="knowledge")
            except Exception:
                knowledge_hits = []

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
            f"{len(test_hits)} Tests, {len(skill_hits)} Skillz, "
            f"{len(docs_hits)} Docs, {len(knowledge_hits)} Knowledge"
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
            # CFZ4: New hit categories for separated collections
            "docs_hits": docs_hits,
            "knowledge_hits": knowledge_hits,
            "docs": docs_hits,
            "knowledge": knowledge_hits,
            "metadata": {
                "query": query,
                "code_count": len(code_hits),
                "wsp_count": len(wsp_hits),
                "test_count": len(test_hits),
                "skill_count": len(skill_hits),
                "symbol_count": len(symbol_results),
                "docs_count": len(docs_hits),
                "knowledge_count": len(knowledge_hits),
                "timestamp": datetime.now().isoformat(),
                "cached": False,
                # FX1-D: Surface retrieval mode in search results.
                # HIA-TAX1: retrieval_mode describes behavior (semantic/lexical/failed);
                # embedding_backend describes implementation
                # (sentence_transformers / turboquant_onnx_int8 / none).
                # HIA3: backend_quality + quality_gate describe *truth-level*
                # claims about that backend (WSP 97). TurboQuant is
                # experimental / not_default_ready until static calibration
                # closes the 3.65% cosine-drift gap.
                "retrieval_mode": getattr(holo, "retrieval_mode", "unknown"),
                "embedding_backend": getattr(holo, "embedding_backend", "unknown"),
                "backend_quality": _backend_quality(
                    getattr(holo, "embedding_backend", "unknown")
                ),
                "quality_gate": _quality_gate(
                    getattr(holo, "embedding_backend", "unknown")
                ),
                # TQ3: per-collection routing truth (WSP 97). When
                # routing_active=True, embedding_backend="routed" and the
                # per-collection claim lives in collection_backend_map.
                # When inactive, the map still reports the single backend
                # used for every collection (never overclaims).
                "routing_active": bool(getattr(holo, "routing_active", False)),
                "collection_backend_map": dict(
                    getattr(holo, "collection_backend_map", {}) or {}
                ),
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
            "docs_hits": [],
            "knowledge_hits": [],
            "docs": [],
            "knowledge": [],
            "metadata": {"error": str(e)},
        }
