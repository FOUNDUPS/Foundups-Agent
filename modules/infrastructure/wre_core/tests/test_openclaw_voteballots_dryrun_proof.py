#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HXA3 Proof Test: OpenClaw → VoteBallots FoundUpJob → WRE → Hermes (dry-run)

Proves the trunk execution path:
  012 build intent → OpenClaw → FoundUpJob → queue → WRE Consumer → Hermes → evidence

This is the P0 VoteBallots idea→PoC proof as defined in HXA3_OPENCLAW_HERMES_VOTEBALLOTS_DRYRUN_PROOF_PHASE1.

WSP 97 Truth Boundaries:
  - dry_run=True throughout
  - real_execution_performed=False
  - No GitHub repo created
  - No live extraction
  - No payout/CABR claims

Slice: HXA3_OPENCLAW_HERMES_VOTEBALLOTS_DRYRUN_PROOF_PHASE1
Worker: W1
"""

from __future__ import annotations

import pytest
from typing import Any, Dict
from unittest.mock import MagicMock, patch

# OpenClaw Orchestrator
from modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator import (
    dispatch_foundup,
    get_job_queue,
    clear_job_queue,
    _is_explicit_build_intent,
    _extract_foundup_id,
    _detect_dry_run_mode,
)

# WRE Consumer
from modules.infrastructure.wre_core.src.foundup_job_consumer import (
    FoundUpJobConsumer,
    drain_openclaw_queue_dry_run,
)

# Router
from modules.infrastructure.wre_core.src.foundup_job_router import (
    RouteStatus,
    TargetBackend,
)


# ---------------------------------------------------------------------------
# VoteBallots Constants
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
        self.session_key = "hxa3_test_session"
        self.channel = "test_channel"


# ---------------------------------------------------------------------------
# Test: Explicit Build Intent Detection for VoteBallots
# ---------------------------------------------------------------------------

class TestVoteBallotsBuildIntentDetection:
    """Verify VoteBallots build intent is correctly detected."""

    def test_voteballots_build_message_detected_as_build_intent(self):
        """'start build voteballots' is explicit build intent."""
        assert _is_explicit_build_intent(VOTEBALLOTS_BUILD_MESSAGE) is True

    def test_voteballots_id_extracted_from_message(self):
        """foundup_id 'voteballots' extracted from build message."""
        foundup_id = _extract_foundup_id(VOTEBALLOTS_BUILD_MESSAGE)
        assert foundup_id == VOTEBALLOTS_FOUNDUP_ID

    def test_dry_run_mode_detected_in_message(self):
        """--dry-run flag detected in message."""
        assert _detect_dry_run_mode(VOTEBALLOTS_BUILD_MESSAGE) is True


# ---------------------------------------------------------------------------
# Test: VoteBallots FoundUpJob Creation via dispatch_foundup
# ---------------------------------------------------------------------------

class TestVoteBallotsDryRunJobCreation:
    """Verify VoteBallots FoundUpJob created with dry_run mode."""

    def setup_method(self):
        """Clear queue before each test."""
        clear_job_queue()

    def teardown_method(self):
        """Clear queue after each test."""
        clear_job_queue()

    def test_dispatch_foundup_creates_voteballots_job_in_queue(self):
        """dispatch_foundup creates job in queue for VoteBallots build intent."""
        intent = MockIntent(VOTEBALLOTS_BUILD_MESSAGE, sender="012")

        # Mock the DAE to satisfy dispatch_foundup signature
        mock_dae = MagicMock()

        # Dispatch (creates job and adds to queue)
        response = dispatch_foundup(mock_dae, intent)

        # Verify response indicates job created
        assert "FoundUpJob created" in response
        assert "voteballots" in response
        assert "dry_run_mode: True" in response

        # Verify job in queue
        queue = get_job_queue()
        assert len(queue) == 1

        job = queue[0]
        assert job.foundup_id == VOTEBALLOTS_FOUNDUP_ID
        assert job.requested_action == "build_foundup"
        assert job.policy_flags.dry_run_mode is True
        assert job.tenant_id == "012"


# ---------------------------------------------------------------------------
# Test: VoteBallots Dry-Run Through Full Pipeline
# ---------------------------------------------------------------------------

class TestVoteBallotsDryRunPipelineProof:
    """
    Prove the full dry-run pipeline:
      OpenClaw → FoundUpJob → queue drain → WRE Consumer → Hermes → result

    This is the HXA3 trunk proof test.
    """

    def setup_method(self):
        """Clear queue before each test."""
        clear_job_queue()

    def teardown_method(self):
        """Clear queue after each test."""
        clear_job_queue()

    @patch("modules.infrastructure.wre_core.src.hermes_job_executor.execute_foundup_job")
    def test_openclaw_voteballots_foundup_build_dryrun_reaches_hermes(
        self, mock_hermes_execute
    ):
        """
        Full pipeline proof: VoteBallots build job drains through WRE to Hermes.

        Asserts:
          - FoundUpJob created with foundup_id=voteballots
          - dry_run=True
          - Hermes executor invoked
          - real_execution_performed=False
          - No live repo/extraction side effect
        """
        # Setup mock Hermes executor response
        mock_hermes_result = MagicMock()
        mock_hermes_result.status.value = "SIMULATED"
        mock_hermes_result.checkpoint_state = "SIMULATED"
        mock_hermes_result.checkpoint_result = "Dry-run simulation for voteballots build"
        mock_hermes_result.checkpoint_blocker = None
        mock_hermes_result.checkpoint_next_action = "Proceed to Phase 2 if approved"
        mock_hermes_result.evidence_path = ".hermes_evidence/hxa3_voteballots_test/"
        mock_hermes_result.real_execution_performed = False
        mock_hermes_execute.return_value = mock_hermes_result

        # Step 1: Create VoteBallots job via OpenClaw dispatcher
        intent = MockIntent(VOTEBALLOTS_BUILD_MESSAGE, sender="012")
        mock_dae = MagicMock()
        response = dispatch_foundup(mock_dae, intent)

        # Verify job created
        assert "FoundUpJob created" in response
        queue = get_job_queue()
        assert len(queue) == 1
        job = queue[0]
        assert job.foundup_id == VOTEBALLOTS_FOUNDUP_ID
        assert job.policy_flags.dry_run_mode is True

        # Step 2: Drain queue through WRE Consumer
        consumer = FoundUpJobConsumer(dry_run=True)
        results = consumer.drain_openclaw_queue_once(clear=False)

        # Verify results
        assert len(results) == 1
        result = results[0]

        # Step 3: Verify Hermes was invoked
        mock_hermes_execute.assert_called_once()
        called_job = mock_hermes_execute.call_args[0][0]
        assert called_job.foundup_id == VOTEBALLOTS_FOUNDUP_ID

        # Step 4: Verify dry-run truth fields
        assert result.dispatched is True
        assert result.target_backend == TargetBackend.HERMES_BUILDER
        assert result.checkpoint_state == "SIMULATED"
        assert result.real_execution_performed is False

        # Step 5: Verify evidence path exists in result
        assert result.evidence_path == ".hermes_evidence/hxa3_voteballots_test/"

        # Step 6: Verify WSP 97 truth fields
        assert result.verification_complete is False
        assert result.cabr_ready is False
        assert result.payout_ready is False

    @patch("modules.infrastructure.wre_core.src.hermes_job_executor.execute_foundup_job")
    def test_drain_openclaw_queue_dry_run_convenience_function(
        self, mock_hermes_execute
    ):
        """
        Test drain_openclaw_queue_dry_run() convenience function with VoteBallots.

        This is the function called by 'python run_wre.py drain'.
        """
        # Setup mock
        mock_hermes_result = MagicMock()
        mock_hermes_result.status.value = "SIMULATED"
        mock_hermes_result.checkpoint_state = "SIMULATED"
        mock_hermes_result.checkpoint_result = None
        mock_hermes_result.checkpoint_blocker = None
        mock_hermes_result.checkpoint_next_action = None
        mock_hermes_result.evidence_path = ".hermes_evidence/test/"
        mock_hermes_result.real_execution_performed = False
        mock_hermes_execute.return_value = mock_hermes_result

        # Create job
        intent = MockIntent(VOTEBALLOTS_BUILD_MESSAGE, sender="012")
        mock_dae = MagicMock()
        dispatch_foundup(mock_dae, intent)

        # Drain using convenience function
        summary = drain_openclaw_queue_dry_run(clear=False)

        # Verify summary structure
        assert summary["dry_run"] is True
        assert summary["job_count"] == 1
        assert len(summary["results"]) == 1

        # Verify result in summary
        result = summary["results"][0]
        assert result["dispatched"] is True
        assert result["checkpoint_state"] == "SIMULATED"
        assert result["real_execution_performed"] is False

        # Verify truth boundaries in summary
        assert summary["summary"]["verification_complete"] is False
        assert summary["summary"]["cabr_ready"] is False
        assert summary["summary"]["payout_ready"] is False


# ---------------------------------------------------------------------------
# Test: VoteBallots Routes to HERMES_BUILDER (not mocked router)
# ---------------------------------------------------------------------------

class TestVoteBallotsBuildRouting:
    """Verify VoteBallots build_foundup routes to HERMES_BUILDER."""

    def setup_method(self):
        """Clear queue before each test."""
        clear_job_queue()

    def teardown_method(self):
        """Clear queue after each test."""
        clear_job_queue()

    def test_voteballots_routes_to_hermes_builder(self):
        """VoteBallots build_foundup action routes to HERMES_BUILDER."""
        from modules.infrastructure.wre_core.src.foundup_job_router import route_foundup_job

        # Create job
        intent = MockIntent(VOTEBALLOTS_BUILD_MESSAGE, sender="012")
        mock_dae = MagicMock()
        dispatch_foundup(mock_dae, intent)

        queue = get_job_queue()
        job = queue[0]

        # Route job
        envelope = route_foundup_job(job)

        # Verify routing
        assert envelope.route_status == RouteStatus.ROUTED
        assert envelope.target_backend == TargetBackend.HERMES_BUILDER
        assert envelope.foundup_id == VOTEBALLOTS_FOUNDUP_ID
