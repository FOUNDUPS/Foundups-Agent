"""Tests for REDDOG_OPENCLAW_LIVE_ENQUEUE_WRITER_ADAPTER_PHASE1."""

from __future__ import annotations

import ast
from pathlib import Path

from modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator import (
    clear_job_queue,
    get_job_queue,
)
from modules.communication.moltbot_bridge.src.reddog_openclaw_live_enqueue import (
    LIVE_ENQUEUE_ACCEPT,
    perform_reddog_openclaw_live_enqueue,
)
from modules.communication.moltbot_bridge.src.reddog_openclaw_live_enqueue_writer import (
    OpenClawLiveEnqueueWriter,
)


def _intake(target_type="foundup_job"):
    return {
        "target_type": target_type,
        "proposed_job_id": "reddog-fj-writer-001" if target_type == "foundup_job" else None,
        "proposed_task_id": "reddog-wo-writer-001" if target_type == "autonomous_task" else None,
        "work_order_id": "wo-writer-001",
        "operation": "feature_slice",
        "requested_action": "build_foundup" if target_type == "foundup_job" else None,
        "repo_scope": "FOUNDUPS/Foundups-Agent",
        "allowed_paths": ["modules/communication/moltbot_bridge/**"],
        "denied_paths": [".env"],
        "required_tests": ["modules/communication/moltbot_bridge/tests/test_reddog_openclaw_live_enqueue_writer.py"],
        "evidence_refs": ["policy_gate:sha256:policy"],
        "no_enqueue_performed": True,
        "no_execution_performed": True,
    }


def _receipt():
    return {
        "live_enqueue_id": "live-enqueue-writer-001",
        "work_order_id": "wo-writer-001",
        "receipt_digest": "sha256:receipt",
        "no_execution_performed": True,
        "no_reward_settlement_performed": True,
    }


def _adapter():
    return {
        "decision": "ADAPTER_DRYRUN_ACCEPT",
        "work_order_id": "wo-writer-001",
        "proposed_intake": _intake("foundup_job"),
        "adapter_receipt": {
            "adapter_receipt_id": "adapter-writer-001",
            "adapter_receipt_digest": "sha256:adapter",
            "decision": "ADAPTER_DRYRUN_ACCEPT",
            "target_type": "foundup_job",
            "work_order_id": "wo-writer-001",
            "created_at": "2026-07-11T00:00:00+00:00",
            "rejection_reasons": [],
        },
        "rejection_reasons": [],
        "no_enqueue_performed": True,
        "no_execution_performed": True,
    }


def _policy():
    return {
        "decision": "POLICY_ACCEPT",
        "receipt_digest": "sha256:policy",
        "signature_gate_status": "SIGNATURE_GATE_ACCEPTED",
        "signature_gate_digest": "sha256:signed-authority",
        "no_execution_performed": True,
        "work_order_id": "wo-writer-001",
    }


def _chain():
    return {
        "decision": "SIGNED_RECEIPT_CHAIN_ACCEPT",
        "accepted": True,
        "terminal_receipt_hash": "sha256:receipt-chain",
        "no_execution_performed": True,
        "no_reward_settlement_performed": True,
    }


def _valve():
    return {
        "valve_state": "VALVE_OPEN_LIVE_ENQUEUE",
        "work_order_id": "wo-writer-001",
        "decision_digest": "sha256:valve",
        "rejection_reasons": [],
        "gates_checked": ["execution_valve_evaluator"],
        "no_execution_performed": True,
        "intake_target": "foundup_job",
    }


class _FakeAgentDB:
    def __init__(self) -> None:
        self.calls = []

    def create_autonomous_task(self, **kwargs):
        self.calls.append(kwargs)
        return True


def test_foundup_job_writer_appends_typed_job_without_execution():
    clear_job_queue()


def test_live_enqueue_seam_with_concrete_writer_appends_queue_item():
    clear_job_queue()
    result = perform_reddog_openclaw_live_enqueue(
        _adapter(),
        _policy(),
        _chain(),
        _valve(),
        writer=OpenClawLiveEnqueueWriter(),
        seen_live_enqueue_keys=set(),
        admission_consumer=lambda: True,
    )

    assert result.decision == LIVE_ENQUEUE_ACCEPT
    assert result.receipt is not None
    assert result.receipt.openclaw_queue_item_id == "reddog-fj-writer-001"
    assert len(get_job_queue()) == 1
    assert get_job_queue()[0].payload["live_enqueue_receipt"]["live_enqueue_id"] == result.receipt.live_enqueue_id
    assert get_job_queue()[0].started_at is None
    clear_job_queue()
    writer = OpenClawLiveEnqueueWriter()

    result = writer.enqueue_foundup_job(_intake("foundup_job"), _receipt())

    queue = get_job_queue()
    assert result == {"ok": True, "openclaw_queue_item_id": "reddog-fj-writer-001", "agentdb_task_id": None}
    assert len(queue) == 1
    job = queue[0]
    assert job.job_id == "reddog-fj-writer-001"
    assert job.requested_action == "build_foundup"
    assert job.intent_id == "wo-writer-001"
    assert job.payload["no_execution_performed"] is True
    assert job.payload["source"] == "reddog_openclaw_live_enqueue"
    assert job.started_at is None
    assert job.worker_id is None
    clear_job_queue()


def test_foundup_job_writer_rejects_missing_proposed_job_id():
    clear_job_queue()
    intake = _intake("foundup_job")
    intake["proposed_job_id"] = ""

    result = OpenClawLiveEnqueueWriter().enqueue_foundup_job(intake, _receipt())

    assert result == {"ok": False, "reason": "missing_proposed_job_id"}
    assert get_job_queue() == []


def test_autonomous_task_writer_calls_agentdb_factory_only_when_used():
    fake_db = _FakeAgentDB()
    writer = OpenClawLiveEnqueueWriter(agent_db_factory=lambda: fake_db)

    result = writer.enqueue_autonomous_task(_intake("autonomous_task"), _receipt())

    assert result == {"ok": True, "openclaw_queue_item_id": None, "agentdb_task_id": "reddog-wo-writer-001"}
    assert len(fake_db.calls) == 1
    call = fake_db.calls[0]
    assert call["task_id"] == "reddog-wo-writer-001"
    assert call["required_skills"] == ["reddog_work_order"]
    assert call["origin_continuity_id"] == "wo-writer-001"
    assert call["context"]["no_execution_performed"] is True


def test_autonomous_task_writer_rejects_missing_task_id_before_db_factory():
    calls = []
    intake = _intake("autonomous_task")
    intake["proposed_task_id"] = ""
    writer = OpenClawLiveEnqueueWriter(agent_db_factory=lambda: calls.append("called"))

    result = writer.enqueue_autonomous_task(intake, _receipt())

    assert result == {"ok": False, "reason": "missing_proposed_task_id"}
    assert calls == []


def test_ast_boundary_no_subprocess_hermes_wre_or_execution_calls():
    path = Path("modules/communication/moltbot_bridge/src/reddog_openclaw_live_enqueue_writer.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports = set()
    calls = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)

    forbidden_import_fragments = ("subprocess", "hermes", "wre_core", "skillz", "github")
    forbidden_calls = {"open", "eval", "exec", "system", "popen", "run", "check_call", "check_output"}
    assert not any(fragment in imported for imported in imports for fragment in forbidden_import_fragments)
    assert not (calls & forbidden_calls)
