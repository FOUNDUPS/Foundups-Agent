#!/usr/bin/env python3
"""
MCP Bridge Diff Tools.

Provides git diff perception for change analysis.

Tools:
- get_file_diff: What changed in file X?
- get_diff_summary: What changed across commit range Y?

WSP References:
- WSP 97: Truthful verification (actual deltas, not guesses)
- WSP 22: ModLog documentation (change tracking)
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from .response_schema import ok_response, error_response

logger = logging.getLogger(__name__)

# Security: Block sensitive files from diff output
BLOCKED_PATTERNS = {".env", "credentials", "secrets", "oauth_token", ".pem", ".key", "id_rsa"}

# Maximum diff size to return (prevent memory issues)
MAX_DIFF_LINES = 500
MAX_DIFF_BYTES = 100_000  # 100KB


def get_file_diff(
    repo_root: Path,
    path: str,
    commit_range: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get diff for a specific file.

    Args:
        repo_root: Repository root path
        path: Relative file path
        commit_range: Git commit range (e.g., "HEAD~3..HEAD", "abc123..def456")
                     If omitted, shows working tree changes vs HEAD

    Returns:
        MCPResponse with diff information
    """
    # Security check
    path_lower = path.lower()
    for blocked in BLOCKED_PATTERNS:
        if blocked in path_lower:
            return error_response(
                f"Path not allowed: {path}",
                reason="Contains sensitive pattern",
            )

    file_path = repo_root / path
    if not file_path.exists() and not commit_range:
        return error_response(f"File not found: {path}")

    try:
        if commit_range:
            # Diff across commit range
            cmd = ["git", "diff", commit_range, "--", path]
        else:
            # Working tree vs HEAD (staged + unstaged)
            cmd = ["git", "diff", "HEAD", "--", path]

        result = subprocess.run(
            cmd,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=30,
        )

        diff_output = result.stdout
        if not diff_output:
            # Try checking if file has staged changes
            staged_result = subprocess.run(
                ["git", "diff", "--cached", "--", path],
                cwd=str(repo_root),
                capture_output=True,
                text=True,
                timeout=30,
            )
            diff_output = staged_result.stdout

        if not diff_output:
            return ok_response(
                {
                    "path": path,
                    "commit_range": commit_range or "HEAD",
                    "has_changes": False,
                    "diff": None,
                    "message": "No changes detected",
                },
                source="git_diff",
                tool="get_file_diff",
            )

        # Parse diff statistics
        stats = _parse_diff_stats(diff_output)

        # Truncate if too large
        truncated = False
        lines = diff_output.split("\n")
        if len(lines) > MAX_DIFF_LINES:
            diff_output = "\n".join(lines[:MAX_DIFF_LINES])
            diff_output += f"\n\n... truncated ({len(lines) - MAX_DIFF_LINES} more lines)"
            truncated = True
        elif len(diff_output) > MAX_DIFF_BYTES:
            diff_output = diff_output[:MAX_DIFF_BYTES]
            diff_output += "\n\n... truncated (exceeded size limit)"
            truncated = True

        # Get commit metadata if using range
        commit_info = None
        if commit_range:
            commit_info = _get_commit_info(repo_root, commit_range, path)

        return ok_response(
            {
                "path": path,
                "commit_range": commit_range or "working_tree_vs_HEAD",
                "has_changes": True,
                "diff": diff_output,
                "stats": stats,
                "truncated": truncated,
                "commit_info": commit_info,
            },
            source="git_diff",
            tool="get_file_diff",
        )

    except subprocess.TimeoutExpired:
        return error_response("Diff operation timed out")
    except subprocess.CalledProcessError as e:
        return error_response(f"Git error: {e.stderr or str(e)}")
    except Exception as e:
        logger.error(f"[MCP] get_file_diff error: {e}")
        return error_response(f"Diff error: {e}")


def get_diff_summary(
    repo_root: Path,
    commit_range: str,
    path: str = ".",
    group_by_module: bool = True,
) -> Dict[str, Any]:
    """
    Get summary of changes across a commit range.

    Args:
        repo_root: Repository root path
        commit_range: Git commit range (e.g., "HEAD~5..HEAD", "main..feature")
        path: Scope path (default "." for entire repo)
        group_by_module: Group files by module/domain

    Returns:
        MCPResponse with change summary
    """
    try:
        # Get list of changed files with stats
        cmd = ["git", "diff", "--stat", "--name-status", commit_range, "--", path]
        result = subprocess.run(
            cmd,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            return error_response(
                f"Invalid commit range: {commit_range}",
                stderr=result.stderr,
            )

        # Parse name-status output
        changed_files = _parse_name_status(result.stdout)

        # Filter out sensitive files
        changed_files = [
            f for f in changed_files
            if not any(blocked in f["path"].lower() for blocked in BLOCKED_PATTERNS)
        ]

        # Get overall stats
        stats_cmd = ["git", "diff", "--shortstat", commit_range, "--", path]
        stats_result = subprocess.run(
            stats_cmd,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=30,
        )
        overall_stats = _parse_shortstat(stats_result.stdout)

        # Get commit count in range
        commit_count_cmd = ["git", "rev-list", "--count", commit_range]
        commit_result = subprocess.run(
            commit_count_cmd,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=10,
        )
        commit_count = int(commit_result.stdout.strip()) if commit_result.returncode == 0 else 0

        # Group by module if requested
        grouped = None
        if group_by_module:
            grouped = _group_by_module(changed_files)

        # Get commit messages in range
        messages_cmd = ["git", "log", "--oneline", commit_range, "--", path]
        messages_result = subprocess.run(
            messages_cmd,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=30,
        )
        commit_messages = messages_result.stdout.strip().split("\n")[:20]  # Limit to 20

        return ok_response(
            {
                "commit_range": commit_range,
                "path_scope": path,
                "commit_count": commit_count,
                "files_changed": len(changed_files),
                "overall_stats": overall_stats,
                "changed_files": changed_files[:100],  # Limit file list
                "truncated_files": len(changed_files) > 100,
                "grouped_by_module": grouped,
                "commit_messages": commit_messages,
            },
            source="git_diff_summary",
            tool="get_diff_summary",
        )

    except subprocess.TimeoutExpired:
        return error_response("Diff summary timed out")
    except Exception as e:
        logger.error(f"[MCP] get_diff_summary error: {e}")
        return error_response(f"Diff summary error: {e}")


# =============================================================================
# Helper Functions
# =============================================================================


def _parse_diff_stats(diff_output: str) -> Dict[str, int]:
    """Parse diff statistics from diff output."""
    lines = diff_output.split("\n")
    additions = 0
    deletions = 0

    for line in lines:
        if line.startswith("+") and not line.startswith("+++"):
            additions += 1
        elif line.startswith("-") and not line.startswith("---"):
            deletions += 1

    return {
        "additions": additions,
        "deletions": deletions,
        "total_changes": additions + deletions,
    }


def _parse_name_status(output: str) -> List[Dict[str, str]]:
    """Parse git diff --name-status output."""
    files = []
    for line in output.strip().split("\n"):
        if not line or line.startswith(" "):
            continue
        parts = line.split("\t")
        if len(parts) >= 2:
            status = parts[0]
            path = parts[1]

            # Map status codes
            status_map = {
                "A": "added",
                "M": "modified",
                "D": "deleted",
                "R": "renamed",
                "C": "copied",
                "T": "type_changed",
            }
            status_name = status_map.get(status[0], "unknown")

            file_info = {"path": path, "status": status_name, "status_code": status}
            if status_name == "renamed" and len(parts) >= 3:
                file_info["old_path"] = path
                file_info["path"] = parts[2]

            files.append(file_info)

    return files


def _parse_shortstat(output: str) -> Dict[str, int]:
    """Parse git diff --shortstat output."""
    stats = {
        "files_changed": 0,
        "insertions": 0,
        "deletions": 0,
    }

    if not output.strip():
        return stats

    # Parse: "3 files changed, 10 insertions(+), 5 deletions(-)"
    import re
    files_match = re.search(r"(\d+) file", output)
    ins_match = re.search(r"(\d+) insertion", output)
    del_match = re.search(r"(\d+) deletion", output)

    if files_match:
        stats["files_changed"] = int(files_match.group(1))
    if ins_match:
        stats["insertions"] = int(ins_match.group(1))
    if del_match:
        stats["deletions"] = int(del_match.group(1))

    return stats


def _get_commit_info(repo_root: Path, commit_range: str, path: str) -> Optional[List[Dict]]:
    """Get commit information for changes to a file in range."""
    try:
        cmd = [
            "git", "log", "--format=%H|%an|%ae|%ai|%s",
            commit_range, "--", path
        ]
        result = subprocess.run(
            cmd,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            return None

        commits = []
        for line in result.stdout.strip().split("\n")[:10]:  # Limit to 10 commits
            if not line:
                continue
            parts = line.split("|", 4)
            if len(parts) >= 5:
                commits.append({
                    "hash": parts[0][:8],
                    "author": parts[1],
                    "email": parts[2],
                    "date": parts[3],
                    "message": parts[4],
                })

        return commits
    except Exception:
        return None


def _group_by_module(files: List[Dict]) -> Dict[str, List[str]]:
    """Group changed files by module/domain."""
    grouped: Dict[str, List[str]] = {}

    for f in files:
        path = f["path"]

        # Determine group
        if path.startswith("modules/"):
            parts = path.split("/")
            if len(parts) >= 3:
                group = f"{parts[1]}/{parts[2]}"  # domain/module
            elif len(parts) >= 2:
                group = parts[1]  # domain
            else:
                group = "modules"
        elif path.startswith("WSP_"):
            group = "wsp_framework"
        elif path.startswith("holo_index/"):
            group = "holo_index"
        elif path.startswith("docs/"):
            group = "docs"
        elif path.startswith("tests/"):
            group = "tests"
        elif path.startswith("public/"):
            group = "public"
        else:
            group = "root"

        if group not in grouped:
            grouped[group] = []
        grouped[group].append(path)

    return grouped
