"""Platform-launch and constructor-bound tests for the owner supervisor."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from modules.infrastructure.foundups_mcp_bridge.src import (
    holo_query_service_supervisor as supervisor_module,
)
from modules.infrastructure.foundups_mcp_bridge.src.holo_query_service_supervisor import (
    HoloQueryServiceSupervisor,
)


def test_non_windows_process_options_are_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(supervisor_module.os, "name", "posix")
    assert supervisor_module._hidden_process_options() == {}


def test_windows_process_options_hide_owner_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class StartupInfo:
        def __init__(self) -> None:
            self.dwFlags = 0
            self.wShowWindow = -1

    monkeypatch.setattr(supervisor_module.os, "name", "nt")
    monkeypatch.setattr(
        supervisor_module.subprocess,
        "STARTUPINFO",
        StartupInfo,
        raising=False,
    )
    monkeypatch.setattr(
        supervisor_module.subprocess,
        "STARTF_USESHOWWINDOW",
        1,
        raising=False,
    )
    monkeypatch.setattr(
        supervisor_module.subprocess,
        "SW_HIDE",
        0,
        raising=False,
    )
    monkeypatch.setattr(
        supervisor_module.subprocess,
        "CREATE_NO_WINDOW",
        0x08000000,
        raising=False,
    )

    options = supervisor_module._hidden_process_options()

    assert options["creationflags"] == 0x08000000
    assert options["startupinfo"].dwFlags == 1
    assert options["startupinfo"].wShowWindow == 0


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"port": 0}, "port must be between 1 and 65535"),
        (
            {"startup_timeout_seconds": 0},
            "lifecycle timeouts must be positive",
        ),
        (
            {"startup_timeout_seconds": float("nan")},
            "lifecycle timeouts must be positive",
        ),
        (
            {"probe_timeout_seconds": float("inf")},
            "lifecycle timeouts must be positive",
        ),
    ],
)
def test_constructor_rejects_unsafe_bounds(
    tmp_path: Path,
    kwargs: dict[str, Any],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        HoloQueryServiceSupervisor(repo_root=tmp_path, **kwargs)
