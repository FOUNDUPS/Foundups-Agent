# -*- coding: utf-8 -*-
"""
DAE Gateway PolicyFlags regression guards (Phase 1).

Slice: HXA_POLICYFLAGS_REGRESSION_GUARDS_PHASE1
Worker-Lane: W6

Gateway-boundary guards for the PolicyFlags trust chain. The wre_gateway module
had NO tests/ directory before this slice; these are the first gateway tests.

Guards in this file:
  G2  GATEWAY VALIDATION AVAILABLE (test-only health check, NOT a production
        startup assertion): importing dae_gateway in a healthy env yields
        FOUNDUP_JOB_VALIDATION_AVAILABLE is True (the WSP 97 envelope validator
        import succeeded).
  G3  GATEWAY E2E D3 FAIL-CLOSED: route_to_dae with a FOUNDUP_JOB-typed envelope
        carrying FORGED security_gate_passed=True + dry_run_mode=False is
        BLOCKED, and (via spies) _invoke_core_dae / _invoke_foundup_dae are NOT
        called - the request is rejected BEFORE any DAE dispatch. No live /
        network / model / process.
  G5  GATEWAY PERMISSIVE-FALLBACK GUARD: with FOUNDUP_JOB_VALIDATION_AVAILABLE
        monkeypatched False, degraded behavior is known/bounded: a FoundUpJob-
        shaped envelope lacking 'objective' is still blocked, and even a generic
        envelope that DOES dispatch in degraded mode reaches only the pattern-
        recall stubs - never route_foundup_job / Hermes execute / destructive
        execution (the gateway module does not import or call those at all).

Blocked-before-dispatch is proven with mocks/spies on the two dispatch methods;
no test starts WRE/DAE/Hermes or touches the network. route_to_dae is async, so
each test drives it with asyncio.run.

Mirrors existing patterns:
  test_foundup_job_router_policyflags_boundary.py (forged-flag fail-closed)
  test_route_foundup_job_live_mode_gate.py (live-mode gate semantics)

WSP Compliance:
  WSP 5  : Test coverage for the gateway boundary
  WSP 97 : Truthful, fail-closed assertions

NO network / NO model / NO live DAE / NO WRE start.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any, Dict

from unittest.mock import AsyncMock, patch

import pytest

# Import via the FULL package path so class identity matches production imports.
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.infrastructure.wre_core.wre_gateway.src import dae_gateway as gw  # noqa: E402
from modules.infrastructure.wre_core.wre_gateway.src.dae_gateway import (  # noqa: E402
    DAEGateway,
    FOUNDUP_JOB_VALIDATION_AVAILABLE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _forged_live_foundup_job_envelope() -> Dict[str, Any]:
    """A FOUNDUP_JOB-typed envelope with a FORGED passing security gate in live mode.

    Has >=2 FoundUpJob signature fields (job_id, foundup_id, tenant_id,
    requested_action) so detect_envelope_type classifies it as FOUNDUP_JOB. It
    self-asserts security_gate_passed=True and requests live mode
    (dry_run_mode=False). The router boundary sanitizes the forged flag to False,
    so live-mode gate validation must FAIL closed and the gateway must block.
    """
    return {
        "job_id": "forged_g3_001",
        "foundup_id": "gotjunk",
        "tenant_id": "tenant_attacker",
        "requested_action": "build_foundup",
        "policy_flags": {
            "security_gate_passed": True,   # forged - sanitized to False upstream
            "permission_gate_passed": True,  # forged - sanitized to False upstream
            "dry_run_mode": False,           # explicit live mode request
        },
        "evidence_refs": ["manifest.json"],
        "compute_budget": 5000,
    }


# ---------------------------------------------------------------------------
# G2: GATEWAY VALIDATION AVAILABLE (test-only health check)
# ---------------------------------------------------------------------------


class TestG2GatewayValidationAvailable:
    """G2: the WSP 97 envelope validator import is wired in a healthy env."""

    def test_foundup_job_validation_available_is_true(self):
        """In a healthy env the validator import succeeded.

        This is a TEST-ONLY health assertion (it guards against the envelope
        validator import silently breaking, which would degrade the gateway to
        permissive validation). It is NOT a production startup assertion - the
        gateway intentionally degrades rather than crashing (see G5).
        """
        assert FOUNDUP_JOB_VALIDATION_AVAILABLE is True, (
            "FOUNDUP_JOB_VALIDATION_AVAILABLE is False - the WSP 97 envelope "
            "validator import in dae_gateway failed; the gateway would fall back "
            "to permissive validation. Investigate the import in dae_gateway.py."
        )

    def test_module_level_flag_matches_imported_flag(self):
        """The module attribute and the imported name agree (no shadowing)."""
        assert gw.FOUNDUP_JOB_VALIDATION_AVAILABLE is FOUNDUP_JOB_VALIDATION_AVAILABLE

    def test_g2_negative_control_flag_false_would_fail(self):
        """SYNTHETIC negative control: when the flag is False, the G2 check fails.

        Monkeypatch the module flag to False and assert the same health condition
        the guard relies on no longer holds - proving G2 is non-vacuous. No
        production state is mutated beyond the test-scoped patch.
        """
        with patch.object(gw, "FOUNDUP_JOB_VALIDATION_AVAILABLE", False):
            assert gw.FOUNDUP_JOB_VALIDATION_AVAILABLE is False
            with pytest.raises(AssertionError):
                assert gw.FOUNDUP_JOB_VALIDATION_AVAILABLE is True


# ---------------------------------------------------------------------------
# G3: GATEWAY E2E D3 FAIL-CLOSED (blocked BEFORE dispatch)
# ---------------------------------------------------------------------------


class TestG3GatewayFailClosedBeforeDispatch:
    """G3: forged live FoundUpJob envelope blocked before any DAE dispatch."""

    def test_forged_security_gate_live_envelope_is_blocked(self):
        """route_to_dae returns a validation error for the forged live envelope."""
        gateway = DAEGateway()
        envelope = _forged_live_foundup_job_envelope()

        # Spy/mocks on BOTH dispatch methods so we can prove non-invocation AND
        # that nothing downstream (executor/Hermes) is reached - the dispatch
        # methods are the only doorway to any DAE work.
        with patch.object(gateway, "_invoke_core_dae", new=AsyncMock()) as mock_core, \
             patch.object(gateway, "_invoke_foundup_dae", new=AsyncMock()) as mock_foundup:
            result = asyncio.run(gateway.route_to_dae("infrastructure", envelope))

        # Blocked: a WSP 97 validation error is returned, not a DAE response.
        assert "error" in result, f"expected block, got dispatch result: {result}"
        assert result.get("envelope_type") == "foundup_job"
        # Fail-closed because the forged security gate was sanitized to False.
        assert result.get("validation_code") in (
            "LIVE_MODE_REQUIRES_SECURITY_GATE",
            "LIVE_MODE_REQUIRES_HUMAN_APPROVAL",
        ), f"unexpected validation_code: {result.get('validation_code')}"

        # Blocked BEFORE dispatch: neither core nor FoundUp DAE was invoked.
        assert mock_core.called is False, (
            "_invoke_core_dae was called - forged envelope reached DAE dispatch!"
        )
        assert mock_foundup.called is False, (
            "_invoke_foundup_dae was called - forged envelope reached DAE dispatch!"
        )

    def test_violations_prevented_metric_incremented_on_block(self):
        """The block path increments violations_prevented (observability)."""
        gateway = DAEGateway()
        envelope = _forged_live_foundup_job_envelope()
        before = gateway.metrics["violations_prevented"]

        with patch.object(gateway, "_invoke_core_dae", new=AsyncMock()), \
             patch.object(gateway, "_invoke_foundup_dae", new=AsyncMock()):
            asyncio.run(gateway.route_to_dae("infrastructure", envelope))

        assert gateway.metrics["violations_prevented"] == before + 1

    def test_g3_negative_control_broken_verify_would_dispatch(self):
        """SYNTHETIC negative control: a broken _verify_envelope DOES dispatch.

        Proves the G3 'not called' assertion is non-vacuous. We monkeypatch
        _verify_envelope to return True (simulating a removed/broken sanitizer);
        the SAME forged envelope then reaches _invoke_core_dae. No production
        code is edited - the bypass is a test-local monkeypatch only.
        """
        gateway = DAEGateway()
        envelope = _forged_live_foundup_job_envelope()
        sentinel = {"dispatched": True}

        with patch.object(gateway, "_verify_envelope", return_value=True), \
             patch.object(
                 gateway, "_invoke_core_dae", new=AsyncMock(return_value=sentinel)
             ) as mock_core, \
             patch.object(gateway, "_invoke_foundup_dae", new=AsyncMock()) as mock_foundup:
            result = asyncio.run(gateway.route_to_dae("infrastructure", envelope))

        # With the guard broken, the forged envelope DOES reach dispatch.
        assert result == sentinel
        assert mock_core.called is True
        assert mock_foundup.called is False

    def test_gateway_module_has_no_execution_path_imports(self):
        """Structural: the gateway never imports the FoundUpJob execution path.

        Proves blocked-before-dispatch is also blocked-before-EXECUTION: the
        gateway module does not import route_foundup_job, HermesJobExecutor, or
        execute_foundup_job, so no gateway code path can reach destructive
        execution regardless of routing.
        """
        source = Path(gw.__file__).read_text(encoding="utf-8-sig")
        for forbidden in (
            "route_foundup_job",
            "HermesJobExecutor",
            "execute_foundup_job",
            "hermes_job_executor",
        ):
            assert forbidden not in source, (
                f"dae_gateway.py references '{forbidden}' - the gateway must not "
                "import the FoundUpJob execution path (no live execution from the "
                "routing layer)."
            )


# ---------------------------------------------------------------------------
# G5: GATEWAY PERMISSIVE-FALLBACK GUARD (degraded behavior is bounded)
# ---------------------------------------------------------------------------


class TestG5PermissiveFallbackBounded:
    """G5: with validation unavailable, degraded behavior stays bounded."""

    def test_degraded_foundupjob_without_objective_is_blocked(self):
        """Validation unavailable: a FoundUpJob-shaped envelope w/o 'objective' is blocked.

        Permissive validation requires 'objective'. A FoundUpJob-shaped envelope
        omits it, so even in the degraded path it is rejected before dispatch.
        """
        gateway = DAEGateway()
        envelope = _forged_live_foundup_job_envelope()  # no 'objective' field

        with patch.object(gw, "FOUNDUP_JOB_VALIDATION_AVAILABLE", False), \
             patch.object(gateway, "_invoke_core_dae", new=AsyncMock()) as mock_core, \
             patch.object(gateway, "_invoke_foundup_dae", new=AsyncMock()) as mock_foundup:
            result = asyncio.run(gateway.route_to_dae("infrastructure", envelope))

        assert "error" in result, f"degraded path should block, got: {result}"
        assert mock_core.called is False
        assert mock_foundup.called is False

    def test_degraded_dispatch_reaches_only_pattern_recall_stub(self):
        """Validation unavailable + valid generic envelope: dispatch reaches ONLY the stub.

        This is the bounded-degradation proof: even when permissive validation
        passes (envelope has 'objective') and the request DOES dispatch, it lands
        on the _invoke_core_dae pattern-recall stub. The gateway never calls
        route_foundup_job / Hermes execute / destructive execution (verified
        structurally in G3's no-import test), so degraded mode cannot escalate to
        live execution.
        """
        gateway = DAEGateway()
        # Generic envelope that passes permissive validation (objective present).
        # It carries forged gate flags, but the gateway routing layer never
        # consumes them for execution.
        envelope = {
            "objective": "do something",
            "job_id": "degraded_g5_001",
            "foundup_id": "gotjunk",
            "policy_flags": {"security_gate_passed": True, "dry_run_mode": False},
        }

        sentinel = {"dae": "infrastructure", "stub": True}
        with patch.object(gw, "FOUNDUP_JOB_VALIDATION_AVAILABLE", False), \
             patch.object(
                 gateway, "_invoke_core_dae", new=AsyncMock(return_value=sentinel)
             ) as mock_core, \
             patch.object(gateway, "_invoke_foundup_dae", new=AsyncMock()) as mock_foundup:
            result = asyncio.run(gateway.route_to_dae("infrastructure", envelope))

        # Reached the core DAE stub (and ONLY the stub) - no FoundUp dispatch.
        assert result == sentinel
        assert mock_core.called is True
        assert mock_foundup.called is False

    def test_g5_negative_control_healthy_env_blocks_forged_live(self):
        """SYNTHETIC negative control: when validation IS available, the forged

        live envelope is blocked by the STRICT path (contrast with the degraded
        path). Proves the monkeypatch in the other G5 tests is what changes
        behavior - i.e. the guard is sensitive to the FOUNDUP_JOB_VALIDATION_
        AVAILABLE flag and not vacuously passing.
        """
        gateway = DAEGateway()
        envelope = _forged_live_foundup_job_envelope()

        # No monkeypatch: validation available -> strict block with WSP 97 code.
        with patch.object(gateway, "_invoke_core_dae", new=AsyncMock()) as mock_core, \
             patch.object(gateway, "_invoke_foundup_dae", new=AsyncMock()) as mock_foundup:
            result = asyncio.run(gateway.route_to_dae("infrastructure", envelope))

        assert result.get("envelope_type") == "foundup_job"
        assert "validation_code" in result
        assert mock_core.called is False
        assert mock_foundup.called is False
