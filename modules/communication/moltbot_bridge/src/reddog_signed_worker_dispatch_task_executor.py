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
_RUNNER_NO_EFFECT_FIELDS = (
    "no_shell_command_executed",
    "no_source_repo_mutation_performed",
    "no_holoindex_reindex_performed",
    "no_hermes_dispatch_performed",
    "no_worktree_operation_performed",
    "no_pr_created",
    "no_live_foundup_enqueue_performed",
    "no_pattern_memory_write_performed",
    "no_reward_settlement_performed",
)


class SignedWorkerDispatchTaskExecutorReason:
    CONTEXT_MALFORMED = "REJECT_SIGNED_WORKER_CONTEXT_MALFORMED"
    SOURCE_MISMATCH = "REJECT_SIGNED_WORKER_SOURCE_MISMATCH"
    SCHEMA_MISMATCH = "REJECT_SIGNED_WORKER_SCHEMA_MISMATCH"
    INTENT_MISSING = "REJECT_SIGNED_WORKER_INTENT_MISSING"
    RECEIPT_MISSING = "REJECT_SIGNED_WORKER_RECEIPT_MISSING"
    INTENT_NOT_IN_RECEIPT = "REJECT_SIGNED_WORKER_INTENT_NOT_IN_RECEIPT"
    CONTEXT_INTENT_MISMATCH = "REJECT_SIGNED_WORKER_CONTEXT_INTENT_MISMATCH"
    WSP15_MISMATCH = "REJECT_SIGNED_WORKER_WSP15_MISMATCH"
    MODEL_RUNTIME_BINDING_MISMATCH = "REJECT_SIGNED_WORKER_MODEL_RUNTIME_BINDING_MISMATCH"
    REPORT_CONTRACT_MISMATCH = "REJECT_SIGNED_WORKER_REPORT_CONTRACT_MISMATCH"
    EXECUTION_FLAG_MISMATCH = "REJECT_SIGNED_WORKER_EXECUTION_FLAG_MISMATCH"
    RUNNER_MISSING = "REJECT_SIGNED_WORKER_RUNNER_MISSING"
    RUNNER_REJECTED = "REJECT_SIGNED_WORKER_RUNNER_REJECTED"
    RUNNER_UNSAFE = "REJECT_SIGNED_WORKER_RUNNER_UNSAFE"
    RUNNER_EFFECT_EVIDENCE_INCOMPLETE = (
        "REJECT_SIGNED_WORKER_RUNNER_EFFECT_EVIDENCE_INCOMPLETE"
    )


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
    worker_execution_performed: bool
    effect_evidence_complete: bool
    rejection_reasons: tuple[str, ...]
    worker_process_spawn_count: int = 0
    shell_command_count: int = 0
    no_shell_command_executed: bool = True
    no_source_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_worktree_operation_performed: bool = True
    no_pr_created: bool = True
    no_live_foundup_enqueue_performed: bool = True
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

    context, intent, receipt, reasons = _validated_worker_context(task_context)
    if reasons:
        return _reject(task_id, reasons, context=context)
    if runner is None:
        return _reject(task_id, [SignedWorkerDispatchTaskExecutorReason.RUNNER_MISSING], context=context)
    return _invoke_signed_worker_runner(
        task_id=task_id, repo_root=repo_root, context=context,
        intent=intent, receipt=receipt, runner=runner,
    )


def _validated_worker_context(
    task_context: Mapping[str, Any],
) -> tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any], list[str]]:
    context = _mapping(task_context)
    if not context:
        return context, {}, {}, [SignedWorkerDispatchTaskExecutorReason.CONTEXT_MALFORMED]
    reasons: list[str] = []
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
    reasons.extend(_intent_binding_reasons(context, intent, allocation))
    reasons.extend(_model_runtime_binding_reasons(context=context, intent=intent, receipt=receipt))
    reasons.extend(_report_contract_reasons(context))
    return context, intent, receipt, reasons


def _intent_binding_reasons(
    context: Mapping[str, Any], intent: Mapping[str, Any], allocation: Mapping[str, Any]
) -> list[str]:
    reasons: list[str] = []
    for context_key, intent_key in (
        ("worker_runtime", "worker_runtime"), ("worker_role", "role"),
        ("capability", "capability"),
    ):
        if intent and str(context.get(context_key) or "") != str(intent.get(intent_key) or ""):
            reasons.append(SignedWorkerDispatchTaskExecutorReason.CONTEXT_INTENT_MISMATCH)
            break
    flags = (
        "dry_run_only", "no_worker_spawn_performed",
        "no_openclaw_enqueue_performed", "no_hermes_dispatch_performed",
    )
    if intent and any(intent.get(flag) is not True for flag in flags):
        reasons.append(SignedWorkerDispatchTaskExecutorReason.EXECUTION_FLAG_MISMATCH)
    if intent and allocation and (
        str(intent.get("wsp15_allocation_receipt_id") or "")
        != str(allocation.get("receipt_id") or "")
        or str(intent.get("wsp15_allocation_digest") or "") != _digest(allocation)
    ):
        reasons.append(SignedWorkerDispatchTaskExecutorReason.WSP15_MISMATCH)
    return reasons


def _report_contract_reasons(context: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    if context.get("execution_allowed_by_dispatch_runtime") is not False:
        reasons.append(SignedWorkerDispatchTaskExecutorReason.EXECUTION_FLAG_MISMATCH)
    contract = _mapping(context.get("report_contract"))
    expected = {
        "requires_signed_authority": True, "worker_process_started": False,
        "repo_mutation_performed": False, "hermes_execution_performed": False,
    }
    if any(contract.get(field) is not value for field, value in expected.items()):
        reasons.append(SignedWorkerDispatchTaskExecutorReason.REPORT_CONTRACT_MISMATCH)
    return reasons


def _invoke_signed_worker_runner(
    *, task_id: str, repo_root: Path, context: Mapping[str, Any],
    intent: Mapping[str, Any], receipt: Mapping[str, Any],
    runner: SignedWorkerDispatchTaskRunner,
) -> SignedWorkerDispatchTaskExecutionResult:
    try:
        runner_result = _call_signed_worker_runner(
            runner, task_id, repo_root, context, intent, receipt
        )
    except Exception:
        return _reject(
            task_id,
            [SignedWorkerDispatchTaskExecutorReason.RUNNER_REJECTED],
            context=context,
            worker_execution_performed=True,
        )
    runner_payload = _mapping(runner_result)
    effects = _runner_effect_attestations(
        runner_payload,
        worker_execution_performed=True,
    )
    if runner_payload.get("accepted") is not True:
        return _reject(
            task_id,
            [SignedWorkerDispatchTaskExecutorReason.RUNNER_REJECTED, *_reasons(runner_payload)],
            context=context,
            runner_result=runner_payload,
            worker_execution_performed=True,
        )
    if effects["effect_evidence_complete"] is not True:
        return _reject(
            task_id,
            [SignedWorkerDispatchTaskExecutorReason.RUNNER_EFFECT_EVIDENCE_INCOMPLETE],
            context=context,
            runner_result=runner_payload,
            worker_execution_performed=True,
        )
    if any(
        runner_payload.get(field) is not True
        for field in ("no_source_repo_mutation_performed", "no_shell_command_executed")
    ):
        return _reject(
            task_id,
            [SignedWorkerDispatchTaskExecutorReason.RUNNER_UNSAFE],
            context=context,
            runner_result=runner_payload,
            worker_execution_performed=True,
        )
    return _accepted_execution_result(task_id, context, runner_payload)


def _call_signed_worker_runner(
    runner: SignedWorkerDispatchTaskRunner,
    task_id: str,
    repo_root: Path,
    context: Mapping[str, Any],
    intent: Mapping[str, Any],
    receipt: Mapping[str, Any],
) -> Mapping[str, Any]:
    return runner.run_signed_worker_dispatch_task(
        task_id=task_id,
        task_context=context,
        worker_dispatch_intent=intent,
        signed_authority_receipt=receipt,
        repo_root=Path(repo_root),
    )


def _accepted_execution_result(
    task_id: str, context: Mapping[str, Any], runner_payload: Mapping[str, Any]
) -> SignedWorkerDispatchTaskExecutionResult:

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
        worker_execution_performed=True,
        effect_evidence_complete=True,
        rejection_reasons=(),
        worker_process_spawn_count=_nonnegative_count(
            runner_payload.get("worker_process_spawn_count")
        ),
        shell_command_count=_observed_shell_count(runner_payload),
        no_shell_command_executed=(
            runner_payload.get("no_shell_command_executed") is True
        ),
        no_source_repo_mutation_performed=(
            runner_payload.get("no_source_repo_mutation_performed") is True
        ),
        no_holoindex_reindex_performed=(
            runner_payload.get("no_holoindex_reindex_performed") is True
        ),
        no_hermes_dispatch_performed=(
            runner_payload.get("no_hermes_dispatch_performed") is True
        ),
        no_worktree_operation_performed=(
            runner_payload.get("no_worktree_operation_performed") is True
        ),
        no_pr_created=runner_payload.get("no_pr_created") is True,
        no_live_foundup_enqueue_performed=(
            runner_payload.get("no_live_foundup_enqueue_performed") is True
        ),
        no_pattern_memory_write_performed=(
            runner_payload.get("no_pattern_memory_write_performed") is True
        ),
        no_reward_settlement_performed=(
            runner_payload.get("no_reward_settlement_performed") is True
        ),
    )


def _reject(
    task_id: str,
    reasons: Sequence[str],
    *,
    context: Mapping[str, Any] | None = None,
    runner_result: Mapping[str, Any] | None = None,
    worker_execution_performed: bool = False,
) -> SignedWorkerDispatchTaskExecutionResult:
    context = _mapping(context)
    effects = _runner_effect_attestations(
        runner_result,
        worker_execution_performed=worker_execution_performed,
    )
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
        worker_execution_performed=worker_execution_performed,
        rejection_reasons=tuple(_dedupe(reasons)),
        **effects,
    )


def _runner_effect_attestations(
    runner_result: Mapping[str, Any] | None,
    *,
    worker_execution_performed: bool,
) -> dict[str, Any]:
    if not isinstance(runner_result, Mapping):
        complete = not worker_execution_performed
        return {
            "effect_evidence_complete": complete,
            **{field: complete for field in _RUNNER_NO_EFFECT_FIELDS},
            "worker_process_spawn_count": 0,
            "shell_command_count": 0,
        }
    count_fields = ("worker_process_spawn_count", "shell_command_count")
    complete = all(
        isinstance(runner_result.get(field), bool)
        for field in _RUNNER_NO_EFFECT_FIELDS
    ) and all(_is_nonnegative_int(runner_result.get(field)) for field in count_fields)
    if complete and runner_result.get("no_shell_command_executed") is True:
        complete = runner_result.get("shell_command_count") == 0
    return {
        "effect_evidence_complete": complete,
        **{
            field: complete and runner_result.get(field) is True
            for field in _RUNNER_NO_EFFECT_FIELDS
        },
        "worker_process_spawn_count": _nonnegative_count(
            runner_result.get("worker_process_spawn_count")
        ),
        "shell_command_count": _observed_shell_count(runner_result),
    }


def _observed_shell_count(runner_result: Mapping[str, Any]) -> int:
    supplied = _nonnegative_count(runner_result.get("shell_command_count"))
    if runner_result.get("no_shell_command_executed") is False:
        return max(supplied, 1)
    return supplied


def _nonnegative_count(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    return max(value, 0)


def _is_nonnegative_int(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value >= 0


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


def _model_runtime_binding_reasons(
    *,
    context: Mapping[str, Any],
    intent: Mapping[str, Any],
    receipt: Mapping[str, Any],
) -> list[str]:
    context_id = str(context.get("model_runtime_binding_receipt_id") or "")
    context_digest = str(context.get("model_runtime_binding_digest") or "")
    intent_id = str(intent.get("model_runtime_binding_receipt_id") or "")
    intent_digest = str(intent.get("model_runtime_binding_digest") or "")
    receipt_id = str(receipt.get("model_runtime_binding_receipt_id") or "")
    receipt_digest = str(receipt.get("model_runtime_binding_digest") or "")
    pairs = ((context_id, context_digest), (intent_id, intent_digest), (receipt_id, receipt_digest))
    if any(bool(item_id) != bool(item_digest) for item_id, item_digest in pairs):
        return [SignedWorkerDispatchTaskExecutorReason.MODEL_RUNTIME_BINDING_MISMATCH]
    if not context_id and not intent_id and not receipt_id:
        return []
    if not (
        context_id
        == intent_id
        == receipt_id
        and context_digest
        == intent_digest
        == receipt_digest
        and receipt_id.startswith("reddog_model_runtime_binding:")
        and receipt_digest.startswith("sha256:")
    ):
        return [SignedWorkerDispatchTaskExecutorReason.MODEL_RUNTIME_BINDING_MISMATCH]
    return []


__all__ = [
    "SIGNED_WORKER_DISPATCH_TASK_EXECUTOR_ACCEPT",
    "SIGNED_WORKER_DISPATCH_TASK_EXECUTOR_REJECT",
    "SignedWorkerDispatchTaskExecutionResult",
    "SignedWorkerDispatchTaskExecutorReason",
    "SignedWorkerDispatchTaskRunner",
    "execute_reddog_signed_worker_dispatch_task",
    "SIGNED_WORKER_DISPATCH_TASK_SKILL",
]
