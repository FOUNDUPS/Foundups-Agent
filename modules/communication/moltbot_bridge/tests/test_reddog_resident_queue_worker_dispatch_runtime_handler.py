"""Tests for resident queue signed worker-dispatch runtime handler."""

from __future__ import annotations

import hashlib
import json

from modules.communication.moltbot_bridge.src.reddog_openclaw_hermes_0102_worker_dispatch_runtime import (
    SIGNED_AUTHORITY_WORKER_DISPATCH_RUNTIME_ACCEPT,
    WorkerDispatchRuntimeReason,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_chain_results_store import (
    InMemoryResidentQueueChainResultsStore,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_next_stage_dispatch import (
    ResidentQueueStageDispatchRequest,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_orchestration_plan import (
    NEXT_QUEUE_WORKER_DISPATCH_RUNTIME,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_worker_dispatch_runtime_handler import (
    FAIL_DISPATCH_RUNTIME_NEXT_ACTION_MISMATCH,
    FAIL_DISPATCH_RUNTIME_STAGE_MISMATCH,
    FAIL_WORKER_DISPATCH_DRYRUN_STAGE_MISSING,
    FAIL_WORKER_DISPATCH_WRITER_MISSING,
    WORKER_DISPATCH_RUNTIME_STAGE_KEY,
    build_reddog_resident_queue_worker_dispatch_runtime_stage_handler,
)
from modules.communication.moltbot_bridge.src.reddog_signed_authority_worker_dispatch_dryrun import (
    SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_ACCEPT,
)


class _FakeWriter:
    def __init__(self, *, ok=True) -> None:
        self.ok = ok
        self.calls = []

    def enqueue_signed_worker_dispatch_tasks(self, tasks, receipt):
        self.calls.append((list(tasks), receipt))
        if not self.ok:
            return {"ok": False, "created_task_ids": []}
        return {"ok": True, "created_task_ids": [task.task_id for task in tasks]}


def _digest(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _allocation():
    return {
        "schema_version": "reddog_wsp15_allocation_receipt.v1",
        "receipt_id": "sha256:wsp15-allocation",
        "mps_total": 14,
        "priority": "P1",
        "reasoning_tier": "HIGH",
        "worker_plan": {
            "schema_version": "reddog_wsp15_worker_plan.v1",
            "fusion_required": True,
            "critic_count": 1,
            "coding_worker_count": 1,
            "independent_verifier_required": True,
            "openclaw_candidate": False,
            "hermes_execution_allowed": False,
            "queue_mutation_allowed": False,
        },
    }


def _snapshot():
    allocation = _allocation()
    return {
        "schema_version": "reddog_authoritative_work_state.v1",
        "wre_queue_items": [
            {
                "queue_item_id": "queue-1",
                "slice_id": "REDDOG_TEST_SLICE_PHASE1",
                "status": "QUEUED",
                "wsp15_allocation_receipt": allocation,
            }
        ],
    }


def _dryrun_stage():
    allocation = _allocation()
    intent = {
        "intent_id": "worker_dispatch_intent_fusion_lead",
        "role": "fusion_lead",
        "worker_runtime": "0102",
        "capability": "architect_review",
        "work_order_id": "wo-1",
        "foundup_id": "paccess_001",
        "requested_operation": "create_foundup",
        "wsp15_allocation_receipt_id": allocation["receipt_id"],
        "wsp15_allocation_digest": _digest(allocation),
        "dry_run_only": True,
        "no_worker_spawn_performed": True,
        "no_openclaw_enqueue_performed": True,
        "no_hermes_dispatch_performed": True,
    }
    return {
        "accepted": True,
        "decision": SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_ACCEPT,
        "receipt": {
            "receipt_id": "signed_authority_worker_dispatch_abc",
            "work_order_id": "wo-1",
            "foundup_id": "paccess_001",
            "requested_operation": "create_foundup",
            "wsp15_allocation_receipt_id": allocation["receipt_id"],
            "wsp15_allocation_digest": _digest(allocation),
            "wsp15_priority": allocation["priority"],
            "wsp15_mps_total": allocation["mps_total"],
            "wsp15_reasoning_tier": allocation["reasoning_tier"],
            "dispatch_intent_count": 1,
            "dispatch_intents": [intent],
        },
    }


def _request(**overrides):
    payload = {
        "stage_key": WORKER_DISPATCH_RUNTIME_STAGE_KEY,
        "next_action": NEXT_QUEUE_WORKER_DISPATCH_RUNTIME,
        "queue_item_id": "queue-1",
        "selected_slice": "REDDOG_TEST_SLICE_PHASE1",
        "plan_id": "plan-1",
        "accepted_stages": ("authority_request", "authority_runtime", "authority_verification", "worker_dispatch_dryrun"),
    }
    payload.update(overrides)
    return ResidentQueueStageDispatchRequest(**payload)


def _handler(writer=None, store=None):
    return build_reddog_resident_queue_worker_dispatch_runtime_stage_handler(
        work_state_snapshot=_snapshot(),
        chain_results_store=store
        or InMemoryResidentQueueChainResultsStore(
            {
                "schema_version": "reddog_resident_queue_chain_results.v1",
                "stage_results": {"worker_dispatch_dryrun": _dryrun_stage()},
            }
        ),
        writer=writer or _FakeWriter(),
    )


def test_runtime_handler_publishes_signed_worker_tasks() -> None:
    writer = _FakeWriter()
    result = _handler(writer=writer)(_request())

    assert result["accepted"] is True
    assert result["decision"] == SIGNED_AUTHORITY_WORKER_DISPATCH_RUNTIME_ACCEPT
    assert result["receipt"]["agentdb_tasks_enqueued"] is True
    assert result["tasks"][0]["context"]["worker_runtime"] == "0102"
    assert writer.calls and len(writer.calls[0][0]) == 1


def test_runtime_handler_rejects_wrong_stage_or_action() -> None:
    wrong_stage = _handler()(_request(stage_key="worker_dispatch_dryrun"))
    wrong_action = _handler()(_request(next_action="RUN_SOMETHING_ELSE"))

    assert wrong_stage["accepted"] is False
    assert FAIL_DISPATCH_RUNTIME_STAGE_MISMATCH in wrong_stage["rejection_reasons"]
    assert wrong_action["accepted"] is False
    assert FAIL_DISPATCH_RUNTIME_NEXT_ACTION_MISMATCH in wrong_action["rejection_reasons"]


def test_runtime_handler_rejects_missing_dryrun_or_writer() -> None:
    missing_dryrun = _handler(
        store=InMemoryResidentQueueChainResultsStore(
            {"schema_version": "reddog_resident_queue_chain_results.v1", "stage_results": {}}
        )
    )(_request())
    missing_writer = build_reddog_resident_queue_worker_dispatch_runtime_stage_handler(
        work_state_snapshot=_snapshot(),
        chain_results_store=InMemoryResidentQueueChainResultsStore(
            {
                "schema_version": "reddog_resident_queue_chain_results.v1",
                "stage_results": {"worker_dispatch_dryrun": _dryrun_stage()},
            }
        ),
        writer=None,
    )(_request())

    assert missing_dryrun["accepted"] is False
    assert FAIL_WORKER_DISPATCH_DRYRUN_STAGE_MISSING in missing_dryrun["rejection_reasons"]
    assert missing_writer["accepted"] is False
    assert FAIL_WORKER_DISPATCH_WRITER_MISSING in missing_writer["rejection_reasons"]


def test_runtime_handler_surfaces_writer_rejection() -> None:
    result = _handler(writer=_FakeWriter(ok=False))(_request())

    assert result["accepted"] is False
    assert WorkerDispatchRuntimeReason.WRITER_REJECTED in result["rejection_reasons"]
