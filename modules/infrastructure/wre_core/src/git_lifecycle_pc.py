"""Observe or fast-forward an explicitly selected PC main worktree."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any


_MAIN_REF = "refs/heads/main"
_TRACKING_REF = "refs/remotes/origin/main"
_SHA = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")


def _receipt(
    status: str, reason: str, head_sha: str | None = None, *, updated: bool = False
) -> dict[str, Any]:
    return {"status": status, "head_sha": head_sha, "reason": reason, "updated": updated}


def _success(result: subprocess.CompletedProcess[str] | None) -> bool:
    return result is not None and result.returncode == 0


def _text(result: subprocess.CompletedProcess[str] | None) -> str:
    return result.stdout.strip() if result is not None and result.returncode == 0 else ""


def _commit(result: subprocess.CompletedProcess[str] | None) -> str | None:
    value = _text(result)
    return value if _SHA.fullmatch(value) else None


def _remote_main(result: subprocess.CompletedProcess[str] | None) -> str | None:
    fields = _text(result).split()
    if len(fields) == 2 and fields[1] == _MAIN_REF and _SHA.fullmatch(fields[0]):
        return fields[0]
    return None


def _only_main_worktree(output: str, root: Path) -> bool:
    paths = []
    for record in output.split("\0\0"):
        fields = record.strip("\0").split("\0")
        if f"branch {_MAIN_REF}" in fields:
            if not fields[0].startswith("worktree "):
                return False
            paths.append(Path(fields[0].removeprefix("worktree ")).resolve())
    return paths == [root]


def reconcile_pc_main(
    repo_root: Path, main_sha: str, *, allow_update: bool, runner
) -> dict[str, Any]:
    """Bind PC state to a supplied GitHub main SHA and preserve other work."""
    if not isinstance(main_sha, str) or not _SHA.fullmatch(main_sha):
        return _receipt("PC_SYNC_BLOCKED", "invalid_target_sha")

    try:
        root = Path(repo_root).resolve()
    except (OSError, RuntimeError, ValueError):
        return _receipt("PC_SYNC_BLOCKED", "repository_root_unverified")

    def git(*args: str, timeout: int = 15) -> subprocess.CompletedProcess[str] | None:
        try:
            return runner(("git", "--no-replace-objects", *args), cwd=root, timeout=timeout)
        except (OSError, subprocess.SubprocessError):
            return None

    def head() -> str | None:
        return _commit(git("rev-parse", "--verify", "HEAD^{commit}"))

    def branch() -> str:
        return _text(git("symbolic-ref", "--quiet", "HEAD"))

    def clean_status() -> str | None:
        result = git(
            "--no-optional-locks", "status", "--porcelain=v1", "-z",
            "--untracked-files=all", "--ignore-submodules=none",
        )
        if result is None or result.returncode != 0:
            return "working_tree_status_unavailable"
        return "working_tree_dirty" if result.stdout else None

    def live_main() -> str | None:
        return _remote_main(git("ls-remote", "--exit-code", "--refs", "origin", _MAIN_REF, timeout=10))

    def unique_main_checkout() -> bool:
        inventory = git("worktree", "list", "--porcelain", "-z")
        try:
            return (
                inventory is not None
                and inventory.returncode == 0
                and _only_main_worktree(inventory.stdout, root)
            )
        except (OSError, RuntimeError, ValueError):
            return False

    root_text = _text(git("rev-parse", "--show-toplevel"))
    try:
        if not root_text or Path(root_text).resolve() != root:
            return _receipt("PC_SYNC_BLOCKED", "repository_root_unverified")
    except (OSError, RuntimeError, ValueError):
        return _receipt("PC_SYNC_BLOCKED", "repository_root_unverified")

    before = head()
    if before is None:
        return _receipt("PC_SYNC_BLOCKED", "local_head_unverified")
    local_branch = branch()
    if not local_branch:
        return _receipt("PC_SYNC_BLOCKED", "main_checkout_unverified", before)
    if local_branch != _MAIN_REF:
        return _receipt("PC_SYNC_PENDING", "main_not_checked_out", before)
    dirty = clean_status()
    if dirty is not None:
        return _receipt("PC_SYNC_BLOCKED", dirty, before)

    observed_main = live_main()
    if observed_main is None:
        return _receipt("PC_SYNC_BLOCKED", "remote_main_unverified", before)
    if observed_main != main_sha:
        return _receipt("PC_SYNC_BLOCKED", "remote_main_changed", before)
    if before == main_sha:
        after = head()
        if branch() != _MAIN_REF or after != main_sha:
            return _receipt("PC_SYNC_BLOCKED", "local_checkout_changed", after)
        dirty = clean_status()
        if dirty is not None:
            return _receipt("PC_SYNC_BLOCKED", dirty, after)
        return _receipt("PC_SYNC_VERIFIED", "already_current", after)
    if allow_update is not True:
        return _receipt("PC_SYNC_PENDING", "update_not_authorized", before)
    if not unique_main_checkout():
        return _receipt("PC_SYNC_BLOCKED", "main_worktree_unverified", before)

    fetched = git(
        "fetch", "--no-tags", "--no-write-fetch-head", "--no-recurse-submodules",
        "origin", f"{_MAIN_REF}:{_TRACKING_REF}", timeout=30,
    )
    if not _success(fetched):
        return _receipt("PC_SYNC_BLOCKED", "main_fetch_failed", before)
    tracking = _commit(git("rev-parse", "--verify", f"{_TRACKING_REF}^{{commit}}"))
    if tracking is None:
        return _receipt("PC_SYNC_BLOCKED", "tracking_main_unverified", before)
    if tracking != main_sha:
        return _receipt("PC_SYNC_BLOCKED", "remote_main_changed", before)
    ancestry = git("merge-base", "--is-ancestor", before, main_sha)
    if not _success(ancestry):
        reason = (
            "local_main_not_fast_forwardable"
            if ancestry is not None and ancestry.returncode == 1
            else "local_ancestry_unverified"
        )
        return _receipt("PC_SYNC_BLOCKED", reason, before)

    observed_main = live_main()
    if observed_main is None:
        return _receipt("PC_SYNC_BLOCKED", "remote_main_unverified", before)
    if observed_main != main_sha:
        return _receipt("PC_SYNC_BLOCKED", "remote_main_changed", before)
    if not unique_main_checkout():
        return _receipt("PC_SYNC_BLOCKED", "main_worktree_unverified", before)
    dirty = clean_status()
    if dirty is not None:
        return _receipt("PC_SYNC_BLOCKED", dirty, before)
    current = head()
    if branch() != _MAIN_REF or current != before:
        return _receipt("PC_SYNC_BLOCKED", "local_checkout_changed", current)

    merged = git(
        "-c", "submodule.recurse=false", "merge", "--ff-only", "--no-autostash",
        "--no-overwrite-ignore", main_sha, timeout=30,
    )
    after = head()
    local_main = _commit(git("rev-parse", "--verify", f"{_MAIN_REF}^{{commit}}"))
    updated = local_main == main_sha
    if not _success(merged):
        return _receipt("PC_SYNC_BLOCKED", "fast_forward_failed", after, updated=updated)
    if branch() != _MAIN_REF or after != main_sha or not updated:
        return _receipt("PC_SYNC_BLOCKED", "local_checkout_changed", after, updated=updated)
    dirty = clean_status()
    if dirty is not None:
        return _receipt("PC_SYNC_BLOCKED", dirty, after, updated=True)
    tracking = _commit(git("rev-parse", "--verify", f"{_TRACKING_REF}^{{commit}}"))
    observed_main = live_main()
    if tracking is None or observed_main is None:
        return _receipt("PC_SYNC_BLOCKED", "remote_main_unverified", after, updated=True)
    if tracking != main_sha or observed_main != main_sha:
        return _receipt("PC_SYNC_BLOCKED", "remote_main_changed", after, updated=True)
    current = head()
    if branch() != _MAIN_REF or current != main_sha:
        return _receipt("PC_SYNC_BLOCKED", "local_checkout_changed", current, updated=True)
    dirty = clean_status()
    if dirty is not None:
        return _receipt("PC_SYNC_BLOCKED", dirty, current, updated=True)
    return _receipt("PC_SYNC_VERIFIED", "fast_forwarded", current, updated=True)
