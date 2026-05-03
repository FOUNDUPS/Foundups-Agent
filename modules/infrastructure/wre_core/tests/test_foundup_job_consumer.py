# -*- coding: utf-8 -*-
"""
Tests for WRE FoundUpJob Consumer — Phase 1A Consumer Seam

W2/OC5 Test Coverage:
  - consume_one calls route_foundup_job before Hermes dispatch
  - HERMES_BUILDER routed job calls execute_foundup_job with dry_run=True
  - HERMES_VALIDATOR routed job calls execute_foundup_job with dry_run=True
  - unsupported/blocked route does not call Hermes
  - drain_jobs consumes multiple jobs
  - drain_openclaw_queue_once clears queue only after successful drain
  - terminal job receipt wrapper rejects non-terminal jobs truthfully

WSP Compliance:
  WSP 11  : Interface contract verified
  WSP 50  : Pre-action validation (route_foundup_job called first)
  WSP 77  : Agent coordination (WRE controls dispatch)
  WSP 97  : Truthful status (dry_run default, no overclaims)
"""

import pytest
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any
from unittest.mock import MagicMock, patch

from modules.infrastructure.wre_core.src.foundup_job_consumer import (
    FoundUpJobConsumer,
    ConsumerResult,
    get_consumer,
    drain_openclaw_queue_dry_run,
)
from modules.infrastructure.wre_core.src.foundup_job_router import (
    RouteStatus,
    TargetBackend,
)


# ---------------------------------------------------------------------------
# Mock Job Classes (duck-typed to match FoundUpJob contract)
# ---------------------------------------------------------------------------


class MockJobStatus(str, Enum):
    """Mock status enum matching FoundUpJob contract."""

    QUEUED = "queued"
    RUNNING = "running"
    BLOCKED = "blocked"
    FAILED = "failed"
    SUCCEEDED = "succeeded"


@dataclass
class MockPolicyFlags:
    """Mock policy flags matching FoundUpJob contract."""

    security_gate_checked: bool = False
    security_gate_passed: bool = False
    dry_run_mode: bool = True

    def to_dict(self) -> Dict[str, bool]:
        return {
            "security_gate_checked": self.security_gate_checked,
            "security_gate_passed": self.security_gate_passed,
            "dry_run_mode": self.dry_run_mode,
        }


@dataclass
class MockFoundUpJob:
    """Mock FoundUpJob for testing consumer."""

    job_id: str
    tenant_id: str
    requested_action: str
    status: MockJobStatus = MockJobStatus.QUEUED
    foundup_id: Optional[str] = None
    policy_flags: Optional[MockPolicyFlags] = None
    payload: Optional[Dict[str, Any]] = None
    evidence_refs: list = None

    def __post_init__(self):
        if self.evidence_refs is None:
            self.evidence_refs = []
        if self.policy_flags is None:
            self.policy_flags = MockPolicyFlags()


# ---------------------------------------------------------------------------
# Test: consume_one calls route_foundup_job before Hermes
# ---------------------------------------------------------------------------


class TestConsumeOneRoutesFirst:
    """Test that consume_one calls route_foundup_job before dispatching."""

    @patch("modules.infrastructure.wre_core.src.foundup_job_consumer.route_foundup_job")
    def test_consume_one_calls_route_first(self, mock_route):
        """consume_one must call route_foundup_job before any dispatch."""
        # Setup mock to return blocked (so no Hermes dispatch)
        mock_envelope = MagicMock()
        mock_envelope.route_status = RouteStatus.BLOCKED
        mock_envelope.target_backend = TargetBackend.NONE
        mock_envelope.reason_human = "Blocked for test"
        mock_envelope.job_id = "job_001"
        mock_route.return_value = mock_envelope

        job = MockFoundUpJob(
            job_id="job_001",
            tenant_id="tenant_test",
            requested_action="build_foundup",
        )

        consumer = FoundUpJobConsumer(dry_run=True)
        result = consumer.consume_one(job)

        # route_foundup_job must have been called
        mock_route.assert_called_once_with(job)
        # Result should not be dispatched (blocked)
        assert result.dispatched is False
        assert result.route_status == RouteStatus.BLOCKED


# ---------------------------------------------------------------------------
# Test: HERMES_BUILDER/VALIDATOR routed jobs call execute_foundup_job
# ---------------------------------------------------------------------------


class TestHermesDispatch:
    """Test that routed jobs dispatch to WRE Hermes executor."""

    @patch("modules.infrastructure.wre_core.src.foundup_job_consumer.route_foundup_job")
    @patch(
        "modules.infrastructure.wre_core.src.hermes_job_executor.execute_foundup_job"
    )
    def test_hermes_builder_dispatches_to_wre_executor(
        self, mock_execute, mock_route
    ):
        """HERMES_BUILDER routed job dispatches to WRE executor."""
        # Setup mock route envelope
        mock_envelope = MagicMock()
        mock_envelope.route_status = RouteStatus.ROUTED
        mock_envelope.target_backend = TargetBackend.HERMES_BUILDER
        mock_envelope.reason_human = "Routed to hermes_builder"
        mock_envelope.job_id = "job_builder"
        mock_route.return_value = mock_envelope

        # Setup mock WRE HermesDelegationResult
        mock_hermes_result = MagicMock()
        mock_hermes_result.status.value = "SIMULATED"
        mock_hermes_result.checkpoint_state = "SIMULATED"
        mock_hermes_result.checkpoint_result = None
        mock_hermes_result.checkpoint_blocker = None
        mock_hermes_result.checkpoint_next_action = None
        mock_hermes_result.evidence_path = ".hermes_evidence/job_builder"
        mock_hermes_result.real_execution_performed = False
        mock_execute.return_value = mock_hermes_result

        job = MockFoundUpJob(
            job_id="job_builder",
            tenant_id="tenant_test",
            requested_action="build_foundup",
        )

        consumer = FoundUpJobConsumer(dry_run=True)
        result = consumer.consume_one(job)

        # WRE executor called with job only (no force_dry_run param)
        mock_execute.assert_called_once_with(job)
        assert result.dispatched is True
        assert result.target_backend == TargetBackend.HERMES_BUILDER
        # Phase 1C checkpoint fields populated
        assert result.checkpoint_state == "SIMULATED"
        assert result.evidence_path == ".hermes_evidence/job_builder"

    @patch("modules.infrastructure.wre_core.src.foundup_job_consumer.route_foundup_job")
    @patch(
        "modules.infrastructure.wre_core.src.hermes_job_executor.execute_foundup_job"
    )
    def test_hermes_validator_dispatches_to_wre_executor(
        self, mock_execute, mock_route
    ):
        """HERMES_VALIDATOR routed job dispatches to WRE executor."""
        mock_envelope = MagicMock()
        mock_envelope.route_status = RouteStatus.ROUTED
        mock_envelope.target_backend = TargetBackend.HERMES_VALIDATOR
        mock_envelope.reason_human = "Routed to hermes_validator"
        mock_envelope.job_id = "job_validator"
        mock_route.return_value = mock_envelope

        mock_hermes_result = MagicMock()
        mock_hermes_result.status.value = "SIMULATED"
        mock_hermes_result.checkpoint_state = "SIMULATED"
        mock_hermes_result.checkpoint_result = None
        mock_hermes_result.checkpoint_blocker = None
        mock_hermes_result.checkpoint_next_action = None
        mock_hermes_result.evidence_path = ".hermes_evidence/job_validator"
        mock_hermes_result.real_execution_performed = False
        mock_execute.return_value = mock_hermes_result

        job = MockFoundUpJob(
            job_id="job_validator",
            tenant_id="tenant_test",
            requested_action="validate_foundup",
        )

        consumer = FoundUpJobConsumer(dry_run=True)
        result = consumer.consume_one(job)

        mock_execute.assert_called_once_with(job)
        assert result.dispatched is True
        assert result.target_backend == TargetBackend.HERMES_VALIDATOR
        assert result.checkpoint_state == "SIMULATED"

    @patch("modules.infrastructure.wre_core.src.foundup_job_consumer.route_foundup_job")
    @patch(
        "modules.infrastructure.wre_core.src.hermes_job_executor.execute_foundup_job"
    )
    def test_wre_executor_uses_singleton_dry_run(self, mock_execute, mock_route):
        """WRE executor uses singleton with consumer's dry_run setting."""
        mock_envelope = MagicMock()
        mock_envelope.route_status = RouteStatus.ROUTED
        mock_envelope.target_backend = TargetBackend.HERMES_BUILDER
        mock_envelope.reason_human = "Routed"
        mock_envelope.job_id = "job_real"
        mock_route.return_value = mock_envelope

        mock_hermes_result = MagicMock()
        mock_hermes_result.status.value = "SIMULATED"
        mock_hermes_result.checkpoint_state = "SIMULATED"
        mock_hermes_result.checkpoint_result = None
        mock_hermes_result.checkpoint_blocker = None
        mock_hermes_result.checkpoint_next_action = None
        mock_hermes_result.evidence_path = ".hermes_evidence/job_real"
        mock_hermes_result.real_execution_performed = False
        mock_execute.return_value = mock_hermes_result

        job = MockFoundUpJob(
            job_id="job_real",
            tenant_id="tenant_test",
            requested_action="build_foundup",
        )

        # Consumer dry_run setting affects singleton, not per-call param
        consumer = FoundUpJobConsumer(dry_run=False)
        result = consumer.consume_one(job)

        # WRE executor called with job only
        mock_execute.assert_called_once_with(job)
        assert result.dispatched is True


# ---------------------------------------------------------------------------
# Test: Unsupported/blocked routes do not call Hermes
# ---------------------------------------------------------------------------


class TestNoHermesForBlockedRoutes:
    """Test that blocked/unsupported routes do not dispatch to Hermes."""

    @patch("modules.infrastructure.wre_core.src.foundup_job_consumer.route_foundup_job")
    @patch(
        "modules.infrastructure.wre_core.src.hermes_job_executor.execute_foundup_job"
    )
    def test_unsupported_action_no_hermes_dispatch(self, mock_execute, mock_route):
        """Unsupported action does not call execute_foundup_job."""
        mock_envelope = MagicMock()
        mock_envelope.route_status = RouteStatus.UNSUPPORTED
        mock_envelope.target_backend = TargetBackend.NONE
        mock_envelope.reason_human = "Action not supported"
        mock_envelope.job_id = "job_unsupported"
        mock_route.return_value = mock_envelope

        job = MockFoundUpJob(
            job_id="job_unsupported",
            tenant_id="tenant_test",
            requested_action="delete_foundup",  # Not supported
        )

        consumer = FoundUpJobConsumer(dry_run=True)
        result = consumer.consume_one(job)

        # execute_foundup_job must NOT be called
        mock_execute.assert_not_called()
        assert result.dispatched is False
        assert result.route_status == RouteStatus.UNSUPPORTED

    @patch("modules.infrastructure.wre_core.src.foundup_job_consumer.route_foundup_job")
    @patch(
        "modules.infrastructure.wre_core.src.hermes_job_executor.execute_foundup_job"
    )
    def test_blocked_route_no_hermes_dispatch(self, mock_execute, mock_route):
        """Blocked route does not call execute_foundup_job."""
        mock_envelope = MagicMock()
        mock_envelope.route_status = RouteStatus.BLOCKED
        mock_envelope.target_backend = TargetBackend.NONE
        mock_envelope.reason_human = "Security gate failed"
        mock_envelope.job_id = "job_blocked"
        mock_route.return_value = mock_envelope

        job = MockFoundUpJob(
            job_id="job_blocked",
            tenant_id="tenant_test",
            requested_action="build_foundup",
            policy_flags=MockPolicyFlags(
                security_gate_checked=True, security_gate_passed=False
            ),
        )

        consumer = FoundUpJobConsumer(dry_run=True)
        result = consumer.consume_one(job)

        mock_execute.assert_not_called()
        assert result.dispatched is False
        assert result.route_status == RouteStatus.BLOCKED

    @patch("modules.infrastructure.wre_core.src.foundup_job_consumer.route_foundup_job")
    @patch(
        "modules.infrastructure.wre_core.src.hermes_job_executor.execute_foundup_job"
    )
    def test_queued_route_status_no_hermes_dispatch(self, mock_execute, mock_route):
        """QUEUED route status (queue_foundup_job) does not call Hermes."""
        mock_envelope = MagicMock()
        mock_envelope.route_status = RouteStatus.QUEUED
        mock_envelope.target_backend = TargetBackend.OPENCLAW_QUEUE
        mock_envelope.reason_human = "Job queued"
        mock_envelope.job_id = "job_queued"
        mock_route.return_value = mock_envelope

        job = MockFoundUpJob(
            job_id="job_queued",
            tenant_id="tenant_test",
            requested_action="queue_foundup_job",
        )

        consumer = FoundUpJobConsumer(dry_run=True)
        result = consumer.consume_one(job)

        mock_execute.assert_not_called()
        assert result.dispatched is False
        assert result.route_status == RouteStatus.QUEUED


# ---------------------------------------------------------------------------
# Test: drain_jobs consumes multiple jobs
# ---------------------------------------------------------------------------


class TestDrainJobs:
    """Test drain_jobs processes multiple jobs."""

    @patch("modules.infrastructure.wre_core.src.foundup_job_consumer.route_foundup_job")
    def test_drain_jobs_processes_all_jobs(self, mock_route):
        """drain_jobs processes all jobs in iterable."""
        # All jobs blocked (no Hermes dispatch needed)
        mock_envelope = MagicMock()
        mock_envelope.route_status = RouteStatus.BLOCKED
        mock_envelope.target_backend = TargetBackend.NONE
        mock_envelope.reason_human = "Blocked"
        mock_envelope.job_id = "job_x"
        mock_route.return_value = mock_envelope

        jobs = [
            MockFoundUpJob(
                job_id=f"job_{i}",
                tenant_id="tenant_test",
                requested_action="build_foundup",
            )
            for i in range(5)
        ]

        consumer = FoundUpJobConsumer(dry_run=True)
        results = consumer.drain_jobs(jobs)

        assert len(results) == 5
        assert mock_route.call_count == 5
        for result in results:
            assert isinstance(result, ConsumerResult)


# ---------------------------------------------------------------------------
# Test: drain_openclaw_queue_once clears queue after drain
# ---------------------------------------------------------------------------


class TestDrainOpenClawQueue:
    """Test drain_openclaw_queue_once behavior with retention semantics."""

    @patch(
        "modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator.remove_jobs_by_id"
    )
    @patch(
        "modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator.get_job_queue"
    )
    @patch("modules.infrastructure.wre_core.src.foundup_job_consumer.route_foundup_job")
    def test_drain_retains_blocked_jobs(
        self, mock_route, mock_get_queue, mock_remove
    ):
        """Blocked jobs are retained, not cleared (retention semantics)."""
        mock_envelope = MagicMock()
        mock_envelope.route_status = RouteStatus.BLOCKED
        mock_envelope.target_backend = TargetBackend.NONE
        mock_envelope.reason_human = "Blocked"
        mock_envelope.job_id = "job_q"
        mock_route.return_value = mock_envelope

        mock_get_queue.return_value = [
            MockFoundUpJob(
                job_id="job_q1",
                tenant_id="tenant_test",
                requested_action="build_foundup",
            ),
            MockFoundUpJob(
                job_id="job_q2",
                tenant_id="tenant_test",
                requested_action="validate_foundup",
            ),
        ]

        consumer = FoundUpJobConsumer(dry_run=True)
        results = consumer.drain_openclaw_queue_once(clear=True)

        # Jobs were processed
        assert len(results) == 2
        # But blocked jobs should not be removed (retained)
        mock_remove.assert_not_called()

    @patch(
        "modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator.remove_jobs_by_id"
    )
    @patch(
        "modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator.get_job_queue"
    )
    @patch("modules.infrastructure.wre_core.src.foundup_job_consumer.route_foundup_job")
    def test_drain_does_not_clear_if_clear_false(
        self, mock_route, mock_get_queue, mock_remove
    ):
        """drain_openclaw_queue_once with clear=False does not remove jobs."""
        mock_envelope = MagicMock()
        mock_envelope.route_status = RouteStatus.BLOCKED
        mock_envelope.target_backend = TargetBackend.NONE
        mock_envelope.reason_human = "Blocked"
        mock_envelope.job_id = "job_q"
        mock_route.return_value = mock_envelope

        mock_get_queue.return_value = [
            MockFoundUpJob(
                job_id="job_q1",
                tenant_id="tenant_test",
                requested_action="build_foundup",
            ),
        ]

        consumer = FoundUpJobConsumer(dry_run=True)
        results = consumer.drain_openclaw_queue_once(clear=False)

        assert len(results) == 1
        mock_remove.assert_not_called()

    @patch(
        "modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator.get_job_queue"
    )
    def test_drain_empty_queue_returns_empty_list(self, mock_get_queue):
        """drain_openclaw_queue_once on empty queue returns empty list."""
        mock_get_queue.return_value = []

        consumer = FoundUpJobConsumer(dry_run=True)
        results = consumer.drain_openclaw_queue_once()

        assert results == []


# ---------------------------------------------------------------------------
# Test: Retention Semantics
# ---------------------------------------------------------------------------


class TestRetentionSemantics:
    """Test retention-aware drain behavior."""

    @patch(
        "modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator.remove_jobs_by_id"
    )
    @patch(
        "modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator.get_job_queue"
    )
    @patch("modules.infrastructure.wre_core.src.foundup_job_consumer.route_foundup_job")
    def test_routing_failure_retained(self, mock_route, mock_get_queue, mock_remove):
        """Jobs with routing failure are retained with reason."""
        mock_envelope = MagicMock()
        mock_envelope.route_status = RouteStatus.FAILED
        mock_envelope.target_backend = TargetBackend.NONE
        mock_envelope.reason_human = "Routing failed"
        mock_envelope.job_id = "job_fail"
        mock_route.return_value = mock_envelope

        mock_get_queue.return_value = [
            MockFoundUpJob(
                job_id="job_fail",
                tenant_id="tenant_test",
                requested_action="build_foundup",
            ),
        ]

        consumer = FoundUpJobConsumer(dry_run=True)
        drain_result = consumer.drain_openclaw_queue_with_retention(clear=True)

        assert drain_result.retained_count == 1
        assert drain_result.cleared_count == 0
        assert "job_fail" in drain_result.retained_job_ids
        assert drain_result.retention_reasons["job_fail"] == "routing_failed"
        mock_remove.assert_not_called()

    @patch(
        "modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator.remove_jobs_by_id"
    )
    @patch(
        "modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator.get_job_queue"
    )
    @patch("modules.infrastructure.wre_core.src.foundup_job_consumer.route_foundup_job")
    def test_routing_blocked_retained(self, mock_route, mock_get_queue, mock_remove):
        """Jobs blocked by security gate are retained."""
        mock_envelope = MagicMock()
        mock_envelope.route_status = RouteStatus.BLOCKED
        mock_envelope.target_backend = TargetBackend.NONE
        mock_envelope.reason_human = "Security gate failed"
        mock_envelope.job_id = "job_blocked"
        mock_route.return_value = mock_envelope

        mock_get_queue.return_value = [
            MockFoundUpJob(
                job_id="job_blocked",
                tenant_id="tenant_test",
                requested_action="build_foundup",
            ),
        ]

        consumer = FoundUpJobConsumer(dry_run=True)
        drain_result = consumer.drain_openclaw_queue_with_retention(clear=True)

        assert drain_result.retained_count == 1
        assert drain_result.retention_reasons["job_blocked"] == "routing_blocked"

    @patch(
        "modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator.get_job_queue"
    )
    def test_empty_queue_no_retained_consumed(self, mock_get_queue):
        """Empty queue returns no retained or consumed jobs."""
        mock_get_queue.return_value = []

        consumer = FoundUpJobConsumer(dry_run=True)
        drain_result = consumer.drain_openclaw_queue_with_retention(clear=True)

        assert drain_result.cleared_count == 0
        assert drain_result.retained_count == 0
        assert drain_result.cleared_job_ids == []
        assert drain_result.retained_job_ids == []
        assert drain_result.retention_reasons == {}

    def test_consumer_result_should_clear_properties(self):
        """ConsumerResult has should_clear and retention_reason properties."""
        # Blocked route - should retain
        blocked_result = ConsumerResult(
            job_id="blocked_job",
            dispatched=False,
            route_status=RouteStatus.BLOCKED,
            target_backend=TargetBackend.NONE,
            reason="Blocked",
        )
        assert blocked_result.should_clear is False
        assert blocked_result.retention_reason == "routing_blocked"

        # Failed route - should retain
        failed_result = ConsumerResult(
            job_id="failed_job",
            dispatched=False,
            route_status=RouteStatus.FAILED,
            target_backend=TargetBackend.NONE,
            reason="Failed",
        )
        assert failed_result.should_clear is False
        assert failed_result.retention_reason == "routing_failed"

        # Unsupported action - should retain
        unsupported_result = ConsumerResult(
            job_id="unsupported_job",
            dispatched=False,
            route_status=RouteStatus.UNSUPPORTED,
            target_backend=TargetBackend.NONE,
            reason="Unsupported",
        )
        assert unsupported_result.should_clear is False
        assert unsupported_result.retention_reason == "action_unsupported"

    @patch(
        "modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator.remove_jobs_by_id"
    )
    @patch(
        "modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator.get_job_queue"
    )
    @patch("modules.infrastructure.wre_core.src.foundup_job_consumer.route_foundup_job")
    @patch(
        "modules.infrastructure.wre_core.src.hermes_job_executor.execute_foundup_job"
    )
    def test_wre_dry_run_job_retained_with_evidence(
        self, mock_execute, mock_route, mock_get_queue, mock_remove
    ):
        """
        WRE dry-run simulated job is retained with checkpoint/evidence.

        Phase 1C behavior:
          - SIMULATED status = terminal-like for WRE executor
          - No receipt emission for dry-run (WSP 97: no overclaim)
          - Job retained (not cleared) because no receipt
          - Evidence captured in checkpoint fields

        Proves:
          - Job retained (not cleared) for dry-run
          - checkpoint_state = "SIMULATED"
          - evidence_path populated
          - WSP 97 fields remain false
        """
        from modules.communication.moltbot_bridge.src.foundup_job_contract import (
            create_job,
        )

        # Setup routing to HERMES_BUILDER
        mock_envelope = MagicMock()
        mock_envelope.route_status = RouteStatus.ROUTED
        mock_envelope.target_backend = TargetBackend.HERMES_BUILDER
        mock_envelope.reason_human = "Routed to hermes_builder"
        mock_envelope.job_id = "job_simulated"
        mock_route.return_value = mock_envelope

        # Setup WRE executor to return SIMULATED result
        mock_hermes_result = MagicMock()
        mock_hermes_result.status.value = "SIMULATED"
        mock_hermes_result.checkpoint_state = "SIMULATED"
        mock_hermes_result.checkpoint_result = None
        mock_hermes_result.checkpoint_blocker = None
        mock_hermes_result.checkpoint_next_action = None
        mock_hermes_result.evidence_path = ".hermes_evidence/job_simulated"
        mock_hermes_result.real_execution_performed = False
        mock_execute.return_value = mock_hermes_result

        # Create real job with proper payload
        job = create_job(
            tenant_id="012",
            requested_action="build_foundup",
            foundup_id="success_test",
            payload={"module_path": "modules/foundups/success_test"},
        )
        # Override job_id to match envelope
        job.job_id = "job_simulated"

        mock_get_queue.return_value = [job]

        consumer = FoundUpJobConsumer(dry_run=True)
        drain_result = consumer.drain_openclaw_queue_with_retention(clear=True)

        # Assert job is retained (not cleared) for dry-run
        assert drain_result.retained_count == 1
        assert drain_result.cleared_count == 0
        assert "job_simulated" in drain_result.retained_job_ids
        assert "job_simulated" not in drain_result.cleared_job_ids

        # No jobs removed (all retained)
        mock_remove.assert_not_called()

        # Assert checkpoint/evidence fields populated
        result = drain_result.results[0]
        assert result.checkpoint_state == "SIMULATED"
        assert result.evidence_path == ".hermes_evidence/job_simulated"
        assert result.real_execution_performed is False

        # Assert WSP 97 truth fields
        assert result.verification_complete is False
        assert result.cabr_ready is False
        assert result.payout_ready is False

        # Verify terminal-like status but no receipt (dry-run)
        assert result.is_terminal is True
        assert result.has_receipt is False  # No receipt for dry-run
        assert result.should_clear is False  # Can't clear without receipt


# ---------------------------------------------------------------------------
# Test: Receipt emitter rejects non-terminal jobs
# ---------------------------------------------------------------------------


class TestReceiptEmitterTerminalCheck:
    """Test receipt emitter rejects non-terminal jobs."""

    def test_non_terminal_job_rejected(self):
        """Non-terminal job receipt emission is rejected."""
        from modules.communication.moltbot_bridge.src.receipt_emitter import (
            emit_receipt_for_terminal_job,
        )

        job = MockFoundUpJob(
            job_id="job_queued",
            tenant_id="tenant_test",
            requested_action="build_foundup",
            status=MockJobStatus.QUEUED,  # Not terminal
        )

        result = emit_receipt_for_terminal_job(job)

        assert result.success is False
        assert "not terminal" in result.error.lower()

    def test_running_job_rejected(self):
        """Running job receipt emission is rejected."""
        from modules.communication.moltbot_bridge.src.receipt_emitter import (
            emit_receipt_for_terminal_job,
        )

        job = MockFoundUpJob(
            job_id="job_running",
            tenant_id="tenant_test",
            requested_action="build_foundup",
            status=MockJobStatus.RUNNING,  # Not terminal
        )

        result = emit_receipt_for_terminal_job(job)

        assert result.success is False
        assert "not terminal" in result.error.lower()

    def test_terminal_succeeded_job_accepted(self):
        """Terminal SUCCEEDED job can emit receipt."""
        from modules.communication.moltbot_bridge.src.receipt_emitter import (
            emit_receipt_for_terminal_job,
        )
        from modules.communication.moltbot_bridge.src.foundup_job_contract import (
            create_job,
            JobStatus,
            StatusReasonCode,
        )

        # Use real FoundUpJob for proper terminal check
        job = create_job(
            tenant_id="tenant_test",
            requested_action="build_foundup",
            payload={"test": True},
        )
        # Manually set to terminal state
        job.status = JobStatus.SUCCEEDED
        job.status_reason_code = StatusReasonCode.OK_COMPLETED
        job.evidence_refs = ["test_evidence.json"]

        result = emit_receipt_for_terminal_job(job)

        assert result.success is True
        assert result.receipt is not None
        assert result.verification is not None
        # WSP 97 truth boundaries
        assert result.verification.cabr_ready is False
        assert result.verification.payout_ready is False


# ---------------------------------------------------------------------------
# Test: get_consumer factory
# ---------------------------------------------------------------------------


class TestGetConsumer:
    """Test get_consumer factory function."""

    def test_get_consumer_returns_instance(self):
        """get_consumer returns FoundUpJobConsumer instance."""
        consumer = get_consumer()
        assert isinstance(consumer, FoundUpJobConsumer)
        assert consumer.dry_run is True

    def test_get_consumer_dry_run_false(self):
        """get_consumer with dry_run=False."""
        consumer = get_consumer(dry_run=False)
        assert consumer.dry_run is False


# ---------------------------------------------------------------------------
# Test: Phase 1B Receipt/pAVS Binding in ConsumerResult
# ---------------------------------------------------------------------------


class TestConsumerResultCheckpointBinding:
    """
    Test Phase 1C: ConsumerResult carries checkpoint and evidence fields.

    Proves:
      - One ConsumerResult contains complete dry-run evidence chain
      - checkpoint_state, evidence_path populated from WRE executor
      - WSP 97 truth fields preserved (no overclaim for dry-run)
    """

    @patch("modules.infrastructure.wre_core.src.foundup_job_consumer.route_foundup_job")
    @patch(
        "modules.infrastructure.wre_core.src.hermes_job_executor.execute_foundup_job"
    )
    def test_simulated_job_has_checkpoint_in_consumer_result(
        self, mock_execute, mock_route
    ):
        """
        Simulated job includes checkpoint fields in ConsumerResult.

        Phase 1C proves:
          - ConsumerResult.checkpoint_state populated
          - ConsumerResult.evidence_path populated
          - No receipt for dry-run (WSP 97 truth)
        """
        from modules.communication.moltbot_bridge.src.foundup_job_contract import (
            create_job,
        )

        # Setup routing
        mock_envelope = MagicMock()
        mock_envelope.route_status = RouteStatus.ROUTED
        mock_envelope.target_backend = TargetBackend.HERMES_BUILDER
        mock_envelope.reason_human = "Routed to hermes_builder"
        mock_envelope.job_id = "job_checkpoint"
        mock_route.return_value = mock_envelope

        # Setup WRE executor SIMULATED result
        mock_hermes_result = MagicMock()
        mock_hermes_result.status.value = "SIMULATED"
        mock_hermes_result.checkpoint_state = "SIMULATED"
        mock_hermes_result.checkpoint_result = "Dry-run validation complete"
        mock_hermes_result.checkpoint_blocker = None
        mock_hermes_result.checkpoint_next_action = None
        mock_hermes_result.evidence_path = ".hermes_evidence/job_checkpoint"
        mock_hermes_result.real_execution_performed = False
        mock_execute.return_value = mock_hermes_result

        # Create job with proper payload
        job = create_job(
            tenant_id="012",
            requested_action="build_foundup",
            foundup_id="test_module",
            payload={"module_path": "modules/foundups/test_module"},
        )

        consumer = FoundUpJobConsumer(dry_run=True)
        result = consumer.consume_one(job)

        # Verify dispatch succeeded
        assert result.dispatched is True
        assert result.is_terminal is True

        # Verify checkpoint fields populated
        assert result.checkpoint_state == "SIMULATED"
        assert result.checkpoint_result == "Dry-run validation complete"
        assert result.evidence_path == ".hermes_evidence/job_checkpoint"
        assert result.real_execution_performed is False

        # Verify NO receipt for dry-run (WSP 97 truth)
        assert result.receipt_emission is None
        assert result.has_receipt is False

    @patch("modules.infrastructure.wre_core.src.foundup_job_consumer.route_foundup_job")
    @patch(
        "modules.infrastructure.wre_core.src.hermes_job_executor.execute_foundup_job"
    )
    def test_consumer_result_contains_wsp97_truth_fields(
        self, mock_execute, mock_route
    ):
        """
        ConsumerResult exposes WSP 97 truth fields.

        Proves:
          - verification_complete=False
          - cabr_ready=False
          - payout_ready=False
          - real_execution_performed=False
        """
        from modules.communication.moltbot_bridge.src.foundup_job_contract import (
            create_job,
        )

        mock_envelope = MagicMock()
        mock_envelope.route_status = RouteStatus.ROUTED
        mock_envelope.target_backend = TargetBackend.HERMES_BUILDER
        mock_envelope.reason_human = "Routed"
        mock_envelope.job_id = "job_wsp97"
        mock_route.return_value = mock_envelope

        mock_hermes_result = MagicMock()
        mock_hermes_result.status.value = "SIMULATED"
        mock_hermes_result.checkpoint_state = "SIMULATED"
        mock_hermes_result.checkpoint_result = None
        mock_hermes_result.checkpoint_blocker = None
        mock_hermes_result.checkpoint_next_action = None
        mock_hermes_result.evidence_path = ".hermes_evidence/job_wsp97"
        mock_hermes_result.real_execution_performed = False
        mock_execute.return_value = mock_hermes_result

        job = create_job(
            tenant_id="012",
            requested_action="build_foundup",
            payload={"module_path": "modules/foundups/wsp97_test"},
        )

        consumer = FoundUpJobConsumer(dry_run=True)
        result = consumer.consume_one(job)

        # WSP 97 truth fields via ConsumerResult properties
        assert result.verification_complete is False
        assert result.cabr_ready is False
        assert result.payout_ready is False

        # Phase 1C truth fields
        assert result.real_execution_performed is False
        assert result.checkpoint_state == "SIMULATED"

        # WSP 97 truth fields in to_dict()
        result_dict = result.to_dict()
        assert result_dict["verification_complete"] is False
        assert result_dict["cabr_ready"] is False
        assert result_dict["payout_ready"] is False
        assert result_dict["real_execution_performed"] is False
        assert result_dict["receipt_emitted"] is False  # No receipt for dry-run

    @patch("modules.infrastructure.wre_core.src.foundup_job_consumer.route_foundup_job")
    def test_non_terminal_job_no_receipt_emission(self, mock_route):
        """
        Non-terminal job does not emit receipt.

        Proves:
          - Blocked route -> no Hermes dispatch -> no receipt
          - ConsumerResult.receipt_emission is None
        """
        mock_envelope = MagicMock()
        mock_envelope.route_status = RouteStatus.BLOCKED
        mock_envelope.target_backend = TargetBackend.NONE
        mock_envelope.reason_human = "Blocked by security gate"
        mock_envelope.job_id = "job_blocked_no_receipt"
        mock_route.return_value = mock_envelope

        job = MockFoundUpJob(
            job_id="job_blocked_no_receipt",
            tenant_id="tenant_test",
            requested_action="build_foundup",
        )

        consumer = FoundUpJobConsumer(dry_run=True)
        result = consumer.consume_one(job)

        # Not dispatched, no receipt
        assert result.dispatched is False
        assert result.receipt_emission is None
        assert result.has_receipt is False
        assert result.is_terminal is False

    @patch("modules.infrastructure.wre_core.src.foundup_job_consumer.route_foundup_job")
    @patch(
        "modules.infrastructure.wre_core.src.hermes_job_executor.execute_foundup_job"
    )
    def test_closed_loop_dry_run_proof_single_result(
        self, mock_execute, mock_route
    ):
        """
        One ConsumerResult proves closed-loop dry-run execution.

        Phase 1C proves:
          - Route -> WRE Executor -> Checkpoint/Evidence all in one result
          - Evidence captured in checkpoint fields (not receipt for dry-run)
          - All evidence accessible from ConsumerResult
        """
        from modules.communication.moltbot_bridge.src.foundup_job_contract import (
            create_job,
        )

        # Setup full pipeline
        mock_envelope = MagicMock()
        mock_envelope.route_status = RouteStatus.ROUTED
        mock_envelope.target_backend = TargetBackend.HERMES_BUILDER
        mock_envelope.reason_human = "Routed to hermes_builder"
        mock_envelope.job_id = "job_closed_loop"
        mock_route.return_value = mock_envelope

        # Setup WRE executor SIMULATED result
        mock_hermes_result = MagicMock()
        mock_hermes_result.status.value = "SIMULATED"
        mock_hermes_result.checkpoint_state = "SIMULATED"
        mock_hermes_result.checkpoint_result = "Dry-run validation complete"
        mock_hermes_result.checkpoint_blocker = None
        mock_hermes_result.checkpoint_next_action = None
        mock_hermes_result.evidence_path = ".hermes_evidence/job_closed_loop"
        mock_hermes_result.real_execution_performed = False
        mock_execute.return_value = mock_hermes_result

        job = create_job(
            tenant_id="012",
            requested_action="build_foundup",
            foundup_id="closed_loop_test",
            payload={"module_path": "modules/foundups/closed_loop_test"},
        )

        consumer = FoundUpJobConsumer(dry_run=True)
        result = consumer.consume_one(job)

        # === Closed-loop evidence in ONE ConsumerResult ===

        # 1. Route evidence
        assert result.route_status == RouteStatus.ROUTED
        assert result.target_backend == TargetBackend.HERMES_BUILDER
        assert result.envelope is not None

        # 2. WRE executor evidence
        assert result.dispatched is True
        assert result.hermes_result is not None
        assert result.hermes_result.status.value == "SIMULATED"

        # 3. Checkpoint/evidence fields (Phase 1C)
        assert result.checkpoint_state == "SIMULATED"
        assert result.checkpoint_result == "Dry-run validation complete"
        assert result.evidence_path == ".hermes_evidence/job_closed_loop"
        assert result.real_execution_performed is False

        # 4. No receipt for dry-run (WSP 97 truth)
        assert result.has_receipt is False
        assert result.receipt_emission is None

        # 5. WSP 97 truth boundaries
        assert result.verification_complete is False
        assert result.cabr_ready is False
        assert result.payout_ready is False

    @patch("modules.infrastructure.wre_core.src.foundup_job_consumer.route_foundup_job")
    @patch(
        "modules.infrastructure.wre_core.src.hermes_job_executor.execute_foundup_job"
    )
    def test_blocked_wre_result_has_checkpoint_evidence(
        self, mock_execute, mock_route
    ):
        """
        Blocked WRE result (terminal) has checkpoint evidence.

        Phase 1C proves:
          - BLOCKED_* status is terminal-like
          - checkpoint_blocker populated
          - No receipt for dry-run blocked state
        """
        from modules.communication.moltbot_bridge.src.foundup_job_contract import (
            create_job,
        )

        mock_envelope = MagicMock()
        mock_envelope.route_status = RouteStatus.ROUTED
        mock_envelope.target_backend = TargetBackend.HERMES_BUILDER
        mock_envelope.reason_human = "Routed"
        mock_envelope.job_id = "job_wre_blocked"
        mock_route.return_value = mock_envelope

        # Setup WRE executor BLOCKED result
        mock_hermes_result = MagicMock()
        mock_hermes_result.status.value = "BLOCKED_INVALID_JOB"
        mock_hermes_result.checkpoint_state = "BLOCKED"
        mock_hermes_result.checkpoint_result = None
        mock_hermes_result.checkpoint_blocker = "Job validation failed"
        mock_hermes_result.checkpoint_next_action = "Fix job payload"
        mock_hermes_result.evidence_path = ".hermes_evidence/job_wre_blocked"
        mock_hermes_result.real_execution_performed = False
        mock_execute.return_value = mock_hermes_result

        job = create_job(
            tenant_id="012",
            requested_action="build_foundup",
            payload={"module_path": "modules/foundups/blocked_test"},
        )

        consumer = FoundUpJobConsumer(dry_run=True)
        result = consumer.consume_one(job)

        # BLOCKED_* is terminal-like
        assert result.is_terminal is True
        assert result.hermes_result.status.value == "BLOCKED_INVALID_JOB"

        # Checkpoint evidence captured
        assert result.checkpoint_state == "BLOCKED"
        assert result.checkpoint_blocker == "Job validation failed"
        assert result.checkpoint_next_action == "Fix job payload"
        assert result.evidence_path == ".hermes_evidence/job_wre_blocked"

        # No receipt for blocked dry-run
        assert result.has_receipt is False
        assert result.receipt_emission is None

        # WSP 97 still enforced
        assert result.verification_complete is False
        assert result.cabr_ready is False
        assert result.payout_ready is False


# ---------------------------------------------------------------------------
# Test: drain_openclaw_queue_dry_run convenience function
# ---------------------------------------------------------------------------


class TestDrainOpenClawQueueDryRun:
    """Test drain_openclaw_queue_dry_run convenience function with retention."""

    @patch(
        "modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator.remove_jobs_by_id"
    )
    @patch(
        "modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator.get_job_queue"
    )
    @patch("modules.infrastructure.wre_core.src.foundup_job_consumer.route_foundup_job")
    def test_drain_dry_run_returns_retention_metadata(
        self, mock_route, mock_get_queue, mock_remove
    ):
        """drain_openclaw_queue_dry_run returns retention metadata."""
        mock_envelope = MagicMock()
        mock_envelope.route_status = RouteStatus.BLOCKED
        mock_envelope.target_backend = TargetBackend.NONE
        mock_envelope.reason_human = "Blocked"
        mock_envelope.job_id = "job_dry"
        mock_route.return_value = mock_envelope

        mock_get_queue.return_value = [
            MockFoundUpJob(
                job_id="job_dry1",
                tenant_id="tenant_test",
                requested_action="build_foundup",
            ),
            MockFoundUpJob(
                job_id="job_dry2",
                tenant_id="tenant_test",
                requested_action="validate_foundup",
            ),
        ]

        summary = drain_openclaw_queue_dry_run(clear=True)

        # Verify structure with retention fields
        assert "job_count" in summary
        assert "results" in summary
        assert "dry_run" in summary
        assert "cleared_job_ids" in summary
        assert "retained_job_ids" in summary
        assert "retention_reasons" in summary
        assert "cleared_count" in summary
        assert "retained_count" in summary
        assert "summary" in summary

        # Verify values - blocked jobs are retained
        assert summary["job_count"] == 2
        assert summary["dry_run"] is True
        assert len(summary["results"]) == 2
        assert summary["retained_count"] == 2
        assert summary["cleared_count"] == 0
        assert "job_dry1" in summary["retained_job_ids"]
        assert "job_dry2" in summary["retained_job_ids"]

    @patch(
        "modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator.remove_jobs_by_id"
    )
    @patch(
        "modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator.get_job_queue"
    )
    @patch("modules.infrastructure.wre_core.src.foundup_job_consumer.route_foundup_job")
    def test_drain_dry_run_wsp97_truth_fields(
        self, mock_route, mock_get_queue, mock_remove
    ):
        """drain_openclaw_queue_dry_run enforces WSP 97 truth boundaries."""
        mock_envelope = MagicMock()
        mock_envelope.route_status = RouteStatus.BLOCKED
        mock_envelope.target_backend = TargetBackend.NONE
        mock_envelope.reason_human = "Blocked"
        mock_envelope.job_id = "job_truth"
        mock_route.return_value = mock_envelope

        mock_get_queue.return_value = [
            MockFoundUpJob(
                job_id="job_truth1",
                tenant_id="tenant_test",
                requested_action="build_foundup",
            ),
        ]

        summary = drain_openclaw_queue_dry_run()

        # WSP 97 truth boundaries in summary
        assert summary["summary"]["verification_complete"] is False
        assert summary["summary"]["cabr_ready"] is False
        assert summary["summary"]["payout_ready"] is False

    @patch(
        "modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator.get_job_queue"
    )
    def test_drain_dry_run_empty_queue(self, mock_get_queue):
        """drain_openclaw_queue_dry_run with empty queue returns no retained/consumed."""
        mock_get_queue.return_value = []

        summary = drain_openclaw_queue_dry_run()

        assert summary["job_count"] == 0
        assert summary["results"] == []
        assert summary["dry_run"] is True
        assert summary["cleared_count"] == 0
        assert summary["retained_count"] == 0
        assert summary["cleared_job_ids"] == []
        assert summary["retained_job_ids"] == []
        assert summary["retention_reasons"] == {}
        assert summary["summary"]["dispatched"] == 0

    @patch(
        "modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator.remove_jobs_by_id"
    )
    @patch(
        "modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator.get_job_queue"
    )
    @patch("modules.infrastructure.wre_core.src.foundup_job_consumer.route_foundup_job")
    def test_drain_dry_run_includes_retention_reasons(
        self, mock_route, mock_get_queue, mock_remove
    ):
        """drain_openclaw_queue_dry_run includes retention reasons for each job."""
        mock_envelope = MagicMock()
        mock_envelope.route_status = RouteStatus.BLOCKED
        mock_envelope.target_backend = TargetBackend.NONE
        mock_envelope.reason_human = "Blocked"
        mock_envelope.job_id = "job_nc"
        mock_route.return_value = mock_envelope

        mock_get_queue.return_value = [
            MockFoundUpJob(
                job_id="job_nc1",
                tenant_id="tenant_test",
                requested_action="build_foundup",
            ),
        ]

        summary = drain_openclaw_queue_dry_run(clear=True)

        # Blocked job should have retention reason
        assert summary["retained_count"] == 1
        assert "job_nc1" in summary["retention_reasons"]
        assert summary["retention_reasons"]["job_nc1"] == "routing_blocked"
        # No jobs removed since all were blocked
        mock_remove.assert_not_called()
