# -*- coding: utf-8 -*-
"""
Tests for FoundUpJob Router policy_flags trust-boundary sanitization + Gate 2 fail-closed.

Slice: FOUNDUP_JOB_ROUTER_POLICYFLAGS_BOUNDARY_SANITIZATION_AND_GATE2_FAILCLOSED_PHASE1 (#752)

Proves at the ROUTER boundary (validate_foundup_job_envelope + _validate_live_mode_gates
+ _sanitize_untrusted_policy_flags_dict):
  1. Raw dict self-asserted gate/token flags do NOT survive sanitization.
  2. Missing dry_run_mode in a raw dict defaults safely (dry_run_mode=True, NOT live).
  3. Missing policy_flags entirely defaults dry_run_mode=True (None branch unchanged).
  4. Explicit live raw dict without a real security pass is BLOCKED (fail-closed).
  5. Explicit live raw dict with FORGED security_gate_passed=True is still BLOCKED.
  6. A legitimate live PASS uses a SERVER-AUTHORED snapshot, exercised directly on
     _validate_live_mode_gates (raw dicts are untrusted by design).
  7. GENERIC_DAE / run_wre-style envelope (no policy_flags) is non-regressed.

WSP Compliance:
  WSP 5  : Test coverage for the trust-boundary fix
  WSP 97 : Truthful validation (explicit failures, fail-closed, no silent fallback)

NO network / NO model / NO live DAE / NO WRE start. Pure validation-layer unit tests.
"""

import pytest

from modules.infrastructure.wre_core.src.foundup_job_router import (
    validate_foundup_job_envelope,
    _validate_live_mode_gates,
    _sanitize_untrusted_policy_flags_dict,
    EnvelopeType,
    EnvelopeValidationCode,
)


# ---------------------------------------------------------------------------
# Group 1: Raw dict self-asserted gate/token flags are sanitized to False
# ---------------------------------------------------------------------------


class TestRawDictSelfAssertionSanitized:
    """Inbound self-asserted gate/token flags must NOT survive into the snapshot."""

    def test_self_asserted_gate_and_token_flags_zeroed_in_helper(self):
        """Helper zeroes ALL server-authored gate/token flags from a raw dict."""
        sanitized, dry_run_defaulted = _sanitize_untrusted_policy_flags_dict(
            {
                "dry_run_mode": False,
                "security_gate_checked": True,
                "security_gate_passed": True,
                "permission_gate_checked": True,
                "permission_gate_passed": True,
                "exfoliation_gate_passed": True,
                "wsp_preflight_passed": True,
                "capability_token_checked": True,
                "capability_token_present": True,
                "capability_token_validated": True,
                "capability_token_scope_authorized": True,
            }
        )
        # Every server-authored flag forced False.
        assert sanitized.get("security_gate_passed") is False
        assert sanitized.get("security_gate_checked") is False
        assert sanitized.get("permission_gate_passed") is False
        assert sanitized.get("permission_gate_checked") is False
        assert sanitized.get("exfoliation_gate_passed") is False
        assert sanitized.get("wsp_preflight_passed") is False
        assert sanitized.get("capability_token_checked") is False
        assert sanitized.get("capability_token_present") is False
        assert sanitized.get("capability_token_validated") is False
        assert sanitized.get("capability_token_scope_authorized") is False
        # Explicit operator-authored dry_run_mode preserved (not defaulted).
        assert sanitized.get("dry_run_mode") is False
        assert dry_run_defaulted is False

    def test_self_asserted_flags_zeroed_in_envelope_snapshot(self):
        """validate_foundup_job_envelope exposes a sanitized policy_flags_snapshot."""
        envelope = {
            "job_id": "job_san_001",
            "foundup_id": "gotjunk",
            "tenant_id": "tenant_alice",
            "requested_action": "build_foundup",
            "policy_flags": {
                "dry_run_mode": True,  # keep dry-run so evidence is pending-friendly
                "security_gate_passed": True,
                "permission_gate_passed": True,
                "capability_token_validated": True,
            },
        }
        result = validate_foundup_job_envelope(envelope)

        snap = result.policy_flags_snapshot
        assert snap.get("security_gate_passed") is False
        assert snap.get("permission_gate_passed") is False
        assert snap.get("capability_token_validated") is False
        # dry_run preserved -> not live, validation still passes structurally
        assert snap.get("dry_run_mode") is True
        assert result.valid is True
        assert result.is_live_mode is False


# ---------------------------------------------------------------------------
# Group 2: Missing dry_run_mode in a raw dict defaults safely (NOT live)
# ---------------------------------------------------------------------------


class TestMissingDryRunDefaultsSafe:
    """A raw dict that omits dry_run_mode must default to True (dry-run), not live."""

    def test_raw_dict_missing_dry_run_defaults_true(self):
        """Helper restores dry_run_mode=True when the inbound dict omits it."""
        sanitized, dry_run_defaulted = _sanitize_untrusted_policy_flags_dict(
            {"security_gate_passed": True}  # no dry_run_mode key
        )
        assert sanitized.get("dry_run_mode") is True
        assert dry_run_defaulted is True
        # And the forged flag is still zeroed.
        assert sanitized.get("security_gate_passed") is False

    def test_envelope_raw_dict_missing_dry_run_not_live(self):
        """Envelope with a raw dict missing dry_run_mode is dry-run, not live."""
        envelope = {
            "job_id": "job_san_002",
            "foundup_id": "kosei",
            "tenant_id": "tenant_bob",
            "requested_action": "validate_foundup",
            "policy_flags": {
                "security_gate_passed": True,  # forged, no dry_run_mode
            },
        }
        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.dry_run_defaulted is True
        assert result.is_live_mode is False
        assert result.policy_flags_snapshot.get("dry_run_mode") is True


# ---------------------------------------------------------------------------
# Group 3: Missing policy_flags entirely (None branch unchanged)
# ---------------------------------------------------------------------------


class TestMissingPolicyFlagsNoneBranch:
    """No policy_flags at all -> dry_run_mode True (None branch is unchanged)."""

    def test_missing_policy_flags_defaults_dry_run(self):
        envelope = {
            "job_id": "job_san_003",
            "foundup_id": "move2japan",
            "tenant_id": "tenant_carol",
            "requested_action": "build_foundup",
        }
        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.dry_run_defaulted is True
        assert result.is_live_mode is False
        assert result.policy_flags_snapshot.get("dry_run_mode") is True


# ---------------------------------------------------------------------------
# Group 4: Explicit live raw dict without real security pass -> BLOCKED
# ---------------------------------------------------------------------------


class TestLiveRawDictWithoutSecurityBlocked:
    """An explicit live raw dict can never pass live mode (security sanitized False)."""

    def test_live_raw_dict_no_security_blocked(self):
        """Live raw dict (dry_run_mode=False) with no real security pass is blocked."""
        envelope = {
            "job_id": "job_san_004",
            "foundup_id": "social_twin",
            "tenant_id": "tenant_dave",
            "requested_action": "build_foundup",
            "policy_flags": {
                "dry_run_mode": False,
                "permission_gate_passed": True,  # sanitized away -> Gate1 also fails
            },
            "evidence_refs": ["manifest.json"],
            "compute_budget": 5000,
        }
        result = validate_foundup_job_envelope(envelope)

        assert result.valid is False
        assert result.is_live_mode is True
        # security_gate_passed is among the missing live gates (fail-closed).
        assert "security_gate_passed" in result.missing_live_gates
        # Primary code is one of the live-mode gate codes (human_approval is
        # checked first since permission_gate_passed was sanitized away).
        assert result.validation_code in (
            EnvelopeValidationCode.LIVE_MODE_REQUIRES_SECURITY_GATE,
            EnvelopeValidationCode.LIVE_MODE_REQUIRES_HUMAN_APPROVAL,
        )


# ---------------------------------------------------------------------------
# Group 5: Explicit live raw dict with FORGED security_gate_passed -> BLOCKED
# ---------------------------------------------------------------------------


class TestLiveRawDictForgedSecurityBlocked:
    """A forged security_gate_passed=True on a raw dict is sanitized -> still blocked."""

    def test_forged_security_gate_passed_blocked(self):
        envelope = {
            "job_id": "job_san_005",
            "foundup_id": "pqn_portal",
            "tenant_id": "tenant_eve",
            "requested_action": "extract_foundup",
            "policy_flags": {
                "dry_run_mode": False,
                "human_approval": True,  # dropped (not a PolicyFlags field)
                "permission_gate_passed": True,  # sanitized False
                "security_gate_checked": True,  # sanitized False
                "security_gate_passed": True,  # FORGED -> sanitized False
            },
            "evidence_refs": ["manifest.json"],
            "compute_budget": 5000,
        }
        result = validate_foundup_job_envelope(envelope)

        assert result.valid is False
        assert result.is_live_mode is True
        assert "security_gate_passed" in result.missing_live_gates
        # The sanitized snapshot proves the forged flag did not survive.
        assert result.policy_flags_snapshot.get("security_gate_passed") is False


# ---------------------------------------------------------------------------
# Group 6: Legitimate live PASS uses a SERVER-AUTHORED snapshot
# ---------------------------------------------------------------------------


class TestLegitimateLivePassServerAuthored:
    """A legitimate live pass requires a server-authored snapshot.

    Raw dicts are untrusted by design and cannot live-pass; therefore the
    legitimate-pass path is proven directly on _validate_live_mode_gates with a
    server-authored snapshot (the object branch's to_dict() output).
    """

    def test_server_authored_snapshot_passes_gates(self):
        """Server-authored snapshot with security_gate_passed=True passes Gate 2."""
        snapshot = {
            "dry_run_mode": False,
            "permission_gate_passed": True,
            "security_gate_passed": True,
        }
        result = _validate_live_mode_gates(
            policy_snapshot=snapshot,
            evidence_count=1,
            evidence_pending=False,
        )
        assert result["valid"] is True
        assert result.get("missing_gates", []) == []

    def test_server_authored_snapshot_human_approval_variant_passes(self):
        """human_approval=True satisfies Gate 1; security_gate_passed satisfies Gate 2."""
        snapshot = {
            "dry_run_mode": False,
            "human_approval": True,
            "security_gate_passed": True,
        }
        result = _validate_live_mode_gates(
            policy_snapshot=snapshot,
            evidence_count=2,
            evidence_pending=False,
        )
        assert result["valid"] is True

    def test_server_authored_snapshot_without_security_still_fails(self):
        """Even server-authored, missing security_gate_passed fails (fail-closed)."""
        snapshot = {
            "dry_run_mode": False,
            "permission_gate_passed": True,
            # security_gate_passed omitted -> False -> blocked
        }
        result = _validate_live_mode_gates(
            policy_snapshot=snapshot,
            evidence_count=1,
            evidence_pending=False,
        )
        assert result["valid"] is False
        assert "security_gate_passed" in result.get("missing_gates", [])


# ---------------------------------------------------------------------------
# Group 7: GENERIC_DAE / run_wre-style envelope non-regression
# ---------------------------------------------------------------------------


class TestGenericDAENoRegression:
    """run_wre-style generic envelope (objective only, no policy_flags) still passes."""

    def test_generic_dae_objective_only_passes(self):
        envelope = {"objective": "Run a generic WRE objective with no identity fields"}
        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.envelope_type == EnvelopeType.GENERIC_DAE
        assert result.validation_code == EnvelopeValidationCode.VALID

    def test_generic_dae_with_context_passes(self):
        envelope = {
            "objective": "Generic objective",
            "context": {"some": "context"},
        }
        result = validate_foundup_job_envelope(envelope)

        assert result.valid is True
        assert result.envelope_type == EnvelopeType.GENERIC_DAE
