#!/usr/bin/env python3
"""
MCP Bridge Test Mapping Utility.

Maps modules and files to their test coverage.

Provides:
- Module-to-test file mapping
- Test coverage detection
- Coverage gap identification

WSP References:
- WSP 5: Test Coverage Protocol
- WSP 49: Module Structure (tests/ directory standard)
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


def get_test_mapping(
    repo_root: Path,
    modules: List[str],
) -> Dict[str, any]:
    """
    Get test coverage mapping for specified modules.

    Args:
        repo_root: Repository root path
        modules: List of module names to check

    Returns:
        Test mapping with coverage details
    """
    results = {
        "modules_checked": len(modules),
        "covered": 0,
        "total": len(modules),
        "gaps": [],
        "coverage_details": [],
    }

    for module_name in modules:
        coverage = _analyze_module_test_coverage(repo_root, module_name)
        results["coverage_details"].append(coverage)

        if coverage["has_tests"]:
            results["covered"] += 1
        else:
            results["gaps"].append(module_name)

    return results


def get_file_test_mapping(
    repo_root: Path,
    file_path: str,
) -> Dict[str, any]:
    """
    Get test coverage for a specific file.

    Args:
        repo_root: Repository root path
        file_path: Relative file path

    Returns:
        Test mapping for the file
    """
    full_path = repo_root / file_path

    # Extract module info from path
    module_info = _extract_module_from_path(file_path)
    if not module_info:
        return {
            "file": file_path,
            "has_tests": False,
            "test_files": [],
            "reason": "File not in modules/ structure",
        }

    module_name = module_info["module"]
    domain = module_info["domain"]

    # Find related test files
    test_files = _find_related_tests(repo_root, file_path, module_name, domain)

    return {
        "file": file_path,
        "module": module_name,
        "domain": domain,
        "has_tests": len(test_files) > 0,
        "test_files": test_files,
        "test_count": len(test_files),
    }


def _analyze_module_test_coverage(
    repo_root: Path,
    module_name: str,
) -> Dict[str, any]:
    """Analyze test coverage for a module."""
    # Find module directory
    module_path = _find_module_path(repo_root, module_name)
    if not module_path:
        return {
            "module": module_name,
            "has_tests": False,
            "test_dir_exists": False,
            "test_count": 0,
            "test_files": [],
            "reason": "Module not found",
        }

    # Check for tests directory
    tests_dir = module_path / "tests"
    if not tests_dir.exists():
        return {
            "module": module_name,
            "has_tests": False,
            "test_dir_exists": False,
            "test_count": 0,
            "test_files": [],
            "reason": "No tests/ directory",
        }

    # Find test files
    test_files = list(tests_dir.rglob("test_*.py"))
    test_files += list(tests_dir.rglob("*_test.py"))

    # Count src files for coverage ratio
    src_dir = module_path / "src"
    src_files = list(src_dir.rglob("*.py")) if src_dir.exists() else []
    src_files = [f for f in src_files if not f.name.startswith("__")]

    return {
        "module": module_name,
        "has_tests": len(test_files) > 0,
        "test_dir_exists": True,
        "test_count": len(test_files),
        "test_files": [str(f.relative_to(repo_root)) for f in test_files[:10]],  # Limit
        "src_file_count": len(src_files),
        "coverage_ratio": len(test_files) / max(len(src_files), 1),
    }


def _find_related_tests(
    repo_root: Path,
    file_path: str,
    module_name: str,
    domain: str,
) -> List[str]:
    """Find test files related to a source file."""
    related = []

    # Get the file stem (without extension)
    file_stem = Path(file_path).stem

    # Module tests directory
    tests_dir = repo_root / "modules" / domain / module_name / "tests"
    if not tests_dir.exists():
        return []

    # Search patterns
    patterns = [
        f"test_{file_stem}.py",
        f"test_{file_stem}_*.py",
        f"{file_stem}_test.py",
    ]

    for test_file in tests_dir.rglob("*.py"):
        test_name = test_file.name.lower()
        file_stem_lower = file_stem.lower()

        # Check if test file name relates to source file
        if (
            f"test_{file_stem_lower}" in test_name
            or f"{file_stem_lower}_test" in test_name
            or file_stem_lower in test_name
        ):
            related.append(str(test_file.relative_to(repo_root)))

    return related[:10]  # Limit results


def _find_module_path(repo_root: Path, module_name: str) -> Optional[Path]:
    """Find module directory by name."""
    modules_dir = repo_root / "modules"
    if not modules_dir.exists():
        return None

    for domain in modules_dir.iterdir():
        if domain.is_dir() and not domain.name.startswith("."):
            candidate = domain / module_name
            if candidate.exists() and candidate.is_dir():
                return candidate

    return None


def _extract_module_from_path(file_path: str) -> Optional[Dict[str, str]]:
    """Extract module and domain from file path."""
    # Pattern: modules/<domain>/<module>/...
    match = re.match(r"modules[/\\]([^/\\]+)[/\\]([^/\\]+)", file_path)
    if match:
        return {
            "domain": match.group(1),
            "module": match.group(2),
        }
    return None


def get_all_test_directories(repo_root: Path) -> List[Dict[str, any]]:
    """Get list of all test directories in the repo."""
    test_dirs = []
    modules_dir = repo_root / "modules"

    if not modules_dir.exists():
        return []

    for domain in modules_dir.iterdir():
        if not domain.is_dir() or domain.name.startswith("."):
            continue

        for module in domain.iterdir():
            if not module.is_dir() or module.name.startswith("."):
                continue

            tests_dir = module / "tests"
            if tests_dir.exists():
                test_files = list(tests_dir.rglob("test_*.py"))
                test_dirs.append({
                    "domain": domain.name,
                    "module": module.name,
                    "test_count": len(test_files),
                    "path": str(tests_dir.relative_to(repo_root)),
                })

    return test_dirs
