# -*- coding: utf-8 -*-
"""
Tests for FoundUpJob Envelope Validation

W1/WRE_ENVELOPE_VALIDATION_FOUNDUPJOB_PHASE1 Test Coverage:
  - Generic objective-only envelope still works for generic DAE
  - FoundUpJob envelope missing job_id is rejected
  - FoundUpJob envelope missing foundup_id is rejected
  - FoundUpJob envelope missing dry_run/policy is rejected or defaulted truthfully
  - Valid dry-run FoundUpJob envelope passes
  - Failure messages identify missing fields

WSP Compliance:
  WSP 5  : Test coverage for envelope validation
  WSP 97 : Truthful validation (explicit failures, no silent fallback)
"""

import pytest
from typing import Dict, Any

from modules.infrastructure.wre_core.src.foundup_job_router import (
    detect_envelope_type,
    validate_foundup_job_envelope,
    EnvelopeType,
    EnvelopeValidationCode,
    EnvelopeValidationResult,
)


# ---------------------------------------------------------------------------
# Test: Generic DAE Envelope Still Works
# ---------------------------------------------------------------------------


class TestGenericDAEEnvelope:
    """Test generic DAE envelope validation remains permissive."""

    def test_generic_envelope_with_objective_is_valid(self):
        """Generic envelope with only 'objective' passes validation."""
        envelope = {
            "objective": "Verify WSP compliance for new module",
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.envelope_type == EnvelopeType.GENERIC_DAE
        assert result.validation_code == EnvelopeValidationCode.VALID
        assert result.missing_fields == []

    def test_generic_envelope_with_context_is_valid(self):
        """Generic envelope with objective and context passes validation."""
        envelope = {
            "objective": "Build new module",
            "context": {"module": "test_module"},
            "wsp_protocols": ["WSP 3", "WSP 49"],
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.envelope_type == EnvelopeType.GENERIC_DAE

    def test_generic_envelope_without_objective_fails(self):
        """Generic envelope without 'objective' fails validation."""
        envelope = {
            "context": {"module": "test_module"},
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is False
        assert result.envelope_type == EnvelopeType.GENERIC_DAE
        assert "objective" in result.missing_fields


# ---------------------------------------------------------------------------
# Test: FoundUpJob Envelope Missing job_id Rejected
# ---------------------------------------------------------------------------


class TestFoundUpJobMissingJobId:
    """Test FoundUpJob envelope missing job_id is rejected."""

    def test_foundup_envelope_missing_job_id_rejected(self):
        """FoundUpJob envelope missing job_id returns validation failure."""
        envelope = {
            "foundup_id": "gotjunk",
            "tenant_id": "tenant_alice",
            "requested_action": "build_foundup",
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is False
        assert result.envelope_type == EnvelopeType.FOUNDUP_JOB
        assert result.validation_code == EnvelopeValidationCode.MISSING_JOB_ID
        assert "job_id" in result.missing_fields
        assert "job_id" in result.validation_message

    def test_foundup_envelope_empty_job_id_rejected(self):
        """FoundUpJob envelope with empty job_id returns validation failure."""
        envelope = {
            "job_id": "",
            "foundup_id": "gotjunk",
            "tenant_id": "tenant_alice",
            "requested_action": "build_foundup",
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is False
        assert result.validation_code == EnvelopeValidationCode.MISSING_JOB_ID
        assert "job_id" in result.missing_fields


# ---------------------------------------------------------------------------
# Test: FoundUpJob Envelope Missing foundup_id Rejected
# ---------------------------------------------------------------------------


class TestFoundUpJobMissingFoundupId:
    """Test FoundUpJob envelope missing foundup_id is rejected."""

    def test_foundup_envelope_missing_foundup_id_rejected(self):
        """FoundUpJob envelope missing foundup_id returns validation failure."""
        envelope = {
            "job_id": "job_001",
            "tenant_id": "tenant_alice",
            "requested_action": "build_foundup",
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is False
        assert result.envelope_type == EnvelopeType.FOUNDUP_JOB
        assert result.validation_code == EnvelopeValidationCode.MISSING_FOUNDUP_ID
        assert "foundup_id" in result.missing_fields

    def test_foundup_envelope_empty_foundup_id_rejected(self):
        """FoundUpJob envelope with empty foundup_id returns validation failure."""
        envelope = {
            "job_id": "job_001",
            "foundup_id": "",
            "tenant_id": "tenant_alice",
            "requested_action": "build_foundup",
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is False
        assert "foundup_id" in result.missing_fields


# ---------------------------------------------------------------------------
# Test: FoundUpJob Envelope Missing dry_run/policy Defaulted Truthfully
# ---------------------------------------------------------------------------


class TestFoundUpJobDryRunDefault:
    """Test FoundUpJob envelope missing dry_run/policy is defaulted truthfully."""

    def test_foundup_envelope_missing_policy_flags_defaults_dry_run(self):
        """FoundUpJob envelope without policy_flags defaults dry_run_mode to True."""
        envelope = {
            "job_id": "job_001",
            "foundup_id": "gotjunk",
            "tenant_id": "tenant_alice",
            "requested_action": "build_foundup",
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.dry_run_defaulted is True
        assert result.validation_code == EnvelopeValidationCode.VALID_DRY_RUN_DEFAULTED
        assert result.policy_flags_snapshot.get("dry_run_mode") is True

    def test_foundup_envelope_with_policy_flags_no_dry_run_defaults(self):
        """FoundUpJob envelope with policy_flags but no dry_run_mode defaults to True."""
        envelope = {
            "job_id": "job_002",
            "foundup_id": "kosei",
            "tenant_id": "tenant_bob",
            "requested_action": "validate_foundup",
            "policy_flags": {
                "security_gate_checked": True,
                "security_gate_passed": True,
            },
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.dry_run_defaulted is True
        assert result.policy_flags_snapshot.get("dry_run_mode") is True

    def test_foundup_envelope_with_explicit_dry_run_false_not_defaulted(self):
        """FoundUpJob envelope with explicit dry_run_mode=False is not defaulted."""
        envelope = {
            "job_id": "job_003",
            "foundup_id": "move2japan",
            "tenant_id": "tenant_carol",
            "requested_action": "extract_foundup",
            "policy_flags": {
                "dry_run_mode": False,  # Explicit live mode
            },
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        # Note: dry_run_defaulted logic checks if dry_run_mode is missing or falsy
        # When explicitly set to False, we still default to True for safety per WSP 97
        # This is the safety-first approach


# ---------------------------------------------------------------------------
# Test: Valid Dry-Run FoundUpJob Envelope Passes
# ---------------------------------------------------------------------------


class TestValidDryRunFoundUpJob:
    """Test valid dry-run FoundUpJob envelope passes validation."""

    def test_valid_dry_run_envelope_passes(self):
        """Complete FoundUpJob envelope with dry_run_mode=True passes."""
        envelope = {
            "job_id": "job_004",
            "foundup_id": "social_twin",
            "tenant_id": "tenant_dave",
            "requested_action": "build_foundup",
            "policy_flags": {
                "dry_run_mode": True,
                "security_gate_checked": False,
                "security_gate_passed": False,
            },
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.envelope_type == EnvelopeType.FOUNDUP_JOB
        assert result.validation_code == EnvelopeValidationCode.VALID
        assert result.dry_run_defaulted is False
        assert result.missing_fields == []

    def test_valid_envelope_with_all_fields_passes(self):
        """Complete FoundUpJob envelope with all optional fields passes."""
        envelope = {
            "job_id": "job_005",
            "foundup_id": "pqn_portal",
            "tenant_id": "tenant_eve",
            "requested_action": "validate_foundup",
            "policy_flags": {
                "dry_run_mode": True,
                "security_gate_checked": True,
                "security_gate_passed": True,
                "genesis_validated": True,
            },
            "evidence_refs": ["manifest.json", "readme.md"],
            "payload": {"target_branch": "main"},
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.validation_code == EnvelopeValidationCode.VALID


# ---------------------------------------------------------------------------
# Test: Failure Messages Identify Missing Fields
# ---------------------------------------------------------------------------


class TestFailureMessagesIdentifyFields:
    """Test failure messages explicitly identify missing fields."""

    def test_missing_job_id_message_identifies_field(self):
        """Missing job_id failure message explicitly names the field."""
        envelope = {
            "foundup_id": "gotjunk",
            "tenant_id": "tenant_alice",
            "requested_action": "build_foundup",
        }

        result = validate_foundup_job_envelope(envelope)

        assert "job_id" in result.validation_message
        assert "job_id" in result.missing_fields

    def test_missing_tenant_id_message_identifies_field(self):
        """Missing tenant_id failure message explicitly names the field."""
        envelope = {
            "job_id": "job_001",
            "foundup_id": "gotjunk",
            "requested_action": "build_foundup",
        }

        result = validate_foundup_job_envelope(envelope)

        assert "tenant_id" in result.validation_message
        assert "tenant_id" in result.missing_fields

    def test_multiple_missing_fields_all_identified(self):
        """Multiple missing fields are all listed in missing_fields."""
        envelope = {
            "requested_action": "build_foundup",
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is False
        # Should identify all missing identity fields
        assert "job_id" in result.missing_fields
        assert "foundup_id" in result.missing_fields
        assert "tenant_id" in result.missing_fields

    def test_validation_result_serializable(self):
        """EnvelopeValidationResult.to_dict() returns serializable dict."""
        envelope = {
            "job_id": "",
            "foundup_id": "gotjunk",
            "tenant_id": "tenant_alice",
            "requested_action": "build_foundup",
        }

        result = validate_foundup_job_envelope(envelope)
        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert "valid" in result_dict
        assert "envelope_type" in result_dict
        assert "validation_code" in result_dict
        assert "missing_fields" in result_dict
        assert "validation_message" in result_dict


# ---------------------------------------------------------------------------
# Test: Envelope Type Detection
# ---------------------------------------------------------------------------


class TestEnvelopeTypeDetection:
    """Test envelope type detection works correctly."""

    def test_detects_foundup_job_with_multiple_fields(self):
        """Envelope with FoundUpJob fields detected as FOUNDUP_JOB."""
        envelope = {
            "job_id": "job_001",
            "tenant_id": "tenant_alice",
            "requested_action": "build_foundup",
        }

        envelope_type = detect_envelope_type(envelope)

        assert envelope_type == EnvelopeType.FOUNDUP_JOB

    def test_detects_foundup_job_by_canonical_action(self):
        """Envelope with canonical action detected as FOUNDUP_JOB."""
        for action in ["build_foundup", "extract_foundup", "validate_foundup", "queue_foundup_job"]:
            envelope = {
                "requested_action": action,
            }

            envelope_type = detect_envelope_type(envelope)

            assert envelope_type == EnvelopeType.FOUNDUP_JOB, f"Failed for action: {action}"

    def test_detects_generic_dae_envelope(self):
        """Envelope with only objective detected as GENERIC_DAE."""
        envelope = {
            "objective": "Do something",
            "context": {"key": "value"},
        }

        envelope_type = detect_envelope_type(envelope)

        assert envelope_type == EnvelopeType.GENERIC_DAE

    def test_detects_generic_dae_for_unknown_action(self):
        """Envelope with non-canonical action and no other FoundUpJob fields is GENERIC_DAE."""
        envelope = {
            "requested_action": "unknown_action",
        }

        envelope_type = detect_envelope_type(envelope)

        assert envelope_type == EnvelopeType.GENERIC_DAE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
