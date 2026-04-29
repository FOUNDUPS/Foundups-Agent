#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test suite for BuildPlanExecutor interface stub.

WSP 97 Truth Boundary Tests:
  - dry_run=True default
  - Real execution returns BLOCKED
  - ExecutionReceipt has truth fields False
  - No CABR/reward/payout/token fields

Test Coverage:
  1. Executor can be instantiated with dry_run=True
  2. validate_plan rejects mode=REAL plans without approval gates
  3. simulate_step returns StepExecutionResult
  4. execute_step with dry_run=True delegates to simulation
  5. execute_step with dry_run=False is blocked
  6. mutating actions are blocked in stub
  7. ExecutionReceipt has WSP_97 truth fields false
  8. No CABR/reward/payout/token fields exist
  9. VoteBallot generated BuildPlan can be validated and simulated without real execution
"""

import pytest
from pathlib import Path

from modules.foundups.agent.src.build_plan import (
    BuildMode,
    BuildPlan,
    BuildPlanStatus,
    BuildScope,
    BuildStep,
    BuildStepAction,
    BuildTarget,
    BuildGate,
    GateType,
    GateStatus,
    StepStatus,
    create_standard_build_steps,
)
from modules.foundups.agent.src.build_plan_executor import (
    BuildPlanExecutor,
    DiffSummary,
    ExecutionBlockReason,
    ExecutionMode,
    ExecutionReceipt,
    GateEvaluationResult,
    StepExecutionContext,
    StepExecutionResult,
    StepExecutionStatus,
    ValidationResult,
    MUTATING_ACTIONS,
    SAFE_SIMULATION_ACTIONS,
    get_executor,
)
from modules.foundups.agent.src.build_plan_generator import (
    create_build_plan_from_job,
)
from modules.communication.moltbot_bridge.src.foundup_job_contract import (
    FoundUpJob,
    JobStatus,
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
        build_plan_id="bp_test_001",
        foundup_id="voteballots",
        tenant_id="foundups",
        mode=BuildMode.DRY_RUN,
        dry_run=True,
        status=BuildPlanStatus.DRAFT,
        target=sample_target,
    )
    plan.steps = create_standard_build_steps("modules/foundups/voteballots")
    return plan


@pytest.fixture
def sample_step() -> BuildStep:
    """Create a sample BuildStep for testing."""
    return BuildStep(
        step_id="step_test_001",
        step_name="Test Step",
        action=BuildStepAction.VALIDATE_GENESIS,
        status=StepStatus.PENDING,
        evidence_required=True,
    )


@pytest.fixture
def executor() -> BuildPlanExecutor:
    """Create a BuildPlanExecutor in dry-run mode."""
    return BuildPlanExecutor(dry_run=True)


# ---------------------------------------------------------------------------
# Test 1: Executor can be instantiated with dry_run=True
# ---------------------------------------------------------------------------


class TestExecutorInstantiation:
    """Test BuildPlanExecutor instantiation."""

    def test_instantiate_with_dry_run_true(self):
        """Executor can be instantiated with dry_run=True."""
        executor = BuildPlanExecutor(dry_run=True)
        assert executor.dry_run is True
        assert executor.is_dry_run() is True

    def test_default_is_dry_run(self):
        """Executor defaults to dry_run=True."""
        executor = BuildPlanExecutor()
        assert executor.dry_run is True

    def test_factory_function_dry_run(self):
        """get_executor factory returns dry-run executor."""
        executor = get_executor()
        assert executor.dry_run is True
        assert isinstance(executor, BuildPlanExecutor)


# ---------------------------------------------------------------------------
# Test 2: validate_plan rejects mode=REAL plans without approval gates
# ---------------------------------------------------------------------------


class TestValidatePlan:
    """Test plan validation."""

    def test_validate_plan_rejects_real_without_approval(self, sample_target):
        """validate_plan rejects mode=REAL plans without approval gates."""
        plan = BuildPlan(
            build_plan_id="bp_real_001",
            foundup_id="voteballots",
            tenant_id="foundups",
            mode=BuildMode.REAL,
            dry_run=False,
            target=sample_target,
        )
        executor = BuildPlanExecutor()
        result = executor.validate_plan(plan)

        assert result.valid is False
        assert result.error_code == "MODE_REAL_NO_APPROVAL"
        assert "human_approval_gate" in result.error_message.lower()

    def test_validate_plan_accepts_dry_run(self, sample_plan, executor):
        """validate_plan accepts dry_run plans."""
        result = executor.validate_plan(sample_plan)
        assert result.valid is True

    def test_validate_plan_requires_plan_id(self, sample_target, executor):
        """BuildPlan itself requires build_plan_id (dataclass validation)."""
        # BuildPlan.__post_init__ raises ValueError for empty build_plan_id
        with pytest.raises(ValueError, match="build_plan_id is required"):
            BuildPlan(
                build_plan_id="",
                foundup_id="voteballots",
                tenant_id="foundups",
                target=sample_target,
            )

    def test_validate_plan_requires_foundup_id(self, sample_target, executor):
        """BuildPlan itself requires foundup_id (dataclass validation)."""
        # BuildPlan.__post_init__ raises ValueError for empty foundup_id
        with pytest.raises(ValueError, match="foundup_id is required"):
            BuildPlan(
                build_plan_id="bp_test_001",
                foundup_id="",
                tenant_id="foundups",
                target=sample_target,
            )

    def test_validate_plan_requires_target(self, executor):
        """validate_plan requires target."""
        plan = BuildPlan(
            build_plan_id="bp_test_001",
            foundup_id="voteballots",
            tenant_id="foundups",
            target=None,
        )
        result = executor.validate_plan(plan)
        assert result.valid is False
        assert result.error_code == "MISSING_TARGET"


# ---------------------------------------------------------------------------
# Test 3: simulate_step returns StepExecutionResult
# ---------------------------------------------------------------------------


class TestSimulateStep:
    """Test step simulation."""

    def test_simulate_step_returns_result(self, sample_plan, sample_step, executor):
        """simulate_step returns StepExecutionResult."""
        result = executor.simulate_step(sample_plan, sample_step)

        assert isinstance(result, StepExecutionResult)
        assert result.step_id == sample_step.step_id
        assert result.step_name == sample_step.step_name
        assert result.action == sample_step.action

    def test_simulate_step_status_simulated(self, sample_plan, sample_step, executor):
        """simulate_step returns SIMULATED status."""
        result = executor.simulate_step(sample_plan, sample_step)

        assert result.status == StepExecutionStatus.SIMULATED
        assert result.simulated is True
        assert result.dry_run is True

    def test_simulate_step_has_evidence_refs(self, sample_plan, sample_step, executor):
        """simulate_step includes evidence_refs."""
        result = executor.simulate_step(sample_plan, sample_step)

        assert len(result.evidence_refs) > 0
        assert "simulation" in result.evidence_refs[0]

    def test_simulate_mutating_action_returns_planned_diff(self, sample_plan, executor):
        """simulate_step for mutating actions returns planned_diff."""
        mutating_step = BuildStep(
            step_id="step_create",
            step_name="Create Module",
            action=BuildStepAction.CREATE_MODULE,
            status=StepStatus.PENDING,
        )
        result = executor.simulate_step(sample_plan, mutating_step)

        assert result.status == StepExecutionStatus.SIMULATED
        assert result.planned_diff is not None
        assert isinstance(result.planned_diff, DiffSummary)


# ---------------------------------------------------------------------------
# Test 4: execute_step with dry_run=True delegates to simulation
# ---------------------------------------------------------------------------


class TestExecuteStepDryRun:
    """Test execute_step in dry-run mode."""

    def test_execute_step_dry_run_delegates_to_simulation(
        self, sample_plan, sample_step, executor
    ):
        """execute_step with dry_run=True delegates to simulate_step."""
        result = executor.execute_step(sample_plan, sample_step)

        assert result.status == StepExecutionStatus.SIMULATED
        assert result.dry_run is True
        assert result.simulated is True

    def test_execute_step_dry_run_no_actual_diff(
        self, sample_plan, sample_step, executor
    ):
        """execute_step in dry-run never produces actual_diff."""
        result = executor.execute_step(sample_plan, sample_step)

        assert result.actual_diff is None


# ---------------------------------------------------------------------------
# Test 5: execute_step with dry_run=False is blocked
# ---------------------------------------------------------------------------


class TestExecuteStepRealBlocked:
    """Test execute_step blocks real execution."""

    def test_execute_step_real_is_blocked(self, sample_plan, sample_step):
        """execute_step with dry_run=False returns BLOCKED."""
        executor = BuildPlanExecutor(dry_run=False)
        result = executor.execute_step(sample_plan, sample_step)

        assert result.status == StepExecutionStatus.BLOCKED
        assert result.dry_run is False
        assert result.simulated is False

    def test_execute_step_real_error_code(self, sample_plan, sample_step):
        """execute_step with dry_run=False has correct error code."""
        executor = BuildPlanExecutor(dry_run=False)
        result = executor.execute_step(sample_plan, sample_step)

        assert result.error_code == ExecutionBlockReason.REAL_EXECUTION_NOT_IMPLEMENTED.value
        assert "not implemented" in result.error_message.lower()


# ---------------------------------------------------------------------------
# Test 6: mutating actions are blocked in stub
# ---------------------------------------------------------------------------


class TestMutatingActionsBlocked:
    """Test mutating actions are identified correctly."""

    def test_mutating_actions_constant_exists(self):
        """MUTATING_ACTIONS constant is defined."""
        assert isinstance(MUTATING_ACTIONS, frozenset)
        assert len(MUTATING_ACTIONS) > 0

    def test_safe_actions_constant_exists(self):
        """SAFE_SIMULATION_ACTIONS constant is defined."""
        assert isinstance(SAFE_SIMULATION_ACTIONS, frozenset)
        assert len(SAFE_SIMULATION_ACTIONS) > 0

    def test_create_actions_are_mutating(self):
        """CREATE_* actions are in MUTATING_ACTIONS."""
        assert BuildStepAction.CREATE_MODULE in MUTATING_ACTIONS
        assert BuildStepAction.CREATE_SPEC in MUTATING_ACTIONS
        assert BuildStepAction.CREATE_TEST in MUTATING_ACTIONS

    def test_validate_actions_are_safe(self):
        """VALIDATE_* actions are in SAFE_SIMULATION_ACTIONS."""
        assert BuildStepAction.VALIDATE_GENESIS in SAFE_SIMULATION_ACTIONS
        assert BuildStepAction.VALIDATE_MANIFEST in SAFE_SIMULATION_ACTIONS

    def test_dry_run_executor_simulates_mutating_actions(self, sample_plan, executor):
        """dry_run executor simulates mutating actions without blocking."""
        mutating_step = BuildStep(
            step_id="step_mut",
            step_name="Create Module",
            action=BuildStepAction.CREATE_MODULE,
            status=StepStatus.PENDING,
        )
        result = executor.execute_step(sample_plan, mutating_step)

        # In dry-run mode, mutating actions are simulated (not blocked)
        assert result.status == StepExecutionStatus.SIMULATED
        assert result.planned_diff is not None


# ---------------------------------------------------------------------------
# Test 7: ExecutionReceipt has WSP_97 truth fields false
# ---------------------------------------------------------------------------


class TestExecutionReceiptTruthFields:
    """Test ExecutionReceipt WSP 97 truth fields."""

    def test_receipt_verification_complete_false(self, sample_plan, executor):
        """ExecutionReceipt.verification_complete is always False."""
        results = []
        receipt = executor.create_execution_receipt(sample_plan, results)

        assert receipt.verification_complete is False

    def test_receipt_cabr_ready_false(self, sample_plan, executor):
        """ExecutionReceipt.cabr_ready is always False."""
        results = []
        receipt = executor.create_execution_receipt(sample_plan, results)

        assert receipt.cabr_ready is False

    def test_receipt_payout_ready_false(self, sample_plan, executor):
        """ExecutionReceipt.payout_ready is always False."""
        results = []
        receipt = executor.create_execution_receipt(sample_plan, results)

        assert receipt.payout_ready is False

    def test_receipt_real_execution_performed_false(self, sample_plan, executor):
        """ExecutionReceipt.real_execution_performed is False in stub."""
        results = []
        receipt = executor.create_execution_receipt(sample_plan, results)

        assert receipt.real_execution_performed is False

    def test_receipt_post_init_enforces_truth_fields(self):
        """ExecutionReceipt.__post_init__ enforces truth fields."""
        # Even if we try to set True, __post_init__ resets to False
        receipt = ExecutionReceipt(
            receipt_id="rcpt_test",
            plan_id="bp_test",
            verification_complete=True,  # Will be overridden
            cabr_ready=True,  # Will be overridden
            payout_ready=True,  # Will be overridden
        )
        assert receipt.verification_complete is False
        assert receipt.cabr_ready is False
        assert receipt.payout_ready is False


# ---------------------------------------------------------------------------
# Test 8: No CABR/reward/payout/token fields exist
# ---------------------------------------------------------------------------


class TestNoCABRFields:
    """Test that no CABR/reward/payout/token fields exist."""

    def test_step_execution_result_no_cabr_fields(self):
        """StepExecutionResult has no CABR/reward/payout fields."""
        import inspect

        sig = inspect.signature(StepExecutionResult)
        param_names = set(sig.parameters.keys())

        forbidden_patterns = ["cabr", "reward", "payout", "token", "ups", "f_i"]
        for pattern in forbidden_patterns:
            for name in param_names:
                assert pattern not in name.lower(), f"Found forbidden field: {name}"

    def test_execution_receipt_no_reward_fields(self):
        """ExecutionReceipt has no reward/UPS/F_i fields."""
        import inspect

        sig = inspect.signature(ExecutionReceipt)
        param_names = set(sig.parameters.keys())

        forbidden_patterns = ["reward", "ups", "f_i", "token_amount", "token_type"]
        for pattern in forbidden_patterns:
            for name in param_names:
                assert pattern not in name.lower(), f"Found forbidden field: {name}"

    def test_receipt_dict_no_cabr_keys(self, sample_plan, executor):
        """ExecutionReceipt.to_dict() has no CABR keys."""
        results = []
        receipt = executor.create_execution_receipt(sample_plan, results)
        receipt_dict = receipt.to_dict()

        forbidden_keys = ["cabr_score", "reward_amount", "ups_amount", "token_type"]
        for key in forbidden_keys:
            assert key not in receipt_dict, f"Found forbidden key: {key}"


# ---------------------------------------------------------------------------
# Test 9: VoteBallot generated BuildPlan can be validated and simulated
# ---------------------------------------------------------------------------


class TestVoteBallotIntegration:
    """Test VoteBallot BuildPlan can be validated and simulated."""

    def test_voteballot_job_generates_valid_plan(self):
        """VoteBallot job generates a valid BuildPlan."""
        job = create_job(
            tenant_id="foundups",
            requested_action="build_foundup",
            foundup_id="voteballots",
            intent_id="test_intent",
        )
        plan = create_build_plan_from_job(job)

        assert plan is not None
        assert plan.foundup_id == "voteballots"
        assert plan.dry_run is True
        assert plan.mode == BuildMode.DRY_RUN

    def test_voteballot_plan_validates(self):
        """VoteBallot generated plan passes validation."""
        job = create_job(
            tenant_id="foundups",
            requested_action="build_foundup",
            foundup_id="voteballots",
            intent_id="test_intent",
        )
        plan = create_build_plan_from_job(job)

        executor = BuildPlanExecutor(dry_run=True)
        validation = executor.validate_plan(plan)

        assert validation.valid is True

    def test_voteballot_plan_steps_can_simulate(self):
        """VoteBallot plan steps can be simulated."""
        job = create_job(
            tenant_id="foundups",
            requested_action="build_foundup",
            foundup_id="voteballots",
            intent_id="test_intent",
        )
        plan = create_build_plan_from_job(job)

        executor = BuildPlanExecutor(dry_run=True)
        results = []

        for step in plan.steps:
            result = executor.execute_step(plan, step)
            results.append(result)

        assert len(results) == len(plan.steps)
        for result in results:
            assert result.status == StepExecutionStatus.SIMULATED

    def test_voteballot_plan_receipt_has_truth_fields(self):
        """VoteBallot plan execution receipt has WSP 97 truth fields False."""
        job = create_job(
            tenant_id="foundups",
            requested_action="build_foundup",
            foundup_id="voteballots",
            intent_id="test_intent",
        )
        plan = create_build_plan_from_job(job)

        executor = BuildPlanExecutor(dry_run=True)
        results = [executor.execute_step(plan, step) for step in plan.steps]
        receipt = executor.create_execution_receipt(plan, results)

        assert receipt.verification_complete is False
        assert receipt.cabr_ready is False
        assert receipt.payout_ready is False
        assert receipt.real_execution_performed is False

    def test_voteballot_plan_no_real_execution(self):
        """VoteBallot plan cannot execute with dry_run=False."""
        job = create_job(
            tenant_id="foundups",
            requested_action="build_foundup",
            foundup_id="voteballots",
            intent_id="test_intent",
        )
        plan = create_build_plan_from_job(job)

        # Force dry_run=False
        executor = BuildPlanExecutor(dry_run=False)
        step = plan.steps[0] if plan.steps else None

        if step:
            result = executor.execute_step(plan, step)
            assert result.status == StepExecutionStatus.BLOCKED
            assert result.error_code == ExecutionBlockReason.REAL_EXECUTION_NOT_IMPLEMENTED.value


# ---------------------------------------------------------------------------
# Additional Coverage Tests
# ---------------------------------------------------------------------------


class TestGateEvaluation:
    """Test gate evaluation."""

    def test_evaluate_genesis_gate(self, sample_plan, executor):
        """evaluate_gate returns result for genesis_gate."""
        result = executor.evaluate_gate(sample_plan, GateType.GENESIS_GATE)

        assert isinstance(result, GateEvaluationResult)
        assert result.gate_type == GateType.GENESIS_GATE
        assert result.passed is True  # Has target

    def test_evaluate_dry_run_gate(self, sample_plan, executor):
        """evaluate_gate returns result for dry_run_gate."""
        result = executor.evaluate_gate(sample_plan, GateType.DRY_RUN_GATE)

        assert result.gate_type == GateType.DRY_RUN_GATE
        assert result.passed is True  # Plan is dry_run

    def test_evaluate_human_approval_gate_requires_human(self, sample_plan, executor):
        """Human approval gate requires human."""
        result = executor.evaluate_gate(sample_plan, GateType.HUMAN_APPROVAL_GATE)

        assert result.requires_human is True
        assert result.passed is False  # Not pre-approved


class TestStepExecutionContext:
    """Test StepExecutionContext dataclass."""

    def test_context_to_dict(self, sample_plan, sample_step):
        """StepExecutionContext.to_dict() works."""
        context = StepExecutionContext(
            plan=sample_plan,
            step=sample_step,
            step_index=0,
            dry_run=True,
        )
        d = context.to_dict()

        assert d["plan_id"] == sample_plan.build_plan_id
        assert d["step_id"] == sample_step.step_id
        assert d["dry_run"] is True


class TestDiffSummary:
    """Test DiffSummary dataclass."""

    def test_diff_summary_to_dict(self):
        """DiffSummary.to_dict() works."""
        diff = DiffSummary(
            files_created=2,
            files_modified=1,
            lines_added=50,
        )
        d = diff.to_dict()

        assert d["files_created"] == 2
        assert d["files_modified"] == 1
        assert d["lines_added"] == 50
