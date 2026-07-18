"""Tests for HOLOINDEX_READONLY_QUERY_GUARD_PHASE1."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("HOLO_SKIP_MODEL", "1")

from holo_index import _cli_main

REPO_ROOT = Path(__file__).resolve().parents[2]


def _args(**overrides):
    values = {
        "bundle_json": False,
        "search": None,
        "offline": False,
        "fast_search": False,
        "allow_auto_refresh": False,
        "index": False,
        "index_all": False,
        "index_code": False,
        "index_wsp": False,
        "index_tests": False,
        "index_symbols": False,
        "index_skills": False,
        "index_cli": False,
        "index_work_ledger": False,
        "index_docs": False,
        "index_knowledge": False,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def test_query_mode_sets_readonly_env(monkeypatch) -> None:
    monkeypatch.delenv(_cli_main.READONLY_QUERY_ENV, raising=False)

    _cli_main._activate_readonly_query_posture(_args(search="RedDog WSP"))

    assert os.environ[_cli_main.READONLY_QUERY_ENV] == "1"


def test_query_mode_overrides_false_readonly_env(monkeypatch) -> None:
    monkeypatch.setenv(_cli_main.READONLY_QUERY_ENV, "0")

    _cli_main._activate_readonly_query_posture(_args(search="RedDog WSP"))

    assert os.environ[_cli_main.READONLY_QUERY_ENV] == "1"


def test_explicit_auto_refresh_is_not_forced_readonly(monkeypatch) -> None:
    monkeypatch.delenv(_cli_main.READONLY_QUERY_ENV, raising=False)

    args = _args(search="maintenance query", allow_auto_refresh=True)
    _cli_main._activate_readonly_query_posture(args)

    assert _cli_main.READONLY_QUERY_ENV not in os.environ
    assert _cli_main._auto_refresh_allowed(args) is True


def test_forced_readonly_still_overrides_auto_refresh(monkeypatch) -> None:
    monkeypatch.setenv(_cli_main.READONLY_QUERY_ENV, "1")

    args = _args(search="maintenance query", allow_auto_refresh=True)
    _cli_main._activate_readonly_query_posture(args)

    assert _cli_main._auto_refresh_allowed(args) is False


def test_manual_index_without_readonly_env_is_allowed(monkeypatch) -> None:
    monkeypatch.delenv(_cli_main.READONLY_QUERY_ENV, raising=False)

    _cli_main._activate_readonly_query_posture(_args(index_code=True))

    assert _cli_main.READONLY_QUERY_ENV not in os.environ
    assert _cli_main._reject_readonly_indexing(_args(index_code=True)) is False


def test_readonly_env_rejects_index_flags(monkeypatch) -> None:
    monkeypatch.setenv(_cli_main.READONLY_QUERY_ENV, "1")

    assert _cli_main._reject_readonly_indexing(_args(index_docs=True)) is True


def test_auto_refresh_requires_explicit_flag_and_non_readonly_env(monkeypatch) -> None:
    monkeypatch.delenv(_cli_main.READONLY_QUERY_ENV, raising=False)
    assert _cli_main._auto_refresh_allowed(_args(search="foo")) is False
    assert _cli_main._auto_refresh_allowed(_args(search="foo", allow_auto_refresh=True)) is True

    monkeypatch.setenv(_cli_main.READONLY_QUERY_ENV, "1")
    assert _cli_main._auto_refresh_allowed(_args(search="foo", allow_auto_refresh=True)) is False


def test_cli_rejects_readonly_indexing_before_writes() -> None:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env[_cli_main.READONLY_QUERY_ENV] = "1"
    result = subprocess.run(
        [sys.executable, "-B", "holo_index.py", "--offline", "--index-code"],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        timeout=30,
        encoding="utf-8",
        errors="replace",
    )

    assert result.returncode == 2
    assert _cli_main.READONLY_GUARD_CODE in (result.stdout + result.stderr)


def test_cli_help_advertises_auto_refresh_opt_in() -> None:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env.setdefault("HOLO_SKIP_MODEL", "1")
    result = subprocess.run(
        [sys.executable, "-B", "holo_index.py", "--help"],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        timeout=30,
        encoding="utf-8",
        errors="replace",
    )

    assert result.returncode == 0
    assert "--allow-auto-refresh" in (result.stdout + result.stderr)


def test_auto_refresh_branch_is_gated_in_cli_source() -> None:
    source = (REPO_ROOT / "holo_index" / "_cli_main.py").read_text(encoding="utf-8")
    assert "if not selected_collections and _auto_refresh_allowed(args)" in source
    assert "if holo is not None and auto_refresh_plan and not selected_collections" in source
    assert "MaintenanceSession.begin(" in source
    assert "if holo is not None and not (index_code or index_wsp or indexing_awarded)" not in source


def test_collection_reset_refuses_readonly_context() -> None:
    source = (REPO_ROOT / "holo_index" / "core" / "holo_index.py").read_text(encoding="utf-8")
    assert "HOLOINDEX_QUERY_READONLY" in source
    assert "HOLOINDEX_READONLY_QUERY_GUARD" in source
    assert "refusing collection reset in read-only query context" in source


def test_reddog_extension_sets_readonly_env_for_holoindex_calls() -> None:
    source = (REPO_ROOT / "extensions" / "reddog" / "extension.js").read_text(encoding="utf-8")
    assert "HOLOINDEX_QUERY_READONLY: '1'" in source
    assert "HOLO_SKIP_MODEL: '1', HOLOINDEX_QUERY_READONLY: '1'" in source
