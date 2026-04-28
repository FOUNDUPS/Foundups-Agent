#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Focused tests for Proof-of-Compute Receipt contract.

Tests WSP 97 truth boundaries:
  - Terminal states (SUCCEEDED, BLOCKED, FAILED) create receipts
  - Non-terminal states (QUEUED, RUNNING) are rejected with truthful reasons
  - Identity validation (job_id, tenant_id required)
  - Evidence preservation and compute summary propagation

Worker slice: W6 (OC6_FAM_PROOF_OF_COMPUTE_RECEIPT_PHASE1)
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
    PolicyFlags,
    StatusReasonCode,
    create_job,
)
from modules.communication.moltbot_bridge.src.proof_of_compute_receipt import (
    CABRStatus,
    PayoutStatus,
    ProofOfComputeReceipt,
    VerificationStatus,
    create_receipt,
    create_receipt_from_job,
    generate_receipt_id,
)


class TestSucceededJobReceipt(unittest.TestCase):
    """SUCCEEDED job creates pending pAVS receipt."""

    def test_succeeded_job_creates_pending_pavs_receipt(self):
        """A SUCCEEDED job yields verification_status=PENDING_PAVS."""
        job = create_job(
            requested_action="create",
            tenant_id="tenant_123",
            foundup_id="f_vision_001",
            intent_id="i_test_001",
        )
        # Advance to SUCCEEDED
        job.status = JobStatus.SUCCEEDED
        job.status_reason_code = StatusReasonCode.OK_COMPLETED
        job.status_reason_human = "Job completed successfully"
        job.compute_used = 150
        job.evidence_refs = ["logs/run_001.txt", "outputs/result.json"]

        result = create_receipt_from_job(job)

        self.assertTrue(result.success)
        self.assertIsNotNone(result.receipt)
        self.assertEqual(result.receipt.verification_status, VerificationStatus.PENDING_PAVS)
        self.assertEqual(result.receipt.payout_status, PayoutStatus.NOT_EVALUATED)
        self.assertEqual(result.receipt.cabr_status, CABRStatus.NOT_SUBMITTED)
        self.assertEqual(result.receipt.job_status, JobStatus.SUCCEEDED)
        self.assertEqual(result.receipt.compute_used, 150)
        self.assertEqual(len(result.receipt.evidence_refs), 2)

    def test_succeeded_dry_run_creates_not_required_receipt(self):
        """A SUCCEEDED + dry-run job yields verification_status=NOT_REQUIRED."""
        job = create_job(
            requested_action="create",
            tenant_id="tenant_123",
        )
        job.status = JobStatus.SUCCEEDED
        job.status_reason_code = StatusReasonCode.OK_DRY_RUN_PASSED
        job.status_reason_human = "Dry run passed validation"
        job.policy_flags = PolicyFlags(dry_run_mode=True)

        result = create_receipt_from_job(job)

        self.assertTrue(result.success)
        self.assertEqual(result.receipt.verification_status, VerificationStatus.NOT_REQUIRED)

    def test_direct_factory_succeeded(self):
        """create_receipt() convenience function works for SUCCEEDED."""
        result = create_receipt(
            job_id="j_test_abc123_def456",
            tenant_id="tenant_456",
            job_status=JobStatus.SUCCEEDED,
            status_reason_code=StatusReasonCode.OK_COMPLETED,
            status_reason_human="Direct creation",
            foundup_id="f_direct_001",
            compute_used=200,
        )

        self.assertTrue(result.success)
        self.assertEqual(result.receipt.verification_status, VerificationStatus.PENDING_PAVS)
        self.assertEqual(result.receipt.compute_used, 200)


class TestBlockedJobReceipt(unittest.TestCase):
    """BLOCKED job records blocked evidence."""

    def test_blocked_job_creates_blocked_receipt(self):
        """A BLOCKED job yields verification_status=BLOCKED."""
        job = create_job(
            requested_action="execute",
            tenant_id="tenant_blocked",
            foundup_id="f_blocked_001",
        )
        job.status = JobStatus.BLOCKED
        job.status_reason_code = StatusReasonCode.BLOCKED_DEPENDENCY_MISSING
        job.status_reason_human = "Required dependency not found"
        job.evidence_refs = ["audit/block_reason.json"]

        result = create_receipt_from_job(job)

        self.assertTrue(result.success)
        self.assertEqual(result.receipt.verification_status, VerificationStatus.BLOCKED)
        self.assertEqual(result.receipt.job_status, JobStatus.BLOCKED)
        self.assertEqual(result.receipt.status_reason_code, StatusReasonCode.BLOCKED_DEPENDENCY_MISSING)
        self.assertIn("audit/block_reason.json", result.receipt.evidence_refs)

    def test_blocked_preserves_blocking_reason(self):
        """Blocking reason is preserved in receipt for audit."""
        job = create_job(requested_action="mint", tenant_id="tenant_x")
        job.status = JobStatus.BLOCKED
        job.status_reason_code = StatusReasonCode.BLOCKED_COMPUTE_EXHAUSTED
        job.status_reason_human = "Compute budget exceeded limit of 1000 units"

        result = create_receipt_from_job(job)

        self.assertTrue(result.success)
        self.assertEqual(result.receipt.status_reason_human, "Compute budget exceeded limit of 1000 units")


class TestFailedJobReceipt(unittest.TestCase):
    """FAILED job records failed evidence."""

    def test_failed_job_creates_failed_input_receipt(self):
        """A FAILED job yields verification_status=FAILED_INPUT."""
        job = create_job(
            requested_action="validate",
            tenant_id="tenant_fail",
            foundup_id="f_fail_001",
        )
        job.status = JobStatus.FAILED
        job.status_reason_code = StatusReasonCode.FAIL_TIMEOUT
        job.status_reason_human = "Execution timed out after 30s"
        job.evidence_refs = ["logs/timeout_trace.log"]

        result = create_receipt_from_job(job)

        self.assertTrue(result.success)
        self.assertEqual(result.receipt.verification_status, VerificationStatus.FAILED_INPUT)
        self.assertEqual(result.receipt.job_status, JobStatus.FAILED)
        self.assertIn("logs/timeout_trace.log", result.receipt.evidence_refs)

    def test_failed_validation_error(self):
        """FAIL_VALIDATION_ERROR reason preserved."""
        job = create_job(requested_action="create", tenant_id="tenant_v")
        job.status = JobStatus.FAILED
        job.status_reason_code = StatusReasonCode.FAIL_VALIDATION_ERROR
        job.status_reason_human = "Missing required field: name"

        result = create_receipt_from_job(job)

        self.assertTrue(result.success)
        self.assertEqual(result.receipt.status_reason_code, StatusReasonCode.FAIL_VALIDATION_ERROR)


class TestNonTerminalRejection(unittest.TestCase):
    """QUEUED and RUNNING jobs are rejected with truthful reasons."""

    def test_queued_job_rejected_with_reason(self):
        """QUEUED job cannot produce a receipt - no proof exists yet."""
        job = create_job(
            requested_action="process",
            tenant_id="tenant_q",
        )
        # Job starts as QUEUED
        self.assertEqual(job.status, JobStatus.QUEUED)

        result = create_receipt_from_job(job)

        self.assertFalse(result.success)
        self.assertIsNone(result.receipt)
        self.assertEqual(result.error_code, "JOB_NOT_STARTED")
        self.assertIn("QUEUED", result.error_message)
        self.assertIn("no proof exists until execution completes", result.error_message)

    def test_running_job_rejected_with_reason(self):
        """RUNNING job cannot produce a receipt - execution in progress."""
        job = create_job(
            requested_action="compute",
            tenant_id="tenant_r",
        )
        job.status = JobStatus.RUNNING

        result = create_receipt_from_job(job)

        self.assertFalse(result.success)
        self.assertIsNone(result.receipt)
        self.assertEqual(result.error_code, "JOB_IN_PROGRESS")
        self.assertIn("RUNNING", result.error_message)
        self.assertIn("no final proof exists yet", result.error_message)

    def test_direct_factory_rejects_queued(self):
        """create_receipt() also rejects non-terminal states."""
        result = create_receipt(
            job_id="j_test_123",
            tenant_id="tenant_123",
            job_status=JobStatus.QUEUED,
            status_reason_code=StatusReasonCode.UNKNOWN,
            status_reason_human="",
        )

        self.assertFalse(result.success)
        self.assertEqual(result.error_code, "NON_TERMINAL_STATUS")

    def test_direct_factory_rejects_running(self):
        """create_receipt() also rejects RUNNING."""
        result = create_receipt(
            job_id="j_test_456",
            tenant_id="tenant_456",
            job_status=JobStatus.RUNNING,
            status_reason_code=StatusReasonCode.UNKNOWN,
            status_reason_human="",
        )

        self.assertFalse(result.success)
        self.assertEqual(result.error_code, "NON_TERMINAL_STATUS")


class TestMissingIdentity(unittest.TestCase):
    """Jobs without identity cannot produce receipts."""

    def test_missing_job_id_rejected(self):
        """Job with empty job_id is rejected."""
        job = create_job(
            requested_action="test",
            tenant_id="tenant_123",
        )
        job.status = JobStatus.SUCCEEDED
        job.job_id = ""  # Clear job_id

        result = create_receipt_from_job(job)

        self.assertFalse(result.success)
        self.assertEqual(result.error_code, "MISSING_JOB_ID")
        self.assertIn("cannot create receipt without identity", result.error_message)

    def test_whitespace_job_id_rejected(self):
        """Job with whitespace-only job_id is rejected."""
        job = create_job(
            requested_action="test",
            tenant_id="tenant_123",
        )
        job.status = JobStatus.SUCCEEDED
        job.job_id = "   "

        result = create_receipt_from_job(job)

        self.assertFalse(result.success)
        self.assertEqual(result.error_code, "MISSING_JOB_ID")

    def test_missing_tenant_id_rejected(self):
        """Job with empty tenant_id is rejected."""
        job = create_job(
            requested_action="test",
            tenant_id="temp",
        )
        job.status = JobStatus.SUCCEEDED
        job.tenant_id = ""  # Clear tenant_id

        result = create_receipt_from_job(job)

        self.assertFalse(result.success)
        self.assertEqual(result.error_code, "MISSING_TENANT_ID")
        self.assertIn("cannot create receipt without actor scope", result.error_message)

    def test_direct_factory_validates_identity(self):
        """create_receipt() validates identity fields."""
        result = create_receipt(
            job_id="",
            tenant_id="tenant_123",
            job_status=JobStatus.SUCCEEDED,
            status_reason_code=StatusReasonCode.OK_COMPLETED,
            status_reason_human="",
        )

        self.assertFalse(result.success)
        self.assertEqual(result.error_code, "MISSING_JOB_ID")


class TestEvidenceRefs(unittest.TestCase):
    """Evidence references are preserved or handled gracefully when missing."""

    def test_evidence_refs_preserved(self):
        """Evidence refs from job are copied to receipt."""
        job = create_job(requested_action="x", tenant_id="t")
        job.status = JobStatus.SUCCEEDED
        job.evidence_refs = ["ref_a", "ref_b", "ref_c"]

        result = create_receipt_from_job(job)

        self.assertEqual(result.receipt.evidence_refs, ["ref_a", "ref_b", "ref_c"])

    def test_empty_evidence_refs_allowed(self):
        """Jobs with no evidence refs still produce receipts."""
        job = create_job(requested_action="x", tenant_id="t")
        job.status = JobStatus.SUCCEEDED
        job.evidence_refs = []

        result = create_receipt_from_job(job)

        self.assertTrue(result.success)
        self.assertEqual(result.receipt.evidence_refs, [])

    def test_evidence_refs_not_mutated(self):
        """Original job's evidence_refs are not mutated."""
        original_refs = ["a", "b"]
        job = create_job(requested_action="x", tenant_id="t")
        job.status = JobStatus.SUCCEEDED
        job.evidence_refs = original_refs

        result = create_receipt_from_job(job)
        result.receipt.evidence_refs.append("c")  # Mutate receipt

        # Original should be unchanged
        self.assertEqual(original_refs, ["a", "b"])


class TestComputeSummaryPropagation(unittest.TestCase):
    """Compute summary is extracted from job payload when present."""

    def test_explicit_compute_summary_propagated(self):
        """Payload with explicit compute_summary is preserved."""
        job = create_job(requested_action="inference", tenant_id="t")
        job.status = JobStatus.SUCCEEDED
        job.payload = {
            "compute_summary": {
                "model": "sonnet",
                "tokens_in": 1000,
                "tokens_out": 500,
                "duration_ms": 2500,
            }
        }

        result = create_receipt_from_job(job)

        self.assertIsNotNone(result.receipt.compute_summary)
        self.assertEqual(result.receipt.compute_summary["model"], "sonnet")
        self.assertEqual(result.receipt.compute_summary["tokens_in"], 1000)
        self.assertEqual(result.receipt.compute_summary["tokens_out"], 500)

    def test_compute_fields_assembled_from_payload(self):
        """Model/token fields in payload are assembled into compute_summary."""
        job = create_job(requested_action="query", tenant_id="t")
        job.status = JobStatus.SUCCEEDED
        job.payload = {
            "model": "opus",
            "tokens_in": 2000,
            "tokens_out": 1500,
            "tier": "premium",
        }

        result = create_receipt_from_job(job)

        self.assertIsNotNone(result.receipt.compute_summary)
        self.assertEqual(result.receipt.compute_summary["model"], "opus")
        self.assertEqual(result.receipt.compute_summary["tokens_in"], 2000)
        self.assertEqual(result.receipt.compute_summary["tier"], "premium")

    def test_no_compute_summary_when_fields_absent(self):
        """Payload without compute fields yields None compute_summary."""
        job = create_job(requested_action="simple", tenant_id="t")
        job.status = JobStatus.SUCCEEDED
        job.payload = {"other_field": "value"}

        result = create_receipt_from_job(job)

        self.assertIsNone(result.receipt.compute_summary)

    def test_null_payload_allowed(self):
        """Job with None payload produces receipt with no compute_summary."""
        job = create_job(requested_action="simple", tenant_id="t")
        job.status = JobStatus.SUCCEEDED
        job.payload = None

        result = create_receipt_from_job(job)

        self.assertTrue(result.success)
        self.assertIsNone(result.receipt.compute_summary)


class TestReceiptSerialization(unittest.TestCase):
    """Receipt serialization round-trips correctly."""

    def test_to_dict_contains_required_fields(self):
        """to_dict includes all required fields."""
        job = create_job(requested_action="x", tenant_id="t", foundup_id="f")
        job.status = JobStatus.SUCCEEDED
        job.compute_used = 100

        result = create_receipt_from_job(job)
        d = result.receipt.to_dict()

        self.assertIn("receipt_id", d)
        self.assertIn("job_id", d)
        self.assertIn("tenant_id", d)
        self.assertIn("verification_status", d)
        self.assertIn("payout_status", d)
        self.assertIn("cabr_status", d)
        self.assertEqual(d["verification_status"], "pending_pavs")
        self.assertEqual(d["payout_status"], "not_evaluated")
        self.assertEqual(d["cabr_status"], "not_submitted")

    def test_from_dict_roundtrip(self):
        """from_dict restores receipt from to_dict."""
        job = create_job(requested_action="round", tenant_id="trip")
        job.status = JobStatus.BLOCKED
        job.status_reason_code = StatusReasonCode.BLOCKED_COMPUTE_EXHAUSTED
        job.compute_used = 500
        job.evidence_refs = ["x", "y"]

        result = create_receipt_from_job(job)
        d = result.receipt.to_dict()
        restored = ProofOfComputeReceipt.from_dict(d)

        self.assertEqual(restored.receipt_id, result.receipt.receipt_id)
        self.assertEqual(restored.job_id, result.receipt.job_id)
        self.assertEqual(restored.verification_status, VerificationStatus.BLOCKED)
        self.assertEqual(restored.status_reason_code, StatusReasonCode.BLOCKED_COMPUTE_EXHAUSTED)
        self.assertEqual(restored.compute_used, 500)


class TestReceiptIdGeneration(unittest.TestCase):
    """Receipt ID generation is deterministic in format."""

    def test_receipt_id_format(self):
        """Receipt ID follows rcpt_{suffix}_{timestamp}_{random} format."""
        receipt_id = generate_receipt_id("j_create_abc123_def456")

        self.assertTrue(receipt_id.startswith("rcpt_"))
        parts = receipt_id.split("_")
        self.assertGreaterEqual(len(parts), 4)  # rcpt, suffix parts, timestamp, random

    def test_receipt_ids_unique(self):
        """Consecutive receipts have unique IDs."""
        ids = [generate_receipt_id("j_test_123") for _ in range(10)]
        self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
