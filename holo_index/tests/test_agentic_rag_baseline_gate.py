# -*- coding: utf-8 -*-
"""HIA_AGENTIC_RAG_BASELINE_GATE_PHASE1: Agentic RAG Verdict Tests

Tests that enforce WSP 97 truth boundaries for retrieval classification:
- WSP-intent with zero WSP hits cannot be SUFFICIENT
- Empty retrieval cannot be SUFFICIENT
- Intent-bucket alignment is enforced

WSP 97: These tests use mock payloads, not live HoloIndex retrieval.
Live retrieval quality is tested in test_search_quality_baseline.py.
"""

import pytest
from holo_index.core.agentic_rag_verdict import (
    RetrievalVerdict,
    QueryIntent,
    RetrievalEvidenceSummary,
    classify_query_intent,
    classify_retrieval_evidence,
    format_verdict_for_agent,
)


# =============================================================================
# Query Intent Classification Tests
# =============================================================================


class TestQueryIntentClassification:
    """Test query intent classification heuristics."""

    def test_wsp_intent_detected(self):
        """WSP keywords trigger WSP intent."""
        assert classify_query_intent("WSP 97 system execution") == QueryIntent.WSP
        assert classify_query_intent("protocol compliance check") == QueryIntent.WSP
        assert classify_query_intent("wsp verification") == QueryIntent.WSP

    def test_docs_intent_detected(self):
        """Documentation keywords trigger DOCS intent."""
        assert classify_query_intent("README module overview") == QueryIntent.DOCS
        assert classify_query_intent("interface documentation") == QueryIntent.DOCS
        assert classify_query_intent("modlog updates") == QueryIntent.DOCS

    def test_knowledge_intent_detected(self):
        """Knowledge keywords trigger KNOWLEDGE intent."""
        assert classify_query_intent("research paper summary") == QueryIntent.KNOWLEDGE
        assert classify_query_intent("knowledge base theory") == QueryIntent.KNOWLEDGE

    def test_skill_intent_detected(self):
        """Skill keywords trigger SKILL intent."""
        assert classify_query_intent("skillz commit workflow") == QueryIntent.SKILL
        assert classify_query_intent("skill capability registry") == QueryIntent.SKILL

    def test_symbol_intent_detected(self):
        """Symbol keywords trigger SYMBOL intent."""
        assert classify_query_intent("function execute_search") == QueryIntent.SYMBOL
        assert classify_query_intent("class HoloIndex") == QueryIntent.SYMBOL
        assert classify_query_intent("def _tokenize_query") == QueryIntent.SYMBOL

    def test_code_intent_detected(self):
        """Code keywords trigger CODE intent."""
        assert classify_query_intent("search engine implementation") == QueryIntent.CODE
        assert classify_query_intent("module code structure") == QueryIntent.CODE

    def test_general_intent_fallback(self):
        """Unknown queries fall back to GENERAL."""
        assert classify_query_intent("random unrelated query") == QueryIntent.GENERAL
        assert classify_query_intent("hello world") == QueryIntent.GENERAL


# =============================================================================
# Core Verdict Rules Tests
# =============================================================================


class TestCoreVerdictRules:
    """Test WSP 97 truth boundary enforcement."""

    def test_empty_retrieval_is_unsafe(self):
        """Empty all buckets => UNSAFE_TO_ACT"""
        payload = {
            "code_hits": [],
            "wsp_hits": [],
            "docs_hits": [],
            "knowledge_hits": [],
            "test_hits": [],
            "skill_hits": [],
            "symbol_hits": [],
            "metadata": {
                "query": "test query",
                "code_count": 0,
                "wsp_count": 0,
                "docs_count": 0,
                "knowledge_count": 0,
                "test_count": 0,
                "skill_count": 0,
                "symbol_count": 0,
            }
        }
        summary = classify_retrieval_evidence(payload, QueryIntent.GENERAL)
        assert summary.verdict == RetrievalVerdict.UNSAFE_TO_ACT
        assert summary.total_hits == 0

    def test_backend_error_is_unsafe(self):
        """Backend error => UNSAFE_TO_ACT"""
        payload = {
            "code_hits": [],
            "wsp_hits": [],
            "metadata": {
                "query": "test query",
                "error": "ChromaDB connection failed",
            }
        }
        summary = classify_retrieval_evidence(payload, QueryIntent.CODE)
        assert summary.verdict == RetrievalVerdict.UNSAFE_TO_ACT
        assert summary.backend_error is True

    def test_wsp_intent_zero_wsp_hits_not_sufficient(self):
        """WSP intent with zero WSP hits => never SUFFICIENT"""
        # Has code hits but no WSP
        payload = {
            "code_hits": [{"path": "some_code.py"}],
            "wsp_hits": [],
            "docs_hits": [],
            "knowledge_hits": [],
            "metadata": {
                "query": "WSP 97 protocol",
                "code_count": 1,
                "wsp_count": 0,
                "docs_count": 0,
                "knowledge_count": 0,
            }
        }
        summary = classify_retrieval_evidence(payload, QueryIntent.WSP)
        assert summary.verdict != RetrievalVerdict.SUFFICIENT
        assert summary.verdict in [RetrievalVerdict.DEGRADED, RetrievalVerdict.UNSAFE_TO_ACT]

    def test_wsp_intent_with_wsp_hits_sufficient(self):
        """WSP intent with WSP hits => SUFFICIENT"""
        payload = {
            "code_hits": [],
            "wsp_hits": [{"path": "WSP_97.md"}],
            "docs_hits": [],
            "knowledge_hits": [],
            "metadata": {
                "query": "WSP 97 protocol",
                "code_count": 0,
                "wsp_count": 1,
                "docs_count": 0,
                "knowledge_count": 0,
            }
        }
        summary = classify_retrieval_evidence(payload, QueryIntent.WSP)
        assert summary.verdict == RetrievalVerdict.SUFFICIENT

    def test_docs_intent_zero_docs_degraded(self):
        """Docs intent with zero docs hits => DEGRADED"""
        payload = {
            "code_hits": [{"path": "code.py"}],
            "wsp_hits": [],
            "docs_hits": [],
            "knowledge_hits": [],
            "metadata": {
                "query": "README overview",
                "code_count": 1,
                "wsp_count": 0,
                "docs_count": 0,
                "knowledge_count": 0,
            }
        }
        summary = classify_retrieval_evidence(payload, QueryIntent.DOCS)
        assert summary.verdict == RetrievalVerdict.DEGRADED
        assert summary.degraded is True

    def test_code_intent_with_code_hits_sufficient(self):
        """Code intent with code hits => SUFFICIENT"""
        payload = {
            "code_hits": [{"path": "search_engine.py"}],
            "wsp_hits": [],
            "docs_hits": [],
            "knowledge_hits": [],
            "symbol_hits": [],
            "metadata": {
                "query": "search implementation",
                "code_count": 1,
                "wsp_count": 0,
                "docs_count": 0,
                "knowledge_count": 0,
                "symbol_count": 0,
            }
        }
        summary = classify_retrieval_evidence(payload, QueryIntent.CODE)
        assert summary.verdict == RetrievalVerdict.SUFFICIENT

    def test_code_intent_only_docs_degraded(self):
        """Code intent with only docs hits => DEGRADED"""
        payload = {
            "code_hits": [],
            "wsp_hits": [],
            "docs_hits": [{"path": "README.md"}],
            "knowledge_hits": [],
            "symbol_hits": [],
            "metadata": {
                "query": "search implementation",
                "code_count": 0,
                "wsp_count": 0,
                "docs_count": 1,
                "knowledge_count": 0,
                "symbol_count": 0,
            }
        }
        summary = classify_retrieval_evidence(payload, QueryIntent.CODE)
        assert summary.verdict == RetrievalVerdict.DEGRADED


# =============================================================================
# Evidence Summary Tests
# =============================================================================


class TestEvidenceSummary:
    """Test RetrievalEvidenceSummary data structure."""

    def test_total_hits_calculated(self):
        """Total hits auto-calculated from bucket counts."""
        summary = RetrievalEvidenceSummary(
            query="test",
            intent=QueryIntent.GENERAL,
            code_hits_count=5,
            wsp_hits_count=3,
            docs_hits_count=2,
            knowledge_hits_count=1,
        )
        assert summary.total_hits == 11

    def test_default_verdict_unsafe(self):
        """Default verdict is UNSAFE_TO_ACT."""
        summary = RetrievalEvidenceSummary(
            query="test",
            intent=QueryIntent.GENERAL,
        )
        assert summary.verdict == RetrievalVerdict.UNSAFE_TO_ACT


# =============================================================================
# Format for Agent Tests
# =============================================================================


class TestFormatForAgent:
    """Test verdict formatting for 0102 agent consumption."""

    def test_sufficient_format(self):
        """SUFFICIENT verdict formats with [OK]."""
        summary = RetrievalEvidenceSummary(
            query="WSP 97",
            intent=QueryIntent.WSP,
            wsp_hits_count=3,
            verdict=RetrievalVerdict.SUFFICIENT,
            reason="WSP intent satisfied",
        )
        output = format_verdict_for_agent(summary)
        assert "[OK]" in output
        assert "sufficient" in output

    def test_degraded_format(self):
        """DEGRADED verdict formats with [WARN]."""
        summary = RetrievalEvidenceSummary(
            query="test",
            intent=QueryIntent.DOCS,
            code_hits_count=1,
            verdict=RetrievalVerdict.DEGRADED,
            reason="Only code hits",
        )
        output = format_verdict_for_agent(summary)
        assert "[WARN]" in output
        assert "degraded" in output

    def test_unsafe_format(self):
        """UNSAFE_TO_ACT verdict formats with [FAIL]."""
        summary = RetrievalEvidenceSummary(
            query="test",
            intent=QueryIntent.WSP,
            verdict=RetrievalVerdict.UNSAFE_TO_ACT,
            reason="No hits",
        )
        output = format_verdict_for_agent(summary)
        assert "[FAIL]" in output
        assert "unsafe_to_act" in output


# =============================================================================
# Integration Tests (Mock Payloads)
# =============================================================================


class TestIntegrationMockPayloads:
    """Integration tests with realistic mock payloads."""

    def test_balanced_retrieval_general_sufficient(self):
        """Balanced retrieval for general query => SUFFICIENT."""
        payload = {
            "code_hits": [{"path": f"code_{i}.py"} for i in range(8)],
            "wsp_hits": [{"path": f"WSP_{i}.md"} for i in range(8)],
            "docs_hits": [{"path": f"doc_{i}.md"} for i in range(8)],
            "knowledge_hits": [{"path": f"knowledge_{i}.md"} for i in range(8)],
            "test_hits": [],
            "skill_hits": [],
            "symbol_hits": [],
            "metadata": {
                "query": "HoloIndex overview",
                "code_count": 8,
                "wsp_count": 8,
                "docs_count": 8,
                "knowledge_count": 8,
                "test_count": 0,
                "skill_count": 0,
                "symbol_count": 0,
            }
        }
        summary = classify_retrieval_evidence(payload)
        assert summary.verdict == RetrievalVerdict.SUFFICIENT
        assert summary.total_hits == 32

    def test_wsp_heavy_for_protocol_query_sufficient(self):
        """WSP-heavy results for protocol query => SUFFICIENT."""
        payload = {
            "code_hits": [],
            "wsp_hits": [{"path": "WSP_97.md"}, {"path": "WSP_50.md"}],
            "docs_hits": [],
            "knowledge_hits": [],
            "metadata": {
                "query": "WSP 97 execution protocol",
                "code_count": 0,
                "wsp_count": 2,
                "docs_count": 0,
                "knowledge_count": 0,
            }
        }
        summary = classify_retrieval_evidence(payload)
        # Query contains "WSP" so intent should be WSP
        assert summary.intent == QueryIntent.WSP
        assert summary.verdict == RetrievalVerdict.SUFFICIENT

    def test_code_only_for_wsp_query_degraded(self):
        """Code-only results for WSP query => DEGRADED."""
        payload = {
            "code_hits": [{"path": "search_engine.py"}],
            "wsp_hits": [],
            "docs_hits": [],
            "knowledge_hits": [],
            "metadata": {
                "query": "WSP compliance checking",
                "code_count": 1,
                "wsp_count": 0,
                "docs_count": 0,
                "knowledge_count": 0,
            }
        }
        summary = classify_retrieval_evidence(payload)
        assert summary.intent == QueryIntent.WSP
        assert summary.verdict == RetrievalVerdict.DEGRADED


# =============================================================================
# WSP 97 Explicit Boundary Tests
# =============================================================================


class TestWSP97Boundaries:
    """Explicit tests for WSP 97 truth boundary claims."""

    def test_never_claim_sufficient_on_empty(self):
        """SUFFICIENT is never returned for empty retrieval."""
        for intent in QueryIntent:
            payload = {
                "code_hits": [],
                "wsp_hits": [],
                "docs_hits": [],
                "knowledge_hits": [],
                "test_hits": [],
                "skill_hits": [],
                "symbol_hits": [],
                "metadata": {
                    "query": "test",
                    "code_count": 0,
                    "wsp_count": 0,
                    "docs_count": 0,
                    "knowledge_count": 0,
                    "test_count": 0,
                    "skill_count": 0,
                    "symbol_count": 0,
                }
            }
            summary = classify_retrieval_evidence(payload, intent)
            assert summary.verdict != RetrievalVerdict.SUFFICIENT, \
                f"Empty retrieval claimed SUFFICIENT for {intent}"

    def test_wsp_intent_requires_wsp_hits_for_sufficient(self):
        """WSP intent requires WSP hits to be SUFFICIENT."""
        # Code hits only
        payload = {
            "code_hits": [{"path": "code.py"}] * 10,
            "wsp_hits": [],
            "docs_hits": [],
            "knowledge_hits": [],
            "metadata": {
                "query": "test",
                "code_count": 10,
                "wsp_count": 0,
                "docs_count": 0,
                "knowledge_count": 0,
            }
        }
        summary = classify_retrieval_evidence(payload, QueryIntent.WSP)
        assert summary.verdict != RetrievalVerdict.SUFFICIENT

        # Add WSP hit
        payload["wsp_hits"] = [{"path": "WSP_97.md"}]
        payload["metadata"]["wsp_count"] = 1
        summary = classify_retrieval_evidence(payload, QueryIntent.WSP)
        assert summary.verdict == RetrievalVerdict.SUFFICIENT
