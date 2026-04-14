"""
Documentation Perception Tools for FoundUps MCP Bridge.

Read-only access to WSP docs, module docs, ModLogs, and INTERFACE files.

WSP References:
- WSP 97: Truthful verification
- WSP 49: Module structure (README, INTERFACE, tests)
- WSP 22: ModLog documentation
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .response_schema import ok_response, error_response

logger = logging.getLogger(__name__)

# WSP document locations
WSP_PATHS = [
    "WSP_framework/src",
    "WSP_knowledge/src",
    "docs/mcp",
]

# Module structure per WSP 49
MODULE_DOC_FILES = ["README.md", "INTERFACE.md", "ROADMAP.md", "ModLog.md"]
TEST_DOC_FILES = ["tests/README.md", "tests/TestModLog.md"]


def get_wsp_docs(repo_root: Path) -> Dict[str, Any]:
    """
    Get list of all WSP protocol documents.

    Args:
        repo_root: Repository root path

    Returns:
        MCPResponse with WSP document listing
    """
    try:
        docs = []

        for wsp_path in WSP_PATHS:
            wsp_dir = repo_root / wsp_path
            if not wsp_dir.exists():
                continue

            for md_file in wsp_dir.glob("*.md"):
                docs.append({
                    "path": str(md_file.relative_to(repo_root)),
                    "name": md_file.stem,
                    "size": md_file.stat().st_size,
                })

        # Sort by name for consistent ordering
        docs.sort(key=lambda x: x["name"])

        return ok_response(
            {"wsp_docs": docs, "count": len(docs)},
            source="wsp",
            paths_searched=WSP_PATHS,
        )

    except Exception as e:
        logger.error(f"[MCP] get_wsp_docs error: {e}")
        return error_response(str(e))


def get_module_docs(repo_root: Path, module_name: str) -> Dict[str, Any]:
    """
    Get module documentation (README.md).

    Args:
        repo_root: Repository root path
        module_name: Module name (e.g., "ai_overseer", "youtube_auth")

    Returns:
        MCPResponse with module README content
    """
    try:
        # Search for module in standard locations
        search_paths = [
            repo_root / "modules",
            repo_root / "holo_index",
        ]

        module_path = None
        for base in search_paths:
            for match in base.rglob(module_name):
                if match.is_dir():
                    module_path = match
                    break
            if module_path:
                break

        if not module_path:
            return error_response(f"Module not found: {module_name}")

        # Read README.md
        readme_path = module_path / "README.md"
        if not readme_path.exists():
            return error_response(f"README.md not found for module: {module_name}")

        content = readme_path.read_text(encoding="utf-8")

        return ok_response(
            {
                "module": module_name,
                "path": str(module_path.relative_to(repo_root)),
                "readme": content,
                "lines": content.count("\n") + 1,
            },
            source="module",
            module=module_name,
        )

    except Exception as e:
        logger.error(f"[MCP] get_module_docs error: {e}")
        return error_response(str(e))


def get_interface_doc(repo_root: Path, module_name: str) -> Dict[str, Any]:
    """
    Get module INTERFACE.md (public API contract).

    Args:
        repo_root: Repository root path
        module_name: Module name

    Returns:
        MCPResponse with INTERFACE.md content
    """
    try:
        # Search for module
        search_paths = [repo_root / "modules", repo_root / "holo_index"]

        module_path = None
        for base in search_paths:
            for match in base.rglob(module_name):
                if match.is_dir():
                    module_path = match
                    break
            if module_path:
                break

        if not module_path:
            return error_response(f"Module not found: {module_name}")

        # Read INTERFACE.md
        interface_path = module_path / "INTERFACE.md"
        if not interface_path.exists():
            return error_response(f"INTERFACE.md not found for module: {module_name}")

        content = interface_path.read_text(encoding="utf-8")

        return ok_response(
            {
                "module": module_name,
                "path": str(module_path.relative_to(repo_root)),
                "interface": content,
                "lines": content.count("\n") + 1,
            },
            source="module",
            module=module_name,
        )

    except Exception as e:
        logger.error(f"[MCP] get_interface_doc error: {e}")
        return error_response(str(e))


def get_test_docs(repo_root: Path, module_name: str) -> Dict[str, Any]:
    """
    Get module test documentation (TestModLog, tests/README).

    Args:
        repo_root: Repository root path
        module_name: Module name

    Returns:
        MCPResponse with test documentation
    """
    try:
        # Search for module
        search_paths = [repo_root / "modules", repo_root / "holo_index"]

        module_path = None
        for base in search_paths:
            for match in base.rglob(module_name):
                if match.is_dir():
                    module_path = match
                    break
            if module_path:
                break

        if not module_path:
            return error_response(f"Module not found: {module_name}")

        result = {
            "module": module_name,
            "path": str(module_path.relative_to(repo_root)),
            "test_readme": None,
            "test_modlog": None,
        }

        # Check tests/README.md
        test_readme = module_path / "tests" / "README.md"
        if test_readme.exists():
            result["test_readme"] = test_readme.read_text(encoding="utf-8")

        # Check tests/TestModLog.md or TestModLog.md
        for modlog_name in ["tests/TestModLog.md", "TestModLog.md"]:
            modlog_path = module_path / modlog_name
            if modlog_path.exists():
                result["test_modlog"] = modlog_path.read_text(encoding="utf-8")
                break

        if not result["test_readme"] and not result["test_modlog"]:
            return error_response(f"No test documentation found for module: {module_name}")

        return ok_response(result, source="module", module=module_name)

    except Exception as e:
        logger.error(f"[MCP] get_test_docs error: {e}")
        return error_response(str(e))


def get_modlog(repo_root: Path, limit: int = 20) -> Dict[str, Any]:
    """
    Get recent ModLog entries from root and key modules.

    Args:
        repo_root: Repository root path
        limit: Maximum entries per ModLog (default 20)

    Returns:
        MCPResponse with ModLog content
    """
    try:
        modlogs = []

        # Root ModLog
        root_modlog = repo_root / "ModLog.md"
        if root_modlog.exists():
            content = root_modlog.read_text(encoding="utf-8")
            # Extract recent entries (rough heuristic: split by ## headers)
            sections = content.split("\n## ")
            recent = sections[:limit + 1]  # +1 for header
            modlogs.append({
                "path": "ModLog.md",
                "scope": "root",
                "content": "\n## ".join(recent),
                "total_sections": len(sections) - 1,
            })

        # Key module ModLogs
        key_modules = [
            "modules/ai_intelligence/ai_overseer",
            "modules/infrastructure/wre_core",
            "modules/foundups",
            "public/member",
            "holo_index",
        ]

        for module_path in key_modules:
            modlog_path = repo_root / module_path / "ModLog.md"
            if modlog_path.exists():
                content = modlog_path.read_text(encoding="utf-8")
                sections = content.split("\n## ")
                recent = sections[:limit + 1]
                modlogs.append({
                    "path": f"{module_path}/ModLog.md",
                    "scope": module_path.split("/")[-1],
                    "content": "\n## ".join(recent),
                    "total_sections": len(sections) - 1,
                })

        return ok_response(
            {"modlogs": modlogs, "count": len(modlogs)},
            source="modlog",
            limit=limit,
        )

    except Exception as e:
        logger.error(f"[MCP] get_modlog error: {e}")
        return error_response(str(e))


def get_violations(repo_root: Path, limit: int = 20) -> Dict[str, Any]:
    """
    Get known WSP violations from violation logs and audit files.

    Args:
        repo_root: Repository root path
        limit: Maximum violations (default 20)

    Returns:
        MCPResponse with violation records
    """
    try:
        violations = []

        # Check WSP violation log
        violation_paths = [
            repo_root / "WSP_VIOLATION_LOG.md",
            repo_root / "docs" / "WSP_VIOLATION_LOG.md",
            repo_root / "modules" / "ai_intelligence" / "ai_overseer" / "memory" / "wsp_framework_audit_latest.json",
        ]

        for vpath in violation_paths:
            if not vpath.exists():
                continue

            if vpath.suffix == ".json":
                import json
                data = json.loads(vpath.read_text(encoding="utf-8"))
                if "drift_files" in data:
                    for drift in data.get("drift_files", [])[:limit]:
                        violations.append({
                            "type": "wsp_drift",
                            "file": drift,
                            "source": str(vpath.relative_to(repo_root)),
                        })
                if "index_issues" in data:
                    for issue in data.get("index_issues", [])[:limit]:
                        violations.append({
                            "type": "index_issue",
                            "issue": issue,
                            "source": str(vpath.relative_to(repo_root)),
                        })
            else:
                content = vpath.read_text(encoding="utf-8")
                violations.append({
                    "type": "violation_log",
                    "path": str(vpath.relative_to(repo_root)),
                    "content": content[:5000],  # Truncate
                })

        return ok_response(
            {"violations": violations[:limit], "count": len(violations)},
            source="violations",
            limit=limit,
        )

    except Exception as e:
        logger.error(f"[MCP] get_violations error: {e}")
        return error_response(str(e))
