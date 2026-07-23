"""Tests for HOLOINDEX_READONLY_QUERY_GUARD_PHASE1."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

import pytest

os.environ.setdefault("HOLO_SKIP_MODEL", "1")

from holo_index import _cli_main
from holo_index.cli import bundle_path_confinement as bundle_confinement
from holo_index.cli.commands import bundle_json
from holo_index.query_admission import ReadonlyQueryAdmission

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


def _run_raw_offline_cli(
    repo_root: Path,
    monkeypatch,
    capsys,
    query: str,
) -> str:
    (repo_root / "holo_index").mkdir(exist_ok=True)
    monkeypatch.setattr(_cli_main, "HoloIndex", None)
    monkeypatch.setattr(
        _cli_main,
        "__file__",
        str(repo_root / "holo_index" / "_cli_main.py"),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "holo_index.py",
            "--offline",
            "--fast-search",
            "--search",
            query,
            "--limit",
            "5",
        ],
    )
    _cli_main.main()
    return capsys.readouterr().out


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


def test_persistent_search_admission_precedes_backend_construction() -> None:
    source = (REPO_ROOT / "holo_index" / "_cli_main.py").read_text(encoding="utf-8")

    admission = source.index("evaluate_readonly_query_admission(")
    backend = source.index("holo = HoloIndex(", admission)

    assert admission < backend


def test_cli_foreign_root_denial_precedes_backend_construction(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    backend_constructed = False

    class UnexpectedBackend:
        def __init__(self, *args, **kwargs) -> None:
            nonlocal backend_constructed
            backend_constructed = True

    monkeypatch.setattr(_cli_main, "HoloIndex", UnexpectedBackend)
    monkeypatch.setattr(
        _cli_main,
        "evaluate_readonly_query_admission",
        lambda **_kwargs: ReadonlyQueryAdmission(
            allowed=False,
            error="STALE_INDEX",
            reasons=("freshness_repo_root_mismatch",),
            freshness="STALE",
            binding={},
        ),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["holo_index.py", "--search", "WSP 97", "--ssd", str(tmp_path)],
    )

    with pytest.raises(SystemExit) as raised:
        _cli_main.main()

    assert raised.value.code == _cli_main.QUERY_ADMISSION_EXIT_CODE
    assert backend_constructed is False
    output = capsys.readouterr().out
    assert "freshness_repo_root_mismatch" in output
    assert str(tmp_path) not in output


def test_cli_offline_lexical_never_runs_persistent_admission(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(_cli_main, "HoloIndex", None)
    monkeypatch.setattr(
        _cli_main,
        "evaluate_readonly_query_admission",
        lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("offline lexical retrieval must bypass persistent admission")
        ),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "holo_index.py",
            "--offline",
            "--fast-search",
            "--search",
            "WSP 97",
            "--ssd",
            str(tmp_path),
        ],
    )

    _cli_main.main()

    output = capsys.readouterr().out
    assert "[DEGRADED]" in output
    assert "current-repository lexical search only" in output


def test_raw_cli_offline_rejects_foreign_navigation_symlink(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    foreign_nav = tmp_path / "foreign-navigation.py"
    foreign_nav.write_text(
        "NEED_TO = {'foreign marker': 'foreign_location.py'}\n",
        encoding="utf-8",
    )
    try:
        (repo_root / "NAVIGATION.py").symlink_to(foreign_nav)
    except OSError as exc:
        pytest.skip(f"file symlink unavailable: {exc}")

    output = _run_raw_offline_cli(
        repo_root,
        monkeypatch,
        capsys,
        "foreign marker",
    )

    assert "foreign_location.py" not in output


def test_raw_cli_offline_rejects_navigation_reparse_seam(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    nav_path = repo_root / "NAVIGATION.py"
    nav_path.write_text(
        "NEED_TO = {'reparse marker': 'reparse_location.py'}\n",
        encoding="utf-8",
    )
    real_detector = bundle_confinement._is_link_or_reparse
    monkeypatch.setattr(
        bundle_confinement,
        "_is_link_or_reparse",
        lambda path: (
            Path(path).resolve(strict=False) == nav_path.resolve(strict=False)
            or real_detector(path)
        ),
    )

    output = _run_raw_offline_cli(
        repo_root,
        monkeypatch,
        capsys,
        "reparse marker",
    )

    assert "reparse_location.py" not in output


def test_raw_cli_offline_rejects_oversize_navigation(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    monkeypatch.setattr(
        bundle_json,
        "LEXICAL_NAVIGATION_MAX_BYTES",
        64,
        raising=False,
    )
    (repo_root / "NAVIGATION.py").write_bytes(
        b"NEED_TO = {'oversize marker': 'oversize_location.py'}\n" + b"#" * 64
    )

    output = _run_raw_offline_cli(
        repo_root,
        monkeypatch,
        capsys,
        "oversize marker",
    )

    assert "oversize_location.py" not in output


def test_offline_lexical_search_bypasses_persistent_admission() -> None:
    source = (REPO_ROOT / "holo_index" / "_cli_main.py").read_text(encoding="utf-8")

    assert "if HoloIndex is not None and args.search and not maintenance_plan:" in source
    assert "_lexical_task_retrieval(" in source
    assert "evaluate_readonly_query_admission(" not in source[
        source.index("if holo is None:") : source.index(
            "# Process search results for throttler"
        )
    ]


def test_bundle_persistent_query_denial_precedes_backend_construction(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    backend_constructed = False
    real_import = __import__

    def guarded_import(name, *args, **kwargs):
        nonlocal backend_constructed
        if name == "holo_index.core":
            backend_constructed = True
        return real_import(name, *args, **kwargs)

    monkeypatch.delenv("HOLO_SKIP_MODEL", raising=False)
    monkeypatch.setattr("builtins.__import__", guarded_import)
    monkeypatch.setattr(
        bundle_json,
        "evaluate_readonly_query_admission",
        lambda **_kwargs: ReadonlyQueryAdmission(
            allowed=False,
            error="STALE_INDEX",
            reasons=("freshness_repo_root_mismatch",),
            freshness="STALE",
            binding={},
        ),
    )
    args = argparse.Namespace(
        bundle_json=True,
        bundle_task=None,
        search="WSP 97",
        bundle_module_hint=None,
        bundle_must_include=None,
        limit=5,
        ssd=str(tmp_path),
        doc_type="all",
    )

    assert bundle_json.handle_bundle_json(args) is True

    assert backend_constructed is False
    output = capsys.readouterr().out
    assert "freshness_repo_root_mismatch" in output
    assert str(tmp_path) not in output


def test_bundle_persistent_admission_precedes_module_hint_resolution(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.delenv("HOLO_SKIP_MODEL", raising=False)
    monkeypatch.setattr(
        bundle_json,
        "evaluate_readonly_query_admission",
        lambda **_kwargs: ReadonlyQueryAdmission(
            allowed=False,
            error="STALE_INDEX",
            reasons=("freshness_repo_root_mismatch",),
            freshness="STALE",
            binding={},
        ),
    )
    monkeypatch.setattr(
        bundle_json,
        "_resolve_module_dir",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("module hint resolution must follow persistent admission")
        ),
    )
    args = argparse.Namespace(
        bundle_json=True,
        bundle_task=None,
        search="WSP 97",
        bundle_module_hint="E:/HoloIndex",
        bundle_must_include=None,
        limit=5,
        ssd=str(tmp_path),
        doc_type="all",
    )

    assert bundle_json.handle_bundle_json(args) is True
    assert "freshness_repo_root_mismatch" in capsys.readouterr().out


def test_collection_reset_refuses_readonly_context() -> None:
    source = (REPO_ROOT / "holo_index" / "core" / "holo_index.py").read_text(encoding="utf-8")
    assert "HOLOINDEX_QUERY_READONLY" in source
    assert "HOLOINDEX_READONLY_QUERY_GUARD" in source
    assert "refusing collection reset in read-only query context" in source


def test_reddog_extension_sets_readonly_env_for_holoindex_calls() -> None:
    source = (REPO_ROOT / "extensions" / "reddog" / "extension.js").read_text(encoding="utf-8")
    assert "HOLOINDEX_QUERY_READONLY: '1'" in source
    assert "env.HOLO_SKIP_MODEL = '1';" in source
    assert "delete env.HOLO_SKIP_MODEL;" in source
