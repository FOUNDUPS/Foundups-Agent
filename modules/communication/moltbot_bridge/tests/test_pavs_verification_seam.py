#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Focused tests for pAVS Verification Seam.

Tests WSP 97 truth boundaries:
  - PENDING_PAVS + evidence -> ACCEPTED_FOR_REVIEW
  - PENDING_PAVS - evidence -> BLOCKED_MISSING_EVIDENCE
  - NOT_REQUIRED -> NOT_REQUIRED (pass-through)
  - BLOCKED -> BLOCKED_UPSTREAM
  - FAILED_INPUT -> FAILED_INPUT
  - Missing identity fields -> rejection
  - cabr_ready and payout_ready always False

Worker slice: W7 (OC7_PAVS_PROOF_OF_COMPUTE_VERIFICATION_PLACEHOLDER_PHASE1)
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from modules.communication.moltbot_bridge.src.foundup_job_contract import (
    JobStatus,
    StatusReasonCode,
    create_job,
)
from modules.communication.moltbot_bridge.src.proof_of_compute_receipt import (
    ProofOfComputeReceipt,
    VerificationStatus,
    create_receipt_from_job,
)
from modules.communication.moltbot_bridge.src.pavs_verification_seam import (
    PAVSDecision,
    PAVSReasonCode,
    PAVSVerificationResult,
    generate_verification_id,
    verify_receipt,
    verify_receipts,
)


class TestSucceededReceiptWithEvidence(unittest.TestCase):
    """PENDING_PAVS receipt with evidence -> ACCEPTED_FOR_REVIEW."""

    def test_pending_pavs_with_evidence_accepted(self):
        """Receipt with evidence_refs is accepted for review."""
        job = create_job(
            requested_action="execute",
            tenant_id="tenant_001",
            foundup_id="f_test_001",
        )
        job.status = JobStatus.SUCCEEDED
        job.status_reason_code = StatusReasonCode.OK_COMPLETED
        job.policy_flags.dry_run_mode = False
        job.evidence_refs = ["logs/run.txt", "outputs/result.json"]

        receipt_result = create_receipt_from_job(job)
        self.assertTrue(receipt_result.success)

        result = verify_receipt(receipt_result.receipt)

        self.assertEqual(result.decision, PAVSDecision.ACCEPTED_FOR_REVIEW)
        self.assertEqual(result.reason_code, PAVSReasonCode.OK_EVIDENCE_PRESENT)
        self.assertEqual(result.evidence_count, 2)
        self.assertIn("logs/run.txt", result.evidence_refs)
        self.assertIn("2 evidence ref(s) present", result.reason_human)

    def test_cabr_ready_always_false(self):
        """cabr_ready must be False regardless of evidence."""
        job = create_job(requested_action="x", tenant_id="t")
        job.status = JobStatus.SUCCEEDED
        job.evidence_refs = ["strong/evidence.json"]

        receipt_result = create_receipt_from_job(job)
        result = verify_receipt(receipt_result.receipt)

        self.assertFalse(result.cabr_ready)

    def test_payout_ready_always_false(self):
        """payout_ready must be False regardless of evidence."""
        job = create_job(requested_action="x", tenant_id="t")
        job.status = JobStatus.SUCCEEDED
        job.evidence_refs = ["evidence.txt"]

        receipt_result = create_receipt_from_job(job)
        result = verify_receipt(receipt_result.receipt)

        self.assertFalse(result.payout_ready)

    def test_verification_complete_always_false(self):
        """verification_complete must be False (we only accept for review)."""
        job = create_job(requested_action="x", tenant_id="t")
        job.status = JobStatus.SUCCEEDED
        job.evidence_refs = ["complete/evidence.json"]

        receipt_result = create_receipt_from_job(job)
        result = verify_receipt(receipt_result.receipt)

        self.assertFalse(result.verification_complete)


class TestSucceededReceiptMissingEvidence(unittest.TestCase):
    """PENDING_PAVS receipt without evidence -> BLOCKED_MISSING_EVIDENCE."""

    def test_pending_pavs_without_evidence_blocked(self):
        """Receipt claiming PENDING_PAVS but no evidence is blocked."""
        job = create_job(
            requested_action="execute",
            tenant_id="tenant_002",
        )
        job.status = JobStatus.SUCCEEDED
        job.status_reason_code = StatusReasonCode.OK_COMPLETED
        job.policy_flags.dry_run_mode = False
        job.evidence_refs = []  # No evidence!

        receipt_result = create_receipt_from_job(job)
        self.assertTrue(receipt_result.success)
        self.assertEqual(
            receipt_result.receipt.verification_status, VerificationStatus.PENDING_PAVS
        )

        result = verify_receipt(receipt_result.receipt)

        self.assertEqual(result.decision, PAVSDecision.BLOCKED_MISSING_EVIDENCE)
        self.assertEqual(result.reason_code, PAVSReasonCode.BLOCKED_NO_EVIDENCE)
        self.assertEqual(result.evidence_count, 0)
        self.assertIn("no evidence_refs", result.reason_human)

    def test_blocked_missing_evidence_preserves_identity(self):
        """Blocked receipt still preserves identity fields."""
        job = create_job(requested_action="x", tenant_id="tenant_xyz")
        job.status = JobStatus.SUCCEEDED
        job.evidence_refs = []

        receipt_result = create_receipt_from_job(job)
        result = verify_receipt(receipt_result.receipt)

        self.assertEqual(result.tenant_id, "tenant_xyz")
        self.assertEqual(result.job_id, receipt_result.receipt.job_id)
        self.assertEqual(result.receipt_id, receipt_result.receipt.receipt_id)


class TestDryRunNotRequiredReceipt(unittest.TestCase):
    """NOT_REQUIRED (dry-run) receipt -> NOT_REQUIRED decision."""

    def test_dry_run_passes_through(self):
        """Dry-run receipt yields NOT_REQUIRED decision."""
        job = create_job(requested_action="validate", tenant_id="tenant_dry")
        job.status = JobStatus.SUCCEEDED
        job.status_reason_code = StatusReasonCode.OK_DRY_RUN_PASSED

        receipt_result = create_receipt_from_job(job)
        self.assertEqual(
            receipt_result.receipt.verification_status, VerificationStatus.NOT_REQUIRED
        )

        result = verify_receipt(receipt_result.receipt)

        self.assertEqual(result.decision, PAVSDecision.NOT_REQUIRED)
        self.assertEqual(result.reason_code, PAVSReasonCode.OK_NOT_REQUIRED)
        self.assertIn("dry-run", result.reason_human)

    def test_not_required_still_has_false_flags(self):
        """NOT_REQUIRED decision still has cabr/payout/complete = False."""
        job = create_job(requested_action="x", tenant_id="t")
        job.status = JobStatus.SUCCEEDED
        job.status_reason_code = StatusReasonCode.OK_DRY_RUN_PASSED

        receipt_result = create_receipt_from_job(job)
        result = verify_receipt(receipt_result.receipt)

        self.assertFalse(result.cabr_ready)
        self.assertFalse(result.payout_ready)
        self.assertFalse(result.verification_complete)


class TestBlockedReceipt(unittest.TestCase):
    """BLOCKED receipt -> BLOCKED_UPSTREAM decision."""

    def test_blocked_receipt_yields_blocked_upstream(self):
        """Receipt from BLOCKED job yields BLOCKED_UPSTREAM."""
        job = create_job(requested_action="process", tenant_id="tenant_blocked")
        job.status = JobStatus.BLOCKED
        job.status_reason_code = StatusReasonCode.BLOCKED_DEPENDENCY_MISSING
        job.status_reason_human = "Required module not found"
        job.evidence_refs = ["audit/block_trace.json"]

        receipt_result = create_receipt_from_job(job)
        self.assertEqual(
            receipt_result.receipt.verification_status, VerificationStatus.BLOCKED
        )

        result = verify_receipt(receipt_result.receipt)

        self.assertEqual(result.decision, PAVSDecision.BLOCKED_UPSTREAM)
        self.assertEqual(result.reason_code, PAVSReasonCode.BLOCKED_JOB_BLOCKED)
        self.assertIn("BLOCKED", result.reason_human)

    def test_blocked_preserves_evidence(self):
        """Blocking evidence is preserved in result."""
        job = create_job(requested_action="x", tenant_id="t")
        job.status = JobStatus.BLOCKED
        job.evidence_refs = ["block_reason.txt"]

        receipt_result = create_receipt_from_job(job)
        result = verify_receipt(receipt_result.receipt)

        self.assertEqual(result.evidence_count, 1)
        self.assertIn("block_reason.txt", result.evidence_refs)


class TestFailedInputReceipt(unittest.TestCase):
    """FAILED_INPUT receipt -> FAILED_INPUT decision."""

    def test_failed_input_receipt_yields_failed_input(self):
        """Receipt from FAILED job yields FAILED_INPUT."""
        job = create_job(requested_action="compute", tenant_id="tenant_fail")
        job.status = JobStatus.FAILED
        job.status_reason_code = StatusReasonCode.FAIL_VALIDATION_ERROR
        job.status_reason_human = "Invalid input format"
        job.evidence_refs = ["logs/validation_error.log"]

        receipt_result = create_receipt_from_job(job)
        self.assertEqual(
            receipt_result.receipt.verification_status, VerificationStatus.FAILED_INPUT
        )

        result = verify_receipt(receipt_result.receipt)

        self.assertEqual(result.decision, PAVSDecision.FAILED_INPUT)
        self.assertEqual(result.reason_code, PAVSReasonCode.FAILED_JOB_FAILED)
        self.assertIn("FAILED", result.reason_human)

    def test_failed_preserves_failure_evidence(self):
        """Failure evidence is preserved."""
        job = create_job(requested_action="x", tenant_id="t")
        job.status = JobStatus.FAILED
        job.evidence_refs = ["error_trace.log", "stack.txt"]

        receipt_result = create_receipt_from_job(job)
        result = verify_receipt(receipt_result.receipt)

        self.assertEqual(result.evidence_count, 2)


class TestMissingIdentityFields(unittest.TestCase):
    """Receipts with missing identity fields are rejected."""

    def test_missing_receipt_id_rejected(self):
        """Receipt without receipt_id is rejected."""
        receipt_dict = {
            "receipt_id": "",
            "job_id": "j_test_123",
            "tenant_id": "t_123",
            "verification_status": "pending_pavs",
            "evidence_refs": ["x.txt"],
        }

        result = verify_receipt(receipt_dict)

        self.assertEqual(result.decision, PAVSDecision.REJECTED_MISSING_IDENTITY)
        self.assertEqual(result.reason_code, PAVSReasonCode.REJECTED_NO_RECEIPT_ID)
        self.assertIn("receipt_id", result.reason_human)

    def test_whitespace_receipt_id_rejected(self):
        """Receipt with whitespace-only receipt_id is rejected."""
        receipt_dict = {
            "receipt_id": "   ",
            "job_id": "j_test_123",
            "tenant_id": "t_123",
            "verification_status": "pending_pavs",
            "evidence_refs": [],
        }

        result = verify_receipt(receipt_dict)

        self.assertEqual(result.decision, PAVSDecision.REJECTED_MISSING_IDENTITY)
        self.assertEqual(result.reason_code, PAVSReasonCode.REJECTED_NO_RECEIPT_ID)

    def test_missing_job_id_rejected(self):
        """Receipt without job_id is rejected."""
        receipt_dict = {
            "receipt_id": "rcpt_test_abc123",
            "job_id": "",
            "tenant_id": "t_123",
            "verification_status": "pending_pavs",
            "evidence_refs": ["x.txt"],
        }

        result = verify_receipt(receipt_dict)

        self.assertEqual(result.decision, PAVSDecision.REJECTED_MISSING_IDENTITY)
        self.assertEqual(result.reason_code, PAVSReasonCode.REJECTED_NO_JOB_ID)
        self.assertIn("job_id", result.reason_human)

    def test_missing_tenant_id_rejected(self):
        """Receipt without tenant_id is rejected."""
        receipt_dict = {
            "receipt_id": "rcpt_test_abc123",
            "job_id": "j_test_123",
            "tenant_id": "",
            "verification_status": "pending_pavs",
            "evidence_refs": ["x.txt"],
        }

        result = verify_receipt(receipt_dict)

        self.assertEqual(result.decision, PAVSDecision.REJECTED_MISSING_IDENTITY)
        self.assertEqual(result.reason_code, PAVSReasonCode.REJECTED_NO_TENANT_ID)
        self.assertIn("tenant_id", result.reason_human)


class TestVerificationIdGeneration(unittest.TestCase):
    """Verification ID generation."""

    def test_verification_id_format(self):
        """Verification ID follows pv_{suffix}_{timestamp}_{random} format."""
        v_id = generate_verification_id("rcpt_create_abc123_def456")

        self.assertTrue(v_id.startswith("pv_"))
        parts = v_id.split("_")
        self.assertGreaterEqual(len(parts), 4)

    def test_verification_ids_unique(self):
        """Consecutive verifications have unique IDs."""
        ids = [generate_verification_id("rcpt_test_123") for _ in range(10)]
        self.assertEqual(len(ids), len(set(ids)))


class TestDictInputSupport(unittest.TestCase):
    """verify_receipt accepts both ProofOfComputeReceipt and dict."""

    def test_accepts_dict_input(self):
        """verify_receipt works with dict input."""
        receipt_dict = {
            "receipt_id": "rcpt_dict_test_12345678_abcdef",
            "job_id": "j_dict_test_abc123",
            "tenant_id": "tenant_dict",
            "verification_status": "pending_pavs",
            "evidence_refs": ["dict_evidence.json"],
        }

        result = verify_receipt(receipt_dict)

        self.assertEqual(result.decision, PAVSDecision.ACCEPTED_FOR_REVIEW)
        self.assertEqual(result.tenant_id, "tenant_dict")
        self.assertEqual(result.evidence_count, 1)

    def test_accepts_receipt_object(self):
        """verify_receipt works with ProofOfComputeReceipt object."""
        job = create_job(requested_action="x", tenant_id="tenant_obj")
        job.status = JobStatus.SUCCEEDED
        job.policy_flags.dry_run_mode = False
        job.evidence_refs = ["obj_evidence.txt"]

        receipt_result = create_receipt_from_job(job)
        result = verify_receipt(receipt_result.receipt)

        self.assertEqual(result.decision, PAVSDecision.ACCEPTED_FOR_REVIEW)
        self.assertEqual(result.tenant_id, "tenant_obj")


class TestBatchVerification(unittest.TestCase):
    """verify_receipts batch processing."""

    def test_batch_verification(self):
        """verify_receipts processes multiple receipts."""
        receipts = [
            {
                "receipt_id": "rcpt_batch_1",
                "job_id": "j_1",
                "tenant_id": "t_1",
                "verification_status": "pending_pavs",
                "evidence_refs": ["e1.txt"],
            },
            {
                "receipt_id": "rcpt_batch_2",
                "job_id": "j_2",
                "tenant_id": "t_2",
                "verification_status": "not_required",
                "evidence_refs": [],
            },
            {
                "receipt_id": "rcpt_batch_3",
                "job_id": "j_3",
                "tenant_id": "t_3",
                "verification_status": "blocked",
                "evidence_refs": ["block.txt"],
            },
        ]

        results = verify_receipts(receipts)

        self.assertEqual(len(results), 3)
        self.assertEqual(results[0].decision, PAVSDecision.ACCEPTED_FOR_REVIEW)
        self.assertEqual(results[1].decision, PAVSDecision.NOT_REQUIRED)
        self.assertEqual(results[2].decision, PAVSDecision.BLOCKED_UPSTREAM)


class TestResultSerialization(unittest.TestCase):
    """PAVSVerificationResult serialization round-trips."""

    def test_to_dict_contains_required_fields(self):
        """to_dict includes all required fields."""
        job = create_job(requested_action="x", tenant_id="t")
        job.status = JobStatus.SUCCEEDED
        job.evidence_refs = ["e.txt"]

        receipt_result = create_receipt_from_job(job)
        result = verify_receipt(receipt_result.receipt)
        d = result.to_dict()

        self.assertIn("verification_id", d)
        self.assertIn("receipt_id", d)
        self.assertIn("job_id", d)
        self.assertIn("tenant_id", d)
        self.assertIn("decision", d)
        self.assertIn("reason_code", d)
        self.assertIn("cabr_ready", d)
        self.assertIn("payout_ready", d)
        self.assertIn("verification_complete", d)

    def test_from_dict_roundtrip(self):
        """from_dict restores result from to_dict."""
        job = create_job(requested_action="x", tenant_id="t_roundtrip")
        job.status = JobStatus.SUCCEEDED
        job.policy_flags.dry_run_mode = False
        job.evidence_refs = ["round.txt", "trip.txt"]

        receipt_result = create_receipt_from_job(job)
        result = verify_receipt(receipt_result.receipt)
        d = result.to_dict()
        restored = PAVSVerificationResult.from_dict(d)

        self.assertEqual(restored.verification_id, result.verification_id)
        self.assertEqual(restored.receipt_id, result.receipt_id)
        self.assertEqual(restored.decision, PAVSDecision.ACCEPTED_FOR_REVIEW)
        self.assertEqual(restored.evidence_count, 2)
        self.assertFalse(restored.cabr_ready)
        self.assertFalse(restored.payout_ready)


class TestUnknownVerificationStatus(unittest.TestCase):
    """Unknown verification_status values are rejected."""

    def test_unknown_status_rejected(self):
        """Receipt with unknown verification_status is rejected."""
        receipt_dict = {
            "receipt_id": "rcpt_unknown_status",
            "job_id": "j_unknown",
            "tenant_id": "t_unknown",
            "verification_status": "some_invalid_status",
            "evidence_refs": ["x.txt"],
        }

        result = verify_receipt(receipt_dict)

        self.assertEqual(result.decision, PAVSDecision.REJECTED_INVALID_STATUS)
        self.assertEqual(result.reason_code, PAVSReasonCode.REJECTED_UNKNOWN_STATUS)


if __name__ == "__main__":
    unittest.main(verbosity=2)
