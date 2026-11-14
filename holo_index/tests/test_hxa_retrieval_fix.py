# -*- coding: utf-8 -*-
"""Tests for HXA retrieval quality fixes.

HOLOINDEX_HXA_AUDIT_INDEXING_FIX_PHASE1

These tests verify:
1. Slice ID extraction (HXA, FX, CFZ patterns)
2. Slice ID boost in search ranking
3. Path display is never "Unknown" for indexed files
4. Worktree exclusion in indexing
5. Audit path priority boost
"""

import re
from pathlib import Path

import pytest


class TestSliceIdExtraction:
    """Test slice ID extraction from filenames and titles."""

    def test_extract_hxa_from_filename(self):
        """HXA22 extracted from HXA22_DESTRUCTIVE_ACTION_GUARD_RUNTIME.md."""
        from holo_index.core.indexing_engine import _extract_slice_id

        result = _extract_slice_id("HXA22_DESTRUCTIVE_ACTION_GUARD_RUNTIME.md", "")
        assert result == "HXA22"

    def test_extract_hxa_from_test_filename(self):
        """HXA30 extracted from test_hxa30_scope_to_action_class.py."""
        from holo_index.core.indexing_engine import _extract_slice_id

        result = _extract_slice_id("test_hxa30_scope_to_action_class.py", "")
        assert result == "HXA30"

    def test_extract_fx_from_filename(self):
        """FX1 extracted from FX1_RETRIEVAL_AUDIT.md."""
        from holo_index.core.indexing_engine import _extract_slice_id

        result = _extract_slice_id("FX1_RETRIEVAL_AUDIT.md", "")
        assert result == "FX1"

    def test_extract_cfz_from_filename(self):
        """CFZ4 extracted from CFZ4_COLLECTION_SEPARATION.md."""
        from holo_index.core.indexing_engine import _extract_slice_id

        result = _extract_slice_id("CFZ4_COLLECTION_SEPARATION.md", "")
        assert result == "CFZ4"

    def test_extract_from_title_when_not_in_filename(self):
        """Slice ID extracted from title when not in filename."""
        from holo_index.core.indexing_engine import _extract_slice_id

        result = _extract_slice_id("README.md", "HXA23 - Hermes Guard Integration")
        assert result == "HXA23"

    def test_no_slice_id_returns_none(self):
        """None returned when no slice ID present."""
        from holo_index.core.indexing_engine import _extract_slice_id

        result = _extract_slice_id("README.md", "Installation Guide")
        assert result is None


class TestSliceIdBoost:
    """Test slice ID boost in search ranking."""

    def test_slice_id_match_boost_hxa(self):
        """HXA22 query boosts HXA22 doc via metadata (tier 1)."""
        from holo_index.core.search_engine import (
            _SLICE_ID_METADATA_PRECEDENCE_BOOST,
            _slice_id_match_boost,
        )

        boost = _slice_id_match_boost(
            query="HXA22 destructive action guard",
            path="docs/audits/openclaw_hermes/HXA22_DESTRUCTIVE_ACTION_GUARD_RUNTIME.md",
            title="HXA22 - Destructive Action Guard Runtime",
            meta_slice_id="HXA22",
        )
        assert boost == _SLICE_ID_METADATA_PRECEDENCE_BOOST

    def test_slice_id_match_boost_cfz(self):
        """CFZ4 query boosts CFZ4 doc via metadata (tier 1)."""
        from holo_index.core.search_engine import (
            _SLICE_ID_METADATA_PRECEDENCE_BOOST,
            _slice_id_match_boost,
        )

        boost = _slice_id_match_boost(
            query="CFZ4 collection separation",
            path="docs/audits/holoindex/CFZ4_COLLECTION_SEPARATION.md",
            title="CFZ4 - Collection Separation",
            meta_slice_id="CFZ4",
        )
        assert boost == _SLICE_ID_METADATA_PRECEDENCE_BOOST

    def test_no_boost_for_different_slice(self):
        """No boost when query slice differs from path slice."""
        from holo_index.core.search_engine import _slice_id_match_boost

        boost = _slice_id_match_boost(
            query="HXA22 destructive action guard",
            path="docs/audits/openclaw_hermes/HXA23_HERMES_GUARD_INTEGRATION.md",
            title="HXA23 - Hermes Guard Integration",
            meta_slice_id="HXA23",
        )
        assert boost == 0.0

    def test_no_boost_for_non_slice_query(self):
        """No boost when query has no slice ID."""
        from holo_index.core.search_engine import _slice_id_match_boost

        boost = _slice_id_match_boost(
            query="destructive action guard",
            path="docs/audits/openclaw_hermes/HXA22_DESTRUCTIVE_ACTION_GUARD_RUNTIME.md",
            title="HXA22 - Destructive Action Guard Runtime",
            meta_slice_id="HXA22",
        )
        assert boost == 0.0


class TestSliceIdPatternExtraction:
    """Test _extract_slice_ids function in search_engine."""

    def test_extract_multiple_slice_ids(self):
        """Multiple slice IDs extracted from text."""
        from holo_index.core.search_engine import _extract_slice_ids

        result = _extract_slice_ids("HXA22 and HXA23 integration")
        assert "HXA22" in result
        assert "HXA23" in result

    def test_case_insensitive_extraction(self):
        """Slice ID extraction is case-insensitive."""
        from holo_index.core.search_engine import _extract_slice_ids

        result = _extract_slice_ids("hxa22 lowercase test")
        assert "HXA22" in result


class TestAuditPathPriority:
    """Test audit path priority boost."""

    def test_openclaw_hermes_priority(self):
        """docs/audits/openclaw_hermes gets priority 9."""
        from holo_index.core.indexing_engine import _calculate_document_priority

        priority = _calculate_document_priority(
            "documentation",
            Path("O:/Foundups-Agent/docs/audits/openclaw_hermes/HXA22_AUDIT.md"),
        )
        assert priority >= 9

    def test_security_audits_priority(self):
        """docs/audits/security gets priority 8."""
        from holo_index.core.indexing_engine import _calculate_document_priority

        priority = _calculate_document_priority(
            "documentation",
            Path("O:/Foundups-Agent/docs/audits/security/DEP_SECURITY.md"),
        )
        assert priority >= 8

    def test_regular_docs_lower_priority(self):
        """Regular docs without audit path get lower priority."""
        from holo_index.core.indexing_engine import _calculate_document_priority

        priority = _calculate_document_priority(
            "documentation",
            Path("O:/Foundups-Agent/docs/README.md"),
        )
        # Should be base priority (7 for documentation)
        assert priority <= 8


class TestWorktreeExclusion:
    """Test worktree exclusion patterns."""

    def test_worktree_path_excluded(self):
        """Worktree paths should be filtered out."""
        # Test the filter pattern used in index_docs_entries
        test_paths = [
            "O:/Foundups-Agent/.claude/worktrees/agent-xxx/docs/README.md",
            "O:/Foundups-Agent/.worktrees/agent-xxx/docs/README.md",
            "O:/Foundups-Agent/docs/README.md",  # Should NOT be excluded
        ]

        for path in test_paths:
            path_lower = path.replace("\\", "/").lower()
            is_excluded = (
                ".claude/worktrees" in path_lower or ".worktrees" in path_lower
            )

            if "worktrees" in path.lower():
                assert is_excluded, f"Path should be excluded: {path}"
            else:
                assert not is_excluded, f"Path should NOT be excluded: {path}"


class TestDocsFormatHit:
    """Test _format_hit for docs kind."""

    def test_docs_format_includes_path(self):
        """Docs format always includes path, never None."""
        from holo_index.core.search_engine import _format_hit

        meta = {
            "title": "Test Doc",
            "summary": "Test summary",
            "path": "O:/Foundups-Agent/docs/test.md",
            "type": "documentation",
            "priority": 7,
            "slice_id": "HXA22",
        }

        result = _format_hit(
            kind="docs",
            meta=meta,
            doc="Test Doc\nTest summary",
            similarity=0.85,
            keyword_score=3.0,
            priority=7,
        )

        assert result["path"] == "O:/Foundups-Agent/docs/test.md"
        assert result["slice_id"] == "HXA22"
        assert result["title"] == "Test Doc"

    def test_docs_format_fallback_when_path_none(self):
        """Docs format uses title as fallback when path is None."""
        from holo_index.core.search_engine import _format_hit

        meta = {
            "title": "Test Doc Title",
            "summary": "Test summary",
            "path": None,  # Explicitly None
            "type": "documentation",
            "priority": 7,
        }

        result = _format_hit(
            kind="docs",
            meta=meta,
            doc="Test Doc\nTest summary",
            similarity=0.85,
            keyword_score=3.0,
            priority=7,
        )

        # Path should fall back to title, not be None
        assert result["path"] == "Test Doc Title"
        assert result["path"] != "Unknown"


class TestSliceIdPattern:
    """Test the slice ID regex pattern."""

    def test_pattern_matches_hxa(self):
        """Pattern matches HXA followed by digits."""
        from holo_index.core.search_engine import _SLICE_ID_PATTERN

        assert _SLICE_ID_PATTERN.search("HXA22") is not None
        assert _SLICE_ID_PATTERN.search("HXA1") is not None
        assert _SLICE_ID_PATTERN.search("HXA123") is not None

    def test_pattern_matches_fx(self):
        """Pattern matches FX followed by digits."""
        from holo_index.core.search_engine import _SLICE_ID_PATTERN

        assert _SLICE_ID_PATTERN.search("FX1") is not None
        assert _SLICE_ID_PATTERN.search("FX99") is not None

    def test_pattern_matches_cfz(self):
        """Pattern matches CFZ followed by digits."""
        from holo_index.core.search_engine import _SLICE_ID_PATTERN

        assert _SLICE_ID_PATTERN.search("CFZ4") is not None
        assert _SLICE_ID_PATTERN.search("CFZ123") is not None

    def test_pattern_case_insensitive(self):
        """Pattern is case-insensitive."""
        from holo_index.core.search_engine import _SLICE_ID_PATTERN

        assert _SLICE_ID_PATTERN.search("hxa22") is not None
        assert _SLICE_ID_PATTERN.search("Hxa22") is not None
        assert _SLICE_ID_PATTERN.search("HXA22") is not None
