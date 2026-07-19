"""Tests for REDDOG_OPERATIONAL_MEMEX_SNAPSHOT_SUPPLIER_PHASE1."""

from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path

from holo_index.freshness_receipt import HoloIndexFreshnessReceipt
from modules.communication.moltbot_bridge.src.reddog_openclaw_readonly_audit_swarm_enqueue import (
    ReadOnlyAuditSwarmEnqueueReceipt,
    ReadOnlyAuditTaskSpec,
)
from modules.communication.moltbot_bridge.src.reddog_operational_context_snapshot import (
    build_operational_context_snapshot,
)
from modules.communication.moltbot_bridge.src.reddog_operational_memex_snapshot_supplier import (
    OPERATIONAL_MEMEX_SUPPLY_ACCEPT,
    OPERATIONAL_MEMEX_SUPPLY_REJECT,
    OperationalMemexReadOnlyAuditTaskWriter,
    enrich_readonly_audit_tasks_with_operational_memex,
)
from modules.communication.moltbot_bridge.tests.holoindex_freshness_receipt_test_helpers import (
    build_fresh_holoindex_receipt,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_operational_memex_snapshot_supplier.py"
)
NOW = "2026-07-16T00:00:00+00:00"
HEAD = "06d823f52"
REVISION = "sha256:work-state-memex"
FOUNDUP_ID = "foundups_agent"
def _fresh_holo_receipt() -> HoloIndexFreshnessReceipt:
    return build_fresh_holoindex_receipt(
        repo_root=REPO_ROOT,
        head_sha=HEAD,
        generated_at=NOW,
    )


def _snapshot(*, breadcrumbs=True, brain=True):
    result = build_operational_context_snapshot(
        repo_state={
            "head_sha": HEAD,
            "dirty_paths": (),
            "dirty_digest": "sha256:clean",
            "worktree_digest": "sha256:worktrees",
        },
        work_state_snapshot={
            "schema_version": "reddog_authoritative_work_state.v1",
            "revision": REVISION,
            "selected_slice": "REDDOG_OPERATIONAL_MEMEX_SNAPSHOT_SUPPLIER_PHASE1",
            "refresh_receipt_id": "sha256:refresh",
            "worker_claims": [
                {
                    "claim_id": "claim-1",
                    "slice_id": "REDDOG_OPERATIONAL_MEMEX_SNAPSHOT_SUPPLIER_PHASE1",
                    "foundup_id": FOUNDUP_ID,
                }
            ],
            "wre_queue_items": [
                {"queue_item_id": "queue-1", "claim_id": "claim-1", "foundup_id": FOUNDUP_ID}
            ],
        },
        holoindex_receipt=_fresh_holo_receipt(),
        changed_paths=("docs/0102_session_briefings/ACTIVE_SLICE_LEDGER.md",),
        now_iso=NOW,
        breadcrumb_scope="REDDOG_OPERATIONAL_MEMEX_SNAPSHOT_SUPPLIER_PHASE1",
        breadcrumbs=(
            [
                {
                    "breadcrumb_id": "crumb-1",
                    "continuity_id": "REDDOG_OPERATIONAL_MEMEX_SNAPSHOT_SUPPLIER_PHASE1",
                    "task_id": "task-1",
                    "created_at": NOW,
                }
            ]
            if breadcrumbs
            else ()
        ),
        brain_state=(
            {
                "available": True,
                "signature_digest": "sha256:brain-signature",
                "summary_digest": "sha256:brain-summary",
                "record_count": 7,
            }
            if brain
            else None
        ),
    )
    assert result.accepted is True
    assert result.snapshot is not None
    return result.snapshot


def _config(**overrides):
    config = {
        "foundup_id": FOUNDUP_ID,
        "principal_id": "principal-012",
        "identity": {"foundup_id": FOUNDUP_ID, "name": "Foundups Agent"},
        "roadmap_state": {
            "foundup_id": FOUNDUP_ID,
            "roadmap_id": "resident-roadmap",
            "version": "1",
            "content_digest": "sha256:roadmap",
        },
        "verified_outcomes": (),
    }
    config.update(overrides)
    return config


def _task(lane_id: str = "repo_code_audit") -> ReadOnlyAuditTaskSpec:
    assignment = {
        "assignment_id": "assignment-1",
        "lane_id": lane_id,
        "snapshot_receipt_id": "placeholder",
        "snapshot_content_digest": "placeholder",
    }
    return ReadOnlyAuditTaskSpec(
        task_id="task-1",
        description="RedDog read-only audit lane: repo_code_audit",
        required_skills=("reddog_readonly_audit",),
        estimated_complexity=0.35,
        priority_score=0.85,
        context={"assignment": assignment},
        origin_continuity_id="determination-1",
    )


class _DelegateWriter:
    def __init__(self) -> None:
        self.calls = []

    def enqueue_readonly_audit_tasks(self, tasks, receipt):
        self.calls.append((tuple(tasks), receipt))
        return {"ok": True, "created_task_ids": [task.task_id for task in tasks]}


def test_enriches_task_with_snapshot_bound_memex_view_and_worker_bindings() -> None:
    snapshot = _snapshot()
    task = _task()
    task = replace(
        task,
        context={**task.context, "assignment": {
            **task.context["assignment"],
            "snapshot_receipt_id": snapshot.snapshot_receipt_id,
            "snapshot_content_digest": snapshot.snapshot_content_digest,
        }},
    )

    result = enrich_readonly_audit_tasks_with_operational_memex(
        tasks=(task,),
        snapshot=snapshot,
        config=_config(),
        now_iso=NOW,
    )

    assert result.accepted is True
    assert result.status == OPERATIONAL_MEMEX_SUPPLY_ACCEPT
    enriched = result.tasks[0].context
    assignment = enriched["assignment"]
    assert enriched["memex_view"]["foundup_id"] == FOUNDUP_ID
    assert enriched["memex_view"]["snapshot_id"] == snapshot.snapshot_receipt_id
    assert assignment["principal_id"] == "principal-012"
    assert assignment["work_order_id"] == "assignment-1"
    assert assignment["memex_source_scope"] == f"foundup:{FOUNDUP_ID}:lane:repo_code_audit"
    assert assignment["memex_source_revision"] == REVISION
    assert assignment["memex_holoindex_generation_id"] == _fresh_holo_receipt().generation_id
    assert enriched["memex_snapshot_supply_receipt"]["no_holoindex_reindex_performed"] is True
    assert result.supply_receipt is not None
    assert result.supply_receipt["schema_version"] == "reddog_operational_memex_snapshot_supply_receipt.v1"
    assert result.supply_receipt["receipt_id"].startswith("sha256:")
    assert result.supply_receipt["snapshot_receipt_id"] == snapshot.snapshot_receipt_id
    assert result.supply_receipt["assignment_count"] == 1
    assert result.supply_receipt["assignment_receipt_ids"] == (
        enriched["memex_snapshot_supply_receipt"]["receipt_id"],
    )
    assert result.supply_receipt["no_holoindex_reindex_performed"] is True


def test_cycle_supply_receipt_aggregates_assignment_receipts() -> None:
    snapshot = _snapshot()
    first = _task("repo_code_audit")
    second = replace(
        _task("external_research"),
        task_id="task-2",
        context={
            "assignment": {
                "assignment_id": "assignment-2",
                "lane_id": "external_research",
                "snapshot_receipt_id": snapshot.snapshot_receipt_id,
                "snapshot_content_digest": snapshot.snapshot_content_digest,
            }
        },
    )
    first = replace(
        first,
        context={
            **first.context,
            "assignment": {
                **first.context["assignment"],
                "snapshot_receipt_id": snapshot.snapshot_receipt_id,
                "snapshot_content_digest": snapshot.snapshot_content_digest,
            },
        },
    )

    result = enrich_readonly_audit_tasks_with_operational_memex(
        tasks=(first, second),
        snapshot=snapshot,
        config=_config(),
        now_iso=NOW,
    )

    assert result.accepted is True
    assert result.supply_receipt is not None
    assert result.supply_receipt["assignment_count"] == 2
    assert result.supply_receipt["assignment_ids"] == ("assignment-1", "assignment-2")
    assert result.supply_receipt["lane_ids"] == ("repo_code_audit", "external_research")
    assert result.supply_receipt["task_ids"] == ("task-1", "task-2")
    assert result.supply_receipt["assignment_receipt_ids"] == tuple(
        task.context["memex_snapshot_supply_receipt"]["receipt_id"] for task in result.tasks
    )


def test_rejects_before_enqueue_when_memex_sources_are_not_fresh() -> None:
    snapshot = _snapshot(breadcrumbs=False)
    task = _task()
    delegate = _DelegateWriter()
    writer = OperationalMemexReadOnlyAuditTaskWriter(
        delegate=delegate,
        snapshot=snapshot,
        config=_config(),
        now_iso=NOW,
    )
    receipt = ReadOnlyAuditSwarmEnqueueReceipt(
        enqueue_receipt_id="receipt-1",
        status="READONLY_AUDIT_SWARM_ENQUEUE_ACCEPT",
        swarm_id="swarm-1",
        snapshot_receipt_id=snapshot.snapshot_receipt_id,
        determination_id="determination-1",
        task_ids=("task-1",),
        assignment_ids=("assignment-1",),
        rejection_reasons=(),
        created_at=NOW,
        receipt_digest="sha256:receipt",
    )

    result = writer.enqueue_readonly_audit_tasks((task,), receipt)

    assert result["ok"] is False
    assert result["reason"] == "operational_memex_supply_rejected"
    assert writer.last_result is not None
    assert writer.last_result.status == OPERATIONAL_MEMEX_SUPPLY_REJECT
    assert "breadcrumbs_source_empty" in writer.last_result.rejection_reasons
    assert delegate.calls == []


def test_rejects_missing_scope_without_guessing_foundup() -> None:
    result = enrich_readonly_audit_tasks_with_operational_memex(
        tasks=(_task(),),
        snapshot=_snapshot(),
        config=_config(foundup_id="", principal_id=""),
        now_iso=NOW,
    )

    assert result.accepted is False
    assert "missing_foundup_id" in result.rejection_reasons
    assert "missing_principal_id" in result.rejection_reasons


def test_supplier_module_is_read_only_by_ast() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    forbidden_imports = {"subprocess", "requests", "httpx", "sqlite3", "os"}
    forbidden_calls = {"open", "write_text", "write_bytes", "system", "popen"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".", 1)[0] not in forbidden_imports
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".", 1)[0] not in forbidden_imports
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                assert node.func.attr not in forbidden_calls
            if isinstance(node.func, ast.Name):
                assert node.func.id not in forbidden_calls
