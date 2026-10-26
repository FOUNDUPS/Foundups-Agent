"""RedDog WRE isolated worktree executor dry-run planner (no mutation).

Slice: REDDOG_WRE_ISOLATED_WORKTREE_EXECUTOR_DRYRUN_PHASE1
Contract: docs/audits/architecture/REDDOG_WRE_ISOLATED_WORKTREE_EXECUTOR_CONTRACT_PHASE1.md

Consumes an accepted #896 invocation result and produces a WREExecutorPlan plus phase
receipts. Validates #897 contract rules without creating branches, worktrees, files,
PRs, or running task commands.

WSP 97 TRUTH BOUNDARIES:
  ✓ DOES:
    - Require accepted invocation + no_execution_performed from prior spine
    - Build proposed branch/worktree path, lock key, cleanup plan (plan only)
    - Validate path confinement, branch naming, deny secrets/global config paths
    - Emit phase receipts: plan_built, lock_checked, cleanup_planned
    - Return rejection receipt digest on failure

  ✗ DOES NOT:
    - Call shell, WRE executor, Skillz, live GitHub, or Hermes queue
    - Create directories, worktrees, branches, commits, PRs, or file edits
    - Invoke task commands or mutate repository content
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, MutableSet, Optional, Sequence, Union

from modules.communication.moltbot_bridge.src.reddog_work_order_binding import (
    canonical_full_work_order_digest,
    canonical_work_order_base_ref,
)

from modules.communication.moltbot_bridge.src.reddog_governed_work_order_dryrun import (
    PROTECTED_BASE_REFS,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_runtime_invocation import (
    INVOCATION_ACCEPT,
    INVOCATION_ACCEPT_WITH_RETRIEVAL_GAP,
    INVOCATION_REJECT,
    WorkOrderDryRunInvocationResult,
)

EXECUTOR_PLAN_ACCEPT = "EXECUTOR_PLAN_ACCEPT"
EXECUTOR_PLAN_REJECT = "EXECUTOR_PLAN_REJECT"

PHASE_PLAN_BUILT = "plan_built"
PHASE_LOCK_CHECKED = "lock_checked"
PHASE_CLEANUP_PLANNED = "cleanup_planned"

EXECUTOR_FORBIDDEN_PATH_GLOBS = (
    ".env",
    ".env.*",
    "**/.env",
    "**/credentials*",
    "**/secrets/**",
    "**/.git/**",
    ".git/config",
    "**/.git/config",
    ".git/hooks/**",
    ".github/workflows/**",
)

_NONCE_SUFFIX_RE = re.compile(r"[^a-zA-Z0-9_-]+")


@dataclass
class ExecutorDryRunPhaseReceipt:
    phase: str
    work_order_id: str
    receipt_digest: str
    no_mutation_performed: bool
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WREExecutorPlan:
    plan_id: str
    work_order_id: str
    work_order_digest: str
    base_ref: str
    proposed_branch_name: str
    proposed_worktree_path: str
    lock_key: str
    allowed_paths: List[str]
    denied_paths: List[str]
    required_tests: List[str]
    cleanup_plan: Dict[str, Any]
    phase_receipts: List[ExecutorDryRunPhaseReceipt]
    no_mutation_performed: bool
    invocation_receipt_digest: str
    plan_digest: str

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["phase_receipts"] = [r.to_dict() for r in self.phase_receipts]
        return payload


@dataclass
class WREExecutorDryRunResult:
    decision: str
    work_order_id: str
    plan: Optional[WREExecutorPlan]
    rejection_reasons: List[str]
    rejection_receipt_digest: str
    no_mutation_performed: bool
    phase_receipts: List[ExecutorDryRunPhaseReceipt] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        if self.plan is not None:
            payload["plan"] = self.plan.to_dict()
        payload["phase_receipts"] = [r.to_dict() for r in self.phase_receipts]
        return payload


def _utc_now(now: Optional[datetime] = None) -> datetime:
    value = now or datetime.now(timezone.utc)
    return value.astimezone(timezone.utc)


def _iso8601(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat()


def _canonical_digest(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _path_matches_any(path: str, patterns: Sequence[str]) -> bool:
    normalized = path.replace("\\", "/")
    for pattern in patterns:
        pat = pattern.replace("\\", "/")
        if fnmatch.fnmatch(normalized, pat) or fnmatch.fnmatch(normalized, f"**/{pat}"):
            return True
    return False


def _forbidden_path_overlap(paths: Sequence[str]) -> List[str]:
    hits: List[str] = []
    for path in paths:
        if _path_matches_any(path, EXECUTOR_FORBIDDEN_PATH_GLOBS):
            hits.append(path)
    return hits


def _normalize_posix(path: str) -> str:
    return path.replace("\\", "/").rstrip("/")


def _nonce_suffix(nonce: str) -> str:
    cleaned = _NONCE_SUFFIX_RE.sub("-", nonce.strip())[:32].strip("-")
    return cleaned or "nonce"


def _repo_slug(repo_root: Path) -> str:
    cleaned = _NONCE_SUFFIX_RE.sub("-", repo_root.name.strip())[:48].strip("-")
    return cleaned or "repo"


def _external_worktree_root(repo_root: str) -> Path:
    root = Path(repo_root or ".").resolve()
    return root.parent / ".reddog" / "worktrees" / _repo_slug(root)


def _invocation_from_any(
    invocation_result: Union[WorkOrderDryRunInvocationResult, Mapping[str, Any]],
) -> WorkOrderDryRunInvocationResult:
    if isinstance(invocation_result, WorkOrderDryRunInvocationResult):
        return invocation_result
    return WorkOrderDryRunInvocationResult(**dict(invocation_result))


def _work_order_id(work_order: Mapping[str, Any]) -> str:
    return str(work_order.get("work_order_id") or "unknown")


def _build_cleanup_plan(work_order: Mapping[str, Any]) -> Dict[str, Any]:
    rollback = str(work_order.get("rollback_plan") or "").strip()
    return {
        "on_success": "remove_worktree_after_pr_draft_receipt",
        "on_failure": "remove_worktree_delete_branch",
        "on_interrupt": "lease_expiry_janitor_cleanup",
        "salvage_requires_operator": True,
        "rollback_plan_ref": rollback,
    }


def _proposed_worktree_path(repo_root: str, work_order_id: str, nonce: str) -> str:
    suffix = _nonce_suffix(nonce)
    root = _external_worktree_root(repo_root)
    return f"{_normalize_posix(str(root))}/{work_order_id}/{suffix}/"


def canonical_external_worktree_path(
    repo_root: str, work_order_id: str, nonce: str
) -> str:
    """Return the sole executor-issued external worktree path."""

    return _proposed_worktree_path(repo_root, work_order_id, nonce)


def _phase_receipt(
    phase: str,
    work_order_id: str,
    payload: Mapping[str, Any],
    checked_at: str,
) -> ExecutorDryRunPhaseReceipt:
    body = {
        "phase": phase,
        "work_order_id": work_order_id,
        "no_mutation_performed": True,
        "created_at": checked_at,
        **dict(payload),
    }
    return ExecutorDryRunPhaseReceipt(
        phase=phase,
        work_order_id=work_order_id,
        receipt_digest=_canonical_digest(body),
        no_mutation_performed=True,
        created_at=checked_at,
    )


def _rejection_result(
    work_order_id: str,
    reasons: List[str],
    checked_at: str,
    phase_receipts: Optional[List[ExecutorDryRunPhaseReceipt]] = None,
) -> WREExecutorDryRunResult:
    body = {
        "decision": EXECUTOR_PLAN_REJECT,
        "work_order_id": work_order_id,
        "rejection_reasons": reasons,
        "no_mutation_performed": True,
        "created_at": checked_at,
    }
    return WREExecutorDryRunResult(
        decision=EXECUTOR_PLAN_REJECT,
        work_order_id=work_order_id,
        plan=None,
        rejection_reasons=reasons,
        rejection_receipt_digest=_canonical_digest(body),
        no_mutation_performed=True,
        phase_receipts=list(phase_receipts or []),
    )


def _validate_contract_rules(
    work_order: Mapping[str, Any],
    repo_root: str,
    locks: Optional[MutableSet[str]],
) -> List[str]:
    reasons: List[str] = []
    work_order_id = _work_order_id(work_order)
    branch = str(work_order.get("branch_name") or "").strip()
    try:
        base_ref = canonical_work_order_base_ref(work_order)
        canonical_full_work_order_digest(work_order)
    except (TypeError, ValueError):
        reasons.append("invalid_work_order_binding")
        base_ref = ""
    nonce = str(work_order.get("nonce") or "").strip()
    allowed_paths = list(work_order.get("allowed_paths") or [])
    denied_paths = list(work_order.get("denied_paths") or [])
    rollback_plan = str(work_order.get("rollback_plan") or "").strip()

    if not branch:
        reasons.append("missing_branch_name")
    elif branch.lower() in PROTECTED_BASE_REFS:
        reasons.append("protected_branch_forbidden")
    elif branch.lower() == base_ref.lower():
        reasons.append("branch_equals_base_ref")

    if not nonce:
        reasons.append("missing_nonce")

    forbidden_allowed = _forbidden_path_overlap(allowed_paths)
    if forbidden_allowed:
        reasons.append("forbidden_path_in_allowed_paths")

    forbidden_denied = _forbidden_path_overlap(denied_paths)
    if forbidden_denied and not denied_paths:
        reasons.append("invalid_denied_paths")

    overlap = [p for p in denied_paths if p in allowed_paths]
    if overlap:
        reasons.append("denied_path_also_allowed")

    for path in allowed_paths:
        norm = _normalize_posix(path)
        if norm.startswith("../") or "/../" in norm:
            reasons.append("allowed_path_escapes_repo_root")

    if not rollback_plan:
        reasons.append("cleanup_plan_missing")

    worktree_path = _proposed_worktree_path(repo_root, work_order_id, nonce or "missing")
    expected_prefix = f"{_normalize_posix(str(_external_worktree_root(repo_root)))}/{work_order_id}/"
    if not worktree_path.startswith(expected_prefix):
        reasons.append("worktree_path_not_confined")

    lock_key = work_order_id
    if locks is not None and lock_key in locks:
        reasons.append("lock_collision")

    return reasons


def plan_wre_isolated_worktree_execution_dryrun(
    invocation_result: Union[WorkOrderDryRunInvocationResult, Mapping[str, Any]],
    work_order: Mapping[str, Any],
    *,
    now: Optional[datetime] = None,
    locks: Optional[MutableSet[str]] = None,
    repo_root: str = ".",
) -> WREExecutorDryRunResult:
    """Plan isolated worktree execution without mutation (dry-run only)."""
    checked = _utc_now(now)
    checked_at = _iso8601(checked)
    invocation = _invocation_from_any(invocation_result)
    work_order_id = _work_order_id(work_order)

    if invocation.decision == INVOCATION_REJECT:
        return _rejection_result(work_order_id, ["invocation_rejected"], checked_at)
    if invocation.decision == INVOCATION_ACCEPT_WITH_RETRIEVAL_GAP:
        return _rejection_result(
            work_order_id,
            ["retrieval_gap_not_allowed_for_executor_plan"],
            checked_at,
        )
    if invocation.decision != INVOCATION_ACCEPT:
        return _rejection_result(work_order_id, ["invocation_not_accepted"], checked_at)
    if not invocation.no_execution_performed:
        return _rejection_result(work_order_id, ["prior_spine_execution_detected"], checked_at)
    if not invocation.receipt_digest:
        return _rejection_result(work_order_id, ["missing_invocation_receipt_digest"], checked_at)

    contract_reasons = _validate_contract_rules(work_order, repo_root, locks)
    if contract_reasons:
        return _rejection_result(work_order_id, contract_reasons, checked_at)

    branch_name = str(work_order["branch_name"]).strip()
    base_ref = canonical_work_order_base_ref(work_order)
    work_order_digest = canonical_full_work_order_digest(work_order)
    nonce = str(work_order["nonce"]).strip()
    lock_key = work_order_id
    worktree_path = _proposed_worktree_path(repo_root, work_order_id, nonce)
    allowed_paths = list(work_order.get("allowed_paths") or [])
    denied_paths = list(work_order.get("denied_paths") or [])
    required_tests = list(work_order.get("required_tests") or [])
    cleanup_plan = _build_cleanup_plan(work_order)

    phase_receipts: List[ExecutorDryRunPhaseReceipt] = []
    phase_receipts.append(
        _phase_receipt(
            PHASE_PLAN_BUILT,
            work_order_id,
            {
                "proposed_branch_name": branch_name,
                "base_ref": base_ref,
                "work_order_digest": work_order_digest,
                "proposed_worktree_path": worktree_path,
                "invocation_receipt_digest": invocation.receipt_digest,
            },
            checked_at,
        )
    )
    phase_receipts.append(
        _phase_receipt(
            PHASE_LOCK_CHECKED,
            work_order_id,
            {"lock_key": lock_key, "lock_available": True},
            checked_at,
        )
    )
    phase_receipts.append(
        _phase_receipt(
            PHASE_CLEANUP_PLANNED,
            work_order_id,
            {"cleanup_plan_digest": _canonical_digest(cleanup_plan)},
            checked_at,
        )
    )

    plan_body = {
        "work_order_id": work_order_id,
        "work_order_digest": work_order_digest,
        "base_ref": base_ref,
        "proposed_branch_name": branch_name,
        "proposed_worktree_path": worktree_path,
        "lock_key": lock_key,
        "allowed_paths": allowed_paths,
        "denied_paths": denied_paths,
        "required_tests": required_tests,
        "cleanup_plan": cleanup_plan,
        "no_mutation_performed": True,
        "invocation_receipt_digest": invocation.receipt_digest,
    }
    plan_digest = _canonical_digest(plan_body)
    plan_id = plan_digest

    plan = WREExecutorPlan(
        plan_id=plan_id,
        work_order_id=work_order_id,
        work_order_digest=work_order_digest,
        base_ref=base_ref,
        proposed_branch_name=branch_name,
        proposed_worktree_path=worktree_path,
        lock_key=lock_key,
        allowed_paths=allowed_paths,
        denied_paths=denied_paths,
        required_tests=required_tests,
        cleanup_plan=cleanup_plan,
        phase_receipts=phase_receipts,
        no_mutation_performed=True,
        invocation_receipt_digest=invocation.receipt_digest,
        plan_digest=plan_digest,
    )

    return WREExecutorDryRunResult(
        decision=EXECUTOR_PLAN_ACCEPT,
        work_order_id=work_order_id,
        plan=plan,
        rejection_reasons=[],
        rejection_receipt_digest="",
        no_mutation_performed=True,
        phase_receipts=phase_receipts,
    )


__all__ = [
    "EXECUTOR_PLAN_ACCEPT",
    "EXECUTOR_PLAN_REJECT",
    "PHASE_CLEANUP_PLANNED",
    "PHASE_LOCK_CHECKED",
    "PHASE_PLAN_BUILT",
    "ExecutorDryRunPhaseReceipt",
    "WREExecutorDryRunResult",
    "WREExecutorPlan",
    "canonical_external_worktree_path",
    "plan_wre_isolated_worktree_execution_dryrun",
]
