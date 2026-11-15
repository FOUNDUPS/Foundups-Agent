"""Regression checks for the read-only PC Git inventory receipt."""

from copy import deepcopy
from datetime import datetime, timedelta
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
