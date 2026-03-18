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
    2. git fetch --all --quiet
    3. Push current branch to both remotes (ensure nothing lost)
    4. Try fast-forward: git push origin HEAD:main
    5. If fails (diverged) -> create PR via gh, merge via gh pr merge
    6. Update local main: git branch -f main origin/main
    7. Checkout main
    8. Delete old feature branch (local + both remotes)

Environment:
    GIT_MAIN_MERGE_SENTINEL=1           Enable sentinel (default ON)
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
    if not force and not _env_bool("GIT_MAIN_MERGE_SENTINEL", default=True):
        result["actions"].append("skip (disabled)")
        return result

    # Get current branch
    ok, current_branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], repo_root)
    if not ok:
        result["error"] = f"Failed to get current branch: {current_branch}"
        result["passed"] = not _env_bool("GIT_MAIN_MERGE_SENTINEL_ENFORCED", default=False)
        return result

    # If on main, nothing to do
    if current_branch == "main":
        result["actions"].append("skip (already on main)")
        return result

    result["branch"] = current_branch
    logger.info(f"[GIT-MERGE-SENTINEL] Merging {current_branch} -> main")

    # Fetch from all remotes
    ok, output = _git(["fetch", "--all", "--quiet"], repo_root, timeout=15)
    if ok:
        result["actions"].append("fetched")
    else:
        # Non-fatal - continue without fetch
        result["actions"].append(f"fetch failed (continuing): {output}")

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
            ok, merge_out = _gh(["pr", "merge", "--merge", "--delete-branch"], repo_root, timeout=120)
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
                ok, merge_out = _gh(["pr", "merge", "--merge", "--delete-branch"], repo_root, timeout=120)
                if ok:
                    result["actions"].append("merged via new PR")
                    result["merged"] = True
                else:
                    result["actions"].append(f"PR merge failed: {merge_out}")
            else:
                result["actions"].append(f"PR create failed: {pr_out}")

    # If merged, update local main and checkout
    if result["merged"]:
        # Update local main to match origin/main
        ok, _ = _git(["branch", "-f", "main", "origin/main"], repo_root)
        if ok:
            result["actions"].append("updated local main")

        # Check for uncommitted changes before checkout
        ok, status = _git(["status", "--porcelain"], repo_root)
        has_changes = bool(status.strip()) if ok else False

        if has_changes:
            # Stash changes
            ok, _ = _git(["stash", "push", "-m", "git-merge-sentinel-auto-stash"], repo_root)
            if ok:
                result["actions"].append("stashed changes")

        # Checkout main
        ok, output = _git(["checkout", "main"], repo_root)
        if ok:
            result["actions"].append("checked out main")

            # Pop stash if we stashed
            if has_changes:
                ok, _ = _git(["stash", "pop"], repo_root)
                if ok:
                    result["actions"].append("restored stash")

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
