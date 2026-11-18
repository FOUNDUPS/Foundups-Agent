"""Regression checks for the read-only PC Git inventory receipt."""

from copy import deepcopy
from datetime import datetime, timedelta
import hashlib
import subprocess

import pytest

from modules.infrastructure.wre_core.src import git_lifecycle_inventory as inventory


REQUEST_ID = "request-1a23"
GITHUB_HEAD = "2" * 40


def _git(root, *args):
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True,
    ).stdout.strip()


@pytest.fixture
def checkout(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    hooks = tmp_path / "empty-hooks"
    hooks.mkdir()
    _git(root, "init", "--quiet", "--initial-branch=main")
    _git(root, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
         "-c", f"core.hooksPath={hooks}", "commit", "--quiet", "--allow-empty", "-m", "fixture")
    _git(root, "remote", "add", "origin", inventory._ORIGIN)
    _git(root, "branch", "local")
    _git(root, "worktree", "add", "--quiet", "--detach", str(tmp_path / "private-checkout"))
    (root / "private-filename").write_text("test", encoding="utf-8")
    return root


def _runner(*, move=False, rewrite=False):
    calls = []

    def run(args, *, cwd, timeout):
        calls.append(args)
        if "--get-url" in args and rewrite:
            return subprocess.CompletedProcess(args, 0, "https://example.invalid/repo.git\n", "")
        if "--heads" in args:
            assert args[-1] == inventory._ORIGIN
            if move:
                _git(cwd, "branch", "concurrent-change")
            return subprocess.CompletedProcess(
                args, 0, f"{GITHUB_HEAD}\trefs/heads/main\n{GITHUB_HEAD}\trefs/heads/remote\n", "",
            )
        return inventory.run_command(args, cwd=cwd, timeout=timeout)

    return run, calls


def test_inventory_binds_request_and_projects_only_git_metadata(checkout):
    runner, calls = _runner()
    head = _git(checkout, "rev-parse", "HEAD")
    index = checkout / ".git" / "index"
    before = index.read_bytes() if index.exists() else None
    result = inventory.get_git_inventory(checkout, REQUEST_ID, runner=runner)
    assert inventory.verify_git_inventory_receipt(result, REQUEST_ID)
    receipt = result["receipt"]
    assert receipt["selected_pc"] == {
        "head": head, "branch": "refs/heads/main", "clean": False,
    }
    assert receipt["github_main"] == GITHUB_HEAD
    assert receipt["branches"] == [
        {"ref": "refs/heads/local", "pc": head, "github": None},
        {"ref": "refs/heads/main", "pc": head, "github": GITHUB_HEAD},
        {"ref": "refs/heads/remote", "pc": None, "github": GITHUB_HEAD},
    ]
    assert len(receipt["worktrees"]) == 2
    assert sum(row["detached"] for row in receipt["worktrees"]) == 1
    assert "private-checkout" not in str(result)
    assert "private-filename" not in str(result)
    assert len([args for args in calls if "--heads" in args]) == 1
    assert (index.read_bytes() if index.exists() else None) == before


def test_inventory_verifier_rejects_stale_replayed_or_altered_receipt(checkout):
    runner, _ = _runner()
    result = inventory.get_git_inventory(checkout, REQUEST_ID, runner=runner)
    observed = datetime.fromisoformat(result["receipt"]["observed_at"])
    assert not inventory.verify_git_inventory_receipt(
        result, REQUEST_ID, now=observed + timedelta(minutes=3),
    )
    assert not inventory.verify_git_inventory_receipt(result, "other-123")
    tampered = deepcopy(result)
    tampered["receipt"]["selected_pc"]["clean"] = True
    assert not inventory.verify_git_inventory_receipt(tampered, REQUEST_ID)


def test_inventory_rejects_invalid_request_before_running_git(checkout):
    runner, calls = _runner()
    assert inventory.get_git_inventory(checkout, "a\nb", runner=runner) == {
        "status": "blocked", "reason": "request_id_invalid",
    }
    assert calls == []


def test_inventory_refuses_noncanonical_origin_or_rewritten_github_url(checkout):
    runner, calls = _runner(rewrite=True)
    assert inventory.get_git_inventory(checkout, REQUEST_ID, runner=runner) == {
        "status": "blocked", "reason": "github_route_unverified",
    }
    _git(checkout, "remote", "set-url", "origin", "https://example.invalid/repo.git")
    assert inventory.get_git_inventory(checkout, REQUEST_ID, runner=runner) == {
        "status": "blocked", "reason": "origin_unverified",
    }
    assert not any("--heads" in args for args in calls)


def test_inventory_blocks_when_local_refs_change_during_remote_observation(checkout):
    runner, _ = _runner(move=True)
    assert inventory.get_git_inventory(checkout, REQUEST_ID, runner=runner) == {
        "status": "blocked", "reason": "pc_state_changed_during_observation",
    }


def test_inventory_pages_have_one_snapshot_digest_and_bounded_rows(checkout, monkeypatch):
    monkeypatch.setattr(inventory, "_PAGE_SIZE", 1)
    runner, _ = _runner()
    summary = inventory.get_git_inventory(checkout, REQUEST_ID, section="summary", runner=runner)
    first = inventory.get_git_inventory(checkout, REQUEST_ID, section="worktrees", runner=runner)
    last = inventory.get_git_inventory(checkout, REQUEST_ID, section="worktrees", offset=1, runner=runner)
    branches = inventory.get_git_inventory(checkout, REQUEST_ID, section="branches", runner=runner)
    for result in (summary, first, last, branches):
        assert inventory.verify_git_inventory_receipt(result, REQUEST_ID)
        assert result["receipt"]["inventory_sha256"] == summary["receipt"]["inventory_sha256"]
    assert summary["receipt"]["branch_comparison"] == {
        "same_tip": 0, "different_tip": 1, "pc_only": 1, "github_only": 1,
    }
    assert summary["receipt"]["branch_count"] == 3
    assert summary["receipt"]["worktree_count"] == 2
    assert summary["receipt"]["branches"] == summary["receipt"]["worktrees"] == []
    assert first["receipt"]["next_offset"] == branches["receipt"]["next_offset"] == 1
    assert last["receipt"]["next_offset"] is None
    assert first["receipt"]["worktrees"] != last["receipt"]["worktrees"]
    assert inventory.get_git_inventory(checkout, REQUEST_ID, section="summary", offset=1) == {
        "status": "blocked", "reason": "page_invalid",
    }


def _commit_file(root, hooks, name, content, message):
    (root / name).write_text(content, encoding="utf-8")
    _git(root, "add", name)
    _git(
        root, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
        "-c", f"core.hooksPath={hooks}", "commit", "--quiet", "-m", message,
    )
    return _git(root, "rev-parse", "HEAD")


def _runner_with_main(main_sha, *, on_heads=None):
    def run(args, *, cwd, timeout):
        if "--heads" in args:
            if on_heads is not None:
                on_heads(cwd)
            return subprocess.CompletedProcess(
                args, 0, f"{main_sha}\trefs/heads/main\n", "",
            )
        return inventory.run_command(args, cwd=cwd, timeout=timeout)

    return run


def test_inventory_stashes_paginate_without_leaking_messages_or_filenames(
    checkout, tmp_path, monkeypatch,
):
    hooks = tmp_path / "empty-hooks"
    _commit_file(checkout, hooks, "secret-stash-file.txt", "base\n", "base file")
    git_identity = ("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid")
    (checkout / "secret-stash-file.txt").write_text("v1\n", encoding="utf-8")
    _git(checkout, *git_identity, "stash", "push", "-m", "secret-stash-msg-1")
    (checkout / "secret-stash-file.txt").write_text("v2\n", encoding="utf-8")
    _git(checkout, *git_identity, "stash", "push", "-m", "secret-stash-msg-2")
    sha0 = _git(checkout, "rev-parse", "stash@{0}")
    sha1 = _git(checkout, "rev-parse", "stash@{1}")

    runner, _ = _runner()
    full = inventory.get_git_inventory(checkout, REQUEST_ID, runner=runner)
    assert inventory.verify_git_inventory_receipt(full, REQUEST_ID)
    assert full["receipt"]["stashes"] == [{"sha": sha0}, {"sha": sha1}]
    assert full["receipt"]["pc_backlog_summary"]["stash_count"] == 2
    serialized = str(full)
    for forbidden in ("secret-stash-msg-1", "secret-stash-msg-2", "secret-stash-file.txt"):
        assert forbidden not in serialized

    monkeypatch.setattr(inventory, "_PAGE_SIZE", 1)
    summary = inventory.get_git_inventory(checkout, REQUEST_ID, section="summary", runner=runner)
    page0 = inventory.get_git_inventory(checkout, REQUEST_ID, section="stashes", runner=runner)
    page1 = inventory.get_git_inventory(
        checkout, REQUEST_ID, section="stashes", offset=1, runner=runner,
    )
    for result in (summary, page0, page1):
        assert inventory.verify_git_inventory_receipt(result, REQUEST_ID)
        assert result["receipt"]["stash_count"] == 2
        assert result["receipt"]["inventory_sha256"] == summary["receipt"]["inventory_sha256"]
    assert summary["receipt"]["stashes"] == []
    assert summary["receipt"]["next_offset"] is None
    assert page0["receipt"]["stashes"] == [{"sha": sha0}]
    assert page0["receipt"]["branches"] == page0["receipt"]["worktrees"] == []
    assert page0["receipt"]["next_offset"] == 1
    assert page1["receipt"]["stashes"] == [{"sha": sha1}]
    assert page1["receipt"]["next_offset"] is None


def test_read_stashes_rejects_malformed_or_oversized_reflog(tmp_path):
    def bad_tip(cwd, *args, reason, timeout=6):
        return "not-a-sha\n"

    with pytest.raises(inventory._InventoryError, match="stash_inventory_invalid_or_too_large"):
        inventory._read_stashes(bad_tip, tmp_path)

    def too_many(cwd, *args, reason, timeout=6):
        if "for-each-ref" in args:
            return f"{'a' * 40}\n"
        return "\n".join("b" * 40 for _ in range(inventory._MAX_ROWS + 1)) + "\n"

    with pytest.raises(inventory._InventoryError, match="stash_inventory_invalid_or_too_large"):
        inventory._read_stashes(too_many, tmp_path)

    def empty_walk(cwd, *args, reason, timeout=6):
        return f"{'a' * 40}\n" if "for-each-ref" in args else ""

    with pytest.raises(inventory._InventoryError, match="stash_inventory_invalid_or_too_large"):
        inventory._read_stashes(empty_walk, tmp_path)


def test_inventory_blocks_when_stashes_change_during_remote_observation(checkout, tmp_path):
    hooks = tmp_path / "empty-hooks"
    _commit_file(checkout, hooks, "tracked.txt", "base\n", "base tracked")
    (checkout / "tracked.txt").write_text("dirty\n", encoding="utf-8")

    def mutate_stash_only(cwd):
        stash_sha = _git(
            cwd, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
            "stash", "create",
        )
        _git(cwd, "stash", "store", "-m", "concurrent-stash", stash_sha)

    runner = _runner_with_main(GITHUB_HEAD, on_heads=mutate_stash_only)
    assert inventory.get_git_inventory(checkout, REQUEST_ID, runner=runner) == {
        "status": "blocked", "reason": "pc_state_changed_during_observation",
    }


def test_inventory_backlog_and_worktree_summaries_with_present_vs_absent_github_main(
    checkout, tmp_path,
):
    hooks = tmp_path / "empty-hooks"
    main_sha = _commit_file(checkout, hooks, "app.txt", "main\n", "advance main")
    _git(checkout, "branch", "merged-unattached", main_sha)

    _git(checkout, "checkout", "--quiet", "-b", "unmerged-unattached")
    _commit_file(checkout, hooks, "unmerged.txt", "u1\n", "unmerged unattached")
    _git(checkout, "checkout", "--quiet", "-b", "unmerged-attached", main_sha)
    _commit_file(checkout, hooks, "attached.txt", "a1\n", "unmerged attached")
    _git(checkout, "checkout", "--quiet", "main")

    attached_wt = tmp_path / "attached-wt"
    _git(checkout, "worktree", "add", "--quiet", str(attached_wt), "unmerged-attached")
    _git(checkout, "worktree", "lock", str(attached_wt))

    (checkout / "app.txt").write_text("stashed\n", encoding="utf-8")
    _git(
        checkout, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
        "stash", "push", "-m", "backlog-stash",
    )

    present = inventory.get_git_inventory(
        checkout, REQUEST_ID, runner=_runner_with_main(main_sha),
    )
    assert inventory.verify_git_inventory_receipt(present, REQUEST_ID)
    assert present["receipt"]["github_main_present_on_pc"] is True
    assert present["receipt"]["pc_backlog_summary"] == {
        "local_head_count": 5,
        "attached_worktree_branch_count": 2,
        "merged_into_github_main_count": 3,
        "unmerged_unattached_head_count": 1,
        "stash_count": 1,
    }
    assert present["receipt"]["worktree_summary"] == {
        "total": 3, "attached": 2, "detached": 1, "bare": 0, "locked": 1, "prunable": 0,
    }

    absent = inventory.get_git_inventory(
        checkout, REQUEST_ID, runner=_runner_with_main(GITHUB_HEAD),
    )
    assert inventory.verify_git_inventory_receipt(absent, REQUEST_ID)
    assert absent["receipt"]["github_main_present_on_pc"] is False
    assert absent["receipt"]["pc_backlog_summary"] == {
        "local_head_count": 5,
        "attached_worktree_branch_count": 2,
        "merged_into_github_main_count": None,
        "unmerged_unattached_head_count": None,
        "stash_count": 1,
    }
    assert absent["receipt"]["worktree_summary"] == present["receipt"]["worktree_summary"]


def _resign(result):
    signed = deepcopy(result)
    signed["sha256"] = hashlib.sha256(inventory._canonical(signed["receipt"])).hexdigest()
    return signed


def test_inventory_verifier_rejects_malformed_or_tampered_stashes_and_summaries(
    checkout, tmp_path,
):
    hooks = tmp_path / "empty-hooks"
    main_sha = _commit_file(checkout, hooks, "item.txt", "x\n", "main commit")
    (checkout / "item.txt").write_text("y\n", encoding="utf-8")
    _git(
        checkout, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
        "stash", "push", "-m", "stash-msg",
    )

    present_result = inventory.get_git_inventory(
        checkout, REQUEST_ID, runner=_runner_with_main(main_sha),
    )
    absent_result = inventory.get_git_inventory(
        checkout, REQUEST_ID, runner=_runner_with_main(GITHUB_HEAD),
    )
    assert inventory.verify_git_inventory_receipt(present_result, REQUEST_ID)
    assert inventory.verify_git_inventory_receipt(absent_result, REQUEST_ID)

    bad_stashes = [
        {"stashes": "not-a-list"},
        {"stashes": [{"sha": "bad"}]},
        {"stashes": [{"sha": "a" * 40, "message": "leak"}]},
        {"stashes": []},
    ]
    for patch in bad_stashes:
        tampered = deepcopy(present_result)
        tampered["receipt"].update(patch)
        assert not inventory.verify_git_inventory_receipt(tampered, REQUEST_ID)
        assert not inventory.verify_git_inventory_receipt(_resign(tampered), REQUEST_ID)

    tampered_bool = deepcopy(present_result)
    tampered_bool["receipt"]["github_main_present_on_pc"] = 1
    assert not inventory.verify_git_inventory_receipt(_resign(tampered_bool), REQUEST_ID)

    tampered_none = deepcopy(present_result)
    tampered_none["receipt"]["pc_backlog_summary"]["merged_into_github_main_count"] = None
    assert not inventory.verify_git_inventory_receipt(_resign(tampered_none), REQUEST_ID)

    tampered_absent = deepcopy(absent_result)
    tampered_absent["receipt"]["pc_backlog_summary"]["merged_into_github_main_count"] = 0
    assert not inventory.verify_git_inventory_receipt(_resign(tampered_absent), REQUEST_ID)

    tampered_backlog_extra = deepcopy(present_result)
    tampered_backlog_extra["receipt"]["pc_backlog_summary"]["extra"] = 1
    assert not inventory.verify_git_inventory_receipt(_resign(tampered_backlog_extra), REQUEST_ID)

    tampered_wt = deepcopy(present_result)
    tampered_wt["receipt"]["worktree_summary"]["detached"] = 99
    assert not inventory.verify_git_inventory_receipt(_resign(tampered_wt), REQUEST_ID)

    tampered_wt_locked = deepcopy(present_result)
    tampered_wt_locked["receipt"]["worktree_summary"]["locked"] = 99
    assert not inventory.verify_git_inventory_receipt(_resign(tampered_wt_locked), REQUEST_ID)
