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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Optional


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
    BOOTSTRAP_REJECTED = "REJECT_RESIDENT_QUEUE_BOOTSTRAP_REJECTED"
    BOOTSTRAP_UNSAFE = "REJECT_RESIDENT_QUEUE_BOOTSTRAP_UNSAFE"
    BOOTSTRAP_EXCEPTION = "REJECT_RESIDENT_QUEUE_BOOTSTRAP_EXCEPTION"
    BOOTSTRAP_KWARG_CONFLICT = "REJECT_RESIDENT_QUEUE_BOOTSTRAP_KWARG_CONFLICT"


BootstrapCallable = Callable[..., Any]
_RESERVED_BOOTSTRAP_KWARGS = frozenset(
    {
        "repo_root",
        "work_state_path",
        "chain_results_path",
        "authority_profile_path",
        "requested_queue_item_id",
        "now_iso",
        "now_epoch",
        "max_steps",
    }
)

_OPENCLAW_QUEUE_RUNTIME = "openclaw"
_OPENCLAW_QUEUE_CAPABILITY = "candidate_queue_review"
_SIGNED_0102_RUNTIME = "0102"
_SIGNED_0102_BOUNDED_CODE_CAPABILITY = "bounded_code_change"
_BOUNDED_WORKER_PILOT_STAGE = "bounded_worker_pilot"
_BOUNDED_WORKER_PILOT_ACTION = "RUN_QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE"
_ARTIFACT_GENERATOR_MODE_FOUNDUPS_FUSION = "foundups_fusion"
_QUEUE_CHAIN_COMPLETE_ACTION = "STOP_QUEUE_CHAIN_COMPLETE"


@dataclass(frozen=True)
class SignedWorkerQueueSerialLoopRunnerConfig:
    """Configuration for invoking the resident queue serial-loop bootstrap."""

    work_state_path: Path | str
    chain_results_path: Path | str
    authority_profile_path: Path | str
    repo_root: Optional[Path | str] = None
    now_iso: Optional[str] = None
    now_epoch: Optional[int] = None
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

        context = _mapping(task_context)
        intent = _mapping(worker_dispatch_intent)
        _ = signed_authority_receipt
        reasons: list[str] = []

        worker_runtime = str(intent.get("worker_runtime") or context.get("worker_runtime") or "")
        capability = str(intent.get("capability") or context.get("capability") or "")
        target_kind = _target_kind(worker_runtime=worker_runtime, capability=capability)
        if target_kind is None:
            if worker_runtime not in {_OPENCLAW_QUEUE_RUNTIME, _SIGNED_0102_RUNTIME}:
                reasons.append(SignedWorkerQueueSerialLoopRunnerReason.UNSUPPORTED_WORKER_RUNTIME)
            if capability not in {_OPENCLAW_QUEUE_CAPABILITY, _SIGNED_0102_BOUNDED_CODE_CAPABILITY}:
                reasons.append(SignedWorkerQueueSerialLoopRunnerReason.UNSUPPORTED_CAPABILITY)
            if not reasons:
                reasons.append(SignedWorkerQueueSerialLoopRunnerReason.UNSUPPORTED_CAPABILITY)

        queue_item_id = str(context.get("queue_item_id") or "").strip()
        if not queue_item_id:
            reasons.append(SignedWorkerQueueSerialLoopRunnerReason.QUEUE_ITEM_MISSING)
        if not self.config.work_state_path or not self.config.chain_results_path or not self.config.authority_profile_path:
            reasons.append(SignedWorkerQueueSerialLoopRunnerReason.CONFIG_MISSING)
        if any(key in _RESERVED_BOOTSTRAP_KWARGS for key in self.config.bootstrap_kwargs):
            reasons.append(SignedWorkerQueueSerialLoopRunnerReason.BOOTSTRAP_KWARG_CONFLICT)
        if target_kind == "0102_bounded_code_change":
            reasons.extend(_bounded_code_stage_reasons(self.config, queue_item_id=queue_item_id))
        if reasons:
            return _reject(task_id, reasons)

        bootstrap = self._bootstrap or _load_bootstrap()
        try:
            result = bootstrap(
                repo_root=Path(self.config.repo_root or repo_root),
                work_state_path=self.config.work_state_path,
                chain_results_path=self.config.chain_results_path,
                authority_profile_path=self.config.authority_profile_path,
                requested_queue_item_id=queue_item_id,
                now_iso=self.config.now_iso,
                now_epoch=self.config.now_epoch,
                max_steps=self.config.max_steps,
                **dict(self.config.bootstrap_kwargs),
            )
        except Exception:
            return _reject(task_id, [SignedWorkerQueueSerialLoopRunnerReason.BOOTSTRAP_EXCEPTION])

        payload = _mapping(result)
        if hasattr(result, "to_dict"):
            payload = _mapping(result.to_dict())
        if payload.get("accepted") is not True:
            return _reject(
                task_id,
                [
                    SignedWorkerQueueSerialLoopRunnerReason.BOOTSTRAP_REJECTED,
                    *_string_list(payload.get("rejection_reasons")),
                ],
                bootstrap_result=payload,
            )
        if _unsafe_bootstrap_effect_detected(payload):
            return _reject(
                task_id,
                [SignedWorkerQueueSerialLoopRunnerReason.BOOTSTRAP_UNSAFE],
                bootstrap_result=payload,
            )
        queue_chain_complete = str(payload.get("next_action") or "") == _QUEUE_CHAIN_COMPLETE_ACTION

        return {
            "accepted": True,
            "decision": SIGNED_WORKER_QUEUE_SERIAL_LOOP_RUNNER_ACCEPT,
            "receipt_id": _receipt_id(task_id, queue_item_id, payload),
            "queue_item_id": queue_item_id,
            "bootstrap_result": dict(payload),
            "queue_chain_complete": queue_chain_complete,
            "queue_chain_requeue_required": not queue_chain_complete,
            "rejection_reasons": [],
            "no_source_repo_mutation_performed": True,
            "no_shell_command_executed": True,
            "no_holoindex_reindex_performed": bool(payload.get("no_holoindex_reindex_performed", True)),
            "no_pr_created": bool(payload.get("no_pr_created", True)),
            "no_pattern_memory_write_performed": bool(payload.get("no_pattern_memory_write_performed", True)),
            "no_reward_settlement_performed": bool(payload.get("no_reward_settlement_performed", True)),
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
        "no_pr_created": True,
        "no_pattern_memory_write_performed": True,
        "no_reward_settlement_performed": True,
    }


def _target_kind(*, worker_runtime: str, capability: str) -> str | None:
    if worker_runtime == _OPENCLAW_QUEUE_RUNTIME and capability == _OPENCLAW_QUEUE_CAPABILITY:
        return "openclaw_candidate_queue_review"
    if worker_runtime == _SIGNED_0102_RUNTIME and capability == _SIGNED_0102_BOUNDED_CODE_CAPABILITY:
        return "0102_bounded_code_change"
    return None


def _bounded_code_stage_reasons(
    config: SignedWorkerQueueSerialLoopRunnerConfig,
    *,
    queue_item_id: str,
) -> list[str]:
    reasons: list[str] = []
    if config.max_steps != 1:
        reasons.append(SignedWorkerQueueSerialLoopRunnerReason.CODE_STAGE_MAX_STEPS_INVALID)

    kwargs = dict(config.bootstrap_kwargs)
    if kwargs.get("artifact_contents_path"):
        reasons.append(SignedWorkerQueueSerialLoopRunnerReason.CODE_STATIC_ARTIFACTS_FORBIDDEN)
    if (
        not kwargs.get("artifact_generation_request_path")
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


def _read_current_plan(
    config: SignedWorkerQueueSerialLoopRunnerConfig,
    *,
    queue_item_id: str,
) -> Mapping[str, Any]:
    try:
        work_state = _read_json_mapping(Path(config.work_state_path))
        chain = _read_json_mapping(Path(config.chain_results_path))
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


def _read_json_mapping(path: Path) -> Mapping[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, Mapping) else {}


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
