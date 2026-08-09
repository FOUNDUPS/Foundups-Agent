"""Tests for REDDOG_OPENCLAW_HERMES_0102_WORKER_DISPATCH_RUNTIME_PHASE1."""

from __future__ import annotations

import ast
import hashlib
import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src import (
    reddog_openclaw_hermes_0102_worker_dispatch_runtime as runtime,
)
from modules.communication.moltbot_bridge.src import (
    reddog_signed_worker_dispatch_runtime_validation as runtime_validation,
)
from modules.communication.moltbot_bridge.src import (
    reddog_signed_worker_dispatch_agentdb_writer as writer_module,
)
from modules.communication.moltbot_bridge.src.reddog_architect_fix_publication_effect_binding import (
    committed_publication_effect_binding,
)
from modules.communication.moltbot_bridge.src.reddog_signed_authority_worker_dispatch_dryrun import (
    SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_worker_dispatch_authority_binding import (
    recorded_authority_verification_binding,
)
from modules.communication.moltbot_bridge.src.reddog_wsp15_allocation_receipt import (
    allocate_reddog_wsp15_receipt,
)
from modules.communication.moltbot_bridge.src.reddog_progressive_execution_stage_policy import (
    admit_bounded_execution,
)
from modules.infrastructure.database.src.agent_db import AgentDB
from modules.infrastructure.database.src.db_manager import DatabaseManager
from modules.communication.moltbot_bridge.tests.reddog_resident_queue_test_helpers import (
    governed_worker_dispatch_snapshot,
    worker_dispatch_authority_verification_context,
    worker_dispatch_authority_stages,
    with_architect_fix_publication,
)
from modules.communication.moltbot_bridge.tests.model_runtime_binding_queue_test_helpers import (
    runtime_binding_refs as _runtime_binding_refs,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_openclaw_hermes_0102_worker_dispatch_runtime.py"
)
RUNTIME_MODULE_PATHS = (
    MODULE_PATH,
    MODULE_PATH.with_name("reddog_signed_worker_dispatch_runtime_types.py"),
    MODULE_PATH.with_name("reddog_signed_worker_dispatch_runtime_validation.py"),
    MODULE_PATH.with_name("reddog_signed_worker_dispatch_task_builder.py"),
    MODULE_PATH.with_name("reddog_signed_worker_dispatch_agentdb_writer.py"),
    MODULE_PATH.with_name("reddog_signed_worker_publication_admission.py"),
)
MEMEX_SUPPLY_ID = "sha256:memex-supply"
MEMEX_SUPPLY_DIGEST = "sha256:" + ("7" * 64)


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

    def enqueue_signed_worker_dispatch_tasks(self, tasks, receipt):
        self.calls.append((list(tasks), receipt))
        if not self.ok:
            return {"ok": False, "reason": "writer_rejected", "created_task_ids": []}
        created = self.created_override
        if created is None:
            created = [task.task_id for task in tasks]
        return {"ok": True, "created_task_ids": created}

    def recover_signed_worker_dispatch_tasks(self, tasks, receipt):
        return self.enqueue_signed_worker_dispatch_tasks(tasks, receipt)

    def recover_applied_signed_worker_dispatch_tasks(self, tasks, receipt):
        return {"ok": False, "reason": "already_applied", "created_task_ids": []}

    def activate_signed_worker_dispatch_tasks(self, tasks, receipt):
        return {
            "ok": self.ok,
            "created_task_ids": [task.task_id for task in tasks] if self.ok else [],
        }


class _FailBeforeInsertAgentDbWriter(
    runtime.AgentDbSignedWorkerDispatchTaskWriter
):
    def enqueue_signed_worker_dispatch_tasks(self, tasks, receipt):
        return {
            "ok": False,
            "reason": "simulated_pre_insert_failure",
            "created_task_ids": [],
        }


def _digest(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _allocation(**overrides):
    payload = allocate_reddog_wsp15_receipt(
        requested_operation="bounded_code_change",
        prompt_text="Fix one urgent authority-bound FoundUp module defect.",
        changed_paths=("modules/foundups/paccess_001/src/worker.py",),
        allowed_read_targets=("modules/foundups/paccess_001/src/worker.py",),
    ).to_dict()
    payload.update(overrides)
    return payload


def _authority_stages(
    allocation=None,
    *,
    work_state_snapshot=None,
    queue_item_id="queue-1",
    **work_authority_overrides,
):
    allocation = allocation or _allocation()
    return worker_dispatch_authority_stages(
        allocation,
        work_state_snapshot=work_state_snapshot,
        queue_item_id=queue_item_id,
        wsp15_priority=allocation["priority"],
        wsp15_mps_total=allocation["mps_total"],
        wsp15_reasoning_tier=allocation["reasoning_tier"],
        **work_authority_overrides,
    )


def _authority_refs(allocation=None):
    allocation = allocation or _allocation()
    _, verification = _authority_stages(
        allocation,
        work_state_snapshot=_snapshot(allocation),
    )
    return {
        key: verification[key]
        for key in (
            "verified_work_authority_digest",
            "authority_verification_receipt_id",
            "authority_verification_receipt_digest",
        )
    }


def _stage_refs(allocation):
    stage = admit_bounded_execution(
        determination_action="FIX",
        allocation=allocation,
        selected_slice="REDDOG_NEXT_OPERATIONAL_SLICE_PHASE1",
        requested_operation=str(allocation["requested_operation"]),
        changed_paths=tuple(allocation["changed_paths"]),
    )
    return {
        "progressive_policy_stage_receipt_id": stage.receipt_id,
        "progressive_policy_stage_digest": _digest(stage.to_dict()),
    }


def _intent(role: str, runtime_name: str, capability: str, allocation=None, **overrides):
    allocation = allocation or _allocation()
    payload = {
        "intent_id": f"worker_dispatch_intent_{role}",
        "role": role,
        "worker_runtime": runtime_name,
        "capability": capability,
        "work_order_id": "wo-1",
        "foundup_id": "paccess_001",
        "requested_operation": str(allocation["requested_operation"]),
        "wsp15_allocation_receipt_id": allocation["receipt_id"],
        "wsp15_allocation_digest": _digest(allocation),
        **_stage_refs(allocation),
        "model_runtime_binding_receipt_id": "",
        "model_runtime_binding_digest": "",
        "model_runtime_binding_verification_receipt_id": "",
        "model_runtime_binding_verification_digest": "",
        "memex_supply_receipt_id": MEMEX_SUPPLY_ID,
        "memex_supply_digest": MEMEX_SUPPLY_DIGEST,
        "architect_fix_publication_receipt_id": "",
        "architect_fix_publication_binding_digest": "",
        **_authority_refs(allocation),
        "dry_run_only": True,
        "no_worker_spawn_performed": True,
        "no_openclaw_enqueue_performed": True,
        "no_hermes_dispatch_performed": True,
    }
    payload.update(overrides)
    return payload


def _dryrun_result(allocation=None, intents=None, **overrides):
    allocation = allocation or _allocation()
    intents = intents or (
        _intent("coding_worker_1", "0102", "bounded_code_change", allocation),
        _intent(
            "independent_slice_verifier",
            "openclaw",
            "independent_slice_verification",
            allocation,
        ),
        _intent("queue_stage_worker", "openclaw", "queue_stage_progress", allocation),
    )
    receipt = {
        "receipt_id": "signed_authority_worker_dispatch_abc",
        "work_order_id": "wo-1",
        "foundup_id": "paccess_001",
        "requested_operation": str(allocation["requested_operation"]),
        "wsp15_allocation_receipt_id": allocation["receipt_id"],
        "wsp15_allocation_digest": _digest(allocation),
        "wsp15_priority": allocation["priority"],
        "wsp15_mps_total": allocation["mps_total"],
        "wsp15_reasoning_tier": allocation["reasoning_tier"],
        **_stage_refs(allocation),
        "model_runtime_binding_receipt_id": "",
        "model_runtime_binding_digest": "",
        "model_runtime_binding_verification_receipt_id": "",
        "model_runtime_binding_verification_digest": "",
        "memex_supply_receipt_id": MEMEX_SUPPLY_ID,
        "memex_supply_digest": MEMEX_SUPPLY_DIGEST,
        "architect_fix_publication_receipt_id": "",
        "architect_fix_publication_binding_digest": "",
        **_authority_refs(allocation),
        "dispatch_intent_count": len(intents),
        "dispatch_intents": list(intents),
        "no_worker_spawn_performed": True,
        "no_queue_mutation_performed": True,
        "no_worktree_created": True,
        "no_shell_command_executed": True,
        "no_openclaw_enqueue_performed": True,
        "no_hermes_dispatch_performed": True,
        "no_repo_mutation_performed": True,
        "no_holoindex_reindex_performed": True,
        "no_pr_created": True,
        "no_reward_settlement_performed": True,
    }
    payload = {
        "accepted": True,
        "decision": SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_ACCEPT,
        "rejection_reasons": [],
        "receipt": receipt,
    }
    payload.update(overrides)
    return payload


def _publish(**kwargs):
    snapshot = kwargs.get("work_state_snapshot", {})
    queue_items = snapshot.get("wre_queue_items", [])
    allocation = (
        queue_items[0].get("wsp15_allocation_receipt")
        if queue_items
        else _allocation()
    )
    authority_runtime, authority_verification = _authority_stages(
        allocation,
        work_state_snapshot=snapshot,
        queue_item_id=str(kwargs.get("queue_item_id") or "queue-1"),
    )
    kwargs.setdefault("queue_authority_runtime_result", authority_runtime)
    kwargs.setdefault(
        "queue_authority_verification_result",
        authority_verification,
    )
    kwargs.setdefault(
        "authority_verification_context",
        worker_dispatch_authority_verification_context(),
    )
    return runtime.publish_reddog_signed_worker_dispatch_runtime(**kwargs)


def _memex_refs():
    return {
        "memex_supply_receipt_id": MEMEX_SUPPLY_ID,
        "memex_supply_digest": MEMEX_SUPPLY_DIGEST,
    }


def _snapshot(allocation=None, **queue_overrides):
    allocation = allocation or _allocation()
    queue_item = {
        "queue_item_id": "queue-1",
        "slice_id": "REDDOG_NEXT_OPERATIONAL_SLICE_PHASE1",
        "status": "QUEUED",
        "wsp15_allocation_receipt": allocation,
        **_memex_refs(),
    }
    queue_item.update(queue_overrides)
    return governed_worker_dispatch_snapshot({
        "schema_version": "reddog_authoritative_work_state.v1",
        "wre_queue_items": [queue_item],
    })


def test_publishes_signed_worker_dispatch_intents_as_pending_tasks() -> None:
    writer = _FakeWriter()

    result = _publish(
        worker_dispatch_dryrun_result=_dryrun_result(),
        work_state_snapshot=_snapshot(),
        queue_item_id="queue-1",
        writer=writer,
        now=datetime(2026, 7, 16, tzinfo=timezone.utc),
    )

    assert result.accepted is True
    assert result.decision == runtime.SIGNED_AUTHORITY_WORKER_DISPATCH_RUNTIME_ACCEPT
    assert result.receipt is not None
    assert result.receipt.agentdb_tasks_enqueued is True
    assert result.receipt.no_worker_process_started is True
    assert result.receipt.no_hermes_execution_performed is True
    assert len(result.tasks) == 3
    assert writer.calls and len(writer.calls[0][0]) == 3
    assert {task.context["worker_runtime"] for task in result.tasks} == {"0102", "openclaw"}
    assert all(task.context["execution_allowed_by_dispatch_runtime"] is False for task in result.tasks)
    assert all(runtime.SIGNED_WORKER_DISPATCH_TASK_SKILL in task.required_skills for task in result.tasks)
    for task in result.tasks:
        assert task.context["authorized_principal_id"] == "github:mjtrout"
        assert task.context["authorized_reddog_id"] == "reddog:worker-dispatch"
        assert task.context["memex_supply_receipt_id"] == MEMEX_SUPPLY_ID
        assert task.context["memex_supply_digest"] == MEMEX_SUPPLY_DIGEST
        envelope = task.context["signed_worker_agentdb_envelope"]
        assert (
            envelope["signed_authority_worker_dispatch_receipt"][
                "memex_supply_receipt_id"
            ]
            == MEMEX_SUPPLY_ID
        )
        assert (
            envelope["queue_authority_runtime_result"]["authority_result"][
                "work_authority"
            ]["memex_supply_digest"]
            == MEMEX_SUPPLY_DIGEST
        )
        assert "principal_id" not in task.context["signed_authority_worker_dispatch_receipt"]
        assert "principal_id" not in task.context["worker_dispatch_intent"]


@pytest.mark.parametrize(
    ("extra_field", "extra_value"),
    (
        ("principal_id", "attacker-principal"),
        ("note", "attacker-data"),
    ),
)
def test_rejects_recomputed_dispatch_with_extra_fields_before_nonce_consumption(
    extra_field: str,
    extra_value: str,
) -> None:
    allocation = _allocation()
    context = worker_dispatch_authority_verification_context()
    injected = _dryrun_result(allocation)
    receipt = dict(injected["receipt"])
    receipt[extra_field] = extra_value
    receipt["dispatch_intents"] = [
        {**dict(intent), extra_field: extra_value}
        for intent in receipt["dispatch_intents"]
    ]
    receipt["receipt_id"] = (
        "signed_authority_worker_dispatch_" + _digest(receipt)[7:23]
    )
    injected["receipt"] = receipt
    writer = _FakeWriter()

    rejected = _publish(
        worker_dispatch_dryrun_result=injected,
        authority_verification_context=context,
        work_state_snapshot=_snapshot(allocation),
        queue_item_id="queue-1",
        writer=writer,
    )
    accepted = _publish(
        worker_dispatch_dryrun_result=_dryrun_result(allocation),
        authority_verification_context=context,
        work_state_snapshot=_snapshot(allocation),
        queue_item_id="queue-1",
        writer=_FakeWriter(),
    )

    assert rejected.accepted is False
    assert (
        runtime.WorkerDispatchRuntimeReason.DISPATCH_SCHEMA_MISMATCH
        in rejected.rejection_reasons
    )
    assert writer.calls == []
    assert accepted.accepted is True


def test_rejects_synthetic_dryrun_without_recorded_authority_stages() -> None:
    writer = _FakeWriter()

    result = runtime.publish_reddog_signed_worker_dispatch_runtime(
        worker_dispatch_dryrun_result=_dryrun_result(),
        queue_authority_runtime_result={},
        queue_authority_verification_result={},
        authority_verification_context=worker_dispatch_authority_verification_context(),
        work_state_snapshot=_snapshot(),
        queue_item_id="queue-1",
        writer=writer,
    )

    assert result.accepted is False
    assert (
        runtime.WorkerDispatchRuntimeReason.AUTHORITY_VERIFICATION_BINDING_MISMATCH
        in result.rejection_reasons
    )
    assert writer.calls == []


def test_rejects_authority_substitution_after_verification_before_writer() -> None:
    allocation = _allocation()
    authority_runtime, authority_verification = _authority_stages(allocation)
    substituted = dict(
        authority_runtime["authority_result"]["work_authority"]
    )
    substituted["requested_operation"] = "attacker_operation"
    authority_runtime["authority_result"]["work_authority"] = substituted
    authority_runtime["authority_result"]["receipt"]["work_authority_digest"] = (
        _digest(substituted)
    )
    writer = _FakeWriter()

    result = runtime.publish_reddog_signed_worker_dispatch_runtime(
        worker_dispatch_dryrun_result=_dryrun_result(allocation),
        queue_authority_runtime_result=authority_runtime,
        queue_authority_verification_result=authority_verification,
        authority_verification_context=worker_dispatch_authority_verification_context(),
        work_state_snapshot=_snapshot(allocation),
        queue_item_id="queue-1",
        writer=writer,
    )

    assert result.accepted is False
    assert (
        runtime.WorkerDispatchRuntimeReason.AUTHORITY_VERIFICATION_BINDING_MISMATCH
        in result.rejection_reasons
    )
    assert writer.calls == []


def test_rejects_forged_authority_after_attacker_recomputes_all_local_receipts() -> None:
    allocation = _allocation()
    authority_runtime, authority_verification = _authority_stages(allocation)
    forged = dict(authority_runtime["authority_result"]["work_authority"])
    forged["allowed_paths"] = [
        "modules/foundups/paccess_001/attacker_selected/**"
    ]
    forged["signature"] = "attacker-forged-signature"
    forged_digest = _digest(forged)
    authority_runtime["authority_result"]["work_authority"] = forged
    authority_runtime["authority_result"]["receipt"]["work_authority_digest"] = (
        forged_digest
    )
    authority_verification["verified_work_authority_digest"] = forged_digest
    forged_binding = recorded_authority_verification_binding(
        authority_runtime,
        authority_verification,
    )
    authority_verification.update(forged_binding)
    dryrun = _dryrun_result(allocation)
    receipt = dict(dryrun["receipt"])
    receipt.update(forged_binding)
    receipt["dispatch_intents"] = [
        {**dict(intent), **forged_binding}
        for intent in receipt["dispatch_intents"]
    ]
    dryrun["receipt"] = receipt
    writer = _FakeWriter()

    result = runtime.publish_reddog_signed_worker_dispatch_runtime(
        worker_dispatch_dryrun_result=dryrun,
        queue_authority_runtime_result=authority_runtime,
        queue_authority_verification_result=authority_verification,
        authority_verification_context=worker_dispatch_authority_verification_context(),
        work_state_snapshot=_snapshot(allocation),
        queue_item_id="queue-1",
        writer=writer,
    )

    assert result.accepted is False
    assert (
        runtime.WorkerDispatchRuntimeReason.AUTHORITY_VERIFICATION_BINDING_MISMATCH
        in result.rejection_reasons
    )
    assert writer.calls == []


def test_rejects_operation_substitution_with_recomputed_local_receipts() -> None:
    allocation = _allocation()
    dryrun = _dryrun_result(allocation)
    receipt = dict(dryrun["receipt"])
    receipt["requested_operation"] = "attacker_operation"
    receipt["dispatch_intents"] = [
        {
            **dict(intent),
            "intent_id": "worker_dispatch_intent_" + _digest(intent)[7:23],
            "requested_operation": "attacker_operation",
        }
        for intent in receipt["dispatch_intents"]
    ]
    receipt["receipt_id"] = "signed_authority_worker_dispatch_" + _digest(receipt)[7:23]
    dryrun["receipt"] = receipt
    writer = _FakeWriter()

    result = _publish(
        worker_dispatch_dryrun_result=dryrun,
        work_state_snapshot=_snapshot(allocation),
        queue_item_id="queue-1",
        writer=writer,
    )

    assert result.accepted is False
    assert (
        runtime.WorkerDispatchRuntimeReason.AUTHORITY_VERIFICATION_BINDING_MISMATCH
        in result.rejection_reasons
    )
    assert writer.calls == []


def test_rejects_work_state_change_after_queue_authority_was_signed() -> None:
    allocation = _allocation()
    original_snapshot = _snapshot(allocation)
    authority_runtime, authority_verification = _authority_stages(
        allocation,
        work_state_snapshot=original_snapshot,
    )
    changed_snapshot = json.loads(json.dumps(original_snapshot))
    changed_snapshot["attacker_selected_state"] = "forged-after-signing"
    writer = _FakeWriter()

    result = runtime.publish_reddog_signed_worker_dispatch_runtime(
        worker_dispatch_dryrun_result=_dryrun_result(allocation),
        queue_authority_runtime_result=authority_runtime,
        queue_authority_verification_result=authority_verification,
        authority_verification_context=worker_dispatch_authority_verification_context(),
        work_state_snapshot=changed_snapshot,
        queue_item_id="queue-1",
        writer=writer,
    )

    assert result.accepted is False
    assert (
        runtime.WorkerDispatchRuntimeReason.WORK_ORDER_BINDING_MISMATCH
        in result.rejection_reasons
    )
    assert writer.calls == []


def test_rejects_worker_role_substitution_against_authoritative_plan() -> None:
    allocation = _allocation()
    dryrun = _dryrun_result(allocation)
    receipt = dict(dryrun["receipt"])
    intents = [dict(intent) for intent in receipt["dispatch_intents"]]
    intents[0].update(
        {
            "intent_id": "worker_dispatch_intent_attacker",
            "role": "attacker_worker",
            "worker_runtime": "hermes",
            "capability": "attacker_capability",
        }
    )
    receipt["dispatch_intents"] = intents
    receipt["receipt_id"] = "signed_authority_worker_dispatch_" + _digest(receipt)[7:23]
    dryrun["receipt"] = receipt
    writer = _FakeWriter()

    result = _publish(
        worker_dispatch_dryrun_result=dryrun,
        work_state_snapshot=_snapshot(allocation),
        queue_item_id="queue-1",
        writer=writer,
    )

    assert result.accepted is False
    assert (
        runtime.WorkerDispatchRuntimeReason.WORKER_PLAN_BINDING_MISMATCH
        in result.rejection_reasons
    )
    assert writer.calls == []


def test_static_rejection_does_not_consume_authority_nonce() -> None:
    allocation = _allocation()
    context = worker_dispatch_authority_verification_context()
    invalid = _dryrun_result(allocation)
    invalid["receipt"]["dispatch_intent_count"] = 99

    rejected = _publish(
        worker_dispatch_dryrun_result=invalid,
        authority_verification_context=context,
        work_state_snapshot=_snapshot(allocation),
        queue_item_id="queue-1",
        writer=_FakeWriter(),
    )
    accepted = _publish(
        worker_dispatch_dryrun_result=_dryrun_result(allocation),
        authority_verification_context=context,
        work_state_snapshot=_snapshot(allocation),
        queue_item_id="queue-1",
        writer=_FakeWriter(),
    )

    assert rejected.accepted is False
    assert accepted.accepted is True


def test_authority_nonce_is_single_use_at_agentdb_admission() -> None:
    allocation = _allocation()
    context = worker_dispatch_authority_verification_context()
    first_writer = _FakeWriter()
    replay_writer = _FakeWriter()

    first = _publish(
        worker_dispatch_dryrun_result=_dryrun_result(allocation),
        authority_verification_context=context,
        work_state_snapshot=_snapshot(allocation),
        queue_item_id="queue-1",
        writer=first_writer,
    )
    replay = _publish(
        worker_dispatch_dryrun_result=_dryrun_result(allocation),
        authority_verification_context=context,
        work_state_snapshot=_snapshot(allocation),
        queue_item_id="queue-1",
        writer=replay_writer,
    )

    assert first.accepted is True
    assert replay.accepted is False
    assert replay_writer.calls == []


def test_writer_failure_allows_only_exact_publication_retry() -> None:
    allocation = _allocation()
    context = worker_dispatch_authority_verification_context()
    rejected = _publish(
        worker_dispatch_dryrun_result=_dryrun_result(allocation),
        authority_verification_context=context,
        work_state_snapshot=_snapshot(allocation),
        queue_item_id="queue-1",
        writer=_FakeWriter(ok=False),
    )
    retry_writer = _FakeWriter()
    retry = _publish(
        worker_dispatch_dryrun_result=_dryrun_result(allocation),
        authority_verification_context=context,
        work_state_snapshot=_snapshot(allocation),
        queue_item_id="queue-1",
        writer=retry_writer,
    )

    assert runtime.WorkerDispatchRuntimeReason.WRITER_REJECTED in rejected.rejection_reasons
    assert retry.accepted is True
    assert len(retry_writer.calls) == 1


def test_production_writer_recovers_zero_row_authorized_batch() -> None:
    allocation = _allocation()
    context = worker_dispatch_authority_verification_context()
    dryrun = _dryrun_result(allocation)
    rejected = _publish(
        worker_dispatch_dryrun_result=dryrun,
        authority_verification_context=context,
        work_state_snapshot=_snapshot(allocation),
        queue_item_id="queue-1",
        writer=_FailBeforeInsertAgentDbWriter(),
    )
    assert AgentDB().get_autonomous_tasks(status="pending", limit=20) == []
    recovered = _publish(
        worker_dispatch_dryrun_result=dryrun,
        authority_verification_context=context,
        work_state_snapshot=_snapshot(allocation),
        queue_item_id="queue-1",
        writer=runtime.AgentDbSignedWorkerDispatchTaskWriter(),
    )

    assert rejected.accepted is False
    assert recovered.accepted is True, recovered.rejection_reasons
    assert len(AgentDB().get_autonomous_tasks(status="pending", limit=20)) == 3


def test_production_writer_rejects_partial_authorized_batch() -> None:
    allocation = _allocation()
    context = worker_dispatch_authority_verification_context()
    dryrun = _dryrun_result(allocation)
    capture = _FakeWriter(ok=False)
    rejected = _publish(
        worker_dispatch_dryrun_result=dryrun,
        authority_verification_context=context,
        work_state_snapshot=_snapshot(allocation),
        queue_item_id="queue-1",
        writer=capture,
    )
    tasks, _receipt = capture.calls[0]
    db = AgentDB()
    with db.db.get_connection() as connection:
        writer_module._insert_tasks(connection, tasks[:1])
    recovered = _publish(
        worker_dispatch_dryrun_result=dryrun,
        authority_verification_context=context,
        work_state_snapshot=_snapshot(allocation),
        queue_item_id="queue-1",
        writer=runtime.AgentDbSignedWorkerDispatchTaskWriter(),
    )

    assert rejected.accepted is False
    assert recovered.accepted is False
    assert AgentDB().get_autonomous_tasks(status="pending", limit=20) == []
    assert len(
        AgentDB().get_autonomous_tasks(status="publication_held", limit=20)
    ) == 1


def test_writer_failure_rejects_altered_publication_retry() -> None:
    allocation = _allocation()
    context = worker_dispatch_authority_verification_context()
    original = _dryrun_result(allocation)
    rejected = _publish(
        worker_dispatch_dryrun_result=original,
        authority_verification_context=context,
        work_state_snapshot=_snapshot(allocation),
        queue_item_id="queue-1",
        writer=_FakeWriter(ok=False),
    )
    altered = json.loads(json.dumps(original))
    altered["receipt"]["receipt_id"] = "signed_authority_worker_dispatch_altered"
    retry_writer = _FakeWriter()
    retry = _publish(
        worker_dispatch_dryrun_result=altered,
        authority_verification_context=context,
        work_state_snapshot=_snapshot(allocation),
        queue_item_id="queue-1",
        writer=retry_writer,
    )

    assert runtime.WorkerDispatchRuntimeReason.WRITER_REJECTED in (
        rejected.rejection_reasons
    )
    assert retry.accepted is False
    assert retry_writer.calls == []


def test_agentdb_publication_recovers_after_post_write_crash(
    monkeypatch,
) -> None:
    allocation = _allocation()
    context = worker_dispatch_authority_verification_context()
    dryrun = _dryrun_result(allocation)
    writer = runtime.AgentDbSignedWorkerDispatchTaskWriter()
    complete = runtime.complete_signed_worker_publication
    monkeypatch.setattr(
        runtime,
        "complete_signed_worker_publication",
        lambda *_args, **_kwargs: False,
    )
    interrupted = _publish(
        worker_dispatch_dryrun_result=dryrun,
        authority_verification_context=context,
        work_state_snapshot=_snapshot(allocation),
        queue_item_id="queue-1",
        writer=writer,
    )
    assert AgentDB().get_autonomous_tasks(status="pending", limit=20) == []
    assert len(
        AgentDB().get_autonomous_tasks(status="publication_held", limit=20)
    ) == 3
    held = AgentDB().get_autonomous_tasks(status="publication_held", limit=20)
    assert all(
        AgentDB().assign_autonomous_task(
            task["task_id"], "openclaw_supervisor"
        )
        is False
        for task in held
    )
    monkeypatch.setattr(runtime, "complete_signed_worker_publication", complete)
    recovered = _publish(
        worker_dispatch_dryrun_result=dryrun,
        authority_verification_context=context,
        work_state_snapshot=_snapshot(allocation),
        queue_item_id="queue-1",
        writer=writer,
    )

    assert interrupted.accepted is False
    assert recovered.accepted is True, recovered.rejection_reasons
    assert len(AgentDB().get_autonomous_tasks(status="pending", limit=20)) == 3


def test_agentdb_publication_recovers_after_post_applied_crash(
    monkeypatch,
) -> None:
    allocation = _allocation()
    context = worker_dispatch_authority_verification_context()
    dryrun = _dryrun_result(allocation)
    writer = runtime.AgentDbSignedWorkerDispatchTaskWriter()
    activate = runtime._writer_activates
    monkeypatch.setattr(runtime, "_writer_activates", lambda *_args: False)
    interrupted = _publish(
        worker_dispatch_dryrun_result=dryrun,
        authority_verification_context=context,
        work_state_snapshot=_snapshot(allocation),
        queue_item_id="queue-1",
        writer=writer,
    )
    assert AgentDB().get_autonomous_tasks(status="pending", limit=20) == []
    monkeypatch.setattr(runtime, "_writer_activates", activate)
    recovered = _publish(
        worker_dispatch_dryrun_result=dryrun,
        authority_verification_context=context,
        work_state_snapshot=_snapshot(allocation),
        queue_item_id="queue-1",
        writer=writer,
    )

    assert interrupted.accepted is False
    assert recovered.accepted is True, recovered.rejection_reasons
    assert len(AgentDB().get_autonomous_tasks(status="pending", limit=20)) == 3


def test_agentdb_publication_recovers_after_post_activation_crash(
    monkeypatch,
) -> None:
    allocation = _allocation()
    context = worker_dispatch_authority_verification_context()
    dryrun = _dryrun_result(allocation)
    writer = runtime.AgentDbSignedWorkerDispatchTaskWriter()
    accepted_result = runtime._accepted_result

    def _crash_after_activation(*_args, **_kwargs):
        raise RuntimeError("post_activation_crash")

    monkeypatch.setattr(runtime, "_accepted_result", _crash_after_activation)
    with pytest.raises(RuntimeError, match="post_activation_crash"):
        _publish(
            worker_dispatch_dryrun_result=dryrun,
            authority_verification_context=context,
            work_state_snapshot=_snapshot(allocation),
            queue_item_id="queue-1",
            writer=writer,
        )
    assert len(AgentDB().get_autonomous_tasks(status="pending", limit=20)) == 3

    monkeypatch.setattr(runtime, "_accepted_result", accepted_result)
    recovered = _publish(
        worker_dispatch_dryrun_result=dryrun,
        authority_verification_context=context,
        work_state_snapshot=_snapshot(allocation),
        queue_item_id="queue-1",
        writer=writer,
    )

    assert recovered.accepted is True, recovered.rejection_reasons
    assert len(AgentDB().get_autonomous_tasks(status="pending", limit=20)) == 3


def test_applied_publication_rejects_tampered_held_batch(
    monkeypatch,
) -> None:
    allocation = _allocation()
    context = worker_dispatch_authority_verification_context()
    dryrun = _dryrun_result(allocation)
    writer = runtime.AgentDbSignedWorkerDispatchTaskWriter()
    activate = runtime._writer_activates
    monkeypatch.setattr(runtime, "_writer_activates", lambda *_args: False)
    interrupted = _publish(
        worker_dispatch_dryrun_result=dryrun,
        authority_verification_context=context,
        work_state_snapshot=_snapshot(allocation),
        queue_item_id="queue-1",
        writer=writer,
    )
    held = AgentDB().get_autonomous_tasks(status="publication_held", limit=20)
    assert interrupted.accepted is False and len(held) == 3
    assert AgentDB().db.execute_write(
        "UPDATE agents_autonomous_tasks SET description = ? WHERE task_id = ?",
        ("attacker-selected-task", held[0]["task_id"]),
    ) == 1
    monkeypatch.setattr(runtime, "_writer_activates", activate)

    recovered = _publish(
        worker_dispatch_dryrun_result=dryrun,
        authority_verification_context=context,
        work_state_snapshot=_snapshot(allocation),
        queue_item_id="queue-1",
        writer=writer,
    )

    assert recovered.accepted is False
    assert AgentDB().get_autonomous_tasks(status="pending", limit=20) == []


def test_rechecks_fresh_time_after_context_construction_before_writer() -> None:
    allocation = _allocation()
    authority_runtime, authority_verification = _authority_stages(allocation)
    clock = {"now": 1000}
    context = replace(
        worker_dispatch_authority_verification_context(),
        trusted_now_epoch=lambda: clock["now"],
    )
    clock["now"] = 5000
    writer = _FakeWriter()

    result = runtime.publish_reddog_signed_worker_dispatch_runtime(
        worker_dispatch_dryrun_result=_dryrun_result(allocation),
        queue_authority_runtime_result=authority_runtime,
        queue_authority_verification_result=authority_verification,
        authority_verification_context=context,
        work_state_snapshot=_snapshot(allocation),
        queue_item_id="queue-1",
        writer=writer,
    )

    assert result.accepted is False
    assert (
        runtime.WorkerDispatchRuntimeReason.AUTHORITY_VERIFICATION_BINDING_MISMATCH
        in result.rejection_reasons
    )
    assert writer.calls == []


@pytest.mark.parametrize(
    "field",
    (
        "verified_work_authority_digest",
        "authority_verification_receipt_id",
        "authority_verification_receipt_digest",
    ),
)
def test_rejects_altered_recorded_authority_verification_proof(
    field: str,
) -> None:
    allocation = _allocation()
    authority_runtime, authority_verification = _authority_stages(allocation)
    authority_verification[field] = "attacker-recomputed"
    writer = _FakeWriter()

    result = runtime.publish_reddog_signed_worker_dispatch_runtime(
        worker_dispatch_dryrun_result=_dryrun_result(allocation),
        queue_authority_runtime_result=authority_runtime,
        queue_authority_verification_result=authority_verification,
        authority_verification_context=worker_dispatch_authority_verification_context(),
        work_state_snapshot=_snapshot(allocation),
        queue_item_id="queue-1",
        writer=writer,
    )

    assert result.accepted is False
    assert (
        runtime.WorkerDispatchRuntimeReason.AUTHORITY_VERIFICATION_BINDING_MISMATCH
        in result.rejection_reasons
    )
    assert writer.calls == []


def test_prepared_architect_publication_cannot_enqueue_agentdb_tasks() -> None:
    writer = _FakeWriter()
    snapshot = _snapshot(
        claim_id="sha256:" + "6" * 64,
    )
    snapshot["architect_fix_promotions"] = [{
        "publication_id": "sha256:" + "4" * 64,
        "queue_item_id": "queue-1",
        "claim_id": "sha256:" + "6" * 64,
    }]
    snapshot["architect_fix_publications"] = [{
        "publication_id": "sha256:" + "4" * 64,
        "state": "STATE_PREPARED",
    }]

    result = _publish(
        worker_dispatch_dryrun_result=_dryrun_result(),
        work_state_snapshot=snapshot,
        queue_item_id="queue-1",
        writer=writer,
    )

    assert result.accepted is False
    assert (
        runtime.WorkerDispatchRuntimeReason.ARCHITECT_FIX_PUBLICATION_BINDING_MISMATCH
        in result.rejection_reasons
    )
    assert writer.calls == []


def test_committed_architect_binding_is_revalidated_before_enqueue() -> None:
    allocation = _allocation()
    base = _snapshot(allocation, claim_id="claim-1")
    committed, profile, queue_id, claim_id = with_architect_fix_publication(
        base,
        {},
    )
    binding = committed_publication_effect_binding(
        committed,
        profile,
        queue_item_id=queue_id,
        claim_id=claim_id,
    )
    assert binding is not None
    refs = {
        "architect_fix_publication_receipt_id": binding["publication_id"],
        "architect_fix_publication_binding_digest": binding["binding_digest"],
    }
    authority_runtime, authority_verification = _authority_stages(
        allocation,
        work_state_snapshot=committed,
        queue_item_id=queue_id,
        **refs,
    )
    refs.update(
        {
            key: authority_verification[key]
            for key in (
                "verified_work_authority_digest",
                "authority_verification_receipt_id",
                "authority_verification_receipt_digest",
            )
        }
    )
    intents = tuple(
        {**dict(intent), **refs}
        for intent in _dryrun_result(allocation)["receipt"]["dispatch_intents"]
    )
    receipt = {
        **_dryrun_result(
            allocation=allocation,
            intents=intents,
        )["receipt"],
        **refs,
    }
    writer = _FakeWriter()

    result = _publish(
        worker_dispatch_dryrun_result=_dryrun_result(
            allocation=allocation,
            intents=intents,
            receipt=receipt,
        ),
        work_state_snapshot=committed,
        queue_item_id=queue_id,
        writer=writer,
        queue_authority_runtime_result=authority_runtime,
        queue_authority_verification_result=authority_verification,
    )

    assert result.accepted is True
    assert result.receipt is not None
    assert result.receipt.architect_fix_publication_receipt_id == binding[
        "publication_id"
    ]
    assert writer.calls
    stale_writer = _FakeWriter()
    stale = {**committed, "revision": "a" * 64}
    rejected = _publish(
        worker_dispatch_dryrun_result=_dryrun_result(
            allocation=allocation,
            intents=intents,
            receipt=receipt,
        ),
        work_state_snapshot=stale,
        queue_item_id=queue_id,
        writer=stale_writer,
    )
    assert rejected.accepted is False
    assert stale_writer.calls == []


def test_carries_signed_model_runtime_binding_into_agentdb_task_context() -> None:
    allocation = _allocation()
    refs = _runtime_binding_refs()
    snapshot = _snapshot(allocation, **refs)
    authority_runtime, authority_verification = _authority_stages(
        allocation,
        work_state_snapshot=snapshot,
        **refs,
    )
    refs.update(
        {
            key: authority_verification[key]
            for key in (
                "verified_work_authority_digest",
                "authority_verification_receipt_id",
                "authority_verification_receipt_digest",
            )
        }
    )
    intents = tuple(
        {**dict(intent), **refs}
        for intent in _dryrun_result(allocation)["receipt"]["dispatch_intents"]
    )
    dryrun = _dryrun_result(
        allocation=allocation,
        intents=intents,
        receipt={
            **_dryrun_result(allocation=allocation, intents=intents)["receipt"],
            **refs,
        },
    )
    writer = _FakeWriter()

    result = _publish(
        worker_dispatch_dryrun_result=dryrun,
        work_state_snapshot=snapshot,
        queue_item_id="queue-1",
        writer=writer,
        queue_authority_runtime_result=authority_runtime,
        queue_authority_verification_result=authority_verification,
    )

    assert result.accepted is True
    assert result.receipt is not None
    assert result.receipt.model_runtime_binding_receipt_id == refs["model_runtime_binding_receipt_id"]
    assert result.receipt.model_runtime_binding_digest == refs["model_runtime_binding_digest"]
    assert result.tasks[0].context["model_runtime_binding_receipt_id"] == refs[
        "model_runtime_binding_receipt_id"
    ]
    assert result.tasks[0].context["model_runtime_binding_digest"] == refs[
        "model_runtime_binding_digest"
    ]


def test_rejects_model_runtime_binding_conflict_between_signed_receipt_and_queue() -> None:
    allocation = _allocation()
    refs = _runtime_binding_refs()
    intents = (
        _intent("coding_worker_1", "0102", "bounded_code_change", allocation, **refs),
    )
    dryrun = _dryrun_result(
        allocation=allocation,
        intents=intents,
        receipt={
            **_dryrun_result(allocation=allocation, intents=intents)["receipt"],
            **refs,
        },
    )

    result = _publish(
        worker_dispatch_dryrun_result=dryrun,
        work_state_snapshot=_snapshot(
            allocation,
            **{**refs, "model_runtime_binding_receipt_id": "reddog_model_runtime_binding:other"},
        ),
        queue_item_id="queue-1",
        writer=_FakeWriter(),
    )

    assert result.accepted is False
    assert runtime.WorkerDispatchRuntimeReason.MODEL_RUNTIME_BINDING_MISMATCH in result.rejection_reasons


def test_rejects_memex_binding_conflict_before_nonce_or_writer_effect() -> None:
    allocation = _allocation()
    context = worker_dispatch_authority_verification_context()
    writer = _FakeWriter()

    rejected = _publish(
        worker_dispatch_dryrun_result=_dryrun_result(allocation),
        authority_verification_context=context,
        work_state_snapshot=_snapshot(
            allocation,
            memex_supply_receipt_id="sha256:other-memex-supply",
            memex_supply_digest="sha256:" + ("8" * 64),
        ),
        queue_item_id="queue-1",
        writer=writer,
    )
    accepted = _publish(
        worker_dispatch_dryrun_result=_dryrun_result(allocation),
        authority_verification_context=context,
        work_state_snapshot=_snapshot(allocation),
        queue_item_id="queue-1",
        writer=_FakeWriter(),
    )

    assert rejected.accepted is False
    assert (
        runtime.WorkerDispatchRuntimeReason.MEMEX_SUPPLY_BINDING_MISMATCH
        in rejected.rejection_reasons
    )
    assert writer.calls == []
    assert accepted.accepted is True


def test_intent_validation_does_not_collapse_falsy_memex_values_to_absent() -> None:
    dryrun = _dryrun_result(_allocation())
    receipt = dict(dryrun["receipt"])
    intent = dict(receipt["dispatch_intents"][0])
    receipt["memex_supply_receipt_id"] = ""
    receipt["memex_supply_digest"] = ""
    intent["memex_supply_receipt_id"] = 0
    intent["memex_supply_digest"] = False

    assert runtime_validation._intent_safe(intent, receipt) is False
    intent["memex_supply_receipt_id"] = ""
    intent["memex_supply_digest"] = ""
    assert runtime_validation._intent_safe(intent, receipt) is True


def test_rejects_legacy_dispatch_without_explicit_memex_fields_before_effect() -> None:
    allocation = _allocation()
    dryrun = _dryrun_result(allocation)
    receipt = dict(dryrun["receipt"])
    receipt.pop("memex_supply_receipt_id")
    receipt.pop("memex_supply_digest")
    receipt["dispatch_intents"] = [
        {
            key: value
            for key, value in intent.items()
            if key not in {"memex_supply_receipt_id", "memex_supply_digest"}
        }
        for intent in receipt["dispatch_intents"]
    ]
    writer = _FakeWriter()

    result = _publish(
        worker_dispatch_dryrun_result={**dryrun, "receipt": receipt},
        work_state_snapshot=_snapshot(allocation),
        queue_item_id="queue-1",
        writer=writer,
    )

    assert result.accepted is False
    assert (
        runtime.WorkerDispatchRuntimeReason.DISPATCH_SCHEMA_MISMATCH
        in result.rejection_reasons
    )
    assert writer.calls == []


def test_agentdb_writer_publishes_tasks_atomically() -> None:
    result = _publish(
        worker_dispatch_dryrun_result=_dryrun_result(),
        work_state_snapshot=_snapshot(),
        queue_item_id="queue-1",
        writer=runtime.AgentDbSignedWorkerDispatchTaskWriter(),
    )

    assert result.accepted is True
    pending = AgentDB().get_autonomous_tasks(status="pending", limit=10)
    assert len(pending) == 3
    assert {task["task_id"] for task in pending} == set(result.receipt.task_ids)
    for task in pending:
        assert task["context"]["source"] == runtime.SIGNED_WORKER_DISPATCH_TASK_SOURCE
        assert task["context"]["requires_downstream_stages"]
        assert task["context"]["report_contract"]["requires_signed_authority"] is True


def test_agentdb_writer_rejects_duplicate_without_second_batch() -> None:
    writer = runtime.AgentDbSignedWorkerDispatchTaskWriter()
    first = _publish(
        worker_dispatch_dryrun_result=_dryrun_result(),
        work_state_snapshot=_snapshot(),
        queue_item_id="queue-1",
        writer=writer,
    )
    second = _publish(
        worker_dispatch_dryrun_result=_dryrun_result(),
        work_state_snapshot=_snapshot(),
        queue_item_id="queue-1",
        writer=writer,
    )

    assert first.accepted is True
    assert second.accepted is False
    assert second.rejection_reasons == (runtime.WorkerDispatchRuntimeReason.WRITER_REJECTED,)
    assert len(AgentDB().get_autonomous_tasks(status="pending", limit=10)) == 3


def test_rejects_missing_writer_and_unaccepted_dryrun() -> None:
    missing_writer = _publish(
        worker_dispatch_dryrun_result=_dryrun_result(),
        work_state_snapshot=_snapshot(),
        queue_item_id="queue-1",
        writer=None,
    )
    rejected_dryrun = _publish(
        worker_dispatch_dryrun_result={"accepted": False, "decision": "NO"},
        work_state_snapshot=_snapshot(),
        queue_item_id="queue-1",
        writer=_FakeWriter(),
    )

    assert missing_writer.accepted is False
    assert runtime.WorkerDispatchRuntimeReason.WRITER_MISSING in missing_writer.rejection_reasons
    assert rejected_dryrun.accepted is False
    assert runtime.WorkerDispatchRuntimeReason.DRYRUN_NOT_ACCEPTED in rejected_dryrun.rejection_reasons


def test_rejects_unsafe_intent_before_writer_call() -> None:
    allocation = _allocation()
    bad_intent = _intent(
        "coding_worker_1",
        "0102",
        "bounded_code_change",
        allocation,
        no_worker_spawn_performed=False,
    )
    writer = _FakeWriter()

    result = _publish(
        worker_dispatch_dryrun_result=_dryrun_result(allocation, intents=(bad_intent,)),
        work_state_snapshot=_snapshot(allocation),
        queue_item_id="queue-1",
        writer=writer,
    )

    assert result.accepted is False
    assert runtime.WorkerDispatchRuntimeReason.INTENT_UNSAFE in result.rejection_reasons
    assert writer.calls == []


def test_effect_runtime_rejects_empty_progressive_stage_before_writer() -> None:
    injected = _dryrun_result()
    receipt = injected["receipt"]
    receipt["progressive_policy_stage_receipt_id"] = ""
    receipt["progressive_policy_stage_digest"] = ""
    for intent in receipt["dispatch_intents"]:
        intent["progressive_policy_stage_receipt_id"] = ""
        intent["progressive_policy_stage_digest"] = ""
    writer = _FakeWriter()

    result = _publish(
        worker_dispatch_dryrun_result=injected,
        work_state_snapshot=_snapshot(),
        queue_item_id="queue-1",
        writer=writer,
    )

    assert result.accepted is False
    assert runtime.WorkerDispatchRuntimeReason.PROGRESSIVE_STAGE_BINDING_MISMATCH in result.rejection_reasons
    assert writer.calls == []


def test_rejects_wsp15_queue_binding_mismatch_and_seen_replay() -> None:
    allocation = _allocation()
    other = _allocation(receipt_id="sha256:other-allocation")
    authority_runtime, authority_verification = _authority_stages(
        allocation, work_state_snapshot=_snapshot(allocation)
    )
    mismatch = runtime.publish_reddog_signed_worker_dispatch_runtime(
        worker_dispatch_dryrun_result=_dryrun_result(allocation),
        queue_authority_runtime_result=authority_runtime,
        queue_authority_verification_result=authority_verification,
        authority_verification_context=worker_dispatch_authority_verification_context(),
        work_state_snapshot=_snapshot(other),
        queue_item_id="queue-1",
        writer=_FakeWriter(),
    )
    replay = _publish(
        worker_dispatch_dryrun_result=_dryrun_result(allocation),
        work_state_snapshot=_snapshot(allocation),
        queue_item_id="queue-1",
        writer=_FakeWriter(),
        seen_intent_ids={"worker_dispatch_intent_coding_worker_1"},
    )

    assert mismatch.accepted is False
    assert runtime.WorkerDispatchRuntimeReason.WSP15_BINDING_MISMATCH in mismatch.rejection_reasons
    assert replay.accepted is False
    assert runtime.WorkerDispatchRuntimeReason.IDEMPOTENCY_REPLAY in replay.rejection_reasons


def test_result_is_deterministic_and_json_serializable() -> None:
    first = _publish(
        worker_dispatch_dryrun_result=_dryrun_result(),
        work_state_snapshot=_snapshot(),
        queue_item_id="queue-1",
        writer=_FakeWriter(),
        now=datetime(2026, 7, 16, tzinfo=timezone.utc),
    )
    second = _publish(
        worker_dispatch_dryrun_result=_dryrun_result(),
        work_state_snapshot=_snapshot(),
        queue_item_id="queue-1",
        writer=_FakeWriter(),
        now=datetime(2026, 7, 16, tzinfo=timezone.utc),
    )

    assert first.receipt is not None and second.receipt is not None
    assert first.receipt.receipt_digest == second.receipt.receipt_digest
    json.dumps(first.to_dict(), sort_keys=True)


def test_module_ast_boundaries() -> None:
    forbidden_text = (
        "subprocess",
        "requests",
        "hermes_job_executor",
        "worktree_pr_runner",
        "git push",
        "gh pr",
        "holo_index.py --index",
        "run_task.py",
        "pattern_memory_sink",
    )
    for path in RUNTIME_MODULE_PATHS:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        assert len(source.splitlines()) <= 675
        for token in forbidden_text:
            assert token not in source
        _assert_bounded_runtime_ast(tree)


def _assert_bounded_runtime_ast(tree: ast.AST) -> None:
    imported = set()
    calls = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            assert node.end_lineno - node.lineno + 1 <= 50
        elif isinstance(node, ast.ClassDef):
            assert node.end_lineno - node.lineno + 1 <= 200
        elif isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])
        elif isinstance(node, ast.Call):
            calls.add(
                node.func.id
                if isinstance(node.func, ast.Name)
                else getattr(node.func, "attr", "")
            )
    assert not (imported & {"subprocess", "requests", "socket", "urllib", "shutil"})
    assert not (calls & {"eval", "exec", "compile", "system", "popen", "run", "Popen"})
