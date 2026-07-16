"""Execute one RedDog signed worker-dispatch AgentDB task.

Slice: REDDOG_SIGNED_WORKER_TASK_OPENCLAW_CLAIM_RUNTIME_PHASE1

This is the OpenClaw task-consumer seam for AgentDB tasks published by
REDDOG_OPENCLAW_HERMES_0102_WORKER_DISPATCH_RUNTIME_PHASE1. It validates the
signed worker-dispatch task context and then delegates to an explicitly
injected worker runner. No default runner is created here.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, Protocol, Sequence

from modules.communication.moltbot_bridge.src.reddog_openclaw_hermes_0102_worker_dispatch_runtime import (
    SIGNED_WORKER_DISPATCH_TASK_SKILL,
    SIGNED_WORKER_DISPATCH_TASK_SOURCE,
    WORKER_DISPATCH_RUNTIME_SCHEMA_VERSION,
)


SIGNED_WORKER_DISPATCH_TASK_EXECUTOR_ACCEPT = "SIGNED_WORKER_DISPATCH_TASK_EXECUTOR_ACCEPT"
SIGNED_WORKER_DISPATCH_TASK_EXECUTOR_REJECT = "SIGNED_WORKER_DISPATCH_TASK_EXECUTOR_REJECT"


class SignedWorkerDispatchTaskExecutorReason:
    CONTEXT_MALFORMED = "REJECT_SIGNED_WORKER_CONTEXT_MALFORMED"
    SOURCE_MISMATCH = "REJECT_SIGNED_WORKER_SOURCE_MISMATCH"
    SCHEMA_MISMATCH = "REJECT_SIGNED_WORKER_SCHEMA_MISMATCH"
    INTENT_MISSING = "REJECT_SIGNED_WORKER_INTENT_MISSING"
    RECEIPT_MISSING = "REJECT_SIGNED_WORKER_RECEIPT_MISSING"
    INTENT_NOT_IN_RECEIPT = "REJECT_SIGNED_WORKER_INTENT_NOT_IN_RECEIPT"
    CONTEXT_INTENT_MISMATCH = "REJECT_SIGNED_WORKER_CONTEXT_INTENT_MISMATCH"
    WSP15_MISMATCH = "REJECT_SIGNED_WORKER_WSP15_MISMATCH"
    REPORT_CONTRACT_MISMATCH = "REJECT_SIGNED_WORKER_REPORT_CONTRACT_MISMATCH"
    EXECUTION_FLAG_MISMATCH = "REJECT_SIGNED_WORKER_EXECUTION_FLAG_MISMATCH"
    RUNNER_MISSING = "REJECT_SIGNED_WORKER_RUNNER_MISSING"
    RUNNER_REJECTED = "REJECT_SIGNED_WORKER_RUNNER_REJECTED"
    RUNNER_UNSAFE = "REJECT_SIGNED_WORKER_RUNNER_UNSAFE"


class SignedWorkerDispatchTaskRunner(Protocol):
    """Injected runner for an already-validated signed worker task."""

    def run_signed_worker_dispatch_task(
        self,
        *,
        task_id: str,
        task_context: Mapping[str, Any],
        worker_dispatch_intent: Mapping[str, Any],
        signed_authority_receipt: Mapping[str, Any],
        repo_root: Path,
    ) -> Mapping[str, Any]: ...


@dataclass(frozen=True)
class SignedWorkerDispatchTaskExecutionResult:
    accepted: bool
    decision: str
    task_id: str
    executor: str
    receipt_id: str
    worker_role: str
    worker_runtime: str
    capability: str
    runner_result: Optional[Mapping[str, Any]]
    rejection_reasons: tuple[str, ...]
    no_shell_command_executed: bool = True
    no_source_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_pr_created: bool = True
    no_pattern_memory_write_performed: bool = True
    no_reward_settlement_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["runner_result"] = dict(self.runner_result) if isinstance(self.runner_result, Mapping) else None
        payload["rejection_reasons"] = list(self.rejection_reasons)
        return payload


def execute_reddog_signed_worker_dispatch_task(
    *,
    task_context: Mapping[str, Any],
    task_id: str,
    repo_root: Path,
    runner: Optional[SignedWorkerDispatchTaskRunner] = None,
) -> SignedWorkerDispatchTaskExecutionResult:
    """Validate and execute one signed worker-dispatch task via injected runner."""

    context = _mapping(task_context)
    reasons: list[str] = []
    if not context:
        return _reject(task_id, [SignedWorkerDispatchTaskExecutorReason.CONTEXT_MALFORMED])
    if context.get("source") != SIGNED_WORKER_DISPATCH_TASK_SOURCE:
        reasons.append(SignedWorkerDispatchTaskExecutorReason.SOURCE_MISMATCH)
    if context.get("schema_version") != WORKER_DISPATCH_RUNTIME_SCHEMA_VERSION:
        reasons.append(SignedWorkerDispatchTaskExecutorReason.SCHEMA_MISMATCH)

    intent = _mapping(context.get("worker_dispatch_intent"))
    receipt = _mapping(context.get("signed_authority_worker_dispatch_receipt"))
    allocation = _mapping(context.get("wsp15_allocation_receipt"))
    if not intent:
        reasons.append(SignedWorkerDispatchTaskExecutorReason.INTENT_MISSING)
    if not receipt:
        reasons.append(SignedWorkerDispatchTaskExecutorReason.RECEIPT_MISSING)
    if intent and receipt and not _receipt_contains_intent(receipt, intent):
        reasons.append(SignedWorkerDispatchTaskExecutorReason.INTENT_NOT_IN_RECEIPT)

    if intent:
        for context_key, intent_key in (
            ("worker_runtime", "worker_runtime"),
            ("worker_role", "role"),
            ("capability", "capability"),
        ):
            if str(context.get(context_key) or "") != str(intent.get(intent_key) or ""):
                reasons.append(SignedWorkerDispatchTaskExecutorReason.CONTEXT_INTENT_MISMATCH)
                break
        if intent.get("dry_run_only") is not True:
            reasons.append(SignedWorkerDispatchTaskExecutorReason.EXECUTION_FLAG_MISMATCH)
        if intent.get("no_worker_spawn_performed") is not True:
            reasons.append(SignedWorkerDispatchTaskExecutorReason.EXECUTION_FLAG_MISMATCH)
        if intent.get("no_openclaw_enqueue_performed") is not True:
            reasons.append(SignedWorkerDispatchTaskExecutorReason.EXECUTION_FLAG_MISMATCH)
        if intent.get("no_hermes_dispatch_performed") is not True:
            reasons.append(SignedWorkerDispatchTaskExecutorReason.EXECUTION_FLAG_MISMATCH)

    if intent and allocation:
        if str(intent.get("wsp15_allocation_receipt_id") or "") != str(allocation.get("receipt_id") or ""):
            reasons.append(SignedWorkerDispatchTaskExecutorReason.WSP15_MISMATCH)
        if str(intent.get("wsp15_allocation_digest") or "") != _digest(allocation):
            reasons.append(SignedWorkerDispatchTaskExecutorReason.WSP15_MISMATCH)

    if context.get("execution_allowed_by_dispatch_runtime") is not False:
        reasons.append(SignedWorkerDispatchTaskExecutorReason.EXECUTION_FLAG_MISMATCH)
    contract = _mapping(context.get("report_contract"))
    if (
        contract.get("requires_signed_authority") is not True
        or contract.get("worker_process_started") is not False
        or contract.get("repo_mutation_performed") is not False
        or contract.get("hermes_execution_performed") is not False
    ):
        reasons.append(SignedWorkerDispatchTaskExecutorReason.REPORT_CONTRACT_MISMATCH)

    if reasons:
        return _reject(task_id, reasons, context=context)
    if runner is None:
        return _reject(task_id, [SignedWorkerDispatchTaskExecutorReason.RUNNER_MISSING], context=context)

    try:
        runner_result = runner.run_signed_worker_dispatch_task(
            task_id=task_id,
            task_context=context,
            worker_dispatch_intent=intent,
            signed_authority_receipt=receipt,
            repo_root=Path(repo_root),
        )
    except Exception:
        return _reject(task_id, [SignedWorkerDispatchTaskExecutorReason.RUNNER_REJECTED], context=context)

    runner_payload = _mapping(runner_result)
    if runner_payload.get("accepted") is not True:
        return _reject(
            task_id,
            [SignedWorkerDispatchTaskExecutorReason.RUNNER_REJECTED, *_reasons(runner_payload)],
            context=context,
            runner_result=runner_payload,
        )
    if runner_payload.get("no_source_repo_mutation_performed") is not True:
        return _reject(
            task_id,
            [SignedWorkerDispatchTaskExecutorReason.RUNNER_UNSAFE],
            context=context,
            runner_result=runner_payload,
        )
    if runner_payload.get("no_shell_command_executed") is not True:
        return _reject(
            task_id,
            [SignedWorkerDispatchTaskExecutorReason.RUNNER_UNSAFE],
            context=context,
            runner_result=runner_payload,
        )

    return SignedWorkerDispatchTaskExecutionResult(
        accepted=True,
        decision=SIGNED_WORKER_DISPATCH_TASK_EXECUTOR_ACCEPT,
        task_id=str(task_id),
        executor="reddog:signed_worker_dispatch",
        receipt_id=_result_receipt_id(task_id, context, runner_payload),
        worker_role=str(context.get("worker_role") or ""),
        worker_runtime=str(context.get("worker_runtime") or ""),
        capability=str(context.get("capability") or ""),
        runner_result=dict(runner_payload),
        rejection_reasons=(),
    )


def _reject(
    task_id: str,
    reasons: Sequence[str],
    *,
    context: Mapping[str, Any] | None = None,
    runner_result: Mapping[str, Any] | None = None,
) -> SignedWorkerDispatchTaskExecutionResult:
    context = _mapping(context)
    return SignedWorkerDispatchTaskExecutionResult(
        accepted=False,
        decision=SIGNED_WORKER_DISPATCH_TASK_EXECUTOR_REJECT,
        task_id=str(task_id),
        executor="reddog:signed_worker_dispatch",
        receipt_id="",
        worker_role=str(context.get("worker_role") or ""),
        worker_runtime=str(context.get("worker_runtime") or ""),
        capability=str(context.get("capability") or ""),
        runner_result=dict(runner_result) if isinstance(runner_result, Mapping) else None,
        rejection_reasons=tuple(_dedupe(reasons)),
    )


def _mapping(value: Any) -> Mapping[str, Any]:
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    return value if isinstance(value, Mapping) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _dedupe(values: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if str(value or "").strip()))


def _reasons(payload: Mapping[str, Any]) -> list[str]:
    raw = payload.get("rejection_reasons")
    if isinstance(raw, list):
        return _dedupe([str(value) for value in raw])
    if isinstance(raw, tuple):
        return _dedupe([str(value) for value in raw])
    return []


def _digest(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _result_receipt_id(task_id: str, context: Mapping[str, Any], runner_result: Mapping[str, Any]) -> str:
    return "signed_worker_task_execution_" + _digest(
        {
            "task_id": task_id,
            "intent_id": _mapping(context.get("worker_dispatch_intent")).get("intent_id"),
            "runner_receipt_id": runner_result.get("receipt_id"),
        }
    ).removeprefix("sha256:")[:16]


def _receipt_contains_intent(receipt: Mapping[str, Any], intent: Mapping[str, Any]) -> bool:
    intent_id = str(intent.get("intent_id") or "")
    return intent_id in {
        str(_mapping(value).get("intent_id") or "")
        for value in _list(receipt.get("dispatch_intents"))
    }


__all__ = [
    "SIGNED_WORKER_DISPATCH_TASK_EXECUTOR_ACCEPT",
    "SIGNED_WORKER_DISPATCH_TASK_EXECUTOR_REJECT",
    "SignedWorkerDispatchTaskExecutionResult",
    "SignedWorkerDispatchTaskExecutorReason",
    "SignedWorkerDispatchTaskRunner",
    "execute_reddog_signed_worker_dispatch_task",
    "SIGNED_WORKER_DISPATCH_TASK_SKILL",
]
