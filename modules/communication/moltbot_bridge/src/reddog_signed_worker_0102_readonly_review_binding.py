"""Runtime binding for signed 0102 read-only review worker tasks.

Slice: REDDOG_SIGNED_0102_READONLY_REVIEW_RUNTIME_BINDING_PHASE1

This module adapts signed RedDog worker-dispatch tasks for 0102 review roles
into the existing model-backed read-only audit worker. It accepts only review
capabilities and derives evidence targets from the bound WSP_15 allocation
receipt. It does not execute shell commands, mutate the repository, create
worktrees, dispatch Hermes, publish PRs, write PatternMemory, or re-index
HoloIndex.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

from modules.communication.moltbot_bridge.src.reddog_openclaw_hermes_0102_worker_dispatch_runtime import (
    SIGNED_WORKER_DISPATCH_TASK_SOURCE,
)
from modules.communication.moltbot_bridge.src.reddog_readonly_0102_audit_worker_runtime import (
    MODEL_WORKER_MODE,
    REPO_CODE_AUDIT_LANE,
)
from modules.communication.moltbot_bridge.src.reddog_readonly_audit_task_executor import (
    READONLY_AUDIT_TASK_SOURCE,
    execute_reddog_readonly_audit_task,
)
from modules.communication.moltbot_bridge.src.reddog_wsp15_allocation_receipt import (
    canonical_reddog_wsp15_allocation_digest,
    validate_reddog_wsp15_allocation_receipt,
)


SIGNED_0102_READONLY_REVIEW_BINDING_ACCEPT = "SIGNED_0102_READONLY_REVIEW_BINDING_ACCEPT"
SIGNED_0102_READONLY_REVIEW_BINDING_REJECT = "SIGNED_0102_READONLY_REVIEW_BINDING_REJECT"

SIGNED_0102_WORKER_RUNTIME = "0102"
SIGNED_0102_READONLY_CAPABILITIES = frozenset(
    {
        "architect_review",
        "adversarial_review",
        "diff_verification",
    }
)


class Signed0102ReadOnlyReviewBindingReason:
    UNSUPPORTED_CONTEXT = "REJECT_SIGNED_0102_READONLY_UNSUPPORTED_CONTEXT"
    ALLOCATION_MISSING_OR_INVALID = "REJECT_SIGNED_0102_READONLY_ALLOCATION_INVALID"
    TARGETS_MISSING = "REJECT_SIGNED_0102_READONLY_TARGETS_MISSING"
    READONLY_WORKER_REJECTED = "REJECT_SIGNED_0102_READONLY_WORKER_REJECTED"


@dataclass(frozen=True)
class Signed0102ReadOnlyReviewRunner:
    """Signed-worker runner that delegates to the read-only 0102 audit worker."""

    model_runner: Any | None = None
    holoindex_adapter: Any | None = None
    codeindex_adapter: Any | None = None
    external_research_retriever: Any | None = None
    timeout_seconds: int = 60

    def run_signed_worker_dispatch_task(
        self,
        *,
        task_id: str,
        task_context: Mapping[str, Any],
        worker_dispatch_intent: Mapping[str, Any],
        signed_authority_receipt: Mapping[str, Any],
        repo_root: Path,
    ) -> Mapping[str, Any]:
        if not is_0102_readonly_signed_worker_context(task_context):
            return _runner_reject(
                task_id=task_id,
                reasons=(Signed0102ReadOnlyReviewBindingReason.UNSUPPORTED_CONTEXT,),
            )

        allocation = _mapping(task_context.get("wsp15_allocation_receipt"))
        validation = validate_reddog_wsp15_allocation_receipt(allocation)
        if not validation.accepted:
            return _runner_reject(
                task_id=task_id,
                reasons=(
                    Signed0102ReadOnlyReviewBindingReason.ALLOCATION_MISSING_OR_INVALID,
                    *validation.rejection_reasons,
                ),
            )

        targets = _text_tuple(allocation.get("allowed_read_targets"))
        if not targets:
            return _runner_reject(
                task_id=task_id,
                reasons=(Signed0102ReadOnlyReviewBindingReason.TARGETS_MISSING,),
            )

        readonly_context = build_readonly_0102_context_from_signed_worker(
            task_id=task_id,
            task_context=task_context,
            worker_dispatch_intent=worker_dispatch_intent,
            signed_authority_receipt=signed_authority_receipt,
            allocation=allocation,
            targets=targets,
        )
        readonly_result = execute_reddog_readonly_audit_task(
            task_context=readonly_context,
            repo_root=repo_root,
            task_id=task_id,
            model_runner=self.model_runner,
            holoindex_adapter=self.holoindex_adapter,
            codeindex_adapter=self.codeindex_adapter,
            external_research_retriever=self.external_research_retriever,
            timeout_seconds=self.timeout_seconds,
        )
        payload = readonly_result.to_dict()
        if not readonly_result.accepted:
            return _runner_reject(
                task_id=task_id,
                reasons=(
                    Signed0102ReadOnlyReviewBindingReason.READONLY_WORKER_REJECTED,
                    *readonly_result.rejection_reasons,
                ),
                readonly_result=payload,
            )

        return {
            "accepted": True,
            "decision": SIGNED_0102_READONLY_REVIEW_BINDING_ACCEPT,
            "receipt_id": _receipt_id(task_id, readonly_context, payload),
            "worker_runtime": SIGNED_0102_WORKER_RUNTIME,
            "capability": str(task_context.get("capability") or ""),
            "readonly_context_digest": _digest(readonly_context),
            "readonly_result": payload,
            "rejection_reasons": [],
            "no_source_repo_mutation_performed": True,
            "no_shell_command_executed": True,
            "no_holoindex_reindex_performed": True,
            "no_hermes_dispatch_performed": True,
            "no_worktree_operation_performed": True,
            "no_pr_created": True,
            "no_pattern_memory_write_performed": True,
            "no_reward_settlement_performed": True,
        }


def is_0102_readonly_signed_worker_context(context: Mapping[str, Any] | None) -> bool:
    """Return True only for signed 0102 review tasks that are read-only."""

    if not isinstance(context, Mapping):
        return False
    return (
        str(context.get("source") or "") == SIGNED_WORKER_DISPATCH_TASK_SOURCE
        and str(context.get("worker_runtime") or "").strip().lower() == SIGNED_0102_WORKER_RUNTIME
        and str(context.get("capability") or "").strip().lower() in SIGNED_0102_READONLY_CAPABILITIES
    )


def build_readonly_0102_context_from_signed_worker(
    *,
    task_id: str,
    task_context: Mapping[str, Any],
    worker_dispatch_intent: Mapping[str, Any],
    signed_authority_receipt: Mapping[str, Any],
    allocation: Mapping[str, Any],
    targets: tuple[str, ...] | None = None,
) -> Mapping[str, Any]:
    """Build the read-only audit context consumed by the 0102 worker."""

    targets = targets or _text_tuple(allocation.get("allowed_read_targets"))
    allocation_digest = canonical_reddog_wsp15_allocation_digest(allocation)
    work_order_id = str(signed_authority_receipt.get("work_order_id") or worker_dispatch_intent.get("work_order_id") or "")
    foundup_id = str(signed_authority_receipt.get("foundup_id") or worker_dispatch_intent.get("foundup_id") or "")
    principal_id = str(signed_authority_receipt.get("principal_id") or worker_dispatch_intent.get("principal_id") or "")
    assignment = {
        "assignment_id": "signed-0102-review-" + _digest(
            {
                "task_id": task_id,
                "intent_id": worker_dispatch_intent.get("intent_id"),
                "targets": targets,
            }
        ).removeprefix("sha256:")[:16],
        "lane_id": REPO_CODE_AUDIT_LANE,
        "snapshot_receipt_id": str(task_context.get("queue_item_id") or ""),
        "allowed_read_targets": list(targets),
        "foundup_id": foundup_id,
        "principal_id": principal_id,
        "work_order_id": work_order_id,
        "queue_item_id": str(task_context.get("queue_item_id") or ""),
        "selected_slice": str(task_context.get("selected_slice") or ""),
        "signed_worker_task_id": str(task_id),
        "signed_worker_role": str(task_context.get("worker_role") or ""),
        "signed_worker_capability": str(task_context.get("capability") or ""),
        "wsp15_allocation_receipt_id": str(allocation.get("receipt_id") or ""),
        "wsp15_allocation_digest": allocation_digest,
    }
    return {
        "source": READONLY_AUDIT_TASK_SOURCE,
        "worker_mode": MODEL_WORKER_MODE,
        "principal_id": principal_id,
        "work_order_id": work_order_id,
        "foundup_id": foundup_id,
        "wsp15_allocation_receipt": dict(allocation),
        "wsp15_allocation_receipt_id": str(allocation.get("receipt_id") or ""),
        "wsp15_allocation_digest": allocation_digest,
        "swarm_receipt": {
            "swarm_id": "signed-worker-dispatch",
            "signed_worker_task_id": str(task_id),
            "source_dispatch_receipt_id": str(signed_authority_receipt.get("receipt_id") or ""),
            "queue_item_id": str(task_context.get("queue_item_id") or ""),
        },
        "assignment": assignment,
        "forbidden_actions": [
            "repo_write",
            "shell_execute",
            "git_push",
            "openclaw_enqueue",
            "holoindex_reindex",
            "hermes_dispatch",
            "worktree_create",
            "pr_publish",
        ],
        "signed_worker_binding": {
            "source": str(task_context.get("source") or ""),
            "worker_runtime": str(task_context.get("worker_runtime") or ""),
            "worker_role": str(task_context.get("worker_role") or ""),
            "capability": str(task_context.get("capability") or ""),
            "intent_id": str(worker_dispatch_intent.get("intent_id") or ""),
            "signed_authority_receipt_id": str(signed_authority_receipt.get("receipt_id") or ""),
        },
    }


def _runner_reject(
    *,
    task_id: str,
    reasons: tuple[str, ...],
    readonly_result: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    return {
        "accepted": False,
        "decision": SIGNED_0102_READONLY_REVIEW_BINDING_REJECT,
        "receipt_id": "",
        "task_id": str(task_id),
        "readonly_result": dict(readonly_result) if isinstance(readonly_result, Mapping) else None,
        "rejection_reasons": list(dict.fromkeys(str(reason) for reason in reasons if str(reason))),
        "no_source_repo_mutation_performed": True,
        "no_shell_command_executed": True,
        "no_holoindex_reindex_performed": True,
        "no_hermes_dispatch_performed": True,
        "no_worktree_operation_performed": True,
        "no_pr_created": True,
        "no_pattern_memory_write_performed": True,
        "no_reward_settlement_performed": True,
    }


def _text_tuple(value: Any) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        return ()
    return tuple(dict.fromkeys(str(item).strip() for item in value if str(item).strip()))


def _mapping(value: Any) -> Mapping[str, Any]:
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    return value if isinstance(value, Mapping) else {}


def _digest(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _receipt_id(task_id: str, readonly_context: Mapping[str, Any], readonly_result: Mapping[str, Any]) -> str:
    return "signed_0102_readonly_review_" + _digest(
        {
            "task_id": task_id,
            "readonly_context_digest": _digest(readonly_context),
            "readonly_report_digest": _mapping(readonly_result.get("report")).get("report_digest"),
        }
    ).removeprefix("sha256:")[:16]


__all__ = [
    "SIGNED_0102_READONLY_CAPABILITIES",
    "SIGNED_0102_READONLY_REVIEW_BINDING_ACCEPT",
    "SIGNED_0102_READONLY_REVIEW_BINDING_REJECT",
    "SIGNED_0102_WORKER_RUNTIME",
    "Signed0102ReadOnlyReviewBindingReason",
    "Signed0102ReadOnlyReviewRunner",
    "build_readonly_0102_context_from_signed_worker",
    "is_0102_readonly_signed_worker_context",
]
