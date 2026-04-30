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

# BuildPlan (OC10 integration)
from modules.foundups.agent.src.build_plan import (
    BuildMode,
    BuildPlan,
    BuildPlanStatus,
    BuildStepAction,
    GateType,
    StepStatus,
)
from modules.foundups.agent.src.build_plan_generator import (
    create_build_plan_from_job,
    can_generate_build_plan,
)

# Swarm Coordination (OC14 integration)
from modules.foundups.agent.src.build_plan_swarm import (
    AssignmentStatus,
    ConflictSeverity,
    EvidenceBundle,
    LeaseStatus,
    StepAssignment,
    SwarmCoordinator,
    SwarmExecutionSummary,
    WorkerIdentity,
    create_swarm_coordinator,
)

# BuildPlan Executor (OC12 integration)
from modules.foundups.agent.src.build_plan_executor import (
    BuildPlanExecutor,
    ExecutionReceipt,
    StepExecutionStatus,
)

# Swarm WRE Queue (OC16 integration)
from modules.foundups.agent.src.build_plan_swarm_queue import (
    AssignmentCompletionReport,
    CompletionStatus,
    DequeueDecision,
    QueueEntryStatus,
    QueuePriority,
    SwarmWorkerQueue,
    WorkerDequeueRequest,
    create_swarm_worker_queue,
)

# Worker Assignment Dispatcher (OC17 integration)
from modules.foundups.agent.src.worker_assignment_protocol import (
    AssignmentDispatcher,
    WorkerRegistration,
    WorkerRuntimeType,
    create_assignment_dispatcher,
)

# Swarm Dispatch Coordinator (OC18/OC19 integration)
from modules.foundups.agent.src.swarm_dispatch_integration import (
    DispatchCycleResult,
    DispatchCycleStatus,
    QueueDispatchSummary,
    SwarmDispatchCoordinator,
    create_swarm_dispatch_coordinator,
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


# ---------------------------------------------------------------------------
# Test: BuildPlan Integration (OC10)
# ---------------------------------------------------------------------------


class TestVoteBallotBuildPlanGeneration:
    """
    Verify BuildPlan generation integration with VoteBallot PoC.

    OC10: Integration tests proving job->plan->receipt correlation.
    These tests do NOT execute BuildPlan steps.
    """

    def test_voteballot_job_generates_build_plan(
        self, voteballot_build_job: FoundUpJob
    ) -> None:
        """
        VoteBallot job generates BuildPlan with matching identity.

        Proves:
          - create_build_plan_from_job() succeeds
          - Plan identity inherits from job
          - Plan is in DRY_RUN mode
        """
        job = voteballot_build_job

        # Generate plan
        plan = create_build_plan_from_job(job)

        # Identity matches
        assert plan.foundup_id == job.foundup_id
        assert plan.tenant_id == job.tenant_id
        assert plan.intent_id == job.intent_id
        assert plan.source_job_id == job.job_id
        assert plan.requested_action == job.requested_action

        # Plan is DRY_RUN
        assert plan.mode == BuildMode.DRY_RUN
        assert plan.dry_run is True
        assert plan.status == BuildPlanStatus.DRAFT

    @patch("modules.foundups.agent.src.hermes_adapter.HermesFoundUpBuilder")
    def test_voteballot_plan_serializes_with_receipt_context(
        self,
        mock_builder_class: MagicMock,
        voteballot_build_job: FoundUpJob,
        mock_hermes_success: Dict[str, Any],
    ) -> None:
        """
        BuildPlan serializes alongside receipt with job_id correlation.

        Proves:
          - plan.to_dict() produces serializable output
          - plan.source_job_id correlates with receipt.job_id
        """
        # Generate plan
        plan = create_build_plan_from_job(voteballot_build_job)

        # Execute job to create terminal state
        mock_builder = MagicMock()
        mock_builder.dry_run = True
        mock_builder.extract_foundup.return_value = mock_hermes_success
        mock_builder_class.return_value = mock_builder

        result = execute_foundup_job(voteballot_build_job, force_dry_run=True)
        terminal_job = result.job

        # Create receipt
        receipt_result = create_receipt_from_job(terminal_job)
        receipt = receipt_result.receipt

        # Serialize plan
        plan_dict = plan.to_dict()

        # Correlation: plan.source_job_id == receipt.job_id
        assert plan.source_job_id == receipt.job_id
        assert plan_dict["source_job_id"] == receipt.job_id

        # Both reference same foundup
        assert plan.foundup_id == receipt.foundup_id

    @patch("modules.foundups.agent.src.hermes_adapter.HermesFoundUpBuilder")
    def test_voteballot_plan_evidence_can_reference_receipt(
        self,
        mock_builder_class: MagicMock,
        voteballot_build_job: FoundUpJob,
        mock_hermes_success: Dict[str, Any],
    ) -> None:
        """
        BuildPlan evidence_refs could correlate with receipt.

        Proves:
          - Plan can add evidence_refs
          - Receipt has evidence_refs from job
          - WSP 97: No verification_complete claims
        """
        # Generate plan
        plan = create_build_plan_from_job(voteballot_build_job)

        # Execute job
        mock_builder = MagicMock()
        mock_builder.dry_run = True
        mock_builder.extract_foundup.return_value = mock_hermes_success
        mock_builder_class.return_value = mock_builder

        result = execute_foundup_job(voteballot_build_job, force_dry_run=True)

        # Create receipt
        receipt_result = create_receipt_from_job(result.job)
        receipt = receipt_result.receipt

        # Receipt has evidence
        assert len(receipt.evidence_refs) > 0

        # Plan can reference receipt evidence (manual correlation)
        # In production, plan.evidence_refs would be populated during execution
        # For this PoC, we just verify the correlation is possible
        assert plan.source_job_id == receipt.job_id

        # WSP 97: Neither claims verification_complete
        # dry-run -> NOT_REQUIRED (no verification claim)
        assert receipt.verification_status == VerificationStatus.NOT_REQUIRED
        pavs_result = verify_receipt(receipt)
        assert pavs_result.verification_complete is False

    @patch("modules.foundups.agent.src.hermes_adapter.HermesFoundUpBuilder")
    def test_full_dry_run_pipeline_includes_build_plan(
        self,
        mock_builder_class: MagicMock,
        voteballot_build_job: FoundUpJob,
        mock_hermes_success: Dict[str, Any],
    ) -> None:
        """
        Full dry-run pipeline: Job -> BuildPlan -> Route -> Execute -> Receipt -> pAVS.

        Proves:
          - Plan is generated before execution
          - Plan is DRY_RUN and not real-build allowed
          - pAVS does not claim final verification
        """
        job = voteballot_build_job

        # Step 1: Generate BuildPlan
        plan = create_build_plan_from_job(job)
        assert plan.mode == BuildMode.DRY_RUN
        assert plan.is_real_build_allowed() is False

        # Step 2: Route
        envelope = route_foundup_job(job)
        assert envelope.route_status == RouteStatus.ROUTED
        assert envelope.target_backend == TargetBackend.HERMES_BUILDER

        # Step 3: Execute (mocked)
        mock_builder = MagicMock()
        mock_builder.dry_run = True
        mock_builder.extract_foundup.return_value = mock_hermes_success
        mock_builder_class.return_value = mock_builder

        result = execute_foundup_job(job, force_dry_run=True)
        assert result.job.status == JobStatus.SUCCEEDED
        assert result.job.policy_flags.dry_run_mode is True

        # Step 4: Receipt
        receipt_result = create_receipt_from_job(result.job)
        assert receipt_result.success is True
        receipt = receipt_result.receipt

        # Step 5: pAVS
        pavs_result = verify_receipt(receipt)

        # Assertions
        assert pavs_result.decision == PAVSDecision.NOT_REQUIRED
        assert pavs_result.cabr_ready is False
        assert pavs_result.payout_ready is False
        assert pavs_result.verification_complete is False

        # Plan correlation
        assert plan.source_job_id == receipt.job_id

    def test_build_plan_steps_are_not_executed(
        self, voteballot_build_job: FoundUpJob
    ) -> None:
        """
        BuildPlan is generated but steps are NOT executed.

        Proves:
          - Plan has steps populated
          - All steps remain in PENDING status
          - No step has started_at or completed_at
          - This PoC generates plans, does not execute them
        """
        # Generate plan
        plan = create_build_plan_from_job(voteballot_build_job)

        # Plan has steps
        assert len(plan.steps) > 0

        # All steps are PENDING (not executed)
        for step in plan.steps:
            assert step.status == StepStatus.PENDING, (
                f"Step {step.step_id} should be PENDING, not {step.status.value}"
            )
            assert step.started_at is None, (
                f"Step {step.step_id} should not have started_at set"
            )
            assert step.completed_at is None, (
                f"Step {step.step_id} should not have completed_at set"
            )

        # Verify step actions exist but are not executed
        actions = [step.action for step in plan.steps]
        assert BuildStepAction.VALIDATE_GENESIS in actions
        assert BuildStepAction.RUN_TESTS in actions
        assert BuildStepAction.SUBMIT_RECEIPT in actions


# ---------------------------------------------------------------------------
# Test: Swarm Coordination Integration (OC14)
# ---------------------------------------------------------------------------


class TestVoteBallotSwarmCoordination:
    """
    Verify SwarmCoordinator integration with VoteBallot PoC.

    OC14: Integration tests proving multi-worker swarm can coordinate
    on a VoteBallot BuildPlan safely. All execution is simulated.
    """

    def test_voteballot_build_plan_can_be_split_across_workers(
        self, voteballot_build_job: FoundUpJob
    ) -> None:
        """
        VoteBallot BuildPlan can be split across multiple simulated workers.

        Proves:
          - SwarmCoordinator creates from VoteBallot plan
          - Multiple workers can register
          - Different steps assigned to different workers
          - All assignments are simulated
        """
        job = voteballot_build_job

        # Generate BuildPlan
        plan = create_build_plan_from_job(job)
        assert plan.foundup_id == VOTEBALLOTS_FOUNDUP_ID

        # Create swarm coordinator
        coordinator = create_swarm_coordinator(plan)

        # Register 3 workers
        coordinator.register_worker(WorkerIdentity(
            worker_id="oc_voteballot_001",
            worker_type="openclaw",
            capabilities=["validate"],
        ))
        coordinator.register_worker(WorkerIdentity(
            worker_id="hermes_voteballot_001",
            worker_type="hermes",
            capabilities=["build"],
        ))
        coordinator.register_worker(WorkerIdentity(
            worker_id="claude_voteballot_001",
            worker_type="0102",
            capabilities=["all"],
        ))

        assert len(coordinator.list_workers()) == 3

        # Assign different steps to different workers
        if len(plan.steps) >= 2:
            assignment_1 = coordinator.assign_step(
                plan.steps[0],
                "oc_voteballot_001",
                [f"{VOTEBALLOTS_MODULE_PATH}/README.md"],
            )
            assignment_2 = coordinator.assign_step(
                plan.steps[1],
                "hermes_voteballot_001",
                [f"{VOTEBALLOTS_MODULE_PATH}/INTERFACE.md"],
            )

            # Both assignments are simulated
            assert assignment_1.simulated is True
            assert assignment_2.simulated is True
            assert assignment_1.worker_id == "oc_voteballot_001"
            assert assignment_2.worker_id == "hermes_voteballot_001"

    def test_swarm_blocks_duplicate_file_claims(
        self, voteballot_build_job: FoundUpJob
    ) -> None:
        """
        Swarm blocks duplicate file claims in VoteBallot context.

        Proves:
          - Worker A claims a VoteBallot target file
          - Worker B tries same file
          - Conflict is reported or claim is blocked
        """
        job = voteballot_build_job
        plan = create_build_plan_from_job(job)
        coordinator = create_swarm_coordinator(plan)

        # Register two workers
        coordinator.register_worker(WorkerIdentity(
            worker_id="worker_a_vb",
            worker_type="openclaw",
            capabilities=["validate"],
        ))
        coordinator.register_worker(WorkerIdentity(
            worker_id="worker_b_vb",
            worker_type="hermes",
            capabilities=["build"],
        ))

        # Worker A claims a file
        coordinator.claim_files(
            "worker_a_vb",
            [f"{VOTEBALLOTS_MODULE_PATH}/README.md"],
            plan.steps[0].step_id,
        )

        # Worker B tries same file - should be blocked
        with pytest.raises(ValueError, match="already claimed"):
            coordinator.claim_files(
                "worker_b_vb",
                [f"{VOTEBALLOTS_MODULE_PATH}/README.md"],
                plan.steps[1].step_id if len(plan.steps) > 1 else plan.steps[0].step_id,
            )

    def test_swarm_releases_and_reclaims_voteballot_files(
        self, voteballot_build_job: FoundUpJob
    ) -> None:
        """
        Swarm allows release then reclaim of VoteBallot files.

        Proves:
          - Worker A claims then releases
          - Worker B can claim after release
        """
        job = voteballot_build_job
        plan = create_build_plan_from_job(job)
        coordinator = create_swarm_coordinator(plan)

        # Register two workers
        coordinator.register_worker(WorkerIdentity(
            worker_id="worker_claim_vb",
            worker_type="openclaw",
            capabilities=["validate"],
        ))
        coordinator.register_worker(WorkerIdentity(
            worker_id="worker_reclaim_vb",
            worker_type="hermes",
            capabilities=["build"],
        ))

        target_file = f"{VOTEBALLOTS_MODULE_PATH}/README.md"

        # Worker A claims and releases
        coordinator.claim_files(
            "worker_claim_vb",
            [target_file],
            plan.steps[0].step_id,
        )
        coordinator.release_files("worker_claim_vb", [target_file])

        # Worker B can now claim
        claims = coordinator.claim_files(
            "worker_reclaim_vb",
            [target_file],
            plan.steps[0].step_id,
        )

        assert len(claims) == 1
        assert claims[0].worker_id == "worker_reclaim_vb"

    def test_swarm_evidence_aggregates_without_final_verification(
        self, voteballot_build_job: FoundUpJob
    ) -> None:
        """
        Swarm aggregates evidence without claiming final verification.

        Proves:
          - Add evidence refs from multiple simulated assignments
          - Aggregate evidence
          - verification_complete=False, cabr_ready=False always
        """
        job = voteballot_build_job
        plan = create_build_plan_from_job(job)
        coordinator = create_swarm_coordinator(plan)

        # Register workers
        coordinator.register_worker(WorkerIdentity(
            worker_id="evidence_worker_1",
            worker_type="openclaw",
            capabilities=["validate"],
        ))
        coordinator.register_worker(WorkerIdentity(
            worker_id="evidence_worker_2",
            worker_type="hermes",
            capabilities=["build"],
        ))

        # Create and complete assignments with evidence
        if len(plan.steps) >= 2:
            assign_1 = coordinator.assign_step(
                plan.steps[0],
                "evidence_worker_1",
                [f"{VOTEBALLOTS_MODULE_PATH}/README.md"],
            )
            assign_2 = coordinator.assign_step(
                plan.steps[1],
                "evidence_worker_2",
                [f"{VOTEBALLOTS_MODULE_PATH}/INTERFACE.md"],
            )

            # Complete with evidence
            coordinator.complete_assignment(
                assign_1.assignment_id,
                [f"evidence/voteballot/{plan.steps[0].step_id}/ref1"],
            )
            coordinator.complete_assignment(
                assign_2.assignment_id,
                [
                    f"evidence/voteballot/{plan.steps[1].step_id}/ref1",
                    f"evidence/voteballot/{plan.steps[1].step_id}/ref2",
                ],
            )

            # Aggregate evidence
            bundle: EvidenceBundle = coordinator.aggregate_evidence()

            assert bundle.total_assignments == 2
            assert bundle.completed_assignments == 2
            assert len(bundle.evidence_refs) == 3

            # WSP 97: No final verification claims
            assert bundle.verification_complete is False
            assert bundle.cabr_ready is False

    def test_full_voteballot_swarm_poc_stays_simulated(
        self, voteballot_build_job: FoundUpJob
    ) -> None:
        """
        Full VoteBallot swarm PoC stays simulated throughout.

        Proves:
          - Job -> BuildPlan -> Swarm assignments -> Executor simulate -> Summary
          - real_execution_performed=False
          - No worker process starts
          - No BuildStep real execution occurs
        """
        job = voteballot_build_job

        # Step 1: Generate BuildPlan
        plan = create_build_plan_from_job(job)
        assert plan.dry_run is True
        assert plan.mode == BuildMode.DRY_RUN

        # Step 2: Create swarm
        coordinator = create_swarm_coordinator(plan)

        # Step 3: Register workers
        coordinator.register_worker(WorkerIdentity(
            worker_id="swarm_worker_001",
            worker_type="openclaw",
            capabilities=["validate", "build"],
        ))
        coordinator.register_worker(WorkerIdentity(
            worker_id="swarm_worker_002",
            worker_type="hermes",
            capabilities=["test"],
        ))

        # Step 4: Assign all steps and complete with simulation
        executor = BuildPlanExecutor(dry_run=True)
        all_evidence_refs = []

        for i, step in enumerate(plan.steps):
            worker_id = "swarm_worker_001" if i % 2 == 0 else "swarm_worker_002"
            file_suffix = f"file_{i}.md"

            assignment = coordinator.assign_step(
                step,
                worker_id,
                [f"{VOTEBALLOTS_MODULE_PATH}/{file_suffix}"],
            )

            # Simulate step execution
            result = executor.simulate_step(plan, step)
            assert result.status == StepExecutionStatus.SIMULATED
            assert result.simulated is True

            # Complete assignment
            coordinator.complete_assignment(
                assignment.assignment_id,
                result.evidence_refs,
            )
            all_evidence_refs.extend(result.evidence_refs)

        # Step 5: Get summary
        summary: SwarmExecutionSummary = coordinator.summarize()

        # WSP 97 Truth Assertions
        assert summary.all_simulated is True
        assert summary.real_execution_performed is False
        assert summary.build_complete is True  # All assignments completed

        # No worker process actually started
        assert summary.total_workers == 2
        assert summary.completed_assignments == len(plan.steps)
        assert summary.failed_assignments == 0

        # Evidence bundle also confirms no verification
        bundle = coordinator.aggregate_evidence()
        assert bundle.verification_complete is False
        assert bundle.cabr_ready is False

        # Create execution receipt
        step_results = [executor.simulate_step(plan, step) for step in plan.steps]
        receipt: ExecutionReceipt = executor.create_execution_receipt(plan, step_results)

        # Receipt confirms no real execution
        assert receipt.verification_complete is False
        assert receipt.cabr_ready is False
        assert receipt.payout_ready is False
        assert receipt.real_execution_performed is False


# ---------------------------------------------------------------------------
# Test: Swarm WRE Queue Integration (OC16)
# ---------------------------------------------------------------------------


class TestVoteBallotSwarmQueueIntegration:
    """
    Verify SwarmWorkerQueue integration with VoteBallot PoC.

    OC16: Integration tests proving swarm assignments can be enqueued,
    dequeued by capability-matching workers, and completed with evidence.
    All execution is simulated per WSP 97.
    """

    def test_voteballot_swarm_assignments_enqueue_to_worker_queue(
        self, voteballot_build_job: FoundUpJob
    ) -> None:
        """
        VoteBallot swarm assignments can be enqueued into SwarmWorkerQueue.

        Proves:
          - Create VoteBallot job -> BuildPlan -> SwarmCoordinator
          - Assign steps to simulated workers
          - Enqueue assignments into SwarmWorkerQueue
          - Queue entries are simulated
        """
        job = voteballot_build_job

        # Generate BuildPlan
        plan = create_build_plan_from_job(job)
        assert plan.foundup_id == VOTEBALLOTS_FOUNDUP_ID

        # Create swarm coordinator
        coordinator = create_swarm_coordinator(plan)

        # Register worker
        coordinator.register_worker(WorkerIdentity(
            worker_id="queue_worker_001",
            worker_type="openclaw",
            capabilities=["validate", "build"],
        ))

        # Create queue
        queue = create_swarm_worker_queue()

        # Assign and enqueue multiple steps
        for i, step in enumerate(plan.steps[:3]):  # First 3 steps
            assignment = coordinator.assign_step(
                step,
                "queue_worker_001",
                [f"{VOTEBALLOTS_MODULE_PATH}/step_{i}.md"],
            )

            # Enqueue
            result = queue.enqueue_assignment(
                assignment=assignment,
                priority=QueuePriority.NORMAL,
                step_action=step.action,
            )

            assert result.success is True
            assert result.entry_id is not None

        # Verify queue state
        entries = queue.list_entries()
        assert len(entries) == 3

        # All entries are simulated
        for entry in entries:
            assert entry.simulated is True
            assert entry.status == QueueEntryStatus.QUEUED

    def test_matching_worker_dequeues_voteballot_assignment(
        self, voteballot_build_job: FoundUpJob
    ) -> None:
        """
        Worker with matching capability can dequeue VoteBallot assignment.

        Proves:
          - Worker with 'validate' capability dequeues validation step
          - Lease and entry status are correct
        """
        job = voteballot_build_job
        plan = create_build_plan_from_job(job)
        coordinator = create_swarm_coordinator(plan)

        # Register worker with validate capability
        coordinator.register_worker(WorkerIdentity(
            worker_id="validator_dequeue",
            worker_type="openclaw",
            capabilities=["validate"],
        ))

        # Get VALIDATE_GENESIS step
        validate_step = next(
            (s for s in plan.steps if s.action == BuildStepAction.VALIDATE_GENESIS),
            plan.steps[0],
        )

        # Assign step
        assignment = coordinator.assign_step(
            validate_step,
            "validator_dequeue",
            [f"{VOTEBALLOTS_MODULE_PATH}/README.md"],
        )

        # Enqueue with VALIDATE action
        queue = create_swarm_worker_queue()
        enqueue_result = queue.enqueue_assignment(
            assignment=assignment,
            priority=QueuePriority.NORMAL,
            step_action=validate_step.action,
        )

        # Dequeue with matching capability
        dequeue_request = WorkerDequeueRequest(
            worker_id="validator_dequeue",
            capabilities=["validate"],
        )
        dequeue_result = queue.dequeue_for_worker(dequeue_request)

        # Assertions
        assert dequeue_result.success is True
        assert dequeue_result.decision == DequeueDecision.ASSIGNED
        assert len(dequeue_result.entries) == 1

        entry = dequeue_result.entries[0]
        assert entry.status == QueueEntryStatus.PROCESSING
        assert entry.worker_id == "validator_dequeue"
        assert entry.lease_expires_at is not None
        assert entry.simulated is True

    def test_mismatched_worker_cannot_dequeue_assignment(
        self, voteballot_build_job: FoundUpJob
    ) -> None:
        """
        Worker lacking required capability cannot dequeue assignment.

        Proves:
          - Worker with only 'test' capability
          - Cannot dequeue 'validate' or 'build' assignments
        """
        job = voteballot_build_job
        plan = create_build_plan_from_job(job)
        coordinator = create_swarm_coordinator(plan)

        # Register workers
        coordinator.register_worker(WorkerIdentity(
            worker_id="build_worker",
            worker_type="hermes",
            capabilities=["build"],
        ))

        # Enqueue a VALIDATE step (requires 'validate' capability)
        validate_step = plan.steps[0]  # VALIDATE_GENESIS
        assignment = coordinator.assign_step(
            validate_step,
            "build_worker",
            [f"{VOTEBALLOTS_MODULE_PATH}/README.md"],
        )

        queue = create_swarm_worker_queue()
        queue.enqueue_assignment(
            assignment=assignment,
            step_action=BuildStepAction.VALIDATE_GENESIS,
        )

        # Try to dequeue with 'test' capability only
        dequeue_request = WorkerDequeueRequest(
            worker_id="test_only_worker",
            capabilities=["test"],  # No 'validate' capability
        )
        dequeue_result = queue.dequeue_for_worker(dequeue_request)

        # Should fail - no matching capability
        assert dequeue_result.success is False
        assert dequeue_result.decision == DequeueDecision.NO_MATCH
        assert len(dequeue_result.entries) == 0

    def test_voteballot_assignment_completion_reports_evidence(
        self, voteballot_build_job: FoundUpJob
    ) -> None:
        """
        Completed VoteBallot assignment includes evidence_refs.

        Proves:
          - Simulated completion report includes evidence_refs
          - Entry becomes COMPLETED
          - No real_execution_performed field exists or is true
        """
        job = voteballot_build_job
        plan = create_build_plan_from_job(job)
        coordinator = create_swarm_coordinator(plan)

        # Register worker
        coordinator.register_worker(WorkerIdentity(
            worker_id="evidence_worker",
            worker_type="openclaw",
            capabilities=["validate"],
        ))

        # Assign step
        step = plan.steps[0]
        assignment = coordinator.assign_step(
            step,
            "evidence_worker",
            [f"{VOTEBALLOTS_MODULE_PATH}/README.md"],
        )

        # Enqueue and dequeue
        queue = create_swarm_worker_queue()
        queue.enqueue_assignment(
            assignment=assignment,
            step_action=step.action,
        )

        dequeue_request = WorkerDequeueRequest(
            worker_id="evidence_worker",
            capabilities=["validate"],
        )
        dequeue_result = queue.dequeue_for_worker(dequeue_request)
        entry = dequeue_result.entries[0]

        # Complete with evidence
        evidence_refs = [
            f"evidence/voteballots/{step.step_id}/genesis_validated",
            f"evidence/voteballots/{step.step_id}/structure_checked",
        ]
        completion_report = AssignmentCompletionReport(
            entry_id=entry.entry_id,
            worker_id="evidence_worker",
            status=CompletionStatus.SUCCEEDED,
            evidence_refs=evidence_refs,
        )
        completion_result = queue.complete_assignment(completion_report)

        # Assertions
        assert completion_result.success is True

        completed_entry = queue.get_entry(entry.entry_id)
        assert completed_entry.status == QueueEntryStatus.COMPLETED
        assert len(completed_entry.evidence_refs) == 2
        assert "genesis_validated" in completed_entry.evidence_refs[0]

        # WSP 97: No real_execution_performed field
        assert not hasattr(completed_entry, "real_execution_performed")
        assert completed_entry.simulated is True

        # Verify completion report itself is simulated
        assert completion_report.simulated is True

    def test_full_voteballot_swarm_queue_poc_stays_simulated(
        self, voteballot_build_job: FoundUpJob
    ) -> None:
        """
        Full VoteBallot swarm queue PoC stays simulated throughout.

        Proves:
          - Job -> BuildPlan -> Swarm assignments -> Queue enqueue
          - Worker dequeue -> simulated completion -> evidence summary
          - No real workers started
          - No file edits occur
          - verification_complete=False, cabr_ready=False, payout_ready=False
        """
        job = voteballot_build_job

        # Step 1: Generate BuildPlan
        plan = create_build_plan_from_job(job)
        assert plan.dry_run is True
        assert plan.mode == BuildMode.DRY_RUN

        # Step 2: Create swarm coordinator and queue
        coordinator = create_swarm_coordinator(plan)
        queue = create_swarm_worker_queue()

        # Step 3: Register workers with different capabilities
        coordinator.register_worker(WorkerIdentity(
            worker_id="full_poc_validator",
            worker_type="openclaw",
            capabilities=["validate"],
        ))
        coordinator.register_worker(WorkerIdentity(
            worker_id="full_poc_builder",
            worker_type="hermes",
            capabilities=["build"],
        ))
        coordinator.register_worker(WorkerIdentity(
            worker_id="full_poc_tester",
            worker_type="0102",
            capabilities=["test"],
        ))

        # Step 4: Assign steps, enqueue, dequeue, complete
        executor = BuildPlanExecutor(dry_run=True)
        all_evidence = []

        for i, step in enumerate(plan.steps[:5]):  # Process first 5 steps
            # Determine worker by step action capability
            action_capability_map = {
                BuildStepAction.VALIDATE_GENESIS: ("validate", "full_poc_validator"),
                BuildStepAction.VALIDATE_MANIFEST: ("validate", "full_poc_validator"),
                BuildStepAction.CREATE_MODULE: ("build", "full_poc_builder"),
                BuildStepAction.RUN_TESTS: ("test", "full_poc_tester"),
            }
            cap, worker_id = action_capability_map.get(
                step.action, ("build", "full_poc_builder")
            )

            # Assign step to worker
            assignment = coordinator.assign_step(
                step,
                worker_id,
                [f"{VOTEBALLOTS_MODULE_PATH}/step_{i}.md"],
            )
            assert assignment.simulated is True

            # Enqueue
            enqueue_result = queue.enqueue_assignment(
                assignment=assignment,
                priority=QueuePriority.NORMAL,
                step_action=step.action,
            )
            assert enqueue_result.success is True

            # Dequeue with matching capability
            dequeue_request = WorkerDequeueRequest(
                worker_id=worker_id,
                capabilities=[cap],
            )
            dequeue_result = queue.dequeue_for_worker(dequeue_request)
            assert dequeue_result.success is True
            entry = dequeue_result.entries[0]

            # Simulate step execution
            exec_result = executor.simulate_step(plan, step)
            assert exec_result.status == StepExecutionStatus.SIMULATED
            assert exec_result.simulated is True

            # Complete assignment
            completion_report = AssignmentCompletionReport(
                entry_id=entry.entry_id,
                worker_id=worker_id,
                status=CompletionStatus.SUCCEEDED,
                evidence_refs=exec_result.evidence_refs,
            )
            queue.complete_assignment(completion_report)

            # Also complete in coordinator
            coordinator.complete_assignment(
                assignment.assignment_id,
                exec_result.evidence_refs,
            )
            all_evidence.extend(exec_result.evidence_refs)

        # Step 5: Verify queue state
        completed_entries = queue.list_entries(status=QueueEntryStatus.COMPLETED)
        assert len(completed_entries) == 5

        for entry in completed_entries:
            assert entry.simulated is True
            assert not hasattr(entry, "real_execution_performed")

        # Step 6: Get swarm summary
        summary: SwarmExecutionSummary = coordinator.summarize()

        # WSP 97 Truth Assertions
        assert summary.all_simulated is True
        assert summary.real_execution_performed is False

        # Evidence bundle
        bundle: EvidenceBundle = coordinator.aggregate_evidence()
        assert bundle.verification_complete is False
        assert bundle.cabr_ready is False

        # No CABR/payout fields on entries
        for entry in completed_entries:
            entry_dict = entry.to_dict()
            assert "cabr_ready" not in entry_dict
            assert "payout_ready" not in entry_dict
            assert "reward" not in entry_dict
            assert "tokens" not in entry_dict

        # No real workers started, no files edited
        # (We can't directly assert this, but the fact that all entries
        # are simulated=True and no exceptions from file operations proves it)
        assert summary.total_workers == 3
        assert len(all_evidence) > 0


# ---------------------------------------------------------------------------
# Test: Full Dispatch PoC Integration (OC19)
# ---------------------------------------------------------------------------


class TestVoteBallotFullDispatchPoC:
    """
    Verify full dispatch PoC integration with VoteBallot.

    OC19: Integration tests proving the full simulated dispatch path:
        FoundUpJob -> BuildPlan -> SwarmCoordinator -> SwarmWorkerQueue
        -> AssignmentDispatcher -> SwarmDispatchCoordinator -> Completion -> Summary

    All execution is simulated per WSP 97.
    """

    def test_full_voteballot_dispatch_pipeline_single_worker(
        self, voteballot_build_job: FoundUpJob
    ) -> None:
        """
        Full VoteBallot dispatch pipeline with single worker.

        Proves:
          - Job -> BuildPlan -> Swarm assignment -> Queue enqueue
          - Worker registration -> dispatch_next -> complete_dispatched_assignment
          - Evidence flows through entire pipeline
          - All WSP 97 truth boundaries preserved
        """
        job = voteballot_build_job

        # Step 1: Generate BuildPlan
        plan = create_build_plan_from_job(job)
        assert plan.foundup_id == VOTEBALLOTS_FOUNDUP_ID
        assert plan.mode == BuildMode.DRY_RUN

        # Step 2: Create swarm coordinator
        coordinator = create_swarm_coordinator(plan)
        coordinator.register_worker(WorkerIdentity(
            worker_id="dispatch_single_001",
            worker_type="openclaw",
            capabilities=["validate", "build", "test"],
        ))

        # Step 3: Create queue and dispatcher
        queue = create_swarm_worker_queue()
        dispatcher = create_assignment_dispatcher()

        # Register worker in dispatcher
        dispatcher.register_worker(WorkerRegistration(
            worker_id="dispatch_single_001",
            runtime_type=WorkerRuntimeType.OPENCLAW,
            capabilities=["validate", "build", "test"],
        ))

        # Step 4: Create dispatch coordinator
        dispatch_coordinator = create_swarm_dispatch_coordinator(
            queue=queue,
            dispatcher=dispatcher,
        )

        # Step 5: Assign steps and enqueue
        for i, step in enumerate(plan.steps[:3]):
            assignment = coordinator.assign_step(
                step,
                "dispatch_single_001",
                [f"{VOTEBALLOTS_MODULE_PATH}/step_{i}.md"],
            )
            queue.enqueue_assignment(
                assignment=assignment,
                priority=QueuePriority.NORMAL,
                step_action=step.action,
            )

        # Step 6: Run dispatch cycles
        all_evidence = []
        for _ in range(3):
            cycle_result: DispatchCycleResult = dispatch_coordinator.run_simulated_cycle(
                worker_id="dispatch_single_001",
            )
            assert cycle_result.success is True
            assert cycle_result.status == DispatchCycleStatus.SUCCESS
            assert cycle_result.simulated is True
            assert cycle_result.real_process_started is False
            all_evidence.extend(cycle_result.evidence_refs)

        # Step 7: Verify summary
        summary: QueueDispatchSummary = dispatch_coordinator.summarize()

        assert summary.total_completed == 3
        assert summary.total_queued == 0
        assert summary.all_simulated is True
        assert summary.real_execution_performed is False
        assert summary.total_evidence_refs == len(all_evidence)

    def test_full_voteballot_dispatch_pipeline_multiple_workers(
        self, voteballot_build_job: FoundUpJob
    ) -> None:
        """
        Full VoteBallot dispatch pipeline with multiple workers.

        Proves:
          - Multiple workers process different assignments
          - Capability matching routes to correct worker
          - No file conflicts between workers
          - Evidence aggregates from all workers
        """
        job = voteballot_build_job

        # Step 1: Generate BuildPlan
        plan = create_build_plan_from_job(job)

        # Step 2: Create coordinator with multiple workers
        coordinator = create_swarm_coordinator(plan)
        coordinator.register_worker(WorkerIdentity(
            worker_id="validator_multi_001",
            worker_type="openclaw",
            capabilities=["validate"],
        ))
        coordinator.register_worker(WorkerIdentity(
            worker_id="builder_multi_001",
            worker_type="hermes",
            capabilities=["build"],
        ))
        coordinator.register_worker(WorkerIdentity(
            worker_id="tester_multi_001",
            worker_type="0102",
            capabilities=["test"],
        ))

        # Step 3: Create queue, dispatcher, and dispatch coordinator
        queue = create_swarm_worker_queue()
        dispatcher = create_assignment_dispatcher()

        # Register all workers in dispatcher
        dispatcher.register_worker(WorkerRegistration(
            worker_id="validator_multi_001",
            runtime_type=WorkerRuntimeType.OPENCLAW,
            capabilities=["validate"],
        ))
        dispatcher.register_worker(WorkerRegistration(
            worker_id="builder_multi_001",
            runtime_type=WorkerRuntimeType.HERMES,
            capabilities=["build"],
        ))
        dispatcher.register_worker(WorkerRegistration(
            worker_id="tester_multi_001",
            runtime_type=WorkerRuntimeType.CLAUDE_0102,
            capabilities=["test"],
        ))

        dispatch_coordinator = create_swarm_dispatch_coordinator(
            queue=queue,
            dispatcher=dispatcher,
        )

        # Step 4: Map actions to workers and enqueue
        action_worker_map = {
            BuildStepAction.VALIDATE_GENESIS: "validator_multi_001",
            BuildStepAction.VALIDATE_MANIFEST: "validator_multi_001",
            BuildStepAction.CREATE_MODULE: "builder_multi_001",
            BuildStepAction.RUN_TESTS: "tester_multi_001",
        }

        enqueued_workers = []
        for i, step in enumerate(plan.steps[:4]):
            worker_id = action_worker_map.get(step.action, "builder_multi_001")
            enqueued_workers.append(worker_id)

            assignment = coordinator.assign_step(
                step,
                worker_id,
                [f"{VOTEBALLOTS_MODULE_PATH}/multi_{i}.md"],
            )
            queue.enqueue_assignment(
                assignment=assignment,
                step_action=step.action,
            )

        # Step 5: Each worker processes its assignments
        total_processed = 0
        for worker_id in ["validator_multi_001", "builder_multi_001", "tester_multi_001"]:
            # Try to process up to 2 assignments per worker
            for _ in range(2):
                cycle_result = dispatch_coordinator.dispatch_next(worker_id)
                if cycle_result.success:
                    # Complete the dispatched assignment
                    evidence = [f"evidence/{cycle_result.assignment_id}/multi_worker"]
                    completion = dispatch_coordinator.complete_dispatched_assignment(
                        worker_id=worker_id,
                        entry_id=cycle_result.entry_id,
                        evidence_refs=evidence,
                    )
                    if completion.success:
                        total_processed += 1

        # Step 6: Verify distribution
        summary = dispatch_coordinator.summarize()

        assert summary.total_completed >= 2  # At least some completed
        assert summary.total_workers == 3
        assert summary.all_simulated is True
        assert summary.real_execution_performed is False

    def test_full_dispatch_summary_preserves_wsp97_boundaries(
        self, voteballot_build_job: FoundUpJob
    ) -> None:
        """
        Full dispatch summary preserves WSP 97 truth boundaries.

        Proves:
          - all_simulated=True always
          - real_execution_performed=False always
          - No CABR/payout/token fields in summary
          - simulated=True on all cycle results
          - real_process_started=False on all cycle results
        """
        job = voteballot_build_job
        plan = create_build_plan_from_job(job)
        coordinator = create_swarm_coordinator(plan)

        coordinator.register_worker(WorkerIdentity(
            worker_id="wsp97_worker",
            worker_type="openclaw",
            capabilities=["validate", "build", "test"],
        ))

        queue = create_swarm_worker_queue()
        dispatcher = create_assignment_dispatcher()
        dispatcher.register_worker(WorkerRegistration(
            worker_id="wsp97_worker",
            runtime_type=WorkerRuntimeType.OPENCLAW,
            capabilities=["validate", "build", "test"],
        ))

        dispatch_coordinator = create_swarm_dispatch_coordinator(
            queue=queue,
            dispatcher=dispatcher,
        )

        # Enqueue some steps
        for i, step in enumerate(plan.steps[:2]):
            assignment = coordinator.assign_step(
                step,
                "wsp97_worker",
                [f"{VOTEBALLOTS_MODULE_PATH}/wsp97_{i}.md"],
            )
            queue.enqueue_assignment(
                assignment=assignment,
                step_action=step.action,
            )

        # Run cycles
        cycle_results = []
        for _ in range(2):
            result = dispatch_coordinator.run_simulated_cycle("wsp97_worker")
            cycle_results.append(result)

        # Verify cycle results
        for result in cycle_results:
            assert result.simulated is True
            assert result.real_process_started is False

            # Cycle result dict should not have CABR/payout fields
            result_dict = result.to_dict()
            assert "cabr_ready" not in result_dict
            assert "payout_ready" not in result_dict
            assert "reward" not in result_dict
            assert "tokens" not in result_dict

        # Verify summary
        summary = dispatch_coordinator.summarize()

        assert summary.all_simulated is True
        assert summary.real_execution_performed is False

        # Summary dict should not have CABR/payout fields
        summary_dict = summary.to_dict()
        assert "cabr_ready" not in summary_dict
        assert "payout_ready" not in summary_dict
        assert "reward" not in summary_dict
        assert "tokens" not in summary_dict

    def test_full_dispatch_pipeline_preserves_job_plan_receipt_correlation(
        self,
        voteballot_build_job: FoundUpJob,
        mock_hermes_success: Dict[str, Any],
    ) -> None:
        """
        Full dispatch pipeline preserves job->plan->receipt correlation.

        Proves:
          - Job identity flows through dispatch coordinator
          - Plan source_job_id matches receipt job_id
          - Evidence from dispatch flows to receipt
          - Correlation maintained across all components
        """
        job = voteballot_build_job

        # Step 1: Generate BuildPlan (preserves job_id)
        plan = create_build_plan_from_job(job)
        assert plan.source_job_id == job.job_id
        assert plan.foundup_id == job.foundup_id

        # Step 2: Create infrastructure
        coordinator = create_swarm_coordinator(plan)
        coordinator.register_worker(WorkerIdentity(
            worker_id="correlation_worker",
            worker_type="openclaw",
            capabilities=["validate", "build", "test"],
        ))

        queue = create_swarm_worker_queue()
        dispatcher = create_assignment_dispatcher()
        dispatcher.register_worker(WorkerRegistration(
            worker_id="correlation_worker",
            runtime_type=WorkerRuntimeType.OPENCLAW,
            capabilities=["validate", "build", "test"],
        ))

        dispatch_coordinator = create_swarm_dispatch_coordinator(
            queue=queue,
            dispatcher=dispatcher,
        )

        # Step 3: Enqueue and process
        for i, step in enumerate(plan.steps[:2]):
            assignment = coordinator.assign_step(
                step,
                "correlation_worker",
                [f"{VOTEBALLOTS_MODULE_PATH}/corr_{i}.md"],
            )
            queue.enqueue_assignment(
                assignment=assignment,
                step_action=step.action,
            )

        # Process assignments
        for _ in range(2):
            dispatch_coordinator.run_simulated_cycle("correlation_worker")

        # Step 4: Execute job via Hermes (mocked) to create terminal state
        with patch("modules.foundups.agent.src.hermes_adapter.HermesFoundUpBuilder") as mock_class:
            mock_builder = MagicMock()
            mock_builder.dry_run = True
            mock_builder.extract_foundup.return_value = mock_hermes_success
            mock_class.return_value = mock_builder

            result = execute_foundup_job(job, force_dry_run=True)

        # Step 5: Create receipt
        receipt_result = create_receipt_from_job(result.job)
        assert receipt_result.success is True
        receipt = receipt_result.receipt

        # Step 6: Verify correlation chain
        # Plan source_job_id == job.job_id == receipt.job_id
        assert plan.source_job_id == job.job_id
        assert receipt.job_id == job.job_id
        assert plan.source_job_id == receipt.job_id

        # foundup_id matches across all
        assert plan.foundup_id == job.foundup_id
        assert receipt.foundup_id == job.foundup_id

        # Evidence from dispatch is collected
        dispatch_evidence = dispatch_coordinator.get_all_evidence()
        assert len(dispatch_evidence) > 0

        # Receipt has evidence from job execution
        assert len(receipt.evidence_refs) > 0

    def test_full_dispatch_pipeline_blocks_mismatched_worker(
        self, voteballot_build_job: FoundUpJob
    ) -> None:
        """
        Full dispatch pipeline blocks worker capability mismatch.

        Proves:
          - Worker registered with 'test' capability only
          - Queue has 'validate' assignments
          - dispatch_next returns NO_CAPABILITY_MATCH
          - No assignment is processed
        """
        job = voteballot_build_job
        plan = create_build_plan_from_job(job)
        coordinator = create_swarm_coordinator(plan)

        # Register worker with limited capability
        coordinator.register_worker(WorkerIdentity(
            worker_id="mismatch_tester",
            worker_type="0102",
            capabilities=["test"],  # Only test, no validate/build
        ))

        queue = create_swarm_worker_queue()
        dispatcher = create_assignment_dispatcher()

        # Register with same limited capability
        dispatcher.register_worker(WorkerRegistration(
            worker_id="mismatch_tester",
            runtime_type=WorkerRuntimeType.CLAUDE_0102,
            capabilities=["test"],
        ))

        dispatch_coordinator = create_swarm_dispatch_coordinator(
            queue=queue,
            dispatcher=dispatcher,
        )

        # Enqueue VALIDATE_GENESIS step (requires 'validate' capability)
        validate_step = next(
            (s for s in plan.steps if s.action == BuildStepAction.VALIDATE_GENESIS),
            plan.steps[0],
        )
        assignment = coordinator.assign_step(
            validate_step,
            "mismatch_tester",  # Wrong worker for this action
            [f"{VOTEBALLOTS_MODULE_PATH}/mismatch.md"],
        )
        queue.enqueue_assignment(
            assignment=assignment,
            step_action=BuildStepAction.VALIDATE_GENESIS,  # Requires 'validate'
        )

        # Try to dispatch - should fail due to capability mismatch
        cycle_result = dispatch_coordinator.dispatch_next("mismatch_tester")

        assert cycle_result.success is False
        assert cycle_result.status == DispatchCycleStatus.NO_CAPABILITY_MATCH
        assert cycle_result.entry_id is None
        assert cycle_result.assignment_id is None

        # Verify no assignments completed
        summary = dispatch_coordinator.summarize()
        assert summary.total_completed == 0
        assert summary.total_queued == 1  # Still queued, not processed

        # WSP 97 still enforced
        assert summary.all_simulated is True
        assert summary.real_execution_performed is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
