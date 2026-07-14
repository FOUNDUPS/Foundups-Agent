"""RedDog queue-authorized executor-plan dry-run bridge.

Slice: REDDOG_WRE_QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_PHASE1

This module bridges an accepted queue-authorized work-order invocation result
into the existing WRE isolated worktree executor dry-run planner. It emits only
a proposed executor plan and phase receipts; it does not open the execution
valve, create worktrees, run commands, enqueue OpenClaw, dispatch Hermes, edit
files, create PRs, or re-index HoloIndex.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping, MutableSet, Optional, Sequence

from modules.communication.moltbot_bridge.src.reddog_wre_executor_dryrun import (
    EXECUTOR_PLAN_ACCEPT,
    WREExecutorDryRunResult,
    plan_wre_isolated_worktree_execution_dryrun,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_verified_authority_work_order_invoke import (
    QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_ACCEPT,
)


QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_ACCEPT = "QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_ACCEPT"
QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_REJECT = "QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_REJECT"


class QueueAuthorizedExecutorPlanDryRunReason:
    EXPLICIT_DRYRUN_MISSING = "REJECT_EXPLICIT_QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_MISSING"
    WORK_ORDER_INVOCATION_NOT_ACCEPTED = "REJECT_QUEUE_WORK_ORDER_INVOCATION_NOT_ACCEPTED"
    INVOCATION_PAYLOAD_MISSING = "REJECT_INVOCATION_PAYLOAD_MISSING"
    EXECUTOR_PLAN_NOT_ACCEPTED = "REJECT_EXECUTOR_PLAN_NOT_ACCEPTED"


@dataclass(frozen=True)
class QueueAuthorizedExecutorPlanDryRunResult:
    decision: str
    rejection_reasons: List[str] = field(default_factory=list)
    executor_plan_result: Optional[WREExecutorDryRunResult] = None
    explicit_queue_authorized_executor_plan_requested: bool = False
    no_execution_valve_opened: bool = True
    no_worker_spawn_performed: bool = True
    no_worktree_created: bool = True
    no_shell_command_executed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_pr_created: bool = True
    no_reward_settlement_performed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["executor_plan_result"] = (
            self.executor_plan_result.to_dict() if self.executor_plan_result else None
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
    executor_plan_result: Optional[WREExecutorDryRunResult] = None,
) -> QueueAuthorizedExecutorPlanDryRunResult:
    return QueueAuthorizedExecutorPlanDryRunResult(
        decision=QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_REJECT,
        rejection_reasons=list(dict.fromkeys(reasons)),
        executor_plan_result=executor_plan_result,
        explicit_queue_authorized_executor_plan_requested=explicit_requested,
    )


def plan_reddog_wre_queue_authorized_executor_dryrun(
    *,
    explicit_queue_authorized_executor_plan_requested: bool,
    queue_work_order_invocation_result: Mapping[str, Any],
    work_order: Mapping[str, Any],
    now: Optional[datetime] = None,
    locks: Optional[MutableSet[str]] = None,
    repo_root: str | Path = ".",
) -> QueueAuthorizedExecutorPlanDryRunResult:
    """Plan executor dry-run from accepted queue-authorized work-order invocation."""

    if explicit_queue_authorized_executor_plan_requested is not True:
        return _reject(
            [QueueAuthorizedExecutorPlanDryRunReason.EXPLICIT_DRYRUN_MISSING],
            explicit_requested=False,
        )

    queue_invocation = _mapping(queue_work_order_invocation_result)
    if queue_invocation.get("decision") != QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_ACCEPT:
        return _reject(
            [QueueAuthorizedExecutorPlanDryRunReason.WORK_ORDER_INVOCATION_NOT_ACCEPTED],
            explicit_requested=True,
        )

    invocation_payload = _mapping(queue_invocation.get("invocation_result"))
    if not invocation_payload:
        return _reject(
            [QueueAuthorizedExecutorPlanDryRunReason.INVOCATION_PAYLOAD_MISSING],
            explicit_requested=True,
        )

    executor = plan_wre_isolated_worktree_execution_dryrun(
        invocation_payload,
        work_order,
        now=now,
        locks=locks,
        repo_root=str(repo_root),
    )
    if executor.decision != EXECUTOR_PLAN_ACCEPT:
        return _reject(
            [
                QueueAuthorizedExecutorPlanDryRunReason.EXECUTOR_PLAN_NOT_ACCEPTED,
                *executor.rejection_reasons,
            ],
            explicit_requested=True,
            executor_plan_result=executor,
        )

    return QueueAuthorizedExecutorPlanDryRunResult(
        decision=QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_ACCEPT,
        rejection_reasons=[],
        executor_plan_result=executor,
        explicit_queue_authorized_executor_plan_requested=True,
    )


__all__ = [
    "QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_ACCEPT",
    "QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_REJECT",
    "QueueAuthorizedExecutorPlanDryRunReason",
    "QueueAuthorizedExecutorPlanDryRunResult",
    "plan_reddog_wre_queue_authorized_executor_dryrun",
]
