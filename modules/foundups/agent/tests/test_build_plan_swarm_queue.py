#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test suite for BuildPlan Swarm WRE Queue scaffold.

WSP 97 Truth Boundary Tests:
  - Queue entries are simulated only
  - No real worker process dequeue
  - No files are edited
  - No CABR/reward/payout/token fields
  - real_execution_performed does not exist (cannot become True)

Test Coverage:
  1. Create queue entry from StepAssignment
  2. Dequeue matching worker capability succeeds
  3. Dequeue mismatched worker capability is blocked
  4. Heartbeat renews lease
  5. Completion report marks entry complete with evidence
  6. Expired entry can be requeued
  7. Simulated completion cannot set real_execution_performed=True
  8. Queue entry has no CABR/reward/payout/token fields
  9. VoteBallot swarm assignment can be enqueued and dequeued by simulated worker
"""

import pytest
from datetime import datetime, timedelta, timezone

from modules.foundups.agent.src.build_plan import (
    BuildMode,
    BuildPlan,
    BuildStep,
    BuildStepAction,
    BuildTarget,
    StepStatus,
    create_standard_build_steps,
)
from modules.foundups.agent.src.build_plan_swarm import (
    AssignmentStatus,
    StepAssignment,
    SwarmCoordinator,
    WorkerCapability,
    WorkerIdentity,
    create_swarm_coordinator,
)
from modules.foundups.agent.src.build_plan_swarm_queue import (
    AssignmentCompletionReport,
    CompletionStatus,
    DequeueDecision,
    QueueAssignmentResult,
    QueueEntryStatus,
    QueuePriority,
    SwarmWorkerQueue,
    SwarmWorkerQueueEntry,
    WorkerDequeueRequest,
    WorkerDequeueResult,
    WorkerHeartbeat,
    create_swarm_worker_queue,
)
from modules.foundups.agent.src.build_plan_generator import (
    create_build_plan_from_job,
)
from modules.communication.moltbot_bridge.src.foundup_job_contract import (
    create_job,
)


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_target() -> BuildTarget:
    """Create a sample BuildTarget for testing."""
    return BuildTarget(
        module_path="modules/foundups/voteballots",
        pwa_surface_path="public/member/foundups/voteballots/",
    )


@pytest.fixture
def sample_plan(sample_target: BuildTarget) -> BuildPlan:
    """Create a sample BuildPlan for testing."""
    plan = BuildPlan(
        build_plan_id="bp_queue_001",
        foundup_id="voteballots",
        tenant_id="foundups",
        mode=BuildMode.DRY_RUN,
        dry_run=True,
        target=sample_target,
    )
    plan.steps = create_standard_build_steps("modules/foundups/voteballots")
    return plan


@pytest.fixture
def coordinator(sample_plan: BuildPlan) -> SwarmCoordinator:
    """Create a SwarmCoordinator for testing."""
    return SwarmCoordinator(plan=sample_plan)


@pytest.fixture
def queue() -> SwarmWorkerQueue:
    """Create a SwarmWorkerQueue for testing."""
    return create_swarm_worker_queue()


@pytest.fixture
def worker_1() -> WorkerIdentity:
    """Create first test worker with validate capability."""
    return WorkerIdentity(
        worker_id="worker_q001",
        worker_type="openclaw",
        capabilities=[WorkerCapability.VALIDATE],
    )


@pytest.fixture
def worker_2() -> WorkerIdentity:
    """Create second test worker with build capability."""
    return WorkerIdentity(
        worker_id="worker_q002",
        worker_type="hermes",
        capabilities=[WorkerCapability.BUILD],
    )


@pytest.fixture
def worker_all() -> WorkerIdentity:
    """Create worker with all capabilities."""
    return WorkerIdentity(
        worker_id="worker_all",
        worker_type="0102",
        capabilities=[WorkerCapability.ALL],
    )


# ---------------------------------------------------------------------------
# Test 1: Create queue entry from StepAssignment
# ---------------------------------------------------------------------------


class TestEnqueueAssignment:
    """Test creating queue entries from StepAssignments."""

    def test_enqueue_creates_entry(
        self,
        coordinator: SwarmCoordinator,
        queue: SwarmWorkerQueue,
        worker_1: WorkerIdentity,
        sample_plan: BuildPlan,
    ) -> None:
        """Test that enqueue_assignment creates a valid queue entry."""
        # Register worker and create assignment
        coordinator.register_worker(worker_1)
        step = sample_plan.steps[0]
        assignment = coordinator.assign_step(
            step=step,
            worker_id=worker_1.worker_id,
            owned_files=["modules/foundups/voteballots/README.md"],
        )

        # Enqueue the assignment
        result = queue.enqueue_assignment(
            assignment=assignment,
            priority=QueuePriority.NORMAL,
            step_action=step.action,
        )

        # Verify
        assert result.success is True
        assert result.entry_id is not None
        assert result.entry_id.startswith("qe_")

        # Check entry was created
        entry = queue.get_entry(result.entry_id)
        assert entry is not None
        assert entry.assignment_id == assignment.assignment_id
        assert entry.step_id == step.step_id
        assert entry.status == QueueEntryStatus.QUEUED
        assert entry.simulated is True  # WSP 97

    def test_enqueue_sets_capability_from_action(
        self,
        coordinator: SwarmCoordinator,
        queue: SwarmWorkerQueue,
        worker_1: WorkerIdentity,
        sample_plan: BuildPlan,
    ) -> None:
        """Test that enqueue derives required_capability from step action."""
        coordinator.register_worker(worker_1)

        # VALIDATE_GENESIS -> validate capability
        validate_step = sample_plan.steps[0]
        assignment = coordinator.assign_step(
            step=validate_step,
            worker_id=worker_1.worker_id,
            owned_files=[],
        )
        result = queue.enqueue_assignment(
            assignment=assignment,
            step_action=BuildStepAction.VALIDATE_GENESIS,
        )
        entry = queue.get_entry(result.entry_id)
        assert entry.required_capability == "validate"

    def test_enqueue_preserves_priority(
        self,
        coordinator: SwarmCoordinator,
        queue: SwarmWorkerQueue,
        worker_1: WorkerIdentity,
        sample_plan: BuildPlan,
    ) -> None:
        """Test that priority is preserved on queue entry."""
        coordinator.register_worker(worker_1)
        step = sample_plan.steps[0]
        assignment = coordinator.assign_step(
            step=step,
            worker_id=worker_1.worker_id,
            owned_files=[],
        )

        result = queue.enqueue_assignment(
            assignment=assignment,
            priority=QueuePriority.CRITICAL,
            step_action=step.action,
        )

        entry = queue.get_entry(result.entry_id)
        assert entry.priority == QueuePriority.CRITICAL


# ---------------------------------------------------------------------------
# Test 2: Dequeue matching worker capability succeeds
# ---------------------------------------------------------------------------


class TestDequeueSuccess:
    """Test successful dequeue operations."""

    def test_dequeue_matching_capability(
        self,
        coordinator: SwarmCoordinator,
        queue: SwarmWorkerQueue,
        worker_1: WorkerIdentity,
        sample_plan: BuildPlan,
    ) -> None:
        """Test worker with matching capability can dequeue."""
        coordinator.register_worker(worker_1)
        step = sample_plan.steps[0]
        assignment = coordinator.assign_step(
            step=step,
            worker_id=worker_1.worker_id,
            owned_files=[],
        )

        # Enqueue with VALIDATE_GENESIS (requires 'validate')
        queue.enqueue_assignment(
            assignment=assignment,
            step_action=BuildStepAction.VALIDATE_GENESIS,
        )

        # Dequeue with worker that has 'validate' capability
        request = WorkerDequeueRequest(
            worker_id="worker_q001",
            capabilities=["validate"],
        )
        result = queue.dequeue_for_worker(request)

        assert result.success is True
        assert result.decision == DequeueDecision.ASSIGNED
        assert len(result.entries) == 1
        assert result.entries[0].status == QueueEntryStatus.PROCESSING
        assert result.entries[0].worker_id == "worker_q001"
        assert result.lease_expires_at is not None

    def test_dequeue_all_capability_matches_any(
        self,
        coordinator: SwarmCoordinator,
        queue: SwarmWorkerQueue,
        worker_1: WorkerIdentity,
        sample_plan: BuildPlan,
    ) -> None:
        """Test worker with 'all' capability can dequeue any entry."""
        coordinator.register_worker(worker_1)
        step = sample_plan.steps[0]
        assignment = coordinator.assign_step(
            step=step,
            worker_id=worker_1.worker_id,
            owned_files=[],
        )

        # Enqueue with BUILD capability requirement
        queue.enqueue_assignment(
            assignment=assignment,
            step_action=BuildStepAction.CREATE_MODULE,  # requires 'build'
        )

        # Dequeue with 'all' capability
        request = WorkerDequeueRequest(
            worker_id="worker_super",
            capabilities=["all"],
        )
        result = queue.dequeue_for_worker(request)

        assert result.success is True
        assert result.decision == DequeueDecision.ASSIGNED


# ---------------------------------------------------------------------------
# Test 3: Dequeue mismatched worker capability is blocked
# ---------------------------------------------------------------------------


class TestDequeueMismatch:
    """Test dequeue failures due to capability mismatch."""

    def test_dequeue_mismatched_capability_fails(
        self,
        coordinator: SwarmCoordinator,
        queue: SwarmWorkerQueue,
        worker_1: WorkerIdentity,
        sample_plan: BuildPlan,
    ) -> None:
        """Test worker without matching capability cannot dequeue."""
        coordinator.register_worker(worker_1)
        step = sample_plan.steps[0]
        assignment = coordinator.assign_step(
            step=step,
            worker_id=worker_1.worker_id,
            owned_files=[],
        )

        # Enqueue with BUILD capability requirement
        queue.enqueue_assignment(
            assignment=assignment,
            step_action=BuildStepAction.CREATE_MODULE,  # requires 'build'
        )

        # Dequeue with worker that only has 'validate' capability
        request = WorkerDequeueRequest(
            worker_id="worker_q001",
            capabilities=["validate"],
        )
        result = queue.dequeue_for_worker(request)

        assert result.success is False
        assert result.decision == DequeueDecision.NO_MATCH
        assert len(result.entries) == 0

    def test_dequeue_empty_queue(
        self,
        queue: SwarmWorkerQueue,
    ) -> None:
        """Test dequeue on empty queue returns QUEUE_EMPTY."""
        request = WorkerDequeueRequest(
            worker_id="worker_q001",
            capabilities=["all"],
        )
        result = queue.dequeue_for_worker(request)

        assert result.success is False
        assert result.decision == DequeueDecision.QUEUE_EMPTY


# ---------------------------------------------------------------------------
# Test 4: Heartbeat renews lease
# ---------------------------------------------------------------------------


class TestHeartbeat:
    """Test heartbeat and lease renewal."""

    def test_heartbeat_renews_lease(
        self,
        coordinator: SwarmCoordinator,
        queue: SwarmWorkerQueue,
        worker_1: WorkerIdentity,
        sample_plan: BuildPlan,
    ) -> None:
        """Test heartbeat renews processing lease."""
        coordinator.register_worker(worker_1)
        step = sample_plan.steps[0]
        assignment = coordinator.assign_step(
            step=step,
            worker_id=worker_1.worker_id,
            owned_files=[],
        )

        # Enqueue and dequeue
        enqueue_result = queue.enqueue_assignment(
            assignment=assignment,
            step_action=BuildStepAction.VALIDATE_GENESIS,
        )
        dequeue_request = WorkerDequeueRequest(
            worker_id="worker_q001",
            capabilities=["validate"],
        )
        dequeue_result = queue.dequeue_for_worker(dequeue_request)

        original_expires = dequeue_result.lease_expires_at
        entry_id = dequeue_result.entries[0].entry_id

        # Send heartbeat
        heartbeat_result = queue.heartbeat(
            worker_id="worker_q001",
            entry_id=entry_id,
        )

        assert heartbeat_result.lease_renewed is True
        assert heartbeat_result.new_expires_at is not None
        # New expiration should be after or equal to original
        # (since we just renewed with same duration)
        assert heartbeat_result.new_expires_at >= original_expires

    def test_heartbeat_wrong_worker_fails(
        self,
        coordinator: SwarmCoordinator,
        queue: SwarmWorkerQueue,
        worker_1: WorkerIdentity,
        sample_plan: BuildPlan,
    ) -> None:
        """Test heartbeat from wrong worker fails."""
        coordinator.register_worker(worker_1)
        step = sample_plan.steps[0]
        assignment = coordinator.assign_step(
            step=step,
            worker_id=worker_1.worker_id,
            owned_files=[],
        )

        # Enqueue and dequeue
        queue.enqueue_assignment(
            assignment=assignment,
            step_action=BuildStepAction.VALIDATE_GENESIS,
        )
        dequeue_request = WorkerDequeueRequest(
            worker_id="worker_q001",
            capabilities=["validate"],
        )
        dequeue_result = queue.dequeue_for_worker(dequeue_request)
        entry_id = dequeue_result.entries[0].entry_id

        # Heartbeat from wrong worker
        heartbeat_result = queue.heartbeat(
            worker_id="wrong_worker",
            entry_id=entry_id,
        )

        assert heartbeat_result.lease_renewed is False


# ---------------------------------------------------------------------------
# Test 5: Completion report marks entry complete with evidence
# ---------------------------------------------------------------------------


class TestCompletion:
    """Test assignment completion reporting."""

    def test_completion_marks_entry_complete(
        self,
        coordinator: SwarmCoordinator,
        queue: SwarmWorkerQueue,
        worker_1: WorkerIdentity,
        sample_plan: BuildPlan,
    ) -> None:
        """Test completion report marks entry as COMPLETED with evidence."""
        coordinator.register_worker(worker_1)
        step = sample_plan.steps[0]
        assignment = coordinator.assign_step(
            step=step,
            worker_id=worker_1.worker_id,
            owned_files=[],
        )

        # Enqueue and dequeue
        queue.enqueue_assignment(
            assignment=assignment,
            step_action=BuildStepAction.VALIDATE_GENESIS,
        )
        dequeue_request = WorkerDequeueRequest(
            worker_id="worker_q001",
            capabilities=["validate"],
        )
        dequeue_result = queue.dequeue_for_worker(dequeue_request)
        entry_id = dequeue_result.entries[0].entry_id

        # Complete with evidence
        report = AssignmentCompletionReport(
            entry_id=entry_id,
            worker_id="worker_q001",
            status=CompletionStatus.SUCCEEDED,
            evidence_refs=["evidence/voteballots/step1_genesis_valid"],
        )
        result = queue.complete_assignment(report)

        assert result.success is True
        entry = queue.get_entry(entry_id)
        assert entry.status == QueueEntryStatus.COMPLETED
        assert "evidence/voteballots/step1_genesis_valid" in entry.evidence_refs
        assert entry.completed_at is not None
        assert entry.simulated is True  # WSP 97

    def test_completion_failed_marks_entry_failed(
        self,
        coordinator: SwarmCoordinator,
        queue: SwarmWorkerQueue,
        worker_1: WorkerIdentity,
        sample_plan: BuildPlan,
    ) -> None:
        """Test failed completion marks entry as FAILED."""
        coordinator.register_worker(worker_1)
        step = sample_plan.steps[0]
        assignment = coordinator.assign_step(
            step=step,
            worker_id=worker_1.worker_id,
            owned_files=[],
        )

        # Enqueue and dequeue
        queue.enqueue_assignment(
            assignment=assignment,
            step_action=BuildStepAction.VALIDATE_GENESIS,
        )
        dequeue_request = WorkerDequeueRequest(
            worker_id="worker_q001",
            capabilities=["validate"],
        )
        dequeue_result = queue.dequeue_for_worker(dequeue_request)
        entry_id = dequeue_result.entries[0].entry_id

        # Complete as failed
        report = AssignmentCompletionReport(
            entry_id=entry_id,
            worker_id="worker_q001",
            status=CompletionStatus.FAILED,
            error_message="Genesis validation failed",
        )
        result = queue.complete_assignment(report)

        assert result.success is True
        entry = queue.get_entry(entry_id)
        assert entry.status == QueueEntryStatus.FAILED
        assert entry.error_message == "Genesis validation failed"


# ---------------------------------------------------------------------------
# Test 6: Expired entry can be requeued
# ---------------------------------------------------------------------------


class TestExpiration:
    """Test lease expiration and requeue."""

    def test_expired_entry_requeued_if_retriable(
        self,
        coordinator: SwarmCoordinator,
        queue: SwarmWorkerQueue,
        worker_1: WorkerIdentity,
        sample_plan: BuildPlan,
    ) -> None:
        """Test expired entry is requeued if retries remain."""
        # Use queue with short lease for testing
        short_queue = SwarmWorkerQueue(lease_duration_seconds=1)

        coordinator.register_worker(worker_1)
        step = sample_plan.steps[0]
        assignment = coordinator.assign_step(
            step=step,
            worker_id=worker_1.worker_id,
            owned_files=[],
        )

        # Enqueue and dequeue
        short_queue.enqueue_assignment(
            assignment=assignment,
            step_action=BuildStepAction.VALIDATE_GENESIS,
        )
        dequeue_request = WorkerDequeueRequest(
            worker_id="worker_q001",
            capabilities=["validate"],
        )
        dequeue_result = short_queue.dequeue_for_worker(dequeue_request)
        entry_id = dequeue_result.entries[0].entry_id

        # Simulate lease expiration
        future_time = datetime.now(timezone.utc) + timedelta(seconds=60)
        expired_ids = short_queue.expire_entries(now=future_time)

        assert entry_id in expired_ids
        entry = short_queue.get_entry(entry_id)
        assert entry.status == QueueEntryStatus.QUEUED  # Requeued
        assert entry.retry_count == 1
        assert entry.worker_id is None

    def test_expired_entry_not_requeued_after_max_retries(
        self,
        coordinator: SwarmCoordinator,
        queue: SwarmWorkerQueue,
        worker_1: WorkerIdentity,
        sample_plan: BuildPlan,
    ) -> None:
        """Test expired entry moves to EXPIRED after max retries."""
        short_queue = SwarmWorkerQueue(lease_duration_seconds=1)

        coordinator.register_worker(worker_1)
        step = sample_plan.steps[0]
        assignment = coordinator.assign_step(
            step=step,
            worker_id=worker_1.worker_id,
            owned_files=[],
        )

        # Enqueue
        enqueue_result = short_queue.enqueue_assignment(
            assignment=assignment,
            step_action=BuildStepAction.VALIDATE_GENESIS,
        )
        entry_id = enqueue_result.entry_id

        # Manually set retry_count to max
        entry = short_queue.get_entry(entry_id)
        entry.retry_count = entry.max_retries

        # Dequeue
        dequeue_request = WorkerDequeueRequest(
            worker_id="worker_q001",
            capabilities=["validate"],
        )
        short_queue.dequeue_for_worker(dequeue_request)

        # Expire
        future_time = datetime.now(timezone.utc) + timedelta(seconds=60)
        expired_ids = short_queue.expire_entries(now=future_time)

        assert entry_id in expired_ids
        entry = short_queue.get_entry(entry_id)
        assert entry.status == QueueEntryStatus.EXPIRED  # Not requeued


# ---------------------------------------------------------------------------
# Test 7: Simulated completion cannot set real_execution_performed=True
# ---------------------------------------------------------------------------


class TestWSP97TruthBoundaries:
    """Test WSP 97 truth boundary enforcement."""

    def test_entry_simulated_always_true(
        self,
        coordinator: SwarmCoordinator,
        queue: SwarmWorkerQueue,
        worker_1: WorkerIdentity,
        sample_plan: BuildPlan,
    ) -> None:
        """Test that entry.simulated is always True."""
        coordinator.register_worker(worker_1)
        step = sample_plan.steps[0]
        assignment = coordinator.assign_step(
            step=step,
            worker_id=worker_1.worker_id,
            owned_files=[],
        )

        result = queue.enqueue_assignment(
            assignment=assignment,
            step_action=BuildStepAction.VALIDATE_GENESIS,
        )
        entry = queue.get_entry(result.entry_id)

        # Try to set simulated=False
        entry.simulated = False
        # __post_init__ doesn't re-run, but let's verify no real_execution_performed field
        assert not hasattr(entry, "real_execution_performed")

        # Create new entry via dataclass and verify
        new_entry = SwarmWorkerQueueEntry(
            entry_id="qe_test",
            assignment_id="a_test",
            step_id="s_test",
            step_action=BuildStepAction.VALIDATE_GENESIS,
            required_capability="validate",
            simulated=False,  # Try to pass False
        )
        assert new_entry.simulated is True  # __post_init__ enforces True

    def test_completion_report_simulated_always_true(self) -> None:
        """Test that AssignmentCompletionReport.simulated is always True."""
        report = AssignmentCompletionReport(
            entry_id="qe_test",
            worker_id="worker_test",
            status=CompletionStatus.SUCCEEDED,
            simulated=False,  # Try to pass False
        )
        assert report.simulated is True  # __post_init__ enforces True

    def test_no_real_execution_performed_field(
        self,
        coordinator: SwarmCoordinator,
        queue: SwarmWorkerQueue,
        worker_1: WorkerIdentity,
        sample_plan: BuildPlan,
    ) -> None:
        """Test that no real_execution_performed field exists."""
        coordinator.register_worker(worker_1)
        step = sample_plan.steps[0]
        assignment = coordinator.assign_step(
            step=step,
            worker_id=worker_1.worker_id,
            owned_files=[],
        )

        result = queue.enqueue_assignment(
            assignment=assignment,
            step_action=BuildStepAction.VALIDATE_GENESIS,
        )
        entry = queue.get_entry(result.entry_id)

        # Verify field does not exist
        assert not hasattr(entry, "real_execution_performed")

        # Verify it's not in to_dict() either
        entry_dict = entry.to_dict()
        assert "real_execution_performed" not in entry_dict


# ---------------------------------------------------------------------------
# Test 8: Queue entry has no CABR/reward/payout/token fields
# ---------------------------------------------------------------------------


class TestNoCABRFields:
    """Test that no CABR/reward/payout/token fields exist."""

    def test_entry_no_cabr_fields(
        self,
        coordinator: SwarmCoordinator,
        queue: SwarmWorkerQueue,
        worker_1: WorkerIdentity,
        sample_plan: BuildPlan,
    ) -> None:
        """Test queue entry has no CABR/reward/payout/token fields."""
        coordinator.register_worker(worker_1)
        step = sample_plan.steps[0]
        assignment = coordinator.assign_step(
            step=step,
            worker_id=worker_1.worker_id,
            owned_files=[],
        )

        result = queue.enqueue_assignment(
            assignment=assignment,
            step_action=BuildStepAction.VALIDATE_GENESIS,
        )
        entry = queue.get_entry(result.entry_id)

        # Forbidden fields
        forbidden_fields = [
            "cabr_ready",
            "payout_ready",
            "reward",
            "payout",
            "token",
            "tokens",
            "cabr_score",
            "verification_complete",
        ]

        for field in forbidden_fields:
            assert not hasattr(entry, field), f"Entry should not have {field}"

        # Also check to_dict()
        entry_dict = entry.to_dict()
        for field in forbidden_fields:
            assert field not in entry_dict, f"Entry dict should not have {field}"

    def test_queue_class_no_cabr_methods(
        self,
        queue: SwarmWorkerQueue,
    ) -> None:
        """Test SwarmWorkerQueue has no CABR-related methods."""
        forbidden_methods = [
            "calculate_payout",
            "distribute_reward",
            "finalize_cabr",
            "verify_work",
            "submit_proof",
        ]

        for method in forbidden_methods:
            assert not hasattr(queue, method), f"Queue should not have {method}"


# ---------------------------------------------------------------------------
# Test 9: VoteBallot swarm assignment can be enqueued and dequeued
# ---------------------------------------------------------------------------


class TestVoteBallotIntegration:
    """Test VoteBallot integration scenario."""

    def test_voteballot_enqueue_dequeue_complete(self) -> None:
        """Test VoteBallot assignment full lifecycle: enqueue -> dequeue -> complete."""
        # Create VoteBallot job and plan
        job = create_job(
            tenant_id="foundups",
            requested_action="build_foundup",
            foundup_id="voteballots",
        )
        plan = create_build_plan_from_job(job)

        # Create coordinator and queue
        coordinator = create_swarm_coordinator(plan)
        queue = create_swarm_worker_queue()

        # Register worker with validate+build capabilities
        worker = WorkerIdentity(
            worker_id="worker_vb_001",
            worker_type="openclaw",
            capabilities=[WorkerCapability.VALIDATE, WorkerCapability.BUILD],
        )
        coordinator.register_worker(worker)

        # Get first step (VALIDATE_GENESIS)
        step = plan.steps[0]
        assert step.action == BuildStepAction.VALIDATE_GENESIS

        # Assign step
        assignment = coordinator.assign_step(
            step=step,
            worker_id="worker_vb_001",
            owned_files=["modules/foundups/voteballots/README.md"],
        )

        # Enqueue
        enqueue_result = queue.enqueue_assignment(
            assignment=assignment,
            priority=QueuePriority.NORMAL,
            step_action=step.action,
        )
        assert enqueue_result.success is True

        # Dequeue
        dequeue_request = WorkerDequeueRequest(
            worker_id="worker_vb_001",
            capabilities=["validate", "build"],
        )
        dequeue_result = queue.dequeue_for_worker(dequeue_request)
        assert dequeue_result.success is True
        assert dequeue_result.decision == DequeueDecision.ASSIGNED

        entry = dequeue_result.entries[0]
        assert entry.status == QueueEntryStatus.PROCESSING
        assert entry.simulated is True

        # Complete
        report = AssignmentCompletionReport(
            entry_id=entry.entry_id,
            worker_id="worker_vb_001",
            status=CompletionStatus.SUCCEEDED,
            evidence_refs=["evidence/voteballots/genesis_validated"],
        )
        complete_result = queue.complete_assignment(report)
        assert complete_result.success is True

        # Verify final state
        final_entry = queue.get_entry(entry.entry_id)
        assert final_entry.status == QueueEntryStatus.COMPLETED
        assert "evidence/voteballots/genesis_validated" in final_entry.evidence_refs
        assert final_entry.simulated is True  # WSP 97

    def test_voteballot_multiple_steps_different_workers(self) -> None:
        """Test multiple VoteBallot steps assigned to different workers."""
        # Create job and plan
        job = create_job(
            tenant_id="foundups",
            requested_action="build_foundup",
            foundup_id="voteballots",
        )
        plan = create_build_plan_from_job(job)

        # Create coordinator and queue
        coordinator = create_swarm_coordinator(plan)
        queue = create_swarm_worker_queue()

        # Register two workers with different capabilities
        validator = WorkerIdentity(
            worker_id="validator_001",
            worker_type="openclaw",
            capabilities=[WorkerCapability.VALIDATE],
        )
        builder = WorkerIdentity(
            worker_id="builder_001",
            worker_type="hermes",
            capabilities=[WorkerCapability.BUILD],
        )
        coordinator.register_worker(validator)
        coordinator.register_worker(builder)

        # Enqueue validation step
        validate_step = plan.steps[0]  # VALIDATE_GENESIS
        validate_assignment = coordinator.assign_step(
            step=validate_step,
            worker_id="validator_001",
            owned_files=[],
        )
        queue.enqueue_assignment(
            assignment=validate_assignment,
            step_action=validate_step.action,
        )

        # Enqueue build step (find CREATE_MODULE step)
        build_step = next(
            (s for s in plan.steps if s.action == BuildStepAction.CREATE_MODULE),
            None,
        )
        if build_step:
            build_assignment = coordinator.assign_step(
                step=build_step,
                worker_id="builder_001",
                owned_files=["modules/foundups/voteballots/src/"],
            )
            queue.enqueue_assignment(
                assignment=build_assignment,
                step_action=build_step.action,
            )

        # Validator can only dequeue validate steps
        validator_request = WorkerDequeueRequest(
            worker_id="validator_001",
            capabilities=["validate"],
        )
        validator_result = queue.dequeue_for_worker(validator_request)
        assert validator_result.success is True
        assert validator_result.entries[0].required_capability == "validate"

        # Builder can only dequeue build steps
        builder_request = WorkerDequeueRequest(
            worker_id="builder_001",
            capabilities=["build"],
        )
        builder_result = queue.dequeue_for_worker(builder_request)

        if build_step:
            assert builder_result.success is True
            assert builder_result.entries[0].required_capability == "build"
        else:
            # If no build step found, queue should be empty for builder
            assert builder_result.decision in [
                DequeueDecision.NO_MATCH,
                DequeueDecision.QUEUE_EMPTY,
            ]
