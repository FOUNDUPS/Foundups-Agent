# -*- coding: utf-8 -*-
"""Tests for the opt-in after-selection antifaFM auto-launch in monitor_youtube.

ANTIFAFM_AUTOSTART_AFTER_SELECT_PHASE1

The 24/7 antifaFM broadcaster must NOT launch at menu boot (that block was
deliberately removed because it broke the daemon -- see
MAIN_MENU_ANTIFAFM_STARTUP_BOUNDARY_FIX_PHASE1). Instead it may launch AFTER 012
selects/starts the YouTube DAE -- i.e. inside main.monitor_youtube() (the
function both menu option 1 and option 6 route through).

These tests pin the gate behavior WITHOUT importing the full main.py (which runs
heavy module-scope startup and needs a logs/ dir). We extract ONLY the
monitor_youtube() source via AST and execute it in a controlled namespace where
every inner dependency is mocked. No real browser, FFmpeg, OBS, or YouTube Live
broadcast is touched.

Non-vacuity contract:
- ANTIFAFM_AUTOSTART=1  -> monitor_youtube() invokes start_antifafm_background.
- ANTIFAFM_AUTOSTART unset/0 (default OFF) -> it does NOT.
- The mocked start_antifafm_background runs on the real threading dispatch, so a
  removed/always-on gate would flip exactly one of these assertions and fail.
"""

from __future__ import annotations

import ast
import asyncio
import sys
import types
from pathlib import Path
from unittest import mock

import pytest


# Project root (tests/ -> antifafm_broadcaster/ -> platform_integration/ ->
# modules/ -> repo root).
PROJECT_ROOT = Path(__file__).parents[4]
MAIN_PY = PROJECT_ROOT / "main.py"


def _extract_monitor_youtube_source() -> str:
    """Return the exact source text of the async monitor_youtube function."""
    tree = ast.parse(MAIN_PY.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "monitor_youtube":
            return ast.get_source_segment(MAIN_PY.read_text(encoding="utf-8"), node)
    raise AssertionError("async monitor_youtube not found in main.py")


def _install_fake_inner_modules(start_spy: mock.Mock) -> dict:
    """Patch sys.modules with the modules monitor_youtube imports function-locally.

    Returns the patched sys.modules dict context manager backing store; callers
    should use it under mock.patch.dict.
    """
    fakes: dict[str, types.ModuleType] = {}

    # instance_lock: get_instance_lock(name) -> lock with no duplicates, acquires.
    lock = mock.Mock()
    lock.check_duplicates.return_value = []
    lock.acquire.return_value = True
    lock.release.return_value = None
    inst_mod = types.ModuleType(
        "modules.infrastructure.instance_lock.src.instance_manager"
    )
    inst_mod.get_instance_lock = mock.Mock(return_value=lock)
    fakes["modules.infrastructure.instance_lock.src.instance_manager"] = inst_mod

    # youtube_auth: preflight returns a healthy, no-reauth-needed status.
    auth_mod = types.ModuleType(
        "modules.platform_integration.youtube_auth.src.youtube_auth"
    )
    auth_mod.preflight_oauth_check = mock.Mock(
        return_value={
            "healthy": [1, 10],
            "expired": [],
            "missing": [],
            "reauth_needed": False,
        }
    )
    fakes["modules.platform_integration.youtube_auth.src.youtube_auth"] = auth_mod

    # quota_monitor: empty summary (the per-set loop just skips).
    quota_mod = types.ModuleType(
        "modules.platform_integration.youtube_auth.src.quota_monitor"
    )
    quota_instance = mock.Mock()
    quota_instance.get_usage_summary.return_value = {"sets": {}}
    quota_mod.QuotaMonitor = mock.Mock(return_value=quota_instance)
    fakes["modules.platform_integration.youtube_auth.src.quota_monitor"] = quota_mod

    # ai_overseer preflight resolution: on_preflight_fail is best-effort no-op.
    overseer_mod = types.ModuleType(
        "modules.ai_intelligence.ai_overseer.src.preflight_resolution"
    )
    overseer_mod.on_preflight_fail = mock.Mock()
    fakes["modules.ai_intelligence.ai_overseer.src.preflight_resolution"] = overseer_mod

    # auto_moderator_dae: AutoModeratorDAE().run() is an awaitable no-op so the
    # function returns immediately after the (already-evaluated) autostart gate.
    dae_mod = types.ModuleType("modules.communication.livechat.src.auto_moderator_dae")

    class _FakeDAE:
        def __init__(self, *args, **kwargs):
            pass

        async def run(self):
            return None

    dae_mod.AutoModeratorDAE = _FakeDAE
    fakes["modules.communication.livechat.src.auto_moderator_dae"] = dae_mod

    return fakes


def _build_monitor_youtube(start_spy: mock.Mock):
    """Compile monitor_youtube() into an isolated namespace with mocked globals."""
    src = _extract_monitor_youtube_source()
    import os as _os
    import logging as _logging

    ns: dict = {
        "os": _os,
        "sys": sys,
        "logger": _logging.getLogger("test_monitor_youtube"),
        "Optional": __import__("typing").Optional,
        "Dict": __import__("typing").Dict,
        # The module-level symbol monitor_youtube references directly:
        "start_antifafm_background": start_spy,
        # builtins input must never block in tests; default OAuth path avoids it,
        # but guard anyway.
        "input": lambda *a, **k: "2",
    }
    exec(compile(src, str(MAIN_PY), "exec"), ns)
    return ns["monitor_youtube"]


def _run_monitor(monkeyenv: dict | None, start_spy: mock.Mock) -> None:
    fakes = _install_fake_inner_modules(start_spy)
    monitor_youtube = _build_monitor_youtube(start_spy)
    with mock.patch.dict(sys.modules, fakes):
        asyncio.run(monitor_youtube(env_overrides=monkeyenv, auto_reauth=True))


def test_autostart_flag_on_launches_broadcaster(monkeypatch):
    """ANTIFAFM_AUTOSTART=1 -> monitor_youtube launches the broadcaster."""
    monkeypatch.delenv("ANTIFAFM_AUTOSTART", raising=False)
    start_spy = mock.Mock(return_value=True)

    # Pass the flag via env_overrides (real path used by the menu) so the gate
    # sees it set inside the function.
    _run_monitor({"ANTIFAFM_AUTOSTART": "1"}, start_spy)

    # Dispatched on a daemon thread -- give it a beat to start.
    import time

    for _ in range(50):
        if start_spy.called:
            break
        time.sleep(0.02)

    assert start_spy.called, (
        "start_antifafm_background should be invoked when ANTIFAFM_AUTOSTART=1"
    )


def test_autostart_flag_off_does_not_launch_broadcaster(monkeypatch):
    """Default OFF: no ANTIFAFM_AUTOSTART -> broadcaster is NOT launched."""
    monkeypatch.delenv("ANTIFAFM_AUTOSTART", raising=False)
    start_spy = mock.Mock(return_value=True)

    _run_monitor(None, start_spy)

    import time

    time.sleep(0.2)  # would-be thread window
    assert not start_spy.called, (
        "start_antifafm_background must NOT run when ANTIFAFM_AUTOSTART is unset"
    )


def test_autostart_flag_explicit_zero_does_not_launch(monkeypatch):
    """Explicit ANTIFAFM_AUTOSTART=0 is OFF (regression guard)."""
    monkeypatch.delenv("ANTIFAFM_AUTOSTART", raising=False)
    start_spy = mock.Mock(return_value=True)

    _run_monitor({"ANTIFAFM_AUTOSTART": "0"}, start_spy)

    import time

    time.sleep(0.2)
    assert not start_spy.called, (
        "start_antifafm_background must NOT run when ANTIFAFM_AUTOSTART=0"
    )


def test_gate_is_distinct_from_retired_flag(monkeypatch):
    """The retired ANTIFAFM_AUTO_START name must NOT trigger the new gate.

    Setting only the old flag (underscore between AUTO and START) must leave the
    broadcaster OFF -- proving the new gate keys on ANTIFAFM_AUTOSTART, not the
    deprecated/ignored ANTIFAFM_AUTO_START.
    """
    monkeypatch.delenv("ANTIFAFM_AUTOSTART", raising=False)
    start_spy = mock.Mock(return_value=True)

    _run_monitor({"ANTIFAFM_AUTO_START": "1"}, start_spy)

    import time

    time.sleep(0.2)
    assert not start_spy.called, (
        "Retired ANTIFAFM_AUTO_START must not trigger the after-selection autostart"
    )
