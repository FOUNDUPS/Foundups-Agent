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


FETCHED_COMMIT = "a1" * 20


def _sync_transcript_steps(delete_branch, sync_failure, fetched_commit):
    """Explicit successful transcript, truncated at a declared failing stage."""
    steps = [
        ("git", ["fetch", "--no-tags", "--quiet", "origin",
                 "+refs/heads/main:refs/remotes/origin/main"], (True, "")),
        ("git", ["rev-parse", "--verify", "refs/remotes/origin/main^{commit}"],
         (True, fetched_commit)),
        ("git", ["status", "--porcelain", "--untracked-files=all"], (True, "")),
        ("git", ["branch", "-f", "main", fetched_commit], (True, "")),
        ("git", ["checkout", "main"], (True, "")),
    ]
    if sync_failure:
        stage, response = sync_failure
        index = {"fetch": 0, "resolve": 1, "late_status": 2, "update": 3}[stage]
        tool, args, _ = steps[index]
        return steps[:index] + [(tool, args, response)]
    if delete_branch:
        steps.extend([
            ("git", ["branch", "-D", "feature/demo"], (True, "")),
            ("git", ["push", "origin", "--delete", "feature/demo"], (True, "")),
            ("git", ["push", "backup", "--delete", "feature/demo"], (True, "")),
        ])
    return steps


def _cleanup_transcript_steps(
    tmp_path: Path, route: str, *,
    cleanup_response: tuple[bool, str] = (True, ""),
    delete_branch: bool = False, merge_succeeds: bool = True,
    sync_failure: tuple | None = None, fetched_commit: str = FETCHED_COMMIT,
) -> list:
    """Declare ordered command responses for the scoped cleanup contract."""
    assert route in ("direct", "existing", "new", "create_failure")
    assert route != "direct" or merge_succeeds
    steps = []

    def add(tool, args, response=(True, "")):
        steps.append((tool, args, response))

    add("git", ["rev-parse", "--abbrev-ref", "HEAD"], (True, "feature/demo"))
    add("git", ["worktree", "list", "--porcelain"],
        (True, f"worktree {tmp_path}\nbranch refs/heads/feature/demo\n"))
    add("git", ["status", "--porcelain", "--untracked-files=all"])
    add("git", ["fetch", "--all", "--quiet"])
    add("git", ["push", "origin", "feature/demo"])
    add("git", ["push", "backup", "feature/demo"])
    add("git", ["push", "origin", "HEAD:main"], (route == "direct", ""))
    merged = merge_succeeds and route != "create_failure"
    if route == "direct":
        add("git", ["push", "backup", "HEAD:main"])
    else:
        add("gh", ["pr", "view", "--json", "state,number"],
            (True, '{"state":"OPEN","number":42}') if route == "existing" else (False, "no PR"))
        if route != "existing":
            add("gh", ["pr", "create", "--fill", "--base", "main"],
                (route != "create_failure", "fixture PR"))
        if route != "create_failure":
            add("gh", ["pr", "merge", "--merge"], (merge_succeeds, "fixture merge"))
    if merged:
        add("git", ["status", "--porcelain", "--untracked-files=all"], cleanup_response)
        if cleanup_response[0] and not cleanup_response[1].strip():
            steps.extend(_sync_transcript_steps(delete_branch, sync_failure, fetched_commit))
    return steps


def _install_cleanup_transcript(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, route: str, *,
    cleanup_response: tuple[bool, str] = (True, ""),
    delete_branch: bool = False, merge_succeeds: bool = True,
    sync_failure: tuple | None = None, fetched_commit: str = FETCHED_COMMIT,
) -> tuple[list, list]:
    """Install fakes which reject any extra, missing or reordered command."""
    monkeypatch.setenv("GIT_MAIN_MERGE_SENTINEL", "1")
    monkeypatch.setenv("GIT_MAIN_MERGE_SENTINEL_DELETE_BRANCH", str(int(delete_branch)))
    steps = _cleanup_transcript_steps(
        tmp_path, route, cleanup_response=cleanup_response,
        delete_branch=delete_branch, merge_succeeds=merge_succeeds,
        sync_failure=sync_failure, fetched_commit=fetched_commit,
    )
    calls = []

    def scripted(tool, args, repo_root, timeout):
        assert repo_root == tmp_path
        index = len(calls)
        assert index < len(steps), f"unexpected command: {tool} {args}"
        expected_tool, expected_args, response = steps[index]
        assert (tool, args) == (expected_tool, expected_args)
        calls.append((tool, args))
        return response

    monkeypatch.setattr(sentinel, "_git", lambda args, repo_root, timeout=30:
                        scripted("git", args, repo_root, timeout))
    monkeypatch.setattr(sentinel, "_gh", lambda args, repo_root, timeout=60:
                        scripted("gh", args, repo_root, timeout))
    return calls, steps


@pytest.mark.parametrize("route", ["direct", "existing", "new"])
@pytest.mark.parametrize("enforced", [False, True])
@pytest.mark.parametrize(
    "cleanup_response,error",
    [((True, " M concurrent.py"), "cleanup_working_tree_dirty"),
     ((True, "?? concurrent.py"), "cleanup_working_tree_dirty"),
     ((False, "unavailable"), "cleanup_status_failed")],
    ids=["tracked", "untracked", "unreadable"],
)
def test_cleanup_preserves_detected_or_unknown_work(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, route: str,
    enforced: bool, cleanup_response: tuple[bool, str], error: str,
) -> None:
    monkeypatch.setenv("GIT_MAIN_MERGE_SENTINEL_ENFORCED", str(int(enforced)))
    calls, steps = _install_cleanup_transcript(
        monkeypatch, tmp_path, route, cleanup_response=cleanup_response, delete_branch=True,
    )
    result = sentinel.run_main_merge_sentinel(tmp_path)
    assert result["merged"] is True  # Command success, not independently verified main.
    assert result["passed"] is not enforced
    assert result["error"] == error
    assert result["actions"][-1] == "blocked: cleanup requires a clean, readable working tree"
    assert len(calls) == len(steps)
    assert calls[-1] == ("git", ["status", "--porcelain", "--untracked-files=all"])
    assert not any(args[0] in ("branch", "checkout", "stash") or
                   "--delete" in args or "--delete-branch" in args for _, args in calls)


@pytest.mark.parametrize("route", ["direct", "existing", "new"])
@pytest.mark.parametrize("delete_branch", [False, True])
def test_clean_cleanup_keeps_explicit_deletion_setting(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, route: str, delete_branch: bool,
) -> None:
    calls, steps = _install_cleanup_transcript(monkeypatch, tmp_path, route, delete_branch=delete_branch)
    result = sentinel.run_main_merge_sentinel(tmp_path)
    assert result["merged"] is True
    assert result["passed"] is True
    assert result["error"] is None
    assert len(calls) == len(steps)
    assert not any(args[0] == "stash" or "--delete-branch" in args for _, args in calls)
    assert (("git", ["branch", "-D", "feature/demo"]) in calls) is delete_branch
    assert ("git", ["branch", "-f", "main", FETCHED_COMMIT]) in calls
    assert not any(args == ["branch", "-f", "main", "origin/main"] for _, args in calls)


@pytest.mark.parametrize("route", ["existing", "new", "create_failure"])
@pytest.mark.parametrize("enforced", [False, True])
def test_terminal_merge_failure_never_enters_cleanup(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, route: str, enforced: bool,
) -> None:
    monkeypatch.setenv("GIT_MAIN_MERGE_SENTINEL_ENFORCED", str(int(enforced)))
    calls, steps = _install_cleanup_transcript(
        monkeypatch, tmp_path, route, delete_branch=True, merge_succeeds=False,
    )
    result = sentinel.run_main_merge_sentinel(tmp_path)
    assert result["merged"] is False
    assert result["passed"] is not enforced
    assert result["error"] == "Could not merge to main (conflicts or permissions)"
    assert len(calls) == len(steps)
    assert sum(args[0] == "status" for _, args in calls) == 1
    assert not any(args[0] in ("branch", "checkout", "stash") or
                   "--delete" in args or "--delete-branch" in args for _, args in calls)


@pytest.mark.parametrize("route", ["direct", "existing", "new"])
@pytest.mark.parametrize("enforced", [False, True])
@pytest.mark.parametrize(
    "stage,response,error",
    [("fetch", (False, "fetch rejected"), "cleanup_fetch_failed"),
     ("resolve", (False, "not a commit"), "cleanup_commit_resolution_failed"),
     ("resolve", (True, ""), "cleanup_commit_resolution_failed"),
     ("resolve", (True, "origin/main"), "cleanup_commit_resolution_failed"),
     ("resolve", (True, "a1a1a1a"), "cleanup_commit_resolution_failed"),
     ("resolve", (True, FETCHED_COMMIT + "\n" + FETCHED_COMMIT), "cleanup_commit_resolution_failed"),
     ("resolve", (True, "z" * 40), "cleanup_commit_resolution_failed"),
     ("late_status", (True, " M concurrent.py"), "cleanup_working_tree_dirty"),
     ("late_status", (True, "?? concurrent.py"), "cleanup_working_tree_dirty"),
     ("late_status", (False, "unreadable"), "cleanup_status_failed"),
     ("update", (False, "main is checked out elsewhere"), "cleanup_main_update_failed")],
    ids=["fetch", "resolve", "empty", "symbolic", "abbreviated", "multiline",
         "nonhex", "late-tracked", "late-untracked", "late-unreadable", "update"],
)
def test_failed_synchronization_stops_before_checkout_or_deletion(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, route: str, enforced: bool,
    stage: str, response: tuple[bool, str], error: str,
) -> None:
    monkeypatch.setenv("GIT_MAIN_MERGE_SENTINEL_ENFORCED", str(int(enforced)))
    calls, steps = _install_cleanup_transcript(
        monkeypatch, tmp_path, route, delete_branch=True, sync_failure=(stage, response),
    )
    result = sentinel.run_main_merge_sentinel(tmp_path)
    assert result["merged"] is True
    assert result["passed"] is not enforced
    assert result["error"] == error
    assert len(calls) == len(steps)
    assert calls[-1] == steps[-1][:2]
    assert not any(args[0] in ("checkout", "stash") or
                   "--delete" in args or "--delete-branch" in args for _, args in calls)
    updates = [args for tool, args in calls if tool == "git" and args[0] == "branch"]
    assert updates == ([["branch", "-f", "main", FETCHED_COMMIT]] if stage == "update" else [])


@pytest.mark.parametrize("delete_branch", [False, True])
def test_sha256_fetched_commit_is_passed_as_exact_local_target(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, delete_branch: bool,
) -> None:
    commit = "b2" * 32
    calls, steps = _install_cleanup_transcript(
        monkeypatch, tmp_path, "existing", delete_branch=delete_branch, fetched_commit=commit,
    )
    result = sentinel.run_main_merge_sentinel(tmp_path)
    assert result["merged"] is True
    assert result["passed"] is True
    assert result["error"] is None
    assert len(calls) == len(steps)
    assert ("git", ["branch", "-f", "main", commit]) in calls
    assert (("git", ["branch", "-D", "feature/demo"]) in calls) is delete_branch
