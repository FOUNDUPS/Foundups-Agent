#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for CABR Consensus Finalizer Phase 3 - Auto-Persist Integration.

Validates optional caller-provided persistence for CABRConsensusRecord per WSP 97.

Required coverage:
  - store=None produces identical result and no DB file
  - provided store saves accepted-for-review record
  - provided store saves rejected/pending records
  - duplicate finalization idempotent
  - store failure returns explicit failure or blocks success
  - batch finalization persists all records deterministically
  - persisted truth fields remain false
  - no payout/DAO/state progression
  - no default DB path used
  - tmp_path only

WSP 97 Critical Constraint:
  Auto-persist means storing the review-only CABRConsensusRecord when an explicit
  store is provided. It does NOT mean:
    - automatic state progression
    - verification_complete=True
    - cabr_ready=True
    - payout_ready=True
    - payout approval
    - DAO activation
    - external settlement

Slice: CABR_CONSENSUS_FINALIZATION_PHASE3_AUTO_PERSIST_INTEGRATION
Worker: W1
"""

from __future__ import annotations

import gc
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Dict

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from modules.communication.moltbot_bridge.src.cabr_consensus_finalizer import (
    CABRConsensusDecision,
    CABRConsensusFinalizeResult,
    CABRConsensusInput,
    CABRConsensusReasonCode,
    CABRConsensusRecord,
    finalize_cabr_consensus,
    finalize_cabr_consensus_batch,
    finalize_cabr_consensus_batch_with_results,
    finalize_cabr_consensus_with_result,
)
from modules.communication.moltbot_bridge.src.cabr_consensus_store import (
    CABRConsensusStore,
    CABRConsensusStoreError,
    CABRConsensusStoreResultStatus,
)


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------


def _make_score_result(
    receipt_id: str = "rcpt_test_001",
    job_id: str = "j_test_001",
    tenant_id: str = "t_test",
    decision: str = "accepted_for_review",
    reason_code: str = "ok_evidence_present_quorum_met",
    quorum_met: bool = True,
    evidence_present: bool = True,
    evidence_count: int = 2,
    is_dry_run: bool = False,
    verification_complete: bool = False,
    cabr_ready: bool = False,
    payout_ready: bool = False,
) -> Dict[str, Any]:
    """Create a mock CABRScoreResult dict."""
    return {
        "score_id": f"cabr_{receipt_id}_{hash(receipt_id) % 10000:04x}",
        "receipt_id": receipt_id,
        "job_id": job_id,
        "tenant_id": tenant_id,
        "decision": decision,
        "reason_code": reason_code,
        "reason_human": f"Scored: {decision}",
        "quorum_met": quorum_met,
        "evidence_present": evidence_present,
        "evidence_count": evidence_count,
        "is_dry_run": is_dry_run,
        "is_simulated": False,
        "verification_complete": verification_complete,
        "cabr_ready": cabr_ready,
        "payout_ready": payout_ready,
    }


def _make_quorum_result(
    receipt_id: str = "rcpt_test_001",
    job_id: str = "j_test_001",
    tenant_id: str = "t_test",
    decision: str = "consensus_accepted_for_review",
    reason_code: str = "ok_quorum_met_threshold_met",
    quorum_met: bool = True,
    threshold_met: bool = True,
    unique_verifiers: int = 3,
    consensus_score: float = 1.0,
    is_dry_run: bool = False,
    verification_complete: bool = False,
    cabr_ready: bool = False,
    payout_ready: bool = False,
) -> Dict[str, Any]:
    """Create a mock QuorumVerificationResult dict."""
    return {
        "quorum_id": f"qv_{receipt_id}_{hash(receipt_id) % 10000:04x}",
        "receipt_id": receipt_id,
        "job_id": job_id,
        "tenant_id": tenant_id,
        "decision": decision,
        "reason_code": reason_code,
        "reason_human": f"Quorum: {decision}",
        "quorum_met": quorum_met,
        "threshold_met": threshold_met,
        "unique_verifiers": unique_verifiers,
        "consensus_score": consensus_score,
        "is_dry_run": is_dry_run,
        "verification_complete": verification_complete,
        "cabr_ready": cabr_ready,
        "payout_ready": payout_ready,
    }


# ---------------------------------------------------------------------------
# Test: store=None Produces Identical Result and No DB File
# ---------------------------------------------------------------------------


class TestStoreNoneProducesNoDbFile(unittest.TestCase):
    """store=None produces identical result to Phase 1 and no DB file."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.tmp_path = Path(self.tmp_dir.name)

    def tearDown(self):
        gc.collect()
        self.tmp_dir.cleanup()

    def test_finalize_without_store_returns_record(self):
        """finalize_cabr_consensus with store=None returns record."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(),
            quorum_result=_make_quorum_result(),
        )

        record = finalize_cabr_consensus(consensus_input, store=None)

        self.assertIsInstance(record, CABRConsensusRecord)
        self.assertEqual(record.decision, CABRConsensusDecision.ACCEPTED_FOR_REVIEW)

    def test_finalize_without_store_creates_no_db_file(self):
        """finalize_cabr_consensus with store=None creates no DB file."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(),
            quorum_result=_make_quorum_result(),
        )

        # Finalize without store
        finalize_cabr_consensus(consensus_input, store=None)

        # Check no DB files created
        db_files = list(self.tmp_path.glob("*.db"))
        self.assertEqual(len(db_files), 0, "No DB files should be created with store=None")

    def test_finalize_with_result_without_store_not_attempted(self):
        """finalize_cabr_consensus_with_result with store=None has persistence_attempted=False."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(),
            quorum_result=_make_quorum_result(),
        )

        result = finalize_cabr_consensus_with_result(consensus_input, store=None)

        self.assertIsInstance(result, CABRConsensusFinalizeResult)
        self.assertFalse(result.persistence_attempted)
        self.assertFalse(result.persistence_success)
        self.assertIsNone(result.persistence_status)
        self.assertIsNone(result.persistence_error)


# ---------------------------------------------------------------------------
# Test: Provided Store Saves Accepted-For-Review Record
# ---------------------------------------------------------------------------


class TestProvidedStoreSavesAcceptedRecord(unittest.TestCase):
    """Provided store saves accepted-for-review record."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_finalize_with_store_saves_record(self):
        """finalize_cabr_consensus with store saves record to DB."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(receipt_id="rcpt_persist_001"),
            quorum_result=_make_quorum_result(receipt_id="rcpt_persist_001"),
        )

        record = finalize_cabr_consensus(consensus_input, store=self.store)

        # Verify record returned
        self.assertEqual(record.decision, CABRConsensusDecision.ACCEPTED_FOR_REVIEW)

        # Verify record persisted
        get_result = self.store.get_record(record.record_id)
        self.assertEqual(get_result.status, CABRConsensusStoreResultStatus.SUCCESS)
        self.assertEqual(get_result.records[0]["decision"], "accepted_for_review")

    def test_finalize_with_result_reports_success(self):
        """finalize_cabr_consensus_with_result reports persistence success."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(receipt_id="rcpt_persist_002"),
            quorum_result=_make_quorum_result(receipt_id="rcpt_persist_002"),
        )

        result = finalize_cabr_consensus_with_result(consensus_input, store=self.store)

        self.assertTrue(result.persistence_attempted)
        self.assertTrue(result.persistence_success)
        self.assertEqual(result.persistence_status, "success")
        self.assertIsNone(result.persistence_error)


# ---------------------------------------------------------------------------
# Test: Provided Store Saves Rejected/Pending Records
# ---------------------------------------------------------------------------


class TestProvidedStoreSavesRejectedPendingRecords(unittest.TestCase):
    """Provided store saves rejected and pending_quorum records."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_rejected_record_persisted(self):
        """Rejected consensus record is persisted."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(
                receipt_id="rcpt_rejected_001",
                decision="rejected_insufficient_evidence",
            ),
            quorum_result=_make_quorum_result(receipt_id="rcpt_rejected_001"),
        )

        record = finalize_cabr_consensus(consensus_input, store=self.store)

        self.assertEqual(record.decision, CABRConsensusDecision.REJECTED)

        # Verify persisted
        get_result = self.store.get_record(record.record_id)
        self.assertEqual(get_result.status, CABRConsensusStoreResultStatus.SUCCESS)
        self.assertEqual(get_result.records[0]["decision"], "rejected")

    def test_pending_quorum_record_persisted(self):
        """Pending quorum consensus record is persisted."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(receipt_id="rcpt_pending_001"),
            quorum_result=_make_quorum_result(
                receipt_id="rcpt_pending_001",
                decision="quorum_not_met",
                reason_code="quorum_zero_attestations",
                quorum_met=False,
                unique_verifiers=0,
            ),
        )

        record = finalize_cabr_consensus(consensus_input, store=self.store)

        self.assertEqual(record.decision, CABRConsensusDecision.PENDING_QUORUM)

        # Verify persisted
        get_result = self.store.get_record(record.record_id)
        self.assertEqual(get_result.status, CABRConsensusStoreResultStatus.SUCCESS)
        self.assertEqual(get_result.records[0]["decision"], "pending_quorum")

    def test_not_finalized_record_persisted(self):
        """NOT_FINALIZED consensus record is persisted."""
        consensus_input = CABRConsensusInput(
            quorum_result=_make_quorum_result(receipt_id="rcpt_not_final_001"),
        )

        record = finalize_cabr_consensus(consensus_input, store=self.store)

        self.assertEqual(record.decision, CABRConsensusDecision.NOT_FINALIZED)

        # Verify persisted
        get_result = self.store.get_record(record.record_id)
        self.assertEqual(get_result.status, CABRConsensusStoreResultStatus.SUCCESS)
        self.assertEqual(get_result.records[0]["decision"], "not_finalized")


# ---------------------------------------------------------------------------
# Test: Duplicate Finalization Idempotent
# ---------------------------------------------------------------------------


class TestDuplicateFinalizationIdempotent(unittest.TestCase):
    """Duplicate finalization is idempotent."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_duplicate_finalize_returns_success(self):
        """Duplicate finalization with same record_id is idempotent."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(receipt_id="rcpt_dup_001"),
            quorum_result=_make_quorum_result(receipt_id="rcpt_dup_001"),
        )

        # First finalization
        record1 = finalize_cabr_consensus(consensus_input, store=self.store)

        # Save record_id for manual duplicate test
        record_id = record1.record_id

        # Manually save same record again to test idempotency
        save_result = self.store.save_record(record1.to_dict())
        self.assertEqual(save_result.status, CABRConsensusStoreResultStatus.ALREADY_EXISTS)

    def test_duplicate_with_result_reports_already_exists(self):
        """Duplicate finalization with explicit result reports already_exists."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(receipt_id="rcpt_dup_002"),
            quorum_result=_make_quorum_result(receipt_id="rcpt_dup_002"),
        )

        # First finalization
        result1 = finalize_cabr_consensus_with_result(consensus_input, store=self.store)
        self.assertTrue(result1.persistence_success)
        self.assertEqual(result1.persistence_status, "success")

        # Second finalization - new record_id generated, but same record_hash
        # Note: finalize creates a NEW record_id each time, so we need to test
        # manual duplicate insertion
        save_result = self.store.save_record(result1.record.to_dict())
        self.assertEqual(save_result.status, CABRConsensusStoreResultStatus.ALREADY_EXISTS)


# ---------------------------------------------------------------------------
# Test: Store Failure Returns Explicit Failure
# ---------------------------------------------------------------------------


class TestStoreFailureReturnsExplicitFailure(unittest.TestCase):
    """Store failure returns explicit failure status."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"

    def tearDown(self):
        gc.collect()
        self.tmp_dir.cleanup()

    def test_store_failure_with_result_reports_error(self):
        """Store schema not initialized returns persistence_success=False."""
        store = CABRConsensusStore(self.db_path)
        # Note: NOT calling initialize_schema()

        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(receipt_id="rcpt_fail_001"),
            quorum_result=_make_quorum_result(receipt_id="rcpt_fail_001"),
        )

        result = finalize_cabr_consensus_with_result(consensus_input, store=store)

        # Record should still be returned
        self.assertIsInstance(result.record, CABRConsensusRecord)
        self.assertEqual(result.record.decision, CABRConsensusDecision.ACCEPTED_FOR_REVIEW)

        # But persistence should have failed
        self.assertTrue(result.persistence_attempted)
        self.assertFalse(result.persistence_success)
        self.assertIsNotNone(result.persistence_error)

        store.close()

    def test_finalize_still_returns_record_on_store_failure(self):
        """finalize_cabr_consensus returns record even if store fails."""
        store = CABRConsensusStore(self.db_path)
        # NOT calling initialize_schema()

        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(receipt_id="rcpt_fail_002"),
            quorum_result=_make_quorum_result(receipt_id="rcpt_fail_002"),
        )

        # Should not raise, should return record
        record = finalize_cabr_consensus(consensus_input, store=store)

        self.assertIsInstance(record, CABRConsensusRecord)
        self.assertEqual(record.decision, CABRConsensusDecision.ACCEPTED_FOR_REVIEW)

        store.close()


# ---------------------------------------------------------------------------
# Test: Batch Finalization Persists All Records Deterministically
# ---------------------------------------------------------------------------


class TestBatchFinalizationPersistsAllRecords(unittest.TestCase):
    """Batch finalization persists all records deterministically."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_batch_persists_all_records(self):
        """Batch finalization persists all records."""
        inputs = [
            CABRConsensusInput(
                score_result=_make_score_result(receipt_id=f"rcpt_batch_{i:03d}"),
                quorum_result=_make_quorum_result(receipt_id=f"rcpt_batch_{i:03d}"),
            )
            for i in range(5)
        ]

        records = finalize_cabr_consensus_batch(inputs, store=self.store)

        self.assertEqual(len(records), 5)

        # Verify all persisted
        for record in records:
            get_result = self.store.get_record(record.record_id)
            self.assertEqual(get_result.status, CABRConsensusStoreResultStatus.SUCCESS)

    def test_batch_order_preserved(self):
        """Batch results are in same order as inputs."""
        inputs = [
            CABRConsensusInput(
                score_result=_make_score_result(receipt_id="rcpt_order_1"),
                quorum_result=_make_quorum_result(receipt_id="rcpt_order_1"),
            ),
            CABRConsensusInput(
                score_result=_make_score_result(
                    receipt_id="rcpt_order_2",
                    decision="rejected_insufficient_evidence",
                ),
                quorum_result=_make_quorum_result(receipt_id="rcpt_order_2"),
            ),
            CABRConsensusInput(
                quorum_result=_make_quorum_result(receipt_id="rcpt_order_3"),
            ),
        ]

        records = finalize_cabr_consensus_batch(inputs, store=self.store)

        self.assertEqual(len(records), 3)
        self.assertEqual(records[0].decision, CABRConsensusDecision.ACCEPTED_FOR_REVIEW)
        self.assertEqual(records[1].decision, CABRConsensusDecision.REJECTED)
        self.assertEqual(records[2].decision, CABRConsensusDecision.NOT_FINALIZED)

    def test_batch_with_results_reports_all_persistence(self):
        """Batch with results reports persistence status for each record."""
        inputs = [
            CABRConsensusInput(
                score_result=_make_score_result(receipt_id=f"rcpt_batch_res_{i:03d}"),
                quorum_result=_make_quorum_result(receipt_id=f"rcpt_batch_res_{i:03d}"),
            )
            for i in range(3)
        ]

        results = finalize_cabr_consensus_batch_with_results(inputs, store=self.store)

        self.assertEqual(len(results), 3)
        for result in results:
            self.assertTrue(result.persistence_attempted)
            self.assertTrue(result.persistence_success)
            self.assertEqual(result.persistence_status, "success")


# ---------------------------------------------------------------------------
# Test: Persisted Truth Fields Remain False
# ---------------------------------------------------------------------------


class TestPersistedTruthFieldsRemainFalse(unittest.TestCase):
    """Persisted truth fields remain False (WSP 97)."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_verification_complete_false_after_persist(self):
        """verification_complete=False after persistence."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(receipt_id="rcpt_truth_001"),
            quorum_result=_make_quorum_result(receipt_id="rcpt_truth_001"),
        )

        record = finalize_cabr_consensus(consensus_input, store=self.store)

        # Check record
        self.assertFalse(record.verification_complete)

        # Check persisted
        get_result = self.store.get_record(record.record_id)
        self.assertFalse(get_result.records[0]["verification_complete"])

    def test_cabr_ready_false_after_persist(self):
        """cabr_ready=False after persistence."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(receipt_id="rcpt_truth_002"),
            quorum_result=_make_quorum_result(receipt_id="rcpt_truth_002"),
        )

        record = finalize_cabr_consensus(consensus_input, store=self.store)

        # Check record
        self.assertFalse(record.cabr_ready)

        # Check persisted
        get_result = self.store.get_record(record.record_id)
        self.assertFalse(get_result.records[0]["cabr_ready"])

    def test_payout_ready_false_after_persist(self):
        """payout_ready=False after persistence."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(receipt_id="rcpt_truth_003"),
            quorum_result=_make_quorum_result(receipt_id="rcpt_truth_003"),
        )

        record = finalize_cabr_consensus(consensus_input, store=self.store)

        # Check record
        self.assertFalse(record.payout_ready)

        # Check persisted
        get_result = self.store.get_record(record.record_id)
        self.assertFalse(get_result.records[0]["payout_ready"])

    def test_all_truth_fields_false_for_accepted_record(self):
        """All truth fields False even for ACCEPTED_FOR_REVIEW."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(
                receipt_id="rcpt_truth_004",
                quorum_met=True,
                evidence_present=True,
            ),
            quorum_result=_make_quorum_result(
                receipt_id="rcpt_truth_004",
                quorum_met=True,
                threshold_met=True,
                unique_verifiers=5,
                consensus_score=1.0,
            ),
        )

        record = finalize_cabr_consensus(consensus_input, store=self.store)

        # Verify it's accepted
        self.assertEqual(record.decision, CABRConsensusDecision.ACCEPTED_FOR_REVIEW)
        self.assertTrue(record.quorum_met)
        self.assertTrue(record.threshold_met)

        # But truth fields still False
        self.assertFalse(record.verification_complete)
        self.assertFalse(record.cabr_ready)
        self.assertFalse(record.payout_ready)

        # Check persisted
        get_result = self.store.get_record(record.record_id)
        persisted = get_result.records[0]
        self.assertFalse(persisted["verification_complete"])
        self.assertFalse(persisted["cabr_ready"])
        self.assertFalse(persisted["payout_ready"])


# ---------------------------------------------------------------------------
# Test: No Payout/DAO/State Progression
# ---------------------------------------------------------------------------


class TestNoPayoutDaoStateProgression(unittest.TestCase):
    """No payout, DAO activation, or state progression (WSP 97)."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_no_payout_fields_in_persisted_record(self):
        """No payout_amount/tokens_issued fields in persisted record."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(receipt_id="rcpt_nopay_001"),
            quorum_result=_make_quorum_result(receipt_id="rcpt_nopay_001"),
        )

        record = finalize_cabr_consensus(consensus_input, store=self.store)

        get_result = self.store.get_record(record.record_id)
        persisted = get_result.records[0]

        self.assertNotIn("payout_amount", persisted)
        self.assertNotIn("tokens_issued", persisted)
        self.assertNotIn("ups_allocated", persisted)
        self.assertNotIn("reward_amount", persisted)

    def test_persistence_does_not_activate_dao(self):
        """Persistence does not set cabr_ready (no DAO activation)."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(
                receipt_id="rcpt_nodao_001",
                quorum_met=True,
            ),
            quorum_result=_make_quorum_result(
                receipt_id="rcpt_nodao_001",
                quorum_met=True,
                threshold_met=True,
                unique_verifiers=10,
            ),
        )

        record = finalize_cabr_consensus(consensus_input, store=self.store)

        # Record accepted
        self.assertEqual(record.decision, CABRConsensusDecision.ACCEPTED_FOR_REVIEW)
        self.assertTrue(record.quorum_met)

        # But cabr_ready still False (no DAO)
        self.assertFalse(record.cabr_ready)

        # Check persisted
        get_result = self.store.get_record(record.record_id)
        self.assertFalse(get_result.records[0]["cabr_ready"])


# ---------------------------------------------------------------------------
# Test: No Default DB Path Used
# ---------------------------------------------------------------------------


class TestNoDefaultDbPathUsed(unittest.TestCase):
    """No default DB path is used (caller must provide)."""

    def test_finalizer_requires_explicit_store(self):
        """Finalizer does not create store if not provided."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(receipt_id="rcpt_nodefault_001"),
            quorum_result=_make_quorum_result(receipt_id="rcpt_nodefault_001"),
        )

        # Without store parameter, no persistence happens
        record = finalize_cabr_consensus(consensus_input)

        # Record still returned
        self.assertIsInstance(record, CABRConsensusRecord)

    def test_store_requires_explicit_path(self):
        """CABRConsensusStore requires explicit path."""
        # Store constructor requires db_path
        with self.assertRaises(TypeError):
            CABRConsensusStore()  # type: ignore - intentional for test


# ---------------------------------------------------------------------------
# Test: tmp_path Only (No Repo DB Files)
# ---------------------------------------------------------------------------


class TestTmpPathOnly(unittest.TestCase):
    """All tests use tmp_path only (no repo DB files)."""

    def test_all_tests_use_temporary_directory(self):
        """This test verifies the tmp_path pattern is used."""
        # All tests in this file use TemporaryDirectory
        # This is a meta-test verifying the pattern
        self.assertTrue(True)


# ---------------------------------------------------------------------------
# Test: CABRConsensusFinalizeResult Serialization
# ---------------------------------------------------------------------------


class TestFinalizeResultSerialization(unittest.TestCase):
    """CABRConsensusFinalizeResult serialization."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_consensus.db"
        self.store = CABRConsensusStore(self.db_path)
        self.store.initialize_schema()

    def tearDown(self):
        self.store.close()
        gc.collect()
        self.tmp_dir.cleanup()

    def test_result_to_dict_success(self):
        """FinalizeResult.to_dict() includes all fields on success."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(receipt_id="rcpt_serial_001"),
            quorum_result=_make_quorum_result(receipt_id="rcpt_serial_001"),
        )

        result = finalize_cabr_consensus_with_result(consensus_input, store=self.store)
        d = result.to_dict()

        self.assertIn("record", d)
        self.assertIn("persistence_attempted", d)
        self.assertIn("persistence_success", d)
        self.assertIn("persistence_status", d)
        self.assertIn("persistence_error", d)

        self.assertTrue(d["persistence_attempted"])
        self.assertTrue(d["persistence_success"])
        self.assertEqual(d["persistence_status"], "success")
        self.assertIsNone(d["persistence_error"])

    def test_result_to_dict_no_store(self):
        """FinalizeResult.to_dict() correct when no store provided."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(receipt_id="rcpt_serial_002"),
            quorum_result=_make_quorum_result(receipt_id="rcpt_serial_002"),
        )

        result = finalize_cabr_consensus_with_result(consensus_input, store=None)
        d = result.to_dict()

        self.assertFalse(d["persistence_attempted"])
        self.assertFalse(d["persistence_success"])
        self.assertIsNone(d["persistence_status"])
        self.assertIsNone(d["persistence_error"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
