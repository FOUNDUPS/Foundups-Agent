# -*- coding: utf-8 -*-
"""
Tests for turboquant_backend.py - TurboQuant Stub Tests

Tests run in HOLO_SKIP_MODEL=1 mode (no model dependencies).

WSP Compliance:
    WSP 5: Test Coverage
    WSP 97: Truth Distinction
"""
import pytest

from holo_index.core.turboquant_backend import (
    EMBEDDING_DIM,
    TurboQuantEmbedder,
)


class TestTurboQuantConstants:
    """Tests for module constants"""

    def test_embedding_dim_is_384(self):
        """Embedding dimension matches ChromaDB-stored vectors"""
        assert EMBEDDING_DIM == 384


class TestTurboQuantEmbedder:
    """Tests for TurboQuantEmbedder stub class"""

    def test_turboquant_marker_exists(self):
        """Class has _turboquant_marker for duck-typing"""
        assert hasattr(TurboQuantEmbedder, "_turboquant_marker")
        assert TurboQuantEmbedder._turboquant_marker is True

    def test_is_available_returns_false(self):
        """Stub always reports unavailable"""
        assert TurboQuantEmbedder.is_available() is False

    def test_encode_raises_not_implemented(self):
        """Encode raises NotImplementedError for stub"""
        embedder = TurboQuantEmbedder()
        with pytest.raises(NotImplementedError) as exc_info:
            embedder.encode("test text")

        assert "TurboQuant backend not yet implemented" in str(exc_info.value)

    def test_encode_accepts_show_progress_bar(self):
        """Encode method accepts show_progress_bar parameter"""
        embedder = TurboQuantEmbedder()
        with pytest.raises(NotImplementedError):
            embedder.encode("test", show_progress_bar=True)

    def test_instance_creation(self):
        """Can create TurboQuantEmbedder instance"""
        embedder = TurboQuantEmbedder()
        assert embedder is not None
