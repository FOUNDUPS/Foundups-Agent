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
    """Test that routed jobs dispatch to Hermes with correct dry_run."""

    @patch("modules.infrastructure.wre_core.src.foundup_job_consumer.route_foundup_job")
    @patch(
        "modules.foundups.agent.src.hermes_foundup_job_executor.execute_foundup_job"
    )
    def test_hermes_builder_dispatches_with_dry_run_true(
        self, mock_execute, mock_route
    ):
        """HERMES_BUILDER routed job dispatches with dry_run=True."""
        # Setup mock route envelope
        mock_envelope = MagicMock()
        mock_envelope.route_status = RouteStatus.ROUTED
        mock_envelope.target_backend = TargetBackend.HERMES_BUILDER
        mock_envelope.reason_human = "Routed to hermes_builder"
        mock_envelope.job_id = "job_builder"
        mock_route.return_value = mock_envelope

        # Setup mock Hermes result
        mock_hermes_result = MagicMock()
        mock_hermes_result.job.status.value = "succeeded"
        mock_execute.return_value = mock_hermes_result

        job = MockFoundUpJob(
            job_id="job_builder",
            tenant_id="tenant_test",
            requested_action="build_foundup",
        )

        consumer = FoundUpJobConsumer(dry_run=True)
        result = consumer.consume_one(job)

        # execute_foundup_job must be called with force_dry_run=True
        mock_execute.assert_called_once_with(job, force_dry_run=True)
        assert result.dispatched is True
        assert result.target_backend == TargetBackend.HERMES_BUILDER

    @patch("modules.infrastructure.wre_core.src.foundup_job_consumer.route_foundup_job")
    @patch(
        "modules.foundups.agent.src.hermes_foundup_job_executor.execute_foundup_job"
    )
    def test_hermes_validator_dispatches_with_dry_run_true(
        self, mock_execute, mock_route
    ):
        """HERMES_VALIDATOR routed job dispatches with dry_run=True."""
        mock_envelope = MagicMock()
        mock_envelope.route_status = RouteStatus.ROUTED
        mock_envelope.target_backend = TargetBackend.HERMES_VALIDATOR
        mock_envelope.reason_human = "Routed to hermes_validator"
        mock_envelope.job_id = "job_validator"
        mock_route.return_value = mock_envelope

        mock_hermes_result = MagicMock()
        mock_hermes_result.job.status.value = "succeeded"
        mock_execute.return_value = mock_hermes_result

        job = MockFoundUpJob(
            job_id="job_validator",
            tenant_id="tenant_test",
            requested_action="validate_foundup",
        )

        consumer = FoundUpJobConsumer(dry_run=True)
        result = consumer.consume_one(job)

        mock_execute.assert_called_once_with(job, force_dry_run=True)
        assert result.dispatched is True
        assert result.target_backend == TargetBackend.HERMES_VALIDATOR

    @patch("modules.infrastructure.wre_core.src.foundup_job_consumer.route_foundup_job")
    @patch(
        "modules.foundups.agent.src.hermes_foundup_job_executor.execute_foundup_job"
    )
    def test_consumer_dry_run_false_passes_to_hermes(self, mock_execute, mock_route):
        """Consumer with dry_run=False passes force_dry_run=False to Hermes."""
        mock_envelope = MagicMock()
        mock_envelope.route_status = RouteStatus.ROUTED
        mock_envelope.target_backend = TargetBackend.HERMES_BUILDER
        mock_envelope.reason_human = "Routed"
        mock_envelope.job_id = "job_real"
        mock_route.return_value = mock_envelope

        mock_hermes_result = MagicMock()
        mock_hermes_result.job.status.value = "succeeded"
        mock_execute.return_value = mock_hermes_result

        job = MockFoundUpJob(
            job_id="job_real",
            tenant_id="tenant_test",
            requested_action="build_foundup",
        )

        consumer = FoundUpJobConsumer(dry_run=False)
        result = consumer.consume_one(job)

        # force_dry_run should be False
        mock_execute.assert_called_once_with(job, force_dry_run=False)
        assert result.dispatched is True


# ---------------------------------------------------------------------------
# Test: Unsupported/blocked routes do not call Hermes
# ---------------------------------------------------------------------------


class TestNoHermesForBlockedRoutes:
    """Test that blocked/unsupported routes do not dispatch to Hermes."""

    @patch("modules.infrastructure.wre_core.src.foundup_job_consumer.route_foundup_job")
    @patch(
        "modules.foundups.agent.src.hermes_foundup_job_executor.execute_foundup_job"
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
        "modules.foundups.agent.src.hermes_foundup_job_executor.execute_foundup_job"
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
        "modules.foundups.agent.src.hermes_foundup_job_executor.execute_foundup_job"
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
    """Test drain_openclaw_queue_once behavior."""

    @patch(
        "modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator.clear_job_queue"
    )
    @patch(
        "modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator.get_job_queue"
    )
    @patch("modules.infrastructure.wre_core.src.foundup_job_consumer.route_foundup_job")
    def test_drain_clears_queue_after_success(
        self, mock_route, mock_get_queue, mock_clear_queue
    ):
        """drain_openclaw_queue_once clears queue after successful drain."""
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

        assert len(results) == 2
        mock_clear_queue.assert_called_once()

    @patch(
        "modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator.clear_job_queue"
    )
    @patch(
        "modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator.get_job_queue"
    )
    @patch("modules.infrastructure.wre_core.src.foundup_job_consumer.route_foundup_job")
    def test_drain_does_not_clear_if_clear_false(
        self, mock_route, mock_get_queue, mock_clear_queue
    ):
        """drain_openclaw_queue_once with clear=False does not clear queue."""
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
        mock_clear_queue.assert_not_called()

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
