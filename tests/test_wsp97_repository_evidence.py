"""Platform-independent tests for WSP 97 repository path confinement."""

from __future__ import annotations

import stat
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

import tools.wsp97_repository_evidence as repository_evidence
from tools.wsp97_repository_evidence import _is_reparse_or_symlink


def test_lstat_seam_detects_posix_symlink_mode() -> None:
    def fake_lstat(_path: Path):
        return SimpleNamespace(st_mode=stat.S_IFLNK, st_file_attributes=0)

    assert _is_reparse_or_symlink(Path("linked"), lstat=fake_lstat) is True


def test_lstat_seam_detects_windows_junction_reparse_flag() -> None:
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)

    def fake_lstat(_path: Path):
        return SimpleNamespace(
            st_mode=stat.S_IFDIR,
            st_file_attributes=reparse_flag,
        )

    assert _is_reparse_or_symlink(Path("junction"), lstat=fake_lstat) is True


def test_lstat_seam_accepts_regular_path_component() -> None:
    def fake_lstat(_path: Path):
        return SimpleNamespace(st_mode=stat.S_IFREG, st_file_attributes=0)

    assert _is_reparse_or_symlink(Path("regular"), lstat=fake_lstat) is False


def test_redirecting_root_is_fully_lstatted_before_any_git_call(
    tmp_path: Path,
) -> None:
    supplied = tmp_path / "redirecting" / "repository"
    expected_components = repository_evidence._components_from_anchor(supplied.absolute())
    lstat_calls: list[Path] = []
    git_calls: list[tuple[str, ...]] = []
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)

    def fake_lstat(path: Path):
        lstat_calls.append(path)
        attributes = reparse_flag if path == expected_components[-1] else 0
        return SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=attributes)

    def forbidden_git(_root: Path, *args: str):
        git_calls.append(args)
        raise AssertionError("Git must not run after a redirecting root component")

    with pytest.raises(ValueError, match="symlink|junction|reparse"):
        repository_evidence.resolve_git_toplevel(
            supplied,
            lstat=fake_lstat,
            git_runner=forbidden_git,
        )

    assert tuple(lstat_calls) == expected_components
    assert git_calls == []


def test_git_query_budget_fails_before_process_spawn(monkeypatch: pytest.MonkeyPatch) -> None:
    process_calls: list[object] = []

    def forbidden_process(*_args, **_kwargs):
        process_calls.append(object())
        raise AssertionError("process must not spawn after budget exhaustion")

    monkeypatch.setattr(repository_evidence.subprocess, "run", forbidden_process)
    budget_type = getattr(repository_evidence, "GitQueryBudget")
    budget = budget_type(max_calls=0)

    with pytest.raises(ValueError, match="budget"):
        repository_evidence._run_git(
            Path.cwd(),
            "rev-parse",
            "HEAD",
            budget=budget,
        )

    assert process_calls == []


def test_git_timeout_is_an_operational_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def timeout_process(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])

    monkeypatch.setattr(repository_evidence.subprocess, "run", timeout_process)
    budget_type = getattr(repository_evidence, "GitQueryBudget")

    with pytest.raises(ValueError, match="timed out"):
        repository_evidence._run_git(
            Path.cwd(),
            "rev-parse",
            "HEAD",
            budget=budget_type(),
        )


def test_git_oversized_tempfile_output_is_not_accepted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_limit = repository_evidence.MAX_ACCEPTED_GIT_OUTPUT_BYTES

    def oversized_process(*_args, **kwargs):
        kwargs["stdout"].write(b"x" * (output_limit + 1))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(repository_evidence.subprocess, "run", oversized_process)
    budget_type = getattr(repository_evidence, "GitQueryBudget")

    with pytest.raises(ValueError, match="accepted output limit"):
        repository_evidence._run_git(
            Path.cwd(),
            "rev-parse",
            "HEAD",
            budget=budget_type(),
        )


def test_wrong_case_check_does_not_fall_back_to_full_catalog(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, ...]] = []

    def missing_exact_path(_root: Path, *args: str, **_kwargs):
        calls.append(args)
        return repository_evidence.GitResult(1, "", "")

    monkeypatch.setattr(repository_evidence, "_run_git", missing_exact_path)
    reason = repository_evidence._tracked_case_violation(
        Path.cwd(),
        "WSP_framework/src/wsp_97_System_Execution_Prompting_Protocol.md",
        repository_evidence.GitQueryBudget(),
    )

    assert reason == "not_tracked"
    assert len(calls) == 1
    assert "WSP_framework/src" not in calls[0]
