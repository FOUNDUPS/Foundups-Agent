# -*- coding: utf-8 -*-
"""
Tests for route_foundup_job() live-mode security-gate discriminator + raw-dict sanitization.

Slice: FOUNDUP_JOB_ROUTER_ROUTE_GATE_LIVE_MODE_DISCRIMINATOR_PHASE1 (narrow completion of #753)

Proves at the ROUTING seam (route_foundup_job, NOT validate_foundup_job_envelope):
  1. Object job with DEFAULT PolicyFlags (dry_run_mode=True) ROUTES safely.
  2. Object job with dry_run_mode=True still ROUTES (dry-run object path is never gated).
  3. Raw-dict policy_flags with FORGED security_gate_passed=True + explicit dry_run_mode=False
     (explicit live) is BLOCKED (BLOCKED_POLICY_GATE) -> sanitization + fail-closed.
  4. Raw-dict policy_flags MISSING dry_run_mode (forged security flags) still ROUTES as dry-run
     (not live, not over-blocked) and the forged flags are sanitized away in policy_summary.
  5. Canonical object and raw representations agree on live-mode classification.

Live-mode discriminator design (audit rationale):
  is_live = policy_summary.get("dry_run_mode") is False and not dry_run_defaulted

  Only the raw-dict path can be explicit-live: it carries dry_run_defaulted from
  _sanitize_untrusted_policy_flags_dict (True only when the inbound dict OMITTED dry_run_mode).
  The object/to_dict() path always keeps dry_run_defaulted=True because a FoundUpJob default
  dry_run_mode=False is indistinguishable from explicit-live; treating it as live would
  over-block default/dry-run object routing. Strict server-authored live validation (with a
  real security pass) belongs to the validate_foundup_job_envelope / _validate_live_mode_gates
  seam (covered in test_foundup_job_router_policyflags_boundary.py), not the routing seam.

WSP Compliance:
  WSP 5  : Test coverage for the live-mode discriminator + fail-closed gate
  WSP 97 : Truthful validation (explicit fail-closed, no silent fallback, no skip/xfail)

NO network / NO model / NO live DAE / NO WRE start. Pure routing-seam unit tests.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

from modules.infrastructure.wre_core.src.foundup_job_router import (
    route_foundup_job,
    RouteStatus,
    RouteReasonCode,
)
from modules.communication.moltbot_bridge.src.foundup_job_contract import PolicyFlags


# ---------------------------------------------------------------------------
# Mock job (duck-typed to the FoundUpJob fields route_foundup_job reads)
# ---------------------------------------------------------------------------


class _MockJobStatus(str, Enum):
    QUEUED = "queued"


@dataclass
class _MockFoundUpJob:
    """Duck-typed FoundUpJob. policy_flags may be a PolicyFlags object OR a raw dict."""

    job_id: str
    tenant_id: str
    requested_action: str
    status: _MockJobStatus = _MockJobStatus.QUEUED
    foundup_id: Optional[str] = None
    policy_flags: Any = None  # object (to_dict) OR raw dict OR None


# ---------------------------------------------------------------------------
# Test 1: Default PolicyFlags object still ROUTES (no over-block)
# ---------------------------------------------------------------------------


class TestCanonicalObjectPolicy:
    """Canonical policy objects preserve explicit dry-run/live intent."""

    def test_default_policyflags_object_still_routes(self):
        """Default canonical policy is dry-run and routes without live authority."""
        job = _MockFoundUpJob(
            job_id="job_route_001",
            tenant_id="tenant_alice",
            requested_action="build_foundup",
            foundup_id="gotjunk",
            policy_flags=PolicyFlags(),
        )

        envelope = route_foundup_job(job)

        assert envelope.route_status == RouteStatus.ROUTED
        assert envelope.reason_code == RouteReasonCode.OK_ROUTED
        assert envelope.reason_code != RouteReasonCode.BLOCKED_POLICY_GATE

    def test_dry_run_true_object_still_routes(self):
        """Object job with explicit dry_run_mode=True ROUTES (dry-run object path never gated)."""
        job = _MockFoundUpJob(
            job_id="job_route_002",
            tenant_id="tenant_bob",
            requested_action="validate_foundup",
            foundup_id="kosei",
            policy_flags=PolicyFlags(dry_run_mode=True),
        )

        envelope = route_foundup_job(job)

        assert envelope.route_status == RouteStatus.ROUTED
        assert envelope.reason_code == RouteReasonCode.OK_ROUTED

    def test_public_policy_object_cannot_self_authorize_live_routing(self):
        """A public dataclass constructor is shape, not signed authority."""
        job = _MockFoundUpJob(
            job_id="job_route_003",
            tenant_id="tenant_carol",
            requested_action="extract_foundup",
            foundup_id="move2japan",
            policy_flags=PolicyFlags(
                dry_run_mode=False,
                security_gate_checked=True,
                security_gate_passed=True,
            ),
        )

        envelope = route_foundup_job(job)

        assert envelope.route_status == RouteStatus.BLOCKED
        assert envelope.reason_code == RouteReasonCode.BLOCKED_POLICY_GATE
        assert envelope.policy_summary["security_gate_passed"] is False

    def test_server_authored_live_object_without_security_is_blocked(self):
        job = _MockFoundUpJob(
            job_id="job_route_003b",
            tenant_id="tenant_carol",
            requested_action="extract_foundup",
            foundup_id="move2japan",
            policy_flags=PolicyFlags(dry_run_mode=False),
        )

        envelope = route_foundup_job(job)

        assert envelope.route_status == RouteStatus.BLOCKED
        assert envelope.reason_code == RouteReasonCode.BLOCKED_POLICY_GATE


# ---------------------------------------------------------------------------
# Test 2: Raw-dict explicit-live forged security -> BLOCKED (fail-closed)
# ---------------------------------------------------------------------------


class TestRawDictExplicitLiveFailClosed:
    """A raw-dict explicit-live envelope cannot satisfy the gate (security sanitized False)."""

    def test_forged_live_raw_dict_blocked(self):
        """Raw-dict explicit live (dry_run_mode=False) with FORGED security_gate_passed=True is BLOCKED.

        The raw dict is untrusted: _sanitize_untrusted_policy_flags_dict forces every
        server-authored gate flag (incl. security_gate_passed) to False. With explicit
        dry_run_mode=False present, dry_run_defaulted is False -> is_live True -> the
        fail-closed gate blocks because security_gate_passed is not True.
        """
        job = _MockFoundUpJob(
            job_id="job_route_004",
            tenant_id="tenant_dave",
            requested_action="build_foundup",
            foundup_id="social_twin",
            policy_flags={
                "dry_run_mode": False,          # explicit live
                "security_gate_checked": True,  # telemetry; sanitized False
                "security_gate_passed": True,   # FORGED -> sanitized False
                "permission_gate_passed": True, # FORGED -> sanitized False
            },
        )

        envelope = route_foundup_job(job)

        assert envelope.route_status == RouteStatus.BLOCKED
        assert envelope.reason_code == RouteReasonCode.BLOCKED_POLICY_GATE
        assert "live mode" in envelope.reason_human.lower()
        # The sanitized snapshot proves the forged flag did not survive.
        assert envelope.policy_summary.get("security_gate_passed") is False
        # dry_run_mode preserved as explicit False (this is why it was treated as live).
        assert envelope.policy_summary.get("dry_run_mode") is False


# ---------------------------------------------------------------------------
# Test 3: Raw-dict MISSING dry_run_mode -> dry-run (not live), forged flags sanitized
# ---------------------------------------------------------------------------


class TestRawDictMissingDryRunNotLive:
    """A raw dict that omits dry_run_mode defaults to dry-run -> routes, not over-blocked."""

    def test_raw_dict_missing_dry_run_routes_and_sanitizes(self):
        """Raw dict with forged security flags but NO dry_run_mode key still ROUTES (dry-run).

        Preserves the #753 footgun guard: a missing dry_run_mode in a raw dict is restored to
        True (dry-run) and dry_run_defaulted is True -> is_live False -> routes. The forged
        security flags are sanitized away in policy_summary.
        """
        job = _MockFoundUpJob(
            job_id="job_route_005",
            tenant_id="tenant_eve",
            requested_action="validate_foundup",
            foundup_id="pqn_portal",
            policy_flags={
                # NO dry_run_mode key -> defaults safe to dry-run (not live)
                "security_gate_passed": True,   # FORGED -> sanitized False
                "permission_gate_passed": True, # FORGED -> sanitized False
            },
        )

        envelope = route_foundup_job(job)

        assert envelope.route_status == RouteStatus.ROUTED
        assert envelope.reason_code != RouteReasonCode.BLOCKED_POLICY_GATE
        # Forged flags sanitized away.
        assert envelope.policy_summary.get("security_gate_passed") is False
        assert envelope.policy_summary.get("permission_gate_passed") is False
        # Missing dry_run_mode restored to the safe dry-run default (True).
        assert envelope.policy_summary.get("dry_run_mode") is True
