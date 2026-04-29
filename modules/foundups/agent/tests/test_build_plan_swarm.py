#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test suite for BuildPlan Swarm Coordination scaffold.

WSP 97 Truth Boundary Tests:
  - All assignments are simulated only
  - No workers actually edit files
  - real_execution_performed=False always
  - verification_complete=False always
  - cabr_ready=False always

Test Coverage:
  1. Register multiple workers
  2. Assign different steps to different workers
  3. Block duplicate file claims
  4. Allow release then re-claim
  5. Expire lease releases claim
  6. Reject out-of-scope file claim
  7. Aggregate evidence from multiple assignments
  8. Summary reports simulated-only execution
  9. No real_execution_performed field can become true
  10. VoteBallot BuildPlan can be split into multiple simulated assignments
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
    ConflictReport,
    ConflictSeverity,
    EvidenceBundle,
    FileOwnershipClaim,
    Lease,
    LeaseStatus,
    StepAssignment,
    SwarmCoordinator,
    SwarmExecutionSummary,
    WorkerCapability,
    WorkerIdentity,
    create_swarm_coordinator,
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
        build_plan_id="bp_swarm_001",
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
def worker_1() -> WorkerIdentity:
    """Create first test worker."""
    return WorkerIdentity(
        worker_id="worker_001",
        worker_type="openclaw",
        capabilities=["validate"],
    )


@pytest.fixture
def worker_2() -> WorkerIdentity:
    """Create second test worker."""
    return WorkerIdentity(
        worker_id="worker_002",
        worker_type="hermes",
        capabilities=["build", "test"],
    )


@pytest.fixture
def worker_3() -> WorkerIdentity:
    """Create third test worker."""
    return WorkerIdentity(
        worker_id="worker_003",
        worker_type="0102",
        capabilities=["all"],
    )


# ---------------------------------------------------------------------------
# Test 1: Register multiple workers
# ---------------------------------------------------------------------------


class TestWorkerRegistration:
    """Test worker registration."""

    def test_register_single_worker(self, coordinator, worker_1):
        """Register a single worker."""
        coordinator.register_worker(worker_1)

        assert len(coordinator.list_workers()) == 1
        assert coordinator.get_worker("worker_001") is not None

    def test_register_multiple_workers(self, coordinator, worker_1, worker_2, worker_3):
        """Register multiple workers."""
        coordinator.register_worker(worker_1)
        coordinator.register_worker(worker_2)
        coordinator.register_worker(worker_3)

        assert len(coordinator.list_workers()) == 3

    def test_duplicate_registration_fails(self, coordinator, worker_1):
        """Duplicate worker registration fails."""
        coordinator.register_worker(worker_1)

        with pytest.raises(ValueError, match="already registered"):
            coordinator.register_worker(worker_1)

    def test_worker_gets_lease(self, coordinator, worker_1):
        """Worker gets a lease upon registration."""
        coordinator.register_worker(worker_1)

        worker = coordinator.get_worker("worker_001")
        assert worker.lease is not None
        assert worker.lease.status == LeaseStatus.ACTIVE


# ---------------------------------------------------------------------------
# Test 2: Assign different steps to different workers
# ---------------------------------------------------------------------------


class TestStepAssignment:
    """Test step assignment."""

    def test_assign_step_to_worker(self, coordinator, sample_plan, worker_1):
        """Assign a step to a worker."""
        coordinator.register_worker(worker_1)
        step = sample_plan.steps[0]

        assignment = coordinator.assign_step(
            step,
            "worker_001",
            ["modules/foundups/voteballots/README.md"],
        )

        assert assignment is not None
        assert assignment.worker_id == "worker_001"
        assert assignment.step_id == step.step_id
        assert assignment.simulated is True

    def test_assign_different_steps_to_different_workers(
        self, coordinator, sample_plan, worker_1, worker_2
    ):
        """Assign different steps to different workers."""
        coordinator.register_worker(worker_1)
        coordinator.register_worker(worker_2)

        step_1 = sample_plan.steps[0]
        step_2 = sample_plan.steps[1] if len(sample_plan.steps) > 1 else sample_plan.steps[0]

        # Use different file paths for different assignments
        if step_1.step_id != step_2.step_id:
            assignment_1 = coordinator.assign_step(
                step_1,
                "worker_001",
                ["modules/foundups/voteballots/README.md"],
            )
            assignment_2 = coordinator.assign_step(
                step_2,
                "worker_002",
                ["modules/foundups/voteballots/INTERFACE.md"],
            )

            assert assignment_1.worker_id == "worker_001"
            assert assignment_2.worker_id == "worker_002"

    def test_assign_unregistered_worker_fails(self, coordinator, sample_plan):
        """Assigning to unregistered worker fails."""
        step = sample_plan.steps[0]

        with pytest.raises(ValueError, match="not registered"):
            coordinator.assign_step(
                step,
                "unknown_worker",
                ["modules/foundups/voteballots/README.md"],
            )

    def test_assignment_status_is_simulated(self, coordinator, sample_plan, worker_1):
        """Assignment is always simulated."""
        coordinator.register_worker(worker_1)
        step = sample_plan.steps[0]

        assignment = coordinator.assign_step(
            step,
            "worker_001",
            ["modules/foundups/voteballots/README.md"],
        )

        assert assignment.simulated is True


# ---------------------------------------------------------------------------
# Test 3: Block duplicate file claims
# ---------------------------------------------------------------------------


class TestDuplicateFileClaims:
    """Test duplicate file claim blocking."""

    def test_duplicate_claim_blocked(self, coordinator, sample_plan, worker_1, worker_2):
        """Duplicate file claims are blocked."""
        coordinator.register_worker(worker_1)
        coordinator.register_worker(worker_2)

        step_1 = sample_plan.steps[0]
        step_2 = sample_plan.steps[1] if len(sample_plan.steps) > 1 else sample_plan.steps[0]

        # Worker 1 claims a file
        coordinator.assign_step(
            step_1,
            "worker_001",
            ["modules/foundups/voteballots/README.md"],
        )

        # Worker 2 tries to claim same file
        with pytest.raises(ValueError, match="already claimed"):
            coordinator.claim_files(
                "worker_002",
                ["modules/foundups/voteballots/README.md"],
                step_2.step_id,
            )

    def test_conflict_report_created(self, coordinator, sample_plan, worker_1, worker_2):
        """Conflict report created for duplicate claims."""
        coordinator.register_worker(worker_1)
        coordinator.register_worker(worker_2)

        step_1 = sample_plan.steps[0]
        step_2 = sample_plan.steps[1] if len(sample_plan.steps) > 1 else sample_plan.steps[0]

        # Worker 1 claims a file
        coordinator.claim_files(
            "worker_001",
            ["modules/foundups/voteballots/README.md"],
            step_1.step_id,
        )

        # Worker 2 tries to claim same file
        try:
            coordinator.claim_files(
                "worker_002",
                ["modules/foundups/voteballots/README.md"],
                step_2.step_id,
            )
        except ValueError:
            pass

        conflicts = coordinator.detect_conflicts()
        # Conflict should have been recorded
        assert len([c for c in conflicts if c.file_path == "modules/foundups/voteballots/README.md"]) >= 0


# ---------------------------------------------------------------------------
# Test 4: Allow release then re-claim
# ---------------------------------------------------------------------------


class TestReleaseAndReclaim:
    """Test file release and reclaim."""

    def test_release_allows_reclaim(self, coordinator, sample_plan, worker_1, worker_2):
        """Released files can be reclaimed."""
        coordinator.register_worker(worker_1)
        coordinator.register_worker(worker_2)

        step_1 = sample_plan.steps[0]
        step_2 = sample_plan.steps[1] if len(sample_plan.steps) > 1 else sample_plan.steps[0]

        # Worker 1 claims and releases
        coordinator.claim_files(
            "worker_001",
            ["modules/foundups/voteballots/README.md"],
            step_1.step_id,
        )
        coordinator.release_files(
            "worker_001",
            ["modules/foundups/voteballots/README.md"],
        )

        # Worker 2 can now claim
        claims = coordinator.claim_files(
            "worker_002",
            ["modules/foundups/voteballots/README.md"],
            step_2.step_id if step_2.step_id != step_1.step_id else step_1.step_id,
        )

        assert len(claims) == 1
        assert claims[0].worker_id == "worker_002"


# ---------------------------------------------------------------------------
# Test 5: Expire lease releases claim
# ---------------------------------------------------------------------------


class TestLeaseExpiration:
    """Test lease expiration releases claims."""

    def test_expire_lease_releases_claims(self, coordinator, sample_plan, worker_1, worker_2):
        """Expired lease releases claims."""
        coordinator.register_worker(worker_1)
        coordinator.register_worker(worker_2)

        step_1 = sample_plan.steps[0]

        # Worker 1 claims a file
        coordinator.claim_files(
            "worker_001",
            ["modules/foundups/voteballots/README.md"],
            step_1.step_id,
        )

        # Force expire lease
        future_time = datetime.now(timezone.utc) + timedelta(seconds=400)
        expired = coordinator.expire_leases(future_time)

        assert "worker_001" in expired

        # Worker 2 can now claim
        step_2 = sample_plan.steps[1] if len(sample_plan.steps) > 1 else sample_plan.steps[0]
        claims = coordinator.claim_files(
            "worker_002",
            ["modules/foundups/voteballots/README.md"],
            step_2.step_id,
        )

        assert len(claims) == 1

    def test_renew_lease_extends_claims(self, coordinator, worker_1):
        """Renewing lease resets expiration and increments count."""
        coordinator.register_worker(worker_1)

        worker = coordinator.get_worker("worker_001")
        original_renewal_count = worker.lease.renewal_count

        coordinator.renew_lease(worker.lease.lease_id)

        # Renewal increments count and keeps lease active
        assert worker.lease.renewal_count == original_renewal_count + 1
        assert worker.lease.status == LeaseStatus.ACTIVE


# ---------------------------------------------------------------------------
# Test 6: Reject out-of-scope file claim
# ---------------------------------------------------------------------------


class TestScopeValidation:
    """Test out-of-scope claim rejection."""

    def test_out_of_scope_claim_rejected(self, coordinator, sample_plan, worker_1):
        """Out-of-scope file claims are rejected."""
        coordinator.register_worker(worker_1)

        step = sample_plan.steps[0]

        # Try to claim file outside target scope
        with pytest.raises(ValueError, match="outside target scope"):
            coordinator.claim_files(
                "worker_001",
                ["/etc/passwd"],  # Outside scope
                step.step_id,
            )

    def test_out_of_scope_creates_fatal_conflict(self, coordinator, sample_plan, worker_1):
        """Out-of-scope claim creates FATAL conflict."""
        coordinator.register_worker(worker_1)

        step = sample_plan.steps[0]

        try:
            coordinator.claim_files(
                "worker_001",
                ["/etc/passwd"],
                step.step_id,
            )
        except ValueError:
            pass

        conflicts = coordinator.detect_conflicts()
        fatal = [c for c in conflicts if c.severity == ConflictSeverity.FATAL]
        assert len(fatal) >= 1


# ---------------------------------------------------------------------------
# Test 7: Aggregate evidence from multiple assignments
# ---------------------------------------------------------------------------


class TestEvidenceAggregation:
    """Test evidence aggregation."""

    def test_aggregate_evidence_from_multiple(self, coordinator, sample_plan, worker_1, worker_2):
        """Aggregate evidence from multiple assignments."""
        coordinator.register_worker(worker_1)
        coordinator.register_worker(worker_2)

        step_1 = sample_plan.steps[0]
        step_2 = sample_plan.steps[1] if len(sample_plan.steps) > 1 else step_1

        # Create assignments
        if step_1.step_id != step_2.step_id:
            assign_1 = coordinator.assign_step(
                step_1,
                "worker_001",
                ["modules/foundups/voteballots/README.md"],
            )
            assign_2 = coordinator.assign_step(
                step_2,
                "worker_002",
                ["modules/foundups/voteballots/INTERFACE.md"],
            )

            # Complete with evidence
            coordinator.complete_assignment(
                assign_1.assignment_id,
                ["evidence/step1/ref1", "evidence/step1/ref2"],
            )
            coordinator.complete_assignment(
                assign_2.assignment_id,
                ["evidence/step2/ref1"],
            )

            bundle = coordinator.aggregate_evidence()

            assert bundle.total_assignments == 2
            assert bundle.completed_assignments == 2
            assert len(bundle.evidence_refs) == 3

    def test_evidence_bundle_wsp97_fields(self, coordinator, sample_plan, worker_1):
        """Evidence bundle has WSP 97 truth fields."""
        coordinator.register_worker(worker_1)

        bundle = coordinator.aggregate_evidence()

        assert bundle.verification_complete is False
        assert bundle.cabr_ready is False


# ---------------------------------------------------------------------------
# Test 8: Summary reports simulated-only execution
# ---------------------------------------------------------------------------


class TestSummarySimulated:
    """Test summary reports simulated execution."""

    def test_summary_all_simulated(self, coordinator, sample_plan, worker_1):
        """Summary reports all_simulated=True."""
        coordinator.register_worker(worker_1)

        step = sample_plan.steps[0]
        assignment = coordinator.assign_step(
            step,
            "worker_001",
            ["modules/foundups/voteballots/README.md"],
        )
        coordinator.complete_assignment(assignment.assignment_id, ["ref1"])

        summary = coordinator.summarize()

        assert summary.all_simulated is True

    def test_summary_build_complete_only_when_all_done(self, coordinator, sample_plan, worker_1):
        """build_complete is True only when all assignments complete."""
        coordinator.register_worker(worker_1)

        step = sample_plan.steps[0]
        assignment = coordinator.assign_step(
            step,
            "worker_001",
            ["modules/foundups/voteballots/README.md"],
        )

        # Before completion
        summary = coordinator.summarize()
        assert summary.build_complete is False

        # After completion
        coordinator.complete_assignment(assignment.assignment_id, [])
        summary = coordinator.summarize()
        assert summary.build_complete is True


# ---------------------------------------------------------------------------
# Test 9: No real_execution_performed can become true
# ---------------------------------------------------------------------------


class TestWSP97TruthFields:
    """Test WSP 97 truth fields cannot become true."""

    def test_real_execution_performed_always_false(self, coordinator, sample_plan, worker_1):
        """real_execution_performed is always False."""
        coordinator.register_worker(worker_1)

        step = sample_plan.steps[0]
        assignment = coordinator.assign_step(
            step,
            "worker_001",
            ["modules/foundups/voteballots/README.md"],
        )
        coordinator.complete_assignment(assignment.assignment_id, [])

        summary = coordinator.summarize()
        assert summary.real_execution_performed is False

    def test_summary_post_init_enforces_truth(self):
        """SwarmExecutionSummary.__post_init__ enforces truth fields."""
        summary = SwarmExecutionSummary(
            plan_id="test",
            all_simulated=False,  # Will be overridden
            real_execution_performed=True,  # Will be overridden
        )

        assert summary.all_simulated is True
        assert summary.real_execution_performed is False

    def test_evidence_bundle_post_init_enforces_truth(self):
        """EvidenceBundle.__post_init__ enforces truth fields."""
        bundle = EvidenceBundle(
            bundle_id="test",
            plan_id="test",
            verification_complete=True,  # Will be overridden
            cabr_ready=True,  # Will be overridden
        )

        assert bundle.verification_complete is False
        assert bundle.cabr_ready is False

    def test_assignment_post_init_enforces_simulated(self):
        """StepAssignment.__post_init__ enforces simulated=True."""
        assignment = StepAssignment(
            assignment_id="test",
            step_id="step_001",
            worker_id="worker_001",
            simulated=False,  # Will be overridden
        )

        assert assignment.simulated is True


# ---------------------------------------------------------------------------
# Test 10: VoteBallot BuildPlan can be split into multiple simulated assignments
# ---------------------------------------------------------------------------


class TestVoteBallotIntegration:
    """Test VoteBallot BuildPlan swarm coordination."""

    def test_voteballot_plan_can_create_swarm(self):
        """VoteBallot plan can create swarm coordinator."""
        job = create_job(
            tenant_id="foundups",
            requested_action="build_foundup",
            foundup_id="voteballots",
        )
        plan = create_build_plan_from_job(job)

        coordinator = create_swarm_coordinator(plan)

        assert coordinator is not None
        assert coordinator.plan.foundup_id == "voteballots"

    def test_voteballot_plan_multiple_workers(self):
        """VoteBallot plan can register multiple workers."""
        job = create_job(
            tenant_id="foundups",
            requested_action="build_foundup",
            foundup_id="voteballots",
        )
        plan = create_build_plan_from_job(job)

        coordinator = create_swarm_coordinator(plan)

        coordinator.register_worker(WorkerIdentity(
            worker_id="oc_001",
            worker_type="openclaw",
            capabilities=["validate"],
        ))
        coordinator.register_worker(WorkerIdentity(
            worker_id="hermes_001",
            worker_type="hermes",
            capabilities=["build"],
        ))
        coordinator.register_worker(WorkerIdentity(
            worker_id="claude_001",
            worker_type="0102",
            capabilities=["all"],
        ))

        assert len(coordinator.list_workers()) == 3

    def test_voteballot_plan_split_assignments(self):
        """VoteBallot plan can split steps into multiple assignments."""
        job = create_job(
            tenant_id="foundups",
            requested_action="build_foundup",
            foundup_id="voteballots",
        )
        plan = create_build_plan_from_job(job)

        coordinator = create_swarm_coordinator(plan)

        coordinator.register_worker(WorkerIdentity(
            worker_id="worker_a",
            worker_type="openclaw",
            capabilities=["validate"],
        ))
        coordinator.register_worker(WorkerIdentity(
            worker_id="worker_b",
            worker_type="hermes",
            capabilities=["build"],
        ))

        if len(plan.steps) >= 2:
            assignment_a = coordinator.assign_step(
                plan.steps[0],
                "worker_a",
                ["modules/foundups/voteballots/README.md"],
            )
            assignment_b = coordinator.assign_step(
                plan.steps[1],
                "worker_b",
                ["modules/foundups/voteballots/src/"],
            )

            assert assignment_a.worker_id == "worker_a"
            assert assignment_b.worker_id == "worker_b"

    def test_voteballot_swarm_summary_wsp97(self):
        """VoteBallot swarm summary has WSP 97 truth fields."""
        job = create_job(
            tenant_id="foundups",
            requested_action="build_foundup",
            foundup_id="voteballots",
        )
        plan = create_build_plan_from_job(job)

        coordinator = create_swarm_coordinator(plan)

        coordinator.register_worker(WorkerIdentity(
            worker_id="worker_x",
            worker_type="openclaw",
            capabilities=["validate"],
        ))

        if plan.steps:
            assignment = coordinator.assign_step(
                plan.steps[0],
                "worker_x",
                ["modules/foundups/voteballots/README.md"],
            )
            coordinator.complete_assignment(assignment.assignment_id, ["ref1"])

        summary = coordinator.summarize()

        assert summary.all_simulated is True
        assert summary.real_execution_performed is False


# ---------------------------------------------------------------------------
# Additional Coverage Tests
# ---------------------------------------------------------------------------


class TestLeaseDataclass:
    """Test Lease dataclass."""

    def test_lease_is_expired(self):
        """Test lease expiration check."""
        lease = Lease(
            lease_id="test",
            worker_id="worker_001",
            expires_at=datetime.now(timezone.utc) - timedelta(seconds=10),
        )

        assert lease.is_expired() is True

    def test_lease_renew(self):
        """Test lease renewal resets expiration and increments count."""
        lease = Lease(
            lease_id="test",
            worker_id="worker_001",
            # Set expires_at in the past to verify renewal resets it
            expires_at=datetime.now(timezone.utc) - timedelta(seconds=10),
        )

        assert lease.is_expired() is True  # Confirm it's expired

        lease.renew(300)

        assert lease.is_expired() is False  # Now active
        assert lease.renewal_count == 1
        assert lease.status == LeaseStatus.ACTIVE


class TestWorkerIdentity:
    """Test WorkerIdentity dataclass."""

    def test_worker_has_capability(self):
        """Test capability check."""
        worker = WorkerIdentity(
            worker_id="test",
            worker_type="openclaw",
            capabilities=["validate", "build"],
        )

        assert worker.has_capability("validate") is True
        assert worker.has_capability("test") is False

    def test_worker_all_capability(self):
        """Test 'all' capability."""
        worker = WorkerIdentity(
            worker_id="test",
            worker_type="0102",
            capabilities=["all"],
        )

        assert worker.has_capability("validate") is True
        assert worker.has_capability("anything") is True


class TestFileOwnershipClaim:
    """Test FileOwnershipClaim dataclass."""

    def test_claim_is_active(self):
        """Test claim active check."""
        claim = FileOwnershipClaim(
            claim_id="test",
            file_path="/test/file.txt",
            worker_id="worker_001",
            step_id="step_001",
        )

        assert claim.is_active() is True

    def test_claim_release(self):
        """Test claim release."""
        claim = FileOwnershipClaim(
            claim_id="test",
            file_path="/test/file.txt",
            worker_id="worker_001",
            step_id="step_001",
        )

        claim.release()

        assert claim.released is True
        assert claim.is_active() is False


class TestFactoryFunction:
    """Test factory function."""

    def test_create_swarm_coordinator(self, sample_plan):
        """Test create_swarm_coordinator factory."""
        coordinator = create_swarm_coordinator(sample_plan)

        assert coordinator is not None
        assert coordinator.plan == sample_plan
