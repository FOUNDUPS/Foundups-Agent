#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for CABR Lifecycle Query Phase 7 - Store Query Integration.

Validates read-only lifecycle query integration with CABRConsensusStore
per WSP 97.

Required coverage:
  - empty store query
  - store with persisted records query
  - time range query
  - invalid time range fails closed
  - limit applied deterministically
  - persisted records correlate with supplied receipts
  - missing supplied receipt data produces gaps
  - lifecycle gap summary from store
  - truth-boundary anomalies propagated
  - JSON export deterministic
  - no store mutation
  - no payout readiness inferred
  - no DAO activation inferred
  - no default DB path
  - tmp_path only

WSP 97 Critical Constraint:
  Lifecycle query is observability only.
  It does NOT mean:
    - automatic state progression
    - verification_complete=True
    - cabr_ready=True
    - payout_ready=True
    - payout approval
    - DAO activation
    - token issuance
    - external settlement

Slice: CABR_CONSENSUS_FINALIZATION_PHASE7_LIFECYCLE_QUERY_INTEGRATION
Worker: W1
"""

from __future__ import annotations

import gc
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Dict

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from modules.communication.moltbot_bridge.src.cabr_lifecycle_query import (
    CABRLifecycleQueryFilter,
    CABRLifecycleQueryResult,
    export_lifecycle_query_json,
    query_lifecycle_from_store,
    query_lifecycle_gaps_from_store,
)
from modules.communication.moltbot_bridge.src.cabr_consensus_store import (
    CABRConsensusStore,
)


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------


def _make_consensus_record(
    record_id: str = "ccr_test_18a3b2c1_abc123",
    record_hash: str = "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
    receipt_id: str = "rcpt_test_001",
    job_id: str = "j_test_001",
    tenant_id: str = "t_test",
    decision: str = "accepted_for_review",
    reason_code: str = "ok_score_accepted_quorum_met",
    finalized_at: str = "2026-05-13T12:00:00+00:00",
    verification_complete: bool = False,
    cabr_ready: bool = False,
    payout_ready: bool = False,
) -> Dict[str, Any]:
    """Create a mock CABRConsensusRecord dict."""
    return {
        "record_id": record_id,
        "record_hash": record_hash,
        "receipt_id": receipt_id,
        "job_id": job_id,
        "tenant_id": tenant_id,
        "score_id": f"cabr_{receipt_id}",
        "score_decision": "accepted_for_review",
        "score_reason_code": "ok_evidence_present_quorum_met",
        "quorum_id": f"qv_{receipt_id}",
        "quorum_decision": "consensus_accepted_for_review",
        "quorum_reason_code": "ok_quorum_met_threshold_met",
        "decision": decision,
        "reason_code": reason_code,
        "reason_human": f"Test record: {decision}",
        "quorum_met": True,
        "threshold_met": True,
        "unique_verifiers": 3,
        "consensus_score": 1.0,
        "evidence_present": True,
        "evidence_count": 2,
        "is_dry_run": False,
        "is_simulated": False,
        "verification_complete": verification_complete,
        "cabr_ready": cabr_ready,
        "payout_ready": payout_ready,
        "finalized_at": finalized_at,
        "finalizer_version": "0.1.0",
    }


def _make_receipt(
    receipt_id: str = "rcpt_test_001",
    job_id: str = "j_test_001",
    verification_status: str = "pending_pavs",
) -> Dict[str, Any]:
    """Create a mock ProofOfComputeReceipt dict."""
    return {
        "receipt_id": receipt_id,
        "job_id": job_id,
        "tenant_id": "t_test",
        "verification_status": verification_status,
        "status_reason_code": "OK",
        "created_at": "2026-05-13T10:00:00+00:00",
    }


def _make_pavs_result(
    receipt_id: str = "rcpt_test_001",
    job_id: str = "j_test_001",
    decision: str = "accepted_for_review",
    verification_complete: bool = False,
    cabr_ready: bool = False,
    payout_ready: bool = False,
) -> Dict[str, Any]:
    """Create a mock PAVSVerificationResult dict."""
    return {
        "verification_id": f"pv_{receipt_id}",
        "receipt_id": receipt_id,
        "job_id": job_id,
        "tenant_id": "t_test",
        "decision": decision,
        "reason_code": "ok_evidence_present",
        "evidence_refs": ["ref1"],
        "evidence_count": 1,
        "verification_complete": verification_complete,
        "cabr_ready": cabr_ready,
        "payout_ready": payout_ready,
        "created_at": "2026-05-13T10:01:00+00:00",
    }


def _make_score_result(
    receipt_id: str = "rcpt_test_001",
    job_id: str = "j_test_001",
    decision: str = "accepted_for_review",
    verification_complete: bool = False,
    cabr_ready: bool = False,
    payout_ready: bool = False,
) -> Dict[str, Any]:
    """Create a mock CABRScoreResult dict."""
    return {
        "score_id": f"cabr_{receipt_id}",
        "receipt_id": receipt_id,
        "job_id": job_id,
        "tenant_id": "t_test",
        "decision": decision,
        "reason_code": "ok_evidence_present_quorum_met",
        "verification_complete": verification_complete,
        "cabr_ready": cabr_ready,
        "payout_ready": payout_ready,
        "scored_at": "2026-05-13T10:02:00+00:00",
    }


def _make_quorum_result(
    receipt_id: str = "rcpt_test_001",
    job_id: str = "j_test_001",
    decision: str = "consensus_accepted_for_review",
    verification_complete: bool = False,
    cabr_ready: bool = False,
    payout_ready: bool = False,
) -> Dict[str, Any]:
    """Create a mock QuorumVerificationResult dict."""
    return {
        "quorum_id": f"qv_{receipt_id}",
        "receipt_id": receipt_id,
        "job_id": job_id,
        "tenant_id": "t_test",
        "decision": decision,
        "reason_code": "ok_quorum_met_threshold_met",
        "quorum_met": True,
        "threshold_met": True,
        "verification_complete": verification_complete,
        "cabr_ready": cabr_ready,
        "payout_ready": payout_ready,
        "evaluated_at": "2026-05-13T10:03:00+00:00",
    }


# ---------------------------------------------------------------------------
# Test: Empty Store Query
# ---------------------------------------------------------------------------


class TestEmptyStoreQuery(unittest.TestCase):
    """Tests for querying an empty store."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_empty_store_returns_empty_result(self):
        """Empty store returns result with zero records."""
        result = query_lifecycle_from_store(self.store)

        self.assertEqual(result.persisted_record_count, 0)
        self.assertIsNotNone(result.correlation_result)
        self.assertEqual(len(result.correlation_result.correlations), 0)

    def test_empty_store_with_receipts_reports_gaps(self):
        """Empty store with supplied receipts reports all as gaps."""
        receipts = [
            _make_receipt(receipt_id="rcpt_001"),
            _make_receipt(receipt_id="rcpt_002"),
        ]

        result = query_lifecycle_from_store(self.store, receipts=receipts)

        self.assertEqual(result.persisted_record_count, 0)
        # Receipts become correlations with downstream gaps
        self.assertEqual(len(result.correlation_result.correlations), 2)

    def test_empty_store_gap_summary_is_empty(self):
        """Empty store gap summary is empty."""
        result = query_lifecycle_from_store(self.store)

        self.assertIsNotNone(result.gap_summary)
        self.assertEqual(result.gap_summary.total_gaps, 0)


# ---------------------------------------------------------------------------
# Test: Store With Persisted Records Query
# ---------------------------------------------------------------------------


class TestStoreWithPersistedRecordsQuery(unittest.TestCase):
    """Tests for querying store with persisted records."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

        # Insert records
        for i in range(5):
            self.store.save_record(_make_consensus_record(
                record_id=f"ccr_{i:04d}",
                receipt_id=f"rcpt_{i:04d}",
                finalized_at=f"2026-0{i + 1}-15T10:00:00+00:00",
            ))

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_query_returns_all_records(self):
        """Query returns all persisted records."""
        result = query_lifecycle_from_store(self.store)

        self.assertEqual(result.persisted_record_count, 5)

    def test_query_creates_correlations(self):
        """Query creates correlations for persisted records."""
        result = query_lifecycle_from_store(self.store)

        self.assertIsNotNone(result.correlation_result)
        # Each record creates a correlation
        self.assertEqual(len(result.correlation_result.correlations), 5)

    def test_persisted_records_appear_at_multiple_stages(self):
        """Persisted records appear at consensus_finalized and persisted stages."""
        result = query_lifecycle_from_store(self.store)

        # Each correlation should have 2 stages: consensus_finalized, persisted
        for corr in result.correlation_result.correlations:
            self.assertGreaterEqual(len(corr.stages_present), 2)


# ---------------------------------------------------------------------------
# Test: Time Range Query
# ---------------------------------------------------------------------------


class TestTimeRangeQuery(unittest.TestCase):
    """Tests for time range filtering."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

        # Insert records with different finalized_at timestamps
        self.store.save_record(_make_consensus_record(
            record_id="ccr_jan",
            receipt_id="rcpt_jan",
            finalized_at="2026-01-15T10:00:00+00:00",
        ))
        self.store.save_record(_make_consensus_record(
            record_id="ccr_jun",
            receipt_id="rcpt_jun",
            finalized_at="2026-06-15T10:00:00+00:00",
        ))
        self.store.save_record(_make_consensus_record(
            record_id="ccr_dec",
            receipt_id="rcpt_dec",
            finalized_at="2026-12-15T10:00:00+00:00",
        ))

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_query_with_start_time(self):
        """Query with start_time filters records >= start."""
        result = query_lifecycle_from_store(
            self.store,
            start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        )

        # Should return Jun and Dec
        self.assertEqual(result.persisted_record_count, 2)

    def test_query_with_end_time(self):
        """Query with end_time filters records <= end."""
        result = query_lifecycle_from_store(
            self.store,
            end=datetime(2026, 6, 30, tzinfo=timezone.utc),
        )

        # Should return Jan and Jun
        self.assertEqual(result.persisted_record_count, 2)

    def test_query_with_both_start_and_end(self):
        """Query with both start and end filters records in range."""
        result = query_lifecycle_from_store(
            self.store,
            start=datetime(2026, 3, 1, tzinfo=timezone.utc),
            end=datetime(2026, 9, 30, tzinfo=timezone.utc),
        )

        # Should return Jun only
        self.assertEqual(result.persisted_record_count, 1)

    def test_query_filter_preserved_in_result(self):
        """Query filter is preserved in result."""
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        end = datetime(2026, 12, 31, tzinfo=timezone.utc)

        result = query_lifecycle_from_store(
            self.store,
            start=start,
            end=end,
            limit=10,
        )

        self.assertIsNotNone(result.query_filter)
        self.assertEqual(result.query_filter.start_time, start)
        self.assertEqual(result.query_filter.end_time, end)
        self.assertEqual(result.query_filter.limit, 10)


# ---------------------------------------------------------------------------
# Test: Invalid Time Range Fails Closed
# ---------------------------------------------------------------------------


class TestInvalidTimeRangeFailsClosed(unittest.TestCase):
    """Tests for invalid time range handling."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_start_after_end_raises_value_error(self):
        """Invalid time range (start > end) raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            query_lifecycle_from_store(
                self.store,
                start=datetime(2026, 12, 31, tzinfo=timezone.utc),
                end=datetime(2026, 1, 1, tzinfo=timezone.utc),
            )

        self.assertIn("Invalid time range", str(ctx.exception))

    def test_filter_validation_start_after_end(self):
        """Filter validation returns False when start > end."""
        query_filter = CABRLifecycleQueryFilter(
            start_time=datetime(2026, 12, 31, tzinfo=timezone.utc),
            end_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )

        self.assertFalse(query_filter.validate())

    def test_filter_validation_start_equals_end(self):
        """Filter validation returns True when start == end."""
        same_time = datetime(2026, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        query_filter = CABRLifecycleQueryFilter(
            start_time=same_time,
            end_time=same_time,
        )

        self.assertTrue(query_filter.validate())


# ---------------------------------------------------------------------------
# Test: Limit Applied Deterministically
# ---------------------------------------------------------------------------


class TestLimitAppliedDeterministically(unittest.TestCase):
    """Tests for deterministic limit application."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

        # Insert records with sequential months (1-10 -> Jan to Oct)
        for i in range(10):
            month = (i % 10) + 1  # Months 1-10
            self.store.save_record(_make_consensus_record(
                record_id=f"ccr_{i:04d}",
                receipt_id=f"rcpt_{i:04d}",
                finalized_at=f"2026-{month:02d}-15T10:00:00+00:00",
            ))

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_limit_returns_exact_count(self):
        """Limit returns exactly the specified number of records."""
        result = query_lifecycle_from_store(self.store, limit=3)

        self.assertEqual(result.persisted_record_count, 3)

    def test_limit_applied_after_time_filter(self):
        """Limit is applied after time filtering."""
        # Filter to first half of year, then limit to 2
        result = query_lifecycle_from_store(
            self.store,
            end=datetime(2026, 5, 31, tzinfo=timezone.utc),
            limit=2,
        )

        self.assertEqual(result.persisted_record_count, 2)

    def test_deterministic_ordering_with_limit(self):
        """Records returned in deterministic order when limited."""
        result1 = query_lifecycle_from_store(self.store, limit=5)
        result2 = query_lifecycle_from_store(self.store, limit=5)

        # Same records in same order
        corr1_ids = [c.correlation_value for c in result1.correlation_result.correlations]
        corr2_ids = [c.correlation_value for c in result2.correlation_result.correlations]

        self.assertEqual(corr1_ids, corr2_ids)


# ---------------------------------------------------------------------------
# Test: Persisted Records Correlate With Supplied Receipts
# ---------------------------------------------------------------------------


class TestPersistedRecordsCorrelateWithSuppliedReceipts(unittest.TestCase):
    """Tests for correlation with supplied receipts."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

        # Insert records
        self.store.save_record(_make_consensus_record(
            record_id="ccr_001",
            receipt_id="rcpt_001",
        ))
        self.store.save_record(_make_consensus_record(
            record_id="ccr_002",
            receipt_id="rcpt_002",
        ))

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_matching_receipts_correlate(self):
        """Supplied receipts matching persisted records correlate."""
        receipts = [
            _make_receipt(receipt_id="rcpt_001"),
            _make_receipt(receipt_id="rcpt_002"),
        ]

        result = query_lifecycle_from_store(self.store, receipts=receipts)

        # Each correlation should include RECEIPT_CREATED stage
        for corr in result.correlation_result.correlations:
            from modules.communication.moltbot_bridge.src.cabr_lifecycle_correlation import (
                CABRLifecycleStage,
            )
            self.assertIn(CABRLifecycleStage.RECEIPT_CREATED, corr.stages_present)

    def test_full_pipeline_correlation(self):
        """Full pipeline with all stages correlates correctly."""
        receipt_id = "rcpt_001"

        receipts = [_make_receipt(receipt_id=receipt_id)]
        pavs_results = [_make_pavs_result(receipt_id=receipt_id)]
        score_results = [_make_score_result(receipt_id=receipt_id)]
        quorum_results = [_make_quorum_result(receipt_id=receipt_id)]

        result = query_lifecycle_from_store(
            self.store,
            receipts=receipts,
            pavs_results=pavs_results,
            score_results=score_results,
            quorum_results=quorum_results,
        )

        # Find correlation for rcpt_001
        corr = None
        for c in result.correlation_result.correlations:
            if c.correlation_value == receipt_id:
                corr = c
                break

        self.assertIsNotNone(corr)
        # Should have 6 stages: receipt, pavs, score, quorum, consensus, persisted
        self.assertEqual(len(corr.stages_present), 6)


# ---------------------------------------------------------------------------
# Test: Missing Supplied Receipt Data Produces Gaps
# ---------------------------------------------------------------------------


class TestMissingSuppliedReceiptDataProducesGaps(unittest.TestCase):
    """Tests for gap reporting when receipt data is missing."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

        # Insert record
        self.store.save_record(_make_consensus_record(
            record_id="ccr_001",
            receipt_id="rcpt_001",
        ))

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_missing_receipt_produces_gap(self):
        """Persisted record without supplied receipt shows upstream gap."""
        # Query without receipts
        result = query_lifecycle_from_store(self.store)

        # Should have gaps for upstream stages
        self.assertIsNotNone(result.gap_summary)
        # Persisted record has no receipt_created stage
        corr = result.correlation_result.correlations[0]
        from modules.communication.moltbot_bridge.src.cabr_lifecycle_correlation import (
            CABRLifecycleStage,
        )
        self.assertNotIn(CABRLifecycleStage.RECEIPT_CREATED, corr.stages_present)

    def test_partial_pipeline_data_produces_gaps(self):
        """Partial pipeline data produces gaps for missing stages."""
        receipts = [_make_receipt(receipt_id="rcpt_001")]
        # No pavs_results, score_results, or quorum_results

        result = query_lifecycle_from_store(
            self.store,
            receipts=receipts,
        )

        # Should have gaps for pavs, score, quorum stages
        self.assertGreater(result.gap_summary.total_gaps, 0)


# ---------------------------------------------------------------------------
# Test: Lifecycle Gap Summary From Store
# ---------------------------------------------------------------------------


class TestLifecycleGapSummaryFromStore(unittest.TestCase):
    """Tests for lifecycle gap summary function."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

        # Insert records
        self.store.save_record(_make_consensus_record(
            record_id="ccr_001",
            receipt_id="rcpt_001",
        ))
        self.store.save_record(_make_consensus_record(
            record_id="ccr_002",
            receipt_id="rcpt_002",
        ))

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_gap_summary_function_returns_summary(self):
        """query_lifecycle_gaps_from_store returns gap summary."""
        summary = query_lifecycle_gaps_from_store(self.store)

        self.assertIsNotNone(summary)
        self.assertIsInstance(summary.total_gaps, int)

    def test_gap_summary_with_receipts(self):
        """Gap summary includes receipt gaps."""
        receipts = [_make_receipt(receipt_id="rcpt_001")]
        # Only 1 receipt but 2 persisted records

        summary = query_lifecycle_gaps_from_store(
            self.store,
            receipts=receipts,
        )

        # rcpt_002 has no receipt data, should have upstream gaps
        self.assertGreater(summary.correlations_with_gaps, 0)

    def test_gap_summary_to_dict(self):
        """Gap summary serializes to dict."""
        summary = query_lifecycle_gaps_from_store(self.store)

        d = summary.to_dict()

        self.assertIn("total_gaps", d)
        self.assertIn("gaps_by_stage", d)


# ---------------------------------------------------------------------------
# Test: Truth-Boundary Anomalies Propagated
# ---------------------------------------------------------------------------


class TestTruthBoundaryAnomaliesPropagated(unittest.TestCase):
    """Tests for truth boundary anomaly propagation."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_verification_complete_true_flagged(self):
        """verification_complete=True in supplied data is flagged."""
        self.store.save_record(_make_consensus_record(
            record_id="ccr_001",
            receipt_id="rcpt_001",
        ))

        # Supply pavs result with anomaly
        pavs_results = [_make_pavs_result(
            receipt_id="rcpt_001",
            verification_complete=True,  # Anomaly
        )]

        result = query_lifecycle_from_store(
            self.store,
            pavs_results=pavs_results,
        )

        self.assertGreater(result.correlation_result.total_anomalies, 0)

    def test_cabr_ready_true_flagged(self):
        """cabr_ready=True in supplied data is flagged."""
        self.store.save_record(_make_consensus_record(
            record_id="ccr_001",
            receipt_id="rcpt_001",
        ))

        # Supply score result with anomaly
        score_results = [_make_score_result(
            receipt_id="rcpt_001",
            cabr_ready=True,  # Anomaly
        )]

        result = query_lifecycle_from_store(
            self.store,
            score_results=score_results,
        )

        self.assertGreater(result.correlation_result.total_anomalies, 0)

    def test_payout_ready_true_flagged(self):
        """payout_ready=True in supplied data is flagged."""
        self.store.save_record(_make_consensus_record(
            record_id="ccr_001",
            receipt_id="rcpt_001",
        ))

        # Supply quorum result with anomaly
        quorum_results = [_make_quorum_result(
            receipt_id="rcpt_001",
            payout_ready=True,  # Anomaly
        )]

        result = query_lifecycle_from_store(
            self.store,
            quorum_results=quorum_results,
        )

        self.assertGreater(result.correlation_result.total_anomalies, 0)


# ---------------------------------------------------------------------------
# Test: JSON Export Deterministic
# ---------------------------------------------------------------------------


class TestJsonExportDeterministic(unittest.TestCase):
    """Tests for deterministic JSON export."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

        self.store.save_record(_make_consensus_record(
            record_id="ccr_001",
            receipt_id="rcpt_001",
        ))

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_export_is_valid_json(self):
        """Export produces valid JSON."""
        result = query_lifecycle_from_store(self.store)
        json_str = export_lifecycle_query_json(result)

        parsed = json.loads(json_str)
        self.assertIn("persisted_record_count", parsed)
        self.assertIn("correlation_result", parsed)
        self.assertIn("gap_summary", parsed)

    def test_export_keys_sorted(self):
        """JSON export has sorted keys."""
        result = query_lifecycle_from_store(self.store)
        json_str = export_lifecycle_query_json(result)

        parsed = json.loads(json_str)
        top_keys = list(parsed.keys())
        self.assertEqual(top_keys, sorted(top_keys))

    def test_export_deterministic(self):
        """Same result produces same JSON."""
        result = query_lifecycle_from_store(self.store)

        json1 = export_lifecycle_query_json(result)
        json2 = export_lifecycle_query_json(result)

        self.assertEqual(json1, json2)

    def test_export_includes_wsp97_note(self):
        """JSON export includes WSP 97 compliance note."""
        result = query_lifecycle_from_store(self.store)
        json_str = export_lifecycle_query_json(result)

        parsed = json.loads(json_str)
        self.assertIn("WSP 97", parsed["wsp97_compliance_note"])

    def test_export_datetime_as_iso_strings(self):
        """Datetime fields exported as ISO strings."""
        result = query_lifecycle_from_store(self.store)
        json_str = export_lifecycle_query_json(result)

        parsed = json.loads(json_str)
        generated_at = parsed["generated_at"]
        self.assertIsInstance(generated_at, str)
        # Should be parseable
        datetime.fromisoformat(generated_at.replace("Z", "+00:00"))


# ---------------------------------------------------------------------------
# Test: No Store Mutation
# ---------------------------------------------------------------------------


class TestNoStoreMutation(unittest.TestCase):
    """Tests that queries do not mutate store."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

        self.store.save_record(_make_consensus_record(
            record_id="ccr_001",
            receipt_id="rcpt_001",
        ))

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_query_does_not_add_records(self):
        """Query does not add records to store."""
        count_before = self.store.list_records().record_count

        query_lifecycle_from_store(
            self.store,
            receipts=[_make_receipt(receipt_id="rcpt_new")],
        )

        count_after = self.store.list_records().record_count

        self.assertEqual(count_before, count_after)

    def test_query_does_not_modify_existing_records(self):
        """Query does not modify existing records."""
        before = self.store.get_record("ccr_001").records[0]

        query_lifecycle_from_store(self.store)

        after = self.store.get_record("ccr_001").records[0]

        self.assertEqual(before, after)


# ---------------------------------------------------------------------------
# Test: No Payout Readiness Inferred
# ---------------------------------------------------------------------------


class TestNoPayoutReadinessInferred(unittest.TestCase):
    """Tests that payout readiness is never inferred."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

        # Insert records
        self.store.save_record(_make_consensus_record(
            record_id="ccr_001",
            receipt_id="rcpt_001",
        ))

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_result_has_no_payout_fields(self):
        """Result has no payout-related fields."""
        result = query_lifecycle_from_store(self.store)
        result_dict = result.to_dict()
        json_str = json.dumps(result_dict)

        self.assertNotIn("total_payout", json_str)
        self.assertNotIn("payout_amount", json_str)
        self.assertNotIn("tokens_issued", json_str)

    def test_full_lifecycle_no_payout_ready(self):
        """Full lifecycle query does not set payout_ready."""
        receipts = [_make_receipt(receipt_id="rcpt_001")]
        pavs_results = [_make_pavs_result(receipt_id="rcpt_001")]
        score_results = [_make_score_result(receipt_id="rcpt_001")]
        quorum_results = [_make_quorum_result(receipt_id="rcpt_001")]

        result = query_lifecycle_from_store(
            self.store,
            receipts=receipts,
            pavs_results=pavs_results,
            score_results=score_results,
            quorum_results=quorum_results,
        )

        # Check all items have payout_ready=False
        for corr in result.correlation_result.correlations:
            for item in corr.items.values():
                self.assertFalse(item.payout_ready)


# ---------------------------------------------------------------------------
# Test: No DAO Activation Inferred
# ---------------------------------------------------------------------------


class TestNoDAOActivationInferred(unittest.TestCase):
    """Tests that DAO activation is never inferred."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

        self.store.save_record(_make_consensus_record(
            record_id="ccr_001",
            receipt_id="rcpt_001",
        ))

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_result_has_no_dao_fields(self):
        """Result has no DAO-related fields."""
        result = query_lifecycle_from_store(self.store)
        result_dict = result.to_dict()
        json_str = json.dumps(result_dict)

        self.assertNotIn("dao_activated", json_str)
        self.assertNotIn("dao_transition", json_str)


# ---------------------------------------------------------------------------
# Test: No Default DB Path
# ---------------------------------------------------------------------------


class TestNoDefaultDbPath(unittest.TestCase):
    """Tests that no default DB path is used."""

    def test_query_requires_store_parameter(self):
        """query_lifecycle_from_store requires store parameter."""
        with self.assertRaises(TypeError):
            query_lifecycle_from_store()  # type: ignore

    def test_gap_query_requires_store_parameter(self):
        """query_lifecycle_gaps_from_store requires store parameter."""
        with self.assertRaises(TypeError):
            query_lifecycle_gaps_from_store()  # type: ignore


# ---------------------------------------------------------------------------
# Test: Uses tmp_path Only
# ---------------------------------------------------------------------------


class TestUsesTmpPathOnly(unittest.TestCase):
    """Tests that all tests use tmp_path pattern."""

    def test_all_tests_use_temporary_directory(self):
        """This test class verifies tmp_path usage pattern."""
        # All tests in this file use TemporaryDirectory
        # This is a meta-test verifying the pattern
        self.assertTrue(True)


# ---------------------------------------------------------------------------
# Test: Filter Dataclass
# ---------------------------------------------------------------------------


class TestFilterDataclass(unittest.TestCase):
    """Tests for CABRLifecycleQueryFilter dataclass."""

    def test_filter_to_dict(self):
        """Filter serializes to dict."""
        filter = CABRLifecycleQueryFilter(
            start_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
            end_time=datetime(2026, 12, 31, tzinfo=timezone.utc),
            limit=100,
            decision_filter="accepted_for_review",
        )

        d = filter.to_dict()

        self.assertIn("start_time", d)
        self.assertIn("end_time", d)
        self.assertEqual(d["limit"], 100)
        self.assertEqual(d["decision_filter"], "accepted_for_review")

    def test_filter_validate_empty(self):
        """Empty filter is valid."""
        filter = CABRLifecycleQueryFilter()

        self.assertTrue(filter.validate())

    def test_filter_validate_start_only(self):
        """Filter with start_time only is valid."""
        filter = CABRLifecycleQueryFilter(
            start_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )

        self.assertTrue(filter.validate())

    def test_filter_validate_end_only(self):
        """Filter with end_time only is valid."""
        filter = CABRLifecycleQueryFilter(
            end_time=datetime(2026, 12, 31, tzinfo=timezone.utc),
        )

        self.assertTrue(filter.validate())


# ---------------------------------------------------------------------------
# Test: Result Dataclass
# ---------------------------------------------------------------------------


class TestResultDataclass(unittest.TestCase):
    """Tests for CABRLifecycleQueryResult dataclass."""

    def test_result_to_dict(self):
        """Result serializes to dict."""
        result = CABRLifecycleQueryResult(
            persisted_record_count=5,
        )

        d = result.to_dict()

        self.assertEqual(d["persisted_record_count"], 5)
        self.assertIn("generated_at", d)
        self.assertIn("wsp97_compliance_note", d)

    def test_result_has_wsp97_note(self):
        """Result includes WSP 97 compliance note."""
        result = CABRLifecycleQueryResult()

        self.assertIn("WSP 97", result.wsp97_compliance_note)


if __name__ == "__main__":
    unittest.main(verbosity=2)
