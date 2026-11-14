# -*- coding: utf-8 -*-
"""Slice-ID metadata precedence — search-time ranking quality tests.

Slice: HOLOINDEX_T1_RANKING_QUALITY_PHASE1
Worker: W7

The rule under test is generic:

    When a query carries a literal slice-ID token AND a document's
    ``meta_slice_id`` is exactly that token, the document outranks any
    other document on the same query — including a sibling that benefits
    from the Trade module path / alias boosts — purely by composition of
    keyword-score boosts (no reindex, no Chroma writes).

These tests exercise the boost-composition math directly so a future
boost-cap change anywhere in the cascade is caught immediately. They do
**not** mock the search pipeline as a whole — they call the boost helpers
that the pipeline composes, with realistic inputs (audit-doc path vs.
module-root path, with and without ``slice_id`` metadata).
"""

from __future__ import annotations

from holo_index.core.search_engine import (
    _SLICE_ID_METADATA_PRECEDENCE_BOOST,
    _SLICE_ID_PATH_OR_TITLE_BOOST,
    _slice_id_match_boost,
    _trade_alias_keyword_boost,
    _trade_path_boost,
)


# ---------------------------------------------------------------------------
# Fixed constants for the three reference targets from the slice prompt.
# ---------------------------------------------------------------------------

T1_SLICE = "TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1"
T1_PATH = (
    "docs/audits/architecture/TRADE_PUMPFUN_DUE_DILIGENCE_SCORING_SPEC_PHASE1.md"
)
T1_TITLE = "Trade Pump.fun Due Diligence Scoring Spec - Phase 1"

T2_SLICE = "TRADE_ADAPTER_INTEGRATION_PHASE1"
T2_PATH = "docs/audits/architecture/TRADE_ADAPTER_INTEGRATION_PHASE1.md"
T2_TITLE = "Trade Adapter Integration - Phase 1"

T3_SLICE = "HOLOINDEX_FOUNDUP_QUERY_ALIAS_AND_TARGETED_VERDICT_PHASE1"
T3_PATH = (
    "docs/audits/holoindex_search_quality/"
    "HOLOINDEX_FOUNDUP_QUERY_ALIAS_AND_TARGETED_VERDICT_PHASE1.md"
)
T3_TITLE = "HoloIndex FoundUp Query Alias and Targeted Verdict - Phase 1"

# Sibling that previously outranked T2 on its own slice-ID query because of
# the Trade module-root path boost.
TRADE_INTERFACE_PATH = "modules/foundups/trade/INTERFACE.md"
TRADE_INTERFACE_TITLE = "Trade Module Interface"


# ---------------------------------------------------------------------------
# Precedence constants — defended against silent erosion
# ---------------------------------------------------------------------------


class TestSliceIdPrecedenceConstants:
    """The numeric precedence rule must dominate competing boosts."""

    def test_metadata_precedence_exceeds_max_trade_combination(self):
        """Metadata precedence boost must strictly exceed the max sum of
        ``_trade_path_boost`` cap (8.0) + ``_trade_alias_keyword_boost`` cap
        (6.0). If a future code change raises either cap, this assertion
        forces the precedence boost to be re-evaluated.
        """
        # Sanity: read the caps directly out of the boost helpers by
        # probing them at their documented saturation points.
        trade_path_cap = _trade_path_boost(
            "trade scoring", "modules/foundups/trade/INTERFACE.md"
        )
        # Trade alias boost saturates at 6.0 for any number of alias matches.
        trade_alias_cap = _trade_alias_keyword_boost(
            "trade analyst due diligence rug honeypot whale concentration",
            "docs/audits/architecture/SOMETHING.md",
            "Some audit doc",
            "trade analyst due diligence rug honeypot whale concentration",
        )
        max_competing = trade_path_cap + trade_alias_cap
        assert _SLICE_ID_METADATA_PRECEDENCE_BOOST > max_competing, (
            f"metadata precedence boost ({_SLICE_ID_METADATA_PRECEDENCE_BOOST}) "
            f"must strictly exceed max non-slice-id boost sum ({max_competing})"
        )

    def test_metadata_precedence_strictly_greater_than_path_title(self):
        """Tier-1 (metadata) boost must strictly exceed tier-2 (path/title)
        boost so a doc with proper metadata cannot be outranked by a doc
        whose only signal is path/title slice-ID presence.
        """
        assert (
            _SLICE_ID_METADATA_PRECEDENCE_BOOST > _SLICE_ID_PATH_OR_TITLE_BOOST
        )


# ---------------------------------------------------------------------------
# Generic rule: exact metadata slice_id match wins
# ---------------------------------------------------------------------------


class TestExactSliceIdMetadataPrecedence:
    """For an exact slice-ID query, a doc whose ``meta_slice_id`` exactly
    matches the query MUST outrank a doc whose only signal is the Trade
    path/alias boost cascade.
    """

    def _competing_score(self, query: str, path: str, title: str, content: str) -> float:
        """The non-slice-id boost portion of the keyword score, as composed
        in ``_compute_keyword_score`` (path + alias)."""
        return (
            _trade_path_boost(query, path)
            + _trade_alias_keyword_boost(query, path, title, content)
        )

    def test_t2_audit_doc_outranks_trade_interface_on_t2_slice_id_query(self):
        """The regression target named by the slice prompt: T2 must outrank
        ``modules/foundups/trade/INTERFACE.md`` for the exact T2 slice-ID query.
        """
        audit_score = _slice_id_match_boost(
            T2_SLICE, T2_PATH, T2_TITLE, T2_SLICE
        ) + self._competing_score(T2_SLICE, T2_PATH, T2_TITLE, T2_TITLE)
        interface_score = _slice_id_match_boost(
            T2_SLICE, TRADE_INTERFACE_PATH, TRADE_INTERFACE_TITLE, ""
        ) + self._competing_score(
            T2_SLICE, TRADE_INTERFACE_PATH, TRADE_INTERFACE_TITLE, ""
        )
        assert audit_score > interface_score, (
            f"T2 audit doc score ({audit_score}) must outrank Trade "
            f"INTERFACE.md score ({interface_score}) on its own slice-ID query"
        )

    def test_t1_audit_doc_outranks_trade_interface_on_t1_slice_id_query(self):
        audit_score = _slice_id_match_boost(
            T1_SLICE, T1_PATH, T1_TITLE, T1_SLICE
        ) + self._competing_score(T1_SLICE, T1_PATH, T1_TITLE, T1_TITLE)
        interface_score = _slice_id_match_boost(
            T1_SLICE, TRADE_INTERFACE_PATH, TRADE_INTERFACE_TITLE, ""
        ) + self._competing_score(
            T1_SLICE, TRADE_INTERFACE_PATH, TRADE_INTERFACE_TITLE, ""
        )
        assert audit_score > interface_score

    def test_t3_audit_doc_outranks_trade_interface_on_t3_slice_id_query(self):
        audit_score = _slice_id_match_boost(
            T3_SLICE, T3_PATH, T3_TITLE, T3_SLICE
        ) + self._competing_score(T3_SLICE, T3_PATH, T3_TITLE, T3_TITLE)
        interface_score = _slice_id_match_boost(
            T3_SLICE, TRADE_INTERFACE_PATH, TRADE_INTERFACE_TITLE, ""
        ) + self._competing_score(
            T3_SLICE, TRADE_INTERFACE_PATH, TRADE_INTERFACE_TITLE, ""
        )
        assert audit_score > interface_score


# ---------------------------------------------------------------------------
# Generic property — the rule does not name any specific slice or file
# ---------------------------------------------------------------------------


class TestGenericMetadataPrecedenceProperty:
    """The metadata-precedence rule must apply uniformly to any audit/spec
    doc that carries proper ``slice_id`` metadata, regardless of file
    path, slice prefix, or domain.
    """

    def test_arbitrary_holoindex_slice_id_metadata_wins(self):
        slice_id = "HOLOINDEX_HXA_AUDIT_INDEXING_FIX_PHASE1"
        audit_path = (
            "docs/audits/holoindex_search_quality/"
            "HOLOINDEX_HXA_AUDIT_INDEXING_FIX_PHASE1.md"
        )
        audit_score = _slice_id_match_boost(slice_id, audit_path, "Some title", slice_id)
        non_audit_score = _slice_id_match_boost(
            slice_id, "modules/foundups/trade/INTERFACE.md", "Trade INTERFACE", ""
        )
        assert audit_score > non_audit_score
        assert audit_score == _SLICE_ID_METADATA_PRECEDENCE_BOOST

    def test_arbitrary_foundups_slice_id_metadata_wins(self):
        slice_id = "FOUNDUPS_PORTFOLIO_DATA_VALIDATOR_PHASE1"
        audit_path = (
            "docs/audits/architecture/FOUNDUPS_PORTFOLIO_DATA_VALIDATOR_PHASE1.md"
        )
        audit_score = _slice_id_match_boost(slice_id, audit_path, "Some title", slice_id)
        # Even a Trade-target path can't beat metadata precedence
        non_audit_score = _slice_id_match_boost(
            slice_id, "modules/foundups/trade/README.md", "Trade README", ""
        )
        assert audit_score > non_audit_score
        assert audit_score == _SLICE_ID_METADATA_PRECEDENCE_BOOST

    def test_short_form_slice_id_metadata_wins(self):
        """The tiering also covers short-form HXA/FX/CFZ slice IDs."""
        slice_id = "HXA22"
        audit_score = _slice_id_match_boost(
            slice_id, "docs/audits/openclaw_hermes/HXA22.md", "Some title", slice_id
        )
        non_audit_score = _slice_id_match_boost(
            slice_id, "modules/foundups/trade/INTERFACE.md", "Trade INTERFACE", ""
        )
        assert audit_score > non_audit_score
        assert audit_score == _SLICE_ID_METADATA_PRECEDENCE_BOOST


# ---------------------------------------------------------------------------
# Anti-overfit guards
# ---------------------------------------------------------------------------


class TestNoTradeOrPathSpecialCase:
    """The fix must not encode any Trade-specific or path-specific
    short-circuit. These tests pin behaviour against accidental
    special-casing.
    """

    def test_non_slice_id_query_returns_zero(self):
        """Analyst-language queries (no slice-ID literal) get no slice-ID
        boost, so Trade alias / path boosts still control ranking."""
        assert (
            _slice_id_match_boost(
                "trade due diligence scoring",
                T1_PATH,
                T1_TITLE,
                T1_SLICE,
            )
            == 0.0
        )
        assert (
            _slice_id_match_boost(
                "pumpfun token launch detection",
                T1_PATH,
                T1_TITLE,
                T1_SLICE,
            )
            == 0.0
        )

    def test_metadata_match_works_for_non_trade_slice(self):
        """A non-Trade slice ID with metadata gets the same precedence
        boost — proving the rule isn't Trade-specific."""
        slice_id = "HOLOINDEX_INDEXER_PROJECT_ROOT_WORKTREE_SAFETY_PHASE1"
        audit_path = (
            "docs/audits/holoindex_search_quality/"
            "HOLOINDEX_INDEXER_PROJECT_ROOT_WORKTREE_SAFETY_PHASE1.md"
        )
        score = _slice_id_match_boost(slice_id, audit_path, "", slice_id)
        assert score == _SLICE_ID_METADATA_PRECEDENCE_BOOST

    def test_path_only_slice_match_keeps_original_5point0(self):
        """Backward compatibility: docs that match by path/title only
        (no ``meta_slice_id``) still receive the original 5.0 boost."""
        slice_id = "HOLOINDEX_INDEXER_PROJECT_ROOT_WORKTREE_SAFETY_PHASE1"
        audit_path = (
            "docs/audits/holoindex_search_quality/"
            "HOLOINDEX_INDEXER_PROJECT_ROOT_WORKTREE_SAFETY_PHASE1.md"
        )
        score = _slice_id_match_boost(slice_id, audit_path, "", "")
        assert score == _SLICE_ID_PATH_OR_TITLE_BOOST

    def test_unrelated_slice_id_no_boost(self):
        """A doc with the wrong ``meta_slice_id`` gets no boost from this
        rule — the fix isn't a blanket "all audit docs win" lever."""
        score = _slice_id_match_boost(
            T1_SLICE,
            "docs/audits/architecture/SOMETHING_ELSE_PHASE1.md",
            "Something else",
            "SOMETHING_ELSE_PHASE1",
        )
        assert score == 0.0


class TestNonSliceTradeQueryBehaviorPreserved:
    """Non-slice-ID Trade analyst queries must continue to benefit from
    ``_trade_path_boost`` + ``_trade_alias_keyword_boost`` as before. This
    pins the architect's anti-overfit constraint: no general suppression of
    the path/alias cascade.
    """

    def test_trade_path_boost_still_fires_for_trade_target_docs(self):
        boost = _trade_path_boost(
            "trade due diligence scoring", "modules/foundups/trade/INTERFACE.md"
        )
        assert boost == 8.0

    def test_trade_alias_boost_still_fires_for_alias_match(self):
        # ``_trade_alias_keyword_boost`` only fires when (a) the query has
        # Trade intent AND (b) an alias-group key in the query expands to
        # at least one alias not already in the query. "pumpfun rug pull"
        # satisfies both: "pumpfun" expands to {pump.fun, pump fun,
        # pump_fun}; "rug pull" expands to {rug_pull_score, soft-rug,
        # honeypot, ...}.
        content = (
            "Trade pump.fun audit doc covering rug_pull_score, honeypot "
            "detection, pump fun bonding curve metrics."
        )
        boost = _trade_alias_keyword_boost(
            "trade pumpfun rug pull",
            "docs/audits/architecture/TRADE_DUE_DILIGENCE_SCORING_ENGINE_PHASE1.md",
            "Trade Due Diligence Scoring Engine - Phase 1",
            content,
        )
        assert boost > 0.0

    def test_non_slice_id_query_does_not_lift_audit_doc_unfairly(self):
        """Without a slice-ID literal in the query, the audit doc does not
        receive a metadata-precedence boost. This proves the lift is gated
        on the user typing the literal slice ID."""
        # Query is purely analyst-language; T1 has metadata but no slice_id
        # is in the query → tier-1 boost does NOT fire.
        boost = _slice_id_match_boost(
            "due diligence scoring engine",
            T1_PATH,
            T1_TITLE,
            T1_SLICE,
        )
        assert boost == 0.0
