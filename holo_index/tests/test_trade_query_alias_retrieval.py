# -*- coding: utf-8 -*-
"""Tests for Trade FoundUp query alias retrieval fix.

HOLOINDEX_FOUNDUP_QUERY_ALIAS_AND_TARGETED_VERDICT_PHASE1

Verifies that natural analyst language queries (pump.fun, memecoin, issuer,
X account, rug pull, etc.) correctly surface Trade module documentation.

WSP 97: Truth boundary — this slice fixes retrieval quality, not Trade behavior.
"""

from holo_index.core.search_engine import (
    _is_trade_intent_query,
    _expand_trade_aliases,
    _trade_path_boost,
    _trade_alias_keyword_boost,
)
from holo_index.core.agentic_rag_verdict import (
    QueryIntent,
    RetrievalVerdict,
    classify_query_intent,
    classify_retrieval_evidence,
    _has_trade_module_evidence,
)


class TestTradeIntentDetection:
    """Tests for Trade intent detection from query keywords."""

    def test_pump_fun_triggers_trade_intent(self):
        """pump.fun keyword triggers Trade intent."""
        assert _is_trade_intent_query("Trade pump.fun memecoin issuer") is True

    def test_pumpfun_triggers_trade_intent(self):
        """pumpfun (no dot) triggers Trade intent."""
        assert _is_trade_intent_query("pumpfun launchpad analysis") is True

    def test_memecoin_triggers_trade_intent(self):
        """memecoin keyword triggers Trade intent."""
        assert _is_trade_intent_query("memecoin due diligence wallet audit") is True

    def test_rug_pull_triggers_trade_intent(self):
        """rug pull keyword triggers Trade intent."""
        assert _is_trade_intent_query("rug pull detection honeypot") is True

    def test_x_account_triggers_trade_intent(self):
        """X account keyword triggers Trade intent."""
        assert _is_trade_intent_query("check x account twitter telegram") is True

    def test_influencer_triggers_trade_intent(self):
        """influencer keyword triggers Trade intent."""
        assert _is_trade_intent_query("influencer promoter social engagement") is True

    def test_large_trades_triggers_trade_intent(self):
        """large trades / whale keyword triggers Trade intent."""
        assert _is_trade_intent_query("whale top traders holder distribution") is True

    def test_unrelated_query_no_trade_intent(self):
        """Unrelated queries do not trigger Trade intent."""
        assert _is_trade_intent_query("pytest fixtures module structure") is False


class TestTradeAliasExpansion:
    """Tests for Trade alias expansion."""

    def test_pump_fun_expands_to_variants(self):
        """pump.fun expands to pumpfun, pump fun variants."""
        expansions = _expand_trade_aliases("pump.fun launchpad")
        assert "pumpfun" in expansions
        assert "pump fun" in expansions

    def test_memecoin_expands_to_variants(self):
        """memecoin expands to meme-coin, meme coin variants."""
        expansions = _expand_trade_aliases("memecoin analysis")
        assert "meme-coin" in expansions
        assert "meme coin" in expansions

    def test_issuer_expands_to_creator(self):
        """issuer expands to creator, creator_address."""
        expansions = _expand_trade_aliases("check issuer background")
        assert "creator" in expansions
        assert "creator_address" in expansions

    def test_rug_pull_expands_to_score_and_honeypot(self):
        """rug pull expands to rug_pull_score, honeypot."""
        expansions = _expand_trade_aliases("rug pull detection")
        assert "rug_pull_score" in expansions
        assert "honeypot" in expansions

    def test_twitter_expands_to_socialevent(self):
        """twitter expands to socialevent."""
        expansions = _expand_trade_aliases("check twitter account")
        assert "socialevent" in expansions


class TestTradePathBoost:
    """Tests for Trade module path boosting."""

    def test_trade_readme_gets_strong_boost(self):
        """Trade README gets 8.0 boost for Trade intent queries."""
        boost = _trade_path_boost(
            "pump.fun memecoin analysis",
            "modules/foundups/trade/README.md"
        )
        assert boost == 8.0

    def test_trade_interface_gets_strong_boost(self):
        """Trade INTERFACE gets 8.0 boost for Trade intent queries."""
        boost = _trade_path_boost(
            "memecoin launchpad",
            "modules/foundups/trade/INTERFACE.md"
        )
        assert boost == 8.0

    def test_trade_contracts_gets_strong_boost(self):
        """Trade contracts.py gets 8.0 boost for Trade intent queries."""
        boost = _trade_path_boost(
            "rug pull detection",
            "modules/foundups/trade/src/contracts.py"
        )
        assert boost == 8.0

    def test_trade_other_files_get_medium_boost(self):
        """Other Trade module files get 5.0 boost."""
        boost = _trade_path_boost(
            "memecoin analysis",
            "modules/foundups/trade/src/simulation_harness.py"
        )
        assert boost == 5.0

    def test_non_trade_path_no_boost(self):
        """Non-Trade paths get no boost even for Trade queries."""
        boost = _trade_path_boost(
            "pump.fun analysis",
            "modules/gamification/whack_a_magat/src/whack.py"
        )
        assert boost == 0.0

    def test_non_trade_query_no_boost(self):
        """Non-Trade queries get no boost even for Trade paths."""
        boost = _trade_path_boost(
            "pytest fixtures",
            "modules/foundups/trade/README.md"
        )
        assert boost == 0.0


class TestTradeAliasKeywordBoost:
    """Tests for Trade alias keyword boosting in content."""

    def test_alias_match_in_content_gets_boost(self):
        """Expanded aliases matching content get boost."""
        # Query uses "issuer", content has "creator_address"
        boost = _trade_alias_keyword_boost(
            "check issuer background",
            "modules/foundups/trade/src/contracts.py",
            "Trade Contracts",
            "creator_address validation"
        )
        assert boost > 0.0

    def test_multiple_alias_matches_accumulate(self):
        """Multiple alias matches accumulate boost."""
        boost = _trade_alias_keyword_boost(
            "issuer rug pull",
            "modules/foundups/trade/src/contracts.py",
            "Trade Contracts",
            "creator_address rug_pull_score honeypot_detection"
        )
        # Should accumulate multiple boosts (capped at 6.0)
        assert boost >= 3.0


class TestTradeQueryIntentClassification:
    """Tests for Trade query intent classification in verdict module."""

    def test_pump_fun_classified_as_trade_intent(self):
        """pump.fun query classified as TRADE intent."""
        intent = classify_query_intent("Trade pump.fun memecoin analysis")
        assert intent == QueryIntent.TRADE

    def test_memecoin_classified_as_trade_intent(self):
        """memecoin query classified as TRADE intent."""
        intent = classify_query_intent("memecoin launchpad bonding curve")
        assert intent == QueryIntent.TRADE

    def test_rug_pull_classified_as_trade_intent(self):
        """rug pull query classified as TRADE intent."""
        intent = classify_query_intent("rug pull honeypot detection")
        assert intent == QueryIntent.TRADE

    def test_wsp_still_classified_as_wsp_intent(self):
        """WSP queries still classified as WSP intent."""
        intent = classify_query_intent("WSP 97 compliance check")
        # WSP takes precedence since we check Trade first but WSP is more specific
        # Actually Trade is checked first, but "WSP 97" doesn't match Trade keywords
        assert intent == QueryIntent.WSP

    def test_unrelated_query_classified_as_general(self):
        """Unrelated queries classified as GENERAL intent."""
        # Note: "module" triggers CODE intent, so use a different example
        intent = classify_query_intent("pytest fixtures setup teardown")
        assert intent == QueryIntent.GENERAL


class TestTradeModuleEvidenceDetection:
    """Tests for Trade module evidence detection in retrieval results."""

    def test_trade_readme_is_evidence(self):
        """Trade README in results counts as Trade evidence."""
        payload = {
            "docs_hits": [
                {"path": "modules/foundups/trade/README.md", "title": "Trade README"}
            ],
            "code_hits": [],
        }
        assert _has_trade_module_evidence(payload) is True

    def test_trade_contracts_is_evidence(self):
        """Trade contracts.py in results counts as Trade evidence."""
        payload = {
            "code_hits": [
                {"path": "modules/foundups/trade/src/contracts.py"}
            ],
            "docs_hits": [],
        }
        assert _has_trade_module_evidence(payload) is True

    def test_trade_guards_is_evidence(self):
        """Trade guards.py in results counts as Trade evidence."""
        payload = {
            "code_hits": [
                {"location": "modules\\foundups\\trade\\src\\guards.py"}
            ],
            "docs_hits": [],
        }
        assert _has_trade_module_evidence(payload) is True

    def test_unrelated_hits_not_evidence(self):
        """Unrelated module hits do not count as Trade evidence."""
        payload = {
            "code_hits": [
                {"path": "modules/gamification/whack_a_magat/src/whack.py"}
            ],
            "docs_hits": [
                {"path": "docs/SPRINT_1_2_WSP_COMPLIANCE_AUDIT.md"}
            ],
        }
        assert _has_trade_module_evidence(payload) is False

    def test_empty_results_not_evidence(self):
        """Empty results do not count as Trade evidence."""
        payload = {"code_hits": [], "docs_hits": []}
        assert _has_trade_module_evidence(payload) is False


class TestTradeVerdictClassification:
    """Tests for Trade intent verdict classification."""

    def test_trade_intent_with_trade_evidence_is_sufficient(self):
        """Trade intent with Trade module evidence is SUFFICIENT."""
        payload = {
            "docs_hits": [
                {"path": "modules/foundups/trade/README.md", "title": "Trade README"}
            ],
            "code_hits": [],
            "wsp_hits": [],
            "knowledge_hits": [],
            "metadata": {"query": "pump.fun memecoin analysis"},
        }
        summary = classify_retrieval_evidence(payload, QueryIntent.TRADE)
        assert summary.verdict == RetrievalVerdict.SUFFICIENT

    def test_trade_intent_with_unrelated_hits_is_degraded(self):
        """Trade intent with unrelated hits is DEGRADED."""
        payload = {
            "docs_hits": [
                {"path": "docs/SPRINT_1_2_WSP_COMPLIANCE_AUDIT.md"}
            ],
            "code_hits": [
                {"path": "modules/gamification/whack_a_magat/src/whack.py"}
            ],
            "wsp_hits": [],
            "knowledge_hits": [],
            "metadata": {"query": "pump.fun memecoin analysis"},
        }
        summary = classify_retrieval_evidence(payload, QueryIntent.TRADE)
        assert summary.verdict == RetrievalVerdict.DEGRADED
        assert "Trade intent but no Trade module evidence" in summary.reason

    def test_trade_intent_with_no_hits_is_unsafe(self):
        """Trade intent with no hits is UNSAFE_TO_ACT."""
        payload = {
            "docs_hits": [],
            "code_hits": [],
            "wsp_hits": [],
            "knowledge_hits": [],
            "metadata": {"query": "pump.fun memecoin analysis"},
        }
        summary = classify_retrieval_evidence(payload, QueryIntent.TRADE)
        assert summary.verdict == RetrievalVerdict.UNSAFE_TO_ACT


class TestRegressionPreviousBehavior:
    """Regression tests to ensure previous behavior is preserved."""

    def test_wsp_intent_still_works(self):
        """WSP intent verdict logic still works correctly."""
        payload = {
            "wsp_hits": [
                {"path": "WSP_framework/src/WSP_97.md", "title": "WSP 97"}
            ],
            "docs_hits": [],
            "code_hits": [],
            "knowledge_hits": [],
            "metadata": {"query": "WSP 97 compliance"},
        }
        summary = classify_retrieval_evidence(payload, QueryIntent.WSP)
        assert summary.verdict == RetrievalVerdict.SUFFICIENT

    def test_general_intent_still_works(self):
        """General intent verdict logic still works correctly."""
        payload = {
            "code_hits": [
                {"path": "some/code/file.py"}
            ],
            "docs_hits": [],
            "wsp_hits": [],
            "knowledge_hits": [],
            "metadata": {"query": "some general query"},
        }
        summary = classify_retrieval_evidence(payload, QueryIntent.GENERAL)
        assert summary.verdict == RetrievalVerdict.SUFFICIENT
