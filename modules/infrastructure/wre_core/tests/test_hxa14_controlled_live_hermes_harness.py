#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HXA14 Proof Test: Controlled Live Hermes Delegation Harness

Proves that controlled live delegation can be explicitly invoked in a test
harness without enabling unsafe production behavior.

Harness Semantics:
  1. Harness is disabled by default
  2. Harness requires explicit opt-in (controlled_harness=True)
  3. Harness rejects repo creation
  4. Harness rejects production source writes
  5. Harness writes only evidence artifacts
  6. Controlled delegate is invoked only inside test harness
  7. Truth fields distinguish controlled delegate from live external delegate

WSP 97 Truth Boundaries:
  - controlled_delegate_invoked=True (harness was used)
  - live_external_delegate_called=False (no real external delegate)
  - real_execution_performed=False (no production execution)
  - repo_created=False (no GitHub operations)
  - production_source_modified=False
  - external_federation_ready=False
  - production_ready=False

Slice: HXA14_CONTROLLED_LIVE_HERMES_DELEGATION_HARNESS_PHASE1
Worker: W1
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from unittest.mock import MagicMock

# FoundUpJob contract
from modules.communication.moltbot_bridge.src.foundup_job_contract import (
    FoundUpJob,
)

# OpenClaw Orchestrator
from modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator import (
    dispatch_foundup,
    get_job_queue,
    clear_job_queue,
)

# Hermes Executor
from modules.infrastructure.wre_core.src.hermes_job_executor import (
    HermesJobExecutor,
    HermesExecutionStatus,
    is_hermes_delegation_enabled,
)


# ---------------------------------------------------------------------------
# Test Constants
# ---------------------------------------------------------------------------

VOTEBALLOTS_FOUNDUP_ID = "voteballots"
GOTJUNK_FOUNDUP_ID = "gotjunk_001"


# ---------------------------------------------------------------------------
# Mock Intent
# ---------------------------------------------------------------------------


class MockIntent:
    """Mock OpenClawIntent for testing dispatch_foundup."""

    def __init__(self, raw_message: str, sender: str = "012"):
        self.raw_message = raw_message
        self.sender = sender
        self.session_key = "hxa14_harness_test"
        self.channel = "test_channel"


# ---------------------------------------------------------------------------
# Test: Harness Default State
# ---------------------------------------------------------------------------


class TestHarnessDisabledByDefault:
    """Verify controlled harness is disabled by default."""

    def test_executor_harness_disabled_by_default(self):
        """HermesJobExecutor has controlled_harness=False by default."""
        executor = HermesJobExecutor()
        assert executor.controlled_harness is False

    def test_executor_dry_run_true_by_default(self):
        """HermesJobExecutor has dry_run=True by default."""
        executor = HermesJobExecutor()
        assert executor.dry_run is True

    def test_default_executor_returns_simulated(self):
        """Default executor returns SIMULATED, not CONTROLLED_HARNESS_EXECUTED."""
        job = FoundUpJob(
            job_id="hxa14_default_test_001",
            tenant_id="012",
            foundup_id=VOTEBALLOTS_FOUNDUP_ID,
            requested_action="build_foundup",
        )

        executor = HermesJobExecutor()  # defaults: dry_run=True, controlled_harness=False
        result = executor.execute(job)

        assert result.status == HermesExecutionStatus.SIMULATED
        assert result.controlled_delegate_invoked is False


# ---------------------------------------------------------------------------
# Test: Harness Explicit Opt-In
# ---------------------------------------------------------------------------


class TestHarnessRequiresExplicitOptIn:
    """Verify harness requires explicit controlled_harness=True."""

    def setup_method(self):
        """Setup temp evidence directory."""
        self.evidence_root = tempfile.mkdtemp(prefix="hxa14_optin_")

    def teardown_method(self):
        """Cleanup temp directory."""
        if hasattr(self, "evidence_root") and os.path.exists(self.evidence_root):
            shutil.rmtree(self.evidence_root, ignore_errors=True)

    def test_controlled_harness_false_returns_simulated(self):
        """controlled_harness=False returns SIMULATED."""
        job = FoundUpJob(
            job_id="hxa14_optin_false_001",
            tenant_id="012",
            foundup_id=VOTEBALLOTS_FOUNDUP_ID,
            requested_action="build_foundup",
        )

        executor = HermesJobExecutor(
            dry_run=True,
            controlled_harness=False,
            workspace_root=self.evidence_root,
        )
        result = executor.execute(job)

        assert result.status == HermesExecutionStatus.SIMULATED
        assert result.controlled_delegate_invoked is False

    def test_controlled_harness_true_returns_harness_executed(self):
        """controlled_harness=True returns CONTROLLED_HARNESS_EXECUTED."""
        job = FoundUpJob(
            job_id="hxa14_optin_true_001",
            tenant_id="012",
            foundup_id=VOTEBALLOTS_FOUNDUP_ID,
            requested_action="build_foundup",
        )

        executor = HermesJobExecutor(
            dry_run=False,  # Even with dry_run=False, harness is safe
            controlled_harness=True,
            workspace_root=self.evidence_root,
        )
        result = executor.execute(job)

        assert result.status == HermesExecutionStatus.CONTROLLED_HARNESS_EXECUTED
        assert result.controlled_delegate_invoked is True

    def test_harness_overrides_feature_flag(self):
        """Controlled harness works regardless of HERMES_DELEGATE_ENABLED."""
        job = FoundUpJob(
            job_id="hxa14_flag_override_001",
            tenant_id="012",
            foundup_id=VOTEBALLOTS_FOUNDUP_ID,
            requested_action="build_foundup",
        )

        # Verify feature flag is disabled
        assert is_hermes_delegation_enabled() is False

        # Harness should still work
        executor = HermesJobExecutor(
            controlled_harness=True,
            workspace_root=self.evidence_root,
        )
        result = executor.execute(job)

        assert result.status == HermesExecutionStatus.CONTROLLED_HARNESS_EXECUTED


# ---------------------------------------------------------------------------
# Test: Harness Safety Boundaries
# ---------------------------------------------------------------------------


class TestHarnessSafetyBoundaries:
    """Verify harness maintains all safety boundaries."""

    def setup_method(self):
        """Setup temp evidence directory."""
        self.evidence_root = tempfile.mkdtemp(prefix="hxa14_safety_")

    def teardown_method(self):
        """Cleanup temp directory."""
        if hasattr(self, "evidence_root") and os.path.exists(self.evidence_root):
            shutil.rmtree(self.evidence_root, ignore_errors=True)

    def test_harness_rejects_repo_creation(self):
        """Harness sets repo_created=False (no GitHub API calls)."""
        job = FoundUpJob(
            job_id="hxa14_repo_reject_001",
            tenant_id="012",
            foundup_id=VOTEBALLOTS_FOUNDUP_ID,
            requested_action="build_foundup",
        )

        executor = HermesJobExecutor(
            controlled_harness=True,
            workspace_root=self.evidence_root,
        )
        result = executor.execute(job)

        assert result.repo_created is False

    def test_harness_rejects_production_source_writes(self):
        """Harness sets production_source_modified=False."""
        job = FoundUpJob(
            job_id="hxa14_prod_reject_001",
            tenant_id="012",
            foundup_id=VOTEBALLOTS_FOUNDUP_ID,
            requested_action="build_foundup",
        )

        executor = HermesJobExecutor(
            controlled_harness=True,
            workspace_root=self.evidence_root,
        )
        result = executor.execute(job)

        assert result.production_source_modified is False

    def test_harness_writes_evidence_artifacts(self):
        """Harness writes evidence artifacts to workspace."""
        job = FoundUpJob(
            job_id="hxa14_evidence_001",
            tenant_id="012",
            foundup_id=VOTEBALLOTS_FOUNDUP_ID,
            requested_action="build_foundup",
        )

        executor = HermesJobExecutor(
            controlled_harness=True,
            workspace_root=self.evidence_root,
        )
        result = executor.execute(job)

        # Evidence path should be set
        assert result.evidence_path is not None
        assert os.path.isdir(result.evidence_path)

        # Standard evidence files should exist
        assert os.path.isfile(os.path.join(result.evidence_path, "metadata.json"))
        assert os.path.isfile(os.path.join(result.evidence_path, "checkpoint.json"))

    def test_harness_does_not_call_live_external_delegate(self):
        """Harness sets live_external_delegate_called=False."""
        job = FoundUpJob(
            job_id="hxa14_live_reject_001",
            tenant_id="012",
            foundup_id=VOTEBALLOTS_FOUNDUP_ID,
            requested_action="build_foundup",
        )

        executor = HermesJobExecutor(
            controlled_harness=True,
            workspace_root=self.evidence_root,
        )
        result = executor.execute(job)

        assert result.live_external_delegate_called is False

    def test_harness_not_production_ready(self):
        """Harness sets production_ready=False."""
        job = FoundUpJob(
            job_id="hxa14_prod_ready_001",
            tenant_id="012",
            foundup_id=VOTEBALLOTS_FOUNDUP_ID,
            requested_action="build_foundup",
        )

        executor = HermesJobExecutor(
            controlled_harness=True,
            workspace_root=self.evidence_root,
        )
        result = executor.execute(job)

        assert result.production_ready is False

    def test_harness_not_external_federation_ready(self):
        """Harness sets external_federation_ready=False."""
        job = FoundUpJob(
            job_id="hxa14_fed_ready_001",
            tenant_id="012",
            foundup_id=VOTEBALLOTS_FOUNDUP_ID,
            requested_action="build_foundup",
        )

        executor = HermesJobExecutor(
            controlled_harness=True,
            workspace_root=self.evidence_root,
        )
        result = executor.execute(job)

        assert result.external_federation_ready is False


# ---------------------------------------------------------------------------
# Test: Controlled Delegate Behavior
# ---------------------------------------------------------------------------


class TestControlledDelegateBehavior:
    """Verify controlled delegate is invoked correctly."""

    def setup_method(self):
        """Setup temp evidence directory."""
        self.evidence_root = tempfile.mkdtemp(prefix="hxa14_delegate_")

    def teardown_method(self):
        """Cleanup temp directory."""
        if hasattr(self, "evidence_root") and os.path.exists(self.evidence_root):
            shutil.rmtree(self.evidence_root, ignore_errors=True)

    def test_controlled_delegate_invoked_in_harness(self):
        """Controlled delegate is invoked when harness is enabled."""
        job = FoundUpJob(
            job_id="hxa14_delegate_invoke_001",
            tenant_id="012",
            foundup_id=VOTEBALLOTS_FOUNDUP_ID,
            requested_action="build_foundup",
        )

        executor = HermesJobExecutor(
            controlled_harness=True,
            workspace_root=self.evidence_root,
        )
        result = executor.execute(job)

        assert result.controlled_delegate_invoked is True
        assert result.delegate_response is not None
        assert result.delegate_response["controlled_harness"] is True

    def test_controlled_delegate_returns_foundup_id(self):
        """Controlled delegate response includes foundup_id."""
        job = FoundUpJob(
            job_id="hxa14_delegate_id_001",
            tenant_id="012",
            foundup_id=VOTEBALLOTS_FOUNDUP_ID,
            requested_action="build_foundup",
        )

        executor = HermesJobExecutor(
            controlled_harness=True,
            workspace_root=self.evidence_root,
        )
        result = executor.execute(job)

        assert result.delegate_response["foundup_id"] == VOTEBALLOTS_FOUNDUP_ID

    def test_controlled_delegate_not_invoked_without_harness(self):
        """Controlled delegate is NOT invoked when harness is disabled."""
        job = FoundUpJob(
            job_id="hxa14_delegate_no_invoke_001",
            tenant_id="012",
            foundup_id=VOTEBALLOTS_FOUNDUP_ID,
            requested_action="build_foundup",
        )

        executor = HermesJobExecutor(
            controlled_harness=False,
            workspace_root=self.evidence_root,
        )
        result = executor.execute(job)

        assert result.controlled_delegate_invoked is False
        assert result.delegate_response is None


# ---------------------------------------------------------------------------
# Test: VoteBallots Harness Execution
# ---------------------------------------------------------------------------


class TestVoteBallotsThroughHarness:
    """Verify VoteBallots passes through harness safely."""

    def setup_method(self):
        """Clear queue and setup temp evidence directory."""
        clear_job_queue()
        self.evidence_root = tempfile.mkdtemp(prefix="hxa14_voteballots_")

    def teardown_method(self):
        """Clear queue and cleanup."""
        clear_job_queue()
        if hasattr(self, "evidence_root") and os.path.exists(self.evidence_root):
            shutil.rmtree(self.evidence_root, ignore_errors=True)

    def test_voteballots_harness_execution_safe(self):
        """VoteBallots can execute through harness safely."""
        job = FoundUpJob(
            job_id="hxa14_voteballots_safe_001",
            tenant_id="012",
            foundup_id=VOTEBALLOTS_FOUNDUP_ID,
            requested_action="build_foundup",
        )

        executor = HermesJobExecutor(
            controlled_harness=True,
            workspace_root=self.evidence_root,
        )
        result = executor.execute(job)

        # Verify harness execution
        assert result.status == HermesExecutionStatus.CONTROLLED_HARNESS_EXECUTED
        assert result.controlled_delegate_invoked is True

        # Verify all safety boundaries
        assert result.real_execution_performed is False
        assert result.live_external_delegate_called is False
        assert result.repo_created is False
        assert result.production_source_modified is False
        assert result.production_ready is False

        # Verify evidence written
        assert result.evidence_path is not None


# ---------------------------------------------------------------------------
# Test: GotJunk Harness Execution
# ---------------------------------------------------------------------------


class TestGotJunkThroughHarness:
    """Verify GotJunk passes through harness safely."""

    def setup_method(self):
        """Setup temp evidence directory."""
        self.evidence_root = tempfile.mkdtemp(prefix="hxa14_gotjunk_")

    def teardown_method(self):
        """Cleanup temp directory."""
        if hasattr(self, "evidence_root") and os.path.exists(self.evidence_root):
            shutil.rmtree(self.evidence_root, ignore_errors=True)

    def test_gotjunk_harness_execution_safe(self):
        """GotJunk can execute through harness safely."""
        job = FoundUpJob(
            job_id="hxa14_gotjunk_safe_001",
            tenant_id="012",
            foundup_id=GOTJUNK_FOUNDUP_ID,
            requested_action="build_foundup",
        )

        executor = HermesJobExecutor(
            controlled_harness=True,
            workspace_root=self.evidence_root,
        )
        result = executor.execute(job)

        # Verify harness execution
        assert result.status == HermesExecutionStatus.CONTROLLED_HARNESS_EXECUTED
        assert result.controlled_delegate_invoked is True

        # Verify GotJunk identity in response
        assert result.delegate_response["foundup_id"] == GOTJUNK_FOUNDUP_ID

        # Verify all safety boundaries
        assert result.real_execution_performed is False
        assert result.live_external_delegate_called is False
        assert result.repo_created is False
        assert result.production_source_modified is False


# ---------------------------------------------------------------------------
# Test: No GitHub API Calls
# ---------------------------------------------------------------------------


class TestNoGitHubAPICalls:
    """Verify no GitHub API calls are made."""

    def setup_method(self):
        """Setup temp evidence directory."""
        self.evidence_root = tempfile.mkdtemp(prefix="hxa14_github_")

    def teardown_method(self):
        """Cleanup temp directory."""
        if hasattr(self, "evidence_root") and os.path.exists(self.evidence_root):
            shutil.rmtree(self.evidence_root, ignore_errors=True)

    def test_harness_delegate_response_confirms_no_repo(self):
        """Delegate response confirms no repo created."""
        job = FoundUpJob(
            job_id="hxa14_no_github_001",
            tenant_id="012",
            foundup_id=VOTEBALLOTS_FOUNDUP_ID,
            requested_action="build_foundup",
        )

        executor = HermesJobExecutor(
            controlled_harness=True,
            workspace_root=self.evidence_root,
        )
        result = executor.execute(job)

        assert result.delegate_response["repo_created"] is False
        assert result.delegate_response["live_delegate_called"] is False


# ---------------------------------------------------------------------------
# Test: No Production Source Modification
# ---------------------------------------------------------------------------


class TestNoProductionSourceModification:
    """Verify no production source files are modified."""

    def setup_method(self):
        """Setup temp evidence directory."""
        self.evidence_root = tempfile.mkdtemp(prefix="hxa14_nosrc_")

    def teardown_method(self):
        """Cleanup temp directory."""
        if hasattr(self, "evidence_root") and os.path.exists(self.evidence_root):
            shutil.rmtree(self.evidence_root, ignore_errors=True)

    def test_voteballots_production_source_unchanged(self):
        """VoteBallots production source is not modified."""
        job = FoundUpJob(
            job_id="hxa14_vb_nosrc_001",
            tenant_id="012",
            foundup_id=VOTEBALLOTS_FOUNDUP_ID,
            requested_action="build_foundup",
        )

        executor = HermesJobExecutor(
            controlled_harness=True,
            workspace_root=self.evidence_root,
        )
        result = executor.execute(job)

        # Verify production_source_modified is False
        assert result.production_source_modified is False

        # files_changed should only be in evidence directory
        for file_path in result.files_changed:
            assert ".hermes_evidence" in file_path or "_poc" in file_path

    def test_gotjunk_production_source_unchanged(self):
        """GotJunk production source is not modified."""
        job = FoundUpJob(
            job_id="hxa14_gj_nosrc_001",
            tenant_id="012",
            foundup_id=GOTJUNK_FOUNDUP_ID,
            requested_action="build_foundup",
        )

        executor = HermesJobExecutor(
            controlled_harness=True,
            workspace_root=self.evidence_root,
        )
        result = executor.execute(job)

        assert result.production_source_modified is False


# ---------------------------------------------------------------------------
# Test: WSP 97 Truth Table Enforcement
# ---------------------------------------------------------------------------


class TestWSP97TruthTableEnforcement:
    """Verify complete WSP 97 truth table is enforced."""

    def setup_method(self):
        """Setup temp evidence directory."""
        self.evidence_root = tempfile.mkdtemp(prefix="hxa14_wsp97_")

    def teardown_method(self):
        """Cleanup temp directory."""
        if hasattr(self, "evidence_root") and os.path.exists(self.evidence_root):
            shutil.rmtree(self.evidence_root, ignore_errors=True)

    def test_complete_wsp97_truth_table(self):
        """
        Complete WSP 97 truth table for controlled harness.

        Truth Table:
          | Field                         | Expected Value |
          |-------------------------------|----------------|
          | status                        | CONTROLLED_HARNESS_EXECUTED |
          | controlled_delegate_invoked   | True           |
          | live_external_delegate_called | False          |
          | real_execution_performed      | False          |
          | repo_created                  | False          |
          | production_source_modified    | False          |
          | verification_complete         | False          |
          | cabr_ready                    | False          |
          | payout_ready                  | False          |
          | external_federation_ready     | False          |
          | production_ready              | False          |
        """
        job = FoundUpJob(
            job_id="hxa14_wsp97_complete_001",
            tenant_id="012",
            foundup_id=VOTEBALLOTS_FOUNDUP_ID,
            requested_action="build_foundup",
        )

        executor = HermesJobExecutor(
            controlled_harness=True,
            workspace_root=self.evidence_root,
        )
        result = executor.execute(job)

        # Complete WSP 97 Truth Table Assertions
        assert result.status == HermesExecutionStatus.CONTROLLED_HARNESS_EXECUTED
        assert result.controlled_delegate_invoked is True
        assert result.live_external_delegate_called is False
        assert result.real_execution_performed is False
        assert result.repo_created is False
        assert result.production_source_modified is False
        assert result.verification_complete is False
        assert result.cabr_ready is False
        assert result.payout_ready is False
        assert result.external_federation_ready is False
        assert result.production_ready is False

    def test_truth_fields_in_to_dict(self):
        """All truth fields are included in to_dict() serialization."""
        job = FoundUpJob(
            job_id="hxa14_todict_001",
            tenant_id="012",
            foundup_id=VOTEBALLOTS_FOUNDUP_ID,
            requested_action="build_foundup",
        )

        executor = HermesJobExecutor(
            controlled_harness=True,
            workspace_root=self.evidence_root,
        )
        result = executor.execute(job)
        result_dict = result.to_dict()

        # Verify all HXA14 truth fields are in serialized output
        assert "controlled_delegate_invoked" in result_dict
        assert "live_external_delegate_called" in result_dict
        assert "repo_created" in result_dict
        assert "production_source_modified" in result_dict
        assert "external_federation_ready" in result_dict
        assert "production_ready" in result_dict
