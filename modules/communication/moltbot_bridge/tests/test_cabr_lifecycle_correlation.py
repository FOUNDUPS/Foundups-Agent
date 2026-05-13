#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for CABR Lifecycle Correlation Phase 6 - Full Pipeline Stage Correlation.

Validates read-only lifecycle correlation across all CABR consensus stages
per WSP 97.

Required coverage:
  - Receipt only -> downstream gaps reported
  - Receipt + pAVS -> scoring/quorum/finalization gaps reported
  - Full lifecycle correlation across all stages
  - Correlation by receipt_id
  - Correlation by job_id fallback
  - Correlation by record_hash where applicable
  - Duplicate records deterministic
  - Missing stage reported, not inferred
  - Truth-boundary anomaly flagged
  - Deterministic JSON export
  - No store mutation
  - No payout readiness inferred
  - No DAO activation inferred
  - No default DB path

WSP 97 Critical Constraint:
  Lifecycle correlation is observability only.
  It does NOT mean:
    - automatic state progression
    - verification_complete=True
    - cabr_ready=True
    - payout_ready=True
    - payout approval
    - DAO activation
    - token issuance
    - external settlement

Slice: CABR_CONSENSUS_FINALIZATION_PHASE6_RECEIPT_LIFECYCLE_CORRELATION
Worker: W1
"""

from __future__ import annotations

import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from modules.communication.moltbot_bridge.src.cabr_lifecycle_correlation import (
    CABRLifecycleCorrelation,
    CABRLifecycleCorrelationResult,
    CABRLifecycleGap,
    CABRLifecycleGapSummary,
    CABRLifecycleItem,
    CABRLifecycleStage,
    LIFECYCLE_STAGE_ORDER,
    correlate_cabr_lifecycle,
    export_lifecycle_correlation_json,
    summarize_lifecycle_gaps,
)


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------


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


def _make_consensus_record(
    receipt_id: str = "rcpt_test_001",
    job_id: str = "j_test_001",
    record_id: str = "ccr_test_001",
    record_hash: str = "a1b2c3d4e5f6",
    decision: str = "accepted_for_review",
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
        "tenant_id": "t_test",
        "decision": decision,
        "reason_code": "ok_score_accepted_quorum_met",
        "verification_complete": verification_complete,
        "cabr_ready": cabr_ready,
        "payout_ready": payout_ready,
        "finalized_at": "2026-05-13T10:04:00+00:00",
    }


def _make_persisted_record(
    receipt_id: str = "rcpt_test_001",
    job_id: str = "j_test_001",
    record_id: str = "ccr_test_001",
    record_hash: str = "a1b2c3d4e5f6",
    decision: str = "accepted_for_review",
    verification_complete: bool = False,
    cabr_ready: bool = False,
    payout_ready: bool = False,
) -> Dict[str, Any]:
    """Create a mock persisted CABRConsensusRecord dict."""
    record = _make_consensus_record(
        receipt_id=receipt_id,
        job_id=job_id,
        record_id=record_id,
        record_hash=record_hash,
        decision=decision,
        verification_complete=verification_complete,
        cabr_ready=cabr_ready,
        payout_ready=payout_ready,
    )
    record["stored_at"] = "2026-05-13T10:05:00+00:00"
    return record


def _make_reported_record(
    receipt_id: str = "rcpt_test_001",
    job_id: str = "j_test_001",
    record_id: str = "ccr_test_001",
    record_hash: str = "a1b2c3d4e5f6",
    decision: str = "accepted_for_review",
    verification_complete: bool = False,
    cabr_ready: bool = False,
    payout_ready: bool = False,
) -> Dict[str, Any]:
    """Create a mock reported CABRConsensusRecord dict."""
    record = _make_persisted_record(
        receipt_id=receipt_id,
        job_id=job_id,
        record_id=record_id,
        record_hash=record_hash,
        decision=decision,
        verification_complete=verification_complete,
        cabr_ready=cabr_ready,
        payout_ready=payout_ready,
    )
    return record


# ---------------------------------------------------------------------------
# Test: Lifecycle Stage Enum
# ---------------------------------------------------------------------------


class TestLifecycleStageEnum(unittest.TestCase):
    """Lifecycle stage enum tests."""

    def test_stage_order_length(self):
        """Stage order has 7 stages."""
        self.assertEqual(len(LIFECYCLE_STAGE_ORDER), 7)

    def test_stage_order_starts_with_receipt(self):
        """First stage is RECEIPT_CREATED."""
        self.assertEqual(
            LIFECYCLE_STAGE_ORDER[0],
            CABRLifecycleStage.RECEIPT_CREATED,
        )

    def test_stage_order_ends_with_reported(self):
        """Last stage is REPORTED."""
        self.assertEqual(
            LIFECYCLE_STAGE_ORDER[-1],
            CABRLifecycleStage.REPORTED,
        )

    def test_all_stages_in_order(self):
        """All stages are in LIFECYCLE_STAGE_ORDER."""
        expected_stages = [
            CABRLifecycleStage.RECEIPT_CREATED,
            CABRLifecycleStage.PAVS_EVALUATED,
            CABRLifecycleStage.CABR_SCORED,
            CABRLifecycleStage.QUORUM_EVALUATED,
            CABRLifecycleStage.CONSENSUS_FINALIZED,
            CABRLifecycleStage.PERSISTED,
            CABRLifecycleStage.REPORTED,
        ]
        self.assertEqual(LIFECYCLE_STAGE_ORDER, expected_stages)


# ---------------------------------------------------------------------------
# Test: Receipt Only -> Downstream Gaps
# ---------------------------------------------------------------------------


class TestReceiptOnlyDownstreamGaps(unittest.TestCase):
    """Tests for receipt only with downstream gaps."""

    def test_receipt_only_reports_all_downstream_gaps(self):
        """Receipt only -> 6 downstream gaps reported."""
        receipts = [_make_receipt()]
        result = correlate_cabr_lifecycle(receipts=receipts)

        self.assertEqual(len(result.correlations), 1)
        correlation = result.correlations[0]

        # Should have RECEIPT_CREATED present
        self.assertIn(CABRLifecycleStage.RECEIPT_CREATED, correlation.stages_present)
        self.assertEqual(len(correlation.stages_present), 1)

        # Should report 6 downstream gaps
        self.assertEqual(len(correlation.gaps), 6)
        gap_stages = [g.missing_stage for g in correlation.gaps]
        self.assertIn(CABRLifecycleStage.PAVS_EVALUATED, gap_stages)
        self.assertIn(CABRLifecycleStage.CABR_SCORED, gap_stages)
        self.assertIn(CABRLifecycleStage.QUORUM_EVALUATED, gap_stages)
        self.assertIn(CABRLifecycleStage.CONSENSUS_FINALIZED, gap_stages)
        self.assertIn(CABRLifecycleStage.PERSISTED, gap_stages)
        self.assertIn(CABRLifecycleStage.REPORTED, gap_stages)

    def test_receipt_only_gap_type_is_missing_downstream(self):
        """Gap type is 'missing_downstream'."""
        receipts = [_make_receipt()]
        result = correlate_cabr_lifecycle(receipts=receipts)

        for gap in result.correlations[0].gaps:
            self.assertEqual(gap.gap_type, "missing_downstream")

    def test_receipt_only_correlation_key_is_receipt_id(self):
        """Correlation key is receipt_id."""
        receipts = [_make_receipt(receipt_id="rcpt_unique_001")]
        result = correlate_cabr_lifecycle(receipts=receipts)

        self.assertEqual(result.correlations[0].correlation_key, "receipt_id")
        self.assertEqual(result.correlations[0].correlation_value, "rcpt_unique_001")


# ---------------------------------------------------------------------------
# Test: Receipt + pAVS -> Remaining Gaps
# ---------------------------------------------------------------------------


class TestReceiptPlusPayvsGaps(unittest.TestCase):
    """Tests for receipt + pAVS with remaining gaps."""

    def test_receipt_plus_pavs_reports_remaining_gaps(self):
        """Receipt + pAVS -> 5 downstream gaps (scoring onward)."""
        receipt_id = "rcpt_001"
        receipts = [_make_receipt(receipt_id=receipt_id)]
        pavs_results = [_make_pavs_result(receipt_id=receipt_id)]

        result = correlate_cabr_lifecycle(
            receipts=receipts,
            pavs_results=pavs_results,
        )

        self.assertEqual(len(result.correlations), 1)
        correlation = result.correlations[0]

        # Should have 2 stages present
        self.assertEqual(len(correlation.stages_present), 2)
        self.assertIn(CABRLifecycleStage.RECEIPT_CREATED, correlation.stages_present)
        self.assertIn(CABRLifecycleStage.PAVS_EVALUATED, correlation.stages_present)

        # Should report 5 downstream gaps
        self.assertEqual(len(correlation.gaps), 5)
        gap_stages = [g.missing_stage for g in correlation.gaps]
        self.assertNotIn(CABRLifecycleStage.RECEIPT_CREATED, gap_stages)
        self.assertNotIn(CABRLifecycleStage.PAVS_EVALUATED, gap_stages)
        self.assertIn(CABRLifecycleStage.CABR_SCORED, gap_stages)


# ---------------------------------------------------------------------------
# Test: Full Lifecycle Correlation
# ---------------------------------------------------------------------------


class TestFullLifecycleCorrelation(unittest.TestCase):
    """Tests for full lifecycle correlation across all stages."""

    def test_full_lifecycle_no_gaps(self):
        """Full lifecycle with all stages -> no gaps."""
        receipt_id = "rcpt_full"
        job_id = "j_full"
        record_id = "ccr_full"

        result = correlate_cabr_lifecycle(
            receipts=[_make_receipt(receipt_id=receipt_id, job_id=job_id)],
            pavs_results=[_make_pavs_result(receipt_id=receipt_id, job_id=job_id)],
            score_results=[_make_score_result(receipt_id=receipt_id, job_id=job_id)],
            quorum_results=[_make_quorum_result(receipt_id=receipt_id, job_id=job_id)],
            consensus_records=[_make_consensus_record(
                receipt_id=receipt_id, job_id=job_id, record_id=record_id
            )],
            persisted_records=[_make_persisted_record(
                receipt_id=receipt_id, job_id=job_id, record_id=record_id
            )],
            reported_records=[_make_reported_record(
                receipt_id=receipt_id, job_id=job_id, record_id=record_id
            )],
        )

        self.assertEqual(len(result.correlations), 1)
        correlation = result.correlations[0]

        # All 7 stages present
        self.assertEqual(len(correlation.stages_present), 7)

        # No gaps
        self.assertEqual(len(correlation.gaps), 0)
        self.assertEqual(result.total_gaps, 0)

    def test_full_lifecycle_items_by_stage(self):
        """Full lifecycle records items per stage."""
        receipt_id = "rcpt_full"
        job_id = "j_full"
        record_id = "ccr_full"

        result = correlate_cabr_lifecycle(
            receipts=[_make_receipt(receipt_id=receipt_id, job_id=job_id)],
            pavs_results=[_make_pavs_result(receipt_id=receipt_id, job_id=job_id)],
            score_results=[_make_score_result(receipt_id=receipt_id, job_id=job_id)],
            quorum_results=[_make_quorum_result(receipt_id=receipt_id, job_id=job_id)],
            consensus_records=[_make_consensus_record(
                receipt_id=receipt_id, job_id=job_id, record_id=record_id
            )],
            persisted_records=[_make_persisted_record(
                receipt_id=receipt_id, job_id=job_id, record_id=record_id
            )],
            reported_records=[_make_reported_record(
                receipt_id=receipt_id, job_id=job_id, record_id=record_id
            )],
        )

        # Should have 7 total items
        self.assertEqual(result.total_items, 7)

        # Each stage should have 1 item
        for stage in LIFECYCLE_STAGE_ORDER:
            self.assertEqual(result.items_by_stage.get(stage.value, 0), 1)


# ---------------------------------------------------------------------------
# Test: Correlation by receipt_id
# ---------------------------------------------------------------------------


class TestCorrelationByReceiptId(unittest.TestCase):
    """Tests for correlation by receipt_id."""

    def test_correlation_by_receipt_id(self):
        """Items with same receipt_id are correlated."""
        receipt_id = "rcpt_shared"
        job_id_1 = "j_001"
        job_id_2 = "j_002"  # Different job_id but same receipt_id

        result = correlate_cabr_lifecycle(
            receipts=[_make_receipt(receipt_id=receipt_id, job_id=job_id_1)],
            pavs_results=[_make_pavs_result(receipt_id=receipt_id, job_id=job_id_2)],
        )

        # Should be correlated by receipt_id
        self.assertEqual(len(result.correlations), 1)
        self.assertEqual(result.correlations[0].correlation_key, "receipt_id")
        self.assertEqual(result.correlations[0].correlation_value, receipt_id)

    def test_different_receipt_ids_not_correlated(self):
        """Items with different receipt_ids are not correlated."""
        result = correlate_cabr_lifecycle(
            receipts=[
                _make_receipt(receipt_id="rcpt_001"),
                _make_receipt(receipt_id="rcpt_002"),
            ],
        )

        # Should have 2 separate correlations
        self.assertEqual(len(result.correlations), 2)


# ---------------------------------------------------------------------------
# Test: Correlation by job_id Fallback
# ---------------------------------------------------------------------------


class TestCorrelationByJobIdFallback(unittest.TestCase):
    """Tests for correlation by job_id when receipt_id is missing."""

    def test_correlation_by_job_id_fallback(self):
        """Items with same job_id but no receipt_id are correlated."""
        job_id = "j_shared"

        # Create items without receipt_id
        receipt = _make_receipt(job_id=job_id)
        receipt["receipt_id"] = None

        pavs = _make_pavs_result(job_id=job_id)
        pavs["receipt_id"] = None

        result = correlate_cabr_lifecycle(
            receipts=[receipt],
            pavs_results=[pavs],
        )

        # Should be correlated by job_id
        self.assertEqual(len(result.correlations), 1)
        self.assertEqual(result.correlations[0].correlation_key, "job_id")
        self.assertEqual(result.correlations[0].correlation_value, job_id)


# ---------------------------------------------------------------------------
# Test: Correlation by record_hash
# ---------------------------------------------------------------------------


class TestCorrelationByRecordHash(unittest.TestCase):
    """Tests for correlation by record_hash."""

    def test_consensus_records_have_record_hash(self):
        """Consensus records include record_hash in item."""
        result = correlate_cabr_lifecycle(
            consensus_records=[_make_consensus_record(record_hash="abc123")],
        )

        self.assertEqual(len(result.correlations), 1)
        item = result.correlations[0].items.get("consensus_finalized")
        self.assertIsNotNone(item)
        self.assertEqual(item.record_hash, "abc123")


# ---------------------------------------------------------------------------
# Test: Duplicate Records Deterministic
# ---------------------------------------------------------------------------


class TestDuplicateRecordsDeterministic(unittest.TestCase):
    """Tests for deterministic duplicate handling."""

    def test_duplicate_receipts_first_wins(self):
        """First receipt is used when duplicates exist."""
        receipt_id = "rcpt_dup"

        receipt1 = _make_receipt(receipt_id=receipt_id)
        receipt1["created_at"] = "2026-05-13T10:00:00+00:00"

        receipt2 = _make_receipt(receipt_id=receipt_id)
        receipt2["created_at"] = "2026-05-13T11:00:00+00:00"

        result = correlate_cabr_lifecycle(
            receipts=[receipt1, receipt2],
        )

        # Should have 1 correlation
        self.assertEqual(len(result.correlations), 1)

        # First item wins (10:00)
        item = result.correlations[0].items.get("receipt_created")
        self.assertIsNotNone(item)
        self.assertEqual(
            item.timestamp,
            datetime(2026, 5, 13, 10, 0, 0, tzinfo=timezone.utc),
        )

    def test_total_items_counts_all_including_duplicates(self):
        """Total items counts all input items."""
        receipt_id = "rcpt_dup"

        result = correlate_cabr_lifecycle(
            receipts=[
                _make_receipt(receipt_id=receipt_id),
                _make_receipt(receipt_id=receipt_id),
                _make_receipt(receipt_id=receipt_id),
            ],
        )

        # All 3 receipts are counted
        self.assertEqual(result.total_items, 3)

        # But only 1 correlation (first wins)
        self.assertEqual(len(result.correlations), 1)


# ---------------------------------------------------------------------------
# Test: Missing Stage Reported, Not Inferred
# ---------------------------------------------------------------------------


class TestMissingStageReportedNotInferred(unittest.TestCase):
    """Tests that missing stages are reported, not inferred."""

    def test_missing_stage_in_gaps(self):
        """Missing intermediate stage appears in gaps."""
        receipt_id = "rcpt_skip"

        # Receipt -> Score (skip pAVS)
        result = correlate_cabr_lifecycle(
            receipts=[_make_receipt(receipt_id=receipt_id)],
            score_results=[_make_score_result(receipt_id=receipt_id)],
        )

        # Should have 1 correlation
        self.assertEqual(len(result.correlations), 1)
        correlation = result.correlations[0]

        # Receipt and Score present
        self.assertIn(CABRLifecycleStage.RECEIPT_CREATED, correlation.stages_present)
        self.assertIn(CABRLifecycleStage.CABR_SCORED, correlation.stages_present)

        # pAVS in missing stages
        self.assertIn(CABRLifecycleStage.PAVS_EVALUATED, correlation.stages_missing)

    def test_missing_stage_not_inferred_as_failure(self):
        """Missing stage gap does not imply failure."""
        result = correlate_cabr_lifecycle(
            receipts=[_make_receipt()],
        )

        # Gaps exist but no failure field
        self.assertTrue(len(result.correlations[0].gaps) > 0)
        # Result has no failure indicator
        result_dict = result.to_dict()
        self.assertNotIn("failure", result_dict)
        self.assertNotIn("failed", result_dict)


# ---------------------------------------------------------------------------
# Test: Truth-Boundary Anomaly Flagged
# ---------------------------------------------------------------------------


class TestTruthBoundaryAnomalyFlagged(unittest.TestCase):
    """Tests for truth boundary anomaly detection."""

    def test_verification_complete_true_flagged(self):
        """verification_complete=True is flagged as anomaly."""
        result = correlate_cabr_lifecycle(
            pavs_results=[_make_pavs_result(verification_complete=True)],
        )

        correlation = result.correlations[0]
        self.assertTrue(correlation.has_truth_boundary_anomaly)
        self.assertTrue(len(correlation.anomaly_details) > 0)
        self.assertIn("verification_complete=True", correlation.anomaly_details[0])

    def test_cabr_ready_true_flagged(self):
        """cabr_ready=True is flagged as anomaly."""
        result = correlate_cabr_lifecycle(
            score_results=[_make_score_result(cabr_ready=True)],
        )

        correlation = result.correlations[0]
        self.assertTrue(correlation.has_truth_boundary_anomaly)
        self.assertIn("cabr_ready=True", " ".join(correlation.anomaly_details))

    def test_payout_ready_true_flagged(self):
        """payout_ready=True is flagged as anomaly."""
        result = correlate_cabr_lifecycle(
            consensus_records=[_make_consensus_record(payout_ready=True)],
        )

        correlation = result.correlations[0]
        self.assertTrue(correlation.has_truth_boundary_anomaly)
        self.assertIn("payout_ready=True", " ".join(correlation.anomaly_details))

    def test_no_anomaly_when_all_false(self):
        """No anomaly when all truth fields are False."""
        result = correlate_cabr_lifecycle(
            receipts=[_make_receipt()],
            pavs_results=[_make_pavs_result(
                verification_complete=False,
                cabr_ready=False,
                payout_ready=False,
            )],
        )

        correlation = result.correlations[0]
        self.assertFalse(correlation.has_truth_boundary_anomaly)
        self.assertEqual(len(correlation.anomaly_details), 0)

    def test_total_anomalies_counted(self):
        """Total anomalies are counted in result."""
        result = correlate_cabr_lifecycle(
            pavs_results=[
                _make_pavs_result(
                    receipt_id="rcpt_001",
                    verification_complete=True,
                    cabr_ready=True,
                    payout_ready=True,
                ),
            ],
        )

        # 3 anomalies (verification_complete, cabr_ready, payout_ready)
        self.assertEqual(result.total_anomalies, 3)


# ---------------------------------------------------------------------------
# Test: Deterministic JSON Export
# ---------------------------------------------------------------------------


class TestDeterministicJsonExport(unittest.TestCase):
    """Tests for deterministic JSON export."""

    def test_export_is_valid_json(self):
        """Export produces valid JSON."""
        result = correlate_cabr_lifecycle(
            receipts=[_make_receipt()],
        )
        json_str = export_lifecycle_correlation_json(result)

        parsed = json.loads(json_str)
        self.assertIn("correlations", parsed)
        self.assertIn("total_items", parsed)
        self.assertIn("total_gaps", parsed)

    def test_export_keys_sorted(self):
        """JSON export has sorted keys."""
        result = correlate_cabr_lifecycle(
            receipts=[_make_receipt()],
        )
        json_str = export_lifecycle_correlation_json(result)

        parsed = json.loads(json_str)
        top_keys = list(parsed.keys())
        self.assertEqual(top_keys, sorted(top_keys))

    def test_export_deterministic(self):
        """Same result produces same JSON."""
        result = correlate_cabr_lifecycle(
            receipts=[_make_receipt()],
            pavs_results=[_make_pavs_result()],
        )

        json1 = export_lifecycle_correlation_json(result)
        json2 = export_lifecycle_correlation_json(result)

        self.assertEqual(json1, json2)

    def test_export_includes_wsp97_note(self):
        """JSON export includes WSP 97 compliance note."""
        result = correlate_cabr_lifecycle()
        json_str = export_lifecycle_correlation_json(result)

        parsed = json.loads(json_str)
        self.assertIn("WSP 97", parsed["wsp97_compliance_note"])

    def test_export_datetime_as_iso_strings(self):
        """Datetime fields exported as ISO strings."""
        result = correlate_cabr_lifecycle(
            receipts=[_make_receipt()],
        )
        json_str = export_lifecycle_correlation_json(result)

        parsed = json.loads(json_str)
        generated_at = parsed["generated_at"]
        self.assertIsInstance(generated_at, str)
        # Should be parseable
        datetime.fromisoformat(generated_at.replace("Z", "+00:00"))


# ---------------------------------------------------------------------------
# Test: No Store Mutation
# ---------------------------------------------------------------------------


class TestNoStoreMutation(unittest.TestCase):
    """Tests that correlation does not mutate any store."""

    def test_correlation_is_pure_function(self):
        """Correlation is a pure function with no side effects."""
        receipts = [_make_receipt()]
        original_receipt = receipts[0].copy()

        correlate_cabr_lifecycle(receipts=receipts)

        # Original input unchanged
        self.assertEqual(receipts[0], original_receipt)

    def test_no_db_path_parameter(self):
        """correlate_cabr_lifecycle has no db_path parameter."""
        import inspect
        sig = inspect.signature(correlate_cabr_lifecycle)
        param_names = list(sig.parameters.keys())

        self.assertNotIn("db_path", param_names)
        self.assertNotIn("store", param_names)


# ---------------------------------------------------------------------------
# Test: No Payout Readiness Inferred
# ---------------------------------------------------------------------------


class TestNoPayoutReadinessInferred(unittest.TestCase):
    """Tests that payout readiness is never inferred."""

    def test_full_lifecycle_no_payout_ready(self):
        """Full lifecycle does not set payout_ready=True."""
        receipt_id = "rcpt_full"
        result = correlate_cabr_lifecycle(
            receipts=[_make_receipt(receipt_id=receipt_id)],
            pavs_results=[_make_pavs_result(receipt_id=receipt_id)],
            score_results=[_make_score_result(receipt_id=receipt_id)],
            quorum_results=[_make_quorum_result(receipt_id=receipt_id)],
            consensus_records=[_make_consensus_record(receipt_id=receipt_id)],
            persisted_records=[_make_persisted_record(receipt_id=receipt_id)],
            reported_records=[_make_reported_record(receipt_id=receipt_id)],
        )

        # Check all items have payout_ready=False
        for correlation in result.correlations:
            for item in correlation.items.values():
                self.assertFalse(item.payout_ready)

    def test_result_has_no_payout_fields(self):
        """Result has no payout-related fields."""
        result = correlate_cabr_lifecycle(
            receipts=[_make_receipt()],
        )
        result_dict = result.to_dict()
        json_str = json.dumps(result_dict)

        self.assertNotIn("total_payout", json_str)
        self.assertNotIn("payout_amount", json_str)
        self.assertNotIn("tokens_issued", json_str)


# ---------------------------------------------------------------------------
# Test: No DAO Activation Inferred
# ---------------------------------------------------------------------------


class TestNoDAOActivationInferred(unittest.TestCase):
    """Tests that DAO activation is never inferred."""

    def test_result_has_no_dao_fields(self):
        """Result has no DAO-related fields."""
        result = correlate_cabr_lifecycle(
            receipts=[_make_receipt()],
        )
        result_dict = result.to_dict()
        json_str = json.dumps(result_dict)

        self.assertNotIn("dao_activated", json_str)
        self.assertNotIn("dao_transition", json_str)


# ---------------------------------------------------------------------------
# Test: No Default DB Path
# ---------------------------------------------------------------------------


class TestNoDefaultDbPath(unittest.TestCase):
    """Tests that no default DB path is used."""

    def test_empty_input_returns_empty_result(self):
        """Empty input returns valid empty result (no DB needed)."""
        result = correlate_cabr_lifecycle()

        self.assertEqual(len(result.correlations), 0)
        self.assertEqual(result.total_items, 0)
        self.assertEqual(result.total_gaps, 0)

    def test_no_filesystem_writes(self):
        """Correlation does not write to filesystem."""
        import os
        import tempfile

        # Get temp dir before correlation
        temp_files_before = set(os.listdir(tempfile.gettempdir()))

        correlate_cabr_lifecycle(
            receipts=[_make_receipt()],
        )

        # No new temp files created (approximately)
        temp_files_after = set(os.listdir(tempfile.gettempdir()))
        # Allow some system temp files but no consensus DB
        new_files = temp_files_after - temp_files_before
        for f in new_files:
            self.assertNotIn("consensus", f.lower())
            self.assertNotIn("cabr", f.lower())


# ---------------------------------------------------------------------------
# Test: Gap Summary
# ---------------------------------------------------------------------------


class TestGapSummary(unittest.TestCase):
    """Tests for gap summary function."""

    def test_gap_summary_counts_gaps_by_stage(self):
        """Gap summary counts gaps by missing stage."""
        result = correlate_cabr_lifecycle(
            receipts=[
                _make_receipt(receipt_id="rcpt_001"),
                _make_receipt(receipt_id="rcpt_002"),
            ],
        )

        summary = summarize_lifecycle_gaps(result)

        # Each receipt missing 6 downstream stages = 12 total gaps
        self.assertEqual(summary.total_gaps, 12)

        # Each missing stage should have count 2
        for stage in LIFECYCLE_STAGE_ORDER[1:]:  # Skip RECEIPT_CREATED
            self.assertEqual(summary.gaps_by_stage.get(stage.value, 0), 2)

    def test_gap_summary_correlations_with_gaps(self):
        """Gap summary counts correlations with gaps."""
        result = correlate_cabr_lifecycle(
            receipts=[
                _make_receipt(receipt_id="rcpt_001"),
                _make_receipt(receipt_id="rcpt_002"),
            ],
        )

        summary = summarize_lifecycle_gaps(result)

        self.assertEqual(summary.correlations_with_gaps, 2)

    def test_gap_summary_complete_correlation(self):
        """Gap summary identifies complete correlations."""
        receipt_id = "rcpt_full"
        result = correlate_cabr_lifecycle(
            receipts=[_make_receipt(receipt_id=receipt_id)],
            pavs_results=[_make_pavs_result(receipt_id=receipt_id)],
            score_results=[_make_score_result(receipt_id=receipt_id)],
            quorum_results=[_make_quorum_result(receipt_id=receipt_id)],
            consensus_records=[_make_consensus_record(receipt_id=receipt_id)],
            persisted_records=[_make_persisted_record(receipt_id=receipt_id)],
            reported_records=[_make_reported_record(receipt_id=receipt_id)],
        )

        summary = summarize_lifecycle_gaps(result)

        self.assertEqual(summary.correlations_complete, 1)
        self.assertEqual(summary.correlations_with_gaps, 0)
        self.assertEqual(summary.total_gaps, 0)

    def test_gap_summary_to_dict(self):
        """Gap summary serializes to dict."""
        result = correlate_cabr_lifecycle(
            receipts=[_make_receipt()],
        )

        summary = summarize_lifecycle_gaps(result)
        d = summary.to_dict()

        self.assertIn("total_gaps", d)
        self.assertIn("gaps_by_stage", d)
        self.assertIn("correlations_with_gaps", d)
        self.assertIn("correlations_complete", d)


# ---------------------------------------------------------------------------
# Test: Lifecycle Item
# ---------------------------------------------------------------------------


class TestLifecycleItem(unittest.TestCase):
    """Tests for CABRLifecycleItem dataclass."""

    def test_item_to_dict(self):
        """CABRLifecycleItem serializes to dict."""
        item = CABRLifecycleItem(
            stage=CABRLifecycleStage.RECEIPT_CREATED,
            receipt_id="rcpt_001",
            job_id="j_001",
            item_id="rcpt_001",
            timestamp=datetime(2026, 5, 13, 12, 0, 0, tzinfo=timezone.utc),
            decision="pending_pavs",
            verification_complete=False,
            cabr_ready=False,
            payout_ready=False,
        )

        d = item.to_dict()

        self.assertEqual(d["stage"], "receipt_created")
        self.assertEqual(d["receipt_id"], "rcpt_001")
        self.assertFalse(d["verification_complete"])


# ---------------------------------------------------------------------------
# Test: Lifecycle Gap
# ---------------------------------------------------------------------------


class TestLifecycleGap(unittest.TestCase):
    """Tests for CABRLifecycleGap dataclass."""

    def test_gap_to_dict(self):
        """CABRLifecycleGap serializes to dict."""
        gap = CABRLifecycleGap(
            correlation_key="receipt_id",
            correlation_value="rcpt_001",
            present_stage=CABRLifecycleStage.RECEIPT_CREATED,
            missing_stage=CABRLifecycleStage.PAVS_EVALUATED,
            gap_type="missing_downstream",
        )

        d = gap.to_dict()

        self.assertEqual(d["correlation_key"], "receipt_id")
        self.assertEqual(d["present_stage"], "receipt_created")
        self.assertEqual(d["missing_stage"], "pavs_evaluated")


# ---------------------------------------------------------------------------
# Test: Multiple Receipts Different Lifecycles
# ---------------------------------------------------------------------------


class TestMultipleReceiptsDifferentLifecycles(unittest.TestCase):
    """Tests for multiple receipts with different lifecycles."""

    def test_mixed_lifecycle_states(self):
        """Multiple receipts at different lifecycle stages."""
        result = correlate_cabr_lifecycle(
            receipts=[
                _make_receipt(receipt_id="rcpt_001"),
                _make_receipt(receipt_id="rcpt_002"),
                _make_receipt(receipt_id="rcpt_003"),
            ],
            pavs_results=[
                _make_pavs_result(receipt_id="rcpt_001"),
                _make_pavs_result(receipt_id="rcpt_002"),
            ],
            score_results=[
                _make_score_result(receipt_id="rcpt_001"),
            ],
        )

        # 3 correlations
        self.assertEqual(len(result.correlations), 3)

        # Find correlations by receipt_id
        correlations_by_id = {
            c.correlation_value: c for c in result.correlations
        }

        # rcpt_001: 3 stages, 4 gaps
        c1 = correlations_by_id["rcpt_001"]
        self.assertEqual(len(c1.stages_present), 3)
        self.assertEqual(len(c1.gaps), 4)

        # rcpt_002: 2 stages, 5 gaps
        c2 = correlations_by_id["rcpt_002"]
        self.assertEqual(len(c2.stages_present), 2)
        self.assertEqual(len(c2.gaps), 5)

        # rcpt_003: 1 stage, 6 gaps
        c3 = correlations_by_id["rcpt_003"]
        self.assertEqual(len(c3.stages_present), 1)
        self.assertEqual(len(c3.gaps), 6)


# ---------------------------------------------------------------------------
# Test: Correlation Sorting
# ---------------------------------------------------------------------------


class TestCorrelationSorting(unittest.TestCase):
    """Tests for deterministic correlation ordering."""

    def test_correlations_sorted_by_key(self):
        """Correlations are sorted by correlation key/value."""
        result = correlate_cabr_lifecycle(
            receipts=[
                _make_receipt(receipt_id="rcpt_zzz"),
                _make_receipt(receipt_id="rcpt_aaa"),
                _make_receipt(receipt_id="rcpt_mmm"),
            ],
        )

        # Should be sorted alphabetically
        values = [c.correlation_value for c in result.correlations]
        self.assertEqual(values, sorted(values))


if __name__ == "__main__":
    unittest.main(verbosity=2)
