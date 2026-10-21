# -*- coding: utf-8 -*-
"""Tests for HOLOINDEX_INDEXER_ZERO_DOCS_OBSERVABILITY_PHASE1.

Verifies that the indexer returns observable IndexResult when zero docs
are discovered or indexed, enabling the CLI to avoid awarding spurious
rewards.

WSP_97 Truth Boundary Checklist:
- NO_CHROMA_MUTATION_IN_TESTS: All tests use mock/fake HoloIndex stubs
- NO_PATH_FILTER_CHANGE: Tests do not modify path filtering logic
- NO_EMBEDDING_MODEL_CHANGE: Tests use stub embeddings
- NO_BULK_INSERT_CHANGE_EXCEPT_COUNT_REPORTING: Tests verify count reporting only
- NO_LIVE_REINDEX: Tests use synthetic paths, no real indexing

Slice: HOLOINDEX_INDEXER_ZERO_DOCS_OBSERVABILITY_PHASE1
Worker: W6
"""

import ast
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

import holo_index.canonical_source_manifest as manifest_module
from holo_index.core.collection_injections import inject_module_tier0_candidates
from holo_index.core.indexing_engine import IndexResult, index_docs_entries
from holo_index.incremental_index_records import prepare_records


# ---------------------------------------------------------------------------
# IndexResult dataclass unit tests
# ---------------------------------------------------------------------------


def test_document_indexing_extraction_respects_wsp62() -> None:
    """The extraction reduces the parent hard-limit debt without new debt."""
    package_root = Path(__file__).parents[1]
    engine_source = (package_root / "core" / "indexing_engine.py").read_text(
        encoding="utf-8"
    )
    extraction_source = (package_root / "core" / "document_indexing.py").read_text(
        encoding="utf-8"
    )

    assert len(engine_source.splitlines()) < 1500
    assert len(extraction_source.splitlines()) < 800
    tree = ast.parse(extraction_source)
    functions = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    assert functions
    assert all(node.end_lineno - node.lineno + 1 <= 50 for node in functions)


class TestIndexResultDataclass:
    """Unit tests for the IndexResult dataclass."""

    def test_is_empty_when_zero_discovered(self):
        """IndexResult.is_empty is True when discovered_count is 0."""
        result = IndexResult(
            discovered_count=0,
            indexed_count=0,
            collection_name="navigation_docs",
            warning="No docs found"
        )
        assert result.is_empty is True
        assert result.success is False

    def test_is_empty_when_zero_indexed(self):
        """IndexResult.is_empty is True when indexed_count is 0 (even if discovered > 0)."""
        result = IndexResult(
            discovered_count=10,
            indexed_count=0,
            collection_name="navigation_docs",
            warning="All files had empty content"
        )
        assert result.is_empty is True
        assert result.success is False

    def test_success_when_indexed_positive(self):
        """IndexResult.success is True when indexed_count > 0."""
        result = IndexResult(
            discovered_count=100,
            indexed_count=95,
            collection_name="navigation_docs",
        )
        assert result.is_empty is False
        assert result.success is True
        assert result.warning is None

    def test_warning_present_on_failure(self):
        """IndexResult contains warning message on zero-doc scenarios."""
        result = IndexResult(
            discovered_count=0,
            indexed_count=0,
            collection_name="navigation_docs",
            warning="No docs found to index -- discovery returned zero files"
        )
        assert result.warning is not None
        assert "zero files" in result.warning.lower()


# ---------------------------------------------------------------------------
# FakeHoloIndex stub (no Chroma dependency)
# ---------------------------------------------------------------------------


class FakeHoloIndex:
    """Minimal stub for HoloIndex to test index_docs_entries without Chroma.

    WSP_97: NO_CHROMA_MUTATION_IN_TESTS -- this stub records calls but does
    not write to any real Chroma collection.
    """

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.docs_collection = None
        self._logged_actions: List[str] = []
        self._embeddings_requested: List[str] = []
        self._reset_calls: List[str] = []
        self._add_calls: List[Dict[str, Any]] = []

    def _log_agent_action(self, message: str, level: str) -> None:
        self._logged_actions.append(f"[{level}] {message}")

    def _get_embedding(self, text: str) -> List[float]:
        self._embeddings_requested.append(text)
        # Return a deterministic zero vector (no model needed)
        return [0.0] * 384

    def _reset_collection(self, name: str):
        self._reset_calls.append(name)
        # Return a mock collection that tracks add() calls
        mock_collection = MagicMock()
        mock_collection.add = lambda **kwargs: self._add_calls.append(kwargs)
        return mock_collection


class IndexedDocsCollection:
    """Exact metadata view over one captured full-index add payload."""

    def __init__(self, added: Dict[str, Any]) -> None:
        self.added = added

    def get(self, *, where, include):
        assert include == ["documents", "metadatas"]
        matches = [
            (document, metadata)
            for document, metadata in zip(
                self.added["documents"], self.added["metadatas"]
            )
            if metadata["path"] == where["path"]
        ]
        return {
            "documents": [item[0] for item in matches],
            "metadatas": [item[1] for item in matches],
        }


# ---------------------------------------------------------------------------
# Integration tests with FakeHoloIndex
# ---------------------------------------------------------------------------


class TestIndexDocsEntriesZeroDocsScenario:
    """Tests for index_docs_entries returning IndexResult on zero-doc scenarios."""

    def test_zero_discovered_returns_index_result_with_warning(self, tmp_path: Path):
        """When no docs are discovered, IndexResult has zero counts and warning."""
        # Create an empty docs directory
        empty_docs = tmp_path / "docs"
        empty_docs.mkdir()

        fake_holo = FakeHoloIndex(project_root=tmp_path)

        result = index_docs_entries(fake_holo)

        assert result is not None
        assert isinstance(result, IndexResult)
        assert result.discovered_count == 0
        assert result.indexed_count == 0
        assert result.is_empty is True
        assert result.success is False
        assert result.warning is not None
        assert "zero" in result.warning.lower() or "no docs" in result.warning.lower()
        # Verify NO Chroma mutation (collection should not be reset when zero discovered)
        assert len(fake_holo._reset_calls) == 0
        assert len(fake_holo._add_calls) == 0

    def test_zero_indexed_from_empty_content_returns_warning(self, tmp_path: Path):
        """When docs exist but have empty content, IndexResult shows zero indexed."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        # Create a file with only whitespace (no actual content)
        empty_file = docs_dir / "empty.md"
        empty_file.write_text("   \n\n   \n", encoding="utf-8")

        fake_holo = FakeHoloIndex(project_root=tmp_path)

        result = index_docs_entries(fake_holo)

        assert result is not None
        assert isinstance(result, IndexResult)
        assert result.discovered_count == 1
        assert result.indexed_count == 0
        assert result.is_empty is True
        assert result.success is False
        assert result.warning is not None

    def test_normal_docs_returns_positive_counts(self, tmp_path: Path):
        """When docs exist with content, IndexResult shows positive counts."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        # Create 3 valid markdown files
        for i in range(3):
            (docs_dir / f"doc_{i}.md").write_text(
                f"# Document {i}\n\nThis is document number {i} with content.",
                encoding="utf-8"
            )

        fake_holo = FakeHoloIndex(project_root=tmp_path)

        result = index_docs_entries(fake_holo)

        assert result is not None
        assert isinstance(result, IndexResult)
        assert result.discovered_count == 3
        assert result.indexed_count == 3
        assert result.is_empty is False
        assert result.success is True
        assert result.warning is None
        # Verify collection was reset and add was called
        assert len(fake_holo._reset_calls) == 1
        assert fake_holo._reset_calls[0] == "navigation_docs"
        assert len(fake_holo._add_calls) == 1

    def test_current_holo_contracts_receive_section_records(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Canonical current contracts expose deep status sections."""
        readme = tmp_path / "holo_index" / "README.md"
        readme.parent.mkdir(parents=True)
        readme.write_text(
            "# HoloIndex\n\nLive retrieval contract.\n\n"
            "## Current operational truth (2026-08-28)\n\nOwner query is current.\n\n"
            "## RSI Boundary\n\nPromotion remains fail-closed.\n\n"
            "## Historical Baseline\n\nOld ranker was A grade.\n\n"
            "## 7. Instance Health & Status\n\nOld closure count was 1376.\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(
            manifest_module,
            "filter_git_tracked_files",
            lambda _root, values: list(values),
        )
        fake_holo = FakeHoloIndex(project_root=tmp_path)

        result = index_docs_entries(fake_holo)

        added = fake_holo._add_calls[0]
        assert result.discovered_count == 1
        assert result.indexed_count > result.discovered_count
        assert {item["truth_class"] for item in added["metadatas"]} == {
            "current_truth"
        }
        assert "document_section" in {
            item["record_kind"] for item in added["metadatas"]
        }
        assert any("Promotion remains fail-closed" in item for item in added["documents"])
        assert not any("Old ranker was A grade" in item for item in added["documents"])
        assert not any("Old closure count was 1376" in item for item in added["documents"])
        assert sum(
            item["record_kind"] == "document_section"
            for item in added["metadatas"]
        ) == 2

    def test_historical_audit_keeps_one_summary_record(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Historical evidence is classified without section expansion."""
        audit = tmp_path / "docs" / "audits" / "holoindex" / "baseline.md"
        audit.parent.mkdir(parents=True)
        audit.write_text(
            "# Old Baseline\n\nHistorical metric.\n\n## Detail\n\nArchived evidence.\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(
            manifest_module,
            "filter_git_tracked_files",
            lambda _root, values: list(values),
        )
        fake_holo = FakeHoloIndex(project_root=tmp_path)

        result = index_docs_entries(fake_holo)

        added = fake_holo._add_calls[0]
        assert result.indexed_count == 1
        assert added["metadatas"][0]["truth_class"] == "historical_record"
        assert added["metadatas"][0]["record_kind"] == "document_summary"

    def test_partial_empty_content_shows_correct_counts(self, tmp_path: Path):
        """When some docs have content and some are empty, counts reflect reality."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        # 2 valid files
        (docs_dir / "valid1.md").write_text("# Valid\n\nContent here.", encoding="utf-8")
        (docs_dir / "valid2.md").write_text("# Also Valid\n\nMore content.", encoding="utf-8")
        # 1 empty file
        (docs_dir / "empty.md").write_text("", encoding="utf-8")

        fake_holo = FakeHoloIndex(project_root=tmp_path)

        result = index_docs_entries(fake_holo)

        assert result is not None
        assert result.discovered_count == 3
        assert result.indexed_count == 2  # Only 2 had content
        assert result.is_empty is False
        assert result.success is True

    def test_full_index_metadata_is_queryable_by_strict_tier0_consumer(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The producer and exact Tier-0 consumer share one path identity."""
        module = "modules/infrastructure/example_bridge"
        module_root = tmp_path / module
        module_root.mkdir(parents=True)
        for name in ("README.md", "INTERFACE.md"):
            (module_root / name).write_text(
                f"# {name}\ncontract", encoding="utf-8"
            )
        fake_holo = FakeHoloIndex(project_root=tmp_path)
        foreign_cwd = tmp_path / "foreign-cwd"
        foreign_cwd.mkdir()
        monkeypatch.chdir(foreign_cwd)
        index_docs_entries(fake_holo)

        added = fake_holo._add_calls[0]
        paths = [metadata["path"] for metadata in added["metadatas"]]
        assert paths == [f"{module}/INTERFACE.md", f"{module}/README.md"]

        incremental = prepare_records(
            operation=SimpleNamespace(
                collection="navigation_docs",
                repo_relative_path=f"{module}/README.md",
                stable_id="hidx_docs_example",
            ),
            document="# README.md\ncontract",
            plan=SimpleNamespace(
                foundup_id="example_bridge", foundup_root=module
            ),
            gateway=SimpleNamespace(embed=lambda _text: [0.0] * 384),
            receipt_source="test",
        )
        assert incremental[0].metadata["path"] in paths

        docs: list = []
        metas: list = []
        dists: list = []
        assert inject_module_tier0_candidates(
            IndexedDocsCollection(added), docs, metas, dists, module, strict=True
        ) == ()
        assert [metadata["path"] for metadata in metas] == [
            f"{module}/README.md",
            f"{module}/INTERFACE.md",
        ]
        assert all(
            metadata["_retrieval_provenance"] == "exact_metadata"
            for metadata in metas
        )


class TestCLIRewardLogic:
    """Tests verifying CLI reward logic based on IndexResult.

    These tests do not invoke the actual CLI but verify the conditional
    logic that should be applied based on IndexResult.is_empty.
    """

    def test_reward_not_awarded_on_is_empty_true(self):
        """Verify reward logic: is_empty=True means no reward."""
        result = IndexResult(
            discovered_count=0,
            indexed_count=0,
            collection_name="navigation_docs",
            warning="Zero files"
        )

        # Simulate CLI logic
        indexing_awarded = False
        if result is not None and not result.is_empty:
            indexing_awarded = True

        assert indexing_awarded is False

    def test_reward_awarded_on_success(self):
        """Verify reward logic: success=True means reward."""
        result = IndexResult(
            discovered_count=100,
            indexed_count=100,
            collection_name="navigation_docs",
        )

        # Simulate CLI logic
        indexing_awarded = False
        if result is not None and not result.is_empty:
            indexing_awarded = True

        assert indexing_awarded is True


class TestBackwardCompatibility:
    """Ensure existing callers handle IndexResult gracefully."""

    def test_result_is_truthy_when_success(self):
        """IndexResult should be truthy (for simple None checks in callers)."""
        result = IndexResult(
            discovered_count=10,
            indexed_count=10,
            collection_name="navigation_docs"
        )
        # Callers might do `if result:` checks
        assert result  # Should be truthy (dataclass instance)

    def test_result_attributes_accessible(self):
        """All expected attributes are accessible."""
        result = IndexResult(
            discovered_count=5,
            indexed_count=3,
            collection_name="test_collection",
            warning="partial failure"
        )
        assert hasattr(result, 'discovered_count')
        assert hasattr(result, 'indexed_count')
        assert hasattr(result, 'collection_name')
        assert hasattr(result, 'warning')
        assert hasattr(result, 'is_empty')
        assert hasattr(result, 'success')
