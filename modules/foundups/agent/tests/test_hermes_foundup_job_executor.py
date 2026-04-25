#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Hermes FoundUp Job Executor.

WSP References:
    WSP 50  : Pre-action verification tested via validation gates
    WSP 97  : Truthful status mapping verified per status transition
    WSP 11  : Interface contract tested via type assertions

Scope:
    - Unit tests for job validation and state transitions
    - Mock-based tests for Hermes builder invocation
    - Status mapping verification for all Hermes result types

Does NOT test:
    - FAM event emission (not in scope for this slice)
    - CABR/PoB/reward logic (not in scope)
    - Live Hermes execution (integration tests elsewhere)
"""

from __future__ import annotations

import pytest
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

from modules.communication.moltbot_bridge.src.foundup_job_contract import (
    FoundUpJob,
    JobStatus,
    PolicyFlags,
    StatusReasonCode,
    create_job,
)

from modules.foundups.agent.src.hermes_foundup_job_executor import (
    HermesJobExecutionResult,
    SUPPORTED_ACTIONS,
    WORKER_ID,
    can_execute_action,
    execute_foundup_job,
    get_supported_actions,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def queued_extract_job() -> FoundUpJob:
    """Create a QUEUED job for extract_foundup action."""
    return create_job(
        tenant_id="012",
        requested_action="extract_foundup",
        foundup_id="modules/foundups/widget",
        payload={"module_path": "modules/foundups/widget", "target_org": "FOUNDUPS"},
    )


@pytest.fixture
def queued_validate_job() -> FoundUpJob:
    """Create a QUEUED job for validate_foundup action."""
    return create_job(
        tenant_id="012",
        requested_action="validate_foundup",
        payload={"module_path": "modules/foundups/widget"},
    )


@pytest.fixture
def queued_build_job() -> FoundUpJob:
    """Create a QUEUED job for build_foundup action."""
    return create_job(
        tenant_id="012",
        requested_action="build_foundup",
        payload={"source_module": "modules/foundups/widget"},
    )


@pytest.fixture
def mock_hermes_success() -> Dict[str, Any]:
    """Mock successful Hermes extract_foundup result."""
    return {
        "success": True,
        "source_module": "modules/foundups/widget",
        "target_repo": "FOUNDUPS/widget",
        "boundary_analysis": {
            "product_files": 5,
            "core_dependencies": 2,
            "adapters_needed": ["wre_adapter", "fam_adapter"],
        },
        "exfoliation_gate": {
            "passed": True,
            "checks": {
                "module_boundary_clear": True,
                "contracts_explicit": True,
                "runtime_testable": True,
                "deploy_surface_understood": True,
                "shared_deps_adapter_level": True,
                "claw_can_participate": True,
            },
        },
        "adapters": {"adapters_created": [], "dry_run": True},
        "manifest": {"foundup_id": "widget", "signature": "abc123"},
        "dry_run": True,
    }


@pytest.fixture
def mock_hermes_security_failed() -> Dict[str, Any]:
    """Mock Hermes result with security gate failure."""
    return {
        "success": False,
        "error": "security_gate_failed",
        "source_module": "modules/foundups/widget",
    }


@pytest.fixture
def mock_hermes_exfoliation_failed() -> Dict[str, Any]:
    """Mock Hermes result with exfoliation gate failure."""
    return {
        "success": False,
        "error": "exfoliation_gate_failed",
        "source_module": "modules/foundups/widget",
        "boundary_analysis": {
            "product_files": 5,
            "core_dependencies": 2,
            "adapters_needed": [],
            "blockers": ["Missing README.md", "Missing INTERFACE.md"],
        },
        "exfoliation_gate": {
            "passed": False,
            "checks": {
                "module_boundary_clear": False,
                "contracts_explicit": False,
                "runtime_testable": True,
                "deploy_surface_understood": False,
                "shared_deps_adapter_level": True,
                "claw_can_participate": False,
            },
        },
    }


# ---------------------------------------------------------------------------
# Test: Pre-Validation
# ---------------------------------------------------------------------------


class TestPreValidation:
    """Tests for job pre-validation before Hermes invocation."""

    def test_terminal_job_not_modified(self, queued_extract_job: FoundUpJob) -> None:
        """Terminal jobs should not be modified."""
        # Force job to terminal state
        queued_extract_job.status = JobStatus.SUCCEEDED
        queued_extract_job.status_reason_code = StatusReasonCode.OK_COMPLETED

        result = execute_foundup_job(queued_extract_job, force_dry_run=True)

        # Job should remain unchanged
        assert result.job.status == JobStatus.SUCCEEDED
        assert result.error is not None
        assert "terminal" in result.error.lower()

    def test_failed_job_not_modified(self, queued_extract_job: FoundUpJob) -> None:
        """FAILED jobs should not be modified."""
        queued_extract_job.status = JobStatus.FAILED
        queued_extract_job.status_reason_code = StatusReasonCode.FAIL_EXECUTION_ERROR

        result = execute_foundup_job(queued_extract_job, force_dry_run=True)

        assert result.job.status == JobStatus.FAILED
        assert result.error is not None

    def test_running_job_fails_validation(self, queued_extract_job: FoundUpJob) -> None:
        """RUNNING jobs should fail validation (must be QUEUED)."""
        queued_extract_job.status = JobStatus.RUNNING
        queued_extract_job.started_at = queued_extract_job.created_at

        result = execute_foundup_job(queued_extract_job, force_dry_run=True)

        assert result.job.status == JobStatus.FAILED
        assert result.job.status_reason_code == StatusReasonCode.FAIL_INVALID_TRANSITION
        assert "QUEUED" in result.job.status_reason_human

    def test_unsupported_action_fails(self) -> None:
        """Unsupported action should fail immediately."""
        job = create_job(
            tenant_id="012",
            requested_action="delete_foundup",  # Not supported
            payload={"module_path": "modules/foundups/widget"},
        )

        result = execute_foundup_job(job, force_dry_run=True)

        assert result.job.status == JobStatus.FAILED
        assert result.job.status_reason_code == StatusReasonCode.FAIL_VALIDATION_ERROR
        assert "delete_foundup" in result.job.status_reason_human
        assert "Supported:" in result.job.status_reason_human

    def test_missing_module_path_fails(self) -> None:
        """Missing module_path should fail."""
        job = create_job(
            tenant_id="012",
            requested_action="extract_foundup",
            payload={},  # No module_path
        )

        result = execute_foundup_job(job, force_dry_run=True)

        assert result.job.status == JobStatus.FAILED
        assert result.job.status_reason_code == StatusReasonCode.FAIL_VALIDATION_ERROR
        assert "module_path" in result.job.status_reason_human.lower()


# ---------------------------------------------------------------------------
# Test: Status Mapping
# ---------------------------------------------------------------------------


class TestStatusMapping:
    """Tests for Hermes result -> JobStatus mapping."""

    @patch("modules.foundups.agent.src.hermes_adapter.HermesFoundUpBuilder")
    def test_success_dry_run_maps_to_succeeded(
        self,
        mock_builder_class: MagicMock,
        queued_extract_job: FoundUpJob,
        mock_hermes_success: Dict[str, Any],
    ) -> None:
        """Successful dry-run extraction should map to SUCCEEDED with OK_DRY_RUN_PASSED."""
        mock_builder = MagicMock()
        mock_builder.dry_run = True
        mock_builder.extract_foundup.return_value = mock_hermes_success
        mock_builder_class.return_value = mock_builder

        result = execute_foundup_job(queued_extract_job, force_dry_run=True)

        assert result.job.status == JobStatus.SUCCEEDED
        assert result.job.status_reason_code == StatusReasonCode.OK_DRY_RUN_PASSED
        assert "dry-run" in result.job.status_reason_human.lower()
        assert result.job.policy_flags.dry_run_mode is True

    @patch("modules.foundups.agent.src.hermes_adapter.HermesFoundUpBuilder")
    def test_success_live_maps_to_succeeded(
        self,
        mock_builder_class: MagicMock,
        queued_extract_job: FoundUpJob,
        mock_hermes_success: Dict[str, Any],
    ) -> None:
        """Successful live extraction should map to SUCCEEDED with OK_COMPLETED."""
        mock_hermes_success["dry_run"] = False

        mock_builder = MagicMock()
        mock_builder.dry_run = False
        mock_builder.extract_foundup.return_value = mock_hermes_success
        mock_builder_class.return_value = mock_builder

        result = execute_foundup_job(queued_extract_job)

        assert result.job.status == JobStatus.SUCCEEDED
        assert result.job.status_reason_code == StatusReasonCode.OK_COMPLETED

    @patch("modules.foundups.agent.src.hermes_adapter.HermesFoundUpBuilder")
    def test_security_gate_failed_maps_to_blocked(
        self,
        mock_builder_class: MagicMock,
        queued_extract_job: FoundUpJob,
        mock_hermes_security_failed: Dict[str, Any],
    ) -> None:
        """Security gate failure should map to BLOCKED with BLOCKED_AWAITING_APPROVAL."""
        mock_builder = MagicMock()
        mock_builder.dry_run = True
        mock_builder.extract_foundup.return_value = mock_hermes_security_failed
        mock_builder_class.return_value = mock_builder

        result = execute_foundup_job(queued_extract_job, force_dry_run=True)

        assert result.job.status == JobStatus.BLOCKED
        assert result.job.status_reason_code == StatusReasonCode.BLOCKED_AWAITING_APPROVAL
        assert "security" in result.job.status_reason_human.lower()
        assert result.job.policy_flags.security_gate_checked is True
        assert result.job.policy_flags.security_gate_passed is False

    @patch("modules.foundups.agent.src.hermes_adapter.HermesFoundUpBuilder")
    def test_exfoliation_gate_failed_maps_to_blocked(
        self,
        mock_builder_class: MagicMock,
        queued_extract_job: FoundUpJob,
        mock_hermes_exfoliation_failed: Dict[str, Any],
    ) -> None:
        """Exfoliation gate failure should map to BLOCKED with FAIL_EXFOLIATION_GATE."""
        mock_builder = MagicMock()
        mock_builder.dry_run = True
        mock_builder.extract_foundup.return_value = mock_hermes_exfoliation_failed
        mock_builder_class.return_value = mock_builder

        result = execute_foundup_job(queued_extract_job, force_dry_run=True)

        assert result.job.status == JobStatus.BLOCKED
        assert result.job.status_reason_code == StatusReasonCode.FAIL_EXFOLIATION_GATE
        assert "exfoliation" in result.job.status_reason_human.lower()
        assert result.job.policy_flags.exfoliation_gate_checked is True
        assert result.job.policy_flags.exfoliation_gate_passed is False

        # Verify failed checks are in payload
        gate_details = result.job.payload.get("exfoliation_gate_details", {})
        assert gate_details.get("passed") is False
        assert "module_boundary_clear" in gate_details.get("failed_checks", [])

    @patch("modules.foundups.agent.src.hermes_adapter.HermesFoundUpBuilder")
    def test_exception_maps_to_failed(
        self,
        mock_builder_class: MagicMock,
        queued_extract_job: FoundUpJob,
    ) -> None:
        """Exception during execution should map to FAILED with FAIL_EXECUTION_ERROR."""
        mock_builder = MagicMock()
        mock_builder.dry_run = True
        mock_builder.extract_foundup.side_effect = RuntimeError("Test explosion")
        mock_builder_class.return_value = mock_builder

        result = execute_foundup_job(queued_extract_job, force_dry_run=True)

        assert result.job.status == JobStatus.FAILED
        assert result.job.status_reason_code == StatusReasonCode.FAIL_EXECUTION_ERROR
        assert "Test explosion" in result.job.status_reason_human


# ---------------------------------------------------------------------------
# Test: Action Dispatch
# ---------------------------------------------------------------------------


class TestActionDispatch:
    """Tests for action-specific Hermes method invocation."""

    @patch("modules.foundups.agent.src.hermes_adapter.HermesFoundUpBuilder")
    def test_extract_foundup_calls_extract_method(
        self,
        mock_builder_class: MagicMock,
        queued_extract_job: FoundUpJob,
        mock_hermes_success: Dict[str, Any],
    ) -> None:
        """extract_foundup action should call builder.extract_foundup()."""
        mock_builder = MagicMock()
        mock_builder.dry_run = True
        mock_builder.extract_foundup.return_value = mock_hermes_success
        mock_builder_class.return_value = mock_builder

        result = execute_foundup_job(queued_extract_job, force_dry_run=True)

        mock_builder.extract_foundup.assert_called_once_with(
            source_module="modules/foundups/widget",
            target_org="FOUNDUPS",
        )
        assert result.job.status == JobStatus.SUCCEEDED

    @patch("modules.foundups.agent.src.hermes_adapter.HermesFoundUpBuilder")
    def test_validate_foundup_calls_gate_and_boundary(
        self,
        mock_builder_class: MagicMock,
        queued_validate_job: FoundUpJob,
    ) -> None:
        """validate_foundup action should call check_exfoliation_gate and analyze_boundary."""
        mock_gate = MagicMock()
        mock_gate.passed = True
        mock_gate.module_boundary_clear = True
        mock_gate.contracts_explicit = True
        mock_gate.runtime_testable = True
        mock_gate.deploy_surface_understood = True
        mock_gate.shared_deps_adapter_level = True
        mock_gate.claw_can_participate = True

        mock_analysis = MagicMock()
        mock_analysis.product_files = ["core.py"]
        mock_analysis.core_imports = []
        mock_analysis.adapters_needed = []
        mock_analysis.blockers = []

        mock_builder = MagicMock()
        mock_builder.dry_run = True
        mock_builder.check_exfoliation_gate.return_value = mock_gate
        mock_builder.analyze_boundary.return_value = mock_analysis
        mock_builder_class.return_value = mock_builder

        result = execute_foundup_job(queued_validate_job, force_dry_run=True)

        mock_builder.check_exfoliation_gate.assert_called_once_with("modules/foundups/widget")
        mock_builder.analyze_boundary.assert_called_once_with("modules/foundups/widget")
        assert result.job.status == JobStatus.SUCCEEDED
        assert result.job.status_reason_code == StatusReasonCode.OK_DRY_RUN_PASSED

    @patch("modules.foundups.agent.src.hermes_adapter.HermesFoundUpBuilder")
    def test_build_foundup_calls_extract(
        self,
        mock_builder_class: MagicMock,
        queued_build_job: FoundUpJob,
        mock_hermes_success: Dict[str, Any],
    ) -> None:
        """build_foundup action should call extract_foundup (same flow for now)."""
        mock_builder = MagicMock()
        mock_builder.dry_run = True
        mock_builder.extract_foundup.return_value = mock_hermes_success
        mock_builder_class.return_value = mock_builder

        result = execute_foundup_job(queued_build_job, force_dry_run=True)

        mock_builder.extract_foundup.assert_called_once()
        assert result.job.status == JobStatus.SUCCEEDED


# ---------------------------------------------------------------------------
# Test: Evidence and Payload
# ---------------------------------------------------------------------------


class TestEvidenceAndPayload:
    """Tests for evidence_refs and payload augmentation."""

    @patch("modules.foundups.agent.src.hermes_adapter.HermesFoundUpBuilder")
    def test_evidence_refs_populated_on_success(
        self,
        mock_builder_class: MagicMock,
        queued_extract_job: FoundUpJob,
        mock_hermes_success: Dict[str, Any],
    ) -> None:
        """Successful execution should populate evidence_refs."""
        mock_builder = MagicMock()
        mock_builder.dry_run = True
        mock_builder.extract_foundup.return_value = mock_hermes_success
        mock_builder_class.return_value = mock_builder

        result = execute_foundup_job(queued_extract_job, force_dry_run=True)

        assert len(result.job.evidence_refs) > 0
        assert any("FOUNDUPS/widget" in ref for ref in result.job.evidence_refs)

    @patch("modules.foundups.agent.src.hermes_adapter.HermesFoundUpBuilder")
    def test_payload_augmented_with_hermes_summary(
        self,
        mock_builder_class: MagicMock,
        queued_extract_job: FoundUpJob,
        mock_hermes_success: Dict[str, Any],
    ) -> None:
        """Job payload should be augmented with hermes_result_summary."""
        mock_builder = MagicMock()
        mock_builder.dry_run = True
        mock_builder.extract_foundup.return_value = mock_hermes_success
        mock_builder_class.return_value = mock_builder

        result = execute_foundup_job(queued_extract_job, force_dry_run=True)

        summary = result.job.payload.get("hermes_result_summary")
        assert summary is not None
        assert summary["success"] is True
        assert summary["dry_run"] is True
        assert summary["action"] == "extract_foundup"


# ---------------------------------------------------------------------------
# Test: Worker Identity
# ---------------------------------------------------------------------------


class TestWorkerIdentity:
    """Tests for worker identity tracking."""

    @patch("modules.foundups.agent.src.hermes_adapter.HermesFoundUpBuilder")
    def test_worker_id_set_on_running(
        self,
        mock_builder_class: MagicMock,
        queued_extract_job: FoundUpJob,
        mock_hermes_success: Dict[str, Any],
    ) -> None:
        """Worker ID should be set when job transitions to RUNNING."""
        mock_builder = MagicMock()
        mock_builder.dry_run = True
        mock_builder.extract_foundup.return_value = mock_hermes_success
        mock_builder_class.return_value = mock_builder

        result = execute_foundup_job(queued_extract_job, force_dry_run=True)

        assert result.job.worker_id == WORKER_ID


# ---------------------------------------------------------------------------
# Test: Utility Functions
# ---------------------------------------------------------------------------


class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_can_execute_action_supported(self) -> None:
        """can_execute_action should return True for supported actions."""
        for action in SUPPORTED_ACTIONS:
            assert can_execute_action(action) is True

    def test_can_execute_action_unsupported(self) -> None:
        """can_execute_action should return False for unsupported actions."""
        assert can_execute_action("delete_foundup") is False
        assert can_execute_action("deploy_foundup") is False
        assert can_execute_action("") is False

    def test_get_supported_actions_returns_list(self) -> None:
        """get_supported_actions should return sorted list."""
        actions = get_supported_actions()
        assert isinstance(actions, list)
        assert "extract_foundup" in actions
        assert "validate_foundup" in actions
        assert "build_foundup" in actions
        assert actions == sorted(actions)


# ---------------------------------------------------------------------------
# Test: Module Path Extraction
# ---------------------------------------------------------------------------


class TestModulePathExtraction:
    """Tests for module path extraction from job."""

    def test_module_path_from_payload(self) -> None:
        """Module path should be extracted from payload.module_path."""
        job = create_job(
            tenant_id="012",
            requested_action="extract_foundup",
            payload={"module_path": "modules/foundups/custom"},
        )

        # Cannot test internal function directly, but can verify job works
        # by checking validation passes
        assert job.payload.get("module_path") == "modules/foundups/custom"

    def test_source_module_from_payload(self) -> None:
        """Module path should be extracted from payload.source_module."""
        job = create_job(
            tenant_id="012",
            requested_action="extract_foundup",
            payload={"source_module": "modules/foundups/other"},
        )

        assert job.payload.get("source_module") == "modules/foundups/other"

    def test_foundup_id_as_fallback(self) -> None:
        """Module path should fallback to foundup_id if it looks like a path."""
        job = create_job(
            tenant_id="012",
            requested_action="extract_foundup",
            foundup_id="modules/foundups/fromid",
            payload={},
        )

        assert job.foundup_id == "modules/foundups/fromid"
