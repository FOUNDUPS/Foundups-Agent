"""Tests for WRE worktree current-directory guard."""

from __future__ import annotations

from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_wre_cwd_guard import (
    FAIL_OPERATION_CWD_INSIDE_REPO_ROOT,
    FAIL_OPERATION_CWD_NOT_ABSOLUTE,
    FAIL_OPERATION_CWD_OUTSIDE_WORKTREE,
    FAIL_WORKTREE_INSIDE_REPO_ROOT,
    FAIL_WORKTREE_NOT_ABSOLUTE,
    WRE_CWD_GUARD_PASS,
    validate_wre_worker_operation_cwd,
)


def test_accepts_cwd_inside_isolated_worktree(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    worktree = tmp_path / "wt"
    cwd = worktree / "modules" / "foundups" / "demo"
    repo.mkdir()
    cwd.mkdir(parents=True)

    result = validate_wre_worker_operation_cwd(
        repo_root=repo,
        worktree_path=worktree,
        operation_cwd=cwd,
    )

    assert result.ok is True
    assert result.code == WRE_CWD_GUARD_PASS
    assert Path(result.operation_cwd).resolve() == cwd.resolve()


def test_rejects_mutating_cwd_at_shared_repo_root(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    worktree = tmp_path / "wt"
    repo.mkdir()
    worktree.mkdir()

    result = validate_wre_worker_operation_cwd(
        repo_root=repo,
        worktree_path=worktree,
        operation_cwd=repo,
    )

    assert result.ok is False
    assert result.code == FAIL_OPERATION_CWD_INSIDE_REPO_ROOT


def test_rejects_worktree_inside_shared_repo_root(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    worktree = repo / ".reddog" / "worktrees" / "wo" / "nonce"
    repo.mkdir(parents=True)
    worktree.mkdir(parents=True)

    result = validate_wre_worker_operation_cwd(
        repo_root=repo,
        worktree_path=worktree,
    )

    assert result.ok is False
    assert result.code == FAIL_WORKTREE_INSIDE_REPO_ROOT


def test_rejects_operation_cwd_outside_worktree(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    worktree = tmp_path / "wt"
    other = tmp_path / "other"
    repo.mkdir()
    worktree.mkdir()
    other.mkdir()

    result = validate_wre_worker_operation_cwd(
        repo_root=repo,
        worktree_path=worktree,
        operation_cwd=other,
    )

    assert result.ok is False
    assert result.code == FAIL_OPERATION_CWD_OUTSIDE_WORKTREE


def test_rejects_relative_worktree_and_cwd(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    relative_worktree = validate_wre_worker_operation_cwd(
        repo_root=repo,
        worktree_path=Path("relative-wt"),
    )
    assert relative_worktree.ok is False
    assert relative_worktree.code == FAIL_WORKTREE_NOT_ABSOLUTE

    worktree = tmp_path / "wt"
    worktree.mkdir()
    relative_cwd = validate_wre_worker_operation_cwd(
        repo_root=repo,
        worktree_path=worktree,
        operation_cwd=Path("relative-cwd"),
    )
    assert relative_cwd.ok is False
    assert relative_cwd.code == FAIL_OPERATION_CWD_NOT_ABSOLUTE
