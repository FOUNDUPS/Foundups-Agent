"""Runtime binding for OpenClaw signed-worker queue-loop execution.

Slice: REDDOG_SIGNED_WORKER_OPENCLAW_QUEUE_LOOP_RUNTIME_BINDING_PHASE1

Delegate signed worker tasks to the existing bounded resident serial loop.
"""

from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Optional

from modules.communication.moltbot_bridge.src.reddog_openclaw_hermes_0102_worker_dispatch_runtime import (
    SIGNED_WORKER_DISPATCH_TASK_SOURCE,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_binding_profile import (
    resident_queue_draft_pr_runner_mode,
    resident_queue_integer_epoch,
    resident_queue_now_epoch,
    resident_queue_pattern_memory_admission_db_path,
)
from modules.communication.moltbot_bridge.src.reddog_signed_worker_queue_loop_environment import (
    SignedWorkerQueueLoopEnvironment,
    project_signed_worker_queue_loop_environment,
)
from modules.communication.moltbot_bridge.src.reddog_signed_worker_queue_serial_loop_runner import (
    RedDogSignedWorkerQueueSerialLoopRunner,
    SignedWorkerQueueSerialLoopRunnerConfig,
)

SIGNED_WORKER_QUEUE_LOOP_BINDING_READY = "SIGNED_WORKER_QUEUE_LOOP_BINDING_READY"
SIGNED_WORKER_QUEUE_LOOP_BINDING_NOT_REQUESTED = (
    "SIGNED_WORKER_QUEUE_LOOP_BINDING_NOT_REQUESTED"
)
SIGNED_WORKER_QUEUE_LOOP_BINDING_REJECT = "SIGNED_WORKER_QUEUE_LOOP_BINDING_REJECT"

OPENCLAW_SIGNED_WORKER_RUNTIME = "openclaw"
OPENCLAW_CANDIDATE_QUEUE_REVIEW_CAPABILITY = "candidate_queue_review"
OPENCLAW_QUEUE_STAGE_PROGRESS_CAPABILITY = "queue_stage_progress"
OPENCLAW_INDEPENDENT_SLICE_VERIFICATION_CAPABILITY = "independent_slice_verification"
SIGNED_0102_WORKER_RUNTIME = "0102"
SIGNED_0102_BOUNDED_CODE_CHANGE_CAPABILITY = "bounded_code_change"


class SignedWorkerOpenClawQueueLoopBindingReason:
    NOT_REQUESTED = "SIGNED_WORKER_QUEUE_LOOP_BINDING_NOT_REQUESTED"
    WORK_STATE_PATH_MISSING = "REJECT_SIGNED_WORKER_QUEUE_LOOP_WORK_STATE_PATH_MISSING"
    CHAIN_RESULTS_PATH_MISSING = (
        "REJECT_SIGNED_WORKER_QUEUE_LOOP_CHAIN_RESULTS_PATH_MISSING"
    )
    AUTHORITY_PROFILE_PATH_MISSING = (
        "REJECT_SIGNED_WORKER_QUEUE_LOOP_AUTHORITY_PROFILE_PATH_MISSING"
    )
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
        payload["runner"] = (
            None if self.runner is None else self.runner.__class__.__name__
        )
        return payload


def is_openclaw_candidate_signed_worker_context(
    context: Mapping[str, Any] | None,
) -> bool:
    """Return True only for the signed worker task OpenClaw is allowed to claim."""

    if not isinstance(context, Mapping):
        return False
    return (
        str(context.get("source") or "") == SIGNED_WORKER_DISPATCH_TASK_SOURCE
        and str(context.get("worker_runtime") or "").strip().lower()
        == OPENCLAW_SIGNED_WORKER_RUNTIME
        and str(context.get("capability") or "").strip().lower()
        == OPENCLAW_CANDIDATE_QUEUE_REVIEW_CAPABILITY
    )


def is_openclaw_queue_stage_progress_signed_worker_context(
    context: Mapping[str, Any] | None,
) -> bool:
    """Return True only for signed OpenClaw queue-stage progress tasks."""

    if not isinstance(context, Mapping):
        return False
    return (
        str(context.get("source") or "") == SIGNED_WORKER_DISPATCH_TASK_SOURCE
        and str(context.get("worker_runtime") or "").strip().lower()
        == OPENCLAW_SIGNED_WORKER_RUNTIME
        and str(context.get("capability") or "").strip().lower()
        == OPENCLAW_QUEUE_STAGE_PROGRESS_CAPABILITY
    )


def is_openclaw_independent_verifier_signed_worker_context(
    context: Mapping[str, Any] | None,
) -> bool:
    """Return True only for the reserved independent verifier task."""

    if not isinstance(context, Mapping):
        return False
    return (
        str(context.get("source") or "") == SIGNED_WORKER_DISPATCH_TASK_SOURCE
        and str(context.get("worker_runtime") or "").strip().lower()
        == OPENCLAW_SIGNED_WORKER_RUNTIME
        and str(context.get("capability") or "").strip().lower()
        == OPENCLAW_INDEPENDENT_SLICE_VERIFICATION_CAPABILITY
    )


def is_0102_bounded_code_change_signed_worker_context(
    context: Mapping[str, Any] | None,
) -> bool:
    """Return True only for signed 0102 coding tasks handled at the bounded stage."""

    if not isinstance(context, Mapping):
        return False
    return (
        str(context.get("source") or "") == SIGNED_WORKER_DISPATCH_TASK_SOURCE
        and str(context.get("worker_runtime") or "").strip()
        == SIGNED_0102_WORKER_RUNTIME
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

    projected = project_signed_worker_queue_loop_environment(
        env,
        repo_root,
        now_epoch_resolver=resident_queue_now_epoch,
    )
    if not projected.requested:
        return SignedWorkerOpenClawQueueLoopBindingResult(
            accepted=False,
            status=SIGNED_WORKER_QUEUE_LOOP_BINDING_NOT_REQUESTED,
            requested=False,
            runner=None,
            rejection_reasons=(
                SignedWorkerOpenClawQueueLoopBindingReason.NOT_REQUESTED,
            ),
        )

    return _build_requested_queue_loop_runner(
        projected=projected, repo_root=repo_root, env=env, bootstrap=bootstrap
    )


def _build_requested_queue_loop_runner(
    *, projected: SignedWorkerQueueLoopEnvironment, repo_root, env, bootstrap
) -> SignedWorkerOpenClawQueueLoopBindingResult:
    reasons: list[str] = []
    if not projected.work_state_path:
        reasons.append(
            SignedWorkerOpenClawQueueLoopBindingReason.WORK_STATE_PATH_MISSING
        )
    if not projected.chain_results_path:
        reasons.append(
            SignedWorkerOpenClawQueueLoopBindingReason.CHAIN_RESULTS_PATH_MISSING
        )
    if not projected.authority_profile_path:
        reasons.append(
            SignedWorkerOpenClawQueueLoopBindingReason.AUTHORITY_PROFILE_PATH_MISSING
        )
    if projected.max_steps < 1:
        reasons.append(SignedWorkerOpenClawQueueLoopBindingReason.MAX_STEPS_INVALID)
    if not projected.now_epoch_valid:
        reasons.append(SignedWorkerOpenClawQueueLoopBindingReason.NOW_EPOCH_INVALID)
    draft_pr_runner, draft_pr_reasons = _build_draft_pr_runner(
        repo_root=repo_root,
        env=env,
    )
    reasons.extend(draft_pr_reasons)
    pattern_memory_admission_sink, pattern_memory_reasons = (
        _build_pattern_memory_admission_sink(
            repo_root=repo_root,
            env=env,
        )
    )
    reasons.extend(pattern_memory_reasons)

    if reasons:
        return _rejected_queue_loop_binding(projected, reasons)
    return _ready_queue_loop_binding(
        projected,
        repo_root,
        env,
        bootstrap,
        draft_pr_runner,
        pattern_memory_admission_sink,
    )


def _rejected_queue_loop_binding(projected, reasons):
    return SignedWorkerOpenClawQueueLoopBindingResult(
        accepted=False,
        status=SIGNED_WORKER_QUEUE_LOOP_BINDING_REJECT,
        requested=True,
        runner=None,
        rejection_reasons=tuple(dict.fromkeys(reasons)),
        work_state_path=projected.work_state_path,
        chain_results_path=projected.chain_results_path,
        authority_profile_path=projected.authority_profile_path,
        max_steps=projected.max_steps,
    )


def _ready_queue_loop_binding(
    projected, repo_root, env, bootstrap, draft_runner, memory_sink
):
    bootstrap_kwargs = dict(projected.bootstrap_kwargs)
    if draft_runner is not None:
        bootstrap_kwargs["draft_pr_runner"] = draft_runner
    if memory_sink is not None:
        bootstrap_kwargs["pattern_memory_admission_sink"] = memory_sink
    worker_dispatch_writer = _build_worker_dispatch_writer(env)
    if worker_dispatch_writer is not None:
        bootstrap_kwargs["worker_dispatch_writer"] = worker_dispatch_writer
    assurance_reservation_store = _build_assurance_reservation_store(env)
    if assurance_reservation_store is not None:
        bootstrap_kwargs["assurance_reservation_store"] = assurance_reservation_store
    config = SignedWorkerQueueSerialLoopRunnerConfig(
        work_state_path=projected.work_state_path,
        chain_results_path=projected.chain_results_path,
        authority_profile_path=projected.authority_profile_path,
        runtime_allowed_root=projected.runtime_allowed_root,
        repo_root=Path(repo_root).resolve(),
        now_iso=projected.now_iso,
        now_epoch=projected.now_epoch,
        trusted_now_epoch=(lambda value=projected.now_epoch: value)
        if projected.now_epoch is not None
        else resident_queue_integer_epoch,
        max_steps=projected.max_steps,
        bootstrap_kwargs=bootstrap_kwargs,
    )
    runner = RedDogSignedWorkerQueueSerialLoopRunner(config, bootstrap=bootstrap)
    return SignedWorkerOpenClawQueueLoopBindingResult(
        accepted=True,
        status=SIGNED_WORKER_QUEUE_LOOP_BINDING_READY,
        requested=True,
        runner=runner,
        rejection_reasons=(),
        work_state_path=projected.work_state_path,
        chain_results_path=projected.chain_results_path,
        authority_profile_path=projected.authority_profile_path,
        max_steps=projected.max_steps,
    )


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
    db_path = resident_queue_pattern_memory_admission_db_path(env, repo_root)
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


def _build_worker_dispatch_writer(env: Mapping[str, str]) -> Any:
    from modules.communication.moltbot_bridge.src.reddog_resident_queue_binding_profile import (
        resident_queue_runtime_flag_enabled,
    )

    if not resident_queue_runtime_flag_enabled(
        env, "REDDOG_WORKER_DISPATCH_AGENTDB_WRITER"
    ):
        return None

    from modules.communication.moltbot_bridge.src.reddog_openclaw_hermes_0102_worker_dispatch_runtime import (
        AgentDbSignedWorkerDispatchTaskWriter,
    )

    return AgentDbSignedWorkerDispatchTaskWriter()


def _build_assurance_reservation_store(env: Mapping[str, str]) -> Any:
    from modules.infrastructure.database.src.agent_db import AgentDB

    return AgentDB()


def _stripped(value: Any) -> str:
    return str(value or "").strip()


__all__ = [
    "OPENCLAW_CANDIDATE_QUEUE_REVIEW_CAPABILITY",
    "OPENCLAW_INDEPENDENT_SLICE_VERIFICATION_CAPABILITY",
    "OPENCLAW_QUEUE_STAGE_PROGRESS_CAPABILITY",
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
    "is_openclaw_independent_verifier_signed_worker_context",
    "is_openclaw_candidate_signed_worker_context",
    "is_openclaw_queue_stage_progress_signed_worker_context",
]
