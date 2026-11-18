#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HXA4 Proof Test: Real Hermes Executor Object in Safe Dry-Run Mode

Proves the VoteBallots path reaches the REAL HermesJobExecutor object
(not mocked) while remaining in safe dry-run mode.

Unlike HXA3 tests which mock execute_foundup_job, this test:
  - Does NOT mock the Hermes executor
  - Exercises the REAL HermesJobExecutor class
  - Verifies real_execution_performed=False
  - Verifies checkpoint_state=SIMULATED
  - Verifies evidence files are written
  - Ensures HERMES_DELEGATE_ENABLED=0 (no live delegate_task)

WSP 97 Truth Boundaries (STRICT):
  - HERMES_DELEGATE_ENABLED=0 (must remain disabled)
  - dry_run=True throughout
  - real_execution_performed=False
  - No live delegate_task calls
  - No GitHub repo creation
  - No payout/CABR production claims

Slice: HXA4_REAL_HERMES_OBJECT_SAFE_DRYRUN_PHASE1
Worker: W1
"""

from __future__ import annotations

import os
import json
import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

# OpenClaw Orchestrator
from modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator import (
    dispatch_foundup,
    get_job_queue,
    clear_job_queue,
)

# WRE Consumer (real, not mocked)
from modules.infrastructure.wre_core.src.foundup_job_consumer import (
    FoundUpJobConsumer,
)

# Hermes Executor (real, not mocked)
from modules.infrastructure.wre_core.src.hermes_job_executor import (
    HermesJobExecutor,
    HermesExecutionStatus,
    is_hermes_delegation_enabled,
    _HERMES_DELEGATE_ENABLED_KEY,
)

# HXA_POLICYFLAGS_WRITEBACK_REMEDIATION_PHASE1 (#746): real capability token
# issuer (server-authored verdict comes from the executor's runtime write-back).
from modules.infrastructure.wre_core.src.capability_token_validator import (
    LocalCapabilityTokenIssuer,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VOTEBALLOTS_FOUNDUP_ID = "voteballots"
VOTEBALLOTS_BUILD_MESSAGE = "start build voteballots --dry-run"


# ---------------------------------------------------------------------------
# Mock Intent (duck-typed to match OpenClawIntent)
# ---------------------------------------------------------------------------

class MockIntent:
    """Mock OpenClawIntent for testing dispatch_foundup."""

    def __init__(self, raw_message: str, sender: str = "012"):
        self.raw_message = raw_message
        self.sender = sender
        self.session_key = "hxa4_real_hermes_test"
        self.channel = "test_channel"
        self.is_authorized_commander = True


def set_d3_capability_token_gates(job):
    """
    Set D3 capability token gates on a job for testing.

    HXA28: build_foundup and extract_foundup are now D3 actions that require
    capability tokens. For tests that need to reach SIMULATED status (not
    BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD), the job must carry a valid token AND
    the security gate.

    HXA_POLICYFLAGS_WRITEBACK_REMEDIATION_PHASE1 (#746): capability_token_*
    flags are SERVER-AUTHORED by the executor's runtime write-back, so we attach
    a REAL valid D3 token to the job payload (forging the flags no longer works).
    The executor's write-back promotes the capability flags from the verdict
    before the guard reads them. security_gate_* is set directly (server-authored;
    no security-gate evaluator in this executor).
    """
    # Attach a REAL valid D3 capability token into the job payload.
    if not isinstance(job.payload, dict):
        job.payload = {}
    job.payload["capability_token"] = LocalCapabilityTokenIssuer().issue_token(
        subject="agent_hxa4",
        audience="wre-local",
        scopes=["d3:sandbox"],  # authorizes D3 (build_foundup / extract_foundup)
        allowed_actions=["build_foundup", "extract_foundup"],
        allowed_paths=["modules/foundups"],
        # dry_run_only=False so the token validates whether the executor runs
        # with dry_run True or False; the guard/harness still bounds execution.
        dry_run_only=False,
    )
    # Security gate (also required for D3) - server-authored direct assignment.
    job.policy_flags.security_gate_checked = True
    job.policy_flags.security_gate_passed = True


# ---------------------------------------------------------------------------
# Test: Environment Safety Gate
# ---------------------------------------------------------------------------

class TestHXA4EnvironmentSafetyGate:
    """
    Verify environment is safe for HXA4 real Hermes object tests.

    These gates MUST pass before any real executor tests run.
    """

    def test_hermes_delegate_disabled_by_default(self):
        """HERMES_DELEGATE_ENABLED must be 0 or unset."""
        # Ensure env var is not set or is explicitly 0
        value = os.environ.get(_HERMES_DELEGATE_ENABLED_KEY, "0")
        assert value in ("0", "", None, "false", "no"), (
            f"SAFETY GATE FAILED: {_HERMES_DELEGATE_ENABLED_KEY}={value}. "
            "Must be 0 for safe dry-run tests."
        )

    def test_is_hermes_delegation_enabled_returns_false(self):
        """is_hermes_delegation_enabled() must return False."""
        assert is_hermes_delegation_enabled() is False, (
            "SAFETY GATE FAILED: Hermes delegation is enabled. "
            "Cannot run real object tests with live delegation."
        )


# ---------------------------------------------------------------------------
# Test: Real HermesJobExecutor Object Instantiation
# ---------------------------------------------------------------------------

class TestRealHermesJobExecutorInstantiation:
    """Verify real HermesJobExecutor can be instantiated safely."""

    def test_executor_instantiates_with_dry_run_true(self):
        """HermesJobExecutor instantiates with dry_run=True."""
        executor = HermesJobExecutor(dry_run=True)

        assert executor.dry_run is True
        assert executor._delegate_task_fn is None
        assert executor._import_attempted is False

    def test_executor_workspace_root_detection(self):
        """Executor detects workspace root."""
        executor = HermesJobExecutor(dry_run=True)

        assert executor.workspace_root is not None
        assert len(executor.workspace_root) > 0


# ---------------------------------------------------------------------------
# Test: VoteBallots Path Reaches Real Executor
# ---------------------------------------------------------------------------

class TestVoteBallotsDryRunReachesRealExecutor:
    """
    Prove VoteBallots path reaches the REAL HermesJobExecutor object.

    This is the HXA4 proof: no mocking, real object, safe dry-run.
    """

    def setup_method(self):
        """Clear queue and setup temp evidence directory."""
        clear_job_queue()
        # Use temp directory for evidence to avoid polluting workspace
        self.evidence_root = tempfile.mkdtemp(prefix="hxa4_hermes_evidence_")

    def teardown_method(self):
        """Clear queue and cleanup temp evidence."""
        clear_job_queue()
        if hasattr(self, "evidence_root") and os.path.exists(self.evidence_root):
            shutil.rmtree(self.evidence_root, ignore_errors=True)

    def test_voteballots_job_reaches_real_executor_object(self):
        """
        VoteBallots build job reaches the REAL HermesJobExecutor.execute() method.

        Proves:
          1. FoundUpJob created via OpenClaw
          2. Job routes to HERMES_BUILDER
          3. Real HermesJobExecutor.execute() is called (not mocked)
          4. Status is SIMULATED (dry-run)
          5. real_execution_performed=False
          6. Evidence files written
        """
        # Step 1: Create VoteBallots job via OpenClaw
        intent = MockIntent(VOTEBALLOTS_BUILD_MESSAGE, sender="012")
        mock_dae = MagicMock()
        response = dispatch_foundup(mock_dae, intent)

        # Verify job created
        assert "FoundUpJob created" in response
        queue = get_job_queue()
        assert len(queue) == 1
        job = queue[0]
        assert job.foundup_id == VOTEBALLOTS_FOUNDUP_ID

        # HXA28: Set D3 capability token gates for build_foundup action
        set_d3_capability_token_gates(job)

        # Step 2: Create REAL executor (NOT mocked)
        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=self.evidence_root,
        )

        # Step 3: Execute job through REAL executor
        result = executor.execute(job)

        # Step 4: Verify SIMULATED status
        assert result.status == HermesExecutionStatus.SIMULATED, (
            f"Expected SIMULATED, got {result.status.value}"
        )

        # Step 5: Verify real_execution_performed=False
        assert result.real_execution_performed is False, (
            "real_execution_performed must be False in dry-run mode"
        )

        # Step 6: Verify checkpoint state
        assert result.checkpoint_state == "SIMULATED", (
            f"Expected checkpoint_state=SIMULATED, got {result.checkpoint_state}"
        )

        # Step 7: Verify WSP 97 truth fields
        assert result.verification_complete is False
        assert result.cabr_ready is False
        assert result.payout_ready is False

        # Step 8: Verify evidence path exists
        assert result.evidence_path is not None
        assert os.path.isdir(result.evidence_path), (
            f"Evidence directory not created: {result.evidence_path}"
        )

        # Step 9: Verify evidence files written
        metadata_path = os.path.join(result.evidence_path, "metadata.json")
        checkpoint_path = os.path.join(result.evidence_path, "checkpoint.json")
        assert os.path.isfile(metadata_path), "metadata.json not written"
        assert os.path.isfile(checkpoint_path), "checkpoint.json not written"

        # Step 10: Verify metadata.json contents
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
        assert metadata["job_id"] == job.job_id
        assert metadata["foundup_id"] == VOTEBALLOTS_FOUNDUP_ID
        assert metadata["dry_run"] is True
        assert metadata["execution_status"] == "SIMULATED"

    def test_consumer_path_reaches_real_executor(self):
        """
        Full consumer path reaches real executor.

        This proves the complete pipeline without mocking:
          OpenClaw → Queue → Consumer → Router → Real Executor → Evidence
        """
        # Create job
        intent = MockIntent(VOTEBALLOTS_BUILD_MESSAGE, sender="012")
        mock_dae = MagicMock()
        dispatch_foundup(mock_dae, intent)

        queue = get_job_queue()
        assert len(queue) == 1
        job = queue[0]

        # HXA28: Set D3 capability token gates for build_foundup action
        set_d3_capability_token_gates(job)

        # Create real consumer (will use real executor via import)
        consumer = FoundUpJobConsumer(dry_run=True)

        # Consume job through full pipeline
        result = consumer.consume_one(job)

        # Verify dispatched to Hermes
        assert result.dispatched is True, (
            f"Job not dispatched: {result.reason}"
        )

        # Verify checkpoint state from real executor
        assert result.checkpoint_state == "SIMULATED", (
            f"Expected checkpoint_state=SIMULATED, got {result.checkpoint_state}"
        )

        # Verify real_execution_performed=False
        assert result.real_execution_performed is False, (
            "real_execution_performed must be False"
        )

        # Verify WSP 97 truth fields
        assert result.verification_complete is False
        assert result.cabr_ready is False
        assert result.payout_ready is False


# ---------------------------------------------------------------------------
# Test: Delegation Request Built Correctly
# ---------------------------------------------------------------------------

class TestVoteBallotsDelegationRequestContract:
    """Verify HermesDelegationRequest built correctly for VoteBallots."""

    def setup_method(self):
        """Clear queue."""
        clear_job_queue()

    def teardown_method(self):
        """Clear queue."""
        clear_job_queue()

    def test_delegation_request_contains_voteballots_identity(self):
        """Request contains correct foundup_id and action."""
        # Create job
        intent = MockIntent(VOTEBALLOTS_BUILD_MESSAGE, sender="012")
        mock_dae = MagicMock()
        dispatch_foundup(mock_dae, intent)

        queue = get_job_queue()
        job = queue[0]

        # Build request via real executor
        executor = HermesJobExecutor(dry_run=True)
        request = executor.build_delegation_request(job)

        # Verify identity fields
        assert request.foundup_id == VOTEBALLOTS_FOUNDUP_ID
        assert request.requested_action == "build_foundup"
        assert request.dry_run is True
        assert request.job_id == job.job_id
        assert request.tenant_id == "012"

    def test_workspace_binding_built_for_voteballots(self):
        """Workspace binding correctly scopes to voteballots module."""
        # Create job
        intent = MockIntent(VOTEBALLOTS_BUILD_MESSAGE, sender="012")
        mock_dae = MagicMock()
        dispatch_foundup(mock_dae, intent)

        queue = get_job_queue()
        job = queue[0]

        # Build request
        executor = HermesJobExecutor(dry_run=True)
        request = executor.build_delegation_request(job)

        # Verify workspace binding
        binding = request.workspace_binding
        assert binding is not None
        assert binding.workspace_hint == f"modules/foundups/{VOTEBALLOTS_FOUNDUP_ID}"
        assert any(
            VOTEBALLOTS_FOUNDUP_ID in path
            for path in binding.allowed_paths
        )


# ---------------------------------------------------------------------------
# Test: No Live Delegate Task Calls
# ---------------------------------------------------------------------------

class TestNoLiveDelegateTaskCalls:
    """
    Verify no live delegate_task calls occur in dry-run mode.

    These tests ensure the safe execution boundary is maintained.
    """

    def setup_method(self):
        """Clear queue."""
        clear_job_queue()

    def teardown_method(self):
        """Clear queue."""
        clear_job_queue()

    def test_delegate_task_not_imported_in_dry_run(self):
        """delegate_task is not imported when dry_run=True and ENABLED=0."""
        # Create executor
        executor = HermesJobExecutor(dry_run=True)

        # Execute a job
        intent = MockIntent(VOTEBALLOTS_BUILD_MESSAGE, sender="012")
        mock_dae = MagicMock()
        dispatch_foundup(mock_dae, intent)

        queue = get_job_queue()
        job = queue[0]
        executor.execute(job)

        # Verify delegate_task was NOT imported
        # (would only be imported if dry_run=False AND ENABLED=1)
        assert executor._delegate_task_fn is None, (
            "delegate_task should not be imported in dry-run mode"
        )
        # _import_attempted should also be False since we never get to that branch
        # (dry_run=True returns early)

    def test_status_reason_indicates_simulation(self):
        """Status reason clearly indicates simulation, not real execution."""
        executor = HermesJobExecutor(dry_run=True)

        intent = MockIntent(VOTEBALLOTS_BUILD_MESSAGE, sender="012")
        mock_dae = MagicMock()
        dispatch_foundup(mock_dae, intent)

        queue = get_job_queue()
        job = queue[0]
        # HXA28: Set D3 capability token gates for build_foundup action
        set_d3_capability_token_gates(job)
        result = executor.execute(job)

        # Verify status reason mentions disabled/simulated
        assert "disabled" in result.status_reason.lower() or "simulated" in result.status_reason.lower(), (
            f"Status reason should indicate simulation: {result.status_reason}"
        )


# ---------------------------------------------------------------------------
# Test: WSP 97 Truth Table Verification
# ---------------------------------------------------------------------------

class TestWSP97TruthTableVerification:
    """
    Verify WSP 97 truth table for HXA4 real Hermes object tests.

    All fields must indicate dry-run/simulation state.
    """

    def setup_method(self):
        """Clear queue and setup temp evidence directory."""
        clear_job_queue()
        self.evidence_root = tempfile.mkdtemp(prefix="hxa4_wsp97_")

    def teardown_method(self):
        """Clear queue and cleanup."""
        clear_job_queue()
        if hasattr(self, "evidence_root") and os.path.exists(self.evidence_root):
            shutil.rmtree(self.evidence_root, ignore_errors=True)

    def test_wsp97_truth_table_all_fields(self):
        """
        Verify complete WSP 97 truth table for VoteBallots dry-run.

        Truth Table:
          | Field                     | Expected Value |
          |---------------------------|----------------|
          | status                    | SIMULATED      |
          | checkpoint_state          | SIMULATED      |
          | real_execution_performed  | False          |
          | verification_complete     | False          |
          | cabr_ready                | False          |
          | payout_ready              | False          |
          | dry_run (request)         | True           |
          | delegate_task imported    | No (None)      |
        """
        # Create job
        intent = MockIntent(VOTEBALLOTS_BUILD_MESSAGE, sender="012")
        mock_dae = MagicMock()
        dispatch_foundup(mock_dae, intent)

        queue = get_job_queue()
        job = queue[0]
        # HXA28: Set D3 capability token gates for build_foundup action
        set_d3_capability_token_gates(job)

        # Execute via real executor
        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=self.evidence_root,
        )
        result = executor.execute(job)

        # WSP 97 Truth Table Assertions
        assert result.status == HermesExecutionStatus.SIMULATED, "status"
        assert result.checkpoint_state == "SIMULATED", "checkpoint_state"
        assert result.real_execution_performed is False, "real_execution_performed"
        assert result.verification_complete is False, "verification_complete"
        assert result.cabr_ready is False, "cabr_ready"
        assert result.payout_ready is False, "payout_ready"
        assert result.request.dry_run is True, "request.dry_run"
        assert executor._delegate_task_fn is None, "delegate_task not imported"

        # Evidence written (observability, not execution proof)
        assert result.evidence_path is not None, "evidence_path"
        assert os.path.isdir(result.evidence_path), "evidence directory exists"


# ---------------------------------------------------------------------------
# Test: HXA9 PoC Artifact Bundle Generation
# ---------------------------------------------------------------------------


class TestHXA9PocArtifactBundleGeneration:
    """
    HXA9 Proof Test: VoteBallots PoC artifact bundle generation in safe dry-run.

    Proves that build_foundup action generates poc_artifact_bundle.json
    with correct WSP 97 truth fields.

    Slice: HXA9_VOTEBALLOTS_POC_GENERATION_SAFE_DRYRUN_PHASE1
    """

    def setup_method(self):
        """Clear queue and setup temp evidence directory."""
        clear_job_queue()
        self.evidence_root = tempfile.mkdtemp(prefix="hxa9_poc_bundle_")

    def teardown_method(self):
        """Clear queue and cleanup."""
        clear_job_queue()
        if hasattr(self, "evidence_root") and os.path.exists(self.evidence_root):
            shutil.rmtree(self.evidence_root, ignore_errors=True)

    def test_voteballots_poc_generation_safe_dryrun_creates_artifact_bundle(self):
        """
        HXA9: VoteBallots build_foundup creates poc_artifact_bundle.json.

        Proves:
          1. build_foundup action reaches real HermesJobExecutor
          2. poc_artifact_bundle.json is written to evidence directory
          3. Bundle contains poc_generation=True
          4. Bundle contains real_execution_performed=False
          5. Bundle contains repo_created=False
          6. Bundle contains live_delegate_called=False
          7. Bundle contains planned_artifacts list for voteballots

        WSP 97 Boundaries:
          - This is observability (PoC plan), not execution proof
          - No actual files are written to modules/foundups/voteballots/src/
          - No GitHub operations performed
          - No delegate_task called
        """
        # Step 1: Create VoteBallots build job via OpenClaw
        intent = MockIntent(VOTEBALLOTS_BUILD_MESSAGE, sender="012")
        mock_dae = MagicMock()
        dispatch_foundup(mock_dae, intent)

        queue = get_job_queue()
        assert len(queue) == 1
        job = queue[0]
        assert job.foundup_id == VOTEBALLOTS_FOUNDUP_ID
        assert job.requested_action == "build_foundup"

        # HXA28: Set D3 capability token gates for build_foundup action
        set_d3_capability_token_gates(job)

        # Step 2: Execute via REAL executor (not mocked)
        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=self.evidence_root,
        )
        result = executor.execute(job)

        # Step 3: Verify SIMULATED status (safe dry-run)
        assert result.status == HermesExecutionStatus.SIMULATED, (
            f"Expected SIMULATED, got {result.status.value}"
        )

        # Step 4: Verify evidence directory exists
        assert result.evidence_path is not None
        assert os.path.isdir(result.evidence_path), "Evidence directory not created"

        # Step 5: Verify poc_artifact_bundle.json exists
        bundle_path = os.path.join(result.evidence_path, "poc_artifact_bundle.json")
        assert os.path.isfile(bundle_path), (
            f"poc_artifact_bundle.json not created at {bundle_path}"
        )

        # Step 6: Load and verify bundle contents
        with open(bundle_path, "r") as f:
            bundle = json.load(f)

        # HXA9 Required Assertions:
        assert bundle["poc_generation"] is True, (
            "poc_generation must be True"
        )
        assert bundle["real_execution_performed"] is False, (
            "real_execution_performed must be False"
        )
        assert bundle["repo_created"] is False, (
            "repo_created must be False"
        )
        assert bundle["live_delegate_called"] is False, (
            "live_delegate_called must be False"
        )

        # Step 7: Verify planned artifacts reference voteballots
        assert bundle["foundup_id"] == VOTEBALLOTS_FOUNDUP_ID
        assert bundle["requested_action"] == "build_foundup"
        assert len(bundle["planned_artifacts"]) > 0, (
            "planned_artifacts should not be empty"
        )
        assert any(
            VOTEBALLOTS_FOUNDUP_ID in artifact
            for artifact in bundle["planned_artifacts"]
        ), "Planned artifacts should reference voteballots"

        # Step 8: Verify planned artifact paths are valid
        expected_paths = [
            f"modules/foundups/{VOTEBALLOTS_FOUNDUP_ID}/src/__init__.py",
            f"modules/foundups/{VOTEBALLOTS_FOUNDUP_ID}/src/{VOTEBALLOTS_FOUNDUP_ID}_core.py",
            f"modules/foundups/{VOTEBALLOTS_FOUNDUP_ID}/src/{VOTEBALLOTS_FOUNDUP_ID}_api.py",
        ]
        for expected in expected_paths:
            assert expected in bundle["planned_artifacts"], (
                f"Expected {expected} in planned_artifacts"
            )

        # Step 9: Verify WSP 97 truth - artifacts NOT written to source
        assert bundle["artifacts_written_to_source"] is False

    def test_extract_foundup_creates_artifact_bundle(self):
        """extract_foundup action also creates poc_artifact_bundle.json."""
        # Create extract job manually (not via OpenClaw intent parsing)
        from modules.communication.moltbot_bridge.src.foundup_job_contract import (
            FoundUpJob,
        )

        job = FoundUpJob(
            job_id="hxa9_extract_test_001",
            tenant_id="012",
            foundup_id=VOTEBALLOTS_FOUNDUP_ID,
            requested_action="extract_foundup",
        )

        # HXA28: Set D3 capability token gates for extract_foundup action
        set_d3_capability_token_gates(job)

        # Execute via real executor
        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=self.evidence_root,
        )
        result = executor.execute(job)

        # Verify bundle created
        assert result.evidence_path is not None
        bundle_path = os.path.join(result.evidence_path, "poc_artifact_bundle.json")
        assert os.path.isfile(bundle_path)

        with open(bundle_path, "r") as f:
            bundle = json.load(f)

        # Verify HXA9 truth fields
        assert bundle["poc_generation"] is True
        assert bundle["real_execution_performed"] is False
        assert bundle["repo_created"] is False
        assert bundle["live_delegate_called"] is False
        assert "external-repos" in bundle["planned_artifacts"][0]

    def test_validate_foundup_does_not_create_artifact_bundle(self):
        """validate_foundup action does NOT create poc_artifact_bundle.json."""
        from modules.communication.moltbot_bridge.src.foundup_job_contract import (
            FoundUpJob,
        )

        job = FoundUpJob(
            job_id="hxa9_validate_test_001",
            tenant_id="012",
            foundup_id=VOTEBALLOTS_FOUNDUP_ID,
            requested_action="validate_foundup",
        )

        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=self.evidence_root,
        )
        result = executor.execute(job)

        # Verify evidence exists
        assert result.evidence_path is not None

        # Verify poc_artifact_bundle.json NOT created for validate
        bundle_path = os.path.join(result.evidence_path, "poc_artifact_bundle.json")
        assert not os.path.isfile(bundle_path), (
            "poc_artifact_bundle.json should NOT be created for validate_foundup"
        )


# ---------------------------------------------------------------------------
# Test: HXA10 Controlled Scaffold Generation
# ---------------------------------------------------------------------------


class TestHXA10ControlledScaffoldGeneration:
    """
    HXA10 Proof Test: VoteBallots controlled scaffold generation in safe dry-run.

    Proves that build_foundup action generates actual scaffold files
    in the temp/evidence workspace, not production source.

    Progression:
      HXA9: Plan only (poc_artifact_bundle.json)
      HXA10: Actual scaffold files (voteballots_poc/*.md, *.json)

    Slice: HXA10_VOTEBALLOTS_CONTROLLED_SCAFFOLD_GENERATION_PHASE1
    """

    def setup_method(self):
        """Clear queue and setup temp evidence directory."""
        clear_job_queue()
        self.evidence_root = tempfile.mkdtemp(prefix="hxa10_scaffold_")

    def teardown_method(self):
        """Clear queue and cleanup."""
        clear_job_queue()
        if hasattr(self, "evidence_root") and os.path.exists(self.evidence_root):
            shutil.rmtree(self.evidence_root, ignore_errors=True)

    def test_voteballots_controlled_scaffold_generation_safe_dryrun_writes_temp_artifacts(
        self,
    ):
        """
        HXA10: VoteBallots build_foundup writes scaffold files to temp workspace.

        Proves:
          1. VoteBallots target is processed
          2. dry_run=True enforced
          3. Scaffold files created in temp/evidence workspace
          4. Generated files include VoteBallots identity
          5. Generated files are marked dry-run / preview
          6. No production VoteBallots source files changed
          7. real_execution_performed=False
          8. repo_created=False
          9. live_delegate_called=False

        WSP 97 Boundaries:
          - controlled_scaffold_generated=True (files written to temp)
          - production_source_modified=False
          - This is controlled dry-run scaffold, not production
        """
        # Step 1: Create VoteBallots build job
        intent = MockIntent(VOTEBALLOTS_BUILD_MESSAGE, sender="012")
        mock_dae = MagicMock()
        dispatch_foundup(mock_dae, intent)

        queue = get_job_queue()
        assert len(queue) == 1
        job = queue[0]

        # Verify VoteBallots target
        assert job.foundup_id == VOTEBALLOTS_FOUNDUP_ID
        assert job.requested_action == "build_foundup"

        # HXA28: Set D3 capability token gates for build_foundup action
        set_d3_capability_token_gates(job)

        # Step 2: Execute via REAL executor (not mocked)
        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=self.evidence_root,
        )
        result = executor.execute(job)

        # Step 3: Verify dry_run enforced (SIMULATED status)
        assert result.status == HermesExecutionStatus.SIMULATED
        assert result.request.dry_run is True

        # Step 4: Verify evidence directory exists
        assert result.evidence_path is not None
        assert os.path.isdir(result.evidence_path)

        # Step 5: Verify controlled_scaffold.json exists
        scaffold_meta_path = os.path.join(
            result.evidence_path, "controlled_scaffold.json"
        )
        assert os.path.isfile(scaffold_meta_path), (
            f"controlled_scaffold.json not created at {scaffold_meta_path}"
        )

        # Step 6: Load and verify scaffold metadata
        with open(scaffold_meta_path, "r") as f:
            scaffold_meta = json.load(f)

        # HXA10 Required Assertions:
        assert scaffold_meta["controlled_scaffold_generated"] is True
        assert scaffold_meta["real_execution_performed"] is False
        assert scaffold_meta["repo_created"] is False
        assert scaffold_meta["live_delegate_called"] is False
        assert scaffold_meta["production_source_modified"] is False
        assert scaffold_meta["dry_run"] is True
        assert scaffold_meta["foundup_id"] == VOTEBALLOTS_FOUNDUP_ID

        # Step 7: Verify scaffold directory exists
        scaffold_dir = scaffold_meta["scaffold_dir"]
        assert os.path.isdir(scaffold_dir), (
            f"Scaffold directory not created at {scaffold_dir}"
        )

        # Step 8: Verify generated files exist
        expected_files = [
            f"{VOTEBALLOTS_FOUNDUP_ID}_poc/README.md",
            f"{VOTEBALLOTS_FOUNDUP_ID}_poc/manifest.preview.json",
            f"{VOTEBALLOTS_FOUNDUP_ID}_poc/interface.preview.md",
            f"{VOTEBALLOTS_FOUNDUP_ID}_poc/implementation_plan.md",
        ]
        for expected_file in expected_files:
            full_path = os.path.join(result.evidence_path, expected_file)
            assert os.path.isfile(full_path), (
                f"Expected scaffold file not created: {expected_file}"
            )

        # Step 9: Verify files are marked as dry-run/preview
        readme_path = os.path.join(scaffold_dir, "README.md")
        with open(readme_path, "r") as f:
            readme_content = f.read()
        assert "DRY-RUN PREVIEW" in readme_content
        assert "NOT PRODUCTION CODE" in readme_content
        assert VOTEBALLOTS_FOUNDUP_ID in readme_content

        # Step 10: Verify manifest.preview.json contains VoteBallots identity
        manifest_path = os.path.join(scaffold_dir, "manifest.preview.json")
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
        assert manifest["foundup_id"] == VOTEBALLOTS_FOUNDUP_ID
        assert manifest["dry_run"] is True
        assert manifest["production_ready"] is False
        assert "_preview_warning" in manifest

        # Step 11: Verify no production VoteBallots source files exist in temp
        # (Production would be at modules/foundups/voteballots/src/)
        production_path = os.path.join(
            self.evidence_root, "modules", "foundups", VOTEBALLOTS_FOUNDUP_ID, "src"
        )
        assert not os.path.exists(production_path), (
            "Production source path should NOT exist in temp workspace"
        )

    def test_scaffold_files_contain_generation_metadata(self):
        """Scaffold files contain correct generation metadata."""
        from modules.communication.moltbot_bridge.src.foundup_job_contract import (
            FoundUpJob,
        )

        job = FoundUpJob(
            job_id="hxa10_metadata_test_001",
            tenant_id="012",
            foundup_id=VOTEBALLOTS_FOUNDUP_ID,
            requested_action="build_foundup",
        )

        # HXA28: Set D3 capability token gates for build_foundup action
        set_d3_capability_token_gates(job)

        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=self.evidence_root,
        )
        result = executor.execute(job)

        # Load scaffold metadata
        scaffold_meta_path = os.path.join(
            result.evidence_path, "controlled_scaffold.json"
        )
        with open(scaffold_meta_path, "r") as f:
            scaffold_meta = json.load(f)

        # Verify generation metadata
        assert scaffold_meta["generator_slice"] == "HXA10_CONTROLLED_SCAFFOLD_GENERATION"
        assert scaffold_meta["generator_version"] == "0.2.0"
        assert "generated_at" in scaffold_meta
        assert scaffold_meta["generated_file_count"] == 4

    def test_validate_foundup_does_not_create_scaffold(self):
        """validate_foundup action does NOT create scaffold files."""
        from modules.communication.moltbot_bridge.src.foundup_job_contract import (
            FoundUpJob,
        )

        job = FoundUpJob(
            job_id="hxa10_validate_test_001",
            tenant_id="012",
            foundup_id=VOTEBALLOTS_FOUNDUP_ID,
            requested_action="validate_foundup",
        )

        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=self.evidence_root,
        )
        result = executor.execute(job)

        # Verify evidence exists
        assert result.evidence_path is not None

        # Verify controlled_scaffold.json NOT created for validate
        scaffold_meta_path = os.path.join(
            result.evidence_path, "controlled_scaffold.json"
        )
        assert not os.path.isfile(scaffold_meta_path), (
            "controlled_scaffold.json should NOT be created for validate_foundup"
        )

        # Verify no scaffold directory
        scaffold_dir = os.path.join(
            result.evidence_path, f"{VOTEBALLOTS_FOUNDUP_ID}_poc"
        )
        assert not os.path.isdir(scaffold_dir), (
            "Scaffold directory should NOT be created for validate_foundup"
        )
