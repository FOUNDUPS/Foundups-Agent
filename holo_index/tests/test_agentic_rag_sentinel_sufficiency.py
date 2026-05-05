# -*- coding: utf-8 -*-
"""HIA_AGENTIC_RAG_SENTINEL_SUFFICIENCY_PHASE3: Live Sentinel Verdict Tests

Tests that verify WSP 97 truth boundaries using LIVE HoloIndex retrieval.
Wires classify_retrieval_evidence() verdicts into sentinel query assertions.

WSP 97: These tests use live E:/HoloIndex index when available.
        Tests skip gracefully if index/model unavailable.
        Retrieval failures are reported, not hidden.
        Code-only hits for WSP intent are NOT sufficient.

WSP 87: Keep tests focused on retrieval sufficiency, not ranking quality.
"""

import os
import pytest
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

# Verdict imports
from holo_index.core.agentic_rag_verdict import (
    RetrievalVerdict,
    QueryIntent,
    RetrievalEvidenceSummary,
    classify_retrieval_evidence,
    classify_query_intent,
    format_verdict_for_agent,
)


# =============================================================================
# Live Index Detection
# =============================================================================


def _get_live_holo() -> Optional[Any]:
    """Get live HoloIndex instance if available.

    Returns:
        HoloIndex instance or None if unavailable.
    """
    try:
        # Check if SSD path exists
        ssd_path = Path("E:/HoloIndex")
        if not ssd_path.exists():
            return None

        vectors_path = ssd_path / "vectors"
        if not vectors_path.exists():
            return None

        # Attempt to import and initialize
        from holo_index.core.holo_index import HoloIndex
        holo = HoloIndex(quiet=True)
        return holo
    except Exception:
        return None


def _is_live_index_available() -> bool:
    """Check if live HoloIndex is available for testing."""
    holo = _get_live_holo()
    if holo is None:
        return False

    # Verify at least code collection has entries
    try:
        code_count = holo.get_code_entry_count()
        return code_count > 0
    except Exception:
        return False


LIVE_INDEX_AVAILABLE = _is_live_index_available()
SKIP_LIVE = pytest.mark.skipif(
    not LIVE_INDEX_AVAILABLE,
    reason="Live HoloIndex not available at E:/HoloIndex"
)


# =============================================================================
# Sentinel Query Definitions with Intent
# =============================================================================


@dataclass
class IntentSentinelQuery:
    """Sentinel query with explicit intent and expected bucket."""
    query: str
    intent: QueryIntent
    expected_bucket: str  # wsp, code, docs, knowledge, skill
    description: str
    must_satisfy_bucket: bool = True  # If True, verdict must reflect this bucket


INTENT_SENTINEL_QUERIES: List[IntentSentinelQuery] = [
    # --- WSP Intent Queries (must have wsp_hits > 0 for SUFFICIENT) ---
    IntentSentinelQuery(
        query="WSP 97 System Execution Prompting Protocol retrieve evidence",
        intent=QueryIntent.WSP,
        expected_bucket="wsp",
        description="WSP 97 retrieval - must return WSP evidence",
        must_satisfy_bucket=True,
    ),
    IntentSentinelQuery(
        query="WSP 87 Code Navigation Protocol HoloIndex retrieval",
        intent=QueryIntent.WSP,
        expected_bucket="wsp",
        description="WSP 87 retrieval - must return WSP evidence",
        must_satisfy_bucket=True,
    ),

    # --- Docs Intent Queries ---
    IntentSentinelQuery(
        query="HoloIndex degraded mode WSP doc retrieval audit",
        intent=QueryIntent.DOCS,
        expected_bucket="docs",
        description="Docs/audit retrieval - docs or WSP hits acceptable",
        must_satisfy_bucket=False,  # DEGRADED acceptable if WSP hits
    ),

    # --- Knowledge Intent Queries ---
    IntentSentinelQuery(
        query="rESP quantum entanglement theoretical foundation",
        intent=QueryIntent.KNOWLEDGE,
        expected_bucket="knowledge",
        description="Knowledge/research retrieval - DEGRADED acceptable",
        must_satisfy_bucket=False,  # DEGRADED acceptable
    ),

    # --- Code Intent Queries (code hits sufficient) ---
    IntentSentinelQuery(
        query="classify_retrieval_evidence RetrievalVerdict",
        intent=QueryIntent.CODE,
        expected_bucket="code",
        description="Code retrieval - must find agentic_rag_verdict.py",
        must_satisfy_bucket=True,
    ),

    # --- Skill Intent Queries ---
    IntentSentinelQuery(
        query="holoindex_package_extractor skillz package extraction",
        intent=QueryIntent.SKILL,
        expected_bucket="skill",
        description="Skill retrieval - skill or code evidence acceptable",
        must_satisfy_bucket=False,  # DEGRADED acceptable with code hits
    ),
]


# =============================================================================
# Live Search to Verdict Payload Adapter
# =============================================================================


def _search_to_verdict_payload(holo: Any, query: str, limit: int = 8) -> Dict[str, Any]:
    """Convert HoloIndex search results to verdict payload format.

    Args:
        holo: HoloIndex instance
        query: Search query
        limit: Result limit per bucket

    Returns:
        Payload dict compatible with classify_retrieval_evidence()
    """
    try:
        # Run search
        results = holo.search(query, limit=limit)

        # Extract hits from each bucket
        code_hits = results.get("code", [])
        wsp_hits = results.get("wsps", [])
        docs_hits = results.get("docs", [])
        knowledge_hits = results.get("knowledge", [])
        skill_hits = results.get("skills", [])
        symbol_hits = []  # Usually merged into code

        # Build payload
        payload = {
            "code_hits": code_hits,
            "wsp_hits": wsp_hits,
            "docs_hits": docs_hits,
            "knowledge_hits": knowledge_hits,
            "test_hits": [],  # Not typically returned by search
            "skill_hits": skill_hits,
            "symbol_hits": symbol_hits,
            "metadata": {
                "query": query,
                "code_count": len(code_hits),
                "wsp_count": len(wsp_hits),
                "docs_count": len(docs_hits),
                "knowledge_count": len(knowledge_hits),
                "test_count": 0,
                "skill_count": len(skill_hits),
                "symbol_count": len(symbol_hits),
                "retrieval_mode": "live",
            }
        }

        return payload

    except Exception as e:
        # Return error payload
        return {
            "code_hits": [],
            "wsp_hits": [],
            "docs_hits": [],
            "knowledge_hits": [],
            "test_hits": [],
            "skill_hits": [],
            "symbol_hits": [],
            "metadata": {
                "query": query,
                "error": str(e),
            }
        }


# =============================================================================
# Result Collection
# =============================================================================


@dataclass
class SentinelVerdictResult:
    """Result of running a sentinel query with verdict classification."""
    query: str
    intent: str
    expected_bucket: str
    description: str
    code_hits: int
    wsp_hits: int
    docs_hits: int
    knowledge_hits: int
    skill_hits: int
    total_hits: int
    verdict: str
    verdict_reason: str
    passes_bucket_requirement: bool
    measured_at: str


def _run_sentinel_with_verdict(
    holo: Any,
    sentinel: IntentSentinelQuery
) -> SentinelVerdictResult:
    """Run a sentinel query and classify with verdict helper.

    Args:
        holo: HoloIndex instance
        sentinel: Sentinel query definition

    Returns:
        SentinelVerdictResult with verdict classification.
    """
    payload = _search_to_verdict_payload(holo, sentinel.query, limit=8)
    summary = classify_retrieval_evidence(payload, sentinel.intent)

    # Check if bucket requirement is met
    bucket_map = {
        "wsp": summary.wsp_hits_count,
        "code": summary.code_hits_count,
        "docs": summary.docs_hits_count,
        "knowledge": summary.knowledge_hits_count,
        "skill": summary.skill_hits_count,
    }

    bucket_count = bucket_map.get(sentinel.expected_bucket, 0)

    if sentinel.must_satisfy_bucket:
        # Strict requirement: must have hits in expected bucket
        passes = bucket_count > 0
    else:
        # Relaxed: either expected bucket or verdict not UNSAFE_TO_ACT
        passes = bucket_count > 0 or summary.verdict != RetrievalVerdict.UNSAFE_TO_ACT

    return SentinelVerdictResult(
        query=sentinel.query,
        intent=sentinel.intent.value,
        expected_bucket=sentinel.expected_bucket,
        description=sentinel.description,
        code_hits=summary.code_hits_count,
        wsp_hits=summary.wsp_hits_count,
        docs_hits=summary.docs_hits_count,
        knowledge_hits=summary.knowledge_hits_count,
        skill_hits=summary.skill_hits_count,
        total_hits=summary.total_hits,
        verdict=summary.verdict.value,
        verdict_reason=summary.reason,
        passes_bucket_requirement=passes,
        measured_at=datetime.utcnow().isoformat() + "Z",
    )


# =============================================================================
# Live Sentinel Tests
# =============================================================================


class TestLiveSentinelSufficiency:
    """Live sentinel tests using real E:/HoloIndex index."""

    @SKIP_LIVE
    def test_wsp_97_sentinel_returns_wsp_evidence(self):
        """WSP 97 query must return WSP hits for SUFFICIENT verdict."""
        holo = _get_live_holo()
        sentinel = IntentSentinelQuery(
            query="WSP 97 System Execution Prompting Protocol retrieve evidence",
            intent=QueryIntent.WSP,
            expected_bucket="wsp",
            description="WSP 97 sentinel",
            must_satisfy_bucket=True,
        )

        result = _run_sentinel_with_verdict(holo, sentinel)

        # WSP intent MUST have WSP hits - this is WSP 97 truth boundary
        assert result.wsp_hits > 0, (
            f"WSP 97 query returned zero WSP hits. "
            f"Got: code={result.code_hits}, wsp={result.wsp_hits}. "
            f"This violates WSP 97: WSP-intent requires WSP evidence."
        )

        # Verdict must be SUFFICIENT if WSP hits present
        assert result.verdict == "sufficient", (
            f"WSP 97 query with WSP hits should be SUFFICIENT. "
            f"Got verdict={result.verdict}, reason={result.verdict_reason}"
        )

    @SKIP_LIVE
    def test_wsp_87_sentinel_returns_wsp_evidence(self):
        """WSP 87 query must return WSP hits for SUFFICIENT verdict."""
        holo = _get_live_holo()
        sentinel = IntentSentinelQuery(
            query="WSP 87 Code Navigation Protocol HoloIndex retrieval",
            intent=QueryIntent.WSP,
            expected_bucket="wsp",
            description="WSP 87 sentinel",
            must_satisfy_bucket=True,
        )

        result = _run_sentinel_with_verdict(holo, sentinel)

        assert result.wsp_hits > 0, (
            f"WSP 87 query returned zero WSP hits. "
            f"Got: code={result.code_hits}, wsp={result.wsp_hits}. "
            f"This violates WSP 97: WSP-intent requires WSP evidence."
        )

        assert result.verdict == "sufficient", (
            f"WSP 87 query with WSP hits should be SUFFICIENT. "
            f"Got verdict={result.verdict}"
        )

    @SKIP_LIVE
    def test_code_intent_returns_code_evidence(self):
        """Code intent query must return code hits for SUFFICIENT verdict."""
        holo = _get_live_holo()
        sentinel = IntentSentinelQuery(
            query="classify_retrieval_evidence RetrievalVerdict",
            intent=QueryIntent.CODE,
            expected_bucket="code",
            description="Code sentinel - agentic_rag_verdict.py",
            must_satisfy_bucket=True,
        )

        result = _run_sentinel_with_verdict(holo, sentinel)

        assert result.code_hits > 0, (
            f"Code intent query returned zero code hits. "
            f"Got: code={result.code_hits}"
        )

        assert result.verdict == "sufficient", (
            f"Code intent with code hits should be SUFFICIENT. "
            f"Got verdict={result.verdict}"
        )

    @SKIP_LIVE
    def test_docs_intent_accepts_wsp_fallback(self):
        """Docs intent can be DEGRADED with WSP hits (not UNSAFE)."""
        holo = _get_live_holo()
        sentinel = IntentSentinelQuery(
            query="HoloIndex degraded mode WSP doc retrieval audit",
            intent=QueryIntent.DOCS,
            expected_bucket="docs",
            description="Docs sentinel",
            must_satisfy_bucket=False,
        )

        result = _run_sentinel_with_verdict(holo, sentinel)

        # Either docs hits for SUFFICIENT, or WSP/code hits for DEGRADED
        assert result.total_hits > 0, (
            f"Docs intent query returned zero total hits. "
            f"This should be UNSAFE_TO_ACT."
        )

        # Should not be UNSAFE_TO_ACT if there are any hits
        if result.total_hits > 0:
            assert result.verdict != "unsafe_to_act", (
                f"Docs intent with {result.total_hits} hits should not be UNSAFE. "
                f"Got verdict={result.verdict}"
            )

    @SKIP_LIVE
    def test_knowledge_intent_reports_degraded_truthfully(self):
        """Knowledge intent can be DEGRADED if no knowledge hits."""
        holo = _get_live_holo()
        sentinel = IntentSentinelQuery(
            query="rESP quantum entanglement theoretical foundation",
            intent=QueryIntent.KNOWLEDGE,
            expected_bucket="knowledge",
            description="Knowledge sentinel - may be DEGRADED",
            must_satisfy_bucket=False,
        )

        result = _run_sentinel_with_verdict(holo, sentinel)

        # If knowledge hits, should be SUFFICIENT
        if result.knowledge_hits > 0:
            assert result.verdict == "sufficient", (
                f"Knowledge intent with knowledge hits should be SUFFICIENT. "
                f"Got verdict={result.verdict}"
            )
        else:
            # If no knowledge hits but other hits, should be DEGRADED
            if result.total_hits > 0:
                assert result.verdict == "degraded", (
                    f"Knowledge intent with no knowledge but {result.total_hits} other hits "
                    f"should be DEGRADED. Got verdict={result.verdict}"
                )

    @SKIP_LIVE
    def test_skill_intent_accepts_code_fallback(self):
        """Skill intent can be DEGRADED with code hits."""
        holo = _get_live_holo()
        sentinel = IntentSentinelQuery(
            query="holoindex_package_extractor skillz package extraction",
            intent=QueryIntent.SKILL,
            expected_bucket="skill",
            description="Skill sentinel",
            must_satisfy_bucket=False,
        )

        result = _run_sentinel_with_verdict(holo, sentinel)

        # If skill hits, should be SUFFICIENT
        if result.skill_hits > 0:
            assert result.verdict == "sufficient", (
                f"Skill intent with skill hits should be SUFFICIENT. "
                f"Got verdict={result.verdict}"
            )
        else:
            # Should not be UNSAFE if there are code/docs hits
            if result.total_hits > 0:
                assert result.verdict != "unsafe_to_act", (
                    f"Skill intent with {result.total_hits} total hits "
                    f"should not be UNSAFE. Got verdict={result.verdict}"
                )

    @SKIP_LIVE
    def test_empty_retrieval_is_unsafe(self):
        """Query that returns no hits must be UNSAFE_TO_ACT."""
        holo = _get_live_holo()

        # Use a query unlikely to match anything
        payload = _search_to_verdict_payload(
            holo,
            "xyzzy_nonexistent_module_12345_impossible_match",
            limit=8
        )
        summary = classify_retrieval_evidence(payload, QueryIntent.GENERAL)

        if summary.total_hits == 0:
            assert summary.verdict == RetrievalVerdict.UNSAFE_TO_ACT, (
                f"Empty retrieval must be UNSAFE_TO_ACT. "
                f"Got verdict={summary.verdict.value}"
            )

    @SKIP_LIVE
    def test_wsp_intent_code_only_not_sufficient(self):
        """WSP intent with only code hits must NOT be SUFFICIENT."""
        # This test verifies WSP 97: code-only for WSP query => DEGRADED
        holo = _get_live_holo()

        # Create a mock payload with code hits but no WSP hits
        mock_payload = {
            "code_hits": [{"path": "some_code.py"}] * 5,
            "wsp_hits": [],
            "docs_hits": [],
            "knowledge_hits": [],
            "test_hits": [],
            "skill_hits": [],
            "symbol_hits": [],
            "metadata": {
                "query": "WSP compliance mock",
                "code_count": 5,
                "wsp_count": 0,
                "docs_count": 0,
                "knowledge_count": 0,
                "test_count": 0,
                "skill_count": 0,
                "symbol_count": 0,
            }
        }

        summary = classify_retrieval_evidence(mock_payload, QueryIntent.WSP)

        assert summary.verdict != RetrievalVerdict.SUFFICIENT, (
            "WSP intent with zero WSP hits must NOT be SUFFICIENT. "
            f"Got verdict={summary.verdict.value}"
        )


# =============================================================================
# Aggregate Test - All Sentinels
# =============================================================================


class TestAggregateSentinelSufficiency:
    """Aggregate test running all sentinels and collecting results."""

    @SKIP_LIVE
    def test_all_sentinels_return_evidence(self):
        """All sentinel queries should return some evidence (not empty)."""
        holo = _get_live_holo()
        results = []
        failures = []

        for sentinel in INTENT_SENTINEL_QUERIES:
            result = _run_sentinel_with_verdict(holo, sentinel)
            results.append(result)

            if result.total_hits == 0:
                failures.append(
                    f"  - {sentinel.query[:50]}... (EMPTY - UNSAFE_TO_ACT)"
                )

        # Report all failures at once
        if failures:
            failure_report = "\n".join(failures)
            pytest.fail(
                f"Some sentinels returned empty results:\n{failure_report}"
            )

    @SKIP_LIVE
    def test_wsp_sentinels_return_wsp_evidence(self):
        """All WSP intent sentinels must return WSP hits."""
        holo = _get_live_holo()
        wsp_sentinels = [s for s in INTENT_SENTINEL_QUERIES if s.intent == QueryIntent.WSP]
        failures = []

        for sentinel in wsp_sentinels:
            result = _run_sentinel_with_verdict(holo, sentinel)

            if result.wsp_hits == 0:
                failures.append(
                    f"  - {sentinel.query[:50]}... "
                    f"(wsp_hits=0, code_hits={result.code_hits}, verdict={result.verdict})"
                )

        if failures:
            failure_report = "\n".join(failures)
            pytest.fail(
                f"WSP sentinels missing WSP evidence (WSP 97 violation):\n{failure_report}"
            )

    @SKIP_LIVE
    def test_no_false_sufficient_on_wrong_bucket(self):
        """Sentinels requiring specific buckets must not claim SUFFICIENT without them."""
        holo = _get_live_holo()
        strict_sentinels = [s for s in INTENT_SENTINEL_QUERIES if s.must_satisfy_bucket]
        failures = []

        for sentinel in strict_sentinels:
            result = _run_sentinel_with_verdict(holo, sentinel)

            bucket_count = {
                "wsp": result.wsp_hits,
                "code": result.code_hits,
                "docs": result.docs_hits,
                "knowledge": result.knowledge_hits,
                "skill": result.skill_hits,
            }.get(sentinel.expected_bucket, 0)

            # If bucket is empty but verdict is SUFFICIENT, that's a violation
            if bucket_count == 0 and result.verdict == "sufficient":
                failures.append(
                    f"  - {sentinel.query[:50]}... "
                    f"(expected {sentinel.expected_bucket}={bucket_count}, verdict=SUFFICIENT)"
                )

        if failures:
            failure_report = "\n".join(failures)
            pytest.fail(
                f"False SUFFICIENT verdicts detected (WSP 97 violation):\n{failure_report}"
            )


# =============================================================================
# Report Generation (for audit doc)
# =============================================================================


def generate_sentinel_sufficiency_report() -> Dict[str, Any]:
    """Generate a report of all sentinel verdicts for audit documentation.

    This function is called directly or from CLI to produce audit data.

    Returns:
        Dict with sentinel results and aggregate metrics.
    """
    holo = _get_live_holo()
    if holo is None:
        return {
            "status": "SKIPPED",
            "reason": "Live HoloIndex not available at E:/HoloIndex",
            "measured_at": datetime.utcnow().isoformat() + "Z",
        }

    results = []
    for sentinel in INTENT_SENTINEL_QUERIES:
        result = _run_sentinel_with_verdict(holo, sentinel)
        results.append(asdict(result))

    # Compute aggregates
    total = len(results)
    sufficient_count = sum(1 for r in results if r["verdict"] == "sufficient")
    degraded_count = sum(1 for r in results if r["verdict"] == "degraded")
    unsafe_count = sum(1 for r in results if r["verdict"] == "unsafe_to_act")
    bucket_pass_count = sum(1 for r in results if r["passes_bucket_requirement"])

    # WSP-specific
    wsp_results = [r for r in results if r["intent"] == "wsp"]
    wsp_total = len(wsp_results)
    wsp_with_wsp_hits = sum(1 for r in wsp_results if r["wsp_hits"] > 0)

    return {
        "status": "COMPLETE",
        "measured_at": datetime.utcnow().isoformat() + "Z",
        "total_sentinels": total,
        "aggregate": {
            "sufficient_count": sufficient_count,
            "sufficient_rate": round(sufficient_count / total, 4) if total > 0 else 0,
            "degraded_count": degraded_count,
            "degraded_rate": round(degraded_count / total, 4) if total > 0 else 0,
            "unsafe_count": unsafe_count,
            "unsafe_rate": round(unsafe_count / total, 4) if total > 0 else 0,
            "bucket_pass_count": bucket_pass_count,
            "bucket_pass_rate": round(bucket_pass_count / total, 4) if total > 0 else 0,
        },
        "wsp_sentinels": {
            "total": wsp_total,
            "with_wsp_hits": wsp_with_wsp_hits,
            "wsp_sufficiency_rate": round(wsp_with_wsp_hits / wsp_total, 4) if wsp_total > 0 else 0,
        },
        "sentinel_results": results,
    }


if __name__ == "__main__":
    import json
    report = generate_sentinel_sufficiency_report()
    print(json.dumps(report, indent=2))
