#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test suite for Worker Assignment Protocol scaffold.

WSP 97 Truth Boundary Tests:
  - All dispatch is simulated only
  - No real processes are started
  - real_process_started=False always
  - simulated=True always
  - No CABR/reward/payout/token fields

Test Coverage:
  1. register_worker creates tracked worker process
  2. register_worker records runtime type and capabilities
  3. dispatch_assignment returns simulated/not-implemented status
  4. dispatch_assignment does not start process
  5. heartbeat updates worker last_seen
  6. completion event records evidence_refs
  7. deregistration changes status
  8. no CABR/reward/payout/token fields exist
  9. all WSP_97 truth fields remain false/simulated
"""

import pytest
from datetime import datetime, timezone

from modules.foundups.agent.src.build_plan import BuildStepAction
from modules.foundups.agent.src.worker_assignment_protocol import (
    AssignmentDispatcher,
    AssignmentDispatchRequest,
    AssignmentDispatchResult,
    AssignmentDispatchStatus,
    WorkerCompletionEvent,
    WorkerDeregistration,
    WorkerHeartbeatEvent,
    WorkerProcess,
    WorkerProcessStatus,
    WorkerRegistration,
    WorkerRuntimeType,
    WorkerTrustLevel,
    create_assignment_dispatcher,
)


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def dispatcher() -> AssignmentDispatcher:
    """Create an AssignmentDispatcher for testing."""
    return create_assignment_dispatcher()


@pytest.fixture
def hermes_registration() -> WorkerRegistration:
    """Create a Hermes worker registration."""
    return WorkerRegistration(
        worker_id="hermes_test_001",
        runtime_type=WorkerRuntimeType.HERMES,
        capabilities=["build", "extract"],
        identity_claim="test_api_key_hermes",
        requested_trust_level=WorkerTrustLevel.VERIFIED,
    )


@pytest.fixture
def openclaw_registration() -> WorkerRegistration:
    """Create an OpenClaw worker registration."""
    return WorkerRegistration(
        worker_id="openclaw_test_001",
        runtime_type=WorkerRuntimeType.OPENCLAW,
        capabilities=["validate", "orchestrate"],
        identity_claim="test_api_key_openclaw",
        requested_trust_level=WorkerTrustLevel.TRUSTED,
    )


# ---------------------------------------------------------------------------
# Test 1: register_worker creates tracked worker process
# ---------------------------------------------------------------------------


class TestWorkerRegistration:
    """Test worker registration functionality."""

    def test_register_worker_creates_process(
        self,
        dispatcher: AssignmentDispatcher,
        hermes_registration: WorkerRegistration,
    ) -> None:
        """Test that register_worker creates a tracked worker process."""
        worker = dispatcher.register_worker(hermes_registration)

        assert worker is not None
        assert worker.worker_id == "hermes_test_001"
        assert worker.status == WorkerProcessStatus.IDLE
        assert worker.simulated is True

        # Worker is tracked
        workers = dispatcher.list_workers()
        assert len(workers) == 1
        assert workers[0].worker_id == "hermes_test_001"

    def test_register_worker_duplicate_fails(
        self,
        dispatcher: AssignmentDispatcher,
        hermes_registration: WorkerRegistration,
    ) -> None:
        """Test that duplicate registration fails."""
        dispatcher.register_worker(hermes_registration)

        with pytest.raises(ValueError, match="already registered"):
            dispatcher.register_worker(hermes_registration)


# ---------------------------------------------------------------------------
# Test 2: register_worker records runtime type and capabilities
# ---------------------------------------------------------------------------


class TestWorkerCapabilities:
    """Test worker runtime type and capabilities."""

    def test_register_records_runtime_type(
        self,
        dispatcher: AssignmentDispatcher,
        hermes_registration: WorkerRegistration,
    ) -> None:
        """Test that registration records runtime type."""
        worker = dispatcher.register_worker(hermes_registration)

        assert worker.runtime_type == WorkerRuntimeType.HERMES

    def test_register_records_capabilities(
        self,
        dispatcher: AssignmentDispatcher,
        hermes_registration: WorkerRegistration,
    ) -> None:
        """Test that registration records capabilities."""
        worker = dispatcher.register_worker(hermes_registration)

        assert "build" in worker.capabilities
        assert "extract" in worker.capabilities
        assert worker.has_capability("build") is True
        assert worker.has_capability("validate") is False

    def test_multiple_workers_different_types(
        self,
        dispatcher: AssignmentDispatcher,
        hermes_registration: WorkerRegistration,
        openclaw_registration: WorkerRegistration,
    ) -> None:
        """Test registering multiple workers with different types."""
        hermes = dispatcher.register_worker(hermes_registration)
        openclaw = dispatcher.register_worker(openclaw_registration)

        assert hermes.runtime_type == WorkerRuntimeType.HERMES
        assert openclaw.runtime_type == WorkerRuntimeType.OPENCLAW

        workers = dispatcher.list_workers()
        assert len(workers) == 2


# ---------------------------------------------------------------------------
# Test 3: dispatch_assignment returns simulated/not-implemented status
# ---------------------------------------------------------------------------


class TestDispatchStatus:
    """Test dispatch assignment status."""

    def test_dispatch_returns_simulated_status(
        self,
        dispatcher: AssignmentDispatcher,
        hermes_registration: WorkerRegistration,
    ) -> None:
        """Test that dispatch returns SIMULATED_DISPATCH status."""
        worker = dispatcher.register_worker(hermes_registration)

        request = AssignmentDispatchRequest(
            assignment_id="assign_001",
            entry_id="qe_001",
            worker_id=worker.worker_id,
            step_id="step_create_module",
            step_action=BuildStepAction.CREATE_MODULE,
            owned_files=["modules/test/src/"],
        )

        result = dispatcher.dispatch_assignment(request)

        assert result.success is True
        assert result.dispatch_status == AssignmentDispatchStatus.SIMULATED_DISPATCH
        assert result.simulated is True

    def test_dispatch_worker_not_found(
        self,
        dispatcher: AssignmentDispatcher,
    ) -> None:
        """Test dispatch fails if worker not found."""
        request = AssignmentDispatchRequest(
            assignment_id="assign_001",
            entry_id="qe_001",
            worker_id="nonexistent_worker",
            step_id="step_001",
            step_action=BuildStepAction.VALIDATE_GENESIS,
            owned_files=[],
        )

        result = dispatcher.dispatch_assignment(request)

        assert result.success is False
        assert result.dispatch_status == AssignmentDispatchStatus.WORKER_NOT_FOUND


# ---------------------------------------------------------------------------
# Test 4: dispatch_assignment does not start process
# ---------------------------------------------------------------------------


class TestNoRealProcess:
    """Test that no real process is started."""

    def test_dispatch_does_not_start_process(
        self,
        dispatcher: AssignmentDispatcher,
        hermes_registration: WorkerRegistration,
    ) -> None:
        """Test that dispatch does not start a real process."""
        worker = dispatcher.register_worker(hermes_registration)

        request = AssignmentDispatchRequest(
            assignment_id="assign_001",
            entry_id="qe_001",
            worker_id=worker.worker_id,
            step_id="step_001",
            step_action=BuildStepAction.CREATE_MODULE,
            owned_files=["modules/test/"],
        )

        result = dispatcher.dispatch_assignment(request)

        # WSP 97: real_process_started is always False
        assert result.real_process_started is False
        assert result.simulated is True

    def test_result_post_init_enforces_no_real_process(self) -> None:
        """Test that __post_init__ enforces real_process_started=False."""
        result = AssignmentDispatchResult(
            success=True,
            dispatch_status=AssignmentDispatchStatus.SIMULATED_DISPATCH,
            real_process_started=True,  # Try to set True
        )

        # __post_init__ should enforce False
        assert result.real_process_started is False
        assert result.simulated is True


# ---------------------------------------------------------------------------
# Test 5: heartbeat updates worker last_seen
# ---------------------------------------------------------------------------


class TestHeartbeat:
    """Test heartbeat functionality."""

    def test_heartbeat_updates_last_seen(
        self,
        dispatcher: AssignmentDispatcher,
        hermes_registration: WorkerRegistration,
    ) -> None:
        """Test that heartbeat updates worker last_seen."""
        worker = dispatcher.register_worker(hermes_registration)
        original_last_seen = worker.last_seen_at

        # Dispatch assignment first
        request = AssignmentDispatchRequest(
            assignment_id="assign_001",
            entry_id="qe_001",
            worker_id=worker.worker_id,
            step_id="step_001",
            step_action=BuildStepAction.CREATE_MODULE,
            owned_files=[],
        )
        dispatcher.dispatch_assignment(request)

        # Send heartbeat
        heartbeat = WorkerHeartbeatEvent(
            worker_id=worker.worker_id,
            assignment_id="assign_001",
            status=WorkerProcessStatus.PROCESSING,
            progress_percent=50,
        )
        updated_worker = dispatcher.receive_heartbeat(heartbeat)

        assert updated_worker.last_seen_at is not None
        assert updated_worker.last_seen_at != original_last_seen

    def test_heartbeat_updates_status(
        self,
        dispatcher: AssignmentDispatcher,
        hermes_registration: WorkerRegistration,
    ) -> None:
        """Test that heartbeat can update worker status."""
        worker = dispatcher.register_worker(hermes_registration)

        # Dispatch first
        request = AssignmentDispatchRequest(
            assignment_id="assign_001",
            entry_id="qe_001",
            worker_id=worker.worker_id,
            step_id="step_001",
            step_action=BuildStepAction.VALIDATE_GENESIS,
            owned_files=[],
        )
        dispatcher.dispatch_assignment(request)

        # Heartbeat with PROCESSING status
        heartbeat = WorkerHeartbeatEvent(
            worker_id=worker.worker_id,
            assignment_id="assign_001",
            status=WorkerProcessStatus.PROCESSING,
        )
        updated_worker = dispatcher.receive_heartbeat(heartbeat)

        assert updated_worker.status == WorkerProcessStatus.PROCESSING


# ---------------------------------------------------------------------------
# Test 6: completion event records evidence_refs
# ---------------------------------------------------------------------------


class TestCompletion:
    """Test completion event functionality."""

    def test_completion_records_evidence(
        self,
        dispatcher: AssignmentDispatcher,
        hermes_registration: WorkerRegistration,
    ) -> None:
        """Test that completion event records evidence_refs."""
        worker = dispatcher.register_worker(hermes_registration)

        # Dispatch
        request = AssignmentDispatchRequest(
            assignment_id="assign_001",
            entry_id="qe_001",
            worker_id=worker.worker_id,
            step_id="step_001",
            step_action=BuildStepAction.CREATE_MODULE,
            owned_files=[],
        )
        dispatcher.dispatch_assignment(request)

        # Complete with evidence
        completion = WorkerCompletionEvent(
            worker_id=worker.worker_id,
            assignment_id="assign_001",
            success=True,
            evidence_refs=[
                "evidence/step_001/module_created",
                "evidence/step_001/tests_passed",
            ],
        )
        result = dispatcher.receive_completion(completion)

        assert result.success is True

        # Check event log
        events = dispatcher.get_events()
        completion_events = [e for e in events if e["event_type"] == "completion_received"]
        assert len(completion_events) == 1
        assert completion_events[0]["evidence_refs"] == [
            "evidence/step_001/module_created",
            "evidence/step_001/tests_passed",
        ]

    def test_completion_returns_worker_to_idle(
        self,
        dispatcher: AssignmentDispatcher,
        hermes_registration: WorkerRegistration,
    ) -> None:
        """Test that completion returns worker to IDLE status."""
        worker = dispatcher.register_worker(hermes_registration)

        # Dispatch
        request = AssignmentDispatchRequest(
            assignment_id="assign_001",
            entry_id="qe_001",
            worker_id=worker.worker_id,
            step_id="step_001",
            step_action=BuildStepAction.VALIDATE_GENESIS,
            owned_files=[],
        )
        dispatcher.dispatch_assignment(request)

        assert worker.status == WorkerProcessStatus.ASSIGNED

        # Complete
        completion = WorkerCompletionEvent(
            worker_id=worker.worker_id,
            assignment_id="assign_001",
            success=True,
            evidence_refs=[],
        )
        dispatcher.receive_completion(completion)

        # Worker should be IDLE again
        updated_worker = dispatcher.get_worker(worker.worker_id)
        assert updated_worker.status == WorkerProcessStatus.IDLE


# ---------------------------------------------------------------------------
# Test 7: deregistration changes status
# ---------------------------------------------------------------------------


class TestDeregistration:
    """Test worker deregistration."""

    def test_deregistration_changes_status(
        self,
        dispatcher: AssignmentDispatcher,
        hermes_registration: WorkerRegistration,
    ) -> None:
        """Test that deregistration changes worker status to TERMINATED."""
        worker = dispatcher.register_worker(hermes_registration)
        assert worker.status == WorkerProcessStatus.IDLE

        result = dispatcher.deregister_worker(worker.worker_id)

        assert result.success is True
        assert result.worker_id == worker.worker_id

        # Worker status should be TERMINATED
        updated_worker = dispatcher.get_worker(worker.worker_id)
        assert updated_worker.status == WorkerProcessStatus.TERMINATED

    def test_deregistration_releases_assignments(
        self,
        dispatcher: AssignmentDispatcher,
        hermes_registration: WorkerRegistration,
    ) -> None:
        """Test that deregistration releases any assignments."""
        worker = dispatcher.register_worker(hermes_registration)

        # Dispatch
        request = AssignmentDispatchRequest(
            assignment_id="assign_001",
            entry_id="qe_001",
            worker_id=worker.worker_id,
            step_id="step_001",
            step_action=BuildStepAction.CREATE_MODULE,
            owned_files=[],
        )
        dispatcher.dispatch_assignment(request)

        # Deregister
        result = dispatcher.deregister_worker(worker.worker_id)

        assert result.success is True
        assert "assign_001" in result.assignments_released


# ---------------------------------------------------------------------------
# Test 8: no CABR/reward/payout/token fields exist
# ---------------------------------------------------------------------------


class TestNoCABRFields:
    """Test that no CABR/reward/payout/token fields exist."""

    def test_worker_no_cabr_fields(
        self,
        dispatcher: AssignmentDispatcher,
        hermes_registration: WorkerRegistration,
    ) -> None:
        """Test WorkerProcess has no CABR fields."""
        worker = dispatcher.register_worker(hermes_registration)

        forbidden_fields = [
            "cabr_ready",
            "payout_ready",
            "reward",
            "payout",
            "tokens",
            "token_balance",
        ]

        for field in forbidden_fields:
            assert not hasattr(worker, field), f"Worker should not have {field}"

        # Also check to_dict()
        worker_dict = worker.to_dict()
        for field in forbidden_fields:
            assert field not in worker_dict, f"Worker dict should not have {field}"

    def test_result_no_cabr_fields(
        self,
        dispatcher: AssignmentDispatcher,
        hermes_registration: WorkerRegistration,
    ) -> None:
        """Test AssignmentDispatchResult has no CABR fields."""
        worker = dispatcher.register_worker(hermes_registration)

        request = AssignmentDispatchRequest(
            assignment_id="assign_001",
            entry_id="qe_001",
            worker_id=worker.worker_id,
            step_id="step_001",
            step_action=BuildStepAction.VALIDATE_GENESIS,
            owned_files=[],
        )
        result = dispatcher.dispatch_assignment(request)

        forbidden_fields = [
            "cabr_ready",
            "payout_ready",
            "reward",
            "payout",
            "tokens",
        ]

        for field in forbidden_fields:
            assert not hasattr(result, field), f"Result should not have {field}"

        result_dict = result.to_dict()
        for field in forbidden_fields:
            assert field not in result_dict, f"Result dict should not have {field}"


# ---------------------------------------------------------------------------
# Test 9: all WSP_97 truth fields remain false/simulated
# ---------------------------------------------------------------------------


class TestWSP97TruthFields:
    """Test WSP 97 truth field enforcement."""

    def test_worker_simulated_always_true(
        self,
        dispatcher: AssignmentDispatcher,
        hermes_registration: WorkerRegistration,
    ) -> None:
        """Test that WorkerProcess.simulated is always True."""
        worker = dispatcher.register_worker(hermes_registration)
        assert worker.simulated is True

        # Try to set False via new instance
        new_worker = WorkerProcess(
            worker_id="test_worker",
            runtime_type=WorkerRuntimeType.GENERIC,
            simulated=False,  # Try to set False
        )
        # __post_init__ should enforce True
        assert new_worker.simulated is True

    def test_result_simulated_always_true(self) -> None:
        """Test that AssignmentDispatchResult.simulated is always True."""
        result = AssignmentDispatchResult(
            success=True,
            dispatch_status=AssignmentDispatchStatus.SIMULATED_DISPATCH,
            simulated=False,  # Try to set False
        )
        # __post_init__ should enforce True
        assert result.simulated is True

    def test_result_real_process_started_always_false(self) -> None:
        """Test that real_process_started is always False."""
        result = AssignmentDispatchResult(
            success=True,
            dispatch_status=AssignmentDispatchStatus.SIMULATED_DISPATCH,
            real_process_started=True,  # Try to set True
        )
        # __post_init__ should enforce False
        assert result.real_process_started is False

    def test_completion_event_simulated_always_true(self) -> None:
        """Test that WorkerCompletionEvent.simulated is always True."""
        completion = WorkerCompletionEvent(
            worker_id="test_worker",
            assignment_id="assign_001",
            success=True,
            simulated=False,  # Try to set False
        )
        # __post_init__ should enforce True
        assert completion.simulated is True

    def test_no_real_execution_performed_field(
        self,
        dispatcher: AssignmentDispatcher,
        hermes_registration: WorkerRegistration,
    ) -> None:
        """Test that no real_execution_performed field exists."""
        worker = dispatcher.register_worker(hermes_registration)

        # Worker has no real_execution_performed
        assert not hasattr(worker, "real_execution_performed")

        # Completion event has no real_execution_performed
        completion = WorkerCompletionEvent(
            worker_id=worker.worker_id,
            assignment_id="assign_001",
            success=True,
        )
        assert not hasattr(completion, "real_execution_performed")


# ---------------------------------------------------------------------------
# Additional Tests
# ---------------------------------------------------------------------------


class TestFactoryFunction:
    """Test factory function."""

    def test_create_assignment_dispatcher(self) -> None:
        """Test create_assignment_dispatcher factory."""
        dispatcher = create_assignment_dispatcher()

        assert dispatcher is not None
        assert isinstance(dispatcher, AssignmentDispatcher)
        assert len(dispatcher.list_workers()) == 0


class TestAuditEvents:
    """Test audit event logging."""

    def test_registration_logs_event(
        self,
        dispatcher: AssignmentDispatcher,
        hermes_registration: WorkerRegistration,
    ) -> None:
        """Test that registration logs an event."""
        dispatcher.register_worker(hermes_registration)

        events = dispatcher.get_events()
        assert len(events) == 1
        assert events[0]["event_type"] == "worker_registered"
        assert events[0]["worker_id"] == "hermes_test_001"

    def test_dispatch_logs_event(
        self,
        dispatcher: AssignmentDispatcher,
        hermes_registration: WorkerRegistration,
    ) -> None:
        """Test that dispatch logs an event."""
        worker = dispatcher.register_worker(hermes_registration)

        request = AssignmentDispatchRequest(
            assignment_id="assign_001",
            entry_id="qe_001",
            worker_id=worker.worker_id,
            step_id="step_001",
            step_action=BuildStepAction.VALIDATE_GENESIS,
            owned_files=[],
        )
        dispatcher.dispatch_assignment(request)

        events = dispatcher.get_events()
        dispatch_events = [e for e in events if e["event_type"] == "assignment_dispatched"]
        assert len(dispatch_events) == 1
        assert dispatch_events[0]["assignment_id"] == "assign_001"
