"""Tests for REDDOG_OPENCLAW_READONLY_AUDIT_SWARM_AGENTDB_ENQUEUE_PHASE1."""

from __future__ import annotations

import ast
import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import pytest

from holo_index.freshness_receipt import HoloIndexFreshnessReceipt
from modules.communication.moltbot_bridge.src.reddog_context_snapshot_fusion_assignment_gate import (
    evaluate_context_snapshot_fusion_assignment_gate,
)
from modules.communication.moltbot_bridge.src.reddog_openclaw_readonly_audit_swarm_enqueue import (
    READONLY_AUDIT_SWARM_ENQUEUE_ACCEPT,
    READONLY_AUDIT_SWARM_ENQUEUE_REJECT,
    READONLY_AUDIT_TASK_SKILL,
    READONLY_AUDIT_TASK_SOURCE,
    AgentDbReadOnlyAuditTaskWriter,
    ReadOnlyAuditEnqueueReason,
    enqueue_reddog_readonly_audit_swarm,
)
from modules.communication.moltbot_bridge.src.reddog_openclaw_readonly_audit_swarm_runtime import (
    DEFAULT_AUDIT_LANES,
    plan_reddog_openclaw_readonly_audit_swarm,
)
from modules.communication.moltbot_bridge.src.reddog_operational_context_snapshot import (
    build_evidence_bundle,
    build_operational_context_snapshot,
)
from modules.communication.moltbot_bridge.src.reddog_wsp15_allocation_receipt import (
    allocate_reddog_wsp15_receipt,
)
from modules.communication.moltbot_bridge.tests.test_reddog_openclaw_readonly_audit_swarm_runtime import (
    GROUNDING_FOCUS,
    _grounding_receipt,
)
from modules.communication.moltbot_bridge.tests.holoindex_freshness_receipt_test_helpers import (
    build_fresh_holoindex_receipt,
)
from modules.infrastructure.database.src.agent_db import AgentDB
from modules.infrastructure.database.src.db_manager import DatabaseManager


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_openclaw_readonly_audit_swarm_enqueue.py"
)
NOW = "2026-07-14T00:00:00+00:00"
HEAD = "eda98c8a9evidence"
REVISION = "sha256:work-state-refresh"


@pytest.fixture(autouse=True)
def isolated_agent_db(tmp_path, monkeypatch):
    monkeypatch.setenv("FOUNDUPS_DB_PATH", str(tmp_path / "foundups.db"))
    DatabaseManager.reset_for_tests()
    yield
    DatabaseManager.reset_for_tests()


class _FakeWriter:
    def __init__(self, *, ok=True, created_override=None) -> None:
        self.ok = ok
        self.created_override = created_override
        self.calls = []

    def enqueue_readonly_audit_tasks(self, tasks, receipt):
        self.calls.append((list(tasks), receipt))
        if not self.ok:
            return {"ok": False, "reason": "writer_rejected", "created_task_ids": []}
        created = self.created_override
        if created is None:
            created = [task.task_id for task in tasks]
        return {"ok": True, "created_task_ids": created}


def _fresh_holo_receipt() -> HoloIndexFreshnessReceipt:
    return build_fresh_holoindex_receipt(
        repo_root=REPO_ROOT,
        head_sha=HEAD,
        generated_at=NOW,
    )


def _valid_plan(wsp15_allocation_receipt=None, *, with_grounding: bool = False):
    snapshot_result = build_operational_context_snapshot(
        repo_state={
            "head_sha": HEAD,
            "dirty_paths": (),
            "dirty_digest": "sha256:clean",
            "worktree_digest": "sha256:worktrees",
        },
        work_state_snapshot={
            "schema_version": "reddog_authoritative_work_state.v1",
            "revision": REVISION,
            "selected_slice": "REDDOG_OPENCLAW_READONLY_AUDIT_SWARM_AGENTDB_ENQUEUE_PHASE1",
            "refresh_receipt_id": "sha256:refresh",
            "worker_claims": [{"claim_id": "claim-1", "status": "ACTIVE"}],
            "wre_queue_items": [{"queue_item_id": "queue-1"}],
        },
        holoindex_receipt=_fresh_holo_receipt(),
        changed_paths=[
            "docs/0102_session_briefings/work_ledger.schema.json",
            "modules/communication/moltbot_bridge/src/reddog_openclaw_readonly_audit_swarm_runtime.py",
        ],
        breadcrumbs=[
            {
                "breadcrumb_id": "b1",
                "continuity_id": "cont-1",
                "timestamp": NOW,
            }
        ],
        breadcrumb_scope="cont-1",
        now_iso=NOW,
    )
    assert snapshot_result.accepted is True
    assert snapshot_result.snapshot is not None
    assert snapshot_result.context_view is not None
    evidence_bundle = build_evidence_bundle(
        snapshot=snapshot_result.snapshot,
        context_view=snapshot_result.context_view,
        report_digests=["sha256:repo-audit", "sha256:security-audit"],
    )
    gate = evaluate_context_snapshot_fusion_assignment_gate(
        snapshot=snapshot_result.snapshot,
        context_view=snapshot_result.context_view,
        evidence_bundle=evidence_bundle,
        current_repo_head_sha=HEAD,
        current_work_state_revision=REVISION,
        current_breadcrumb_high_watermark=snapshot_result.snapshot.breadcrumbs_state["high_watermark"],
        requested_operation="readonly_audit_swarm",
        prompt_text="audit current RedDog operational loop",
        now_iso="2026-07-14T00:01:00+00:00",
    )
    assert gate.accepted is True
    plan = plan_reddog_openclaw_readonly_audit_swarm(
        snapshot=snapshot_result.snapshot,
        context_view=snapshot_result.context_view,
        evidence_bundle=evidence_bundle,
        gate_decision=gate,
        allowed_read_targets=[
            "docs/0102_session_briefings/work_ledger.schema.json",
            "modules/communication/moltbot_bridge/src/reddog_operational_context_snapshot.py",
        ],
        wsp15_allocation_receipt=wsp15_allocation_receipt,
        grounding_receipt=_grounding_receipt() if with_grounding else None,
        grounding_work_focus=GROUNDING_FOCUS if with_grounding else "",
    )
    assert plan.accepted is True
    return plan


def test_enqueue_accepts_plan_and_builds_pending_readonly_tasks() -> None:
    plan = _valid_plan()
    writer = _FakeWriter()

    result = enqueue_reddog_readonly_audit_swarm(
        plan=plan,
        writer=writer,
        now=datetime(2026, 7, 14, tzinfo=timezone.utc),
    )

    assert result.accepted is True
    assert result.decision == READONLY_AUDIT_SWARM_ENQUEUE_ACCEPT
    assert result.receipt.status == READONLY_AUDIT_SWARM_ENQUEUE_ACCEPT
    assert result.receipt.no_task_execution_performed is True
    assert result.receipt.no_repo_mutation_performed is True
    assert result.receipt.no_live_foundup_enqueue_performed is True
    assert tuple(task.context["assignment"]["lane_id"] for task in result.tasks) == DEFAULT_AUDIT_LANES
    assert all(task.required_skills == (READONLY_AUDIT_TASK_SKILL,) for task in result.tasks)
    assert all(task.context["source"] == READONLY_AUDIT_TASK_SOURCE for task in result.tasks)
    assert all(task.context["worker_mode"] == "model_backed_0102" for task in result.tasks)
    assert writer.calls and len(writer.calls[0][0]) == 5


def test_enqueue_carries_wsp15_allocation_into_every_task_context() -> None:
    allocation = allocate_reddog_wsp15_receipt(
        requested_operation="readonly_audit_swarm",
        prompt_text="audit current RedDog operational loop",
        allowed_read_targets=["docs/0102_session_briefings/work_ledger.schema.json"],
    ).to_dict()
    plan = _valid_plan(wsp15_allocation_receipt=allocation)

    result = enqueue_reddog_readonly_audit_swarm(plan=plan, writer=_FakeWriter())

    assert result.accepted is True
    assert len(result.tasks) == len(DEFAULT_AUDIT_LANES)
    for task in result.tasks:
        assert task.context["worker_mode"] == "model_backed_0102"
        assert task.context["wsp15_allocation_receipt"]["receipt_id"] == allocation["receipt_id"]
        assert task.context["wsp15_allocation_receipt_id"] == allocation["receipt_id"]
        assert task.context["wsp15_allocation_digest"]


def test_enqueue_carries_grounding_receipt_and_typed_targets_into_agentdb_tasks() -> None:
    plan = _valid_plan(with_grounding=True)

    result = enqueue_reddog_readonly_audit_swarm(plan=plan, writer=_FakeWriter())

    assert result.accepted is True
    for task in result.tasks:
        assert task.context["grounding_receipt_id"] == plan.receipt.grounding_receipt_id
        assert task.context["grounding_receipt"] == plan.receipt.grounding_receipt
        assert task.context["work_focus"] == GROUNDING_FOCUS
        assert task.context["typed_targets"]["repo_file_targets"] == [
            "holo_index/adaptive_learning/breadcrumb_tracer.py"
        ]
        assert task.context["semantic_targets"] == ["RedDog continuity semantics"]


def test_enqueue_rejects_assignment_grounding_substitution_before_writer() -> None:
    plan = _valid_plan(with_grounding=True)
    bad_assignment = replace(plan.assignments[0], grounding_receipt_id="sha256:wrong")
    bad_plan = replace(plan, assignments=(bad_assignment,) + plan.assignments[1:])
    writer = _FakeWriter()

    result = enqueue_reddog_readonly_audit_swarm(plan=bad_plan, writer=writer)

    assert result.accepted is False
    assert ReadOnlyAuditEnqueueReason.ASSIGNMENT_UNSAFE in result.rejection_reasons
    assert writer.calls == []


def test_enqueue_revalidates_nested_grounding_mapping_after_plan_creation() -> None:
    plan = _valid_plan(with_grounding=True)
    plan.receipt.grounding_receipt["typed_targets"]["semantic_targets"] = ["substituted"]
    writer = _FakeWriter()

    result = enqueue_reddog_readonly_audit_swarm(plan=plan, writer=writer)

    assert result.accepted is False
    assert ReadOnlyAuditEnqueueReason.ASSIGNMENT_UNSAFE in result.rejection_reasons
    assert writer.calls == []


def test_rejects_rejected_plan_and_missing_writer_before_publication() -> None:
    plan = _valid_plan()
    rejected = replace(plan, accepted=False)

    result = enqueue_reddog_readonly_audit_swarm(plan=rejected, writer=_FakeWriter())
    missing_writer = enqueue_reddog_readonly_audit_swarm(plan=plan, writer=None)

    assert result.accepted is False
    assert result.decision == READONLY_AUDIT_SWARM_ENQUEUE_REJECT
    assert ReadOnlyAuditEnqueueReason.PLAN_NOT_ACCEPTED in result.rejection_reasons
    assert result.tasks == ()
    assert missing_writer.accepted is False
    assert ReadOnlyAuditEnqueueReason.WRITER_MISSING in missing_writer.rejection_reasons


def test_rejects_unsafe_assignment_binding() -> None:
    plan = _valid_plan()
    bad_assignment = replace(plan.assignments[0], determination_id="wrong")
    bad_plan = replace(plan, assignments=(bad_assignment,) + plan.assignments[1:])
    writer = _FakeWriter()

    result = enqueue_reddog_readonly_audit_swarm(plan=bad_plan, writer=writer)

    assert result.accepted is False
    assert ReadOnlyAuditEnqueueReason.ASSIGNMENT_UNSAFE in result.rejection_reasons
    assert writer.calls == []


def test_rejects_assignment_id_replay_before_writer_call() -> None:
    plan = _valid_plan()
    seen = {plan.assignments[0].assignment_id}
    writer = _FakeWriter()

    result = enqueue_reddog_readonly_audit_swarm(plan=plan, writer=writer, seen_assignment_ids=seen)

    assert result.accepted is False
    assert ReadOnlyAuditEnqueueReason.IDEMPOTENCY_REPLAY in result.rejection_reasons
    assert writer.calls == []


def test_writer_rejection_or_bad_created_ids_rejects() -> None:
    plan = _valid_plan()
    rejected = enqueue_reddog_readonly_audit_swarm(plan=plan, writer=_FakeWriter(ok=False))
    bad_created = enqueue_reddog_readonly_audit_swarm(
        plan=plan,
        writer=_FakeWriter(created_override=["wrong"]),
    )

    assert rejected.accepted is False
    assert bad_created.accepted is False
    assert rejected.rejection_reasons == (ReadOnlyAuditEnqueueReason.WRITER_REJECTED,)
    assert bad_created.rejection_reasons == (ReadOnlyAuditEnqueueReason.WRITER_REJECTED,)


def test_agentdb_writer_publishes_tasks_atomically() -> None:
    plan = _valid_plan()
    result = enqueue_reddog_readonly_audit_swarm(
        plan=plan,
        writer=AgentDbReadOnlyAuditTaskWriter(),
        now=datetime(2026, 7, 14, tzinfo=timezone.utc),
    )

    assert result.accepted is True
    db = AgentDB()
    pending = db.get_autonomous_tasks(status="pending", limit=10)
    assert len(pending) == 5
    task_ids = {task["task_id"] for task in pending}
    assert task_ids == set(result.receipt.task_ids)
    for task in pending:
        assert task["required_skills"] == [READONLY_AUDIT_TASK_SKILL]
        assert task["context"]["source"] == READONLY_AUDIT_TASK_SOURCE
        assert task["context"]["swarm_receipt"]["swarm_id"] == plan.receipt.swarm_id
        assert task["origin_continuity_id"] == plan.receipt.determination_id


def test_agentdb_writer_rejects_duplicate_without_partial_second_batch() -> None:
    plan = _valid_plan()
    writer = AgentDbReadOnlyAuditTaskWriter()
    first = enqueue_reddog_readonly_audit_swarm(plan=plan, writer=writer)
    second = enqueue_reddog_readonly_audit_swarm(plan=plan, writer=writer)

    assert first.accepted is True
    assert second.accepted is False
    assert second.rejection_reasons == (ReadOnlyAuditEnqueueReason.WRITER_REJECTED,)
    pending = AgentDB().get_autonomous_tasks(status="pending", limit=20)
    assert len(pending) == 5


def test_result_is_deterministic_and_json_serializable() -> None:
    plan = _valid_plan()
    first = enqueue_reddog_readonly_audit_swarm(
        plan=plan,
        writer=_FakeWriter(),
        now=datetime(2026, 7, 14, tzinfo=timezone.utc),
    )
    second = enqueue_reddog_readonly_audit_swarm(
        plan=plan,
        writer=_FakeWriter(),
        now=datetime(2026, 7, 14, tzinfo=timezone.utc),
    )

    assert first.receipt.receipt_digest == second.receipt.receipt_digest
    json.dumps(first.to_dict(), sort_keys=True)


def test_module_ast_boundaries() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_text = (
        "subprocess",
        "requests",
        "openclaw_supervisor",
        "hermes_job_executor",
        "execute_skill",
        "worktree_create",
        "git push",
        "gh pr",
        "holo_index.py --index",
        "run_task.py",
    )
    for token in forbidden_text:
        assert token not in source

    imported = set()
    calls = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)

    assert not (imported & {"subprocess", "requests", "socket", "urllib", "shutil"})
    assert not (calls & {"eval", "exec", "compile", "system", "popen", "run", "Popen"})
