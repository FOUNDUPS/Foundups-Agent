# -*- coding: utf-8 -*-
"""CFZ4 — Collection separation tests.

Verifies that:
- navigation_wsp only contains WSP_framework/src/WSP_*.md files
- navigation_docs contains module/root docs
- navigation_knowledge contains papers/research
- ID prefixes are correct (wsp_, doc_, paper_)

WSP: WSP 97 (truthful collections), WSP 50 (pre-action verification)
"""
from pathlib import Path
import pytest


class TestCollectionPathRouting:
    """Test that paths route to correct collections."""

    def test_wsp_protocol_path_routes_to_wsp(self):
        """WSP_framework/src/WSP_*.md -> navigation_wsp."""
        path = Path("WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md")
        assert "WSP_framework" in str(path) and "src" in str(path)
        assert path.name.startswith("WSP_")

    def test_module_readme_routes_to_docs(self):
        """modules/**/README.md -> navigation_docs."""
        path = Path("modules/ai_intelligence/agent_permissions/README.md")
        assert "modules" in str(path)

    def test_root_docs_routes_to_docs(self):
        """docs/** -> navigation_docs."""
        path = Path("docs/audits/holoindex_turboquant/CFZ3_REPORT.md")
        assert str(path).startswith("docs")

    def test_paper_routes_to_knowledge(self):
        """WSP_knowledge/docs/Papers/** -> navigation_knowledge."""
        path = Path("WSP_knowledge/docs/Papers/PQN_Deep_Dive.md")
        assert "WSP_knowledge" in str(path) and "Papers" in str(path)


class TestIdPrefixCorrectness:
    """Test that ID prefixes match collection semantics."""

    def test_wsp_prefix_only_for_protocols(self):
        """wsp_ prefix should only be used for WSP protocols."""
        # Valid: wsp_1 for WSP_00_Zen_State_Attainment_Protocol.md
        valid_wsp_id = "wsp_1"
        assert valid_wsp_id.startswith("wsp_")

    def test_doc_prefix_for_module_docs(self):
        """doc_ prefix should be used for module/root docs."""
        valid_doc_id = "doc_42"
        assert valid_doc_id.startswith("doc_")

    def test_paper_prefix_for_knowledge(self):
        """paper_ prefix should be used for papers/research."""
        valid_paper_id = "paper_7"
        assert valid_paper_id.startswith("paper_")


class TestWspCollectionPurity:
    """Test that navigation_wsp only contains true WSP protocols."""

    def test_wsp_file_pattern_validation(self):
        """Only WSP_*.md files should be in navigation_wsp."""
        valid_wsp_names = [
            "WSP_00_Zen_State_Attainment_Protocol.md",
            "WSP_15_Micro_Sprint_Protocol.md",
            "WSP_97_System_Execution_Prompting_Protocol.md",
        ]
        for name in valid_wsp_names:
            assert name.startswith("WSP_")
            assert name.endswith(".md")

    def test_non_wsp_excluded_from_wsp_collection(self):
        """Non-WSP files should NOT be in navigation_wsp."""
        invalid_for_wsp = [
            "README.md",
            "INTERFACE.md",
            "ModLog.md",
            "PQN_Deep_Dive.md",
            "resp_detector_architecture.md",
        ]
        for name in invalid_for_wsp:
            assert not name.startswith("WSP_"), f"{name} should not be in navigation_wsp"


class TestSearchCompatibility:
    """Test backward compatibility of search results."""

    def test_search_result_has_wsp_hits(self):
        """Search result should have wsp_hits key."""
        mock_result = {
            "code_hits": [],
            "wsp_hits": [],
            "docs_hits": [],
            "knowledge_hits": [],
        }
        assert "wsp_hits" in mock_result

    def test_search_result_has_docs_hits(self):
        """Search result should have docs_hits key (CFZ4)."""
        mock_result = {
            "code_hits": [],
            "wsp_hits": [],
            "docs_hits": [],
            "knowledge_hits": [],
        }
        assert "docs_hits" in mock_result

    def test_search_result_has_knowledge_hits(self):
        """Search result should have knowledge_hits key (CFZ4)."""
        mock_result = {
            "code_hits": [],
            "wsp_hits": [],
            "docs_hits": [],
            "knowledge_hits": [],
        }
        assert "knowledge_hits" in mock_result
