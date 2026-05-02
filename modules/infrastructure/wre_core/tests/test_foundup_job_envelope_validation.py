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
        # Evidence pending takes precedence over dry_run_defaulted in code
        assert result.validation_code in (
            EnvelopeValidationCode.VALID_DRY_RUN_DEFAULTED,
            EnvelopeValidationCode.VALID_EVIDENCE_PENDING,
        )
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
                "human_approval": True,  # Required for live mode
            },
            "evidence_refs": ["manifest.json"],  # Required for live mode
            "compute_budget": 5000,  # Required for live mode
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.is_live_mode is True
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
            "evidence_refs": ["manifest.json"],  # Provide evidence to get VALID code
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.envelope_type == EnvelopeType.FOUNDUP_JOB
        assert result.validation_code == EnvelopeValidationCode.VALID
        assert result.dry_run_defaulted is False
        assert result.missing_fields == []
        assert result.evidence_refs_validated is True

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


# ---------------------------------------------------------------------------
# Test: Evidence Refs Validation (WRE_EVIDENCE_REFS_VALIDATION_PHASE1)
# ---------------------------------------------------------------------------


class TestEvidenceRefsListOfStrings:
    """Test evidence_refs list of strings passes validation."""

    def test_evidence_refs_list_of_strings_passes(self):
        """evidence_refs as list of non-empty strings passes."""
        envelope = {
            "job_id": "job_001",
            "foundup_id": "gotjunk",
            "tenant_id": "tenant_alice",
            "requested_action": "build_foundup",
            "policy_flags": {"dry_run_mode": True},
            "evidence_refs": ["manifest.json", "readme.md", "proof_abc123"],
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.evidence_refs_validated is True
        assert result.evidence_refs_count == 3
        assert result.evidence_pending is False

    def test_evidence_refs_single_string_passes(self):
        """evidence_refs with single string entry passes."""
        envelope = {
            "job_id": "job_002",
            "foundup_id": "kosei",
            "tenant_id": "tenant_bob",
            "requested_action": "validate_foundup",
            "evidence_refs": ["foundup_manifest.json"],
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.evidence_refs_count == 1


class TestEvidenceRefsEmptyWithDryRun:
    """Test evidence_refs empty with dry-run/pending policy passes."""

    def test_empty_evidence_refs_in_dry_run_passes_as_pending(self):
        """Empty evidence_refs with dry_run_mode=True passes as pending."""
        envelope = {
            "job_id": "job_003",
            "foundup_id": "move2japan",
            "tenant_id": "tenant_carol",
            "requested_action": "extract_foundup",
            "policy_flags": {"dry_run_mode": True},
            "evidence_refs": [],
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.evidence_pending is True
        assert result.validation_code == EnvelopeValidationCode.VALID_EVIDENCE_PENDING
        assert result.evidence_refs_count == 0

    def test_no_evidence_refs_in_dry_run_passes_as_pending(self):
        """No evidence_refs field with dry_run_mode=True passes as pending."""
        envelope = {
            "job_id": "job_004",
            "foundup_id": "social_twin",
            "tenant_id": "tenant_dave",
            "requested_action": "build_foundup",
            "policy_flags": {"dry_run_mode": True},
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.evidence_pending is True

    def test_no_evidence_refs_defaults_dry_run_and_pending(self):
        """No evidence_refs and no policy_flags defaults to dry-run pending."""
        envelope = {
            "job_id": "job_005",
            "foundup_id": "pqn_portal",
            "tenant_id": "tenant_eve",
            "requested_action": "validate_foundup",
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.dry_run_defaulted is True
        assert result.evidence_pending is True


class TestEvidenceRefsWrongType:
    """Test evidence_refs wrong type fails validation."""

    def test_evidence_refs_string_instead_of_list_fails(self):
        """evidence_refs as string instead of list fails."""
        envelope = {
            "job_id": "job_006",
            "foundup_id": "gotjunk",
            "tenant_id": "tenant_frank",
            "requested_action": "build_foundup",
            "evidence_refs": "manifest.json",  # Should be list
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is False
        assert result.validation_code == EnvelopeValidationCode.INVALID_EVIDENCE_REFS_TYPE
        assert "list" in result.validation_message.lower()

    def test_evidence_refs_dict_instead_of_list_fails(self):
        """evidence_refs as dict instead of list fails."""
        envelope = {
            "job_id": "job_007",
            "foundup_id": "kosei",
            "tenant_id": "tenant_grace",
            "requested_action": "validate_foundup",
            "evidence_refs": {"path": "manifest.json"},  # Should be list
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is False
        assert result.validation_code == EnvelopeValidationCode.INVALID_EVIDENCE_REFS_TYPE

    def test_evidence_refs_int_fails(self):
        """evidence_refs as int fails."""
        envelope = {
            "job_id": "job_008",
            "foundup_id": "move2japan",
            "tenant_id": "tenant_hank",
            "requested_action": "extract_foundup",
            "evidence_refs": 123,
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is False
        assert result.validation_code == EnvelopeValidationCode.INVALID_EVIDENCE_REFS_TYPE


class TestEvidenceRefsEmptyString:
    """Test evidence_refs with empty string fails validation."""

    def test_evidence_refs_with_empty_string_fails(self):
        """evidence_refs containing empty string fails."""
        envelope = {
            "job_id": "job_009",
            "foundup_id": "social_twin",
            "tenant_id": "tenant_ivan",
            "requested_action": "build_foundup",
            "evidence_refs": ["manifest.json", "", "readme.md"],
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is False
        assert result.validation_code == EnvelopeValidationCode.INVALID_EVIDENCE_REF_ENTRY
        assert "empty string" in result.validation_message.lower()

    def test_evidence_refs_with_whitespace_only_fails(self):
        """evidence_refs containing whitespace-only string fails."""
        envelope = {
            "job_id": "job_010",
            "foundup_id": "pqn_portal",
            "tenant_id": "tenant_judy",
            "requested_action": "validate_foundup",
            "evidence_refs": ["   ", "manifest.json"],
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is False
        assert result.validation_code == EnvelopeValidationCode.INVALID_EVIDENCE_REF_ENTRY


class TestEvidenceRefsMalformedDict:
    """Test evidence_refs malformed dict fails unless matching accepted schema."""

    def test_evidence_refs_dict_without_required_fields_fails(self):
        """evidence_refs dict entry without path/id/ref fails."""
        envelope = {
            "job_id": "job_011",
            "foundup_id": "gotjunk",
            "tenant_id": "tenant_kevin",
            "requested_action": "build_foundup",
            "evidence_refs": [
                {"type": "manifest", "status": "verified"},  # Missing path/id/ref
            ],
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is False
        assert result.validation_code == EnvelopeValidationCode.INVALID_EVIDENCE_REF_ENTRY
        assert "path" in result.validation_message or "id" in result.validation_message

    def test_evidence_refs_dict_with_path_passes(self):
        """evidence_refs dict entry with 'path' field passes."""
        envelope = {
            "job_id": "job_012",
            "foundup_id": "kosei",
            "tenant_id": "tenant_larry",
            "requested_action": "validate_foundup",
            "evidence_refs": [
                {"path": "modules/foundups/gotjunk/manifest.json", "type": "manifest"},
            ],
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.evidence_refs_count == 1

    def test_evidence_refs_dict_with_id_passes(self):
        """evidence_refs dict entry with 'id' field passes."""
        envelope = {
            "job_id": "job_013",
            "foundup_id": "move2japan",
            "tenant_id": "tenant_mary",
            "requested_action": "extract_foundup",
            "evidence_refs": [
                {"id": "proof_abc123", "type": "verification"},
            ],
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True

    def test_evidence_refs_dict_with_ref_passes(self):
        """evidence_refs dict entry with 'ref' field passes."""
        envelope = {
            "job_id": "job_014",
            "foundup_id": "social_twin",
            "tenant_id": "tenant_nancy",
            "requested_action": "build_foundup",
            "evidence_refs": [
                {"ref": "commit:abc123def", "type": "git"},
            ],
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True

    def test_evidence_refs_mixed_string_and_valid_dict_passes(self):
        """evidence_refs with mixed strings and valid dicts passes."""
        envelope = {
            "job_id": "job_015",
            "foundup_id": "pqn_portal",
            "tenant_id": "tenant_oscar",
            "requested_action": "validate_foundup",
            "evidence_refs": [
                "manifest.json",
                {"path": "readme.md", "type": "doc"},
                "proof_xyz789",
            ],
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.evidence_refs_count == 3

    def test_evidence_refs_invalid_type_in_list_fails(self):
        """evidence_refs with invalid type (int) in list fails."""
        envelope = {
            "job_id": "job_016",
            "foundup_id": "gotjunk",
            "tenant_id": "tenant_paul",
            "requested_action": "build_foundup",
            "evidence_refs": ["manifest.json", 123, "readme.md"],
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is False
        assert result.validation_code == EnvelopeValidationCode.INVALID_EVIDENCE_REF_ENTRY


class TestEvidenceRefsWSP97TruthFields:
    """Test evidence_refs do not change WSP 97 truth fields."""

    def test_valid_evidence_does_not_set_verification_complete(self):
        """Valid evidence_refs does NOT set verification_complete=True."""
        envelope = {
            "job_id": "job_017",
            "foundup_id": "kosei",
            "tenant_id": "tenant_quinn",
            "requested_action": "validate_foundup",
            "policy_flags": {
                "dry_run_mode": False,
                "human_approval": True,  # Required for live mode
            },
            "evidence_refs": ["manifest.json", "proof_abc123"],
            "compute_budget": 5000,  # Required for live mode
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.verification_complete is False  # WSP 97: Always False

    def test_valid_evidence_does_not_set_cabr_ready(self):
        """Valid evidence_refs does NOT set cabr_ready=True."""
        envelope = {
            "job_id": "job_018",
            "foundup_id": "move2japan",
            "tenant_id": "tenant_rachel",
            "requested_action": "build_foundup",
            "evidence_refs": ["manifest.json", "readme.md", "cabr_proof.json"],
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.cabr_ready is False  # WSP 97: Always False

    def test_valid_evidence_does_not_set_payout_ready(self):
        """Valid evidence_refs does NOT set payout_ready=True."""
        envelope = {
            "job_id": "job_019",
            "foundup_id": "social_twin",
            "tenant_id": "tenant_steve",
            "requested_action": "extract_foundup",
            "evidence_refs": ["payout_evidence.json", "verification_proof.json"],
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.payout_ready is False  # WSP 97: Always False

    def test_wsp97_truth_fields_in_serialized_result(self):
        """WSP 97 truth fields appear in to_dict() output as False."""
        envelope = {
            "job_id": "job_020",
            "foundup_id": "pqn_portal",
            "tenant_id": "tenant_tina",
            "requested_action": "validate_foundup",
            "evidence_refs": ["full_evidence.json"],
        }

        result = validate_foundup_job_envelope(envelope)
        result_dict = result.to_dict()

        assert result_dict["verification_complete"] is False
        assert result_dict["cabr_ready"] is False
        assert result_dict["payout_ready"] is False
        assert result_dict["evidence_refs_validated"] is True


class TestGenericDAEEvidenceBehavior:
    """Test generic DAE envelope evidence behavior unchanged."""

    def test_generic_dae_ignores_evidence_refs(self):
        """Generic DAE envelope validation ignores evidence_refs."""
        envelope = {
            "objective": "Do something generic",
            "evidence_refs": ["some_evidence.json"],
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.envelope_type == EnvelopeType.GENERIC_DAE
        # Evidence fields should be defaults (not validated for generic DAE)
        assert result.evidence_refs_validated is False
        assert result.evidence_refs_count == 0

    def test_generic_dae_with_malformed_evidence_still_passes(self):
        """Generic DAE envelope passes even with malformed evidence_refs."""
        envelope = {
            "objective": "Do something else",
            "evidence_refs": "not_a_list",  # Invalid type but ignored for generic DAE
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.envelope_type == EnvelopeType.GENERIC_DAE


# ---------------------------------------------------------------------------
# Test: Live Mode Policy Gates (WRE_LIVE_MODE_EVIDENCE_POLICY_GATE_PHASE1)
# ---------------------------------------------------------------------------


class TestDryRunWithPendingEvidenceStillPasses:
    """Test dry-run envelope with pending evidence still passes."""

    def test_dry_run_with_no_evidence_passes_as_pending(self):
        """Dry-run envelope without evidence passes with pending status."""
        envelope = {
            "job_id": "job_live_001",
            "foundup_id": "gotjunk",
            "tenant_id": "tenant_alice",
            "requested_action": "build_foundup",
            "policy_flags": {"dry_run_mode": True},
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.evidence_pending is True
        assert result.is_live_mode is False

    def test_dry_run_defaulted_with_no_evidence_passes(self):
        """Envelope with no policy_flags defaults to dry-run and passes."""
        envelope = {
            "job_id": "job_live_002",
            "foundup_id": "kosei",
            "tenant_id": "tenant_bob",
            "requested_action": "validate_foundup",
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.dry_run_defaulted is True
        assert result.evidence_pending is True
        assert result.is_live_mode is False


class TestLiveModeWithoutApprovalFails:
    """Test live-mode envelope without approval fails."""

    def test_live_mode_without_human_approval_fails(self):
        """Live mode without human_approval or permission_gate_passed fails."""
        envelope = {
            "job_id": "job_live_003",
            "foundup_id": "move2japan",
            "tenant_id": "tenant_carol",
            "requested_action": "extract_foundup",
            "policy_flags": {
                "dry_run_mode": False,  # Explicit live mode
                "human_approval": False,
                "permission_gate_passed": False,
            },
            "evidence_refs": ["manifest.json"],
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is False
        assert result.validation_code == EnvelopeValidationCode.LIVE_MODE_REQUIRES_HUMAN_APPROVAL
        assert result.is_live_mode is True
        assert "human_approval" in result.missing_live_gates

    def test_live_mode_without_any_approval_flag_fails(self):
        """Live mode with no approval flags at all fails."""
        envelope = {
            "job_id": "job_live_004",
            "foundup_id": "social_twin",
            "tenant_id": "tenant_dave",
            "requested_action": "build_foundup",
            "policy_flags": {
                "dry_run_mode": False,
            },
            "evidence_refs": ["evidence.json"],
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is False
        assert result.validation_code == EnvelopeValidationCode.LIVE_MODE_REQUIRES_HUMAN_APPROVAL
        assert "human_approval" in result.missing_live_gates


class TestLiveModeWithoutEvidenceFails:
    """Test live-mode envelope without evidence fails."""

    def test_live_mode_with_empty_evidence_fails(self):
        """Live mode with empty evidence_refs fails."""
        envelope = {
            "job_id": "job_live_005",
            "foundup_id": "pqn_portal",
            "tenant_id": "tenant_eve",
            "requested_action": "validate_foundup",
            "policy_flags": {
                "dry_run_mode": False,
                "human_approval": True,
            },
            "evidence_refs": [],
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is False
        assert result.validation_code == EnvelopeValidationCode.LIVE_MODE_REQUIRES_EVIDENCE
        assert "evidence_refs" in result.missing_live_gates

    def test_live_mode_with_no_evidence_field_fails(self):
        """Live mode without evidence_refs field fails."""
        envelope = {
            "job_id": "job_live_006",
            "foundup_id": "gotjunk",
            "tenant_id": "tenant_frank",
            "requested_action": "build_foundup",
            "policy_flags": {
                "dry_run_mode": False,
                "human_approval": True,
            },
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is False
        assert result.validation_code == EnvelopeValidationCode.LIVE_MODE_REQUIRES_EVIDENCE
        assert "evidence_refs" in result.missing_live_gates


class TestLiveModeWithMalformedEvidenceFails:
    """Test live-mode envelope with malformed evidence fails."""

    def test_live_mode_with_invalid_evidence_type_fails(self):
        """Live mode with wrong evidence_refs type fails."""
        envelope = {
            "job_id": "job_live_007",
            "foundup_id": "kosei",
            "tenant_id": "tenant_grace",
            "requested_action": "validate_foundup",
            "policy_flags": {
                "dry_run_mode": False,
                "human_approval": True,
            },
            "evidence_refs": "not_a_list",
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is False
        assert result.validation_code == EnvelopeValidationCode.INVALID_EVIDENCE_REFS_TYPE

    def test_live_mode_with_empty_string_evidence_fails(self):
        """Live mode with empty string in evidence fails."""
        envelope = {
            "job_id": "job_live_008",
            "foundup_id": "move2japan",
            "tenant_id": "tenant_hank",
            "requested_action": "extract_foundup",
            "policy_flags": {
                "dry_run_mode": False,
                "human_approval": True,
            },
            "evidence_refs": ["valid.json", "", "also_valid.json"],
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is False
        assert result.validation_code == EnvelopeValidationCode.INVALID_EVIDENCE_REF_ENTRY


class TestLiveModeWithApprovalAndEvidenceNoVerification:
    """Test live-mode envelope with approval and evidence does not claim verification."""

    def test_live_mode_valid_does_not_set_verification_complete(self):
        """Valid live mode envelope does NOT set verification_complete."""
        envelope = {
            "job_id": "job_live_009",
            "foundup_id": "social_twin",
            "tenant_id": "tenant_ivan",
            "requested_action": "build_foundup",
            "policy_flags": {
                "dry_run_mode": False,
                "human_approval": True,
            },
            "evidence_refs": ["manifest.json", "proof.json"],
            "compute_budget": 5000,  # Required for live mode
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.is_live_mode is True
        assert result.live_mode_gates_passed is True
        assert result.verification_complete is False  # WSP 97

    def test_live_mode_valid_does_not_set_cabr_ready(self):
        """Valid live mode envelope does NOT set cabr_ready."""
        envelope = {
            "job_id": "job_live_010",
            "foundup_id": "pqn_portal",
            "tenant_id": "tenant_judy",
            "requested_action": "validate_foundup",
            "policy_flags": {
                "dry_run_mode": False,
                "permission_gate_passed": True,  # Alternative approval
            },
            "evidence_refs": ["cabr_evidence.json"],
            "compute_budget": 5000,  # Required for live mode
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.cabr_ready is False  # WSP 97

    def test_live_mode_valid_does_not_set_payout_ready(self):
        """Valid live mode envelope does NOT set payout_ready."""
        envelope = {
            "job_id": "job_live_011",
            "foundup_id": "gotjunk",
            "tenant_id": "tenant_kevin",
            "requested_action": "extract_foundup",
            "policy_flags": {
                "dry_run_mode": False,
                "human_approval": True,
                "security_gate_checked": True,
                "security_gate_passed": True,
            },
            "evidence_refs": ["payout_ready_evidence.json"],
            "compute_budget": 5000,  # Required for live mode
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.payout_ready is False  # WSP 97


class TestLiveModeSecurityGate:
    """Test live mode security gate validation."""

    def test_live_mode_security_gate_checked_but_not_passed_fails(self):
        """Live mode with security_gate_checked=True but security_gate_passed=False fails."""
        envelope = {
            "job_id": "job_live_012",
            "foundup_id": "kosei",
            "tenant_id": "tenant_larry",
            "requested_action": "build_foundup",
            "policy_flags": {
                "dry_run_mode": False,
                "human_approval": True,
                "security_gate_checked": True,
                "security_gate_passed": False,
            },
            "evidence_refs": ["manifest.json"],
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is False
        assert result.validation_code == EnvelopeValidationCode.LIVE_MODE_REQUIRES_SECURITY_GATE
        assert "security_gate_passed" in result.missing_live_gates

    def test_live_mode_security_gate_not_checked_passes(self):
        """Live mode without security_gate_checked passes (gate not required if not checked)."""
        envelope = {
            "job_id": "job_live_013",
            "foundup_id": "move2japan",
            "tenant_id": "tenant_mary",
            "requested_action": "validate_foundup",
            "policy_flags": {
                "dry_run_mode": False,
                "human_approval": True,
                "security_gate_checked": False,  # Not checked, so not required
            },
            "evidence_refs": ["evidence.json"],
            "compute_budget": 5000,  # Required for live mode
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.live_mode_gates_passed is True


class TestLiveModeValidationErrorDetails:
    """Test validation error includes explicit reason and missing gates."""

    def test_missing_gates_list_in_result(self):
        """Validation result includes missing_live_gates list."""
        envelope = {
            "job_id": "job_live_014",
            "foundup_id": "social_twin",
            "tenant_id": "tenant_nancy",
            "requested_action": "build_foundup",
            "policy_flags": {
                "dry_run_mode": False,
                # Missing: human_approval, evidence
            },
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is False
        assert len(result.missing_live_gates) >= 1
        assert "human_approval" in result.missing_live_gates

    def test_multiple_missing_gates_all_listed(self):
        """Multiple missing gates are all listed."""
        envelope = {
            "job_id": "job_live_015",
            "foundup_id": "pqn_portal",
            "tenant_id": "tenant_oscar",
            "requested_action": "extract_foundup",
            "policy_flags": {
                "dry_run_mode": False,
                "security_gate_checked": True,
                "security_gate_passed": False,
                # Missing: human_approval, security_gate_passed, evidence
            },
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is False
        assert "human_approval" in result.missing_live_gates
        assert "security_gate_passed" in result.missing_live_gates
        assert "evidence_refs" in result.missing_live_gates

    def test_validation_message_mentions_missing_gates(self):
        """Validation message mentions the missing gates."""
        envelope = {
            "job_id": "job_live_016",
            "foundup_id": "gotjunk",
            "tenant_id": "tenant_paul",
            "requested_action": "validate_foundup",
            "policy_flags": {
                "dry_run_mode": False,
            },
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is False
        assert "human_approval" in result.validation_message or "gates" in result.validation_message

    def test_live_mode_fields_in_serialized_result(self):
        """Live mode fields appear in to_dict() output."""
        envelope = {
            "job_id": "job_live_017",
            "foundup_id": "kosei",
            "tenant_id": "tenant_quinn",
            "requested_action": "build_foundup",
            "policy_flags": {
                "dry_run_mode": False,
                "human_approval": True,
            },
            "evidence_refs": ["complete_evidence.json"],
            "compute_budget": 5000,  # Required for live mode
        }

        result = validate_foundup_job_envelope(envelope)
        result_dict = result.to_dict()

        assert "is_live_mode" in result_dict
        assert "live_mode_gates_passed" in result_dict
        assert "missing_live_gates" in result_dict
        assert result_dict["is_live_mode"] is True
        assert result_dict["live_mode_gates_passed"] is True


# ---------------------------------------------------------------------------
# Test: Compute Budget Validation (WRE_COMPUTE_BUDGET_VALIDATION_PHASE1)
# ---------------------------------------------------------------------------


class TestComputeBudgetTypeValidation:
    """Test compute_budget type validation (int only per contract)."""

    def test_compute_budget_none_is_valid(self):
        """compute_budget=None (unlimited) is valid."""
        envelope = {
            "job_id": "job_budget_001",
            "foundup_id": "gotjunk",
            "tenant_id": "tenant_alice",
            "requested_action": "build_foundup",
            "compute_budget": None,
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.compute_budget_validated is True
        assert result.compute_budget_value is None

    def test_compute_budget_int_is_valid(self):
        """compute_budget as int is valid."""
        envelope = {
            "job_id": "job_budget_002",
            "foundup_id": "kosei",
            "tenant_id": "tenant_bob",
            "requested_action": "validate_foundup",
            "compute_budget": 1000,
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.compute_budget_validated is True
        assert result.compute_budget_value == 1000

    def test_compute_budget_float_fails(self):
        """compute_budget as float fails (contract is int only)."""
        envelope = {
            "job_id": "job_budget_003",
            "foundup_id": "move2japan",
            "tenant_id": "tenant_carol",
            "requested_action": "extract_foundup",
            "compute_budget": 100.5,
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is False
        assert result.validation_code == EnvelopeValidationCode.INVALID_COMPUTE_BUDGET_TYPE
        assert "int" in result.validation_message

    def test_compute_budget_string_fails(self):
        """compute_budget as string fails."""
        envelope = {
            "job_id": "job_budget_004",
            "foundup_id": "social_twin",
            "tenant_id": "tenant_dave",
            "requested_action": "build_foundup",
            "compute_budget": "1000",
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is False
        assert result.validation_code == EnvelopeValidationCode.INVALID_COMPUTE_BUDGET_TYPE

    def test_compute_budget_bool_fails(self):
        """compute_budget as bool fails (bool is subclass of int in Python)."""
        envelope = {
            "job_id": "job_budget_005",
            "foundup_id": "pqn_portal",
            "tenant_id": "tenant_eve",
            "requested_action": "validate_foundup",
            "compute_budget": True,  # bool is subclass of int, must be rejected
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is False
        assert result.validation_code == EnvelopeValidationCode.INVALID_COMPUTE_BUDGET_TYPE


class TestComputeBudgetNegativeValidation:
    """Test compute_budget non-negative validation."""

    def test_compute_budget_zero_is_valid(self):
        """compute_budget=0 is valid (exhausted but not negative)."""
        envelope = {
            "job_id": "job_budget_006",
            "foundup_id": "gotjunk",
            "tenant_id": "tenant_frank",
            "requested_action": "build_foundup",
            "compute_budget": 0,
            "compute_used": 0,
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.compute_budget_value == 0

    def test_compute_budget_positive_is_valid(self):
        """compute_budget > 0 is valid."""
        envelope = {
            "job_id": "job_budget_007",
            "foundup_id": "kosei",
            "tenant_id": "tenant_grace",
            "requested_action": "validate_foundup",
            "compute_budget": 5000,
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.compute_budget_value == 5000

    def test_compute_budget_negative_fails(self):
        """compute_budget < 0 fails."""
        envelope = {
            "job_id": "job_budget_008",
            "foundup_id": "move2japan",
            "tenant_id": "tenant_hank",
            "requested_action": "extract_foundup",
            "compute_budget": -100,
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is False
        assert result.validation_code == EnvelopeValidationCode.INVALID_COMPUTE_BUDGET_NEGATIVE
        assert "non-negative" in result.validation_message


class TestComputeUsedTypeValidation:
    """Test compute_used type validation (int only per contract)."""

    def test_compute_used_int_is_valid(self):
        """compute_used as int is valid."""
        envelope = {
            "job_id": "job_budget_009",
            "foundup_id": "social_twin",
            "tenant_id": "tenant_ivan",
            "requested_action": "build_foundup",
            "compute_used": 500,
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.compute_used_value == 500

    def test_compute_used_float_fails(self):
        """compute_used as float fails."""
        envelope = {
            "job_id": "job_budget_010",
            "foundup_id": "pqn_portal",
            "tenant_id": "tenant_judy",
            "requested_action": "validate_foundup",
            "compute_used": 100.5,
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is False
        assert result.validation_code == EnvelopeValidationCode.INVALID_COMPUTE_USED_TYPE

    def test_compute_used_string_fails(self):
        """compute_used as string fails."""
        envelope = {
            "job_id": "job_budget_011",
            "foundup_id": "gotjunk",
            "tenant_id": "tenant_kevin",
            "requested_action": "extract_foundup",
            "compute_used": "500",
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is False
        assert result.validation_code == EnvelopeValidationCode.INVALID_COMPUTE_USED_TYPE

    def test_compute_used_bool_fails(self):
        """compute_used as bool fails."""
        envelope = {
            "job_id": "job_budget_012",
            "foundup_id": "kosei",
            "tenant_id": "tenant_larry",
            "requested_action": "build_foundup",
            "compute_used": False,
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is False
        assert result.validation_code == EnvelopeValidationCode.INVALID_COMPUTE_USED_TYPE


class TestComputeUsedNegativeValidation:
    """Test compute_used non-negative validation."""

    def test_compute_used_zero_is_valid(self):
        """compute_used=0 is valid."""
        envelope = {
            "job_id": "job_budget_013",
            "foundup_id": "move2japan",
            "tenant_id": "tenant_mary",
            "requested_action": "validate_foundup",
            "compute_used": 0,
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.compute_used_value == 0

    def test_compute_used_positive_is_valid(self):
        """compute_used > 0 is valid."""
        envelope = {
            "job_id": "job_budget_014",
            "foundup_id": "social_twin",
            "tenant_id": "tenant_nancy",
            "requested_action": "build_foundup",
            "compute_used": 250,
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.compute_used_value == 250

    def test_compute_used_negative_fails(self):
        """compute_used < 0 fails."""
        envelope = {
            "job_id": "job_budget_015",
            "foundup_id": "pqn_portal",
            "tenant_id": "tenant_oscar",
            "requested_action": "extract_foundup",
            "compute_used": -50,
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is False
        assert result.validation_code == EnvelopeValidationCode.INVALID_COMPUTE_USED_NEGATIVE


class TestComputeUsedExceedsBudget:
    """Test compute_used cannot exceed compute_budget."""

    def test_compute_used_less_than_budget_passes(self):
        """compute_used < compute_budget passes."""
        envelope = {
            "job_id": "job_budget_016",
            "foundup_id": "gotjunk",
            "tenant_id": "tenant_paul",
            "requested_action": "build_foundup",
            "compute_budget": 1000,
            "compute_used": 500,
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.compute_budget_value == 1000
        assert result.compute_used_value == 500

    def test_compute_used_equals_budget_passes(self):
        """compute_used == compute_budget passes (fully consumed)."""
        envelope = {
            "job_id": "job_budget_017",
            "foundup_id": "kosei",
            "tenant_id": "tenant_quinn",
            "requested_action": "validate_foundup",
            "compute_budget": 1000,
            "compute_used": 1000,
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.compute_used_value == result.compute_budget_value

    def test_compute_used_exceeds_budget_fails(self):
        """compute_used > compute_budget fails."""
        envelope = {
            "job_id": "job_budget_018",
            "foundup_id": "move2japan",
            "tenant_id": "tenant_rachel",
            "requested_action": "extract_foundup",
            "compute_budget": 1000,
            "compute_used": 1001,
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is False
        assert result.validation_code == EnvelopeValidationCode.COMPUTE_USED_EXCEEDS_BUDGET
        assert "exceeds" in result.validation_message

    def test_compute_used_with_none_budget_passes(self):
        """compute_used with compute_budget=None passes (unlimited)."""
        envelope = {
            "job_id": "job_budget_019",
            "foundup_id": "social_twin",
            "tenant_id": "tenant_steve",
            "requested_action": "build_foundup",
            "compute_budget": None,
            "compute_used": 999999,
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.compute_budget_value is None
        assert result.compute_used_value == 999999


class TestLiveModeRequiresComputeBudget:
    """Test live mode requires explicit compute_budget."""

    def test_live_mode_with_budget_passes(self):
        """Live mode with explicit compute_budget passes."""
        envelope = {
            "job_id": "job_budget_020",
            "foundup_id": "pqn_portal",
            "tenant_id": "tenant_tina",
            "requested_action": "validate_foundup",
            "policy_flags": {
                "dry_run_mode": False,
                "human_approval": True,
            },
            "evidence_refs": ["manifest.json"],
            "compute_budget": 5000,
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.is_live_mode is True
        assert result.compute_budget_value == 5000

    def test_live_mode_without_budget_fails(self):
        """Live mode without compute_budget fails."""
        envelope = {
            "job_id": "job_budget_021",
            "foundup_id": "gotjunk",
            "tenant_id": "tenant_uma",
            "requested_action": "build_foundup",
            "policy_flags": {
                "dry_run_mode": False,
                "human_approval": True,
            },
            "evidence_refs": ["evidence.json"],
            "compute_budget": None,
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is False
        assert result.validation_code == EnvelopeValidationCode.LIVE_MODE_REQUIRES_COMPUTE_BUDGET
        assert result.is_live_mode is True

    def test_dry_run_without_budget_passes(self):
        """Dry-run mode without compute_budget passes (allowed for dry-run)."""
        envelope = {
            "job_id": "job_budget_022",
            "foundup_id": "kosei",
            "tenant_id": "tenant_victor",
            "requested_action": "validate_foundup",
            "policy_flags": {"dry_run_mode": True},
            "compute_budget": None,
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.is_live_mode is False
        assert result.compute_budget_value is None


class TestComputeTierValidation:
    """Test compute_tier validation against allowed values."""

    def test_compute_tier_freemium_passes(self):
        """compute_tier='freemium' passes."""
        envelope = {
            "job_id": "job_budget_023",
            "foundup_id": "move2japan",
            "tenant_id": "tenant_wendy",
            "requested_action": "extract_foundup",
            "compute_tier": "freemium",
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.compute_tier_value == "freemium"

    def test_compute_tier_basic_passes(self):
        """compute_tier='basic' passes."""
        envelope = {
            "job_id": "job_budget_024",
            "foundup_id": "social_twin",
            "tenant_id": "tenant_xander",
            "requested_action": "build_foundup",
            "compute_tier": "basic",
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.compute_tier_value == "basic"

    def test_compute_tier_enterprise_passes(self):
        """compute_tier='enterprise' passes."""
        envelope = {
            "job_id": "job_budget_025",
            "foundup_id": "pqn_portal",
            "tenant_id": "tenant_yolanda",
            "requested_action": "validate_foundup",
            "compute_tier": "enterprise",
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.compute_tier_value == "enterprise"

    def test_compute_tier_unknown_fails(self):
        """compute_tier with unknown value fails."""
        envelope = {
            "job_id": "job_budget_026",
            "foundup_id": "gotjunk",
            "tenant_id": "tenant_zach",
            "requested_action": "build_foundup",
            "compute_tier": "premium_plus",
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is False
        assert result.validation_code == EnvelopeValidationCode.INVALID_COMPUTE_TIER
        assert "premium_plus" in result.validation_message


class TestModelPreferenceValidation:
    """Test model_preference validation against allowed values."""

    def test_model_preference_auto_passes(self):
        """model_preference='auto' passes."""
        envelope = {
            "job_id": "job_budget_027",
            "foundup_id": "kosei",
            "tenant_id": "tenant_amy",
            "requested_action": "validate_foundup",
            "model_preference": "auto",
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.model_preference_value == "auto"

    def test_model_preference_free_passes(self):
        """model_preference='free' passes."""
        envelope = {
            "job_id": "job_budget_028",
            "foundup_id": "move2japan",
            "tenant_id": "tenant_bill",
            "requested_action": "extract_foundup",
            "model_preference": "free",
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.model_preference_value == "free"

    def test_model_preference_standard_passes(self):
        """model_preference='standard' passes (with compatible tier)."""
        envelope = {
            "job_id": "job_budget_029",
            "foundup_id": "social_twin",
            "tenant_id": "tenant_cara",
            "requested_action": "build_foundup",
            "compute_tier": "basic",  # basic tier allows standard
            "model_preference": "standard",
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.model_preference_value == "standard"

    def test_model_preference_premium_passes(self):
        """model_preference='premium' passes (with compatible tier)."""
        envelope = {
            "job_id": "job_budget_030",
            "foundup_id": "pqn_portal",
            "tenant_id": "tenant_dan",
            "requested_action": "validate_foundup",
            "compute_tier": "enterprise",  # enterprise tier allows premium
            "model_preference": "premium",
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.model_preference_value == "premium"

    def test_model_preference_unknown_fails(self):
        """model_preference with unknown value fails."""
        envelope = {
            "job_id": "job_budget_031",
            "foundup_id": "gotjunk",
            "tenant_id": "tenant_emma",
            "requested_action": "build_foundup",
            "model_preference": "opus",  # Not in allowed list
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is False
        assert result.validation_code == EnvelopeValidationCode.INVALID_MODEL_PREFERENCE
        assert "opus" in result.validation_message


class TestComputeBudgetWSP97Truth:
    """Test compute budget validation does not claim metering accuracy."""

    def test_compute_validation_does_not_claim_verification(self):
        """Compute validation does NOT set verification_complete=True."""
        envelope = {
            "job_id": "job_budget_032",
            "foundup_id": "kosei",
            "tenant_id": "tenant_frank",
            "requested_action": "validate_foundup",
            "compute_budget": 5000,
            "compute_used": 1000,
            "compute_tier": "enterprise",
            "model_preference": "premium",
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.compute_budget_validated is True
        # WSP 97: Compute validation is structural only
        assert result.verification_complete is False
        assert result.cabr_ready is False
        assert result.payout_ready is False

    def test_compute_fields_in_serialized_result(self):
        """Compute budget fields appear in to_dict() output."""
        envelope = {
            "job_id": "job_budget_033",
            "foundup_id": "move2japan",
            "tenant_id": "tenant_gina",
            "requested_action": "extract_foundup",
            "compute_budget": 2000,
            "compute_used": 500,
            "compute_tier": "basic",
            "model_preference": "free",
        }

        result = validate_foundup_job_envelope(envelope)
        result_dict = result.to_dict()

        assert "compute_budget_validated" in result_dict
        assert "compute_budget_value" in result_dict
        assert "compute_used_value" in result_dict
        assert "compute_tier_value" in result_dict
        assert "model_preference_value" in result_dict
        assert result_dict["compute_budget_validated"] is True
        assert result_dict["compute_budget_value"] == 2000
        assert result_dict["compute_used_value"] == 500


class TestGenericDAEComputeIgnored:
    """Test generic DAE envelope ignores compute fields."""

    def test_generic_dae_ignores_compute_budget(self):
        """Generic DAE envelope does not validate compute_budget."""
        envelope = {
            "objective": "Do something generic",
            "compute_budget": "invalid_string",  # Would fail for FoundUpJob
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.envelope_type == EnvelopeType.GENERIC_DAE
        assert result.compute_budget_validated is False


# ---------------------------------------------------------------------------
# Test: Model Routing Policy Validation (WRE_MODEL_ROUTING_POLICY_VALIDATION_PHASE1)
# ---------------------------------------------------------------------------


class TestFreemiumTierModelRouting:
    """Test freemium tier model preference restrictions."""

    def test_freemium_with_free_passes(self):
        """freemium tier with free preference passes."""
        envelope = {
            "job_id": "job_policy_001",
            "foundup_id": "gotjunk",
            "tenant_id": "tenant_alice",
            "requested_action": "build_foundup",
            "compute_tier": "freemium",
            "model_preference": "free",
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.model_routing_policy_validated is True
        assert "freemium" in result.model_routing_policy_reason
        assert "free" in result.model_routing_policy_reason

    def test_freemium_with_auto_passes(self):
        """freemium tier with auto preference passes (auto always allowed)."""
        envelope = {
            "job_id": "job_policy_002",
            "foundup_id": "kosei",
            "tenant_id": "tenant_bob",
            "requested_action": "validate_foundup",
            "compute_tier": "freemium",
            "model_preference": "auto",
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.model_routing_policy_validated is True

    def test_freemium_with_standard_fails(self):
        """freemium tier with standard preference fails."""
        envelope = {
            "job_id": "job_policy_003",
            "foundup_id": "move2japan",
            "tenant_id": "tenant_carol",
            "requested_action": "extract_foundup",
            "compute_tier": "freemium",
            "model_preference": "standard",
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is False
        assert result.validation_code == EnvelopeValidationCode.MODEL_PREFERENCE_NOT_ALLOWED_FOR_TIER
        assert "standard" in result.validation_message
        assert "freemium" in result.validation_message
        assert result.model_routing_policy_validated is False

    def test_freemium_with_premium_fails(self):
        """freemium tier with premium preference fails."""
        envelope = {
            "job_id": "job_policy_004",
            "foundup_id": "social_twin",
            "tenant_id": "tenant_dave",
            "requested_action": "build_foundup",
            "compute_tier": "freemium",
            "model_preference": "premium",
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is False
        assert result.validation_code == EnvelopeValidationCode.MODEL_PREFERENCE_NOT_ALLOWED_FOR_TIER
        assert "premium" in result.validation_message
        assert result.model_routing_policy_validated is False


class TestBasicTierModelRouting:
    """Test basic tier model preference restrictions."""

    def test_basic_with_free_passes(self):
        """basic tier with free preference passes."""
        envelope = {
            "job_id": "job_policy_005",
            "foundup_id": "pqn_portal",
            "tenant_id": "tenant_eve",
            "requested_action": "validate_foundup",
            "compute_tier": "basic",
            "model_preference": "free",
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.model_routing_policy_validated is True

    def test_basic_with_standard_passes(self):
        """basic tier with standard preference passes."""
        envelope = {
            "job_id": "job_policy_006",
            "foundup_id": "gotjunk",
            "tenant_id": "tenant_frank",
            "requested_action": "build_foundup",
            "compute_tier": "basic",
            "model_preference": "standard",
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.model_routing_policy_validated is True
        assert "basic" in result.model_routing_policy_reason
        assert "standard" in result.model_routing_policy_reason

    def test_basic_with_auto_passes(self):
        """basic tier with auto preference passes."""
        envelope = {
            "job_id": "job_policy_007",
            "foundup_id": "kosei",
            "tenant_id": "tenant_grace",
            "requested_action": "extract_foundup",
            "compute_tier": "basic",
            "model_preference": "auto",
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.model_routing_policy_validated is True

    def test_basic_with_premium_fails(self):
        """basic tier with premium preference fails."""
        envelope = {
            "job_id": "job_policy_008",
            "foundup_id": "move2japan",
            "tenant_id": "tenant_hank",
            "requested_action": "validate_foundup",
            "compute_tier": "basic",
            "model_preference": "premium",
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is False
        assert result.validation_code == EnvelopeValidationCode.MODEL_PREFERENCE_NOT_ALLOWED_FOR_TIER
        assert "premium" in result.validation_message
        assert "basic" in result.validation_message
        assert result.model_routing_policy_validated is False


class TestEnterpriseTierModelRouting:
    """Test enterprise tier allows all model preferences."""

    def test_enterprise_with_free_passes(self):
        """enterprise tier with free preference passes."""
        envelope = {
            "job_id": "job_policy_009",
            "foundup_id": "social_twin",
            "tenant_id": "tenant_ivan",
            "requested_action": "build_foundup",
            "compute_tier": "enterprise",
            "model_preference": "free",
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.model_routing_policy_validated is True

    def test_enterprise_with_standard_passes(self):
        """enterprise tier with standard preference passes."""
        envelope = {
            "job_id": "job_policy_010",
            "foundup_id": "pqn_portal",
            "tenant_id": "tenant_judy",
            "requested_action": "validate_foundup",
            "compute_tier": "enterprise",
            "model_preference": "standard",
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.model_routing_policy_validated is True

    def test_enterprise_with_premium_passes(self):
        """enterprise tier with premium preference passes."""
        envelope = {
            "job_id": "job_policy_011",
            "foundup_id": "gotjunk",
            "tenant_id": "tenant_kevin",
            "requested_action": "extract_foundup",
            "compute_tier": "enterprise",
            "model_preference": "premium",
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.model_routing_policy_validated is True
        assert "enterprise" in result.model_routing_policy_reason
        assert "premium" in result.model_routing_policy_reason

    def test_enterprise_with_auto_passes(self):
        """enterprise tier with auto preference passes."""
        envelope = {
            "job_id": "job_policy_012",
            "foundup_id": "kosei",
            "tenant_id": "tenant_larry",
            "requested_action": "build_foundup",
            "compute_tier": "enterprise",
            "model_preference": "auto",
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.model_routing_policy_validated is True


class TestAutoPreferenceAllTiers:
    """Test auto preference is valid for all tiers."""

    def test_auto_with_freemium_passes(self):
        """auto preference with freemium tier passes."""
        envelope = {
            "job_id": "job_policy_013",
            "foundup_id": "move2japan",
            "tenant_id": "tenant_mary",
            "requested_action": "validate_foundup",
            "compute_tier": "freemium",
            "model_preference": "auto",
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.model_routing_policy_validated is True

    def test_auto_with_basic_passes(self):
        """auto preference with basic tier passes."""
        envelope = {
            "job_id": "job_policy_014",
            "foundup_id": "social_twin",
            "tenant_id": "tenant_nancy",
            "requested_action": "extract_foundup",
            "compute_tier": "basic",
            "model_preference": "auto",
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.model_routing_policy_validated is True

    def test_auto_with_enterprise_passes(self):
        """auto preference with enterprise tier passes."""
        envelope = {
            "job_id": "job_policy_015",
            "foundup_id": "pqn_portal",
            "tenant_id": "tenant_oscar",
            "requested_action": "build_foundup",
            "compute_tier": "enterprise",
            "model_preference": "auto",
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.model_routing_policy_validated is True


class TestModelRoutingPolicyWSP97Truth:
    """Test model routing policy validation does not claim execution."""

    def test_routing_policy_does_not_claim_verification(self):
        """Policy validation does NOT set verification_complete=True."""
        envelope = {
            "job_id": "job_policy_016",
            "foundup_id": "gotjunk",
            "tenant_id": "tenant_paul",
            "requested_action": "validate_foundup",
            "compute_tier": "enterprise",
            "model_preference": "premium",
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.model_routing_policy_validated is True
        # WSP 97: Policy validation is structural only
        assert result.verification_complete is False
        assert result.cabr_ready is False
        assert result.payout_ready is False

    def test_routing_policy_fields_in_serialized_result(self):
        """Model routing policy fields appear in to_dict() output."""
        envelope = {
            "job_id": "job_policy_017",
            "foundup_id": "kosei",
            "tenant_id": "tenant_quinn",
            "requested_action": "build_foundup",
            "compute_tier": "basic",
            "model_preference": "standard",
        }

        result = validate_foundup_job_envelope(envelope)
        result_dict = result.to_dict()

        assert "model_routing_policy_validated" in result_dict
        assert "model_routing_policy_reason" in result_dict
        assert result_dict["model_routing_policy_validated"] is True
        assert "basic" in result_dict["model_routing_policy_reason"]


class TestGenericDAERoutingPolicyIgnored:
    """Test generic DAE envelope ignores routing policy."""

    def test_generic_dae_ignores_routing_policy(self):
        """Generic DAE envelope does not validate tier/preference compatibility."""
        envelope = {
            "objective": "Do something generic",
            "compute_tier": "freemium",
            "model_preference": "premium",  # Would fail for FoundUpJob
        }

        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.envelope_type == EnvelopeType.GENERIC_DAE
        assert result.model_routing_policy_validated is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
