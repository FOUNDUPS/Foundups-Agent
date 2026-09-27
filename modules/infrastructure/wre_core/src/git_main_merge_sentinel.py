#!/usr/bin/env python3
"""
Git Main-Merge Sentinel - Auto-merge feature branches to main at startup.

WSP Compliance:
    WSP 72: Module Independence
    WSP 91: Observability (logging)

Purpose:
    Agents commit to whatever branch is checked out (often feature branches).
    When 012 says "push to git" expecting code on main, it lands on the feature
    branch instead. This sentinel ensures code reaches main automatically.

Flow:
    1. If on main -> skip (nothing to do)
    2. Require a named branch, readable worktrees and a clean working tree
    3. Require git fetch --all --quiet to succeed
    4. Push current branch to both remotes (ensure nothing lost)
    5. Try fast-forward: git push origin HEAD:main
    6. If fails (diverged) -> create PR via gh, merge via gh pr merge
    7. Require a second clean/readable status before local cleanup
    8. Update local main and checkout main without automatic stash/pop
    9. Delete old feature branch when configured (local + both remotes)

Environment:
    GIT_MAIN_MERGE_SENTINEL=1           Enable sentinel (default OFF)
    GIT_MAIN_MERGE_SENTINEL_ENFORCED=0  If 1, block startup on failure
    GIT_MAIN_MERGE_SENTINEL_DELETE_BRANCH=1  Delete merged branch (default ON)
"""

import logging
import os
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _env_bool(name: str, default: bool = False) -> bool:
    """Get boolean from environment variable."""
    val = os.getenv(name, "1" if default else "0")
    return val.lower() in ("1", "true", "yes", "on")


def _env_int(name: str, default: int) -> int:
    """Get integer from environment variable."""
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _git(args: list[str], repo_root: Path, timeout: int = 30) -> tuple[bool, str]:
    """
    Run a git command safely.

    Returns:
        (success, output_or_error)
    """
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout.strip() or result.stderr.strip()
        return result.returncode == 0, output
    except subprocess.TimeoutExpired:
        return False, f"timeout after {timeout}s"
    except Exception as e:
        return False, str(e)


def _gh(args: list[str], repo_root: Path, timeout: int = 60) -> tuple[bool, str]:
    """
    Run a gh (GitHub CLI) command safely.

    Returns:
        (success, output_or_error)
    """
    try:
        result = subprocess.run(
            ["gh"] + args,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout.strip() or result.stderr.strip()
        return result.returncode == 0, output
    except FileNotFoundError:
        return False, "gh CLI not found"
    except subprocess.TimeoutExpired:
        return False, f"timeout after {timeout}s"
    except Exception as e:
        return False, str(e)


def _branch_checkout_paths(
    repo_root: Path, branch: str, current_branch: str,
) -> list[Path] | None:
    """Return other branch checkouts, or None when discovery is unavailable."""

    ok, output = _git(["worktree", "list", "--porcelain"], repo_root, timeout=15)
    if not ok or not output.strip():
        return None

    root = repo_root.resolve()
    branch_ref = f"refs/heads/{branch}"
    matches: list[Path] = []
    current_seen = False
    for record in output.strip().split("\n\n"):
        lines = record.splitlines()
        paths = [line[9:] for line in lines if line.startswith("worktree ")]
        states = [line for line in lines
                  if line.startswith("branch ") or line in ("detached", "bare")]
        if len(paths) != 1 or not paths[0].strip() or len(states) != 1:
            return None
        try:
            resolved = Path(paths[0]).resolve()
        except (OSError, ValueError):
            return None
        if resolved == root:
            if current_seen or states[0] != f"branch refs/heads/{current_branch}":
                return None
            current_seen = True
        elif states[0] == f"branch {branch_ref}":
            matches.append(resolved)
    # A competing main checkout is independently sufficient to block. Otherwise
    # require evidence for this checkout rather than treating an omission as safe.
    return matches if matches or current_seen else None


def run_main_merge_sentinel(repo_root: Path, force: bool = False) -> dict[str, Any]:
    """
    Run git main-merge sentinel: merge current branch to main if needed.

    Args:
        repo_root: Repository root path
        force: Force run even if disabled by env

    Returns:
        Status dict with keys:
            passed: bool - True if operation succeeded or was skipped
            merged: bool - True if a merge was performed
            branch: str - Branch that was merged (if any)
            actions: list[str] - Actions taken
            error: str - Error message (if failed)
    """
    result: dict[str, Any] = {
        "passed": True,
        "merged": False,
        "branch": None,
        "actions": [],
        "error": None,
    }

    # Check if enabled
    if not force and not _env_bool("GIT_MAIN_MERGE_SENTINEL", default=False):
        result["actions"].append("skip (disabled)")
        return result

    # Get current branch
    ok, current_branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], repo_root)
    if not ok:
        result["error"] = f"Failed to get current branch: {current_branch}"
        result["passed"] = not _env_bool("GIT_MAIN_MERGE_SENTINEL_ENFORCED", default=False)
        return result

    if not current_branch.strip() or current_branch == "HEAD":
        result["error"] = "named_branch_required"
        result["passed"] = not _env_bool("GIT_MAIN_MERGE_SENTINEL_ENFORCED", default=False)
        return result

    # If on main, nothing to do
    if current_branch == "main":
        result["actions"].append("skip (already on main)")
        return result

    result["branch"] = current_branch
    logger.info(f"[GIT-MERGE-SENTINEL] Merging {current_branch} -> main")

    main_paths = _branch_checkout_paths(repo_root, "main", current_branch)
    if main_paths is None:
        result["error"] = "worktree_discovery_failed"
        result["passed"] = not _env_bool("GIT_MAIN_MERGE_SENTINEL_ENFORCED", default=False)
        return result
    if main_paths:
        result["actions"].append("blocked: main checked out in another worktree")
        result["error"] = "main_checked_out_in_another_worktree"
        result["main_worktree_paths"] = [str(path) for path in main_paths]
        result["passed"] = not _env_bool("GIT_MAIN_MERGE_SENTINEL_ENFORCED", default=False)
        return result

    # Reject unknown/dirty state at preflight; later concurrent changes remain
    # a separate downstream ownership problem, not solved by this snapshot.
    ok, status = _git(["status", "--porcelain", "--untracked-files=all"], repo_root)
    if not ok or status.strip():
        result["error"] = "working_tree_dirty" if ok else "working_tree_status_failed"
        result["passed"] = not _env_bool("GIT_MAIN_MERGE_SENTINEL_ENFORCED", default=False)
        return result

    # Fetch from all remotes
    ok, output = _git(["fetch", "--all", "--quiet"], repo_root, timeout=15)
    if ok:
        result["actions"].append("fetched")
    else:
        result["actions"].append("blocked: fetch failed")
        result["error"] = "fetch_failed"
        result["passed"] = not _env_bool("GIT_MAIN_MERGE_SENTINEL_ENFORCED", default=False)
        return result

    # Push current branch to origin (ensure nothing lost)
    ok, output = _git(["push", "origin", current_branch], repo_root, timeout=30)
    if ok:
        result["actions"].append(f"pushed {current_branch} to origin")
    else:
        # Non-fatal if already up to date
        if "up-to-date" not in output.lower() and "nothing to push" not in output.lower():
            result["actions"].append(f"push to origin: {output}")

    # Try to push to backup remote (if exists)
    ok, output = _git(["push", "backup", current_branch], repo_root, timeout=30)
    if ok:
        result["actions"].append(f"pushed {current_branch} to backup")
    # Don't log backup failures - it may not exist

    # Try fast-forward merge: push HEAD to main on origin
    ok, output = _git(["push", "origin", f"HEAD:main"], repo_root, timeout=30)
    if ok:
        result["actions"].append("fast-forward to origin/main")

        # Also push to backup/main
        ok2, _ = _git(["push", "backup", f"HEAD:main"], repo_root, timeout=30)
        if ok2:
            result["actions"].append("fast-forward to backup/main")

        result["merged"] = True
    else:
        # Fast-forward failed - try PR merge
        result["actions"].append(f"fast-forward failed: {output}")

        # Check if PR already exists for this branch
        ok, pr_check = _gh(["pr", "view", "--json", "state,number"], repo_root)
        if ok and '"state":"OPEN"' in pr_check:
            # PR exists, try to merge it
            ok, merge_out = _gh(["pr", "merge", "--merge"], repo_root, timeout=120)
            if ok:
                result["actions"].append("merged via existing PR")
                result["merged"] = True
            else:
                result["actions"].append(f"PR merge failed: {merge_out}")
        else:
            # Create new PR and merge
            ok, pr_out = _gh(
                ["pr", "create", "--fill", "--base", "main"],
                repo_root,
                timeout=60,
            )
            if ok:
                result["actions"].append(f"created PR: {pr_out}")

                # Merge the PR
                ok, merge_out = _gh(["pr", "merge", "--merge"], repo_root, timeout=120)
                if ok:
                    result["actions"].append("merged via new PR")
                    result["merged"] = True
                else:
                    result["actions"].append(f"PR merge failed: {merge_out}")
            else:
                result["actions"].append(f"PR create failed: {pr_out}")

    # If merged, update local main and checkout
    if result["merged"]:
        # Remote command success does not grant ownership of work that appeared
        # after preflight. Preserve it before any local ref/checkout/deletion.
        ok, status = _git(["status", "--porcelain", "--untracked-files=all"], repo_root)
        if not ok or status.strip():
            result["error"] = "cleanup_working_tree_dirty" if ok else "cleanup_status_failed"
            result["actions"].append("blocked: cleanup requires a clean, readable working tree")
            result["passed"] = not _env_bool("GIT_MAIN_MERGE_SENTINEL_ENFORCED", default=False)
            return result

        # Update local main to match origin/main
        ok, _ = _git(["branch", "-f", "main", "origin/main"], repo_root)
        if ok:
            result["actions"].append("updated local main")

        # Checkout main
        ok, output = _git(["checkout", "main"], repo_root)
        if ok:
            result["actions"].append("checked out main")

            # Delete the old feature branch if configured
            if _env_bool("GIT_MAIN_MERGE_SENTINEL_DELETE_BRANCH", default=True):
                # Delete local branch
                ok, _ = _git(["branch", "-D", current_branch], repo_root)
                if ok:
                    result["actions"].append(f"deleted local {current_branch}")

                # Delete remote branch (origin)
                ok, _ = _git(["push", "origin", "--delete", current_branch], repo_root, timeout=30)
                if ok:
                    result["actions"].append(f"deleted origin/{current_branch}")

                # Delete remote branch (backup)
                ok, _ = _git(["push", "backup", "--delete", current_branch], repo_root, timeout=30)
                if ok:
                    result["actions"].append(f"deleted backup/{current_branch}")
        else:
            result["actions"].append(f"checkout main failed: {output}")
            result["passed"] = not _env_bool("GIT_MAIN_MERGE_SENTINEL_ENFORCED", default=False)
    else:
        # Merge failed
        result["error"] = "Could not merge to main (conflicts or permissions)"
        result["passed"] = not _env_bool("GIT_MAIN_MERGE_SENTINEL_ENFORCED", default=False)

    return result


if __name__ == "__main__":
    # CLI test mode
    import sys

    repo_root = Path(__file__).resolve().parents[4]  # Up to repo root
    print(f"[TEST] Running git main-merge sentinel on {repo_root}")

    result = run_main_merge_sentinel(repo_root, force="--force" in sys.argv)

    print(f"\n[RESULT]")
    print(f"  passed: {result['passed']}")
    print(f"  merged: {result['merged']}")
    print(f"  branch: {result['branch']}")
    print(f"  error: {result['error']}")
    print(f"  actions:")
    for action in result['actions']:
        print(f"    - {action}")
