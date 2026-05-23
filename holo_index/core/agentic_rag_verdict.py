# -*- coding: utf-8 -*-
"""Agentic RAG Verdict Helper — HIA_AGENTIC_RAG_BASELINE_GATE_PHASE1

Classifies HoloIndex retrieval results into actionable verdicts:
- SUFFICIENT: 0102 can act on retrieval evidence
- DEGRADED: Retrieval incomplete but not blocking
- UNSAFE_TO_ACT: Retrieval failed or wrong bucket — do not proceed

WSP 97: This helper enforces truth boundaries. WSP-intent queries with
zero WSP hits cannot be classified SUFFICIENT. Empty retrieval cannot
be classified SUFFICIENT.

WSP 87: Keep this helper small and pure. Do not refactor search engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class RetrievalVerdict(Enum):
    """Agentic RAG verdict for retrieval quality."""

    SUFFICIENT = "sufficient"
    """Retrieval evidence is adequate for 0102 to act."""

    DEGRADED = "degraded"
    """Retrieval incomplete but may still be usable with caution."""

    UNSAFE_TO_ACT = "unsafe_to_act"
    """Retrieval failed or returned wrong evidence — do not proceed."""


class QueryIntent(Enum):
    """Classification of query intent for routing verdict logic."""

    WSP = "wsp"
    """Query seeks WSP protocol information."""

    DOCS = "docs"
    """Query seeks documentation."""

    KNOWLEDGE = "knowledge"
    """Query seeks knowledge/research content."""

    CODE = "code"
    """Query seeks code implementation."""

    SYMBOL = "symbol"
    """Query seeks specific symbol/function/class."""

    SKILL = "skill"
    """Query seeks skillz definition."""

    TRADE = "trade"
    """Query seeks Trade FoundUp module information (pump.fun, memecoin, etc.)."""

    GENERAL = "general"
    """General query — any hits acceptable."""


@dataclass
class RetrievalEvidenceSummary:
    """Summary of retrieval evidence for verdict classification."""

    query: str
    intent: QueryIntent
    code_hits_count: int = 0
    wsp_hits_count: int = 0
    docs_hits_count: int = 0
    knowledge_hits_count: int = 0
    test_hits_count: int = 0
    skill_hits_count: int = 0
    symbol_hits_count: int = 0
    total_hits: int = 0
    degraded: bool = False
    backend_error: bool = False
    reason: str = ""
    verdict: RetrievalVerdict = field(default=RetrievalVerdict.UNSAFE_TO_ACT)

    def __post_init__(self):
        """Calculate total hits."""
        self.total_hits = (
            self.code_hits_count +
            self.wsp_hits_count +
            self.docs_hits_count +
            self.knowledge_hits_count +
            self.test_hits_count +
            self.skill_hits_count +
            self.symbol_hits_count
        )


# Trade FoundUp intent keywords
# HOLOINDEX_FOUNDUP_QUERY_ALIAS_AND_TARGETED_VERDICT_PHASE1
_TRADE_INTENT_KEYWORDS = [
    "trade", "trading",
    "pump.fun", "pumpfun", "pump fun",
    "memecoin", "meme-coin", "meme coin",
    "issuer", "creator", "token_creator",
    "rug pull", "rugpull", "honeypot", "soft-rug",
    "launchpad", "bonding curve",
    "whale", "top traders", "holder distribution",
    "x account", "telegram",
    "influencer", "promoter",
    "wallet audit", "due diligence",
]


def classify_query_intent(query: str) -> QueryIntent:
    """Classify query intent based on keywords.

    Simple heuristic classification. Can be enhanced with Gemma later.
    """
    query_lower = query.lower()

    # Trade FoundUp intent detection (check first - specific module)
    # HOLOINDEX_FOUNDUP_QUERY_ALIAS_AND_TARGETED_VERDICT_PHASE1
    if any(kw in query_lower for kw in _TRADE_INTENT_KEYWORDS):
        return QueryIntent.TRADE

    # WSP intent detection
    if any(kw in query_lower for kw in ["wsp", "protocol", "compliance"]):
        return QueryIntent.WSP

    # Docs intent detection
    if any(kw in query_lower for kw in ["doc", "readme", "interface", "roadmap", "modlog"]):
        return QueryIntent.DOCS

    # Knowledge intent detection
    if any(kw in query_lower for kw in ["knowledge", "research", "paper", "theory"]):
        return QueryIntent.KNOWLEDGE

    # Skill intent detection
    if any(kw in query_lower for kw in ["skill", "skillz", "capability"]):
        return QueryIntent.SKILL

    # Symbol intent detection (specific identifiers)
    if any(kw in query_lower for kw in ["function", "class", "method", "def ", "import"]):
        return QueryIntent.SYMBOL

    # Code intent (implementation-focused)
    if any(kw in query_lower for kw in ["implementation", "code", "module", "engine"]):
        return QueryIntent.CODE

    # Default to general
    return QueryIntent.GENERAL


def classify_retrieval_evidence(
    payload: Dict[str, Any],
    query_intent: Optional[QueryIntent] = None,
) -> RetrievalEvidenceSummary:
    """Classify retrieval evidence into actionable verdict.

    Args:
        payload: HoloIndex search result payload
        query_intent: Optional explicit intent. If None, inferred from query.

    Returns:
        RetrievalEvidenceSummary with verdict classification.

    WSP 97 Rules:
    - WSP intent with zero WSP hits => UNSAFE_TO_ACT or DEGRADED, never SUFFICIENT
    - Docs intent with zero docs hits => DEGRADED unless WSP hits satisfy intent
    - Knowledge intent with zero knowledge hits => DEGRADED
    - Code intent with code hits can be SUFFICIENT
    - Any explicit backend/model/index failure => DEGRADED or UNSAFE_TO_ACT
    - Empty all buckets => UNSAFE_TO_ACT
    """
    # Extract metadata
    metadata = payload.get("metadata", {})
    query = metadata.get("query", "")

    # Infer intent if not provided
    if query_intent is None:
        query_intent = classify_query_intent(query)

    # Extract hit counts
    code_count = metadata.get("code_count", len(payload.get("code_hits", [])))
    wsp_count = metadata.get("wsp_count", len(payload.get("wsp_hits", [])))
    docs_count = metadata.get("docs_count", len(payload.get("docs_hits", [])))
    knowledge_count = metadata.get("knowledge_count", len(payload.get("knowledge_hits", [])))
    test_count = metadata.get("test_count", len(payload.get("test_hits", [])))
    skill_count = metadata.get("skill_count", len(payload.get("skill_hits", [])))
    symbol_count = metadata.get("symbol_count", len(payload.get("symbol_hits", [])))

    # Check for backend errors
    backend_error = "error" in metadata
    retrieval_mode = metadata.get("retrieval_mode", "unknown")
    backend_quality = metadata.get("backend_quality", "unknown")

    # Build summary
    summary = RetrievalEvidenceSummary(
        query=query,
        intent=query_intent,
        code_hits_count=code_count,
        wsp_hits_count=wsp_count,
        docs_hits_count=docs_count,
        knowledge_hits_count=knowledge_count,
        test_hits_count=test_count,
        skill_hits_count=skill_count,
        symbol_hits_count=symbol_count,
        backend_error=backend_error,
    )

    # Rule: Backend error => DEGRADED or UNSAFE_TO_ACT
    if backend_error:
        summary.degraded = True
        summary.reason = f"Backend error: {metadata.get('error', 'unknown')}"
        summary.verdict = RetrievalVerdict.UNSAFE_TO_ACT
        return summary

    # Rule: Empty all buckets => UNSAFE_TO_ACT
    if summary.total_hits == 0:
        summary.reason = "No hits in any bucket — retrieval failed"
        summary.verdict = RetrievalVerdict.UNSAFE_TO_ACT
        return summary

    # Intent-specific rules
    if query_intent == QueryIntent.WSP:
        if wsp_count == 0:
            # WSP intent with zero WSP hits
            if code_count > 0:
                # Has code hits but no WSP — DEGRADED (might find WSP refs in code)
                summary.degraded = True
                summary.reason = "WSP intent but only code hits — may miss protocol context"
                summary.verdict = RetrievalVerdict.DEGRADED
            else:
                # No WSP and no code — UNSAFE
                summary.reason = "WSP intent with zero WSP hits — cannot verify protocol"
                summary.verdict = RetrievalVerdict.UNSAFE_TO_ACT
        else:
            # Has WSP hits — SUFFICIENT
            summary.reason = f"WSP intent satisfied: {wsp_count} WSP hits"
            summary.verdict = RetrievalVerdict.SUFFICIENT
        return summary

    if query_intent == QueryIntent.DOCS:
        if docs_count == 0:
            if wsp_count > 0:
                # No docs but WSP hits may satisfy — DEGRADED
                summary.degraded = True
                summary.reason = "Docs intent but only WSP hits — partial coverage"
                summary.verdict = RetrievalVerdict.DEGRADED
            elif code_count > 0:
                # No docs but code hits — DEGRADED
                summary.degraded = True
                summary.reason = "Docs intent but only code hits — missing documentation"
                summary.verdict = RetrievalVerdict.DEGRADED
            else:
                summary.reason = "Docs intent with zero docs hits"
                summary.verdict = RetrievalVerdict.UNSAFE_TO_ACT
        else:
            summary.reason = f"Docs intent satisfied: {docs_count} docs hits"
            summary.verdict = RetrievalVerdict.SUFFICIENT
        return summary

    if query_intent == QueryIntent.KNOWLEDGE:
        if knowledge_count == 0:
            if docs_count > 0 or wsp_count > 0:
                summary.degraded = True
                summary.reason = "Knowledge intent but only docs/WSP hits — may be sufficient"
                summary.verdict = RetrievalVerdict.DEGRADED
            else:
                summary.reason = "Knowledge intent with zero knowledge hits"
                summary.verdict = RetrievalVerdict.DEGRADED
        else:
            summary.reason = f"Knowledge intent satisfied: {knowledge_count} knowledge hits"
            summary.verdict = RetrievalVerdict.SUFFICIENT
        return summary

    if query_intent == QueryIntent.SKILL:
        if skill_count == 0:
            if code_count > 0:
                summary.degraded = True
                summary.reason = "Skill intent but only code hits — skill definition may be in code"
                summary.verdict = RetrievalVerdict.DEGRADED
            else:
                summary.reason = "Skill intent with zero skill hits"
                summary.verdict = RetrievalVerdict.DEGRADED
        else:
            summary.reason = f"Skill intent satisfied: {skill_count} skill hits"
            summary.verdict = RetrievalVerdict.SUFFICIENT
        return summary

    if query_intent == QueryIntent.SYMBOL:
        if symbol_count == 0 and code_count == 0:
            summary.reason = "Symbol intent with zero symbol/code hits"
            summary.verdict = RetrievalVerdict.DEGRADED
        else:
            hit_source = "symbol" if symbol_count > 0 else "code"
            hit_count = symbol_count if symbol_count > 0 else code_count
            summary.reason = f"Symbol intent satisfied: {hit_count} {hit_source} hits"
            summary.verdict = RetrievalVerdict.SUFFICIENT
        return summary

    if query_intent == QueryIntent.CODE:
        if code_count == 0 and symbol_count == 0:
            if wsp_count > 0 or docs_count > 0:
                summary.degraded = True
                summary.reason = "Code intent but only docs/WSP hits — implementation not found"
                summary.verdict = RetrievalVerdict.DEGRADED
            else:
                summary.reason = "Code intent with zero code hits"
                summary.verdict = RetrievalVerdict.UNSAFE_TO_ACT
        else:
            summary.reason = f"Code intent satisfied: {code_count} code + {symbol_count} symbol hits"
            summary.verdict = RetrievalVerdict.SUFFICIENT
        return summary

    # Trade FoundUp intent — must have Trade module evidence
    # HOLOINDEX_FOUNDUP_QUERY_ALIAS_AND_TARGETED_VERDICT_PHASE1
    if query_intent == QueryIntent.TRADE:
        # Check if any hits are from Trade module
        trade_evidence = _has_trade_module_evidence(payload)
        if trade_evidence:
            summary.reason = f"Trade intent satisfied: Trade module evidence found"
            summary.verdict = RetrievalVerdict.SUFFICIENT
        elif docs_count > 0 or code_count > 0:
            # Has hits but none from Trade module
            summary.degraded = True
            summary.reason = "Trade intent but no Trade module evidence in results — retrieval may miss relevant docs"
            summary.verdict = RetrievalVerdict.DEGRADED
        else:
            # No relevant hits at all
            summary.reason = "Trade intent with no Trade module evidence"
            summary.verdict = RetrievalVerdict.UNSAFE_TO_ACT
        return summary

    # General intent — any hits are acceptable
    summary.reason = f"General query: {summary.total_hits} total hits"
    summary.verdict = RetrievalVerdict.SUFFICIENT
    return summary


# Trade module target paths for evidence checking
# HOLOINDEX_FOUNDUP_QUERY_ALIAS_AND_TARGETED_VERDICT_PHASE1
_TRADE_TARGET_PATHS = [
    "modules/foundups/trade/readme.md",
    "modules/foundups/trade/interface.md",
    "modules/foundups/trade/roadmap.md",
    "modules/foundups/trade/src/contracts.py",
    "modules/foundups/trade/src/adapters.py",
    "modules/foundups/trade/src/guards.py",
    "modules/foundups/trade/",
]


def _has_trade_module_evidence(payload: Dict[str, Any]) -> bool:
    """Check if retrieval results contain Trade module evidence.

    HOLOINDEX_FOUNDUP_QUERY_ALIAS_AND_TARGETED_VERDICT_PHASE1:
    Trade intent queries are not sufficient unless Trade docs/code appear
    in the results. This prevents false positives where unrelated hits
    satisfy generic thresholds.
    """
    # Check all hit types
    hit_lists = [
        payload.get("code_hits", []),
        payload.get("docs_hits", []),
        payload.get("wsp_hits", []),
        payload.get("knowledge_hits", []),
    ]

    for hits in hit_lists:
        for hit in hits:
            path = (hit.get("path") or hit.get("location") or "").lower().replace("\\", "/")
            for target in _TRADE_TARGET_PATHS:
                if target in path:
                    return True

    return False


def format_verdict_for_agent(summary: RetrievalEvidenceSummary) -> str:
    """Format verdict summary for 0102 agent consumption.

    Returns a concise string suitable for logging or agent context.
    """
    verdict_emoji = {
        RetrievalVerdict.SUFFICIENT: "[OK]",
        RetrievalVerdict.DEGRADED: "[WARN]",
        RetrievalVerdict.UNSAFE_TO_ACT: "[FAIL]",
    }

    emoji = verdict_emoji.get(summary.verdict, "[?]")

    return (
        f"{emoji} Retrieval verdict: {summary.verdict.value}\n"
        f"  Intent: {summary.intent.value}\n"
        f"  Hits: code={summary.code_hits_count}, wsp={summary.wsp_hits_count}, "
        f"docs={summary.docs_hits_count}, knowledge={summary.knowledge_hits_count}\n"
        f"  Reason: {summary.reason}"
    )
