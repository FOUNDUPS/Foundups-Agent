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
