#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Exact, non-ratcheting WSP62 debt authority for create-route host files."""

from __future__ import annotations

import ast
from datetime import date
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[4]
WRE_ROOT = Path(__file__).resolve().parents[1]
MOLTBOT_ROOT = REPO_ROOT / "modules" / "communication" / "moltbot_bridge"
SLICE_DATE = date(2026, 7, 23)
EXPECTED = {
    WRE_ROOT / "src/foundup_job_router.py": (
        1193,
        {
            "validate_foundup_job_envelope": 212,
            "_validate_live_mode_gates": 88,
            "_validate_evidence_refs": 113,
            "_validate_compute_budget": 163,
        },
    ),
    WRE_ROOT / "src/foundup_job_consumer.py": (
        1110,
        {
            "_dispatch_to_hermes": 111,
            "_attach_context_bundle_dry_run": 160,
            "drain_openclaw_queue_with_retention": 94,
        },
    ),
    MOLTBOT_ROOT / "src/foundup_job_contract.py": (796, {}),
}


def _entries(path: Path) -> list[dict]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    assert isinstance(payload.get("exemptions"), list)
    return payload["exemptions"]


def _named_function_sizes(path: Path) -> dict[str, int]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.name: node.end_lineno - node.lineno + 1
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _assert_exact_entry(
    entry: dict,
    target: Path,
    file_ceiling: int,
    function_ceilings: dict[str, int],
) -> None:
    assert entry["temporary"] is True
    assert entry["owner"] and entry["architect_reviewer"]
    assert SLICE_DATE < date.fromisoformat(entry["expires_on"])
    assert entry["remediation"]
    assert "\\" not in entry["file"]
    ceiling = entry["no_growth_ceiling"]
    assert entry["threshold_override"] == file_ceiling
    assert ceiling == {
        "file_lines": file_ceiling,
        "functions": function_ceilings,
    }
    assert len(target.read_text(encoding="utf-8").splitlines()) == file_ceiling
    sizes = _named_function_sizes(target)
    for name, exact_ceiling in function_ceilings.items():
        assert sizes[name] == exact_ceiling


def test_create_route_host_exemptions_are_exact_and_non_ratcheting() -> None:
    wre_entries = {
        WRE_ROOT / entry["file"]: entry
        for entry in _entries(WRE_ROOT / "wsp_62_exemptions.yaml")
    }
    moltbot_entries = {
        MOLTBOT_ROOT / entry["file"]: entry
        for entry in _entries(MOLTBOT_ROOT / "wsp_62_exemptions.yaml")
    }
    entries = {**wre_entries, **moltbot_entries}

    for target, (file_ceiling, function_ceilings) in EXPECTED.items():
        _assert_exact_entry(
            entries[target],
            target,
            file_ceiling,
            function_ceilings,
        )
