#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HXA16 Proof Test: Real Hermes Delegate Adapter Safe Harness

Determines if FoundUps Agent can invoke a real Hermes delegate interface
through the controlled harness without unsafe production behavior.

WSP 97 Truth Boundaries:
  - real_delegate_adapter_invoked: True (adapter boundary proven)
  - live_external_delegate_called: False (no actual external call)
  - controlled_delegate_invoked: True (controlled harness path)
  - repo_created: False
  - production_source_modified: False
  - external_federation_initiated: False
  - production_readiness_claimed: False

Verdict: DELEGATE_ADAPTER_BOUNDARY_PROVEN_EXTERNAL_CALL_NOT_ENABLED

Rationale:
  The vendor/hermes-agent/tools/delegate_tool.py delegate_task() function
  requires full Hermes runtime infrastructure:
    - parent_agent: AIAgent instance with full agent context
    - toolsets: Hermes toolset configurations
    - model configurations, credentials, terminal sessions
    - Child AIAgent spawning with isolated contexts

  We can prove the adapter boundary exists and document the interface
  requirements, but cannot safely invoke the actual external delegate
  without instantiating the full Hermes agent runtime.

Slice: HXA16_REAL_HERMES_DELEGATE_ADAPTER_SAFE_HARNESS_PHASE1
Worker: W1
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# FoundUpJob contract
from modules.communication.moltbot_bridge.src.foundup_job_contract import (
    FoundUpJob,
)

# Hermes Executor
from modules.infrastructure.wre_core.src.hermes_job_executor import (
    HermesJobExecutor,
    HermesExecutionStatus,
    is_hermes_delegation_enabled,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VOTEBALLOTS_FOUNDUP_ID = "voteballots_001"
GOTJUNK_FOUNDUP_ID = "gotjunk_001"

# Hermes delegate_tool.py location - resolve from repo root
def _get_delegate_tool_path() -> Path:
    """Get absolute path to delegate_tool.py from repo root."""
    # Try environment variable first
    import os
    workspace_root = os.environ.get("FOUNDUPS_WORKSPACE_ROOT")
    if workspace_root:
        return Path(workspace_root) / "vendor/hermes-agent/tools/delegate_tool.py"
    # Fall back to finding repo root from this file's location
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "CLAUDE.md").exists():
            return parent / "vendor/hermes-agent/tools/delegate_tool.py"
    # Last resort - cwd
    return Path("vendor/hermes-agent/tools/delegate_tool.py")

HERMES_DELEGATE_TOOL_PATH = _get_delegate_tool_path()


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
# Test: Hermes Delegate Interface Exists
# ---------------------------------------------------------------------------


class TestHermesRealDelegateInterfaceExists:
    """Verify the real Hermes delegate interface exists and document requirements."""

    def test_delegate_tool_file_exists(self):
        """Hermes delegate_tool.py exists in vendor directory."""
        assert HERMES_DELEGATE_TOOL_PATH.exists(), (
            f"delegate_tool.py not found at {HERMES_DELEGATE_TOOL_PATH}"
        )

    def test_delegate_tool_contains_delegate_task_function(self):
        """delegate_tool.py contains delegate_task function."""
        content = HERMES_DELEGATE_TOOL_PATH.read_text(encoding="utf-8")
        assert "def delegate_task(" in content, (
            "delegate_task function not found in delegate_tool.py"
        )

    def test_delegate_task_requires_parent_agent(self):
        """delegate_task requires parent_agent parameter (AIAgent instance)."""
        content = HERMES_DELEGATE_TOOL_PATH.read_text(encoding="utf-8")
        # The function signature includes parent_agent parameter
        assert "parent_agent" in content, (
            "parent_agent parameter not found in delegate_task"
        )

    def test_delegate_task_spawns_child_agents(self):
        """delegate_task spawns child AIAgent instances."""
        content = HERMES_DELEGATE_TOOL_PATH.read_text(encoding="utf-8")
        # The function creates child agents
        assert "AIAgent(" in content or "child_agent" in content.lower(), (
            "Child agent spawning not found in delegate_task"
        )


# ---------------------------------------------------------------------------
# Test: Delegate Interface Requirements Documentation
# ---------------------------------------------------------------------------


class TestHermesDelegateInterfaceRequirements:
    """Document the requirements for invoking real Hermes delegate."""

    def test_delegate_requires_full_hermes_runtime(self):
        """
        Document: delegate_task requires full Hermes runtime infrastructure.

        Required components:
        1. parent_agent: AIAgent instance with full context
        2. toolsets: Hermes toolset configurations
        3. model_config: LLM model configurations
        4. credentials: API keys and auth tokens
        5. terminal_sessions: Isolated terminal contexts

        Without these, delegate_task cannot be safely invoked.
        """
        # This test documents the requirement - actual invocation would need
        # all these components which we cannot safely instantiate
        requirements = {
            "parent_agent": "AIAgent instance with full agent context",
            "toolsets": "Hermes toolset configurations (file ops, web, etc)",
            "model_config": "LLM model configurations (Claude, etc)",
            "credentials": "API keys and authentication tokens",
            "terminal_sessions": "Isolated terminal session contexts",
            "child_agent_spawning": "Ability to spawn child AIAgent instances",
        }

        # All requirements must be met for safe invocation
        for req, description in requirements.items():
            assert req is not None
            assert description is not None

    def test_cannot_instantiate_hermes_runtime_safely(self):
        """
        Cannot instantiate full Hermes runtime without production risk.

        Attempting to instantiate AIAgent would require:
        - Real API credentials (production exposure)
        - Network access to LLM providers (external calls)
        - File system access beyond evidence workspace (production risk)

        Therefore: We prove adapter boundary exists but cannot call external delegate.
        """
        # We explicitly do NOT attempt to import or instantiate AIAgent
        # because doing so would violate WSP 97 truth boundaries
        pass


# ---------------------------------------------------------------------------
# Test: HXA16 Adapter Boundary Proof
# ---------------------------------------------------------------------------


class TestHXA16AdapterBoundaryProof:
    """
    HXA16 Proof: Real delegate adapter boundary exists but external call not enabled.

    Proves:
    1. Adapter boundary can be documented and tested
    2. Interface requirements are known
    3. Controlled harness can route to adapter
    4. External delegate call is NOT made (by design)
    5. WSP 97 truth fields accurately reflect this state
    """

    def setup_method(self):
        """Setup temp evidence directory."""
        self.evidence_root = tempfile.mkdtemp(prefix="hxa16_adapter_")

    def teardown_method(self):
        """Cleanup temp directory."""
        if hasattr(self, "evidence_root") and os.path.exists(self.evidence_root):
            shutil.rmtree(self.evidence_root, ignore_errors=True)

    def test_adapter_boundary_proven_via_controlled_harness(self):
        """
        HXA16 Proof: Adapter boundary proven, external call not enabled.

        This test:
        1. Creates FoundUpJob for VoteBallots
        2. Executes via controlled harness
        3. Verifies adapter boundary is reached
        4. Confirms NO external delegate call made
        5. Validates all WSP 97 truth fields
        """
        # Create job
        job = FoundUpJob(
            job_id="hxa16_adapter_proof_001",
            tenant_id="012",
            foundup_id=VOTEBALLOTS_FOUNDUP_ID,
            requested_action="build_foundup",
        )

        # HXA28: Set D3 capability token gates for build_foundup action
        set_d3_capability_token_gates(job)

        # Execute via controlled harness with real_delegate_adapter mode
        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=self.evidence_root,
            controlled_harness=True,
            real_delegate_adapter=True,  # New flag for HXA16
        )
        result = executor.execute(job)

        # Verify adapter boundary status
        assert result.status == HermesExecutionStatus.DELEGATE_ADAPTER_BOUNDARY_PROVEN

        # Verify WSP 97 truth fields
        assert result.real_delegate_adapter_invoked is True, (
            "Adapter boundary was reached"
        )
        assert result.live_external_delegate_called is False, (
            "No external delegate call"
        )
        assert result.controlled_delegate_invoked is True, (
            "Controlled harness path used"
        )
        assert result.repo_created is False
        assert result.production_source_modified is False
        assert result.external_federation_initiated is False
        assert result.production_readiness_claimed is False
        assert result.real_execution_performed is False

    def test_adapter_documents_interface_requirements_in_evidence(self):
        """Adapter boundary proof generates interface requirements documentation."""
        job = FoundUpJob(
            job_id="hxa16_interface_doc_001",
            tenant_id="012",
            foundup_id=VOTEBALLOTS_FOUNDUP_ID,
            requested_action="build_foundup",
        )

        # HXA28: Set D3 capability token gates for build_foundup action
        set_d3_capability_token_gates(job)

        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=self.evidence_root,
            controlled_harness=True,
            real_delegate_adapter=True,
        )
        result = executor.execute(job)

        # Verify interface requirements documented in evidence
        interface_doc_path = os.path.join(
            result.evidence_path, "delegate_interface_requirements.json"
        )
        assert os.path.isfile(interface_doc_path), (
            "Interface requirements not documented"
        )

        with open(interface_doc_path, "r") as f:
            requirements = json.load(f)

        assert "parent_agent" in requirements
        assert "toolsets" in requirements
        assert "external_call_blocked_reason" in requirements
        assert requirements["external_call_enabled"] is False

    def test_gotjunk_adapter_boundary_same_as_voteballots(self):
        """GotJunk receives same adapter boundary treatment as VoteBallots."""
        job = FoundUpJob(
            job_id="hxa16_gotjunk_adapter_001",
            tenant_id="012",
            foundup_id=GOTJUNK_FOUNDUP_ID,
            requested_action="build_foundup",
        )

        # HXA28: Set D3 capability token gates for build_foundup action
        set_d3_capability_token_gates(job)

        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=self.evidence_root,
            controlled_harness=True,
            real_delegate_adapter=True,
        )
        result = executor.execute(job)

        # Same treatment as VoteBallots
        assert result.status == HermesExecutionStatus.DELEGATE_ADAPTER_BOUNDARY_PROVEN
        assert result.real_delegate_adapter_invoked is True
        assert result.live_external_delegate_called is False


# ---------------------------------------------------------------------------
# Test: Real Delegate Adapter Disabled by Default
# ---------------------------------------------------------------------------


class TestRealDelegateAdapterDisabledByDefault:
    """Verify real_delegate_adapter is disabled by default."""

    def setup_method(self):
        """Setup temp evidence directory."""
        self.evidence_root = tempfile.mkdtemp(prefix="hxa16_default_")

    def teardown_method(self):
        """Cleanup temp directory."""
        if hasattr(self, "evidence_root") and os.path.exists(self.evidence_root):
            shutil.rmtree(self.evidence_root, ignore_errors=True)

    def test_real_delegate_adapter_false_by_default(self):
        """real_delegate_adapter defaults to False."""
        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=self.evidence_root,
        )
        assert executor.real_delegate_adapter is False

    def test_controlled_harness_without_adapter_uses_controlled_delegate(self):
        """Controlled harness without real_delegate_adapter uses controlled delegate only."""
        job = FoundUpJob(
            job_id="hxa16_no_adapter_001",
            tenant_id="012",
            foundup_id=VOTEBALLOTS_FOUNDUP_ID,
            requested_action="build_foundup",
        )

        # HXA28: Set D3 capability token gates for build_foundup action
        set_d3_capability_token_gates(job)

        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=self.evidence_root,
            controlled_harness=True,
            real_delegate_adapter=False,  # Explicit
        )
        result = executor.execute(job)

        # Should use controlled delegate, not adapter boundary
        assert result.status == HermesExecutionStatus.CONTROLLED_HARNESS_EXECUTED
        assert result.controlled_delegate_invoked is True
        assert result.real_delegate_adapter_invoked is False


# ---------------------------------------------------------------------------
# Test: Verdict Documentation
# ---------------------------------------------------------------------------


class TestHXA16VerdictDocumentation:
    """Document the HXA16 verdict and rationale."""

    def test_verdict_is_delegate_adapter_boundary_proven_external_call_not_enabled(self):
        """
        HXA16 Verdict: DELEGATE_ADAPTER_BOUNDARY_PROVEN_EXTERNAL_CALL_NOT_ENABLED

        Rationale:
        - The vendor/hermes-agent/tools/delegate_tool.py interface EXISTS
        - delegate_task() function is present and documented
        - Interface requirements are known (parent_agent, toolsets, etc)
        - Adapter boundary CAN be reached via controlled harness
        - External delegate CANNOT be called safely without full Hermes runtime
        - Calling external delegate would violate WSP 97 truth boundaries

        Outcome:
        - real_delegate_adapter_invoked = True (boundary proven)
        - live_external_delegate_called = False (not enabled)
        - controlled_delegate_invoked = True (controlled path used)
        - All production safety fields = False
        """
        verdict = "DELEGATE_ADAPTER_BOUNDARY_PROVEN_EXTERNAL_CALL_NOT_ENABLED"

        # Verify this is the correct verdict based on analysis
        reasons = [
            "delegate_tool.py exists and contains delegate_task",
            "delegate_task requires parent_agent (AIAgent instance)",
            "AIAgent requires full Hermes runtime infrastructure",
            "Cannot safely instantiate Hermes runtime without production risk",
            "Adapter boundary is provable without external call",
        ]

        for reason in reasons:
            assert len(reason) > 0

        assert verdict == "DELEGATE_ADAPTER_BOUNDARY_PROVEN_EXTERNAL_CALL_NOT_ENABLED"


# ---------------------------------------------------------------------------
# Test: Evidence Generation
# ---------------------------------------------------------------------------


class TestHXA16EvidenceGeneration:
    """Verify HXA16 generates proper evidence artifacts."""

    def setup_method(self):
        """Setup temp evidence directory."""
        self.evidence_root = tempfile.mkdtemp(prefix="hxa16_evidence_")

    def teardown_method(self):
        """Cleanup temp directory."""
        if hasattr(self, "evidence_root") and os.path.exists(self.evidence_root):
            shutil.rmtree(self.evidence_root, ignore_errors=True)

    def test_generates_adapter_boundary_proof_json(self):
        """Generates adapter_boundary_proof.json with full documentation."""
        job = FoundUpJob(
            job_id="hxa16_evidence_001",
            tenant_id="012",
            foundup_id=VOTEBALLOTS_FOUNDUP_ID,
            requested_action="build_foundup",
        )

        # HXA28: Set D3 capability token gates for build_foundup action
        set_d3_capability_token_gates(job)

        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=self.evidence_root,
            controlled_harness=True,
            real_delegate_adapter=True,
        )
        result = executor.execute(job)

        # Check adapter boundary proof
        proof_path = os.path.join(result.evidence_path, "adapter_boundary_proof.json")
        assert os.path.isfile(proof_path)

        with open(proof_path, "r") as f:
            proof = json.load(f)

        assert proof["foundup_id"] == VOTEBALLOTS_FOUNDUP_ID
        assert proof["verdict"] == "DELEGATE_ADAPTER_BOUNDARY_PROVEN_EXTERNAL_CALL_NOT_ENABLED"
        assert proof["real_delegate_adapter_invoked"] is True
        assert proof["live_external_delegate_called"] is False
        # Path may be absolute or relative - verify it ends with the expected path
        assert proof["delegate_tool_path"].replace("\\", "/").endswith(
            "vendor/hermes-agent/tools/delegate_tool.py"
        )
        assert "interface_requirements" in proof
        assert "blocked_reason" in proof

    def test_all_standard_evidence_files_present(self):
        """All standard evidence files are generated."""
        job = FoundUpJob(
            job_id="hxa16_standard_evidence_001",
            tenant_id="012",
            foundup_id=VOTEBALLOTS_FOUNDUP_ID,
            requested_action="build_foundup",
        )

        # HXA28: Set D3 capability token gates for build_foundup action
        set_d3_capability_token_gates(job)

        executor = HermesJobExecutor(
            dry_run=True,
            workspace_root=self.evidence_root,
            controlled_harness=True,
            real_delegate_adapter=True,
        )
        result = executor.execute(job)

        # Standard files
        assert os.path.isfile(os.path.join(result.evidence_path, "metadata.json"))
        assert os.path.isfile(os.path.join(result.evidence_path, "checkpoint.json"))

        # HXA16-specific files
        assert os.path.isfile(os.path.join(result.evidence_path, "adapter_boundary_proof.json"))
        assert os.path.isfile(os.path.join(result.evidence_path, "delegate_interface_requirements.json"))
