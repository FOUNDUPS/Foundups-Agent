# -*- coding: utf-8 -*-
"""
Tests for comment_search.py - Comment Search API Tests

Tests run in HOLO_SKIP_MODEL=1 mode using mocks.

WSP Compliance:
    WSP 5: Test Coverage
    WSP 84: Code Reuse
"""
import sys
from unittest.mock import MagicMock, patch

from holo_index.core.comment_search import (
    search_comments,
    index_comments,
    get_comment_index_stats,
)


class TestSearchComments:
    """Tests for search_comments function"""

    def test_search_returns_formatted_results(self):
        """search_comments returns standardized result format"""
        mock_vm = MagicMock()
        mock_vm.query.return_value = [
            {
                "text": "Test comment",
                "source_id": "vid123",
                "source_type": "comment",
                "score": 0.95,
                "video_id": "vid123",
                "timestamp": "2024-01-01",
                "url": "https://youtube.com/watch?v=vid123",
            }
        ]

        mock_module = MagicMock()
        mock_module.VoiceMemory.return_value = mock_vm

        with patch.dict(sys.modules, {"modules.ai_intelligence.digital_twin.src.voice_memory": mock_module}):
            results = search_comments("test query", k=5)

        assert len(results) == 1
        assert results[0]["text"] == "Test comment"
        assert results[0]["source_id"] == "vid123"
        assert results[0]["score"] == 0.95

    def test_search_handles_missing_fields(self):
        """search_comments handles results with missing fields"""
        mock_vm = MagicMock()
        mock_vm.query.return_value = [
            {"text": "Minimal result"}  # Missing most fields
        ]

        mock_module = MagicMock()
        mock_module.VoiceMemory.return_value = mock_vm

        with patch.dict(sys.modules, {"modules.ai_intelligence.digital_twin.src.voice_memory": mock_module}):
            results = search_comments("query")

        assert len(results) == 1
        assert results[0]["text"] == "Minimal result"
        assert results[0]["source_id"] == ""
        assert results[0]["source_type"] == "comment"
        assert results[0]["score"] == 0.0

    def test_search_passes_index_dir(self):
        """search_comments passes index_dir to VoiceMemory"""
        mock_vm = MagicMock()
        mock_vm.query.return_value = []

        mock_module = MagicMock()
        mock_module.VoiceMemory.return_value = mock_vm

        with patch.dict(sys.modules, {"modules.ai_intelligence.digital_twin.src.voice_memory": mock_module}):
            search_comments("query", index_dir="/custom/path")
            mock_module.VoiceMemory.assert_called_once_with(index_dir="/custom/path")

    def test_search_returns_empty_on_import_error(self):
        """search_comments returns empty list on ImportError"""
        # Create a mock module that raises ImportError when VoiceMemory is accessed
        mock_module = MagicMock()
        mock_module.VoiceMemory = property(lambda self: (_ for _ in ()).throw(ImportError("No module")))

        # A module that raises on any attribute access
        class FailingModule:
            def __getattr__(self, name):
                raise ImportError(f"Module not found: {name}")

        with patch.dict(sys.modules, {"modules.ai_intelligence.digital_twin.src.voice_memory": FailingModule()}):
            results = search_comments("query")
            assert results == []

    def test_search_returns_empty_on_exception(self):
        """search_comments returns empty list on query exception"""
        mock_vm = MagicMock()
        mock_vm.query.side_effect = Exception("Database error")

        mock_module = MagicMock()
        mock_module.VoiceMemory.return_value = mock_vm

        with patch.dict(sys.modules, {"modules.ai_intelligence.digital_twin.src.voice_memory": mock_module}):
            results = search_comments("query")
            assert results == []

    def test_search_default_k_value(self):
        """search_comments uses default k=5"""
        mock_vm = MagicMock()
        mock_vm.query.return_value = []

        mock_module = MagicMock()
        mock_module.VoiceMemory.return_value = mock_vm

        with patch.dict(sys.modules, {"modules.ai_intelligence.digital_twin.src.voice_memory": mock_module}):
            search_comments("query")
            mock_vm.query.assert_called_once_with("query", k=5)


class TestIndexComments:
    """Tests for index_comments function"""

    def test_index_returns_document_count(self):
        """index_comments returns number of indexed documents"""
        mock_vm = MagicMock()
        mock_vm.build_index.return_value = 42

        mock_module = MagicMock()
        mock_module.VoiceMemory.return_value = mock_vm

        with patch.dict(sys.modules, {"modules.ai_intelligence.digital_twin.src.voice_memory": mock_module}):
            count = index_comments("/corpus/dir", "/index/dir")
            assert count == 42
            mock_vm.build_index.assert_called_once_with("/corpus/dir", "/index/dir")

    def test_index_returns_zero_on_exception(self):
        """index_comments returns 0 on exception"""
        mock_module = MagicMock()
        mock_module.VoiceMemory.side_effect = Exception("Index error")

        with patch.dict(sys.modules, {"modules.ai_intelligence.digital_twin.src.voice_memory": mock_module}):
            count = index_comments("/corpus", "/index")
            assert count == 0


class TestGetCommentIndexStats:
    """Tests for get_comment_index_stats function"""

    def test_stats_returns_dict(self):
        """get_comment_index_stats returns statistics dict"""
        mock_vm = MagicMock()
        mock_vm.get_stats.return_value = {"count": 100, "size": "1MB"}

        mock_module = MagicMock()
        mock_module.VoiceMemory.return_value = mock_vm

        with patch.dict(sys.modules, {"modules.ai_intelligence.digital_twin.src.voice_memory": mock_module}):
            stats = get_comment_index_stats("/index/dir")
            assert stats["count"] == 100
            assert stats["size"] == "1MB"

    def test_stats_returns_error_dict_on_exception(self):
        """get_comment_index_stats returns error dict on exception"""
        mock_module = MagicMock()
        mock_module.VoiceMemory.side_effect = Exception("Stats error")

        with patch.dict(sys.modules, {"modules.ai_intelligence.digital_twin.src.voice_memory": mock_module}):
            stats = get_comment_index_stats("/index")
            assert "error" in stats
            assert "Stats error" in stats["error"]
