#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test suite for Swarm Dispatch Integration.

WSP 97 Truth Boundary Tests:
  - All dispatch is simulated only
  - No real processes are started
  - real_process_started=False always
  - all_simulated=True always
  - real_execution_performed=False always
  - No CABR/reward/payout/token fields

Test Coverage:
  1. dispatch_next dequeues matching queue entry and dispatches simulated assignment
  2. dispatch_next returns blocked/no-match for wrong capability
  3. complete_dispatched_assignment records evidence in queue and dispatcher
  4. run_simulated_cycle performs dequeue -> dispatch -> complete
  5. multiple workers can process different assignments without file conflicts
  6. summary reports all_simulated=True and real_execution_performed=False
  7. VoteBallot swarm queue can run one simulated dispatch cycle
"""

import pytest
from datetime import datetime, timezone

from modules.foundups.agent.src.build_plan import (
    BuildMode,
    BuildPlan,
    BuildStepAction,
    BuildTarget,
    create_standard_build_steps,
)
from modules.foundups.agent.src.build_plan_swarm import (
    SwarmCoordinator,
    WorkerIdentity,
    create_swarm_coordinator,
)
from modules.foundups.agent.src.build_plan_swarm_queue import (
    QueueEntryStatus,
    QueuePriority,
    SwarmWorkerQueue,
    create_swarm_worker_queue,
)
from modules.foundups.agent.src.worker_assignment_protocol import (
    AssignmentDispatcher,
    WorkerProcessStatus,
    WorkerRegistration,
    WorkerRuntimeType,
    WorkerTrustLevel,
    create_assignment_dispatcher,
)
from modules.foundups.agent.src.swarm_dispatch_integration import (
    DispatchCycleResult,
    DispatchCycleStatus,
    QueueDispatchSummary,
    SwarmDispatchCoordinator,
    create_swarm_dispatch_coordinator,
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
    """Create a sample BuildTarget."""
    return BuildTarget(
        module_path="modules/foundups/voteballots",
        pwa_surface_path="public/member/foundups/voteballots/",
    )


@pytest.fixture
def sample_plan(sample_target: BuildTarget) -> BuildPlan:
    """Create a sample BuildPlan."""
    plan = BuildPlan(
        build_plan_id="bp_dispatch_001",
        foundup_id="voteballots",
        tenant_id="foundups",
        mode=BuildMode.DRY_RUN,
        dry_run=True,
        target=sample_target,
    )
    plan.steps = create_standard_build_steps("modules/foundups/voteballots")
    return plan


@pytest.fixture
def swarm_coordinator(sample_plan: BuildPlan) -> SwarmCoordinator:
    """Create a SwarmCoordinator."""
    return create_swarm_coordinator(sample_plan)


@pytest.fixture
def queue() -> SwarmWorkerQueue:
    """Create a SwarmWorkerQueue."""
    return create_swarm_worker_queue()


@pytest.fixture
def dispatcher() -> AssignmentDispatcher:
    """Create an AssignmentDispatcher."""
    return create_assignment_dispatcher()


@pytest.fixture
def coordinator(
    queue: SwarmWorkerQueue,
    dispatcher: AssignmentDispatcher,
) -> SwarmDispatchCoordinator:
    """Create a SwarmDispatchCoordinator."""
    return create_swarm_dispatch_coordinator(queue, dispatcher)


def register_worker_in_both(
    swarm_coordinator: SwarmCoordinator,
    dispatcher: AssignmentDispatcher,
    worker_id: str,
    capabilities: list,
    runtime_type: WorkerRuntimeType = WorkerRuntimeType.OPENCLAW,
) -> None:
    """Register a worker in both swarm coordinator and dispatcher."""
    # Register in swarm coordinator
    swarm_coordinator.register_worker(WorkerIdentity(
        worker_id=worker_id,
        worker_type=runtime_type.value,
        capabilities=capabilities,
    ))

    # Register in dispatcher
    dispatcher.register_worker(WorkerRegistration(
        worker_id=worker_id,
        runtime_type=runtime_type,
        capabilities=capabilities,
        requested_trust_level=WorkerTrustLevel.VERIFIED,
    ))


# ---------------------------------------------------------------------------
# Test 1: dispatch_next dequeues and dispatches
# ---------------------------------------------------------------------------


class TestDispatchNext:
    """Test dispatch_next functionality."""

    def test_dispatch_next_dequeues_and_dispatches(
        self,
        coordinator: SwarmDispatchCoordinator,
        swarm_coordinator: SwarmCoordinator,
        sample_plan: BuildPlan,
    ) -> None:
        """Test that dispatch_next dequeues matching entry and dispatches."""
        # Register worker in both systems
        register_worker_in_both(
            swarm_coordinator,
            coordinator.dispatcher,
            "worker_dispatch_001",
            ["validate"],
        )

        # Create assignment and enqueue
        step = sample_plan.steps[0]  # VALIDATE_GENESIS
        assignment = swarm_coordinator.assign_step(
            step,
            "worker_dispatch_001",
            ["modules/foundups/voteballots/README.md"],
        )
        coordinator.queue.enqueue_assignment(
            assignment=assignment,
            priority=QueuePriority.NORMAL,
            step_action=step.action,
        )

        # Dispatch next
        result = coordinator.dispatch_next("worker_dispatch_001")

        # Assertions
        assert result.success is True
        assert result.status == DispatchCycleStatus.SUCCESS
        assert result.entry_id is not None
        assert result.assignment_id is not None
        assert result.simulated is True
        assert result.real_process_started is False

    def test_dispatch_next_worker_not_found(
        self,
        coordinator: SwarmDispatchCoordinator,
    ) -> None:
        """Test dispatch_next fails when worker not registered."""
        result = coordinator.dispatch_next("nonexistent_worker")

        assert result.success is False
        assert result.status == DispatchCycleStatus.WORKER_NOT_FOUND


# ---------------------------------------------------------------------------
# Test 2: dispatch_next returns no-match for wrong capability
# ---------------------------------------------------------------------------


class TestCapabilityMismatch:
    """Test capability mismatch handling."""

    def test_dispatch_no_match_for_wrong_capability(
        self,
        coordinator: SwarmDispatchCoordinator,
        swarm_coordinator: SwarmCoordinator,
        sample_plan: BuildPlan,
    ) -> None:
        """Test dispatch returns NO_CAPABILITY_MATCH for wrong capability."""
        # Register worker with 'test' capability
        register_worker_in_both(
            swarm_coordinator,
            coordinator.dispatcher,
            "worker_test_only",
            ["test"],
        )

        # Register another worker with 'validate' for assignment
        register_worker_in_both(
            swarm_coordinator,
            coordinator.dispatcher,
            "worker_validator",
            ["validate"],
        )

        # Enqueue a VALIDATE step (requires 'validate')
        step = sample_plan.steps[0]  # VALIDATE_GENESIS
        assignment = swarm_coordinator.assign_step(
            step,
            "worker_validator",
            [],
        )
        coordinator.queue.enqueue_assignment(
            assignment=assignment,
            step_action=BuildStepAction.VALIDATE_GENESIS,
        )

        # Try to dispatch with 'test' worker - should fail
        result = coordinator.dispatch_next("worker_test_only")

        assert result.success is False
        assert result.status == DispatchCycleStatus.NO_CAPABILITY_MATCH

    def test_dispatch_empty_queue(
        self,
        coordinator: SwarmDispatchCoordinator,
    ) -> None:
        """Test dispatch returns NO_QUEUED_ENTRIES for empty queue."""
        # Register worker
        coordinator.dispatcher.register_worker(WorkerRegistration(
            worker_id="worker_empty",
            runtime_type=WorkerRuntimeType.OPENCLAW,
            capabilities=["all"],
        ))

        result = coordinator.dispatch_next("worker_empty")

        assert result.success is False
        assert result.status == DispatchCycleStatus.NO_QUEUED_ENTRIES


# ---------------------------------------------------------------------------
# Test 3: complete_dispatched_assignment records evidence
# ---------------------------------------------------------------------------


class TestCompletionEvidence:
    """Test completion and evidence recording."""

    def test_complete_records_evidence_in_queue_and_dispatcher(
        self,
        coordinator: SwarmDispatchCoordinator,
        swarm_coordinator: SwarmCoordinator,
        sample_plan: BuildPlan,
    ) -> None:
        """Test completion records evidence in both queue and dispatcher."""
        # Setup
        register_worker_in_both(
            swarm_coordinator,
            coordinator.dispatcher,
            "worker_evidence",
            ["validate"],
        )

        step = sample_plan.steps[0]
        assignment = swarm_coordinator.assign_step(
            step,
            "worker_evidence",
            [],
        )
        coordinator.queue.enqueue_assignment(
            assignment=assignment,
            step_action=step.action,
        )

        # Dispatch
        dispatch_result = coordinator.dispatch_next("worker_evidence")
        entry_id = dispatch_result.entry_id

        # Complete with evidence
        evidence = [
            "evidence/voteballots/genesis_validated",
            "evidence/voteballots/structure_checked",
        ]
        completion_result = coordinator.complete_dispatched_assignment(
            worker_id="worker_evidence",
            entry_id=entry_id,
            evidence_refs=evidence,
        )

        # Assertions
        assert completion_result.success is True
        assert completion_result.evidence_refs == evidence

        # Check queue entry
        entry = coordinator.queue.get_entry(entry_id)
        assert entry.status == QueueEntryStatus.COMPLETED
        assert "evidence/voteballots/genesis_validated" in entry.evidence_refs

        # Check dispatcher events
        events = coordinator.dispatcher.get_events()
        completion_events = [e for e in events if e["event_type"] == "completion_received"]
        assert len(completion_events) == 1


# ---------------------------------------------------------------------------
# Test 4: run_simulated_cycle performs full cycle
# ---------------------------------------------------------------------------


class TestSimulatedCycle:
    """Test run_simulated_cycle functionality."""

    def test_run_simulated_cycle_dequeue_dispatch_complete(
        self,
        coordinator: SwarmDispatchCoordinator,
        swarm_coordinator: SwarmCoordinator,
        sample_plan: BuildPlan,
    ) -> None:
        """Test run_simulated_cycle performs dequeue -> dispatch -> complete."""
        # Setup
        register_worker_in_both(
            swarm_coordinator,
            coordinator.dispatcher,
            "worker_cycle",
            ["validate"],
        )

        step = sample_plan.steps[0]
        assignment = swarm_coordinator.assign_step(
            step,
            "worker_cycle",
            [],
        )
        coordinator.queue.enqueue_assignment(
            assignment=assignment,
            step_action=step.action,
        )

        # Run cycle
        evidence = ["evidence/test/step1_complete"]
        result = coordinator.run_simulated_cycle(
            worker_id="worker_cycle",
            evidence_refs=evidence,
        )

        # Assertions
        assert result.success is True
        assert result.status == DispatchCycleStatus.SUCCESS
        assert result.evidence_refs == evidence

        # Entry should be completed
        entry = coordinator.queue.get_entry(result.entry_id)
        assert entry.status == QueueEntryStatus.COMPLETED

        # Worker should be back to IDLE
        worker = coordinator.dispatcher.get_worker("worker_cycle")
        assert worker.status == WorkerProcessStatus.IDLE


# ---------------------------------------------------------------------------
# Test 5: multiple workers process different assignments
# ---------------------------------------------------------------------------


class TestMultipleWorkers:
    """Test multiple worker coordination."""

    def test_multiple_workers_no_conflicts(
        self,
        coordinator: SwarmDispatchCoordinator,
        swarm_coordinator: SwarmCoordinator,
        sample_plan: BuildPlan,
    ) -> None:
        """Test multiple workers can process different assignments."""
        # Register two workers with different capabilities
        register_worker_in_both(
            swarm_coordinator,
            coordinator.dispatcher,
            "worker_validator",
            ["validate"],
        )
        register_worker_in_both(
            swarm_coordinator,
            coordinator.dispatcher,
            "worker_builder",
            ["build"],
            WorkerRuntimeType.HERMES,
        )

        # Enqueue validate step
        validate_step = sample_plan.steps[0]  # VALIDATE_GENESIS
        validate_assignment = swarm_coordinator.assign_step(
            validate_step,
            "worker_validator",
            ["modules/foundups/voteballots/README.md"],
        )
        coordinator.queue.enqueue_assignment(
            assignment=validate_assignment,
            step_action=validate_step.action,
        )

        # Enqueue build step
        build_step = next(
            (s for s in sample_plan.steps if s.action == BuildStepAction.CREATE_MODULE),
            sample_plan.steps[1],
        )
        build_assignment = swarm_coordinator.assign_step(
            build_step,
            "worker_builder",
            ["modules/foundups/voteballots/src/"],
        )
        coordinator.queue.enqueue_assignment(
            assignment=build_assignment,
            step_action=build_step.action,
        )

        # Run cycles for both workers
        validate_result = coordinator.run_simulated_cycle(
            "worker_validator",
            ["evidence/validate/done"],
        )
        build_result = coordinator.run_simulated_cycle(
            "worker_builder",
            ["evidence/build/done"],
        )

        # Both should succeed
        assert validate_result.success is True
        assert build_result.success is True

        # Summary should show 2 completed
        summary = coordinator.summarize()
        assert summary.total_completed == 2
        assert summary.total_evidence_refs == 2


# ---------------------------------------------------------------------------
# Test 6: summary reports WSP 97 truth fields
# ---------------------------------------------------------------------------


class TestSummaryTruthFields:
    """Test summary WSP 97 truth fields."""

    def test_summary_all_simulated_true(
        self,
        coordinator: SwarmDispatchCoordinator,
        swarm_coordinator: SwarmCoordinator,
        sample_plan: BuildPlan,
    ) -> None:
        """Test summary reports all_simulated=True."""
        # Run a cycle
        register_worker_in_both(
            swarm_coordinator,
            coordinator.dispatcher,
            "worker_summary",
            ["validate"],
        )

        step = sample_plan.steps[0]
        assignment = swarm_coordinator.assign_step(step, "worker_summary", [])
        coordinator.queue.enqueue_assignment(
            assignment=assignment,
            step_action=step.action,
        )
        coordinator.run_simulated_cycle("worker_summary")

        # Get summary
        summary = coordinator.summarize()

        # WSP 97 assertions
        assert summary.all_simulated is True
        assert summary.real_execution_performed is False

    def test_summary_post_init_enforces_truth(self) -> None:
        """Test QueueDispatchSummary __post_init__ enforces truth fields."""
        summary = QueueDispatchSummary(
            all_simulated=False,  # Try to set False
            real_execution_performed=True,  # Try to set True
        )

        # __post_init__ should enforce
        assert summary.all_simulated is True
        assert summary.real_execution_performed is False


# ---------------------------------------------------------------------------
# Test 7: VoteBallot dispatch cycle
# ---------------------------------------------------------------------------


class TestVoteBallotIntegration:
    """Test VoteBallot integration."""

    def test_voteballot_swarm_queue_dispatch_cycle(self) -> None:
        """Test VoteBallot swarm queue can run one simulated dispatch cycle."""
        # Create VoteBallot job and plan
        job = create_job(
            tenant_id="foundups",
            requested_action="build_foundup",
            foundup_id="voteballots",
        )
        plan = create_build_plan_from_job(job)

        # Create all components
        swarm_coordinator = create_swarm_coordinator(plan)
        queue = create_swarm_worker_queue()
        dispatcher = create_assignment_dispatcher()
        coordinator = create_swarm_dispatch_coordinator(queue, dispatcher)

        # Register worker in both systems
        swarm_coordinator.register_worker(WorkerIdentity(
            worker_id="vb_worker_001",
            worker_type="openclaw",
            capabilities=["validate", "build"],
        ))
        dispatcher.register_worker(WorkerRegistration(
            worker_id="vb_worker_001",
            runtime_type=WorkerRuntimeType.OPENCLAW,
            capabilities=["validate", "build"],
            requested_trust_level=WorkerTrustLevel.VERIFIED,
        ))

        # Assign and enqueue first step
        step = plan.steps[0]  # VALIDATE_GENESIS
        assignment = swarm_coordinator.assign_step(
            step,
            "vb_worker_001",
            ["modules/foundups/voteballots/README.md"],
        )
        queue.enqueue_assignment(
            assignment=assignment,
            priority=QueuePriority.NORMAL,
            step_action=step.action,
        )

        # Run simulated cycle
        evidence = [
            f"evidence/voteballots/{step.step_id}/genesis_validated",
            f"evidence/voteballots/{step.step_id}/structure_verified",
        ]
        result = coordinator.run_simulated_cycle(
            "vb_worker_001",
            evidence_refs=evidence,
        )

        # Assertions
        assert result.success is True
        assert result.status == DispatchCycleStatus.SUCCESS
        assert result.simulated is True
        assert result.real_process_started is False

        # Summary
        summary = coordinator.summarize()
        assert summary.total_completed == 1
        assert summary.all_simulated is True
        assert summary.real_execution_performed is False

        # Check evidence collected
        all_evidence = coordinator.get_all_evidence()
        assert len(all_evidence) == 2
        assert "genesis_validated" in all_evidence[0]


class TestNoCABRFields:
    """Test that no CABR fields exist."""

    def test_dispatch_result_no_cabr_fields(
        self,
        coordinator: SwarmDispatchCoordinator,
        swarm_coordinator: SwarmCoordinator,
        sample_plan: BuildPlan,
    ) -> None:
        """Test DispatchCycleResult has no CABR fields."""
        register_worker_in_both(
            swarm_coordinator,
            coordinator.dispatcher,
            "worker_cabr",
            ["validate"],
        )

        step = sample_plan.steps[0]
        assignment = swarm_coordinator.assign_step(step, "worker_cabr", [])
        coordinator.queue.enqueue_assignment(
            assignment=assignment,
            step_action=step.action,
        )

        result = coordinator.run_simulated_cycle("worker_cabr")

        forbidden = ["cabr_ready", "payout_ready", "reward", "tokens"]
        for field in forbidden:
            assert not hasattr(result, field), f"Result should not have {field}"

        result_dict = result.to_dict()
        for field in forbidden:
            assert field not in result_dict

    def test_summary_no_cabr_fields(
        self,
        coordinator: SwarmDispatchCoordinator,
    ) -> None:
        """Test QueueDispatchSummary has no CABR fields."""
        summary = coordinator.summarize()

        forbidden = ["cabr_ready", "payout_ready", "reward", "tokens"]
        for field in forbidden:
            assert not hasattr(summary, field), f"Summary should not have {field}"

        summary_dict = summary.to_dict()
        for field in forbidden:
            assert field not in summary_dict
