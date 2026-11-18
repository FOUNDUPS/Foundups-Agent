"""Exercise PC main synchronization against disposable Git repositories."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from modules.infrastructure.wre_core.src.git_lifecycle_pc import reconcile_pc_main


def _runner(args, *, cwd: Path, timeout: int):
    return subprocess.run(
        args, cwd=cwd, timeout=timeout, capture_output=True, text=True, encoding="utf-8"
    )


def _git(root: Path, *args: str) -> str:
    result = _runner(("git", *args), cwd=root, timeout=30)
    result.check_returncode()
    return result.stdout.strip()


def _commit(root: Path, filename: str, content: str) -> str:
    (root / filename).write_text(content, encoding="utf-8")
    _git(root, "add", "--", filename)
    _git(root, "commit", "-m", f"Update {filename}")
    return _git(root, "rev-parse", "HEAD")


@pytest.fixture()
def repository(tmp_path: Path):
    origin = tmp_path / "remote.git"
    writer = tmp_path / "writer"
    pc = tmp_path / "PC worktree"
    _git(tmp_path, "init", "--bare", "--initial-branch=main", str(origin))
    _git(tmp_path, "init", "--initial-branch=main", str(writer))
    _git(writer, "config", "user.name", "PC Sync Test")
    _git(writer, "config", "user.email", "pc-sync@example.invalid")
    _git(writer, "remote", "add", "origin", str(origin))
    initial = _commit(writer, "README.md", "initial\n")
    _git(writer, "push", "origin", "main")
    _git(tmp_path, "clone", str(origin), str(pc))
    _git(pc, "config", "user.name", "PC Sync Test")
    _git(pc, "config", "user.email", "pc-sync@example.invalid")
    return writer, pc, initial


def _advance(writer: Path, filename: str = "README.md", text: str = "new main\n") -> str:
    revision = _commit(writer, filename, text)
    _git(writer, "push", "origin", "main")
    return revision


def test_aligned_checkout_verifies_without_writing_refs(repository) -> None:
    _, pc, initial = repository

    def read_only(args, *, cwd, timeout):
        assert "fetch" not in args and "merge" not in args
        return _runner(args, cwd=cwd, timeout=timeout)

    result = reconcile_pc_main(pc, initial, allow_update=False, runner=read_only)
    assert result == {
        "status": "PC_SYNC_VERIFIED",
        "head_sha": initial,
        "reason": "already_current",
        "updated": False,
    }


def test_clean_linked_main_fast_forwards_and_preserves_primary(repository) -> None:
    writer, pc, initial = repository
    _git(pc, "switch", "-c", "agent/active")
    linked = pc.parent / "designated main"
    _git(pc, "worktree", "add", str(linked), "main")
    (pc / "README.md").write_text("owned edits\n", encoding="utf-8")
    (pc / "untracked.txt").write_text("preserve\n", encoding="utf-8")
    target = _advance(writer)

    result = reconcile_pc_main(linked, target, allow_update=True, runner=_runner)

    assert result == {
        "status": "PC_SYNC_VERIFIED",
        "head_sha": target,
        "reason": "fast_forwarded",
        "updated": True,
    }
    assert _git(linked, "rev-parse", "HEAD") == target
    assert (linked / "README.md").read_text(encoding="utf-8") == "new main\n"
    assert _git(pc, "rev-parse", "HEAD") == initial
    assert _git(pc, "branch", "--show-current") == "agent/active"
    assert (pc / "README.md").read_text(encoding="utf-8") == "owned edits\n"
    assert (pc / "untracked.txt").read_text(encoding="utf-8") == "preserve\n"


def test_unselected_main_does_not_fetch_or_merge(repository) -> None:
    writer, pc, initial = repository
    target = _advance(writer)

    def read_only(args, *, cwd, timeout):
        assert "fetch" not in args and "merge" not in args
        return _runner(args, cwd=cwd, timeout=timeout)

    result = reconcile_pc_main(pc, target, allow_update=False, runner=read_only)

    assert result["status"] == "PC_SYNC_PENDING"
    assert result["reason"] == "update_not_authorized"
    assert result["head_sha"] == initial
    assert _git(pc, "rev-parse", "refs/remotes/origin/main") == initial


@pytest.mark.parametrize("filename", ["README.md", "untracked.txt"])
def test_dirty_main_is_preserved(repository, filename: str) -> None:
    writer, pc, initial = repository
    target = _advance(writer)
    _git(pc, "config", "status.showUntrackedFiles", "no")
    (pc / filename).write_text("local work\n", encoding="utf-8")

    result = reconcile_pc_main(pc, target, allow_update=True, runner=_runner)

    assert result == {
        "status": "PC_SYNC_BLOCKED",
        "head_sha": initial,
        "reason": "working_tree_dirty",
        "updated": False,
    }
    assert (pc / filename).read_text(encoding="utf-8") == "local work\n"
    assert _git(pc, "rev-parse", "refs/remotes/origin/main") == initial


def test_ignored_file_collision_blocks_without_overwrite(repository) -> None:
    writer, pc, initial = repository
    target = _advance(writer, "local-only.txt", "newly tracked\n")
    (pc / ".git" / "info" / "exclude").write_text("local-only.txt\n", encoding="utf-8")
    (pc / "local-only.txt").write_text("ignored local work\n", encoding="utf-8")
    assert _git(pc, "status", "--porcelain=v1") == ""

    result = reconcile_pc_main(pc, target, allow_update=True, runner=_runner)

    assert result["status"] == "PC_SYNC_BLOCKED"
    assert result["reason"] == "fast_forward_failed"
    assert result["head_sha"] == initial
    assert result["updated"] is False
    assert (pc / "local-only.txt").read_text(encoding="utf-8") == "ignored local work\n"


def test_active_topic_is_preserved_even_when_update_is_allowed(repository) -> None:
    writer, pc, initial = repository
    target = _advance(writer)
    _git(pc, "switch", "-c", "agent/active")

    result = reconcile_pc_main(pc, target, allow_update=True, runner=_runner)

    assert result["status"] == "PC_SYNC_PENDING"
    assert result["reason"] == "main_not_checked_out"
    assert _git(pc, "branch", "--show-current") == "agent/active"
    assert _git(pc, "rev-parse", "HEAD") == initial


def test_stale_target_is_rejected_before_fetch(repository) -> None:
    writer, pc, initial = repository
    _advance(writer)

    result = reconcile_pc_main(pc, initial, allow_update=True, runner=_runner)

    assert result["status"] == "PC_SYNC_BLOCKED"
    assert result["reason"] == "remote_main_changed"
    assert _git(pc, "rev-parse", "refs/remotes/origin/main") == initial


def test_diverged_local_main_is_preserved(repository) -> None:
    writer, pc, _ = repository
    target = _advance(writer)
    local = _commit(pc, "unique.txt", "local commit\n")

    result = reconcile_pc_main(pc, target, allow_update=True, runner=_runner)

    assert result["status"] == "PC_SYNC_BLOCKED"
    assert result["reason"] == "local_main_not_fast_forwardable"
    assert result["head_sha"] == local
    assert _git(pc, "rev-parse", "HEAD") == local


def test_remote_moving_after_fetch_blocks_before_checkout(repository) -> None:
    writer, pc, initial = repository
    target = _advance(writer)

    def move_after_fetch(args, *, cwd, timeout):
        result = _runner(args, cwd=cwd, timeout=timeout)
        if "fetch" in args:
            _advance(writer, text="newer main\n")
        assert "merge" not in args
        return result

    result = reconcile_pc_main(pc, target, allow_update=True, runner=move_after_fetch)

    assert result["status"] == "PC_SYNC_BLOCKED"
    assert result["reason"] == "remote_main_changed"
    assert _git(pc, "rev-parse", "HEAD") == initial


def test_remote_moving_after_update_records_observed_effect(repository) -> None:
    writer, pc, _ = repository
    target = _advance(writer)

    def move_after_update(args, *, cwd, timeout):
        result = _runner(args, cwd=cwd, timeout=timeout)
        if "merge" in args:
            _advance(writer, text="newer main\n")
        return result

    result = reconcile_pc_main(pc, target, allow_update=True, runner=move_after_update)

    assert result == {
        "status": "PC_SYNC_BLOCKED",
        "head_sha": target,
        "reason": "remote_main_changed",
        "updated": True,
    }
    assert _git(pc, "rev-parse", "HEAD") == target


def test_remote_query_failure_reports_only_bounded_reason(repository) -> None:
    writer, pc, initial = repository
    target = _advance(writer)

    def unreadable(args, *, cwd, timeout):
        if "ls-remote" in args:
            return subprocess.CompletedProcess(args, 1, "", "private transport detail")
        assert "fetch" not in args and "merge" not in args
        return _runner(args, cwd=cwd, timeout=timeout)

    result = reconcile_pc_main(pc, target, allow_update=True, runner=unreadable)

    assert result == {
        "status": "PC_SYNC_BLOCKED",
        "head_sha": initial,
        "reason": "remote_main_unverified",
        "updated": False,
    }


def test_dirty_change_after_fetch_blocks_before_checkout(repository) -> None:
    writer, pc, initial = repository
    target = _advance(writer)

    def local_edit_after_fetch(args, *, cwd, timeout):
        result = _runner(args, cwd=cwd, timeout=timeout)
        if "fetch" in args:
            (pc / "late.txt").write_text("preserve late work\n", encoding="utf-8")
        assert "merge" not in args
        return result

    result = reconcile_pc_main(pc, target, allow_update=True, runner=local_edit_after_fetch)

    assert result == {
        "status": "PC_SYNC_BLOCKED",
        "head_sha": initial,
        "reason": "working_tree_dirty",
        "updated": False,
    }
    assert _git(pc, "rev-parse", "HEAD") == initial
    assert (pc / "late.txt").read_text(encoding="utf-8") == "preserve late work\n"
