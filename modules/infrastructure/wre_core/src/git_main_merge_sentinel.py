#!/usr/bin/env python3
"""Compatibility entry point for read-only Git lifecycle reconciliation."""

import os
from pathlib import Path
from typing import Any


def _env_enabled(name: str) -> bool:
    return os.getenv(name, "0").lower() in ("1", "true", "yes", "on")


def run_main_merge_sentinel(repo_root: Path, force: bool = False) -> dict[str, Any]:
    """Observe Git lifecycle coverage through the legacy startup interface."""
    result: dict[str, Any] = {
        "passed": True,
        "merged": False,
        "branch": None,
        "actions": [],
        "error": None,
    }
    if not force and not _env_enabled("GIT_MAIN_MERGE_SENTINEL"):
        result["actions"].append("skip (disabled)")
        return result

    try:
        from .git_lifecycle import reconcile_git_lifecycle

        observation = reconcile_git_lifecycle(repo_root, synchronize_pc=False)
        coverage = observation.get("coverage")
        reason = observation.get("reason")
    except Exception:
        coverage = "unavailable"
        reason = "git_lifecycle_reconciliation_failed"

    if coverage not in ("complete", "partial", "unavailable"):
        coverage = "unavailable"
    result["actions"].append(f"checked git lifecycle ({coverage})")
    if coverage != "complete":
        result["passed"] = not _env_enabled("GIT_MAIN_MERGE_SENTINEL_ENFORCED")
        result["error"] = reason or f"git_lifecycle_coverage_{coverage}"
    return result


if __name__ == "__main__":
    import sys

    repo_root = Path(__file__).resolve().parents[4]
    if not __package__:
        sys.path.insert(0, str(repo_root))
        __package__ = "modules.infrastructure.wre_core.src"

    result = run_main_merge_sentinel(repo_root, force="--force" in sys.argv)
    for name in ("passed", "merged", "branch", "error", "actions"):
        print(f"{name}: {result[name]}")
