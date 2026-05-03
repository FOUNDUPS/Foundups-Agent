"""Tests for CLI docs/knowledge display rendering.

HOLOINDEX_CLI_DOCS_DISPLAY_FIX_PHASE1: Verify _render_fast_search_summary
displays DOCS and KNOWLEDGE hits in addition to CODE and WSP.
"""

import pytest
from io import StringIO
from unittest.mock import patch


class TestCliDocsDisplay:
    """Test _render_fast_search_summary renders docs/knowledge hits."""

    def test_fast_summary_renders_docs_hits(self):
        """Fast summary should render docs_hits with [DOCS] prefix."""
        from holo_index._cli_main import _render_fast_search_summary

        results = {
            "code": [],
            "wsps": [],
            "docs": [
                {"path": "docs/architecture/WRE_GATEWAY_ADAPTER_DESIGN.md", "title": "WRE Gateway"},
                {"path": "docs/architecture/FOUNDUPS_AGENT_WORKSPACE_FORK_PLAN.md", "title": "Fork Plan"},
            ],
            "knowledge": [],
        }

        with patch("holo_index._cli_main.safe_print") as mock_print:
            _render_fast_search_summary(results, limit=5)

        calls = [str(c) for c in mock_print.call_args_list]
        call_str = " ".join(calls)

        assert "[DOCS]" in call_str
        assert "WRE_GATEWAY_ADAPTER_DESIGN.md" in call_str

    def test_fast_summary_renders_knowledge_hits(self):
        """Fast summary should render knowledge_hits with [KNOWLEDGE] prefix."""
        from holo_index._cli_main import _render_fast_search_summary

        results = {
            "code": [],
            "wsps": [],
            "docs": [],
            "knowledge": [
                {"path": "WSP_knowledge/docs/Papers/some_paper.md", "title": "Research Paper"},
            ],
        }

        with patch("holo_index._cli_main.safe_print") as mock_print:
            _render_fast_search_summary(results, limit=5)

        calls = [str(c) for c in mock_print.call_args_list]
        call_str = " ".join(calls)

        assert "[KNOWLEDGE]" in call_str
        assert "some_paper.md" in call_str

    def test_existing_code_wsp_rendering_unchanged(self):
        """Existing code_hits and wsp_hits rendering should still work."""
        from holo_index._cli_main import _render_fast_search_summary

        results = {
            "code": [
                {"location": "modules/wre_core/src/router.py"},
            ],
            "wsps": [
                {"path": "WSP_framework/src/WSP_106.md", "title": "WSP 106"},
            ],
            "docs": [],
            "knowledge": [],
        }

        with patch("holo_index._cli_main.safe_print") as mock_print:
            _render_fast_search_summary(results, limit=5)

        calls = [str(c) for c in mock_print.call_args_list]
        call_str = " ".join(calls)

        assert "[CODE]" in call_str
        assert "router.py" in call_str
        assert "[WSP]" in call_str
        assert "WSP_106.md" in call_str

    def test_empty_docs_knowledge_does_not_error(self):
        """Empty docs/knowledge lists should not cause errors."""
        from holo_index._cli_main import _render_fast_search_summary

        results = {
            "code": [{"location": "some/path.py"}],
            "wsps": [],
            "docs": [],
            "knowledge": [],
        }

        # Should not raise
        with patch("holo_index._cli_main.safe_print"):
            _render_fast_search_summary(results, limit=5)

    def test_none_docs_knowledge_does_not_error(self):
        """None docs/knowledge values should not cause errors."""
        from holo_index._cli_main import _render_fast_search_summary

        results = {
            "code": [{"location": "some/path.py"}],
            "wsps": [],
            "docs": None,
            "knowledge": None,
        }

        # Should not raise
        with patch("holo_index._cli_main.safe_print"):
            _render_fast_search_summary(results, limit=5)

    def test_total_hits_includes_docs_knowledge(self):
        """Total hits count should include docs and knowledge."""
        from holo_index._cli_main import _render_fast_search_summary

        results = {
            "code": [{"location": "a.py"}],
            "wsps": [{"path": "WSP_1.md"}],
            "docs": [{"path": "doc1.md"}, {"path": "doc2.md"}],
            "knowledge": [{"path": "paper1.md"}],
        }

        with patch("holo_index._cli_main.safe_print") as mock_print:
            _render_fast_search_summary(results, limit=10)

        # First call should contain total hits summary
        first_call = str(mock_print.call_args_list[0])
        assert "5 hits" in first_call
        assert "code=1" in first_call
        assert "wsp=1" in first_call
        assert "docs=2" in first_call
        assert "knowledge=1" in first_call

    def test_limit_applies_across_all_categories(self):
        """Limit should apply across all hit categories."""
        from holo_index._cli_main import _render_fast_search_summary

        results = {
            "code": [{"location": f"code{i}.py"} for i in range(3)],
            "wsps": [{"path": f"wsp{i}.md"} for i in range(3)],
            "docs": [{"path": f"doc{i}.md"} for i in range(3)],
            "knowledge": [{"path": f"paper{i}.md"} for i in range(3)],
        }

        with patch("holo_index._cli_main.safe_print") as mock_print:
            _render_fast_search_summary(results, limit=5)

        # Count actual result lines (excluding header lines)
        result_calls = [c for c in mock_print.call_args_list if "[CODE]" in str(c) or "[WSP]" in str(c) or "[DOCS]" in str(c) or "[KNOWLEDGE]" in str(c)]
        assert len(result_calls) == 5
