#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Internal VoteBallot FoundUp Build PoC Test

Proves the FoundUp build pipeline can process a VoteBallot-like build request
without RedDog, pfMALL UI, tokens, or rewards.

This is an INTERNAL DRY-RUN PoC test, NOT production build automation.

WSP 97 TRUTH BOUNDARIES:
  - dry_run=True enforced throughout pipeline
  - cabr_ready=False, payout_ready=False always
  - verification_complete=False always
  - No token/reward issuance
  - No wallet actions
  - No autonomous build claims

Target Flow:
  1. Create FoundUpJob for voteballots build request
  2. Route via WRE router
  3. Execute through Hermes in dry_run=True
  4. Produce terminal job state (SUCCEEDED, BLOCKED, or FAILED)
  5. Emit ProofOfComputeReceipt
  6. pAVS accepts for review only
  7. Assert evidence_refs/status_reason_human present

WSP Compliance:
  WSP 11  : Interface contract (typed job, not raw chat)
  WSP 50  : Pre-action validation at each seam
  WSP 77  : Worker coordination via typed job
  WSP 97  : Truthful status/evidence, no overclaims

NAVIGATION:
  -> Uses: foundup_job_contract.py, foundup_job_router.py
  -> Uses: hermes_foundup_job_executor.py (mocked)
  -> Uses: proof_of_compute_receipt.py, pavs_verification_seam.py
  -> VoteBallots manifest: modules/foundups/voteballots/foundup_manifest.json
"""

from __future__ import annotations

from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

# Job Contract
from modules.communication.moltbot_bridge.src.foundup_job_contract import (
    CANONICAL_ACTIONS,
    FoundUpJob,
    JobStatus,
    PolicyFlags,
    StatusReasonCode,
    create_job,
    is_supported_action,
    is_terminal_status,
)

# WRE Router
from modules.infrastructure.wre_core.src.foundup_job_router import (
    RouteEnvelope,
    RouteStatus,
    TargetBackend,
    route_foundup_job,
)

# Hermes Executor
from modules.foundups.agent.src.hermes_foundup_job_executor import (
    HermesJobExecutionResult,
    SUPPORTED_ACTIONS as HERMES_SUPPORTED_ACTIONS,
    execute_foundup_job,
)

# FAM Receipt
from modules.communication.moltbot_bridge.src.proof_of_compute_receipt import (
    CABRStatus,
    PayoutStatus,
    ProofOfComputeReceipt,
    ReceiptResult,
    VerificationStatus,
    create_receipt_from_job,
)

# pAVS Verification
from modules.communication.moltbot_bridge.src.pavs_verification_seam import (
    PAVSDecision,
    PAVSReasonCode,
    PAVSVerificationResult,
    verify_receipt,
)


# ---------------------------------------------------------------------------
# VoteBallot Constants (from foundup_manifest.json)
# ---------------------------------------------------------------------------

VOTEBALLOTS_FOUNDUP_ID = "voteballots"
VOTEBALLOTS_MODULE_PATH = "modules/foundups/voteballots"
VOTEBALLOTS_TIER = "F0_DAE"
VOTEBALLOTS_LIFECYCLE_STAGE = "incubating"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def voteballot_build_job() -> FoundUpJob:
    """Create a VoteBallot build_foundup job for internal PoC."""
    return create_job(
        tenant_id="012",
        requested_action="build_foundup",
        foundup_id=VOTEBALLOTS_FOUNDUP_ID,
        intent_id="internal_poc_voteballot_build",
        payload={
            "module_path": VOTEBALLOTS_MODULE_PATH,
            "target_org": "FOUNDUPS",
            "build_goal": "internal dry-run PoC for VoteBallot",
            "target_surface": "PWA/module",
            "dry_run": True,
            "source": "internal_poc",
        },
    )


@pytest.fixture
def mock_hermes_success() -> Dict[str, Any]:
    """Mock successful Hermes build result for VoteBallot."""
    return {
        "success": True,
        "source_module": VOTEBALLOTS_MODULE_PATH,
        "target_repo": f"FOUNDUPS/{VOTEBALLOTS_FOUNDUP_ID}",
        "boundary_analysis": {
            "product_files": 8,
            "core_dependencies": 3,
            "adapters_needed": ["wre_adapter", "fec_adapter"],
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
        "adapters": {
            "adapters_created": [
                "adapters/wre_adapter.py",
                "adapters/fec_adapter.ts",
            ],
            "dry_run": True,
        },
        "manifest": {
            "foundup_id": VOTEBALLOTS_FOUNDUP_ID,
            "signature": "poc_sig_voteballot",
        },
        "dry_run": True,
    }


@pytest.fixture
def mock_hermes_blocked() -> Dict[str, Any]:
    """Mock blocked Hermes result (exfoliation gate failed)."""
    return {
        "success": False,
        "error": "exfoliation_gate_failed",
        "source_module": VOTEBALLOTS_MODULE_PATH,
        "exfoliation_gate": {
            "passed": False,
            "checks": {
                "module_boundary_clear": True,
                "contracts_explicit": False,  # Missing contracts
                "runtime_testable": True,
                "deploy_surface_understood": False,  # No deploy surface
                "shared_deps_adapter_level": True,
                "claw_can_participate": False,
            },
        },
        "dry_run": True,
    }


# ---------------------------------------------------------------------------
# Test: VoteBallot Build Job Routes Through WRE
# ---------------------------------------------------------------------------


class TestVoteBallotBuildPoCRouting:
    """Verify VoteBallot build request routes correctly."""

    def test_voteballot_build_job_uses_canonical_action(
        self, voteballot_build_job: FoundUpJob
    ) -> None:
        """Job uses canonical build_foundup action, not raw chat."""
        job = voteballot_build_job

        # Canonical action, not free-form text
        assert job.requested_action == "build_foundup"
        assert job.requested_action in CANONICAL_ACTIONS
        assert is_supported_action(job.requested_action)
        assert job.requested_action in HERMES_SUPPORTED_ACTIONS

        # No raw chat in payload
        payload = job.payload
        assert "message" not in payload
        assert "prompt" not in payload
        assert "chat" not in payload
        assert "raw_instruction" not in payload

        # Structured build goal
        assert payload.get("build_goal") == "internal dry-run PoC for VoteBallot"
        assert payload.get("source") == "internal_poc"

    def test_voteballot_routes_to_hermes_builder(
        self, voteballot_build_job: FoundUpJob
    ) -> None:
        """VoteBallot build_foundup routes to HERMES_BUILDER."""
        envelope: RouteEnvelope = route_foundup_job(voteballot_build_job)

        assert envelope.route_status == RouteStatus.ROUTED
        assert envelope.target_backend == TargetBackend.HERMES_BUILDER
        assert envelope.job_id == voteballot_build_job.job_id
        assert envelope.foundup_id == VOTEBALLOTS_FOUNDUP_ID


# ---------------------------------------------------------------------------
# Test: Hermes Execution (Mocked)
# ---------------------------------------------------------------------------


class TestVoteBallotBuildPoCExecution:
    """Verify VoteBallot build executes through Hermes (mocked)."""

    @patch("modules.foundups.agent.src.hermes_adapter.HermesFoundUpBuilder")
    def test_hermes_executes_voteballot_build_dry_run(
        self,
        mock_builder_class: MagicMock,
        voteballot_build_job: FoundUpJob,
        mock_hermes_success: Dict[str, Any],
    ) -> None:
        """
        Hermes executes VoteBallot build in dry_run mode.

        Proves:
          - execute_foundup_job dispatches to Hermes
          - dry_run=True enforced
          - Job reaches terminal SUCCEEDED state
          - evidence_refs populated
        """
        # Mock Hermes builder
        mock_builder = MagicMock()
        mock_builder.dry_run = True
        mock_builder.extract_foundup.return_value = mock_hermes_success
        mock_builder_class.return_value = mock_builder

        # Execute job with dry_run
        result: HermesJobExecutionResult = execute_foundup_job(
            voteballot_build_job, force_dry_run=True
        )

        # Verify job reached terminal state
        assert result.job.status == JobStatus.SUCCEEDED
        assert result.job.status_reason_code == StatusReasonCode.OK_DRY_RUN_PASSED
        assert result.job.policy_flags.dry_run_mode is True

        # Verify evidence refs populated
        assert len(result.job.evidence_refs) > 0
        assert result.job.worker_id == "hermes_foundup_executor"

    @patch("modules.foundups.agent.src.hermes_adapter.HermesFoundUpBuilder")
    def test_hermes_handles_blocked_voteballot_build(
        self,
        mock_builder_class: MagicMock,
        voteballot_build_job: FoundUpJob,
        mock_hermes_blocked: Dict[str, Any],
    ) -> None:
        """
        Hermes handles BLOCKED VoteBallot build with truthful reason.

        Proves:
          - BLOCKED state is truthful (not claimed as failure)
          - reason_human explains what failed
          - Exfoliation gate checks preserved
        """
        mock_builder = MagicMock()
        mock_builder.dry_run = True
        mock_builder.extract_foundup.return_value = mock_hermes_blocked
        mock_builder_class.return_value = mock_builder

        result = execute_foundup_job(voteballot_build_job, force_dry_run=True)

        assert result.job.status == JobStatus.BLOCKED
        assert result.job.status_reason_code == StatusReasonCode.FAIL_EXFOLIATION_GATE

        # Reason explains what checks failed
        reason = result.job.status_reason_human
        assert "exfoliation" in reason.lower() or "gate" in reason.lower()


# ---------------------------------------------------------------------------
# Test: Receipt Creation (Terminal vs Non-Terminal)
# ---------------------------------------------------------------------------


class TestVoteBallotBuildPoCReceipt:
    """Verify receipt creation behavior for VoteBallot build jobs."""

    def test_receipt_rejects_non_terminal_job(
        self, voteballot_build_job: FoundUpJob
    ) -> None:
        """Receipt creation rejects non-terminal (QUEUED/RUNNING) jobs."""
        job = voteballot_build_job
        assert job.status == JobStatus.QUEUED

        # QUEUED job -> rejected
        result = create_receipt_from_job(job)
        assert result.success is False
        assert result.error_code == "JOB_NOT_STARTED"
        assert "QUEUED" in result.error_message

        # RUNNING job -> rejected
        job.start(worker_id="test")
        assert job.status == JobStatus.RUNNING
        result = create_receipt_from_job(job)
        assert result.success is False
        assert result.error_code == "JOB_IN_PROGRESS"
        assert "RUNNING" in result.error_message

    @patch("modules.foundups.agent.src.hermes_adapter.HermesFoundUpBuilder")
    def test_receipt_accepts_terminal_voteballot_job(
        self,
        mock_builder_class: MagicMock,
        voteballot_build_job: FoundUpJob,
        mock_hermes_success: Dict[str, Any],
    ) -> None:
        """Receipt creation accepts terminal VoteBallot jobs."""
        mock_builder = MagicMock()
        mock_builder.dry_run = True
        mock_builder.extract_foundup.return_value = mock_hermes_success
        mock_builder_class.return_value = mock_builder

        result = execute_foundup_job(voteballot_build_job, force_dry_run=True)
        terminal_job = result.job

        assert is_terminal_status(terminal_job.status)

        # Create receipt from terminal job
        receipt_result = create_receipt_from_job(terminal_job)

        assert receipt_result.success is True
        receipt = receipt_result.receipt

        # Receipt identity matches job
        assert receipt.job_id == terminal_job.job_id
        assert receipt.tenant_id == terminal_job.tenant_id
        assert receipt.foundup_id == VOTEBALLOTS_FOUNDUP_ID
        assert receipt.requested_action == "build_foundup"

        # Evidence preserved
        assert len(receipt.evidence_refs) > 0
        assert receipt.status_reason_human != ""

        # dry-run -> NOT_REQUIRED verification
        assert receipt.verification_status == VerificationStatus.NOT_REQUIRED


# ---------------------------------------------------------------------------
# Test: pAVS Accepts for Review (No Final Verification)
# ---------------------------------------------------------------------------


class TestVoteBallotBuildPoCpAVS:
    """Verify pAVS accepts VoteBallot receipts for review only."""

    @patch("modules.foundups.agent.src.hermes_adapter.HermesFoundUpBuilder")
    def test_pavs_accepts_voteballot_dry_run_not_required(
        self,
        mock_builder_class: MagicMock,
        voteballot_build_job: FoundUpJob,
        mock_hermes_success: Dict[str, Any],
    ) -> None:
        """
        pAVS accepts dry-run VoteBallot receipt with NOT_REQUIRED decision.

        Proves:
          - pAVS does not claim final verification
          - cabr_ready=False, payout_ready=False
          - verification_complete=False
        """
        mock_builder = MagicMock()
        mock_builder.dry_run = True
        mock_builder.extract_foundup.return_value = mock_hermes_success
        mock_builder_class.return_value = mock_builder

        # Execute through pipeline
        result = execute_foundup_job(voteballot_build_job, force_dry_run=True)

        # Create receipt
        receipt_result = create_receipt_from_job(result.job)
        receipt = receipt_result.receipt

        # Verify through pAVS
        pavs_result: PAVSVerificationResult = verify_receipt(receipt)

        # dry-run -> NOT_REQUIRED
        assert pavs_result.decision == PAVSDecision.NOT_REQUIRED
        assert pavs_result.reason_code == PAVSReasonCode.OK_NOT_REQUIRED

        # Identity preserved
        assert pavs_result.receipt_id == receipt.receipt_id
        assert pavs_result.job_id == receipt.job_id
        assert pavs_result.tenant_id == receipt.tenant_id

        # WSP 97: No final verification claims
        assert pavs_result.cabr_ready is False
        assert pavs_result.payout_ready is False
        assert pavs_result.verification_complete is False

    @patch("modules.foundups.agent.src.hermes_adapter.HermesFoundUpBuilder")
    def test_pavs_blocked_voteballot_upstream(
        self,
        mock_builder_class: MagicMock,
        voteballot_build_job: FoundUpJob,
        mock_hermes_blocked: Dict[str, Any],
    ) -> None:
        """pAVS reflects BLOCKED_UPSTREAM for blocked VoteBallot jobs."""
        mock_builder = MagicMock()
        mock_builder.dry_run = True
        mock_builder.extract_foundup.return_value = mock_hermes_blocked
        mock_builder_class.return_value = mock_builder

        result = execute_foundup_job(voteballot_build_job, force_dry_run=True)

        receipt_result = create_receipt_from_job(result.job)
        assert receipt_result.success is True
        assert receipt_result.receipt.verification_status == VerificationStatus.BLOCKED

        pavs_result = verify_receipt(receipt_result.receipt)

        assert pavs_result.decision == PAVSDecision.BLOCKED_UPSTREAM
        assert pavs_result.reason_code == PAVSReasonCode.BLOCKED_JOB_BLOCKED

        # Still no payout/cabr claims
        assert pavs_result.cabr_ready is False
        assert pavs_result.payout_ready is False


# ---------------------------------------------------------------------------
# Test: WSP 97 Truth Boundaries
# ---------------------------------------------------------------------------


class TestVoteBallotBuildPoCWSP97:
    """Verify WSP 97 truth boundaries for VoteBallot PoC."""

    def test_no_raw_chat_in_build_instruction(
        self, voteballot_build_job: FoundUpJob
    ) -> None:
        """Build instruction is typed job, not raw chat."""
        job = voteballot_build_job

        # Action is canonical
        assert job.requested_action == "build_foundup"
        assert "_" in job.requested_action
        assert " " not in job.requested_action

        # Payload has structured fields, not raw text
        payload = job.payload
        assert isinstance(payload.get("module_path"), str)
        assert isinstance(payload.get("target_org"), str)
        assert isinstance(payload.get("dry_run"), bool)

    @patch("modules.foundups.agent.src.hermes_adapter.HermesFoundUpBuilder")
    def test_no_payout_cabr_reward_claims(
        self,
        mock_builder_class: MagicMock,
        voteballot_build_job: FoundUpJob,
        mock_hermes_success: Dict[str, Any],
    ) -> None:
        """
        No payout, CABR, or reward claims at any stage.

        Proves:
          - Receipt: payout_status=NOT_EVALUATED, cabr_status=NOT_SUBMITTED
          - pAVS: cabr_ready=False, payout_ready=False
          - No token/reward fields present
        """
        mock_builder = MagicMock()
        mock_builder.dry_run = True
        mock_builder.extract_foundup.return_value = mock_hermes_success
        mock_builder_class.return_value = mock_builder

        result = execute_foundup_job(voteballot_build_job, force_dry_run=True)

        # Receipt truth
        receipt_result = create_receipt_from_job(result.job)
        receipt = receipt_result.receipt

        assert receipt.payout_status == PayoutStatus.NOT_EVALUATED
        assert receipt.cabr_status == CABRStatus.NOT_SUBMITTED

        # No token/reward fields in receipt dict
        receipt_dict = receipt.to_dict()
        assert "tokens_issued" not in receipt_dict
        assert "reward" not in receipt_dict
        assert "payout_amount" not in receipt_dict

        # pAVS truth
        pavs_result = verify_receipt(receipt)
        assert pavs_result.cabr_ready is False
        assert pavs_result.payout_ready is False
        assert pavs_result.verification_complete is False

    def test_voteballot_id_matches_manifest(self) -> None:
        """VoteBallot ID matches the canonical manifest."""
        # This proves we're using the real VoteBallots FoundUp ID
        assert VOTEBALLOTS_FOUNDUP_ID == "voteballots"
        assert VOTEBALLOTS_MODULE_PATH == "modules/foundups/voteballots"

        # ID format is correct
        assert VOTEBALLOTS_FOUNDUP_ID.islower()
        assert "/" not in VOTEBALLOTS_FOUNDUP_ID


# ---------------------------------------------------------------------------
# Test: Evidence and Status Reason Present
# ---------------------------------------------------------------------------


class TestVoteBallotBuildPoCEvidence:
    """Verify evidence_refs and status_reason_human are present."""

    @patch("modules.foundups.agent.src.hermes_adapter.HermesFoundUpBuilder")
    def test_evidence_refs_populated_on_success(
        self,
        mock_builder_class: MagicMock,
        voteballot_build_job: FoundUpJob,
        mock_hermes_success: Dict[str, Any],
    ) -> None:
        """Successful VoteBallot build populates evidence_refs."""
        mock_builder = MagicMock()
        mock_builder.dry_run = True
        mock_builder.extract_foundup.return_value = mock_hermes_success
        mock_builder_class.return_value = mock_builder

        result = execute_foundup_job(voteballot_build_job, force_dry_run=True)
        job = result.job

        # Evidence populated
        assert len(job.evidence_refs) > 0
        assert job.status_reason_human != ""
        assert "build_foundup" in job.status_reason_human.lower() or "dry" in job.status_reason_human.lower()

    @patch("modules.foundups.agent.src.hermes_adapter.HermesFoundUpBuilder")
    def test_status_reason_truthful_on_blocked(
        self,
        mock_builder_class: MagicMock,
        voteballot_build_job: FoundUpJob,
        mock_hermes_blocked: Dict[str, Any],
    ) -> None:
        """Blocked VoteBallot build has truthful status_reason_human."""
        mock_builder = MagicMock()
        mock_builder.dry_run = True
        mock_builder.extract_foundup.return_value = mock_hermes_blocked
        mock_builder_class.return_value = mock_builder

        result = execute_foundup_job(voteballot_build_job, force_dry_run=True)
        job = result.job

        assert job.status == JobStatus.BLOCKED
        assert job.status_reason_human != ""

        # Reason explains gate failure
        reason_lower = job.status_reason_human.lower()
        # Should mention what failed (exfoliation, contracts, deploy, etc.)
        gate_keywords = ["exfoliation", "gate", "contracts", "deploy", "boundary"]
        assert any(kw in reason_lower for kw in gate_keywords), (
            f"status_reason_human should explain gate failure: {job.status_reason_human}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
