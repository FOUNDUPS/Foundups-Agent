"""Characterization tests for OpenClaw WSP 109 onboarding + FOUNDUP routing.

Slice:      OPENCLAW_WSP109_ONBOARDING_DRYRUN_TEST_PHASE1 (Worker-Lane W6)
Precedent:  PR #737 OPUS_4_8_OPENCLAW_INTERNAL_MODEL_PROBE_PHASE1
Audit:      docs/audits/architecture/OPENCLAW_WSP109_ONBOARDING_DRYRUN_TEST_PHASE1.md

PURPOSE
    Capture the CURRENT OpenClaw behaviour around WSP 109 onboarding and FOUNDUP
    routing as executable evidence. This slice characterises; it does NOT fix.
    The known gaps from #737 are locked as STRICT xfail tests whose assertions
    describe the DESIRED post-remediation behaviour. When the remediation slice
    (OPENCLAW_WSP109_GENESIS_GATE_REMEDIATION_PHASE1) lands, the strict xfails
    will XPASS and fail the suite, signalling that these tests must be promoted
    to real assertions.

DETERMINISM (hard constraints for this slice)
    Pure-function calls, source inspection, and lightweight MagicMock only.
    No live OpenClaw process. No network. No .env reads. No external model calls.
    No real GitHub writes. No production code is imported for mutation.
"""

import inspect
import sys

import pytest
from unittest.mock import patch, MagicMock

# Future remediation slice that these xfail contracts target.
REMEDIATION_SLICE = "OPENCLAW_WSP109_GENESIS_GATE_REMEDIATION_PHASE1"


class TestWSP109OnboardingClassification:
    """Q1: Does a WSP 109 onboarding prompt route through intake/governance,
    or directly toward FOUNDUP execution?"""

    ONBOARD_MSG = "Follow WSP 109 and onboard a FoundUp called Shield."

    def test_onboard_prompt_is_not_explicit_build_intent_CURRENT(self):
        """CURRENT: 'onboard' is not a recognised build/intake trigger, so the
        prompt is not treated as an explicit (gateable) build intent and falls
        through to FAM passthrough. (#737 S1)"""
        from modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator import (
            _is_explicit_build_intent,
            _FOUNDUP_BUILD_WORDS,
        )

        assert "onboard" not in " ".join(_FOUNDUP_BUILD_WORDS)
        assert _is_explicit_build_intent(self.ONBOARD_MSG) is False

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "Current OpenClaw lacks a WSP 109 genesis/intake gate: 'onboard ... "
            "FoundUp' routes to FAM passthrough with no intake validation (#737 "
            "S1). Remediation: " + REMEDIATION_SLICE
        ),
    )
    def test_onboard_prompt_should_route_through_intake_REMEDIATION(self):
        """DESIRED (remediation contract): a WSP 109 onboarding prompt is
        recognised as an explicit, gateable intake/build intent."""
        from modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator import (
            _is_explicit_build_intent,
        )

        assert _is_explicit_build_intent(self.ONBOARD_MSG) is True


class TestFoundupGenesisGateVisibility:
    """Q2: Does FOUNDUP routing call a gated genesis-envelope validator before
    execution?"""

    def test_dispatch_foundup_does_not_invoke_genesis_validator_CURRENT(self):
        """CURRENT: the live dispatch_foundup never references
        validate_genesis_envelope; it routes to the dry-run queue or FAM
        passthrough instead. (#737 S1 / 9.1#1)"""
        from modules.communication.moltbot_bridge.src import (
            openclaw_foundup_orchestrator,
        )

        source = inspect.getsource(openclaw_foundup_orchestrator.dispatch_foundup)
        assert "validate_genesis_envelope" not in source
        assert ("handle_fam_intent" in source) or ("_handle_build_intent" in source)

    def test_fam_passthrough_reached_without_genesis_for_launch_msg_CURRENT(self):
        """CURRENT: a bare 'launch foundup' message (not an explicit-build phrase)
        reaches fam_adapter.handle_fam_intent with no genesis gate in between."""
        mock_intent = MagicMock()
        mock_intent.raw_message = "launch foundup Shield with token SHLD"
        mock_intent.sender = "012"
        mock_dae = MagicMock()

        mock_fam = MagicMock()
        mock_fam.handle_fam_intent = MagicMock(return_value="FAM passthrough result")

        from modules.communication.moltbot_bridge.src import (
            openclaw_foundup_orchestrator,
        )

        # dispatch_foundup performs a function-local `from .fam_adapter import
        # handle_fam_intent` at call time, so patching sys.modules is sufficient.
        # Deliberately NO importlib.reload: reloading the orchestrator under a
        # mocked fam_adapter pollutes the module for downstream tests.
        with patch.dict(
            sys.modules,
            {"modules.communication.moltbot_bridge.src.fam_adapter": mock_fam},
        ):
            result = openclaw_foundup_orchestrator.dispatch_foundup(
                mock_dae, mock_intent
            )

        mock_fam.handle_fam_intent.assert_called_once()
        assert result == "FAM passthrough result"

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "FOUNDUP launch reaches fam_adapter.launch_foundup via FAM passthrough "
            "with no genesis-envelope validation; the gated launch_foundup/"
            "validate_genesis_envelope methods are defined but never invoked by the "
            "live dispatch (#737 9.1#1). Remediation: " + REMEDIATION_SLICE
        ),
    )
    def test_foundup_dispatch_should_be_genesis_gated_REMEDIATION(self):
        """DESIRED (remediation contract): dispatch_foundup validates a genesis
        envelope before any FoundUp launch."""
        from modules.communication.moltbot_bridge.src import (
            openclaw_foundup_orchestrator,
        )

        source = inspect.getsource(openclaw_foundup_orchestrator.dispatch_foundup)
        assert "validate_genesis_envelope" in source


class TestDualParserAmbiguity:
    """Q3: Can 'create foundup X' and 'create foundup job' diverge into different
    parser paths?"""

    def test_create_foundup_variants_diverge_CURRENT(self):
        """CURRENT: bare 'create foundup X' is NOT an explicit-build phrase (-> FAM
        passthrough, can reach a real launch) while 'create foundup job' IS (->
        queued dry-run FoundUpJob). Same leading words, divergent paths. (#737
        9.1#2)"""
        from modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator import (
            _is_explicit_build_intent,
        )

        bare = _is_explicit_build_intent("create foundup Shield")
        jobish = _is_explicit_build_intent("create foundup job for Shield")

        assert bare is False
        assert jobish is True
        assert bare != jobish  # divergence locked as current behaviour

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "'create foundup X' (FAM passthrough / can launch for real) and 'create "
            "foundup job' (queue dry-run) route through different parser paths with "
            "shared trigger words (#737 9.1#2). Remediation: " + REMEDIATION_SLICE
        ),
    )
    def test_create_foundup_variants_should_converge_REMEDIATION(self):
        """DESIRED (remediation contract): both create-foundup phrasings resolve to
        the same gated entrypoint."""
        from modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator import (
            _is_explicit_build_intent,
        )

        bare = _is_explicit_build_intent("create foundup Shield")
        jobish = _is_explicit_build_intent("create foundup job for Shield")
        assert bare == jobish


class TestW10HandoffAbsence:
    """Q4: Does any current path produce a W10 handoff packet, or does
    validate_and_remember self-approve?"""

    def test_validate_and_remember_self_approves_no_w10_CURRENT(self):
        """CURRENT: success is computed from wsp_violations (empty-response +
        secret-scan) only; there is no W10 / READY / NOT_READY handoff authority.
        (#737 9.1#3)"""
        from modules.communication.moltbot_bridge.src import openclaw_result_memory

        source = inspect.getsource(openclaw_result_memory.validate_and_remember)
        assert "success=len(wsp_violations) == 0" in source
        for token in ("W10", "READY", "NOT_READY", "handoff"):
            assert token not in source

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "validate_and_remember self-approves success on empty-response + "
            "secret-scan only; no W10 READY/NOT_READY pre-merge handoff packet is "
            "produced (#737 9.1#3). Remediation: " + REMEDIATION_SLICE
        ),
    )
    def test_mutating_path_should_emit_w10_handoff_REMEDIATION(self):
        """DESIRED (remediation contract): a mutating outcome emits a W10 handoff
        packet (READY/NOT_READY), not a self-approved success flag."""
        from modules.communication.moltbot_bridge.src import openclaw_result_memory

        source = inspect.getsource(openclaw_result_memory.validate_and_remember)
        assert ("W10" in source) or ("handoff" in source) or ("NOT_READY" in source)


class TestProtectedPathRemainsBlocked:
    """Q5: Protected-path edits remain blocked. These MUST PASS (not xfail) so the
    suite does not imply every gate is broken. Preserves #737 S5 proof."""

    PROTECTED_MSG = "modify modules/communication/moltbot_bridge/src/openclaw_dae.py"

    def test_protected_path_edit_is_source_modification_PASS(self):
        """A code edit naming a protected *_dae.py path is classified as a source
        modification (-> SOURCE tier)."""
        from modules.communication.moltbot_bridge.src.openclaw_permission_policy import (
            is_source_modification,
        )

        intent = MagicMock()
        intent.raw_message = self.PROTECTED_MSG
        assert is_source_modification(MagicMock(), intent) is True

    def test_source_tier_fails_closed_without_permission_manager_PASS(self):
        """SOURCE-tier write is denied FAIL-CLOSED when no permission manager is
        loaded (#737 S5: fail-closed enforcement)."""
        from modules.communication.moltbot_bridge.src.openclaw_permission_policy import (
            check_source_permission,
        )

        dae = MagicMock()
        dae.permissions = None  # permission manager unavailable -> fail closed
        intent = MagicMock()
        intent.raw_message = self.PROTECTED_MSG

        granted, reason = check_source_permission(dae, intent)
        assert granted is False
        assert "permission manager unavailable" in reason


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
