"""
No-network unit tests for per-set OAuth browser resolution (WSP 84 / WSP 97).

Covers:
    - Set 1 prefers CHROME_PATH env when it exists (mirrors authorize_set1.py)
    - Set 10 prefers EDGE_PATH env when it exists (mirrors authorize_set10.py)
    - No browser present -> BrowserNotFoundError carrying the exact reauth command

All filesystem and environment access is mocked; nothing is launched and no
network call is made.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from modules.platform_integration.youtube_auth.src import oauth_browser
from modules.platform_integration.youtube_auth.src import oauth_health
from modules.platform_integration.youtube_auth.src.oauth_browser import (
    BrowserNotFoundError,
    resolve_browser_for_set,
)


def test_resolve_browser_set1_prefers_chrome_path_env():
    """Set 1 returns ('chrome', $CHROME_PATH) when CHROME_PATH exists first."""
    env_chrome = r"D:\custom\chrome.exe"
    with patch.dict("os.environ", {"CHROME_PATH": env_chrome}, clear=False):
        # Only the env path "exists" -> it must win over the hardcoded fallbacks.
        with patch("os.path.exists", side_effect=lambda p: p == env_chrome):
            name, path = resolve_browser_for_set(1)
    assert name == "chrome"
    assert path == env_chrome


def test_resolve_browser_set1_falls_back_to_64bit_then_x86():
    """Set 1 candidate order exactly mirrors authorize_set1.py."""
    sixtyfour = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    x86 = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"

    # No env var; only 64-bit exists -> 64-bit chosen.
    with patch.dict("os.environ", {}, clear=True):
        with patch("os.path.exists", side_effect=lambda p: p == sixtyfour):
            name, path = resolve_browser_for_set(1)
    assert (name, path) == ("chrome", sixtyfour)

    # No env var, no 64-bit; only x86 exists -> x86 chosen last.
    with patch.dict("os.environ", {}, clear=True):
        with patch("os.path.exists", side_effect=lambda p: p == x86):
            name, path = resolve_browser_for_set(1)
    assert (name, path) == ("chrome", x86)


def test_resolve_browser_set10_prefers_edge_path_env():
    """Set 10 returns ('edge', $EDGE_PATH) when EDGE_PATH exists first."""
    env_edge = r"D:\custom\msedge.exe"
    with patch.dict("os.environ", {"EDGE_PATH": env_edge}, clear=False):
        with patch("os.path.exists", side_effect=lambda p: p == env_edge):
            name, path = resolve_browser_for_set(10)
    assert name == "edge"
    assert path == env_edge


def test_resolve_browser_set10_falls_back_to_64bit_then_x86():
    """Set 10 candidate order exactly mirrors authorize_set10.py."""
    sixtyfour = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
    x86 = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

    with patch.dict("os.environ", {}, clear=True):
        with patch("os.path.exists", side_effect=lambda p: p == sixtyfour):
            name, path = resolve_browser_for_set(10)
    assert (name, path) == ("edge", sixtyfour)

    with patch.dict("os.environ", {}, clear=True):
        with patch("os.path.exists", side_effect=lambda p: p == x86):
            name, path = resolve_browser_for_set(10)
    assert (name, path) == ("edge", x86)


def test_missing_browser_raises_with_reauth_command():
    """No candidate exists -> BrowserNotFoundError with exact reauth command."""
    with patch.dict("os.environ", {}, clear=True):
        with patch("os.path.exists", return_value=False):
            with pytest.raises(BrowserNotFoundError) as exc_info:
                resolve_browser_for_set(1)

    err = exc_info.value
    assert err.set_id == 1
    # operator_action must be the canonical oauth_health reauth command.
    assert err.operator_action == oauth_health.reauth_command_for(1)
    assert "authorize_set1.py" in err.operator_action
    # attempted_paths records the concrete fallbacks we checked (env unset -> skipped).
    assert any("chrome.exe" in p for p in err.attempted_paths)


def test_unknown_set_raises_browser_not_found():
    """Unknown set_id is an explicit, tested error (not a silent default)."""
    with pytest.raises(BrowserNotFoundError) as exc_info:
        resolve_browser_for_set(999)
    err = exc_info.value
    assert err.set_id == 999
    assert err.operator_action == oauth_health.reauth_command_for(999)
    assert err.attempted_paths == []
