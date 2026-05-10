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
