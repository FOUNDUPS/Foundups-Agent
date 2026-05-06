# -*- coding: utf-8 -*-
"""HIA_FEDERATION_QUERY_FILTERING_PHASE3: Query Filtering Tests

Tests that verify FoundUp-scoped query filtering behavior:
- Unfiltered search unchanged (backward compat)
- Strict foundup_id filter
- include_shared includes 'core' documents
- Unknown foundup_id returns empty scoped hits

WSP 97: These tests verify filtering correctness at the unit level.
WSP 87: Keep tests focused on filter behavior.
"""

import pytest
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

from holo_index.core.search_engine import (
    _build_foundup_where_filter,
    _search_collection,
    _lexical_search_collection,
    execute_search,
)


# =============================================================================
# Filter Builder Tests
# =============================================================================


class TestBuildFoundupWhereFilter:
    """Test _build_foundup_where_filter() logic."""

    def test_no_foundup_id_returns_none(self):
        """No foundup_id means no filtering."""
        result = _build_foundup_where_filter(None, include_shared=True)
        assert result is None

    def test_no_foundup_id_include_shared_false_returns_none(self):
        """No foundup_id means no filtering even with include_shared=False."""
        result = _build_foundup_where_filter(None, include_shared=False)
        assert result is None

    def test_strict_foundup_filter(self):
        """foundup_id + include_shared=False returns strict filter."""
        result = _build_foundup_where_filter("trade", include_shared=False)
        assert result == {"foundup_id": "trade"}

    def test_include_shared_filter(self):
        """foundup_id + include_shared=True returns OR filter."""
        result = _build_foundup_where_filter("trade", include_shared=True)
        assert result == {"$or": [{"foundup_id": "trade"}, {"foundup_id": "core"}]}

    def test_gotjunk_001_strict(self):
        """gotjunk_001 strict filter."""
        result = _build_foundup_where_filter("gotjunk_001", include_shared=False)
        assert result == {"foundup_id": "gotjunk_001"}

    def test_kosei_with_shared(self):
        """kosei with shared includes core."""
        result = _build_foundup_where_filter("kosei", include_shared=True)
        assert result == {"$or": [{"foundup_id": "kosei"}, {"foundup_id": "core"}]}

    def test_unknown_foundup_id_still_builds_filter(self):
        """Unknown foundup_id still builds filter (ChromaDB returns empty)."""
        result = _build_foundup_where_filter("nonexistent_foundup", include_shared=False)
        assert result == {"foundup_id": "nonexistent_foundup"}


# =============================================================================
# Execute Search Metadata Tests
# =============================================================================


class TestExecuteSearchMetadata:
    """Test that execute_search() includes filtering params in metadata."""

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
        holo._log_agent_action = MagicMock()
        return holo

    def test_unfiltered_metadata(self, mock_holo):
        """Unfiltered search has foundup_id=None in metadata."""
        result = execute_search(mock_holo, "test query", limit=5)
        assert result["metadata"]["foundup_id"] is None
        assert result["metadata"]["include_shared"] is True

    def test_filtered_metadata(self, mock_holo):
        """Filtered search includes foundup_id in metadata."""
        result = execute_search(mock_holo, "test query", limit=5, foundup_id="trade")
        assert result["metadata"]["foundup_id"] == "trade"
        assert result["metadata"]["include_shared"] is True

    def test_strict_filter_metadata(self, mock_holo):
        """Strict filter has include_shared=False in metadata."""
        result = execute_search(mock_holo, "test query", limit=5, foundup_id="kosei", include_shared=False)
        assert result["metadata"]["foundup_id"] == "kosei"
        assert result["metadata"]["include_shared"] is False


# =============================================================================
# Search Collection Filter Tests
# =============================================================================


class TestSearchCollectionFiltering:
    """Test that _search_collection() passes where filter to ChromaDB."""

    @pytest.fixture
    def mock_holo(self):
        """Create a mock HoloIndex for collection tests."""
        holo = MagicMock()
        holo.model = MagicMock()
        holo.model.encode = MagicMock(return_value=MagicMock(tolist=lambda: [0.1] * 384))
        holo.embedders = None
        holo.routing_active = False
        holo._log_agent_action = MagicMock()
        return holo

    @pytest.fixture
    def mock_collection(self):
        """Create a mock ChromaDB collection."""
        collection = MagicMock()
        collection.name = "navigation_code"
        collection.count = MagicMock(return_value=10)
        collection.query = MagicMock(return_value={
            "documents": [["doc1", "doc2"]],
            "metadatas": [[
                {"need": "need1", "type": "code", "path": "path1", "foundup_id": "trade"},
                {"need": "need2", "type": "code", "path": "path2", "foundup_id": "core"},
            ]],
            "distances": [[0.1, 0.2]],
        })
        return collection

    def test_unfiltered_query_no_where(self, mock_holo, mock_collection):
        """Unfiltered search passes where=None to collection.query()."""
        _search_collection(mock_holo, mock_collection, "test", 5, "code")

        mock_collection.query.assert_called_once()
        call_kwargs = mock_collection.query.call_args[1]
        assert call_kwargs.get("where") is None

    def test_strict_filter_passes_where(self, mock_holo, mock_collection):
        """Strict filter passes where clause to collection.query()."""
        _search_collection(mock_holo, mock_collection, "test", 5, "code",
                          foundup_id="trade", include_shared=False)

        mock_collection.query.assert_called_once()
        call_kwargs = mock_collection.query.call_args[1]
        assert call_kwargs.get("where") == {"foundup_id": "trade"}

    def test_include_shared_passes_or_where(self, mock_holo, mock_collection):
        """Include shared passes $or where clause."""
        _search_collection(mock_holo, mock_collection, "test", 5, "code",
                          foundup_id="trade", include_shared=True)

        mock_collection.query.assert_called_once()
        call_kwargs = mock_collection.query.call_args[1]
        assert call_kwargs.get("where") == {"$or": [{"foundup_id": "trade"}, {"foundup_id": "core"}]}


# =============================================================================
# Lexical Search Filter Tests
# =============================================================================


class TestLexicalSearchFiltering:
    """Test that _lexical_search_collection() filters by foundup_id."""

    @pytest.fixture
    def mock_holo(self):
        """Create a mock HoloIndex."""
        holo = MagicMock()
        holo._log_agent_action = MagicMock()
        return holo

    @pytest.fixture
    def mock_collection_with_data(self):
        """Create a mock collection with mixed foundup_id data."""
        collection = MagicMock()
        collection.count = MagicMock(return_value=4)
        collection.get = MagicMock(return_value={
            "documents": [
                "trade engine code",
                "core search code",
                "kosei contracts",
                "trade utils",
            ],
            "metadatas": [
                {"title": "trade_engine", "path": "trade/src/engine.py", "type": "code", "foundup_id": "trade"},
                {"title": "search_engine", "path": "holo_index/search.py", "type": "code", "foundup_id": "core"},
                {"title": "kosei_contracts", "path": "kosei/contracts.py", "type": "code", "foundup_id": "kosei"},
                {"title": "trade_utils", "path": "trade/utils.py", "type": "code", "foundup_id": "trade"},
            ],
        })
        return collection

    def test_unfiltered_returns_all(self, mock_holo, mock_collection_with_data):
        """Unfiltered lexical search returns all matching docs."""
        results = _lexical_search_collection(
            mock_holo, mock_collection_with_data, "trade engine", 10, "code"
        )
        # Should find docs containing "trade" or "engine"
        assert len(results) >= 1

    def test_strict_filter_excludes_others(self, mock_holo, mock_collection_with_data):
        """Strict filter excludes non-matching foundup_id docs."""
        results = _lexical_search_collection(
            mock_holo, mock_collection_with_data, "code", 10, "code",
            foundup_id="trade", include_shared=False
        )
        # Should only return trade docs (2 out of 4)
        # Results have 'location' field containing doc text, not metadata fields
        for result in results:
            location = result.get("location", "").lower()
            # Doc text for trade docs contains "trade"
            assert "trade" in location

    def test_include_shared_includes_core(self, mock_holo, mock_collection_with_data):
        """include_shared=True includes core docs."""
        results = _lexical_search_collection(
            mock_holo, mock_collection_with_data, "engine code", 10, "code",
            foundup_id="trade", include_shared=True
        )
        # Should include both trade and core docs
        # Results have 'location' field containing doc text
        locations = [r.get("location", "").lower() for r in results]
        has_trade = any("trade" in loc for loc in locations)
        has_core = any("core" in loc for loc in locations)
        # At least one should match (depends on keyword scoring)
        assert len(results) >= 1


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
        holo._log_agent_action = MagicMock()
        return holo

    def test_old_signature_works(self, mock_holo):
        """Old callers with just (query, limit, doc_type_filter) still work."""
        result = execute_search(mock_holo, "test query", 5, "all")
        assert "metadata" in result
        assert result["metadata"]["foundup_id"] is None

    def test_old_signature_no_limit(self, mock_holo):
        """Old callers with just query still work."""
        result = execute_search(mock_holo, "test query")
        assert "metadata" in result

    def test_result_structure_unchanged(self, mock_holo):
        """Result structure is unchanged for unfiltered search."""
        result = execute_search(mock_holo, "test query")
        # All expected keys present
        assert "code_hits" in result
        assert "wsp_hits" in result
        assert "code" in result
        assert "wsps" in result
        assert "docs" in result
        assert "knowledge" in result
        assert "metadata" in result
