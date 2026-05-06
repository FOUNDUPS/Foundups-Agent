# -*- coding: utf-8 -*-
"""HIA_TENANT_CONTEXT_BINDING_PHASE4: Tenant Context Binding Tests

Tests that verify automatic FoundUp scope resolution with precedence:
1. explicit foundup_id argument
2. instance context (set_foundup_context)
3. HOLO_FOUNDUP_ID environment variable
4. none (legacy global behavior)

WSP 97: These tests verify scope resolution correctness at the unit level.
WSP 87: Keep tests focused on binding behavior.
"""

import os
import pytest
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

from holo_index.core.search_engine import (
    _resolve_foundup_scope,
    execute_search,
)


# =============================================================================
# Scope Resolution Tests
# =============================================================================


class TestResolveFoundupScope:
    """Test _resolve_foundup_scope() precedence logic."""

    @pytest.fixture
    def mock_holo(self):
        """Create a mock HoloIndex without context."""
        holo = MagicMock()
        holo._foundup_context = None
        return holo

    @pytest.fixture
    def mock_holo_with_context(self):
        """Create a mock HoloIndex with context bound."""
        holo = MagicMock()
        holo._foundup_context = "context_foundup"
        return holo

    def test_explicit_takes_precedence(self, mock_holo_with_context):
        """Explicit foundup_id arg overrides context."""
        with patch.dict(os.environ, {"HOLO_FOUNDUP_ID": "env_foundup"}):
            foundup_id, source = _resolve_foundup_scope(
                mock_holo_with_context, "explicit_foundup"
            )
            assert foundup_id == "explicit_foundup"
            assert source == "explicit"

    def test_context_takes_precedence_over_env(self, mock_holo_with_context):
        """Instance context overrides environment."""
        with patch.dict(os.environ, {"HOLO_FOUNDUP_ID": "env_foundup"}):
            foundup_id, source = _resolve_foundup_scope(
                mock_holo_with_context, None
            )
            assert foundup_id == "context_foundup"
            assert source == "context"

    def test_env_fallback(self, mock_holo):
        """Environment variable used when no explicit or context."""
        with patch.dict(os.environ, {"HOLO_FOUNDUP_ID": "env_foundup"}):
            foundup_id, source = _resolve_foundup_scope(mock_holo, None)
            assert foundup_id == "env_foundup"
            assert source == "env"

    def test_none_when_no_scope(self, mock_holo):
        """No scope returns None with 'none' source."""
        with patch.dict(os.environ, {}, clear=True):
            # Ensure HOLO_FOUNDUP_ID is not set
            os.environ.pop("HOLO_FOUNDUP_ID", None)
            foundup_id, source = _resolve_foundup_scope(mock_holo, None)
            assert foundup_id is None
            assert source == "none"

    def test_explicit_none_does_not_fallback(self, mock_holo_with_context):
        """Explicit None still resolves to context (None means 'not provided')."""
        # Note: Python can't distinguish between f(x=None) and f() without sentinels
        # Our API uses None as "not provided", so context applies
        foundup_id, source = _resolve_foundup_scope(mock_holo_with_context, None)
        assert foundup_id == "context_foundup"
        assert source == "context"


# =============================================================================
# Execute Search Metadata Tests
# =============================================================================


class TestExecuteSearchScopeMetadata:
    """Test that execute_search() includes scope resolution in metadata."""

    @pytest.fixture
    def mock_holo(self):
        """Create a mock HoloIndex instance."""
        holo = MagicMock()
        holo.code_collection = None
        holo.symbol_collection = None
        holo.wsp_collection = None
        holo.test_collection = None
        holo.skill_collection = None
        holo.docs_collection = None
        holo.knowledge_collection = None
        holo.search_cache = None
        holo.retrieval_mode = "semantic"
        holo.embedding_backend = "sentence_transformers"
        holo.routing_active = False
        holo.collection_backend_map = {}
        holo._foundup_context = None
        holo._log_agent_action = MagicMock()
        return holo

    def test_explicit_scope_metadata(self, mock_holo):
        """Explicit foundup_id shows in metadata with 'explicit' source."""
        result = execute_search(mock_holo, "test query", limit=5, foundup_id="trade")
        meta = result["metadata"]
        assert meta["foundup_id"] == "trade"
        assert meta["effective_foundup_id"] == "trade"
        assert meta["scope_source"] == "explicit"

    def test_context_scope_metadata(self, mock_holo):
        """Context-bound scope shows with 'context' source."""
        mock_holo._foundup_context = "kosei"
        result = execute_search(mock_holo, "test query", limit=5)
        meta = result["metadata"]
        assert meta["foundup_id"] is None  # Original arg
        assert meta["effective_foundup_id"] == "kosei"
        assert meta["scope_source"] == "context"

    def test_env_scope_metadata(self, mock_holo):
        """Environment scope shows with 'env' source."""
        with patch.dict(os.environ, {"HOLO_FOUNDUP_ID": "gotjunk_001"}):
            result = execute_search(mock_holo, "test query", limit=5)
            meta = result["metadata"]
            assert meta["foundup_id"] is None
            assert meta["effective_foundup_id"] == "gotjunk_001"
            assert meta["scope_source"] == "env"

    def test_no_scope_metadata(self, mock_holo):
        """No scope shows None with 'none' source."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("HOLO_FOUNDUP_ID", None)
            result = execute_search(mock_holo, "test query", limit=5)
            meta = result["metadata"]
            assert meta["foundup_id"] is None
            assert meta["effective_foundup_id"] is None
            assert meta["scope_source"] == "none"

    def test_explicit_overrides_context_in_metadata(self, mock_holo):
        """Explicit arg overrides context in effective scope."""
        mock_holo._foundup_context = "context_value"
        result = execute_search(mock_holo, "test query", limit=5, foundup_id="explicit_value")
        meta = result["metadata"]
        assert meta["foundup_id"] == "explicit_value"
        assert meta["effective_foundup_id"] == "explicit_value"
        assert meta["scope_source"] == "explicit"


# =============================================================================
# HoloIndex Context Binding API Tests
# =============================================================================


class TestHoloIndexContextAPI:
    """Test HoloIndex context binding methods."""

    def test_set_and_get_context(self):
        """set_foundup_context() and get_foundup_context() work correctly."""
        holo = MagicMock()
        holo._foundup_context = None
        holo._log_agent_action = MagicMock()

        # Import and bind the methods
        from holo_index.core.holo_index import HoloIndex

        # Test set
        HoloIndex.set_foundup_context(holo, "trade")
        assert holo._foundup_context == "trade"

        # Test get
        result = HoloIndex.get_foundup_context(holo)
        assert result == "trade"

    def test_clear_context(self):
        """clear_foundup_context() resets to None."""
        holo = MagicMock()
        holo._foundup_context = "some_context"
        holo._log_agent_action = MagicMock()

        from holo_index.core.holo_index import HoloIndex

        HoloIndex.clear_foundup_context(holo)
        assert holo._foundup_context is None

    def test_get_context_when_none(self):
        """get_foundup_context() returns None when not set."""
        holo = MagicMock()
        holo._foundup_context = None

        from holo_index.core.holo_index import HoloIndex

        result = HoloIndex.get_foundup_context(holo)
        assert result is None


# =============================================================================
# Precedence Integration Tests
# =============================================================================


class TestPrecedenceIntegration:
    """Integration tests verifying full precedence chain."""

    @pytest.fixture
    def mock_holo(self):
        """Create a mock HoloIndex with all search infrastructure."""
        holo = MagicMock()
        holo.code_collection = None
        holo.symbol_collection = None
        holo.wsp_collection = None
        holo.test_collection = None
        holo.skill_collection = None
        holo.docs_collection = None
        holo.knowledge_collection = None
        holo.search_cache = None
        holo.retrieval_mode = "semantic"
        holo.embedding_backend = "sentence_transformers"
        holo.routing_active = False
        holo.collection_backend_map = {}
        holo._foundup_context = None
        holo._log_agent_action = MagicMock()
        return holo

    def test_full_precedence_chain(self, mock_holo):
        """Test all four precedence levels in order."""
        with patch.dict(os.environ, {"HOLO_FOUNDUP_ID": "env_level"}):
            # Level 4: No scope
            mock_holo._foundup_context = None
            os.environ.pop("HOLO_FOUNDUP_ID", None)
            result = execute_search(mock_holo, "test", limit=1)
            assert result["metadata"]["scope_source"] == "none"

            # Level 3: Environment
            os.environ["HOLO_FOUNDUP_ID"] = "env_level"
            result = execute_search(mock_holo, "test", limit=1)
            assert result["metadata"]["effective_foundup_id"] == "env_level"
            assert result["metadata"]["scope_source"] == "env"

            # Level 2: Context
            mock_holo._foundup_context = "context_level"
            result = execute_search(mock_holo, "test", limit=1)
            assert result["metadata"]["effective_foundup_id"] == "context_level"
            assert result["metadata"]["scope_source"] == "context"

            # Level 1: Explicit
            result = execute_search(mock_holo, "test", limit=1, foundup_id="explicit_level")
            assert result["metadata"]["effective_foundup_id"] == "explicit_level"
            assert result["metadata"]["scope_source"] == "explicit"


# =============================================================================
# Backward Compatibility Tests
# =============================================================================


class TestBackwardCompatibility:
    """Test that existing callers work unchanged."""

    @pytest.fixture
    def mock_holo(self):
        """Create a mock HoloIndex."""
        holo = MagicMock()
        holo.code_collection = None
        holo.symbol_collection = None
        holo.wsp_collection = None
        holo.test_collection = None
        holo.skill_collection = None
        holo.docs_collection = None
        holo.knowledge_collection = None
        holo.search_cache = None
        holo.retrieval_mode = "semantic"
        holo.embedding_backend = "sentence_transformers"
        holo.routing_active = False
        holo.collection_backend_map = {}
        holo._foundup_context = None
        holo._log_agent_action = MagicMock()
        return holo

    def test_old_signature_works(self, mock_holo):
        """Old callers with just (query, limit, doc_type_filter) still work."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("HOLO_FOUNDUP_ID", None)
            result = execute_search(mock_holo, "test query", 5, "all")
            assert "metadata" in result
            assert result["metadata"]["effective_foundup_id"] is None
            assert result["metadata"]["scope_source"] == "none"

    def test_phase3_explicit_still_works(self, mock_holo):
        """Phase 3 callers using explicit foundup_id still work."""
        result = execute_search(mock_holo, "test", limit=5, foundup_id="trade", include_shared=False)
        meta = result["metadata"]
        assert meta["foundup_id"] == "trade"
        assert meta["include_shared"] is False
        assert meta["effective_foundup_id"] == "trade"
        assert meta["scope_source"] == "explicit"

    def test_result_structure_includes_new_fields(self, mock_holo):
        """Result structure includes new Phase 4 metadata fields."""
        result = execute_search(mock_holo, "test query")
        meta = result["metadata"]
        # All expected keys present
        assert "foundup_id" in meta  # Phase 3
        assert "include_shared" in meta  # Phase 3
        assert "effective_foundup_id" in meta  # Phase 4
        assert "scope_source" in meta  # Phase 4
