"""Tests for git main-merge sentinel startup safety."""

from __future__ import annotations

from pathlib import Path

import pytest

from modules.infrastructure.wre_core.src import git_main_merge_sentinel as sentinel


def test_sentinel_disabled_by_default_does_not_call_git(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("GIT_MAIN_MERGE_SENTINEL", raising=False)

    def fail_git(*args, **kwargs):
        raise AssertionError("git must not be called when sentinel is disabled by default")

    monkeypatch.setattr(sentinel, "_git", fail_git)

    result = sentinel.run_main_merge_sentinel(tmp_path)

    assert result["passed"] is True
    assert result["merged"] is False
    assert result["actions"] == ["skip (disabled)"]


def test_enabled_sentinel_skips_on_main(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("GIT_MAIN_MERGE_SENTINEL", "1")
    calls: list[list[str]] = []

    def fake_git(args, repo_root, timeout=30):
        calls.append(args)
        assert args == ["rev-parse", "--abbrev-ref", "HEAD"]
        return True, "main"

    monkeypatch.setattr(sentinel, "_git", fake_git)

    result = sentinel.run_main_merge_sentinel(tmp_path)

    assert result["passed"] is True
    assert result["merged"] is False
    assert result["actions"] == ["skip (already on main)"]
    assert calls == [["rev-parse", "--abbrev-ref", "HEAD"]]


def test_enabled_sentinel_blocks_when_main_checked_out_elsewhere(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("GIT_MAIN_MERGE_SENTINEL", "1")
    feature = tmp_path / "feature"
    main = tmp_path / "main"
    feature.mkdir()
    main.mkdir()
    calls: list[list[str]] = []

    worktree_output = "\n".join(
        [
            f"worktree {feature}",
            "HEAD " + "a" * 40,
            "branch refs/heads/feature/demo",
            "",
            f"worktree {main}",
            "HEAD " + "b" * 40,
            "branch refs/heads/main",
            "",
        ]
    )

    def fake_git(args, repo_root, timeout=30):
        calls.append(args)
        if args == ["rev-parse", "--abbrev-ref", "HEAD"]:
            return True, "feature/demo"
        if args == ["worktree", "list", "--porcelain"]:
            return True, worktree_output
        raise AssertionError(f"unexpected git call after worktree block: {args}")

    monkeypatch.setattr(sentinel, "_git", fake_git)

    result = sentinel.run_main_merge_sentinel(feature)

    assert result["passed"] is True
    assert result["merged"] is False
    assert result["error"] == "main_checked_out_in_another_worktree"
    assert result["main_worktree_paths"] == [str(main.resolve())]
    assert result["actions"] == ["blocked: main checked out in another worktree"]
    assert calls == [
        ["rev-parse", "--abbrev-ref", "HEAD"],
        ["worktree", "list", "--porcelain"],
    ]


def test_enforced_sentinel_fails_when_main_checked_out_elsewhere(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("GIT_MAIN_MERGE_SENTINEL", "1")
    monkeypatch.setenv("GIT_MAIN_MERGE_SENTINEL_ENFORCED", "1")
    feature = tmp_path / "feature"
    main = tmp_path / "main"
    feature.mkdir()
    main.mkdir()

    def fake_git(args, repo_root, timeout=30):
        if args == ["rev-parse", "--abbrev-ref", "HEAD"]:
            return True, "feature/demo"
        if args == ["worktree", "list", "--porcelain"]:
            return True, f"worktree {main}\nbranch refs/heads/main\n"
        raise AssertionError(f"unexpected git call after worktree block: {args}")

    monkeypatch.setattr(sentinel, "_git", fake_git)

    result = sentinel.run_main_merge_sentinel(feature)

    assert result["passed"] is False
    assert result["merged"] is False
    assert result["error"] == "main_checked_out_in_another_worktree"
