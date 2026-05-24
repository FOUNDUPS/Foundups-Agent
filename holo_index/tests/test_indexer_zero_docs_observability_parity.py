# -*- coding: utf-8 -*-
"""Tests for HOLOINDEX_INDEXER_ZERO_DOCS_OBSERVABILITY_PARITY_PHASE1.

Verifies that all 6 target indexers return IndexResult symmetrically with
index_docs_entries() for CLI observability parity.

Target indexers:
1. index_code_entries() -> navigation_code
2. index_symbol_entries() -> navigation_symbols
3. index_wsp_entries() -> navigation_wsp
4. index_knowledge_entries() -> navigation_knowledge
5. index_skillz_entries() -> navigation_skills
6. index_work_ledger_entries() -> navigation_work_ledger

WSP_97 Truth Boundary Checklist:
- NO_CHROMA_MUTATION_IN_TESTS: All tests use mock/fake HoloIndex stubs
- NO_NETWORK_CALL_IN_TESTS: Tests use synthetic paths, no real network
- NO_ACTUAL_PIP_INSTALL_IN_TESTS: No pip operations
- INDEXRESULT_SHAPE_REUSED_NOT_REDEFINED: Uses same IndexResult dataclass
- ALL_6_TARGET_INDEXERS_COVERED: Tests for all 6 indexers
- INDEX_DOCS_ENTRIES_UNCHANGED: Does not modify index_docs_entries behavior

Slice: HOLOINDEX_INDEXER_ZERO_DOCS_OBSERVABILITY_PARITY_PHASE1
Worker: W6
"""

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

from holo_index.core.indexing_engine import (
    IndexResult,
    index_code_entries,
    index_symbol_entries,
    index_wsp_entries,
    index_docs_entries,
    index_knowledge_entries,
    index_skillz_entries,
    index_work_ledger_entries,
)


# ---------------------------------------------------------------------------
# FakeHoloIndex stub (extended from test_indexer_zero_docs_observability.py)
# ---------------------------------------------------------------------------


class FakeHoloIndex:
    """Minimal stub for HoloIndex to test indexers without Chroma.

    WSP_97: NO_CHROMA_MUTATION_IN_TESTS — this stub records calls but does
    not write to any real Chroma collection.
    """

    def __init__(self, project_root: Path):
        self.project_root = project_root
        # Collection stubs
        self.code_collection = None
        self.symbol_collection = None
        self.wsp_collection = None
        self.docs_collection = None
        self.knowledge_collection = None
        self.skill_collection = None
        self.work_ledger_collection = None
        # Tracking
        self._logged_actions: List[str] = []
        self._embeddings_requested: List[str] = []
        self._reset_calls: List[str] = []
        self._add_calls: List[Dict[str, Any]] = []
        # For code indexer
        self.need_to: Dict[str, str] = {}
        # For WSP indexer
        self.wsp_summary: Dict[str, Any] = {}
        self.wsp_summary_file = project_root / ".wsp_summary.json"

    def _log_agent_action(self, message: str, level: str) -> None:
        self._logged_actions.append(f"[{level}] {message}")

    def _get_embedding(self, text: str) -> List[float]:
        self._embeddings_requested.append(text)
        return [0.0] * 384

    def _reset_collection(self, name: str):
        self._reset_calls.append(name)
        mock_collection = MagicMock()
        mock_collection.add = lambda **kwargs: self._add_calls.append(kwargs)
        return mock_collection

    def _infer_cube_tag(self, *args, **kwargs) -> str:
        return ""


# ---------------------------------------------------------------------------
# IndexResult dataclass tests (ensure shape unchanged)
# ---------------------------------------------------------------------------


class TestIndexResultShape:
    """Verify IndexResult shape is unchanged from PR #695."""

    def test_indexresult_has_required_attributes(self):
        """IndexResult must have discovered_count, indexed_count, collection_name, warning."""
        result = IndexResult(
            discovered_count=10,
            indexed_count=5,
            collection_name="test_collection",
            warning="test warning"
        )
        assert hasattr(result, 'discovered_count')
        assert hasattr(result, 'indexed_count')
        assert hasattr(result, 'collection_name')
        assert hasattr(result, 'warning')

    def test_indexresult_has_is_empty_property(self):
        """IndexResult must have is_empty property."""
        result = IndexResult(discovered_count=0, indexed_count=0, collection_name="test")
        assert hasattr(result, 'is_empty')
        assert result.is_empty is True

    def test_indexresult_has_success_property(self):
        """IndexResult must have success property."""
        result = IndexResult(discovered_count=10, indexed_count=10, collection_name="test")
        assert hasattr(result, 'success')
        assert result.success is True


# ---------------------------------------------------------------------------
# index_code_entries tests
# ---------------------------------------------------------------------------


class TestIndexCodeEntriesReturnsIndexResult:
    """Tests for index_code_entries returning IndexResult."""

    def test_returns_indexresult_not_none(self, tmp_path: Path):
        """index_code_entries must return IndexResult, not None."""
        fake_holo = FakeHoloIndex(project_root=tmp_path)
        fake_holo.need_to = {}  # Empty code entries

        result = index_code_entries(fake_holo)

        assert result is not None
        assert isinstance(result, IndexResult)

    def test_zero_discovered_returns_empty_result(self, tmp_path: Path):
        """Zero code entries discovered -> is_empty=True, warning populated."""
        fake_holo = FakeHoloIndex(project_root=tmp_path)
        fake_holo.need_to = {}

        result = index_code_entries(fake_holo)

        assert result.discovered_count == 0
        assert result.indexed_count == 0
        assert result.is_empty is True
        assert result.warning is not None
        assert result.collection_name == "navigation_code"

    def test_positive_entries_returns_success(self, tmp_path: Path):
        """Positive code entries -> is_empty=False, success=True."""
        fake_holo = FakeHoloIndex(project_root=tmp_path)
        fake_holo.need_to = {"find files": "src/main.py", "search": "holo_index/search.py"}

        result = index_code_entries(fake_holo)

        assert result.discovered_count == 2
        assert result.indexed_count == 2
        assert result.is_empty is False
        assert result.success is True
        assert result.warning is None


# ---------------------------------------------------------------------------
# index_symbol_entries tests
# ---------------------------------------------------------------------------


class TestIndexSymbolEntriesReturnsIndexResult:
    """Tests for index_symbol_entries returning IndexResult."""

    def test_returns_indexresult_not_none(self, tmp_path: Path):
        """index_symbol_entries must return IndexResult, not None."""
        fake_holo = FakeHoloIndex(project_root=tmp_path)

        result = index_symbol_entries(fake_holo, roots=[tmp_path])

        assert result is not None
        assert isinstance(result, IndexResult)

    def test_empty_directory_returns_empty_result(self, tmp_path: Path):
        """Empty directory -> zero symbols, is_empty=True."""
        fake_holo = FakeHoloIndex(project_root=tmp_path)

        result = index_symbol_entries(fake_holo, roots=[tmp_path])

        assert result.indexed_count == 0
        assert result.is_empty is True
        assert result.collection_name == "navigation_symbols"

    def test_python_file_with_function_returns_positive(self, tmp_path: Path):
        """Python file with function -> positive indexed_count."""
        src_file = tmp_path / "example.py"
        src_file.write_text("def hello():\n    '''Say hello'''\n    pass\n", encoding="utf-8")

        fake_holo = FakeHoloIndex(project_root=tmp_path)

        result = index_symbol_entries(fake_holo, roots=[tmp_path])

        assert result.discovered_count >= 1  # At least 1 file
        assert result.indexed_count >= 1  # At least 1 function
        assert result.is_empty is False
        assert result.success is True


# ---------------------------------------------------------------------------
# index_wsp_entries tests
# ---------------------------------------------------------------------------


class TestIndexWspEntriesReturnsIndexResult:
    """Tests for index_wsp_entries returning IndexResult."""

    def test_returns_indexresult_not_none(self, tmp_path: Path):
        """index_wsp_entries must return IndexResult, not None."""
        fake_holo = FakeHoloIndex(project_root=tmp_path)
        wsp_dir = tmp_path / "WSP_framework" / "src"
        wsp_dir.mkdir(parents=True)

        result = index_wsp_entries(fake_holo)

        assert result is not None
        assert isinstance(result, IndexResult)

    def test_no_wsp_files_returns_empty_result(self, tmp_path: Path):
        """No WSP_*.md files -> is_empty=True, warning populated."""
        fake_holo = FakeHoloIndex(project_root=tmp_path)
        wsp_dir = tmp_path / "WSP_framework" / "src"
        wsp_dir.mkdir(parents=True)

        result = index_wsp_entries(fake_holo)

        assert result.discovered_count == 0
        assert result.indexed_count == 0
        assert result.is_empty is True
        assert result.warning is not None
        assert result.collection_name == "navigation_wsp"

    def test_wsp_files_present_returns_success(self, tmp_path: Path):
        """WSP_*.md files present -> positive counts, success=True."""
        wsp_dir = tmp_path / "WSP_framework" / "src"
        wsp_dir.mkdir(parents=True)
        (wsp_dir / "WSP_01_Test.md").write_text("# WSP 01 Test\n\nContent.", encoding="utf-8")
        (wsp_dir / "WSP_02_Other.md").write_text("# WSP 02 Other\n\nMore.", encoding="utf-8")

        fake_holo = FakeHoloIndex(project_root=tmp_path)
        fake_holo.wsp_summary_file = tmp_path / ".wsp_summary.json"

        result = index_wsp_entries(fake_holo)

        assert result.discovered_count == 2
        assert result.indexed_count == 2
        assert result.is_empty is False
        assert result.success is True


# ---------------------------------------------------------------------------
# index_knowledge_entries tests
# ---------------------------------------------------------------------------


class TestIndexKnowledgeEntriesReturnsIndexResult:
    """Tests for index_knowledge_entries returning IndexResult."""

    def test_returns_indexresult_not_none(self, tmp_path: Path):
        """index_knowledge_entries must return IndexResult, not None."""
        fake_holo = FakeHoloIndex(project_root=tmp_path)

        result = index_knowledge_entries(fake_holo)

        assert result is not None
        assert isinstance(result, IndexResult)

    def test_missing_path_returns_empty_result(self, tmp_path: Path):
        """Missing knowledge path -> is_empty=True, warning populated."""
        fake_holo = FakeHoloIndex(project_root=tmp_path)

        result = index_knowledge_entries(fake_holo)

        assert result.discovered_count == 0
        assert result.indexed_count == 0
        assert result.is_empty is True
        assert result.warning is not None
        assert result.collection_name == "navigation_knowledge"

    def test_knowledge_files_present_returns_success(self, tmp_path: Path):
        """Papers present -> positive counts, success=True."""
        papers_dir = tmp_path / "WSP_knowledge" / "docs" / "Papers"
        papers_dir.mkdir(parents=True)
        (papers_dir / "paper1.md").write_text("# Paper 1\n\nAbstract.", encoding="utf-8")

        fake_holo = FakeHoloIndex(project_root=tmp_path)

        result = index_knowledge_entries(fake_holo)

        assert result.discovered_count == 1
        assert result.indexed_count == 1
        assert result.is_empty is False
        assert result.success is True


# ---------------------------------------------------------------------------
# index_skillz_entries tests
# ---------------------------------------------------------------------------


class TestIndexSkillzEntriesReturnsIndexResult:
    """Tests for index_skillz_entries returning IndexResult."""

    def test_returns_indexresult_not_none(self, tmp_path: Path):
        """index_skillz_entries must return IndexResult, not None."""
        fake_holo = FakeHoloIndex(project_root=tmp_path)

        result = index_skillz_entries(fake_holo)

        assert result is not None
        assert isinstance(result, IndexResult)

    def test_no_skillz_files_returns_empty_result(self, tmp_path: Path):
        """No SKILLz.md files -> is_empty=True, warning populated."""
        fake_holo = FakeHoloIndex(project_root=tmp_path)

        result = index_skillz_entries(fake_holo)

        assert result.discovered_count == 0
        assert result.indexed_count == 0
        assert result.is_empty is True
        assert result.warning is not None
        assert result.collection_name == "navigation_skills"

    def test_skillz_files_present_returns_success(self, tmp_path: Path):
        """SKILLz.md files present -> positive counts, success=True."""
        skills_dir = tmp_path / "holo_index" / "skillz" / "test_skill"
        skills_dir.mkdir(parents=True)
        skillz_file = skills_dir / "SKILLz.md"
        skillz_file.write_text(
            "---\nname: test_skill\ndescription: Test\nprimary_agent: test\n---\n# Test",
            encoding="utf-8"
        )

        fake_holo = FakeHoloIndex(project_root=tmp_path)

        result = index_skillz_entries(fake_holo)

        assert result.discovered_count >= 1
        assert result.indexed_count >= 1
        assert result.is_empty is False
        assert result.success is True


# ---------------------------------------------------------------------------
# index_work_ledger_entries tests
# ---------------------------------------------------------------------------


class TestIndexWorkLedgerEntriesReturnsIndexResult:
    """Tests for index_work_ledger_entries returning IndexResult."""

    def test_returns_indexresult_not_none(self, tmp_path: Path):
        """index_work_ledger_entries must return IndexResult, not None."""
        fake_holo = FakeHoloIndex(project_root=tmp_path)

        result = index_work_ledger_entries(fake_holo)

        assert result is not None
        assert isinstance(result, IndexResult)

    def test_missing_ledger_returns_empty_result(self, tmp_path: Path):
        """Missing work_ledger.example.json -> is_empty=True, warning populated."""
        fake_holo = FakeHoloIndex(project_root=tmp_path)

        result = index_work_ledger_entries(fake_holo)

        assert result.discovered_count == 0
        assert result.indexed_count == 0
        assert result.is_empty is True
        assert result.warning is not None
        assert result.collection_name == "navigation_work_ledger"

    def test_empty_slices_returns_empty_result(self, tmp_path: Path):
        """Empty slices array -> is_empty=True, warning populated."""
        ledger_dir = tmp_path / "docs" / "0102_session_briefings"
        ledger_dir.mkdir(parents=True)
        ledger_file = ledger_dir / "work_ledger.example.json"
        ledger_file.write_text('{"slices": []}', encoding="utf-8")

        fake_holo = FakeHoloIndex(project_root=tmp_path)

        result = index_work_ledger_entries(fake_holo)

        assert result.discovered_count == 0
        assert result.indexed_count == 0
        assert result.is_empty is True
        assert result.warning is not None

    def test_slices_present_returns_success(self, tmp_path: Path):
        """Slices present -> positive counts, success=True."""
        ledger_dir = tmp_path / "docs" / "0102_session_briefings"
        ledger_dir.mkdir(parents=True)
        ledger_file = ledger_dir / "work_ledger.example.json"
        ledger_data = {
            "slices": [
                {"slice_id": "TEST_SLICE_1", "title": "Test Slice 1", "status": "PROPOSED"},
                {"slice_id": "TEST_SLICE_2", "title": "Test Slice 2", "status": "IN_PROGRESS"},
            ]
        }
        ledger_file.write_text(json.dumps(ledger_data), encoding="utf-8")

        fake_holo = FakeHoloIndex(project_root=tmp_path)

        result = index_work_ledger_entries(fake_holo)

        assert result.discovered_count == 2
        assert result.indexed_count == 2
        assert result.is_empty is False
        assert result.success is True


# ---------------------------------------------------------------------------
# Regression: index_docs_entries behavior unchanged
# ---------------------------------------------------------------------------


class TestIndexDocsEntriesUnchanged:
    """Verify index_docs_entries behavior is unchanged from PR #695."""

    def test_returns_indexresult(self, tmp_path: Path):
        """index_docs_entries still returns IndexResult."""
        fake_holo = FakeHoloIndex(project_root=tmp_path)

        result = index_docs_entries(fake_holo)

        assert result is not None
        assert isinstance(result, IndexResult)

    def test_collection_name_is_navigation_docs(self, tmp_path: Path):
        """Collection name must be navigation_docs."""
        fake_holo = FakeHoloIndex(project_root=tmp_path)

        result = index_docs_entries(fake_holo)

        assert result.collection_name == "navigation_docs"

    def test_zero_docs_returns_empty_with_warning(self, tmp_path: Path):
        """Zero docs discovered -> is_empty=True, warning populated."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        fake_holo = FakeHoloIndex(project_root=tmp_path)

        result = index_docs_entries(fake_holo)

        assert result.is_empty is True
        assert result.warning is not None


# ---------------------------------------------------------------------------
# CLI reward logic parity
# ---------------------------------------------------------------------------


class TestCLIRewardLogicParity:
    """Verify CLI reward logic works consistently across all indexers."""

    @pytest.mark.parametrize("indexer_name,collection_name", [
        ("code", "navigation_code"),
        ("symbols", "navigation_symbols"),
        ("wsp", "navigation_wsp"),
        ("docs", "navigation_docs"),
        ("knowledge", "navigation_knowledge"),
        ("skills", "navigation_skills"),
        ("work_ledger", "navigation_work_ledger"),
    ])
    def test_is_empty_blocks_reward(self, indexer_name, collection_name):
        """is_empty=True should block reward for all indexers."""
        result = IndexResult(
            discovered_count=0,
            indexed_count=0,
            collection_name=collection_name,
            warning="Zero indexed"
        )

        # Simulate CLI logic
        indexing_awarded = False
        if result is not None and not result.is_empty:
            indexing_awarded = True

        assert indexing_awarded is False, f"{indexer_name}: is_empty should block reward"

    @pytest.mark.parametrize("indexer_name,collection_name", [
        ("code", "navigation_code"),
        ("symbols", "navigation_symbols"),
        ("wsp", "navigation_wsp"),
        ("docs", "navigation_docs"),
        ("knowledge", "navigation_knowledge"),
        ("skills", "navigation_skills"),
        ("work_ledger", "navigation_work_ledger"),
    ])
    def test_success_awards_reward(self, indexer_name, collection_name):
        """success=True should award reward for all indexers."""
        result = IndexResult(
            discovered_count=10,
            indexed_count=10,
            collection_name=collection_name,
        )

        # Simulate CLI logic
        indexing_awarded = False
        if result is not None and not result.is_empty:
            indexing_awarded = True

        assert indexing_awarded is True, f"{indexer_name}: success should award reward"
