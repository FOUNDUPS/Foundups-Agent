"""RedDog WRE worktree-create operational spine.

Slice: REDDOG_WRE_OPERATIONAL_SPINE_WORKTREE_CREATE_PHASE1

This module composes the landed RedDog governance spine into one callable path:
work-order invocation dry-run -> executor plan dry-run -> execution valve ->
isolated worktree create. It requires accepted signed work authority by default,
then stops before task execution, file edits, tests, PR, push, merge, OpenClaw
enqueue, or Hermes dispatch.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, MutableSet, Optional

from modules.communication.moltbot_bridge.src.reddog_wre_execution_valve import (
    INTAKE_FOUNDUP_JOB,
    VALVE_OPEN_WORKTREE_CREATE,
    ExecutionValveEnvironment,
    ExecutionValveRequest,
    evaluate_reddog_execution_valve,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_receipt import (
    RedDogWorkOrderReceiptStore,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_runtime_invocation import (
    INVOCATION_ACCEPT,
    WorkOrderDryRunInvocationResult,
    invoke_reddog_work_order_dryrun,
)
from modules.communication.moltbot_bridge.src.reddog_wre_executor_dryrun import (
    EXECUTOR_PLAN_ACCEPT,
    plan_wre_isolated_worktree_execution_dryrun,
)
from modules.communication.moltbot_bridge.src.reddog_wre_worktree_create import (
    WORKTREE_CREATE_ACCEPT,
    create_reddog_wre_worktree,
)

WORKTREE_SPINE_ACCEPT = "WORKTREE_SPINE_ACCEPT"
WORKTREE_SPINE_REJECT = "WORKTREE_SPINE_REJECT"


@dataclass
class RedDogWREOperationalSpineResult:
    decision: str
    work_order_id: str
    invocation_result: Dict[str, Any]
    executor_plan_result: Dict[str, Any]
    valve_decision: Dict[str, Any]
    worktree_create_result: Dict[str, Any]
    policy_gate_receipt: Dict[str, Any]
    reddog_work_order_receipt: Dict[str, Any]
    rejection_reasons: List[str]
    no_task_execution_performed: bool
    no_file_edit_performed: bool
    no_pr_created: bool
    no_live_openclaw_enqueue: bool
    no_hermes_dispatch: bool
    merge_performed: bool
    main_checkout_untouched: bool
    created_at: str
    result_digest: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _utc_now(now: Optional[datetime] = None) -> datetime:
    value = now or datetime.now(timezone.utc)
    return value.astimezone(timezone.utc)


def _iso8601(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat()


def _canonical_digest(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _work_order_id(work_order: Mapping[str, Any]) -> str:
    return str(work_order.get("work_order_id") or "unknown")


def _minimal_policy_gate_receipt(
    invocation: WorkOrderDryRunInvocationResult,
) -> Dict[str, Any]:
    return {
        "decision": invocation.policy_gate_decision,
        "receipt_digest": invocation.policy_gate_receipt_digest,
        "no_execution_performed": True,
        "work_order_id": invocation.work_order_id,
    }


def _minimal_reddog_work_order_receipt(
    invocation: WorkOrderDryRunInvocationResult,
) -> Dict[str, Any]:
    return {
        "receipt_id": invocation.receipt_id,
        "receipt_digest": invocation.receipt_digest,
        "policy_gate_receipt_digest": invocation.policy_gate_receipt_digest,
        "no_execution_performed": True,
        "work_order_id": invocation.work_order_id,
    }


def _empty_spine_dict() -> Dict[str, Any]:
    return {}


def _result_digest(
    *,
    decision: str,
    work_order_id: str,
    invocation_result: Mapping[str, Any],
    executor_plan_result: Mapping[str, Any],
    valve_decision: Mapping[str, Any],
    worktree_create_result: Mapping[str, Any],
    rejection_reasons: List[str],
    created_at: str,
) -> str:
    return _canonical_digest(
        {
            "decision": decision,
            "work_order_id": work_order_id,
            "invocation_decision": invocation_result.get("decision"),
            "invocation_receipt_digest": invocation_result.get("receipt_digest"),
            "executor_plan_decision": executor_plan_result.get("decision"),
            "executor_plan_digest": (
                dict(executor_plan_result.get("plan") or {}).get("plan_digest")
                if isinstance(executor_plan_result.get("plan"), Mapping)
                else ""
            ),
            "valve_state": valve_decision.get("valve_state"),
            "valve_decision_digest": valve_decision.get("decision_digest"),
            "worktree_create_decision": worktree_create_result.get("decision"),
            "worktree_create_digest": worktree_create_result.get("result_digest"),
            "rejection_reasons": rejection_reasons,
            "created_at": created_at,
        }
    )


def _build_result(
    *,
    decision: str,
    work_order_id: str,
    invocation_result: Mapping[str, Any],
    executor_plan_result: Mapping[str, Any],
    valve_decision: Mapping[str, Any],
    worktree_create_result: Mapping[str, Any],
    policy_gate_receipt: Mapping[str, Any],
    reddog_work_order_receipt: Mapping[str, Any],
    rejection_reasons: List[str],
    created_at: str,
) -> RedDogWREOperationalSpineResult:
    deduped = list(dict.fromkeys(rejection_reasons))
    digest = _result_digest(
        decision=decision,
        work_order_id=work_order_id,
        invocation_result=invocation_result,
        executor_plan_result=executor_plan_result,
        valve_decision=valve_decision,
        worktree_create_result=worktree_create_result,
        rejection_reasons=deduped,
        created_at=created_at,
    )
    return RedDogWREOperationalSpineResult(
        decision=decision,
        work_order_id=work_order_id,
        invocation_result=dict(invocation_result),
        executor_plan_result=dict(executor_plan_result),
        valve_decision=dict(valve_decision),
        worktree_create_result=dict(worktree_create_result),
        policy_gate_receipt=dict(policy_gate_receipt),
        reddog_work_order_receipt=dict(reddog_work_order_receipt),
        rejection_reasons=deduped,
        no_task_execution_performed=True,
        no_file_edit_performed=True,
        no_pr_created=True,
        no_live_openclaw_enqueue=True,
        no_hermes_dispatch=True,
        merge_performed=False,
        main_checkout_untouched=True,
        created_at=created_at,
        result_digest=digest,
    )


def run_reddog_wre_worktree_create_spine(
    work_order: Mapping[str, Any],
    *,
    permission_snapshot: Optional[Mapping[str, Any]] = None,
    seen_nonces: Optional[MutableSet[str]] = None,
    receipt_store: Optional[RedDogWorkOrderReceiptStore] = None,
    valve_environment: Optional[ExecutionValveEnvironment | Mapping[str, Any]] = None,
    signature_verification_result: Optional[Mapping[str, Any]] = None,
    require_signed_authority: bool = True,
    runner: Optional[Any] = None,
    repo_root: Optional[Path] = None,
    now: Optional[datetime] = None,
    locks: Optional[MutableSet[str]] = None,
    intake_target: str = INTAKE_FOUNDUP_JOB,
    permission_ttl_seconds: int = 300, permission_expires_at: Optional[str] = None,
    admission_consumer: Optional[Callable[[], bool]] = None, admission_consumer_factory: Optional[Callable[[Mapping[str, Any], Mapping[str, Any]], Optional[Callable[[], bool]]]] = None,
) -> RedDogWREOperationalSpineResult:
    """Run the RedDog worktree-create spine and stop before task execution."""
    checked = _utc_now(now)
    created_at = _iso8601(checked)
    work_order_id = _work_order_id(work_order)

    invocation = invoke_reddog_work_order_dryrun(
        work_order,
        permission_snapshot=permission_snapshot,
        now=checked,
        seen_nonces=seen_nonces,
        receipt_store=receipt_store,
        permission_ttl_seconds=permission_ttl_seconds,
        permission_expires_at=permission_expires_at,
        require_signed_authority=require_signed_authority,
        signature_verification_result=signature_verification_result,
    )
    invocation_dict = invocation.to_dict()
    policy_receipt = _minimal_policy_gate_receipt(invocation)
    work_order_receipt = _minimal_reddog_work_order_receipt(invocation)

    if invocation.decision != INVOCATION_ACCEPT:
        return _build_result(
            decision=WORKTREE_SPINE_REJECT,
            work_order_id=work_order_id,
            invocation_result=invocation_dict,
            executor_plan_result=_empty_spine_dict(),
            valve_decision=_empty_spine_dict(),
            worktree_create_result=_empty_spine_dict(),
            policy_gate_receipt=policy_receipt,
            reddog_work_order_receipt=work_order_receipt,
            rejection_reasons=["invocation_not_accepted", *invocation.rejection_reasons],
            created_at=created_at,
        )

    executor_plan = plan_wre_isolated_worktree_execution_dryrun(
        invocation,
        work_order,
        now=checked,
        locks=locks,
        repo_root=str(Path(repo_root).resolve()) if repo_root is not None else ".",
    )
    executor_dict = executor_plan.to_dict()
    if executor_plan.decision != EXECUTOR_PLAN_ACCEPT:
        return _build_result(
            decision=WORKTREE_SPINE_REJECT,
            work_order_id=work_order_id,
            invocation_result=invocation_dict,
            executor_plan_result=executor_dict,
            valve_decision=_empty_spine_dict(),
            worktree_create_result=_empty_spine_dict(),
            policy_gate_receipt=policy_receipt,
            reddog_work_order_receipt=work_order_receipt,
            rejection_reasons=[
                "executor_plan_not_accepted",
                *executor_plan.rejection_reasons,
            ],
            created_at=created_at,
        )

    env = valve_environment or ExecutionValveEnvironment()
    snapshot = dict(permission_snapshot or work_order.get("repo_permission_snapshot") or {})
    valve = evaluate_reddog_execution_valve(
        ExecutionValveRequest(
            work_order=work_order,
            policy_gate_receipt=policy_receipt,
            reddog_work_order_receipt=work_order_receipt,
            invocation_result=invocation_dict,
            executor_plan_result=executor_dict,
            intake_target=intake_target,
            permission_snapshot=snapshot,
        ),
        env,
        now=checked,
    )
    valve_dict = valve.to_dict()
    if valve.valve_state != VALVE_OPEN_WORKTREE_CREATE:
        return _build_result(
            decision=WORKTREE_SPINE_REJECT,
            work_order_id=work_order_id,
            invocation_result=invocation_dict,
            executor_plan_result=executor_dict,
            valve_decision=valve_dict,
            worktree_create_result=_empty_spine_dict(),
            policy_gate_receipt=policy_receipt,
            reddog_work_order_receipt=work_order_receipt,
            rejection_reasons=[
                "execution_valve_not_open_for_worktree_create",
                *valve.rejection_reasons,
            ],
            created_at=created_at,
        )

    effect_consumer = _effect_consumer(admission_consumer, admission_consumer_factory, executor_dict, valve_dict)
    worktree = create_reddog_wre_worktree(
        work_order,
        executor_dict,
        valve_dict,
        runner=runner,
        repo_root=repo_root,
        now=checked,
        locks=locks,
        admission_consumer=effect_consumer,
    )
    worktree_dict = worktree.to_dict()
    if worktree.decision != WORKTREE_CREATE_ACCEPT:
        return _build_result(
            decision=WORKTREE_SPINE_REJECT,
            work_order_id=work_order_id,
            invocation_result=invocation_dict,
            executor_plan_result=executor_dict,
            valve_decision=valve_dict,
            worktree_create_result=worktree_dict,
            policy_gate_receipt=policy_receipt,
            reddog_work_order_receipt=work_order_receipt,
            rejection_reasons=[
                "worktree_create_not_accepted",
                *worktree.rejection_reasons,
            ],
            created_at=created_at,
        )

    return _build_result(
        decision=WORKTREE_SPINE_ACCEPT,
        work_order_id=work_order_id,
        invocation_result=invocation_dict,
        executor_plan_result=executor_dict,
        valve_decision=valve_dict,
        worktree_create_result=worktree_dict,
        policy_gate_receipt=policy_receipt,
        reddog_work_order_receipt=work_order_receipt,
        rejection_reasons=[],
        created_at=created_at,
    )


def _effect_consumer(
    fallback: Optional[Callable[[], bool]],
    factory: Optional[Callable[[Mapping[str, Any], Mapping[str, Any]], Optional[Callable[[], bool]]]],
    executor: Mapping[str, Any],
    valve: Mapping[str, Any],
) -> Optional[Callable[[], bool]]:
    if factory is None:
        return fallback
    try:
        return factory(executor, valve)
    except Exception:
        return None


__all__ = [
    "RedDogWREOperationalSpineResult",
    "WORKTREE_SPINE_ACCEPT",
    "WORKTREE_SPINE_REJECT",
    "run_reddog_wre_worktree_create_spine",
]
