#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BuildPlan Dataclass Tests

Verifies the BuildPlan interface from FOUNDUP_BUILD_PLAN_CONTRACT.md.

WSP 97 TRUTH BOUNDARIES:
  - Tests verify dry_run=True by default
  - Tests verify real builds are blocked by default
  - Tests verify no CABR/payout/reward/token fields exist
  - Tests verify scope validation

Test Coverage:
  1. BuildPlan can be constructed with dry_run defaults
  2. to_dict() preserves identity and target
  3. Real builds are blocked by default
  4. is_real_build_allowed() requires human approval + gates + rollback
  5. Blocked operations are not represented as executable actions
  6. VoteBallot example plan can be represented (SPEC_EXAMPLE_NOT_EXECUTED)
  7. No cabr_ready/payout_ready/reward/token fields exist
  8. validate_scope rejects paths outside target module

NAVIGATION:
  -> Tests: modules/foundups/agent/src/build_plan.py
  -> Spec: modules/foundups/docs/FOUNDUP_BUILD_PLAN_CONTRACT.md
"""

from __future__ import annotations

import pytest

from modules.foundups.agent.src.build_plan import (
    BLOCKED_PATH_PATTERNS,
    BuildEvidence,
    BuildGate,
    BuildMode,
    BuildPlan,
    BuildPlanStatus,
    BuildScope,
    BuildStep,
    BuildStepAction,
    BuildTarget,
    GateStatus,
    GateType,
    StepStatus,
    create_build_plan,
    create_standard_build_steps,
    generate_build_plan_id,
    is_blocked_path,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def voteballot_target() -> BuildTarget:
    """Create VoteBallot build target."""
    return BuildTarget(
        module_path="modules/foundups/voteballots",
        pwa_surface_path="public/member/foundups/voteballots/",
    )


@pytest.fixture
def voteballot_plan(voteballot_target: BuildTarget) -> BuildPlan:
    """Create VoteBallot build plan with defaults."""
    plan = create_build_plan(
        foundup_id="voteballots",
        tenant_id="012",
        module_path="modules/foundups/voteballots",
        intent_id="internal_poc_voteballot_build",
    )
    plan.steps = create_standard_build_steps("modules/foundups/voteballots")
    return plan


# ---------------------------------------------------------------------------
# Test 1: BuildPlan Constructed with Dry-Run Defaults
# ---------------------------------------------------------------------------


class TestBuildPlanDefaults:
    """Test BuildPlan construction with dry_run defaults."""

    def test_buildplan_defaults_to_dry_run(self) -> None:
        """BuildPlan defaults to dry_run=True."""
        plan = create_build_plan(
            foundup_id="test",
            tenant_id="012",
            module_path="modules/foundups/test",
        )

        assert plan.dry_run is True
        assert plan.mode == BuildMode.DRY_RUN
        assert plan.status == BuildPlanStatus.DRAFT

    def test_buildplan_has_default_gates(self) -> None:
        """BuildPlan creates default gates."""
        plan = create_build_plan(
            foundup_id="test",
            tenant_id="012",
            module_path="modules/foundups/test",
        )

        # 8 default gates
        assert len(plan.gates) == 8

        # Check key gate types exist
        gate_types = {g.gate_type for g in plan.gates}
        assert GateType.GENESIS_GATE in gate_types
        assert GateType.DRY_RUN_GATE in gate_types
        assert GateType.TEST_GATE in gate_types
        assert GateType.HUMAN_APPROVAL_GATE in gate_types

    def test_buildplan_id_format(self) -> None:
        """BuildPlan ID follows format bp_{foundup}_{ts}_{random}."""
        plan_id = generate_build_plan_id("voteballots")

        assert plan_id.startswith("bp_voteballots_")
        parts = plan_id.split("_")
        assert len(parts) >= 4

    def test_build_target_auto_populates_paths(self) -> None:
        """BuildTarget auto-populates paths from module_path."""
        target = BuildTarget(module_path="modules/foundups/test")

        assert target.foundup_manifest_path == "modules/foundups/test/foundup_manifest.json"
        assert target.tests_path == "modules/foundups/test/tests/"
        assert target.docs_path == "modules/foundups/test/docs/"
        assert target.modlog_path == "modules/foundups/test/ModLog.md"
        assert target.testmodlog_path == "modules/foundups/test/tests/TestModLog.md"
        assert target.readme_path == "modules/foundups/test/README.md"


# ---------------------------------------------------------------------------
# Test 2: to_dict() Preserves Identity and Target
# ---------------------------------------------------------------------------


class TestBuildPlanSerialization:
    """Test BuildPlan serialization."""

    def test_to_dict_preserves_identity(self, voteballot_plan: BuildPlan) -> None:
        """to_dict() preserves plan identity fields."""
        d = voteballot_plan.to_dict()

        assert d["build_plan_id"] == voteballot_plan.build_plan_id
        assert d["foundup_id"] == "voteballots"
        assert d["tenant_id"] == "012"
        assert d["intent_id"] == "internal_poc_voteballot_build"
        assert d["mode"] == "dry_run"
        assert d["dry_run"] is True
        assert d["status"] == "draft"

    def test_to_dict_preserves_target(self, voteballot_plan: BuildPlan) -> None:
        """to_dict() preserves target paths."""
        d = voteballot_plan.to_dict()

        assert d["target"] is not None
        assert d["target"]["module_path"] == "modules/foundups/voteballots"
        assert "allowed_paths" in d["target"]
        assert "blocked_paths" in d["target"]

    def test_from_dict_roundtrip(self, voteballot_plan: BuildPlan) -> None:
        """from_dict(to_dict()) roundtrip preserves data."""
        d = voteballot_plan.to_dict()
        restored = BuildPlan.from_dict(d)

        assert restored.build_plan_id == voteballot_plan.build_plan_id
        assert restored.foundup_id == voteballot_plan.foundup_id
        assert restored.tenant_id == voteballot_plan.tenant_id
        assert restored.mode == voteballot_plan.mode
        assert restored.dry_run == voteballot_plan.dry_run
        assert restored.status == voteballot_plan.status
        assert len(restored.steps) == len(voteballot_plan.steps)
        assert len(restored.gates) == len(voteballot_plan.gates)


# ---------------------------------------------------------------------------
# Test 3: Real Builds Blocked by Default
# ---------------------------------------------------------------------------


class TestRealBuildBlocking:
    """Test that real builds are blocked by default."""

    def test_real_build_blocked_by_default(self, voteballot_plan: BuildPlan) -> None:
        """Real builds are blocked with default settings."""
        # Default plan has dry_run=True, mode=DRY_RUN
        assert voteballot_plan.is_real_build_allowed() is False

    def test_real_build_blocked_without_human_approval(
        self, voteballot_plan: BuildPlan
    ) -> None:
        """Real build blocked without human approval gate."""
        # Set mode to REAL, dry_run to False
        voteballot_plan.mode = BuildMode.REAL
        voteballot_plan.dry_run = False

        # Pass dry_run_gate and test_gate
        dry_run_gate = voteballot_plan.get_gate(GateType.DRY_RUN_GATE)
        test_gate = voteballot_plan.get_gate(GateType.TEST_GATE)
        if dry_run_gate:
            dry_run_gate.evaluate(passed=True, reason="dry-run passed")
        if test_gate:
            test_gate.evaluate(passed=True, reason="tests passed")

        # Still blocked - no human approval
        assert voteballot_plan.is_real_build_allowed() is False

    def test_real_build_blocked_without_dry_run_gate(
        self, voteballot_plan: BuildPlan
    ) -> None:
        """Real build blocked without prior dry-run."""
        voteballot_plan.mode = BuildMode.REAL
        voteballot_plan.dry_run = False

        # Pass human approval and test gates
        human_gate = voteballot_plan.get_gate(GateType.HUMAN_APPROVAL_GATE)
        test_gate = voteballot_plan.get_gate(GateType.TEST_GATE)
        if human_gate:
            human_gate.evaluate(passed=True, reason="approved")
        if test_gate:
            test_gate.evaluate(passed=True, reason="tests passed")

        # Blocked - dry_run_gate not passed
        assert voteballot_plan.is_real_build_allowed() is False


# ---------------------------------------------------------------------------
# Test 4: is_real_build_allowed() Requirements
# ---------------------------------------------------------------------------


class TestRealBuildAllowed:
    """Test is_real_build_allowed() complete requirements."""

    def test_real_build_allowed_with_all_requirements(
        self, voteballot_plan: BuildPlan
    ) -> None:
        """Real build allowed when all requirements met."""
        # Set mode and dry_run
        voteballot_plan.mode = BuildMode.REAL
        voteballot_plan.dry_run = False

        # Pass all required gates
        human_gate = voteballot_plan.get_gate(GateType.HUMAN_APPROVAL_GATE)
        dry_run_gate = voteballot_plan.get_gate(GateType.DRY_RUN_GATE)
        test_gate = voteballot_plan.get_gate(GateType.TEST_GATE)

        if human_gate:
            human_gate.evaluate(passed=True, reason="architect approved")
        if dry_run_gate:
            dry_run_gate.evaluate(passed=True, reason="dry-run succeeded")
        if test_gate:
            test_gate.evaluate(passed=True, reason="all tests passed")

        # Ensure rollback points exist (standard steps have them)
        assert voteballot_plan.has_rollback_points()

        # Now real build should be allowed
        assert voteballot_plan.is_real_build_allowed() is True

    def test_real_build_blocked_without_rollback_points(self) -> None:
        """Real build blocked without rollback points."""
        plan = create_build_plan(
            foundup_id="test",
            tenant_id="012",
            module_path="modules/foundups/test",
        )
        # No steps = no rollback points
        plan.steps = []

        plan.mode = BuildMode.REAL
        plan.dry_run = False

        # Pass all gates
        for gate in plan.gates:
            if gate.gate_type in (
                GateType.HUMAN_APPROVAL_GATE,
                GateType.DRY_RUN_GATE,
                GateType.TEST_GATE,
            ):
                gate.evaluate(passed=True, reason="passed")

        # No rollback points
        assert plan.has_rollback_points() is False
        assert plan.is_real_build_allowed() is False


# ---------------------------------------------------------------------------
# Test 5: Blocked Operations Not Executable
# ---------------------------------------------------------------------------


class TestBlockedOperations:
    """Test that blocked operations are not represented as executable."""

    def test_blocked_path_patterns_exist(self) -> None:
        """BLOCKED_PATH_PATTERNS contains protected paths."""
        assert len(BLOCKED_PATH_PATTERNS) > 0
        assert "**/wallet/**" in BLOCKED_PATH_PATTERNS
        assert "**/token/**" in BLOCKED_PATH_PATTERNS
        assert "**/reward/**" in BLOCKED_PATH_PATTERNS
        assert "**/payout/**" in BLOCKED_PATH_PATTERNS
        assert "**/cabr/**" in BLOCKED_PATH_PATTERNS

    def test_is_blocked_path_detects_wallet(self) -> None:
        """is_blocked_path() detects wallet paths."""
        assert is_blocked_path("modules/wallet/src/wallet.py") is True
        assert is_blocked_path("src/wallet/config.json") is True

    def test_is_blocked_path_detects_token(self) -> None:
        """is_blocked_path() detects token paths."""
        assert is_blocked_path("modules/token/src/token.py") is True

    def test_is_blocked_path_detects_reward(self) -> None:
        """is_blocked_path() detects reward paths."""
        assert is_blocked_path("modules/reward/payout.py") is True

    def test_is_blocked_path_allows_safe_paths(self) -> None:
        """is_blocked_path() allows safe module paths."""
        assert is_blocked_path("modules/foundups/voteballots/src/main.py") is False
        assert is_blocked_path("modules/foundups/test/tests/test_main.py") is False


# ---------------------------------------------------------------------------
# Test 6: VoteBallot Example Plan (SPEC_EXAMPLE_NOT_EXECUTED)
# ---------------------------------------------------------------------------


class TestVoteBallotExamplePlan:
    """Test VoteBallot example plan representation."""

    def test_voteballot_plan_matches_spec_example(
        self, voteballot_plan: BuildPlan
    ) -> None:
        """VoteBallot plan matches FOUNDUP_BUILD_PLAN_CONTRACT.md example."""
        # Identity matches spec
        assert voteballot_plan.foundup_id == "voteballots"
        assert voteballot_plan.tenant_id == "012"
        assert voteballot_plan.intent_id == "internal_poc_voteballot_build"
        assert voteballot_plan.requested_action == "build_foundup"
        assert voteballot_plan.dry_run is True
        assert voteballot_plan.plan_version == "1.0.0"

        # Target matches spec
        assert voteballot_plan.target is not None
        assert voteballot_plan.target.module_path == "modules/foundups/voteballots"

        # Has standard steps
        assert len(voteballot_plan.steps) == 12

        # Has gates
        assert len(voteballot_plan.gates) == 8

    def test_voteballot_plan_has_standard_step_sequence(
        self, voteballot_plan: BuildPlan
    ) -> None:
        """VoteBallot plan has standard 12-step sequence."""
        step_actions = [step.action for step in voteballot_plan.steps]

        expected_sequence = [
            BuildStepAction.VALIDATE_GENESIS,
            BuildStepAction.VALIDATE_MANIFEST,
            BuildStepAction.CREATE_SPEC,
            BuildStepAction.CREATE_TEST,
            BuildStepAction.CREATE_MODULE,
            BuildStepAction.UPDATE_MANIFEST,
            BuildStepAction.RUN_TESTS,
            BuildStepAction.UPDATE_MODLOG,
            BuildStepAction.UPDATE_TESTMODLOG,
            BuildStepAction.DRY_RUN_BUILD,
            BuildStepAction.SUBMIT_RECEIPT,
            BuildStepAction.REQUEST_APPROVAL,
        ]

        assert step_actions == expected_sequence

    def test_voteballot_plan_is_spec_example_not_executed(
        self, voteballot_plan: BuildPlan
    ) -> None:
        """VoteBallot plan status is DRAFT (not executed)."""
        # Plan is DRAFT = SPEC_EXAMPLE_NOT_EXECUTED
        assert voteballot_plan.status == BuildPlanStatus.DRAFT

        # No steps have been executed
        for step in voteballot_plan.steps:
            assert step.status == StepStatus.PENDING

        # No gates have been checked
        for gate in voteballot_plan.gates:
            assert gate.status == GateStatus.PENDING


# ---------------------------------------------------------------------------
# Test 7: No CABR/Payout/Reward/Token Fields
# ---------------------------------------------------------------------------


class TestNoCABRPayoutFields:
    """Test that no CABR/payout/reward/token fields exist."""

    def test_buildplan_has_no_cabr_fields(self, voteballot_plan: BuildPlan) -> None:
        """BuildPlan has no cabr_ready or similar fields."""
        d = voteballot_plan.to_dict()

        # No CABR/payout/reward/token fields
        assert "cabr_ready" not in d
        assert "payout_ready" not in d
        assert "reward" not in d
        assert "tokens" not in d
        assert "tokens_issued" not in d
        assert "payout_amount" not in d
        assert "verification_complete" not in d

    def test_buildplan_dict_keys_are_safe(self, voteballot_plan: BuildPlan) -> None:
        """BuildPlan dict contains only safe keys."""
        d = voteballot_plan.to_dict()

        # Check all keys are expected
        expected_keys = {
            "build_plan_id",
            "foundup_id",
            "tenant_id",
            "intent_id",
            "source_job_id",
            "requested_action",
            "mode",
            "dry_run",
            "status",
            "target",
            "steps",
            "gates",
            "evidence_refs",
            "created_at",
            "updated_at",
            "plan_version",
        }
        assert set(d.keys()) == expected_keys

    def test_buildgate_has_no_reward_fields(self) -> None:
        """BuildGate has no reward/token fields."""
        gate = BuildGate(
            gate_id="test_gate",
            gate_type=GateType.TEST_GATE,
        )
        d = gate.to_dict()

        assert "reward" not in d
        assert "tokens" not in d
        assert "payout" not in d

    def test_buildstep_has_no_reward_fields(self) -> None:
        """BuildStep has no reward/token fields."""
        step = BuildStep(
            step_id="step_01",
            step_name="Test step",
            action=BuildStepAction.RUN_TESTS,
        )
        d = step.to_dict()

        assert "reward" not in d
        assert "tokens" not in d
        assert "payout" not in d


# ---------------------------------------------------------------------------
# Test 8: validate_scope Rejects Paths Outside Target
# ---------------------------------------------------------------------------


class TestValidateScope:
    """Test validate_scope() rejects paths outside target module."""

    def test_validate_scope_allows_target_module(
        self, voteballot_plan: BuildPlan
    ) -> None:
        """validate_scope() allows paths within target module."""
        assert voteballot_plan.validate_scope(
            "modules/foundups/voteballots/src/main.py"
        ) is True
        assert voteballot_plan.validate_scope(
            "modules/foundups/voteballots/tests/test_main.py"
        ) is True
        assert voteballot_plan.validate_scope(
            "modules/foundups/voteballots/ModLog.md"
        ) is True

    def test_validate_scope_rejects_other_modules(
        self, voteballot_plan: BuildPlan
    ) -> None:
        """validate_scope() rejects paths in other modules."""
        # Other foundups
        assert voteballot_plan.validate_scope(
            "modules/foundups/gotjunk/src/main.py"
        ) is False

        # Infrastructure
        assert voteballot_plan.validate_scope(
            "modules/infrastructure/wre_core/src/router.py"
        ) is False

    def test_validate_scope_rejects_blocked_patterns(
        self, voteballot_plan: BuildPlan
    ) -> None:
        """validate_scope() rejects blocked path patterns."""
        # Wallet - always blocked
        assert voteballot_plan.validate_scope(
            "modules/foundups/voteballots/wallet/config.json"
        ) is False

        # Token - always blocked
        assert voteballot_plan.validate_scope(
            "modules/foundups/voteballots/token/mint.py"
        ) is False

        # Reward - always blocked
        assert voteballot_plan.validate_scope(
            "modules/foundups/voteballots/reward/payout.py"
        ) is False

    def test_validate_scope_rejects_without_target(self) -> None:
        """validate_scope() rejects all paths when no target defined."""
        plan = BuildPlan(
            build_plan_id="bp_test_123_abc",
            foundup_id="test",
            tenant_id="012",
            target=None,  # No target
        )

        assert plan.validate_scope("anything/at/all.py") is False

    def test_validate_scope_rejects_env_and_secrets(
        self, voteballot_plan: BuildPlan
    ) -> None:
        """validate_scope() rejects .env and secrets paths."""
        assert voteballot_plan.validate_scope(
            "modules/foundups/voteballots/.env"
        ) is False
        assert voteballot_plan.validate_scope(
            "modules/foundups/voteballots/.env.local"
        ) is False
        assert voteballot_plan.validate_scope(
            "modules/foundups/voteballots/credentials.json"
        ) is False
        assert voteballot_plan.validate_scope(
            "modules/foundups/voteballots/secrets.yaml"
        ) is False


# ---------------------------------------------------------------------------
# Additional Edge Case Tests
# ---------------------------------------------------------------------------


class TestBuildPlanEdgeCases:
    """Test edge cases and error handling."""

    def test_buildplan_requires_identity_fields(self) -> None:
        """BuildPlan requires build_plan_id, foundup_id, tenant_id."""
        with pytest.raises(ValueError, match="build_plan_id"):
            BuildPlan(
                build_plan_id="",
                foundup_id="test",
                tenant_id="012",
            )

        with pytest.raises(ValueError, match="foundup_id"):
            BuildPlan(
                build_plan_id="bp_test_123",
                foundup_id="",
                tenant_id="012",
            )

        with pytest.raises(ValueError, match="tenant_id"):
            BuildPlan(
                build_plan_id="bp_test_123",
                foundup_id="test",
                tenant_id="",
            )

    def test_get_gate_returns_none_for_missing(
        self, voteballot_plan: BuildPlan
    ) -> None:
        """get_gate() returns None for non-existent gate type."""
        # Remove all gates
        voteballot_plan.gates = []
        assert voteballot_plan.get_gate(GateType.TEST_GATE) is None

    def test_required_gates_passed_with_all_passed(
        self, voteballot_plan: BuildPlan
    ) -> None:
        """required_gates_passed() returns True when all required gates pass."""
        for gate in voteballot_plan.gates:
            if gate.required:
                gate.evaluate(passed=True, reason="test passed")

        assert voteballot_plan.required_gates_passed() is True

    def test_required_gates_passed_with_one_failed(
        self, voteballot_plan: BuildPlan
    ) -> None:
        """required_gates_passed() returns False when any required gate fails."""
        for gate in voteballot_plan.gates:
            if gate.required:
                gate.evaluate(passed=True, reason="test passed")

        # Fail one required gate
        genesis_gate = voteballot_plan.get_gate(GateType.GENESIS_GATE)
        if genesis_gate:
            genesis_gate.evaluate(passed=False, reason="genesis invalid")

        assert voteballot_plan.required_gates_passed() is False

    def test_buildstep_status_tracking(self) -> None:
        """BuildStep tracks status correctly."""
        step = BuildStep(
            step_id="step_01",
            step_name="Test",
            action=BuildStepAction.RUN_TESTS,
        )

        assert step.status == StepStatus.PENDING
        assert step.started_at is None
        assert step.completed_at is None

    def test_buildgate_evaluation(self) -> None:
        """BuildGate evaluate() updates state correctly."""
        gate = BuildGate(
            gate_id="test_gate",
            gate_type=GateType.TEST_GATE,
        )

        assert gate.status == GateStatus.PENDING
        assert gate.passed is False
        assert gate.checked is False

        gate.evaluate(passed=True, reason="all tests passed", checked_by="pytest")

        assert gate.status == GateStatus.PASSED
        assert gate.passed is True
        assert gate.checked is True
        assert gate.reason == "all tests passed"
        assert gate.checked_by == "pytest"
        assert gate.checked_at is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
