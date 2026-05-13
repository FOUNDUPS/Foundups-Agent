#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for CABR Consensus Finalizer Phase 1.

Validates deterministic consensus finalization per WSP 29 and WSP 97 truth boundaries.

Required coverage:
  - missing score result fails closed (NOT_FINALIZED)
  - missing quorum result pending quorum (PENDING_QUORUM)
  - scoring reject rejects (REJECTED)
  - quorum not met pending quorum (PENDING_QUORUM)
  - scoring accepted + quorum accepted -> accepted for review (ACCEPTED_FOR_REVIEW)
  - truth-boundary violation blocks (BLOCKED_TRUTH_BOUNDARY)
  - deterministic record hash stable
  - batch finalization deterministic
  - no payout status changes
  - no DAO activation
  - no external dependency
  - verification_complete=False always
  - cabr_ready=False always
  - payout_ready=False always

Slice: CABR_CONSENSUS_FINALIZATION_PHASE1
Worker: W1
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from modules.communication.moltbot_bridge.src.cabr_consensus_finalizer import (
    CABRConsensusDecision,
    CABRConsensusInput,
    CABRConsensusReasonCode,
    CABRConsensusRecord,
    finalize_cabr_consensus,
    finalize_cabr_consensus_batch,
    generate_record_hash,
    generate_record_id,
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
) -> dict:
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
) -> dict:
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
# Test: Missing Score Result Fails Closed
# ---------------------------------------------------------------------------


class TestMissingScoreResultFailsClosed(unittest.TestCase):
    """Missing score result results in NOT_FINALIZED."""

    def test_missing_score_result_not_finalized(self):
        """No score result -> NOT_FINALIZED."""
        consensus_input = CABRConsensusInput(
            quorum_result=_make_quorum_result(),
        )

        record = finalize_cabr_consensus(consensus_input)

        self.assertEqual(record.decision, CABRConsensusDecision.NOT_FINALIZED)
        self.assertEqual(record.reason_code, CABRConsensusReasonCode.MISSING_SCORE_RESULT)

    def test_missing_both_results_not_finalized(self):
        """No score and no quorum -> NOT_FINALIZED with MISSING_BOTH_RESULTS."""
        consensus_input = CABRConsensusInput()

        record = finalize_cabr_consensus(consensus_input)

        self.assertEqual(record.decision, CABRConsensusDecision.NOT_FINALIZED)
        self.assertEqual(record.reason_code, CABRConsensusReasonCode.MISSING_BOTH_RESULTS)

    def test_missing_score_preserves_quorum_metrics(self):
        """Missing score still extracts quorum metrics."""
        consensus_input = CABRConsensusInput(
            quorum_result=_make_quorum_result(unique_verifiers=5, consensus_score=0.8),
        )

        record = finalize_cabr_consensus(consensus_input)

        self.assertEqual(record.unique_verifiers, 5)
        self.assertAlmostEqual(record.consensus_score, 0.8, places=2)


# ---------------------------------------------------------------------------
# Test: Missing Quorum Result Pending Quorum
# ---------------------------------------------------------------------------


class TestMissingQuorumResultPendingQuorum(unittest.TestCase):
    """Missing quorum result results in PENDING_QUORUM."""

    def test_missing_quorum_result_pending(self):
        """No quorum result -> PENDING_QUORUM."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(),
        )

        record = finalize_cabr_consensus(consensus_input)

        self.assertEqual(record.decision, CABRConsensusDecision.PENDING_QUORUM)
        self.assertEqual(record.reason_code, CABRConsensusReasonCode.MISSING_QUORUM_RESULT)

    def test_missing_quorum_preserves_score_metrics(self):
        """Missing quorum still extracts score metrics."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(evidence_count=5, evidence_present=True),
        )

        record = finalize_cabr_consensus(consensus_input)

        self.assertEqual(record.evidence_count, 5)
        self.assertTrue(record.evidence_present)


# ---------------------------------------------------------------------------
# Test: Scoring Reject Rejects
# ---------------------------------------------------------------------------


class TestScoringRejectRejects(unittest.TestCase):
    """Scoring rejection results in REJECTED."""

    def test_score_rejected_insufficient_evidence(self):
        """Scoring rejection (insufficient evidence) -> REJECTED."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(
                decision="rejected_insufficient_evidence",
                reason_code="rejected_empty_evidence",
                evidence_present=False,
            ),
            quorum_result=_make_quorum_result(),
        )

        record = finalize_cabr_consensus(consensus_input)

        self.assertEqual(record.decision, CABRConsensusDecision.REJECTED)
        self.assertEqual(
            record.reason_code,
            CABRConsensusReasonCode.SCORE_REJECTED_INSUFFICIENT_EVIDENCE,
        )

    def test_score_rejected_missing_identity(self):
        """Scoring rejection (missing identity) -> REJECTED."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(
                decision="rejected_missing_identity",
                reason_code="rejected_no_receipt_id",
            ),
            quorum_result=_make_quorum_result(),
        )

        record = finalize_cabr_consensus(consensus_input)

        self.assertEqual(record.decision, CABRConsensusDecision.REJECTED)
        self.assertEqual(
            record.reason_code,
            CABRConsensusReasonCode.SCORE_REJECTED_MISSING_IDENTITY,
        )

    def test_score_rejected_duplicate_verifiers(self):
        """Scoring rejection (duplicate verifiers) -> REJECTED."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(
                decision="rejected_duplicate_verifiers",
                reason_code="rejected_duplicate_verifier_ids",
            ),
            quorum_result=_make_quorum_result(),
        )

        record = finalize_cabr_consensus(consensus_input)

        self.assertEqual(record.decision, CABRConsensusDecision.REJECTED)
        self.assertEqual(
            record.reason_code,
            CABRConsensusReasonCode.SCORE_REJECTED_DUPLICATE_VERIFIERS,
        )

    def test_score_rejected_pavs_failed(self):
        """Scoring rejection (pAVS failed) -> REJECTED."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(
                decision="rejected_pavs_failed",
                reason_code="rejected_pavs_blocked_missing_evidence",
            ),
            quorum_result=_make_quorum_result(),
        )

        record = finalize_cabr_consensus(consensus_input)

        self.assertEqual(record.decision, CABRConsensusDecision.REJECTED)
        self.assertEqual(
            record.reason_code,
            CABRConsensusReasonCode.SCORE_REJECTED_PAVS_FAILED,
        )

    def test_score_rejected_truth_boundary(self):
        """Scoring rejection (truth boundary) -> REJECTED."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(
                decision="rejected_truth_boundary",
                reason_code="rejected_verification_complete_claimed",
            ),
            quorum_result=_make_quorum_result(),
        )

        record = finalize_cabr_consensus(consensus_input)

        self.assertEqual(record.decision, CABRConsensusDecision.REJECTED)
        self.assertEqual(
            record.reason_code,
            CABRConsensusReasonCode.SCORE_REJECTED_TRUTH_BOUNDARY,
        )


# ---------------------------------------------------------------------------
# Test: Quorum Not Met Pending Quorum
# ---------------------------------------------------------------------------


class TestQuorumNotMetPendingQuorum(unittest.TestCase):
    """Quorum not met results in PENDING_QUORUM."""

    def test_quorum_not_met_zero_attestations(self):
        """Quorum not met (zero attestations) -> PENDING_QUORUM."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(),
            quorum_result=_make_quorum_result(
                decision="quorum_not_met",
                reason_code="quorum_zero_attestations",
                quorum_met=False,
                unique_verifiers=0,
            ),
        )

        record = finalize_cabr_consensus(consensus_input)

        self.assertEqual(record.decision, CABRConsensusDecision.PENDING_QUORUM)
        self.assertEqual(
            record.reason_code,
            CABRConsensusReasonCode.QUORUM_NOT_MET_ZERO_ATTESTATIONS,
        )
        self.assertFalse(record.quorum_met)

    def test_quorum_not_met_insufficient_verifiers(self):
        """Quorum not met (insufficient verifiers) -> PENDING_QUORUM."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(),
            quorum_result=_make_quorum_result(
                decision="quorum_not_met",
                reason_code="quorum_insufficient_unique_verifiers",
                quorum_met=False,
                unique_verifiers=2,
            ),
        )

        record = finalize_cabr_consensus(consensus_input)

        self.assertEqual(record.decision, CABRConsensusDecision.PENDING_QUORUM)
        self.assertEqual(
            record.reason_code,
            CABRConsensusReasonCode.QUORUM_NOT_MET_INSUFFICIENT_VERIFIERS,
        )
        self.assertEqual(record.unique_verifiers, 2)

    def test_quorum_met_threshold_not_met(self):
        """Quorum met but threshold not met -> PENDING_QUORUM."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(),
            quorum_result=_make_quorum_result(
                decision="quorum_met_pending_consensus",
                reason_code="pending_threshold_not_met",
                quorum_met=True,
                threshold_met=False,
                consensus_score=0.2,
            ),
        )

        record = finalize_cabr_consensus(consensus_input)

        self.assertEqual(record.decision, CABRConsensusDecision.PENDING_QUORUM)
        self.assertEqual(
            record.reason_code,
            CABRConsensusReasonCode.QUORUM_MET_THRESHOLD_NOT_MET,
        )
        self.assertTrue(record.quorum_met)
        self.assertFalse(record.threshold_met)

    def test_score_pending_quorum(self):
        """Score pending quorum -> PENDING_QUORUM."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(
                decision="accepted_for_review_pending_quorum",
                reason_code="ok_evidence_present_pending_quorum",
                quorum_met=False,
            ),
            quorum_result=_make_quorum_result(),
        )

        record = finalize_cabr_consensus(consensus_input)

        self.assertEqual(record.decision, CABRConsensusDecision.PENDING_QUORUM)
        self.assertEqual(
            record.reason_code,
            CABRConsensusReasonCode.SCORE_PENDING_QUORUM,
        )


# ---------------------------------------------------------------------------
# Test: Scoring Accepted + Quorum Accepted -> Accepted For Review
# ---------------------------------------------------------------------------


class TestScoringAcceptedQuorumAcceptedAcceptedForReview(unittest.TestCase):
    """Scoring accepted + quorum accepted -> ACCEPTED_FOR_REVIEW."""

    def test_both_accepted_for_review(self):
        """Both accepted -> ACCEPTED_FOR_REVIEW."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(),
            quorum_result=_make_quorum_result(),
        )

        record = finalize_cabr_consensus(consensus_input)

        self.assertEqual(record.decision, CABRConsensusDecision.ACCEPTED_FOR_REVIEW)
        self.assertEqual(
            record.reason_code,
            CABRConsensusReasonCode.OK_SCORE_ACCEPTED_QUORUM_MET,
        )

    def test_dry_run_accepted_for_review(self):
        """Dry-run accepted -> ACCEPTED_FOR_REVIEW with dry-run reason."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(is_dry_run=True),
            quorum_result=_make_quorum_result(is_dry_run=True),
        )

        record = finalize_cabr_consensus(consensus_input)

        self.assertEqual(record.decision, CABRConsensusDecision.ACCEPTED_FOR_REVIEW)
        self.assertEqual(
            record.reason_code,
            CABRConsensusReasonCode.OK_SCORE_ACCEPTED_DRY_RUN,
        )
        self.assertTrue(record.is_dry_run)

    def test_accepted_preserves_metrics(self):
        """Accepted record preserves all metrics."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(evidence_count=5),
            quorum_result=_make_quorum_result(
                unique_verifiers=4,
                consensus_score=0.9,
            ),
        )

        record = finalize_cabr_consensus(consensus_input)

        self.assertEqual(record.evidence_count, 5)
        self.assertEqual(record.unique_verifiers, 4)
        self.assertAlmostEqual(record.consensus_score, 0.9, places=2)
        self.assertTrue(record.quorum_met)
        self.assertTrue(record.threshold_met)


# ---------------------------------------------------------------------------
# Test: Truth-Boundary Violation Blocks
# ---------------------------------------------------------------------------


class TestTruthBoundaryViolationBlocks(unittest.TestCase):
    """Truth boundary violations result in BLOCKED_TRUTH_BOUNDARY."""

    def test_score_verification_complete_true_blocks(self):
        """Score with verification_complete=True -> BLOCKED."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(verification_complete=True),
            quorum_result=_make_quorum_result(),
        )

        record = finalize_cabr_consensus(consensus_input)

        self.assertEqual(record.decision, CABRConsensusDecision.BLOCKED_TRUTH_BOUNDARY)
        self.assertEqual(
            record.reason_code,
            CABRConsensusReasonCode.INPUT_VERIFICATION_COMPLETE_TRUE,
        )

    def test_score_cabr_ready_true_blocks(self):
        """Score with cabr_ready=True -> BLOCKED."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(cabr_ready=True),
            quorum_result=_make_quorum_result(),
        )

        record = finalize_cabr_consensus(consensus_input)

        self.assertEqual(record.decision, CABRConsensusDecision.BLOCKED_TRUTH_BOUNDARY)
        self.assertEqual(
            record.reason_code,
            CABRConsensusReasonCode.INPUT_CABR_READY_TRUE,
        )

    def test_score_payout_ready_true_blocks(self):
        """Score with payout_ready=True -> BLOCKED."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(payout_ready=True),
            quorum_result=_make_quorum_result(),
        )

        record = finalize_cabr_consensus(consensus_input)

        self.assertEqual(record.decision, CABRConsensusDecision.BLOCKED_TRUTH_BOUNDARY)
        self.assertEqual(
            record.reason_code,
            CABRConsensusReasonCode.INPUT_PAYOUT_READY_TRUE,
        )

    def test_quorum_verification_complete_true_blocks(self):
        """Quorum with verification_complete=True -> BLOCKED."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(),
            quorum_result=_make_quorum_result(verification_complete=True),
        )

        record = finalize_cabr_consensus(consensus_input)

        self.assertEqual(record.decision, CABRConsensusDecision.BLOCKED_TRUTH_BOUNDARY)
        self.assertEqual(
            record.reason_code,
            CABRConsensusReasonCode.QUORUM_VERIFICATION_COMPLETE_TRUE,
        )

    def test_quorum_cabr_ready_true_blocks(self):
        """Quorum with cabr_ready=True -> BLOCKED."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(),
            quorum_result=_make_quorum_result(cabr_ready=True),
        )

        record = finalize_cabr_consensus(consensus_input)

        self.assertEqual(record.decision, CABRConsensusDecision.BLOCKED_TRUTH_BOUNDARY)
        self.assertEqual(
            record.reason_code,
            CABRConsensusReasonCode.QUORUM_CABR_READY_TRUE,
        )

    def test_quorum_payout_ready_true_blocks(self):
        """Quorum with payout_ready=True -> BLOCKED."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(),
            quorum_result=_make_quorum_result(payout_ready=True),
        )

        record = finalize_cabr_consensus(consensus_input)

        self.assertEqual(record.decision, CABRConsensusDecision.BLOCKED_TRUTH_BOUNDARY)
        self.assertEqual(
            record.reason_code,
            CABRConsensusReasonCode.QUORUM_PAYOUT_READY_TRUE,
        )


# ---------------------------------------------------------------------------
# Test: Deterministic Record Hash Stable
# ---------------------------------------------------------------------------


class TestDeterministicRecordHashStable(unittest.TestCase):
    """Record hash is deterministic for same inputs."""

    def test_same_inputs_same_hash(self):
        """Same inputs produce same hash."""
        hash1 = generate_record_hash(
            receipt_id="rcpt_test_001",
            job_id="j_test_001",
            tenant_id="t_test",
            score_id="cabr_test_001",
            quorum_id="qv_test_001",
            score_decision="accepted_for_review",
            quorum_decision="consensus_accepted_for_review",
        )
        hash2 = generate_record_hash(
            receipt_id="rcpt_test_001",
            job_id="j_test_001",
            tenant_id="t_test",
            score_id="cabr_test_001",
            quorum_id="qv_test_001",
            score_decision="accepted_for_review",
            quorum_decision="consensus_accepted_for_review",
        )

        self.assertEqual(hash1, hash2)

    def test_different_inputs_different_hash(self):
        """Different inputs produce different hash."""
        hash1 = generate_record_hash(
            receipt_id="rcpt_test_001",
            job_id="j_test_001",
            tenant_id="t_test",
            score_id="cabr_test_001",
            quorum_id="qv_test_001",
            score_decision="accepted_for_review",
            quorum_decision="consensus_accepted_for_review",
        )
        hash2 = generate_record_hash(
            receipt_id="rcpt_test_002",  # Different receipt
            job_id="j_test_001",
            tenant_id="t_test",
            score_id="cabr_test_001",
            quorum_id="qv_test_001",
            score_decision="accepted_for_review",
            quorum_decision="consensus_accepted_for_review",
        )

        self.assertNotEqual(hash1, hash2)

    def test_hash_format_valid(self):
        """Hash is 32-char hex string."""
        hash_val = generate_record_hash(
            receipt_id="rcpt_test_001",
            job_id="j_test_001",
            tenant_id="t_test",
            score_id="cabr_test_001",
            quorum_id="qv_test_001",
            score_decision="accepted_for_review",
            quorum_decision="consensus_accepted_for_review",
        )

        self.assertEqual(len(hash_val), 32)
        # Should be valid hex
        int(hash_val, 16)

    def test_finalized_records_have_stable_hash(self):
        """Records finalized from same inputs have same hash."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(receipt_id="rcpt_stable_001"),
            quorum_result=_make_quorum_result(receipt_id="rcpt_stable_001"),
        )

        record1 = finalize_cabr_consensus(consensus_input)
        record2 = finalize_cabr_consensus(consensus_input)

        self.assertEqual(record1.record_hash, record2.record_hash)


# ---------------------------------------------------------------------------
# Test: Batch Finalization Deterministic
# ---------------------------------------------------------------------------


class TestBatchFinalizationDeterministic(unittest.TestCase):
    """Batch finalization returns deterministic results in order."""

    def test_batch_order_preserved(self):
        """Batch results are in same order as inputs."""
        inputs = [
            CABRConsensusInput(
                score_result=_make_score_result(receipt_id="rcpt_batch_1"),
                quorum_result=_make_quorum_result(receipt_id="rcpt_batch_1"),
            ),
            CABRConsensusInput(
                score_result=_make_score_result(
                    receipt_id="rcpt_batch_2",
                    decision="rejected_insufficient_evidence",
                ),
                quorum_result=_make_quorum_result(receipt_id="rcpt_batch_2"),
            ),
            CABRConsensusInput(
                quorum_result=_make_quorum_result(receipt_id="rcpt_batch_3"),
            ),
        ]

        records = finalize_cabr_consensus_batch(inputs)

        self.assertEqual(len(records), 3)
        self.assertEqual(records[0].receipt_id, "rcpt_batch_1")
        self.assertEqual(records[0].decision, CABRConsensusDecision.ACCEPTED_FOR_REVIEW)
        self.assertEqual(records[1].receipt_id, "rcpt_batch_2")
        self.assertEqual(records[1].decision, CABRConsensusDecision.REJECTED)
        self.assertEqual(records[2].receipt_id, "rcpt_batch_3")
        self.assertEqual(records[2].decision, CABRConsensusDecision.NOT_FINALIZED)

    def test_batch_empty_input(self):
        """Empty batch returns empty results."""
        records = finalize_cabr_consensus_batch([])
        self.assertEqual(len(records), 0)


# ---------------------------------------------------------------------------
# Test: No Payout Status Changes
# ---------------------------------------------------------------------------


class TestNoPayoutStatusChanges(unittest.TestCase):
    """Finalization does not change payout status."""

    def test_payout_ready_always_false(self):
        """payout_ready is always False in output."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(),
            quorum_result=_make_quorum_result(),
        )

        record = finalize_cabr_consensus(consensus_input)

        self.assertFalse(record.payout_ready)

    def test_no_payout_fields_in_result(self):
        """Result does not contain payout amounts."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(),
            quorum_result=_make_quorum_result(),
        )

        record = finalize_cabr_consensus(consensus_input)
        record_dict = record.to_dict()

        self.assertNotIn("payout_amount", record_dict)
        self.assertNotIn("tokens_issued", record_dict)
        self.assertNotIn("ups_allocated", record_dict)
        self.assertNotIn("reward_amount", record_dict)


# ---------------------------------------------------------------------------
# Test: No DAO Activation
# ---------------------------------------------------------------------------


class TestNoDAOActivation(unittest.TestCase):
    """Finalization does not activate DAO."""

    def test_cabr_ready_always_false(self):
        """cabr_ready is always False in output (no DAO transition)."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(),
            quorum_result=_make_quorum_result(),
        )

        record = finalize_cabr_consensus(consensus_input)

        self.assertFalse(record.cabr_ready)

    def test_accepted_with_quorum_still_cabr_not_ready(self):
        """Even ACCEPTED_FOR_REVIEW has cabr_ready=False."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(quorum_met=True),
            quorum_result=_make_quorum_result(
                quorum_met=True,
                threshold_met=True,
                unique_verifiers=10,
            ),
        )

        record = finalize_cabr_consensus(consensus_input)

        self.assertEqual(record.decision, CABRConsensusDecision.ACCEPTED_FOR_REVIEW)
        self.assertTrue(record.quorum_met)
        self.assertFalse(record.cabr_ready)


# ---------------------------------------------------------------------------
# Test: No External Dependency
# ---------------------------------------------------------------------------


class TestNoExternalDependency(unittest.TestCase):
    """Finalization requires no external systems."""

    def test_finalization_is_purely_local(self):
        """Finalization is a pure local computation."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(),
            quorum_result=_make_quorum_result(),
        )

        # If this tried network calls, it would fail
        record = finalize_cabr_consensus(consensus_input)

        self.assertIsNotNone(record)
        self.assertIsNotNone(record.record_id)
        self.assertIsNotNone(record.record_hash)


# ---------------------------------------------------------------------------
# Test: WSP 97 Truth Fields Always False
# ---------------------------------------------------------------------------


class TestWSP97TruthFieldsAlwaysFalse(unittest.TestCase):
    """All WSP 97 truth fields remain False in Phase 1 output."""

    def test_verification_complete_always_false(self):
        """verification_complete is always False."""
        test_cases = [
            CABRConsensusInput(
                score_result=_make_score_result(),
                quorum_result=_make_quorum_result(),
            ),
            CABRConsensusInput(
                score_result=_make_score_result(is_dry_run=True),
                quorum_result=_make_quorum_result(is_dry_run=True),
            ),
            CABRConsensusInput(
                quorum_result=_make_quorum_result(),
            ),
            CABRConsensusInput(
                score_result=_make_score_result(decision="rejected_insufficient_evidence"),
                quorum_result=_make_quorum_result(),
            ),
        ]

        for consensus_input in test_cases:
            record = finalize_cabr_consensus(consensus_input)
            self.assertFalse(
                record.verification_complete,
                f"verification_complete should be False for {record.decision}",
            )

    def test_cabr_ready_always_false(self):
        """cabr_ready is always False."""
        test_cases = [
            CABRConsensusInput(
                score_result=_make_score_result(),
                quorum_result=_make_quorum_result(),
            ),
            CABRConsensusInput(
                score_result=_make_score_result(),
                quorum_result=_make_quorum_result(decision="quorum_not_met"),
            ),
        ]

        for consensus_input in test_cases:
            record = finalize_cabr_consensus(consensus_input)
            self.assertFalse(
                record.cabr_ready,
                f"cabr_ready should be False for {record.decision}",
            )

    def test_payout_ready_always_false(self):
        """payout_ready is always False."""
        test_cases = [
            CABRConsensusInput(
                score_result=_make_score_result(),
                quorum_result=_make_quorum_result(),
            ),
            CABRConsensusInput(
                score_result=_make_score_result(),
            ),
        ]

        for consensus_input in test_cases:
            record = finalize_cabr_consensus(consensus_input)
            self.assertFalse(
                record.payout_ready,
                f"payout_ready should be False for {record.decision}",
            )


# ---------------------------------------------------------------------------
# Test: Quorum Rejection
# ---------------------------------------------------------------------------


class TestQuorumRejection(unittest.TestCase):
    """Quorum rejection results in REJECTED."""

    def test_quorum_rejected_duplicate_verifiers(self):
        """Quorum rejected (duplicate verifiers) -> REJECTED."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(),
            quorum_result=_make_quorum_result(
                decision="consensus_rejected",
                reason_code="rejected_duplicate_verifier_ids",
            ),
        )

        record = finalize_cabr_consensus(consensus_input)

        self.assertEqual(record.decision, CABRConsensusDecision.REJECTED)
        self.assertEqual(
            record.reason_code,
            CABRConsensusReasonCode.QUORUM_REJECTED_DUPLICATE_VERIFIERS,
        )

    def test_quorum_rejected_missing_verifier_id(self):
        """Quorum rejected (missing verifier ID) -> REJECTED."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(),
            quorum_result=_make_quorum_result(
                decision="consensus_rejected",
                reason_code="rejected_missing_verifier_id",
            ),
        )

        record = finalize_cabr_consensus(consensus_input)

        self.assertEqual(record.decision, CABRConsensusDecision.REJECTED)
        self.assertEqual(
            record.reason_code,
            CABRConsensusReasonCode.QUORUM_REJECTED_MISSING_VERIFIER_ID,
        )


# ---------------------------------------------------------------------------
# Test: Record ID Generation
# ---------------------------------------------------------------------------


class TestRecordIdGeneration(unittest.TestCase):
    """Record ID generation."""

    def test_record_id_format(self):
        """Record ID follows ccr_{suffix}_{timestamp}_{random} format."""
        record_id = generate_record_id("rcpt_test_abc123_def456")

        self.assertTrue(record_id.startswith("ccr_"))
        parts = record_id.split("_")
        self.assertGreaterEqual(len(parts), 4)

    def test_record_ids_unique(self):
        """Consecutive records have unique IDs."""
        ids = [generate_record_id("rcpt_test_123") for _ in range(10)]
        self.assertEqual(len(ids), len(set(ids)))


# ---------------------------------------------------------------------------
# Test: Result Serialization
# ---------------------------------------------------------------------------


class TestResultSerialization(unittest.TestCase):
    """CABRConsensusRecord serialization round-trips."""

    def test_to_dict_contains_required_fields(self):
        """to_dict includes all required fields."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(),
            quorum_result=_make_quorum_result(),
        )

        record = finalize_cabr_consensus(consensus_input)
        d = record.to_dict()

        self.assertIn("record_id", d)
        self.assertIn("record_hash", d)
        self.assertIn("receipt_id", d)
        self.assertIn("job_id", d)
        self.assertIn("tenant_id", d)
        self.assertIn("decision", d)
        self.assertIn("reason_code", d)
        self.assertIn("quorum_met", d)
        self.assertIn("threshold_met", d)
        self.assertIn("verification_complete", d)
        self.assertIn("cabr_ready", d)
        self.assertIn("payout_ready", d)

    def test_from_dict_roundtrip(self):
        """from_dict restores record from to_dict."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(receipt_id="rcpt_round_001"),
            quorum_result=_make_quorum_result(receipt_id="rcpt_round_001"),
        )

        record = finalize_cabr_consensus(consensus_input)
        d = record.to_dict()
        restored = CABRConsensusRecord.from_dict(d)

        self.assertEqual(restored.record_id, record.record_id)
        self.assertEqual(restored.record_hash, record.record_hash)
        self.assertEqual(restored.receipt_id, record.receipt_id)
        self.assertEqual(restored.decision, CABRConsensusDecision.ACCEPTED_FOR_REVIEW)
        self.assertTrue(restored.quorum_met)
        self.assertFalse(restored.cabr_ready)
        self.assertFalse(restored.payout_ready)


# ---------------------------------------------------------------------------
# Test: Identity Extraction
# ---------------------------------------------------------------------------


class TestIdentityExtraction(unittest.TestCase):
    """Identity is extracted from input or nested results."""

    def test_identity_from_explicit_input(self):
        """Identity is taken from explicit input fields first."""
        consensus_input = CABRConsensusInput(
            receipt_id="rcpt_explicit_001",
            job_id="j_explicit_001",
            tenant_id="t_explicit",
            score_result=_make_score_result(
                receipt_id="rcpt_nested",
                job_id="j_nested",
                tenant_id="t_nested",
            ),
            quorum_result=_make_quorum_result(),
        )

        record = finalize_cabr_consensus(consensus_input)

        self.assertEqual(record.receipt_id, "rcpt_explicit_001")
        self.assertEqual(record.job_id, "j_explicit_001")
        self.assertEqual(record.tenant_id, "t_explicit")

    def test_identity_from_score_result(self):
        """Identity is extracted from score_result if not explicit."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(
                receipt_id="rcpt_from_score",
                job_id="j_from_score",
                tenant_id="t_from_score",
            ),
            quorum_result=_make_quorum_result(),
        )

        record = finalize_cabr_consensus(consensus_input)

        self.assertEqual(record.receipt_id, "rcpt_from_score")
        self.assertEqual(record.job_id, "j_from_score")
        self.assertEqual(record.tenant_id, "t_from_score")

    def test_identity_from_quorum_result(self):
        """Identity is extracted from quorum_result as fallback."""
        consensus_input = CABRConsensusInput(
            quorum_result=_make_quorum_result(
                receipt_id="rcpt_from_quorum",
                job_id="j_from_quorum",
                tenant_id="t_from_quorum",
            ),
        )

        record = finalize_cabr_consensus(consensus_input)

        self.assertEqual(record.receipt_id, "rcpt_from_quorum")
        self.assertEqual(record.job_id, "j_from_quorum")
        self.assertEqual(record.tenant_id, "t_from_quorum")


# ---------------------------------------------------------------------------
# Test: Input Snapshot
# ---------------------------------------------------------------------------


class TestInputSnapshot(unittest.TestCase):
    """Input snapshot is optionally included."""

    def test_snapshot_not_included_by_default(self):
        """Input snapshot is not included by default."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(),
            quorum_result=_make_quorum_result(),
        )

        record = finalize_cabr_consensus(consensus_input)

        self.assertIsNone(record.input_snapshot)

    def test_snapshot_included_when_requested(self):
        """Input snapshot is included when requested."""
        consensus_input = CABRConsensusInput(
            score_result=_make_score_result(),
            quorum_result=_make_quorum_result(),
        )

        record = finalize_cabr_consensus(consensus_input, include_input_snapshot=True)

        self.assertIsNotNone(record.input_snapshot)
        self.assertIn("score_result", record.input_snapshot)
        self.assertIn("quorum_result", record.input_snapshot)


if __name__ == "__main__":
    unittest.main(verbosity=2)
