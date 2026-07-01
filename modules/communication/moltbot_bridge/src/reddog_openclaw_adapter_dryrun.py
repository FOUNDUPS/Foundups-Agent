"""RedDog OpenClaw FoundUpJob adapter dry-run planner (no enqueue).

Slice: REDDOG_OPENCLAW_FOUNDUPJOB_ADAPTER_DRYRUN_PHASE1
Contract: docs/audits/architecture/REDDOG_OPENCLAW_FOUNDUPJOB_ADAPTER_DRYRUN_CONTRACT_PHASE1.md
Mapping: docs/audits/architecture/REDDOG_WORK_ORDER_TO_OPENCLAW_FOUNDUPJOB_ADAPTER_CONTRACT_PHASE1.md

Translates a fully gated RedDog spine plus open dry-run valve into a proposed
FoundUpJob or AgentDB autonomous_task intake record. Proposes only -- no enqueue,
no AgentDB writes, no Hermes/WRE execution.

WSP 97 TRUTH BOUNDARIES:
  DOES:
    - Require VALVE_OPEN_DRYRUN_ONLY (reject CLOSED / WORKTREE_CREATE)
    - Map spine fields to proposed intake per #901 contract
    - Emit adapter dry-run receipt with deterministic digests
    - Always set no_enqueue_performed and no_execution_performed

  DOES NOT:
    - Enqueue OpenClaw Supervisor, append FoundUpJob queue, or write AgentDB
    - Invoke Hermes, WRE executor, Skillz, subprocess, git, or gh
    - Create worktrees, branches, PRs, or mutate repository content
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional, Sequence, Union

from modules.communication.moltbot_bridge.src.reddog_governed_work_order_dryrun import (
    _normalize_operation,
)
from modules.communication.moltbot_bridge.src.reddog_openclaw_work_order_policy_gate import (
    POLICY_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_execution_valve import (
    INTAKE_ASSIGNMENT_DISPATCHER,
    INTAKE_AUTONOMOUS_TASK,
    INTAKE_FOUNDUP_JOB,
    VALVE_CLOSED,
    VALVE_OPEN_DRYRUN_ONLY,
    VALVE_OPEN_WORKTREE_CREATE,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_runtime_invocation import (
    INVOCATION_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_executor_dryrun import (
    EXECUTOR_PLAN_ACCEPT,
)

ADAPTER_DRYRUN_ACCEPT = "ADAPTER_DRYRUN_ACCEPT"
ADAPTER_DRYRUN_REJECT = "ADAPTER_DRYRUN_REJECT"

TARGET_FOUNDUP_JOB = "foundup_job"
TARGET_AUTONOMOUS_TASK = "autonomous_task"

FORBIDDEN_ADAPTER_OPERATIONS = frozenset(
    {"repo", "write", "pr", "merge_request", "merge", "push", "pull_request"}
)

OPERATION_TO_REQUESTED_ACTION: Dict[str, str] = {
    "audit_only": "validate_foundup",
    "docs_audit": "validate_foundup",
    "docs_only": "validate_foundup",
    "feature_slice": "build_foundup",
    "docs_patch": "build_foundup",
    "test_fix": "build_foundup",
}

_TASK_SUMMARY_MAX_LEN = 512
_TASK_ID_PREFIX = "reddog-wo-"
_JOB_ID_PREFIX = "reddog-fj-"

_WHITESPACE_RE = re.compile(r"\s+")


@dataclass
class ProposedOpenClawIntakeRecord:
    target_type: str
    proposed_job_id: Optional[str]
    proposed_task_id: Optional[str]
    work_order_id: str
    operation: str
    requested_action: Optional[str]
    repo_scope: str
    allowed_paths: List[str]
    denied_paths: List[str]
    required_tests: List[str]
    evidence_refs: List[str]
    policy_receipt_digest: str
    work_order_receipt_digest: str
    invocation_receipt_digest: str
    executor_plan_id: str
    valve_decision_digest: str
    no_enqueue_performed: bool
    no_execution_performed: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AdapterDryRunReceipt:
    adapter_receipt_id: str
    adapter_receipt_digest: str
    decision: str
    rejection_reasons: List[str]
    target_type: str
    work_order_id: str
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RedDogOpenClawAdapterDryRunResult:
    decision: str
    work_order_id: str
    proposed_intake: Optional[ProposedOpenClawIntakeRecord]
    adapter_receipt: AdapterDryRunReceipt
    rejection_reasons: List[str]
    no_enqueue_performed: bool
    no_execution_performed: bool

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        if self.proposed_intake is not None:
            payload["proposed_intake"] = self.proposed_intake.to_dict()
        payload["adapter_receipt"] = self.adapter_receipt.to_dict()
        return payload


def _utc_now(now: Optional[datetime] = None) -> datetime:
    value = now or datetime.now(timezone.utc)
    return value.astimezone(timezone.utc)


def _iso8601(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat()


def _canonical_digest(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _work_order_id(work_order: Mapping[str, Any]) -> str:
    return str(work_order.get("work_order_id") or "unknown")


def _sanitize_task_summary(text: str) -> str:
    cleaned = _WHITESPACE_RE.sub(" ", (text or "").strip())
    if len(cleaned) > _TASK_SUMMARY_MAX_LEN:
        return cleaned[: _TASK_SUMMARY_MAX_LEN - 3] + "..."
    return cleaned


def _path_covered_by_allowed(path: str, allowed_patterns: Sequence[str]) -> bool:
    normalized = path.replace("\\", "/")
    for pattern in allowed_patterns:
        pat = pattern.replace("\\", "/")
        if fnmatch.fnmatch(normalized, pat) or fnmatch.fnmatch(normalized, f"**/{pat}"):
            return True
    return False


def _build_evidence_refs(
    policy_digest: str,
    work_order_digest: str,
    invocation_digest: str,
    work_order: Mapping[str, Any],
) -> List[str]:
    refs: List[str] = []
    if policy_digest:
        refs.append(f"policy_gate:{policy_digest}")
    if work_order_digest:
        refs.append(f"reddog_receipt:{work_order_digest}")
    if invocation_digest:
        refs.append(f"invocation:{invocation_digest}")
    holo = work_order.get("holoindex_evidence")
    if isinstance(holo, Mapping):
        for ref in holo.get("evidence_refs") or []:
            text = str(ref).strip()
            if text and text not in refs:
                refs.append(text)
    for ref in work_order.get("holoindex_evidence_refs") or []:
        text = str(ref).strip()
        if text and text not in refs:
            refs.append(text)
    return refs


def _validate_valve(valve_decision: Mapping[str, Any]) -> List[str]:
    reasons: List[str] = []
    state = str(valve_decision.get("valve_state") or "")
    if state == VALVE_CLOSED:
        reasons.append("execution_valve_closed")
    elif state == VALVE_OPEN_WORKTREE_CREATE:
        reasons.append("worktree_valve_not_allowed_for_adapter_dryrun")
    elif state != VALVE_OPEN_DRYRUN_ONLY:
        reasons.append("execution_valve_not_dryrun_only")
    if valve_decision.get("no_execution_performed") is not True:
        reasons.append("valve_execution_detected")
    if not valve_decision.get("decision_digest"):
        reasons.append("missing_valve_decision_digest")
    if valve_decision.get("rejection_reasons"):
        reasons.append("valve_has_rejection_reasons")
    return reasons


def _validate_spine(
    work_order: Mapping[str, Any],
    policy_gate_receipt: Mapping[str, Any],
    reddog_work_order_receipt: Mapping[str, Any],
    invocation_result: Mapping[str, Any],
    executor_plan_result: Mapping[str, Any],
) -> List[str]:
    reasons: List[str] = []

    if policy_gate_receipt.get("decision") != POLICY_ACCEPT:
        reasons.append("policy_gate_not_accepted")
    if policy_gate_receipt.get("no_execution_performed") is not True:
        reasons.append("policy_gate_execution_detected")

    if not reddog_work_order_receipt.get("receipt_id") or not reddog_work_order_receipt.get(
        "receipt_digest"
    ):
        reasons.append("missing_reddog_work_order_receipt")
    if reddog_work_order_receipt.get("no_execution_performed") is not True:
        reasons.append("receipt_execution_detected")

    policy_digest = str(policy_gate_receipt.get("receipt_digest") or "")
    if policy_digest and reddog_work_order_receipt.get("policy_gate_receipt_digest") != policy_digest:
        reasons.append("receipt_policy_digest_mismatch")

    if invocation_result.get("decision") != INVOCATION_ACCEPT:
        reasons.append("invocation_not_accepted")
    if invocation_result.get("no_execution_performed") is not True:
        reasons.append("invocation_execution_detected")
    if not invocation_result.get("receipt_digest"):
        reasons.append("missing_invocation_receipt_digest")

    if executor_plan_result.get("decision") != EXECUTOR_PLAN_ACCEPT:
        reasons.append("executor_plan_not_accepted")
    if executor_plan_result.get("no_mutation_performed") is not True:
        reasons.append("executor_mutation_detected")

    plan = executor_plan_result.get("plan")
    if not isinstance(plan, Mapping):
        reasons.append("missing_executor_plan")
    elif not plan.get("plan_id") or not plan.get("plan_digest"):
        reasons.append("incomplete_executor_plan")

    op_norm = _normalize_operation(str(work_order.get("requested_operation") or ""))
    if op_norm in FORBIDDEN_ADAPTER_OPERATIONS:
        reasons.append("forbidden_adapter_operation")

    return reasons


def _validate_target(target_type: str) -> List[str]:
    normalized = (target_type or "").strip().lower()
    if normalized == INTAKE_ASSIGNMENT_DISPATCHER:
        return ["assignment_dispatcher_forbidden_target"]
    if normalized not in {INTAKE_FOUNDUP_JOB, INTAKE_AUTONOMOUS_TASK}:
        return ["intake_target_not_canonical"]
    return []


def _validate_path_scope(work_order: Mapping[str, Any], plan: Mapping[str, Any]) -> List[str]:
    reasons: List[str] = []
    wo_allowed = list(work_order.get("allowed_paths") or [])
    plan_allowed = list(plan.get("allowed_paths") or [])
    denied = {
        str(p)
        for p in list(work_order.get("denied_paths") or []) + list(plan.get("denied_paths") or [])
    }

    if wo_allowed:
        for path in plan_allowed:
            if not _path_covered_by_allowed(str(path), wo_allowed):
                reasons.append("path_outside_allowed_scope")
                break

    for path in plan_allowed:
        norm = str(path).replace("\\", "/")
        if norm.startswith("../") or "/../" in norm:
            reasons.append("path_escapes_repo_scope")
            break
        if str(path) in denied:
            reasons.append("path_in_denied_scope")
            break

    worktree = str(plan.get("proposed_worktree_path") or "")
    work_order_id = _work_order_id(work_order)
    if worktree and f"/.reddog/worktrees/{work_order_id}/" not in worktree.replace("\\", "/"):
        reasons.append("worktree_path_outside_scope")

    return reasons


def _proposed_job_id(work_order_id: str, plan_id: str) -> str:
    seed = _canonical_digest({"work_order_id": work_order_id, "plan_id": plan_id})
    return f"{_JOB_ID_PREFIX}{seed[:16]}"


def _proposed_task_id(work_order_id: str) -> str:
    safe_id = re.sub(r"[^a-zA-Z0-9_-]+", "-", work_order_id.strip())[:64].strip("-") or "unknown"
    return f"{_TASK_ID_PREFIX}{safe_id}"


def _build_foundup_job_intake(
    work_order: Mapping[str, Any],
    plan: Mapping[str, Any],
    *,
    policy_digest: str,
    work_order_digest: str,
    invocation_digest: str,
    valve_digest: str,
) -> ProposedOpenClawIntakeRecord:
    work_order_id = _work_order_id(work_order)
    op_norm = _normalize_operation(str(work_order.get("requested_operation") or ""))
    requested_action = OPERATION_TO_REQUESTED_ACTION.get(op_norm, "")
    plan_id = str(plan.get("plan_id") or "")
    job_id = _proposed_job_id(work_order_id, plan_id)
    repo_scope = str(work_order.get("repo_full_name") or "")
    return ProposedOpenClawIntakeRecord(
        target_type=TARGET_FOUNDUP_JOB,
        proposed_job_id=job_id,
        proposed_task_id=None,
        work_order_id=work_order_id,
        operation=op_norm,
        requested_action=requested_action or None,
        repo_scope=repo_scope,
        allowed_paths=list(plan.get("allowed_paths") or work_order.get("allowed_paths") or []),
        denied_paths=list(plan.get("denied_paths") or work_order.get("denied_paths") or []),
        required_tests=list(work_order.get("required_tests") or []),
        evidence_refs=_build_evidence_refs(
            policy_digest, work_order_digest, invocation_digest, work_order
        ),
        policy_receipt_digest=policy_digest,
        work_order_receipt_digest=work_order_digest,
        invocation_receipt_digest=invocation_digest,
        executor_plan_id=plan_id,
        valve_decision_digest=valve_digest,
        no_enqueue_performed=True,
        no_execution_performed=True,
    )


def _build_autonomous_task_intake(
    work_order: Mapping[str, Any],
    plan: Mapping[str, Any],
    *,
    policy_digest: str,
    work_order_digest: str,
    invocation_digest: str,
    valve_digest: str,
) -> ProposedOpenClawIntakeRecord:
    work_order_id = _work_order_id(work_order)
    op_norm = _normalize_operation(str(work_order.get("requested_operation") or ""))
    plan_id = str(plan.get("plan_id") or "")
    task_id = _proposed_task_id(work_order_id)
    repo_scope = str(work_order.get("repo_full_name") or "")
    return ProposedOpenClawIntakeRecord(
        target_type=TARGET_AUTONOMOUS_TASK,
        proposed_job_id=None,
        proposed_task_id=task_id,
        work_order_id=work_order_id,
        operation=op_norm,
        requested_action=None,
        repo_scope=repo_scope,
        allowed_paths=list(plan.get("allowed_paths") or work_order.get("allowed_paths") or []),
        denied_paths=list(plan.get("denied_paths") or work_order.get("denied_paths") or []),
        required_tests=list(work_order.get("required_tests") or []),
        evidence_refs=_build_evidence_refs(
            policy_digest, work_order_digest, invocation_digest, work_order
        ),
        policy_receipt_digest=policy_digest,
        work_order_receipt_digest=work_order_digest,
        invocation_receipt_digest=invocation_digest,
        executor_plan_id=plan_id,
        valve_decision_digest=valve_digest,
        no_enqueue_performed=True,
        no_execution_performed=True,
    )


def _rejection_result(
    work_order_id: str,
    target_type: str,
    reasons: List[str],
    checked_at: str,
) -> RedDogOpenClawAdapterDryRunResult:
    receipt_core = {
        "decision": ADAPTER_DRYRUN_REJECT,
        "work_order_id": work_order_id,
        "rejection_reasons": reasons,
        "target_type": target_type,
        "no_enqueue_performed": True,
        "no_execution_performed": True,
        "created_at": checked_at,
    }
    receipt_digest = _canonical_digest(receipt_core)
    receipt_id = f"adapter-dryrun-{work_order_id}-{receipt_digest[:12]}"
    receipt = AdapterDryRunReceipt(
        adapter_receipt_id=receipt_id,
        adapter_receipt_digest=receipt_digest,
        decision=ADAPTER_DRYRUN_REJECT,
        rejection_reasons=reasons,
        target_type=target_type,
        work_order_id=work_order_id,
        created_at=checked_at,
    )
    return RedDogOpenClawAdapterDryRunResult(
        decision=ADAPTER_DRYRUN_REJECT,
        work_order_id=work_order_id,
        proposed_intake=None,
        adapter_receipt=receipt,
        rejection_reasons=reasons,
        no_enqueue_performed=True,
        no_execution_performed=True,
    )


def plan_reddog_openclaw_adapter_dryrun(
    work_order: Mapping[str, Any],
    policy_gate_receipt: Mapping[str, Any],
    reddog_work_order_receipt: Mapping[str, Any],
    invocation_result: Mapping[str, Any],
    executor_plan_result: Mapping[str, Any],
    valve_decision: Mapping[str, Any],
    *,
    target_type: str = INTAKE_FOUNDUP_JOB,
    now: Optional[datetime] = None,
) -> RedDogOpenClawAdapterDryRunResult:
    """Plan OpenClaw intake translation without enqueue or execution."""
    checked = _utc_now(now)
    checked_at = _iso8601(checked)
    work_order_id = _work_order_id(work_order)
    normalized_target = (target_type or INTAKE_FOUNDUP_JOB).strip().lower()

    reasons: List[str] = []
    reasons.extend(_validate_valve(valve_decision))
    reasons.extend(_validate_target(normalized_target))
    reasons.extend(
        _validate_spine(
            work_order,
            policy_gate_receipt,
            reddog_work_order_receipt,
            invocation_result,
            executor_plan_result,
        )
    )

    plan = executor_plan_result.get("plan")
    if isinstance(plan, Mapping):
        reasons.extend(_validate_path_scope(work_order, plan))

    op_norm = _normalize_operation(str(work_order.get("requested_operation") or ""))
    if normalized_target == INTAKE_FOUNDUP_JOB and op_norm not in OPERATION_TO_REQUESTED_ACTION:
        reasons.append("unsupported_operation_for_foundup_job")

    deduped = list(dict.fromkeys(reasons))
    if deduped:
        return _rejection_result(work_order_id, normalized_target, deduped, checked_at)

    assert isinstance(plan, Mapping)
    policy_digest = str(policy_gate_receipt.get("receipt_digest") or "")
    work_order_digest = str(reddog_work_order_receipt.get("receipt_digest") or "")
    invocation_digest = str(invocation_result.get("receipt_digest") or "")
    valve_digest = str(valve_decision.get("decision_digest") or "")

    if normalized_target == INTAKE_AUTONOMOUS_TASK:
        proposed = _build_autonomous_task_intake(
            work_order,
            plan,
            policy_digest=policy_digest,
            work_order_digest=work_order_digest,
            invocation_digest=invocation_digest,
            valve_digest=valve_digest,
        )
    else:
        proposed = _build_foundup_job_intake(
            work_order,
            plan,
            policy_digest=policy_digest,
            work_order_digest=work_order_digest,
            invocation_digest=invocation_digest,
            valve_digest=valve_digest,
        )

    intake_digest = _canonical_digest(proposed.to_dict())
    receipt_core = {
        "decision": ADAPTER_DRYRUN_ACCEPT,
        "work_order_id": work_order_id,
        "target_type": normalized_target,
        "proposed_intake_digest": intake_digest,
        "rejection_reasons": [],
        "no_enqueue_performed": True,
        "no_execution_performed": True,
        "created_at": checked_at,
    }
    receipt_digest = _canonical_digest(receipt_core)
    receipt_id = f"adapter-dryrun-{work_order_id}-{receipt_digest[:12]}"
    receipt = AdapterDryRunReceipt(
        adapter_receipt_id=receipt_id,
        adapter_receipt_digest=receipt_digest,
        decision=ADAPTER_DRYRUN_ACCEPT,
        rejection_reasons=[],
        target_type=normalized_target,
        work_order_id=work_order_id,
        created_at=checked_at,
    )

    return RedDogOpenClawAdapterDryRunResult(
        decision=ADAPTER_DRYRUN_ACCEPT,
        work_order_id=work_order_id,
        proposed_intake=proposed,
        adapter_receipt=receipt,
        rejection_reasons=[],
        no_enqueue_performed=True,
        no_execution_performed=True,
    )


__all__ = [
    "ADAPTER_DRYRUN_ACCEPT",
    "ADAPTER_DRYRUN_REJECT",
    "AdapterDryRunReceipt",
    "ProposedOpenClawIntakeRecord",
    "RedDogOpenClawAdapterDryRunResult",
    "TARGET_AUTONOMOUS_TASK",
    "TARGET_FOUNDUP_JOB",
    "plan_reddog_openclaw_adapter_dryrun",
]
