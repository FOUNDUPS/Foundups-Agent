# -*- coding: utf-8 -*-
"""HIA_AGENTIC_RAG_WSP97_ALIAS_RECALL_PHASE5: WSP 97 Alias Recall Tests

Tests that natural-language operational phrases retrieve WSP_97
via the deterministic alias registry. No Gemma/LLM required.

WSP 97: These tests prove alias recall, not ranking quality.
        Every registered alias phrase must recall WSP_97 in top 5.

WSP 87: Keep tests focused on specific expected documents.
"""

import os
import pytest
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Live Index Detection
# ---------------------------------------------------------------------------


def _get_live_holo() -> Optional[Any]:
    """Get live HoloIndex instance if available."""
    try:
        ssd_path = Path("E:/HoloIndex")
        if not ssd_path.exists():
            return None

        vectors_path = ssd_path / "vectors"
        if not vectors_path.exists():
            return None

        from holo_index.core.holo_index import HoloIndex
        holo = HoloIndex(quiet=True)
        return holo
    except Exception:
        return None


def _is_live_index_available() -> bool:
    """Check if live HoloIndex is available for testing."""
    holo = _get_live_holo()
    if holo is None:
        return False
    try:
        code_count = holo.get_code_entry_count()
        return code_count > 0
    except Exception:
        return False


LIVE_INDEX_AVAILABLE = _is_live_index_available()
SKIP_LIVE = pytest.mark.skipif(
    not LIVE_INDEX_AVAILABLE,
    reason="Live HoloIndex not available at E:/HoloIndex"
)


# ---------------------------------------------------------------------------
# Alias Recall Assertion Helper
# ---------------------------------------------------------------------------


def _assert_wsp97_recalled(holo: Any, query: str, top_n: int = 5):
    """Assert that WSP_97 appears in top_n WSP results for the given query.

    Returns the position (1-indexed) where WSP_97 was found.
    """
    results = holo.search(query, limit=top_n)
    wsps = results.get("wsps", [])

    for i, hit in enumerate(wsps[:top_n]):
        path = hit.get("path", "")
        if "WSP_97" in path:
            return i + 1  # 1-indexed position

    top_paths = [h.get("path", "?")[-60:] for h in wsps[:top_n]]
    pytest.fail(
        f"WSP_97 not in top {top_n} WSP results for: {query!r}\n"
        f"Top paths: {top_paths}"
    )


# ---------------------------------------------------------------------------
# Explicit WSP 97 Query (Baseline)
# ---------------------------------------------------------------------------


class TestWSP97ExplicitRecall:
    """Baseline: explicit WSP 97 query must return WSP_97 at top-1."""

    @SKIP_LIVE
    def test_explicit_wsp97_query(self):
        """Explicit 'WSP 97 System Execution Prompting Protocol' -> top-1."""
        holo = _get_live_holo()
        pos = _assert_wsp97_recalled(
            holo,
            "WSP 97 System Execution Prompting Protocol",
            top_n=5,
        )
        assert pos == 1, f"WSP_97 at position {pos}, expected top-1"


# ---------------------------------------------------------------------------
# Natural-Language Alias Recall Tests
# ---------------------------------------------------------------------------


class TestWSP97AliasRecall:
    """Natural-language alias phrases must recall WSP_97 in top 5.

    HIA5: These tests prove the deterministic alias registry works.
    No Gemma/Qwen import required. No LLM reranking.
    """

    @SKIP_LIVE
    def test_retrieve_evidence_before_stating_facts(self):
        """'retrieve evidence before stating facts' -> WSP_97 top-5."""
        holo = _get_live_holo()
        _assert_wsp97_recalled(
            holo, "retrieve evidence before stating facts", top_n=5
        )

    @SKIP_LIVE
    def test_function_agentically_cot_cor(self):
        """'function agentically apply CoT CoR' -> WSP_97 top-5."""
        holo = _get_live_holo()
        _assert_wsp97_recalled(
            holo, "function agentically apply CoT CoR", top_n=5
        )

    @SKIP_LIVE
    def test_hard_think_dialectic_sweep(self):
        """'hard think dialectic sweep first principles' -> WSP_97 top-5."""
        holo = _get_live_holo()
        _assert_wsp97_recalled(
            holo,
            "hard think dialectic sweep first principles",
            top_n=5,
        )

    @SKIP_LIVE
    def test_agentic_activation_protocol(self):
        """'agentic activation protocol execution' -> WSP_97 top-5."""
        holo = _get_live_holo()
        _assert_wsp97_recalled(
            holo, "agentic activation protocol execution", top_n=5
        )

    @SKIP_LIVE
    def test_micro_pass_macro_pass(self):
        """'micro pass macro pass' -> WSP_97 top-5."""
        holo = _get_live_holo()
        _assert_wsp97_recalled(
            holo, "micro pass macro pass", top_n=5
        )

    @SKIP_LIVE
    def test_cot_cor_verification_gates(self):
        """'cot cor verification gates' -> WSP_97 top-5."""
        holo = _get_live_holo()
        _assert_wsp97_recalled(
            holo, "cot cor verification gates", top_n=5
        )

    @SKIP_LIVE
    def test_first_principles_then_execute(self):
        """'first principles then execute' -> WSP_97 top-5."""
        holo = _get_live_holo()
        _assert_wsp97_recalled(
            holo, "first principles then execute", top_n=5
        )

    @SKIP_LIVE
    def test_chain_of_thought_chain_of_reasoning(self):
        """'chain of thought chain of reasoning' -> WSP_97 top-5."""
        holo = _get_live_holo()
        _assert_wsp97_recalled(
            holo, "chain of thought chain of reasoning", top_n=5
        )


# ---------------------------------------------------------------------------
# Combined Query Recall (WSP number + alias phrase)
# ---------------------------------------------------------------------------


class TestWSP97CombinedRecall:
    """WSP 97 + alias phrase must still return WSP_97 at top-1."""

    @SKIP_LIVE
    def test_wsp97_with_alias_phrase(self):
        """'WSP 97 retrieve evidence before stating facts' -> top-1."""
        holo = _get_live_holo()
        pos = _assert_wsp97_recalled(
            holo,
            "WSP 97 retrieve evidence before stating facts",
            top_n=5,
        )
        assert pos == 1, f"WSP_97 at position {pos}, expected top-1"


# ---------------------------------------------------------------------------
# No-Gemma Guard
# ---------------------------------------------------------------------------


class TestNoLLMImportRequired:
    """Verify alias recall is deterministic — no LLM/Gemma imports."""

    def test_alias_registry_is_dict(self):
        """Alias registry is a plain dict, not an LLM model."""
        from holo_index.core.search_engine import _WSP_ALIAS_REGISTRY
        assert isinstance(_WSP_ALIAS_REGISTRY, dict)
        assert "97" in _WSP_ALIAS_REGISTRY
        assert len(_WSP_ALIAS_REGISTRY["97"]) >= 10

    def test_resolve_alias_no_llm(self):
        """_resolve_alias_wsp_numbers is pure string matching."""
        from holo_index.core.search_engine import _resolve_alias_wsp_numbers
        result = _resolve_alias_wsp_numbers("retrieve evidence before stating facts")
        assert "97" in result

    def test_alias_boost_no_llm(self):
        """_wsp_alias_match_boost is pure deterministic scoring."""
        from holo_index.core.search_engine import _wsp_alias_match_boost
        boost = _wsp_alias_match_boost(
            "retrieve evidence before stating facts",
            "WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md",
            "WSP 97: System Execution Prompting Protocol",
        )
        assert boost == 5.0

    def test_no_gemma_import_in_search_engine(self):
        """search_engine.py does not import Gemma or Qwen."""
        import inspect
        from holo_index.core import search_engine
        source = inspect.getsource(search_engine)
        assert "gemma" not in source.lower().split("alias")[0]  # Before alias registry
        assert "from llama_cpp" not in source
        assert "import ollama" not in source
