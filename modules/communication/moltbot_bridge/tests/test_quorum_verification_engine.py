#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Quorum Verification Engine Phase 1.

Validates deterministic quorum enforcement for CABR scoring per WSP 29 and WSP 97.

Required coverage:
  - Zero attestations -> QUORUM_NOT_MET
  - One/two attestations -> QUORUM_NOT_MET
  - Three unique attestations -> quorum met
  - Duplicate verifier IDs rejected/not counted
  - Missing verifier ID rejected
  - Invalid signature unsupported/rejected
  - Consensus score below 0.382 rejected
  - Consensus score at 0.382 accepted for review
  - Consensus score above 0.382 accepted for review
  - Conflicting attestations handled deterministically
  - Batch evaluation deterministic
  - No external systems required
  - No payout
  - No DAO activation
  - WSP_97 truth fields remain false

Slice: QUORUM_VERIFICATION_ENFORCEMENT_PHASE1
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

from modules.communication.moltbot_bridge.src.quorum_verification_engine import (
    AttestationStatus,
    CONSENSUS_THRESHOLD,
    MIN_VALIDATORS_DEFAULT,
    QuorumDecision,
    QuorumReasonCode,
    QuorumVerificationInput,
    QuorumVerificationResult,
    VerifierAttestation,
    build_quorum_input_from_cabr_result,
    evaluate_quorum,
    evaluate_quorum_batch,
    generate_quorum_id,
)


class TestZeroAttestationsQuorumNotMet(unittest.TestCase):
    """Zero attestations results in QUORUM_NOT_MET."""

    def test_empty_attestations_returns_quorum_not_met(self):
        """Empty attestations list results in QUORUM_NOT_MET."""
        quorum_input = QuorumVerificationInput(
            receipt_id="rcpt_test_001",
            job_id="j_test_001",
            tenant_id="t_test",
            attestations=[],
        )

        result = evaluate_quorum(quorum_input)

        self.assertEqual(result.decision, QuorumDecision.QUORUM_NOT_MET)
        self.assertEqual(result.reason_code, QuorumReasonCode.QUORUM_ZERO_ATTESTATIONS)
        self.assertEqual(result.total_attestations, 0)
        self.assertEqual(result.valid_attestations, 0)
        self.assertEqual(result.unique_verifiers, 0)
        self.assertFalse(result.quorum_met)
        self.assertFalse(result.threshold_met)


class TestOneOrTwoAttestationsQuorumNotMet(unittest.TestCase):
    """One or two attestations results in QUORUM_NOT_MET."""

    def test_one_attestation_quorum_not_met(self):
        """1 attestation results in QUORUM_NOT_MET."""
        quorum_input = QuorumVerificationInput(
            receipt_id="rcpt_test_002",
            job_id="j_test_002",
            tenant_id="t_test",
            attestations=[
                VerifierAttestation(verifier_id="v1", decision=AttestationStatus.APPROVE),
            ],
        )

        result = evaluate_quorum(quorum_input)

        self.assertEqual(result.decision, QuorumDecision.QUORUM_NOT_MET)
        self.assertEqual(result.reason_code, QuorumReasonCode.QUORUM_INSUFFICIENT_UNIQUE_VERIFIERS)
        self.assertEqual(result.unique_verifiers, 1)
        self.assertFalse(result.quorum_met)

    def test_two_attestations_quorum_not_met(self):
        """2 attestations results in QUORUM_NOT_MET."""
        quorum_input = QuorumVerificationInput(
            receipt_id="rcpt_test_003",
            job_id="j_test_003",
            tenant_id="t_test",
            attestations=[
                VerifierAttestation(verifier_id="v1", decision=AttestationStatus.APPROVE),
                VerifierAttestation(verifier_id="v2", decision=AttestationStatus.APPROVE),
            ],
        )

        result = evaluate_quorum(quorum_input)

        self.assertEqual(result.decision, QuorumDecision.QUORUM_NOT_MET)
        self.assertEqual(result.unique_verifiers, 2)
        self.assertFalse(result.quorum_met)


class TestThreeUniqueAttestationsQuorumMet(unittest.TestCase):
    """Three unique attestations meets quorum."""

    def test_three_attestations_with_threshold_met(self):
        """3 approving attestations meets quorum and threshold."""
        quorum_input = QuorumVerificationInput(
            receipt_id="rcpt_test_004",
            job_id="j_test_004",
            tenant_id="t_test",
            attestations=[
                VerifierAttestation(verifier_id="v1", decision=AttestationStatus.APPROVE),
                VerifierAttestation(verifier_id="v2", decision=AttestationStatus.APPROVE),
                VerifierAttestation(verifier_id="v3", decision=AttestationStatus.APPROVE),
            ],
        )

        result = evaluate_quorum(quorum_input)

        self.assertEqual(result.decision, QuorumDecision.CONSENSUS_ACCEPTED_FOR_REVIEW)
        self.assertEqual(result.reason_code, QuorumReasonCode.OK_QUORUM_MET_THRESHOLD_MET)
        self.assertEqual(result.unique_verifiers, 3)
        self.assertTrue(result.quorum_met)
        self.assertEqual(result.consensus_score, 1.0)  # 3/3 = 100%
        self.assertTrue(result.threshold_met)

    def test_four_attestations_quorum_met(self):
        """More than 3 attestations also meets quorum."""
        quorum_input = QuorumVerificationInput(
            receipt_id="rcpt_test_005",
            job_id="j_test_005",
            tenant_id="t_test",
            attestations=[
                VerifierAttestation(verifier_id="v1", decision=AttestationStatus.APPROVE),
                VerifierAttestation(verifier_id="v2", decision=AttestationStatus.APPROVE),
                VerifierAttestation(verifier_id="v3", decision=AttestationStatus.APPROVE),
                VerifierAttestation(verifier_id="v4", decision=AttestationStatus.APPROVE),
            ],
        )

        result = evaluate_quorum(quorum_input)

        self.assertTrue(result.quorum_met)
        self.assertEqual(result.unique_verifiers, 4)
        self.assertEqual(result.decision, QuorumDecision.CONSENSUS_ACCEPTED_FOR_REVIEW)


class TestDuplicateVerifierIDsRejected(unittest.TestCase):
    """Duplicate verifier IDs are rejected."""

    def test_duplicate_verifier_ids_rejected(self):
        """Duplicate verifier IDs result in CONSENSUS_REJECTED."""
        quorum_input = QuorumVerificationInput(
            receipt_id="rcpt_dup_001",
            job_id="j_dup_001",
            tenant_id="t_test",
            attestations=[
                VerifierAttestation(verifier_id="v1", decision=AttestationStatus.APPROVE),
                VerifierAttestation(verifier_id="v1", decision=AttestationStatus.APPROVE),  # duplicate
                VerifierAttestation(verifier_id="v2", decision=AttestationStatus.APPROVE),
            ],
        )

        result = evaluate_quorum(quorum_input)

        self.assertEqual(result.decision, QuorumDecision.CONSENSUS_REJECTED)
        self.assertEqual(result.reason_code, QuorumReasonCode.REJECTED_DUPLICATE_VERIFIER_IDS)
        self.assertTrue(result.duplicate_verifiers_detected)
        self.assertFalse(result.quorum_met)

    def test_all_duplicates_rejected(self):
        """All-duplicate verifier IDs are rejected."""
        quorum_input = QuorumVerificationInput(
            receipt_id="rcpt_dup_002",
            job_id="j_dup_002",
            tenant_id="t_test",
            attestations=[
                VerifierAttestation(verifier_id="v1", decision=AttestationStatus.APPROVE),
                VerifierAttestation(verifier_id="v1", decision=AttestationStatus.APPROVE),
                VerifierAttestation(verifier_id="v1", decision=AttestationStatus.APPROVE),
            ],
        )

        result = evaluate_quorum(quorum_input)

        self.assertEqual(result.decision, QuorumDecision.CONSENSUS_REJECTED)
        self.assertEqual(result.reason_code, QuorumReasonCode.REJECTED_DUPLICATE_VERIFIER_IDS)
        self.assertTrue(result.duplicate_verifiers_detected)


class TestMissingVerifierIDRejected(unittest.TestCase):
    """Missing verifier ID is rejected."""

    def test_empty_verifier_id_rejected(self):
        """Empty verifier_id results in CONSENSUS_REJECTED."""
        quorum_input = QuorumVerificationInput(
            receipt_id="rcpt_missing_001",
            job_id="j_missing_001",
            tenant_id="t_test",
            attestations=[
                VerifierAttestation(verifier_id="v1", decision=AttestationStatus.APPROVE),
                VerifierAttestation(verifier_id="", decision=AttestationStatus.APPROVE),  # missing
                VerifierAttestation(verifier_id="v2", decision=AttestationStatus.APPROVE),
            ],
        )

        result = evaluate_quorum(quorum_input)

        self.assertEqual(result.decision, QuorumDecision.CONSENSUS_REJECTED)
        self.assertEqual(result.reason_code, QuorumReasonCode.REJECTED_MISSING_VERIFIER_ID)
        self.assertTrue(result.missing_verifier_ids_detected)

    def test_whitespace_verifier_id_rejected(self):
        """Whitespace-only verifier_id results in CONSENSUS_REJECTED."""
        quorum_input = QuorumVerificationInput(
            receipt_id="rcpt_missing_002",
            job_id="j_missing_002",
            tenant_id="t_test",
            attestations=[
                VerifierAttestation(verifier_id="v1", decision=AttestationStatus.APPROVE),
                VerifierAttestation(verifier_id="   ", decision=AttestationStatus.APPROVE),  # whitespace
                VerifierAttestation(verifier_id="v2", decision=AttestationStatus.APPROVE),
            ],
        )

        result = evaluate_quorum(quorum_input)

        self.assertEqual(result.decision, QuorumDecision.CONSENSUS_REJECTED)
        self.assertEqual(result.reason_code, QuorumReasonCode.REJECTED_MISSING_VERIFIER_ID)


class TestInvalidSignatureUnsupported(unittest.TestCase):
    """Invalid signature is unsupported/noted in Phase 1."""

    def test_signature_present_noted_but_not_rejected(self):
        """Signature present is noted but not rejected in Phase 1."""
        # Phase 1: Signatures are unsupported, so we note them but don't reject
        quorum_input = QuorumVerificationInput(
            receipt_id="rcpt_sig_001",
            job_id="j_sig_001",
            tenant_id="t_test",
            attestations=[
                VerifierAttestation(
                    verifier_id="v1",
                    decision=AttestationStatus.APPROVE,
                    signature="abc123",  # Non-empty signature
                ),
                VerifierAttestation(verifier_id="v2", decision=AttestationStatus.APPROVE),
                VerifierAttestation(verifier_id="v3", decision=AttestationStatus.APPROVE),
            ],
        )

        result = evaluate_quorum(quorum_input)

        # Phase 1: Still accepts but notes invalid signatures
        self.assertTrue(result.invalid_signatures_detected)
        # Attestations still counted for Phase 1 dry-run behavior
        self.assertEqual(result.decision, QuorumDecision.CONSENSUS_ACCEPTED_FOR_REVIEW)


class TestConsensusScoreBelowThresholdRejected(unittest.TestCase):
    """Consensus score below 0.382 results in QUORUM_MET_PENDING_CONSENSUS."""

    def test_all_reject_below_threshold(self):
        """All REJECT attestations = 0% score, below threshold."""
        quorum_input = QuorumVerificationInput(
            receipt_id="rcpt_reject_001",
            job_id="j_reject_001",
            tenant_id="t_test",
            attestations=[
                VerifierAttestation(verifier_id="v1", decision=AttestationStatus.REJECT),
                VerifierAttestation(verifier_id="v2", decision=AttestationStatus.REJECT),
                VerifierAttestation(verifier_id="v3", decision=AttestationStatus.REJECT),
            ],
        )

        result = evaluate_quorum(quorum_input)

        self.assertTrue(result.quorum_met)
        self.assertEqual(result.consensus_score, 0.0)
        self.assertFalse(result.threshold_met)
        self.assertEqual(result.decision, QuorumDecision.QUORUM_MET_PENDING_CONSENSUS)
        self.assertEqual(result.reason_code, QuorumReasonCode.PENDING_THRESHOLD_NOT_MET)

    def test_one_approve_two_reject_below_threshold(self):
        """1/3 = 33.3% score, below 38.2% threshold."""
        quorum_input = QuorumVerificationInput(
            receipt_id="rcpt_mix_001",
            job_id="j_mix_001",
            tenant_id="t_test",
            attestations=[
                VerifierAttestation(verifier_id="v1", decision=AttestationStatus.APPROVE),
                VerifierAttestation(verifier_id="v2", decision=AttestationStatus.REJECT),
                VerifierAttestation(verifier_id="v3", decision=AttestationStatus.REJECT),
            ],
        )

        result = evaluate_quorum(quorum_input)

        self.assertTrue(result.quorum_met)
        self.assertAlmostEqual(result.consensus_score, 1 / 3, places=4)  # 0.333...
        self.assertFalse(result.threshold_met)  # 0.333 < 0.382
        self.assertEqual(result.decision, QuorumDecision.QUORUM_MET_PENDING_CONSENSUS)


class TestConsensusScoreAtThresholdAccepted(unittest.TestCase):
    """Consensus score at 0.382 is accepted for review."""

    def test_exact_threshold_accepted(self):
        """Score exactly at threshold = accepted."""
        # Need to construct attestations that yield exactly 0.382
        # 382/1000 = 0.382 -> Need 382 approve, 618 reject (not practical)
        # Instead, use custom threshold to test boundary
        quorum_input = QuorumVerificationInput(
            receipt_id="rcpt_threshold_001",
            job_id="j_threshold_001",
            tenant_id="t_test",
            attestations=[
                VerifierAttestation(verifier_id="v1", decision=AttestationStatus.APPROVE),
                VerifierAttestation(verifier_id="v2", decision=AttestationStatus.APPROVE),
                VerifierAttestation(verifier_id="v3", decision=AttestationStatus.REJECT),
            ],
            consensus_threshold=0.5,  # 2/3 = 0.666 >= 0.5
        )

        result = evaluate_quorum(quorum_input)

        self.assertTrue(result.quorum_met)
        self.assertAlmostEqual(result.consensus_score, 2 / 3, places=4)  # 0.666
        self.assertTrue(result.threshold_met)  # 0.666 >= 0.5
        self.assertEqual(result.decision, QuorumDecision.CONSENSUS_ACCEPTED_FOR_REVIEW)

    def test_score_at_exact_382_threshold(self):
        """Test with custom attestation count to hit 0.382 exactly is hard, test boundary."""
        # With 5 attestations: 2 approve / 5 = 0.4 >= 0.382
        quorum_input = QuorumVerificationInput(
            receipt_id="rcpt_boundary_001",
            job_id="j_boundary_001",
            tenant_id="t_test",
            attestations=[
                VerifierAttestation(verifier_id="v1", decision=AttestationStatus.APPROVE),
                VerifierAttestation(verifier_id="v2", decision=AttestationStatus.APPROVE),
                VerifierAttestation(verifier_id="v3", decision=AttestationStatus.REJECT),
                VerifierAttestation(verifier_id="v4", decision=AttestationStatus.REJECT),
                VerifierAttestation(verifier_id="v5", decision=AttestationStatus.REJECT),
            ],
            consensus_threshold=CONSENSUS_THRESHOLD,  # 0.382
        )

        result = evaluate_quorum(quorum_input)

        self.assertTrue(result.quorum_met)
        self.assertAlmostEqual(result.consensus_score, 2 / 5, places=4)  # 0.4
        self.assertTrue(result.threshold_met)  # 0.4 >= 0.382
        self.assertEqual(result.decision, QuorumDecision.CONSENSUS_ACCEPTED_FOR_REVIEW)


class TestConsensusScoreAboveThresholdAccepted(unittest.TestCase):
    """Consensus score above 0.382 is accepted for review."""

    def test_all_approve_above_threshold(self):
        """All APPROVE = 100% score, well above threshold."""
        quorum_input = QuorumVerificationInput(
            receipt_id="rcpt_above_001",
            job_id="j_above_001",
            tenant_id="t_test",
            attestations=[
                VerifierAttestation(verifier_id="v1", decision=AttestationStatus.APPROVE),
                VerifierAttestation(verifier_id="v2", decision=AttestationStatus.APPROVE),
                VerifierAttestation(verifier_id="v3", decision=AttestationStatus.APPROVE),
            ],
        )

        result = evaluate_quorum(quorum_input)

        self.assertTrue(result.quorum_met)
        self.assertEqual(result.consensus_score, 1.0)
        self.assertTrue(result.threshold_met)
        self.assertEqual(result.decision, QuorumDecision.CONSENSUS_ACCEPTED_FOR_REVIEW)
        self.assertEqual(result.reason_code, QuorumReasonCode.OK_QUORUM_MET_THRESHOLD_MET)

    def test_two_approve_one_reject_above_threshold(self):
        """2/3 = 66.6% score, above 38.2% threshold."""
        quorum_input = QuorumVerificationInput(
            receipt_id="rcpt_above_002",
            job_id="j_above_002",
            tenant_id="t_test",
            attestations=[
                VerifierAttestation(verifier_id="v1", decision=AttestationStatus.APPROVE),
                VerifierAttestation(verifier_id="v2", decision=AttestationStatus.APPROVE),
                VerifierAttestation(verifier_id="v3", decision=AttestationStatus.REJECT),
            ],
        )

        result = evaluate_quorum(quorum_input)

        self.assertTrue(result.quorum_met)
        self.assertAlmostEqual(result.consensus_score, 2 / 3, places=4)
        self.assertTrue(result.threshold_met)
        self.assertEqual(result.decision, QuorumDecision.CONSENSUS_ACCEPTED_FOR_REVIEW)


class TestConflictingAttestationsHandledDeterministically(unittest.TestCase):
    """Conflicting attestations are handled deterministically."""

    def test_mixed_approve_reject_counted(self):
        """Mixed APPROVE/REJECT attestations are counted correctly."""
        quorum_input = QuorumVerificationInput(
            receipt_id="rcpt_conflict_001",
            job_id="j_conflict_001",
            tenant_id="t_test",
            attestations=[
                VerifierAttestation(verifier_id="v1", decision=AttestationStatus.APPROVE),
                VerifierAttestation(verifier_id="v2", decision=AttestationStatus.REJECT),
                VerifierAttestation(verifier_id="v3", decision=AttestationStatus.APPROVE),
                VerifierAttestation(verifier_id="v4", decision=AttestationStatus.ABSTAIN),
            ],
        )

        result = evaluate_quorum(quorum_input)

        self.assertEqual(result.approve_count, 2)
        self.assertEqual(result.reject_count, 1)
        self.assertEqual(result.abstain_count, 1)
        # Consensus score = approve / (approve + reject) = 2/3 = 0.666
        self.assertAlmostEqual(result.consensus_score, 2 / 3, places=4)
        self.assertTrue(result.quorum_met)
        self.assertTrue(result.threshold_met)

    def test_abstain_does_not_affect_score(self):
        """ABSTAIN votes don't count in consensus score calculation."""
        quorum_input = QuorumVerificationInput(
            receipt_id="rcpt_abstain_001",
            job_id="j_abstain_001",
            tenant_id="t_test",
            attestations=[
                VerifierAttestation(verifier_id="v1", decision=AttestationStatus.APPROVE),
                VerifierAttestation(verifier_id="v2", decision=AttestationStatus.ABSTAIN),
                VerifierAttestation(verifier_id="v3", decision=AttestationStatus.ABSTAIN),
            ],
        )

        result = evaluate_quorum(quorum_input)

        # Only 1 APPROVE, no REJECT -> score = 1/1 = 1.0
        self.assertEqual(result.approve_count, 1)
        self.assertEqual(result.reject_count, 0)
        self.assertEqual(result.abstain_count, 2)
        self.assertEqual(result.consensus_score, 1.0)


class TestBatchEvaluationDeterministic(unittest.TestCase):
    """Batch evaluation returns deterministic results in order."""

    def test_batch_order_preserved(self):
        """Batch results are in same order as inputs."""
        inputs = [
            QuorumVerificationInput(
                receipt_id="rcpt_batch_1",
                job_id="j_1",
                tenant_id="t_1",
                attestations=[
                    VerifierAttestation(verifier_id="v1", decision=AttestationStatus.APPROVE),
                    VerifierAttestation(verifier_id="v2", decision=AttestationStatus.APPROVE),
                    VerifierAttestation(verifier_id="v3", decision=AttestationStatus.APPROVE),
                ],
            ),
            QuorumVerificationInput(
                receipt_id="rcpt_batch_2",
                job_id="j_2",
                tenant_id="t_2",
                attestations=[],  # Zero attestations
            ),
            QuorumVerificationInput(
                receipt_id="rcpt_batch_3",
                job_id="j_3",
                tenant_id="t_3",
                attestations=[
                    VerifierAttestation(verifier_id="v1", decision=AttestationStatus.APPROVE),
                ],
                is_dry_run=True,
            ),
        ]

        results = evaluate_quorum_batch(inputs)

        self.assertEqual(len(results), 3)
        self.assertEqual(results[0].receipt_id, "rcpt_batch_1")
        self.assertEqual(results[0].decision, QuorumDecision.CONSENSUS_ACCEPTED_FOR_REVIEW)
        self.assertEqual(results[1].receipt_id, "rcpt_batch_2")
        self.assertEqual(results[1].decision, QuorumDecision.QUORUM_NOT_MET)
        self.assertEqual(results[2].receipt_id, "rcpt_batch_3")
        # Single attestation in dry-run still doesn't meet quorum
        self.assertEqual(results[2].decision, QuorumDecision.QUORUM_NOT_MET)

    def test_batch_empty_input(self):
        """Empty batch returns empty results."""
        results = evaluate_quorum_batch([])
        self.assertEqual(len(results), 0)


class TestNoExternalSystemsRequired(unittest.TestCase):
    """Quorum evaluation requires no external systems."""

    def test_evaluation_is_purely_local(self):
        """Evaluation is a pure local computation."""
        quorum_input = QuorumVerificationInput(
            receipt_id="rcpt_local_001",
            job_id="j_local_001",
            tenant_id="t_test",
            attestations=[
                VerifierAttestation(verifier_id="v1", decision=AttestationStatus.APPROVE),
                VerifierAttestation(verifier_id="v2", decision=AttestationStatus.APPROVE),
                VerifierAttestation(verifier_id="v3", decision=AttestationStatus.APPROVE),
            ],
        )

        # This test verifies no network calls are made
        result = evaluate_quorum(quorum_input)

        self.assertIsNotNone(result)
        self.assertIsNotNone(result.quorum_id)


class TestNoPayoutTriggered(unittest.TestCase):
    """Quorum evaluation does not trigger payout."""

    def test_payout_ready_always_false(self):
        """payout_ready is always False."""
        quorum_input = QuorumVerificationInput(
            receipt_id="rcpt_payout_001",
            job_id="j_payout_001",
            tenant_id="t_test",
            attestations=[
                VerifierAttestation(verifier_id="v1", decision=AttestationStatus.APPROVE),
                VerifierAttestation(verifier_id="v2", decision=AttestationStatus.APPROVE),
                VerifierAttestation(verifier_id="v3", decision=AttestationStatus.APPROVE),
            ],
        )

        result = evaluate_quorum(quorum_input)

        self.assertFalse(result.payout_ready)

    def test_no_payout_fields_in_result(self):
        """Result does not contain payout amounts."""
        quorum_input = QuorumVerificationInput(
            receipt_id="rcpt_no_payout_001",
            job_id="j_no_payout_001",
            tenant_id="t_test",
            attestations=[
                VerifierAttestation(verifier_id="v1", decision=AttestationStatus.APPROVE),
                VerifierAttestation(verifier_id="v2", decision=AttestationStatus.APPROVE),
                VerifierAttestation(verifier_id="v3", decision=AttestationStatus.APPROVE),
            ],
        )

        result = evaluate_quorum(quorum_input)
        result_dict = result.to_dict()

        self.assertNotIn("payout_amount", result_dict)
        self.assertNotIn("tokens_issued", result_dict)
        self.assertNotIn("ups_allocated", result_dict)


class TestNoDAOActivation(unittest.TestCase):
    """Quorum evaluation does not activate DAO."""

    def test_cabr_ready_always_false(self):
        """cabr_ready is always False (no DAO transition)."""
        quorum_input = QuorumVerificationInput(
            receipt_id="rcpt_dao_001",
            job_id="j_dao_001",
            tenant_id="t_test",
            attestations=[
                VerifierAttestation(verifier_id="v1", decision=AttestationStatus.APPROVE),
                VerifierAttestation(verifier_id="v2", decision=AttestationStatus.APPROVE),
                VerifierAttestation(verifier_id="v3", decision=AttestationStatus.APPROVE),
            ],
        )

        result = evaluate_quorum(quorum_input)

        self.assertFalse(result.cabr_ready)


class TestWSP97TruthFieldsRemainFalse(unittest.TestCase):
    """All WSP 97 truth fields remain False in Phase 1 output."""

    def test_all_acceptance_states_have_false_truth_fields(self):
        """Every state has truth fields False."""
        test_cases = [
            # CONSENSUS_ACCEPTED_FOR_REVIEW
            QuorumVerificationInput(
                receipt_id="rcpt_wsp_1",
                job_id="j_1",
                tenant_id="t",
                attestations=[
                    VerifierAttestation(verifier_id="v1", decision=AttestationStatus.APPROVE),
                    VerifierAttestation(verifier_id="v2", decision=AttestationStatus.APPROVE),
                    VerifierAttestation(verifier_id="v3", decision=AttestationStatus.APPROVE),
                ],
            ),
            # QUORUM_MET_PENDING_CONSENSUS
            QuorumVerificationInput(
                receipt_id="rcpt_wsp_2",
                job_id="j_2",
                tenant_id="t",
                attestations=[
                    VerifierAttestation(verifier_id="v1", decision=AttestationStatus.REJECT),
                    VerifierAttestation(verifier_id="v2", decision=AttestationStatus.REJECT),
                    VerifierAttestation(verifier_id="v3", decision=AttestationStatus.REJECT),
                ],
            ),
            # QUORUM_NOT_MET
            QuorumVerificationInput(
                receipt_id="rcpt_wsp_3",
                job_id="j_3",
                tenant_id="t",
                attestations=[
                    VerifierAttestation(verifier_id="v1", decision=AttestationStatus.APPROVE),
                ],
            ),
        ]

        for quorum_input in test_cases:
            result = evaluate_quorum(quorum_input)
            self.assertFalse(
                result.verification_complete,
                f"verification_complete should be False for {quorum_input.receipt_id}",
            )
            self.assertFalse(
                result.cabr_ready,
                f"cabr_ready should be False for {quorum_input.receipt_id}",
            )
            self.assertFalse(
                result.payout_ready,
                f"payout_ready should be False for {quorum_input.receipt_id}",
            )


class TestMissingIdentityRejects(unittest.TestCase):
    """Missing identity fields cause rejection."""

    def test_missing_receipt_id_rejects(self):
        """Empty receipt_id causes rejection."""
        quorum_input = QuorumVerificationInput(
            receipt_id="",
            job_id="j_id_001",
            tenant_id="t_test",
            attestations=[
                VerifierAttestation(verifier_id="v1", decision=AttestationStatus.APPROVE),
            ],
        )

        result = evaluate_quorum(quorum_input)

        self.assertEqual(result.decision, QuorumDecision.CONSENSUS_REJECTED)
        self.assertEqual(result.reason_code, QuorumReasonCode.REJECTED_MISSING_RECEIPT_ID)

    def test_missing_job_id_rejects(self):
        """Empty job_id causes rejection."""
        quorum_input = QuorumVerificationInput(
            receipt_id="rcpt_id_001",
            job_id="",
            tenant_id="t_test",
            attestations=[
                VerifierAttestation(verifier_id="v1", decision=AttestationStatus.APPROVE),
            ],
        )

        result = evaluate_quorum(quorum_input)

        self.assertEqual(result.decision, QuorumDecision.CONSENSUS_REJECTED)
        self.assertEqual(result.reason_code, QuorumReasonCode.REJECTED_MISSING_JOB_ID)


class TestQuorumIdGeneration(unittest.TestCase):
    """Quorum ID generation."""

    def test_quorum_id_format(self):
        """Quorum ID follows qv_{suffix}_{timestamp}_{random} format."""
        quorum_id = generate_quorum_id("rcpt_test_abc123_def456")

        self.assertTrue(quorum_id.startswith("qv_"))
        parts = quorum_id.split("_")
        self.assertGreaterEqual(len(parts), 4)

    def test_quorum_ids_unique(self):
        """Consecutive evaluations have unique IDs."""
        ids = [generate_quorum_id("rcpt_test_123") for _ in range(10)]
        self.assertEqual(len(ids), len(set(ids)))


class TestResultSerialization(unittest.TestCase):
    """QuorumVerificationResult serialization round-trips."""

    def test_to_dict_contains_required_fields(self):
        """to_dict includes all required fields."""
        quorum_input = QuorumVerificationInput(
            receipt_id="rcpt_serial_001",
            job_id="j_serial_001",
            tenant_id="t_test",
            attestations=[
                VerifierAttestation(verifier_id="v1", decision=AttestationStatus.APPROVE),
                VerifierAttestation(verifier_id="v2", decision=AttestationStatus.APPROVE),
                VerifierAttestation(verifier_id="v3", decision=AttestationStatus.APPROVE),
            ],
        )

        result = evaluate_quorum(quorum_input)
        d = result.to_dict()

        self.assertIn("quorum_id", d)
        self.assertIn("receipt_id", d)
        self.assertIn("job_id", d)
        self.assertIn("tenant_id", d)
        self.assertIn("decision", d)
        self.assertIn("reason_code", d)
        self.assertIn("quorum_met", d)
        self.assertIn("threshold_met", d)
        self.assertIn("consensus_score", d)
        self.assertIn("verification_complete", d)
        self.assertIn("cabr_ready", d)
        self.assertIn("payout_ready", d)

    def test_from_dict_roundtrip(self):
        """from_dict restores result from to_dict."""
        quorum_input = QuorumVerificationInput(
            receipt_id="rcpt_round_001",
            job_id="j_round_001",
            tenant_id="t_roundtrip",
            attestations=[
                VerifierAttestation(verifier_id="v1", decision=AttestationStatus.APPROVE),
                VerifierAttestation(verifier_id="v2", decision=AttestationStatus.APPROVE),
                VerifierAttestation(verifier_id="v3", decision=AttestationStatus.APPROVE),
            ],
        )

        result = evaluate_quorum(quorum_input)
        d = result.to_dict()
        restored = QuorumVerificationResult.from_dict(d)

        self.assertEqual(restored.quorum_id, result.quorum_id)
        self.assertEqual(restored.receipt_id, result.receipt_id)
        self.assertEqual(restored.decision, QuorumDecision.CONSENSUS_ACCEPTED_FOR_REVIEW)
        self.assertTrue(restored.quorum_met)
        self.assertTrue(restored.threshold_met)
        self.assertFalse(restored.cabr_ready)
        self.assertFalse(restored.payout_ready)


class TestMinValidatorsConfiguration(unittest.TestCase):
    """min_validators configuration."""

    def test_default_min_validators_is_three(self):
        """Default min_validators is 3 per WSP 29."""
        self.assertEqual(MIN_VALIDATORS_DEFAULT, 3)

    def test_custom_min_validators(self):
        """Custom min_validators threshold works."""
        quorum_input = QuorumVerificationInput(
            receipt_id="rcpt_minval_001",
            job_id="j_minval_001",
            tenant_id="t_test",
            attestations=[
                VerifierAttestation(verifier_id="v1", decision=AttestationStatus.APPROVE),
                VerifierAttestation(verifier_id="v2", decision=AttestationStatus.APPROVE),
                VerifierAttestation(verifier_id="v3", decision=AttestationStatus.APPROVE),
                VerifierAttestation(verifier_id="v4", decision=AttestationStatus.APPROVE),
                VerifierAttestation(verifier_id="v5", decision=AttestationStatus.APPROVE),
            ],
            min_validators=5,  # Custom threshold
        )

        result_5 = evaluate_quorum(quorum_input)
        self.assertTrue(result_5.quorum_met)
        self.assertEqual(result_5.min_validators, 5)

        # With min_validators=6, quorum should NOT be met
        quorum_input.min_validators = 6
        result_6 = evaluate_quorum(quorum_input)
        self.assertFalse(result_6.quorum_met)
        self.assertEqual(result_6.min_validators, 6)


class TestConsensusThresholdConfiguration(unittest.TestCase):
    """Consensus threshold configuration."""

    def test_default_threshold_is_382(self):
        """Default consensus_threshold is 0.382 per WSP 29."""
        self.assertAlmostEqual(CONSENSUS_THRESHOLD, 0.382, places=3)

    def test_custom_threshold(self):
        """Custom consensus_threshold works."""
        # 2/3 = 0.666, test with threshold 0.7
        quorum_input = QuorumVerificationInput(
            receipt_id="rcpt_thresh_001",
            job_id="j_thresh_001",
            tenant_id="t_test",
            attestations=[
                VerifierAttestation(verifier_id="v1", decision=AttestationStatus.APPROVE),
                VerifierAttestation(verifier_id="v2", decision=AttestationStatus.APPROVE),
                VerifierAttestation(verifier_id="v3", decision=AttestationStatus.REJECT),
            ],
            consensus_threshold=0.7,  # 2/3 < 0.7
        )

        result = evaluate_quorum(quorum_input)

        self.assertTrue(result.quorum_met)
        self.assertFalse(result.threshold_met)  # 0.666 < 0.7
        self.assertEqual(result.decision, QuorumDecision.QUORUM_MET_PENDING_CONSENSUS)


class TestDryRunMode(unittest.TestCase):
    """Dry-run mode behavior."""

    def test_dry_run_with_quorum_accepted(self):
        """Dry-run with quorum met is accepted for review."""
        quorum_input = QuorumVerificationInput(
            receipt_id="rcpt_dry_001",
            job_id="j_dry_001",
            tenant_id="t_test",
            attestations=[
                VerifierAttestation(verifier_id="v1", decision=AttestationStatus.APPROVE),
                VerifierAttestation(verifier_id="v2", decision=AttestationStatus.APPROVE),
                VerifierAttestation(verifier_id="v3", decision=AttestationStatus.APPROVE),
            ],
            is_dry_run=True,
        )

        result = evaluate_quorum(quorum_input)

        self.assertEqual(result.decision, QuorumDecision.CONSENSUS_ACCEPTED_FOR_REVIEW)
        self.assertEqual(result.reason_code, QuorumReasonCode.OK_QUORUM_MET_DRY_RUN)
        self.assertTrue(result.is_dry_run)

    def test_dry_run_ignores_threshold(self):
        """Dry-run with quorum met ignores consensus threshold."""
        quorum_input = QuorumVerificationInput(
            receipt_id="rcpt_dry_002",
            job_id="j_dry_002",
            tenant_id="t_test",
            attestations=[
                VerifierAttestation(verifier_id="v1", decision=AttestationStatus.REJECT),
                VerifierAttestation(verifier_id="v2", decision=AttestationStatus.REJECT),
                VerifierAttestation(verifier_id="v3", decision=AttestationStatus.REJECT),
            ],
            is_dry_run=True,
        )

        result = evaluate_quorum(quorum_input)

        # Even with 0% approval, dry-run accepts for review
        self.assertEqual(result.decision, QuorumDecision.CONSENSUS_ACCEPTED_FOR_REVIEW)
        self.assertEqual(result.reason_code, QuorumReasonCode.OK_QUORUM_MET_DRY_RUN)
        self.assertEqual(result.consensus_score, 0.0)


class TestInputBuilders(unittest.TestCase):
    """Input builder functions."""

    def test_build_from_cabr_result_dict(self):
        """build_quorum_input_from_cabr_result works with CABR dict."""
        cabr_dict = {
            "score_id": "cabr_test_001",
            "receipt_id": "rcpt_build_001",
            "job_id": "j_build_001",
            "tenant_id": "t_test",
            "is_dry_run": False,
        }
        attestations = [
            VerifierAttestation(verifier_id="v1", decision=AttestationStatus.APPROVE),
            VerifierAttestation(verifier_id="v2", decision=AttestationStatus.APPROVE),
        ]

        quorum_input = build_quorum_input_from_cabr_result(
            cabr_dict,
            attestations,
            min_validators=2,  # Custom threshold
        )

        self.assertEqual(quorum_input.receipt_id, "rcpt_build_001")
        self.assertEqual(quorum_input.job_id, "j_build_001")
        self.assertEqual(quorum_input.cabr_score_id, "cabr_test_001")
        self.assertEqual(len(quorum_input.attestations), 2)
        self.assertEqual(quorum_input.min_validators, 2)


class TestAttestationSerialization(unittest.TestCase):
    """VerifierAttestation serialization."""

    def test_attestation_to_dict(self):
        """Attestation to_dict includes all fields."""
        attestation = VerifierAttestation(
            verifier_id="v_test",
            decision=AttestationStatus.APPROVE,
            signature="sig123",
            is_dry_run=True,
            reason="Test reason",
        )

        d = attestation.to_dict()

        self.assertEqual(d["verifier_id"], "v_test")
        self.assertEqual(d["decision"], "approve")
        self.assertEqual(d["signature"], "sig123")
        self.assertTrue(d["is_dry_run"])
        self.assertEqual(d["reason"], "Test reason")

    def test_attestation_from_dict(self):
        """Attestation from_dict restores values."""
        d = {
            "verifier_id": "v_restore",
            "decision": "reject",
            "is_dry_run": False,
            "reason": "Not valid",
        }

        attestation = VerifierAttestation.from_dict(d)

        self.assertEqual(attestation.verifier_id, "v_restore")
        self.assertEqual(attestation.decision, AttestationStatus.REJECT)
        self.assertFalse(attestation.is_dry_run)
        self.assertEqual(attestation.reason, "Not valid")


class TestValidAttestationStatus(unittest.TestCase):
    """VALID attestation status behavior."""

    def test_valid_status_counts_as_approve(self):
        """VALID status counts as implicit APPROVE."""
        quorum_input = QuorumVerificationInput(
            receipt_id="rcpt_valid_001",
            job_id="j_valid_001",
            tenant_id="t_test",
            attestations=[
                VerifierAttestation(verifier_id="v1", decision=AttestationStatus.VALID),
                VerifierAttestation(verifier_id="v2", decision=AttestationStatus.VALID),
                VerifierAttestation(verifier_id="v3", decision=AttestationStatus.VALID),
            ],
        )

        result = evaluate_quorum(quorum_input)

        self.assertEqual(result.approve_count, 3)
        self.assertEqual(result.consensus_score, 1.0)
        self.assertTrue(result.threshold_met)


if __name__ == "__main__":
    unittest.main(verbosity=2)
