"""Trusted maintenance child output isolation regressions."""

from __future__ import annotations

import json

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
    monkeypatch.setattr(cli, "_safe_print", emitted.append)

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
    monkeypatch.setattr(cli, "_safe_print", emitted.append)

    cli.safe_print("normal progress")

    assert emitted == ["normal progress"]
