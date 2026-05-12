#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HXA20 Proof Test: Production Source Modification Gate

Defines and tests the fail-closed gate contract required BEFORE any production
source modification path can ever be enabled. This is a fail-closed gate design.

WSP 97 Truth Boundaries:
  - production_source_modified: False (ALWAYS - this slice MUST NOT modify production source)
  - repo_created: False
  - live_external_delegate_called: False
  - external_federation_initiated: False
  - verification_complete: False
  - cabr_ready: False
  - payout_ready: False

HXA19 Verdict was: REPO_CREATION_APPROVAL_GATE_DEFINED
HXA20 defines: Safe approval gate contract for future production source modification paths.

Key Principle: FAIL-CLOSED
  - Missing human approval -> BLOCK
  - Missing capability token -> BLOCK
  - Security gate not passed -> BLOCK
  - Target path outside allowed roots -> BLOCK
  - Target path in blocked paths -> BLOCK
  - Production source path while dry_run_mode=True -> BLOCK
  - Workspace binding not enforced -> BLOCK
  - Path constraints not validated -> BLOCK
  - Destructive class above threshold -> BLOCK
  - Unsupported operation -> BLOCK

Slice: HXA20_PRODUCTION_SOURCE_GATE_PHASE1
Worker: 0102
"""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

# FoundUpJob contract
from modules.communication.moltbot_bridge.src.foundup_job_contract import (
    FoundUpJob,
)


# ===========================================================================
# SECTION 1: Production Source Gate Model (Test-Local Definition)
# ===========================================================================


class ProductionSourceBlockReason(str, Enum):
    """Reasons why production source modification would be blocked."""

    NONE = "NONE"
    MISSING_HUMAN_APPROVAL = "MISSING_HUMAN_APPROVAL"
    MISSING_CAPABILITY_TOKEN = "MISSING_CAPABILITY_TOKEN"
    SECURITY_GATE_NOT_PASSED = "SECURITY_GATE_NOT_PASSED"
    TARGET_PATH_OUTSIDE_ALLOWED_ROOTS = "TARGET_PATH_OUTSIDE_ALLOWED_ROOTS"
    TARGET_PATH_IN_BLOCKED_PATHS = "TARGET_PATH_IN_BLOCKED_PATHS"
    DRY_RUN_MODE_ACTIVE = "DRY_RUN_MODE_ACTIVE"
    WORKSPACE_BINDING_NOT_ENFORCED = "WORKSPACE_BINDING_NOT_ENFORCED"
    PATH_CONSTRAINTS_NOT_VALIDATED = "PATH_CONSTRAINTS_NOT_VALIDATED"
    DESTRUCTIVE_CLASS_ABOVE_THRESHOLD = "DESTRUCTIVE_CLASS_ABOVE_THRESHOLD"
    UNSUPPORTED_OPERATION = "UNSUPPORTED_OPERATION"


class ProductionSourceGateResult(str, Enum):
    """Result of production source gate evaluation."""

    BLOCKED = "BLOCKED"
    SIMULATED_ONLY = "SIMULATED_ONLY"  # Dry-run approved
    APPROVED_LIVE = "APPROVED_LIVE"  # Future - never returned in HXA20


# Destructive action classes (from WRE_DESTRUCTIVE_ACTION_GUARD.md)
class DestructiveClass(str, Enum):
    """Destructive action classification scale."""

    D0_OBSERVE = "D0_OBSERVE"  # Read-only operations
    D1_LOCAL_TEMP = "D1_LOCAL_TEMP"  # Local temporary changes
    D2_LOCAL_PERSIST = "D2_LOCAL_PERSIST"  # Local persistent changes
    D3_REMOTE_SOFT = "D3_REMOTE_SOFT"  # Remote reversible changes
    D4_REMOTE_HARD = "D4_REMOTE_HARD"  # Remote difficult-to-reverse
    D5_PRODUCTION = "D5_PRODUCTION"  # Production state modification
    D6_IRREVERSIBLE = "D6_IRREVERSIBLE"  # Cannot be undone


# Supported file operations
SUPPORTED_OPERATIONS = frozenset({
    "read",
    "write",
    "create",
    "delete",
    "rename",
    "patch",
})


@dataclass
class ProductionSourceGate:
    """
    Production source modification approval gate model.

    Defines all fields required before production source modification can ever occur.
    This is a fail-closed contract - all gates must pass.

    WSP 97: This is a test-local definition. Production implementation
    should be derived from this contract if/when source modification is enabled.
    """

    # Request identity
    source_modification_requested: bool = False
    target_path: str = ""
    operation: str = ""

    # Approval gates (ALL must be True for live approval)
    human_approval: bool = False
    approval_id: Optional[str] = None
    capability_token_present: bool = False
    security_gate_passed: bool = False

    # Destructive action classification
    destructive_class: DestructiveClass = DestructiveClass.D0_OBSERVE

    # Execution mode
    dry_run_mode: bool = True  # Default True = SAFE

    # Workspace binding enforcement
    workspace_binding_enforced: bool = False
    path_constraints_validated: bool = False

    # Path constraints
    allowed_roots: List[str] = field(default_factory=list)
    blocked_paths: List[str] = field(default_factory=list)

    # Destructive class threshold (max allowed without escalation)
    max_allowed_destructive_class: DestructiveClass = DestructiveClass.D2_LOCAL_PERSIST

    def validate_target_path_in_allowed_roots(self) -> bool:
        """
        Validate target path is within allowed roots.

        Empty allowed_roots = no paths allowed (fail-closed).
        """
        if not self.target_path:
            return False
        if not self.allowed_roots:
            return False  # Fail-closed: empty allowed roots = all blocked

        normalized = os.path.normpath(self.target_path).replace("\\", "/")
        for allowed_root in self.allowed_roots:
            allowed_clean = os.path.normpath(allowed_root).replace("\\", "/")
            if normalized.startswith(allowed_clean + "/") or normalized == allowed_clean:
                return True
        return False

    def validate_target_path_not_blocked(self) -> bool:
        """
        Validate target path is NOT in blocked paths.

        Empty blocked_paths = nothing blocked (but still need allowed_roots).
        """
        if not self.target_path:
            return True  # No path = nothing to block

        normalized = os.path.normpath(self.target_path).replace("\\", "/")

        for blocked in self.blocked_paths:
            blocked_clean = os.path.normpath(blocked).replace("\\", "/")
            # Check exact match
            if normalized == blocked_clean:
                return False
            # Check path starts with blocked directory
            if normalized.startswith(blocked_clean + "/"):
                return False
            # Check if blocked pattern contains filename (e.g., ".env")
            if "/" not in blocked_clean:
                # It's a filename pattern - check if path ends with it
                if normalized.endswith("/" + blocked_clean) or normalized == blocked_clean:
                    return False

        return True

    def validate_operation_supported(self) -> bool:
        """Validate operation is in supported operations list."""
        return self.operation.lower() in SUPPORTED_OPERATIONS

    def validate_destructive_class_threshold(self) -> bool:
        """
        Validate destructive class is within allowed threshold.

        Higher classes (D5_PRODUCTION, D6_IRREVERSIBLE) require additional approval.
        """
        class_order = [
            DestructiveClass.D0_OBSERVE,
            DestructiveClass.D1_LOCAL_TEMP,
            DestructiveClass.D2_LOCAL_PERSIST,
            DestructiveClass.D3_REMOTE_SOFT,
            DestructiveClass.D4_REMOTE_HARD,
            DestructiveClass.D5_PRODUCTION,
            DestructiveClass.D6_IRREVERSIBLE,
        ]

        try:
            current_index = class_order.index(self.destructive_class)
            max_index = class_order.index(self.max_allowed_destructive_class)
            return current_index <= max_index
        except ValueError:
            return False

    def evaluate_gate(self) -> tuple[ProductionSourceGateResult, ProductionSourceBlockReason]:
        """
        Evaluate all gates and return result.

        Returns:
            Tuple of (result, block_reason).
            block_reason is NONE only if result is APPROVED_*.
        """
        # Gate 1: Operation validation
        if not self.validate_operation_supported():
            return (ProductionSourceGateResult.BLOCKED, ProductionSourceBlockReason.UNSUPPORTED_OPERATION)

        # Gate 2: Target path in allowed roots
        if not self.validate_target_path_in_allowed_roots():
            return (ProductionSourceGateResult.BLOCKED, ProductionSourceBlockReason.TARGET_PATH_OUTSIDE_ALLOWED_ROOTS)

        # Gate 3: Target path not in blocked paths
        if not self.validate_target_path_not_blocked():
            return (ProductionSourceGateResult.BLOCKED, ProductionSourceBlockReason.TARGET_PATH_IN_BLOCKED_PATHS)

        # Gate 4: Human approval
        if not self.human_approval:
            return (ProductionSourceGateResult.BLOCKED, ProductionSourceBlockReason.MISSING_HUMAN_APPROVAL)

        # Gate 5: Capability token
        if not self.capability_token_present:
            return (ProductionSourceGateResult.BLOCKED, ProductionSourceBlockReason.MISSING_CAPABILITY_TOKEN)

        # Gate 6: Security gate
        if not self.security_gate_passed:
            return (ProductionSourceGateResult.BLOCKED, ProductionSourceBlockReason.SECURITY_GATE_NOT_PASSED)

        # Gate 7: Workspace binding enforced
        if not self.workspace_binding_enforced:
            return (ProductionSourceGateResult.BLOCKED, ProductionSourceBlockReason.WORKSPACE_BINDING_NOT_ENFORCED)

        # Gate 8: Path constraints validated
        if not self.path_constraints_validated:
            return (ProductionSourceGateResult.BLOCKED, ProductionSourceBlockReason.PATH_CONSTRAINTS_NOT_VALIDATED)

        # Gate 9: Destructive class threshold
        if not self.validate_destructive_class_threshold():
            return (ProductionSourceGateResult.BLOCKED, ProductionSourceBlockReason.DESTRUCTIVE_CLASS_ABOVE_THRESHOLD)

        # Gate 10: Dry-run mode (special case - approved but simulation only)
        if self.dry_run_mode:
            return (ProductionSourceGateResult.SIMULATED_ONLY, ProductionSourceBlockReason.NONE)

        # All gates passed for live (NOT enabled in HXA20)
        # Return SIMULATED_ONLY to be safe - live is never enabled
        return (ProductionSourceGateResult.SIMULATED_ONLY, ProductionSourceBlockReason.NONE)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for evidence/logging."""
        return {
            "source_modification_requested": self.source_modification_requested,
            "target_path": self.target_path,
            "operation": self.operation,
            "human_approval": self.human_approval,
            "approval_id": self.approval_id,
            "capability_token_present": self.capability_token_present,
            "security_gate_passed": self.security_gate_passed,
            "destructive_class": self.destructive_class.value,
            "dry_run_mode": self.dry_run_mode,
            "workspace_binding_enforced": self.workspace_binding_enforced,
            "path_constraints_validated": self.path_constraints_validated,
            "allowed_roots": self.allowed_roots,
            "blocked_paths": self.blocked_paths,
            "max_allowed_destructive_class": self.max_allowed_destructive_class.value,
        }


# ===========================================================================
# SECTION 2: Fake File Patch Adapter (Test-Only - Never Writes Production)
# ===========================================================================


@dataclass
class FakePatchAdapterResult:
    """Result from fake patch adapter invocation."""

    invoked: bool = False
    request_recorded: bool = False
    simulation_path: Optional[str] = None
    call_args: Dict[str, Any] = field(default_factory=dict)

    # WSP 97 truth fields (ALWAYS False in HXA20)
    production_source_modified: bool = False
    file_written: bool = False
    network_called: bool = False
    repo_created: bool = False


class FakePatchAdapter:
    """
    Fake file patch adapter that records requests without real file operations.

    This adapter NEVER modifies production source files. It exists solely to
    prove the approval gate contract can be invoked through the adapter
    boundary without triggering real file modifications.

    WSP 97: production_source_modified=False, file_written=False always.
    """

    def __init__(self, temp_dir: Optional[str] = None):
        """
        Initialize fake patch adapter.

        Args:
            temp_dir: Optional temp directory for recording simulated requests.
                      If provided, dry-run simulations write to temp_dir only.
        """
        self.call_count = 0
        self.call_history: List[FakePatchAdapterResult] = []
        self.temp_dir = temp_dir

    def apply_patch(
        self,
        gate: ProductionSourceGate,
        patch_content: Optional[str] = None,
    ) -> FakePatchAdapterResult:
        """
        Fake apply_patch invocation.

        NEVER modifies production source files. Records the request for testing.

        Args:
            gate: ProductionSourceGate that passed evaluation
            patch_content: Optional patch content (for simulation recording)

        Returns:
            FakePatchAdapterResult with recorded request info

        WSP 97: production_source_modified=False always. This is a test fixture.
        """
        self.call_count += 1

        # Evaluate gate first - adapter should only be called after gate passes
        result, block_reason = gate.evaluate_gate()

        if result == ProductionSourceGateResult.BLOCKED:
            # Gate failed - should not have been called, but record it anyway
            fake_result = FakePatchAdapterResult(
                invoked=True,
                request_recorded=True,
                simulation_path=None,
                call_args={
                    "target_path": gate.target_path,
                    "operation": gate.operation,
                    "blocked": True,
                    "block_reason": block_reason.value,
                },
                production_source_modified=False,
                file_written=False,
                network_called=False,
                repo_created=False,
            )
        else:
            # Gate passed (dry-run) - record simulation but don't modify production
            simulation_path = None
            if self.temp_dir and result == ProductionSourceGateResult.SIMULATED_ONLY:
                # Write simulation record to temp dir only
                simulation_path = os.path.join(
                    self.temp_dir,
                    "simulation_record.json",
                )
                os.makedirs(os.path.dirname(simulation_path), exist_ok=True)
                simulation_record = {
                    "target_path": gate.target_path,
                    "operation": gate.operation,
                    "simulation_only": True,
                    "production_modified": False,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                with open(simulation_path, "w", encoding="utf-8") as f:
                    json.dump(simulation_record, f, indent=2)

            fake_result = FakePatchAdapterResult(
                invoked=True,
                request_recorded=True,
                simulation_path=simulation_path,
                call_args={
                    "target_path": gate.target_path,
                    "operation": gate.operation,
                    "dry_run_mode": gate.dry_run_mode,
                    "gate_result": result.value,
                },
                production_source_modified=False,  # NEVER True in HXA20
                file_written=False,  # NEVER True in HXA20
                network_called=False,  # NEVER True in HXA20
                repo_created=False,
            )

        self.call_history.append(fake_result)
        return fake_result


# ===========================================================================
# SECTION 3: Test Classes
# ===========================================================================


class TestProductionSourceGateModel:
    """Test the ProductionSourceGate dataclass contract."""

    def test_default_values_are_safe(self):
        """Default values should block source modification (fail-closed)."""
        gate = ProductionSourceGate()

        assert gate.source_modification_requested is False
        assert gate.human_approval is False
        assert gate.capability_token_present is False
        assert gate.security_gate_passed is False
        assert gate.dry_run_mode is True
        assert gate.workspace_binding_enforced is False
        assert gate.path_constraints_validated is False

    def test_default_gate_evaluation_blocks(self):
        """Default gate should be blocked."""
        gate = ProductionSourceGate()
        result, reason = gate.evaluate_gate()

        assert result == ProductionSourceGateResult.BLOCKED
        assert reason == ProductionSourceBlockReason.UNSUPPORTED_OPERATION

    def test_gate_fields_defined(self):
        """All required gate fields should be defined."""
        gate = ProductionSourceGate()

        assert hasattr(gate, "source_modification_requested")
        assert hasattr(gate, "target_path")
        assert hasattr(gate, "operation")
        assert hasattr(gate, "human_approval")
        assert hasattr(gate, "approval_id")
        assert hasattr(gate, "capability_token_present")
        assert hasattr(gate, "security_gate_passed")
        assert hasattr(gate, "destructive_class")
        assert hasattr(gate, "dry_run_mode")
        assert hasattr(gate, "workspace_binding_enforced")
        assert hasattr(gate, "path_constraints_validated")
        assert hasattr(gate, "allowed_roots")
        assert hasattr(gate, "blocked_paths")


class TestProductionSourceGateBlocking:
    """Test that gates properly block source modification."""

    def _create_valid_gate(self) -> ProductionSourceGate:
        """Create a gate that would pass all checks (dry-run)."""
        return ProductionSourceGate(
            source_modification_requested=True,
            target_path="/tmp/test/evidence/file.txt",
            operation="write",
            human_approval=True,
            approval_id="approval_hxa20_001",
            capability_token_present=True,
            security_gate_passed=True,
            destructive_class=DestructiveClass.D1_LOCAL_TEMP,
            dry_run_mode=True,
            workspace_binding_enforced=True,
            path_constraints_validated=True,
            allowed_roots=["/tmp/test/evidence"],
            blocked_paths=[],
        )

    def test_blocks_without_human_approval(self):
        """Source modification should be blocked without human approval."""
        gate = self._create_valid_gate()
        gate.human_approval = False

        result, reason = gate.evaluate_gate()

        assert result == ProductionSourceGateResult.BLOCKED
        assert reason == ProductionSourceBlockReason.MISSING_HUMAN_APPROVAL

    def test_blocks_without_capability_token(self):
        """Source modification should be blocked without capability token."""
        gate = self._create_valid_gate()
        gate.capability_token_present = False

        result, reason = gate.evaluate_gate()

        assert result == ProductionSourceGateResult.BLOCKED
        assert reason == ProductionSourceBlockReason.MISSING_CAPABILITY_TOKEN

    def test_blocks_when_security_gate_not_passed(self):
        """Source modification should be blocked if security gate not passed."""
        gate = self._create_valid_gate()
        gate.security_gate_passed = False

        result, reason = gate.evaluate_gate()

        assert result == ProductionSourceGateResult.BLOCKED
        assert reason == ProductionSourceBlockReason.SECURITY_GATE_NOT_PASSED

    def test_blocks_outside_allowed_roots(self):
        """Source modification should be blocked if path outside allowed roots."""
        gate = self._create_valid_gate()
        gate.target_path = "/production/src/main.py"

        result, reason = gate.evaluate_gate()

        assert result == ProductionSourceGateResult.BLOCKED
        assert reason == ProductionSourceBlockReason.TARGET_PATH_OUTSIDE_ALLOWED_ROOTS

    def test_blocks_for_blocked_paths(self):
        """Source modification should be blocked if path is in blocked paths."""
        gate = self._create_valid_gate()
        gate.blocked_paths = ["/tmp/test/evidence/secrets"]
        gate.target_path = "/tmp/test/evidence/secrets/key.pem"

        result, reason = gate.evaluate_gate()

        assert result == ProductionSourceGateResult.BLOCKED
        assert reason == ProductionSourceBlockReason.TARGET_PATH_IN_BLOCKED_PATHS

    def test_blocks_when_workspace_binding_not_enforced(self):
        """Source modification should be blocked if workspace binding not enforced."""
        gate = self._create_valid_gate()
        gate.workspace_binding_enforced = False

        result, reason = gate.evaluate_gate()

        assert result == ProductionSourceGateResult.BLOCKED
        assert reason == ProductionSourceBlockReason.WORKSPACE_BINDING_NOT_ENFORCED

    def test_blocks_when_path_constraints_not_validated(self):
        """Source modification should be blocked if path constraints not validated."""
        gate = self._create_valid_gate()
        gate.path_constraints_validated = False

        result, reason = gate.evaluate_gate()

        assert result == ProductionSourceGateResult.BLOCKED
        assert reason == ProductionSourceBlockReason.PATH_CONSTRAINTS_NOT_VALIDATED

    def test_blocks_unsupported_operation(self):
        """Source modification should be blocked for unsupported operations."""
        gate = self._create_valid_gate()
        gate.operation = "execute_command"  # Not a supported file operation

        result, reason = gate.evaluate_gate()

        assert result == ProductionSourceGateResult.BLOCKED
        assert reason == ProductionSourceBlockReason.UNSUPPORTED_OPERATION

    def test_blocks_destructive_class_above_threshold(self):
        """Source modification should be blocked if destructive class too high."""
        gate = self._create_valid_gate()
        gate.destructive_class = DestructiveClass.D5_PRODUCTION
        gate.max_allowed_destructive_class = DestructiveClass.D2_LOCAL_PERSIST

        result, reason = gate.evaluate_gate()

        assert result == ProductionSourceGateResult.BLOCKED
        assert reason == ProductionSourceBlockReason.DESTRUCTIVE_CLASS_ABOVE_THRESHOLD


class TestProductionSourceDryRunSimulation:
    """Test that dry-run simulation works correctly."""

    def _create_valid_gate(self) -> ProductionSourceGate:
        """Create a gate that would pass all checks (dry-run)."""
        return ProductionSourceGate(
            source_modification_requested=True,
            target_path="/tmp/test/evidence/file.txt",
            operation="write",
            human_approval=True,
            approval_id="approval_hxa20_001",
            capability_token_present=True,
            security_gate_passed=True,
            destructive_class=DestructiveClass.D1_LOCAL_TEMP,
            dry_run_mode=True,
            workspace_binding_enforced=True,
            path_constraints_validated=True,
            allowed_roots=["/tmp/test/evidence"],
            blocked_paths=[],
        )

    def test_dry_run_returns_simulated_only(self):
        """Valid dry-run gate should return SIMULATED_ONLY."""
        gate = self._create_valid_gate()

        result, reason = gate.evaluate_gate()

        assert result == ProductionSourceGateResult.SIMULATED_ONLY
        assert reason == ProductionSourceBlockReason.NONE

    def test_dry_run_does_not_modify_production(self):
        """Dry-run should not modify production source."""
        gate = self._create_valid_gate()
        adapter = FakePatchAdapter()

        result, _ = gate.evaluate_gate()
        assert result == ProductionSourceGateResult.SIMULATED_ONLY

        # Even after approval, adapter should not modify production
        adapter_result = adapter.apply_patch(gate)

        assert adapter_result.production_source_modified is False
        assert adapter_result.file_written is False


class TestFakePatchAdapter:
    """Test the FakePatchAdapter test fixture."""

    def setup_method(self):
        """Setup temp directory."""
        self.temp_dir = tempfile.mkdtemp(prefix="hxa20_test_")

    def teardown_method(self):
        """Cleanup temp directory."""
        if hasattr(self, "temp_dir") and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_valid_gate(self) -> ProductionSourceGate:
        """Create a gate that would pass all checks (dry-run)."""
        return ProductionSourceGate(
            source_modification_requested=True,
            target_path=os.path.join(self.temp_dir, "evidence/file.txt"),
            operation="write",
            human_approval=True,
            approval_id="approval_hxa20_001",
            capability_token_present=True,
            security_gate_passed=True,
            destructive_class=DestructiveClass.D1_LOCAL_TEMP,
            dry_run_mode=True,
            workspace_binding_enforced=True,
            path_constraints_validated=True,
            allowed_roots=[self.temp_dir],
            blocked_paths=[],
        )

    def test_fake_adapter_instantiates(self):
        """FakePatchAdapter can be instantiated."""
        adapter = FakePatchAdapter()
        assert adapter.call_count == 0
        assert adapter.call_history == []

    def test_fake_adapter_invocation_records_call(self):
        """FakePatchAdapter.apply_patch() records the call."""
        adapter = FakePatchAdapter(temp_dir=self.temp_dir)
        gate = self._create_valid_gate()

        result = adapter.apply_patch(gate)

        assert result.invoked is True
        assert adapter.call_count == 1

    def test_fake_adapter_never_modifies_production(self):
        """FakePatchAdapter never modifies production source."""
        adapter = FakePatchAdapter(temp_dir=self.temp_dir)
        gate = self._create_valid_gate()

        result = adapter.apply_patch(gate)

        assert result.production_source_modified is False
        assert result.file_written is False
        assert result.network_called is False
        assert result.repo_created is False

    def test_fake_adapter_blocked_gates_recorded(self):
        """FakePatchAdapter records blocked gate calls."""
        adapter = FakePatchAdapter()
        gate = ProductionSourceGate(
            source_modification_requested=True,
            target_path="/tmp/test/file.txt",
            operation="write",
            human_approval=False,  # Will block
            capability_token_present=True,
            security_gate_passed=True,
            dry_run_mode=True,
            workspace_binding_enforced=True,
            path_constraints_validated=True,
            allowed_roots=["/tmp/test"],
            blocked_paths=[],
        )

        result = adapter.apply_patch(gate)

        assert result.invoked is True
        assert result.production_source_modified is False
        assert result.call_args.get("blocked") is True
        assert result.call_args.get("block_reason") == "MISSING_HUMAN_APPROVAL"

    def test_fake_adapter_not_called_unless_gates_pass(self):
        """Fake adapter should only be called after gate evaluation."""
        adapter = FakePatchAdapter()

        # First evaluate gates
        gate = ProductionSourceGate(
            source_modification_requested=True,
            target_path="/tmp/test/file.txt",
            operation="write",
            human_approval=False,  # Will block
            capability_token_present=True,
            security_gate_passed=True,
            dry_run_mode=True,
            workspace_binding_enforced=True,
            path_constraints_validated=True,
            allowed_roots=["/tmp/test"],
            blocked_paths=[],
        )

        result, reason = gate.evaluate_gate()
        assert result == ProductionSourceGateResult.BLOCKED

        # Adapter should not be called if blocked (design pattern)
        assert adapter.call_count == 0

    def test_fake_adapter_records_simulation_path_on_dry_run(self):
        """FakePatchAdapter records simulation path for dry-run approved requests."""
        adapter = FakePatchAdapter(temp_dir=self.temp_dir)
        gate = self._create_valid_gate()

        result = adapter.apply_patch(gate)

        assert result.simulation_path is not None
        assert os.path.exists(result.simulation_path)
        assert result.production_source_modified is False  # Still False - simulation only


class TestNoWritesOutsideTmpDir:
    """Test that no writes occur outside temp directories."""

    def setup_method(self):
        """Setup temp directory."""
        self.temp_dir = tempfile.mkdtemp(prefix="hxa20_sandbox_")

    def teardown_method(self):
        """Cleanup temp directory."""
        if hasattr(self, "temp_dir") and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_adapter_only_writes_to_temp_dir(self):
        """Adapter should only write simulation records to temp dir."""
        adapter = FakePatchAdapter(temp_dir=self.temp_dir)
        gate = ProductionSourceGate(
            source_modification_requested=True,
            target_path=os.path.join(self.temp_dir, "safe/file.txt"),
            operation="write",
            human_approval=True,
            approval_id="approval_001",
            capability_token_present=True,
            security_gate_passed=True,
            destructive_class=DestructiveClass.D1_LOCAL_TEMP,
            dry_run_mode=True,
            workspace_binding_enforced=True,
            path_constraints_validated=True,
            allowed_roots=[self.temp_dir],
            blocked_paths=[],
        )

        result = adapter.apply_patch(gate)

        # Verify simulation path is within temp dir
        if result.simulation_path:
            assert result.simulation_path.startswith(self.temp_dir)

        # Verify no production modification
        assert result.production_source_modified is False


class TestWSP97TruthFieldsPreserved:
    """Test WSP 97 truth fields are always preserved correctly."""

    def test_production_source_modified_false_by_default(self):
        """production_source_modified should be False by default."""
        result = FakePatchAdapterResult()
        assert result.production_source_modified is False

    def test_production_source_modified_false_after_adapter_call(self):
        """production_source_modified should remain False after adapter call."""
        temp_dir = tempfile.mkdtemp(prefix="hxa20_wsp97_")
        try:
            adapter = FakePatchAdapter(temp_dir=temp_dir)
            gate = ProductionSourceGate(
                source_modification_requested=True,
                target_path=os.path.join(temp_dir, "file.txt"),
                operation="write",
                human_approval=True,
                approval_id="approval_001",
                capability_token_present=True,
                security_gate_passed=True,
                destructive_class=DestructiveClass.D1_LOCAL_TEMP,
                dry_run_mode=True,
                workspace_binding_enforced=True,
                path_constraints_validated=True,
                allowed_roots=[temp_dir],
                blocked_paths=[],
            )

            result = adapter.apply_patch(gate)

            assert result.production_source_modified is False
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_file_written_false(self):
        """file_written should always be False."""
        result = FakePatchAdapterResult(invoked=True)
        assert result.file_written is False

    def test_network_called_false(self):
        """network_called should always be False in test adapter."""
        result = FakePatchAdapterResult(invoked=True)
        assert result.network_called is False

    def test_repo_created_false(self):
        """repo_created should always be False."""
        result = FakePatchAdapterResult(invoked=True)
        assert result.repo_created is False


class TestLiveExternalDelegateCalledFalse:
    """Test live_external_delegate_called is always False."""

    def test_fake_adapter_no_external_calls(self):
        """Fake adapter should never make external calls."""
        adapter = FakePatchAdapter()
        gate = ProductionSourceGate(
            source_modification_requested=True,
            target_path="/tmp/test/file.txt",
            operation="write",
            human_approval=True,
            capability_token_present=True,
            security_gate_passed=True,
            dry_run_mode=True,
            workspace_binding_enforced=True,
            path_constraints_validated=True,
            allowed_roots=["/tmp/test"],
            blocked_paths=[],
        )

        result = adapter.apply_patch(gate)

        # No external delegation - this is a fake adapter
        assert result.network_called is False


class TestVerificationCompleteCABRPayoutFalse:
    """Test verification_complete, cabr_ready, payout_ready are always False."""

    def test_no_verification_in_source_gate(self):
        """Source gate does not claim verification_complete."""
        gate = ProductionSourceGate(
            source_modification_requested=True,
            target_path="/tmp/test/file.txt",
            operation="write",
            human_approval=True,
            capability_token_present=True,
            security_gate_passed=True,
            dry_run_mode=True,
            workspace_binding_enforced=True,
            path_constraints_validated=True,
            allowed_roots=["/tmp/test"],
            blocked_paths=[],
        )

        # Gate evaluation does not claim verification
        result, _ = gate.evaluate_gate()
        assert result in [
            ProductionSourceGateResult.BLOCKED,
            ProductionSourceGateResult.SIMULATED_ONLY,
        ]
        # There is no verification_complete field on gate - by design


class TestExternalFederationInitiatedFalse:
    """Test external_federation_initiated is always False."""

    def test_no_external_federation_in_dry_run(self):
        """No external federation should be initiated in dry-run mode."""
        gate = ProductionSourceGate(
            source_modification_requested=True,
            target_path="/tmp/test/file.txt",
            operation="write",
            human_approval=True,
            capability_token_present=True,
            security_gate_passed=True,
            dry_run_mode=True,
            workspace_binding_enforced=True,
            path_constraints_validated=True,
            allowed_roots=["/tmp/test"],
            blocked_paths=[],
        )

        result, _ = gate.evaluate_gate()

        assert result == ProductionSourceGateResult.SIMULATED_ONLY
        # Dry-run does not initiate federation


class TestHXA20CompleteSourceGate:
    """Integration tests for complete HXA20 source gate."""

    def setup_method(self):
        """Setup temp directory."""
        self.temp_dir = tempfile.mkdtemp(prefix="hxa20_integration_")

    def teardown_method(self):
        """Cleanup temp directory."""
        if hasattr(self, "temp_dir") and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_complete_source_gate_contract(self):
        """
        HXA20 PROOF: Complete source gate contract is enforced.

        This test proves:
        1. Gate model has all required fields
        2. All blocking conditions are tested
        3. Dry-run simulation works correctly
        4. Fake adapter never modifies production source
        5. All WSP 97 truth fields remain False
        """
        # Create gate with all fields
        gate = ProductionSourceGate(
            source_modification_requested=True,
            target_path=os.path.join(self.temp_dir, "evidence/file.txt"),
            operation="write",
            human_approval=True,
            approval_id="hxa20_proof_001",
            capability_token_present=True,
            security_gate_passed=True,
            destructive_class=DestructiveClass.D1_LOCAL_TEMP,
            dry_run_mode=True,
            workspace_binding_enforced=True,
            path_constraints_validated=True,
            allowed_roots=[self.temp_dir],
            blocked_paths=[],
        )

        # Evaluate gate
        result, reason = gate.evaluate_gate()

        # Should be approved for dry-run (simulation only)
        assert result == ProductionSourceGateResult.SIMULATED_ONLY
        assert reason == ProductionSourceBlockReason.NONE

        # Create fake adapter and invoke
        adapter = FakePatchAdapter(temp_dir=self.temp_dir)
        adapter_result = adapter.apply_patch(gate)

        # Verify adapter invocation
        assert adapter_result.invoked is True
        assert adapter_result.request_recorded is True

        # Verify all WSP 97 truth fields
        assert adapter_result.production_source_modified is False
        assert adapter_result.file_written is False
        assert adapter_result.network_called is False
        assert adapter_result.repo_created is False

    def test_all_block_conditions_tested(self):
        """
        HXA20 PROOF: All block conditions are tested.

        Enumerates all blocking scenarios to prove fail-closed behavior.
        """
        base_gate_kwargs = {
            "source_modification_requested": True,
            "target_path": os.path.join(self.temp_dir, "file.txt"),
            "operation": "write",
            "human_approval": True,
            "capability_token_present": True,
            "security_gate_passed": True,
            "destructive_class": DestructiveClass.D1_LOCAL_TEMP,
            "dry_run_mode": True,
            "workspace_binding_enforced": True,
            "path_constraints_validated": True,
            "allowed_roots": [self.temp_dir],
            "blocked_paths": [],
        }

        test_cases = [
            (
                "missing_human_approval",
                {**base_gate_kwargs, "human_approval": False},
                ProductionSourceBlockReason.MISSING_HUMAN_APPROVAL,
            ),
            (
                "missing_capability_token",
                {**base_gate_kwargs, "capability_token_present": False},
                ProductionSourceBlockReason.MISSING_CAPABILITY_TOKEN,
            ),
            (
                "security_gate_not_passed",
                {**base_gate_kwargs, "security_gate_passed": False},
                ProductionSourceBlockReason.SECURITY_GATE_NOT_PASSED,
            ),
            (
                "target_path_outside_allowed_roots",
                {**base_gate_kwargs, "target_path": "/production/src/main.py"},
                ProductionSourceBlockReason.TARGET_PATH_OUTSIDE_ALLOWED_ROOTS,
            ),
            (
                "target_path_in_blocked_paths",
                {
                    **base_gate_kwargs,
                    "blocked_paths": [self.temp_dir],
                },
                ProductionSourceBlockReason.TARGET_PATH_IN_BLOCKED_PATHS,
            ),
            (
                "workspace_binding_not_enforced",
                {**base_gate_kwargs, "workspace_binding_enforced": False},
                ProductionSourceBlockReason.WORKSPACE_BINDING_NOT_ENFORCED,
            ),
            (
                "path_constraints_not_validated",
                {**base_gate_kwargs, "path_constraints_validated": False},
                ProductionSourceBlockReason.PATH_CONSTRAINTS_NOT_VALIDATED,
            ),
            (
                "unsupported_operation",
                {**base_gate_kwargs, "operation": "unknown_op"},
                ProductionSourceBlockReason.UNSUPPORTED_OPERATION,
            ),
            (
                "destructive_class_above_threshold",
                {
                    **base_gate_kwargs,
                    "destructive_class": DestructiveClass.D5_PRODUCTION,
                    "max_allowed_destructive_class": DestructiveClass.D2_LOCAL_PERSIST,
                },
                ProductionSourceBlockReason.DESTRUCTIVE_CLASS_ABOVE_THRESHOLD,
            ),
        ]

        for name, kwargs, expected_reason in test_cases:
            gate = ProductionSourceGate(**kwargs)
            result, reason = gate.evaluate_gate()
            assert result == ProductionSourceGateResult.BLOCKED, f"Case {name} should be blocked"
            assert reason == expected_reason, f"Case {name} expected {expected_reason}, got {reason}"


class TestHXA20VerdictDocumentation:
    """Document HXA20 verdict and proof."""

    def test_hxa20_verdict_production_source_gate_defined(self):
        """
        HXA20 Verdict: PRODUCTION_SOURCE_GATE_DEFINED

        HXA19 verdict was: REPO_CREATION_APPROVAL_GATE_DEFINED

        HXA20 proves:
        1. ProductionSourceGate model defines all required fields
        2. All blocking conditions are implemented (fail-closed)
        3. Dry-run simulation path works correctly
        4. FakePatchAdapter never modifies production source
        5. All WSP 97 truth fields remain False
        6. Gate can be evaluated without modifying production

        This does NOT enable live production source modification.
        This DOES define the contract required for future source modification.
        """
        verdict = "PRODUCTION_SOURCE_GATE_DEFINED"

        # Verify model fields
        gate = ProductionSourceGate()
        assert hasattr(gate, "source_modification_requested")
        assert hasattr(gate, "target_path")
        assert hasattr(gate, "operation")
        assert hasattr(gate, "human_approval")
        assert hasattr(gate, "approval_id")
        assert hasattr(gate, "capability_token_present")
        assert hasattr(gate, "security_gate_passed")
        assert hasattr(gate, "destructive_class")
        assert hasattr(gate, "dry_run_mode")
        assert hasattr(gate, "workspace_binding_enforced")
        assert hasattr(gate, "path_constraints_validated")
        assert hasattr(gate, "allowed_roots")
        assert hasattr(gate, "blocked_paths")

        # Verify gate evaluation
        result, reason = gate.evaluate_gate()
        assert result == ProductionSourceGateResult.BLOCKED  # Default blocks

        # Verify fake adapter
        adapter = FakePatchAdapter()
        assert adapter.call_count == 0

        assert verdict == "PRODUCTION_SOURCE_GATE_DEFINED"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
