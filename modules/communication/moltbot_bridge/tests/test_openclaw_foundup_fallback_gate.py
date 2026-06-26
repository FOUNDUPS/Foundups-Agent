#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WAE-L0 (#737): Tests for the FOUNDUP ImportError fallback genesis gate.

Closes the ONE residual ungated path identified and ratified by WAE-AR1: the
ImportError fallback in ``execute_foundup`` that previously reached
``fam_adapter.launch_foundup`` (via ``handle_fam_intent``) WITHOUT passing the
WSP 109 genesis gate.

Invariant proven here:
    For a FOUNDUP launch/onboard/create/genesis intent, when the orchestrator
    import (and thus the genesis gate) is forced to raise ImportError,
    ``execute_foundup`` FAILS CLOSED - it returns a NOT_READY/blocked packet and
    does NOT invoke ``fam_adapter.handle_fam_intent`` / ``launch_foundup``.

Non-launch advisory queries keep the safe FAM passthrough (regression guard).

Slice: WAE-L0   Worker-Lane: B
"""

import builtins
import sys
import pytest
from unittest.mock import MagicMock


def _make_intent(raw_message: str, sender: str = "test_user") -> MagicMock:
    """Build a minimal mock intent with the fields execute_foundup reads."""
    intent = MagicMock()
    intent.raw_message = raw_message
    intent.sender = sender
    return intent


def _force_orchestrator_import_error(monkeypatch):
    """Force ``from .openclaw_foundup_orchestrator import dispatch_foundup`` to
    raise ImportError, simulating the residual fallback path. Real ``__import__``
    is preserved for all other modules.
    """
    real_import = builtins.__import__
    target = "openclaw_foundup_orchestrator"

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if target in name or (fromlist and "dispatch_foundup" in fromlist and target in name):
            raise ImportError(f"forced import error for {name}")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)


# ---------------------------------------------------------------------------
# The ONE pass/fail test (WAE-L0)
# ---------------------------------------------------------------------------


class TestFoundupImportErrorFallbackGate:
    """Launch/onboard intents fail closed when the orchestrator import fails."""

    def test_launch_intent_blocked_when_orchestrator_import_fails(self, monkeypatch):
        """PASS: 'launch foundup Shield with token SHLD' through execute_foundup
        with the orchestrator import forced to raise ImportError returns
        NOT_READY/blocked AND fam_adapter.launch_foundup is NOT invoked.
        FAIL: a FoundUp is created, or launch_foundup / handle_fam_intent is called.
        """
        from modules.communication.moltbot_bridge.src import openclaw_execution_routes

        # Mock fam_adapter so we can assert it is NEVER reached on the launch path.
        mock_fam_adapter = MagicMock()
        mock_fam_adapter.handle_fam_intent = MagicMock(return_value="LAUNCHED!")
        mock_fam_adapter.launch_foundup = MagicMock(return_value="LAUNCHED!")
        monkeypatch.setitem(
            sys.modules,
            "modules.communication.moltbot_bridge.src.fam_adapter",
            mock_fam_adapter,
        )

        # Force the orchestrator (and thus the genesis gate) import to fail.
        _force_orchestrator_import_error(monkeypatch)

        intent = _make_intent("launch foundup Shield with token SHLD")
        result = openclaw_execution_routes.execute_foundup(MagicMock(), intent)

        # Genesis gate unavailable -> FAM launch must NOT be invoked.
        mock_fam_adapter.handle_fam_intent.assert_not_called()
        mock_fam_adapter.launch_foundup.assert_not_called()

        # Response must signal a blocked / NOT_READY state.
        result_lower = result.lower()
        assert any(
            blocker in result_lower
            for blocker in ("not_ready", "blocked", "unavailable", "genesis gate unavailable")
        ), f"expected a NOT_READY/blocked packet, got: {result!r}"

        # Response must NOT claim FoundUp creation / success.
        assert "launched" not in result_lower
        assert "created" not in result_lower
        assert "onboarded" not in result_lower

    @pytest.mark.parametrize(
        "raw_message",
        [
            "launch foundup Shield with token SHLD",
            "launch this foundup now",
            "onboard a FoundUp called Shield",
            "create foundup Shield",
            "follow WSP 109 and run genesis for Shield",
            "go live with foundup Shield",
        ],
    )
    def test_all_launch_verbs_fail_closed(self, monkeypatch, raw_message):
        """Every launch/onboard/create/genesis verb fails closed on import error."""
        from modules.communication.moltbot_bridge.src import openclaw_execution_routes

        mock_fam_adapter = MagicMock()
        mock_fam_adapter.handle_fam_intent = MagicMock(return_value="LAUNCHED!")
        mock_fam_adapter.launch_foundup = MagicMock(return_value="LAUNCHED!")
        monkeypatch.setitem(
            sys.modules,
            "modules.communication.moltbot_bridge.src.fam_adapter",
            mock_fam_adapter,
        )
        _force_orchestrator_import_error(monkeypatch)

        intent = _make_intent(raw_message)
        result = openclaw_execution_routes.execute_foundup(MagicMock(), intent)

        mock_fam_adapter.handle_fam_intent.assert_not_called()
        mock_fam_adapter.launch_foundup.assert_not_called()
        assert "not_ready" in result.lower() or "blocked" in result.lower()


# ---------------------------------------------------------------------------
# Regression guard: non-launch advisory queries keep the FAM passthrough.
# ---------------------------------------------------------------------------


class TestAdvisoryFallbackPreserved:
    """Non-launch advisory queries still reach FAM on the fallback path."""

    def test_advisory_query_still_routes_to_fam_on_import_error(self, monkeypatch):
        """An advisory 'what is cabr' query keeps the safe FAM passthrough when
        the orchestrator import fails (the launch gate must not over-block).
        """
        from modules.communication.moltbot_bridge.src import openclaw_execution_routes

        mock_fam_adapter = MagicMock()
        mock_fam_adapter.handle_fam_intent = MagicMock(return_value="CABR advisory response")
        monkeypatch.setitem(
            sys.modules,
            "modules.communication.moltbot_bridge.src.fam_adapter",
            mock_fam_adapter,
        )
        _force_orchestrator_import_error(monkeypatch)

        intent = _make_intent("what is cabr")
        result = openclaw_execution_routes.execute_foundup(MagicMock(), intent)

        mock_fam_adapter.handle_fam_intent.assert_called_once_with("what is cabr", "test_user")
        assert result == "CABR advisory response"


# ---------------------------------------------------------------------------
# Predicate unit tests (local/private helper).
# ---------------------------------------------------------------------------


class TestLaunchVerbPredicate:
    """The local launch-verb predicate covers the ratified verbs only."""

    def test_launch_verbs_detected(self):
        from modules.communication.moltbot_bridge.src.openclaw_execution_routes import (
            _is_launch_or_onboard_verb,
        )

        assert _is_launch_or_onboard_verb("launch foundup Shield with token SHLD") is True
        assert _is_launch_or_onboard_verb("onboard a FoundUp called Shield") is True
        assert _is_launch_or_onboard_verb("create foundup Shield") is True
        assert _is_launch_or_onboard_verb("run genesis for Shield") is True
        assert _is_launch_or_onboard_verb("go live with foundup Shield") is True

    def test_non_launch_queries_not_detected(self):
        from modules.communication.moltbot_bridge.src.openclaw_execution_routes import (
            _is_launch_or_onboard_verb,
        )

        assert _is_launch_or_onboard_verb("what is cabr") is False
        assert _is_launch_or_onboard_verb("tell me about foundups") is False
        assert _is_launch_or_onboard_verb("list all foundups") is False

    def test_non_string_message_is_safe(self):
        from modules.communication.moltbot_bridge.src.openclaw_execution_routes import (
            _is_launch_or_onboard_verb,
        )

        assert _is_launch_or_onboard_verb(None) is False
        assert _is_launch_or_onboard_verb(MagicMock()) is False
