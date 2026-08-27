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
from typing import Any, Dict, Iterable, List, Mapping, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .holo_index import HoloIndex

# Re-use the module-level timeout helper already in holo_index.py
from .holo_index import _run_with_timeout, HOLO_ENCODE_TIMEOUT
from .collection_injections import (
    Tier0IncompleteError,
    Tier0LookupError,
    inject_module_tier0_candidates as _inject_module_tier0_candidates,
)
from .collection_search import CollectionSearchOps, search_collection
from holo_index.module_intent_snapshot import (
    ModuleIntentSnapshotError,
    load_module_intent_paths,
)
from holo_index.tier0_retrieval import infer_explicit_module_target
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _tokenize_query(query: str) -> List[str]:
    """Split *query* into lowercase alphanumeric tokens."""
    return [token for token in re.findall(r"[a-z0-9_]+", query.lower()) if token]


def _strict_semantic_owner(holo: "HoloIndex") -> bool:
    return bool(getattr(holo, "strict_semantic_owner", False))


def _safe_search_error_code(error: Exception) -> str:
    """Return only exact-type, low-cardinality producer error codes."""
    return {
        Tier0IncompleteError: "HOLOINDEX_TIER0_INCOMPLETE",
        Tier0LookupError: "HOLOINDEX_TIER0_LOOKUP_FAILED",
        ModuleIntentSnapshotError: "HOLOINDEX_MODULE_INTENT_SNAPSHOT_UNAVAILABLE",
    }.get(type(error), "HOLOINDEX_SEARCH_FAILED")


# Slice-priority label → numeric weight (used when metadata stores P0/P1/.../P4 strings
# instead of a numeric priority_num field). Mirrors WSP 15 priority ordering, scaled to the
# 1-5 range that _format_hit's _sort_key expects.
_PRIORITY_LABEL_WEIGHTS: Dict[str, float] = {
    "P0": 5.0,
    "P1": 4.0,
    "P2": 3.0,
    "P3": 2.0,
    "P4": 1.0,
}


def _coerce_priority(meta: Dict[str, Any], default: float = 1.0) -> float:
    """Return a numeric priority for *meta* suitable for arithmetic scoring.

    Resolution order:
      1. `priority_num` (work-ledger metadata always writes a numeric here).
      2. `priority` interpreted as int/float.
      3. `priority` interpreted as a P0..P4 label via `_PRIORITY_LABEL_WEIGHTS`.
      4. *default*.

    Never raises. Guards against the historical bug where work-ledger entries
    stored `priority="P3"` (string) and downstream scoring did `0.5 * priority`
    → TypeError, which was silently swallowed and erased work-ledger hits from
    the search payload.
    """
    raw_num = meta.get("priority_num")
    if isinstance(raw_num, (int, float)) and not isinstance(raw_num, bool):
        return float(raw_num)

    raw = meta.get("priority", default)
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        return float(raw)

    if isinstance(raw, str):
        label = raw.strip().upper()
        if label in _PRIORITY_LABEL_WEIGHTS:
            return _PRIORITY_LABEL_WEIGHTS[label]
        try:
            return float(label)
        except (TypeError, ValueError):
            pass

    return float(default)


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

# Audit Spec Slice ID Fix: Long-form audit/spec slice IDs ending in _PHASE<digits>
# Examples:
#   FOUNDUPS_PORTFOLIO_DATA_VALIDATOR_PHASE1
#   FOUNDUPS_AGENT_REDTEAM_HARNESS_PROVENANCE_CHECK_PHASE1
#   HOLOINDEX_PUBLIC_FOUNDUP_CONNECTIVE_TRUST_SURFACE_DOCS_PHASE1
_AUDIT_SPEC_SLICE_ID_PATTERN = re.compile(
    r"\b([A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*_PHASE\d+)\b"
)


def _extract_wsp_numbers(text: str) -> List[str]:
    """Extract WSP numbers from text (e.g., 'WSP 97', 'WSP_97', 'WSP-97').

    Returns list of normalized WSP numbers like ['97', '00'].
    """
    matches = _WSP_NUMBER_PATTERN.findall(text)
    return [m.lstrip("0") or "0" for m in matches]  # Normalize: '00' -> '0', '97' -> '97'


def _extract_slice_ids(text: str) -> List[str]:
    """Extract slice IDs from text.

    Supports two slice ID formats:
    1. Short form: HXA, FX, CFZ patterns (e.g., 'HXA22', 'FX1', 'CFZ4')
    2. Long form: Audit/spec IDs ending in _PHASE<digits>
       (e.g., 'FOUNDUPS_PORTFOLIO_DATA_VALIDATOR_PHASE1')

    Returns list of normalized slice IDs like ['HXA22', 'CFZ4', 'FOUNDUPS_PORTFOLIO_DATA_VALIDATOR_PHASE1'].
    """
    # Extract short-form slice IDs (HXA/FX/CFZ)
    short_matches = _SLICE_ID_PATTERN.findall(text)
    short_ids = [m.upper() for m in short_matches]

    # Extract long-form audit/spec slice IDs
    long_matches = _AUDIT_SPEC_SLICE_ID_PATTERN.findall(text)
    # Long-form IDs are already uppercase in the pattern match

    return short_ids + long_matches


# Tier-1 boost when an exact ``meta_slice_id`` match is observed. Must
# strictly exceed the maximum sum of all non-slice-id keyword boosts
# (currently _trade_path_boost cap 8.0 + _trade_alias_keyword_boost cap
# 6.0 = 14.0) so a doc carrying proper slice_id metadata cannot be
# outranked by a sibling that benefits from the module path/alias
# cascade. A future cap increase will fail the precedence invariant test.
_SLICE_ID_METADATA_PRECEDENCE_BOOST = 20.0

# Tier-2 fallback for docs that match the query slice ID only via path
# or title (no slice_id metadata). Preserves prior behavior for docs that
# have not been re-indexed under the HXA metadata fix.
_SLICE_ID_PATH_OR_TITLE_BOOST = 5.0


def _slice_id_match_boost(query: str, path: str, title: str, meta_slice_id: str = "") -> float:
    """Return tiered slice-ID keyword boost.

    - Tier 1 (metadata precedence): if the query contains a literal
      slice-ID token and the doc's ``meta_slice_id`` exactly equals that
      token, return ``_SLICE_ID_METADATA_PRECEDENCE_BOOST``.
    - Tier 2 (path/title fallback): if the same query slice-ID literal
      appears in the doc path or title (no metadata match), return
      ``_SLICE_ID_PATH_OR_TITLE_BOOST``.
    - Otherwise 0.0 — including any query that carries no slice-ID
      literal, so analyst-language queries are not affected by this rule.
    """
    query_slices = _extract_slice_ids(query)
    if not query_slices:
        return 0.0

    # Tier 1: exact metadata slice_id match wins over path/title hits.
    if meta_slice_id:
        meta_upper = meta_slice_id.upper()
        for qslice in query_slices:
            if qslice == meta_upper:
                return _SLICE_ID_METADATA_PRECEDENCE_BOOST

    # Tier 2: path or title slice-ID hit.
    path_slices = _extract_slice_ids(path)
    title_slices = _extract_slice_ids(title)
    path_or_title = set(path_slices + title_slices)
    for qslice in query_slices:
        if qslice in path_or_title:
            return _SLICE_ID_PATH_OR_TITLE_BOOST

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
# HIA6: Trade/FoundUp analyst language alias registry
# HOLOINDEX_FOUNDUP_QUERY_ALIAS_AND_TARGETED_VERDICT_PHASE1
# ---------------------------------------------------------------------------

# Maps natural analyst language to Trade module terminology.
# When a query uses analyst terms like "pump.fun" or "rug pull", expands
# to include the actual terminology used in Trade contracts/docs.
# No LLM required. Deterministic pattern matching.

_TRADE_ALIAS_GROUPS: Dict[str, List[str]] = {
    # Platform aliases
    "pump.fun": ["pumpfun", "pump fun", "pump_fun"],
    "pumpfun": ["pump.fun", "pump fun", "pump_fun"],
    # Token type aliases
    "memecoin": ["meme-coin", "meme coin", "meme_coin"],
    "meme-coin": ["memecoin", "meme coin", "meme_coin"],
    "meme coin": ["memecoin", "meme-coin", "meme_coin"],
    # Creator/issuer aliases
    "issuer": ["creator", "creator_address", "token_creator"],
    "creator": ["issuer", "creator_address", "token_creator"],
    # Social platform aliases
    "x account": ["twitter", "socialevent", "social_event"],
    "twitter": ["x account", "socialevent", "social_event"],
    "telegram": ["socialevent", "social_event", "tg"],
    # Risk/fraud aliases
    "rug pull": ["rug_pull_score", "soft-rug", "honeypot", "rugpull", "rug_pull"],
    "rug_pull": ["rug pull", "rug_pull_score", "soft-rug", "honeypot"],
    "rugpull": ["rug pull", "rug_pull_score", "soft-rug", "honeypot"],
    "honeypot": ["rug pull", "rug_pull_score", "honeypot_detection"],
    # Trading activity aliases
    "large trades": ["top traders", "walletevent", "wallet_event", "holder distribution"],
    "top traders": ["large trades", "walletevent", "wallet_event", "holder_distribution"],
    "whale": ["top traders", "large trades", "holder_distribution"],
    # Social influence aliases
    "influencer": ["social", "engagement", "promoter", "socialevent"],
    "promoter": ["influencer", "social", "engagement"],
}

# Trade-specific keywords that indicate Trade intent
_TRADE_INTENT_KEYWORDS: List[str] = [
    "trade", "trading", "pump.fun", "pumpfun", "pump fun",
    "memecoin", "meme-coin", "meme coin",
    "issuer", "creator", "token_creator",
    "rug pull", "rugpull", "honeypot", "soft-rug",
    "launchpad", "bonding curve",
    "whale", "top traders", "holder distribution",
    "x account", "twitter", "telegram",
    "influencer", "promoter",
    "wallet audit", "due diligence",
]

# Trade module paths that MUST appear for Trade intent queries
_TRADE_TARGET_PATHS: List[str] = [
    "modules/foundups/trade/readme.md",
    "modules/foundups/trade/interface.md",
    "modules/foundups/trade/roadmap.md",
    "modules/foundups/trade/src/contracts.py",
    "modules/foundups/trade/src/adapters.py",
    "modules/foundups/trade/src/guards.py",
]


def _is_trade_intent_query(query: str) -> bool:
    """Detect if query has Trade/FoundUp intent based on keywords."""
    ql = query.lower()
    for kw in _TRADE_INTENT_KEYWORDS:
        if kw in ql:
            return True
    return False


def _expand_trade_aliases(query: str) -> List[str]:
    """Expand Trade analyst language to include all aliases.

    Returns list of additional search terms to consider.
    """
    ql = query.lower()
    expansions: List[str] = []

    for term, aliases in _TRADE_ALIAS_GROUPS.items():
        if term in ql:
            for alias in aliases:
                if alias not in ql:
                    expansions.append(alias)

    return expansions


def _trade_path_boost(query: str, path: str) -> float:
    """Return boost if Trade intent query targets Trade module path.

    HOLOINDEX_FOUNDUP_QUERY_ALIAS_AND_TARGETED_VERDICT_PHASE1:
    When query has Trade intent, boost Trade module paths significantly.
    """
    if not _is_trade_intent_query(query):
        return 0.0

    path_lower = path.lower().replace("\\", "/")

    # Strong boost for Trade module paths
    if "modules/foundups/trade/" in path_lower:
        # Extra boost for core documentation
        for target in _TRADE_TARGET_PATHS:
            if target in path_lower:
                return 8.0  # Very strong boost for Trade target docs
        return 5.0  # Strong boost for any Trade module file

    return 0.0


def _trade_alias_keyword_boost(query: str, path: str, title: str, content: str = "") -> float:
    """Return boost if expanded Trade aliases match document content.

    HOLOINDEX_FOUNDUP_QUERY_ALIAS_AND_TARGETED_VERDICT_PHASE1:
    Bridges analyst language to Trade module terminology.
    """
    if not _is_trade_intent_query(query):
        return 0.0

    expansions = _expand_trade_aliases(query)
    if not expansions:
        return 0.0

    boost = 0.0
    combined = (path + " " + title + " " + content).lower()

    for alias in expansions:
        if alias in combined:
            boost += 1.5  # Boost for each matched alias

    return min(boost, 6.0)  # Cap at 6.0


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

def _token_keyword_score(query: str, meta: Dict[str, Any]) -> float:
    """Score exact and normalized query tokens against bounded metadata."""
    fields = {
        "title": ((meta.get("title") or "").lower(), 2.0),
        "symbol": ((meta.get("symbol") or "").lower(), 3.0),
        "summary": ((meta.get("summary") or "").lower(), 0.5),
        "keywords": ((meta.get("keywords") or "").lower(), 1.25),
        "test_id": ((meta.get("test_id") or "").lower(), 3.0),
        "capabilities": ((meta.get("capabilities") or "").lower(), 1.5),
    }
    path = (meta.get("path") or "").lower()
    normalized_path = _normalize_for_match(path)
    score = 0.0
    for token in set(query.lower().split()):
        if not token:
            continue
        score += sum(weight for value, weight in fields.values() if token in value)
        if token in path or _normalize_for_match(token) in normalized_path:
            score += 1.0
    return score


def _vector_result(
    kind: str, query: str, doc_type_filter: str, doc: str,
    meta: Dict[str, Any], distance: Any,
) -> Dict[str, Any] | None:
    """Convert one vector row into a scored public-hit candidate."""
    provenance = meta.get("_retrieval_provenance")
    exact = provenance == "exact_metadata"
    similarity = None if exact else 1.0 / (1.0 + float(distance))
    if similarity is not None and similarity < float(
        os.getenv("HOLO_MIN_SIMILARITY", "0.35")
    ):
        return None
    doc_type = meta.get("type", "other")
    if doc_type_filter != "all" and not doc_type.startswith(doc_type_filter):
        return None
    title = (meta.get("title") or "").lower()
    path = (meta.get("path") or "").lower()
    score = _token_keyword_score(query, meta)
    score += _wsp_number_match_boost(query, path, title)
    score += _wsp_alias_match_boost(query, path, title)
    score += _slice_id_match_boost(query, path, title, meta.get("slice_id", ""))
    if doc_type == "work_ledger_slice":
        score += _work_ledger_combined_boost(query, meta)
    score += _trade_path_boost(query, path)
    score += _trade_alias_keyword_boost(query, path, title, doc or "")
    return _format_hit(
        kind, meta, doc, similarity, score, _coerce_priority(meta),
        retrieval_provenance="exact_metadata" if exact else None,
    )


def _vector_search_ops() -> CollectionSearchOps:
    """Bind search-engine policy callbacks without a circular import."""
    return CollectionSearchOps(
        strict_owner=_strict_semantic_owner,
        lexical_search=_lexical_search_collection,
        run_with_timeout=_run_with_timeout,
        resolve_alias_wsps=_resolve_alias_wsp_numbers,
        extract_wsp_numbers=_extract_wsp_numbers,
        score_result=_vector_result,
        encode_timeout=HOLO_ENCODE_TIMEOUT,
    )


def _search_collection(
    holo: "HoloIndex", collection, query: str, limit: int, kind: str,
    doc_type_filter: str = "all", module_path_hint: str | None = None,
    module_context_hits: Iterable[Mapping[str, object]] = (),
    module_registry_hits: Iterable[Mapping[str, object]] | None = None,
) -> List[Dict[str, Any]]:
    """Search a collection through the bounded vector-search pipeline."""
    return search_collection(
        holo, collection, query, limit, kind, doc_type_filter,
        module_path_hint, _vector_search_ops(), module_context_hits,
        module_registry_hits,
    )


def _module_intent(
    holo: "HoloIndex", query: str,
) -> tuple[str | None, tuple[dict[str, str], ...] | None]:
    """Resolve full paths directly or names against the pinned Git tree."""
    explicit_path = infer_explicit_module_target(query, ())
    if explicit_path:
        return explicit_path, None
    try:
        paths = load_module_intent_paths(holo.project_root)
    except ModuleIntentSnapshotError:
        if _strict_semantic_owner(holo):
            raise
        holo._log_agent_action(
            "Module intent catalog unavailable; Tier-0 name promotion suppressed",
            "WARN",
        )
        return None, ()
    registry = tuple({"path": path} for path in paths)
    return infer_explicit_module_target(query, registry), registry


def _docs_search(
    holo: "HoloIndex", collection: Any, query: str, limit: int,
    context_hits: Iterable[Mapping[str, object]],
    module_target: str | None,
    registry_hits: Iterable[Mapping[str, object]] | None,
) -> List[Dict[str, Any]]:
    """Search docs with generation-stable module intent policy."""
    try:
        return _search_collection(
            holo, collection, query, limit, kind="docs",
            module_path_hint=module_target,
            module_context_hits=context_hits,
            module_registry_hits=registry_hits,
        )
    except Exception:
        if _strict_semantic_owner(holo):
            raise
        return []


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
            # HIA6: Trade/FoundUp alias and path boost
            keyword_score += _trade_path_boost(query, path)
            keyword_score += _trade_alias_keyword_boost(query, path, title, doc_text)

            if keyword_score <= 0:
                continue

            similarity = min(1.0, keyword_score / max(1.0, len(tokens) * 2.5))
            priority = _coerce_priority(meta)

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
    similarity: float | None,
    keyword_score: float,
    priority: int,
    *,
    retrieval_provenance: str | None = None,
) -> Dict[str, Any]:
    """Build a single search hit dict with ``_sort_key`` for ranking.

    HIA2: Optionally includes ``confidence`` when HOLO_EMIT_CONFIDENCE=1.
    """
    sim_str = None if similarity is None else f"{similarity * 100:.1f}%"
    rank_similarity = similarity or 0.0
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
            "_sort_key": (0.5 * priority + 0.3 * rank_similarity + 0.2 * keyword_score, rank_similarity, priority),
        }
        if emit_conf:
            result["confidence"] = _compute_confidence(rank_similarity, keyword_score, result_type)
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
            "_sort_key": (0.5 * priority + 0.3 * rank_similarity + 0.2 * keyword_score, rank_similarity, priority),
        }
        if emit_conf:
            result["confidence"] = _compute_confidence(rank_similarity, keyword_score, "test")
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
            "_sort_key": (0.6 * priority + 0.3 * rank_similarity + 0.1 * keyword_score, rank_similarity, priority),
        }
        if emit_conf:
            result["confidence"] = _compute_confidence(rank_similarity, keyword_score, "skillz")
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
            "_sort_key": (0.5 * priority + 0.3 * rank_similarity + 0.2 * keyword_score, rank_similarity, priority),
        }
        if retrieval_provenance is not None:
            result["retrieval_provenance"] = retrieval_provenance
        if emit_conf:
            result["confidence"] = _compute_confidence(rank_similarity, keyword_score, result_type)
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
        "_sort_key": (0.5 * priority + 0.3 * rank_similarity + 0.2 * keyword_score, rank_similarity, priority),
    }
    if emit_conf:
        result["confidence"] = _compute_confidence(rank_similarity, keyword_score, result_type)
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
        # Work Ledger: slice tracking hits
        work_ledger_hits: List[Dict[str, Any]] = []

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
        # Work Ledger collection
        work_ledger_collection = getattr(holo, "work_ledger_collection", None)
        tier0_module_target = None
        module_registry_hits = None
        if doc_type_filter in ["docs", "all"] and docs_collection is not None:
            tier0_module_target, module_registry_hits = _module_intent(holo, query)

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
                if _strict_semantic_owner(holo):
                    raise
                skill_hits = []

        # CFZ4: Search Docs index (module/root docs)
        if doc_type_filter in ["docs", "all"] and docs_collection is not None:
            docs_hits = _docs_search(
                holo, docs_collection, query, limit,
                (*code_hits, *test_hits, *symbol_results),
                tier0_module_target,
                module_registry_hits,
            )

        # CFZ4: Search Knowledge index (papers/research)
        if doc_type_filter in ["knowledge", "all"] and knowledge_collection is not None:
            try:
                knowledge_hits = _search_collection(holo, knowledge_collection, query, limit, kind="knowledge")
            except Exception:
                if _strict_semantic_owner(holo):
                    raise
                knowledge_hits = []

        # Work Ledger: Search slice tracking index (WSP 15/60/70)
        if doc_type_filter in ["work_ledger", "all"] and work_ledger_collection is not None:
            try:
                work_ledger_hits = _search_collection(holo, work_ledger_collection, query, limit, kind="work_ledger")
            except Exception as exc:
                # Log instead of silently erasing hits — silent failures here cost W6/W10 an
                # entire reindex cycle before the bug was detected. See
                # FOUNDUPS_WORK_LEDGER_SEARCH_RETRIEVAL_PRIORITY_HOTFIX_PHASE1.
                logger.warning(
                    "Work-ledger search failed (%s): %s. Falling back to empty hits — normal search continues.",
                    type(exc).__name__,
                    exc,
                    exc_info=True,
                )
                work_ledger_hits = []

        # Symbol-query fallback: lexical + rg for exact identifiers/paths
        if symbol_query and not _strict_semantic_owner(holo):
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
            f"{len(docs_hits)} Docs, {len(knowledge_hits)} Knowledge, "
            f"{len(work_ledger_hits)} WorkLedger"
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
            # Work Ledger: slice tracking hits
            "work_ledger_hits": work_ledger_hits,
            "work_ledger": work_ledger_hits,
            "metadata": {
                "query": query,
                "code_count": len(code_hits),
                "wsp_count": len(wsp_hits),
                "test_count": len(test_hits),
                "skill_count": len(skill_hits),
                "symbol_count": len(symbol_results),
                "docs_count": len(docs_hits),
                "knowledge_count": len(knowledge_hits),
                "work_ledger_count": len(work_ledger_hits),
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
                "tier0_module_target": tier0_module_target,
                # TQ3: per-collection routing truth (WSP 97). When
                # routing_active=True, embedding_backend="routed" and the
                # per-collection claim lives in collection_backend_map.
                # When inactive, the map still reports the single backend
                # used for every collection (never overclaims).
                "routing_active": bool(getattr(holo, "routing_active", False)),
                "collection_backend_map": dict(
                    getattr(holo, "collection_backend_map", {}) or {}
                ),
                "collection_embedding_space_map": dict(
                    getattr(holo, "collection_embedding_space_map", {}) or {}
                ),
            },
        }

        if search_cache is not None:
            search_cache.put(query, doc_type_filter, payload)

        return payload

    except Exception as e:
        error = _safe_search_error_code(e)
        holo._log_agent_action(f"Search error: {error}", "ERROR")
        return {
            "code_hits": [],
            "wsp_hits": [],
            "code": [],
            "wsps": [],
            "docs_hits": [],
            "knowledge_hits": [],
            "docs": [],
            "knowledge": [],
            "work_ledger_hits": [],
            "work_ledger": [],
            "metadata": {"error": error},
        }
