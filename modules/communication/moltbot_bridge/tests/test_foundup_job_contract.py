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

    def test_to_dict_roundtrip(self):
        """PolicyFlags survives to_dict/from_dict roundtrip."""
        flags = PolicyFlags(
            security_gate_checked=True,
            security_gate_passed=True,
            permission_gate_checked=True,
            permission_gate_passed=False,
            dry_run_mode=True,
        )
        data = flags.to_dict()
        restored = PolicyFlags.from_dict(data)

        assert restored.security_gate_checked is True
        assert restored.security_gate_passed is True
        assert restored.permission_gate_checked is True
        assert restored.permission_gate_passed is False
        assert restored.exfoliation_gate_checked is False  # Default
        assert restored.dry_run_mode is True

    def test_from_dict_missing_fields_default_false(self):
        """Missing fields in dict default to False."""
        data = {"security_gate_checked": True}
        flags = PolicyFlags.from_dict(data)
        assert flags.security_gate_checked is True
        assert flags.permission_gate_checked is False  # Not in data

    def test_policy_flags_in_job_roundtrip(self):
        """PolicyFlags survive job serialization."""
        job = create_job(tenant_id="t", requested_action="a")
        job.policy_flags.security_gate_checked = True
        job.policy_flags.security_gate_passed = True
        job.policy_flags.dry_run_mode = True

        data = job.to_dict()
        restored = FoundUpJob.from_dict(data)

        assert restored.policy_flags.security_gate_checked is True
        assert restored.policy_flags.security_gate_passed is True
        assert restored.policy_flags.dry_run_mode is True
        assert restored.policy_flags.permission_gate_checked is False


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
# Main
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
