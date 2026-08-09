"""Construct signed worker AgentDB tasks and publication receipts."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from modules.communication.moltbot_bridge.src.reddog_signed_authority_worker_dispatch_dryrun import (
    WORKER_DISPATCH_INTENT_FIELDS,
    WORKER_DISPATCH_RECEIPT_FIELDS,
)
from modules.communication.moltbot_bridge.src.reddog_signed_worker_agentdb_envelope import (
    SIGNED_WORKER_DISPATCH_TASK_SKILL,
    SIGNED_WORKER_DISPATCH_TASK_SOURCE,
    WORKER_DISPATCH_RUNTIME_SCHEMA_VERSION,
    build_reddog_signed_worker_agentdb_envelope,
    canonical_reddog_signed_worker_task_id,
)
from modules.communication.moltbot_bridge.src.reddog_signed_worker_dispatch_runtime_types import (
    SIGNED_AUTHORITY_WORKER_DISPATCH_RUNTIME_ACCEPT,
    SignedWorkerDispatchRuntimeReceipt,
    SignedWorkerDispatchTaskSpec,
    canonical_digest,
    mapping,
    sequence,
)


_PRIORITY_SCORE = {"P0": 0.97, "P1": 0.90, "P2": 0.82, "P3": 0.70, "P4": 0.55}
_COMPLEXITY_SCORE = {"P0": 0.85, "P1": 0.75, "P2": 0.62, "P3": 0.48, "P4": 0.35}


def build_signed_worker_dispatch_task(
    *,
    queue_item: Mapping[str, Any],
    dryrun_receipt: Mapping[str, Any],
    intent: Mapping[str, Any],
    work_authority: Mapping[str, Any],
    queue_authority_runtime_result: Mapping[str, Any],
    queue_consumer_receipt: Mapping[str, Any],
    work_order_materialization_binding: Mapping[str, Any],
) -> SignedWorkerDispatchTaskSpec:
    core = _task_core(queue_item, dryrun_receipt, intent, queue_consumer_receipt)
    envelope = build_reddog_signed_worker_agentdb_envelope(
        task_id=core["task_id"],
        queue_authority_runtime_result=queue_authority_runtime_result,
        wsp15_allocation_receipt=mapping(queue_item.get("wsp15_allocation_receipt")),
        dispatch_receipt=dryrun_receipt,
        dispatch_intent=intent,
        queue_consumer_receipt=queue_consumer_receipt,
        work_order_materialization_binding=work_order_materialization_binding,
        task_binding=_task_binding(core),
        model_runtime_binding_receipt=mapping(
            queue_item.get("model_runtime_binding_receipt")
        ),
    )
    context = _task_context(
        core=core,
        queue_item=queue_item,
        dryrun_receipt=dryrun_receipt,
        intent=intent,
        work_authority=work_authority,
        envelope=envelope,
    )
    return SignedWorkerDispatchTaskSpec(
        task_id=core["task_id"],
        description=core["description"],
        required_skills=core["required_skills"],
        estimated_complexity=core["estimated_complexity"],
        priority_score=core["priority_score"],
        context=context,
        origin_continuity_id=core["origin_continuity_id"],
    )


def build_signed_worker_dispatch_runtime_receipt(
    *,
    receipt: Mapping[str, Any],
    queue_item: Mapping[str, Any],
    tasks: Sequence[SignedWorkerDispatchTaskSpec],
    created_at: str,
) -> SignedWorkerDispatchRuntimeReceipt:
    payload = _receipt_payload(receipt, queue_item, tasks, created_at)
    receipt_id = (
        "signed_worker_dispatch_runtime_"
        + canonical_digest(payload).removeprefix("sha256:")[:16]
    )
    return SignedWorkerDispatchRuntimeReceipt(
        **_receipt_identity_fields(receipt, queue_item),
        schema_version=WORKER_DISPATCH_RUNTIME_SCHEMA_VERSION,
        receipt_id=receipt_id,
        status=SIGNED_AUTHORITY_WORKER_DISPATCH_RUNTIME_ACCEPT,
        task_ids=tuple(task.task_id for task in tasks),
        intent_ids=tuple(payload["intent_ids"]),
        worker_runtimes=_worker_runtimes(receipt),
        created_at=created_at,
        receipt_digest=canonical_digest({**payload, "receipt_id": receipt_id}),
        agentdb_tasks_enqueued=True,
    )


def _task_core(
    queue_item: Mapping[str, Any],
    receipt: Mapping[str, Any],
    intent: Mapping[str, Any],
    queue_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    runtime = str(intent["worker_runtime"])
    capability = str(intent["capability"])
    role = str(intent["role"])
    task_id = canonical_reddog_signed_worker_task_id(
        source_dispatch_receipt_id=str(receipt["receipt_id"]),
        queue_item_id=str(queue_item["queue_item_id"]),
        intent_id=str(intent["intent_id"]),
    )
    priority = str(receipt.get("wsp15_priority") or "P2")
    return {
        "task_id": task_id,
        "runtime": runtime,
        "capability": capability,
        "role": role,
        "description": f"RedDog signed worker dispatch: {role} ({runtime}/{capability})",
        "required_skills": (
            SIGNED_WORKER_DISPATCH_TASK_SKILL,
            f"runtime:{runtime}",
            f"capability:{capability}",
        ),
        "estimated_complexity": _COMPLEXITY_SCORE.get(priority, 0.62),
        "priority_score": _PRIORITY_SCORE.get(priority, 0.82),
        "origin_continuity_id": str(receipt["work_order_id"]),
        "queue_item_id": str(queue_item["queue_item_id"]),
        "source_dispatch_receipt_id": str(receipt["receipt_id"]),
        "operational_snapshot_id": str(queue_receipt["operational_snapshot_id"]),
        "selected_slice": str(queue_item.get("slice_id") or ""),
    }


def _task_binding(core: Mapping[str, Any]) -> dict[str, Any]:
    payload = {
        key: core[key]
        for key in (
            "task_id",
            "description",
            "required_skills",
            "estimated_complexity",
            "priority_score",
            "origin_continuity_id",
            "queue_item_id",
            "source_dispatch_receipt_id",
            "operational_snapshot_id",
            "selected_slice",
        )
    } | {"source": SIGNED_WORKER_DISPATCH_TASK_SOURCE}
    payload["required_skills"] = list(core["required_skills"])
    return payload


def _task_context(
    *,
    core: Mapping[str, Any],
    queue_item: Mapping[str, Any],
    dryrun_receipt: Mapping[str, Any],
    intent: Mapping[str, Any],
    work_authority: Mapping[str, Any],
    envelope: Mapping[str, Any],
) -> dict[str, Any]:
    context = _base_context(core, queue_item, dryrun_receipt, intent, work_authority)
    context.update(_authority_context(dryrun_receipt))
    context["signed_worker_agentdb_envelope"] = envelope
    context["execution_allowed_by_dispatch_runtime"] = False
    context["requires_downstream_stages"] = _downstream_stages()
    context["report_contract"] = _report_contract()
    return context


def _base_context(
    core: Mapping[str, Any],
    queue_item: Mapping[str, Any],
    receipt: Mapping[str, Any],
    intent: Mapping[str, Any],
    authority: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "source": SIGNED_WORKER_DISPATCH_TASK_SOURCE,
        "schema_version": WORKER_DISPATCH_RUNTIME_SCHEMA_VERSION,
        "slice_name": "REDDOG_OPENCLAW_HERMES_0102_WORKER_DISPATCH_RUNTIME_PHASE1",
        "queue_item_id": str(queue_item["queue_item_id"]),
        "work_order_id": str(receipt.get("work_order_id") or ""),
        "operational_snapshot_id": core["operational_snapshot_id"],
        "wsp15_allocation_receipt_id": str(receipt.get("wsp15_allocation_receipt_id") or ""),
        "progressive_policy_stage_receipt_id": str(
            receipt.get("progressive_policy_stage_receipt_id") or ""
        ),
        "progressive_policy_stage_digest": str(
            receipt.get("progressive_policy_stage_digest") or ""
        ),
        "selected_slice": core["selected_slice"],
        "worker_runtime": core["runtime"],
        "worker_role": core["role"],
        "worker_principal_id": f"agentdb-task:{core['task_id']}",
        "capability": core["capability"],
        "signed_authority_worker_dispatch_receipt": _canonical_receipt(receipt),
        "worker_dispatch_intent": _canonical_intent(intent),
        "authorized_principal_id": str(authority["principal_id"]),
        "authorized_reddog_id": str(authority["reddog_id"]),
        "wsp15_allocation_receipt": dict(mapping(queue_item.get("wsp15_allocation_receipt"))),
        "model_runtime_binding_receipt": dict(
            mapping(queue_item.get("model_runtime_binding_receipt"))
        ),
    }


def _authority_context(receipt: Mapping[str, Any]) -> dict[str, Any]:
    fields = (
        "model_runtime_binding_receipt_id",
        "model_runtime_binding_digest",
        "memex_supply_receipt_id",
        "memex_supply_digest",
        "architect_fix_publication_receipt_id",
        "architect_fix_publication_binding_digest",
        "progressive_policy_stage_receipt_id",
        "progressive_policy_stage_digest",
        "verified_work_authority_digest",
        "authority_verification_receipt_id",
        "authority_verification_receipt_digest",
    )
    return {field: str(receipt.get(field) or "") for field in fields}


def _downstream_stages() -> list[str]:
    return [
        "work_order_invocation",
        "executor_plan",
        "execution_valve",
        "worktree_create",
        "assurance_capacity_admission",
        "bounded_worker_pilot",
        "slice_verifier",
    ]


def _report_contract() -> dict[str, bool]:
    return {
        "worker_process_started": False,
        "repo_mutation_performed": False,
        "hermes_execution_performed": False,
        "requires_signed_authority": True,
    }


def _receipt_payload(
    receipt: Mapping[str, Any],
    queue_item: Mapping[str, Any],
    tasks: Sequence[SignedWorkerDispatchTaskSpec],
    created_at: str,
) -> dict[str, Any]:
    return {
        "schema_version": WORKER_DISPATCH_RUNTIME_SCHEMA_VERSION,
        "status": SIGNED_AUTHORITY_WORKER_DISPATCH_RUNTIME_ACCEPT,
        "source_dispatch_receipt_id": str(receipt.get("receipt_id") or ""),
        "queue_item_id": str(queue_item.get("queue_item_id") or ""),
        **_receipt_digest_authority_context(receipt),
        "task_ids": [task.task_id for task in tasks],
        "intent_ids": [
            str(mapping(intent).get("intent_id") or "")
            for intent in sequence(receipt.get("dispatch_intents"))
        ],
        "rejection_reasons": [],
        "created_at": created_at,
    }


def _receipt_digest_authority_context(
    receipt: Mapping[str, Any],
) -> dict[str, str]:
    fields = (
        "memex_supply_receipt_id",
        "memex_supply_digest",
        "architect_fix_publication_receipt_id",
        "architect_fix_publication_binding_digest",
        "verified_work_authority_digest",
        "authority_verification_receipt_id",
        "authority_verification_receipt_digest",
    )
    return {field: str(receipt.get(field) or "") for field in fields}


def _receipt_identity_fields(
    receipt: Mapping[str, Any],
    queue_item: Mapping[str, Any],
) -> dict[str, str]:
    fields = (
        "work_order_id",
        "foundup_id",
        "requested_operation",
        "wsp15_allocation_receipt_id",
        "wsp15_allocation_digest",
        "progressive_policy_stage_receipt_id",
        "progressive_policy_stage_digest",
        "model_runtime_binding_receipt_id",
        "model_runtime_binding_digest",
        "memex_supply_receipt_id",
        "memex_supply_digest",
        "architect_fix_publication_receipt_id",
        "architect_fix_publication_binding_digest",
        "verified_work_authority_digest",
        "authority_verification_receipt_id",
        "authority_verification_receipt_digest",
    )
    return {
        "source_dispatch_receipt_id": str(receipt.get("receipt_id") or ""),
        "queue_item_id": str(queue_item.get("queue_item_id") or ""),
        **{field: str(receipt.get(field) or "") for field in fields},
    }


def _worker_runtimes(receipt: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                str(mapping(intent).get("worker_runtime") or "")
                for intent in sequence(receipt.get("dispatch_intents"))
            }
        )
    )


def _canonical_intent(intent: Mapping[str, Any]) -> dict[str, Any]:
    return {field: intent[field] for field in WORKER_DISPATCH_INTENT_FIELDS}


def _canonical_receipt(receipt: Mapping[str, Any]) -> dict[str, Any]:
    projected = {
        field: receipt[field]
        for field in WORKER_DISPATCH_RECEIPT_FIELDS
        if field != "dispatch_intents"
    }
    projected["dispatch_intents"] = [
        _canonical_intent(mapping(intent))
        for intent in sequence(receipt["dispatch_intents"])
    ]
    return projected
