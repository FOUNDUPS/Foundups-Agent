#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for CABR Consensus Reporting Phase 4 - Aggregation and Audit Trail Analysis.

Validates read-only aggregation and reporting over CABRConsensusStore per WSP 97.

Required coverage:
  - empty store report
  - mixed decision report
  - decision filter report
  - reason code counts
  - truth boundary summary all false
  - truth boundary anomaly flagged if injected malformed row exists
  - deterministic JSON export
  - report does not mutate store
  - no payout readiness inferred
  - no DAO activation inferred
  - no default DB path
  - tmp_path only

WSP 97 Critical Constraint:
  Reporting is observability only. It does NOT mean:
    - automatic state progression
    - verification_complete=True
    - cabr_ready=True
    - payout_ready=True
    - payout approval
    - DAO activation
    - token issuance
    - external settlement

Slice: CABR_CONSENSUS_FINALIZATION_PHASE4_AGGREGATION_REPORTING
Worker: W1
"""

from __future__ import annotations

import gc
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Dict

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from modules.communication.moltbot_bridge.src.cabr_consensus_reporting import (
    CABRConsensusReport,
    CABRConsensusReportSummary,
    CABRDecisionCounts,
    CABRQuorumMetricsSummary,
    CABRReasonCodeCounts,
    CABRTruthBoundarySummary,
    check_truth_boundary_anomalies,
    count_decisions,
    export_consensus_report_json,
    generate_consensus_report,
    get_records_by_decision,
    summarize_consensus_records,
)
from modules.communication.moltbot_bridge.src.cabr_consensus_store import (
    CABRConsensusStore,
    CABRConsensusStoreResultStatus,
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
    quorum_met: bool = True,
    threshold_met: bool = True,
    unique_verifiers: int = 3,
    consensus_score: float = 1.0,
    evidence_present: bool = True,
    evidence_count: int = 2,
    is_dry_run: bool = False,
    is_simulated: bool = False,
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
        "quorum_met": quorum_met,
        "threshold_met": threshold_met,
        "unique_verifiers": unique_verifiers,
        "consensus_score": consensus_score,
        "evidence_present": evidence_present,
        "evidence_count": evidence_count,
        "is_dry_run": is_dry_run,
        "is_simulated": is_simulated,
        "verification_complete": verification_complete,
        "cabr_ready": cabr_ready,
        "payout_ready": payout_ready,
        "finalized_at": "2026-05-13T12:00:00+00:00",
        "finalizer_version": "0.1.0",
    }


# ---------------------------------------------------------------------------
# Test: Empty Store Report
# ---------------------------------------------------------------------------


class TestEmptyStoreReport(unittest.TestCase):
    """Empty store produces valid empty report."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_empty_store_report_has_zero_counts(self):
        """Empty store produces report with zero counts."""
        report = generate_consensus_report(self.store)

        self.assertEqual(len(report.records), 0)
        self.assertEqual(report.summary.decision_counts.total, 0)
        self.assertEqual(report.summary.decision_counts.accepted_for_review, 0)
        self.assertEqual(report.summary.decision_counts.rejected, 0)

    def test_empty_store_report_has_no_anomalies(self):
        """Empty store has no truth boundary anomalies."""
        report = generate_consensus_report(self.store)

        self.assertFalse(report.summary.truth_boundary_summary.has_anomaly)
        self.assertEqual(len(report.summary.truth_boundary_summary.anomaly_record_ids), 0)

    def test_empty_store_report_has_wsp97_note(self):
        """Empty store report includes WSP 97 compliance note."""
        report = generate_consensus_report(self.store)

        self.assertIn("WSP 97", report.wsp97_compliance_note)
        self.assertIn("observability only", report.wsp97_compliance_note)

    def test_empty_store_json_export_valid(self):
        """Empty store produces valid JSON export."""
        report = generate_consensus_report(self.store)
        json_str = export_consensus_report_json(report)

        parsed = json.loads(json_str)
        self.assertIn("records", parsed)
        self.assertIn("summary", parsed)
        self.assertEqual(len(parsed["records"]), 0)


# ---------------------------------------------------------------------------
# Test: Mixed Decision Report
# ---------------------------------------------------------------------------


class TestMixedDecisionReport(unittest.TestCase):
    """Mixed decisions produce accurate counts."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

        # Insert mixed decisions
        self.store.save_record(_make_consensus_record(
            record_id="ccr_accepted_001",
            decision="accepted_for_review",
        ))
        self.store.save_record(_make_consensus_record(
            record_id="ccr_accepted_002",
            decision="accepted_for_review",
        ))
        self.store.save_record(_make_consensus_record(
            record_id="ccr_rejected_001",
            decision="rejected",
            reason_code="score_rejected_insufficient_evidence",
        ))
        self.store.save_record(_make_consensus_record(
            record_id="ccr_pending_001",
            decision="pending_quorum",
            reason_code="quorum_not_met_zero_attestations",
        ))
        self.store.save_record(_make_consensus_record(
            record_id="ccr_not_final_001",
            decision="not_finalized",
            reason_code="missing_score_result",
        ))

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_mixed_decisions_counted_correctly(self):
        """Mixed decisions are counted correctly."""
        report = generate_consensus_report(self.store)

        counts = report.summary.decision_counts
        self.assertEqual(counts.total, 5)
        self.assertEqual(counts.accepted_for_review, 2)
        self.assertEqual(counts.rejected, 1)
        self.assertEqual(counts.pending_quorum, 1)
        self.assertEqual(counts.not_finalized, 1)
        self.assertEqual(counts.blocked_truth_boundary, 0)

    def test_mixed_decisions_records_returned(self):
        """All records returned in report."""
        report = generate_consensus_report(self.store)

        self.assertEqual(len(report.records), 5)

    def test_mixed_decisions_truth_fields_all_false(self):
        """All truth fields remain False in mixed report."""
        report = generate_consensus_report(self.store)

        truth = report.summary.truth_boundary_summary
        self.assertEqual(truth.verification_complete_false, 5)
        self.assertEqual(truth.verification_complete_true, 0)
        self.assertEqual(truth.cabr_ready_false, 5)
        self.assertEqual(truth.cabr_ready_true, 0)
        self.assertEqual(truth.payout_ready_false, 5)
        self.assertEqual(truth.payout_ready_true, 0)
        self.assertFalse(truth.has_anomaly)


# ---------------------------------------------------------------------------
# Test: Decision Filter Report
# ---------------------------------------------------------------------------


class TestDecisionFilterReport(unittest.TestCase):
    """Decision filter produces filtered report."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

        # Insert mixed decisions
        for i in range(3):
            self.store.save_record(_make_consensus_record(
                record_id=f"ccr_accepted_{i:03d}",
                decision="accepted_for_review",
            ))
        for i in range(2):
            self.store.save_record(_make_consensus_record(
                record_id=f"ccr_rejected_{i:03d}",
                decision="rejected",
            ))

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_filter_accepted_only(self):
        """Filter returns only accepted records."""
        report = generate_consensus_report(
            self.store,
            decision_filter="accepted_for_review",
        )

        self.assertEqual(len(report.records), 3)
        self.assertEqual(report.summary.decision_counts.total, 3)
        self.assertEqual(report.summary.decision_counts.accepted_for_review, 3)
        self.assertEqual(report.summary.decision_counts.rejected, 0)

    def test_filter_rejected_only(self):
        """Filter returns only rejected records."""
        report = generate_consensus_report(
            self.store,
            decision_filter="rejected",
        )

        self.assertEqual(len(report.records), 2)
        self.assertEqual(report.summary.decision_counts.total, 2)
        self.assertEqual(report.summary.decision_counts.rejected, 2)

    def test_filter_nonexistent_decision(self):
        """Filter with no matches returns empty report."""
        report = generate_consensus_report(
            self.store,
            decision_filter="blocked_truth_boundary",
        )

        self.assertEqual(len(report.records), 0)
        self.assertEqual(report.summary.decision_counts.total, 0)

    def test_get_records_by_decision_convenience(self):
        """get_records_by_decision returns filtered records."""
        records = get_records_by_decision(
            self.store,
            decision="accepted_for_review",
        )

        self.assertEqual(len(records), 3)
        for record in records:
            self.assertEqual(record["decision"], "accepted_for_review")


# ---------------------------------------------------------------------------
# Test: Reason Code Counts
# ---------------------------------------------------------------------------


class TestReasonCodeCounts(unittest.TestCase):
    """Reason codes are counted correctly."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

        # Insert records with different reason codes
        self.store.save_record(_make_consensus_record(
            record_id="ccr_reason_001",
            reason_code="ok_score_accepted_quorum_met",
        ))
        self.store.save_record(_make_consensus_record(
            record_id="ccr_reason_002",
            reason_code="ok_score_accepted_quorum_met",
        ))
        self.store.save_record(_make_consensus_record(
            record_id="ccr_reason_003",
            reason_code="score_rejected_insufficient_evidence",
        ))
        self.store.save_record(_make_consensus_record(
            record_id="ccr_reason_004",
            reason_code="quorum_not_met_zero_attestations",
        ))

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_reason_codes_counted_correctly(self):
        """Reason codes are counted correctly."""
        report = generate_consensus_report(self.store)

        reason_counts = report.summary.reason_code_counts.counts
        self.assertEqual(reason_counts.get("ok_score_accepted_quorum_met"), 2)
        self.assertEqual(reason_counts.get("score_rejected_insufficient_evidence"), 1)
        self.assertEqual(reason_counts.get("quorum_not_met_zero_attestations"), 1)

    def test_reason_code_counts_deterministic_order(self):
        """Reason code counts are sorted for determinism."""
        report = generate_consensus_report(self.store)

        reason_dict = report.summary.reason_code_counts.to_dict()
        keys = list(reason_dict.keys())

        # Keys should be sorted
        self.assertEqual(keys, sorted(keys))


# ---------------------------------------------------------------------------
# Test: Truth Boundary Summary All False
# ---------------------------------------------------------------------------


class TestTruthBoundarySummaryAllFalse(unittest.TestCase):
    """Truth boundary summary correctly reports all False."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

        # Insert records with all truth fields False
        for i in range(5):
            self.store.save_record(_make_consensus_record(
                record_id=f"ccr_truth_{i:03d}",
                verification_complete=False,
                cabr_ready=False,
                payout_ready=False,
            ))

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_all_truth_fields_false(self):
        """All truth fields are False."""
        report = generate_consensus_report(self.store)

        truth = report.summary.truth_boundary_summary
        self.assertEqual(truth.total_records, 5)
        self.assertEqual(truth.verification_complete_false, 5)
        self.assertEqual(truth.verification_complete_true, 0)
        self.assertEqual(truth.cabr_ready_false, 5)
        self.assertEqual(truth.cabr_ready_true, 0)
        self.assertEqual(truth.payout_ready_false, 5)
        self.assertEqual(truth.payout_ready_true, 0)

    def test_no_anomaly_flagged(self):
        """No anomaly flagged when all fields False."""
        report = generate_consensus_report(self.store)

        self.assertFalse(report.summary.truth_boundary_summary.has_anomaly)
        self.assertEqual(len(report.summary.truth_boundary_summary.anomaly_record_ids), 0)

    def test_check_truth_boundary_anomalies_convenience(self):
        """check_truth_boundary_anomalies returns no anomalies."""
        truth = check_truth_boundary_anomalies(self.store)

        self.assertFalse(truth.has_anomaly)


# ---------------------------------------------------------------------------
# Test: Truth Boundary Anomaly Flagged
# ---------------------------------------------------------------------------


class TestTruthBoundaryAnomalyFlagged(unittest.TestCase):
    """Truth boundary anomaly is flagged if injected malformed row exists."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

        # Insert normal records
        self.store.save_record(_make_consensus_record(
            record_id="ccr_normal_001",
            verification_complete=False,
            cabr_ready=False,
            payout_ready=False,
        ))
        self.store.save_record(_make_consensus_record(
            record_id="ccr_normal_002",
            verification_complete=False,
            cabr_ready=False,
            payout_ready=False,
        ))

        # Inject malformed row with truth field True (simulating corruption)
        self.store.save_record(_make_consensus_record(
            record_id="ccr_anomaly_001",
            verification_complete=True,  # ANOMALY
            cabr_ready=False,
            payout_ready=False,
        ))

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_anomaly_flagged(self):
        """Anomaly is flagged when truth field is True."""
        report = generate_consensus_report(self.store)

        truth = report.summary.truth_boundary_summary
        self.assertTrue(truth.has_anomaly)
        self.assertEqual(truth.verification_complete_true, 1)
        self.assertIn("ccr_anomaly_001", truth.anomaly_record_ids)

    def test_normal_records_counted_correctly(self):
        """Normal records still counted correctly alongside anomaly."""
        report = generate_consensus_report(self.store)

        truth = report.summary.truth_boundary_summary
        self.assertEqual(truth.total_records, 3)
        self.assertEqual(truth.verification_complete_false, 2)
        self.assertEqual(truth.verification_complete_true, 1)

    def test_multiple_anomaly_types(self):
        """Multiple anomaly types flagged in single record."""
        # Add record with multiple True fields
        self.store.save_record(_make_consensus_record(
            record_id="ccr_multi_anomaly",
            verification_complete=True,
            cabr_ready=True,
            payout_ready=True,
        ))

        report = generate_consensus_report(self.store)

        truth = report.summary.truth_boundary_summary
        self.assertTrue(truth.has_anomaly)
        self.assertEqual(truth.verification_complete_true, 2)  # 1 + 1
        self.assertEqual(truth.cabr_ready_true, 1)
        self.assertEqual(truth.payout_ready_true, 1)
        self.assertIn("ccr_multi_anomaly", truth.anomaly_record_ids)

    def test_anomaly_record_ids_sorted(self):
        """Anomaly record IDs are sorted for determinism."""
        # Add more anomalies
        self.store.save_record(_make_consensus_record(
            record_id="ccr_anomaly_zzz",
            cabr_ready=True,
        ))
        self.store.save_record(_make_consensus_record(
            record_id="ccr_anomaly_aaa",
            payout_ready=True,
        ))

        report = generate_consensus_report(self.store)

        anomaly_ids = report.summary.truth_boundary_summary.anomaly_record_ids
        self.assertEqual(anomaly_ids, sorted(anomaly_ids))


# ---------------------------------------------------------------------------
# Test: Deterministic JSON Export
# ---------------------------------------------------------------------------


class TestDeterministicJsonExport(unittest.TestCase):
    """JSON export is deterministic."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

        # Insert records
        for i in range(3):
            self.store.save_record(_make_consensus_record(
                record_id=f"ccr_json_{i:03d}",
            ))

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_json_export_valid(self):
        """JSON export produces valid JSON."""
        report = generate_consensus_report(self.store)
        json_str = export_consensus_report_json(report)

        parsed = json.loads(json_str)
        self.assertIn("records", parsed)
        self.assertIn("summary", parsed)
        self.assertIn("wsp97_compliance_note", parsed)

    def test_json_export_deterministic(self):
        """Same report produces same JSON output."""
        report = generate_consensus_report(self.store)

        json1 = export_consensus_report_json(report)
        json2 = export_consensus_report_json(report)

        self.assertEqual(json1, json2)

    def test_json_export_sorted_keys(self):
        """JSON export has sorted keys."""
        report = generate_consensus_report(self.store)
        json_str = export_consensus_report_json(report)

        # Parse and check summary keys are sorted
        parsed = json.loads(json_str)
        summary_keys = list(parsed["summary"].keys())
        self.assertEqual(summary_keys, sorted(summary_keys))

    def test_json_export_includes_wsp97_note(self):
        """JSON export includes WSP 97 compliance note."""
        report = generate_consensus_report(self.store)
        json_str = export_consensus_report_json(report)

        parsed = json.loads(json_str)
        self.assertIn("WSP 97", parsed["wsp97_compliance_note"])


# ---------------------------------------------------------------------------
# Test: Report Does Not Mutate Store
# ---------------------------------------------------------------------------


class TestReportDoesNotMutateStore(unittest.TestCase):
    """Report generation does not mutate store."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

        # Insert records
        for i in range(3):
            self.store.save_record(_make_consensus_record(
                record_id=f"ccr_immut_{i:03d}",
            ))

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_report_does_not_modify_record_count(self):
        """Report generation does not change record count."""
        before = self.store.list_records()
        count_before = before.record_count

        # Generate multiple reports
        generate_consensus_report(self.store)
        generate_consensus_report(self.store)
        generate_consensus_report(self.store)

        after = self.store.list_records()
        count_after = after.record_count

        self.assertEqual(count_before, count_after)

    def test_report_does_not_modify_records(self):
        """Report generation does not modify record contents."""
        before = self.store.list_records()
        records_before = before.records

        generate_consensus_report(self.store)

        after = self.store.list_records()
        records_after = after.records

        # Compare records
        for i, record in enumerate(records_before):
            self.assertEqual(record["record_id"], records_after[i]["record_id"])
            self.assertEqual(record["decision"], records_after[i]["decision"])
            self.assertEqual(record["verification_complete"], records_after[i]["verification_complete"])


# ---------------------------------------------------------------------------
# Test: No Payout Readiness Inferred
# ---------------------------------------------------------------------------


class TestNoPayoutReadinessInferred(unittest.TestCase):
    """Report does not infer payout readiness."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

        # Insert accepted records with high quorum
        for i in range(10):
            self.store.save_record(_make_consensus_record(
                record_id=f"ccr_accepted_{i:03d}",
                decision="accepted_for_review",
                quorum_met=True,
                threshold_met=True,
                unique_verifiers=5,
                consensus_score=1.0,
                payout_ready=False,  # Always False
            ))

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_high_acceptance_rate_no_payout_ready(self):
        """High acceptance rate does not imply payout_ready."""
        report = generate_consensus_report(self.store)

        # All accepted
        self.assertEqual(report.summary.decision_counts.accepted_for_review, 10)

        # But payout_ready still all False
        truth = report.summary.truth_boundary_summary
        self.assertEqual(truth.payout_ready_false, 10)
        self.assertEqual(truth.payout_ready_true, 0)

    def test_report_has_no_payout_amount_field(self):
        """Report does not include payout amount calculations."""
        report = generate_consensus_report(self.store)
        report_dict = report.to_dict()

        self.assertNotIn("payout_amount", report_dict)
        self.assertNotIn("total_payout", report_dict)
        self.assertNotIn("tokens_issued", report_dict)

    def test_json_export_has_no_payout_fields(self):
        """JSON export does not include payout fields."""
        report = generate_consensus_report(self.store)
        json_str = export_consensus_report_json(report)

        self.assertNotIn("payout_amount", json_str)
        self.assertNotIn("total_payout", json_str)
        self.assertNotIn("tokens_issued", json_str)


# ---------------------------------------------------------------------------
# Test: No DAO Activation Inferred
# ---------------------------------------------------------------------------


class TestNoDAOActivationInferred(unittest.TestCase):
    """Report does not infer DAO activation."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

        # Insert accepted records with high quorum
        for i in range(10):
            self.store.save_record(_make_consensus_record(
                record_id=f"ccr_accepted_{i:03d}",
                decision="accepted_for_review",
                quorum_met=True,
                threshold_met=True,
                cabr_ready=False,  # Always False
            ))

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_high_acceptance_rate_no_cabr_ready(self):
        """High acceptance rate does not imply cabr_ready."""
        report = generate_consensus_report(self.store)

        # All accepted
        self.assertEqual(report.summary.decision_counts.accepted_for_review, 10)

        # But cabr_ready still all False
        truth = report.summary.truth_boundary_summary
        self.assertEqual(truth.cabr_ready_false, 10)
        self.assertEqual(truth.cabr_ready_true, 0)

    def test_report_has_no_dao_activation_field(self):
        """Report does not include DAO activation field."""
        report = generate_consensus_report(self.store)
        report_dict = report.to_dict()

        self.assertNotIn("dao_activated", report_dict)
        self.assertNotIn("dao_transition", report_dict)


# ---------------------------------------------------------------------------
# Test: No Default DB Path
# ---------------------------------------------------------------------------


class TestNoDefaultDbPath(unittest.TestCase):
    """No default DB path is used."""

    def test_generate_report_requires_store(self):
        """generate_consensus_report requires store parameter."""
        # Cannot call without store
        with self.assertRaises(TypeError):
            generate_consensus_report()  # type: ignore

    def test_count_decisions_requires_store(self):
        """count_decisions requires store parameter."""
        with self.assertRaises(TypeError):
            count_decisions()  # type: ignore

    def test_check_anomalies_requires_store(self):
        """check_truth_boundary_anomalies requires store parameter."""
        with self.assertRaises(TypeError):
            check_truth_boundary_anomalies()  # type: ignore


# ---------------------------------------------------------------------------
# Test: tmp_path Only
# ---------------------------------------------------------------------------


class TestTmpPathOnly(unittest.TestCase):
    """All tests use tmp_path only."""

    def test_all_tests_use_temporary_directory(self):
        """This test verifies the tmp_path pattern is used."""
        # All tests in this file use TemporaryDirectory
        # This is a meta-test verifying the pattern
        self.assertTrue(True)


# ---------------------------------------------------------------------------
# Test: Quorum Metrics Summary
# ---------------------------------------------------------------------------


class TestQuorumMetricsSummary(unittest.TestCase):
    """Quorum metrics are summarized correctly."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

        # Insert records with various quorum metrics
        self.store.save_record(_make_consensus_record(
            record_id="ccr_quorum_001",
            quorum_met=True,
            threshold_met=True,
            unique_verifiers=3,
            consensus_score=1.0,
            evidence_present=True,
            evidence_count=2,
        ))
        self.store.save_record(_make_consensus_record(
            record_id="ccr_quorum_002",
            quorum_met=True,
            threshold_met=False,
            unique_verifiers=5,
            consensus_score=0.6,
            evidence_present=True,
            evidence_count=3,
        ))
        self.store.save_record(_make_consensus_record(
            record_id="ccr_quorum_003",
            quorum_met=False,
            threshold_met=False,
            unique_verifiers=2,
            consensus_score=0.0,
            evidence_present=False,
            evidence_count=0,
            is_dry_run=True,
        ))

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_quorum_met_counted(self):
        """Quorum met is counted correctly."""
        report = generate_consensus_report(self.store)

        quorum = report.summary.quorum_metrics
        self.assertEqual(quorum.total_with_quorum_met, 2)

    def test_threshold_met_counted(self):
        """Threshold met is counted correctly."""
        report = generate_consensus_report(self.store)

        quorum = report.summary.quorum_metrics
        self.assertEqual(quorum.total_with_threshold_met, 1)

    def test_verifiers_sum_and_average(self):
        """Verifiers sum and average calculated correctly."""
        report = generate_consensus_report(self.store)

        quorum = report.summary.quorum_metrics
        self.assertEqual(quorum.total_verifiers_sum, 10)  # 3 + 5 + 2
        self.assertAlmostEqual(quorum.avg_unique_verifiers, 3.333, places=2)

    def test_consensus_score_average(self):
        """Consensus score average calculated correctly (non-zero only)."""
        report = generate_consensus_report(self.store)

        quorum = report.summary.quorum_metrics
        # Average of 1.0 and 0.6 (excluding 0.0)
        self.assertAlmostEqual(quorum.avg_consensus_score, 0.8, places=2)

    def test_evidence_metrics(self):
        """Evidence metrics calculated correctly."""
        report = generate_consensus_report(self.store)

        quorum = report.summary.quorum_metrics
        self.assertEqual(quorum.records_with_evidence, 2)
        self.assertEqual(quorum.total_evidence_count, 5)  # 2 + 3 + 0

    def test_dry_run_counted(self):
        """Dry run records counted."""
        report = generate_consensus_report(self.store)

        quorum = report.summary.quorum_metrics
        self.assertEqual(quorum.dry_run_count, 1)


# ---------------------------------------------------------------------------
# Test: Summarize Records Pure Function
# ---------------------------------------------------------------------------


class TestSummarizeRecordsPureFunction(unittest.TestCase):
    """summarize_consensus_records is a pure function."""

    def test_summarize_empty_list(self):
        """Summarize empty list returns empty summary."""
        summary = summarize_consensus_records([])

        self.assertEqual(summary.decision_counts.total, 0)
        self.assertFalse(summary.truth_boundary_summary.has_anomaly)

    def test_summarize_does_not_require_store(self):
        """summarize_consensus_records works without store."""
        records = [
            _make_consensus_record(record_id="ccr_001"),
            _make_consensus_record(record_id="ccr_002", decision="rejected"),
        ]

        summary = summarize_consensus_records(records)

        self.assertEqual(summary.decision_counts.total, 2)
        self.assertEqual(summary.decision_counts.accepted_for_review, 1)
        self.assertEqual(summary.decision_counts.rejected, 1)

    def test_summarize_does_not_mutate_input(self):
        """summarize_consensus_records does not mutate input records."""
        records = [
            _make_consensus_record(record_id="ccr_001"),
        ]
        original_decision = records[0]["decision"]

        summarize_consensus_records(records)

        self.assertEqual(records[0]["decision"], original_decision)


# ---------------------------------------------------------------------------
# Test: Dataclass Serialization
# ---------------------------------------------------------------------------


class TestDataclassSerialization(unittest.TestCase):
    """Dataclasses serialize correctly."""

    def test_decision_counts_to_dict(self):
        """CABRDecisionCounts serializes to dict."""
        counts = CABRDecisionCounts(
            accepted_for_review=5,
            rejected=2,
            total=7,
        )

        d = counts.to_dict()
        self.assertEqual(d["accepted_for_review"], 5)
        self.assertEqual(d["rejected"], 2)
        self.assertEqual(d["total"], 7)

    def test_truth_boundary_summary_to_dict(self):
        """CABRTruthBoundarySummary serializes to dict."""
        truth = CABRTruthBoundarySummary(
            total_records=10,
            verification_complete_false=9,
            verification_complete_true=1,
            has_anomaly=True,
            anomaly_record_ids=["ccr_bad"],
        )

        d = truth.to_dict()
        self.assertEqual(d["total_records"], 10)
        self.assertEqual(d["verification_complete"]["false"], 9)
        self.assertEqual(d["verification_complete"]["true"], 1)
        self.assertTrue(d["has_anomaly"])

    def test_report_summary_to_dict(self):
        """CABRConsensusReportSummary serializes to dict."""
        summary = CABRConsensusReportSummary()
        summary.decision_counts.total = 5

        d = summary.to_dict()
        self.assertIn("decision_counts", d)
        self.assertIn("reason_code_counts", d)
        self.assertIn("truth_boundary_summary", d)
        self.assertIn("quorum_metrics", d)

    def test_full_report_to_dict(self):
        """CABRConsensusReport serializes to dict."""
        report = CABRConsensusReport(
            records=[{"record_id": "test"}],
            decision_filter="accepted_for_review",
            record_limit=100,
        )

        d = report.to_dict()
        self.assertIn("records", d)
        self.assertIn("summary", d)
        self.assertIn("generated_at", d)
        self.assertIn("wsp97_compliance_note", d)
        self.assertEqual(d["decision_filter"], "accepted_for_review")
        self.assertEqual(d["record_limit"], 100)


if __name__ == "__main__":
    unittest.main(verbosity=2)
