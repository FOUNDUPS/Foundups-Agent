# -*- coding: utf-8 -*-
"""HIA_AGENTIC_RAG_LIVE_COLLECTION_HEALTH_PHASE2: Collection Health Tests

Tests for collection health inspection and Agentic RAG readiness classification.

WSP 97: These tests use mock collection objects, not live ChromaDB.
Live collection health is tested via CLI command separately.
"""

import json
import pytest
from unittest.mock import MagicMock, PropertyMock

from holo_index.core.collection_health import (
    CollectionHealthStatus,
    CollectionHealth,
    HoloIndexHealthReport,
    inspect_holoindex_collection_health,
    format_health_report,
    REQUIRED_COLLECTIONS,
    OPTIONAL_COLLECTIONS,
)


# =============================================================================
# Mock Fixtures
# =============================================================================


def create_mock_holo(collection_counts: dict) -> MagicMock:
    """Create a mock HoloIndex with specified collection counts.

    Args:
        collection_counts: Dict mapping collection names to counts.
            Special values:
            - -1: Collection raises exception (access error)
            - None: Collection doesn't exist
    """
    mock_holo = MagicMock()
    mock_holo.vector_path = "/test/vectors"

    # Map collection names to attributes
    attr_map = {
        "navigation_code": "code_collection",
        "navigation_wsp": "wsp_collection",
        "navigation_tests": "test_collection",
        "navigation_skills": "skill_collection",
        "navigation_symbols": "symbol_collection",
        "navigation_docs": "docs_collection",
        "navigation_knowledge": "knowledge_collection",
    }

    # Set up collection mocks
    for collection_name, attr_name in attr_map.items():
        count = collection_counts.get(collection_name)

        if count is None:
            setattr(mock_holo, attr_name, None)
        elif count == -1:
            mock_collection = MagicMock()
            mock_collection.count.side_effect = Exception("Access error")
            setattr(mock_holo, attr_name, mock_collection)
        else:
            mock_collection = MagicMock()
            mock_collection.count.return_value = count
            setattr(mock_holo, attr_name, mock_collection)

    # Mock client for fallback (not used in tests but needed)
    mock_holo.client = None

    return mock_holo


# =============================================================================
# CollectionHealth Dataclass Tests
# =============================================================================


class TestCollectionHealth:
    """Test CollectionHealth dataclass."""

    def test_to_dict(self):
        """CollectionHealth converts to JSON-serializable dict."""
        health = CollectionHealth(
            name="navigation_wsp",
            count=117,
            status=CollectionHealthStatus.HEALTHY,
            required_for_agentic_rag=True,
            reason="Collection healthy",
        )
        d = health.to_dict()
        assert d["name"] == "navigation_wsp"
        assert d["count"] == 117
        assert d["status"] == "healthy"
        assert d["required_for_agentic_rag"] is True

    def test_default_values(self):
        """CollectionHealth has sensible defaults."""
        health = CollectionHealth(name="test")
        assert health.count == 0
        assert health.status == CollectionHealthStatus.UNKNOWN
        assert health.required_for_agentic_rag is False


# =============================================================================
# HoloIndexHealthReport Dataclass Tests
# =============================================================================


class TestHoloIndexHealthReport:
    """Test HoloIndexHealthReport dataclass."""

    def test_to_json(self):
        """Report converts to valid JSON."""
        report = HoloIndexHealthReport(
            vector_path="/test",
            collections=[
                CollectionHealth(
                    name="navigation_wsp",
                    count=100,
                    status=CollectionHealthStatus.HEALTHY,
                    required_for_agentic_rag=True,
                )
            ],
            overall_status=CollectionHealthStatus.HEALTHY,
            agentic_rag_ready=True,
            degraded=False,
            reasons=[],
        )
        json_str = report.to_json()
        parsed = json.loads(json_str)
        assert parsed["vector_path"] == "/test"
        assert parsed["agentic_rag_ready"] is True
        assert len(parsed["collections"]) == 1


# =============================================================================
# Agentic RAG Readiness Tests
# =============================================================================


class TestAgenticRagReadiness:
    """Test Agentic RAG readiness classification."""

    def test_all_required_present_ready(self):
        """All required collections with counts > 0 => ready."""
        mock_holo = create_mock_holo({
            "navigation_code": 500,
            "navigation_wsp": 117,
            "navigation_symbols": 20000,
            "navigation_docs": 100,
            "navigation_knowledge": 50,
            "navigation_tests": 30,
            "navigation_skills": 20,
        })
        report = inspect_holoindex_collection_health(mock_holo)
        assert report.agentic_rag_ready is True
        assert report.overall_status == CollectionHealthStatus.HEALTHY

    def test_missing_wsp_not_ready(self):
        """Missing WSP collection => not ready."""
        mock_holo = create_mock_holo({
            "navigation_code": 500,
            "navigation_wsp": None,  # Missing
            "navigation_symbols": 20000,
            "navigation_docs": 100,
            "navigation_knowledge": 50,
            "navigation_tests": 30,
            "navigation_skills": 20,
        })
        report = inspect_holoindex_collection_health(mock_holo)
        assert report.agentic_rag_ready is False
        assert any("navigation_wsp" in r and "missing" in r.lower() for r in report.reasons)

    def test_empty_wsp_not_ready(self):
        """Empty WSP collection => not ready."""
        mock_holo = create_mock_holo({
            "navigation_code": 500,
            "navigation_wsp": 0,  # Empty
            "navigation_symbols": 20000,
            "navigation_docs": 100,
            "navigation_knowledge": 50,
            "navigation_tests": 30,
            "navigation_skills": 20,
        })
        report = inspect_holoindex_collection_health(mock_holo)
        assert report.agentic_rag_ready is False
        assert any("navigation_wsp" in r and "empty" in r.lower() for r in report.reasons)

    def test_missing_code_not_ready(self):
        """Missing code collection => not ready."""
        mock_holo = create_mock_holo({
            "navigation_code": None,  # Missing
            "navigation_wsp": 117,
            "navigation_symbols": 20000,
            "navigation_docs": 100,
            "navigation_knowledge": 50,
            "navigation_tests": 30,
            "navigation_skills": 20,
        })
        report = inspect_holoindex_collection_health(mock_holo)
        assert report.agentic_rag_ready is False

    def test_missing_optional_degraded_but_ready(self):
        """Missing optional collections => degraded but still ready."""
        mock_holo = create_mock_holo({
            "navigation_code": 500,
            "navigation_wsp": 117,
            "navigation_symbols": 20000,
            "navigation_docs": None,  # Optional missing
            "navigation_knowledge": None,  # Optional missing
            "navigation_tests": None,  # Optional missing
            "navigation_skills": None,  # Optional missing
        })
        report = inspect_holoindex_collection_health(mock_holo)
        assert report.agentic_rag_ready is True
        assert report.degraded is True
        assert len(report.reasons) > 0  # Should have reasons for missing optional

    def test_access_error_unknown_not_ready(self):
        """Collection access error => unknown, not ready."""
        mock_holo = create_mock_holo({
            "navigation_code": 500,
            "navigation_wsp": -1,  # Access error
            "navigation_symbols": 20000,
            "navigation_docs": 100,
            "navigation_knowledge": 50,
            "navigation_tests": 30,
            "navigation_skills": 20,
        })
        report = inspect_holoindex_collection_health(mock_holo)
        assert report.agentic_rag_ready is False

        # Find WSP collection in report
        wsp_health = next(c for c in report.collections if c.name == "navigation_wsp")
        assert wsp_health.status == CollectionHealthStatus.UNKNOWN

    def test_low_count_degraded(self):
        """Low count (< 10) => degraded status."""
        mock_holo = create_mock_holo({
            "navigation_code": 5,  # Low count
            "navigation_wsp": 117,
            "navigation_symbols": 20000,
            "navigation_docs": 100,
            "navigation_knowledge": 50,
            "navigation_tests": 30,
            "navigation_skills": 20,
        })
        report = inspect_holoindex_collection_health(mock_holo)

        code_health = next(c for c in report.collections if c.name == "navigation_code")
        assert code_health.status == CollectionHealthStatus.DEGRADED


# =============================================================================
# Format Tests
# =============================================================================


class TestFormatHealthReport:
    """Test health report formatting."""

    def test_format_healthy_report(self):
        """Healthy report formats with [OK] markers."""
        mock_holo = create_mock_holo({
            "navigation_code": 500,
            "navigation_wsp": 117,
            "navigation_symbols": 20000,
            "navigation_docs": 100,
            "navigation_knowledge": 50,
            "navigation_tests": 30,
            "navigation_skills": 20,
        })
        report = inspect_holoindex_collection_health(mock_holo)
        output = format_health_report(report)

        assert "HEALTHY" in output
        assert "Agentic RAG Ready: YES" in output
        assert "[OK]" in output

    def test_format_unhealthy_report(self):
        """Unhealthy report formats with warnings."""
        mock_holo = create_mock_holo({
            "navigation_code": 500,
            "navigation_wsp": 0,  # Empty
            "navigation_symbols": 20000,
            "navigation_docs": 100,
            "navigation_knowledge": 50,
            "navigation_tests": 30,
            "navigation_skills": 20,
        })
        report = inspect_holoindex_collection_health(mock_holo)
        output = format_health_report(report)

        assert "Agentic RAG Ready: NO" in output
        assert "[EMPTY]" in output or "[MISSING]" in output

    def test_format_contains_vector_path(self):
        """Report output includes vector path."""
        mock_holo = create_mock_holo({
            "navigation_code": 500,
            "navigation_wsp": 117,
            "navigation_symbols": 20000,
        })
        report = inspect_holoindex_collection_health(mock_holo)
        output = format_health_report(report)

        assert "/test/vectors" in output


# =============================================================================
# Required Collections Tests
# =============================================================================


class TestRequiredCollections:
    """Test required collection configuration."""

    def test_wsp_is_required(self):
        """navigation_wsp is marked required."""
        assert REQUIRED_COLLECTIONS.get("navigation_wsp") is True

    def test_code_is_required(self):
        """navigation_code is marked required."""
        assert REQUIRED_COLLECTIONS.get("navigation_code") is True

    def test_symbols_is_required(self):
        """navigation_symbols is marked required."""
        assert REQUIRED_COLLECTIONS.get("navigation_symbols") is True

    def test_docs_is_optional(self):
        """navigation_docs is optional."""
        assert OPTIONAL_COLLECTIONS.get("navigation_docs") is False

    def test_knowledge_is_optional(self):
        """navigation_knowledge is optional."""
        assert OPTIONAL_COLLECTIONS.get("navigation_knowledge") is False
