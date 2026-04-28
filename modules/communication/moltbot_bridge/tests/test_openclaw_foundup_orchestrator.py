#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for OpenClaw FoundUp Orchestrator — Genesis Validation Gate.

Slice: OC3_GENESIS_VALIDATION_GATE_PHASE1
Worker: W3
"""

import pytest
from datetime import datetime

from modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator import (
    OpenClawFoundUpOrchestrator,
    GenesisGateReason,
    GenesisGateResult,
    get_orchestrator,
    validate_genesis_before_execution,
)


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def orchestrator():
    """Fresh orchestrator instance for each test."""
    return OpenClawFoundUpOrchestrator(strict_mode=True, allow_012_bypass=False)


@pytest.fixture
def orchestrator_with_bypass():
    """Orchestrator with 012 bypass enabled."""
    return OpenClawFoundUpOrchestrator(strict_mode=True, allow_012_bypass=True)


@pytest.fixture
def valid_envelope_data():
    """Minimal valid genesis envelope data."""
    return {
        "foundup_id": "test_foundup",
        "name": "Test FoundUp",
        "tagline": "A test FoundUp for validation",
        "description": "This is a test FoundUp used to validate the genesis gate.",
        "category": "tools",
        "requested_by": "012",
        "lifecycle_stage": "incubating",
        "binding_state": "discoverable_only",
        "external_repo_requested": False,
        "acceptance_criteria": [
            {
                "observable": "Gate validation passes",
                "method": "automated",
                "oracle": "test assertion",
                "pass_condition": "result.allowed == True",
            }
        ],
        "truth_state_map": [
            {
                "feature": "genesis_gate",
                "marker": "SPECIFIED",
                "evidence": "",
            }
        ],
        "holo_recall_results": [],
        "prior_art": [],
        "created_at": datetime.now().timestamp(),
        "created_by": "0102",
        "notes": "Test envelope",
        "is_valid": False,
        "validation_errors": [],
    }


@pytest.fixture
def invalid_envelope_missing_id():
    """Envelope missing foundup_id."""
    return {
        "foundup_id": "",
        "name": "Test FoundUp",
        "tagline": "Missing ID",
        "description": "This envelope has no foundup_id",
        "category": "tools",
        "lifecycle_stage": "incubating",
        "binding_state": "discoverable_only",
        "external_repo_requested": False,
        "acceptance_criteria": [],
        "truth_state_map": [],
    }


@pytest.fixture
def invalid_envelope_bad_lifecycle():
    """Envelope with invalid lifecycle stage for genesis."""
    return {
        "foundup_id": "proto_foundup",
        "name": "Proto FoundUp",
        "tagline": "Invalid lifecycle",
        "description": "This envelope claims proto stage at genesis",
        "category": "tools",
        "lifecycle_stage": "proto",  # Invalid at genesis
        "binding_state": "ready",  # Also invalid at genesis
        "external_repo_requested": False,
        "acceptance_criteria": [],
        "truth_state_map": [],
    }


# -----------------------------------------------------------------------------
# Gate Blocking Tests
# -----------------------------------------------------------------------------


class TestGateBlocking:
    """Tests for gate blocking (invalid envelopes)."""

    def test_blocks_empty_envelope(self, orchestrator):
        """Gate blocks when no envelope data provided."""
        result = orchestrator.validate_genesis_envelope({})
        assert not result.allowed
        assert result.reason == GenesisGateReason.NO_ENVELOPE
        assert len(result.errors) > 0

    def test_blocks_none_envelope(self, orchestrator):
        """Gate blocks when envelope is None."""
        result = orchestrator.validate_genesis_envelope(None)
        assert not result.allowed
        assert result.reason == GenesisGateReason.NO_ENVELOPE

    def test_blocks_missing_foundup_id(self, orchestrator, invalid_envelope_missing_id):
        """Gate blocks when foundup_id is missing or empty."""
        result = orchestrator.validate_genesis_envelope(invalid_envelope_missing_id)
        assert not result.allowed
        # Gate blocks - reason depends on which error classifier matches first
        assert result.reason != GenesisGateReason.GATE_PASSED
        # Verify foundup_id error is in the errors list
        assert any("foundup_id" in err.lower() for err in result.errors)

    def test_blocks_invalid_foundup_id_format(self, orchestrator, valid_envelope_data):
        """Gate blocks when foundup_id doesn't match WSP 104 format."""
        valid_envelope_data["foundup_id"] = "123invalid"  # Can't start with number
        result = orchestrator.validate_genesis_envelope(valid_envelope_data)
        assert not result.allowed
        assert result.reason in (
            GenesisGateReason.FOUNDUP_ID_INVALID,
            GenesisGateReason.ENVELOPE_INVALID,
        )

    def test_blocks_missing_required_fields(self, orchestrator):
        """Gate blocks when required fields are missing."""
        envelope = {
            "foundup_id": "test_foundup",
            # Missing name, tagline, description
            "category": "tools",
            "lifecycle_stage": "incubating",
            "binding_state": "discoverable_only",
        }
        result = orchestrator.validate_genesis_envelope(envelope)
        assert not result.allowed
        # Gate blocks with any validation failure reason
        assert result.reason != GenesisGateReason.GATE_PASSED
        # Verify required field errors are present
        errors_text = " ".join(result.errors).lower()
        assert "name" in errors_text or "tagline" in errors_text or "description" in errors_text


# -----------------------------------------------------------------------------
# Gate Passing Tests
# -----------------------------------------------------------------------------


class TestGatePassing:
    """Tests for gate allowing (valid envelopes)."""

    def test_allows_valid_envelope(self, orchestrator, valid_envelope_data):
        """Gate allows a valid genesis envelope."""
        result = orchestrator.validate_genesis_envelope(valid_envelope_data)
        assert result.allowed
        assert result.reason == GenesisGateReason.GATE_PASSED
        assert result.envelope_summary is not None
        assert result.envelope_summary["foundup_id"] == "test_foundup"

    def test_envelope_summary_populated(self, orchestrator, valid_envelope_data):
        """Gate result includes envelope summary on success."""
        result = orchestrator.validate_genesis_envelope(valid_envelope_data)
        assert result.allowed
        summary = result.envelope_summary
        assert summary["foundup_id"] == "test_foundup"
        assert summary["name"] == "Test FoundUp"
        assert summary["lifecycle_stage"] == "incubating"
        assert summary["is_valid"] is True


# -----------------------------------------------------------------------------
# 012 Bypass Tests
# -----------------------------------------------------------------------------


class TestBypassMode:
    """Tests for 012 emergency bypass."""

    def test_bypass_disabled_by_default(self, orchestrator):
        """Bypass flag has no effect when allow_012_bypass is False."""
        result = orchestrator.validate_genesis_envelope(
            {}, actor_id="012", bypass_012=True
        )
        # Should still block because bypass is disabled
        assert not result.allowed
        assert result.reason == GenesisGateReason.NO_ENVELOPE

    def test_bypass_requires_012_actor(self, orchestrator_with_bypass):
        """Bypass only works for actor_id='012'."""
        result = orchestrator_with_bypass.validate_genesis_envelope(
            {"foundup_id": "test"}, actor_id="openclaw", bypass_012=True
        )
        # Should not bypass for non-012 actor
        assert not result.allowed
        assert result.reason != GenesisGateReason.BYPASS_AUTHORIZED

    def test_bypass_works_for_012(self, orchestrator_with_bypass):
        """Bypass allows 012 to skip validation."""
        result = orchestrator_with_bypass.validate_genesis_envelope(
            {"foundup_id": "emergency_foundup"}, actor_id="012", bypass_012=True
        )
        assert result.allowed
        assert result.reason == GenesisGateReason.BYPASS_AUTHORIZED


# -----------------------------------------------------------------------------
# Gated Execution Tests
# -----------------------------------------------------------------------------


class TestGatedExecution:
    """Tests for gated execution methods (launch, build, promote)."""

    def test_launch_blocked_without_envelope(self, orchestrator):
        """launch_foundup blocks without valid envelope."""
        result = orchestrator.launch_foundup({})
        assert not result["success"]
        assert result["blocked"]
        assert result["action"] == "launch_foundup"
        assert "next_steps" in result

    def test_launch_allowed_with_valid_envelope(self, orchestrator, valid_envelope_data):
        """launch_foundup succeeds with valid envelope."""
        result = orchestrator.launch_foundup(valid_envelope_data)
        assert result["success"]
        assert not result["blocked"]
        assert result["status"] == "GENESIS_VALIDATED_READY_FOR_FAM"

    def test_build_blocked_for_idea_stage(self, orchestrator, valid_envelope_data):
        """build_foundup blocks when lifecycle is 'idea'."""
        valid_envelope_data["lifecycle_stage"] = "idea"
        result = orchestrator.build_foundup(valid_envelope_data)
        assert not result["success"]
        assert result["blocked"]
        assert "LIFECYCLE_TOO_EARLY" in str(result["gate_result"])

    def test_build_allowed_for_incubating(self, orchestrator, valid_envelope_data):
        """build_foundup succeeds when lifecycle is 'incubating'."""
        result = orchestrator.build_foundup(valid_envelope_data)
        assert result["success"]
        assert not result["blocked"]
        assert result["status"] == "GENESIS_VALIDATED_READY_FOR_HERMES"

    def test_promote_blocked_without_valid_envelope(self, orchestrator):
        """promote_lifecycle blocks without valid envelope."""
        result = orchestrator.promote_lifecycle({}, target_stage="soft-proto")
        assert not result["success"]
        assert result["blocked"]
        assert result["action"] == "promote_lifecycle"

    def test_promote_allowed_with_valid_envelope(self, orchestrator, valid_envelope_data):
        """promote_lifecycle succeeds with valid envelope."""
        result = orchestrator.promote_lifecycle(
            valid_envelope_data, target_stage="soft-proto"
        )
        assert result["success"]
        assert not result["blocked"]
        assert result["status"] == "GENESIS_VALIDATED_PROMOTION_READY"


# -----------------------------------------------------------------------------
# Result Serialization Tests
# -----------------------------------------------------------------------------


class TestResultSerialization:
    """Tests for GenesisGateResult serialization."""

    def test_result_to_dict(self, orchestrator, valid_envelope_data):
        """GenesisGateResult.to_dict() produces valid dict."""
        result = orchestrator.validate_genesis_envelope(valid_envelope_data)
        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert "allowed" in result_dict
        assert "reason" in result_dict
        assert "errors" in result_dict
        assert "checked_at" in result_dict

    def test_reason_serializes_to_string(self, orchestrator, valid_envelope_data):
        """Reason code serializes to string value."""
        result = orchestrator.validate_genesis_envelope(valid_envelope_data)
        result_dict = result.to_dict()

        assert result_dict["reason"] == "GATE_PASSED"
        assert isinstance(result_dict["reason"], str)


# -----------------------------------------------------------------------------
# Convenience Function Tests
# -----------------------------------------------------------------------------


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_get_orchestrator_returns_singleton(self):
        """get_orchestrator returns the same instance."""
        orch1 = get_orchestrator()
        orch2 = get_orchestrator()
        assert orch1 is orch2

    def test_validate_genesis_before_execution(self, valid_envelope_data):
        """validate_genesis_before_execution works as expected."""
        result = validate_genesis_before_execution(valid_envelope_data)
        assert result.allowed
        assert result.reason == GenesisGateReason.GATE_PASSED


# -----------------------------------------------------------------------------
# Integration with ai_overseer Tests
# -----------------------------------------------------------------------------


class TestValidatorIntegration:
    """Tests for integration with ai_overseer validator."""

    def test_validator_loaded_on_first_use(self, orchestrator, valid_envelope_data):
        """Validator is lazy-loaded on first validation."""
        assert orchestrator._validator is None
        orchestrator.validate_genesis_envelope(valid_envelope_data)
        # After validation, validator should be loaded (or marked as attempted)
        assert orchestrator._validator_loaded

    def test_handles_missing_validator_gracefully(self, orchestrator, monkeypatch):
        """Gate handles missing validator module gracefully."""
        # Simulate import failure by breaking the import
        def mock_get_validator():
            raise ImportError("Simulated import failure")

        monkeypatch.setattr(orchestrator, "_get_validator", lambda: None)
        monkeypatch.setattr(orchestrator, "_validator_loaded", True)

        result = orchestrator.validate_genesis_envelope({"foundup_id": "test"})
        assert not result.allowed
        assert result.reason == GenesisGateReason.VALIDATOR_UNAVAILABLE
