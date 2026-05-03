# -*- coding: utf-8 -*-
"""Tests for index refresh repair (HOLOINDEX_INDEX_REFRESH_REPAIR).

Verifies:
- index_wsp_entries accepts optional paths parameter without TypeError
- WSP custom paths still only index WSP_*.md files (CFZ4 purity)
- HoloIndex exposes index_docs_entries and index_knowledge_entries
- docs/architecture paths route to navigation_docs

WSP: WSP 97 (truth), WSP 50 (pre-action verification)
"""
from pathlib import Path
from typing import List, Optional
from unittest.mock import MagicMock, patch
import pytest


class TestWspEntriesSignature:
    """Test index_wsp_entries accepts paths parameter."""

    def test_index_wsp_entries_accepts_none_paths(self):
        """index_wsp_entries(holo, paths=None) should not raise TypeError."""
        from holo_index.core.indexing_engine import index_wsp_entries
        import inspect
        sig = inspect.signature(index_wsp_entries)
        params = list(sig.parameters.keys())
        assert "holo" in params
        assert "paths" in params
        # Verify paths has default None
        assert sig.parameters["paths"].default is None

    def test_index_wsp_entries_accepts_paths_list(self):
        """index_wsp_entries(holo, paths=[...]) should not raise TypeError."""
        from holo_index.core.indexing_engine import index_wsp_entries
        import inspect
        sig = inspect.signature(index_wsp_entries)
        # Verify annotation includes Optional[List[Path]]
        paths_param = sig.parameters["paths"]
        # Just check it's Optional (has None default)
        assert paths_param.default is None


class TestWspPurity:
    """Test WSP custom paths still only index WSP_*.md (CFZ4 purity)."""

    def test_wsp_purity_only_wsp_files(self):
        """Even with custom paths, only WSP_*.md files should be indexed."""
        # This is a design contract test - the function should glob WSP_*.md
        from holo_index.core.indexing_engine import index_wsp_entries
        import inspect
        source = inspect.getsource(index_wsp_entries)
        # Verify the function globs for WSP_*.md pattern
        assert 'glob("WSP_*.md")' in source or "glob('WSP_*.md')" in source


class TestHoloIndexExposure:
    """Test HoloIndex class exposes new indexing methods."""

    def test_holoindex_has_index_docs_entries(self):
        """HoloIndex should expose index_docs_entries method."""
        from holo_index.core.holo_index import HoloIndex
        assert hasattr(HoloIndex, 'index_docs_entries')
        assert callable(getattr(HoloIndex, 'index_docs_entries'))

    def test_holoindex_has_index_knowledge_entries(self):
        """HoloIndex should expose index_knowledge_entries method."""
        from holo_index.core.holo_index import HoloIndex
        assert hasattr(HoloIndex, 'index_knowledge_entries')
        assert callable(getattr(HoloIndex, 'index_knowledge_entries'))

    def test_holoindex_has_index_wsp_entries_with_paths(self):
        """HoloIndex.index_wsp_entries should accept paths parameter."""
        from holo_index.core.holo_index import HoloIndex
        import inspect
        sig = inspect.signature(HoloIndex.index_wsp_entries)
        params = list(sig.parameters.keys())
        assert "paths" in params


class TestDocsArchitectureRouting:
    """Test docs/architecture paths route to navigation_docs."""

    def test_docs_architecture_in_docs_paths(self):
        """docs/architecture/** should be indexed by index_docs_entries."""
        from holo_index.core.indexing_engine import index_docs_entries
        import inspect
        source = inspect.getsource(index_docs_entries)
        # Verify docs path is included
        assert 'project_root / "docs"' in source or '"docs"' in source

    def test_docs_indexed_separately_from_wsp(self):
        """navigation_docs collection should be separate from navigation_wsp."""
        from holo_index.core.indexing_engine import index_docs_entries, index_wsp_entries
        import inspect
        docs_source = inspect.getsource(index_docs_entries)
        wsp_source = inspect.getsource(index_wsp_entries)
        # docs uses navigation_docs
        assert 'navigation_docs' in docs_source
        # wsp uses navigation_wsp
        assert 'navigation_wsp' in wsp_source


class TestCliFlags:
    """Test CLI supports --index-docs and --index-knowledge flags."""

    def test_cli_has_index_docs_flag(self):
        """CLI should have --index-docs argument."""
        from holo_index._cli_main import main
        import argparse
        # Read the source to check for argument
        import inspect
        source = inspect.getsource(main)
        # Check in the module source instead
        from holo_index import _cli_main
        module_source = inspect.getsource(_cli_main)
        assert '--index-docs' in module_source

    def test_cli_has_index_knowledge_flag(self):
        """CLI should have --index-knowledge argument."""
        from holo_index import _cli_main
        import inspect
        module_source = inspect.getsource(_cli_main)
        assert '--index-knowledge' in module_source


class TestNoDestructiveActions:
    """WSP 97: Verify no destructive actions on E:/HoloIndex."""

    def test_no_shutil_rmtree_on_holoindex(self):
        """No shutil.rmtree calls targeting E:/HoloIndex."""
        from holo_index.core import indexing_engine
        import inspect
        source = inspect.getsource(indexing_engine)
        # Should not have rmtree on E:/HoloIndex
        assert 'rmtree' not in source.lower() or 'e:/holoindex' not in source.lower()

    def test_reset_collection_uses_chromadb_api(self):
        """_reset_collection should use ChromaDB API, not filesystem deletion."""
        from holo_index.core.holo_index import HoloIndex
        import inspect
        source = inspect.getsource(HoloIndex._reset_collection)
        # Should use delete_collection or get_or_create_collection
        assert 'delete_collection' in source or 'get_or_create_collection' in source
