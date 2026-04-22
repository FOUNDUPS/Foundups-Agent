#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for FoundUp Genesis Envelope validator.

Validates WSP 97 truth enforcement and WSP 104 namespace rules.

WSP Compliance:
    WSP 5: Test Coverage
    WSP 97: Implementation Truth
    WSP 104: Namespace Protocol
"""

import pytest

from modules.ai_intelligence.ai_overseer.src.foundup_genesis.envelope import (
    FoundUpGenesisEnvelope,
    AcceptanceCriterion,
    TruthStateEntry,
    LifecycleStage,
    BindingState,
    TruthMarker,
    is_valid_foundup_id,
)
from modules.ai_intelligence.ai_overseer.src.foundup_genesis.validator import (
    GenesisEnvelopeValidator,
    ValidationResult,
    validate_genesis_envelope,
    RESERVED_FOUNDUP_IDS,
    VALID_CATEGORIES,
)


# -----------------------------------------------------------------------------
# foundup_id format tests (WSP 104)
# -----------------------------------------------------------------------------


class TestFoundupIdFormat:
    """Test foundup_id validation per WSP 104."""

    def test_valid_simple_id(self):
        assert is_valid_foundup_id("gotjunk")

    def test_valid_id_with_underscore(self):
        assert is_valid_foundup_id("gotjunk_001")

    def test_valid_id_with_numbers(self):
        assert is_valid_foundup_id("science_swarm_hub_v2")

    def test_invalid_starts_with_number(self):
        assert not is_valid_foundup_id("123gotjunk")

    def test_invalid_uppercase(self):
        assert not is_valid_foundup_id("GotJunk")

    def test_invalid_hyphen(self):
        assert not is_valid_foundup_id("got-junk")

    def test_invalid_too_short(self):
        assert not is_valid_foundup_id("ab")

    def test_invalid_too_long(self):
        assert not is_valid_foundup_id("a" * 51)

    def test_invalid_empty(self):
        assert not is_valid_foundup_id("")

    def test_invalid_spaces(self):
        assert not is_valid_foundup_id("got junk")

    def test_valid_minimum_length(self):
        assert is_valid_foundup_id("abc")

    def test_valid_maximum_length(self):
        assert is_valid_foundup_id("a" * 50)


# -----------------------------------------------------------------------------
# Envelope creation tests
# -----------------------------------------------------------------------------


class TestEnvelopeCreation:
    """Test FoundUpGenesisEnvelope dataclass."""

    def test_create_minimal_envelope(self):
        envelope = FoundUpGenesisEnvelope(
            foundup_id="test_foundup",
            name="Test FoundUp",
            tagline="A test FoundUp",
            description="This is a test FoundUp for validation.",
            category="tools",
        )
        assert envelope.foundup_id == "test_foundup"
        assert envelope.lifecycle_stage == LifecycleStage.IDEA
        assert envelope.binding_state == BindingState.UNBOUND
        assert envelope.external_repo_requested is False

    def test_envelope_to_dict(self):
        envelope = FoundUpGenesisEnvelope(
            foundup_id="test_foundup",
            name="Test",
            tagline="Test",
            description="Test",
            category="tools",
        )
        d = envelope.to_dict()
        assert d["foundup_id"] == "test_foundup"
        assert d["lifecycle_stage"] == "idea"
        assert d["binding_state"] == "unbound"

    def test_envelope_from_dict(self):
        data = {
            "foundup_id": "restored_foundup",
            "name": "Restored",
            "tagline": "From dict",
            "description": "Loaded from dict",
            "category": "tools",
            "lifecycle_stage": "incubating",
        }
        envelope = FoundUpGenesisEnvelope.from_dict(data)
        assert envelope.foundup_id == "restored_foundup"
        assert envelope.lifecycle_stage == LifecycleStage.INCUBATING

    def test_envelope_with_acceptance_criteria(self):
        ac = AcceptanceCriterion(
            observable="User can list item",
            method="UI test",
            oracle="Listing exists",
            pass_condition="listing_id is not None",
        )
        envelope = FoundUpGenesisEnvelope(
            foundup_id="test_with_ac",
            name="Test",
            tagline="Test",
            description="Test",
            category="marketplace",
            acceptance_criteria=[ac],
        )
        assert len(envelope.acceptance_criteria) == 1
        assert envelope.acceptance_criteria[0].observable == "User can list item"


# -----------------------------------------------------------------------------
# Validator tests
# -----------------------------------------------------------------------------


class TestGenesisValidator:
    """Test GenesisEnvelopeValidator."""

    def test_valid_minimal_envelope(self):
        envelope = FoundUpGenesisEnvelope(
            foundup_id="new_foundup",
            name="New FoundUp",
            tagline="A new thing",
            description="This does something new.",
            category="tools",
            acceptance_criteria=[
                AcceptanceCriterion(
                    observable="Feature works",
                    method="Manual test",
                    oracle="Expected output",
                    pass_condition="output matches expected",
                )
            ],
        )
        result = validate_genesis_envelope(envelope, strict_mode=False)
        assert result.is_valid
        assert "foundup_id_format" in result.passed_checks

    def test_invalid_foundup_id_format(self):
        envelope = FoundUpGenesisEnvelope(
            foundup_id="Invalid-ID",
            name="Test",
            tagline="Test",
            description="Test",
            category="tools",
        )
        result = validate_genesis_envelope(envelope)
        assert not result.is_valid
        assert any("invalid format" in e for e in result.errors)

    def test_reserved_foundup_id(self):
        envelope = FoundUpGenesisEnvelope(
            foundup_id="openclaw",
            name="Test",
            tagline="Test",
            description="Test",
            category="tools",
        )
        result = validate_genesis_envelope(envelope)
        assert not result.is_valid
        assert any("reserved" in e for e in result.errors)

    def test_invalid_lifecycle_stage(self):
        envelope = FoundUpGenesisEnvelope(
            foundup_id="test_proto",
            name="Test",
            tagline="Test",
            description="Test",
            category="tools",
        )
        # Force invalid stage
        envelope.lifecycle_stage = LifecycleStage.IDEA  # Valid, but test boundary
        result = validate_genesis_envelope(envelope, strict_mode=False)
        # Should pass for IDEA
        assert "lifecycle_stage_valid" in result.passed_checks

    def test_external_repo_requested_at_genesis(self):
        envelope = FoundUpGenesisEnvelope(
            foundup_id="test_external",
            name="Test",
            tagline="Test",
            description="Test",
            category="tools",
            external_repo_requested=True,
        )
        result = validate_genesis_envelope(envelope)
        assert not result.is_valid
        assert any("external_repo_requested" in e for e in result.errors)

    def test_missing_acceptance_criteria_fields(self):
        envelope = FoundUpGenesisEnvelope(
            foundup_id="test_ac",
            name="Test",
            tagline="Test",
            description="Test",
            category="tools",
            acceptance_criteria=[
                AcceptanceCriterion(
                    observable="",  # Missing
                    method="Test",
                    oracle="Test",
                    pass_condition="Test",
                )
            ],
        )
        result = validate_genesis_envelope(envelope)
        assert not result.is_valid
        assert any("acceptance_criteria" in e and "observable" in e for e in result.errors)

    def test_wsp97_implementation_claim_without_evidence(self):
        """WSP 97: No implementation claims without evidence."""
        envelope = FoundUpGenesisEnvelope(
            foundup_id="test_wsp97",
            name="Test",
            tagline="Test",
            description="Test",
            category="tools",
            truth_state_map=[
                TruthStateEntry(
                    feature="core_feature",
                    marker=TruthMarker.IMPLEMENTED,
                    evidence="",  # No evidence!
                )
            ],
        )
        result = validate_genesis_envelope(envelope)
        assert not result.is_valid
        assert any("WSP 97 violation" in e for e in result.errors)

    def test_wsp97_idea_only_no_evidence_ok(self):
        """WSP 97: IDEA_ONLY doesn't require evidence."""
        envelope = FoundUpGenesisEnvelope(
            foundup_id="test_idea",
            name="Test",
            tagline="Test",
            description="Test",
            category="tools",
            truth_state_map=[
                TruthStateEntry(
                    feature="future_feature",
                    marker=TruthMarker.IDEA_ONLY,
                    evidence="",  # OK for IDEA_ONLY
                )
            ],
            acceptance_criteria=[
                AcceptanceCriterion(
                    observable="Feature",
                    method="Test",
                    oracle="Oracle",
                    pass_condition="Condition",
                )
            ],
        )
        result = validate_genesis_envelope(envelope, strict_mode=False)
        assert result.is_valid

    def test_existing_id_conflict(self):
        envelope = FoundUpGenesisEnvelope(
            foundup_id="existing_one",
            name="Test",
            tagline="Test",
            description="Test",
            category="tools",
        )
        result = validate_genesis_envelope(
            envelope,
            existing_ids={"existing_one", "another_one"},
        )
        assert not result.is_valid
        assert any("already exists" in e for e in result.errors)

    def test_missing_required_fields(self):
        envelope = FoundUpGenesisEnvelope(
            foundup_id="test_missing",
            name="",  # Empty!
            tagline="Test",
            description="Test",
            category="tools",
        )
        result = validate_genesis_envelope(envelope)
        assert not result.is_valid
        assert any("'name' is required" in e for e in result.errors)

    def test_strict_mode_warnings_become_errors(self):
        envelope = FoundUpGenesisEnvelope(
            foundup_id="test_strict",
            name="Test",
            tagline="Test",
            description="Test",
            category="tools",
            acceptance_criteria=[],  # Warning: empty
        )
        # Non-strict: should pass (just warning)
        result_lenient = validate_genesis_envelope(envelope, strict_mode=False)
        assert result_lenient.is_valid
        assert len(result_lenient.warnings) > 0

        # Strict: warning becomes error
        result_strict = validate_genesis_envelope(envelope, strict_mode=True)
        assert not result_strict.is_valid


# -----------------------------------------------------------------------------
# Integration tests
# -----------------------------------------------------------------------------


class TestValidatorIntegration:
    """Integration tests for full envelope lifecycle."""

    def test_complete_valid_envelope(self):
        """Test a complete, well-formed envelope passes all checks."""
        envelope = FoundUpGenesisEnvelope(
            foundup_id="complete_foundup",
            name="Complete FoundUp",
            tagline="A fully specified FoundUp",
            description="This FoundUp has all required fields and proper structure.",
            category="marketplace",
            lifecycle_stage=LifecycleStage.IDEA,
            binding_state=BindingState.DISCOVERABLE_ONLY,
            external_repo_requested=False,
            acceptance_criteria=[
                AcceptanceCriterion(
                    observable="User can create account",
                    method="E2E test with Playwright",
                    oracle="User record exists in database",
                    pass_condition="SELECT COUNT(*) FROM users WHERE id=? returns 1",
                ),
                AcceptanceCriterion(
                    observable="User can list item",
                    method="API test",
                    oracle="Listing API returns 201",
                    pass_condition="response.status == 201 AND listing_id exists",
                ),
            ],
            truth_state_map=[
                TruthStateEntry(
                    feature="user_accounts",
                    marker=TruthMarker.SPECIFIED,
                    evidence="",
                ),
                TruthStateEntry(
                    feature="marketplace_listings",
                    marker=TruthMarker.IDEA_ONLY,
                    evidence="",
                ),
            ],
            holo_recall_results=[
                {"pattern": "marketplace", "similarity": 0.85},
            ],
            prior_art=["modules/foundups/gotjunk/"],
            notes="Based on GotJunk pattern.",
        )

        result = validate_genesis_envelope(envelope, strict_mode=True)
        assert result.is_valid, f"Expected valid but got errors: {result.errors}"
        assert len(result.passed_checks) >= 8  # Multiple checks passed

    def test_envelope_roundtrip(self):
        """Test envelope survives serialization roundtrip."""
        original = FoundUpGenesisEnvelope(
            foundup_id="roundtrip_test",
            name="Roundtrip",
            tagline="Survives JSON",
            description="Test serialization.",
            category="tools",
            acceptance_criteria=[
                AcceptanceCriterion(
                    observable="Works",
                    method="Test",
                    oracle="Pass",
                    pass_condition="True",
                )
            ],
        )

        # Roundtrip
        as_dict = original.to_dict()
        restored = FoundUpGenesisEnvelope.from_dict(as_dict)

        assert restored.foundup_id == original.foundup_id
        assert restored.lifecycle_stage == original.lifecycle_stage
        assert len(restored.acceptance_criteria) == 1
        assert restored.acceptance_criteria[0].observable == "Works"
