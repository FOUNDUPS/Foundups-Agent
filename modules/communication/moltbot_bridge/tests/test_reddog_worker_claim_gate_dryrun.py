"""Tests for RedDog worker-claim gate dry-run."""

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
from modules.communication.moltbot_bridge.src.reddog_worker_claim_gate_dryrun import (
    CLAIM_READY_DRYRUN,
    CLAIM_REJECTED,
    evaluate_reddog_worker_claim_dryrun,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_worker_claim_gate_dryrun.py"
)


ACTIVE_LEDGER = """# Active Slice Ledger

**Updated**: 2026-07-13

## Closed Slices

| Slice | Commit | Evidence |
|-------|--------|----------|
| `REDDOG_DONE_PHASE1` | `abc1234` | landed |

## Open Slices

| Slice | Priority | Blocked By | Notes |
|-------|----------|------------|-------|
| `REDDOG_NEXT_PHASE1` | P0 | - | next |
| `REDDOG_OTHER_PHASE1` | P1 | - | other |

## Next Priority Order

1. **REDDOG-NEXT** - first
2. **REDDOG-OTHER** - second
"""


WORK_LEDGER = {
    "schema_version": "1.0.0",
    "last_updated": "2026-07-13T00:00:00Z",
    "slices": [
        {
            "slice_id": "REDDOG_JSON_PHASE1",
            "title": "JSON slice",
            "status": "PROPOSED",
            "priority": "P2",
            "source": "audit",
            "created_at": "2026-07-13T00:00:00Z",
            "lane": "B",
            "owner_worker": "W2",
        }
    ],
}


def _fresh_report():
    return reconcile_active_and_json_ledgers(
        ACTIVE_LEDGER,
        json.dumps(WORK_LEDGER),
        now_iso="2026-07-13T00:00:00Z",
        stale_after_days=30,
    )


def test_accepts_fresh_non_conflicting_selected_slice_dryrun_only() -> None:
    decision = evaluate_reddog_worker_claim_dryrun(
        _fresh_report(),
        worker_id="reddog-0102",
        lane_id="A",
    )

    assert decision.accepted is True
    assert decision.receipt.decision == CLAIM_READY_DRYRUN
    assert decision.receipt.selected_slice == "REDDOG_NEXT_PHASE1"
    assert decision.receipt.worker_id == "reddog-0102"
    assert decision.receipt.lane_id == "A"
    assert decision.receipt.rejection_reasons == ()
    assert decision.receipt.no_worker_assignment_performed is True
    assert decision.receipt.no_worker_spawn_performed is True
    assert decision.receipt.no_execution_performed is True


def test_rejects_stale_sources_by_default() -> None:
    stale = reconcile_active_and_json_ledgers(
        ACTIVE_LEDGER.replace("2026-07-13", "2026-04-01"),
        json.dumps({**WORK_LEDGER, "last_updated": "2026-04-01T00:00:00Z"}),
        now_iso="2026-07-13T00:00:00Z",
    )
    decision = evaluate_reddog_worker_claim_dryrun(stale, worker_id="reddog-0102")

    assert decision.accepted is False
    assert decision.receipt.decision == CLAIM_REJECTED
    assert "ledger_sources_stale" in decision.receipt.rejection_reasons
    assert decision.receipt.selected_slice is None


def test_allow_stale_sources_is_explicit_and_still_dryrun() -> None:
    stale = reconcile_active_and_json_ledgers(
        ACTIVE_LEDGER.replace("2026-07-13", "2026-04-01"),
        json.dumps({**WORK_LEDGER, "last_updated": "2026-04-01T00:00:00Z"}),
        now_iso="2026-07-13T00:00:00Z",
    )
    decision = evaluate_reddog_worker_claim_dryrun(
        stale,
        worker_id="reddog-0102",
        allow_stale_sources=True,
    )

    assert decision.accepted is True
    assert decision.receipt.selected_slice == "REDDOG_NEXT_PHASE1"
    assert decision.receipt.stale_sources
    assert decision.receipt.no_worker_assignment_performed is True


def test_rejects_lane_state_conflict() -> None:
    active = parse_active_slice_ledger(ACTIVE_LEDGER)
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
        [active, parse_work_ledger_json(json.dumps(conflict_json))],
        now_iso="2026-07-13T00:00:00Z",
    )
    decision = evaluate_reddog_worker_claim_dryrun(report)

    assert decision.accepted is False
    assert "lane_state_conflict" in decision.receipt.rejection_reasons
    assert "reconcile_ledger_before_claim" in decision.receipt.rejection_reasons
    assert decision.receipt.conflict_slice_ids == ("REDDOG_DONE_PHASE1",)


def test_rejects_requested_closed_slice() -> None:
    decision = evaluate_reddog_worker_claim_dryrun(
        _fresh_report(),
        requested_slice="REDDOG_DONE_PHASE1",
    )

    assert decision.accepted is False
    assert "requested_slice_already_closed" in decision.receipt.rejection_reasons
    assert decision.receipt.selected_slice is None


def test_rejects_requested_slice_not_in_open_queue() -> None:
    decision = evaluate_reddog_worker_claim_dryrun(
        _fresh_report(),
        requested_slice="REDDOG_UNKNOWN_PHASE1",
    )

    assert decision.accepted is False
    assert "requested_slice_not_in_open_queue" in decision.receipt.rejection_reasons
    assert "selected_slice_not_open" in decision.receipt.rejection_reasons


def test_requested_open_slice_can_override_default_candidate() -> None:
    decision = evaluate_reddog_worker_claim_dryrun(
        _fresh_report(),
        requested_slice="REDDOG_OTHER_PHASE1",
        worker_id="reddog-0102",
    )

    assert decision.accepted is True
    assert decision.receipt.selected_slice == "REDDOG_OTHER_PHASE1"


def test_rejects_no_open_work() -> None:
    closed_only = """# Active Slice Ledger
**Updated**: 2026-07-13

## Closed Slices

| Slice | Commit | Evidence |
|-------|--------|----------|
| `REDDOG_DONE_PHASE1` | `abc1234` | landed |
"""
    report = reconcile_active_and_json_ledgers(
        closed_only,
        json.dumps({"schema_version": "1.0.0", "last_updated": "2026-07-13T00:00:00Z", "slices": []}),
        now_iso="2026-07-13T00:00:00Z",
    )
    decision = evaluate_reddog_worker_claim_dryrun(report)

    assert decision.accepted is False
    assert "no_open_work" in decision.receipt.rejection_reasons
    assert "no_selected_slice" in decision.receipt.rejection_reasons


def test_receipt_digest_is_deterministic() -> None:
    kwargs = {"report": _fresh_report(), "worker_id": "reddog-0102", "lane_id": "A"}
    first = evaluate_reddog_worker_claim_dryrun(**kwargs)
    second = evaluate_reddog_worker_claim_dryrun(**kwargs)

    assert first.receipt.claim_id == second.receipt.claim_id
    assert len(first.receipt.claim_id) == 64


def test_receipt_is_json_serializable() -> None:
    decision = evaluate_reddog_worker_claim_dryrun(_fresh_report())

    payload = decision.to_dict()
    assert payload["receipt"]["no_ledger_mutation_performed"] is True
    json.dumps(payload, sort_keys=True)


def test_type_error_for_non_report_input() -> None:
    with pytest.raises(TypeError):
        evaluate_reddog_worker_claim_dryrun("not a report")  # type: ignore[arg-type]


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
