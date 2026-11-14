"""Tests for REDDOG_WORK_LEDGER_SOURCE_PROJECTION_SUPPLY_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_lane_state_reconciler import (
    parse_active_slice_ledger,
    parse_work_ledger_json,
)
from modules.communication.moltbot_bridge.src.reddog_authoritative_work_state_refresh_runtime import (
    InMemoryAuthoritativeWorkStateStore,
    refresh_authoritative_work_state_runtime,
)
from modules.communication.moltbot_bridge.src.reddog_work_ledger_source_projection_supply import (
    WORK_LEDGER_PROJECTION_APPLIED,
    WORK_LEDGER_PROJECTION_NOT_READY,
    supply_work_ledger_source_projection,
)
from modules.communication.moltbot_bridge.src.reddog_work_ledger_source_projection_supply_bootstrap import (
    run_reddog_work_ledger_source_projection_supply_bootstrap,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_work_ledger_source_projection_supply.py"
)
NOW = "2026-07-16T00:00:00+00:00"
SLICE_ID = "REDDOG_WORK_LEDGER_SOURCE_PROJECTION_SUPPLY_PHASE1"


def _write_json(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _github_records() -> list[dict[str, object]]:
    return [
        {
            "slice_id": SLICE_ID,
            "status": "PR_OPEN",
            "priority": "P0",
            "lane": "A",
            "pr_number": 1180,
            "head_commit": "b" * 40,
            "evidence_refs": ["github:pr:1180"],
            "wsp15_score": {"total": 19},
        }
    ]


def _w10_records() -> list[dict[str, object]]:
    return [
        {
            "slice_id": SLICE_ID,
            "status": "PR_OPEN",
            "priority": "P0",
            "lane": "A",
            "evidence_refs": ["w10:ledger_projection:fixture"],
            "wsp15_score": {"total": 19},
        }
    ]


def test_projection_writes_fresh_active_and_work_ledger_outside_repo(tmp_path: Path) -> None:
    github_path = _write_json(tmp_path / "runtime" / "github.json", _github_records())
    w10_path = _write_json(tmp_path / "runtime" / "w10.json", _w10_records())
    active_path = tmp_path / "runtime" / "ACTIVE_SLICE_LEDGER.runtime.md"
    work_path = tmp_path / "runtime" / "work_ledger.runtime.json"

    result = supply_work_ledger_source_projection(
        repo_root=REPO_ROOT,
        github_pr_records_path=github_path,
        w10_report_records_path=w10_path,
        active_slice_ledger_output_path=active_path,
        work_ledger_json_output_path=work_path,
        now_iso=NOW,
    )

    assert result.accepted is True
    assert result.status == WORK_LEDGER_PROJECTION_APPLIED
    assert result.receipt.projected_slice_count == 1
    assert result.receipt.open_slice_count == 1
    assert result.receipt.no_canonical_ledger_mutation_performed is True
    active = active_path.read_text(encoding="utf-8")
    work = work_path.read_text(encoding="utf-8")
    assert f"**Updated**: {NOW}" in active
    assert SLICE_ID in active
    assert parse_active_slice_ledger(active).records[0].slice_id == SLICE_ID
    assert parse_work_ledger_json(work).records[0].slice_id == SLICE_ID


def test_projection_outputs_feed_authoritative_refresh(tmp_path: Path) -> None:
    github_path = _write_json(tmp_path / "runtime" / "github.json", _github_records())
    w10_path = _write_json(tmp_path / "runtime" / "w10.json", _w10_records())
    active_path = tmp_path / "runtime" / "ACTIVE_SLICE_LEDGER.runtime.md"
    work_path = tmp_path / "runtime" / "work_ledger.runtime.json"

    projection = supply_work_ledger_source_projection(
        repo_root=REPO_ROOT,
        github_pr_records_path=github_path,
        w10_report_records_path=w10_path,
        active_slice_ledger_output_path=active_path,
        work_ledger_json_output_path=work_path,
        now_iso=NOW,
    )

    refresh = refresh_authoritative_work_state_runtime(
        active_slice_ledger_markdown=active_path.read_text(encoding="utf-8"),
        work_ledger_json=work_path.read_text(encoding="utf-8"),
        github_pr_records=json.loads(github_path.read_text(encoding="utf-8")),
        w10_report_records=json.loads(w10_path.read_text(encoding="utf-8")),
        store=InMemoryAuthoritativeWorkStateStore(),
        worker_id="reddog-projection-test",
        now_iso=NOW,
    )

    assert projection.accepted is True
    assert refresh.accepted is True
    assert refresh.receipt.selected_slice == SLICE_ID
    assert refresh.snapshot and refresh.snapshot["wre_queue_items"][0]["no_execution_performed"] is True


def test_projection_rejects_outputs_inside_repo(tmp_path: Path) -> None:
    github_path = _write_json(tmp_path / "runtime" / "github.json", _github_records())
    w10_path = _write_json(tmp_path / "runtime" / "w10.json", _w10_records())

    result = supply_work_ledger_source_projection(
        repo_root=REPO_ROOT,
        github_pr_records_path=github_path,
        w10_report_records_path=w10_path,
        active_slice_ledger_output_path=REPO_ROOT / "ACTIVE_SLICE_LEDGER.runtime.md",
        work_ledger_json_output_path=tmp_path / "runtime" / "work_ledger.runtime.json",
        now_iso=NOW,
    )

    assert result.accepted is False
    assert result.status == WORK_LEDGER_PROJECTION_NOT_READY
    assert "active_slice_ledger_output_inside_repo" in result.receipt.rejection_reasons
    assert not (REPO_ROOT / "ACTIVE_SLICE_LEDGER.runtime.md").exists()


def test_projection_rejects_missing_sources_without_writing(tmp_path: Path) -> None:
    active_path = tmp_path / "runtime" / "ACTIVE_SLICE_LEDGER.runtime.md"
    work_path = tmp_path / "runtime" / "work_ledger.runtime.json"

    result = supply_work_ledger_source_projection(
        repo_root=REPO_ROOT,
        github_pr_records_path=tmp_path / "missing_github.json",
        w10_report_records_path=tmp_path / "missing_w10.json",
        active_slice_ledger_output_path=active_path,
        work_ledger_json_output_path=work_path,
        now_iso=NOW,
    )

    assert result.accepted is False
    assert "missing_github_pr_records" in result.receipt.rejection_reasons
    assert "missing_w10_report_records" in result.receipt.rejection_reasons
    assert not active_path.exists()
    assert not work_path.exists()


def test_bootstrap_returns_projection_paths(tmp_path: Path) -> None:
    github_path = _write_json(tmp_path / "runtime" / "github.json", _github_records())
    w10_path = _write_json(tmp_path / "runtime" / "w10.json", _w10_records())
    active_path = tmp_path / "runtime" / "ACTIVE_SLICE_LEDGER.runtime.md"
    work_path = tmp_path / "runtime" / "work_ledger.runtime.json"

    result = run_reddog_work_ledger_source_projection_supply_bootstrap(
        repo_root=tmp_path / "repo",
        github_pr_records_path=github_path,
        w10_report_records_path=w10_path,
        active_slice_ledger_output_path=active_path,
        work_ledger_json_output_path=work_path,
        now_iso=NOW,
    )

    assert result.accepted is True
    assert result.active_slice_ledger_path == str(active_path.resolve())
    assert result.work_ledger_json_path == str(work_path.resolve())
    assert result.open_slice_count == 1


def test_module_has_no_shell_execution_holoindex_or_repo_mutation_imports() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    banned_import_roots = {"subprocess", "requests", "urllib", "http", "socket", "holo_index"}
    banned_calls = {"eval", "exec", "compile", "__import__"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] not in banned_import_roots
        elif isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] not in banned_import_roots
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                assert func.id not in banned_calls
            if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                assert func.value.id not in banned_import_roots
