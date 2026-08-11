#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Differential, non-ratcheting WSP62 authority for WRE inherited files."""

from __future__ import annotations

import ast
from datetime import date
from pathlib import Path

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[4]
WRE_ROOT = Path(__file__).resolve().parents[1]
MOLTBOT_ROOT = REPO_ROOT / "modules" / "communication" / "moltbot_bridge"
WSP62_FRAMEWORK = REPO_ROOT / "WSP_framework/src/WSP_62_Large_File_Refactoring_Enforcement_Protocol.md"
WSP62_KNOWLEDGE = REPO_ROOT / "WSP_knowledge/src/WSP_62_Large_File_Refactoring_Enforcement_Protocol.md"
EXPECTED = {
    WRE_ROOT / "src/wre_autonomous_slice_verifier_runtime.py": (
        586,
        {"verify_autonomous_slice_runtime": 157},
    ),
    WRE_ROOT / "src/foundup_job_router.py": (
        1198,
        {
            "validate_foundup_job_envelope": 212,
            "_validate_live_mode_gates": 88,
            "_validate_evidence_refs": 113,
            "_validate_compute_budget": 163,
        },
    ),
    WRE_ROOT / "src/foundup_job_consumer.py": (
        1112,
        {
            "_dispatch_to_hermes": 111,
            "_attach_context_bundle_dry_run": 160,
            "drain_openclaw_queue_with_retention": 94,
        },
    ),
    WRE_ROOT / "INTERFACE.md": (1114, {}),
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


def _assert_no_growth_entry(
    entry: dict,
    target: Path,
    file_ceiling: int,
    function_ceilings: dict[str, int],
) -> None:
    assert entry["temporary"] is True
    assert entry["owner"] and entry["architect_reviewer"]
    assert entry["reviewer"] and entry["review_date"]
    assert isinstance(date.fromisoformat(entry["expires_on"]), date)
    assert entry["remediation"]
    assert "\\" not in entry["file"]
    ceiling = entry["no_growth_ceiling"]
    assert entry["threshold_override"] == file_ceiling
    assert ceiling == {
        "file_lines": file_ceiling,
        "functions": function_ceilings,
    }
    assert len(target.read_text(encoding="utf-8").splitlines()) <= file_ceiling
    if function_ceilings:
        sizes = _named_function_sizes(target)
        for name, exact_ceiling in function_ceilings.items():
            if name in sizes:
                assert sizes[name] <= exact_ceiling


def test_wre_inherited_exemptions_are_bounded_and_non_ratcheting() -> None:
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
        _assert_no_growth_entry(
            entries[target],
            target,
            file_ceiling,
            function_ceilings,
        )


def test_required_audit_logs_use_non_blocking_archival_policy() -> None:
    entries = {
        entry["file"]: entry
        for entry in _entries(WRE_ROOT / "wsp_62_exemptions.yaml")
    }

    advisory_entries = {
        path: entry
        for path, entry in entries.items()
        if entry.get("enforcement_mode") == "advisory_archive"
    }
    assert set(advisory_entries) == {"ModLog.md", "tests/TestModLog.md"}

    for relative_path, entry in advisory_entries.items():
        assert entry["enforcement_mode"] == "advisory_archive"
        assert entry["advisory_archive_threshold"] == 1000
        assert entry["owner"] and entry["architect_reviewer"]
        assert entry["remediation"]
        assert "no_growth_ceiling" not in entry
        assert Path(relative_path).name in {"ModLog.md", "TestModLog.md"}


def _temporary_entry(file_ceiling: int) -> dict:
    return {
        "temporary": True,
        "owner": "WRE Core Maintainers",
        "architect_reviewer": "0102 Technical Architect",
        "reviewer": "0102 Technical Architect",
        "review_date": "2026-Q3",
        "expires_on": "2999-12-31",
        "remediation": "ROADMAP.md#wsp62-decomposition",
        "file": "src/legacy.py",
        "threshold_override": file_ceiling,
        "no_growth_ceiling": {"file_lines": file_ceiling, "functions": {}},
    }


def test_no_growth_ceiling_allows_debt_reduction(tmp_path: Path) -> None:
    target = tmp_path / "legacy.py"
    target.write_text("one\ntwo\n", encoding="utf-8")

    _assert_no_growth_entry(_temporary_entry(3), target, 3, {})


def test_no_growth_ceiling_rejects_candidate_growth(tmp_path: Path) -> None:
    target = tmp_path / "legacy.py"
    target.write_text("one\ntwo\nthree\nfour\n", encoding="utf-8")

    with pytest.raises(AssertionError):
        _assert_no_growth_entry(_temporary_entry(3), target, 3, {})


def test_wsp62_framework_and_knowledge_mirrors_are_byte_identical() -> None:
    assert WSP62_FRAMEWORK.read_bytes() == WSP62_KNOWLEDGE.read_bytes()
