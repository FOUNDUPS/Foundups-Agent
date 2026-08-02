#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E2E Integration Test: OpenClaw → FoundUpJob → WRE → Hermes → FAM → pAVS

Verifies the complete typed seam exists for FoundUpJob orchestration.

WSP 97 Verification:
  - No raw chat sent to Hermes (typed FoundUpJob only)
  - dry_run mode propagates through entire pipeline
  - evidence_refs flow from Hermes → Receipt → pAVS
  - Truth boundaries preserved: cabr_ready=False, payout_ready=False

WSP Compliance:
  WSP 11  : Interface contract verified across module boundaries
  WSP 50  : Pre-action validation at each seam
  WSP 77  : Worker coordination via typed job
  WSP 97  : Truthful status/evidence preserved end-to-end

NAVIGATION:
  -> Tests: foundup_job_contract.py, foundup_job_router.py,
            hermes_foundup_job_executor.py, proof_of_compute_receipt.py,
            pavs_verification_seam.py
"""

from __future__ import annotations

from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

# W2: Contract (single source of truth)
from modules.communication.moltbot_bridge.src.foundup_job_contract import (
    CANONICAL_ACTIONS,
    FoundUpJob,
    JobStatus,
    PolicyFlags,
    StatusReasonCode,
    create_job,
    is_supported_action,
)

# W5: WRE Router
from modules.infrastructure.wre_core.src.foundup_job_router import (
    RouteEnvelope,
    RouteStatus,
    TargetBackend,
    route_foundup_job,
)

# W4: Hermes Executor
from modules.foundups.agent.src.hermes_foundup_job_executor import (
    HermesJobExecutionResult,
    SUPPORTED_ACTIONS as HERMES_SUPPORTED_ACTIONS,
    execute_foundup_job,
)

# W6: FAM Receipt
from modules.communication.moltbot_bridge.src.proof_of_compute_receipt import (
    ProofOfComputeReceipt,
    ReceiptResult,
    VerificationStatus,
    create_receipt_from_job,
)

# W7: pAVS Verification
from modules.communication.moltbot_bridge.src.pavs_verification_seam import (
    PAVSDecision,
    PAVSReasonCode,
    PAVSVerificationResult,
    verify_receipt,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_hermes_success() -> Dict[str, Any]:
    """Mock successful Hermes extraction result."""
    return {
        "success": True,
        "source_module": "modules/foundups/test_module",
        "target_repo": "FOUNDUPS/test_module",
        "boundary_analysis": {
            "product_files": 5,
            "core_dependencies": 2,
            "adapters_needed": ["wre_adapter"],
        },
        "exfoliation_gate": {
            "passed": True,
            "checks": {
                "module_boundary_clear": True,
                "contracts_explicit": True,
                "runtime_testable": True,
                "deploy_surface_understood": True,
                "shared_deps_adapter_level": True,
                "claw_can_participate": True,
            },
        },
        "adapters": {"adapters_created": ["adapters/wre_adapter.py"], "dry_run": True},
        "manifest": {"foundup_id": "test_module", "signature": "e2e_sig"},
        "dry_run": True,
    }


# ---------------------------------------------------------------------------
# E2E Test: Full Seam Verification
# ---------------------------------------------------------------------------


class TestE2EFoundUpJobSeam:
    """E2E tests verifying the complete typed seam."""

    @patch("modules.foundups.agent.src.hermes_adapter.HermesFoundUpBuilder")
    def test_e2e_extract_foundup_success_path(
        self,
        mock_builder_class: MagicMock,
        mock_hermes_success: Dict[str, Any],
    ) -> None:
        """
        E2E: extract_foundup success path through all components.

        OpenClaw Intent
          → FoundUpJob (QUEUED, canonical action)
          → WRE Router (ROUTED to HERMES_BUILDER)
          → Hermes Executor (SUCCEEDED)
          → FAM Receipt (PENDING_PAVS)
          → pAVS Verifier (ACCEPTED_FOR_REVIEW)

        Proves:
          - No raw chat sent (typed job only)
          - WSP 97 truth preserved (dry_run, cabr_ready=False, payout_ready=False)
        """
        # === Step 1: OpenClaw creates typed FoundUpJob ===
        job = create_job(
            tenant_id="012",
            requested_action="extract_foundup",
            foundup_id="modules/foundups/test_module",
            intent_id="openclaw_session_abc123",
            payload={
                "module_path": "modules/foundups/test_module",
                "target_org": "FOUNDUPS",
            },
        )

        # Verify: Job uses canonical action (not raw chat)
        assert job.requested_action == "extract_foundup"
        assert is_supported_action(job.requested_action)
        assert job.requested_action in CANONICAL_ACTIONS
        assert job.status == JobStatus.QUEUED

        # === Step 2: WRE routes to Hermes ===
        envelope: RouteEnvelope = route_foundup_job(job)

        assert envelope.route_status == RouteStatus.ROUTED
        assert envelope.target_backend == TargetBackend.HERMES_BUILDER
        assert envelope.job_id == job.job_id
        assert envelope.tenant_id == job.tenant_id
        assert envelope.requested_action == "extract_foundup"

        # === Step 3: Hermes executes (mocked) ===
        mock_builder = MagicMock()
        mock_builder.dry_run = True
        mock_builder.extract_foundup.return_value = mock_hermes_success
        mock_builder_class.return_value = mock_builder

        result: HermesJobExecutionResult = execute_foundup_job(job, force_dry_run=True)

        # Verify: Job reached terminal state with evidence
        assert result.job.status == JobStatus.SUCCEEDED
        assert result.job.status_reason_code == StatusReasonCode.OK_DRY_RUN_PASSED
        assert result.job.policy_flags.dry_run_mode is True
        assert len(result.job.evidence_refs) > 0
        assert result.job.worker_id == "hermes_foundup_executor"

        # === Step 4: FAM creates receipt from terminal job ===
        receipt_result: ReceiptResult = create_receipt_from_job(result.job)

        assert receipt_result.success is True
        receipt: ProofOfComputeReceipt = receipt_result.receipt

        # Verify: Receipt inherits job identity and state
        assert receipt.job_id == job.job_id
        assert receipt.tenant_id == job.tenant_id
        assert receipt.foundup_id == job.foundup_id
        assert receipt.intent_id == job.intent_id
        assert receipt.requested_action == "extract_foundup"
        assert receipt.job_status == JobStatus.SUCCEEDED
        assert receipt.verification_status == VerificationStatus.NOT_REQUIRED  # dry-run
        assert len(receipt.evidence_refs) > 0

        # === Step 5: pAVS verifies receipt ===
        pavs_result: PAVSVerificationResult = verify_receipt(receipt)

        # Verify: pAVS accepts dry-run with proper truth boundaries
        assert pavs_result.decision == PAVSDecision.NOT_REQUIRED
        assert pavs_result.reason_code == PAVSReasonCode.OK_NOT_REQUIRED
        assert pavs_result.receipt_id == receipt.receipt_id
        assert pavs_result.job_id == receipt.job_id
        assert pavs_result.tenant_id == receipt.tenant_id

        # === WSP 97 Truth Boundaries ===
        assert pavs_result.cabr_ready is False
        assert pavs_result.payout_ready is False
        assert pavs_result.verification_complete is False

    @patch("modules.foundups.agent.src.hermes_adapter.HermesFoundUpBuilder")
    def test_e2e_validate_foundup_with_evidence_accepted(
        self,
        mock_builder_class: MagicMock,
    ) -> None:
        """
        E2E: validate_foundup with real execution (not dry-run) accepted for review.

        Tests: PENDING_PAVS → ACCEPTED_FOR_REVIEW when evidence present.
        """
        # Setup mock for validation
        mock_gate = MagicMock()
        mock_gate.passed = True
        mock_gate.module_boundary_clear = True
        mock_gate.contracts_explicit = True
        mock_gate.runtime_testable = True
        mock_gate.deploy_surface_understood = True
        mock_gate.shared_deps_adapter_level = True
        mock_gate.claw_can_participate = True

        mock_analysis = MagicMock()
        mock_analysis.product_files = ["core.py", "utils.py"]
        mock_analysis.core_imports = []
        mock_analysis.adapters_needed = []
        mock_analysis.blockers = []

        mock_builder = MagicMock()
        mock_builder.dry_run = False  # NOT dry-run
        mock_builder.check_exfoliation_gate.return_value = mock_gate
        mock_builder.analyze_boundary.return_value = mock_analysis
        mock_builder_class.return_value = mock_builder

        # Create and execute
        job = create_job(
            tenant_id="012",
            requested_action="validate_foundup",
            payload={"module_path": "modules/foundups/real_module"},
        )
        job.policy_flags.dry_run_mode = False

        result = execute_foundup_job(job)

        assert result.job.status == JobStatus.SUCCEEDED
        assert result.job.status_reason_code == StatusReasonCode.OK_COMPLETED
        assert result.job.policy_flags.dry_run_mode is False

        # Create receipt - should be PENDING_PAVS (real execution)
        receipt_result = create_receipt_from_job(result.job)
        assert receipt_result.success is True
        receipt = receipt_result.receipt
        assert receipt.verification_status == VerificationStatus.PENDING_PAVS

        # Verify - should be ACCEPTED (has evidence)
        pavs_result = verify_receipt(receipt)
        assert pavs_result.decision == PAVSDecision.ACCEPTED_FOR_REVIEW
        assert pavs_result.reason_code == PAVSReasonCode.OK_EVIDENCE_PRESENT
        assert pavs_result.evidence_count > 0

        # WSP 97 truth still preserved
        assert pavs_result.cabr_ready is False
        assert pavs_result.payout_ready is False

    def test_e2e_queue_foundup_job_routes_to_openclaw(self) -> None:
        """
        E2E: queue_foundup_job routes to OPENCLAW_QUEUE (not Hermes).

        Proves: Actions are correctly separated between Hermes and OpenClaw queue.
        """
        job = create_job(
            tenant_id="012",
            requested_action="queue_foundup_job",
            payload={"deferred_action": "build_foundup"},
        )

        assert job.requested_action in CANONICAL_ACTIONS
        assert job.requested_action not in HERMES_SUPPORTED_ACTIONS

        envelope = route_foundup_job(job)

        assert envelope.route_status == RouteStatus.QUEUED
        assert envelope.target_backend == TargetBackend.OPENCLAW_QUEUE
        assert envelope.reason_code.value == "OK_QUEUED"

    def test_e2e_unsupported_action_rejected_at_route(self) -> None:
        """
        E2E: Unsupported action is rejected at routing layer.

        Proves: Invalid actions don't reach Hermes.
        """
        job = create_job(
            tenant_id="012",
            requested_action="delete_foundup",  # Not canonical
            payload={},
        )

        assert not is_supported_action(job.requested_action)

        envelope = route_foundup_job(job)

        assert envelope.route_status == RouteStatus.UNSUPPORTED
        assert envelope.target_backend == TargetBackend.NONE

    @patch("modules.foundups.agent.src.hermes_adapter.HermesFoundUpBuilder")
    def test_e2e_blocked_job_creates_blocked_receipt(
        self,
        mock_builder_class: MagicMock,
    ) -> None:
        """
        E2E: BLOCKED job → BLOCKED receipt → BLOCKED_UPSTREAM verification.
        """
        mock_builder = MagicMock()
        mock_builder.dry_run = True
        mock_builder.extract_foundup.return_value = {
            "success": False,
            "error": "exfoliation_gate_failed",
            "source_module": "modules/foundups/blocked_module",
            "exfoliation_gate": {
                "passed": False,
                "checks": {
                    "module_boundary_clear": False,
                    "contracts_explicit": False,
                    "runtime_testable": True,
                    "deploy_surface_understood": False,
                    "shared_deps_adapter_level": True,
                    "claw_can_participate": False,
                },
            },
        }
        mock_builder_class.return_value = mock_builder

        job = create_job(
            tenant_id="012",
            requested_action="extract_foundup",
            payload={"module_path": "modules/foundups/blocked_module"},
        )

        result = execute_foundup_job(job, force_dry_run=True)
        assert result.job.status == JobStatus.BLOCKED

        receipt_result = create_receipt_from_job(result.job)
        assert receipt_result.success is True
        assert receipt_result.receipt.verification_status == VerificationStatus.BLOCKED

        pavs_result = verify_receipt(receipt_result.receipt)
        assert pavs_result.decision == PAVSDecision.BLOCKED_UPSTREAM
        assert pavs_result.reason_code == PAVSReasonCode.BLOCKED_JOB_BLOCKED

    def test_e2e_identity_preserved_through_pipeline(self) -> None:
        """
        E2E: Job identity (tenant_id, foundup_id, intent_id) preserved throughout.
        """
        job = create_job(
            tenant_id="012_test",
            requested_action="validate_foundup",
            foundup_id="modules/foundups/identity_test",
            intent_id="session_xyz789",
            payload={"module_path": "modules/foundups/identity_test"},
        )

        # Route preserves identity
        envelope = route_foundup_job(job)
        assert envelope.tenant_id == "012_test"
        assert envelope.job_id == job.job_id
        assert envelope.foundup_id == "modules/foundups/identity_test"

        # Manually advance job to terminal for receipt test
        job.status = JobStatus.SUCCEEDED
        job.status_reason_code = StatusReasonCode.OK_COMPLETED
        job.evidence_refs = ["test_evidence.json"]

        # Receipt preserves identity
        receipt_result = create_receipt_from_job(job)
        receipt = receipt_result.receipt
        assert receipt.tenant_id == "012_test"
        assert receipt.job_id == job.job_id
        assert receipt.foundup_id == "modules/foundups/identity_test"
        assert receipt.intent_id == "session_xyz789"

        # pAVS preserves identity
        pavs_result = verify_receipt(receipt)
        assert pavs_result.tenant_id == "012_test"
        assert pavs_result.job_id == job.job_id


# ---------------------------------------------------------------------------
# Test: No Raw Chat to Hermes
# ---------------------------------------------------------------------------


class TestNoRawChatToHermes:
    """Verify that raw chat/text is never sent to Hermes."""

    def test_hermes_only_accepts_foundup_job(self) -> None:
        """Hermes executor only accepts FoundUpJob, not raw strings."""
        from inspect import signature

        sig = signature(execute_foundup_job)
        params = list(sig.parameters.keys())

        # First param must be "job" (FoundUpJob type)
        assert params[0] == "job"

        # No "message", "prompt", "chat", or "text" parameters
        forbidden = {"message", "prompt", "chat", "text", "query", "request_text"}
        assert not forbidden.intersection(params)

    def test_canonical_actions_are_structured(self) -> None:
        """Canonical actions are structured strings, not free-form chat."""
        for action in CANONICAL_ACTIONS:
            assert "_" in action  # verb_noun format
            assert action == action.lower()  # no mixed case
            assert " " not in action  # no spaces
            assert len(action) < 30  # bounded length


# ---------------------------------------------------------------------------
# Test: WSP 97 Truth Boundaries
# ---------------------------------------------------------------------------


class TestWSP97TruthBoundaries:
    """Verify WSP 97 truth boundaries are enforced at every seam."""

    def test_receipt_never_claims_payout(self) -> None:
        """Receipt payout_status is always NOT_EVALUATED."""
        from modules.communication.moltbot_bridge.src.proof_of_compute_receipt import (
            PayoutStatus,
        )

        job = create_job(
            tenant_id="012",
            requested_action="extract_foundup",
            payload={"module_path": "test"},
        )
        job.status = JobStatus.SUCCEEDED
        job.status_reason_code = StatusReasonCode.OK_COMPLETED

        receipt_result = create_receipt_from_job(job)
        assert receipt_result.receipt.payout_status == PayoutStatus.NOT_EVALUATED

    def test_receipt_never_claims_cabr(self) -> None:
        """Receipt cabr_status is always NOT_SUBMITTED."""
        from modules.communication.moltbot_bridge.src.proof_of_compute_receipt import (
            CABRStatus,
        )

        job = create_job(
            tenant_id="012",
            requested_action="extract_foundup",
            payload={"module_path": "test"},
        )
        job.status = JobStatus.SUCCEEDED
        job.status_reason_code = StatusReasonCode.OK_COMPLETED

        receipt_result = create_receipt_from_job(job)
        assert receipt_result.receipt.cabr_status == CABRStatus.NOT_SUBMITTED

    def test_pavs_never_claims_verification_complete(self) -> None:
        """pAVS verification_complete is always False."""
        job = create_job(
            tenant_id="012",
            requested_action="extract_foundup",
            payload={"module_path": "test"},
        )
        job.status = JobStatus.SUCCEEDED
        job.status_reason_code = StatusReasonCode.OK_COMPLETED
        job.evidence_refs = ["evidence.json"]

        receipt_result = create_receipt_from_job(job)
        pavs_result = verify_receipt(receipt_result.receipt)

        assert pavs_result.verification_complete is False
        assert pavs_result.cabr_ready is False
        assert pavs_result.payout_ready is False
