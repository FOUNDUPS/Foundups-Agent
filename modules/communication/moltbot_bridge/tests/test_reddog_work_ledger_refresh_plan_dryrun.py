"""Tests for RedDog work-ledger refresh plan dry-run."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_lane_state_reconciler import (
    parse_active_slice_ledger,
    parse_work_ledger_json,
    reconcile_active_and_json_ledgers,
    reconcile_lane_sources,
)
from modules.communication.moltbot_bridge.src.reddog_work_ledger_refresh_plan_dryrun import (
    REFRESH_PLAN_BLOCKED,
    REFRESH_PLAN_READY,
    build_work_ledger_refresh_plan_dryrun,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_work_ledger_refresh_plan_dryrun.py"
)


ACTIVE_LEDGER = """# Active Slice Ledger

**Updated**: 2026-04-01

## Open Slices

| Slice | Priority | Blocked By | Notes |
|-------|----------|------------|-------|
| `BH1_BRANCH_HYGIENE_FORENSICS` | HIGH | - | first |

## Next Priority Order

1. **BH1** - first
"""


WORK_LEDGER = {
    "schema_version": "1.0.0",
    "last_updated": "2026-04-01T00:00:00Z",
    "slices": [
        {
            "slice_id": "DJ2_F_OPENCLAW_SECURITY_FAIL_DISPATCH",
            "title": "security dispatch",
            "status": "PROPOSED",
            "priority": "P0",
            "source": "audit",
            "created_at": "2026-04-01T00:00:00Z",
        }
    ],
}


def test_stale_sources_produce_ready_refresh_plan_without_mutation() -> None:
    report = reconcile_active_and_json_ledgers(
        ACTIVE_LEDGER,
        json.dumps(WORK_LEDGER),
        now_iso="2026-07-13T00:00:00Z",
    )
    plan = build_work_ledger_refresh_plan_dryrun(
        report,
        proposed_last_updated="2026-07-13T00:00:00Z",
    )

    assert plan.status == REFRESH_PLAN_READY
    assert plan.proposed_next_claim_slice == "BH1_BRANCH_HYGIENE_FORENSICS"
    assert "docs/0102_session_briefings/ACTIVE_SLICE_LEDGER.md" in plan.refresh_targets
    assert "docs/0102_session_briefings/work_ledger.example.json" in plan.refresh_targets
    assert "rerun_worker_claim_gate" in plan.refresh_steps
    assert plan.no_ledger_mutation_performed is True
    assert plan.no_holoindex_mutation_performed is True
    assert plan.no_worker_assignment_performed is True


def test_conflicted_report_blocks_refresh_plan_until_conflict_resolved() -> None:
    active = """# Active Slice Ledger
**Updated**: 2026-07-13

## Closed Slices

| Slice | Commit | Evidence |
|-------|--------|----------|
| `REDDOG_DONE_PHASE1` | `abc1234` | landed |
"""
    conflict_json = {
        "schema_version": "1.0.0",
        "last_updated": "2026-07-13T00:00:00Z",
        "slices": [
            {
                "slice_id": "REDDOG_DONE_PHASE1",
                "title": "stale duplicate",
                "status": "IN_PROGRESS",
                "source": "manual",
                "created_at": "2026-07-13T00:00:00Z",
            }
        ],
    }
    report = reconcile_lane_sources(
        [
            parse_active_slice_ledger(active),
            parse_work_ledger_json(json.dumps(conflict_json)),
        ],
        now_iso="2026-07-13T00:00:00Z",
    )
    plan = build_work_ledger_refresh_plan_dryrun(
        report,
        proposed_last_updated="2026-07-13T00:00:00Z",
    )

    assert plan.status == REFRESH_PLAN_BLOCKED
    assert plan.proposed_next_claim_slice is None
    assert plan.conflict_slice_ids == ("REDDOG_DONE_PHASE1",)
    assert "resolve_lane_state_conflicts_first" in plan.rejection_reasons


def test_fresh_report_marks_no_refresh_needed() -> None:
    fresh_active = ACTIVE_LEDGER.replace("2026-04-01", "2026-07-13")
    fresh_work = {**WORK_LEDGER, "last_updated": "2026-07-13T00:00:00Z"}
    report = reconcile_active_and_json_ledgers(
        fresh_active,
        json.dumps(fresh_work),
        now_iso="2026-07-13T00:00:00Z",
    )
    plan = build_work_ledger_refresh_plan_dryrun(
        report,
        proposed_last_updated="2026-07-13T00:00:00Z",
    )

    assert plan.status == REFRESH_PLAN_READY
    assert plan.stale_sources == ()
    assert "no_refresh_needed" in plan.rejection_reasons


def test_plan_digest_is_deterministic() -> None:
    report = reconcile_active_and_json_ledgers(
        ACTIVE_LEDGER,
        json.dumps(WORK_LEDGER),
        now_iso="2026-07-13T00:00:00Z",
    )
    first = build_work_ledger_refresh_plan_dryrun(report, proposed_last_updated="2026-07-13T00:00:00Z")
    second = build_work_ledger_refresh_plan_dryrun(report, proposed_last_updated="2026-07-13T00:00:00Z")

    assert first.plan_id == second.plan_id
    assert len(first.plan_id) == 64


def test_plan_json_serializable() -> None:
    report = reconcile_active_and_json_ledgers(
        ACTIVE_LEDGER,
        json.dumps(WORK_LEDGER),
        now_iso="2026-07-13T00:00:00Z",
    )
    plan = build_work_ledger_refresh_plan_dryrun(report, proposed_last_updated="2026-07-13T00:00:00Z")

    json.dumps(plan.to_dict(), sort_keys=True)


def test_rejects_invalid_inputs() -> None:
    report = reconcile_active_and_json_ledgers(
        ACTIVE_LEDGER,
        json.dumps(WORK_LEDGER),
        now_iso="2026-07-13T00:00:00Z",
    )
    with pytest.raises(TypeError):
        build_work_ledger_refresh_plan_dryrun("not a report", proposed_last_updated="2026-07-13T00:00:00Z")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        build_work_ledger_refresh_plan_dryrun(report, proposed_last_updated="")


def test_module_has_no_mutating_or_execution_imports() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    banned_import_roots = {
        "os",
        "subprocess",
        "requests",
        "urllib",
        "http",
        "shutil",
        "sqlite3",
        "pathlib",
    }
    banned_calls = {"open", "eval", "exec", "compile", "__import__"}

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
