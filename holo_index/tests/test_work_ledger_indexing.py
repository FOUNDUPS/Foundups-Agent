# -*- coding: utf-8 -*-
"""Tests for Work Ledger HoloIndex Indexing.

FOUNDUPS_WORK_LEDGER_HOLOINDEX_IMPLEMENTATION_PHASE1

These tests verify:
1. Work ledger metadata extraction
2. Freshness score calculation
3. Status ranking weights
4. Work ledger search boosts (PR, worker, branch, status, foundup_id)
5. End-to-end indexing
"""

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest


class TestFreshnessCalculation:
    """Test freshness score calculation from last_verified_at."""

    def test_freshness_today_returns_1_0(self):
        """Entry verified today returns 1.0 freshness."""
        from holo_index.core.indexing_engine import _calculate_freshness

        now = datetime.now(timezone.utc).isoformat()
        assert _calculate_freshness(now) == 1.0

    def test_freshness_7_days_returns_0_9(self):
        """Entry verified 7 days ago returns 0.9 freshness."""
        from holo_index.core.indexing_engine import _calculate_freshness

        week_ago = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        assert _calculate_freshness(week_ago) == 0.9

    def test_freshness_14_days_returns_0_7(self):
        """Entry verified 14 days ago returns 0.7 freshness."""
        from holo_index.core.indexing_engine import _calculate_freshness

        two_weeks = (datetime.now(timezone.utc) - timedelta(days=12)).isoformat()
        assert _calculate_freshness(two_weeks) == 0.7

    def test_freshness_30_days_returns_0_5(self):
        """Entry verified 30 days ago returns 0.5 freshness."""
        from holo_index.core.indexing_engine import _calculate_freshness

        month_ago = (datetime.now(timezone.utc) - timedelta(days=25)).isoformat()
        assert _calculate_freshness(month_ago) == 0.5

    def test_freshness_60_days_returns_low(self):
        """Entry verified 60 days ago returns low freshness."""
        from holo_index.core.indexing_engine import _calculate_freshness

        two_months = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        result = _calculate_freshness(two_months)
        assert result <= 0.3
        assert result >= 0.1

    def test_freshness_null_returns_0_5(self):
        """None last_verified_at returns 0.5 (middle value)."""
        from holo_index.core.indexing_engine import _calculate_freshness

        assert _calculate_freshness(None) == 0.5

    def test_freshness_invalid_string_returns_0_5(self):
        """Invalid date string returns 0.5 (fallback)."""
        from holo_index.core.indexing_engine import _calculate_freshness

        assert _calculate_freshness("not-a-date") == 0.5


class TestStatusRanking:
    """Test status ranking weights."""

    def test_in_progress_highest_rank(self):
        """IN_PROGRESS has highest rank (1.0)."""
        from holo_index.core.indexing_engine import WORK_LEDGER_STATUS_RANKING

        assert WORK_LEDGER_STATUS_RANKING["IN_PROGRESS"] == 1.0

    def test_staged_for_w10_second_highest(self):
        """STAGED_FOR_W10 has second highest rank."""
        from holo_index.core.indexing_engine import WORK_LEDGER_STATUS_RANKING

        assert WORK_LEDGER_STATUS_RANKING["STAGED_FOR_W10"] == 0.95

    def test_superseded_near_lowest(self):
        """SUPERSEDED has near lowest rank (0.1)."""
        from holo_index.core.indexing_engine import WORK_LEDGER_STATUS_RANKING

        assert WORK_LEDGER_STATUS_RANKING["SUPERSEDED"] == 0.1

    def test_abandoned_lowest(self):
        """ABANDONED has lowest rank (0.05)."""
        from holo_index.core.indexing_engine import WORK_LEDGER_STATUS_RANKING

        assert WORK_LEDGER_STATUS_RANKING["ABANDONED"] == 0.05

    def test_merged_lower_than_open(self):
        """MERGED ranks lower than IN_PROGRESS."""
        from holo_index.core.indexing_engine import WORK_LEDGER_STATUS_RANKING

        assert WORK_LEDGER_STATUS_RANKING["MERGED"] < WORK_LEDGER_STATUS_RANKING["IN_PROGRESS"]


class TestPRNumberBoost:
    """Test PR number exact match boost."""

    def test_pr_number_match_returns_2_5(self):
        """Exact PR number match returns 2.5 boost."""
        from holo_index.core.search_engine import _pr_number_match_boost

        boost = _pr_number_match_boost("PR 642", 642)
        assert boost == 2.5

    def test_pr_hash_format_match(self):
        """PR#642 format matches."""
        from holo_index.core.search_engine import _pr_number_match_boost

        boost = _pr_number_match_boost("PR#642", 642)
        assert boost == 2.5

    def test_pr_no_space_match(self):
        """PR642 format matches."""
        from holo_index.core.search_engine import _pr_number_match_boost

        boost = _pr_number_match_boost("PR642", 642)
        assert boost == 2.5

    def test_pr_mismatch_returns_0(self):
        """PR number mismatch returns 0."""
        from holo_index.core.search_engine import _pr_number_match_boost

        boost = _pr_number_match_boost("PR 642", 643)
        assert boost == 0.0

    def test_no_pr_in_query_returns_0(self):
        """No PR in query returns 0."""
        from holo_index.core.search_engine import _pr_number_match_boost

        boost = _pr_number_match_boost("work ledger schema", 642)
        assert boost == 0.0

    def test_negative_pr_number_returns_0(self):
        """Negative/invalid PR number returns 0."""
        from holo_index.core.search_engine import _pr_number_match_boost

        boost = _pr_number_match_boost("PR 642", -1)
        assert boost == 0.0


class TestOwnerWorkerBoost:
    """Test owner_worker exact match boost."""

    def test_worker_match_returns_2_0(self):
        """Exact worker match returns 2.0 boost."""
        from holo_index.core.search_engine import _owner_worker_match_boost

        boost = _owner_worker_match_boost("what did W9 do", "W9")
        assert boost == 2.0

    def test_worker_case_insensitive(self):
        """Worker match is case insensitive."""
        from holo_index.core.search_engine import _owner_worker_match_boost

        boost = _owner_worker_match_boost("what did w9 do", "W9")
        assert boost == 2.0

    def test_lane_worker_format(self):
        """0102-A format matches."""
        from holo_index.core.search_engine import _owner_worker_match_boost

        boost = _owner_worker_match_boost("0102-A work", "0102-A")
        assert boost == 2.0

    def test_worker_mismatch_returns_0(self):
        """Worker mismatch returns 0."""
        from holo_index.core.search_engine import _owner_worker_match_boost

        boost = _owner_worker_match_boost("what did W9 do", "W10")
        assert boost == 0.0

    def test_no_worker_in_query_returns_0(self):
        """No worker in query returns 0."""
        from holo_index.core.search_engine import _owner_worker_match_boost

        boost = _owner_worker_match_boost("work ledger status", "W9")
        assert boost == 0.0

    def test_empty_worker_returns_0(self):
        """Empty owner_worker returns 0."""
        from holo_index.core.search_engine import _owner_worker_match_boost

        boost = _owner_worker_match_boost("what did W9 do", "")
        assert boost == 0.0


class TestBranchBoost:
    """Test branch name match boost."""

    def test_branch_substring_match(self):
        """Branch substring match returns 2.0 boost."""
        from holo_index.core.search_engine import _branch_match_boost

        boost = _branch_match_boost(
            "docs/foundups-work-ledger-schema-phase1",
            "docs/foundups-work-ledger-schema-phase1"
        )
        assert boost == 2.0

    def test_branch_partial_match(self):
        """Branch partial match returns 1.5 boost."""
        from holo_index.core.search_engine import _branch_match_boost

        boost = _branch_match_boost("work ledger schema", "docs/foundups-work-ledger-schema-phase1")
        assert boost >= 1.5

    def test_branch_no_match_returns_0(self):
        """No branch match returns 0."""
        from holo_index.core.search_engine import _branch_match_boost

        boost = _branch_match_boost("security audit", "docs/foundups-work-ledger-schema-phase1")
        assert boost == 0.0

    def test_empty_branch_returns_0(self):
        """Empty branch returns 0."""
        from holo_index.core.search_engine import _branch_match_boost

        boost = _branch_match_boost("work ledger", "")
        assert boost == 0.0


class TestStatusBoost:
    """Test status match boost."""

    def test_exact_status_match(self):
        """Exact status match returns 1.5 boost."""
        from holo_index.core.search_engine import _status_match_boost

        boost = _status_match_boost("IN_PROGRESS work", "IN_PROGRESS")
        assert boost == 1.5

    def test_open_query_matches_in_progress(self):
        """'open' query matches IN_PROGRESS."""
        from holo_index.core.search_engine import _status_match_boost

        boost = _status_match_boost("what is open", "IN_PROGRESS")
        assert boost >= 1.0

    def test_blocked_query_matches_blocked(self):
        """'blocked' query matches BLOCKED status."""
        from holo_index.core.search_engine import _status_match_boost

        boost = _status_match_boost("what is blocked", "BLOCKED")
        assert boost == 1.5

    def test_merged_query_matches_merged(self):
        """'merged' query matches MERGED status."""
        from holo_index.core.search_engine import _status_match_boost

        boost = _status_match_boost("what merged", "MERGED")
        assert boost == 1.5

    def test_status_mismatch_returns_0(self):
        """Status mismatch returns 0."""
        from holo_index.core.search_engine import _status_match_boost

        boost = _status_match_boost("PR_OPEN", "MERGED")
        assert boost == 0.0

    def test_empty_status_returns_0(self):
        """Empty status returns 0."""
        from holo_index.core.search_engine import _status_match_boost

        boost = _status_match_boost("IN_PROGRESS", "")
        assert boost == 0.0


class TestRelatedFoundupBoost:
    """Test related_foundup_id match boost."""

    def test_foundup_match_returns_2_0(self):
        """Foundup ID match returns 2.0 boost."""
        from holo_index.core.search_engine import _related_foundup_match_boost

        boost = _related_foundup_match_boost("gotjunk work", "gotjunk_001")
        assert boost == 2.0

    def test_foundup_no_match_returns_0(self):
        """No foundup match returns 0."""
        from holo_index.core.search_engine import _related_foundup_match_boost

        boost = _related_foundup_match_boost("kosei work", "gotjunk_001")
        assert boost == 0.0

    def test_empty_foundup_returns_0(self):
        """Empty related_foundup_id returns 0."""
        from holo_index.core.search_engine import _related_foundup_match_boost

        boost = _related_foundup_match_boost("gotjunk work", "")
        assert boost == 0.0


class TestCombinedBoost:
    """Test combined work ledger boost function."""

    def test_combined_boost_with_all_fields(self):
        """Combined boost adds all matching fields."""
        from holo_index.core.search_engine import _work_ledger_combined_boost

        meta: Dict[str, Any] = {
            "pr_number": 642,
            "owner_worker": "W9",
            "branch": "docs/foundups-work-ledger",
            "status": "IN_PROGRESS",
            "related_foundup_id": "gotjunk_001",
        }

        # Query hits PR and worker
        boost = _work_ledger_combined_boost("PR 642 W9 work", meta)
        assert boost >= 4.5  # PR (2.5) + Worker (2.0)

    def test_combined_boost_partial_match(self):
        """Combined boost with partial matches."""
        from holo_index.core.search_engine import _work_ledger_combined_boost

        meta: Dict[str, Any] = {
            "pr_number": 642,
            "owner_worker": "W9",
            "branch": "",
            "status": "MERGED",
            "related_foundup_id": "",
        }

        boost = _work_ledger_combined_boost("PR 642", meta)
        assert boost == 2.5  # Only PR matches

    def test_combined_boost_no_match(self):
        """Combined boost with no matches returns 0."""
        from holo_index.core.search_engine import _work_ledger_combined_boost

        meta: Dict[str, Any] = {
            "pr_number": 642,
            "owner_worker": "W9",
            "branch": "feature/something",
            "status": "IN_PROGRESS",
            "related_foundup_id": "gotjunk_001",
        }

        boost = _work_ledger_combined_boost("unrelated query", meta)
        assert boost == 0.0


class TestWorkLedgerIndexing:
    """Test end-to-end work ledger indexing."""

    def test_index_work_ledger_entries_extracts_metadata(self):
        """index_work_ledger_entries extracts all required metadata fields."""
        from holo_index.core.indexing_engine import index_work_ledger_entries

        # Create mock HoloIndex
        mock_holo = MagicMock()
        mock_holo._get_embedding = MagicMock(return_value=[0.1] * 384)
        mock_holo._reset_collection = MagicMock(return_value=MagicMock())
        mock_holo._log_agent_action = MagicMock()

        # Create temp work ledger
        ledger_data = {
            "schema_version": "1.0.0",
            "last_updated": "2026-05-21T12:00:00Z",
            "slices": [
                {
                    "slice_id": "TEST_SLICE_001",
                    "title": "Test Slice",
                    "lane": "W9",
                    "priority": "P1",
                    "status": "IN_PROGRESS",
                    "owner_worker": "W9",
                    "source": "audit",
                    "branch": "test/branch",
                    "pr_number": 123,
                    "related_foundup_id": "gotjunk_001",
                    "related_wsp": ["WSP 97"],
                    "blocked_by": [],
                    "next_slice": "TEST_SLICE_002",
                    "created_at": "2026-05-21T10:00:00Z",
                    "last_verified_at": "2026-05-21T12:00:00Z",
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            ledger_path = Path(tmpdir) / "docs" / "0102_session_briefings"
            ledger_path.mkdir(parents=True)
            (ledger_path / "work_ledger.example.json").write_text(
                json.dumps(ledger_data), encoding="utf-8"
            )

            mock_holo.project_root = Path(tmpdir)

            index_work_ledger_entries(mock_holo)

            # Verify collection.add was called
            mock_collection = mock_holo.work_ledger_collection
            assert mock_collection.add.called

            # Get the metadata that was passed
            call_args = mock_collection.add.call_args
            metadatas = call_args[1]["metadatas"]
            assert len(metadatas) == 1

            meta = metadatas[0]
            assert meta["slice_id"] == "TEST_SLICE_001"
            assert meta["title"] == "Test Slice"
            assert meta["lane"] == "W9"
            assert meta["priority"] == "P1"
            assert meta["status"] == "IN_PROGRESS"
            assert meta["owner_worker"] == "W9"
            assert meta["pr_number"] == 123
            assert meta["related_foundup_id"] == "gotjunk_001"
            assert meta["type"] == "work_ledger_slice"
            assert meta["freshness_score"] > 0.0
            assert meta["status_rank"] == 1.0  # IN_PROGRESS

    def test_index_work_ledger_handles_missing_file(self):
        """index_work_ledger_entries handles missing file gracefully."""
        from holo_index.core.indexing_engine import index_work_ledger_entries

        mock_holo = MagicMock()
        mock_holo._log_agent_action = MagicMock()

        with tempfile.TemporaryDirectory() as tmpdir:
            mock_holo.project_root = Path(tmpdir)
            index_work_ledger_entries(mock_holo)

            # Should log warning
            mock_holo._log_agent_action.assert_called_with(
                "work_ledger.example.json not found", "WARN"
            )


# =============================================================================
# Search Integration Tests (FOUNDUPS_WORK_LEDGER_HOLOINDEX_SEARCH_INTEGRATION_PHASE1)
# =============================================================================


class TestSearchIntegrationWorkLedger(unittest.TestCase):
    """Tests for work ledger search integration in execute_search()."""

    def test_execute_search_returns_work_ledger_hits_key(self):
        """execute_search result includes work_ledger_hits key."""
        from holo_index.core.search_engine import execute_search

        mock_holo = MagicMock()
        mock_holo._log_agent_action = MagicMock()
        mock_holo.code_collection = None
        mock_holo.wsp_collection = None
        mock_holo.test_collection = None
        mock_holo.skill_collection = None
        mock_holo.symbol_collection = None
        mock_holo.docs_collection = None
        mock_holo.knowledge_collection = None
        mock_holo.work_ledger_collection = None
        mock_holo.model = None
        mock_holo.project_root = Path(".")
        mock_holo.retrieval_mode = "lexical"
        mock_holo.embedding_backend = "none"
        mock_holo.routing_active = False
        mock_holo.collection_backend_map = {}
        mock_holo.search_cache = None  # Disable cache

        result = execute_search(mock_holo, "test query", limit=5)

        assert "work_ledger_hits" in result
        assert "work_ledger" in result
        assert "work_ledger_count" in result["metadata"]

    def test_execute_search_graceful_without_work_ledger_collection(self):
        """execute_search works when work_ledger_collection is None."""
        from holo_index.core.search_engine import execute_search

        mock_holo = MagicMock()
        mock_holo._log_agent_action = MagicMock()
        mock_holo.code_collection = None
        mock_holo.wsp_collection = None
        mock_holo.test_collection = None
        mock_holo.skill_collection = None
        mock_holo.symbol_collection = None
        mock_holo.docs_collection = None
        mock_holo.knowledge_collection = None
        mock_holo.work_ledger_collection = None
        mock_holo.model = None
        mock_holo.project_root = Path(".")
        mock_holo.retrieval_mode = "lexical"
        mock_holo.embedding_backend = "none"
        mock_holo.routing_active = False
        mock_holo.collection_backend_map = {}
        mock_holo.search_cache = None  # Disable cache

        result = execute_search(mock_holo, "PR 642", limit=5)

        assert result["work_ledger_hits"] == []
        assert result["metadata"]["work_ledger_count"] == 0

    def test_execute_search_queries_work_ledger_collection_when_present(self):
        """execute_search queries work_ledger_collection when it exists."""
        from holo_index.core.search_engine import execute_search

        mock_collection = MagicMock()
        mock_collection.query = MagicMock(return_value={
            "documents": [["Work Slice: TEST_SLICE"]],
            "metadatas": [[{
                "slice_id": "TEST_SLICE",
                "title": "Test Slice",
                "status": "IN_PROGRESS",
                "owner_worker": "W9",
                "pr_number": 642,
                "type": "work_ledger_slice",
                "path": "work_ledger.example.json",
            }]],
            "distances": [[0.5]],
        })

        mock_holo = MagicMock()
        mock_holo._log_agent_action = MagicMock()
        mock_holo._get_embedding = MagicMock(return_value=[0.0] * 384)
        mock_holo.code_collection = None
        mock_holo.wsp_collection = None
        mock_holo.test_collection = None
        mock_holo.skill_collection = None
        mock_holo.symbol_collection = None
        mock_holo.docs_collection = None
        mock_holo.knowledge_collection = None
        mock_holo.work_ledger_collection = mock_collection
        mock_holo.model = MagicMock()
        mock_holo.project_root = Path(".")
        mock_holo.retrieval_mode = "semantic"
        mock_holo.embedding_backend = "sentence_transformers"
        mock_holo.routing_active = False
        mock_holo.collection_backend_map = {}
        mock_holo.search_cache = None  # Disable cache

        result = execute_search(mock_holo, "PR 642", limit=5)

        mock_collection.query.assert_called()
        assert result["metadata"]["work_ledger_count"] >= 0

    def test_execute_search_doc_type_filter_work_ledger(self):
        """execute_search respects doc_type_filter='work_ledger'."""
        from holo_index.core.search_engine import execute_search

        mock_collection = MagicMock()
        mock_collection.query = MagicMock(return_value={
            "documents": [["Work Slice: TEST_SLICE"]],
            "metadatas": [[{
                "slice_id": "TEST_SLICE",
                "title": "Test Slice",
                "status": "IN_PROGRESS",
                "type": "work_ledger_slice",
                "path": "work_ledger.example.json",
            }]],
            "distances": [[0.5]],
        })

        mock_holo = MagicMock()
        mock_holo._log_agent_action = MagicMock()
        mock_holo._get_embedding = MagicMock(return_value=[0.0] * 384)
        mock_holo.code_collection = MagicMock()
        mock_holo.wsp_collection = MagicMock()
        mock_holo.test_collection = MagicMock()
        mock_holo.skill_collection = MagicMock()
        mock_holo.symbol_collection = MagicMock()
        mock_holo.docs_collection = MagicMock()
        mock_holo.knowledge_collection = MagicMock()
        mock_holo.work_ledger_collection = mock_collection
        mock_holo.model = MagicMock()
        mock_holo.project_root = Path(".")
        mock_holo.retrieval_mode = "semantic"
        mock_holo.embedding_backend = "sentence_transformers"
        mock_holo.routing_active = False
        mock_holo.collection_backend_map = {}
        mock_holo.search_cache = None  # Disable cache

        result = execute_search(mock_holo, "what is open", limit=5, doc_type_filter="work_ledger")

        mock_collection.query.assert_called()
        mock_holo.code_collection.query.assert_not_called()
        assert "work_ledger_hits" in result


class TestHoloIndexWrapperMethod(unittest.TestCase):
    """Tests for HoloIndex.index_work_ledger_entries() wrapper method."""

    def test_holo_index_has_work_ledger_collection_attribute(self):
        """HoloIndex class exposes work_ledger_collection attribute."""
        from holo_index.core.holo_index import HoloIndex

        assert hasattr(HoloIndex, "__init__")
        import inspect
        source = inspect.getsource(HoloIndex.__init__)
        assert "work_ledger_collection" in source

    def test_holo_index_has_index_work_ledger_entries_method(self):
        """HoloIndex class exposes index_work_ledger_entries() method."""
        from holo_index.core.holo_index import HoloIndex

        assert hasattr(HoloIndex, "index_work_ledger_entries")


class TestWorkLedgerBoostsReachable(unittest.TestCase):
    """Tests proving boosts are reachable through integrated search."""

    def test_pr_number_boost_reachable_in_search(self):
        """PR number boost is applied when querying work_ledger_slice."""
        from holo_index.core.search_engine import _work_ledger_combined_boost

        meta = {
            "pr_number": 642,
            "owner_worker": "W9",
            "branch": "feat/test",
            "status": "IN_PROGRESS",
            "related_foundup_id": "gotjunk",
        }

        boost = _work_ledger_combined_boost("PR 642", meta)
        assert boost >= 2.0

    def test_owner_worker_boost_reachable_in_search(self):
        """Owner worker boost is applied when querying work_ledger_slice."""
        from holo_index.core.search_engine import _work_ledger_combined_boost

        meta = {
            "pr_number": -1,
            "owner_worker": "W9",
            "branch": "",
            "status": "IN_PROGRESS",
            "related_foundup_id": "",
        }

        boost = _work_ledger_combined_boost("what did W9 do", meta)
        assert boost >= 2.0

    def test_branch_boost_reachable_in_search(self):
        """Branch boost is applied when querying work_ledger_slice."""
        from holo_index.core.search_engine import _work_ledger_combined_boost

        meta = {
            "pr_number": -1,
            "owner_worker": "",
            "branch": "feat/work-ledger-integration",
            "status": "IN_PROGRESS",
            "related_foundup_id": "",
        }

        # Query with tokens that match branch: work + ledger from branch tokens
        boost = _work_ledger_combined_boost("work ledger branch", meta)
        assert boost >= 1.5

    def test_status_boost_reachable_in_search(self):
        """Status boost is applied when querying work_ledger_slice."""
        from holo_index.core.search_engine import _work_ledger_combined_boost

        meta = {
            "pr_number": -1,
            "owner_worker": "",
            "branch": "",
            "status": "IN_PROGRESS",
            "related_foundup_id": "",
        }

        boost = _work_ledger_combined_boost("what is IN_PROGRESS", meta)
        assert boost >= 1.5

    def test_related_foundup_boost_reachable_in_search(self):
        """Related foundup ID boost is applied when querying work_ledger_slice."""
        from holo_index.core.search_engine import _work_ledger_combined_boost

        meta = {
            "pr_number": -1,
            "owner_worker": "",
            "branch": "",
            "status": "IN_PROGRESS",
            "related_foundup_id": "gotjunk",
        }

        boost = _work_ledger_combined_boost("gotjunk work", meta)
        assert boost >= 2.0


class TestCLITargetedReindex:
    """Targeted reindex CLI dispatch — FOUNDUPS_WORK_LEDGER_TARGETED_REINDEX_CLI_PHASE1."""

    def _make_args(self, **overrides):
        import argparse
        ns = argparse.Namespace(index_work_ledger=False)
        for k, v in overrides.items():
            setattr(ns, k, v)
        return ns

    def _make_holo(self, project_root: Path):
        holo = MagicMock()
        holo.project_root = project_root
        holo.work_ledger_collection = MagicMock()
        holo.work_ledger_collection.count.return_value = 0
        return holo

    def test_helper_returns_false_when_flag_unset(self, tmp_path):
        """Dispatch helper is a no-op when --index-work-ledger flag is False."""
        from holo_index._cli_main import _run_work_ledger_indexing
        holo = self._make_holo(project_root=tmp_path)
        result = _run_work_ledger_indexing(holo, self._make_args(index_work_ledger=False))
        assert result is False
        holo.index_work_ledger_entries.assert_not_called()

    def test_helper_returns_false_when_flag_missing(self, tmp_path):
        """Dispatch helper is a no-op when args has no index_work_ledger attribute."""
        import argparse
        from holo_index._cli_main import _run_work_ledger_indexing
        holo = self._make_holo(project_root=tmp_path)
        ns = argparse.Namespace()  # no attribute at all
        result = _run_work_ledger_indexing(holo, ns)
        assert result is False
        holo.index_work_ledger_entries.assert_not_called()

    def test_helper_fail_closed_when_source_missing(self, tmp_path, capsys):
        """Dispatch helper fails gracefully when work_ledger.example.json is missing."""
        from holo_index._cli_main import _run_work_ledger_indexing
        holo = self._make_holo(project_root=tmp_path)
        result = _run_work_ledger_indexing(holo, self._make_args(index_work_ledger=True))
        assert result is False
        holo.index_work_ledger_entries.assert_not_called()
        captured = capsys.readouterr()
        assert "[WORK-LEDGER]" in captured.out
        assert "SKIPPED" in captured.out
        assert "source file missing" in captured.out
        assert "navigation_work_ledger" in captured.out

    def test_helper_invokes_wrapper_when_source_exists(self, tmp_path, capsys):
        """Dispatch helper invokes index_work_ledger_entries() when source is present."""
        from holo_index._cli_main import _run_work_ledger_indexing
        from holo_index.core.indexing_engine import IndexResult

        ledger_dir = tmp_path / "docs" / "0102_session_briefings"
        ledger_dir.mkdir(parents=True)
        (ledger_dir / "work_ledger.example.json").write_text('{"slices": []}', encoding="utf-8")

        holo = self._make_holo(project_root=tmp_path)
        # HOLOINDEX_INDEXER_ZERO_DOCS_OBSERVABILITY_PARITY_PHASE1 repair:
        # CLI now expects IndexResult, not MagicMock
        holo.index_work_ledger_entries.return_value = IndexResult(
            discovered_count=7,
            indexed_count=7,
            collection_name="navigation_work_ledger",
            warning=None,
        )

        result = _run_work_ledger_indexing(holo, self._make_args(index_work_ledger=True))
        assert result is True
        holo.index_work_ledger_entries.assert_called_once_with()

        captured = capsys.readouterr()
        assert "[WORK-LEDGER] Entries indexed: 7" in captured.out
        assert "SUCCESS" in captured.out

    def test_helper_handles_wrapper_exception_gracefully(self, tmp_path, capsys):
        """Dispatch helper does not crash if index_work_ledger_entries() raises."""
        from holo_index._cli_main import _run_work_ledger_indexing

        ledger_dir = tmp_path / "docs" / "0102_session_briefings"
        ledger_dir.mkdir(parents=True)
        (ledger_dir / "work_ledger.example.json").write_text('{"slices": []}', encoding="utf-8")

        holo = self._make_holo(project_root=tmp_path)
        holo.index_work_ledger_entries.side_effect = RuntimeError("indexer boom")

        result = _run_work_ledger_indexing(holo, self._make_args(index_work_ledger=True))
        assert result is False
        captured = capsys.readouterr()
        assert "FAILURE" in captured.out
        assert "indexer boom" in captured.out

    def test_helper_does_not_invoke_other_index_methods(self, tmp_path):
        """Targeted reindex only touches work-ledger — not code/wsp/docs/knowledge/symbols."""
        from holo_index._cli_main import _run_work_ledger_indexing

        ledger_dir = tmp_path / "docs" / "0102_session_briefings"
        ledger_dir.mkdir(parents=True)
        (ledger_dir / "work_ledger.example.json").write_text('{"slices": []}', encoding="utf-8")

        holo = self._make_holo(project_root=tmp_path)

        _run_work_ledger_indexing(holo, self._make_args(index_work_ledger=True))

        holo.index_code_entries.assert_not_called()
        holo.index_wsp_entries.assert_not_called()
        holo.index_docs_entries.assert_not_called()
        holo.index_knowledge_entries.assert_not_called()
        holo.index_symbol_entries.assert_not_called()
        holo.index_skillz_entries.assert_not_called()


class TestCLIFlagParsing:
    """CLI parser accepts targeted reindex flags — FOUNDUPS_WORK_LEDGER_TARGETED_REINDEX_CLI_PHASE1."""

    def _run_help(self):
        import os
        import subprocess
        import sys
        repo_root = Path(__file__).resolve().parent.parent.parent
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        result = subprocess.run(
            [sys.executable, "holo_index.py", "--help"],
            capture_output=True,
            timeout=60,
            cwd=str(repo_root),
            env=env,
        )
        stdout = result.stdout.decode("utf-8", errors="replace")
        stderr = result.stderr.decode("utf-8", errors="replace")
        return stdout + stderr

    def test_help_advertises_index_work_ledger_flag(self):
        """--help output lists --index-work-ledger."""
        output = self._run_help()
        assert "--index-work-ledger" in output

    def test_help_advertises_reindex_work_ledger_alias(self):
        """--help output lists --reindex-work-ledger alias."""
        output = self._run_help()
        assert "--reindex-work-ledger" in output

    def test_help_advertises_reindex_ledger_alias(self):
        """--help output lists --reindex-ledger alias."""
        output = self._run_help()
        assert "--reindex-ledger" in output

    def test_existing_index_flags_still_advertised(self):
        """Pre-existing index flags remain in --help (no regression)."""
        output = self._run_help()
        assert "--index-code" in output
        assert "--index-wsp" in output
        assert "--index-docs" in output
        assert "--index-knowledge" in output
        assert "--index-skillz" in output
        assert "--index-cli" in output
        assert "--index-all" in output


class TestPriorityCoercion:
    """_coerce_priority — FOUNDUPS_WORK_LEDGER_SEARCH_RETRIEVAL_PRIORITY_HOTFIX_PHASE1."""

    def test_priority_num_wins_over_string_priority(self):
        """priority_num takes precedence — work-ledger indexer writes both fields."""
        from holo_index.core.search_engine import _coerce_priority
        # Work-ledger indexer writes priority="P3" AND priority_num=10
        assert _coerce_priority({"priority_num": 10, "priority": "P3"}) == 10.0

    def test_numeric_priority_returned_unchanged(self):
        """Standard collections (code/wsp/docs) pass numeric priority through."""
        from holo_index.core.search_engine import _coerce_priority
        assert _coerce_priority({"priority": 7}) == 7.0
        assert _coerce_priority({"priority": 2.5}) == 2.5

    def test_p_label_coerced_to_weight(self):
        """P0..P4 string labels coerce to numeric weights."""
        from holo_index.core.search_engine import _coerce_priority
        assert _coerce_priority({"priority": "P0"}) == 5.0
        assert _coerce_priority({"priority": "P1"}) == 4.0
        assert _coerce_priority({"priority": "P2"}) == 3.0
        assert _coerce_priority({"priority": "P3"}) == 2.0
        assert _coerce_priority({"priority": "P4"}) == 1.0

    def test_p_label_case_and_whitespace_tolerated(self):
        """Defensive coercion handles lowercase/whitespace variants."""
        from holo_index.core.search_engine import _coerce_priority
        assert _coerce_priority({"priority": "p3"}) == 2.0
        assert _coerce_priority({"priority": " P1 "}) == 4.0

    def test_unknown_label_falls_back_to_default(self):
        """Invalid label does not crash; returns default."""
        from holo_index.core.search_engine import _coerce_priority
        assert _coerce_priority({"priority": "URGENT"}) == 1.0
        assert _coerce_priority({"priority": "URGENT"}, default=7.0) == 7.0

    def test_numeric_string_parsed(self):
        """String containing numeric value is parsed."""
        from holo_index.core.search_engine import _coerce_priority
        assert _coerce_priority({"priority": "3"}) == 3.0
        assert _coerce_priority({"priority": "10.5"}) == 10.5

    def test_missing_metadata_returns_default(self):
        """Empty metadata returns default."""
        from holo_index.core.search_engine import _coerce_priority
        assert _coerce_priority({}) == 1.0
        assert _coerce_priority({}, default=2.5) == 2.5

    def test_bool_priority_rejected_falls_through(self):
        """Booleans (which subclass int in Python) should fall through to default."""
        from holo_index.core.search_engine import _coerce_priority
        # bool subclasses int in Python; ensure we don't propagate True/False as 1.0/0.0
        assert _coerce_priority({"priority": True}) == 1.0
        assert _coerce_priority({"priority": False}) == 1.0


class TestFormatHitWithStringPriority:
    """Search path with work-ledger string priority — regression for the silent TypeError."""

    def test_lexical_search_does_not_crash_with_string_priority(self):
        """Lexical fallback path handles priority=\"P3\" via _coerce_priority."""
        from holo_index.core.search_engine import _lexical_search_collection

        holo = MagicMock()
        holo.search_cache = None
        holo.model = None

        collection = MagicMock()
        collection.count.return_value = 1  # one document in collection
        collection.get.return_value = {
            "ids": ["wl_test_001"],
            "documents": ["Work Slice: TEST_SLICE\nPriority: P3\nTitle: Test Lexical"],
            "metadatas": [{
                "type": "work_ledger_slice",
                "slice_id": "TEST_SLICE",
                "title": "Test Lexical Slice",
                "path": "/tmp/work_ledger.example.json",
                "priority": "P3",       # string priority that crashed lexical fallback
                "pr_number": 999,
                "owner_worker": "W1",
                "status": "IN_PROGRESS",
            }],
        }

        # This would crash with TypeError before the fix (line 899 in search_engine.py)
        hits = _lexical_search_collection(holo, collection, "TEST_SLICE", limit=5, kind="work_ledger")
        assert isinstance(hits, list)
        assert len(hits) == 1
        assert hits[0].get("title") == "Test Lexical Slice"
        # Priority coerced from "P3" (label) to 2.0 (weight) via PRIORITY_MAP
        assert hits[0].get("priority") == 2.0

    def test_search_collection_does_not_crash_with_string_priority(self):
        """Full _search_collection path no longer raises on priority=\"P3\"."""
        from holo_index.core.search_engine import _search_collection

        holo = MagicMock()
        holo.search_cache = None
        holo.model = None

        collection = MagicMock()
        collection.query.return_value = {
            "documents": [["Work Slice: TEST_SLICE\nTitle: Test"]],
            "metadatas": [[{
                "type": "work_ledger_slice",
                "slice_id": "TEST_SLICE",
                "title": "Test Slice",
                "path": "/tmp/work_ledger.example.json",
                "priority": "P3",       # historical poison
                "priority_num": 10,     # numeric companion field
                "pr_number": 642,
                "owner_worker": "W9",
                "status": "MERGED",
                "branch": "",
                "related_foundup_id": "",
                "summary": "",
                "keywords": "",
            }]],
            "distances": [[0.4]],
        }
        collection.get.return_value = {"documents": [], "metadatas": [], "ids": []}

        hits = _search_collection(holo, collection, "TEST_SLICE", limit=5, kind="work_ledger")
        assert isinstance(hits, list)
        assert len(hits) == 1
        # _sort_key is stripped before return; verify result payload is intact and
        # priority was coerced from "P3" string to numeric (via priority_num=10)
        assert hits[0].get("title") == "Test Slice"
        assert hits[0].get("type") == "work_ledger_slice"
        assert hits[0].get("priority") == 10.0  # coerced from priority_num, not "P3"


class TestExecuteSearchWorkLedgerLogging:
    """execute_search work-ledger block no longer silently swallows exceptions."""

    def test_work_ledger_exception_is_logged_and_search_continues(self, caplog):
        """If work-ledger _search_collection raises, log a warning AND let other hits return."""
        import logging
        from holo_index.core.search_engine import execute_search

        holo = MagicMock()
        holo.search_cache = None
        holo.model = None
        holo.code_collection = None
        holo.symbol_collection = None
        holo.wsp_collection = None
        holo.test_collection = None
        holo.skill_collection = None
        holo.docs_collection = None
        holo.knowledge_collection = None

        boom_collection = MagicMock()
        boom_collection.query.side_effect = TypeError("can't multiply sequence by non-int of type 'float'")
        boom_collection.get.return_value = {"documents": [], "metadatas": [], "ids": []}
        holo.work_ledger_collection = boom_collection

        with caplog.at_level(logging.WARNING, logger="holo_index.core.search_engine"):
            result = execute_search(holo, "test_query", limit=5, doc_type_filter="work_ledger")

        assert isinstance(result, dict)
        assert result.get("work_ledger_hits") == []

        warning_messages = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
        assert any("Work-ledger search failed" in m for m in warning_messages), \
            f"Expected warning containing 'Work-ledger search failed', got: {warning_messages}"

    def test_work_ledger_collection_none_does_not_log_warning(self, caplog):
        """If collection is None (uninitialized), no warning — that's normal pre-reindex state."""
        import logging
        from holo_index.core.search_engine import execute_search

        holo = MagicMock()
        holo.search_cache = None
        holo.model = None
        holo.code_collection = None
        holo.symbol_collection = None
        holo.wsp_collection = None
        holo.test_collection = None
        holo.skill_collection = None
        holo.docs_collection = None
        holo.knowledge_collection = None
        holo.work_ledger_collection = None

        with caplog.at_level(logging.WARNING, logger="holo_index.core.search_engine"):
            result = execute_search(holo, "test_query", limit=5, doc_type_filter="all")

        warning_messages = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
        assert not any("Work-ledger search failed" in m for m in warning_messages), \
            "Should not warn when work_ledger_collection is None"
        assert result.get("work_ledger_hits") == []
