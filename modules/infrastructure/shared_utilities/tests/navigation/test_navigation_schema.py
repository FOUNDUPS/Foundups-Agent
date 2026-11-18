# -*- coding: utf-8 -*-
import sys
import io


# === UTF-8 ENFORCEMENT (WSP 90) ===
# Prevent UnicodeEncodeError on Windows systems
# Only apply when running as main script, not during import
if __name__ == '__main__' and sys.platform.startswith('win'):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except (OSError, ValueError):
        # Ignore if stdout/stderr already wrapped or closed
        pass
# === END UTF-8 ENFORCEMENT ===

"""Validation for NAVIGATION.py schema and coverage."""

from pathlib import Path

import importlib

NAV = importlib.import_module("NAVIGATION")
REPO_ROOT = Path(NAV.__file__).resolve().parent


def _location_path(location: str) -> str:
    """Extract the repository-relative path from one navigation location."""

    return location.split(" - ", 1)[0].split(":", 1)[0].strip()


def _exact_repo_path_exists(relative_path: str) -> bool:
    """Require every path component to exist with the spelling in NAVIGATION."""

    path = Path(relative_path)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        return False
    current = REPO_ROOT
    for part in path.parts:
        try:
            names = {entry.name for entry in current.iterdir()}
        except OSError:
            return False
        if part not in names:
            return False
        current /= part
    return current.exists()


def test_need_to_entries_are_semantic():
    assert NAV.NEED_TO, "NEED_TO map cannot be empty"
    for need, location in NAV.NEED_TO.items():
        assert isinstance(need, str) and need.strip(), "Need keys must be non-empty strings"
        assert isinstance(location, str) and location.strip(), f"Location missing for {need}"


def test_need_to_paths_resolve_exactly_in_current_repository():
    missing = sorted(
        (need, _location_path(location))
        for need, location in NAV.NEED_TO.items()
        if not _exact_repo_path_exists(_location_path(location))
    )
    assert not missing, f"NEED_TO contains stale or case-mismatched paths: {missing}"


def test_module_graph_contains_wre_flow():
    core_flows = NAV.MODULE_GRAPH.get("core_flows", [])
    assert isinstance(core_flows, list), "core_flows must be an ordered edge list"
    names = {name for name, _location in core_flows}
    assert {
        "handle_holoindex_request",
        "route_to_agent",
        "load_skill_on_demand",
    }.issubset(names), "HoloIndex -> orchestrator -> WRE recall flow is incomplete"


def test_coverage_table_retains_navigation_operations():
    coverage_path = Path("WSP_framework/reports/NAVIGATION/NAVIGATION_COVERAGE.md")
    assert coverage_path.exists(), "Coverage table missing"
    lines = [line for line in coverage_path.read_text(encoding="utf-8").splitlines() if line.startswith("|")]
    # Skip header divider lines
    coverage_needs = {
        line.split("|")[1].strip()
        for line in lines[2:]
        if line.count("|") >= 3
    }
    assert {
        "run navigation audit",
        "validate navigation schema",
    }.issubset(coverage_needs), "Coverage table is missing its maintenance operations"


def test_navigation_module_import_is_canonical():
    assert "NAVIGATION.py" in NAV.__file__, "Module import path unexpected"
