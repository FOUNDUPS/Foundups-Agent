"""
Repo Perception Tools for FoundUps MCP Bridge.

Read-only access to repository structure, files, and search.

WSP References:
- WSP 97: Truthful verification
- WSP 15: Pre-action verification (search before edit)
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from .response_schema import ok_response, error_response

logger = logging.getLogger(__name__)

# Path allowlist for security (no .env, credentials, etc.)
ALLOWED_EXTENSIONS = {
    ".md", ".txt", ".py", ".ts", ".tsx", ".js", ".jsx",
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".html", ".css", ".scss", ".sh", ".bat", ".ps1",
}
BLOCKED_PATTERNS = {".env", "credentials", "secrets", "oauth_token", ".pem", ".key"}
MAX_FILE_SIZE = 200 * 1024  # 200KB


def _is_path_allowed(path: Path, repo_root: Path) -> bool:
    """Check if path is within repo and not blocked."""
    try:
        resolved = path.resolve()
        if not str(resolved).startswith(str(repo_root.resolve())):
            return False
        name_lower = path.name.lower()
        for blocked in BLOCKED_PATTERNS:
            if blocked in name_lower:
                return False
        return True
    except Exception:
        return False


def get_repo_tree(repo_root: Path, path: str = ".", depth: int = 3) -> Dict[str, Any]:
    """
    Get repository directory tree.

    Args:
        repo_root: Repository root path
        path: Relative path to start from (default ".")
        depth: Maximum depth to traverse (default 3)

    Returns:
        MCPResponse with tree structure
    """
    try:
        start_path = (repo_root / path).resolve()
        if not _is_path_allowed(start_path, repo_root):
            return error_response(f"Path not allowed: {path}")

        def build_tree(current: Path, current_depth: int) -> Dict[str, Any]:
            if current_depth > depth:
                return {"truncated": True}

            result = {
                "name": current.name or str(current),
                "type": "directory" if current.is_dir() else "file",
            }

            if current.is_dir():
                children = []
                try:
                    for child in sorted(current.iterdir()):
                        # Skip hidden and blocked
                        if child.name.startswith(".") and child.name not in {".claude"}:
                            continue
                        if any(blocked in child.name.lower() for blocked in BLOCKED_PATTERNS):
                            continue
                        children.append(build_tree(child, current_depth + 1))
                except PermissionError:
                    result["error"] = "permission_denied"
                result["children"] = children[:100]  # Limit children
                if len(children) > 100:
                    result["truncated_children"] = len(children) - 100
            else:
                result["size"] = current.stat().st_size if current.exists() else 0

            return result

        tree = build_tree(start_path, 0)
        return ok_response(tree, source="repo", path=path, depth=depth)

    except Exception as e:
        logger.error(f"[MCP] get_repo_tree error: {e}")
        return error_response(str(e))


def read_file(repo_root: Path, path: str) -> Dict[str, Any]:
    """
    Read file contents.

    Args:
        repo_root: Repository root path
        path: Relative path to file

    Returns:
        MCPResponse with file content
    """
    try:
        file_path = (repo_root / path).resolve()
        if not _is_path_allowed(file_path, repo_root):
            return error_response(f"Path not allowed: {path}")

        if not file_path.exists():
            return error_response(f"File not found: {path}")

        if not file_path.is_file():
            return error_response(f"Not a file: {path}")

        # Check size
        size = file_path.stat().st_size
        if size > MAX_FILE_SIZE:
            return error_response(f"File too large: {size} bytes (max {MAX_FILE_SIZE})")

        # Read content
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return error_response(f"Cannot read binary file: {path}")

        return ok_response(
            {"content": content, "lines": content.count("\n") + 1},
            source="repo",
            path=path,
            size=size,
        )

    except Exception as e:
        logger.error(f"[MCP] read_file error: {e}")
        return error_response(str(e))


def search_repo(
    repo_root: Path,
    query: str,
    path: str = ".",
    top_k: int = 20,
) -> Dict[str, Any]:
    """
    Search repository using ripgrep.

    Args:
        repo_root: Repository root path
        query: Search query (regex supported)
        path: Relative path to search in (default ".")
        top_k: Maximum results (default 20)

    Returns:
        MCPResponse with search results
    """
    try:
        search_path = (repo_root / path).resolve()
        if not _is_path_allowed(search_path, repo_root):
            return error_response(f"Path not allowed: {path}")

        # Use ripgrep for fast search
        cmd = [
            "rg",
            "--json",
            "--max-count", str(top_k * 2),  # Get extra for filtering
            "--ignore-case",
            query,
            str(search_path),
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(repo_root),
        )

        matches = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            try:
                item = json.loads(line)
                if item.get("type") == "match":
                    data = item.get("data", {})
                    file_path = data.get("path", {}).get("text", "")
                    # Filter blocked paths
                    if any(blocked in file_path.lower() for blocked in BLOCKED_PATTERNS):
                        continue
                    matches.append({
                        "path": file_path,
                        "line_number": data.get("line_number"),
                        "text": data.get("lines", {}).get("text", "").strip()[:200],
                    })
            except json.JSONDecodeError:
                continue

        return ok_response(
            {"matches": matches[:top_k], "total_found": len(matches)},
            source="repo",
            query=query,
            path=path,
        )

    except subprocess.TimeoutExpired:
        return error_response("Search timeout (30s)")
    except FileNotFoundError:
        return error_response("ripgrep (rg) not found - install with: choco install ripgrep")
    except Exception as e:
        logger.error(f"[MCP] search_repo error: {e}")
        return error_response(str(e))


def get_recent_changes(repo_root: Path, limit: int = 50) -> Dict[str, Any]:
    """
    Get recent git commits.

    Args:
        repo_root: Repository root path
        limit: Maximum commits (default 50)

    Returns:
        MCPResponse with commit history
    """
    try:
        cmd = [
            "git", "log",
            f"--max-count={limit}",
            "--pretty=format:%H|%an|%ae|%at|%s",
            "--name-only",
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(repo_root),
        )

        if result.returncode != 0:
            return error_response(f"git log failed: {result.stderr}")

        commits = []
        current_commit = None

        for line in result.stdout.strip().split("\n"):
            if "|" in line and line.count("|") >= 4:
                # New commit line
                if current_commit:
                    commits.append(current_commit)
                parts = line.split("|", 4)
                current_commit = {
                    "hash": parts[0][:8],
                    "author": parts[1],
                    "email": parts[2],
                    "timestamp": int(parts[3]),
                    "message": parts[4],
                    "files": [],
                }
            elif line.strip() and current_commit:
                # File changed
                current_commit["files"].append(line.strip())

        if current_commit:
            commits.append(current_commit)

        return ok_response(
            {"commits": commits, "count": len(commits)},
            source="git",
            limit=limit,
        )

    except subprocess.TimeoutExpired:
        return error_response("git log timeout")
    except Exception as e:
        logger.error(f"[MCP] get_recent_changes error: {e}")
        return error_response(str(e))
