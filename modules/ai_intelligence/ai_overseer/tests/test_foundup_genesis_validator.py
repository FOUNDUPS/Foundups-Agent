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


# -----------------------------------------------------------------------------
# #823 -- CONTROL / FORMAT CHARACTER REJECTION IN PUBLIC DISPLAY FIELDS
#
# name / tagline / description are PUBLIC display fields. A control char (Cc) or a
# dangerous format char (pinned Cf subset) must be REJECTED -- never sanitized.
# This is the genesis-side line of defense (the intake path rejects earlier, at
# validate_launch_request, BEFORE an envelope is ever constructed). ALL fixtures
# are built from chr(codepoint) so this SOURCE stays pure ASCII (byte-check clean).
# -----------------------------------------------------------------------------


# Representative Unicode category Cc sweep (C0 + DEL + C1) -- codepoints only.
_GV_CC_SWEEP = {
    "NUL_0x00": 0x00,
    "TAB_0x09": 0x09,
    "LF_0x0A": 0x0A,
    "CR_0x0D": 0x0D,
    "ESC_0x1B": 0x1B,
    "DEL_0x7F": 0x7F,
    "NEL_0x85": 0x85,   # C1
    "APC_0x9F": 0x9F,   # C1
}

# The ARCHITECT-pinned dangerous Cf subset -- codepoints only.
_GV_CF_PINNED = {
    "ZWSP_200B": 0x200B,
    "ZWNJ_200C": 0x200C,
    "ZWJ_200D": 0x200D,
    "BOM_FEFF": 0xFEFF,
    "WJ_2060": 0x2060,
    "LRE_202A": 0x202A,
    "RLE_202B": 0x202B,
    "PDF_202C": 0x202C,
    "LRO_202D": 0x202D,
    "RLO_202E": 0x202E,
    "LRI_2066": 0x2066,
    "RLI_2067": 0x2067,
    "FSI_2068": 0x2068,
    "PDI_2069": 0x2069,
}

# The three DISPLAY fields validated by the genesis validator.
_GV_DISPLAY_FIELDS = ["name", "tagline", "description"]

# Negative controls that MUST still be ACCEPTED (Addendum E). chr() keeps source ASCII.
_GV_NEGATIVE_VALUES = [
    "Caf" + chr(0x00E9) + " " + chr(0x00C9) + "tude",   # accented Latin
    chr(0x672A) + chr(0x6765) + " FoundUp",             # CJK "future" + FoundUp
    "O'Hara-Smith (test)",                              # ordinary ASCII punctuation
]


def _envelope_with(field, value):
    """A valid genesis envelope with one display field overridden."""
    fields = {
        "foundup_id": "ctl_char_test",
        "name": "Clean Name",
        "tagline": "Clean tagline",
        "description": "Clean description.",
        "category": "tools",
    }
    fields[field] = value
    return FoundUpGenesisEnvelope(**fields)


class TestDisplayFieldControlChars:
    """#823: control/format chars rejected in name/tagline/description."""

    @pytest.mark.parametrize("char_name,cp", sorted(_GV_CC_SWEEP.items()))
    @pytest.mark.parametrize("field", _GV_DISPLAY_FIELDS)
    def test_cc_control_char_rejected(self, field, char_name, cp):
        env = _envelope_with(field, "Good" + chr(cp) + "Name")
        result = validate_genesis_envelope(env, strict_mode=False)
        assert not result.is_valid, f"{field} with {char_name} not rejected"
        assert any(
            f"{field} contains disallowed control/format character" in e
            for e in result.errors
        )

    @pytest.mark.parametrize("char_name,cp", sorted(_GV_CF_PINNED.items()))
    @pytest.mark.parametrize("field", _GV_DISPLAY_FIELDS)
    def test_cf_format_char_rejected(self, field, char_name, cp):
        env = _envelope_with(field, "Good" + chr(cp) + "Name")
        result = validate_genesis_envelope(env, strict_mode=False)
        assert not result.is_valid, f"{field} with {char_name} not rejected"
        assert any(
            f"{field} contains disallowed control/format character" in e
            for e in result.errors
        )

    def test_newline_rejected_in_description_phase1(self):
        # description is NOT exempt this phase: a newline (LF, Cc) is rejected.
        env = _envelope_with("description", "line one" + chr(0x0A) + "line two")
        result = validate_genesis_envelope(env, strict_mode=False)
        assert not result.is_valid
        assert any(
            "description contains disallowed control/format character" in e
            for e in result.errors
        )

    @pytest.mark.parametrize("field", _GV_DISPLAY_FIELDS)
    @pytest.mark.parametrize("value", _GV_NEGATIVE_VALUES)
    def test_unicode_letters_not_false_positive_rejected(self, field, value):
        # Accented Latin / CJK / ordinary punctuation are NOT Cc/Cf -> accepted.
        env = _envelope_with(field, value)
        result = validate_genesis_envelope(env, strict_mode=False)
        assert result.is_valid, f"{field}={value!r} wrongly rejected: {result.errors}"

    def test_reject_error_never_echoes_raw_control_char(self):
        # SAFE error policy: never echo the raw value, repr(value), or the offending char.
        offender = chr(0x202E)  # RLO
        env = _envelope_with("name", "Good" + offender + "Name")
        result = validate_genesis_envelope(env, strict_mode=False)
        assert not result.is_valid
        for e in result.errors:
            assert offender not in e
            assert "Good" not in e

    def test_plain_space_accepted(self):
        env = _envelope_with("name", "Good Name With Spaces")
        result = validate_genesis_envelope(env, strict_mode=False)
        assert result.is_valid, result.errors
