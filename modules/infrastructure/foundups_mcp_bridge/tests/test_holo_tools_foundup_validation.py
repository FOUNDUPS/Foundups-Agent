# -*- coding: utf-8 -*-
"""Tests for S2 holo_search foundup_id fail-closed validation.

Contract: MCP_FOUNDUP_SCOPE_S2_VALIDATION_IMPL_PHASE1
Per spec section 11 test plan.

WSP 97 Labels:
  - MCP_SCOPE_VALIDATION_ONLY
  - REGISTRY_READONLY
  - FAIL_CLOSED_REQUIRED
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from modules.infrastructure.foundups_mcp_bridge.src.holo_tools import holo_search

# Test repo root (use the actual repo for real registry)
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent


class TestValidFoundupIdProceeds:
    """T1: Valid foundup_id passes validation and search executes."""

    def test_valid_foundup_id_returns_ok(self):
        """Known foundup_id allows search to proceed."""
        result = holo_search(REPO_ROOT, "test query", foundup_id="gotjunk_001")
        assert result["status"] == "ok", f"Expected ok, got: {result}"
        assert "error" not in result or result.get("error") is None

    def test_valid_foundup_id_includes_warning(self):
        """Valid foundup_id adds Phase 2 deferral warning."""
        result = holo_search(REPO_ROOT, "test query", foundup_id="kosei")
        assert result["status"] == "ok"
        warnings = result.get("data", {}).get("metadata", {}).get("warnings", [])
        assert any("Phase 2" in w for w in warnings), f"Expected Phase 2 warning, got: {warnings}"


class TestInvalidFoundupIdFailsClosed:
    """T2/T3: Invalid foundup_id fails closed with INVALID_FOUNDUP_ID."""

    def test_unknown_foundup_id_returns_error(self):
        """Unknown foundup_id returns INVALID_FOUNDUP_ID error."""
        result = holo_search(REPO_ROOT, "test query", foundup_id="nonexistent_xyz_999")
        assert result["status"] == "error"
        assert result["error"]["code"] == "INVALID_FOUNDUP_ID"
        assert "nonexistent_xyz_999" in result["error"]["message"]

    def test_unknown_id_includes_details(self):
        """Error includes pattern_valid and registry_checked details."""
        result = holo_search(REPO_ROOT, "test query", foundup_id="valid_pattern_but_unknown")
        assert result["status"] == "error"
        details = result["error"].get("details", {})
        assert details.get("pattern_valid") is True
        assert details.get("registry_checked") is True

    def test_pattern_invalid_id_fails(self):
        """ID not matching ^[a-z0-9_]+$ pattern fails with pattern_valid=False."""
        result = holo_search(REPO_ROOT, "test query", foundup_id="INVALID-ID")
        assert result["status"] == "error"
        assert result["error"]["code"] == "INVALID_FOUNDUP_ID"
        details = result["error"].get("details", {})
        assert details.get("pattern_valid") is False

    def test_invalid_id_includes_data_envelope(self):
        """Error response includes data envelope with query context."""
        result = holo_search(REPO_ROOT, "my test query", foundup_id="fake_id", doc_type_filter="code")
        assert result["status"] == "error"
        data = result.get("data", {})
        assert data.get("query") == "my test query"
        assert data.get("foundup_id") == "fake_id"
        assert data.get("hits") == []
        assert data.get("hit_count") == 0


class TestMissingFoundupIdPreservesBehavior:
    """T5: null/None foundup_id skips validation entirely."""

    def test_none_foundup_id_proceeds(self):
        """None foundup_id skips validation and proceeds to search."""
        result = holo_search(REPO_ROOT, "test query", foundup_id=None)
        assert result["status"] == "ok"

    def test_omitted_foundup_id_proceeds(self):
        """Omitted foundup_id parameter proceeds to search."""
        result = holo_search(REPO_ROOT, "test query")
        assert result["status"] == "ok"

    def test_no_foundup_id_no_validation_warning(self):
        """When foundup_id is not provided, no validation warning is added."""
        result = holo_search(REPO_ROOT, "test query")
        warnings = result.get("data", {}).get("metadata", {}).get("warnings", [])
        assert not any("Phase 2" in w for w in warnings)


class TestRegistryUnavailableFailsClosed:
    """T6: Registry load failure returns REGISTRY_UNAVAILABLE."""

    def test_registry_unavailable_returns_error(self):
        """If registry loader fails, return REGISTRY_UNAVAILABLE error."""
        # Reset the global loader state
        import modules.infrastructure.foundups_mcp_bridge.src.holo_tools as holo_tools
        original_loader = holo_tools._REGISTRY_LOADER
        original_error = holo_tools._REGISTRY_LOAD_ERROR

        try:
            # Force a load error
            holo_tools._REGISTRY_LOADER = None
            holo_tools._REGISTRY_LOAD_ERROR = FileNotFoundError("Test: registry not found")

            result = holo_search(REPO_ROOT, "test query", foundup_id="gotjunk_001")
            assert result["status"] == "error"
            assert result["error"]["code"] == "REGISTRY_UNAVAILABLE"
            assert "exception_type" in result["error"].get("details", {})

        finally:
            # Restore original state
            holo_tools._REGISTRY_LOADER = original_loader
            holo_tools._REGISTRY_LOAD_ERROR = original_error

    def test_registry_unavailable_includes_data_envelope(self):
        """REGISTRY_UNAVAILABLE error includes query context."""
        import modules.infrastructure.foundups_mcp_bridge.src.holo_tools as holo_tools
        original_loader = holo_tools._REGISTRY_LOADER
        original_error = holo_tools._REGISTRY_LOAD_ERROR

        try:
            holo_tools._REGISTRY_LOADER = None
            holo_tools._REGISTRY_LOAD_ERROR = FileNotFoundError("Test")

            result = holo_search(REPO_ROOT, "my query", foundup_id="any_id")
            assert result["status"] == "error"
            data = result.get("data", {})
            assert data.get("query") == "my query"
            assert data.get("foundup_id") == "any_id"

        finally:
            holo_tools._REGISTRY_LOADER = original_loader
            holo_tools._REGISTRY_LOAD_ERROR = original_error


class TestSearchNotCalledOnInvalidId:
    """T8: Search function is not called when validation rejects."""

    def test_holoindex_not_called_on_invalid_id(self):
        """HoloIndex search is not invoked when foundup_id is invalid."""
        import modules.infrastructure.foundups_mcp_bridge.src.holo_tools as holo_tools

        call_count = {"value": 0}
        original_get_holoindex = holo_tools._get_holoindex

        def mock_get_holoindex(repo_root):
            call_count["value"] += 1
            return original_get_holoindex(repo_root)

        try:
            holo_tools._get_holoindex = mock_get_holoindex
            result = holo_search(REPO_ROOT, "test query", foundup_id="invalid_xyz")

            assert result["status"] == "error"
            assert result["error"]["code"] == "INVALID_FOUNDUP_ID"
            assert call_count["value"] == 0, "HoloIndex should not be called on invalid foundup_id"

        finally:
            holo_tools._get_holoindex = original_get_holoindex


class TestValidationMetaSource:
    """T8 extended: Validation rejections have correct meta.source."""

    def test_validation_error_has_validation_source(self):
        """Validation error response has meta.source='validation'."""
        result = holo_search(REPO_ROOT, "test query", foundup_id="fake_id")
        assert result["status"] == "error"
        meta = result.get("meta", {})
        assert meta.get("source") == "validation"

    def test_validation_error_has_surface_s2(self):
        """Validation error has correct surface tag."""
        result = holo_search(REPO_ROOT, "test query", foundup_id="fake_id")
        meta = result.get("meta", {})
        assert meta.get("surface") == "S2"

    def test_validation_error_has_zero_confidence(self):
        """Validation error has confidence=0.0."""
        result = holo_search(REPO_ROOT, "test query", foundup_id="fake_id")
        meta = result.get("meta", {})
        assert meta.get("confidence") == 0.0


class TestRegressionExistingBehavior:
    """R1/R2: Existing behavior is preserved."""

    def test_empty_query_still_rejected(self):
        """Empty query rejection still works."""
        result = holo_search(REPO_ROOT, "")
        assert result["status"] == "error"
        assert result["error"]["code"] == "EMPTY_QUERY"

    def test_whitespace_query_still_rejected(self):
        """Whitespace-only query rejection still works."""
        result = holo_search(REPO_ROOT, "   ")
        assert result["status"] == "error"
        assert result["error"]["code"] == "EMPTY_QUERY"

    def test_normal_search_without_foundup_id_works(self):
        """Normal search without foundup_id still works."""
        result = holo_search(REPO_ROOT, "HoloIndex search")
        assert result["status"] == "ok"
        assert "hits" in result.get("data", {})

    def test_limit_clamping_still_works(self):
        """Limit clamping behavior preserved."""
        result = holo_search(REPO_ROOT, "test", limit=100)
        assert result["status"] == "ok"
        warnings = result.get("data", {}).get("metadata", {}).get("warnings", [])
        assert any("clamped" in w.lower() for w in warnings)


class TestAllKnownFoundupIds:
    """Verify validation accepts all known registry IDs."""

    @pytest.fixture
    def known_ids(self):
        """Load known IDs from production registry."""
        registry_path = REPO_ROOT / "modules" / "foundups" / "foundup_registry.json"
        with open(registry_path) as f:
            registry = json.load(f)
        return [e["foundup_id"] for e in registry["entities"]]

    def test_all_known_ids_pass_validation(self, known_ids):
        """All IDs in production registry pass validation."""
        for fid in known_ids[:5]:  # Test first 5 to keep test fast
            result = holo_search(REPO_ROOT, "test", foundup_id=fid)
            assert result["status"] == "ok", f"foundup_id '{fid}' should pass validation"
