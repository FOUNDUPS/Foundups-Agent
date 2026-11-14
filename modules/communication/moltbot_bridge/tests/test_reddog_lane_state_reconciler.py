"""Tests for RedDog lane-state reconciler dry-run."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_lane_state_reconciler import (
    parse_active_slice_ledger,
    parse_work_ledger_json,
    reconcile_active_and_json_ledgers,
    reconcile_lane_sources,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_lane_state_reconciler.py"
)


ACTIVE_LEDGER = """# Active Slice Ledger

**Authority**: 0102 architect lane
**Updated**: 2026-04-21 (LEDGER-RECON3)

## Closed Slices

| Slice | Commit | Evidence |
|-------|--------|----------|
| `REDDOG_DONE_PHASE1` | `abc1234` | landed module |

## Open Slices

| Slice | Priority | Blocked By | Notes |
|-------|----------|------------|-------|
| `REDDOG_P0_PHASE1` | P0 | - | top priority |
| `REDDOG_P2_PHASE1` | P2 | - | lower priority |
| `REDDOG_BLOCKED_PHASE1` | P1 | `REDDOG_DONE_PHASE1` | blocked |

## Deferred Slices

| Slice | Reason |
|-------|--------|
| `REDDOG_PARKED_PHASE1` | later |
"""


WORK_LEDGER = {
    "schema_version": "1.0.0",
    "last_updated": "2026-07-13T00:00:00Z",
    "slices": [
        {
            "slice_id": "REDDOG_JSON_P1_PHASE1",
            "title": "JSON P1",
            "status": "PROPOSED",
            "priority": "P1",
            "wsp15_score": {"total": 18},
            "source": "audit",
            "created_at": "2026-07-13T00:00:00Z",
            "owner_worker": "W1",
            "lane": "A",
        },
        {
            "slice_id": "REDDOG_JSON_MERGED_PHASE1",
            "title": "Merged",
            "status": "MERGED",
            "priority": "P3",
            "source": "audit",
            "created_at": "2026-07-13T00:00:00Z",
            "merge_commit": "def5678",
        },
    ],
}


def test_parse_active_slice_ledger_extracts_closed_open_blocked_and_deferred() -> None:
    snapshot = parse_active_slice_ledger(ACTIVE_LEDGER)
    by_id = {record.slice_id: record for record in snapshot.records}

    assert snapshot.source_type == "active_slice_ledger"
    assert snapshot.last_updated == "2026-04-21"
    assert by_id["REDDOG_DONE_PHASE1"].status == "MERGED"
    assert by_id["REDDOG_P0_PHASE1"].status == "PROPOSED"
    assert by_id["REDDOG_BLOCKED_PHASE1"].status == "BLOCKED"
    assert by_id["REDDOG_PARKED_PHASE1"].status == "PARKED"


def test_parse_active_slice_ledger_normalizes_legacy_lowercase_ids() -> None:
    markdown = """# Active Slice Ledger
**Updated**: 2026-07-13

## Closed Slices

| Slice | Commit | Evidence |
|-------|--------|----------|
| `legacy_lowercase_slice` | `abc1234` | landed |

## Open Slices

| Slice | Priority | Blocked By | Notes |
|-------|----------|------------|-------|
| `next_lowercase_slice` | P1 | - | open |
"""
    snapshot = parse_active_slice_ledger(markdown)
    ids = {record.slice_id for record in snapshot.records}

    assert "LEGACY_LOWERCASE_SLICE" in ids
    assert "NEXT_LOWERCASE_SLICE" in ids


def test_parse_active_slice_ledger_ignores_none_rows() -> None:
    markdown = """# Active Slice Ledger
**Updated**: 2026-07-13

## Blocked Slices

| Slice | Reason |
|-------|--------|
| _(none)_ | - |
"""
    snapshot = parse_active_slice_ledger(markdown)

    assert all(record.slice_id != "NONE" for record in snapshot.records)


def test_parse_work_ledger_json_extracts_typed_fields() -> None:
    snapshot = parse_work_ledger_json(json.dumps(WORK_LEDGER))
    record = next(item for item in snapshot.records if item.slice_id == "REDDOG_JSON_P1_PHASE1")

    assert snapshot.source_type == "work_ledger_json"
    assert snapshot.last_updated == "2026-07-13T00:00:00Z"
    assert record.priority == "P1"
    assert record.wsp15_total == 18
    assert record.owner_worker == "W1"
    assert record.lane == "A"


def test_reconcile_marks_stale_ledger_but_still_produces_prework_packet() -> None:
    report = reconcile_active_and_json_ledgers(
        ACTIVE_LEDGER,
        json.dumps(WORK_LEDGER),
        now_iso="2026-07-13T00:00:00Z",
    )

    assert report.recommended_action == "VERIFY_STALE_LEDGER_BEFORE_WORK"
    assert any(item.startswith("ACTIVE_SLICE_LEDGER:stale:2026-04-21") for item in report.stale_sources)
    assert report.prework_packet.no_assignment_performed is True
    assert report.no_ledger_mutation_performed is True


def test_wsp15_queue_prefers_p0_then_p1_high_score_then_p2() -> None:
    report = reconcile_active_and_json_ledgers(
        ACTIVE_LEDGER,
        json.dumps(WORK_LEDGER),
        now_iso="2026-04-22T00:00:00Z",
        stale_after_days=90,
    )

    assert report.next_wsp15_queue[:4] == (
        "REDDOG_P0_PHASE1",
        "REDDOG_JSON_P1_PHASE1",
        "REDDOG_BLOCKED_PHASE1",
        "REDDOG_P2_PHASE1",
    )
    assert report.prework_packet.chosen_slice == "REDDOG_P0_PHASE1"


def test_active_ledger_next_priority_order_overrides_raw_priority() -> None:
    markdown = ACTIVE_LEDGER + """

## Next Priority Order

1. **REDDOG-P2** - architect says do this first
2. **REDDOG-P0** - then the raw P0
"""
    report = reconcile_active_and_json_ledgers(
        markdown,
        json.dumps(WORK_LEDGER),
        now_iso="2026-04-22T00:00:00Z",
        stale_after_days=90,
    )

    assert report.next_wsp15_queue[:2] == ("REDDOG_P2_PHASE1", "REDDOG_P0_PHASE1")
    assert report.prework_packet.chosen_slice == "REDDOG_P2_PHASE1"


def test_requested_closed_slice_redirects_to_next_open_slice() -> None:
    report = reconcile_active_and_json_ledgers(
        ACTIVE_LEDGER,
        json.dumps(WORK_LEDGER),
        requested_slice="REDDOG_DONE_PHASE1",
        now_iso="2026-04-22T00:00:00Z",
        stale_after_days=90,
    )

    assert report.prework_packet.closed_groundwork == ("REDDOG_DONE_PHASE1",)
    assert report.prework_packet.not_this_slice == ("REDDOG_DONE_PHASE1",)
    assert report.prework_packet.chosen_slice == "REDDOG_P0_PHASE1"
    assert report.prework_packet.reason == "requested_slice_already_closed_redirected_to_next_open"


def test_open_closed_conflict_blocks_worker_assignment() -> None:
    active = parse_active_slice_ledger(ACTIVE_LEDGER)
    stale_json = {
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
    typed = parse_work_ledger_json(json.dumps(stale_json), source_id="stale_json")
    report = reconcile_lane_sources([active, typed], now_iso="2026-07-13T00:00:00Z")

    assert report.recommended_action == "RECONCILE_LEDGER_BEFORE_WORK"
    assert report.conflicts[0].slice_id == "REDDOG_DONE_PHASE1"
    assert report.prework_packet.chosen_slice is None
    assert report.prework_packet.reason == "ledger_conflict_blocks_worker_assignment"
    assert report.prework_packet.no_execution_performed is True


def test_invalid_json_fails_closed_as_unusable_source() -> None:
    snapshot = parse_work_ledger_json("{not json")

    assert snapshot.records == ()
    assert "invalid_json" in snapshot.parse_warnings


def test_report_digest_is_deterministic_for_same_inputs() -> None:
    kwargs = {
        "active_slice_ledger_markdown": ACTIVE_LEDGER,
        "work_ledger_json": json.dumps(WORK_LEDGER),
        "now_iso": "2026-07-13T00:00:00Z",
    }
    first = reconcile_active_and_json_ledgers(**kwargs)
    second = reconcile_active_and_json_ledgers(**kwargs)

    assert first.report_id == second.report_id
    assert len(first.report_id) == 64


def test_report_is_json_serializable_and_truth_flags_are_hardcoded() -> None:
    report = reconcile_active_and_json_ledgers(
        ACTIVE_LEDGER,
        json.dumps(WORK_LEDGER),
        now_iso="2026-07-13T00:00:00Z",
    )
    payload = report.to_dict()

    assert payload["no_ledger_mutation_performed"] is True
    assert payload["no_agentdb_mutation_performed"] is True
    assert payload["no_holoindex_mutation_performed"] is True
    assert payload["no_worker_assignment_performed"] is True
    assert payload["no_execution_performed"] is True
    json.dumps(payload, sort_keys=True)


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
