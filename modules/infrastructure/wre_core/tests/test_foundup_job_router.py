# -*- coding: utf-8 -*-
"""
Tests for WRE FoundUpJob Router — Phase 1 Routing Envelope

W5/OC5 Test Coverage:
  - build/extract/validate route to Hermes target
  - queue_foundup_job produces queued decision
  - unsupported action
  - terminal job blocked
  - missing tenant/job identity blocked
  - policy blocked if policy flags expose blocking state
"""

import pytest
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any

from modules.infrastructure.wre_core.src.foundup_job_router import (
    route_foundup_job,
    RouteStatus,
    TargetBackend,
    RouteReasonCode,
    RouteEnvelope,
)


# ---------------------------------------------------------------------------
# Mock Job Classes (duck-typed to match FoundUpJob contract)
# ---------------------------------------------------------------------------


class MockJobStatus(str, Enum):
    """Mock status enum matching FoundUpJob contract."""
    QUEUED = "queued"
    RUNNING = "running"
    BLOCKED = "blocked"
    FAILED = "failed"
    SUCCEEDED = "succeeded"


@dataclass
class MockPolicyFlags:
    """Mock policy flags matching FoundUpJob contract."""
    security_gate_checked: bool = False
    security_gate_passed: bool = False
    genesis_validated: bool = False

    def to_dict(self) -> Dict[str, bool]:
        return {
            "security_gate_checked": self.security_gate_checked,
            "security_gate_passed": self.security_gate_passed,
            "genesis_validated": self.genesis_validated,
        }


@dataclass
class MockFoundUpJob:
    """Mock FoundUpJob for testing router."""
    job_id: str
    tenant_id: str
    requested_action: str
    status: MockJobStatus = MockJobStatus.QUEUED
    foundup_id: Optional[str] = None
    policy_flags: Optional[MockPolicyFlags] = None


# ---------------------------------------------------------------------------
# Test: Build/Extract/Validate Route to Hermes
# ---------------------------------------------------------------------------


class TestHermesRouting:
    """Test routing to Hermes builder/validator backends."""

    def test_build_foundup_routes_to_hermes_builder(self):
        """build_foundup action routes to HERMES_BUILDER."""
        job = MockFoundUpJob(
            job_id="job_001",
            tenant_id="tenant_alice",
            requested_action="build_foundup",
            foundup_id="gotjunk",
        )

        envelope = route_foundup_job(job)

        assert envelope.route_status == RouteStatus.ROUTED
        assert envelope.target_backend == TargetBackend.HERMES_BUILDER
        assert envelope.reason_code == RouteReasonCode.OK_ROUTED
        assert envelope.job_id == "job_001"
        assert envelope.tenant_id == "tenant_alice"
        assert envelope.foundup_id == "gotjunk"

    def test_extract_foundup_routes_to_hermes_builder(self):
        """extract_foundup action routes to HERMES_BUILDER."""
        job = MockFoundUpJob(
            job_id="job_002",
            tenant_id="tenant_bob",
            requested_action="extract_foundup",
        )

        envelope = route_foundup_job(job)

        assert envelope.route_status == RouteStatus.ROUTED
        assert envelope.target_backend == TargetBackend.HERMES_BUILDER
        assert envelope.reason_code == RouteReasonCode.OK_ROUTED

    def test_validate_foundup_routes_to_hermes_validator(self):
        """validate_foundup action routes to HERMES_VALIDATOR."""
        job = MockFoundUpJob(
            job_id="job_003",
            tenant_id="tenant_carol",
            requested_action="validate_foundup",
            foundup_id="kosei",
        )

        envelope = route_foundup_job(job)

        assert envelope.route_status == RouteStatus.ROUTED
        assert envelope.target_backend == TargetBackend.HERMES_VALIDATOR
        assert envelope.reason_code == RouteReasonCode.OK_ROUTED


# ---------------------------------------------------------------------------
# Test: Queue Action Produces Queued Decision
# ---------------------------------------------------------------------------


class TestQueueRouting:
    """Test queue_foundup_job produces QUEUED status."""

    def test_queue_foundup_job_returns_queued_status(self):
        """queue_foundup_job action returns QUEUED, not ROUTED."""
        job = MockFoundUpJob(
            job_id="job_004",
            tenant_id="tenant_dave",
            requested_action="queue_foundup_job",
        )

        envelope = route_foundup_job(job)

        assert envelope.route_status == RouteStatus.QUEUED
        assert envelope.target_backend == TargetBackend.OPENCLAW_QUEUE
        assert envelope.reason_code == RouteReasonCode.OK_QUEUED
        assert "queued" in envelope.reason_human.lower()


# ---------------------------------------------------------------------------
# Test: Unsupported Action
# ---------------------------------------------------------------------------


class TestUnsupportedAction:
    """Test unsupported actions return UNSUPPORTED status."""

    def test_unknown_action_returns_unsupported(self):
        """Unknown action returns UNSUPPORTED with NONE backend."""
        job = MockFoundUpJob(
            job_id="job_005",
            tenant_id="tenant_eve",
            requested_action="delete_everything",
        )

        envelope = route_foundup_job(job)

        assert envelope.route_status == RouteStatus.UNSUPPORTED
        assert envelope.target_backend == TargetBackend.NONE
        assert envelope.reason_code == RouteReasonCode.UNSUPPORTED_ACTION
        assert "delete_everything" in envelope.reason_human

    def test_empty_action_returns_blocked(self):
        """Empty action returns BLOCKED, not UNSUPPORTED."""
        job = MockFoundUpJob(
            job_id="job_006",
            tenant_id="tenant_frank",
            requested_action="",
        )

        envelope = route_foundup_job(job)

        assert envelope.route_status == RouteStatus.BLOCKED
        assert envelope.reason_code == RouteReasonCode.BLOCKED_MISSING_ACTION


# ---------------------------------------------------------------------------
# Test: Terminal Job Blocked
# ---------------------------------------------------------------------------


class TestTerminalJobBlocked:
    """Test terminal status jobs are blocked from routing."""

    def test_succeeded_job_blocked(self):
        """Job with SUCCEEDED status is blocked (terminal)."""
        job = MockFoundUpJob(
            job_id="job_007",
            tenant_id="tenant_grace",
            requested_action="build_foundup",
            status=MockJobStatus.SUCCEEDED,
        )

        envelope = route_foundup_job(job)

        assert envelope.route_status == RouteStatus.BLOCKED
        assert envelope.target_backend == TargetBackend.NONE
        assert envelope.reason_code == RouteReasonCode.BLOCKED_TERMINAL_STATUS
        assert "terminal" in envelope.reason_human.lower() or "succeeded" in envelope.reason_human.lower()

    def test_failed_job_blocked(self):
        """Job with FAILED status is blocked (terminal)."""
        job = MockFoundUpJob(
            job_id="job_008",
            tenant_id="tenant_hank",
            requested_action="validate_foundup",
            status=MockJobStatus.FAILED,
        )

        envelope = route_foundup_job(job)

        assert envelope.route_status == RouteStatus.BLOCKED
        assert envelope.reason_code == RouteReasonCode.BLOCKED_TERMINAL_STATUS

    def test_running_job_not_blocked(self):
        """Job with RUNNING status is not blocked (non-terminal)."""
        job = MockFoundUpJob(
            job_id="job_009",
            tenant_id="tenant_ivan",
            requested_action="extract_foundup",
            status=MockJobStatus.RUNNING,
        )

        envelope = route_foundup_job(job)

        assert envelope.route_status == RouteStatus.ROUTED
        assert envelope.reason_code == RouteReasonCode.OK_ROUTED


# ---------------------------------------------------------------------------
# Test: Missing Identity Blocked
# ---------------------------------------------------------------------------


class TestMissingIdentity:
    """Test missing job_id or tenant_id results in BLOCKED."""

    def test_missing_job_id_blocked(self):
        """Missing job_id returns BLOCKED."""
        job = MockFoundUpJob(
            job_id="",
            tenant_id="tenant_judy",
            requested_action="build_foundup",
        )

        envelope = route_foundup_job(job)

        assert envelope.route_status == RouteStatus.BLOCKED
        assert envelope.reason_code == RouteReasonCode.BLOCKED_MISSING_JOB_ID
        assert "job id" in envelope.reason_human.lower()

    def test_none_job_id_blocked(self):
        """None job_id returns BLOCKED."""
        job = MockFoundUpJob(
            job_id=None,  # type: ignore
            tenant_id="tenant_kevin",
            requested_action="build_foundup",
        )

        envelope = route_foundup_job(job)

        assert envelope.route_status == RouteStatus.BLOCKED
        assert envelope.reason_code == RouteReasonCode.BLOCKED_MISSING_JOB_ID

    def test_missing_tenant_id_blocked(self):
        """Missing tenant_id returns BLOCKED."""
        job = MockFoundUpJob(
            job_id="job_010",
            tenant_id="",
            requested_action="validate_foundup",
        )

        envelope = route_foundup_job(job)

        assert envelope.route_status == RouteStatus.BLOCKED
        assert envelope.reason_code == RouteReasonCode.BLOCKED_MISSING_TENANT_ID
        assert "tenant id" in envelope.reason_human.lower()

    def test_none_tenant_id_blocked(self):
        """None tenant_id returns BLOCKED."""
        job = MockFoundUpJob(
            job_id="job_011",
            tenant_id=None,  # type: ignore
            requested_action="build_foundup",
        )

        envelope = route_foundup_job(job)

        assert envelope.route_status == RouteStatus.BLOCKED
        assert envelope.reason_code == RouteReasonCode.BLOCKED_MISSING_TENANT_ID


# ---------------------------------------------------------------------------
# Test: Policy Gate Blocked
# ---------------------------------------------------------------------------


class TestPolicyGateBlocked:
    """Test policy flags blocking routing.

    NOTE (live-mode discriminator, FOUNDUP_JOB_ROUTER_ROUTE_GATE_LIVE_MODE_DISCRIMINATOR_PHASE1):
    The legacy opt-in ``security_gate_checked and not security_gate_passed`` block was
    REPLACED by an explicit-live fail-closed gate. The object/to_dict() path is intentionally
    never treated as live (``dry_run_defaulted`` stays True), so an object-path job with a
    failed security gate now ROUTES rather than blocking - over-blocking the default/object
    path is the regression the new gate explicitly avoids. Strict live-mode blocking coverage
    lives in ``test_route_foundup_job_live_mode_gate.py`` (raw-dict explicit-live path).
    """

    def test_security_gate_failed_object_path_still_routes(self):
        """Object-path job with security gate not passed ROUTES (object path is never live).

        Replaces the legacy ``test_security_gate_failed_blocks_routing``: under the live-mode
        discriminator the to_dict() object path keeps ``dry_run_defaulted`` True, so ``is_live``
        is False and routing is preserved. This is the no-over-block guarantee for object jobs.
        """
        job = MockFoundUpJob(
            job_id="job_012",
            tenant_id="tenant_larry",
            requested_action="build_foundup",
            policy_flags=MockPolicyFlags(
                security_gate_checked=True,
                security_gate_passed=False,
            ),
        )

        envelope = route_foundup_job(job)

        # Stricter than the legacy assertion: prove the object path is NOT live-gated and routes.
        assert envelope.route_status == RouteStatus.ROUTED
        assert envelope.reason_code == RouteReasonCode.OK_ROUTED
        assert envelope.reason_code != RouteReasonCode.BLOCKED_POLICY_GATE

    def test_security_gate_passed_allows_routing(self):
        """Security gate checked and passed allows routing."""
        job = MockFoundUpJob(
            job_id="job_013",
            tenant_id="tenant_mary",
            requested_action="build_foundup",
            policy_flags=MockPolicyFlags(
                security_gate_checked=True,
                security_gate_passed=True,
            ),
        )

        envelope = route_foundup_job(job)

        assert envelope.route_status == RouteStatus.ROUTED
        assert envelope.reason_code == RouteReasonCode.OK_ROUTED

    def test_no_policy_flags_allows_routing(self):
        """No policy flags (default) allows routing."""
        job = MockFoundUpJob(
            job_id="job_014",
            tenant_id="tenant_nancy",
            requested_action="validate_foundup",
            policy_flags=None,
        )

        envelope = route_foundup_job(job)

        assert envelope.route_status == RouteStatus.ROUTED


# ---------------------------------------------------------------------------
# Test: Envelope Serialization
# ---------------------------------------------------------------------------


class TestEnvelopeSerialization:
    """Test RouteEnvelope.to_dict() serialization."""

    def test_to_dict_contains_all_fields(self):
        """to_dict() returns all expected fields."""
        job = MockFoundUpJob(
            job_id="job_015",
            tenant_id="tenant_oscar",
            requested_action="build_foundup",
            foundup_id="move2japan",
        )

        envelope = route_foundup_job(job)
        result = envelope.to_dict()

        assert result["job_id"] == "job_015"
        assert result["tenant_id"] == "tenant_oscar"
        assert result["target_backend"] == "hermes_builder"
        assert result["requested_action"] == "build_foundup"
        assert result["route_status"] == "routed"
        assert result["reason_code"] == "OK_ROUTED"
        assert "reason_human" in result
        assert "routed_at" in result
        assert result["foundup_id"] == "move2japan"
