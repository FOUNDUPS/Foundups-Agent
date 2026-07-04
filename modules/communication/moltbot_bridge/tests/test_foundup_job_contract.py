#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for FoundUp Job Contract — Canonical Orchestration Contract

Tests cover:
  1. Job creation and validation
  2. Valid state transitions (full lifecycle paths)
  3. Invalid state transition rejection
  4. Idempotency key generation determinism
  5. Serialization round-trip (to_dict/from_dict)
  6. PolicyFlags serialization
  7. Factory functions

WSP Compliance: WSP 5 (Test Coverage), WSP 6 (Test Audit)
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from modules.communication.moltbot_bridge.src.foundup_job_contract import (
    FoundUpJob,
    JobStatus,
    PolicyFlags,
    StatusReasonCode,
    create_job,
    generate_idempotency_key,
    generate_job_id,
    is_terminal_status,
    is_valid_transition,
)


# ---------------------------------------------------------------------------
# Test: Job Creation and Validation
# ---------------------------------------------------------------------------


class TestJobCreation:
    """Tests for job creation and validation."""

    def test_create_job_basic(self):
        """Basic job creation with minimal fields."""
        job = create_job(
            tenant_id="tenant_012",
            requested_action="extract",
        )
        assert job.job_id.startswith("j_extract_")
        assert job.tenant_id == "tenant_012"
        assert job.status == JobStatus.QUEUED
        assert job.requested_action == "extract"
        assert job.idempotency_key is not None

    def test_create_job_with_foundup(self):
        """Job creation with foundup_id."""
        job = create_job(
            tenant_id="tenant_012",
            requested_action="launch",
            foundup_id="gotjunk",
            intent_id="intent_abc",
            payload={"dry_run": True},
        )
        assert job.foundup_id == "gotjunk"
        assert job.intent_id == "intent_abc"
        assert job.payload == {"dry_run": True}

    def test_create_job_without_idempotency(self):
        """Job creation without idempotency key."""
        job = create_job(
            tenant_id="tenant_012",
            requested_action="query",
            generate_idempotency=False,
        )
        assert job.idempotency_key is None

    def test_job_requires_job_id(self):
        """Job creation fails without job_id."""
        with pytest.raises(ValueError, match="job_id is required"):
            FoundUpJob(job_id="", tenant_id="tenant_012")

    def test_job_requires_tenant_id(self):
        """Job creation fails without tenant_id."""
        with pytest.raises(ValueError, match="tenant_id is required"):
            FoundUpJob(job_id="j_test_123", tenant_id="")

    def test_job_whitespace_only_ids_rejected(self):
        """Whitespace-only IDs are rejected."""
        with pytest.raises(ValueError, match="job_id is required"):
            FoundUpJob(job_id="   ", tenant_id="tenant_012")

        with pytest.raises(ValueError, match="tenant_id is required"):
            FoundUpJob(job_id="j_test_123", tenant_id="   ")

    def test_job_default_values(self):
        """Job has correct default values."""
        job = FoundUpJob(job_id="j_test_123", tenant_id="tenant_012")
        assert job.status == JobStatus.QUEUED
        assert job.previous_status is None
        assert job.worker_id is None
        assert job.started_at is None
        assert job.completed_at is None
        assert job.blocked_at is None
        assert job.status_reason_code == StatusReasonCode.UNKNOWN
        assert job.status_reason_human == ""
        assert job.evidence_refs == []
        assert isinstance(job.policy_flags, PolicyFlags)
        assert job.payload == {}


# ---------------------------------------------------------------------------
# Test: State Transitions
# ---------------------------------------------------------------------------


class TestStateTransitions:
    """Tests for job state machine transitions."""

    def test_valid_queued_to_running(self):
        """QUEUED -> RUNNING is valid."""
        assert is_valid_transition(JobStatus.QUEUED, JobStatus.RUNNING) is True

    def test_valid_queued_to_failed(self):
        """QUEUED -> FAILED is valid (e.g., preflight failure)."""
        assert is_valid_transition(JobStatus.QUEUED, JobStatus.FAILED) is True

    def test_valid_running_to_succeeded(self):
        """RUNNING -> SUCCEEDED is valid."""
        assert is_valid_transition(JobStatus.RUNNING, JobStatus.SUCCEEDED) is True

    def test_valid_running_to_blocked(self):
        """RUNNING -> BLOCKED is valid."""
        assert is_valid_transition(JobStatus.RUNNING, JobStatus.BLOCKED) is True

    def test_valid_running_to_failed(self):
        """RUNNING -> FAILED is valid."""
        assert is_valid_transition(JobStatus.RUNNING, JobStatus.FAILED) is True

    def test_valid_blocked_to_running(self):
        """BLOCKED -> RUNNING is valid (resume)."""
        assert is_valid_transition(JobStatus.BLOCKED, JobStatus.RUNNING) is True

    def test_valid_blocked_to_failed(self):
        """BLOCKED -> FAILED is valid (timeout)."""
        assert is_valid_transition(JobStatus.BLOCKED, JobStatus.FAILED) is True

    def test_invalid_queued_to_succeeded(self):
        """QUEUED -> SUCCEEDED is invalid (must go through RUNNING)."""
        assert is_valid_transition(JobStatus.QUEUED, JobStatus.SUCCEEDED) is False

    def test_invalid_queued_to_blocked(self):
        """QUEUED -> BLOCKED is invalid (must start first)."""
        assert is_valid_transition(JobStatus.QUEUED, JobStatus.BLOCKED) is False

    def test_invalid_succeeded_to_any(self):
        """SUCCEEDED is terminal - no transitions allowed."""
        assert is_valid_transition(JobStatus.SUCCEEDED, JobStatus.RUNNING) is False
        assert is_valid_transition(JobStatus.SUCCEEDED, JobStatus.FAILED) is False
        assert is_valid_transition(JobStatus.SUCCEEDED, JobStatus.QUEUED) is False

    def test_invalid_failed_to_any(self):
        """FAILED is terminal - no transitions allowed."""
        assert is_valid_transition(JobStatus.FAILED, JobStatus.RUNNING) is False
        assert is_valid_transition(JobStatus.FAILED, JobStatus.SUCCEEDED) is False
        assert is_valid_transition(JobStatus.FAILED, JobStatus.QUEUED) is False

    def test_terminal_status_check(self):
        """Terminal status detection."""
        assert is_terminal_status(JobStatus.SUCCEEDED) is True
        assert is_terminal_status(JobStatus.FAILED) is True
        assert is_terminal_status(JobStatus.QUEUED) is False
        assert is_terminal_status(JobStatus.RUNNING) is False
        assert is_terminal_status(JobStatus.BLOCKED) is False


class TestJobLifecycle:
    """Tests for full job lifecycle flows."""

    def test_happy_path_lifecycle(self):
        """Test QUEUED -> RUNNING -> SUCCEEDED lifecycle."""
        job = create_job(
            tenant_id="tenant_012",
            requested_action="validate",
            foundup_id="gotjunk",
        )

        # Start
        assert job.start(worker_id="hermes_001")
        assert job.status == JobStatus.RUNNING
        assert job.previous_status == JobStatus.QUEUED
        assert job.worker_id == "hermes_001"
        assert job.started_at is not None

        # Succeed
        assert job.succeed(
            reason_human="Validation complete",
            evidence_refs=["modules/foundups/gotjunk/foundup_manifest.json"],
        )
        assert job.status == JobStatus.SUCCEEDED
        assert job.previous_status == JobStatus.RUNNING
        assert job.completed_at is not None
        assert "modules/foundups/gotjunk/foundup_manifest.json" in job.evidence_refs

    def test_blocked_resume_lifecycle(self):
        """Test QUEUED -> RUNNING -> BLOCKED -> RUNNING -> SUCCEEDED lifecycle."""
        job = create_job(
            tenant_id="tenant_012",
            requested_action="build",
            foundup_id="kosei",
        )

        # Start
        assert job.start(worker_id="hermes_002")
        assert job.status == JobStatus.RUNNING

        # Block
        assert job.block(
            reason_code=StatusReasonCode.BLOCKED_DEPENDENCY_MISSING,
            reason_human="Waiting for npm install",
        )
        assert job.status == JobStatus.BLOCKED
        assert job.blocked_at is not None
        assert job.status_reason_code == StatusReasonCode.BLOCKED_DEPENDENCY_MISSING

        # Resume
        assert job.resume(reason_human="npm install complete")
        assert job.status == JobStatus.RUNNING

        # Succeed
        assert job.succeed()
        assert job.status == JobStatus.SUCCEEDED

    def test_failure_from_running(self):
        """Test QUEUED -> RUNNING -> FAILED lifecycle."""
        job = create_job(
            tenant_id="tenant_012",
            requested_action="deploy",
        )

        job.start(worker_id="hermes_003")

        assert job.fail(
            reason_code=StatusReasonCode.FAIL_EXECUTION_ERROR,
            reason_human="Deployment script crashed",
            evidence_refs=["logs/deploy_error.log"],
        )
        assert job.status == JobStatus.FAILED
        assert job.completed_at is not None
        assert job.status_reason_code == StatusReasonCode.FAIL_EXECUTION_ERROR

    def test_failure_from_blocked_timeout(self):
        """Test QUEUED -> RUNNING -> BLOCKED -> FAILED (timeout) lifecycle."""
        job = create_job(
            tenant_id="tenant_012",
            requested_action="external_call",
        )

        job.start(worker_id="hermes_004")
        job.block(
            reason_code=StatusReasonCode.BLOCKED_EXTERNAL_SERVICE,
            reason_human="API rate limited",
        )

        # Timeout after being blocked
        assert job.fail(
            reason_code=StatusReasonCode.FAIL_TIMEOUT,
            reason_human="Blocked for >5 minutes, aborting",
        )
        assert job.status == JobStatus.FAILED

    def test_invalid_transition_rejected(self):
        """Invalid transition returns False and sets reason code."""
        job = create_job(
            tenant_id="tenant_012",
            requested_action="test",
        )

        # Try to succeed without starting - should fail
        result = job.transition_to(
            new_status=JobStatus.SUCCEEDED,
            reason_code=StatusReasonCode.OK_COMPLETED,
            reason_human="Tried to skip running",
        )
        assert result is False
        assert job.status == JobStatus.QUEUED  # Unchanged
        assert job.status_reason_code == StatusReasonCode.FAIL_INVALID_TRANSITION

    def test_cannot_transition_from_terminal(self):
        """Cannot transition from terminal states."""
        job = create_job(tenant_id="t", requested_action="a")
        job.start(worker_id="w")
        job.succeed()

        # Try to restart - should fail
        result = job.start(worker_id="w2")
        assert result is False
        assert job.status == JobStatus.SUCCEEDED

    def test_transition_history_recorded(self):
        """Transition history is recorded for debugging."""
        job = create_job(tenant_id="t", requested_action="a")
        job.start(worker_id="w")
        job.succeed()

        assert len(job._transition_history) == 2
        assert job._transition_history[0]["from"] == "queued"
        assert job._transition_history[0]["to"] == "running"
        assert job._transition_history[1]["from"] == "running"
        assert job._transition_history[1]["to"] == "succeeded"


# ---------------------------------------------------------------------------
# Test: Idempotency Key Generation
# ---------------------------------------------------------------------------


class TestIdempotencyKey:
    """Tests for idempotency key generation."""

    def test_idempotency_key_deterministic(self):
        """Same inputs produce same key."""
        key1 = generate_idempotency_key(
            tenant_id="tenant_012",
            foundup_id="gotjunk",
            action="validate",
            payload={"field": "value"},
        )
        key2 = generate_idempotency_key(
            tenant_id="tenant_012",
            foundup_id="gotjunk",
            action="validate",
            payload={"field": "value"},
        )
        assert key1 == key2
        assert len(key1) == 16

    def test_idempotency_key_differs_on_tenant(self):
        """Different tenant produces different key."""
        key1 = generate_idempotency_key("tenant_012", "f1", "act", {})
        key2 = generate_idempotency_key("tenant_013", "f1", "act", {})
        assert key1 != key2

    def test_idempotency_key_differs_on_foundup(self):
        """Different foundup produces different key."""
        key1 = generate_idempotency_key("t1", "gotjunk", "act", {})
        key2 = generate_idempotency_key("t1", "kosei", "act", {})
        assert key1 != key2

    def test_idempotency_key_differs_on_action(self):
        """Different action produces different key."""
        key1 = generate_idempotency_key("t1", "f1", "validate", {})
        key2 = generate_idempotency_key("t1", "f1", "deploy", {})
        assert key1 != key2

    def test_idempotency_key_differs_on_payload(self):
        """Different payload produces different key."""
        key1 = generate_idempotency_key("t1", "f1", "act", {"a": 1})
        key2 = generate_idempotency_key("t1", "f1", "act", {"a": 2})
        assert key1 != key2

    def test_idempotency_key_payload_order_independent(self):
        """Payload key order does not affect idempotency key."""
        key1 = generate_idempotency_key("t1", "f1", "act", {"a": 1, "b": 2})
        key2 = generate_idempotency_key("t1", "f1", "act", {"b": 2, "a": 1})
        assert key1 == key2

    def test_idempotency_key_none_foundup(self):
        """None foundup_id is handled correctly."""
        key1 = generate_idempotency_key("t1", None, "act", {})
        key2 = generate_idempotency_key("t1", None, "act", {})
        assert key1 == key2


# ---------------------------------------------------------------------------
# Test: Job ID Generation
# ---------------------------------------------------------------------------


class TestJobIdGeneration:
    """Tests for job ID generation."""

    def test_job_id_format(self):
        """Job ID follows expected format."""
        job_id = generate_job_id("validate_manifest")
        assert job_id.startswith("j_validate_manifest_")
        parts = job_id.split("_")
        assert len(parts) >= 4

    def test_job_id_action_truncation(self):
        """Long action is truncated to 20 chars."""
        job_id = generate_job_id("this_is_a_very_long_action_name_that_exceeds_limit")
        assert "this_is_a_very_long_" in job_id

    def test_job_id_spaces_replaced(self):
        """Spaces in action are replaced with underscores."""
        job_id = generate_job_id("validate manifest")
        assert "validate_manifest" in job_id

    def test_job_id_uniqueness(self):
        """Sequential job IDs are unique."""
        ids = [generate_job_id("test") for _ in range(10)]
        assert len(set(ids)) == 10


# ---------------------------------------------------------------------------
# Test: Serialization
# ---------------------------------------------------------------------------


class TestSerialization:
    """Tests for job serialization and deserialization."""

    def test_to_dict_roundtrip(self):
        """Job survives to_dict/from_dict roundtrip."""
        job = create_job(
            tenant_id="tenant_012",
            requested_action="extract",
            foundup_id="gotjunk",
            intent_id="intent_123",
            payload={"config": {"nested": True}},
        )
        job.start(worker_id="hermes_001")
        job.succeed(evidence_refs=["path/to/file.json"])

        data = job.to_dict()
        restored = FoundUpJob.from_dict(data)

        assert restored.job_id == job.job_id
        assert restored.tenant_id == job.tenant_id
        assert restored.foundup_id == job.foundup_id
        assert restored.intent_id == job.intent_id
        assert restored.status == job.status
        assert restored.previous_status == job.previous_status
        assert restored.worker_id == job.worker_id
        assert restored.requested_action == job.requested_action
        assert restored.idempotency_key == job.idempotency_key
        assert restored.status_reason_code == job.status_reason_code
        assert restored.status_reason_human == job.status_reason_human
        assert restored.evidence_refs == job.evidence_refs
        assert restored.payload == job.payload

    def test_to_json_produces_valid_json(self):
        """to_json produces valid JSON string."""
        job = create_job(
            tenant_id="tenant_012",
            requested_action="test",
        )
        json_str = job.to_json()
        data = json.loads(json_str)
        assert data["job_id"] == job.job_id
        assert data["status"] == "queued"

    def test_timestamps_survive_roundtrip(self):
        """Timestamps survive serialization roundtrip."""
        job = create_job(tenant_id="t", requested_action="a")
        job.start(worker_id="w")
        job.block(StatusReasonCode.BLOCKED_RATE_LIMITED, "Rate limited")
        job.resume()
        job.succeed()

        data = job.to_dict()
        restored = FoundUpJob.from_dict(data)

        # All timestamps should be restored
        assert restored.created_at is not None
        assert restored.started_at is not None
        assert restored.blocked_at is not None
        assert restored.completed_at is not None

    def test_enum_string_coercion(self):
        """String enum values are coerced to enums."""
        data = {
            "job_id": "j_test_123",
            "tenant_id": "tenant_012",
            "status": "running",
            "status_reason_code": "OK_COMPLETED",
        }
        job = FoundUpJob.from_dict(data)
        assert job.status == JobStatus.RUNNING
        assert job.status_reason_code == StatusReasonCode.OK_COMPLETED

    def test_unknown_reason_code_fallback(self):
        """Unknown reason code falls back to UNKNOWN."""
        data = {
            "job_id": "j_test_123",
            "tenant_id": "tenant_012",
            "status_reason_code": "NOT_A_REAL_CODE",
        }
        job = FoundUpJob.from_dict(data)
        assert job.status_reason_code == StatusReasonCode.UNKNOWN


# ---------------------------------------------------------------------------
# Test: PolicyFlags
# ---------------------------------------------------------------------------


class TestPolicyFlags:
    """Tests for PolicyFlags dataclass."""

    def test_default_all_false(self):
        """All flags default to False."""
        flags = PolicyFlags()
        assert flags.security_gate_checked is False
        assert flags.security_gate_passed is False
        assert flags.permission_gate_checked is False
        assert flags.permission_gate_passed is False
        assert flags.exfoliation_gate_checked is False
        assert flags.exfoliation_gate_passed is False
        assert flags.wsp_preflight_checked is False
        assert flags.wsp_preflight_passed is False
        assert flags.dry_run_mode is False
        # HXA24: Capability token fields
        assert flags.capability_token_checked is False
        assert flags.capability_token_present is False
        assert flags.capability_token_validated is False
        assert flags.capability_token_scope_authorized is False

    def test_from_dict_sanitizes_server_authored_flags(self):
        """from_dict FORCES server-authored gate flags to False (#746).

        HXA_POLICYFLAGS_WRITEBACK_REMEDIATION_PHASE1: deserialized gate/token
        state is UNTRUSTED. Even if a (possibly malicious) payload carries True
        for security/permission gate flags, from_dict zeroes them. Only
        dry_run_mode is preserved (operator-authored).
        """
        flags = PolicyFlags(
            security_gate_checked=True,
            security_gate_passed=True,
            permission_gate_checked=True,
            permission_gate_passed=False,
            dry_run_mode=True,
        )
        data = flags.to_dict()
        restored = PolicyFlags.from_dict(data)

        # Server-authored gate flags forced False regardless of inbound True
        assert restored.security_gate_checked is False
        assert restored.security_gate_passed is False
        assert restored.permission_gate_checked is False
        assert restored.permission_gate_passed is False
        assert restored.exfoliation_gate_checked is False
        # Operator-authored flag preserved
        assert restored.dry_run_mode is True

    def test_from_dict_missing_fields_default_false(self):
        """Missing fields default to False; present gate flags forced False (#746).

        Inbound security_gate_checked=True is IGNORED (server-authored,
        untrusted) and sanitized to False.
        """
        data = {"security_gate_checked": True}
        flags = PolicyFlags.from_dict(data)
        assert flags.security_gate_checked is False  # Sanitized: forced False
        assert flags.permission_gate_checked is False  # Not in data
        # HXA24: Capability token fields should default to False
        assert flags.capability_token_checked is False
        assert flags.capability_token_present is False
        assert flags.capability_token_validated is False
        assert flags.capability_token_scope_authorized is False

    def test_policy_flags_in_job_roundtrip_sanitizes_gates(self):
        """Job from_dict sanitizes server-authored gate flags (#746).

        Even when a serialized job carries True security gate flags, the
        untrusted FoundUpJob.from_dict path forces them False; only the
        operator-authored dry_run_mode survives.
        """
        job = create_job(tenant_id="t", requested_action="a")
        job.policy_flags.security_gate_checked = True
        job.policy_flags.security_gate_passed = True
        job.policy_flags.dry_run_mode = True

        data = job.to_dict()
        restored = FoundUpJob.from_dict(data)

        # Server-authored gate flags sanitized to False on deserialization
        assert restored.policy_flags.security_gate_checked is False
        assert restored.policy_flags.security_gate_passed is False
        assert restored.policy_flags.permission_gate_checked is False
        # Operator-authored flag preserved
        assert restored.policy_flags.dry_run_mode is True

    # HXA24: Capability Token PolicyFlags Tests

    def test_capability_token_fields_exist(self):
        """PolicyFlags has capability token fields (HXA24)."""
        flags = PolicyFlags()
        assert hasattr(flags, "capability_token_checked")
        assert hasattr(flags, "capability_token_present")
        assert hasattr(flags, "capability_token_validated")
        assert hasattr(flags, "capability_token_scope_authorized")

    def test_capability_token_fields_to_dict(self):
        """Capability token fields included in to_dict() (HXA24)."""
        flags = PolicyFlags(
            capability_token_checked=True,
            capability_token_present=True,
            capability_token_validated=True,
            capability_token_scope_authorized=True,
        )
        data = flags.to_dict()

        assert data["capability_token_checked"] is True
        assert data["capability_token_present"] is True
        assert data["capability_token_validated"] is True
        assert data["capability_token_scope_authorized"] is True

    def test_capability_token_fields_from_dict_sanitized(self):
        """from_dict FORCES capability token fields to False (#746).

        Capability token flags are server-authored and must never be trusted
        from deserialized data. A malicious payload presenting all four as True
        is sanitized to all-False; server authority comes from executor
        write-back.
        """
        data = {
            "capability_token_checked": True,
            "capability_token_present": True,
            "capability_token_validated": True,
            "capability_token_scope_authorized": True,
        }
        flags = PolicyFlags.from_dict(data)

        assert flags.capability_token_checked is False
        assert flags.capability_token_present is False
        assert flags.capability_token_validated is False
        assert flags.capability_token_scope_authorized is False

    def test_capability_token_fields_sanitized_on_roundtrip(self):
        """Capability token fields forced False through from_dict (#746).

        Even though to_dict faithfully serializes True flags (server-authored
        object state), the untrusted from_dict path zeroes them.
        """
        original = PolicyFlags(
            capability_token_checked=True,
            capability_token_present=True,
            capability_token_validated=True,
            capability_token_scope_authorized=True,
        )
        data = original.to_dict()
        # to_dict preserves the server-authored object state
        assert data["capability_token_checked"] is True
        assert data["capability_token_scope_authorized"] is True

        restored = PolicyFlags.from_dict(data)
        # from_dict sanitizes: untrusted deserialization cannot grant tokens
        assert restored.capability_token_checked is False
        assert restored.capability_token_present is False
        assert restored.capability_token_validated is False
        assert restored.capability_token_scope_authorized is False


# ---------------------------------------------------------------------------
# Test: PolicyFlags Deserialization Sanitization (#746)
# HXA_POLICYFLAGS_WRITEBACK_REMEDIATION_PHASE1
# ---------------------------------------------------------------------------


# Every server-authored gate/token flag that from_dict MUST force False.
_SANITIZED_FLAG_NAMES = [
    "security_gate_checked",
    "security_gate_passed",
    "permission_gate_checked",
    "permission_gate_passed",
    "exfoliation_gate_checked",
    "exfoliation_gate_passed",
    "wsp_preflight_checked",
    "wsp_preflight_passed",
    "capability_token_checked",
    "capability_token_present",
    "capability_token_validated",
    "capability_token_scope_authorized",
]


class TestPolicyFlagsDeserializationSanitization:
    """#746: deserialized gate/token state is UNTRUSTED and forced False."""

    def test_malicious_inbound_all_true_forced_false(self):
        """A payload presenting EVERY gate/token flag True is fully sanitized."""
        malicious = {name: True for name in _SANITIZED_FLAG_NAMES}
        malicious["dry_run_mode"] = True  # operator-authored, must survive

        flags = PolicyFlags.from_dict(malicious)

        for name in _SANITIZED_FLAG_NAMES:
            assert getattr(flags, name) is False, (
                f"{name} must be forced False on untrusted deserialization"
            )
        # dry_run_mode is the only inbound flag preserved
        assert flags.dry_run_mode is True

    def test_dry_run_mode_preserved_true(self):
        """dry_run_mode=True is preserved (safe/sandbox direction)."""
        flags = PolicyFlags.from_dict({"dry_run_mode": True})
        assert flags.dry_run_mode is True

    def test_dry_run_mode_preserved_false(self):
        """dry_run_mode=False is preserved verbatim."""
        flags = PolicyFlags.from_dict({"dry_run_mode": False})
        assert flags.dry_run_mode is False

    def test_dry_run_mode_defaults_false_when_missing(self):
        """dry_run_mode defaults False when absent from inbound data."""
        flags = PolicyFlags.from_dict({})
        assert flags.dry_run_mode is False

    def test_foundupjob_from_dict_sanitizes_malicious_payload(self):
        """FoundUpJob.from_dict routes through the same sanitization chokepoint."""
        malicious_flags = {name: True for name in _SANITIZED_FLAG_NAMES}
        malicious_flags["dry_run_mode"] = True
        data = {
            "job_id": "j_attack_001",
            "tenant_id": "attacker",
            "requested_action": "create_repo",
            "policy_flags": malicious_flags,
        }
        job = FoundUpJob.from_dict(data)

        for name in _SANITIZED_FLAG_NAMES:
            assert getattr(job.policy_flags, name) is False
        assert job.policy_flags.dry_run_mode is True

    def test_post_init_dict_policy_flags_sanitized(self):
        """__post_init__ coerces a dict of malicious flags through from_dict."""
        malicious_flags = {name: True for name in _SANITIZED_FLAG_NAMES}
        job = FoundUpJob(
            job_id="j_attack_002",
            tenant_id="attacker",
            requested_action="delete_permanently",
            policy_flags=malicious_flags,  # dict -> coerced in __post_init__
        )
        for name in _SANITIZED_FLAG_NAMES:
            assert getattr(job.policy_flags, name) is False

    def test_create_job_yields_all_false_gate_flags(self):
        """create_job() yields all-False gate/token flags at birth (unchanged)."""
        job = create_job(tenant_id="t", requested_action="build_foundup")
        for name in _SANITIZED_FLAG_NAMES:
            assert getattr(job.policy_flags, name) is False
        assert job.policy_flags.dry_run_mode is False

    def test_direct_constructor_still_allows_server_authored_true(self):
        """Direct PolicyFlags(...) constructor is UNCHANGED (server authority).

        Only the untrusted from_dict path is locked down; server code can still
        author True flags by direct object construction/assignment.
        """
        flags = PolicyFlags(
            security_gate_passed=True,
            capability_token_validated=True,
        )
        assert flags.security_gate_passed is True
        assert flags.capability_token_validated is True


# ---------------------------------------------------------------------------
# Test: StatusReasonCode Categories
# ---------------------------------------------------------------------------


class TestStatusReasonCodes:
    """Tests for StatusReasonCode enum."""

    def test_ok_codes_exist(self):
        """OK codes exist for success scenarios."""
        assert StatusReasonCode.OK_COMPLETED
        assert StatusReasonCode.OK_DRY_RUN_PASSED
        assert StatusReasonCode.OK_VALIDATION_PASSED

    def test_blocked_codes_exist(self):
        """BLOCKED codes exist for blocking scenarios."""
        assert StatusReasonCode.BLOCKED_DEPENDENCY_MISSING
        assert StatusReasonCode.BLOCKED_AWAITING_APPROVAL
        assert StatusReasonCode.BLOCKED_RATE_LIMITED
        assert StatusReasonCode.BLOCKED_EXTERNAL_SERVICE

    def test_fail_codes_exist(self):
        """FAIL codes exist for failure scenarios."""
        assert StatusReasonCode.FAIL_SECURITY_GATE
        assert StatusReasonCode.FAIL_PERMISSION_DENIED
        assert StatusReasonCode.FAIL_VALIDATION_ERROR
        assert StatusReasonCode.FAIL_EXFOLIATION_GATE
        assert StatusReasonCode.FAIL_MANIFEST_INVALID
        assert StatusReasonCode.FAIL_EXECUTION_ERROR
        assert StatusReasonCode.FAIL_TIMEOUT
        assert StatusReasonCode.FAIL_WORKER_UNAVAILABLE
        assert StatusReasonCode.FAIL_INVALID_TRANSITION
        assert StatusReasonCode.FAIL_ALREADY_TERMINAL


# ---------------------------------------------------------------------------
# Test: Compute Metering
# ---------------------------------------------------------------------------


class TestComputeMetering:
    """Tests for compute metering fields."""

    def test_default_compute_fields(self):
        """Job has correct default compute values."""
        job = create_job(tenant_id="t", requested_action="a")
        assert job.compute_tier == "freemium"
        assert job.compute_budget is None
        assert job.compute_used == 0
        assert job.model_preference == "auto"

    def test_compute_fields_roundtrip(self):
        """Compute fields survive serialization roundtrip."""
        job = create_job(tenant_id="t", requested_action="a")
        job.compute_tier = "basic"
        job.compute_budget = 1000
        job.compute_used = 250
        job.model_preference = "free"

        data = job.to_dict()
        restored = FoundUpJob.from_dict(data)

        assert restored.compute_tier == "basic"
        assert restored.compute_budget == 1000
        assert restored.compute_used == 250
        assert restored.model_preference == "free"

    def test_blocked_compute_exhausted_code_exists(self):
        """BLOCKED_COMPUTE_EXHAUSTED reason code exists."""
        assert StatusReasonCode.BLOCKED_COMPUTE_EXHAUSTED

    def test_compute_exhausted_blocks_job(self):
        """Job can be blocked due to compute exhaustion."""
        job = create_job(tenant_id="t", requested_action="build")
        job.compute_budget = 100
        job.compute_used = 100

        job.start(worker_id="hermes")
        result = job.block(
            reason_code=StatusReasonCode.BLOCKED_COMPUTE_EXHAUSTED,
            reason_human="Compute budget exhausted, waiting for top-up",
        )

        assert result is True
        assert job.status == JobStatus.BLOCKED
        assert job.status_reason_code == StatusReasonCode.BLOCKED_COMPUTE_EXHAUSTED


# ---------------------------------------------------------------------------
# Test: Canonical Action Validation
# ---------------------------------------------------------------------------


class TestCanonicalActions:
    """Tests for canonical requested_action validation."""

    def test_canonical_actions_frozenset_exists(self):
        """CANONICAL_ACTIONS frozenset exists and is immutable.

        5 actions after FOUNDUP_CREATE_ACTION_DRYRUN_PHASE1 added create_foundup
        (a NEW-scaffold action, distinct from the existing build/extract actions).
        """
        from modules.communication.moltbot_bridge.src.foundup_job_contract import (
            CANONICAL_ACTIONS,
            EXISTING_MODULE_ACTIONS,
        )
        assert isinstance(CANONICAL_ACTIONS, frozenset)
        assert len(CANONICAL_ACTIONS) == 5
        assert "create_foundup" in CANONICAL_ACTIONS
        # No-alias invariant: create_foundup is NOT an existing-module action.
        assert "create_foundup" not in EXISTING_MODULE_ACTIONS

    def test_create_foundup_is_canonical(self):
        """create_foundup is a canonical action (FOUNDUP_CREATE_ACTION_DRYRUN_PHASE1)."""
        from modules.communication.moltbot_bridge.src.foundup_job_contract import (
            is_supported_action,
        )
        assert is_supported_action("create_foundup") is True

    def test_build_foundup_is_canonical(self):
        """build_foundup is a canonical action."""
        from modules.communication.moltbot_bridge.src.foundup_job_contract import (
            is_supported_action,
        )
        assert is_supported_action("build_foundup") is True

    def test_extract_foundup_is_canonical(self):
        """extract_foundup is a canonical action."""
        from modules.communication.moltbot_bridge.src.foundup_job_contract import (
            is_supported_action,
        )
        assert is_supported_action("extract_foundup") is True

    def test_validate_foundup_is_canonical(self):
        """validate_foundup is a canonical action."""
        from modules.communication.moltbot_bridge.src.foundup_job_contract import (
            is_supported_action,
        )
        assert is_supported_action("validate_foundup") is True

    def test_queue_foundup_job_is_canonical(self):
        """queue_foundup_job is a canonical action."""
        from modules.communication.moltbot_bridge.src.foundup_job_contract import (
            is_supported_action,
        )
        assert is_supported_action("queue_foundup_job") is True

    def test_short_build_is_rejected(self):
        """Short form 'build' is NOT a canonical action."""
        from modules.communication.moltbot_bridge.src.foundup_job_contract import (
            is_supported_action,
        )
        assert is_supported_action("build") is False

    def test_short_extract_is_rejected(self):
        """Short form 'extract' is NOT a canonical action."""
        from modules.communication.moltbot_bridge.src.foundup_job_contract import (
            is_supported_action,
        )
        assert is_supported_action("extract") is False

    def test_short_validate_is_rejected(self):
        """Short form 'validate' is NOT a canonical action."""
        from modules.communication.moltbot_bridge.src.foundup_job_contract import (
            is_supported_action,
        )
        assert is_supported_action("validate") is False

    def test_short_queue_is_rejected(self):
        """Short form 'queue' is NOT a canonical action."""
        from modules.communication.moltbot_bridge.src.foundup_job_contract import (
            is_supported_action,
        )
        assert is_supported_action("queue") is False

    def test_unsupported_action_is_rejected(self):
        """Arbitrary unsupported action is rejected."""
        from modules.communication.moltbot_bridge.src.foundup_job_contract import (
            is_supported_action,
        )
        assert is_supported_action("launch_rocket") is False
        assert is_supported_action("") is False
        assert is_supported_action("BUILD_FOUNDUP") is False  # Case-sensitive

    def test_fail_unsupported_action_code_exists(self):
        """FAIL_UNSUPPORTED_ACTION reason code exists."""
        assert StatusReasonCode.FAIL_UNSUPPORTED_ACTION

    def test_job_can_fail_with_unsupported_action(self):
        """Job can be failed with FAIL_UNSUPPORTED_ACTION reason."""
        job = create_job(
            tenant_id="t",
            requested_action="invalid_action",  # Intentionally invalid
        )
        job.start(worker_id="w")
        result = job.fail(
            reason_code=StatusReasonCode.FAIL_UNSUPPORTED_ACTION,
            reason_human="Action 'invalid_action' is not supported",
        )
        assert result is True
        assert job.status == JobStatus.FAILED
        assert job.status_reason_code == StatusReasonCode.FAIL_UNSUPPORTED_ACTION

    def test_wsp97_fields_preserved_after_action_failure(self):
        """WSP 97 audit fields are preserved when job fails due to unsupported action."""
        job = create_job(
            tenant_id="tenant_012",
            requested_action="bad_action",
            foundup_id="test_foundup",
        )
        job.start(worker_id="hermes")
        job.fail(
            reason_code=StatusReasonCode.FAIL_UNSUPPORTED_ACTION,
            reason_human="Unsupported action: bad_action",
            evidence_refs=["audit/action_validation.log"],
        )

        # WSP 97 fields must be preserved
        assert job.status_reason_code == StatusReasonCode.FAIL_UNSUPPORTED_ACTION
        assert "bad_action" in job.status_reason_human
        assert "audit/action_validation.log" in job.evidence_refs
        assert len(job._transition_history) == 2  # start + fail


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
