"""Runtime binding for OpenClaw signed-worker queue-loop execution.

Slice: REDDOG_SIGNED_WORKER_OPENCLAW_QUEUE_LOOP_RUNTIME_BINDING_PHASE1

This module builds the narrow OpenClaw queue-loop runner used by signed
worker-dispatch tasks. It is disabled unless explicitly requested through
environment/configuration, accepts only the OpenClaw candidate queue-review
capability, and delegates all queue advancement to the existing bounded
resident queue serial-loop bootstrap.

It does not execute shell commands, mutate repository files, create worktrees,
publish PRs, dispatch Hermes, settle rewards, write PatternMemory, or re-index
HoloIndex.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Optional

from modules.communication.moltbot_bridge.src.reddog_openclaw_hermes_0102_worker_dispatch_runtime import (
    SIGNED_WORKER_DISPATCH_TASK_SOURCE,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_binding_profile import (
    resident_queue_artifact_generator_mode,
    resident_queue_binding_enabled,
    resident_queue_draft_pr_runner_mode,
    resident_queue_evidence_command_runner_mode,
    resident_queue_materializer_mode,
    resident_queue_runtime_flag_enabled,
    resident_queue_worktree_runner_mode,
)
from modules.communication.moltbot_bridge.src.reddog_signed_worker_queue_serial_loop_runner import (
    RedDogSignedWorkerQueueSerialLoopRunner,
    SignedWorkerQueueSerialLoopRunnerConfig,
)


SIGNED_WORKER_QUEUE_LOOP_BINDING_READY = "SIGNED_WORKER_QUEUE_LOOP_BINDING_READY"
SIGNED_WORKER_QUEUE_LOOP_BINDING_NOT_REQUESTED = "SIGNED_WORKER_QUEUE_LOOP_BINDING_NOT_REQUESTED"
SIGNED_WORKER_QUEUE_LOOP_BINDING_REJECT = "SIGNED_WORKER_QUEUE_LOOP_BINDING_REJECT"

OPENCLAW_SIGNED_WORKER_RUNTIME = "openclaw"
OPENCLAW_CANDIDATE_QUEUE_REVIEW_CAPABILITY = "candidate_queue_review"
SIGNED_0102_WORKER_RUNTIME = "0102"
SIGNED_0102_BOUNDED_CODE_CHANGE_CAPABILITY = "bounded_code_change"


class SignedWorkerOpenClawQueueLoopBindingReason:
    NOT_REQUESTED = "SIGNED_WORKER_QUEUE_LOOP_BINDING_NOT_REQUESTED"
    WORK_STATE_PATH_MISSING = "REJECT_SIGNED_WORKER_QUEUE_LOOP_WORK_STATE_PATH_MISSING"
    CHAIN_RESULTS_PATH_MISSING = "REJECT_SIGNED_WORKER_QUEUE_LOOP_CHAIN_RESULTS_PATH_MISSING"
    AUTHORITY_PROFILE_PATH_MISSING = "REJECT_SIGNED_WORKER_QUEUE_LOOP_AUTHORITY_PROFILE_PATH_MISSING"
    MAX_STEPS_INVALID = "REJECT_SIGNED_WORKER_QUEUE_LOOP_MAX_STEPS_INVALID"
    NOW_EPOCH_INVALID = "REJECT_SIGNED_WORKER_QUEUE_LOOP_NOW_EPOCH_INVALID"
    DRAFT_PR_RUNNER_MODE_UNSUPPORTED = (
        "REJECT_SIGNED_WORKER_QUEUE_LOOP_DRAFT_PR_RUNNER_MODE_UNSUPPORTED"
    )
    DRAFT_PR_RUNNER_TIMEOUT_INVALID = (
        "REJECT_SIGNED_WORKER_QUEUE_LOOP_DRAFT_PR_RUNNER_TIMEOUT_INVALID"
    )
    PATTERN_MEMORY_ADMISSION_DB_PATH_INVALID = (
        "REJECT_SIGNED_WORKER_QUEUE_LOOP_PATTERN_MEMORY_ADMISSION_DB_PATH_INVALID"
    )


@dataclass(frozen=True)
class SignedWorkerOpenClawQueueLoopBindingResult:
    """Result from constructing the OpenClaw signed-worker runner."""

    accepted: bool
    status: str
    requested: bool
    runner: Optional[RedDogSignedWorkerQueueSerialLoopRunner]
    rejection_reasons: tuple[str, ...]
    work_state_path: Optional[str] = None
    chain_results_path: Optional[str] = None
    authority_profile_path: Optional[str] = None
    max_steps: Optional[int] = None
    no_shell_command_executed: bool = True
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_worktree_operation_performed: bool = True
    no_pr_created: bool = True
    no_pattern_memory_write_performed: bool = True
    no_reward_settlement_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["runner"] = None if self.runner is None else self.runner.__class__.__name__
        return payload


def is_openclaw_candidate_signed_worker_context(context: Mapping[str, Any] | None) -> bool:
    """Return True only for the signed worker task OpenClaw is allowed to claim."""

    if not isinstance(context, Mapping):
        return False
    return (
        str(context.get("source") or "") == SIGNED_WORKER_DISPATCH_TASK_SOURCE
        and str(context.get("worker_runtime") or "").strip().lower() == OPENCLAW_SIGNED_WORKER_RUNTIME
        and str(context.get("capability") or "").strip().lower() == OPENCLAW_CANDIDATE_QUEUE_REVIEW_CAPABILITY
    )


def is_0102_bounded_code_change_signed_worker_context(context: Mapping[str, Any] | None) -> bool:
    """Return True only for signed 0102 coding tasks handled at the bounded stage."""

    if not isinstance(context, Mapping):
        return False
    return (
        str(context.get("source") or "") == SIGNED_WORKER_DISPATCH_TASK_SOURCE
        and str(context.get("worker_runtime") or "").strip() == SIGNED_0102_WORKER_RUNTIME
        and str(context.get("capability") or "").strip().lower()
        == SIGNED_0102_BOUNDED_CODE_CHANGE_CAPABILITY
    )


def build_reddog_signed_worker_queue_loop_runner_from_env(
    *,
    repo_root: Path | str,
    env: Mapping[str, str],
    bootstrap: Optional[Callable[..., Any]] = None,
) -> SignedWorkerOpenClawQueueLoopBindingResult:
    """Build the OpenClaw queue-loop runner from explicit runtime config."""

    requested = resident_queue_runtime_flag_enabled(
        env,
        "REDDOG_SIGNED_WORKER_QUEUE_LOOP_RUNNER",
    )
    if not requested:
        return SignedWorkerOpenClawQueueLoopBindingResult(
            accepted=False,
            status=SIGNED_WORKER_QUEUE_LOOP_BINDING_NOT_REQUESTED,
            requested=False,
            runner=None,
            rejection_reasons=(SignedWorkerOpenClawQueueLoopBindingReason.NOT_REQUESTED,),
        )

    work_state_path = _stripped(env.get("REDDOG_AUTHORITATIVE_WORK_STATE_PATH"))
    chain_results_path = _stripped(env.get("REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH"))
    authority_profile_path = _stripped(env.get("REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH"))
    reasons: list[str] = []
    if not work_state_path:
        reasons.append(SignedWorkerOpenClawQueueLoopBindingReason.WORK_STATE_PATH_MISSING)
    if not chain_results_path:
        reasons.append(SignedWorkerOpenClawQueueLoopBindingReason.CHAIN_RESULTS_PATH_MISSING)
    if not authority_profile_path:
        reasons.append(SignedWorkerOpenClawQueueLoopBindingReason.AUTHORITY_PROFILE_PATH_MISSING)

    max_steps_raw = _stripped(env.get("REDDOG_SIGNED_WORKER_QUEUE_LOOP_MAX_STEPS")) or _stripped(
        env.get("REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_MAX_STEPS")
    )
    try:
        max_steps = int(max_steps_raw) if max_steps_raw else 1
    except ValueError:
        max_steps = 0
    if max_steps < 1:
        reasons.append(SignedWorkerOpenClawQueueLoopBindingReason.MAX_STEPS_INVALID)

    now_epoch_raw = _stripped(env.get("REDDOG_RESIDENT_QUEUE_NOW_EPOCH"))
    try:
        now_epoch = int(now_epoch_raw) if now_epoch_raw else None
    except ValueError:
        now_epoch = None
        reasons.append(SignedWorkerOpenClawQueueLoopBindingReason.NOW_EPOCH_INVALID)

    draft_pr_runner, draft_pr_reasons = _build_draft_pr_runner(
        repo_root=repo_root,
        env=env,
    )
    reasons.extend(draft_pr_reasons)
    pattern_memory_admission_sink, pattern_memory_reasons = _build_pattern_memory_admission_sink(
        repo_root=repo_root,
        env=env,
    )
    reasons.extend(pattern_memory_reasons)

    if reasons:
        return SignedWorkerOpenClawQueueLoopBindingResult(
            accepted=False,
            status=SIGNED_WORKER_QUEUE_LOOP_BINDING_REJECT,
            requested=True,
            runner=None,
            rejection_reasons=tuple(dict.fromkeys(reasons)),
            work_state_path=work_state_path,
            chain_results_path=chain_results_path,
            authority_profile_path=authority_profile_path,
            max_steps=max_steps,
        )

    bootstrap_kwargs = _bootstrap_kwargs(env)
    if draft_pr_runner is not None:
        bootstrap_kwargs["draft_pr_runner"] = draft_pr_runner
    if pattern_memory_admission_sink is not None:
        bootstrap_kwargs["pattern_memory_admission_sink"] = pattern_memory_admission_sink
    config = SignedWorkerQueueSerialLoopRunnerConfig(
        work_state_path=str(work_state_path),
        chain_results_path=str(chain_results_path),
        authority_profile_path=str(authority_profile_path),
        repo_root=Path(repo_root).resolve(),
        now_iso=_stripped(env.get("REDDOG_RESIDENT_QUEUE_NOW_ISO")) or None,
        now_epoch=now_epoch,
        max_steps=max_steps,
        bootstrap_kwargs=bootstrap_kwargs,
    )
    runner = RedDogSignedWorkerQueueSerialLoopRunner(config, bootstrap=bootstrap)
    return SignedWorkerOpenClawQueueLoopBindingResult(
        accepted=True,
        status=SIGNED_WORKER_QUEUE_LOOP_BINDING_READY,
        requested=True,
        runner=runner,
        rejection_reasons=(),
        work_state_path=work_state_path,
        chain_results_path=chain_results_path,
        authority_profile_path=authority_profile_path,
        max_steps=max_steps,
    )


def _bootstrap_kwargs(env: Mapping[str, str]) -> dict[str, Any]:
    materializer_mode = resident_queue_materializer_mode(env)
    artifact_generator_mode = resident_queue_artifact_generator_mode(env)
    worktree_runner_mode = resident_queue_worktree_runner_mode(env)
    evidence_command_runner_mode = resident_queue_evidence_command_runner_mode(env)
    pairs = {
        "work_orders_path": "REDDOG_WORK_ORDERS_PATH",
        "valve_environment_path": "REDDOG_EXECUTION_VALVE_ENV_PATH",
        "generic_writer_dryrun_result_path": "REDDOG_GENERIC_WRITER_DRYRUN_RESULT_PATH",
        "governed_shell_dryrun_result_path": "REDDOG_GOVERNED_SHELL_DRYRUN_RESULT_PATH",
        "artifact_contents_path": "REDDOG_ARTIFACT_CONTENTS_PATH",
        "artifact_generation_request_path": "REDDOG_ARTIFACT_GENERATION_REQUEST_PATH",
        "holoindex_evidence_path": "REDDOG_HOLOINDEX_EVIDENCE_PATH",
        "verifier_request_path": "REDDOG_SLICE_VERIFIER_REQUEST_PATH",
        "evidence_producer_request_path": "REDDOG_EVIDENCE_PRODUCER_REQUEST_PATH",
        "publish_request_path": "REDDOG_DRAFT_PR_PUBLISH_REQUEST_PATH",
        "ratchet_request_path": "REDDOG_OUTCOME_RATCHET_REQUEST_PATH",
        "outcome_ratchet_store_path": "REDDOG_OUTCOME_RATCHET_STORE_PATH",
        "held_out_gate_request_path": "REDDOG_HELD_OUT_GATE_REQUEST_PATH",
        "admission_request_path": "REDDOG_PATTERN_MEMORY_ADMISSION_REQUEST_PATH",
        "authority_state_path": "REDDOG_AUTHORITY_RUNTIME_STATE_PATH",
        "permission_snapshots_path": "REDDOG_PERMISSION_SNAPSHOTS_PATH",
        "principal_authority_records_path": "REDDOG_PRINCIPAL_AUTHORITY_RECORDS_PATH",
        "signer_socket_path": "REDDOG_SIGNER_SOCKET_PATH",
        "signature_verifier_backend": "REDDOG_SIGNATURE_VERIFIER_BACKEND",
        "worktree_runner_mode": "REDDOG_RESIDENT_QUEUE_WORKTREE_RUNNER_MODE",
        "artifact_generator_mode": "REDDOG_ARTIFACT_GENERATOR_MODE",
        "evidence_command_runner_mode": "REDDOG_EVIDENCE_COMMAND_RUNNER_MODE",
    }
    payload: dict[str, Any] = {}
    if materializer_mode:
        payload["work_order_materializer_mode"] = materializer_mode
    for key, env_name in pairs.items():
        value = _stripped(env.get(env_name))
        if value:
            payload[key] = value
    if artifact_generator_mode:
        payload["artifact_generator_mode"] = artifact_generator_mode
    if worktree_runner_mode:
        payload["worktree_runner_mode"] = worktree_runner_mode
    if evidence_command_runner_mode:
        payload["evidence_command_runner_mode"] = evidence_command_runner_mode
    for key, env_name in (
        ("pilot_dryrun_binding_enabled", "REDDOG_PILOT_DRYRUN_BINDING"),
        (
            "artifact_generation_request_binding_enabled",
            "REDDOG_ARTIFACT_GENERATION_REQUEST_BINDING",
        ),
        ("slice_verifier_request_binding_enabled", "REDDOG_SLICE_VERIFIER_REQUEST_BINDING"),
        ("draft_pr_publish_request_binding_enabled", "REDDOG_DRAFT_PR_PUBLISH_REQUEST_BINDING"),
        ("outcome_ratchet_request_binding_enabled", "REDDOG_OUTCOME_RATCHET_REQUEST_BINDING"),
        ("held_out_gate_request_binding_enabled", "REDDOG_HELD_OUT_GATE_REQUEST_BINDING"),
        (
            "pattern_memory_admission_request_binding_enabled",
            "REDDOG_PATTERN_MEMORY_ADMISSION_REQUEST_BINDING",
        ),
    ):
        if resident_queue_binding_enabled(env, env_name):
            payload[key] = True
    return payload


def _build_draft_pr_runner(
    *,
    repo_root: Path | str,
    env: Mapping[str, str],
) -> tuple[Any, tuple[str, ...]]:
    mode = resident_queue_draft_pr_runner_mode(env).strip().lower()
    if not mode:
        return None, ()
    if mode != "real":
        return None, (
            SignedWorkerOpenClawQueueLoopBindingReason.DRAFT_PR_RUNNER_MODE_UNSUPPORTED,
        )
    timeout_raw = _stripped(env.get("REDDOG_DRAFT_PR_RUNNER_TIMEOUT_S"))
    try:
        timeout_s = int(timeout_raw) if timeout_raw else 120
    except ValueError:
        timeout_s = 0
    if timeout_s <= 0:
        return None, (
            SignedWorkerOpenClawQueueLoopBindingReason.DRAFT_PR_RUNNER_TIMEOUT_INVALID,
        )

    from modules.foundups.agent.src.worktree_pr_runner import RealWorktreeRunner

    return RealWorktreeRunner(
        repo_root=Path(repo_root).resolve(),
        timeout_s=timeout_s,
    ), ()


def _build_pattern_memory_admission_sink(
    *,
    repo_root: Path | str,
    env: Mapping[str, str],
) -> tuple[Any, tuple[str, ...]]:
    db_path = _stripped(env.get("REDDOG_PATTERN_MEMORY_ADMISSION_DB_PATH"))
    if not db_path:
        return None, ()

    from modules.communication.moltbot_bridge.src.reddog_verified_pattern_memory_sink import (
        PatternMemorySinkConfigurationError,
        build_reddog_verified_pattern_memory_sink,
    )

    try:
        return build_reddog_verified_pattern_memory_sink(
            repo_root=repo_root,
            db_path=db_path,
        ), ()
    except PatternMemorySinkConfigurationError:
        return None, (
            SignedWorkerOpenClawQueueLoopBindingReason.PATTERN_MEMORY_ADMISSION_DB_PATH_INVALID,
        )


def _stripped(value: Any) -> str:
    return str(value or "").strip()


__all__ = [
    "OPENCLAW_CANDIDATE_QUEUE_REVIEW_CAPABILITY",
    "OPENCLAW_SIGNED_WORKER_RUNTIME",
    "SIGNED_0102_BOUNDED_CODE_CHANGE_CAPABILITY",
    "SIGNED_0102_WORKER_RUNTIME",
    "SIGNED_WORKER_QUEUE_LOOP_BINDING_NOT_REQUESTED",
    "SIGNED_WORKER_QUEUE_LOOP_BINDING_READY",
    "SIGNED_WORKER_QUEUE_LOOP_BINDING_REJECT",
    "SignedWorkerOpenClawQueueLoopBindingReason",
    "SignedWorkerOpenClawQueueLoopBindingResult",
    "build_reddog_signed_worker_queue_loop_runner_from_env",
    "is_0102_bounded_code_change_signed_worker_context",
    "is_openclaw_candidate_signed_worker_context",
]
