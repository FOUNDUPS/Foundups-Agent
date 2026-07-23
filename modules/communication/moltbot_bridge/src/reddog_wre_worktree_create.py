"""RedDog WRE isolated worktree create orchestration.

Slice: REDDOG_WRE_ISOLATED_WORKTREE_EXECUTOR_WORKTREE_CREATE_PHASE1

Consumes an accepted RedDog executor dry-run plan plus an explicit
VALVE_OPEN_WORKTREE_CREATE decision and materializes only the isolated git
worktree. It does not edit files, run task commands, run tests, create PRs,
push branches, invoke Skillz, or merge.

WSP 97 truth boundary:
  DOES:
    - Validate the accepted dry-run plan and execution valve
    - Create one isolated worktree through an injected runner
    - Emit deterministic receipts and result digests
  DOES NOT:
    - Execute task code, edit files, run shell commands directly, call gh, or
      invoke Hermes/OpenClaw/WRE workers
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, MutableSet, Optional

from modules.communication.moltbot_bridge.src.reddog_work_order_binding import (
    canonical_full_work_order_digest,
    canonical_work_order_base_ref,
)

from modules.communication.moltbot_bridge.src.reddog_governed_work_order_dryrun import (
    PROTECTED_BASE_REFS,
)
from modules.communication.moltbot_bridge.src.reddog_effect_commit_outcome import (
    EFFECT_COMMITTED,
    EFFECT_INDETERMINATE,
    EFFECT_NOT_COMMITTED,
)
from modules.communication.moltbot_bridge.src.reddog_wre_cwd_guard import (
    validate_wre_worker_operation_cwd,
)
from modules.communication.moltbot_bridge.src.reddog_wre_execution_valve import (
    VALVE_OPEN_WORKTREE_CREATE,
)
from modules.communication.moltbot_bridge.src.reddog_wre_executor_dryrun import (
    EXECUTOR_PLAN_ACCEPT,
)

WORKTREE_CREATE_ACCEPT = "WORKTREE_CREATE_ACCEPT"
WORKTREE_CREATE_REJECT = "WORKTREE_CREATE_REJECT"

PHASE_WORKTREE_PREFLIGHT = "worktree_create_preflight"
PHASE_WORKTREE_CREATED = "worktree_created"
PHASE_WORKTREE_CLEANUP_PLANNED = "cleanup_planned"


@dataclass
class WorktreeCreateReceipt:
    phase: str
    work_order_id: str
    receipt_digest: str
    no_task_execution_performed: bool
    no_file_edit_performed: bool
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RedDogWorktreeCreateResult:
    decision: str
    work_order_id: str
    branch_name: str
    worktree_path: str
    plan_id: str
    plan_digest: str
    valve_decision_digest: str
    rejection_reasons: List[str]
    phase_receipts: List[WorktreeCreateReceipt]
    no_task_execution_performed: bool
    no_file_edit_performed: bool
    no_pr_created: bool
    merge_performed: bool
    main_checkout_untouched: bool
    cleanup_plan: Dict[str, Any]
    effect_commit_state: str
    effect_attempt_key: str
    reconciliation_required: bool
    reconciliation_data: Dict[str, Any]
    result_digest: str

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["phase_receipts"] = [r.to_dict() for r in self.phase_receipts]
        return payload


def _utc_now(now: Optional[datetime] = None) -> datetime:
    value = now or datetime.now(timezone.utc)
    return value.astimezone(timezone.utc)


def _iso8601(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat()


def _canonical_digest(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _worktree_attempt_key(
    *,
    work_order: Mapping[str, Any],
    plan: Mapping[str, Any],
    valve_decision: Mapping[str, Any],
) -> str:
    evidence = {
        "work_order": dict(work_order),
        "plan": dict(plan),
        "valve_decision": dict(valve_decision),
    }
    return "worktree-attempt-" + _canonical_digest(evidence)[:24]


def _work_order_id(work_order: Mapping[str, Any]) -> str:
    return str(work_order.get("work_order_id") or "unknown")


def _receipt(
    phase: str,
    work_order_id: str,
    payload: Mapping[str, Any],
    created_at: str,
) -> WorktreeCreateReceipt:
    body = {
        "phase": phase,
        "work_order_id": work_order_id,
        "no_task_execution_performed": True,
        "no_file_edit_performed": True,
        "created_at": created_at,
        **dict(payload),
    }
    return WorktreeCreateReceipt(
        phase=phase,
        work_order_id=work_order_id,
        receipt_digest=_canonical_digest(body),
        no_task_execution_performed=True,
        no_file_edit_performed=True,
        created_at=created_at,
    )


def _default_repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _is_inside(child: Path, parent: Path) -> bool:
    child_r = child.resolve()
    parent_r = parent.resolve()
    return child_r == parent_r or parent_r in child_r.parents


def _repo_slug(repo_root: Path) -> str:
    text = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in repo_root.name.strip())
    return text[:48].strip("-_") or "repo"


def _external_worktree_root(repo_root: Path) -> Path:
    root = repo_root.resolve()
    return root.parent / ".reddog" / "worktrees" / _repo_slug(root)


def _reject(
    *,
    work_order_id: str,
    reasons: List[str],
    created_at: str,
    branch_name: str = "",
    worktree_path: str = "",
    plan_id: str = "",
    plan_digest: str = "",
    valve_decision_digest: str = "",
    phase_receipts: Optional[List[WorktreeCreateReceipt]] = None,
    cleanup_plan: Optional[Mapping[str, Any]] = None,
    effect_attempt_key: str = "",
    effect_commit_state: str = EFFECT_NOT_COMMITTED,
    reconciliation_required: bool = False,
    reconciliation_data: Optional[Mapping[str, Any]] = None,
) -> RedDogWorktreeCreateResult:
    deduped = list(dict.fromkeys(reasons))
    receipts = list(phase_receipts or [])
    cleanup = dict(cleanup_plan or {"status": "no_worktree_created"})
    reconciliation = dict(reconciliation_data or {"effect_attempted": False})
    body = {
        "decision": WORKTREE_CREATE_REJECT,
        "work_order_id": work_order_id,
        "rejection_reasons": deduped,
        "created_at": created_at,
        "plan_id": plan_id,
        "valve_decision_digest": valve_decision_digest,
        "effect_commit_state": effect_commit_state,
        "effect_attempt_key": effect_attempt_key,
        "reconciliation_required": reconciliation_required,
        "reconciliation_data": reconciliation,
    }
    return RedDogWorktreeCreateResult(
        decision=WORKTREE_CREATE_REJECT,
        work_order_id=work_order_id,
        branch_name=branch_name,
        worktree_path=worktree_path,
        plan_id=plan_id,
        plan_digest=plan_digest,
        valve_decision_digest=valve_decision_digest,
        rejection_reasons=deduped,
        phase_receipts=receipts,
        no_task_execution_performed=True,
        no_file_edit_performed=True,
        no_pr_created=True,
        merge_performed=False,
        main_checkout_untouched=True,
        cleanup_plan=cleanup,
        effect_commit_state=effect_commit_state,
        effect_attempt_key=effect_attempt_key,
        reconciliation_required=reconciliation_required,
        reconciliation_data=reconciliation,
        result_digest=_canonical_digest(body),
    )


def _consume_admission(consumer: Optional[Callable[[], bool]]) -> bool:
    try:
        return consumer is not None and consumer() is True
    except Exception:
        return False


def _validate_valve(valve_decision: Mapping[str, Any]) -> List[str]:
    reasons: List[str] = []
    if valve_decision.get("valve_state") != VALVE_OPEN_WORKTREE_CREATE:
        reasons.append("execution_valve_not_open_for_worktree_create")
    if valve_decision.get("no_execution_performed") is not True:
        reasons.append("valve_execution_detected")
    if not valve_decision.get("decision_digest"):
        reasons.append("missing_valve_decision_digest")
    if valve_decision.get("rejection_reasons"):
        reasons.append("valve_has_rejection_reasons")
    return reasons


def _plan_from_result(executor_plan_result: Mapping[str, Any]) -> Mapping[str, Any]:
    plan = executor_plan_result.get("plan")
    return plan if isinstance(plan, Mapping) else {}


def _validate_plan(
    work_order: Mapping[str, Any],
    executor_plan_result: Mapping[str, Any],
    plan: Mapping[str, Any],
) -> List[str]:
    reasons: List[str] = []
    work_order_id = _work_order_id(work_order)
    if executor_plan_result.get("decision") != EXECUTOR_PLAN_ACCEPT:
        reasons.append("executor_plan_not_accepted")
    if executor_plan_result.get("no_mutation_performed") is not True:
        reasons.append("executor_plan_mutation_detected")
    if not plan:
        reasons.append("missing_executor_plan")
        return reasons

    if plan.get("work_order_id") != work_order_id:
        reasons.append("plan_work_order_mismatch")
    if not plan.get("plan_id"):
        reasons.append("missing_plan_id")
    if not plan.get("plan_digest"):
        reasons.append("missing_plan_digest")
    if plan.get("no_mutation_performed") is not True:
        reasons.append("plan_mutation_detected")

    try:
        work_order_digest = canonical_full_work_order_digest(work_order)
        base_ref = canonical_work_order_base_ref(work_order)
    except (TypeError, ValueError):
        reasons.append("work_order_binding_invalid")
        work_order_digest = ""
        base_ref = ""
    if plan.get("work_order_digest") != work_order_digest:
        reasons.append("plan_work_order_digest_mismatch")
    if plan.get("base_ref") != base_ref:
        reasons.append("plan_base_ref_mismatch")

    plan_body = {
        "work_order_id": plan.get("work_order_id"),
        "work_order_digest": plan.get("work_order_digest"),
        "base_ref": plan.get("base_ref"),
        "proposed_branch_name": plan.get("proposed_branch_name"),
        "proposed_worktree_path": plan.get("proposed_worktree_path"),
        "lock_key": plan.get("lock_key"),
        "allowed_paths": plan.get("allowed_paths"),
        "denied_paths": plan.get("denied_paths"),
        "required_tests": plan.get("required_tests"),
        "cleanup_plan": plan.get("cleanup_plan"),
        "no_mutation_performed": plan.get("no_mutation_performed"),
        "invocation_receipt_digest": plan.get("invocation_receipt_digest"),
    }
    expected_plan_digest = _canonical_digest(plan_body)
    if plan.get("plan_digest") != expected_plan_digest:
        reasons.append("plan_digest_mismatch")
    if plan.get("plan_id") != expected_plan_digest:
        reasons.append("plan_id_mismatch")

    branch = str(work_order.get("branch_name") or "").strip()
    if not branch:
        reasons.append("missing_branch_name")
    elif branch.lower() in PROTECTED_BASE_REFS:
        reasons.append("protected_branch_forbidden")
    if plan.get("proposed_branch_name") != branch:
        reasons.append("plan_branch_mismatch")

    if plan.get("lock_key") != work_order_id:
        reasons.append("plan_lock_key_mismatch")

    return reasons


def _validate_worktree_path(
    work_order_id: str,
    worktree_path: Path,
    *,
    repo_root: Path,
) -> List[str]:
    reasons: List[str] = []
    if not worktree_path.is_absolute():
        reasons.append("worktree_path_not_absolute")
        return reasons

    raw = str(worktree_path)
    resolved = str(worktree_path.resolve())
    for prefix in ("\\\\?\\", "\\\\.\\", "//?/", "//./"):
        if raw.startswith(prefix) or resolved.startswith(prefix):
            reasons.append("worktree_path_device_prefix_forbidden")
            return reasons

    if _is_inside(worktree_path, repo_root):
        reasons.append("worktree_path_inside_repo_root")
    expected_root = (_external_worktree_root(repo_root) / work_order_id).resolve()
    if not _is_inside(worktree_path, expected_root):
        reasons.append("worktree_path_not_under_reddog_root")
    if worktree_path.resolve() == repo_root.resolve():
        reasons.append("worktree_equals_repo_root")
    guard = validate_wre_worker_operation_cwd(
        repo_root=repo_root,
        worktree_path=worktree_path,
        operation_cwd=worktree_path,
    )
    if not guard.ok:
        reasons.append(f"cwd_guard_failed:{guard.code}")
    return reasons


def create_reddog_wre_worktree(
    work_order: Mapping[str, Any],
    executor_plan_result: Mapping[str, Any],
    valve_decision: Mapping[str, Any],
    *,
    runner: Optional[Any] = None,
    repo_root: Optional[Path] = None,
    now: Optional[datetime] = None,
    locks: Optional[MutableSet[str]] = None,
    admission_consumer: Optional[Callable[[], bool]] = None,
) -> RedDogWorktreeCreateResult:
    """Create the isolated RedDog WRE worktree and stop before task execution."""
    checked = _utc_now(now)
    created_at = _iso8601(checked)
    repo = (Path(repo_root) if repo_root is not None else _default_repo_root()).resolve()
    work_order_id = _work_order_id(work_order)
    plan = _plan_from_result(executor_plan_result)
    branch_name = str(plan.get("proposed_branch_name") or work_order.get("branch_name") or "")
    base_ref = str(plan.get("base_ref") or "")
    worktree_path_text = str(plan.get("proposed_worktree_path") or "")
    plan_id = str(plan.get("plan_id") or "")
    plan_digest = str(plan.get("plan_digest") or "")
    valve_digest = str(valve_decision.get("decision_digest") or "")
    cleanup_plan = dict(plan.get("cleanup_plan") or {"status": "no_plan_cleanup"})
    effect_attempt_key = _worktree_attempt_key(
        work_order=work_order,
        plan=plan,
        valve_decision=valve_decision,
    )

    phase_receipts: List[WorktreeCreateReceipt] = []
    reasons: List[str] = []
    reasons.extend(_validate_valve(valve_decision))
    reasons.extend(_validate_plan(work_order, executor_plan_result, plan))

    if locks is not None and work_order_id in locks:
        reasons.append("lock_collision")

    worktree_path = Path(worktree_path_text)
    if worktree_path_text:
        reasons.extend(_validate_worktree_path(work_order_id, worktree_path, repo_root=repo))
    else:
        reasons.append("missing_worktree_path")

    if reasons:
        return _reject(
            work_order_id=work_order_id,
            reasons=reasons,
            created_at=created_at,
            branch_name=branch_name,
            worktree_path=worktree_path_text,
            plan_id=plan_id,
            plan_digest=plan_digest,
            valve_decision_digest=valve_digest,
            phase_receipts=phase_receipts,
            cleanup_plan={"status": "no_worktree_created", **cleanup_plan},
            effect_attempt_key=effect_attempt_key,
        )

    if not _consume_admission(admission_consumer):
        return _reject(
            work_order_id=work_order_id,
            reasons=["authoritative_worktree_admission_missing"],
            created_at=created_at,
            branch_name=branch_name,
            worktree_path=worktree_path_text,
            plan_id=plan_id,
            plan_digest=plan_digest,
            valve_decision_digest=valve_digest,
            cleanup_plan={"status": "no_worktree_created", **cleanup_plan},
            effect_attempt_key=effect_attempt_key,
        )

    phase_receipts.append(
        _receipt(
            PHASE_WORKTREE_PREFLIGHT,
            work_order_id,
            {
                "plan_id": plan_id,
                "plan_digest": plan_digest,
                "valve_decision_digest": valve_digest,
                "branch_name": branch_name,
            },
            created_at,
        )
    )

    if runner is None:
        from modules.communication.moltbot_bridge.src.reddog_wre_worktree_runner import (
            RealRedDogWorktreeRunner,
        )

        runner = RealRedDogWorktreeRunner(repo)

    if locks is not None:
        locks.add(work_order_id)

    attempted = False
    create_exception = False
    try:
        attempted = True
        create_result = runner.create_worktree(
            worktree_path=worktree_path,
            branch_name=branch_name,
            base_ref=base_ref,
        )
    except Exception as exc:
        create_exception = True
        create_result = {"ok": False, "error": type(exc).__name__}

    if not isinstance(create_result, Mapping) or create_result.get("ok") is not True:
        cleanup_result: Mapping[str, Any] = {"status": "not_attempted"}
        if attempted:
            try:
                cleanup_result = runner.cleanup_worktree(worktree_path=worktree_path)
            except Exception as exc:
                cleanup_result = {"ok": False, "error": type(exc).__name__}
        if locks is not None:
            locks.discard(work_order_id)
        phase_receipts.append(
            _receipt(
                PHASE_WORKTREE_CLEANUP_PLANNED,
                work_order_id,
                {"cleanup_attempted": attempted, "cleanup_digest": _canonical_digest(cleanup_result)},
                created_at,
            )
        )
        return _reject(
            work_order_id=work_order_id,
            reasons=["worktree_create_failed"],
            created_at=created_at,
            branch_name=branch_name,
            worktree_path=worktree_path_text,
            plan_id=plan_id,
            plan_digest=plan_digest,
            valve_decision_digest=valve_digest,
            phase_receipts=phase_receipts,
            cleanup_plan={"status": "cleanup_planned_after_create_failure", **cleanup_plan},
            effect_attempt_key=effect_attempt_key,
            effect_commit_state=(
                EFFECT_INDETERMINATE if create_exception else EFFECT_NOT_COMMITTED
            ),
            reconciliation_required=create_exception,
            reconciliation_data={
                "effect_attempted": attempted,
                "worktree_path": worktree_path_text,
                "branch_name": branch_name,
                "base_ref": base_ref,
                "runner_result_digest": _canonical_digest(create_result),
                "cleanup_result_digest": _canonical_digest(cleanup_result),
                "next_action": (
                    "inspect_worktree_registry_path_and_branch"
                    if create_exception
                    else "none"
                ),
            },
        )

    phase_receipts.append(
        _receipt(
            PHASE_WORKTREE_CREATED,
            work_order_id,
            {
                "branch_name": branch_name,
                "worktree_path": worktree_path_text,
                "runner_result_digest": _canonical_digest(create_result),
            },
            created_at,
        )
    )
    phase_receipts.append(
        _receipt(
            PHASE_WORKTREE_CLEANUP_PLANNED,
            work_order_id,
            {"cleanup_plan_digest": _canonical_digest(cleanup_plan)},
            created_at,
        )
    )

    body = {
        "decision": WORKTREE_CREATE_ACCEPT,
        "work_order_id": work_order_id,
        "branch_name": branch_name,
        "worktree_path": worktree_path_text,
        "plan_id": plan_id,
        "plan_digest": plan_digest,
        "valve_decision_digest": valve_digest,
        "phase_receipts": [r.receipt_digest for r in phase_receipts],
        "no_task_execution_performed": True,
        "no_file_edit_performed": True,
        "no_pr_created": True,
        "merge_performed": False,
        "main_checkout_untouched": True,
        "effect_commit_state": EFFECT_COMMITTED,
        "effect_attempt_key": effect_attempt_key,
    }
    return RedDogWorktreeCreateResult(
        decision=WORKTREE_CREATE_ACCEPT,
        work_order_id=work_order_id,
        branch_name=branch_name,
        worktree_path=worktree_path_text,
        plan_id=plan_id,
        plan_digest=plan_digest,
        valve_decision_digest=valve_digest,
        rejection_reasons=[],
        phase_receipts=phase_receipts,
        no_task_execution_performed=True,
        no_file_edit_performed=True,
        no_pr_created=True,
        merge_performed=False,
        main_checkout_untouched=True,
        cleanup_plan=cleanup_plan,
        effect_commit_state=EFFECT_COMMITTED,
        effect_attempt_key=effect_attempt_key,
        reconciliation_required=False,
        reconciliation_data={
            "effect_attempted": True,
            "worktree_path": worktree_path_text,
            "branch_name": branch_name,
            "base_ref": base_ref,
            "runner_result_digest": _canonical_digest(create_result),
            "next_action": "none",
        },
        result_digest=_canonical_digest(body),
    )


__all__ = [
    "PHASE_WORKTREE_CLEANUP_PLANNED",
    "PHASE_WORKTREE_CREATED",
    "PHASE_WORKTREE_PREFLIGHT",
    "RedDogWorktreeCreateResult",
    "WORKTREE_CREATE_ACCEPT",
    "WORKTREE_CREATE_REJECT",
    "WorktreeCreateReceipt",
    "create_reddog_wre_worktree",
]
