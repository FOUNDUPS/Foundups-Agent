# -*- coding: utf-8 -*-
"""Tests for audit/spec slice ID extraction and search boost.

HOLOINDEX_AUDIT_SPEC_SLICE_ID_INDEXING_FIX_PHASE1

These tests verify:
1. Long-form slice ID extraction from filenames (e.g., FOUNDUPS_PORTFOLIO_DATA_VALIDATOR_PHASE1)
2. Long-form slice ID extraction from titles/H1 headings
3. Slice ID boost for exact matches in search ranking
4. Lexical fallback path honors slice_id boost
5. Existing HXA/FX/CFZ patterns continue to work (no regression)
"""

import pytest
from pathlib import Path


class TestAuditSpecSliceIdExtraction:
    """Test long-form audit/spec slice ID extraction from filenames and titles."""

    def test_extract_audit_spec_from_filename(self):
        """FOUNDUPS_PORTFOLIO_DATA_VALIDATOR_PHASE1 extracted from filename."""
        from holo_index.core.indexing_engine import _extract_slice_id

        result = _extract_slice_id(
            "FOUNDUPS_PORTFOLIO_DATA_VALIDATOR_PHASE1.md", ""
        )
        assert result == "FOUNDUPS_PORTFOLIO_DATA_VALIDATOR_PHASE1"

    def test_extract_long_audit_spec_from_filename(self):
        """Long audit spec ID extracted from filename."""
        from holo_index.core.indexing_engine import _extract_slice_id

        result = _extract_slice_id(
            "FOUNDUPS_AGENT_REDTEAM_HARNESS_PROVENANCE_CHECK_PHASE1.md", ""
        )
        assert result == "FOUNDUPS_AGENT_REDTEAM_HARNESS_PROVENANCE_CHECK_PHASE1"

    def test_extract_holoindex_audit_spec_from_filename(self):
        """HoloIndex audit spec ID extracted from filename."""
        from holo_index.core.indexing_engine import _extract_slice_id

        result = _extract_slice_id(
            "HOLOINDEX_PUBLIC_FOUNDUP_CONNECTIVE_TRUST_SURFACE_DOCS_PHASE1.md", ""
        )
        assert result == "HOLOINDEX_PUBLIC_FOUNDUP_CONNECTIVE_TRUST_SURFACE_DOCS_PHASE1"

    def test_extract_audit_spec_from_title(self):
        """Audit spec ID extracted from title when not in filename."""
        from holo_index.core.indexing_engine import _extract_slice_id

        result = _extract_slice_id(
            "README.md",
            "PORTFOLIO_DATA_VALIDATOR_PHASE1 - Validator Implementation",
        )
        assert result == "PORTFOLIO_DATA_VALIDATOR_PHASE1"

    def test_extract_audit_spec_from_h1_heading(self):
        """Audit spec ID extracted from H1 heading style title."""
        from holo_index.core.indexing_engine import _extract_slice_id

        result = _extract_slice_id(
            "audit.md",
            "# HOLOINDEX_AUDIT_SPEC_SLICE_ID_INDEXING_FIX_PHASE1",
        )
        assert result == "HOLOINDEX_AUDIT_SPEC_SLICE_ID_INDEXING_FIX_PHASE1"

    def test_multi_digit_phase_number(self):
        """Phase numbers with multiple digits are supported."""
        from holo_index.core.indexing_engine import _extract_slice_id

        result = _extract_slice_id("SOME_SLICE_PHASE12.md", "")
        assert result == "SOME_SLICE_PHASE12"

    def test_hxa_still_works_after_extension(self):
        """HXA pattern still works (no regression)."""
        from holo_index.core.indexing_engine import _extract_slice_id

        result = _extract_slice_id("HXA22_DESTRUCTIVE_ACTION_GUARD_RUNTIME.md", "")
        assert result == "HXA22"

    def test_cfz_still_works_after_extension(self):
        """CFZ pattern still works (no regression)."""
        from holo_index.core.indexing_engine import _extract_slice_id

        result = _extract_slice_id("CFZ4_COLLECTION_SEPARATION.md", "")
        assert result == "CFZ4"

    def test_fx_still_works_after_extension(self):
        """FX pattern still works (no regression)."""
        from holo_index.core.indexing_engine import _extract_slice_id

        result = _extract_slice_id("FX1_RETRIEVAL_AUDIT.md", "")
        assert result == "FX1"

    def test_hxa_priority_over_audit_spec(self):
        """HXA pattern takes priority when both could match."""
        from holo_index.core.indexing_engine import _extract_slice_id

        # Filename has HXA pattern - should match HXA first
        result = _extract_slice_id("HXA22_SOME_AUDIT_PHASE1.md", "")
        assert result == "HXA22"

    def test_no_slice_id_returns_none(self):
        """None returned when no slice ID pattern matches."""
        from holo_index.core.indexing_engine import _extract_slice_id

        result = _extract_slice_id("README.md", "Installation Guide")
        assert result is None

    def test_lowercase_not_matched(self):
        """Lowercase audit spec IDs are not matched (must be uppercase)."""
        from holo_index.core.indexing_engine import _extract_slice_id

        result = _extract_slice_id("foundups_portfolio_validator_phase1.md", "")
        assert result is None


class TestAuditSpecSliceIdSearchExtraction:
    """Test _extract_slice_ids function in search_engine for audit spec IDs."""

    def test_extract_audit_spec_from_query(self):
        """Audit spec ID extracted from search query."""
        from holo_index.core.search_engine import _extract_slice_ids

        result = _extract_slice_ids("FOUNDUPS_PORTFOLIO_DATA_VALIDATOR_PHASE1")
        assert "FOUNDUPS_PORTFOLIO_DATA_VALIDATOR_PHASE1" in result

    def test_extract_multiple_audit_spec_ids(self):
        """Multiple audit spec IDs extracted from text."""
        from holo_index.core.search_engine import _extract_slice_ids

        result = _extract_slice_ids(
            "PORTFOLIO_DATA_VALIDATOR_PHASE1 and HOLOINDEX_AUDIT_FIX_PHASE2"
        )
        assert "PORTFOLIO_DATA_VALIDATOR_PHASE1" in result
        assert "HOLOINDEX_AUDIT_FIX_PHASE2" in result

    def test_extract_mixed_slice_id_formats(self):
        """Both HXA and audit spec formats extracted."""
        from holo_index.core.search_engine import _extract_slice_ids

        result = _extract_slice_ids("HXA22 and PORTFOLIO_DATA_VALIDATOR_PHASE1")
        assert "HXA22" in result
        assert "PORTFOLIO_DATA_VALIDATOR_PHASE1" in result

    def test_hxa_still_extracted(self):
        """HXA pattern still extracted (no regression)."""
        from holo_index.core.search_engine import _extract_slice_ids

        result = _extract_slice_ids("HXA22 destructive action guard")
        assert "HXA22" in result

    def test_audit_spec_pattern_object_exists(self):
        """_AUDIT_SPEC_SLICE_ID_PATTERN is defined in search_engine."""
        from holo_index.core.search_engine import _AUDIT_SPEC_SLICE_ID_PATTERN

        assert _AUDIT_SPEC_SLICE_ID_PATTERN is not None
        # Verify pattern matches expected format
        match = _AUDIT_SPEC_SLICE_ID_PATTERN.search("FOUNDUPS_PORTFOLIO_DATA_VALIDATOR_PHASE1")
        assert match is not None
        assert match.group(1) == "FOUNDUPS_PORTFOLIO_DATA_VALIDATOR_PHASE1"


class TestAuditSpecSliceIdBoost:
    """Test slice ID boost for audit spec IDs in search ranking."""

    def test_audit_spec_match_boost(self):
        """Audit spec ID query boosts matching doc via meta_slice_id (tier 1)."""
        from holo_index.core.search_engine import (
            _SLICE_ID_METADATA_PRECEDENCE_BOOST,
            _slice_id_match_boost,
        )

        boost = _slice_id_match_boost(
            query="FOUNDUPS_PORTFOLIO_DATA_VALIDATOR_PHASE1",
            path="docs/audits/architecture/FOUNDUPS_PORTFOLIO_DATA_VALIDATOR_PHASE1.md",
            title="Portfolio Data Validator Phase 1",
            meta_slice_id="FOUNDUPS_PORTFOLIO_DATA_VALIDATOR_PHASE1",
        )
        assert boost == _SLICE_ID_METADATA_PRECEDENCE_BOOST

    def test_audit_spec_match_via_path(self):
        """Boost applied when slice ID is in path even if not in meta (tier 2)."""
        from holo_index.core.search_engine import (
            _SLICE_ID_PATH_OR_TITLE_BOOST,
            _slice_id_match_boost,
        )

        boost = _slice_id_match_boost(
            query="FOUNDUPS_PORTFOLIO_DATA_VALIDATOR_PHASE1",
            path="docs/audits/architecture/FOUNDUPS_PORTFOLIO_DATA_VALIDATOR_PHASE1.md",
            title="Some Title",
            meta_slice_id="",  # No metadata slice_id
        )
        assert boost == _SLICE_ID_PATH_OR_TITLE_BOOST

    def test_audit_spec_match_via_title(self):
        """Boost applied when slice ID is in title (tier 2)."""
        from holo_index.core.search_engine import (
            _SLICE_ID_PATH_OR_TITLE_BOOST,
            _slice_id_match_boost,
        )

        boost = _slice_id_match_boost(
            query="PORTFOLIO_DATA_VALIDATOR_PHASE1",
            path="docs/audits/architecture/audit.md",
            title="PORTFOLIO_DATA_VALIDATOR_PHASE1 - Audit Report",
            meta_slice_id="",
        )
        assert boost == _SLICE_ID_PATH_OR_TITLE_BOOST

    def test_audit_spec_match_via_metadata(self):
        """Boost applied when slice ID is only in metadata (tier 1)."""
        from holo_index.core.search_engine import (
            _SLICE_ID_METADATA_PRECEDENCE_BOOST,
            _slice_id_match_boost,
        )

        boost = _slice_id_match_boost(
            query="FOUNDUPS_PORTFOLIO_DATA_VALIDATOR_PHASE1",
            path="docs/audits/architecture/generic_audit.md",
            title="Generic Audit",
            meta_slice_id="FOUNDUPS_PORTFOLIO_DATA_VALIDATOR_PHASE1",
        )
        assert boost == _SLICE_ID_METADATA_PRECEDENCE_BOOST

    def test_no_boost_for_different_audit_spec(self):
        """No boost when query audit spec differs from target."""
        from holo_index.core.search_engine import _slice_id_match_boost

        boost = _slice_id_match_boost(
            query="FOUNDUPS_PORTFOLIO_DATA_VALIDATOR_PHASE1",
            path="docs/audits/architecture/HOLOINDEX_REGISTRY_ENTRY_PHASE1.md",
            title="HoloIndex Registry Entry",
            meta_slice_id="HOLOINDEX_REGISTRY_ENTRY_PHASE1",
        )
        assert boost == 0.0

    def test_no_boost_for_non_slice_query(self):
        """No boost when query has no slice ID."""
        from holo_index.core.search_engine import _slice_id_match_boost

        boost = _slice_id_match_boost(
            query="portfolio data validator",
            path="docs/audits/architecture/FOUNDUPS_PORTFOLIO_DATA_VALIDATOR_PHASE1.md",
            title="Portfolio Data Validator Phase 1",
            meta_slice_id="FOUNDUPS_PORTFOLIO_DATA_VALIDATOR_PHASE1",
        )
        assert boost == 0.0

    def test_hxa_boost_still_works(self):
        """HXA boost still works (tier 1 via metadata)."""
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


class TestSyntheticIndexAndSearch:
    """Synthetic fixture tests proving exact slice ID match ranks target doc first."""

    def test_synthetic_audit_spec_extraction_during_indexing(self):
        """Verify slice_id is extracted and stored during indexing for docs/audits/** paths."""
        from holo_index.core.indexing_engine import _extract_slice_id

        # Simulate what index_docs_entries does
        test_cases = [
            (
                "FOUNDUPS_PORTFOLIO_DATA_VALIDATOR_PHASE1.md",
                "Portfolio Data Validator Phase 1",
                "FOUNDUPS_PORTFOLIO_DATA_VALIDATOR_PHASE1",
            ),
            (
                "HOLOINDEX_PROD_01_REGISTRY_ENTRY_PHASE1.md",
                "HoloIndex Prod 01 Registry Entry — Phase 1",
                "HOLOINDEX_PROD_01_REGISTRY_ENTRY_PHASE1",
            ),
            (
                "FOUNDUPS_AGENT_REDTEAM_HARNESS_PROVENANCE_CHECK_PHASE1.md",
                "Provenance Check Phase 1",
                "FOUNDUPS_AGENT_REDTEAM_HARNESS_PROVENANCE_CHECK_PHASE1",
            ),
        ]

        for filename, title, expected_slice_id in test_cases:
            slice_id = _extract_slice_id(filename, title)
            assert slice_id == expected_slice_id, f"Failed for {filename}"

    def test_synthetic_search_ranking_prefers_exact_slice_match(self):
        """Synthetic proof: exact metadata slice ID match gets tier-1 boost
        over semantic-similar distractor docs (which match no query slice).
        """
        from holo_index.core.search_engine import (
            _SLICE_ID_METADATA_PRECEDENCE_BOOST,
            _slice_id_match_boost,
        )

        query = "FOUNDUPS_PORTFOLIO_DATA_VALIDATOR_PHASE1"

        # Target doc: exact metadata slice ID match
        target_boost = _slice_id_match_boost(
            query=query,
            path="docs/audits/architecture/FOUNDUPS_PORTFOLIO_DATA_VALIDATOR_PHASE1.md",
            title="Portfolio Data Validator Phase 1",
            meta_slice_id="FOUNDUPS_PORTFOLIO_DATA_VALIDATOR_PHASE1",
        )

        # Distractor docs: semantically similar but different slice IDs
        distractor_boosts = [
            _slice_id_match_boost(
                query=query,
                path="docs/audits/architecture/PORTFOLIO_DATA_GENERATOR_PHASE1.md",
                title="Portfolio Data Generator Phase 1",
                meta_slice_id="PORTFOLIO_DATA_GENERATOR_PHASE1",
            ),
            _slice_id_match_boost(
                query=query,
                path="modules/foundups/portfolio_validator/README.md",
                title="Portfolio Validator Module",
                meta_slice_id="",
            ),
            _slice_id_match_boost(
                query=query,
                path="docs/audits/architecture/FOUNDUPS_PUBLIC_PORTFOLIO_STATUS_SCHEMA_PHASE1.md",
                title="Public Portfolio Status Schema Phase 1",
                meta_slice_id="FOUNDUPS_PUBLIC_PORTFOLIO_STATUS_SCHEMA_PHASE1",
            ),
        ]

        # Target gets tier-1 boost, distractors get 0.0
        assert target_boost == _SLICE_ID_METADATA_PRECEDENCE_BOOST
        for distractor_boost in distractor_boosts:
            assert distractor_boost == 0.0

        # Therefore target_boost > all distractor_boosts
        assert all(target_boost > db for db in distractor_boosts)


class TestLexicalFallbackHonorsSliceIdBoost:
    """Verify lexical fallback path also applies slice_id boost."""

    def test_lexical_search_calls_slice_id_match_boost(self):
        """Lexical search path includes _slice_id_match_boost call."""
        # This test verifies via code inspection that _lexical_search_collection
        # calls _slice_id_match_boost. We verify by importing and checking
        # the function exists and is used in the expected location.
        import inspect
        from holo_index.core import search_engine

        # Get source of _lexical_search_collection
        source = inspect.getsource(search_engine._lexical_search_collection)

        # Verify it calls _slice_id_match_boost
        assert "_slice_id_match_boost" in source, (
            "_lexical_search_collection must call _slice_id_match_boost "
            "to honor slice_id boost in lexical fallback path"
        )

    def test_vector_search_calls_slice_id_match_boost(self):
        """Vector search path includes _slice_id_match_boost call."""
        import inspect
        from holo_index.core import search_engine

        # Get source of _search_collection (vector search)
        source = inspect.getsource(search_engine._search_collection)

        # Verify it calls _slice_id_match_boost
        assert "_slice_id_match_boost" in source, (
            "_search_collection must call _slice_id_match_boost "
            "to honor slice_id boost in vector search path"
        )
