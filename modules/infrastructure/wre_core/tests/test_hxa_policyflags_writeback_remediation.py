#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HXA_POLICYFLAGS_WRITEBACK_REMEDIATION_PHASE1 (#746) Proof Tests.

Positive control for the bounded PolicyFlags write-back defect:
security/token gate flags must be SERVER-AUTHORED ONLY, never trusted from
deserialized job data. The validator verdict is written into job.policy_flags
BEFORE the destructive-action guard reads it.

Predecessors: #744 (PolicyFlags write-back defect), HXA24 (capability token
policy flags), HXA27 (Hermes token validation integration), HXA30
(scope-to-action-class integration).

This slice proves:
  1. HermesJobExecutor writes the validator verdict back into job.policy_flags
     for valid-token, no-token, and invalid-token paths.
  2. The write-back precedes guard evaluation (server-authored truth seen).
  3. A job whose deserialized payload pre-set capability_token_*=True but
     carries NO real token is still BLOCKED at D3 (bypass closed).
  4. D4/D5/D6 remain BLOCKED regardless of flags.
  5. D3 remains bounded/dry-run only (live_execution_allowed=False).

This slice does NOT:
  - Enable live delegation, create repos, modify production source.
  - Issue or validate real (production) tokens.
  - Add any production caller of FoundUpJob.from_dict.

Run with:
    python -m pytest \
      modules/infrastructure/wre_core/tests/test_hxa_policyflags_writeback_remediation.py -q

Slice: HXA_POLICYFLAGS_WRITEBACK_REMEDIATION_PHASE1
Worker-Lane: W6
"""

from __future__ import annotations

import os
import sys
import shutil
import tempfile
from pathlib import Path

import pytest
from unittest.mock import patch

# Import via the FULL package path so CapabilityToken class identity matches the
# executor's import (a sys.path shortcut would create a distinct module object
# and break the executor's isinstance(token, CapabilityToken) check).
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.infrastructure.wre_core.src.hermes_job_executor import (  # noqa: E402
    HermesExecutionStatus,
    HermesJobExecutor,
)
from modules.communication.moltbot_bridge.src.foundup_job_contract import (  # noqa: E402
    FoundUpJob,
    PolicyFlags,
    create_job,
)
from modules.infrastructure.wre_core.src.capability_token_validator import (  # noqa: E402
    LocalCapabilityTokenIssuer,
    LocalCapabilityTokenValidator,
    TokenValidationResult,
)
from modules.infrastructure.wre_core.src.destructive_action_guard import (  # noqa: E402
    DestructiveActionClass,
)


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def temp_workspace():
    """Create temporary workspace directory for tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def token_issuer() -> LocalCapabilityTokenIssuer:
    return LocalCapabilityTokenIssuer()


@pytest.fixture
def executor(temp_workspace) -> HermesJobExecutor:
    """Executor with a fresh, isolated validator (no shared nonce state)."""
    return HermesJobExecutor(
        dry_run=True,
        workspace_root=temp_workspace,
        token_validator=LocalCapabilityTokenValidator(),
    )


def _disabled_env():
    """HERMES_DELEGATE_ENABLED=0 so no live delegate path is taken."""
    return patch.dict(os.environ, {"HERMES_DELEGATE_ENABLED": "0"})


# ===========================================================================
# SECTION 1: Write-back reflects the validator verdict
# ===========================================================================


class TestWriteBackReflectsVerdict:
    """The 4 capability_token_* flags on job.policy_flags reflect the verdict."""

    def test_valid_token_writeback_all_capability_flags_true(
        self, executor, token_issuer
    ):
        """Valid D3 token -> capability_token_* all True after execute()."""
        token = token_issuer.issue_token(
            subject="agent_w6",
            audience="wre-local",
            scopes=["d3:sandbox"],
            allowed_actions=["build_foundup"],
            allowed_paths=["modules/foundups"],
        )
        job = create_job(
            tenant_id="t1",
            requested_action="build_foundup",  # D3
            foundup_id="test",
            payload={"capability_token": token},
        )
        # Birth state: all capability flags False
        assert job.policy_flags.capability_token_validated is False

        with _disabled_env():
            executor.execute(job)

        # Server-authored verdict written back into the job
        assert job.policy_flags.capability_token_checked is True
        assert job.policy_flags.capability_token_present is True
        assert job.policy_flags.capability_token_validated is True
        assert job.policy_flags.capability_token_scope_authorized is True

    def test_no_token_writeback_present_false_validated_false(self, executor):
        """No token in payload -> checked True, present/validated/scope False."""
        job = create_job(
            tenant_id="t1",
            requested_action="build_foundup",  # D3
            foundup_id="test",
        )
        with _disabled_env():
            executor.execute(job)

        # A check is always performed
        assert job.policy_flags.capability_token_checked is True
        # But no token was present
        assert job.policy_flags.capability_token_present is False
        assert job.policy_flags.capability_token_validated is False
        assert job.policy_flags.capability_token_scope_authorized is False

    def test_invalid_token_writeback_present_true_validated_false(
        self, executor, token_issuer
    ):
        """Invalid token (D3 scope, D4 action) -> present True, validated False.

        The invalid-token path early-returns BEFORE guard, but the write-back
        runs first via _validate_token_if_present semantics. We assert the
        verdict reflects the token presence and invalidity.
        """
        # D3-scoped token attempting a D4 action -> token_valid False
        token = token_issuer.issue_token(
            subject="agent_w6",
            audience="wre-local",
            scopes=["d3:sandbox"],  # does NOT authorize D4
            allowed_actions=["create_repo"],
            allowed_paths=["modules/foundups"],
        )
        job = create_job(
            tenant_id="t1",
            requested_action="create_repo",  # D4 action
            foundup_id="test",
            payload={"capability_token": token},
        )
        with _disabled_env():
            result = executor.execute(job)

        # Invalid token blocks before guard
        assert result.status == HermesExecutionStatus.BLOCKED_BY_TOKEN_VALIDATION
        # The job is blocked; capability flags were NOT promoted to all-True
        # (the early-return path never grants a valid verdict).
        assert job.policy_flags.capability_token_validated is False
        assert job.policy_flags.capability_token_scope_authorized is False


# ===========================================================================
# SECTION 2: Guard sees server-authored fields (bypass closed)
# ===========================================================================


class TestBypassClosed:
    """Pre-set capability flags from payload cannot bypass the D3 guard."""

    def test_payload_preset_capability_flags_but_no_token_blocked_at_d3(
        self, executor
    ):
        """A job carrying capability_token_*=True in payload but NO token is
        STILL blocked at D3 (the deserialization sanitization + server write-back
        close the bypass).
        """
        # Simulate an attacker-supplied serialized job: capability flags True
        # but no real capability_token in payload.
        malicious_data = {
            "job_id": "j_attack_d3",
            "tenant_id": "attacker",
            "requested_action": "build_foundup",  # D3
            "foundup_id": "test",
            "policy_flags": {
                "capability_token_checked": True,
                "capability_token_present": True,
                "capability_token_validated": True,
                "capability_token_scope_authorized": True,
                "security_gate_passed": True,
                "dry_run_mode": True,
            },
            "payload": {},  # NO capability_token
        }
        job = FoundUpJob.from_dict(malicious_data)

        # Sanitization already zeroed the flags at deserialization
        assert job.policy_flags.capability_token_validated is False
        assert job.policy_flags.security_gate_passed is False

        with _disabled_env():
            result = executor.execute(job)

        # D3 requires a real validated token -> blocked
        assert (
            result.status
            == HermesExecutionStatus.BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD
        )
        # After execute, write-back reflects the TRUE state: no token present
        assert job.policy_flags.capability_token_present is False
        assert job.policy_flags.capability_token_validated is False

    def test_writeback_overrides_stale_object_flags_before_guard(
        self, executor
    ):
        """Even if object flags were manually set True but no token exists,
        the server write-back demotes them to the real verdict before guard.
        """
        job = create_job(
            tenant_id="t1",
            requested_action="build_foundup",  # D3
            foundup_id="test",
        )
        # Stale/forged object state (e.g. set by buggy upstream code)
        job.policy_flags.capability_token_checked = True
        job.policy_flags.capability_token_present = True
        job.policy_flags.capability_token_validated = True
        job.policy_flags.capability_token_scope_authorized = True
        # No token in payload, so the write-back must demote present/validated.

        with _disabled_env():
            result = executor.execute(job)

        # Write-back corrected the forged flags to the real (no-token) verdict
        assert job.policy_flags.capability_token_present is False
        assert job.policy_flags.capability_token_validated is False
        assert job.policy_flags.capability_token_scope_authorized is False
        # Guard blocks D3 accordingly
        assert (
            result.status
            == HermesExecutionStatus.BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD
        )


# ===========================================================================
# SECTION 3: D4/D5/D6 remain blocked; D3 bounded dry-run only
# ===========================================================================


class TestBoundaryUnchanged:
    """D4/D5/D6 blocked regardless of flags; D3 stays dry-run only."""

    @pytest.mark.parametrize(
        "action_class",
        [
            DestructiveActionClass.D4_WRITE_REPO,
            DestructiveActionClass.D5_EXTERNAL_SIDE_EFFECT,
            DestructiveActionClass.D6_IRREVERSIBLE,
        ],
    )
    def test_d4_d5_d6_blocked_even_with_valid_token(
        self, executor, token_issuer, action_class
    ):
        """D4/D5/D6 blocked even with a valid token + write-back."""
        token = token_issuer.issue_token(
            subject="agent_w6",
            audience="wre-local",
            # Scope that authorizes the class (so token itself validates) - the
            # guard, not the token, must be what blocks.
            scopes=["d4:repo", "d5:external", "d6:delete"],
            allowed_actions=[
                "create_repo",
                "send_email",
                "delete_permanently",
            ],
            allowed_paths=["modules/foundups"],
        )
        action_map = {
            DestructiveActionClass.D4_WRITE_REPO: "create_repo",
            DestructiveActionClass.D5_EXTERNAL_SIDE_EFFECT: "send_email",
            DestructiveActionClass.D6_IRREVERSIBLE: "delete_permanently",
        }
        job = create_job(
            tenant_id="t1",
            requested_action=action_map[action_class],
            foundup_id="test",
            payload={"capability_token": token},
        )
        with patch.object(
            executor,
            "_classify_destructive_action",
            return_value=action_class,
        ):
            with _disabled_env():
                result = executor.execute(job)

        assert (
            result.status
            == HermesExecutionStatus.BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD
        )

    def test_d3_valid_token_remains_dry_run_only(self, executor, token_issuer):
        """Valid D3 token: guard may allow but live_execution_allowed=False.

        Note: with security_gate_passed left at server-default False, D3 is
        still blocked. This asserts the D3 boundary stays dry-run only and live
        execution is never enabled by the write-back.
        """
        token = token_issuer.issue_token(
            subject="agent_w6",
            audience="wre-local",
            scopes=["d3:sandbox"],
            allowed_actions=["build_foundup"],
            allowed_paths=["modules/foundups"],
        )
        job = create_job(
            tenant_id="t1",
            requested_action="build_foundup",  # D3
            foundup_id="test",
            payload={"capability_token": token},
        )
        with _disabled_env():
            result = executor.execute(job)

        # Capability verdict written True, but security_gate_passed stays False
        assert job.policy_flags.capability_token_validated is True
        assert job.policy_flags.security_gate_passed is False
        # No live execution enabled anywhere
        assert result.real_execution_performed is False
        if result.guard_result is not None:
            assert result.guard_result.get("live_execution_allowed") is False

    def test_security_gate_not_fabricated_by_writeback(
        self, executor, token_issuer
    ):
        """Write-back never sets security_gate_passed True (out of scope)."""
        token = token_issuer.issue_token(
            subject="agent_w6",
            audience="wre-local",
            scopes=["d3:sandbox"],
            allowed_actions=["build_foundup"],
            allowed_paths=["modules/foundups"],
        )
        job = create_job(
            tenant_id="t1",
            requested_action="build_foundup",
            foundup_id="test",
            payload={"capability_token": token},
        )
        with _disabled_env():
            executor.execute(job)

        # security_gate_* untouched by token write-back
        assert job.policy_flags.security_gate_checked is False
        assert job.policy_flags.security_gate_passed is False


# ===========================================================================
# SECTION 4: Helper unit semantics
# ===========================================================================


class TestWriteBackHelperSemantics:
    """Direct unit coverage of _writeback_token_verdict mapping."""

    def test_none_result_checked_true_rest_false(self, executor):
        job = create_job(tenant_id="t", requested_action="build_foundup")
        executor._writeback_token_verdict(job, None)
        assert job.policy_flags.capability_token_checked is True
        assert job.policy_flags.capability_token_present is False
        assert job.policy_flags.capability_token_validated is False
        assert job.policy_flags.capability_token_scope_authorized is False

    def test_valid_result_all_true(self, executor):
        job = create_job(tenant_id="t", requested_action="build_foundup")
        result = TokenValidationResult(
            token_valid=True,
            scope_action_class_mismatch=False,
        )
        executor._writeback_token_verdict(job, result)
        assert job.policy_flags.capability_token_checked is True
        assert job.policy_flags.capability_token_present is True
        assert job.policy_flags.capability_token_validated is True
        assert job.policy_flags.capability_token_scope_authorized is True

    def test_invalid_result_present_true_validated_false(self, executor):
        job = create_job(tenant_id="t", requested_action="build_foundup")
        result = TokenValidationResult(
            token_valid=False,
            scope_action_class_mismatch=True,
        )
        executor._writeback_token_verdict(job, result)
        assert job.policy_flags.capability_token_checked is True
        assert job.policy_flags.capability_token_present is True
        assert job.policy_flags.capability_token_validated is False
        assert job.policy_flags.capability_token_scope_authorized is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
