"""Tests for REDDOG_OPENCLAW_LIVE_ENQUEUE_IMPLEMENTATION_PHASE1."""

from __future__ import annotations

import ast
from datetime import datetime, timezone
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_openclaw_live_enqueue import (
    LIVE_ENQUEUE_ACCEPT,
    LIVE_ENQUEUE_REJECT,
    LiveEnqueueReason,
    perform_reddog_openclaw_live_enqueue,
)
from modules.communication.moltbot_bridge.src.reddog_openclaw_adapter_dryrun import (
    ADAPTER_DRYRUN_ACCEPT,
    ADAPTER_DRYRUN_REJECT,
    TARGET_AUTONOMOUS_TASK,
    TARGET_FOUNDUP_JOB,
)
from modules.communication.moltbot_bridge.src.reddog_openclaw_work_order_policy_gate import (
    POLICY_ACCEPT,
    POLICY_REJECT,
    SIGNATURE_GATE_ACCEPTED,
    SIGNATURE_GATE_REJECTED,
)
from modules.communication.moltbot_bridge.src.reddog_signed_receipt_chain import (
    SIGNED_RECEIPT_CHAIN_ACCEPT,
    SIGNED_RECEIPT_CHAIN_REJECT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_execution_valve import (
    VALVE_CLOSED,
    VALVE_OPEN_DRYRUN_ONLY,
    VALVE_OPEN_LIVE_ENQUEUE,
    VALVE_OPEN_WORKTREE_CREATE,
)


class _FakeWriter:
    def __init__(self, ok=True) -> None:
        self.ok = ok
        self.calls = []

    def enqueue_foundup_job(self, intake, receipt):
        self.calls.append(("foundup_job", dict(intake), dict(receipt)))
        if not self.ok:
            return {"ok": False}
        return {"ok": True, "openclaw_queue_item_id": intake["proposed_job_id"], "agentdb_task_id": None}

    def enqueue_autonomous_task(self, intake, receipt):
        self.calls.append(("autonomous_task", dict(intake), dict(receipt)))
        if not self.ok:
            return {"ok": False}
        return {"ok": True, "openclaw_queue_item_id": None, "agentdb_task_id": intake["proposed_task_id"]}


def _intake(target_type=TARGET_FOUNDUP_JOB):
    return {
        "target_type": target_type,
        "proposed_job_id": "reddog-fj-1234" if target_type == TARGET_FOUNDUP_JOB else None,
        "proposed_task_id": "reddog-wo-1234" if target_type == TARGET_AUTONOMOUS_TASK else None,
        "work_order_id": "wo-live-enqueue-001",
        "operation": "feature_slice",
        "requested_action": "build_foundup" if target_type == TARGET_FOUNDUP_JOB else None,
        "repo_scope": "FOUNDUPS/Foundups-Agent",
        "allowed_paths": ["modules/communication/moltbot_bridge/**"],
        "denied_paths": [".env"],
        "required_tests": ["modules/communication/moltbot_bridge/tests/test_reddog_openclaw_live_enqueue.py"],
        "evidence_refs": ["policy_gate:sha256:policy"],
        "policy_receipt_digest": "sha256:policy",
        "work_order_receipt_digest": "sha256:work-order",
        "invocation_receipt_digest": "sha256:invocation",
        "executor_plan_id": "plan-live-enqueue",
        "valve_decision_digest": "sha256:dryrun-valve",
        "no_enqueue_performed": True,
        "no_execution_performed": True,
    }


def _adapter(target_type=TARGET_FOUNDUP_JOB, decision=ADAPTER_DRYRUN_ACCEPT):
    return {
        "decision": decision,
        "work_order_id": "wo-live-enqueue-001",
        "proposed_intake": _intake(target_type) if decision == ADAPTER_DRYRUN_ACCEPT else None,
        "adapter_receipt": {
            "adapter_receipt_id": "adapter-dryrun-001",
            "adapter_receipt_digest": "sha256:adapter",
            "decision": decision,
            "rejection_reasons": [],
            "target_type": target_type,
            "work_order_id": "wo-live-enqueue-001",
            "created_at": "2026-07-11T00:00:00+00:00",
        },
        "rejection_reasons": [],
        "no_enqueue_performed": True,
        "no_execution_performed": True,
    }


def _policy(decision=POLICY_ACCEPT, signature_status=SIGNATURE_GATE_ACCEPTED):
    return {
        "decision": decision,
        "receipt_digest": "sha256:policy",
        "signature_gate_status": signature_status,
        "signature_gate_digest": "sha256:signed-authority",
        "no_execution_performed": True,
        "work_order_id": "wo-live-enqueue-001",
    }


def _chain(decision=SIGNED_RECEIPT_CHAIN_ACCEPT, accepted=True):
    return {
        "decision": decision,
        "accepted": accepted,
        "verified_count": 1 if accepted else 0,
        "terminal_receipt_hash": "sha256:terminal-receipt" if accepted else None,
        "no_reward_settlement_performed": True,
        "no_execution_performed": True,
    }


def _valve(state=VALVE_OPEN_LIVE_ENQUEUE):
    return {
        "valve_state": state,
        "work_order_id": "wo-live-enqueue-001",
        "rejection_reasons": [],
        "gates_checked": ["execution_valve_evaluator"],
        "no_execution_performed": True,
        "decision_digest": "sha256:live-enqueue-valve",
        "intake_target": TARGET_FOUNDUP_JOB,
    }


def test_live_enqueue_foundup_job_calls_injected_writer_only():
    writer = _FakeWriter()
    result = perform_reddog_openclaw_live_enqueue(
        _adapter(),
        _policy(),
        _chain(),
        _valve(),
        writer=writer,
        seen_live_enqueue_keys=set(),
        now=datetime(2026, 7, 11, tzinfo=timezone.utc),
        admission_consumer=lambda: True,
    )

    assert result.decision == LIVE_ENQUEUE_ACCEPT
    assert result.live_enqueue_performed is True
    assert result.no_execution_performed is True
    assert result.no_reward_settlement_performed is True
    assert result.receipt is not None
    assert result.receipt.openclaw_queue_item_id == "reddog-fj-1234"
    assert result.receipt.agentdb_task_id is None
    assert writer.calls[0][0] == "foundup_job"


def test_live_enqueue_autonomous_task_calls_task_writer():
    writer = _FakeWriter()
    result = perform_reddog_openclaw_live_enqueue(
        _adapter(TARGET_AUTONOMOUS_TASK),
        _policy(),
        _chain(),
        _valve(),
        writer=writer,
        admission_consumer=lambda: True,
    )

    assert result.decision == LIVE_ENQUEUE_ACCEPT
    assert result.target_type == TARGET_AUTONOMOUS_TASK
    assert result.receipt is not None
    assert result.receipt.agentdb_task_id == "reddog-wo-1234"
    assert writer.calls[0][0] == "autonomous_task"


def test_rejects_dryrun_valve_before_writer_call():
    writer = _FakeWriter()
    result = perform_reddog_openclaw_live_enqueue(
        _adapter(), _policy(), _chain(), _valve(VALVE_OPEN_DRYRUN_ONLY), writer=writer
    )

    assert result.decision == LIVE_ENQUEUE_REJECT
    assert LiveEnqueueReason.VALVE_NOT_OPEN in result.rejection_reasons
    assert writer.calls == []


def test_rejects_worktree_valve_as_wrong_authority():
    writer = _FakeWriter()
    result = perform_reddog_openclaw_live_enqueue(
        _adapter(), _policy(), _chain(), _valve(VALVE_OPEN_WORKTREE_CREATE), writer=writer
    )

    assert result.decision == LIVE_ENQUEUE_REJECT
    assert result.rejection_reasons == [LiveEnqueueReason.VALVE_NOT_OPEN]
    assert writer.calls == []


def test_rejects_closed_valve():
    result = perform_reddog_openclaw_live_enqueue(
        _adapter(), _policy(), _chain(), _valve(VALVE_CLOSED), writer=_FakeWriter()
    )

    assert result.decision == LIVE_ENQUEUE_REJECT
    assert LiveEnqueueReason.VALVE_NOT_OPEN in result.rejection_reasons


def test_rejects_missing_signed_authority():
    result = perform_reddog_openclaw_live_enqueue(
        _adapter(), _policy(signature_status=SIGNATURE_GATE_REJECTED), _chain(), _valve(), writer=_FakeWriter()
    )

    assert result.decision == LIVE_ENQUEUE_REJECT
    assert LiveEnqueueReason.SIGNATURE_GATE_NOT_ACCEPTED in result.rejection_reasons


def test_rejects_rejected_policy():
    result = perform_reddog_openclaw_live_enqueue(
        _adapter(), _policy(decision=POLICY_REJECT), _chain(), _valve(), writer=_FakeWriter()
    )

    assert result.decision == LIVE_ENQUEUE_REJECT
    assert LiveEnqueueReason.POLICY_NOT_ACCEPTED in result.rejection_reasons


def test_rejects_unsigned_or_rejected_receipt_chain():
    result = perform_reddog_openclaw_live_enqueue(
        _adapter(), _policy(), _chain(SIGNED_RECEIPT_CHAIN_REJECT, accepted=False), _valve(), writer=_FakeWriter()
    )

    assert result.decision == LIVE_ENQUEUE_REJECT
    assert LiveEnqueueReason.RECEIPT_CHAIN_NOT_ACCEPTED in result.rejection_reasons


def test_rejects_adapter_rejection_and_missing_intake():
    result = perform_reddog_openclaw_live_enqueue(
        _adapter(decision=ADAPTER_DRYRUN_REJECT), _policy(), _chain(), _valve(), writer=_FakeWriter()
    )

    assert result.decision == LIVE_ENQUEUE_REJECT
    assert LiveEnqueueReason.ADAPTER_NOT_ACCEPTED in result.rejection_reasons
    assert LiveEnqueueReason.MISSING_PROPOSED_INTAKE in result.rejection_reasons


def test_rejects_replay_before_second_writer_call():
    writer = _FakeWriter()
    seen = set()
    first = perform_reddog_openclaw_live_enqueue(_adapter(), _policy(), _chain(), _valve(), writer=writer, seen_live_enqueue_keys=seen, admission_consumer=lambda: True)
    second = perform_reddog_openclaw_live_enqueue(_adapter(), _policy(), _chain(), _valve(), writer=writer, seen_live_enqueue_keys=seen, admission_consumer=lambda: True)

    assert first.decision == LIVE_ENQUEUE_ACCEPT
    assert second.decision == LIVE_ENQUEUE_REJECT
    assert LiveEnqueueReason.IDEMPOTENCY_REPLAY in second.rejection_reasons
    assert len(writer.calls) == 1


def test_rejects_writer_missing_or_writer_rejected():
    missing = perform_reddog_openclaw_live_enqueue(_adapter(), _policy(), _chain(), _valve(), writer=None)
    rejected = perform_reddog_openclaw_live_enqueue(_adapter(), _policy(), _chain(), _valve(), writer=_FakeWriter(ok=False), admission_consumer=lambda: True)

    assert missing.decision == LIVE_ENQUEUE_REJECT
    assert LiveEnqueueReason.WRITER_MISSING in missing.rejection_reasons
    assert rejected.decision == LIVE_ENQUEUE_REJECT
    assert rejected.rejection_reasons == [LiveEnqueueReason.WRITER_REJECTED]


def test_ast_boundary_no_direct_execution_or_queue_imports():
    path = Path("modules/communication/moltbot_bridge/src/reddog_openclaw_live_enqueue.py")
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

    forbidden_import_fragments = (
        "subprocess",
        "socket",
        "agent_db",
        "openclaw_foundup_orchestrator",
        "hermes",
        "wre_core",
        "skillz",
        "github",
    )
    forbidden_calls = {"open", "eval", "exec", "system", "popen", "run", "check_call", "check_output"}
    assert not any(fragment in imported for imported in imports for fragment in forbidden_import_fragments)
    assert not (calls & forbidden_calls)
