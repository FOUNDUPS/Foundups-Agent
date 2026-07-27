"""Signed worker runner for the resident RedDog queue serial loop.

Slice: REDDOG_SIGNED_WORKER_QUEUE_SERIAL_LOOP_RUNNER_PHASE1

This adapter implements the runner protocol consumed by
reddog_signed_worker_dispatch_task_executor. It accepts only the OpenClaw
candidate signed-worker task and advances the already-built resident queue
serial loop for the bound queue item through the existing bootstrap.

The adapter creates no tasks, performs no signing, creates no worktree, runs no
shell commands, publishes no PR, settles no rewards, writes no PatternMemory,
and re-indexes no HoloIndex. Any queue-chain work must pass through the
existing serial-loop bootstrap and its handler gates.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Optional

from modules.communication.moltbot_bridge.src.reddog_runtime_json_read import (
    read_reddog_runtime_json_mapping,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    runtime_operation_lock,
)


SIGNED_WORKER_QUEUE_SERIAL_LOOP_RUNNER_ACCEPT = (
    "SIGNED_WORKER_QUEUE_SERIAL_LOOP_RUNNER_ACCEPT"
)
SIGNED_WORKER_QUEUE_SERIAL_LOOP_RUNNER_REJECT = (
    "SIGNED_WORKER_QUEUE_SERIAL_LOOP_RUNNER_REJECT"
)


class SignedWorkerQueueSerialLoopRunnerReason:
    CONFIG_MISSING = "REJECT_SIGNED_WORKER_QUEUE_SERIAL_LOOP_CONFIG_MISSING"
    QUEUE_ITEM_MISSING = "REJECT_SIGNED_WORKER_QUEUE_ITEM_MISSING"
    UNSUPPORTED_WORKER_RUNTIME = "REJECT_UNSUPPORTED_WORKER_RUNTIME"
    UNSUPPORTED_CAPABILITY = "REJECT_UNSUPPORTED_CAPABILITY"
    CODE_STAGE_NOT_READY = "REJECT_0102_BOUNDED_CODE_STAGE_NOT_READY"
    CODE_STAGE_MAX_STEPS_INVALID = "REJECT_0102_BOUNDED_CODE_MAX_STEPS_INVALID"
    CODE_ARTIFACT_GENERATION_MISSING = "REJECT_0102_BOUNDED_CODE_ARTIFACT_GENERATION_MISSING"
    CODE_STATIC_ARTIFACTS_FORBIDDEN = "REJECT_0102_BOUNDED_CODE_STATIC_ARTIFACTS_FORBIDDEN"
    CODE_ASSIGNED_STAGE_NOT_DISPATCHED = "REJECT_0102_BOUNDED_CODE_ASSIGNED_STAGE_NOT_DISPATCHED"
    QUEUE_STAGE_NOT_READY = "REJECT_OPENCLAW_QUEUE_STAGE_NOT_READY"
    QUEUE_STAGE_MAX_STEPS_INVALID = "REJECT_OPENCLAW_QUEUE_STAGE_MAX_STEPS_INVALID"
    BOOTSTRAP_REJECTED = "REJECT_RESIDENT_QUEUE_BOOTSTRAP_REJECTED"
    BOOTSTRAP_UNSAFE = "REJECT_RESIDENT_QUEUE_BOOTSTRAP_UNSAFE"
    BOOTSTRAP_EXCEPTION = "REJECT_RESIDENT_QUEUE_BOOTSTRAP_EXCEPTION"
    BOOTSTRAP_KWARG_CONFLICT = "REJECT_RESIDENT_QUEUE_BOOTSTRAP_KWARG_CONFLICT"


BootstrapCallable = Callable[..., Any]
_RESERVED_BOOTSTRAP_KWARGS = frozenset(
    {
        "repo_root",
        "runtime_allowed_root",
        "work_state_path",
        "chain_results_path",
        "authority_profile_path",
        "requested_queue_item_id",
        "now_iso",
        "now_epoch",
        "trusted_now_epoch",
        "max_steps",
    }
)

_OPENCLAW_QUEUE_RUNTIME = "openclaw"
_OPENCLAW_QUEUE_CAPABILITY = "candidate_queue_review"
_OPENCLAW_QUEUE_STAGE_CAPABILITY = "queue_stage_progress"
_OPENCLAW_INDEPENDENT_VERIFIER_CAPABILITY = "independent_slice_verification"
_SIGNED_0102_RUNTIME = "0102"
_SIGNED_0102_BOUNDED_CODE_CAPABILITY = "bounded_code_change"
_BOUNDED_WORKER_PILOT_STAGE = "bounded_worker_pilot"
_BOUNDED_WORKER_PILOT_ACTION = "RUN_QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE"
_EXACT_SHA_COMMIT_STAGE = "exact_sha_commit"
_ARTIFACT_GENERATOR_MODE_FOUNDUPS_FUSION = "foundups_fusion"
_QUEUE_CHAIN_COMPLETE_ACTION = "STOP_QUEUE_CHAIN_COMPLETE"
_POST_BOUNDED_QUEUE_STAGES = frozenset(
    {
        "verified_draft_pr_publish",
        "verified_outcome_ratchet",
        "model_feedback_admission",
        "held_out_regression_gate",
        "pattern_memory_admission",
    }
)


@dataclass(frozen=True)
class SignedWorkerQueueSerialLoopRunnerConfig:
    """Configuration for invoking the resident queue serial-loop bootstrap."""
    work_state_path: Path | str
    chain_results_path: Path | str
    authority_profile_path: Path | str
    runtime_allowed_root: Path | str
    repo_root: Optional[Path | str] = None
    now_iso: Optional[str] = None
    now_epoch: Optional[int] = None
    trusted_now_epoch: Callable[[], int] = time.time
    max_steps: int = 1
    bootstrap_kwargs: Mapping[str, Any] = field(default_factory=dict)


class RedDogSignedWorkerQueueSerialLoopRunner:
    """OpenClaw candidate runner backed by the resident queue serial loop."""
    def __init__(
        self,
        config: SignedWorkerQueueSerialLoopRunnerConfig,
        *,
        bootstrap: Optional[BootstrapCallable] = None,
    ) -> None:
        self.config = config
        self._bootstrap = bootstrap

    def run_signed_worker_dispatch_task(
        self,
        *,
        task_id: str,
        task_context: Mapping[str, Any],
        worker_dispatch_intent: Mapping[str, Any],
        signed_authority_receipt: Mapping[str, Any],
        repo_root: Path,
    ) -> Mapping[str, Any]:
        """Run one claimed OpenClaw candidate task through the queue loop."""

        _ = signed_authority_receipt
        target_kind, queue_item_id, reasons = _validate_runner_request(
            self.config,
            task_context=task_context,
            worker_dispatch_intent=worker_dispatch_intent,
        )
        if reasons:
            return _reject(task_id, reasons)

        try:
            result = _invoke_bootstrap(
                self.config,
                bootstrap=self._bootstrap or _load_bootstrap(),
                repo_root=repo_root,
                queue_item_id=queue_item_id,
                target_kind=target_kind,
            )
        except Exception:
            return _reject(task_id, [SignedWorkerQueueSerialLoopRunnerReason.BOOTSTRAP_EXCEPTION])

        payload = _mapping(result.to_dict() if hasattr(result, "to_dict") else result)
        rejection = _bootstrap_rejection(task_id, target_kind, payload)
        return rejection or _accepted_runner_result(
            task_id, queue_item_id, target_kind, payload
        )


def _validate_runner_request(
    config: SignedWorkerQueueSerialLoopRunnerConfig,
    *,
    task_context: Mapping[str, Any],
    worker_dispatch_intent: Mapping[str, Any],
) -> tuple[str | None, str, list[str]]:
    context = _mapping(task_context)
    intent = _mapping(worker_dispatch_intent)
    runtime = str(intent.get("worker_runtime") or context.get("worker_runtime") or "")
    capability = str(intent.get("capability") or context.get("capability") or "")
    target_kind = _target_kind(worker_runtime=runtime, capability=capability)
    reasons: list[str] = []
    if target_kind is None:
        if runtime not in {_OPENCLAW_QUEUE_RUNTIME, _SIGNED_0102_RUNTIME}:
            reasons.append(SignedWorkerQueueSerialLoopRunnerReason.UNSUPPORTED_WORKER_RUNTIME)
        reasons.append(SignedWorkerQueueSerialLoopRunnerReason.UNSUPPORTED_CAPABILITY)
    queue_item_id = str(context.get("queue_item_id") or "").strip()
    if not queue_item_id:
        reasons.append(SignedWorkerQueueSerialLoopRunnerReason.QUEUE_ITEM_MISSING)
    if not all(
        (config.runtime_allowed_root, config.work_state_path, config.chain_results_path,
         config.authority_profile_path)
    ):
        reasons.append(SignedWorkerQueueSerialLoopRunnerReason.CONFIG_MISSING)
    if any(key in _RESERVED_BOOTSTRAP_KWARGS for key in config.bootstrap_kwargs):
        reasons.append(SignedWorkerQueueSerialLoopRunnerReason.BOOTSTRAP_KWARG_CONFLICT)
    stage_checks = {
        "0102_bounded_code_change": _bounded_code_stage_reasons,
        "openclaw_queue_stage_progress": _queue_stage_progress_reasons,
        "openclaw_independent_slice_verification": _independent_verifier_stage_reasons,
    }
    if target_kind in stage_checks:
        reasons.extend(stage_checks[target_kind](config, queue_item_id=queue_item_id))
    return target_kind, queue_item_id, list(dict.fromkeys(reasons))
def _invoke_bootstrap(
    config: SignedWorkerQueueSerialLoopRunnerConfig,
    *,
    bootstrap: BootstrapCallable,
    repo_root: Path,
    queue_item_id: str,
    target_kind: str | None,
) -> Any:
    assigned_max_steps = (
        2 if target_kind == "0102_bounded_code_change" else 1
    )
    return bootstrap(
        repo_root=Path(config.repo_root or repo_root),
        runtime_allowed_root=config.runtime_allowed_root,
        work_state_path=config.work_state_path,
        chain_results_path=config.chain_results_path,
        authority_profile_path=config.authority_profile_path,
        requested_queue_item_id=queue_item_id,
        now_iso=config.now_iso,
        now_epoch=config.now_epoch,
        trusted_now_epoch=config.trusted_now_epoch,
        max_steps=assigned_max_steps,
        **dict(config.bootstrap_kwargs),
    )
def _bootstrap_rejection(
    task_id: str,
    target_kind: str | None,
    payload: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    if payload.get("accepted") is not True:
        return _reject(
            task_id,
            [SignedWorkerQueueSerialLoopRunnerReason.BOOTSTRAP_REJECTED,
             *_string_list(payload.get("rejection_reasons"))],
            bootstrap_result=payload,
        )
    if _unsafe_bootstrap_effect_detected(payload):
        return _reject(
            task_id,
            [SignedWorkerQueueSerialLoopRunnerReason.BOOTSTRAP_UNSAFE],
            bootstrap_result=payload,
        )
    dispatched = set(_string_list(payload.get("dispatched_stages")))
    if target_kind == "0102_bounded_code_change" and not {
        _BOUNDED_WORKER_PILOT_STAGE,
        _EXACT_SHA_COMMIT_STAGE,
    }.issubset(dispatched):
        return _reject(
            task_id,
            [SignedWorkerQueueSerialLoopRunnerReason.CODE_ASSIGNED_STAGE_NOT_DISPATCHED],
            bootstrap_result=payload,
        )
    return None


def _accepted_runner_result(
    task_id: str,
    queue_item_id: str,
    target_kind: str | None,
    payload: Mapping[str, Any],
) -> Mapping[str, Any]:
    chain_complete = str(payload.get("next_action") or "") == _QUEUE_CHAIN_COMPLETE_ACTION
    assigned_complete = target_kind in {
        "0102_bounded_code_change",
        "openclaw_independent_slice_verification",
    }
    return {
        "accepted": True,
        "decision": SIGNED_WORKER_QUEUE_SERIAL_LOOP_RUNNER_ACCEPT,
        "receipt_id": _receipt_id(task_id, queue_item_id, payload),
        "queue_item_id": queue_item_id,
        "bootstrap_result": dict(payload),
        "queue_chain_complete": chain_complete,
        "assigned_stage_complete": assigned_complete,
        "queue_chain_requeue_required": payload.get("queue_chain_requeue_required") is True
        or (not chain_complete and not assigned_complete),
        "retry_at": str(payload.get("retry_at") or "") or None,
        "rejection_reasons": [],
        "no_source_repo_mutation_performed": True,
        "no_shell_command_executed": True,
        "no_holoindex_reindex_performed": payload.get("no_holoindex_reindex_performed") is True,
        "no_hermes_dispatch_performed": payload.get("no_hermes_dispatch_performed") is True,
        "no_worktree_operation_performed": payload.get("no_worktree_created") is True,
        "no_pr_created": payload.get("no_pr_created") is True,
        "no_live_foundup_enqueue_performed": True,
        "no_pattern_memory_write_performed": payload.get("no_pattern_memory_write_performed") is True,
        "no_reward_settlement_performed": payload.get("no_reward_settlement_performed") is True,
        "worker_process_spawn_count": _nonnegative_count(payload.get("worker_process_spawn_count")),
        "shell_command_count": _nonnegative_count(payload.get("shell_command_count")),
    }


def _load_bootstrap() -> BootstrapCallable:
    from modules.communication.moltbot_bridge.src.reddog_main_resident_queue_serial_loop_bootstrap import (
        run_reddog_main_resident_queue_serial_loop_bootstrap,
    )

    return run_reddog_main_resident_queue_serial_loop_bootstrap


def _mapping(value: Any) -> Mapping[str, Any]:
    if hasattr(value, "to_dict"):
        candidate = value.to_dict()
        return candidate if isinstance(candidate, Mapping) else {}
    return value if isinstance(value, Mapping) else {}


def _string_list(value: Any) -> list[str]:
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value if str(item or "").strip()]
    return []


def _digest(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _receipt_id(task_id: str, queue_item_id: str, bootstrap_result: Mapping[str, Any]) -> str:
    return "signed_worker_queue_loop_" + _digest(
        {
            "task_id": task_id,
            "queue_item_id": queue_item_id,
            "store_revision": bootstrap_result.get("store_revision"),
            "next_action": bootstrap_result.get("next_action"),
        }
    ).removeprefix("sha256:")[:16]


def _unsafe_bootstrap_effect_detected(payload: Mapping[str, Any]) -> bool:
    """Reject effects outside the signed queue-loop boundary.

    The serial-loop bootstrap is allowed to create an isolated worktree and
    materialize bounded artifacts there after the upstream valve and writer
    gates accept. That makes ``no_repo_mutation_performed`` false by design.
    The runner still fails closed for side effects that are not permitted in
    this OpenClaw queue-review handoff.
    """

    guarded_true_flags = (
        "no_shell_command_executed",
        "no_openclaw_enqueue_performed",
        "no_hermes_dispatch_performed",
        "no_holoindex_reindex_performed",
        "no_reward_settlement_performed",
    )
    if any(payload.get(flag) is not True for flag in guarded_true_flags):
        return True
    dispatched = set(_string_list(payload.get("dispatched_stages")))
    if (
        payload.get("no_pattern_memory_write_performed") is not True
        and "pattern_memory_admission" not in dispatched
    ):
        return True
    if payload.get("no_pr_created") is not True and "verified_draft_pr_publish" not in dispatched:
        return True
    return False


def _reject(
    task_id: str,
    reasons: list[str],
    *,
    bootstrap_result: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    return {
        "accepted": False,
        "decision": SIGNED_WORKER_QUEUE_SERIAL_LOOP_RUNNER_REJECT,
        "receipt_id": "",
        "task_id": task_id,
        "bootstrap_result": dict(bootstrap_result) if isinstance(bootstrap_result, Mapping) else None,
        "rejection_reasons": list(dict.fromkeys(reason for reason in reasons if reason)),
        "no_source_repo_mutation_performed": True,
        "no_shell_command_executed": True,
        "no_holoindex_reindex_performed": True,
        "no_hermes_dispatch_performed": True,
        "no_worktree_operation_performed": True,
        "no_pr_created": True,
        "no_live_foundup_enqueue_performed": True,
        "no_pattern_memory_write_performed": True,
        "no_reward_settlement_performed": True,
        "worker_process_spawn_count": 0,
        "shell_command_count": 0,
    }


def _nonnegative_count(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    return max(value, 0)


def _target_kind(*, worker_runtime: str, capability: str) -> str | None:
    if worker_runtime == _OPENCLAW_QUEUE_RUNTIME and capability == _OPENCLAW_QUEUE_CAPABILITY:
        return "openclaw_candidate_queue_review"
    if worker_runtime == _OPENCLAW_QUEUE_RUNTIME and capability == _OPENCLAW_QUEUE_STAGE_CAPABILITY:
        return "openclaw_queue_stage_progress"
    if (
        worker_runtime == _OPENCLAW_QUEUE_RUNTIME
        and capability == _OPENCLAW_INDEPENDENT_VERIFIER_CAPABILITY
    ):
        return "openclaw_independent_slice_verification"
    if worker_runtime == _SIGNED_0102_RUNTIME and capability == _SIGNED_0102_BOUNDED_CODE_CAPABILITY:
        return "0102_bounded_code_change"
    return None


def _bounded_code_stage_reasons(
    config: SignedWorkerQueueSerialLoopRunnerConfig,
    *,
    queue_item_id: str,
) -> list[str]:
    reasons: list[str] = []
    if config.max_steps < 2:
        reasons.append(SignedWorkerQueueSerialLoopRunnerReason.CODE_STAGE_MAX_STEPS_INVALID)

    kwargs = dict(config.bootstrap_kwargs)
    if kwargs.get("artifact_contents_path"):
        reasons.append(SignedWorkerQueueSerialLoopRunnerReason.CODE_STATIC_ARTIFACTS_FORBIDDEN)
    artifact_request_available = bool(
        kwargs.get("artifact_generation_request_path")
        or kwargs.get("artifact_generation_request_binding_enabled")
    )
    if (
        not artifact_request_available
        or str(kwargs.get("artifact_generator_mode") or "") != _ARTIFACT_GENERATOR_MODE_FOUNDUPS_FUSION
    ):
        reasons.append(SignedWorkerQueueSerialLoopRunnerReason.CODE_ARTIFACT_GENERATION_MISSING)

    plan = _read_current_plan(config, queue_item_id=queue_item_id)
    if (
        not plan
        or plan.get("accepted") is not True
        or plan.get("current_stage") != _BOUNDED_WORKER_PILOT_STAGE
        or plan.get("next_action") != _BOUNDED_WORKER_PILOT_ACTION
    ):
        reasons.append(SignedWorkerQueueSerialLoopRunnerReason.CODE_STAGE_NOT_READY)
    return reasons


def _queue_stage_progress_reasons(
    config: SignedWorkerQueueSerialLoopRunnerConfig,
    *,
    queue_item_id: str,
) -> list[str]:
    reasons: list[str] = []
    if config.max_steps < 1:
        reasons.append(SignedWorkerQueueSerialLoopRunnerReason.QUEUE_STAGE_MAX_STEPS_INVALID)

    plan = _read_current_plan(config, queue_item_id=queue_item_id)
    if (
        not plan
        or plan.get("accepted") is not True
        or str(plan.get("current_stage") or "") not in _POST_BOUNDED_QUEUE_STAGES
    ):
        reasons.append(SignedWorkerQueueSerialLoopRunnerReason.QUEUE_STAGE_NOT_READY)
    return reasons


def _independent_verifier_stage_reasons(
    config: SignedWorkerQueueSerialLoopRunnerConfig,
    *,
    queue_item_id: str,
) -> list[str]:
    reasons: list[str] = []
    if config.max_steps < 1:
        reasons.append(
            SignedWorkerQueueSerialLoopRunnerReason.QUEUE_STAGE_MAX_STEPS_INVALID
        )
    plan = _read_current_plan(config, queue_item_id=queue_item_id)
    if (
        not plan
        or plan.get("accepted") is not True
        or str(plan.get("current_stage") or "") != "slice_verifier"
    ):
        reasons.append(SignedWorkerQueueSerialLoopRunnerReason.QUEUE_STAGE_NOT_READY)
    return reasons


def _read_current_plan(
    config: SignedWorkerQueueSerialLoopRunnerConfig,
    *,
    queue_item_id: str,
) -> Mapping[str, Any]:
    try:
        work_state = _read_json_mapping(
            Path(config.work_state_path),
            allowed_root=config.runtime_allowed_root,
        )
        chain = _read_json_mapping(
            Path(config.chain_results_path),
            allowed_root=config.runtime_allowed_root,
        )
    except Exception:
        return {}
    if not work_state:
        return {}
    try:
        from modules.communication.moltbot_bridge.src.reddog_resident_queue_orchestration_plan import (
            plan_reddog_resident_queue_orchestration,
        )

        plan = plan_reddog_resident_queue_orchestration(
            work_state,
            chain_results=_stage_results(chain),
            requested_queue_item_id=queue_item_id,
            now_iso=config.now_iso,
        )
    except Exception:
        return {}
    return plan.to_dict()


def _read_json_mapping(
    path: Path,
    *,
    allowed_root: Path | str,
) -> Mapping[str, Any]:
    with runtime_operation_lock(str(path) + ".operation"):
        return read_reddog_runtime_json_mapping(path, allowed_root=allowed_root)


def _stage_results(state: Mapping[str, Any]) -> Mapping[str, Mapping[str, Any]]:
    raw = state.get("stage_results") if state.get("schema_version") == "reddog_resident_queue_chain_results.v1" else state
    if not isinstance(raw, Mapping):
        return {}
    return {str(key): value for key, value in raw.items() if isinstance(value, Mapping)}


__all__ = [
    "RedDogSignedWorkerQueueSerialLoopRunner",
    "SIGNED_WORKER_QUEUE_SERIAL_LOOP_RUNNER_ACCEPT",
    "SIGNED_WORKER_QUEUE_SERIAL_LOOP_RUNNER_REJECT",
    "SignedWorkerQueueSerialLoopRunnerConfig",
    "SignedWorkerQueueSerialLoopRunnerReason",
]
