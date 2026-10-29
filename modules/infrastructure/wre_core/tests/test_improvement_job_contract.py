#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ImprovementJob Contract Tests

Verifies the ImprovementJob typed contract for codebase self-improvement.

WSP 97 TRUTH BOUNDARIES:
  - Tests verify contract structure, NOT execution
  - Tests verify dry_run=True default, NOT repair behavior
  - Tests verify no CABR/reward fields exist
  - Tests verify no execution methods exist

Contract References:
  modules/infrastructure/wre_core/src/improvement_job_contract.py
  modules/communication/moltbot_bridge/src/foundup_job_contract.py (pattern)
"""

import json
from datetime import datetime, timezone

import pytest

from modules.infrastructure.wre_core.src.improvement_job_contract import (
    ImprovementJob,
    ImprovementReasonCode,
    ImprovementRiskLevel,
    ImprovementScope,
    ImprovementStatus,
    ImprovementType,
    WSP15Priority,
    create_improvement_job,
    generate_improvement_job_id,
    is_terminal_improvement_status,
    is_valid_improvement_transition,
)


# ---------------------------------------------------------------------------
# Test 1: ImprovementJob creation with dry_run default
# ---------------------------------------------------------------------------


class TestImprovementJobCreation:
    """Test ImprovementJob creation and defaults."""

    def test_creation_with_required_fields_only(self):
        """ImprovementJob can be created with minimal required fields."""
        job = ImprovementJob(
            job_id="imp_test_123",
            finding_id="FMAS_001",
            improvement_type=ImprovementType.WSP_VIOLATION,
        )
        assert job.job_id == "imp_test_123"
        assert job.finding_id == "FMAS_001"
        assert job.improvement_type == ImprovementType.WSP_VIOLATION

    def test_dry_run_default_true(self):
        """WSP 97: dry_run defaults to True."""
        job = ImprovementJob(
            job_id="imp_test_123",
            finding_id="FMAS_001",
            improvement_type=ImprovementType.MODULE_REPAIR,
        )
        assert job.dry_run is True

    def test_status_default_pending(self):
        """Default status is PENDING."""
        job = ImprovementJob(
            job_id="imp_test_123",
            finding_id="FMAS_001",
            improvement_type=ImprovementType.TEST_HYGIENE,
        )
        assert job.status == ImprovementStatus.PENDING

    def test_factory_creates_job_with_defaults(self):
        """create_improvement_job() factory sets correct defaults."""
        job = create_improvement_job(
            finding_id="orphan_123",
            improvement_type=ImprovementType.ORPHAN_CONNECTION,
        )
        assert job.job_id.startswith("imp_")
        assert job.finding_id == "orphan_123"
        assert job.dry_run is True
        assert job.status == ImprovementStatus.PENDING

    def test_required_fields_validation(self):
        """job_id and finding_id are required."""
        with pytest.raises(ValueError, match="job_id is required"):
            ImprovementJob(
                job_id="",
                finding_id="test",
                improvement_type=ImprovementType.FMAS_SCAN,
            )

        with pytest.raises(ValueError, match="finding_id is required"):
            ImprovementJob(
                job_id="test",
                finding_id="",
                improvement_type=ImprovementType.FMAS_SCAN,
            )


@pytest.mark.parametrize(
    "unsafe_path",
    [
        "modules/example/.env.",
        "modules/example/.env ",
        "modules/example/NUL",
        "modules/example/con.txt",
        "modules/example/COM1.py",
        "modules/example/file.py:stream",
        "modules/example/file.py::$DATA",
    ],
)
def test_scope_rejects_windows_alias_and_ads_paths(unsafe_path):
    """Windows aliases and alternate data streams are never valid scope."""
    scope = ImprovementScope(
        module_path="modules/example",
        file_paths=[unsafe_path],
        allowed_paths=[unsafe_path],
    )

    assert scope.is_well_formed() is False


# ---------------------------------------------------------------------------
# Test 2: ImprovementType values exist
# ---------------------------------------------------------------------------


class TestImprovementTypeEnum:
    """Test ImprovementType enum values."""

    def test_all_improvement_types_exist(self):
        """All expected improvement types are defined."""
        expected_types = {
            "wsp_violation",
            "module_repair",
            "test_hygiene",
            "orphan_connection",
            "drift_correction",
            "fmas_scan",
            "doc_ledger_hygiene",
        }
        actual_types = {t.value for t in ImprovementType}
        assert actual_types == expected_types

    def test_improvement_type_string_conversion(self):
        """ImprovementType can be created from string."""
        assert ImprovementType("wsp_violation") == ImprovementType.WSP_VIOLATION
        assert ImprovementType("orphan_connection") == ImprovementType.ORPHAN_CONNECTION


# ---------------------------------------------------------------------------
# Test 3: ImprovementStatus values exist
# ---------------------------------------------------------------------------


class TestImprovementStatusEnum:
    """Test ImprovementStatus enum values."""

    def test_all_status_values_exist(self):
        """All expected status values are defined."""
        expected_statuses = {
            "pending",
            "approved",
            "executing",
            "validating",
            "completed",
            "failed",
            "blocked",
        }
        actual_statuses = {s.value for s in ImprovementStatus}
        assert actual_statuses == expected_statuses

    def test_terminal_status_detection(self):
        """Terminal statuses are correctly identified."""
        assert is_terminal_improvement_status(ImprovementStatus.COMPLETED) is True
        assert is_terminal_improvement_status(ImprovementStatus.FAILED) is True
        assert is_terminal_improvement_status(ImprovementStatus.PENDING) is False
        assert is_terminal_improvement_status(ImprovementStatus.EXECUTING) is False

    def test_valid_transitions(self):
        """Valid state transitions are allowed."""
        # PENDING -> APPROVED
        assert is_valid_improvement_transition(
            ImprovementStatus.PENDING, ImprovementStatus.APPROVED
        )
        # APPROVED -> EXECUTING
        assert is_valid_improvement_transition(
            ImprovementStatus.APPROVED, ImprovementStatus.EXECUTING
        )
        # EXECUTING -> VALIDATING
        assert is_valid_improvement_transition(
            ImprovementStatus.EXECUTING, ImprovementStatus.VALIDATING
        )
        # VALIDATING -> COMPLETED
        assert is_valid_improvement_transition(
            ImprovementStatus.VALIDATING, ImprovementStatus.COMPLETED
        )

    def test_invalid_transitions(self):
        """Invalid state transitions are rejected."""
        # Cannot go backwards
        assert not is_valid_improvement_transition(
            ImprovementStatus.EXECUTING, ImprovementStatus.PENDING
        )
        # Cannot skip states
        assert not is_valid_improvement_transition(
            ImprovementStatus.PENDING, ImprovementStatus.COMPLETED
        )
        # Terminal states have no transitions
        assert not is_valid_improvement_transition(
            ImprovementStatus.COMPLETED, ImprovementStatus.EXECUTING
        )


# ---------------------------------------------------------------------------
# Test 4: WSP15Priority marks low-lying fruit correctly
# ---------------------------------------------------------------------------


class TestWSP15Priority:
    """Test WSP 15 low-lying fruit priority scoring."""

    def test_low_risk_factory(self):
        """for_low_risk() creates correct priority."""
        priority = WSP15Priority.for_low_risk("Auto-fix documentation typo")
        assert priority.low_lying_fruit is True
        assert priority.estimated_complexity == "trivial"
        assert priority.blast_radius == "single_file"
        assert priority.requires_architect_review is False

    def test_medium_risk_factory(self):
        """for_medium_risk() creates correct priority."""
        priority = WSP15Priority.for_medium_risk("Module restructuring needed")
        assert priority.low_lying_fruit is False
        assert priority.estimated_complexity == "moderate"
        assert priority.requires_architect_review is True

    def test_high_risk_factory(self):
        """for_high_risk() creates correct priority."""
        priority = WSP15Priority.for_high_risk("Cross-module refactor")
        assert priority.low_lying_fruit is False
        assert priority.blast_radius == "cross_module"
        assert priority.requires_architect_review is True

    def test_serialization_roundtrip(self):
        """WSP15Priority serializes and deserializes correctly."""
        original = WSP15Priority(
            low_lying_fruit=True,
            estimated_complexity="simple",
            blast_radius="single_module",
            requires_architect_review=False,
            reason="Test reason",
        )
        as_dict = original.to_dict()
        restored = WSP15Priority.from_dict(as_dict)

        assert restored.low_lying_fruit == original.low_lying_fruit
        assert restored.estimated_complexity == original.estimated_complexity
        assert restored.blast_radius == original.blast_radius
        assert restored.requires_architect_review == original.requires_architect_review
        assert restored.reason == original.reason


# ---------------------------------------------------------------------------
# Test 5: Medium/high risk requires architect review
# ---------------------------------------------------------------------------


class TestArchitectReviewRequirements:
    """Test architect review enforcement for risk levels."""

    def test_low_risk_can_auto_approve(self):
        """LOW risk with low_lying_fruit can auto-approve."""
        job = create_improvement_job(
            finding_id="typo_001",
            improvement_type=ImprovementType.DOC_LEDGER_HYGIENE,
            risk_level=ImprovementRiskLevel.LOW,
            scope=ImprovementScope(
                module_path="modules/infrastructure/wre_core",
                file_paths=["modules/infrastructure/wre_core/README.md"],
            ),
        )
        # LOW risk factory sets requires_architect_review=False
        job.wsp15_priority.requires_architect_review = False
        job.wsp15_priority.low_lying_fruit = True

        assert job.can_auto_approve() is True
        assert job.requires_architect_review() is False

    def test_invalid_scope_cannot_auto_approve(self):
        """Traversal-bearing scope never qualifies for auto-approval."""
        job = create_improvement_job(
            finding_id="forged_001",
            improvement_type=ImprovementType.DOC_LEDGER_HYGIENE,
            risk_level=ImprovementRiskLevel.LOW,
            scope=ImprovementScope(
                module_path="modules/infrastructure/wre_core",
                file_paths=["modules/infrastructure/wre_core/../.env"],
            ),
        )
        job.wsp15_priority.requires_architect_review = False
        job.wsp15_priority.low_lying_fruit = True

        assert job.scope.is_well_formed() is False
        assert job.can_auto_approve() is False

    def test_medium_risk_requires_review(self):
        """MEDIUM risk always requires architect review."""
        job = create_improvement_job(
            finding_id="module_001",
            improvement_type=ImprovementType.MODULE_REPAIR,
            risk_level=ImprovementRiskLevel.MEDIUM,
        )
        assert job.requires_architect_review() is True
        assert job.can_auto_approve() is False

    def test_high_risk_requires_review(self):
        """HIGH risk always requires architect review."""
        job = create_improvement_job(
            finding_id="refactor_001",
            improvement_type=ImprovementType.DRIFT_CORRECTION,
            risk_level=ImprovementRiskLevel.HIGH,
        )
        assert job.requires_architect_review() is True
        assert job.can_auto_approve() is False

    def test_post_init_enforces_review_for_medium_risk(self):
        """__post_init__ enforces requires_architect_review for MEDIUM risk."""
        job = ImprovementJob(
            job_id="imp_test",
            finding_id="test",
            improvement_type=ImprovementType.MODULE_REPAIR,
            risk_level=ImprovementRiskLevel.MEDIUM,
            wsp15_priority=WSP15Priority(requires_architect_review=False),
        )
        # Should be forced to True by __post_init__
        assert job.wsp15_priority.requires_architect_review is True


# ---------------------------------------------------------------------------
# Test 6: Serialization round-trip
# ---------------------------------------------------------------------------


class TestSerialization:
    """Test ImprovementJob serialization."""

    def test_to_dict_includes_all_fields(self):
        """to_dict() includes all expected fields."""
        job = create_improvement_job(
            finding_id="test_finding",
            improvement_type=ImprovementType.WSP_VIOLATION,
            scope=ImprovementScope(
                module_path="modules/test",
                wsp_refs=["WSP 49", "WSP 22"],
            ),
        )
        d = job.to_dict()

        assert "job_id" in d
        assert "finding_id" in d
        assert "improvement_type" in d
        assert "status" in d
        assert "scope" in d
        assert "dry_run" in d
        assert "risk_level" in d
        assert "wsp15_priority" in d
        assert "evidence_refs" in d
        assert "validation_refs" in d
        assert "payload" in d

    def test_to_json_produces_valid_json(self):
        """to_json() produces valid JSON string."""
        job = create_improvement_job(
            finding_id="json_test",
            improvement_type=ImprovementType.FMAS_SCAN,
        )
        json_str = job.to_json()

        # Should parse without error
        parsed = json.loads(json_str)
        assert parsed["finding_id"] == "json_test"
        assert parsed["dry_run"] is True

    def test_roundtrip_serialization(self):
        """Job survives to_dict/from_dict round-trip."""
        original = create_improvement_job(
            finding_id="roundtrip_test",
            improvement_type=ImprovementType.ORPHAN_CONNECTION,
            scope=ImprovementScope(
                module_path="modules/orphan",
                file_paths=["src/orphan.py"],
                wsp_refs=["WSP 88"],
            ),
            risk_level=ImprovementRiskLevel.LOW,
            requested_by="012",
            payload={"orphan_id": "orphan_123"},
        )
        original.evidence_refs.append("orphan_report.json")

        as_dict = original.to_dict()
        restored = ImprovementJob.from_dict(as_dict)

        assert restored.job_id == original.job_id
        assert restored.finding_id == original.finding_id
        assert restored.improvement_type == original.improvement_type
        assert restored.dry_run == original.dry_run
        assert restored.risk_level == original.risk_level
        assert restored.requested_by == original.requested_by
        assert restored.evidence_refs == original.evidence_refs
        assert restored.payload == original.payload


# ---------------------------------------------------------------------------
# Test 7: validate_scope accepts allowed path
# ---------------------------------------------------------------------------


class TestScopeValidation:
    """Test ImprovementScope path validation."""

    def test_validate_scope_accepts_allowed_path(self):
        """Paths within allowed scope are accepted."""
        scope = ImprovementScope(
            module_path="modules/infrastructure/wre_core",
            allowed_paths=["modules/infrastructure/wre_core/**"],
        )
        job = ImprovementJob(
            job_id="imp_scope_test",
            finding_id="scope_001",
            improvement_type=ImprovementType.MODULE_REPAIR,
            scope=scope,
        )

        assert job.validate_scope("modules/infrastructure/wre_core/src/test.py") is True
        assert job.validate_scope("modules/infrastructure/wre_core/tests/test_x.py") is True

    def test_validate_scope_accepts_specific_files(self):
        """Specific file_paths are accepted."""
        scope = ImprovementScope(
            module_path="modules/test",
            file_paths=["src/specific.py", "tests/test_specific.py"],
        )
        job = ImprovementJob(
            job_id="imp_file_test",
            finding_id="file_001",
            improvement_type=ImprovementType.TEST_HYGIENE,
            scope=scope,
        )

        assert job.validate_scope("modules/test/src/specific.py") is True
        assert job.validate_scope("modules/test/tests/test_specific.py") is True


# ---------------------------------------------------------------------------
# Test 8: validate_scope rejects blocked/out-of-scope path
# ---------------------------------------------------------------------------


class TestScopeRejection:
    """Test ImprovementScope path rejection."""

    def test_validate_scope_rejects_blocked_path(self):
        """Blocked paths are rejected."""
        scope = ImprovementScope(
            module_path="modules/test",
            allowed_paths=["modules/test/**"],
            blocked_paths=["**/secrets.py", "**/credentials.json"],
        )
        job = ImprovementJob(
            job_id="imp_blocked_test",
            finding_id="blocked_001",
            improvement_type=ImprovementType.MODULE_REPAIR,
            scope=scope,
        )

        # Allowed path
        assert job.validate_scope("modules/test/src/normal.py") is True
        # Blocked paths
        assert job.validate_scope("modules/test/src/secrets.py") is False
        assert job.validate_scope("modules/test/config/credentials.json") is False

    def test_validate_scope_rejects_out_of_scope(self):
        """Paths outside allowed scope are rejected."""
        scope = ImprovementScope(
            module_path="modules/specific",
            allowed_paths=["modules/specific/**"],
        )
        job = ImprovementJob(
            job_id="imp_outofscope_test",
            finding_id="oos_001",
            improvement_type=ImprovementType.DRIFT_CORRECTION,
            scope=scope,
        )

        # In scope
        assert job.validate_scope("modules/specific/src/file.py") is True
        # Out of scope
        assert job.validate_scope("modules/other/src/file.py") is False
        assert job.validate_scope("holo_index/src/file.py") is False

    @pytest.mark.parametrize(
        "path",
        [
            "modules/test/../.env.py",
            "modules/test/src/../../.env.py",
            "C:/modules/test/src/file.py",
            "/modules/test/src/file.py",
            "modules/test/src/file.py\x00.extra",
        ],
    )
    def test_validate_scope_rejects_noncanonical_paths(self, path):
        scope = ImprovementScope(
            module_path="modules/test",
            file_paths=["modules/test/src/file.py"],
        )
        job = ImprovementJob(
            job_id="imp_scope_attack",
            finding_id="scope_attack",
            improvement_type=ImprovementType.MODULE_REPAIR,
            scope=scope,
        )
        assert job.validate_scope(path) is False


# ---------------------------------------------------------------------------
# Test 9: No CABR/reward/payout/token fields exist
# ---------------------------------------------------------------------------


class TestNoEconomicFields:
    """WSP 97: Verify no CABR/reward/payout/token fields exist."""

    def test_no_cabr_fields(self):
        """ImprovementJob has no CABR-related fields."""
        job = create_improvement_job(
            finding_id="econ_test",
            improvement_type=ImprovementType.MODULE_REPAIR,
        )

        forbidden_attrs = [
            "cabr",
            "cabr_score",
            "cabr_ready",
            "reward",
            "reward_amount",
            "payout",
            "payout_amount",
            "token",
            "token_amount",
            "ups",
            "f_i",
        ]
        for attr in forbidden_attrs:
            assert not hasattr(job, attr), f"ImprovementJob should not have {attr}"

    def test_no_economic_fields_in_serialization(self):
        """Serialized job has no economic fields."""
        job = create_improvement_job(
            finding_id="serial_econ_test",
            improvement_type=ImprovementType.FMAS_SCAN,
        )
        d = job.to_dict()

        forbidden_keys = [
            "cabr", "cabr_score", "reward", "payout", "token", "ups", "f_i"
        ]
        for key in forbidden_keys:
            assert key not in d, f"Serialized job should not have {key}"


# ---------------------------------------------------------------------------
# Test 10: No execution methods exist
# ---------------------------------------------------------------------------


class TestNoExecutionMethods:
    """WSP 97: Verify no execution methods exist."""

    def test_no_execute_method(self):
        """ImprovementJob has no execute() method."""
        job = create_improvement_job(
            finding_id="exec_test",
            improvement_type=ImprovementType.MODULE_REPAIR,
        )
        assert not hasattr(job, "execute")
        assert not hasattr(job, "run")
        assert not hasattr(job, "perform")
        assert not hasattr(job, "repair")

    def test_no_transition_methods(self):
        """ImprovementJob has no state transition methods (unlike FoundUpJob)."""
        job = create_improvement_job(
            finding_id="trans_test",
            improvement_type=ImprovementType.TEST_HYGIENE,
        )
        # Unlike FoundUpJob, ImprovementJob is contract-only
        # State transitions happen externally
        assert not hasattr(job, "start")
        assert not hasattr(job, "succeed")
        assert not hasattr(job, "fail")
        assert not hasattr(job, "transition_to")


# ---------------------------------------------------------------------------
# Additional Tests
# ---------------------------------------------------------------------------


class TestJobIdGeneration:
    """Test job ID generation."""

    def test_generate_job_id_format(self):
        """Generated job IDs have correct format."""
        job_id = generate_improvement_job_id(ImprovementType.WSP_VIOLATION)
        assert job_id.startswith("imp_")
        parts = job_id.split("_")
        assert len(parts) == 4  # imp_type_timestamp_random

    def test_generated_ids_are_unique(self):
        """Generated job IDs are unique."""
        ids = [
            generate_improvement_job_id(ImprovementType.MODULE_REPAIR)
            for _ in range(100)
        ]
        assert len(set(ids)) == 100


class TestRiskLevelEnum:
    """Test ImprovementRiskLevel enum."""

    def test_all_risk_levels_exist(self):
        """All expected risk levels are defined."""
        expected_levels = {"low", "medium", "high"}
        actual_levels = {r.value for r in ImprovementRiskLevel}
        assert actual_levels == expected_levels


class TestReasonCodeEnum:
    """Test ImprovementReasonCode enum."""

    def test_success_codes_exist(self):
        """Success reason codes exist."""
        assert ImprovementReasonCode.OK_COMPLETED
        assert ImprovementReasonCode.OK_DRY_RUN_PASSED
        assert ImprovementReasonCode.OK_AUTO_APPROVED

    def test_failure_codes_exist(self):
        """Failure reason codes exist."""
        assert ImprovementReasonCode.FAIL_VALIDATION_ERROR
        assert ImprovementReasonCode.FAIL_FMAS_CHECK
        assert ImprovementReasonCode.FAIL_SCOPE_VIOLATION

    def test_blocked_codes_exist(self):
        """Blocked reason codes exist."""
        assert ImprovementReasonCode.BLOCKED_REQUIRES_ARCHITECT_REVIEW
        assert ImprovementReasonCode.BLOCKED_SCOPE_VIOLATION


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
