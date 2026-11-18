"""Tests for the shared-main pre-commit cwd guard."""

from __future__ import annotations

from pathlib import Path

from tools.hooks.pre_commit_worktree_cwd_guard import (
    FAIL_DETACHED_UNSAFE_CHECKOUT,
    FAIL_SHARED_MAIN_CHECKOUT,
    PASS,
    evaluate_pre_commit_cwd,
)


def test_blocks_shared_main_checkout(tmp_path: Path) -> None:
    shared = tmp_path / "Foundups-Agent"
    shared.mkdir()

    decision = evaluate_pre_commit_cwd(
        repo_root=shared,
        shared_repo_root=shared,
        branch="main",
    )

    assert decision.ok is False
    assert decision.code == FAIL_SHARED_MAIN_CHECKOUT


def test_override_allows_shared_main_checkout(tmp_path: Path) -> None:
    shared = tmp_path / "Foundups-Agent"
    shared.mkdir()

    decision = evaluate_pre_commit_cwd(
        repo_root=shared,
        shared_repo_root=shared,
        branch="main",
        allow_override=True,
    )

    assert decision.ok is True
    assert decision.code == PASS


def test_allows_feature_worktree_under_repo_worktrees(tmp_path: Path) -> None:
    shared = tmp_path / "Foundups-Agent"
    worker = shared / ".worktrees" / "feature-x"
    worker.mkdir(parents=True)

    decision = evaluate_pre_commit_cwd(
        repo_root=worker,
        shared_repo_root=shared,
        branch="feat/example",
    )

    assert decision.ok is True
    assert decision.code == PASS


def test_allows_claude_agent_worktree(tmp_path: Path) -> None:
    shared = tmp_path / "Foundups-Agent"
    worker = shared / ".claude" / "worktrees" / "agent-123"
    worker.mkdir(parents=True)

    decision = evaluate_pre_commit_cwd(
        repo_root=worker,
        shared_repo_root=shared,
        branch="worktree-agent-123",
    )

    assert decision.ok is True
    assert decision.code == PASS


def test_blocks_unmarked_detached_checkout(tmp_path: Path) -> None:
    shared = tmp_path / "Foundups-Agent"
    detached = tmp_path / "detached-copy"
    shared.mkdir()
    detached.mkdir()

    decision = evaluate_pre_commit_cwd(
        repo_root=detached,
        shared_repo_root=shared,
        branch="",
    )

    assert decision.ok is False
    assert decision.code == FAIL_DETACHED_UNSAFE_CHECKOUT


def test_allows_detached_clean_build_worktree(tmp_path: Path) -> None:
    shared = tmp_path / "Foundups-Agent"
    build = shared / ".worktrees" / "reddog-build"
    shared.mkdir()
    build.mkdir(parents=True)

    decision = evaluate_pre_commit_cwd(
        repo_root=build,
        shared_repo_root=shared,
        branch="",
    )

    assert decision.ok is True
    assert decision.code == PASS

