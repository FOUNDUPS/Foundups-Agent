#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BuildPlan Generator Tests

Verifies BuildPlan generation from FoundUpJob.

WSP 97 TRUTH BOUNDARIES:
  - Generator produces dry_run=True plans only
  - Generator does not execute steps
  - Generator validates job before generation
  - No CABR/payout/reward/token fields

Test Coverage:
  1. VoteBallot FoundUpJob generates valid BuildPlan
  2. Plan inherits job identity
  3. Plan preserves dry_run=True
  4. Plan mode is DRY_RUN by default
  5. module_path maps to BuildTarget
  6. standard steps are populated
  7. queue_foundup_job is rejected
  8. missing foundup_id fails truthfully
  9. missing module_path can infer VoteBallot path
  10. outside-scope module_path is rejected
  11. no CABR/reward/payout/token fields
  12. generated plan is not real-build allowed

NAVIGATION:
  -> Tests: modules/foundups/agent/src/build_plan_generator.py
  -> Uses: build_plan.py, foundup_job_contract.py
"""

from __future__ import annotations

import pytest

from modules.communication.moltbot_bridge.src.foundup_job_contract import (
    FoundUpJob,
    JobStatus,
    PolicyFlags,
    create_job,
)

from modules.foundups.agent.src.build_plan import (
    BuildMode,
    BuildPlan,
    BuildPlanStatus,
    BuildScope,
    BuildStepAction,
    GateType,
)

from modules.foundups.agent.src.build_plan_generator import (
    BUILDPLAN_SUPPORTED_ACTIONS,
    BUILDPLAN_UNSUPPORTED_ACTIONS,
    KNOWN_FOUNDUP_PATHS,
    build_target_from_job,
    can_generate_build_plan,
    create_build_plan_from_job,
    get_generation_error,
    get_known_foundup_path,
    infer_build_scope,
    validate_job_for_build_plan,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def voteballot_job() -> FoundUpJob:
    """Create a VoteBallot build_foundup job."""
    return create_job(
        tenant_id="012",
        requested_action="build_foundup",
        foundup_id="voteballots",
        intent_id="internal_poc_voteballot_build",
        payload={
            "module_path": "modules/foundups/voteballots",
            "target_org": "FOUNDUPS",
            "build_goal": "internal dry-run PoC for VoteBallot",
            "dry_run": True,
        },
    )


@pytest.fixture
def voteballot_job_no_module_path() -> FoundUpJob:
    """Create a VoteBallot job without explicit module_path."""
    return create_job(
        tenant_id="012",
        requested_action="build_foundup",
        foundup_id="voteballots",
        intent_id="internal_poc_voteballot_build",
        payload={
            "target_org": "FOUNDUPS",
            "dry_run": True,
        },
    )


@pytest.fixture
def queue_job() -> FoundUpJob:
    """Create a queue_foundup_job action job."""
    return create_job(
        tenant_id="012",
        requested_action="queue_foundup_job",
        foundup_id="voteballots",
        payload={
            "module_path": "modules/foundups/voteballots",
        },
    )


@pytest.fixture
def unknown_foundup_job() -> FoundUpJob:
    """Create a job for unknown FoundUp without module_path."""
    return create_job(
        tenant_id="012",
        requested_action="build_foundup",
        foundup_id="unknown_foundup_xyz",
        payload={},
    )


# ---------------------------------------------------------------------------
# Test 1: VoteBallot FoundUpJob Generates Valid BuildPlan
# ---------------------------------------------------------------------------


class TestVoteBallotPlanGeneration:
    """Test VoteBallot job generates valid plan."""

    def test_voteballot_generates_valid_plan(
        self, voteballot_job: FoundUpJob
    ) -> None:
        """VoteBallot job generates a valid BuildPlan."""
        plan = create_build_plan_from_job(voteballot_job)

        assert plan is not None
        assert isinstance(plan, BuildPlan)
        assert plan.build_plan_id.startswith("bp_voteballots_")
        assert plan.foundup_id == "voteballots"

    def test_voteballot_plan_has_target(
        self, voteballot_job: FoundUpJob
    ) -> None:
        """Generated plan has BuildTarget."""
        plan = create_build_plan_from_job(voteballot_job)

        assert plan.target is not None
        assert plan.target.module_path == "modules/foundups/voteballots"

    def test_voteballot_plan_has_steps(
        self, voteballot_job: FoundUpJob
    ) -> None:
        """Generated plan has standard build steps."""
        plan = create_build_plan_from_job(voteballot_job)

        # Full build has 12 steps
        assert len(plan.steps) == 12
        assert plan.steps[0].action == BuildStepAction.VALIDATE_GENESIS
        assert plan.steps[-1].action == BuildStepAction.REQUEST_APPROVAL

    def test_voteballot_plan_has_gates(
        self, voteballot_job: FoundUpJob
    ) -> None:
        """Generated plan has default gates."""
        plan = create_build_plan_from_job(voteballot_job)

        assert len(plan.gates) == 8
        gate_types = {g.gate_type for g in plan.gates}
        assert GateType.HUMAN_APPROVAL_GATE in gate_types
        assert GateType.DRY_RUN_GATE in gate_types


# ---------------------------------------------------------------------------
# Test 2: Plan Inherits Job Identity
# ---------------------------------------------------------------------------


class TestPlanInheritsJobIdentity:
    """Test plan inherits job identity fields."""

    def test_plan_inherits_foundup_id(
        self, voteballot_job: FoundUpJob
    ) -> None:
        """Plan inherits foundup_id from job."""
        plan = create_build_plan_from_job(voteballot_job)
        assert plan.foundup_id == voteballot_job.foundup_id

    def test_plan_inherits_tenant_id(
        self, voteballot_job: FoundUpJob
    ) -> None:
        """Plan inherits tenant_id from job."""
        plan = create_build_plan_from_job(voteballot_job)
        assert plan.tenant_id == voteballot_job.tenant_id

    def test_plan_inherits_intent_id(
        self, voteballot_job: FoundUpJob
    ) -> None:
        """Plan inherits intent_id from job."""
        plan = create_build_plan_from_job(voteballot_job)
        assert plan.intent_id == voteballot_job.intent_id

    def test_plan_has_source_job_id(
        self, voteballot_job: FoundUpJob
    ) -> None:
        """Plan has source_job_id linking to originating job."""
        plan = create_build_plan_from_job(voteballot_job)
        assert plan.source_job_id == voteballot_job.job_id

    def test_plan_inherits_requested_action(
        self, voteballot_job: FoundUpJob
    ) -> None:
        """Plan inherits requested_action from job."""
        plan = create_build_plan_from_job(voteballot_job)
        assert plan.requested_action == "build_foundup"


# ---------------------------------------------------------------------------
# Test 3: Plan Preserves dry_run=True
# ---------------------------------------------------------------------------


class TestPlanPreservesDryRun:
    """Test plan preserves dry_run=True."""

    def test_plan_has_dry_run_true(
        self, voteballot_job: FoundUpJob
    ) -> None:
        """Generated plan has dry_run=True."""
        plan = create_build_plan_from_job(voteballot_job)
        assert plan.dry_run is True

    def test_plan_ignores_dry_run_false_in_payload(self) -> None:
        """Generator ignores dry_run=False in payload (WSP 97)."""
        job = create_job(
            tenant_id="012",
            requested_action="build_foundup",
            foundup_id="voteballots",
            payload={
                "module_path": "modules/foundups/voteballots",
                "dry_run": False,  # Request dry_run=False
            },
        )

        plan = create_build_plan_from_job(job)

        # Generator ALWAYS produces dry_run=True
        assert plan.dry_run is True

    def test_plan_ignores_policy_flags_dry_run_false(self) -> None:
        """Generator ignores policy_flags.dry_run_mode=False (WSP 97)."""
        job = create_job(
            tenant_id="012",
            requested_action="build_foundup",
            foundup_id="voteballots",
            payload={
                "module_path": "modules/foundups/voteballots",
            },
        )
        job.policy_flags.dry_run_mode = False  # Set to False

        plan = create_build_plan_from_job(job)

        # Generator ALWAYS produces dry_run=True
        assert plan.dry_run is True


# ---------------------------------------------------------------------------
# Test 4: Plan Mode is DRY_RUN by Default
# ---------------------------------------------------------------------------


class TestPlanModeDefault:
    """Test plan mode defaults to DRY_RUN."""

    def test_plan_mode_is_dry_run(
        self, voteballot_job: FoundUpJob
    ) -> None:
        """Generated plan has mode=DRY_RUN."""
        plan = create_build_plan_from_job(voteballot_job)
        assert plan.mode == BuildMode.DRY_RUN

    def test_plan_status_is_draft(
        self, voteballot_job: FoundUpJob
    ) -> None:
        """Generated plan has status=DRAFT."""
        plan = create_build_plan_from_job(voteballot_job)
        assert plan.status == BuildPlanStatus.DRAFT


# ---------------------------------------------------------------------------
# Test 5: module_path Maps to BuildTarget
# ---------------------------------------------------------------------------


class TestModulePathMapping:
    """Test module_path maps to BuildTarget."""

    def test_module_path_from_payload(
        self, voteballot_job: FoundUpJob
    ) -> None:
        """BuildTarget.module_path from payload.module_path."""
        plan = create_build_plan_from_job(voteballot_job)
        assert plan.target.module_path == "modules/foundups/voteballots"

    def test_manifest_path_auto_generated(
        self, voteballot_job: FoundUpJob
    ) -> None:
        """BuildTarget auto-generates manifest path."""
        plan = create_build_plan_from_job(voteballot_job)
        assert plan.target.foundup_manifest_path == (
            "modules/foundups/voteballots/foundup_manifest.json"
        )

    def test_tests_path_auto_generated(
        self, voteballot_job: FoundUpJob
    ) -> None:
        """BuildTarget auto-generates tests path."""
        plan = create_build_plan_from_job(voteballot_job)
        assert plan.target.tests_path == "modules/foundups/voteballots/tests/"

    def test_explicit_paths_override_defaults(self) -> None:
        """Explicit paths in payload override defaults."""
        job = create_job(
            tenant_id="012",
            requested_action="build_foundup",
            foundup_id="voteballots",
            payload={
                "module_path": "modules/foundups/voteballots",
                "tests_path": "custom/tests/",
                "docs_path": "custom/docs/",
            },
        )

        plan = create_build_plan_from_job(job)

        assert plan.target.tests_path == "custom/tests/"
        assert plan.target.docs_path == "custom/docs/"


# ---------------------------------------------------------------------------
# Test 6: Standard Steps are Populated
# ---------------------------------------------------------------------------


class TestStandardStepsPopulated:
    """Test standard steps are populated."""

    def test_full_build_has_12_steps(
        self, voteballot_job: FoundUpJob
    ) -> None:
        """Full build scope has 12 standard steps."""
        plan = create_build_plan_from_job(voteballot_job)

        assert len(plan.steps) == 12
        actions = [s.action for s in plan.steps]
        assert BuildStepAction.VALIDATE_GENESIS in actions
        assert BuildStepAction.RUN_TESTS in actions
        assert BuildStepAction.SUBMIT_RECEIPT in actions

    def test_validate_foundup_has_genesis_steps_only(self) -> None:
        """validate_foundup action has genesis steps only."""
        job = create_job(
            tenant_id="012",
            requested_action="validate_foundup",
            foundup_id="voteballots",
            payload={
                "module_path": "modules/foundups/voteballots",
            },
        )

        plan = create_build_plan_from_job(job)

        # Genesis only = first 2 steps
        assert len(plan.steps) == 2
        assert plan.steps[0].action == BuildStepAction.VALIDATE_GENESIS
        assert plan.steps[1].action == BuildStepAction.VALIDATE_MANIFEST

    def test_extract_foundup_has_full_steps(self) -> None:
        """extract_foundup action has full build steps."""
        job = create_job(
            tenant_id="012",
            requested_action="extract_foundup",
            foundup_id="voteballots",
            payload={
                "module_path": "modules/foundups/voteballots",
            },
        )

        plan = create_build_plan_from_job(job)

        assert len(plan.steps) == 12


# ---------------------------------------------------------------------------
# Test 7: queue_foundup_job is Rejected
# ---------------------------------------------------------------------------


class TestQueueActionRejected:
    """Test queue_foundup_job is rejected for BuildPlan generation."""

    def test_queue_foundup_job_is_unsupported(self) -> None:
        """queue_foundup_job is in unsupported actions set."""
        assert "queue_foundup_job" in BUILDPLAN_UNSUPPORTED_ACTIONS
        assert "queue_foundup_job" not in BUILDPLAN_SUPPORTED_ACTIONS

    def test_queue_job_fails_validation(
        self, queue_job: FoundUpJob
    ) -> None:
        """queue_foundup_job fails validation."""
        result = validate_job_for_build_plan(queue_job)

        assert result.valid is False
        assert result.error_code == "UNSUPPORTED_ACTION"
        assert "queue_foundup_job" in result.error_message

    def test_queue_job_cannot_generate_plan(
        self, queue_job: FoundUpJob
    ) -> None:
        """queue_foundup_job cannot generate plan."""
        assert can_generate_build_plan(queue_job) is False

    def test_queue_job_raises_on_generate(
        self, queue_job: FoundUpJob
    ) -> None:
        """queue_foundup_job raises ValueError on generation."""
        with pytest.raises(ValueError, match="UNSUPPORTED_ACTION"):
            create_build_plan_from_job(queue_job)


# ---------------------------------------------------------------------------
# Test 8: Missing foundup_id Fails Truthfully
# ---------------------------------------------------------------------------


class TestMissingFoundupIdFails:
    """Test missing foundup_id fails truthfully."""

    def test_missing_foundup_id_fails_validation(self) -> None:
        """Job without foundup_id fails validation."""
        job = create_job(
            tenant_id="012",
            requested_action="build_foundup",
            foundup_id=None,  # type: ignore
            payload={
                "module_path": "modules/foundups/test",
            },
        )
        # Manually clear foundup_id (create_job might set it)
        job.foundup_id = None

        result = validate_job_for_build_plan(job)

        assert result.valid is False
        assert result.error_code == "MISSING_FOUNDUP_ID"

    def test_empty_foundup_id_fails_validation(self) -> None:
        """Job with empty foundup_id fails validation."""
        job = create_job(
            tenant_id="012",
            requested_action="build_foundup",
            foundup_id="",
            payload={
                "module_path": "modules/foundups/test",
            },
        )
        job.foundup_id = ""

        result = validate_job_for_build_plan(job)

        assert result.valid is False
        assert result.error_code == "MISSING_FOUNDUP_ID"


# ---------------------------------------------------------------------------
# Test 9: Missing module_path Can Infer VoteBallot Path
# ---------------------------------------------------------------------------


class TestModulePathInference:
    """Test module_path inference from foundup_id."""

    def test_known_foundup_paths_include_voteballots(self) -> None:
        """KNOWN_FOUNDUP_PATHS includes voteballots."""
        assert "voteballots" in KNOWN_FOUNDUP_PATHS
        assert KNOWN_FOUNDUP_PATHS["voteballots"] == "modules/foundups/voteballots"

    def test_get_known_foundup_path_returns_voteballots(self) -> None:
        """get_known_foundup_path returns VoteBallots path."""
        path = get_known_foundup_path("voteballots")
        assert path == "modules/foundups/voteballots"

    def test_infer_module_path_for_voteballots(
        self, voteballot_job_no_module_path: FoundUpJob
    ) -> None:
        """Can infer module_path for VoteBallots."""
        result = validate_job_for_build_plan(voteballot_job_no_module_path)

        assert result.valid is True
        assert result.inferred_module_path == "modules/foundups/voteballots"

    def test_generate_plan_with_inferred_path(
        self, voteballot_job_no_module_path: FoundUpJob
    ) -> None:
        """Can generate plan with inferred module_path."""
        plan = create_build_plan_from_job(voteballot_job_no_module_path)

        assert plan.target.module_path == "modules/foundups/voteballots"

    def test_unknown_foundup_without_module_path_fails(
        self, unknown_foundup_job: FoundUpJob
    ) -> None:
        """Unknown FoundUp without module_path fails."""
        result = validate_job_for_build_plan(unknown_foundup_job)

        assert result.valid is False
        assert result.error_code == "MISSING_MODULE_PATH"
        assert "unknown_foundup_xyz" in result.error_message


# ---------------------------------------------------------------------------
# Test 10: Outside-Scope module_path is Rejected
# ---------------------------------------------------------------------------


class TestOutsideScopeRejected:
    """Test outside-scope module_path is rejected."""

    def test_infrastructure_path_rejected(self) -> None:
        """Infrastructure module path is rejected."""
        job = create_job(
            tenant_id="012",
            requested_action="build_foundup",
            foundup_id="test",
            payload={
                "module_path": "modules/infrastructure/wre_core",
            },
        )

        result = validate_job_for_build_plan(job)

        assert result.valid is False
        assert result.error_code == "INVALID_MODULE_PATH"

    def test_root_path_rejected(self) -> None:
        """Root path is rejected."""
        job = create_job(
            tenant_id="012",
            requested_action="build_foundup",
            foundup_id="test",
            payload={
                "module_path": "/etc/passwd",
            },
        )

        result = validate_job_for_build_plan(job)

        assert result.valid is False
        assert result.error_code == "INVALID_MODULE_PATH"

    def test_ai_intelligence_path_rejected(self) -> None:
        """AI intelligence module path is rejected."""
        job = create_job(
            tenant_id="012",
            requested_action="build_foundup",
            foundup_id="test",
            payload={
                "module_path": "modules/ai_intelligence/agent_permissions",
            },
        )

        result = validate_job_for_build_plan(job)

        assert result.valid is False
        assert result.error_code == "INVALID_MODULE_PATH"


# ---------------------------------------------------------------------------
# Test 11: No CABR/Reward/Payout/Token Fields
# ---------------------------------------------------------------------------


class TestNoCABRFields:
    """Test no CABR/reward/payout/token fields exist."""

    def test_plan_dict_has_no_cabr_fields(
        self, voteballot_job: FoundUpJob
    ) -> None:
        """Generated plan dict has no CABR fields."""
        plan = create_build_plan_from_job(voteballot_job)
        d = plan.to_dict()

        assert "cabr_ready" not in d
        assert "payout_ready" not in d
        assert "reward" not in d
        assert "tokens" not in d
        assert "tokens_issued" not in d
        assert "payout_amount" not in d
        assert "verification_complete" not in d

    def test_plan_has_no_cabr_attributes(
        self, voteballot_job: FoundUpJob
    ) -> None:
        """Generated plan has no CABR attributes."""
        plan = create_build_plan_from_job(voteballot_job)

        assert not hasattr(plan, "cabr_ready")
        assert not hasattr(plan, "payout_ready")
        assert not hasattr(plan, "tokens_issued")
        assert not hasattr(plan, "reward")


# ---------------------------------------------------------------------------
# Test 12: Generated Plan is Not Real-Build Allowed
# ---------------------------------------------------------------------------


class TestNotRealBuildAllowed:
    """Test generated plan is not real-build allowed."""

    def test_generated_plan_not_real_build_allowed(
        self, voteballot_job: FoundUpJob
    ) -> None:
        """Generated plan cannot do real build."""
        plan = create_build_plan_from_job(voteballot_job)

        # WSP 97: Generated plans are always dry-run
        assert plan.is_real_build_allowed() is False

    def test_plan_requires_human_approval_for_real(
        self, voteballot_job: FoundUpJob
    ) -> None:
        """Real build would require human approval gate."""
        plan = create_build_plan_from_job(voteballot_job)

        # Get human approval gate
        human_gate = plan.get_gate(GateType.HUMAN_APPROVAL_GATE)
        assert human_gate is not None
        assert human_gate.passed is False


# ---------------------------------------------------------------------------
# Test: BuildScope Inference
# ---------------------------------------------------------------------------


class TestBuildScopeInference:
    """Test BuildScope inference from job."""

    def test_build_foundup_infers_full_build(
        self, voteballot_job: FoundUpJob
    ) -> None:
        """build_foundup infers FULL_BUILD scope."""
        scope = infer_build_scope(voteballot_job)
        assert scope == BuildScope.FULL_BUILD

    def test_validate_foundup_infers_genesis_only(self) -> None:
        """validate_foundup infers GENESIS_ONLY scope."""
        job = create_job(
            tenant_id="012",
            requested_action="validate_foundup",
            foundup_id="voteballots",
            payload={"module_path": "modules/foundups/voteballots"},
        )

        scope = infer_build_scope(job)
        assert scope == BuildScope.GENESIS_ONLY

    def test_explicit_scope_in_payload(self) -> None:
        """Explicit build_scope in payload is used."""
        job = create_job(
            tenant_id="012",
            requested_action="build_foundup",
            foundup_id="voteballots",
            payload={
                "module_path": "modules/foundups/voteballots",
                "build_scope": "incremental",
            },
        )

        scope = infer_build_scope(job)
        assert scope == BuildScope.INCREMENTAL


# ---------------------------------------------------------------------------
# Test: Convenience Functions
# ---------------------------------------------------------------------------


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_can_generate_build_plan_true(
        self, voteballot_job: FoundUpJob
    ) -> None:
        """can_generate_build_plan returns True for valid job."""
        assert can_generate_build_plan(voteballot_job) is True

    def test_can_generate_build_plan_false(
        self, queue_job: FoundUpJob
    ) -> None:
        """can_generate_build_plan returns False for invalid job."""
        assert can_generate_build_plan(queue_job) is False

    def test_get_generation_error_none(
        self, voteballot_job: FoundUpJob
    ) -> None:
        """get_generation_error returns None for valid job."""
        assert get_generation_error(voteballot_job) is None

    def test_get_generation_error_message(
        self, queue_job: FoundUpJob
    ) -> None:
        """get_generation_error returns error for invalid job."""
        error = get_generation_error(queue_job)
        assert error is not None
        assert "UNSUPPORTED_ACTION" in error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
