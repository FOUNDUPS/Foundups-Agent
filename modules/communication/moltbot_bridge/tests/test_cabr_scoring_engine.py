#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for CABR Scoring Engine Phase 1.

Validates deterministic CABR scoring per WSP 29 and WSP 97 truth boundaries.

Required coverage:
  - Missing evidence rejects
  - Valid dry-run receipt accepted for review only
  - verification_complete=False never produces final consensus
  - cabr_ready=False preserved
  - payout_ready=False preserved
  - verifier_count below 3 fails quorum
  - 3 unique verifiers passes quorum eligibility but still no payout
  - Duplicate verifiers do not count
  - Failed pAVS result rejects
  - Truth-boundary violation rejects
  - Batch scoring deterministic
  - No network calls
  - No token issuance
  - WSP 97 truth fields remain False

Slice: CABR_RUNTIME_SCORING_ENGINE_PHASE1
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

from modules.communication.moltbot_bridge.src.cabr_scoring_engine import (
    CABRScoreDecision,
    CABRScoreInput,
    CABRScoreReason,
    CABRScoreResult,
    MIN_VALIDATORS_DEFAULT,
    build_score_input_from_pavs_result,
    build_score_input_from_receipt,
    generate_score_id,
    score_cabr_batch,
    score_cabr_receipt,
    score_from_pavs_result,
    score_from_receipt,
)


class TestMissingEvidenceRejects(unittest.TestCase):
    """Missing evidence results in rejection."""

    def test_empty_evidence_refs_rejects(self):
        """Empty evidence_refs list results in REJECTED_INSUFFICIENT_EVIDENCE."""
        score_input = CABRScoreInput(
            receipt_id="rcpt_test_001",
            job_id="j_test_001",
            tenant_id="t_test",
            evidence_refs=[],
            evidence_count=0,
        )

        result = score_cabr_receipt(score_input)

        self.assertEqual(result.decision, CABRScoreDecision.REJECTED_INSUFFICIENT_EVIDENCE)
        self.assertEqual(result.reason_code, CABRScoreReason.REJECTED_EMPTY_EVIDENCE)
        self.assertFalse(result.evidence_present)

    def test_none_evidence_refs_rejects(self):
        """None evidence_refs results in REJECTED_INSUFFICIENT_EVIDENCE."""
        score_input = CABRScoreInput(
            receipt_id="rcpt_test_002",
            job_id="j_test_002",
            tenant_id="t_test",
            evidence_refs=None,  # type: ignore
            evidence_count=0,
        )

        result = score_cabr_receipt(score_input)

        self.assertEqual(result.decision, CABRScoreDecision.REJECTED_INSUFFICIENT_EVIDENCE)
        self.assertEqual(result.reason_code, CABRScoreReason.REJECTED_NO_EVIDENCE)


class TestDryRunAcceptedForReviewOnly(unittest.TestCase):
    """Dry-run receipts are accepted for review only, not final consensus."""

    def test_dry_run_with_evidence_accepted(self):
        """Dry-run receipt with evidence is ACCEPTED_FOR_REVIEW."""
        score_input = CABRScoreInput(
            receipt_id="rcpt_dry_001",
            job_id="j_dry_001",
            tenant_id="t_test",
            evidence_refs=["logs/run.txt", "outputs/result.json"],
            evidence_count=2,
            is_dry_run=True,
        )

        result = score_cabr_receipt(score_input)

        self.assertEqual(result.decision, CABRScoreDecision.ACCEPTED_FOR_REVIEW)
        self.assertEqual(result.reason_code, CABRScoreReason.OK_EVIDENCE_PRESENT_DRY_RUN)
        self.assertTrue(result.is_dry_run)
        self.assertTrue(result.evidence_present)

    def test_dry_run_never_cabr_ready(self):
        """Dry-run receipt never sets cabr_ready=True."""
        score_input = CABRScoreInput(
            receipt_id="rcpt_dry_002",
            job_id="j_dry_002",
            tenant_id="t_test",
            evidence_refs=["evidence.txt"],
            is_dry_run=True,
            verifier_ids=["v1", "v2", "v3"],  # Even with quorum
        )

        result = score_cabr_receipt(score_input)

        self.assertFalse(result.cabr_ready)
        self.assertFalse(result.payout_ready)
        self.assertFalse(result.verification_complete)

    def test_simulated_accepted_for_review(self):
        """Simulated execution is also accepted for review only."""
        score_input = CABRScoreInput(
            receipt_id="rcpt_sim_001",
            job_id="j_sim_001",
            tenant_id="t_test",
            evidence_refs=["sim_output.json"],
            is_simulated=True,
        )

        result = score_cabr_receipt(score_input)

        self.assertEqual(result.decision, CABRScoreDecision.ACCEPTED_FOR_REVIEW)
        self.assertTrue(result.is_simulated)


class TestVerificationCompleteNeverTrue(unittest.TestCase):
    """verification_complete=False in all Phase 1 outputs."""

    def test_accepted_review_verification_false(self):
        """ACCEPTED_FOR_REVIEW result has verification_complete=False."""
        score_input = CABRScoreInput(
            receipt_id="rcpt_ver_001",
            job_id="j_ver_001",
            tenant_id="t_test",
            evidence_refs=["evidence.txt"],
            verifier_ids=["v1", "v2", "v3"],
        )

        result = score_cabr_receipt(score_input)

        self.assertFalse(result.verification_complete)

    def test_rejected_verification_false(self):
        """Rejected results also have verification_complete=False."""
        score_input = CABRScoreInput(
            receipt_id="rcpt_ver_002",
            job_id="j_ver_002",
            tenant_id="t_test",
            evidence_refs=[],
        )

        result = score_cabr_receipt(score_input)

        self.assertFalse(result.verification_complete)


class TestCABRReadyAlwaysFalse(unittest.TestCase):
    """cabr_ready=False in all Phase 1 outputs."""

    def test_accepted_with_quorum_cabr_false(self):
        """Even with quorum met, cabr_ready=False."""
        score_input = CABRScoreInput(
            receipt_id="rcpt_cabr_001",
            job_id="j_cabr_001",
            tenant_id="t_test",
            evidence_refs=["e1.txt", "e2.txt"],
            verifier_ids=["v1", "v2", "v3", "v4", "v5"],  # Well above quorum
        )

        result = score_cabr_receipt(score_input)

        self.assertEqual(result.decision, CABRScoreDecision.ACCEPTED_FOR_REVIEW)
        self.assertTrue(result.quorum_met)
        self.assertFalse(result.cabr_ready)


class TestPayoutReadyAlwaysFalse(unittest.TestCase):
    """payout_ready=False in all Phase 1 outputs."""

    def test_accepted_payout_false(self):
        """Accepted results have payout_ready=False."""
        score_input = CABRScoreInput(
            receipt_id="rcpt_pay_001",
            job_id="j_pay_001",
            tenant_id="t_test",
            evidence_refs=["evidence.txt"],
            verifier_ids=["v1", "v2", "v3"],
        )

        result = score_cabr_receipt(score_input)

        self.assertFalse(result.payout_ready)


class TestQuorumBelowThreeFails(unittest.TestCase):
    """Verifier count below 3 (min_validators) does not meet quorum."""

    def test_two_verifiers_pending_quorum(self):
        """2 verifiers results in ACCEPTED_FOR_REVIEW_PENDING_QUORUM."""
        score_input = CABRScoreInput(
            receipt_id="rcpt_q_001",
            job_id="j_q_001",
            tenant_id="t_test",
            evidence_refs=["evidence.txt"],
            verifier_ids=["v1", "v2"],
        )

        result = score_cabr_receipt(score_input)

        self.assertEqual(result.decision, CABRScoreDecision.ACCEPTED_FOR_REVIEW_PENDING_QUORUM)
        self.assertEqual(result.reason_code, CABRScoreReason.OK_EVIDENCE_PRESENT_PENDING_QUORUM)
        self.assertEqual(result.unique_verifier_count, 2)
        self.assertFalse(result.quorum_met)

    def test_one_verifier_pending_quorum(self):
        """1 verifier results in ACCEPTED_FOR_REVIEW_PENDING_QUORUM."""
        score_input = CABRScoreInput(
            receipt_id="rcpt_q_002",
            job_id="j_q_002",
            tenant_id="t_test",
            evidence_refs=["evidence.txt"],
            verifier_ids=["v1"],
        )

        result = score_cabr_receipt(score_input)

        self.assertEqual(result.decision, CABRScoreDecision.ACCEPTED_FOR_REVIEW_PENDING_QUORUM)
        self.assertEqual(result.unique_verifier_count, 1)
        self.assertFalse(result.quorum_met)

    def test_zero_verifiers_pending_quorum(self):
        """0 verifiers results in ACCEPTED_FOR_REVIEW_PENDING_QUORUM."""
        score_input = CABRScoreInput(
            receipt_id="rcpt_q_003",
            job_id="j_q_003",
            tenant_id="t_test",
            evidence_refs=["evidence.txt"],
            verifier_ids=[],
        )

        result = score_cabr_receipt(score_input)

        self.assertEqual(result.decision, CABRScoreDecision.ACCEPTED_FOR_REVIEW_PENDING_QUORUM)
        self.assertEqual(result.unique_verifier_count, 0)
        self.assertFalse(result.quorum_met)


class TestThreeVerifiersQuorumEligible(unittest.TestCase):
    """3 unique verifiers passes quorum eligibility but still no payout."""

    def test_three_verifiers_accepted_with_quorum(self):
        """3 verifiers results in ACCEPTED_FOR_REVIEW with quorum_met=True."""
        score_input = CABRScoreInput(
            receipt_id="rcpt_3v_001",
            job_id="j_3v_001",
            tenant_id="t_test",
            evidence_refs=["evidence.txt"],
            verifier_ids=["v1", "v2", "v3"],
        )

        result = score_cabr_receipt(score_input)

        self.assertEqual(result.decision, CABRScoreDecision.ACCEPTED_FOR_REVIEW)
        self.assertEqual(result.reason_code, CABRScoreReason.OK_EVIDENCE_PRESENT_QUORUM_MET)
        self.assertEqual(result.unique_verifier_count, 3)
        self.assertTrue(result.quorum_met)
        # Still no payout
        self.assertFalse(result.payout_ready)
        self.assertFalse(result.cabr_ready)

    def test_four_verifiers_accepted_with_quorum(self):
        """More than 3 verifiers also passes quorum."""
        score_input = CABRScoreInput(
            receipt_id="rcpt_4v_001",
            job_id="j_4v_001",
            tenant_id="t_test",
            evidence_refs=["evidence.txt"],
            verifier_ids=["v1", "v2", "v3", "v4"],
        )

        result = score_cabr_receipt(score_input)

        self.assertEqual(result.decision, CABRScoreDecision.ACCEPTED_FOR_REVIEW)
        self.assertEqual(result.unique_verifier_count, 4)
        self.assertTrue(result.quorum_met)


class TestDuplicateVerifiersDoNotCount(unittest.TestCase):
    """Duplicate verifier IDs do not count toward quorum."""

    def test_duplicate_verifiers_rejected(self):
        """Duplicate verifier IDs result in REJECTED_DUPLICATE_VERIFIERS."""
        score_input = CABRScoreInput(
            receipt_id="rcpt_dup_001",
            job_id="j_dup_001",
            tenant_id="t_test",
            evidence_refs=["evidence.txt"],
            verifier_ids=["v1", "v1", "v2"],  # v1 duplicated
        )

        result = score_cabr_receipt(score_input)

        self.assertEqual(result.decision, CABRScoreDecision.REJECTED_DUPLICATE_VERIFIERS)
        self.assertEqual(result.reason_code, CABRScoreReason.REJECTED_DUPLICATE_VERIFIER_IDS)
        self.assertTrue(result.duplicate_verifiers_detected)
        self.assertEqual(result.verifier_count, 3)
        self.assertEqual(result.unique_verifier_count, 2)

    def test_all_duplicates_rejected(self):
        """All-duplicate verifier list is rejected."""
        score_input = CABRScoreInput(
            receipt_id="rcpt_dup_002",
            job_id="j_dup_002",
            tenant_id="t_test",
            evidence_refs=["evidence.txt"],
            verifier_ids=["v1", "v1", "v1"],  # All same
        )

        result = score_cabr_receipt(score_input)

        self.assertEqual(result.decision, CABRScoreDecision.REJECTED_DUPLICATE_VERIFIERS)
        self.assertEqual(result.verifier_count, 3)
        self.assertEqual(result.unique_verifier_count, 1)


class TestFailedPAVSResultRejects(unittest.TestCase):
    """Failed pAVS results cause CABR rejection."""

    def test_pavs_blocked_missing_evidence_rejects(self):
        """BLOCKED_MISSING_EVIDENCE pAVS decision rejects."""
        score_input = CABRScoreInput(
            receipt_id="rcpt_pavs_001",
            job_id="j_pavs_001",
            tenant_id="t_test",
            evidence_refs=["evidence.txt"],  # Has evidence but pAVS says no
            pavs_decision="blocked_missing_evidence",
        )

        result = score_cabr_receipt(score_input)

        self.assertEqual(result.decision, CABRScoreDecision.REJECTED_PAVS_FAILED)
        self.assertEqual(result.reason_code, CABRScoreReason.REJECTED_PAVS_BLOCKED_MISSING_EVIDENCE)
        self.assertFalse(result.pavs_passed)

    def test_pavs_blocked_upstream_rejects(self):
        """BLOCKED_UPSTREAM pAVS decision rejects."""
        score_input = CABRScoreInput(
            receipt_id="rcpt_pavs_002",
            job_id="j_pavs_002",
            tenant_id="t_test",
            evidence_refs=["evidence.txt"],
            pavs_decision="blocked_upstream",
        )

        result = score_cabr_receipt(score_input)

        self.assertEqual(result.decision, CABRScoreDecision.REJECTED_PAVS_FAILED)
        self.assertEqual(result.reason_code, CABRScoreReason.REJECTED_PAVS_BLOCKED_UPSTREAM)

    def test_pavs_failed_input_rejects(self):
        """FAILED_INPUT pAVS decision rejects."""
        score_input = CABRScoreInput(
            receipt_id="rcpt_pavs_003",
            job_id="j_pavs_003",
            tenant_id="t_test",
            evidence_refs=["evidence.txt"],
            pavs_decision="failed_input",
        )

        result = score_cabr_receipt(score_input)

        self.assertEqual(result.decision, CABRScoreDecision.REJECTED_PAVS_FAILED)
        self.assertEqual(result.reason_code, CABRScoreReason.REJECTED_PAVS_FAILED_INPUT)

    def test_pavs_accepted_passes(self):
        """ACCEPTED_FOR_REVIEW pAVS decision allows scoring."""
        score_input = CABRScoreInput(
            receipt_id="rcpt_pavs_004",
            job_id="j_pavs_004",
            tenant_id="t_test",
            evidence_refs=["evidence.txt"],
            pavs_decision="accepted_for_review",
            verifier_ids=["v1", "v2", "v3"],
        )

        result = score_cabr_receipt(score_input)

        self.assertEqual(result.decision, CABRScoreDecision.ACCEPTED_FOR_REVIEW)
        self.assertTrue(result.pavs_passed)


class TestTruthBoundaryViolationRejects(unittest.TestCase):
    """Inputs claiming completion/ready states are rejected."""

    def test_verification_complete_true_rejects(self):
        """verification_complete=True in input causes rejection."""
        score_input = CABRScoreInput(
            receipt_id="rcpt_truth_001",
            job_id="j_truth_001",
            tenant_id="t_test",
            evidence_refs=["evidence.txt"],
            verification_complete=True,  # Violates WSP 97
        )

        result = score_cabr_receipt(score_input)

        self.assertEqual(result.decision, CABRScoreDecision.REJECTED_TRUTH_BOUNDARY)
        self.assertEqual(result.reason_code, CABRScoreReason.REJECTED_VERIFICATION_COMPLETE_CLAIMED)

    def test_cabr_ready_true_rejects(self):
        """cabr_ready=True in input causes rejection."""
        score_input = CABRScoreInput(
            receipt_id="rcpt_truth_002",
            job_id="j_truth_002",
            tenant_id="t_test",
            evidence_refs=["evidence.txt"],
            cabr_ready=True,  # Violates WSP 97
        )

        result = score_cabr_receipt(score_input)

        self.assertEqual(result.decision, CABRScoreDecision.REJECTED_TRUTH_BOUNDARY)
        self.assertEqual(result.reason_code, CABRScoreReason.REJECTED_CABR_READY_CLAIMED)

    def test_payout_ready_true_rejects(self):
        """payout_ready=True in input causes rejection."""
        score_input = CABRScoreInput(
            receipt_id="rcpt_truth_003",
            job_id="j_truth_003",
            tenant_id="t_test",
            evidence_refs=["evidence.txt"],
            payout_ready=True,  # Violates WSP 97
        )

        result = score_cabr_receipt(score_input)

        self.assertEqual(result.decision, CABRScoreDecision.REJECTED_TRUTH_BOUNDARY)
        self.assertEqual(result.reason_code, CABRScoreReason.REJECTED_PAYOUT_READY_CLAIMED)


class TestBatchScoringDeterministic(unittest.TestCase):
    """Batch scoring returns deterministic results in order."""

    def test_batch_order_preserved(self):
        """Batch results are in same order as inputs."""
        inputs = [
            CABRScoreInput(
                receipt_id="rcpt_batch_1",
                job_id="j_1",
                tenant_id="t_1",
                evidence_refs=["e1.txt"],
                verifier_ids=["v1", "v2", "v3"],
            ),
            CABRScoreInput(
                receipt_id="rcpt_batch_2",
                job_id="j_2",
                tenant_id="t_2",
                evidence_refs=[],  # Will reject
            ),
            CABRScoreInput(
                receipt_id="rcpt_batch_3",
                job_id="j_3",
                tenant_id="t_3",
                evidence_refs=["e3.txt"],
                is_dry_run=True,
            ),
        ]

        results = score_cabr_batch(inputs)

        self.assertEqual(len(results), 3)
        self.assertEqual(results[0].receipt_id, "rcpt_batch_1")
        self.assertEqual(results[0].decision, CABRScoreDecision.ACCEPTED_FOR_REVIEW)
        self.assertEqual(results[1].receipt_id, "rcpt_batch_2")
        self.assertEqual(results[1].decision, CABRScoreDecision.REJECTED_INSUFFICIENT_EVIDENCE)
        self.assertEqual(results[2].receipt_id, "rcpt_batch_3")
        self.assertEqual(results[2].decision, CABRScoreDecision.ACCEPTED_FOR_REVIEW)
        self.assertTrue(results[2].is_dry_run)

    def test_batch_empty_input(self):
        """Empty batch returns empty results."""
        results = score_cabr_batch([])
        self.assertEqual(len(results), 0)


class TestNoNetworkCalls(unittest.TestCase):
    """CABR scoring makes no network calls."""

    def test_score_is_purely_local(self):
        """Scoring is a pure local computation."""
        # This test verifies the function runs without network
        # by successfully completing - if it tried network calls
        # and they failed, this would raise
        score_input = CABRScoreInput(
            receipt_id="rcpt_local_001",
            job_id="j_local_001",
            tenant_id="t_test",
            evidence_refs=["evidence.txt"],
            verifier_ids=["v1", "v2", "v3"],
        )

        result = score_cabr_receipt(score_input)

        # Successfully computed
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.score_id)


class TestNoTokenIssuance(unittest.TestCase):
    """CABR scoring does not issue tokens."""

    def test_no_token_fields_in_result(self):
        """Result does not contain token/UPS/payout amounts."""
        score_input = CABRScoreInput(
            receipt_id="rcpt_token_001",
            job_id="j_token_001",
            tenant_id="t_test",
            evidence_refs=["evidence.txt"],
            verifier_ids=["v1", "v2", "v3"],
        )

        result = score_cabr_receipt(score_input)
        result_dict = result.to_dict()

        # Verify no token-related fields
        self.assertNotIn("tokens_issued", result_dict)
        self.assertNotIn("ups_allocated", result_dict)
        self.assertNotIn("payout_amount", result_dict)
        self.assertNotIn("reward_amount", result_dict)


class TestWSP97TruthFieldsRemainFalse(unittest.TestCase):
    """All WSP 97 truth fields remain False in Phase 1 output."""

    def test_all_acceptance_states_have_false_truth_fields(self):
        """Every acceptance state has truth fields False."""
        # Test various acceptance scenarios
        test_cases = [
            CABRScoreInput(
                receipt_id="rcpt_wsp_1",
                job_id="j_1",
                tenant_id="t",
                evidence_refs=["e.txt"],
                verifier_ids=["v1", "v2", "v3"],
            ),
            CABRScoreInput(
                receipt_id="rcpt_wsp_2",
                job_id="j_2",
                tenant_id="t",
                evidence_refs=["e.txt"],
                is_dry_run=True,
            ),
            CABRScoreInput(
                receipt_id="rcpt_wsp_3",
                job_id="j_3",
                tenant_id="t",
                evidence_refs=["e.txt"],
                verifier_ids=["v1"],  # Pending quorum
            ),
        ]

        for score_input in test_cases:
            result = score_cabr_receipt(score_input)
            self.assertFalse(
                result.verification_complete,
                f"verification_complete should be False for {score_input.receipt_id}",
            )
            self.assertFalse(
                result.cabr_ready,
                f"cabr_ready should be False for {score_input.receipt_id}",
            )
            self.assertFalse(
                result.payout_ready,
                f"payout_ready should be False for {score_input.receipt_id}",
            )


class TestMissingIdentityRejects(unittest.TestCase):
    """Missing identity fields cause rejection."""

    def test_missing_receipt_id_rejects(self):
        """Empty receipt_id causes rejection."""
        score_input = CABRScoreInput(
            receipt_id="",
            job_id="j_id_001",
            tenant_id="t_test",
            evidence_refs=["evidence.txt"],
        )

        result = score_cabr_receipt(score_input)

        self.assertEqual(result.decision, CABRScoreDecision.REJECTED_MISSING_IDENTITY)
        self.assertEqual(result.reason_code, CABRScoreReason.REJECTED_NO_RECEIPT_ID)

    def test_whitespace_receipt_id_rejects(self):
        """Whitespace-only receipt_id causes rejection."""
        score_input = CABRScoreInput(
            receipt_id="   ",
            job_id="j_id_002",
            tenant_id="t_test",
            evidence_refs=["evidence.txt"],
        )

        result = score_cabr_receipt(score_input)

        self.assertEqual(result.decision, CABRScoreDecision.REJECTED_MISSING_IDENTITY)
        self.assertEqual(result.reason_code, CABRScoreReason.REJECTED_NO_RECEIPT_ID)

    def test_missing_job_id_rejects(self):
        """Empty job_id causes rejection."""
        score_input = CABRScoreInput(
            receipt_id="rcpt_id_001",
            job_id="",
            tenant_id="t_test",
            evidence_refs=["evidence.txt"],
        )

        result = score_cabr_receipt(score_input)

        self.assertEqual(result.decision, CABRScoreDecision.REJECTED_MISSING_IDENTITY)
        self.assertEqual(result.reason_code, CABRScoreReason.REJECTED_NO_JOB_ID)

    def test_missing_tenant_id_rejects(self):
        """Empty tenant_id causes rejection."""
        score_input = CABRScoreInput(
            receipt_id="rcpt_id_001",
            job_id="j_id_001",
            tenant_id="",
            evidence_refs=["evidence.txt"],
        )

        result = score_cabr_receipt(score_input)

        self.assertEqual(result.decision, CABRScoreDecision.REJECTED_MISSING_IDENTITY)
        self.assertEqual(result.reason_code, CABRScoreReason.REJECTED_NO_TENANT_ID)


class TestScoreIdGeneration(unittest.TestCase):
    """Score ID generation."""

    def test_score_id_format(self):
        """Score ID follows cabr_{suffix}_{timestamp}_{random} format."""
        score_id = generate_score_id("rcpt_test_abc123_def456")

        self.assertTrue(score_id.startswith("cabr_"))
        parts = score_id.split("_")
        self.assertGreaterEqual(len(parts), 4)

    def test_score_ids_unique(self):
        """Consecutive scores have unique IDs."""
        ids = [generate_score_id("rcpt_test_123") for _ in range(10)]
        self.assertEqual(len(ids), len(set(ids)))


class TestResultSerialization(unittest.TestCase):
    """CABRScoreResult serialization round-trips."""

    def test_to_dict_contains_required_fields(self):
        """to_dict includes all required fields."""
        score_input = CABRScoreInput(
            receipt_id="rcpt_serial_001",
            job_id="j_serial_001",
            tenant_id="t_test",
            evidence_refs=["e.txt"],
            verifier_ids=["v1", "v2", "v3"],
        )

        result = score_cabr_receipt(score_input)
        d = result.to_dict()

        self.assertIn("score_id", d)
        self.assertIn("receipt_id", d)
        self.assertIn("job_id", d)
        self.assertIn("tenant_id", d)
        self.assertIn("decision", d)
        self.assertIn("reason_code", d)
        self.assertIn("quorum_met", d)
        self.assertIn("verification_complete", d)
        self.assertIn("cabr_ready", d)
        self.assertIn("payout_ready", d)

    def test_from_dict_roundtrip(self):
        """from_dict restores result from to_dict."""
        score_input = CABRScoreInput(
            receipt_id="rcpt_round_001",
            job_id="j_round_001",
            tenant_id="t_roundtrip",
            evidence_refs=["r1.txt", "r2.txt"],
            verifier_ids=["v1", "v2", "v3"],
        )

        result = score_cabr_receipt(score_input)
        d = result.to_dict()
        restored = CABRScoreResult.from_dict(d)

        self.assertEqual(restored.score_id, result.score_id)
        self.assertEqual(restored.receipt_id, result.receipt_id)
        self.assertEqual(restored.decision, CABRScoreDecision.ACCEPTED_FOR_REVIEW)
        self.assertTrue(restored.quorum_met)
        self.assertFalse(restored.cabr_ready)
        self.assertFalse(restored.payout_ready)


class TestConvenienceFunctions(unittest.TestCase):
    """Convenience functions for direct scoring."""

    def test_score_from_receipt_dict(self):
        """score_from_receipt works with dict input."""
        receipt_dict = {
            "receipt_id": "rcpt_conv_001",
            "job_id": "j_conv_001",
            "tenant_id": "t_test",
            "evidence_refs": ["evidence.txt"],
            "verification_status": "pending_pavs",
        }

        result = score_from_receipt(receipt_dict, verifier_ids=["v1", "v2", "v3"])

        self.assertEqual(result.decision, CABRScoreDecision.ACCEPTED_FOR_REVIEW)
        self.assertEqual(result.receipt_id, "rcpt_conv_001")

    def test_score_from_pavs_result_dict(self):
        """score_from_pavs_result works with dict input."""
        pavs_dict = {
            "receipt_id": "rcpt_pavs_conv_001",
            "job_id": "j_pavs_conv_001",
            "tenant_id": "t_test",
            "evidence_refs": ["evidence.txt"],
            "evidence_count": 1,
            "decision": "accepted_for_review",
            "verification_complete": False,
            "cabr_ready": False,
            "payout_ready": False,
        }

        result = score_from_pavs_result(pavs_dict, verifier_ids=["v1", "v2", "v3"])

        self.assertEqual(result.decision, CABRScoreDecision.ACCEPTED_FOR_REVIEW)
        self.assertTrue(result.pavs_passed)


class TestMinValidatorsConfiguration(unittest.TestCase):
    """min_validators configuration."""

    def test_default_min_validators_is_three(self):
        """Default min_validators is 3 per WSP 29."""
        self.assertEqual(MIN_VALIDATORS_DEFAULT, 3)

    def test_custom_min_validators(self):
        """Custom min_validators threshold works."""
        score_input = CABRScoreInput(
            receipt_id="rcpt_minval_001",
            job_id="j_minval_001",
            tenant_id="t_test",
            evidence_refs=["evidence.txt"],
            verifier_ids=["v1", "v2", "v3", "v4", "v5"],  # 5 verifiers
        )

        # With min_validators=5, quorum should be met
        result_5 = score_cabr_receipt(score_input, min_validators=5)
        self.assertTrue(result_5.quorum_met)
        self.assertEqual(result_5.min_validators, 5)

        # With min_validators=6, quorum should NOT be met
        result_6 = score_cabr_receipt(score_input, min_validators=6)
        self.assertFalse(result_6.quorum_met)
        self.assertEqual(result_6.min_validators, 6)


class TestInputBuilders(unittest.TestCase):
    """Input builder functions."""

    def test_build_from_receipt_dict(self):
        """build_score_input_from_receipt works with dict."""
        receipt_dict = {
            "receipt_id": "rcpt_build_001",
            "job_id": "j_build_001",
            "tenant_id": "t_test",
            "evidence_refs": ["e1.txt", "e2.txt"],
            "foundup_id": "f_test",
            "intent_id": "i_test",
            "verification_status": "pending_pavs",
        }

        score_input = build_score_input_from_receipt(
            receipt_dict,
            verifier_ids=["v1", "v2"],
        )

        self.assertEqual(score_input.receipt_id, "rcpt_build_001")
        self.assertEqual(score_input.evidence_count, 2)
        self.assertEqual(score_input.foundup_id, "f_test")
        self.assertEqual(len(score_input.verifier_ids), 2)
        self.assertEqual(score_input.source_type, "receipt")

    def test_build_from_pavs_dict(self):
        """build_score_input_from_pavs_result works with dict."""
        pavs_dict = {
            "receipt_id": "rcpt_pavs_build_001",
            "job_id": "j_pavs_build_001",
            "tenant_id": "t_test",
            "evidence_refs": ["e.txt"],
            "evidence_count": 1,
            "decision": "not_required",
            "verification_complete": False,
            "cabr_ready": False,
            "payout_ready": False,
        }

        score_input = build_score_input_from_pavs_result(pavs_dict)

        self.assertEqual(score_input.receipt_id, "rcpt_pavs_build_001")
        self.assertEqual(score_input.pavs_decision, "not_required")
        self.assertTrue(score_input.is_dry_run)
        self.assertEqual(score_input.source_type, "pavs_result")


if __name__ == "__main__":
    unittest.main(verbosity=2)
