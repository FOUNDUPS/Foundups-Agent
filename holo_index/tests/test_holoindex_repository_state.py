"""Tests for exact-HEAD plus clean-worktree freshness proof."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from holo_index.freshness_receipt import read_git_head_sha
from holo_index.repository_state import (
    REPOSITORY_DIRTY_CODE,
    REPOSITORY_STATE_UNAVAILABLE_CODE,
    read_repository_state,
    runtime_repository_root,
)


SHA = "a" * 40


def _git_layout(root: Path) -> None:
    git_dir = root / ".git"
    git_dir.mkdir(parents=True)
    (git_dir / "HEAD").write_text(SHA, encoding="utf-8")


def _result(stdout: str = "", returncode: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(["git"], returncode, stdout=stdout, stderr="")


def test_clean_state_binds_head_without_exposing_paths(tmp_path: Path) -> None:
    _git_layout(tmp_path)
    state = read_repository_state(tmp_path, runner=lambda *_args, **_kwargs: _result())

    assert state.proven_clean is True
    assert state.head_sha == SHA
    assert state.state_digest.startswith("sha256:")
    assert state.error == ""


def test_dirty_state_fails_closed_and_digest_hides_path(tmp_path: Path) -> None:
    _git_layout(tmp_path)
    changed_path = "modules/secret_name.py"
    state = read_repository_state(
        tmp_path,
        runner=lambda *_args, **_kwargs: _result(
            " M " + changed_path + chr(10)
        ),
    )

    assert state.proven_clean is False
    assert state.error == REPOSITORY_DIRTY_CODE
    assert changed_path not in state.state_digest


def test_missing_git_or_runner_failure_is_unavailable(tmp_path: Path) -> None:
    missing = read_repository_state(tmp_path)
    assert missing.error == REPOSITORY_STATE_UNAVAILABLE_CODE

    _git_layout(tmp_path)

    def fail(*_args, **_kwargs):
        raise subprocess.TimeoutExpired("git", 1)

    failed = read_repository_state(tmp_path, runner=fail)
    assert failed.proven_clean is False
    assert failed.error == REPOSITORY_STATE_UNAVAILABLE_CODE


def test_symbolic_head_resolves_through_linked_worktree_commondir(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "lane"
    worktree_git = tmp_path / "central.git" / "worktrees" / "lane"
    shared_git = tmp_path / "central.git"
    repo.mkdir()
    worktree_git.mkdir(parents=True)
    (repo / ".git").write_text(
        f"gitdir: {worktree_git}",
        encoding="utf-8",
    )
    (worktree_git / "HEAD").write_text(
        "ref: refs/heads/fix/lane",
        encoding="utf-8",
    )
    (worktree_git / "commondir").write_text("../..", encoding="utf-8")
    branch_ref = shared_git / "refs" / "heads" / "fix" / "lane"
    branch_ref.parent.mkdir(parents=True)
    branch_ref.write_text(SHA, encoding="utf-8")

    assert read_git_head_sha(repo) == SHA


def test_current_isolated_lane_has_real_head_and_repository_proof() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    assert read_git_head_sha(repo_root) != "unknown"
    state = read_repository_state(repo_root)
    assert state.head_sha != "unknown"


def test_runtime_repository_root_uses_sealed_target_checkout(tmp_path: Path) -> None:
    source = tmp_path / "sealed-source"
    target = tmp_path / "target-repo"
    source.mkdir()
    _git_layout(target)

    selected = runtime_repository_root(
        source,
        environ={
            "REDDOG_SEALED_RUNTIME_REQUIRED": "1",
            "REDDOG_SEALED_RUNTIME_TARGET_REPO_ROOT": str(target),
        },
    )

    assert selected == target.resolve()


def test_runtime_repository_root_rejects_missing_sealed_target(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        RuntimeError,
        match="HOLOINDEX_SEALED_TARGET_REPO_ROOT_INVALID",
    ):
        runtime_repository_root(
            tmp_path,
            environ={"REDDOG_SEALED_RUNTIME_REQUIRED": "1"},
        )
