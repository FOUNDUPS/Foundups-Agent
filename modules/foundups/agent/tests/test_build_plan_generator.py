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

from pathlib import Path

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
    build_target_from_job,
    can_generate_build_plan,
    create_build_plan_from_job,
    get_generation_error,
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
        """BuildTarget.module_path is the validated CANONICAL module_path.

        UPDATED (BUILD_PLAN_GENERATOR_MODULE_PATH_TRUST_REMOVAL_PHASE1; see
        TestModLog): under legacy behavior this came straight from
        payload.module_path. It now comes from the validated manifest's
        canonical module_path (the source of truth). For voteballots the
        payload candidate and the canonical happen to be identical, so the
        asserted value is unchanged -- but the SOURCE is the manifest now,
        not the payload string.
        """
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
    """Module-path derivation when payload omits module_path.

    UPDATED (BUILD_PLAN_GENERATOR_MODULE_PATH_TRUST_REMOVAL_PHASE1; see
    TestModLog): the prior KNOWN_FOUNDUP_PATHS / get_known_foundup_path
    inference helpers are DELETED. Module-path derivation now flows
    exclusively through the shared resolver's bounded foundup_id scan, which
    reads on-disk manifests instead of a hard-coded dict.
    """

    def test_infer_module_path_for_voteballots(
        self, voteballot_job_no_module_path: FoundUpJob
    ) -> None:
        """Payload omits module_path; resolver locates the real
        modules/foundups/voteballots/foundup_manifest.json via the bounded
        foundup_id scan and derives the canonical path."""
        result = validate_job_for_build_plan(voteballot_job_no_module_path)

        assert result.valid is True
        assert result.inferred_module_path == "modules/foundups/voteballots"
        # No payload candidate was supplied; observable-ignore stays None.
        assert result.rejected_payload_value is None

    def test_generate_plan_with_inferred_path(
        self, voteballot_job_no_module_path: FoundUpJob
    ) -> None:
        """Generated BuildPlan target carries the manifest-derived canonical
        module_path (NOT a synthesized modules/foundups/{foundup_id} string
        -- that fallback was DELETED in this slice)."""
        plan = create_build_plan_from_job(voteballot_job_no_module_path)

        assert plan.target.module_path == "modules/foundups/voteballots"

    def test_unknown_foundup_without_module_path_fails(
        self, unknown_foundup_job: FoundUpJob
    ) -> None:
        """Unknown FoundUp + no payload candidate -> bounded foundup_id scan
        misses -> manifest_missing (NOT the legacy MISSING_MODULE_PATH error
        code for the dead KNOWN_FOUNDUP_PATHS branch)."""
        result = validate_job_for_build_plan(unknown_foundup_job)

        assert result.valid is False
        assert result.error_code == "manifest_missing"
        assert "unknown_foundup_xyz" in result.error_message


# ---------------------------------------------------------------------------
# Test 10: Outside-Scope module_path is Rejected
# ---------------------------------------------------------------------------


class TestOutsideScopeRejected:
    """Outside-scope module_path is rejected.

    UPDATED (BUILD_PLAN_GENERATOR_MODULE_PATH_TRUST_REMOVAL_PHASE1; see
    TestModLog): the prior _is_valid_foundup_path prefix-only gate with
    case-insensitive .lower() compare is DELETED. The shared resolver
    enforces a strict startswith("modules/") pre-manifest syntactic check;
    non-foundup paths under modules/ still reach the validator and reject
    with manifest_missing (no on-disk FoundUp manifest there). The expected
    error_code is now one of the closed-set #778 tokens instead of the
    legacy INVALID_MODULE_PATH.
    """

    @staticmethod
    def _resolver_error_codes() -> set:
        return {
            "syntactic_reject",
            "manifest_mismatch",
            "manifest_missing",
            "cross_foundup_mismatch",
        }

    def test_infrastructure_path_rejected(self) -> None:
        """modules/infrastructure/wre_core is under modules/ but has no
        FoundUp manifest -> manifest_missing."""
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
        assert result.error_code in self._resolver_error_codes()
        assert result.error_code == "manifest_missing"

    def test_root_path_rejected(self) -> None:
        """/etc/passwd is rejected at the pre-manifest syntactic-harden step
        (absolute path -> syntactic_reject)."""
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
        assert result.error_code == "syntactic_reject"

    def test_ai_intelligence_path_rejected(self) -> None:
        """modules/ai_intelligence/agent_permissions is under modules/ but
        has no FoundUp manifest -> manifest_missing."""
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
        assert result.error_code in self._resolver_error_codes()
        assert result.error_code == "manifest_missing"


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




# ===========================================================================
# BUILD_PLAN_GENERATOR_MODULE_PATH_TRUST_REMOVAL_PHASE1: validated resolution
# ===========================================================================
#
# The 14-test contract from the dispatch. Every negative test below would
# have PASSED under the legacy behavior (raw payload trust +
# KNOWN_FOUNDUP_PATHS inference + foundup_id synthesis + _is_valid_foundup_path
# prefix-only gate) and now FAILS. Grounded against real on-disk manifests
# (voteballots foundup_id=voteballots; kosei foundup_id=kosei).


class TestSharedResolverValidationInGenerator:
    """14 dispatch-required tests for the validated resolution contract."""

    def test_payload_path_with_no_backing_manifest_rejected(self) -> None:
        """No backing manifest maps to manifest_missing; rejected value is
        observable and NEVER reaches the BuildTarget."""
        job = create_job(
            tenant_id="012",
            requested_action="build_foundup",
            foundup_id="voteballots",
            payload={"module_path": "modules/foundups/nope_xyz_nobacking"},
        )
        result = validate_job_for_build_plan(job)
        assert result.valid is False
        assert result.error_code == "manifest_missing"
        assert result.rejected_payload_value == "modules/foundups/nope_xyz_nobacking"
        assert result.inferred_module_path is None

    def test_source_module_alias_with_wrong_path_rejected(self) -> None:
        job = create_job(
            tenant_id="012",
            requested_action="build_foundup",
            foundup_id="voteballots",
            payload={"source_module": "modules/foundups/nope_alias_xyz"},
        )
        result = validate_job_for_build_plan(job)
        assert result.valid is False
        assert result.error_code == "manifest_missing"
        assert result.rejected_payload_value == "modules/foundups/nope_alias_xyz"

    def test_source_module_alias_happy_path(self) -> None:
        """The source_module alias gets the same happy-path treatment as
        module_path."""
        job = create_job(
            tenant_id="012",
            requested_action="build_foundup",
            foundup_id="voteballots",
            payload={"source_module": "modules/foundups/voteballots"},
        )
        result = validate_job_for_build_plan(job)
        assert result.valid is True
        assert result.inferred_module_path == "modules/foundups/voteballots"

    def test_cross_foundup_substitution_rejected(self) -> None:
        """job.foundup_id = A (voteballots), payload points at B (kosei) real
        manifest path. The manifest binds to A; A not equal B is the #778
        load-bearing defense."""
        job = create_job(
            tenant_id="012",
            requested_action="build_foundup",
            foundup_id="voteballots",
            payload={"module_path": "modules/foundups/kosei"},
        )
        result = validate_job_for_build_plan(job)
        assert result.valid is False
        assert result.error_code == "cross_foundup_mismatch"
        assert "voteballots" in result.error_message
        assert "kosei" in result.error_message
        assert result.rejected_payload_value == "modules/foundups/kosei"

    def test_basename_partial_match_rejected(self) -> None:
        """A bare basename matching the LAST segment is REJECTED at the
        syntactic-harden step (not under modules/)."""
        job = create_job(
            tenant_id="012",
            requested_action="build_foundup",
            foundup_id="voteballots",
            payload={"module_path": "voteballots"},
        )
        result = validate_job_for_build_plan(job)
        assert result.valid is False
        assert result.error_code == "syntactic_reject"

    def test_case_variant_payload_rejected(self) -> None:
        """A mixed-case path rejects via the resolver case-sensitive
        exact-match. The legacy lower-case compare is dead."""
        job = create_job(
            tenant_id="012",
            requested_action="build_foundup",
            foundup_id="voteballots",
            payload={"module_path": "modules/Foundups/voteballots"},
        )
        result = validate_job_for_build_plan(job)
        assert result.valid is False
        assert result.error_code in ("syntactic_reject", "manifest_mismatch")

    def test_uppercase_modules_prefix_rejected(self) -> None:
        """Uppercase Modules/ rejects at the modules/ startswith guard. This
        would have PASSED under the legacy lower-case compare."""
        job = create_job(
            tenant_id="012",
            requested_action="build_foundup",
            foundup_id="voteballots",
            payload={"module_path": "Modules/foundups/voteballots"},
        )
        result = validate_job_for_build_plan(job)
        assert result.valid is False
        assert result.error_code == "syntactic_reject"

    def test_absolute_path_rejected_pre_manifest(self) -> None:
        job = create_job(
            tenant_id="012",
            requested_action="build_foundup",
            foundup_id="voteballots",
            payload={"module_path": "/modules/foundups/voteballots"},
        )
        result = validate_job_for_build_plan(job)
        assert result.valid is False
        assert result.error_code == "syntactic_reject"

    def test_drive_prefix_path_rejected_pre_manifest(self) -> None:
        job = create_job(
            tenant_id="012",
            requested_action="build_foundup",
            foundup_id="voteballots",
            payload={"module_path": "O:/Foundups-Agent/modules/foundups/voteballots"},
        )
        result = validate_job_for_build_plan(job)
        assert result.valid is False
        assert result.error_code == "syntactic_reject"

    def test_traversal_rejected_pre_manifest(self) -> None:
        job = create_job(
            tenant_id="012",
            requested_action="build_foundup",
            foundup_id="voteballots",
            payload={"module_path": "../modules/foundups/voteballots"},
        )
        result = validate_job_for_build_plan(job)
        assert result.valid is False
        assert result.error_code == "syntactic_reject"

    def test_backslash_rejected_pre_manifest(self) -> None:
        job = create_job(
            tenant_id="012",
            requested_action="build_foundup",
            foundup_id="voteballots",
            payload={"module_path": "modules\foundups\voteballots"},
        )
        result = validate_job_for_build_plan(job)
        assert result.valid is False
        assert result.error_code == "syntactic_reject"

    def test_empty_string_payload_treated_as_absent(self) -> None:
        """Empty string is ABSENT (#778 Addendum D #4); bounded scan finds the
        real voteballots manifest and derives the canonical path."""
        job = create_job(
            tenant_id="012",
            requested_action="build_foundup",
            foundup_id="voteballots",
            payload={"module_path": ""},
        )
        result = validate_job_for_build_plan(job)
        assert result.valid is True
        assert result.inferred_module_path == "modules/foundups/voteballots"
        assert result.rejected_payload_value is None

    def test_known_foundup_id_without_on_disk_manifest_fails_closed(self) -> None:
        """A foundup_id from the dead KNOWN_FOUNDUP_PATHS dict with NO real
        on-disk manifest must now FAIL closed."""
        for legacy_id in ("pqn_portal", "social_twin", "move2japan"):
            job = create_job(
                tenant_id="012",
                requested_action="build_foundup",
                foundup_id=legacy_id,
                payload={},
            )
            result = validate_job_for_build_plan(job)
            assert result.valid is False, (
                "legacy dead-dict entry " + repr(legacy_id) + " resolved"
            )
            assert result.error_code == "manifest_missing"

    def test_known_foundup_paths_symbol_is_gone(self) -> None:
        """Importing KNOWN_FOUNDUP_PATHS raises ImportError; a future
        re-introduction fails this test loudly."""
        with pytest.raises(ImportError):
            from modules.foundups.agent.src.build_plan_generator import (  # noqa: F401
                KNOWN_FOUNDUP_PATHS,
            )

    def test_foundup_id_synthesis_dead_no_modules_foundups_fallback(self) -> None:
        """The dead foundup_id-as-path synthesis is gone: foundup_id not on
        disk with payload absent maps to manifest_missing, not a fabricated
        path."""
        job = create_job(
            tenant_id="012",
            requested_action="build_foundup",
            foundup_id="newly_invented_foundup_no_manifest",
            payload={},
        )
        result = validate_job_for_build_plan(job)
        assert result.valid is False
        assert result.error_code == "manifest_missing"

    def test_build_target_does_not_use_synthesized_path(self) -> None:
        """build_target_from_job raises ValueError instead of returning a
        BuildTarget with a synthesized modules/foundups/<id> path."""
        job = create_job(
            tenant_id="012",
            requested_action="build_foundup",
            foundup_id="synth_xyz_no_manifest",
            payload={},
        )
        with pytest.raises(ValueError, match="manifest_missing"):
            build_target_from_job(job)

    def test_pwa_surface_path_as_module_identity_rejected(self) -> None:
        """A PWA surface payload rejects at the modules/ startswith guard with
        syntactic_reject (PWA-surface ruling: DERIVED_ONLY)."""
        job = create_job(
            tenant_id="012",
            requested_action="build_foundup",
            foundup_id="voteballots",
            payload={"module_path": "public/member/foundups/voteballots"},
        )
        result = validate_job_for_build_plan(job)
        assert result.valid is False
        assert result.error_code == "syntactic_reject"

    def test_rejected_value_observable_on_failure(self) -> None:
        job = create_job(
            tenant_id="012",
            requested_action="build_foundup",
            foundup_id="voteballots",
            payload={"module_path": "modules/foundups/observable_test_no_manifest"},
        )
        result = validate_job_for_build_plan(job)
        assert result.valid is False
        assert result.rejected_payload_value == (
            "modules/foundups/observable_test_no_manifest"
        )
        assert "observable_test_no_manifest" in result.error_message

    def test_rejected_value_observable_on_success(self) -> None:
        """Even on success rejected_payload_value carries the declared
        candidate; silent swallow is refused per #777 / #778."""
        job = create_job(
            tenant_id="012",
            requested_action="build_foundup",
            foundup_id="voteballots",
            payload={"module_path": "modules/foundups/voteballots"},
        )
        result = validate_job_for_build_plan(job)
        assert result.valid is True
        assert result.rejected_payload_value == "modules/foundups/voteballots"

    def test_rejected_payload_value_does_not_propagate_into_buildtarget(self) -> None:
        """On rejection the BuildTarget is never produced; the rejected value
        is visible only as diagnostic evidence."""
        bogus_path = "modules/foundups/bogus_will_not_resolve"
        job = create_job(
            tenant_id="012",
            requested_action="build_foundup",
            foundup_id="voteballots",
            payload={"module_path": bogus_path},
        )
        with pytest.raises(ValueError, match="manifest_missing"):
            create_build_plan_from_job(job)
        with pytest.raises(ValueError, match="manifest_missing"):
            build_target_from_job(job)

    def test_buildplan_carries_only_canonical_when_payload_provided(self) -> None:
        """BuildTarget.module_path is the manifest canonical (source of
        truth); pwa_surface_path is DERIVED from the canonical basename."""
        job = create_job(
            tenant_id="012",
            requested_action="build_foundup",
            foundup_id="voteballots",
            payload={"module_path": "modules/foundups/voteballots"},
        )
        plan = create_build_plan_from_job(job)
        assert plan.target.module_path == "modules/foundups/voteballots"
        assert plan.target.pwa_surface_path == "public/member/foundups/voteballots/"


# ===========================================================================
# Single source of truth: exactly ONE resolver, shared across files
# ===========================================================================


class TestSharedResolverIsSingleSourceOfTruth:
    """Prove there is exactly ONE module-path resolver implementation, and the
    executor shim resolves to the SAME object (Addendum C #4 / #5)."""

    def test_executor_shim_and_shared_module_resolve_same_function(self) -> None:
        from modules.foundups.agent.src import hermes_foundup_job_executor as e
        from modules.foundups.agent.src import module_path_resolution as m

        assert e._resolve_validated_module_path is m._resolve_validated_module_path
        assert e.ResolvedModulePath is m.ResolvedModulePath
        assert e.DEFAULT_REPO_ROOT == m.DEFAULT_REPO_ROOT
        assert e.ALL_FAIL_TOKENS is m.ALL_FAIL_TOKENS
        assert e.FAIL_TOKEN_SYNTACTIC_REJECT == m.FAIL_TOKEN_SYNTACTIC_REJECT
        assert e.FAIL_TOKEN_MANIFEST_MISMATCH == m.FAIL_TOKEN_MANIFEST_MISMATCH
        assert e.FAIL_TOKEN_MANIFEST_MISSING == m.FAIL_TOKEN_MANIFEST_MISSING
        assert e.FAIL_TOKEN_CROSS_FOUNDUP_MISMATCH == m.FAIL_TOKEN_CROSS_FOUNDUP_MISMATCH

    def test_generator_uses_same_resolver_as_executor(self) -> None:
        from modules.foundups.agent.src import build_plan_generator as g
        from modules.foundups.agent.src import hermes_foundup_job_executor as e

        assert g._resolve_validated_module_path is e._resolve_validated_module_path

    def test_no_second_resolver_implementation_in_executor(self) -> None:
        import ast
        path = Path(__file__).resolve().parents[1] / "src" / "hermes_foundup_job_executor.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        local_defs = [
            node.name for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
        ]
        assert "_resolve_validated_module_path" not in local_defs, (
            "Second resolver implementation found in executor; the shared "
            "module is the single source of truth."
        )
        assert "_find_manifest_for_foundup_id" not in local_defs
        assert "_stringify_ignored" not in local_defs
        class_defs = [
            node.name for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef)
        ]
        assert "ResolvedModulePath" not in class_defs

    def test_no_second_resolver_in_build_plan_generator(self) -> None:
        import ast
        path = Path(__file__).resolve().parents[1] / "src" / "build_plan_generator.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        local_defs = [
            node.name for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
        ]
        assert "_resolve_validated_module_path" not in local_defs
        assert "_is_valid_foundup_path" not in local_defs
        assert "get_known_foundup_path" not in local_defs
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        assert target.id != "KNOWN_FOUNDUP_PATHS"

    def test_exactly_one_resolver_definition_in_repo_module_set(self) -> None:
        import ast
        src_dir = Path(__file__).resolve().parents[1] / "src"
        definers = []
        for py in sorted(src_dir.glob("*.py")):
            tree = ast.parse(py.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == "_resolve_validated_module_path":
                    definers.append(py.name)
        assert definers == ["module_path_resolution.py"], definers


# ===========================================================================
# WSP_97 row HERMES_778_TESTS_UNCHANGED_GREEN: cross-file invariant
# ===========================================================================


class TestHermes778TestsUnchanged:
    """The #778 executor test file must keep passing with ZERO edits
    (Addendum C #3). Meta-test: verify the executor test imports still resolve
    via the shim."""

    def test_executor_test_imports_still_resolve(self) -> None:
        from modules.foundups.agent.src.hermes_foundup_job_executor import (  # noqa: F401
            HermesJobExecutionResult,
            SUPPORTED_ACTIONS,
            WORKER_ID,
            can_execute_action,
            execute_foundup_job,
            get_supported_actions,
            DEFAULT_REPO_ROOT,
            FAIL_TOKEN_MANIFEST_MISSING,
            _resolve_validated_module_path,
        )

    def test_executor_attribute_access_pattern_still_works(self) -> None:
        from modules.foundups.agent.src import hermes_foundup_job_executor as e
        assert callable(e._resolve_validated_module_path)
        assert isinstance(e.DEFAULT_REPO_ROOT, Path)
        assert e.FAIL_TOKEN_MANIFEST_MISSING == "manifest_missing"
        assert e.FAIL_TOKEN_SYNTACTIC_REJECT == "syntactic_reject"
        assert e.FAIL_TOKEN_MANIFEST_MISMATCH == "manifest_mismatch"
        assert e.FAIL_TOKEN_CROSS_FOUNDUP_MISMATCH == "cross_foundup_mismatch"
        assert e.ALL_FAIL_TOKENS == frozenset({
            "syntactic_reject", "manifest_mismatch",
            "manifest_missing", "cross_foundup_mismatch",
        })


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
