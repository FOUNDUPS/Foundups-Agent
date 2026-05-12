#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HXA12 Proof Test: GotJunk Second FoundUp Safe Dry-Run Proof

Proves the OpenClaw/Hermes factory generalizes beyond VoteBallots by running
GotJunk through the same safe dry-run proof path.

Progression:
  HXA3/HXA4: VoteBallots proof (first FoundUp)
  HXA12: GotJunk proof (second FoundUp - validates generalization)

WSP 97 Truth Boundaries:
  - dry_run=True throughout
  - real_execution_performed=False
  - No GitHub repo created
  - No live extraction
  - No payout/CABR claims
  - Production GotJunk files unchanged

Slice: HXA12_GOTJUNK_SECOND_PROOF_SAFE_DRYRUN_PHASE1
Worker: W1
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from unittest.mock import MagicMock

# OpenClaw Orchestrator
from modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator import (
    dispatch_foundup,
    get_job_queue,
    clear_job_queue,
    _is_explicit_build_intent,
    _extract_foundup_id,
    _detect_dry_run_mode,
)

# FoundUpJob contract
from modules.communication.moltbot_bridge.src.foundup_job_contract import (
    FoundUpJob,
)

# WRE Consumer
from modules.infrastructure.wre_core.src.foundup_job_consumer import (
    FoundUpJobConsumer,
)

# Hermes Executor
from modules.infrastructure.wre_core.src.hermes_job_executor import (
    HermesJobExecutor,
    HermesExecutionStatus,
    is_hermes_delegation_enabled,
)


# ---------------------------------------------------------------------------
# GotJunk Constants (from foundup_manifest.json)
# ---------------------------------------------------------------------------

GOTJUNK_FOUNDUP_ID = "gotjunk_001"
GOTJUNK_BUILD_MESSAGE = "start build gotjunk_001 --dry-run"
GOTJUNK_ENTRY_URL = "https://gotjunk-56566376153.us-west1.run.app/"


# ---------------------------------------------------------------------------
# Mock Intent (duck-typed to match OpenClawIntent)
# ---------------------------------------------------------------------------


class MockIntent:
    """Mock OpenClawIntent for testing dispatch_foundup."""

    def __init__(self, raw_message: str, sender: str = "012"):
        self.raw_message = raw_message
        self.sender = sender
        self.session_key = "hxa12_gotjunk_test"
        self.channel = "test_channel"


def set_d3_capability_token_gates(job):
    """
    Set D3 capability token gates on a job for testing.

    HXA28: build_foundup and extract_foundup are now D3 actions that require
    capability tokens. For tests that need to reach SIMULATED status (not
    BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD), set all four capability token gates
    AND the security gate.

    This simulates a valid capability token being present with security gate passed.
    """
    # Capability token gates
    job.policy_flags.capability_token_checked = True
    job.policy_flags.capability_token_present = True
    job.policy_flags.capability_token_validated = True
    job.policy_flags.capability_token_scope_authorized = True
    # Security gate (also required for D3)
    job.policy_flags.security_gate_checked = True
    job.policy_flags.security_gate_passed = True


# ---------------------------------------------------------------------------
# Test: GotJunk Build Intent Detection
# ---------------------------------------------------------------------------


class TestGotJunkBuildIntentDetection:
    """Verify GotJunk build intent is correctly detected."""

    def test_gotjunk_build_message_detected_as_build_intent(self):
        """'start build gotjunk_001' is explicit build intent."""
        assert _is_explicit_build_intent(GOTJUNK_BUILD_MESSAGE) is True

    def test_gotjunk_id_extracted_from_message(self):
        """foundup_id 'gotjunk_001' extracted from build message."""
        foundup_id = _extract_foundup_id(GOTJUNK_BUILD_MESSAGE)
        assert foundup_id == GOTJUNK_FOUNDUP_ID

    def test_dry_run_mode_detected_in_message(self):
        """--dry-run flag detected in message."""
        assert _detect_dry_run_mode(GOTJUNK_BUILD_MESSAGE) is True


# ---------------------------------------------------------------------------
# Test: GotJunk FoundUpJob Creation
# ---------------------------------------------------------------------------


class TestGotJunkDryRunJobCreation:
    """Verify GotJunk FoundUpJob created with dry_run mode."""

    def setup_method(self):
        """Clear job queue before each test."""
        clear_job_queue()

    def teardown_method(self):
        """Clear job queue after each test."""
        clear_job_queue()

    def test_gotjunk_build_creates_foundup_job(self):
        """GotJunk build intent creates FoundUpJob in queue."""
        intent = MockIntent(GOTJUNK_BUILD_MESSAGE, sender="012")
        mock_dae = MagicMock()

        response = dispatch_foundup(mock_dae, intent)

        assert "FoundUpJob created" in response
        queue = get_job_queue()
        assert len(queue) == 1

        job = queue[0]
        assert job.foundup_id == GOTJUNK_FOUNDUP_ID
        assert job.requested_action == "build_foundup"
        assert job.policy_flags.dry_run_mode is True
        assert job.tenant_id == "012"


# ---------------------------------------------------------------------------
# Test: GotJunk Second Proof - Safe Dry-Run Path
# ---------------------------------------------------------------------------


class TestHXA12GotJunkSecondProofSafeDryRun:
    """
    HXA12 Proof: GotJunk reaches same safe dry-run factory path as VoteBallots.

    Proves the factory generalizes beyond the first proof target.
    """

    def setup_method(self):
        """Clear queue and setup temp evidence directory."""
        clear_job_queue()
        self.evidence_root = tempfile.mkdtemp(prefix="hxa12_gotjunk_")

    def teardown_method(self):
        """Clear queue and cleanup."""
        clear_job_queue()
        if hasattr(self, "evidence_root") and os.path.exists(self.evidence_root):
            shutil.rmtree(self.evidence_root, ignore_errors=True)

    def test_gotjunk_second_proof_safe_dryrun_reaches_hermes_and_generates_preview(
        self,
    ):
        """
        HXA12: GotJunk build reaches Hermes and generates dry-run preview.

        Proves:
          1. Target is GotJunk/gotjunk_001
          2. dry_run=True enforced
          3. Real Hermes executor object is used (not mocked)
          4. Artifact plan and scaffold preview generated
          5. Generated preview identifies GotJunk
          6. Production GotJunk source unchanged
          7. real_execution_performed=False
          8. repo_created=False
          9. live_delegate_called=False

        WSP 97: This proves factory generalization, not production readiness.
        """
        # Step 1: Verify environment safety gate
        assert is_hermes_delegation_enabled() is False, (
            "HERMES_DELEGATE_ENABLED must be 0 for safe dry-run"
        )

        # Step 2: Create GotJunk build job via OpenClaw
        intent = MockIntent(GOTJUNK_BUILD_MESSAGE, sender="012")
        mock_dae = MagicMock()
        dispatch_foundup(mock_dae, intent)

        queue = get_job_queue()
        assert len(queue) == 1
        job = queue[0]

        # Step 3: Verify target is GotJunk
        assert job.foundup_id == GOTJUNK_FOUNDUP_ID, (
            f"Expected {GOTJUNK_FOUNDUP_ID}, got {job.foundup_id}"
        )
        assert job.requested_action == "build_foundup"

        # HXA28: Set D3 capability token gates for build_foundup action
        set_d3_capability_token_gates(job)

        # Step 4: Execute via REAL Hermes executor (not mocked)
        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=self.evidence_root,
        )
        result = executor.execute(job)

        # Step 5: Verify dry_run enforced (SIMULATED status)
        assert result.status == HermesExecutionStatus.SIMULATED, (
            f"Expected SIMULATED, got {result.status.value}"
        )
        assert result.request.dry_run is True

        # Step 6: Verify WSP 97 truth fields
        assert result.real_execution_performed is False, (
            "real_execution_performed must be False"
        )
        assert result.verification_complete is False
        assert result.cabr_ready is False
        assert result.payout_ready is False

        # Step 7: Verify evidence directory created
        assert result.evidence_path is not None
        assert os.path.isdir(result.evidence_path)

        # Step 8: Verify poc_artifact_bundle.json exists and identifies GotJunk
        bundle_path = os.path.join(result.evidence_path, "poc_artifact_bundle.json")
        assert os.path.isfile(bundle_path), "poc_artifact_bundle.json not created"

        with open(bundle_path, "r") as f:
            bundle = json.load(f)

        assert bundle["foundup_id"] == GOTJUNK_FOUNDUP_ID
        assert bundle["poc_generation"] is True
        assert bundle["real_execution_performed"] is False
        assert bundle["repo_created"] is False
        assert bundle["live_delegate_called"] is False

        # Step 9: Verify controlled_scaffold.json exists and identifies GotJunk
        scaffold_meta_path = os.path.join(
            result.evidence_path, "controlled_scaffold.json"
        )
        assert os.path.isfile(scaffold_meta_path), (
            "controlled_scaffold.json not created"
        )

        with open(scaffold_meta_path, "r") as f:
            scaffold_meta = json.load(f)

        assert scaffold_meta["foundup_id"] == GOTJUNK_FOUNDUP_ID
        assert scaffold_meta["controlled_scaffold_generated"] is True
        assert scaffold_meta["real_execution_performed"] is False
        assert scaffold_meta["repo_created"] is False
        assert scaffold_meta["live_delegate_called"] is False
        assert scaffold_meta["production_source_modified"] is False

        # Step 10: Verify scaffold directory exists with GotJunk identity
        scaffold_dir = scaffold_meta["scaffold_dir"]
        assert os.path.isdir(scaffold_dir)

        # Step 11: Verify generated files reference GotJunk
        readme_path = os.path.join(scaffold_dir, "README.md")
        assert os.path.isfile(readme_path)
        with open(readme_path, "r") as f:
            readme_content = f.read()
        assert GOTJUNK_FOUNDUP_ID in readme_content or "GOTJUNK" in readme_content.upper()
        assert "DRY-RUN PREVIEW" in readme_content

        manifest_path = os.path.join(scaffold_dir, "manifest.preview.json")
        assert os.path.isfile(manifest_path)
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
        assert manifest["foundup_id"] == GOTJUNK_FOUNDUP_ID
        assert manifest["dry_run"] is True
        assert manifest["production_ready"] is False

    def test_gotjunk_consumer_path_reaches_real_executor(self):
        """Full consumer path reaches real executor for GotJunk."""
        intent = MockIntent(GOTJUNK_BUILD_MESSAGE, sender="012")
        mock_dae = MagicMock()
        dispatch_foundup(mock_dae, intent)

        queue = get_job_queue()
        job = queue[0]

        # HXA28: Set D3 capability token gates for build_foundup action
        set_d3_capability_token_gates(job)

        # Use real consumer (not mocked)
        consumer = FoundUpJobConsumer(dry_run=True)
        result = consumer.consume_one(job)

        # Verify dispatched via Hermes
        assert result.dispatched is True
        assert result.checkpoint_state == "SIMULATED"
        assert result.real_execution_performed is False

    def test_gotjunk_direct_job_reaches_hermes(self):
        """Direct FoundUpJob creation reaches Hermes for GotJunk."""
        # Create job directly (bypassing OpenClaw intent parsing)
        job = FoundUpJob(
            job_id="hxa12_gotjunk_direct_001",
            tenant_id="012",
            foundup_id=GOTJUNK_FOUNDUP_ID,
            requested_action="build_foundup",
        )

        # HXA28: Set D3 capability token gates for build_foundup action
        set_d3_capability_token_gates(job)

        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=self.evidence_root,
        )
        result = executor.execute(job)

        # Verify SIMULATED and GotJunk identity
        assert result.status == HermesExecutionStatus.SIMULATED
        assert result.real_execution_performed is False

        # Verify evidence files identify GotJunk
        bundle_path = os.path.join(result.evidence_path, "poc_artifact_bundle.json")
        with open(bundle_path, "r") as f:
            bundle = json.load(f)
        assert bundle["foundup_id"] == GOTJUNK_FOUNDUP_ID


# ---------------------------------------------------------------------------
# Test: GotJunk vs VoteBallots Parity
# ---------------------------------------------------------------------------


class TestGotJunkVoteBallotsParity:
    """Verify GotJunk receives same treatment as VoteBallots."""

    def setup_method(self):
        """Clear queue and setup temp evidence directory."""
        clear_job_queue()
        self.evidence_root = tempfile.mkdtemp(prefix="hxa12_parity_")

    def teardown_method(self):
        """Clear queue and cleanup."""
        clear_job_queue()
        if hasattr(self, "evidence_root") and os.path.exists(self.evidence_root):
            shutil.rmtree(self.evidence_root, ignore_errors=True)

    def test_gotjunk_generates_same_artifact_types_as_voteballots(self):
        """GotJunk generates same evidence artifacts as VoteBallots."""
        # Create GotJunk job
        job = FoundUpJob(
            job_id="hxa12_parity_test_001",
            tenant_id="012",
            foundup_id=GOTJUNK_FOUNDUP_ID,
            requested_action="build_foundup",
        )

        # HXA28: Set D3 capability token gates for build_foundup action
        set_d3_capability_token_gates(job)

        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=self.evidence_root,
        )
        result = executor.execute(job)

        # Same evidence files as VoteBallots
        assert os.path.isfile(
            os.path.join(result.evidence_path, "metadata.json")
        )
        assert os.path.isfile(
            os.path.join(result.evidence_path, "checkpoint.json")
        )
        assert os.path.isfile(
            os.path.join(result.evidence_path, "poc_artifact_bundle.json")
        )
        assert os.path.isfile(
            os.path.join(result.evidence_path, "controlled_scaffold.json")
        )

        # Same scaffold structure
        scaffold_dir = os.path.join(
            result.evidence_path, f"{GOTJUNK_FOUNDUP_ID}_poc"
        )
        assert os.path.isfile(os.path.join(scaffold_dir, "README.md"))
        assert os.path.isfile(os.path.join(scaffold_dir, "manifest.preview.json"))
        assert os.path.isfile(os.path.join(scaffold_dir, "interface.preview.md"))
        assert os.path.isfile(os.path.join(scaffold_dir, "implementation_plan.md"))

    def test_gotjunk_wsp97_truth_fields_match_voteballots(self):
        """GotJunk has same WSP 97 truth field values as VoteBallots."""
        job = FoundUpJob(
            job_id="hxa12_wsp97_test_001",
            tenant_id="012",
            foundup_id=GOTJUNK_FOUNDUP_ID,
            requested_action="build_foundup",
        )

        # HXA28: Set D3 capability token gates for build_foundup action
        set_d3_capability_token_gates(job)

        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=self.evidence_root,
        )
        result = executor.execute(job)

        # WSP 97 truth table (same as VoteBallots)
        assert result.status == HermesExecutionStatus.SIMULATED
        assert result.checkpoint_state == "SIMULATED"
        assert result.real_execution_performed is False
        assert result.verification_complete is False
        assert result.cabr_ready is False
        assert result.payout_ready is False
        assert result.request.dry_run is True
        assert executor._delegate_task_fn is None
