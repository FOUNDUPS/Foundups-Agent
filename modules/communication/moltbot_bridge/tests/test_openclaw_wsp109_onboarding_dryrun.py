"""WSP 109 onboarding + FOUNDUP routing tests (remediated).

Slice:      OPENCLAW_WSP109_GENESIS_GATE_REMEDIATION_PHASE1 (Worker-Lane W6)
History:    Created as strict-xfail characterization in PR #738
            (OPENCLAW_WSP109_ONBOARDING_DRYRUN_TEST_PHASE1); the four xfail
            contracts are now CONVERTED to passing assertions by this remediation.
Precedent:  PR #737 OPUS_4_8_OPENCLAW_INTERNAL_MODEL_PROBE_PHASE1

WHAT CHANGED (remediation, no second orchestration layer):
- Launch/onboard intents now pass through the WSP 109 genesis gate
  (`dispatch_foundup` -> `validate_genesis_envelope`) before any FAM launch; with
  no envelope they return a NOT_READY W10 handoff instead of launching.
- `create foundup X` and `create foundup job for X` converge on the safe dry-run
  queue path (no launch).
- `validate_and_remember` emits a W10 READY/NOT_READY handoff for FOUNDUP work
  instead of self-approving.
- Protected-path edits remain fail-closed BLOCKED (preserved from #737 S5).

DETERMINISM: pure-function + `inspect.getsource` + lightweight MagicMock only.
`validate_genesis_envelope({})` short-circuits to NO_ENVELOPE before loading any
validator, so no live process / network / .env / model calls occur.
"""

import inspect
import sys

import pytest
from unittest.mock import patch, MagicMock


class TestWSP109OnboardingGated:
    """A WSP 109 onboarding prompt is recognised and routed through the genesis
    gate (intake/handoff), not launched directly."""

    ONBOARD_MSG = "Follow WSP 109 and onboard a FoundUp called Shield."

    def test_onboard_is_launch_or_onboard_intent(self):
        """'onboard ... FoundUp' is recognised as a gateable launch/onboard intent."""
        from modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator import (
            _is_foundup_launch_or_onboard_intent,
        )

        assert _is_foundup_launch_or_onboard_intent(self.ONBOARD_MSG) is True

    def test_onboard_dispatch_returns_not_ready_handoff(self):
        """Dispatching an onboarding prompt returns a NOT_READY genesis handoff and
        does NOT reach fam_adapter (no launch)."""
        mock_intent = MagicMock()
        mock_intent.raw_message = self.ONBOARD_MSG
        mock_intent.sender = "012"
        mock_intent.is_authorized_commander = True
        mock_intent.payload = None  # no genesis envelope present
        mock_dae = MagicMock()

        mock_fam = MagicMock()
        mock_fam.handle_fam_intent = MagicMock(return_value="SHOULD NOT BE CALLED")

        from modules.communication.moltbot_bridge.src import (
            openclaw_foundup_orchestrator,
        )

        with patch.dict(
            sys.modules,
            {"modules.communication.moltbot_bridge.src.fam_adapter": mock_fam},
        ):
            result = openclaw_foundup_orchestrator.dispatch_foundup(
                mock_dae, mock_intent
            )

        assert "NOT_READY" in result
        assert "WSP_109" in result or "WSP 109" in result
        mock_fam.handle_fam_intent.assert_not_called()
        # No false execution claim.
        for token in ("executed", "launched successfully", "completed"):
            assert token not in result.lower()


class TestFoundupGenesisGate:
    """FOUNDUP dispatch invokes the genesis validator before any launch."""

    def test_dispatch_foundup_invokes_genesis_validator(self):
        """dispatch_foundup now references validate_genesis_envelope (gate wired)."""
        from modules.communication.moltbot_bridge.src import (
            openclaw_foundup_orchestrator,
        )

        source = inspect.getsource(openclaw_foundup_orchestrator.dispatch_foundup)
        assert "validate_genesis_envelope" in source

    def test_launch_msg_is_gated_not_fam_passthrough(self):
        """A bare 'launch foundup' message is gated (NOT_READY), not handed to FAM."""
        mock_intent = MagicMock()
        mock_intent.raw_message = "launch foundup Shield with token SHLD"
        mock_intent.sender = "012"
        mock_intent.is_authorized_commander = True
        mock_intent.payload = None
        mock_dae = MagicMock()

        mock_fam = MagicMock()
        mock_fam.handle_fam_intent = MagicMock(return_value="SHOULD NOT BE CALLED")

        from modules.communication.moltbot_bridge.src import (
            openclaw_foundup_orchestrator,
        )

        with patch.dict(
            sys.modules,
            {"modules.communication.moltbot_bridge.src.fam_adapter": mock_fam},
        ):
            result = openclaw_foundup_orchestrator.dispatch_foundup(
                mock_dae, mock_intent
            )

        assert "NOT_READY" in result
        mock_fam.handle_fam_intent.assert_not_called()


class TestDualParserConverged:
    """'create foundup X' and 'create foundup job for X' converge on one path."""

    def test_create_foundup_variants_converge(self):
        """Both create-foundup phrasings resolve identically (safe dry-run queue)."""
        from modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator import (
            _is_explicit_build_intent,
        )

        bare = _is_explicit_build_intent("create foundup Shield")
        jobish = _is_explicit_build_intent("create foundup job for Shield")
        assert bare is True
        assert jobish is True
        assert bare == jobish

    def test_create_foundup_variants_both_queue_no_launch(self):
        """Both phrasings create a QUEUED dry-run job; neither reaches FAM launch."""
        from modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator import (
            dispatch_foundup,
            clear_job_queue,
            get_job_queue,
        )

        for msg in ("create foundup Shield", "create foundup job for Shield"):
            clear_job_queue()
            mock_intent = MagicMock()
            mock_intent.raw_message = msg
            mock_intent.sender = "012"
            mock_intent.is_authorized_commander = True
            mock_intent.session_key = None
            mock_intent.channel = "local_repl"
            result = dispatch_foundup(MagicMock(), mock_intent)

            assert "status: queued" in result
            assert len(get_job_queue()) == 1
            assert "launched successfully" not in result.lower()


class TestW10Handoff:
    """validate_and_remember emits a W10 READY/NOT_READY handoff for FOUNDUP work
    instead of self-approving."""

    def test_validate_and_remember_emits_w10_handoff(self):
        """The validator now builds a W10 handoff for FOUNDUP-category outcomes."""
        from modules.communication.moltbot_bridge.src import openclaw_result_memory

        source = inspect.getsource(openclaw_result_memory.validate_and_remember)
        assert "build_w10_handoff" in source
        assert ("W10" in source) and ("NOT_READY" in source)

    def test_build_w10_handoff_packet_shape(self):
        """W10 handoff packet has the required fields and normalises status."""
        from modules.communication.moltbot_bridge.src.openclaw_result_memory import (
            build_w10_handoff,
        )

        packet = build_w10_handoff(
            status="NOT_READY",
            reason="genesis gate blocked",
            required_wsp="WSP_109",
            required_artifacts=["FoundUpGenesisEnvelope"],
            suggested_next_slice="OPENCLAW_WSP109_GENESIS_GATE_REMEDIATION_PHASE1",
            blocked_execution=True,
        )
        assert packet["status"] == "NOT_READY"
        assert packet["required_wsp"] == "WSP_109"
        assert packet["blocked_execution"] is True
        for key in ("kind", "reason", "required_artifacts", "suggested_next_slice"):
            assert key in packet
        # Unknown status normalises to NOT_READY (no accidental self-approval).
        assert build_w10_handoff(status="bogus", reason="x")["status"] == "NOT_READY"


class TestProtectedPathRemainsBlocked:
    """Protected-path edits remain blocked (preserved from #737 S5)."""

    PROTECTED_MSG = "modify modules/communication/moltbot_bridge/src/openclaw_dae.py"

    def test_protected_path_edit_is_source_modification_PASS(self):
        from modules.communication.moltbot_bridge.src.openclaw_permission_policy import (
            is_source_modification,
        )

        intent = MagicMock()
        intent.raw_message = self.PROTECTED_MSG
        assert is_source_modification(MagicMock(), intent) is True

    def test_source_tier_fails_closed_without_permission_manager_PASS(self):
        from modules.communication.moltbot_bridge.src.openclaw_permission_policy import (
            check_source_permission,
        )

        dae = MagicMock()
        dae.permissions = None
        intent = MagicMock()
        intent.raw_message = self.PROTECTED_MSG

        granted, reason = check_source_permission(dae, intent)
        assert granted is False
        assert "permission manager unavailable" in reason


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
