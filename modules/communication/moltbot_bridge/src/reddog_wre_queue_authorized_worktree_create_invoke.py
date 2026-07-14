"""RedDog queue-authorized worktree-create explicit invoke guard.

Slice: REDDOG_WRE_QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_PHASE1

This module consumes a queue-authorized executor plan and queue-authorized
execution-valve decision, then calls the existing isolated worktree-create
orchestrator via an injected runner. It creates no task files, runs no
commands, enqueues no OpenClaw work, dispatches no Hermes worker, publishes no
PR, settles no rewards, and performs no HoloIndex re-index.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping, MutableSet, Optional, Sequence

from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_execution_valve_invoke import (
    QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_executor_plan_dryrun import (
    QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_worktree_create import (
    WORKTREE_CREATE_ACCEPT,
    RedDogWorktreeCreateResult,
    create_reddog_wre_worktree,
)


QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_ACCEPT = "QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_ACCEPT"
QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_REJECT = "QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_REJECT"


class QueueAuthorizedWorktreeCreateInvokeReason:
    EXPLICIT_INVOKE_MISSING = "REJECT_EXPLICIT_QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_MISSING"
    EXECUTOR_PLAN_NOT_ACCEPTED = "REJECT_QUEUE_EXECUTOR_PLAN_NOT_ACCEPTED"
    VALVE_NOT_ACCEPTED = "REJECT_QUEUE_EXECUTION_VALVE_NOT_ACCEPTED"
    EXECUTOR_PLAN_PAYLOAD_MISSING = "REJECT_EXECUTOR_PLAN_PAYLOAD_MISSING"
    VALVE_PAYLOAD_MISSING = "REJECT_VALVE_PAYLOAD_MISSING"
    RUNNER_REQUIRED = "REJECT_INJECTED_WORKTREE_RUNNER_REQUIRED"
    WORKTREE_CREATE_NOT_ACCEPTED = "REJECT_WORKTREE_CREATE_NOT_ACCEPTED"


@dataclass(frozen=True)
class QueueAuthorizedWorktreeCreateInvokeResult:
    decision: str
    rejection_reasons: List[str] = field(default_factory=list)
    worktree_create_result: Optional[RedDogWorktreeCreateResult] = None
    explicit_queue_authorized_worktree_create_requested: bool = False
    no_task_execution_performed: bool = True
    no_file_edit_performed: bool = True
    no_shell_command_executed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_pr_created: bool = True
    no_reward_settlement_performed: bool = True
    no_holoindex_reindex_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["worktree_create_result"] = (
            self.worktree_create_result.to_dict() if self.worktree_create_result else None
        )
        return payload


def _mapping(value: Any) -> Mapping[str, Any]:
    if hasattr(value, "to_dict"):
        candidate = value.to_dict()
        return candidate if isinstance(candidate, Mapping) else {}
    if isinstance(value, Mapping):
        return value
    return {}


def _reject(
    reasons: Sequence[str],
    *,
    explicit_requested: bool,
    worktree_create_result: Optional[RedDogWorktreeCreateResult] = None,
) -> QueueAuthorizedWorktreeCreateInvokeResult:
    return QueueAuthorizedWorktreeCreateInvokeResult(
        decision=QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_REJECT,
        rejection_reasons=list(dict.fromkeys(reasons)),
        worktree_create_result=worktree_create_result,
        explicit_queue_authorized_worktree_create_requested=explicit_requested,
    )


def invoke_reddog_wre_queue_authorized_worktree_create(
    *,
    explicit_queue_authorized_worktree_create_requested: bool,
    queue_executor_plan_result: Mapping[str, Any],
    queue_execution_valve_result: Mapping[str, Any],
    work_order: Mapping[str, Any],
    runner: Optional[Any],
    repo_root: Path,
    now: Optional[datetime] = None,
    locks: Optional[MutableSet[str]] = None,
) -> QueueAuthorizedWorktreeCreateInvokeResult:
    """Create an isolated worktree only from accepted queue-authorized gates."""

    if explicit_queue_authorized_worktree_create_requested is not True:
        return _reject(
            [QueueAuthorizedWorktreeCreateInvokeReason.EXPLICIT_INVOKE_MISSING],
            explicit_requested=False,
        )
    if runner is None:
        return _reject(
            [QueueAuthorizedWorktreeCreateInvokeReason.RUNNER_REQUIRED],
            explicit_requested=True,
        )

    queue_executor = _mapping(queue_executor_plan_result)
    if queue_executor.get("decision") != QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_ACCEPT:
        return _reject(
            [QueueAuthorizedWorktreeCreateInvokeReason.EXECUTOR_PLAN_NOT_ACCEPTED],
            explicit_requested=True,
        )
    executor_payload = _mapping(queue_executor.get("executor_plan_result"))
    if not executor_payload:
        return _reject(
            [QueueAuthorizedWorktreeCreateInvokeReason.EXECUTOR_PLAN_PAYLOAD_MISSING],
            explicit_requested=True,
        )

    queue_valve = _mapping(queue_execution_valve_result)
    if queue_valve.get("decision") != QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_ACCEPT:
        return _reject(
            [QueueAuthorizedWorktreeCreateInvokeReason.VALVE_NOT_ACCEPTED],
            explicit_requested=True,
        )
    valve_payload = _mapping(queue_valve.get("valve_decision"))
    if not valve_payload:
        return _reject(
            [QueueAuthorizedWorktreeCreateInvokeReason.VALVE_PAYLOAD_MISSING],
            explicit_requested=True,
        )

    worktree = create_reddog_wre_worktree(
        work_order,
        executor_payload,
        valve_payload,
        runner=runner,
        repo_root=repo_root,
        now=now,
        locks=locks,
    )
    if worktree.decision != WORKTREE_CREATE_ACCEPT:
        return _reject(
            [
                QueueAuthorizedWorktreeCreateInvokeReason.WORKTREE_CREATE_NOT_ACCEPTED,
                *worktree.rejection_reasons,
            ],
            explicit_requested=True,
            worktree_create_result=worktree,
        )

    return QueueAuthorizedWorktreeCreateInvokeResult(
        decision=QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_ACCEPT,
        rejection_reasons=[],
        worktree_create_result=worktree,
        explicit_queue_authorized_worktree_create_requested=True,
    )


__all__ = [
    "QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_ACCEPT",
    "QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_REJECT",
    "QueueAuthorizedWorktreeCreateInvokeReason",
    "QueueAuthorizedWorktreeCreateInvokeResult",
    "invoke_reddog_wre_queue_authorized_worktree_create",
]
