"""Tests for resident queue signed worker-dispatch runtime handler."""

from __future__ import annotations

import hashlib
import json

from modules.communication.moltbot_bridge.src.reddog_authoritative_work_state_refresh_runtime import (
    InMemoryAuthoritativeWorkStateStore,
)
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
    FAIL_AUTHORITY_RUNTIME_STAGE_MISSING,
    FAIL_AUTHORITY_VERIFICATION_STAGE_MISSING,
    FAIL_DISPATCH_RUNTIME_NEXT_ACTION_MISMATCH,
    FAIL_DISPATCH_RUNTIME_STAGE_MISMATCH,
    FAIL_WORKER_DISPATCH_DRYRUN_STAGE_MISSING,
    FAIL_WORKER_DISPATCH_WRITER_MISSING,
    WORKER_DISPATCH_RUNTIME_STAGE_KEY,
    build_reddog_resident_queue_worker_dispatch_runtime_stage_handler,
)
from modules.communication.moltbot_bridge.src.reddog_signed_authority_worker_dispatch_dryrun import (
    SIGNED_AUTHORITY_WORKER_DISPATCH_DRYRUN_ACCEPT,
    derive_worker_dispatch_roles,
)
from modules.communication.moltbot_bridge.tests.reddog_resident_queue_test_helpers import (
    governed_worker_dispatch_snapshot,
    worker_dispatch_authority_verification_context,
    worker_dispatch_authority_stages,
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

    def activate_signed_worker_dispatch_tasks(self, tasks, receipt):
        return {
            "ok": self.ok,
            "created_task_ids": [task.task_id for task in tasks] if self.ok else [],
        }


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
    return governed_worker_dispatch_snapshot({
        "schema_version": "reddog_authoritative_work_state.v1",
        "wre_queue_items": [
            {
                "queue_item_id": "queue-1",
                "slice_id": "REDDOG_TEST_SLICE_PHASE1",
                "status": "QUEUED",
                "wsp15_allocation_receipt": allocation,
            }
        ],
    })


def _dryrun_stage():
    allocation = _allocation()
    _, verification = _authority_stages()
    queue_item = _snapshot()["wre_queue_items"][0]
    refs = {
        key: verification[key]
        for key in (
            "verified_work_authority_digest",
            "authority_verification_receipt_id",
            "authority_verification_receipt_digest",
        )
    }
    intents = [
        {
            "intent_id": f"worker_dispatch_intent_{role}",
            "role": role,
            "worker_runtime": worker_runtime,
            "capability": capability,
            "work_order_id": "wo-1",
            "foundup_id": "paccess_001",
            "requested_operation": "create_foundup",
            "wsp15_allocation_receipt_id": allocation["receipt_id"],
            "wsp15_allocation_digest": _digest(allocation),
            "model_runtime_binding_receipt_id": "",
            "model_runtime_binding_digest": "",
            "model_runtime_binding_verification_receipt_id": "",
            "model_runtime_binding_verification_digest": "",
            "memex_supply_receipt_id": queue_item["memex_supply_receipt_id"],
            "memex_supply_digest": queue_item["memex_supply_digest"],
            "architect_fix_publication_receipt_id": "",
            "architect_fix_publication_binding_digest": "",
            **refs,
            "dry_run_only": True,
            "no_worker_spawn_performed": True,
            "no_openclaw_enqueue_performed": True,
            "no_hermes_dispatch_performed": True,
        }
        for role, worker_runtime, capability in derive_worker_dispatch_roles(allocation)
    ]
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
            "model_runtime_binding_receipt_id": "",
            "model_runtime_binding_digest": "",
            "model_runtime_binding_verification_receipt_id": "",
            "model_runtime_binding_verification_digest": "",
            "memex_supply_receipt_id": queue_item["memex_supply_receipt_id"],
            "memex_supply_digest": queue_item["memex_supply_digest"],
            "architect_fix_publication_receipt_id": "",
            "architect_fix_publication_binding_digest": "",
            **refs,
            "dispatch_intent_count": len(intents),
            "dispatch_intents": intents,
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
        },
    }


def _authority_stages():
    return worker_dispatch_authority_stages(
        _allocation(),
        work_state_snapshot=_snapshot(),
    )


def _stage_results():
    authority_runtime, authority_verification = _authority_stages()
    return {
        "authority_runtime": authority_runtime,
        "authority_verification": authority_verification,
        "worker_dispatch_dryrun": _dryrun_stage(),
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
                "stage_results": _stage_results(),
            }
        ),
        writer=writer or _FakeWriter(),
        authority_verification_context=worker_dispatch_authority_verification_context(),
        work_state_store=InMemoryAuthoritativeWorkStateStore(_snapshot()),
    )


def test_runtime_handler_publishes_signed_worker_tasks() -> None:
    writer = _FakeWriter()
    result = _handler(writer=writer)(_request())

    assert result["accepted"] is True
    assert result["decision"] == SIGNED_AUTHORITY_WORKER_DISPATCH_RUNTIME_ACCEPT
    assert result["receipt"]["agentdb_tasks_enqueued"] is True
    assert result["tasks"][0]["context"]["worker_runtime"] == "0102"
    assert writer.calls and len(writer.calls[0][0]) == 3


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
                "stage_results": _stage_results(),
            }
        ),
        writer=None,
        authority_verification_context=worker_dispatch_authority_verification_context(),
        work_state_store=InMemoryAuthoritativeWorkStateStore(_snapshot()),
    )(_request())

    assert missing_dryrun["accepted"] is False
    assert FAIL_WORKER_DISPATCH_DRYRUN_STAGE_MISSING in missing_dryrun["rejection_reasons"]
    assert missing_writer["accepted"] is False
    assert FAIL_WORKER_DISPATCH_WRITER_MISSING in missing_writer["rejection_reasons"]


def test_runtime_handler_requires_recorded_authority_and_verification_stages() -> None:
    dryrun_only = {
        "schema_version": "reddog_resident_queue_chain_results.v1",
        "stage_results": {"worker_dispatch_dryrun": _dryrun_stage()},
    }
    no_authority = _handler(
        store=InMemoryResidentQueueChainResultsStore(dryrun_only)
    )(_request())
    authority_runtime, _ = _authority_stages()
    no_verification = _handler(
        store=InMemoryResidentQueueChainResultsStore(
            {
                "schema_version": "reddog_resident_queue_chain_results.v1",
                "stage_results": {
                    "authority_runtime": authority_runtime,
                    "worker_dispatch_dryrun": _dryrun_stage(),
                },
            }
        )
    )(_request())

    assert FAIL_AUTHORITY_RUNTIME_STAGE_MISSING in no_authority[
        "rejection_reasons"
    ]
    assert FAIL_AUTHORITY_VERIFICATION_STAGE_MISSING in no_verification[
        "rejection_reasons"
    ]


def test_runtime_handler_surfaces_writer_rejection() -> None:
    result = _handler(writer=_FakeWriter(ok=False))(_request())

    assert result["accepted"] is False
    assert WorkerDispatchRuntimeReason.WRITER_REJECTED in result["rejection_reasons"]
