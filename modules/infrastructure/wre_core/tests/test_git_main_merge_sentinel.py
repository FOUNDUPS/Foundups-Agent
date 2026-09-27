"""Tests for git main-merge sentinel startup safety."""

from __future__ import annotations

from pathlib import Path

import pytest

from modules.infrastructure.wre_core.src import git_main_merge_sentinel as sentinel


@pytest.fixture(autouse=True)
def isolate_sentinel_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every case supplies exact fake Git responses; no subprocess may escape."""
    for name in ("GIT_MAIN_MERGE_SENTINEL", "GIT_MAIN_MERGE_SENTINEL_ENFORCED"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("GIT_MAIN_MERGE_SENTINEL_DELETE_BRANCH", "0")

    def denied(*args, **kwargs):
        pytest.fail("unexpected external command in sentinel unit test")

    monkeypatch.setattr(sentinel, "_git", denied)
    monkeypatch.setattr(sentinel, "_gh", denied)
    monkeypatch.setattr(sentinel.subprocess, "run", denied)


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


@pytest.mark.parametrize("enforced", [False, True], ids=["advisory", "enforced"])
@pytest.mark.parametrize(
    "stage,response,error",
    [
        ("branch", (False, "unavailable"), "Failed to get current branch: unavailable"),
        ("branch", (True, ""), "named_branch_required"),
        ("branch", (True, "  "), "named_branch_required"),
        ("branch", (True, "HEAD"), "named_branch_required"),
        ("worktrees", (False, "unavailable"), "worktree_discovery_failed"),
        ("worktrees", (True, ""), "worktree_discovery_failed"),
        ("worktrees", (True, "garbled"), "worktree_discovery_failed"),
        ("worktrees", (True, "worktree \nbranch refs/heads/feature/demo"), "worktree_discovery_failed"),
        ("worktrees", (True, "worktree {root}\nHEAD abc"), "worktree_discovery_failed"),
        ("worktrees", (True, "worktree {root}/other\ndetached"), "worktree_discovery_failed"),
        ("worktrees", (True, "worktree {root}\nbranch refs/heads/other"), "worktree_discovery_failed"),
        ("status", (False, "unavailable"), "working_tree_status_failed"),
        ("status", (True, " M existing.py"), "working_tree_dirty"),
        ("status", (True, "?? new.py"), "working_tree_dirty"),
        ("fetch", (False, "unavailable"), "fetch_failed"),
    ],
    ids=["branch-error", "empty-branch", "blank-branch", "detached", "worktree-error",
         "empty-worktrees", "malformed-worktrees", "empty-path", "missing-branch",
         "missing-current", "changed-branch", "status-error", "tracked-dirty",
         "untracked", "fetch-error"],
)
def test_sentinel_rejects_unqualified_prerequisites(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    enforced: bool, stage: str, response: tuple[bool, str], error: str,
) -> None:
    monkeypatch.setenv("GIT_MAIN_MERGE_SENTINEL", "1")
    monkeypatch.setenv("GIT_MAIN_MERGE_SENTINEL_ENFORCED", str(int(enforced)))
    steps = [
        ("branch", ["rev-parse", "--abbrev-ref", "HEAD"], (True, "feature/demo")),
        ("worktrees", ["worktree", "list", "--porcelain"],
         (True, f"worktree {tmp_path}\nbranch refs/heads/feature/demo\n")),
        ("status", ["status", "--porcelain", "--untracked-files=all"], (True, "")),
        ("fetch", ["fetch", "--all", "--quiet"], (True, "")),
    ]
    stop = next(i for i, step in enumerate(steps) if step[0] == stage)
    calls = []

    def fake_git(args, repo_root, timeout=30):
        index = len(calls)
        assert index <= stop, "command escaped failed prerequisite"
        assert repo_root == tmp_path
        assert args == steps[index][1]
        calls.append(args)
        return (response[0], response[1].replace("{root}", str(tmp_path))) if index == stop else steps[index][2]

    monkeypatch.setattr(sentinel, "_git", fake_git)
    result = sentinel.run_main_merge_sentinel(tmp_path)
    assert result["passed"] is not enforced
    assert result["merged"] is False
    assert result["error"] == error
    assert calls == [step[1] for step in steps[:stop + 1]]


@pytest.mark.parametrize("enforced", [False, True])
def test_force_only_bypasses_enablement(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, enforced: bool,
) -> None:
    monkeypatch.setenv("GIT_MAIN_MERGE_SENTINEL_ENFORCED", str(int(enforced)))

    def fake_git(args, repo_root, timeout=30):
        assert args == ["rev-parse", "--abbrev-ref", "HEAD"]
        return True, "HEAD"

    monkeypatch.setattr(sentinel, "_git", fake_git)
    result = sentinel.run_main_merge_sentinel(tmp_path, force=True)
    assert result["error"] == "named_branch_required"
    assert result["passed"] is not enforced
    assert result["merged"] is False


@pytest.mark.parametrize("other_detached", [False, True])
def test_clean_prerequisites_reach_existing_push_boundary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, other_detached: bool,
) -> None:
    monkeypatch.setenv("GIT_MAIN_MERGE_SENTINEL", "1")
    worktrees = f"worktree {tmp_path}\nbranch refs/heads/feature/demo\n"
    if other_detached:
        worktrees += f"\nworktree {tmp_path}/other\ndetached\n"
    steps = [
        (["rev-parse", "--abbrev-ref", "HEAD"], (True, "feature/demo")),
        (["worktree", "list", "--porcelain"],
         (True, worktrees)),
        (["status", "--porcelain", "--untracked-files=all"], (True, "")),
        (["fetch", "--all", "--quiet"], (True, "")),
    ]
    calls = []

    class ReachedPush(Exception):
        pass

    def fake_git(args, repo_root, timeout=30):
        index = len(calls)
        calls.append(args)
        if index == len(steps):
            assert args == ["push", "origin", "feature/demo"]
            raise ReachedPush
        assert args == steps[index][0]
        return steps[index][1]

    monkeypatch.setattr(sentinel, "_git", fake_git)
    with pytest.raises(ReachedPush):
        sentinel.run_main_merge_sentinel(tmp_path)
    assert len(calls) == len(steps) + 1


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
