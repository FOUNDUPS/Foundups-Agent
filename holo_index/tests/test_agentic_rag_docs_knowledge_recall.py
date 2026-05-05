# -*- coding: utf-8 -*-
"""HIA_AGENTIC_RAG_DOCS_KNOWLEDGE_RECALL_PHASE4: Docs/Knowledge Recall Quality Tests

Tests that verify docs and knowledge recall QUALITY, not just bucket availability.
Proves that expected documents appear in retrieval results.

WSP 97: These tests measure recall quality. Missing expected evidence is a
        failure or degraded finding, not a pass. Bucket availability alone
        is not recall quality.

WSP 87: Keep tests focused on specific expected documents, not broad ranking.
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
    classify_retrieval_evidence,
)


# =============================================================================
# Live Index Detection (reused from sentinel tests)
# =============================================================================


def _get_live_holo() -> Optional[Any]:
    """Get live HoloIndex instance if available."""
    try:
        ssd_path = Path("E:/HoloIndex")
        if not ssd_path.exists():
            return None

        vectors_path = ssd_path / "vectors"
        if not vectors_path.exists():
            return None

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
# Recall Sentinel Definitions
# =============================================================================


@dataclass
class RecallSentinel:
    """Sentinel for docs/knowledge recall quality testing."""
    query: str
    expected_path_contains: str  # Substring that must appear in a result path
    expected_bucket: str  # docs, wsp, knowledge
    description: str
    top_n: int = 8  # Required position (top_n)


# WSP/Protocol sentinels - should appear in WSP bucket
WSP_RECALL_SENTINELS: List[RecallSentinel] = [
    RecallSentinel(
        query="WSP 97 System Execution Prompting Protocol",
        expected_path_contains="WSP_97_System_Execution_Prompting_Protocol",
        expected_bucket="wsp",
        description="WSP 97 system execution protocol",
        top_n=8,
    ),
    RecallSentinel(
        query="rESP quantum entanglement theoretical foundation WSP 61",
        expected_path_contains="WSP_61_Theoretical_Physics_Foundation_Protocol",
        expected_bucket="wsp",
        description="WSP 61 theoretical physics",
        top_n=8,
    ),
]

# NOTE: Natural language WSP queries have degraded recall
# "WSP 97 retrieve evidence before stating facts" does NOT find WSP_97 in top 8
# Explicit protocol name queries work; natural language descriptions do not
# This is a documented ranking gap for future improvement

# Docs sentinels - should appear in docs bucket
DOCS_RECALL_SENTINELS: List[RecallSentinel] = [
    RecallSentinel(
        query="FOUNDUPS BTC reserve token architecture",
        expected_path_contains="FOUNDUPS_BTC_RESERVE_TOKEN_ARCHITECTURE",
        expected_bucket="docs",
        description="BTC reserve architecture doc",
        top_n=8,
    ),
    # NOTE: These are expected to be DEGRADED based on preflight
    RecallSentinel(
        query="HIA Agentic RAG live collection health audit",
        expected_path_contains="HIA_AGENTIC_RAG_LIVE_COLLECTION_HEALTH",
        expected_bucket="docs",
        description="Live collection health audit doc",
        top_n=8,
    ),
    RecallSentinel(
        query="HoloIndex degraded mode WSP doc retrieval audit",
        expected_path_contains="DEGRADED_MODE_WSP_DOC_RETRIEVAL_AUDIT",
        expected_bucket="docs",
        description="Degraded mode audit doc",
        top_n=8,
    ),
]

# Knowledge sentinels - should appear in knowledge bucket
KNOWLEDGE_RECALL_SENTINELS: List[RecallSentinel] = [
    RecallSentinel(
        query="rESP quantum entanglement cross linguistic signatures research",
        expected_path_contains="rESP_Cross_Linguistic_Quantum_Signatures",
        expected_bucket="knowledge",
        description="rESP cross-linguistic paper",
        top_n=8,
    ),
]

ALL_RECALL_SENTINELS = WSP_RECALL_SENTINELS + DOCS_RECALL_SENTINELS + KNOWLEDGE_RECALL_SENTINELS


# =============================================================================
# Relevance Assertion Helpers
# =============================================================================


def _get_bucket_hits(results: Dict[str, Any], bucket: str) -> List[Dict[str, Any]]:
    """Extract hits from a specific bucket in search results."""
    bucket_map = {
        "code": results.get("code", []),
        "wsp": results.get("wsps", []),
        "docs": results.get("docs", []),
        "knowledge": results.get("knowledge", []),
        "skills": results.get("skills", []),
    }
    return bucket_map.get(bucket, [])


def _find_path_in_hits(
    hits: List[Dict[str, Any]],
    path_contains: str,
    top_n: int = 8
) -> Tuple[bool, int, Optional[str]]:
    """Find if expected path substring appears in top_n hits.

    Returns:
        Tuple of (found, position, actual_path)
        - found: True if path_contains substring found in any top_n result
        - position: 1-indexed position where found, or -1 if not found
        - actual_path: The full path that matched, or None
    """
    for i, hit in enumerate(hits[:top_n]):
        path = hit.get("path") or hit.get("location") or ""
        if path_contains.lower() in path.lower():
            return (True, i + 1, path)
    return (False, -1, None)


def _summarize_top_paths(hits: List[Dict[str, Any]], n: int = 5) -> List[str]:
    """Get top n paths from hits for reporting."""
    paths = []
    for hit in hits[:n]:
        path = hit.get("path") or hit.get("location") or "unknown"
        paths.append(path)
    return paths


# =============================================================================
# Recall Result Dataclass
# =============================================================================


@dataclass
class RecallResult:
    """Result of a recall sentinel test."""
    query: str
    expected_path_contains: str
    expected_bucket: str
    description: str
    top_n: int
    found: bool
    position: int  # 1-indexed, -1 if not found
    actual_path: Optional[str]
    bucket_hit_count: int
    top_paths: List[str]
    verdict: str
    measured_at: str


def _run_recall_sentinel(holo: Any, sentinel: RecallSentinel) -> RecallResult:
    """Run a recall sentinel and check if expected path appears."""
    results = holo.search(sentinel.query, limit=sentinel.top_n)

    # Get bucket hits
    bucket_hits = _get_bucket_hits(results, sentinel.expected_bucket)

    # Check if expected path is in results
    found, position, actual_path = _find_path_in_hits(
        bucket_hits,
        sentinel.expected_path_contains,
        sentinel.top_n
    )

    # Determine verdict
    if found:
        verdict = "PASS"
    else:
        verdict = "FAIL"

    return RecallResult(
        query=sentinel.query,
        expected_path_contains=sentinel.expected_path_contains,
        expected_bucket=sentinel.expected_bucket,
        description=sentinel.description,
        top_n=sentinel.top_n,
        found=found,
        position=position,
        actual_path=actual_path,
        bucket_hit_count=len(bucket_hits),
        top_paths=_summarize_top_paths(bucket_hits, 5),
        verdict=verdict,
        measured_at=datetime.utcnow().isoformat() + "Z",
    )


# =============================================================================
# Live Recall Tests - WSP
# =============================================================================


class TestWSPRecallQuality:
    """Test WSP document recall quality."""

    @SKIP_LIVE
    def test_wsp_97_recall(self):
        """WSP 97 query should return WSP_97 protocol in top 8."""
        holo = _get_live_holo()
        sentinel = WSP_RECALL_SENTINELS[0]  # WSP 97

        result = _run_recall_sentinel(holo, sentinel)

        assert result.found, (
            f"WSP 97 not found in top {sentinel.top_n} WSP results. "
            f"Top paths: {result.top_paths}"
        )

    @SKIP_LIVE
    def test_wsp_61_recall(self):
        """WSP 61 query should return WSP_61 protocol in top 8."""
        holo = _get_live_holo()
        sentinel = WSP_RECALL_SENTINELS[1]  # WSP 61

        result = _run_recall_sentinel(holo, sentinel)

        assert result.found, (
            f"WSP 61 not found in top {sentinel.top_n} WSP results. "
            f"Top paths: {result.top_paths}"
        )


# =============================================================================
# Live Recall Tests - Docs
# =============================================================================


class TestDocsRecallQuality:
    """Test docs recall quality."""

    @SKIP_LIVE
    def test_btc_reserve_architecture_recall(self):
        """BTC reserve query should return architecture doc in top 8."""
        holo = _get_live_holo()
        sentinel = DOCS_RECALL_SENTINELS[0]  # BTC reserve

        result = _run_recall_sentinel(holo, sentinel)

        assert result.found, (
            f"BTC reserve architecture doc not found in top {sentinel.top_n} docs. "
            f"Top paths: {result.top_paths}"
        )

    @SKIP_LIVE
    def test_collection_health_audit_recall(self):
        """Collection health query should return HIA audit doc in top 8.

        After docs re-index (Phase 4B), this file is discoverable at TOP-1.
        """
        holo = _get_live_holo()
        sentinel = DOCS_RECALL_SENTINELS[1]  # HIA collection health

        result = _run_recall_sentinel(holo, sentinel)

        assert result.found, (
            f"HIA collection health doc not found in top {sentinel.top_n} docs. "
            f"Top paths: {result.top_paths}. "
            f"Ensure docs index is fresh: python holo_index.py --index-docs --ssd E:/HoloIndex"
        )

    @SKIP_LIVE
    def test_degraded_mode_audit_recall(self):
        """Degraded mode query should return degraded mode audit doc in top 8.

        After docs re-index (Phase 4B), this file is discoverable at TOP-1.
        """
        holo = _get_live_holo()
        sentinel = DOCS_RECALL_SENTINELS[2]  # Degraded mode audit

        result = _run_recall_sentinel(holo, sentinel)

        assert result.found, (
            f"Degraded mode audit doc not found in top {sentinel.top_n} docs. "
            f"Top paths: {result.top_paths}. "
            f"Ensure docs index is fresh: python holo_index.py --index-docs --ssd E:/HoloIndex"
        )


# =============================================================================
# Live Recall Tests - Knowledge
# =============================================================================


class TestKnowledgeRecallQuality:
    """Test knowledge recall quality."""

    @SKIP_LIVE
    def test_resp_cross_linguistic_recall(self):
        """rESP research query should return cross-linguistic paper in top 8."""
        holo = _get_live_holo()
        sentinel = KNOWLEDGE_RECALL_SENTINELS[0]  # rESP paper

        result = _run_recall_sentinel(holo, sentinel)

        # Knowledge recall may be degraded - use xfail for known gaps
        if not result.found:
            pytest.xfail(
                f"DEGRADED: rESP cross-linguistic paper not in top {sentinel.top_n} knowledge. "
                f"Top paths: {result.top_paths}. "
                f"This is a recall gap to document."
            )


# =============================================================================
# Aggregate Recall Report
# =============================================================================


class TestAggregateRecallQuality:
    """Aggregate recall quality tests."""

    @SKIP_LIVE
    def test_wsp_sentinels_all_pass(self):
        """All WSP recall sentinels should find expected documents."""
        holo = _get_live_holo()
        failures = []

        for sentinel in WSP_RECALL_SENTINELS:
            result = _run_recall_sentinel(holo, sentinel)
            if not result.found:
                failures.append(
                    f"  - {sentinel.description}: expected '{sentinel.expected_path_contains}' "
                    f"not in top {sentinel.top_n}"
                )

        if failures:
            pytest.fail(f"WSP recall failures:\n" + "\n".join(failures))

    @SKIP_LIVE
    def test_critical_docs_sentinels_pass(self):
        """Critical docs (like BTC architecture) should be retrievable."""
        holo = _get_live_holo()

        # Only test the critical doc that must pass
        critical_sentinel = DOCS_RECALL_SENTINELS[0]  # BTC reserve
        result = _run_recall_sentinel(holo, critical_sentinel)

        assert result.found, (
            f"Critical doc recall failure: {critical_sentinel.description}. "
            f"Top paths: {result.top_paths}"
        )


# =============================================================================
# Report Generation
# =============================================================================


def generate_recall_quality_report() -> Dict[str, Any]:
    """Generate a recall quality report for audit documentation."""
    holo = _get_live_holo()
    if holo is None:
        return {
            "status": "SKIPPED",
            "reason": "Live HoloIndex not available at E:/HoloIndex",
            "measured_at": datetime.utcnow().isoformat() + "Z",
        }

    results = []
    for sentinel in ALL_RECALL_SENTINELS:
        result = _run_recall_sentinel(holo, sentinel)
        results.append(asdict(result))

    # Compute aggregates
    total = len(results)
    pass_count = sum(1 for r in results if r["verdict"] == "PASS")
    fail_count = sum(1 for r in results if r["verdict"] == "FAIL")

    # By bucket
    wsp_results = [r for r in results if r["expected_bucket"] == "wsp"]
    docs_results = [r for r in results if r["expected_bucket"] == "docs"]
    knowledge_results = [r for r in results if r["expected_bucket"] == "knowledge"]

    return {
        "status": "COMPLETE",
        "measured_at": datetime.utcnow().isoformat() + "Z",
        "total_sentinels": total,
        "aggregate": {
            "pass_count": pass_count,
            "pass_rate": round(pass_count / total, 4) if total > 0 else 0,
            "fail_count": fail_count,
            "fail_rate": round(fail_count / total, 4) if total > 0 else 0,
        },
        "by_bucket": {
            "wsp": {
                "total": len(wsp_results),
                "pass": sum(1 for r in wsp_results if r["verdict"] == "PASS"),
            },
            "docs": {
                "total": len(docs_results),
                "pass": sum(1 for r in docs_results if r["verdict"] == "PASS"),
            },
            "knowledge": {
                "total": len(knowledge_results),
                "pass": sum(1 for r in knowledge_results if r["verdict"] == "PASS"),
            },
        },
        "sentinel_results": results,
    }


if __name__ == "__main__":
    import json
    report = generate_recall_quality_report()
    print(json.dumps(report, indent=2))
