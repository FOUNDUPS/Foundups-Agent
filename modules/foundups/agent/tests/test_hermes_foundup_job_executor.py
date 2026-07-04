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
    """Create a QUEUED job for extract_foundup action.

    Uses a REAL on-disk manifest (gotjunk_001 at modules/foundups/gotjunk)
    so the new validated-resolution pre-flight
    (HERMES_MODULE_PATH_TRUST_REMOVAL_PHASE1) passes and the test can
    exercise the downstream mocked Hermes path. Prior to the trust-
    removal patch this fixture used a synthetic ``modules/foundups/widget``
    path; that no longer reaches the executor because the new pre-flight
    rejects any module_path without a backing validated manifest.
    """
    return create_job(
        tenant_id="012",
        requested_action="extract_foundup",
        foundup_id="gotjunk_001",
        payload={"module_path": "modules/foundups/gotjunk", "target_org": "FOUNDUPS"},
    )


@pytest.fixture
def queued_validate_job() -> FoundUpJob:
    """Create a QUEUED job for validate_foundup action (real manifest)."""
    return create_job(
        tenant_id="012",
        requested_action="validate_foundup",
        foundup_id="gotjunk_001",
        payload={"module_path": "modules/foundups/gotjunk"},
    )


@pytest.fixture
def queued_build_job() -> FoundUpJob:
    """Create a QUEUED job for build_foundup action (real manifest, alias key)."""
    return create_job(
        tenant_id="012",
        requested_action="build_foundup",
        foundup_id="gotjunk_001",
        payload={"source_module": "modules/foundups/gotjunk"},
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


# ---------------------------------------------------------------------------
# HERMES_BUILDER_DRYRUN_DEFAULT_SAFETY_PHASE1 acceptance A4
# ---------------------------------------------------------------------------


def test_a4_executor_respects_builder_dry_run_default(
    queued_validate_job: FoundUpJob, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A4: execute_foundup_job(..., force_dry_run=False) with no env opt-in must
    still run dry-run, because the builder now defaults to dry-run. The executor
    must not silently enable real writes when the caller merely declines to force
    dry-run.

    Ref: docs/audits/architecture/HERMES_BUILDER_DRYRUN_DEFAULT_SAFETY_PHASE1.md
    """
    monkeypatch.delenv("HERMES_BUILDER_DRY_RUN", raising=False)
    monkeypatch.delenv("HERMES_BUILDER_ALLOW_REAL_WRITES", raising=False)
    monkeypatch.setenv("HERMES_BUILDER_SECURITY_GATE", "0")

    repo_root = Path(__file__).resolve().parents[4]
    result = execute_foundup_job(
        queued_validate_job, repo_root=repo_root, force_dry_run=False
    )

    # Builder default (dry-run) is reflected in the job's policy flags...
    assert result.job.policy_flags.dry_run_mode is True
    # ...and in the Hermes result payload when the action dispatched.
    if result.hermes_result is not None:
        assert result.hermes_result.get("dry_run") is True


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

        # UPDATED for HERMES_MODULE_PATH_TRUST_REMOVAL_PHASE1: the queued_extract_job
        # fixture now uses real manifest ``modules/foundups/gotjunk`` so the validated
        # pre-flight passes; the dispatch then forwards the validator-confirmed
        # canonical path (NOT a raw payload string) into the builder.
        mock_builder.extract_foundup.assert_called_once_with(
            source_module="modules/foundups/gotjunk",
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

        # UPDATED for HERMES_MODULE_PATH_TRUST_REMOVAL_PHASE1: the fixture now
        # uses real manifest ``modules/foundups/gotjunk`` (see fixture docstring).
        mock_builder.check_exfoliation_gate.assert_called_once_with("modules/foundups/gotjunk")
        mock_builder.analyze_boundary.assert_called_once_with("modules/foundups/gotjunk")
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
    """Tests for module path extraction from job.

    UPDATED (HERMES_MODULE_PATH_TRUST_REMOVAL_PHASE1, see TestModLog):
    These tests previously pinned the prior raw-payload-trust behavior
    of ``_extract_module_path`` (which trusted ``payload.module_path``
    /  ``payload.source_module`` / a ``foundup_id`` containing "/"
    without manifest validation). The function has been REMOVED;
    resolution now flows through ``_resolve_validated_module_path`` which
    requires the #773 manifest validator to confirm the path. The
    payload-shape assertions below are retained for documentation but the
    foundup-id-as-fallback test is replaced by an explicit
    no-inference assertion.
    """

    def test_module_path_from_payload(self) -> None:
        """Payload may declare module_path; the validated resolver decides
        whether it is the source of truth (see
        TestResolvedModulePathValidation)."""
        job = create_job(
            tenant_id="012",
            requested_action="extract_foundup",
            payload={"module_path": "modules/foundups/custom"},
        )
        assert job.payload.get("module_path") == "modules/foundups/custom"

    def test_source_module_from_payload(self) -> None:
        """The ``source_module`` alias key may also declare a candidate
        module_path; the validated resolver treats it identically to
        ``module_path``."""
        job = create_job(
            tenant_id="012",
            requested_action="extract_foundup",
            payload={"source_module": "modules/foundups/other"},
        )
        assert job.payload.get("source_module") == "modules/foundups/other"

    def test_foundup_id_path_heuristic_removed(self) -> None:
        """The prior heuristic "foundup_id contains '/' -> treat as path"
        is REMOVED. A path-shaped foundup_id with no payload module_path
        no longer resolves to a module path by itself; the executor must
        find a real manifest by foundup_id or fail
        ``manifest_missing``."""
        from modules.foundups.agent.src.hermes_foundup_job_executor import (
            DEFAULT_REPO_ROOT,
            FAIL_TOKEN_MANIFEST_MISSING,
            _resolve_validated_module_path,
        )
        job = create_job(
            tenant_id="012",
            requested_action="extract_foundup",
            foundup_id="modules/foundups/fromid",  # path-shaped, fake
            payload={},
        )
        resolved = _resolve_validated_module_path(job, DEFAULT_REPO_ROOT)
        assert resolved.failed is True
        assert resolved.fail_token == FAIL_TOKEN_MANIFEST_MISSING
        assert resolved.effective is None
        # Even though the foundup_id "looks like a path", it is NOT used
        # as a path source by the resolver.
        assert "modules/foundups/fromid" not in (resolved.fail_human or "").lower() \
            or "manifest_missing" in resolved.fail_human


# ---------------------------------------------------------------------------
# HERMES_MODULE_PATH_TRUST_REMOVAL_PHASE1: validated module-path resolution
# ---------------------------------------------------------------------------


class TestResolvedModulePathValidation:
    """Validated-resolution tests for ``_resolve_validated_module_path``.

    These tests replace the prior raw-trust extraction and pin the
    fail-closed contract dictated by HERMES_MODULE_PATH_TRUST_REMOVAL_PHASE1.
    Real on-disk manifests (gotjunk_001, kosei) are used as the happy-path
    anchors so the validator's exact-match check has a stable target.

    Coverage map (Addendum C tests 1-8 + Addendum D tests 1, 3, 4 +
    Addendum A 4-step fork protocol verified by the resolver's
    fail-token taxonomy):
      C1 mismatch              -> test_payload_path_wrong_manifest_path_rejected
      C2 alias mismatch        -> test_source_module_alias_validates_same_as_module_path
      C3 foundup_id heuristic  -> TestModulePathExtraction.test_foundup_id_path_heuristic_removed
      C4 suffix-only           -> test_suffix_only_path_rejected
      C5 backslash             -> test_backslash_payload_rejected_pre_manifest
      C6 absolute / traversal  -> test_absolute_path_rejected_pre_manifest /
                                  test_traversal_path_rejected_pre_manifest
      C7 omitted               -> test_payload_omitted_derives_from_validated_manifest
      C8 observable ignored    -> test_rejected_payload_value_appears_in_evidence
      D1 cross-foundup         -> test_cross_foundup_substitution_rejected
      D3 case-variant          -> test_case_variant_payload_rejected
      D4 empty-string semantics-> test_empty_string_payload_treated_as_absent
    """

    # ---- Imports / constants used throughout the class ------------------

    @staticmethod
    def _resolver_module():
        from modules.foundups.agent.src import hermes_foundup_job_executor as e
        return e

    @staticmethod
    def _resolve(job):
        e = TestResolvedModulePathValidation._resolver_module()
        return e._resolve_validated_module_path(job, e.DEFAULT_REPO_ROOT)

    # ---- Happy paths ----------------------------------------------------

    def test_happy_path_real_manifest_resolves_to_canonical(self) -> None:
        """Real manifest gotjunk_001 + matching payload: resolves to the
        validator-confirmed canonical module_path. Observable-ignore
        preserves the payload value even though it equals the result."""
        job = create_job(
            tenant_id="012",
            requested_action="extract_foundup",
            foundup_id="gotjunk_001",
            payload={"module_path": "modules/foundups/gotjunk"},
        )
        r = self._resolve(job)
        assert r.failed is False
        assert r.effective == "modules/foundups/gotjunk"
        assert r.ignored == "modules/foundups/gotjunk"  # observable even on success
        assert r.fail_token is None

    def test_cross_domain_real_manifest_resolves(self) -> None:
        """Cross-domain real manifest (kosei) is also accepted."""
        job = create_job(
            tenant_id="012",
            requested_action="extract_foundup",
            foundup_id="kosei",
            payload={"module_path": "modules/foundups/kosei"},
        )
        r = self._resolve(job)
        assert r.failed is False
        assert r.effective == "modules/foundups/kosei"

    # ---- Addendum C #1: payload path wrong manifest path ----------------

    def test_payload_path_wrong_manifest_path_rejected(self) -> None:
        """Payload points at a path with no backing manifest -> manifest_missing
        (the value is rejected before the executor's subprocess sink)."""
        e = self._resolver_module()
        job = create_job(
            tenant_id="012",
            requested_action="extract_foundup",
            foundup_id="gotjunk_001",
            payload={"module_path": "modules/foundups/nonexistent_xyz"},
        )
        r = self._resolve(job)
        assert r.failed is True
        assert r.fail_token == e.FAIL_TOKEN_MANIFEST_MISSING
        # Rejected payload value is observable.
        assert r.ignored == "modules/foundups/nonexistent_xyz"
        assert r.effective is None

    # ---- Addendum C #2: source_module alias path ------------------------

    def test_source_module_alias_validates_same_as_module_path(self) -> None:
        """``payload.source_module`` (the alias) goes through the same
        validated resolution as ``payload.module_path``."""
        job = create_job(
            tenant_id="012",
            requested_action="extract_foundup",
            foundup_id="gotjunk_001",
            payload={"source_module": "modules/foundups/gotjunk"},
        )
        r = self._resolve(job)
        assert r.failed is False
        assert r.effective == "modules/foundups/gotjunk"
        assert r.ignored == "modules/foundups/gotjunk"

    def test_source_module_alias_with_wrong_path_rejected(self) -> None:
        """The alias receives the same fail-closed treatment as the
        primary key."""
        e = self._resolver_module()
        job = create_job(
            tenant_id="012",
            requested_action="extract_foundup",
            foundup_id="gotjunk_001",
            payload={"source_module": "modules/foundups/nope_alias"},
        )
        r = self._resolve(job)
        assert r.failed is True
        assert r.fail_token == e.FAIL_TOKEN_MANIFEST_MISSING

    # ---- Addendum C #4: suffix-only / basename rejected -----------------

    def test_suffix_only_path_rejected(self) -> None:
        """A bare basename (``gotjunk``) that matches the LAST segment of a
        real manifest's module_path must NOT validate. This pins #773's
        exact-match semantics at the consumer boundary."""
        e = self._resolver_module()
        job = create_job(
            tenant_id="012",
            requested_action="extract_foundup",
            foundup_id="gotjunk_001",
            payload={"module_path": "gotjunk"},
        )
        r = self._resolve(job)
        assert r.failed is True
        assert r.fail_token == e.FAIL_TOKEN_SYNTACTIC_REJECT  # not under modules/

    def test_partial_path_rejected(self) -> None:
        """A path that is partial (missing the leading ``modules/``) is
        rejected at the syntactic-hardening step, never reaching the
        manifest."""
        e = self._resolver_module()
        job = create_job(
            tenant_id="012",
            requested_action="extract_foundup",
            foundup_id="gotjunk_001",
            payload={"module_path": "foundups/gotjunk"},
        )
        r = self._resolve(job)
        assert r.failed is True
        assert r.fail_token == e.FAIL_TOKEN_SYNTACTIC_REJECT

    # ---- Addendum C #5: backslashes rejected pre-manifest ---------------

    def test_backslash_payload_rejected_pre_manifest(self) -> None:
        """Backslashes are rejected BEFORE any manifest contact. On
        Windows, the validator would itself convert them; the consumer
        boundary refuses them so the token stays ``syntactic_reject``."""
        e = self._resolver_module()
        job = create_job(
            tenant_id="012",
            requested_action="extract_foundup",
            foundup_id="gotjunk_001",
            payload={"module_path": r"modules\foundups\gotjunk"},
        )
        r = self._resolve(job)
        assert r.failed is True
        assert r.fail_token == e.FAIL_TOKEN_SYNTACTIC_REJECT
        assert "backslash" in r.fail_human.lower()

    # ---- Addendum C #6: absolute / traversal rejected pre-manifest ------

    def test_absolute_path_rejected_pre_manifest(self) -> None:
        e = self._resolver_module()
        job = create_job(
            tenant_id="012",
            requested_action="extract_foundup",
            foundup_id="gotjunk_001",
            payload={"module_path": "/modules/foundups/gotjunk"},
        )
        r = self._resolve(job)
        assert r.failed is True
        assert r.fail_token == e.FAIL_TOKEN_SYNTACTIC_REJECT

    def test_absolute_drive_path_rejected_pre_manifest(self) -> None:
        e = self._resolver_module()
        job = create_job(
            tenant_id="012",
            requested_action="extract_foundup",
            foundup_id="gotjunk_001",
            payload={"module_path": "O:/Foundups-Agent/modules/foundups/gotjunk"},
        )
        r = self._resolve(job)
        assert r.failed is True
        assert r.fail_token == e.FAIL_TOKEN_SYNTACTIC_REJECT

    def test_traversal_path_rejected_pre_manifest(self) -> None:
        e = self._resolver_module()
        job = create_job(
            tenant_id="012",
            requested_action="extract_foundup",
            foundup_id="gotjunk_001",
            payload={"module_path": "../modules/foundups/gotjunk"},
        )
        r = self._resolve(job)
        assert r.failed is True
        assert r.fail_token == e.FAIL_TOKEN_SYNTACTIC_REJECT

    def test_internal_traversal_rejected(self) -> None:
        e = self._resolver_module()
        job = create_job(
            tenant_id="012",
            requested_action="extract_foundup",
            foundup_id="gotjunk_001",
            payload={"module_path": "modules/foundups/../foundups/gotjunk"},
        )
        r = self._resolve(job)
        assert r.failed is True
        assert r.fail_token == e.FAIL_TOKEN_SYNTACTIC_REJECT

    # ---- Addendum C #7: omitted payload derives from manifest -----------

    def test_payload_omitted_derives_from_validated_manifest(self) -> None:
        """No payload candidate; the executor must NOT infer from
        foundup_id-as-path. It must run a bounded foundup_id scan and
        derive the effective path from the validated manifest."""
        job = create_job(
            tenant_id="012",
            requested_action="extract_foundup",
            foundup_id="gotjunk_001",
            payload={},
        )
        r = self._resolve(job)
        assert r.failed is False
        assert r.effective == "modules/foundups/gotjunk"
        # No candidate was supplied; observable-ignore is None.
        assert r.ignored is None

    def test_payload_omitted_unknown_foundup_id_fails_missing(self) -> None:
        """Bounded scan misses for an unknown foundup_id -> manifest_missing."""
        e = self._resolver_module()
        job = create_job(
            tenant_id="012",
            requested_action="extract_foundup",
            foundup_id="totally_unknown_foundup_xyz",
            payload={},
        )
        r = self._resolve(job)
        assert r.failed is True
        assert r.fail_token == e.FAIL_TOKEN_MANIFEST_MISSING

    # ---- Addendum C #8: rejected payload value visible in evidence ------

    def test_rejected_payload_value_appears_in_evidence(self) -> None:
        """End-to-end through ``execute_foundup_job``: when the resolver
        fails, the job's evidence_refs contains the rejected payload
        value AND the greppable fail token (mirrors #777 observable-
        ignore)."""
        job = create_job(
            tenant_id="012",
            requested_action="extract_foundup",
            foundup_id="gotjunk_001",
            payload={"module_path": "modules/foundups/nope_evidence"},
        )
        result = execute_foundup_job(job=job)
        assert result.job.status == JobStatus.FAILED
        assert result.job.status_reason_code == StatusReasonCode.FAIL_VALIDATION_ERROR
        refs = result.job.evidence_refs or []
        assert any("rejected_payload_value:modules/foundups/nope_evidence" in r for r in refs)
        assert any("fail_token:manifest_missing" in r for r in refs)

    # ---- Addendum D #1: cross-FoundUp substitution rejected -------------

    def test_cross_foundup_substitution_rejected(self) -> None:
        """job.foundup_id = A, payload.module_path = B's REAL, validator-
        passing module path. The manifest must bind to A; resolving B's
        manifest and finding A != B is the load-bearing defense."""
        e = self._resolver_module()
        job = create_job(
            tenant_id="012",
            requested_action="extract_foundup",
            foundup_id="gotjunk_001",  # A
            payload={"module_path": "modules/foundups/kosei"},  # B's real path
        )
        r = self._resolve(job)
        assert r.failed is True
        assert r.fail_token == e.FAIL_TOKEN_CROSS_FOUNDUP_MISMATCH
        # The mismatch is observable: both ids appear in the human message.
        assert "gotjunk_001" in r.fail_human
        assert "kosei" in r.fail_human

    def test_cross_foundup_substitution_via_alias_rejected(self) -> None:
        """The alias key carries the same protection."""
        e = self._resolver_module()
        job = create_job(
            tenant_id="012",
            requested_action="extract_foundup",
            foundup_id="gotjunk_001",
            payload={"source_module": "modules/foundups/kosei"},
        )
        r = self._resolve(job)
        assert r.failed is True
        assert r.fail_token == e.FAIL_TOKEN_CROSS_FOUNDUP_MISMATCH

    # ---- Addendum D #3: case-variant rejected ---------------------------

    def test_case_variant_payload_rejected(self) -> None:
        """Windows host reality: a case-variant payload (same on disk
        case-insensitively, different string) MUST be rejected. The
        resolver's exact-string comparison against the canonical
        manifest module_path catches it."""
        e = self._resolver_module()
        job = create_job(
            tenant_id="012",
            requested_action="extract_foundup",
            foundup_id="gotjunk_001",
            payload={"module_path": "modules/Foundups/gotjunk"},  # caps inside
        )
        r = self._resolve(job)
        assert r.failed is True
        # The token may be syntactic_reject OR manifest_mismatch depending on
        # which check catches first; both are valid "reject" outcomes per
        # Addendum D #3. Pin that the FAILURE happened and the value is
        # observable.
        assert r.fail_token in (
            e.FAIL_TOKEN_SYNTACTIC_REJECT, e.FAIL_TOKEN_MANIFEST_MISMATCH,
        )
        assert r.ignored == "modules/Foundups/gotjunk"

    def test_uppercase_modules_prefix_rejected(self) -> None:
        """Uppercase ``Modules/`` prefix fails the ``startswith('modules/')``
        guard at the syntactic-harden step."""
        e = self._resolver_module()
        job = create_job(
            tenant_id="012",
            requested_action="extract_foundup",
            foundup_id="gotjunk_001",
            payload={"module_path": "Modules/foundups/gotjunk"},
        )
        r = self._resolve(job)
        assert r.failed is True
        assert r.fail_token == e.FAIL_TOKEN_SYNTACTIC_REJECT

    # ---- Addendum D #4: empty-string semantics --------------------------

    def test_empty_string_payload_treated_as_absent(self) -> None:
        """``payload.module_path = ''`` is ABSENT (falsy semantics pinned).
        Derivation falls through to the bounded foundup_id scan."""
        job = create_job(
            tenant_id="012",
            requested_action="extract_foundup",
            foundup_id="gotjunk_001",
            payload={"module_path": ""},
        )
        r = self._resolve(job)
        assert r.failed is False
        assert r.effective == "modules/foundups/gotjunk"
        # Empty string is treated as absent, so ignored stays None.
        assert r.ignored is None

    def test_empty_string_alias_also_treated_as_absent(self) -> None:
        """The same falsy-semantics rule applies to ``source_module``."""
        job = create_job(
            tenant_id="012",
            requested_action="extract_foundup",
            foundup_id="gotjunk_001",
            payload={"source_module": ""},
        )
        r = self._resolve(job)
        assert r.failed is False
        assert r.effective == "modules/foundups/gotjunk"
        assert r.ignored is None

    # ---- Greppable fail-token taxonomy ----------------------------------

    def test_all_fail_tokens_present_in_taxonomy(self) -> None:
        """Addendum D #5: the closed token set is exactly the documented
        four. No other tokens may leak into ``reason_human`` from this
        resolver."""
        e = self._resolver_module()
        assert e.ALL_FAIL_TOKENS == frozenset({
            "syntactic_reject",
            "manifest_mismatch",
            "manifest_missing",
            "cross_foundup_mismatch",
        })

    # ---- End-to-end through execute_foundup_job -------------------------

    def test_execute_foundup_job_fails_closed_on_invalid_payload(self) -> None:
        """End-to-end: invalid payload reaches FAILED before HermesFoundUpBuilder
        is instantiated (subprocess sink is unreached)."""
        with patch(
            "modules.foundups.agent.src.hermes_foundup_job_executor"
            ".HermesFoundUpBuilder" if False else
            "modules.foundups.agent.src.hermes_adapter.HermesFoundUpBuilder"
        ) as mock_builder_cls:
            job = create_job(
                tenant_id="012",
                requested_action="extract_foundup",
                foundup_id="gotjunk_001",
                payload={"module_path": "modules/foundups/will_not_resolve"},
            )
            result = execute_foundup_job(job=job)
            # FAILED before any builder construction.
            mock_builder_cls.assert_not_called()
            assert result.job.status == JobStatus.FAILED
            assert result.job.status_reason_code == StatusReasonCode.FAIL_VALIDATION_ERROR

    def test_execute_foundup_job_fails_closed_on_cross_foundup_substitution(self) -> None:
        """End-to-end cross-FoundUp substitution attempt is rejected and
        the subprocess sink is unreached."""
        with patch(
            "modules.foundups.agent.src.hermes_adapter.HermesFoundUpBuilder"
        ) as mock_builder_cls:
            job = create_job(
                tenant_id="012",
                requested_action="extract_foundup",
                foundup_id="gotjunk_001",
                payload={"module_path": "modules/foundups/kosei"},
            )
            result = execute_foundup_job(job=job)
            mock_builder_cls.assert_not_called()
            assert result.job.status == JobStatus.FAILED
            assert result.job.status_reason_code == StatusReasonCode.FAIL_VALIDATION_ERROR
            refs = result.job.evidence_refs or []
            assert any("fail_token:cross_foundup_mismatch" in r for r in refs)
