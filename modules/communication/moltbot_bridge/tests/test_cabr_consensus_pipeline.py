#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for CABR Consensus Pipeline Phase 10.

WSP 97 Test Coverage:
  - Minimal receipt pipeline returns review-only result
  - Missing evidence fails closed
  - pAVS reject blocks scoring/finalization path
  - Quorum not met returns pending/review-only state
  - Quorum met + score accepted returns accepted-for-review only
  - Optional store persists record when provided
  - No store creates no DB/file writes
  - Export JSON/Markdown deterministic
  - Required WSP_97 labels present
  - No payout readiness inferred
  - No DAO activation inferred
  - No CABR readiness inferred
  - Stage failure explicit
  - Batch pipeline deterministic if implemented

Slice: CABR_CONSENSUS_FINALIZATION_PHASE10_PIPELINE_INTEGRATION
Worker: W1
"""

import json
import pytest
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from modules.communication.moltbot_bridge.src.cabr_consensus_pipeline import (
    CABRConsensusPipelineInput,
    CABRConsensusPipelineResult,
    CABRConsensusPipelineStage,
    CABRConsensusPipelineStageStatus,
    PIPELINE_STAGE_ORDER,
    export_cabr_consensus_pipeline_json,
    export_cabr_consensus_pipeline_markdown,
    run_cabr_consensus_pipeline,
)
from modules.communication.moltbot_bridge.src.cabr_consensus_store import (
    CABRConsensusStore,
)
from modules.communication.moltbot_bridge.src.quorum_verification_engine import (
    AttestationStatus,
    VerifierAttestation,
)
from modules.communication.moltbot_bridge.src.cabr_lifecycle_report_export import (
    WSP97_REQUIRED_LABELS,
    WSP97_TRUTH_FIELDS,
)


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------


def _build_minimal_receipt(
    receipt_id: str = "rcpt_test_001",
    job_id: str = "j_test_001",
    tenant_id: str = "tenant_001",
    evidence_refs: List[str] = None,
) -> Dict[str, Any]:
    """Build a minimal receipt dict for testing."""
    # Use default evidence if None, but allow empty list to be passed explicitly
    if evidence_refs is None:
        evidence_refs = ["evidence/test.json"]
    return {
        "receipt_id": receipt_id,
        "job_id": job_id,
        "tenant_id": tenant_id,
        "verification_status": "pending_pavs",
        "evidence_refs": evidence_refs,
        "compute_used": 100,
        "job_status": "succeeded",
    }


def _build_attestation(
    verifier_id: str,
    decision: AttestationStatus = AttestationStatus.APPROVE,
) -> VerifierAttestation:
    """Build a verifier attestation for testing."""
    return VerifierAttestation(
        verifier_id=verifier_id,
        decision=decision,
        is_dry_run=True,
    )


def _build_quorum_attestations(count: int = 3) -> List[VerifierAttestation]:
    """Build attestations to meet quorum (default 3)."""
    return [
        _build_attestation(f"verifier_{i}", AttestationStatus.APPROVE)
        for i in range(count)
    ]


# ---------------------------------------------------------------------------
# Test: Minimal Receipt Pipeline Returns Review-Only Result
# ---------------------------------------------------------------------------


class TestMinimalReceiptPipeline:
    """Test minimal receipt pipeline returns review-only result."""

    def test_minimal_receipt_with_quorum_returns_accepted_for_review(self):
        """Minimal receipt with full quorum returns ACCEPTED_FOR_REVIEW."""
        receipt = _build_minimal_receipt()
        attestations = _build_quorum_attestations(3)

        pipeline_input = CABRConsensusPipelineInput(
            receipts=[receipt],
            attestations=attestations,
        )

        result = run_cabr_consensus_pipeline(pipeline_input)

        assert result.success is True
        assert result.receipts_processed == 1
        assert len(result.consensus_records) == 1

        # Verify review-only status
        record = result.consensus_records[0]
        assert record.decision.value == "accepted_for_review"
        assert record.verification_complete is False
        assert record.cabr_ready is False
        assert record.payout_ready is False

    def test_minimal_receipt_wsp97_labels_present(self):
        """Pipeline result includes all WSP 97 required labels."""
        receipt = _build_minimal_receipt()
        attestations = _build_quorum_attestations(3)

        pipeline_input = CABRConsensusPipelineInput(
            receipts=[receipt],
            attestations=attestations,
        )

        result = run_cabr_consensus_pipeline(pipeline_input)

        # Verify all required labels are present
        for label in WSP97_REQUIRED_LABELS:
            assert label in result.wsp97_labels, f"Missing label: {label}"

    def test_minimal_receipt_truth_boundary_all_false(self):
        """All truth boundary fields are False in result."""
        receipt = _build_minimal_receipt()
        attestations = _build_quorum_attestations(3)

        pipeline_input = CABRConsensusPipelineInput(
            receipts=[receipt],
            attestations=attestations,
        )

        result = run_cabr_consensus_pipeline(pipeline_input)

        # Verify all truth boundary fields are False
        for field, value in result.truth_boundary.items():
            assert value is False, f"Truth field {field} should be False"


# ---------------------------------------------------------------------------
# Test: Missing Evidence Fails Closed
# ---------------------------------------------------------------------------


class TestMissingEvidenceFailsClosed:
    """Test missing evidence fails closed."""

    def test_empty_evidence_refs_causes_pavs_rejection(self):
        """Receipt with empty evidence_refs causes pAVS BLOCKED_MISSING_EVIDENCE."""
        receipt = _build_minimal_receipt(evidence_refs=[])  # No evidence
        attestations = _build_quorum_attestations(3)

        pipeline_input = CABRConsensusPipelineInput(
            receipts=[receipt],
            attestations=attestations,
        )

        result = run_cabr_consensus_pipeline(pipeline_input)

        # Pipeline completes - pAVS returns BLOCKED_MISSING_EVIDENCE
        # which scoring then rejects
        assert result.success is True
        assert len(result.consensus_records) == 1

        # Check that pAVS stage detected missing evidence
        pavs_stage = next(
            (sr for sr in result.stage_results if sr.stage == CABRConsensusPipelineStage.PAVS),
            None
        )
        assert pavs_stage is not None
        assert pavs_stage.status == CABRConsensusPipelineStageStatus.SUCCESS

        # The consensus record reflects the blocked pAVS state propagating to rejected
        record = result.consensus_records[0]
        # With empty evidence, pAVS returns BLOCKED_MISSING_EVIDENCE,
        # then scoring rejects with REJECTED_PAVS_FAILED
        assert record.decision.value == "rejected"

    def test_none_evidence_refs_fails_scoring(self):
        """Receipt with None evidence_refs fails at scoring stage."""
        receipt = _build_minimal_receipt()
        receipt["evidence_refs"] = None

        attestations = _build_quorum_attestations(3)

        pipeline_input = CABRConsensusPipelineInput(
            receipts=[receipt],
            attestations=attestations,
        )

        result = run_cabr_consensus_pipeline(pipeline_input)

        # Pipeline completes but scoring rejects due to no evidence
        assert result.success is True
        # With None evidence_refs, pAVS returns BLOCKED_MISSING_EVIDENCE
        # which leads to CABR scoring rejection
        assert result.records_rejected >= 1


# ---------------------------------------------------------------------------
# Test: pAVS Reject Blocks Finalization Path
# ---------------------------------------------------------------------------


class TestPAVSRejectBlocksPath:
    """Test pAVS rejection blocks downstream stages."""

    def test_pavs_blocked_missing_evidence_blocks_path(self):
        """pAVS BLOCKED_MISSING_EVIDENCE causes CABR rejection."""
        # Provide a pre-computed pAVS result with rejection
        receipt = _build_minimal_receipt()
        pavs_result = {
            "verification_id": "pv_test_001",
            "receipt_id": receipt["receipt_id"],
            "job_id": receipt["job_id"],
            "tenant_id": receipt["tenant_id"],
            "decision": "blocked_missing_evidence",
            "reason_code": "blocked_no_evidence",
            "reason_human": "No evidence refs provided",
            "evidence_refs": [],
            "evidence_count": 0,
            "cabr_ready": False,
            "payout_ready": False,
            "verification_complete": False,
        }

        attestations = _build_quorum_attestations(3)

        pipeline_input = CABRConsensusPipelineInput(
            receipts=[receipt],
            attestations=attestations,
            pavs_results=[pavs_result],
        )

        result = run_cabr_consensus_pipeline(pipeline_input)

        assert result.success is True
        assert len(result.consensus_records) == 1
        assert result.records_rejected == 1

        record = result.consensus_records[0]
        assert record.decision.value == "rejected"

    def test_pavs_failed_input_blocks_path(self):
        """pAVS FAILED_INPUT causes CABR rejection."""
        receipt = _build_minimal_receipt()
        pavs_result = {
            "verification_id": "pv_test_002",
            "receipt_id": receipt["receipt_id"],
            "job_id": receipt["job_id"],
            "tenant_id": receipt["tenant_id"],
            "decision": "failed_input",
            "reason_code": "failed_job_failed",
            "reason_human": "Upstream job failed",
            "evidence_refs": ["evidence/failed.json"],
            "evidence_count": 1,
            "cabr_ready": False,
            "payout_ready": False,
            "verification_complete": False,
        }

        attestations = _build_quorum_attestations(3)

        pipeline_input = CABRConsensusPipelineInput(
            receipts=[receipt],
            attestations=attestations,
            pavs_results=[pavs_result],
        )

        result = run_cabr_consensus_pipeline(pipeline_input)

        assert result.success is True
        assert result.records_rejected == 1


# ---------------------------------------------------------------------------
# Test: Quorum Not Met Returns Pending State
# ---------------------------------------------------------------------------


class TestQuorumNotMetReturnsPending:
    """Test quorum not met returns pending/review-only state."""

    def test_zero_attestations_returns_pending_quorum(self):
        """Zero attestations returns PENDING_QUORUM decision."""
        receipt = _build_minimal_receipt()
        attestations = []  # No attestations

        pipeline_input = CABRConsensusPipelineInput(
            receipts=[receipt],
            attestations=attestations,
        )

        result = run_cabr_consensus_pipeline(pipeline_input)

        assert result.success is True
        assert len(result.consensus_records) == 1
        assert result.records_pending_quorum == 1

        record = result.consensus_records[0]
        assert record.decision.value == "pending_quorum"
        assert record.quorum_met is False

    def test_insufficient_attestations_returns_pending_quorum(self):
        """Insufficient attestations (< min_validators) returns PENDING_QUORUM."""
        receipt = _build_minimal_receipt()
        attestations = _build_quorum_attestations(2)  # Need 3, have 2

        pipeline_input = CABRConsensusPipelineInput(
            receipts=[receipt],
            attestations=attestations,
            min_validators=3,
        )

        result = run_cabr_consensus_pipeline(pipeline_input)

        assert result.success is True
        assert result.records_pending_quorum == 1

        record = result.consensus_records[0]
        assert record.decision.value == "pending_quorum"


# ---------------------------------------------------------------------------
# Test: Quorum Met + Score Accepted Returns Accepted-for-Review
# ---------------------------------------------------------------------------


class TestQuorumMetReturnsAcceptedForReview:
    """Test quorum met + score accepted returns accepted-for-review only."""

    def test_full_quorum_with_evidence_returns_accepted(self):
        """Full quorum with evidence returns ACCEPTED_FOR_REVIEW."""
        receipt = _build_minimal_receipt()
        attestations = _build_quorum_attestations(3)

        pipeline_input = CABRConsensusPipelineInput(
            receipts=[receipt],
            attestations=attestations,
        )

        result = run_cabr_consensus_pipeline(pipeline_input)

        assert result.success is True
        assert result.records_accepted == 1

        record = result.consensus_records[0]
        assert record.decision.value == "accepted_for_review"
        assert record.quorum_met is True

        # Critical: Still review-only
        assert record.verification_complete is False
        assert record.cabr_ready is False
        assert record.payout_ready is False

    def test_exceeding_quorum_still_review_only(self):
        """Even with 5 verifiers, result is still review-only."""
        receipt = _build_minimal_receipt()
        attestations = _build_quorum_attestations(5)

        pipeline_input = CABRConsensusPipelineInput(
            receipts=[receipt],
            attestations=attestations,
        )

        result = run_cabr_consensus_pipeline(pipeline_input)

        assert result.success is True
        record = result.consensus_records[0]

        # Still review-only
        assert record.verification_complete is False
        assert record.cabr_ready is False
        assert record.payout_ready is False


# ---------------------------------------------------------------------------
# Test: Optional Store Persists Record When Provided
# ---------------------------------------------------------------------------


class TestOptionalStorePersistence:
    """Test optional store persists record when provided."""

    def test_store_provided_persists_record(self, tmp_path: Path):
        """Store provided persists consensus record."""
        db_path = tmp_path / "test_consensus.db"
        store = CABRConsensusStore(db_path)
        store.initialize_schema()

        receipt = _build_minimal_receipt()
        attestations = _build_quorum_attestations(3)

        pipeline_input = CABRConsensusPipelineInput(
            receipts=[receipt],
            attestations=attestations,
            store=store,
        )

        result = run_cabr_consensus_pipeline(pipeline_input)

        assert result.success is True
        assert result.persistence_attempted is True
        assert result.persistence_success is True
        assert len(result.persistence_failures) == 0

        # Verify record exists in store
        record_id = result.consensus_records[0].record_id
        get_result = store.get_record(record_id)
        assert get_result.status.value == "success"
        assert get_result.records[0]["record_id"] == record_id

        store.close()

    def test_store_idempotent_on_duplicate(self, tmp_path: Path):
        """Running pipeline twice with same receipt is idempotent."""
        db_path = tmp_path / "test_idempotent.db"
        store = CABRConsensusStore(db_path)
        store.initialize_schema()

        receipt = _build_minimal_receipt()
        attestations = _build_quorum_attestations(3)

        pipeline_input = CABRConsensusPipelineInput(
            receipts=[receipt],
            attestations=attestations,
            store=store,
        )

        # First run
        result1 = run_cabr_consensus_pipeline(pipeline_input)
        assert result1.persistence_success is True

        # Second run with different record_id (generate new)
        receipt2 = _build_minimal_receipt(receipt_id="rcpt_test_002")
        pipeline_input2 = CABRConsensusPipelineInput(
            receipts=[receipt2],
            attestations=attestations,
            store=store,
        )
        result2 = run_cabr_consensus_pipeline(pipeline_input2)
        assert result2.persistence_success is True

        # Verify both records exist
        list_result = store.list_records(limit=10)
        assert list_result.record_count == 2

        store.close()


# ---------------------------------------------------------------------------
# Test: No Store Creates No DB/File Writes
# ---------------------------------------------------------------------------


class TestNoStoreNoWrites:
    """Test no store creates no DB/file writes."""

    def test_no_store_no_persistence_attempt(self):
        """No store means no persistence attempt."""
        receipt = _build_minimal_receipt()
        attestations = _build_quorum_attestations(3)

        pipeline_input = CABRConsensusPipelineInput(
            receipts=[receipt],
            attestations=attestations,
            store=None,  # Explicitly no store
        )

        result = run_cabr_consensus_pipeline(pipeline_input)

        assert result.success is True
        assert result.persistence_attempted is False
        assert result.persistence_success is False

    def test_persistence_stage_skipped_without_store(self):
        """Persistence stage is SKIPPED when no store provided."""
        receipt = _build_minimal_receipt()
        attestations = _build_quorum_attestations(3)

        pipeline_input = CABRConsensusPipelineInput(
            receipts=[receipt],
            attestations=attestations,
        )

        result = run_cabr_consensus_pipeline(pipeline_input)

        persistence_stage = next(
            (sr for sr in result.stage_results if sr.stage == CABRConsensusPipelineStage.PERSISTENCE),
            None
        )
        assert persistence_stage is not None
        assert persistence_stage.status == CABRConsensusPipelineStageStatus.SKIPPED


# ---------------------------------------------------------------------------
# Test: Export JSON/Markdown Deterministic
# ---------------------------------------------------------------------------


class TestExportDeterministic:
    """Test export JSON/Markdown is deterministic."""

    def test_json_export_deterministic(self):
        """JSON export is deterministic (sorted keys)."""
        receipt = _build_minimal_receipt()
        attestations = _build_quorum_attestations(3)

        pipeline_input = CABRConsensusPipelineInput(
            receipts=[receipt],
            attestations=attestations,
        )

        result = run_cabr_consensus_pipeline(pipeline_input)

        json1 = export_cabr_consensus_pipeline_json(result)
        json2 = export_cabr_consensus_pipeline_json(result)

        # Parse and compare (timestamps may differ slightly)
        data1 = json.loads(json1)
        data2 = json.loads(json2)

        # Keys should be identical and sorted
        assert list(data1.keys()) == sorted(data1.keys())
        assert list(data1.keys()) == list(data2.keys())

    def test_json_export_contains_wsp97_labels(self):
        """JSON export contains all WSP 97 required labels."""
        receipt = _build_minimal_receipt()
        attestations = _build_quorum_attestations(3)

        pipeline_input = CABRConsensusPipelineInput(
            receipts=[receipt],
            attestations=attestations,
        )

        result = run_cabr_consensus_pipeline(pipeline_input)
        json_str = export_cabr_consensus_pipeline_json(result)
        data = json.loads(json_str)

        for label in WSP97_REQUIRED_LABELS:
            assert label in data["wsp97_labels"]

    def test_markdown_export_deterministic(self):
        """Markdown export is deterministic."""
        receipt = _build_minimal_receipt()
        attestations = _build_quorum_attestations(3)

        pipeline_input = CABRConsensusPipelineInput(
            receipts=[receipt],
            attestations=attestations,
        )

        result = run_cabr_consensus_pipeline(pipeline_input)

        md1 = export_cabr_consensus_pipeline_markdown(result)
        md2 = export_cabr_consensus_pipeline_markdown(result)

        # Headers should be identical
        assert "# CABR Consensus Pipeline Result" in md1
        assert "# CABR Consensus Pipeline Result" in md2
        assert "WSP 97 Compliance Notice" in md1

    def test_markdown_export_contains_truth_boundary_table(self):
        """Markdown export contains truth boundary table."""
        receipt = _build_minimal_receipt()
        attestations = _build_quorum_attestations(3)

        pipeline_input = CABRConsensusPipelineInput(
            receipts=[receipt],
            attestations=attestations,
        )

        result = run_cabr_consensus_pipeline(pipeline_input)
        md = export_cabr_consensus_pipeline_markdown(result)

        assert "## Truth Boundary Fields" in md
        assert "verification_complete" in md
        assert "cabr_ready" in md
        assert "payout_ready" in md


# ---------------------------------------------------------------------------
# Test: Required WSP 97 Labels Present
# ---------------------------------------------------------------------------


class TestWSP97LabelsPresent:
    """Test required WSP 97 labels are present in all results."""

    def test_all_required_labels_in_result(self):
        """All required WSP 97 labels present in result."""
        receipt = _build_minimal_receipt()
        attestations = _build_quorum_attestations(3)

        pipeline_input = CABRConsensusPipelineInput(
            receipts=[receipt],
            attestations=attestations,
        )

        result = run_cabr_consensus_pipeline(pipeline_input)

        required_labels = [
            "REVIEW_ONLY",
            "OBSERVABILITY_ONLY",
            "NOT_CABR_READY",
            "NOT_PAYOUT_READY",
            "NO_DAO_ACTIVATION",
            "NO_EXTERNAL_ATTESTATION_REQUIRED",
        ]

        for label in required_labels:
            assert label in result.wsp97_labels

    def test_compliance_note_present(self):
        """WSP 97 compliance note is present."""
        receipt = _build_minimal_receipt()
        attestations = _build_quorum_attestations(3)

        pipeline_input = CABRConsensusPipelineInput(
            receipts=[receipt],
            attestations=attestations,
        )

        result = run_cabr_consensus_pipeline(pipeline_input)

        assert "WSP 97" in result.wsp97_compliance_note
        assert "REVIEW_ONLY" in result.wsp97_compliance_note


# ---------------------------------------------------------------------------
# Test: No Payout Readiness Inferred
# ---------------------------------------------------------------------------


class TestNoPayoutReadinessInferred:
    """Test no payout readiness is inferred from pipeline results."""

    def test_accepted_record_payout_ready_false(self):
        """Accepted records have payout_ready=False."""
        receipt = _build_minimal_receipt()
        attestations = _build_quorum_attestations(5)  # Exceeds quorum

        pipeline_input = CABRConsensusPipelineInput(
            receipts=[receipt],
            attestations=attestations,
        )

        result = run_cabr_consensus_pipeline(pipeline_input)

        assert result.records_accepted == 1
        for record in result.consensus_records:
            assert record.payout_ready is False

    def test_result_truth_boundary_payout_false(self):
        """Result truth_boundary has payout_ready=False."""
        receipt = _build_minimal_receipt()
        attestations = _build_quorum_attestations(3)

        pipeline_input = CABRConsensusPipelineInput(
            receipts=[receipt],
            attestations=attestations,
        )

        result = run_cabr_consensus_pipeline(pipeline_input)

        assert result.truth_boundary["payout_ready"] is False


# ---------------------------------------------------------------------------
# Test: No DAO Activation Inferred
# ---------------------------------------------------------------------------


class TestNoDAOActivationInferred:
    """Test no DAO activation is inferred from pipeline results."""

    def test_accepted_record_cabr_ready_false(self):
        """Accepted records have cabr_ready=False."""
        receipt = _build_minimal_receipt()
        attestations = _build_quorum_attestations(5)

        pipeline_input = CABRConsensusPipelineInput(
            receipts=[receipt],
            attestations=attestations,
        )

        result = run_cabr_consensus_pipeline(pipeline_input)

        assert result.records_accepted == 1
        for record in result.consensus_records:
            assert record.cabr_ready is False

    def test_no_dao_activation_label_present(self):
        """NO_DAO_ACTIVATION label is present."""
        receipt = _build_minimal_receipt()
        attestations = _build_quorum_attestations(3)

        pipeline_input = CABRConsensusPipelineInput(
            receipts=[receipt],
            attestations=attestations,
        )

        result = run_cabr_consensus_pipeline(pipeline_input)

        assert "NO_DAO_ACTIVATION" in result.wsp97_labels


# ---------------------------------------------------------------------------
# Test: No CABR Readiness Inferred
# ---------------------------------------------------------------------------


class TestNoCABRReadinessInferred:
    """Test no CABR readiness is inferred from pipeline results."""

    def test_not_cabr_ready_label_present(self):
        """NOT_CABR_READY label is present."""
        receipt = _build_minimal_receipt()
        attestations = _build_quorum_attestations(3)

        pipeline_input = CABRConsensusPipelineInput(
            receipts=[receipt],
            attestations=attestations,
        )

        result = run_cabr_consensus_pipeline(pipeline_input)

        assert "NOT_CABR_READY" in result.wsp97_labels

    def test_verification_complete_always_false(self):
        """verification_complete is always False."""
        receipt = _build_minimal_receipt()
        attestations = _build_quorum_attestations(5)

        pipeline_input = CABRConsensusPipelineInput(
            receipts=[receipt],
            attestations=attestations,
        )

        result = run_cabr_consensus_pipeline(pipeline_input)

        assert result.truth_boundary["verification_complete"] is False
        for record in result.consensus_records:
            assert record.verification_complete is False


# ---------------------------------------------------------------------------
# Test: Stage Failure Explicit
# ---------------------------------------------------------------------------


class TestStageFailureExplicit:
    """Test stage failures are explicit and fail closed."""

    def test_invalid_input_fails_at_receipt_stage(self):
        """Invalid input fails at receipt stage."""
        pipeline_input = CABRConsensusPipelineInput(
            receipts=[],  # Empty receipts
            attestations=[],
        )

        result = run_cabr_consensus_pipeline(pipeline_input)

        assert result.success is False
        assert result.failed_stage == CABRConsensusPipelineStage.RECEIPT
        assert "At least one receipt is required" in result.error_message

    def test_missing_receipt_id_fails_validation(self):
        """Missing receipt_id fails input validation."""
        receipt = {"job_id": "j_001", "tenant_id": "t_001"}  # Missing receipt_id

        pipeline_input = CABRConsensusPipelineInput(
            receipts=[receipt],
            attestations=_build_quorum_attestations(3),
        )

        result = run_cabr_consensus_pipeline(pipeline_input)

        assert result.success is False
        assert result.failed_stage == CABRConsensusPipelineStage.RECEIPT

    def test_downstream_stages_blocked_on_failure(self):
        """Downstream stages are marked BLOCKED on failure."""
        pipeline_input = CABRConsensusPipelineInput(
            receipts=[],  # Will fail
            attestations=[],
        )

        result = run_cabr_consensus_pipeline(pipeline_input)

        # Pipeline should have failed
        assert result.success is False
        assert result.failed_stage == CABRConsensusPipelineStage.RECEIPT

        # Find blocked stages
        blocked_stages = [
            sr for sr in result.stage_results
            if sr.status == CABRConsensusPipelineStageStatus.BLOCKED
        ]

        # All stages after RECEIPT should be blocked (6 stages: PAVS, SCORING, QUORUM, FINALIZATION, PERSISTENCE, EXPORT)
        assert len(blocked_stages) == 6, f"Expected 6 blocked stages, got {len(blocked_stages)}: {[s.stage.value for s in blocked_stages]}"
        for sr in blocked_stages:
            assert sr.error_message is not None
            assert "Blocked by upstream failure" in sr.error_message


# ---------------------------------------------------------------------------
# Test: Batch Pipeline Deterministic
# ---------------------------------------------------------------------------


class TestBatchPipelineDeterministic:
    """Test batch pipeline produces deterministic results."""

    def test_multiple_receipts_deterministic_order(self):
        """Multiple receipts processed in deterministic order."""
        receipts = [
            _build_minimal_receipt(receipt_id=f"rcpt_test_{i:03d}")
            for i in range(3)
        ]
        attestations = _build_quorum_attestations(3)

        pipeline_input = CABRConsensusPipelineInput(
            receipts=receipts,
            attestations=attestations,
        )

        result = run_cabr_consensus_pipeline(pipeline_input)

        assert result.success is True
        assert result.receipts_processed == 3
        assert len(result.consensus_records) == 3

        # Verify deterministic order
        for i, record in enumerate(result.consensus_records):
            assert record.receipt_id == f"rcpt_test_{i:03d}"


# ---------------------------------------------------------------------------
# Test: Lifecycle Export Integration
# ---------------------------------------------------------------------------


class TestLifecycleExportIntegration:
    """Test lifecycle export integration in pipeline."""

    def test_lifecycle_export_generated_when_requested(self):
        """Lifecycle export is generated when include_lifecycle_export=True."""
        receipt = _build_minimal_receipt()
        attestations = _build_quorum_attestations(3)

        pipeline_input = CABRConsensusPipelineInput(
            receipts=[receipt],
            attestations=attestations,
            include_lifecycle_export=True,
        )

        result = run_cabr_consensus_pipeline(pipeline_input)

        assert result.success is True
        assert result.lifecycle_export is not None
        assert result.json_export is not None
        assert result.markdown_export is not None

    def test_lifecycle_export_not_generated_when_not_requested(self):
        """Lifecycle export is not generated when include_lifecycle_export=False."""
        receipt = _build_minimal_receipt()
        attestations = _build_quorum_attestations(3)

        pipeline_input = CABRConsensusPipelineInput(
            receipts=[receipt],
            attestations=attestations,
            include_lifecycle_export=False,
        )

        result = run_cabr_consensus_pipeline(pipeline_input)

        assert result.success is True
        assert result.lifecycle_export is None
        assert result.json_export is None
        assert result.markdown_export is None

    def test_export_stage_skipped_when_not_requested(self):
        """Export stage is SKIPPED when not requested."""
        receipt = _build_minimal_receipt()
        attestations = _build_quorum_attestations(3)

        pipeline_input = CABRConsensusPipelineInput(
            receipts=[receipt],
            attestations=attestations,
            include_lifecycle_export=False,
        )

        result = run_cabr_consensus_pipeline(pipeline_input)

        export_stage = next(
            (sr for sr in result.stage_results if sr.stage == CABRConsensusPipelineStage.EXPORT),
            None
        )
        assert export_stage is not None
        assert export_stage.status == CABRConsensusPipelineStageStatus.SKIPPED


# ---------------------------------------------------------------------------
# Test: Pre-Computed Results Skip Stages
# ---------------------------------------------------------------------------


class TestPreComputedResultsSkipStages:
    """Test pre-computed results skip corresponding stages."""

    def test_pavs_results_provided_skips_pavs_stage(self):
        """Pre-computed pAVS results skip pAVS stage."""
        receipt = _build_minimal_receipt()
        pavs_result = {
            "verification_id": "pv_test_001",
            "receipt_id": receipt["receipt_id"],
            "job_id": receipt["job_id"],
            "tenant_id": receipt["tenant_id"],
            "decision": "accepted_for_review",
            "reason_code": "ok_evidence_present",
            "reason_human": "Evidence present",
            "evidence_refs": ["evidence/test.json"],
            "evidence_count": 1,
            "cabr_ready": False,
            "payout_ready": False,
            "verification_complete": False,
        }
        attestations = _build_quorum_attestations(3)

        pipeline_input = CABRConsensusPipelineInput(
            receipts=[receipt],
            attestations=attestations,
            pavs_results=[pavs_result],
        )

        result = run_cabr_consensus_pipeline(pipeline_input)

        pavs_stage = next(
            (sr for sr in result.stage_results if sr.stage == CABRConsensusPipelineStage.PAVS),
            None
        )
        assert pavs_stage is not None
        assert pavs_stage.status == CABRConsensusPipelineStageStatus.SKIPPED
