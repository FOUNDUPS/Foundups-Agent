"""Trusted maintenance child output isolation regressions."""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

from holo_index import _cli_main as cli
from holo_index.maintenance_session import (
    MAINTENANCE_FAILURE_EXIT_CODE,
    MaintenanceSessionError,
)


def test_json_only_maintenance_suppresses_progress_but_emits_final_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    emitted: list[str] = []
    monkeypatch.setenv(cli.MAINTENANCE_JSON_ONLY_ENV, "1")
    monkeypatch.setattr(
        cli, "_safe_print", lambda value, **_kwargs: emitted.append(value)
    )

    cli.safe_print("untrusted progress and paths")
    with pytest.raises(SystemExit) as stopped:
        cli._exit_maintenance_error(
            MaintenanceSessionError("HOLOINDEX_MAINTENANCE_PROOF_FAILED")
        )

    assert stopped.value.code == MAINTENANCE_FAILURE_EXIT_CODE
    assert [json.loads(value) for value in emitted] == [
        {"error": "HOLOINDEX_MAINTENANCE_PROOF_FAILED", "ok": False}
    ]


def test_normal_cli_output_is_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    emitted: list[str] = []
    monkeypatch.delenv(cli.MAINTENANCE_JSON_ONLY_ENV, raising=False)
    monkeypatch.setattr(
        cli, "_safe_print", lambda value, **_kwargs: emitted.append(value)
    )

    cli.safe_print("normal progress")

    assert emitted == ["normal progress"]


def test_json_only_subprocess_hides_direct_prints_and_preserves_error() -> None:
    environment = os.environ.copy()
    environment[cli.MAINTENANCE_JSON_ONLY_ENV] = "1"
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from holo_index import _cli_main as c; "
                "print('direct progress and paths'); "
                "c.safe_print('wrapped progress'); "
                "c._exit_maintenance_error("
                "c.MaintenanceSessionError('HOLOINDEX_MAINTENANCE_PROOF_FAILED'))"
            ),
        ],
        cwd=str(cli.project_root),
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == MAINTENANCE_FAILURE_EXIT_CODE
    assert json.loads(result.stdout) == {
        "error": "HOLOINDEX_MAINTENANCE_PROOF_FAILED",
        "ok": False,
    }
    assert result.stderr == ""
